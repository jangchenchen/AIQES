#!/usr/bin/env python3
"""Web API 服务器 - 对接答题系统后端"""

import json
import uuid
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
from src.record_manager import RecordManager

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# 全局变量存储会话数据
sessions: Dict[str, Dict[str, Any]] = {}
UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

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
        ai_count = data.get('ai_count', 0)
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

        # 生成题目
        generator = QuestionGenerator(entries)
        questions = generator.generate_questions(type_filters=type_filters)

        # AI 生成额外题目
        if ai_count > 0:
            ai_config = load_ai_config()
            if ai_config:
                try:
                    ai_client = AIClient(ai_config)
                    ai_questions = ai_client.generate_additional_questions(
                        entries,
                        count=ai_count,
                        question_types=type_filters,
                    )
                    questions.extend(ai_questions)
                except (AITransportError, AIResponseFormatError) as e:
                    # AI 失败不影响主流程
                    pass

        if not questions:
            return jsonify({"error": "题库为空，无法生成题目"}), 400

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

    # 简单的关键词匹配
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
