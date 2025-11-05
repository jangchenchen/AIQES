#!/usr/bin/env python3
"""Web API 服务器 - 对接答题系统后端"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from manage_ai_config import (
    load_config as load_ai_config,
    save_config,
    test_connectivity,
    delete_config,
    AIConfig,
)
from src.ai_client import AIClient, AIResponseFormatError, AITransportError
from src.knowledge_loader import MAX_KNOWLEDGE_FILE_SIZE, load_knowledge_entries
from src.question_generator import QuestionGenerator
from src.question_models import Question, QuestionType
from src.record_manager import RecordManager, _dict_to_question as dict_to_question

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# 全局变量存储会话数据
sessions: Dict[str, Dict[str, Any]] = {}
UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)
SESSIONS_FILE = Path("data/sessions.json")
SESSIONS_FILE.parent.mkdir(exist_ok=True)

# 初始化 RecordManager
record_manager = RecordManager()


# Session持久化函数
def load_sessions():
    """从文件加载sessions"""
    global sessions
    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 反序列化Question对象
                for session_id, session in data.items():
                    if 'questions' in session:
                        session['questions'] = [
                            dict_to_question(q) for q in session['questions']
                        ]
                sessions = data
                print(f"✅ 加载了 {len(sessions)} 个会话")
        except Exception as e:
            print(f"⚠️  加载会话失败: {e}")
            sessions = {}


def save_sessions():
    """保存sessions到文件"""
    try:
        # 序列化Question对象
        data = {}
        for session_id, session in sessions.items():
            session_copy = session.copy()
            if 'questions' in session_copy:
                session_copy['questions'] = [
                    question_to_dict(q) for q in session_copy['questions']
                ]
            data[session_id] = session_copy

        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️  保存会话失败: {e}")


# 启动时加载sessions
load_sessions()

_TYPE_ALIAS: Dict[str, QuestionType] = {
    "single": QuestionType.SINGLE_CHOICE,
    "multi": QuestionType.MULTI_CHOICE,
    "cloze": QuestionType.CLOZE,
    "qa": QuestionType.QA,
}


def question_to_dict(q: Question) -> Dict[str, Any]:
    """将 Question 对象转换为字典"""
    return {
        "identifier": q.identifier,
        "question_type": q.question_type.name,
        "prompt": q.prompt,
        "options": q.options,
        "correct_options": q.correct_options,
        "answer_text": q.answer_text,
        "explanation": q.explanation,
        "keywords": q.keywords,
    }


def _parse_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"true", "1", "yes"}:
        return True
    if lowered in {"false", "0", "no"}:
        return False
    return None


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed


@app.route('/')
def index():
    """主页"""
    return send_from_directory('frontend', 'app.html')


@app.route('/web/<path:filename>')
def serve_web_files(filename):
    """Serve files from the web/ directory (for AI config page)"""
    return send_from_directory('web', filename)


@app.route('/api/upload-knowledge', methods=['POST'])
def upload_knowledge():
    """上传知识文件"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "未选择文件"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "文件名为空"}), 400

        # 检查文件大小
        file.seek(0, 2)  # 移动到文件末尾
        size = file.tell()
        file.seek(0)  # 回到开头

        if size > MAX_KNOWLEDGE_FILE_SIZE:
            return jsonify({
                "error": f"文件过大（{size // 1024}KB），最大支持 {MAX_KNOWLEDGE_FILE_SIZE // 1024}KB"
            }), 400

        # 检查文件扩展名
        ext = Path(file.filename).suffix.lower()
        if ext not in ['.txt', '.md', '.pdf']:
            return jsonify({"error": "仅支持 .txt、.md、.pdf 格式"}), 400

        # 保存文件
        filename = f"{uuid.uuid4()}{ext}"
        filepath = UPLOAD_FOLDER / filename
        file.save(filepath)

        # 加载知识条目
        try:
            entries = load_knowledge_entries(filepath)
        except Exception as e:
            filepath.unlink()  # 删除无效文件
            return jsonify({"error": f"解析失败：{str(e)}"}), 400

        return jsonify({
            "success": True,
            "filename": filename,
            "filepath": str(filepath),
            "entry_count": len(entries),
            "entries_preview": [
                {"component": e.component, "text": e.raw_text[:100] + "..."}
                for e in entries[:3]
            ]
        })

    except Exception as e:
        return jsonify({"error": f"上传失败：{str(e)}"}), 500


@app.route('/api/generate-questions', methods=['POST'])
def generate_questions():
    """生成题目"""
    try:
        data = request.json
        filepath = data.get('filepath')
        question_types = data.get('types', ['single', 'multi', 'cloze', 'qa'])
        count = data.get('count', 10)
        use_ai = data.get('use_ai', False)  # 新参数：是否使用AI增强
        mode = data.get('mode', 'sequential')
        seed = data.get('seed')

        if not filepath:
            return jsonify({"error": "未指定知识文件"}), 400

        # 加载知识条目
        knowledge_path = Path(filepath)
        if not knowledge_path.exists():
            return jsonify({"error": "知识文件不存在"}), 404

        entries = load_knowledge_entries(knowledge_path)
        if not entries:
            return jsonify({"error": "知识文件为空"}), 400

        # 转换题型
        type_filters = [_TYPE_ALIAS[t] for t in question_types if t in _TYPE_ALIAS]
        if not type_filters:
            type_filters = list(_TYPE_ALIAS.values())

        questions = []
        ai_used = False

        # 优先使用AI生成所有题目
        ai_config = load_ai_config()
        if ai_config:
            try:
                ai_client = AIClient(ai_config)
                questions = ai_client.generate_additional_questions(
                    entries,
                    count=count,
                    question_types=type_filters,
                )
                ai_used = True
                print(f"✅ AI生成成功：生成 {len(questions)} 道题目")
            except (AITransportError, AIResponseFormatError) as e:
                print(f"⚠️  AI生成失败：{str(e)}，降级使用本地生成")
                ai_used = False

        # 如果AI未配置或失败，降级使用本地生成
        if not questions:
            print("📝 使用本地算法生成题目")
            generator = QuestionGenerator(entries)
            questions = generator.generate_questions(type_filters=type_filters)

            # 限制数量
            if count and count < len(questions):
                questions = questions[:count]

        if not questions:
            return jsonify({"error": "题库为空，无法生成题目。请检查知识文件内容或配置AI。"}), 400

        # 创建会话
        session_id = str(uuid.uuid4())

        # 模式处理
        if mode == 'random':
            import random
            rng = random.Random(seed)
            rng.shuffle(questions)

        # 限制数量
        if count and count < len(questions):
            questions = questions[:count]

        # 保存会话
        sessions[session_id] = {
            "questions": questions,
            "current_index": 0,
            "answers": [],
            "correct_count": 0,
            "total_count": len(questions),
            "filepath": filepath,
        }
        save_sessions()  # 持久化到文件

        return jsonify({
            "success": True,
            "session_id": session_id,
            "total_count": len(questions),
            "question_types": list(set(q.question_type.name for q in questions)),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"生成失败：{str(e)}"}), 500


@app.route('/api/get-question', methods=['POST'])
def get_question():
    """获取当前题目"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({"error": "会话不存在"}), 404

        session = sessions[session_id]
        index = session['current_index']

        if index >= len(session['questions']):
            return jsonify({
                "finished": True,
                "correct_count": session['correct_count'],
                "total_count": session['total_count'],
            })

        question = session['questions'][index]

        return jsonify({
            "finished": False,
            "question": question_to_dict(question),
            "current_index": index + 1,
            "total_count": session['total_count'],
        })

    except Exception as e:
        return jsonify({"error": f"获取题目失败：{str(e)}"}), 500


@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    """提交答案"""
    try:
        data = request.json
        session_id = data.get('session_id')
        user_answer = data.get('answer', '').strip()

        if not session_id or session_id not in sessions:
            return jsonify({"error": "会话不存在"}), 404

        session = sessions[session_id]
        index = session['current_index']

        if index >= len(session['questions']):
            return jsonify({"error": "已完成所有题目"}), 400

        question = session['questions'][index]

        # 判分
        is_correct, plain_explanation = _grade_answer(question, user_answer)

        # 记录答案
        session['answers'].append({
            "question_id": question.identifier,
            "user_answer": user_answer,
            "is_correct": is_correct,
            "explanation": plain_explanation,
        })

        if is_correct:
            session['correct_count'] += 1

        # 移动到下一题
        session['current_index'] += 1
        save_sessions()  # 持久化到文件

        # 记录到数据库（如果需要）
        record_manager = RecordManager()
        record_manager.log_attempt(
            session_id=session_id,
            question=question,
            user_answer=user_answer,
            is_correct=is_correct,
            plain_explanation=plain_explanation,
            session_context={
                "filepath": session.get('filepath'),
                "mode": "web",
            }
        )

        # 错题管理
        if is_correct:
            record_manager.remove_wrong_question(question.identifier)
        else:
            record_manager.upsert_wrong_question(
                question,
                last_plain_explanation=plain_explanation
            )

        return jsonify({
            "success": True,
            "is_correct": is_correct,
            "explanation": plain_explanation,
            "correct_answer": _get_correct_answer_text(question),
            "next_available": session['current_index'] < len(session['questions']),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"提交失败：{str(e)}"}), 500


@app.route('/api/session-status', methods=['POST'])
def session_status():
    """获取会话状态"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({"error": "会话不存在"}), 404

        session = sessions[session_id]

        return jsonify({
            "session_id": session_id,
            "current_index": session['current_index'],
            "total_count": session['total_count'],
            "correct_count": session['correct_count'],
            "finished": session['current_index'] >= session['total_count'],
        })

    except Exception as e:
        return jsonify({"error": f"获取状态失败：{str(e)}"}), 500


# ============ Answer History API Routes ============


@app.route('/api/answer-history', methods=['GET'])
def api_answer_history():
    """分页返回历史作答记录"""
    try:
        page = max(1, int(request.args.get('page', 1)))
        page_size = int(request.args.get('page_size', 20))
        page_size = max(1, min(page_size, 200))

        session_id = request.args.get('session_id') or None
        question_type_param = request.args.get('question_type')
        question_type = None
        if question_type_param:
            try:
                question_type = QuestionType[question_type_param]
            except KeyError:
                return jsonify({"error": f"无效的题型: {question_type_param}"}), 400

        is_correct_raw = request.args.get('is_correct')
        is_correct = _parse_bool(is_correct_raw)
        if is_correct_raw is not None and is_correct is None:
            return jsonify({"error": "is_correct 参数必须为 true/false"}), 400

        date_from_raw = request.args.get('date_from')
        date_to_raw = request.args.get('date_to')
        date_from = _parse_datetime(date_from_raw)
        date_to = _parse_datetime(date_to_raw)
        if date_from_raw and date_from is None:
            return jsonify({"error": "date_from 不是有效的 ISO 8601 时间"}), 400
        if date_to_raw and date_to is None:
            return jsonify({"error": "date_to 不是有效的 ISO 8601 时间"}), 400

        result = record_manager.query_answer_history(
            page=page,
            page_size=page_size,
            session_id=session_id,
            question_type=question_type,
            is_correct=is_correct,
            date_from=date_from,
            date_to=date_to,
        )
        return jsonify({"success": True, "data": result})
    except ValueError as exc:
        return jsonify({"error": f"参数错误：{exc}"}), 400
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"获取历史失败：{str(exc)}"}), 500


@app.route('/api/answer-history/sessions', methods=['GET'])
def api_answer_history_sessions():
    """获取最近若干作答会话的摘要"""
    try:
        limit = int(request.args.get('limit', 20))
        limit = max(1, min(limit, 100))
        summaries = record_manager.list_answer_history_sessions(limit=limit)
        return jsonify({"success": True, "data": summaries})
    except ValueError as exc:
        return jsonify({"error": f"参数错误：{exc}"}), 400
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"获取会话失败：{str(exc)}"}), 500


# ============ Wrong Questions API Routes ============

@app.route('/api/wrong-questions', methods=['GET'])
def get_wrong_questions():
    """获取错题列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        question_type_str = request.args.get('question_type')
        sort_by = request.args.get('sort_by', 'last_wrong_at')
        order = request.args.get('order', 'desc')

        question_type = None
        if question_type_str:
            try:
                question_type = QuestionType[question_type_str]
            except KeyError:
                return jsonify({"error": f"无效的题型: {question_type_str}"}), 400

        result = record_manager.get_wrong_questions_paginated(
            page=page,
            page_size=page_size,
            question_type=question_type,
            sort_by=sort_by,
            order=order,
        )

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"获取错题失败：{str(e)}"}), 500


@app.route('/api/wrong-questions/stats', methods=['GET'])
def get_wrong_questions_stats():
    """获取错题统计"""
    try:
        stats = record_manager.get_wrong_question_stats()
        return jsonify({
            "success": True,
            "data": stats
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"获取统计失败：{str(e)}"}), 500


@app.route('/api/wrong-questions/practice', methods=['POST'])
def start_wrong_question_practice():
    """创建错题复练会话"""
    try:
        data = request.json or {}
        question_types = data.get('question_types', [])
        count = data.get('count')
        mode = data.get('mode', 'random')

        # 加载错题
        wrong_questions = record_manager.load_wrong_questions()

        if not wrong_questions:
            return jsonify({"error": "当前没有错题"}), 400

        # 筛选题型
        if question_types:
            type_filters = [QuestionType[t] for t in question_types if t in QuestionType.__members__]
            wrong_questions = [q for q in wrong_questions if q.question_type in type_filters]

        if not wrong_questions:
            return jsonify({"error": "没有符合条件的错题"}), 400

        # 随机/顺序
        if mode == 'random':
            import random
            random.shuffle(wrong_questions)

        # 限制数量
        if count and count < len(wrong_questions):
            wrong_questions = wrong_questions[:count]

        # 创建会话
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "questions": wrong_questions,
            "current_index": 0,
            "answers": [],
            "correct_count": 0,
            "total_count": len(wrong_questions),
            "mode": "wrong_question_practice",  # 标识为错题练习
        }
        save_sessions()  # 持久化到文件

        return jsonify({
            "success": True,
            "session_id": session_id,
            "total_count": len(wrong_questions),
            "question_types": list(set(q.question_type.name for q in wrong_questions)),
            "mode": "wrong_question_practice"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"创建练习失败：{str(e)}"}), 500


@app.route('/api/wrong-questions/<identifier>', methods=['GET'])
def get_wrong_question_detail(identifier: str):
    """获取单个错题详情"""
    try:
        detail = record_manager.get_wrong_question_detail(identifier)
        if not detail:
            return jsonify({"error": "题目不存在"}), 404

        return jsonify({
            "success": True,
            "data": detail
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"获取详情失败：{str(e)}"}), 500


@app.route('/api/wrong-questions/<identifier>', methods=['DELETE'])
def delete_wrong_question(identifier: str):
    """删除单个错题"""
    try:
        record_manager.remove_wrong_question(identifier)
        return jsonify({
            "success": True,
            "message": "错题已删除"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"删除失败：{str(e)}"}), 500


@app.route('/api/wrong-questions', methods=['DELETE'])
def clear_wrong_questions():
    """清空错题本"""
    try:
        count = record_manager.clear_all_wrong_questions()
        return jsonify({
            "success": True,
            "message": "已清空错题本",
            "deleted_count": count
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"清空失败：{str(e)}"}), 500


# ============ AI Configuration API Routes ============

@app.route('/api/ai-config', methods=['GET'])
def get_ai_config():
    """获取当前 AI 配置"""
    try:
        config = load_ai_config()
        if config is None:
            return jsonify(None)

        return jsonify({
            "url": config.url,
            "key": config.key,
            "model": config.model,
            "timeout": config.timeout,
            "dev_document": config.dev_document,
        })
    except Exception as e:
        return jsonify({"error": f"获取配置失败：{str(e)}"}), 500


@app.route('/api/ai-config', methods=['PUT'])
def put_ai_config():
    """保存/更新 AI 配置"""
    try:
        data = request.json

        url = data.get('url', '').strip()
        key = data.get('key', '').strip()
        model = data.get('model', '').strip()
        timeout = data.get('timeout', 10.0)
        dev_document = data.get('dev_document', '').strip()

        if not url or not key or not model:
            return jsonify({"error": "URL、Key 和模型名称为必填项"}), 400

        config = AIConfig(
            key=key,
            url=url,
            model=model,
            timeout=float(timeout) if timeout else 10.0,
            dev_document=dev_document if dev_document else None,
        )

        save_config(config)

        return jsonify({
            "url": config.url,
            "key": config.key,
            "model": config.model,
            "timeout": config.timeout,
            "dev_document": config.dev_document,
        })
    except Exception as e:
        return jsonify({"error": f"保存配置失败：{str(e)}"}), 500


@app.route('/api/ai-config/test', methods=['POST'])
def test_ai_config():
    """测试 AI 配置连通性"""
    try:
        data = request.json

        url = data.get('url', '').strip()
        key = data.get('key', '').strip()
        model = data.get('model', '').strip()
        timeout = data.get('timeout', 10.0)
        dev_document = data.get('dev_document', '').strip()

        if not url or not key or not model:
            return jsonify({
                "ok": False,
                "message": "URL、Key 和模型名称为必填项"
            }), 400

        config = AIConfig(
            key=key,
            url=url,
            model=model,
            timeout=float(timeout) if timeout else 10.0,
            dev_document=dev_document if dev_document else None,
        )

        ok, message = test_connectivity(config)

        return jsonify({
            "ok": ok,
            "message": message
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"测试失败：{str(e)}"
        }), 500


@app.route('/api/ai-config', methods=['DELETE'])
def delete_ai_config():
    """删除当前 AI 配置"""
    try:
        deleted = delete_config()
        if not deleted:
            return jsonify({"error": "当前没有已保存的配置"}), 404

        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": f"删除配置失败：{str(e)}"}), 500


@app.route('/api/reset-data', methods=['POST'])
def reset_data():
    """清空所有数据（保留AI配置）"""
    try:
        # 清空会话
        global sessions
        sessions = {}
        if SESSIONS_FILE.exists():
            SESSIONS_FILE.unlink()

        # 清空答题历史
        history_file = Path("data/answer_history.jsonl")
        if history_file.exists():
            history_file.unlink()

        # 清空错题本
        wrong_file = Path("data/wrong_questions.json")
        if wrong_file.exists():
            wrong_file.write_text("[]", encoding="utf-8")

        # 清空上传的知识文件
        uploads_dir = Path("uploads")
        if uploads_dir.exists():
            for file in uploads_dir.glob("*"):
                if file.is_file():
                    file.unlink()

        print("✅ 数据已重置（保留AI配置）")
        return jsonify({
            "success": True,
            "message": "所有数据已清空（AI配置已保留）"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"重置失败：{str(e)}"}), 500


def _try_ai_grading(question: Question, user_answer: str, question_type_name: str) -> Optional[tuple[bool, str]]:
    """
    尝试使用AI进行语义评分

    返回：
    - (is_correct, explanation) 如果AI评分成功
    - None 如果AI未启用或评分失败（降级到关键词匹配）
    """
    try:
        ai_config = load_ai_config()
        if not ai_config or not ai_config.enable_ai_grading:
            return None  # AI评分未启用

        if not question.answer_text:
            return None  # 没有标准答案，无法AI评分

        ai_client = AIClient(ai_config)
        result = ai_client.evaluate_answer(
            question_prompt=question.prompt,
            standard_answer=question.answer_text,
            user_answer=user_answer,
            question_type=question_type_name
        )

        if result.get("error"):
            print(f"⚠️  AI评分失败：{result.get('explanation')}，降级到关键词匹配")
            return None  # AI评分失败，降级

        is_correct = result["is_correct"]
        score = result["score"]
        explanation = result["explanation"]
        matched_points = result.get("matched_points", [])

        # 格式化反馈信息
        if is_correct:
            feedback = f"✓ AI评分：{score}分 - {explanation}"
            if matched_points:
                feedback += f"\n匹配要点：{', '.join(matched_points)}"
        else:
            feedback = f"✗ AI评分：{score}分 - {explanation}"

        print(f"✅ AI评分成功：{'正确' if is_correct else '错误'} ({score}分)")
        return (is_correct, feedback)

    except Exception as e:
        print(f"⚠️  AI评分异常：{str(e)}，降级到关键词匹配")
        return None  # 异常时降级


def _grade_answer(question: Question, user_answer: str) -> tuple[bool, str]:
    """判分逻辑"""
    if question.question_type == QuestionType.SINGLE_CHOICE:
        return _grade_single_choice(question, user_answer)
    elif question.question_type == QuestionType.MULTI_CHOICE:
        return _grade_multi_choice(question, user_answer)
    elif question.question_type == QuestionType.CLOZE:
        return _grade_cloze(question, user_answer)
    elif question.question_type == QuestionType.QA:
        return _grade_qa(question, user_answer)
    else:
        return False, "未知题型"


def _grade_single_choice(question: Question, user_answer: str) -> tuple[bool, str]:
    """单选题判分"""
    user_answer = user_answer.upper().strip()

    # 转换字母为索引
    if len(user_answer) == 1 and 'A' <= user_answer <= 'Z':
        user_idx = ord(user_answer) - ord('A')
    else:
        return False, "请输入有效的选项字母（如 A、B、C）"

    correct_idx = question.correct_options[0] if question.correct_options else -1

    if user_idx == correct_idx:
        correct_text = question.options[correct_idx] if correct_idx < len(question.options) else ""
        return True, f"✓ 回答正确！正确答案是 {chr(ord('A') + correct_idx)} 选项：{correct_text[:50]}..."
    else:
        correct_letter = chr(ord('A') + correct_idx)
        return False, f"✗ 回答错误。正确答案是 {correct_letter} 选项，你选择了 {user_answer}。"


def _grade_multi_choice(question: Question, user_answer: str) -> tuple[bool, str]:
    """多选题判分"""
    user_answer = user_answer.upper().strip()
    user_letters = [c for c in user_answer if 'A' <= c <= 'Z']
    user_indices = sorted([ord(c) - ord('A') for c in user_letters])

    correct_indices = sorted(question.correct_options or [])

    if user_indices == correct_indices:
        correct_letters = ''.join(chr(ord('A') + i) for i in correct_indices)
        return True, f"✓ 回答正确！正确答案是 {correct_letters}"
    else:
        correct_letters = ''.join(chr(ord('A') + i) for i in correct_indices)
        user_letters_str = ''.join(user_letters)
        return False, f"✗ 回答错误。正确答案是 {correct_letters}，你选择了 {user_letters_str}。"


def _grade_cloze(question: Question, user_answer: str) -> tuple[bool, str]:
    """填空题判分"""
    # 尝试使用AI评分
    ai_result = _try_ai_grading(question, user_answer, "填空题")
    if ai_result:
        return ai_result

    # AI评分失败或未启用，使用关键词匹配
    normalized_answer = user_answer.strip().lower()

    if question.keywords:
        for keyword in question.keywords:
            if keyword.strip().lower() in normalized_answer:
                return True, f"✓ 回答正确！关键词匹配：{keyword}"

    if question.answer_text:
        expected = question.answer_text.strip().lower()
        if expected in normalized_answer or normalized_answer in expected:
            return True, f"✓ 回答正确！答案：{question.answer_text}"

    answer_hint = question.answer_text or (question.keywords[0] if question.keywords else "")
    return False, f"✗ 回答不完全正确。参考答案：{answer_hint}"


def _grade_qa(question: Question, user_answer: str) -> tuple[bool, str]:
    """问答题判分"""
    if not user_answer:
        return False, "回答不能为空"

    # 尝试使用AI评分
    ai_result = _try_ai_grading(question, user_answer, "问答题")
    if ai_result:
        return ai_result

    # AI评分失败或未启用，使用关键词匹配
    if question.keywords:
        matched = []
        for keyword in question.keywords:
            if keyword.strip().lower() in user_answer.lower():
                matched.append(keyword)

        if matched:
            return True, f"✓ 回答包含关键要点：{', '.join(matched)}"
        else:
            return False, f"提示：参考要点包括 {', '.join(question.keywords[:3])}"

    # 如果没有关键词，只检查长度
    if len(user_answer) >= 10:
        return True, "✓ 已收到回答"
    else:
        return False, "回答过于简短，请详细说明"


def _get_correct_answer_text(question: Question) -> str:
    """获取正确答案文本"""
    if question.question_type == QuestionType.SINGLE_CHOICE:
        idx = question.correct_options[0] if question.correct_options else -1
        if 0 <= idx < len(question.options):
            return f"{chr(ord('A') + idx)}. {question.options[idx]}"
    elif question.question_type == QuestionType.MULTI_CHOICE:
        letters = ''.join(chr(ord('A') + i) for i in sorted(question.correct_options or []))
        return letters
    elif question.question_type in (QuestionType.CLOZE, QuestionType.QA):
        return question.answer_text or (', '.join(question.keywords) if question.keywords else "")
    return ""


if __name__ == '__main__':
    print("=" * 60)
    print("答题考试系统（AI版）Web 服务器")
    print("=" * 60)
    print("访问地址: http://localhost:5001")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5001)
