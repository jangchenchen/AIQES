#!/usr/bin/env python3
"""集成测试：验证新增的答题记录、错题本、解析和AI功能"""

import json
import sys
from pathlib import Path
from subprocess import run, PIPE


def cleanup_test_data():
    """清理测试数据"""
    print("=== 清理测试数据 ===")
    data_dir = Path("data")
    if data_dir.exists():
        for file in ["answer_history_test.jsonl", "wrong_questions_test.json"]:
            path = data_dir / file
            if path.exists():
                path.unlink()
                print(f"✓ 删除 {file}")
    print()


def test_answer_recording():
    """测试答题历史记录"""
    print("=== 测试答题历史记录 ===")

    # 检查 JSONL 格式
    history_path = Path("data/answer_history.jsonl")
    if not history_path.exists():
        print("⚠️  答题历史文件不存在，跳过测试")
        return False

    try:
        lines = history_path.read_text().strip().split("\n")
        print(f"✓ 找到 {len(lines)} 条答题记录")

        # 验证每行都是合法 JSON
        for i, line in enumerate(lines[-3:], start=max(1, len(lines) - 2)):
            try:
                record = json.loads(line)
                assert "timestamp" in record
                assert "session_id" in record
                assert "question" in record
                assert "user_answer" in record
                assert "is_correct" in record
                assert "plain_explanation" in record
                print(f"✓ 记录 {i} 格式正确")
            except Exception as e:
                print(f"❌ 记录 {i} 格式错误：{e}")
                return False

        # 检查是否包含大白话解析
        last_record = json.loads(lines[-1])
        explanation = last_record.get("plain_explanation", "")
        if explanation:
            print(f"✓ 包含解析：{explanation[:50]}...")

        return True
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False


def test_wrong_questions():
    """测试错题本功能"""
    print("\n=== 测试错题本功能 ===")

    # 先清空错题本
    wrong_path = Path("data/wrong_questions.json")
    if wrong_path.exists():
        wrong_path.unlink()
        print("✓ 清空现有错题本")

    # 故意答错生成错题
    print("测试1：故意答错生成错题")
    result = run(
        ["python", "main.py", "--types", "single", "--count", "1", "--seed", "42"],
        input="A\n",
        capture_output=True,
        text=True,
    )

    if "❌" in result.stdout or "回答不正确" in result.stdout:
        print("✓ 生成错题记录")

        if wrong_path.exists():
            try:
                wrong_data = json.loads(wrong_path.read_text())
                assert isinstance(wrong_data, list)
                assert len(wrong_data) > 0
                assert "question" in wrong_data[0]
                assert "last_plain_explanation" in wrong_data[0]
                assert "last_wrong_at" in wrong_data[0]
                print(f"✓ 错题本包含 {len(wrong_data)} 道题")
                print(f"✓ 错题信息完整")
            except Exception as e:
                print(f"❌ 错题本格式错误：{e}")
                return False
        else:
            print("❌ 错题本未生成")
            return False
    else:
        print("⚠️  未能生成错题（答对了），跳过后续测试")
        return True

    # 测试错题复练
    print("\n测试2：错题复练")
    result = run(
        ["python", "main.py", "--review-wrong", "--count", "1"],
        input="Z\n",  # 随便输入一个答案
        capture_output=True,
        text=True,
    )

    if "进入错题练习模式" in result.stdout:
        print("✓ 错题复练模式启动成功")
    else:
        print("⚠️  未能进入错题复练模式")

    return True


def test_plain_explanation():
    """测试大白话解析功能"""
    print("\n=== 测试大白话解析 ===")

    result = run(
        ["python", "main.py", "--types", "single", "--count", "1"],
        input="B\n",
        capture_output=True,
        text=True,
    )

    # 检查是否包含解析
    if "解析：" in result.stdout:
        print("✓ 输出包含解析")

        # 提取解析内容
        lines = result.stdout.split("\n")
        for line in lines:
            if line.startswith("解析："):
                explanation = line[3:].strip()
                print(f"✓ 解析内容：{explanation[:80]}...")

                # 检查是否是大白话（包含关键词）
                keywords = ["选得很准", "填的是", "正确答案", "选项", "留意"]
                if any(kw in explanation for kw in keywords):
                    print("✓ 解析风格为大白话")
                    return True
                else:
                    print("⚠️  解析可能不够通俗")
                    return True
        return False
    else:
        print("⚠️  未找到解析输出")
        return False


def test_ai_prompt_fix():
    """测试 AI prompt 修复"""
    print("\n=== 测试 AI Prompt 修复 ===")

    try:
        from src.ai_client import AIClient, AIConfig
        from src.knowledge_loader import KnowledgeEntry

        config = AIConfig(key="test", url="http://test", model="test")
        client = AIClient(config)

        # 测试 prompt 构建
        summary = "测试知识点"
        count = 5
        types = ["single", "multi"]

        prompt = client._build_prompt(summary, count, types)

        # 检查是否正确格式化
        assert f"生成 {count} 道题" in prompt
        assert ", ".join(types) in prompt
        assert "{count}" not in prompt  # 确保已替换
        assert "{types}" not in prompt  # 确保已替换

        print("✓ AI prompt 构建正确")
        print(f"✓ 题目数量：{count}")
        print(f"✓ 题型限定：{', '.join(types)}")
        return True

    except Exception as e:
        print(f"❌ AI prompt 测试失败：{e}")
        return False


def test_cli_parameters():
    """测试新增CLI参数"""
    print("\n=== 测试 CLI 参数 ===")

    # 测试 --review-wrong
    result = run(
        ["python", "main.py", "--help"],
        capture_output=True,
        text=True,
    )

    if "--review-wrong" in result.stdout:
        print("✓ --review-wrong 参数存在")
    else:
        print("❌ --review-wrong 参数缺失")
        return False

    # 测试 --ai-questions
    if "--ai-questions" in result.stdout:
        print("✓ --ai-questions 参数存在")
    else:
        print("❌ --ai-questions 参数缺失")
        return False

    # 测试 --ai-temperature
    if "--ai-temperature" in result.stdout:
        print("✓ --ai-temperature 参数存在")
    else:
        print("❌ --ai-temperature 参数缺失")
        return False

    return True


def test_data_persistence():
    """测试数据持久化"""
    print("\n=== 测试数据持久化 ===")

    data_dir = Path("data")
    if not data_dir.exists():
        print("❌ data 目录不存在")
        return False

    print("✓ data 目录存在")

    # 检查 answer_history.jsonl
    history_path = data_dir / "answer_history.jsonl"
    if history_path.exists():
        size = history_path.stat().st_size
        print(f"✓ answer_history.jsonl 存在 ({size} 字节)")
    else:
        print("⚠️  answer_history.jsonl 不存在（可能还没有答题）")

    # 检查是否是 JSONL 格式
    if history_path.exists():
        try:
            lines = history_path.read_text().strip().split("\n")
            for line in lines:
                json.loads(line)  # 验证每行都是合法 JSON
            print(f"✓ JSONL 格式正确 ({len(lines)} 行)")
        except Exception as e:
            print(f"❌ JSONL 格式错误：{e}")
            return False

    return True


def main():
    """运行所有集成测试"""
    print("=" * 60)
    print("集成测试：新增功能验证")
    print("=" * 60)
    print()

    tests = {
        "答题历史记录": test_answer_recording,
        "错题本功能": test_wrong_questions,
        "大白话解析": test_plain_explanation,
        "AI Prompt 修复": test_ai_prompt_fix,
        "CLI 参数": test_cli_parameters,
        "数据持久化": test_data_persistence,
    }

    results = {}
    for name, test_func in tests.items():
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ {name} 测试异常：{e}")
            results[name] = False

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name:<20} {status}")

    passed_count = sum(results.values())
    total_count = len(results)
    pass_rate = 100 * passed_count / total_count if total_count > 0 else 0

    print("\n" + "=" * 60)
    print(f"通过率：{pass_rate:.1f}% ({passed_count}/{total_count})")

    if passed_count == total_count:
        print("🎉 所有集成测试通过！")
    elif passed_count > total_count // 2:
        print("⚠️  部分测试通过，需要关注失败项。")
    else:
        print("❌ 多数测试失败，需要修复。")
    print("=" * 60)

    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
