#!/usr/bin/env python3
"""测试脚本：检测代码中的潜在逻辑问题"""

from pathlib import Path

from src.knowledge_loader import load_knowledge_entries
from src.question_generator import QuestionGenerator
from src.question_models import QuestionType


def test_knowledge_loading():
    """测试知识库加载"""
    print("=== 测试知识库加载 ===")
    entries = load_knowledge_entries(Path("docs/Knowledge/电梯安全装置维护程序.md"))
    print(f"✓ 加载了 {len(entries)} 个知识条目")

    for entry in entries:
        if not entry.component:
            print(f"⚠️ 警告：发现空的部件名称")
        if not entry.sentences:
            print(f"⚠️ 警告：部件 {entry.component} 没有句子")

    print()


def test_question_generation():
    """测试题目生成"""
    print("=== 测试题目生成 ===")
    entries = load_knowledge_entries(Path("docs/Knowledge/电梯安全装置维护程序.md"))
    generator = QuestionGenerator(entries, seed=42)

    # 测试各类题目生成
    single_choice = generator.build_single_choice()
    print(f"✓ 生成了 {len(single_choice)} 个单选题")

    multi_choice = generator.build_multi_choice()
    print(f"✓ 生成了 {len(multi_choice)} 个多选题")

    cloze = generator.build_cloze()
    print(f"✓ 生成了 {len(cloze)} 个填空题")

    open_ended = generator.build_open_ended()
    print(f"✓ 生成了 {len(open_ended)} 个问答题")

    print()


def test_multi_choice_logic():
    """测试多选题生成逻辑中的潜在问题"""
    print("=== 检测多选题生成逻辑 ===")
    entries = load_knowledge_entries(Path("docs/Knowledge/电梯安全装置维护程序.md"))
    generator = QuestionGenerator(entries, seed=42)
    questions = generator.build_multi_choice()

    issues = []
    for q in questions:
        # 检查选项数量
        if q.options and len(q.options) < 2:
            issues.append(f"题目 {q.identifier} 选项数量不足: {len(q.options)}")

        # 检查正确选项数量
        if q.correct_options:
            if len(q.correct_options) < 1:
                issues.append(f"题目 {q.identifier} 没有正确选项")
            if len(q.correct_options) > len(q.options or []):
                issues.append(f"题目 {q.identifier} 正确选项数量超过总选项数")

        # 检查选项索引范围
        if q.options and q.correct_options:
            for idx in q.correct_options:
                if idx >= len(q.options):
                    issues.append(f"题目 {q.identifier} 正确选项索引超出范围: {idx}")

    if issues:
        print("⚠️ 发现以下问题：")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ 多选题生成逻辑正常")

    print()


def test_cloze_generation():
    """测试填空题生成"""
    print("=== 测试填空题生成 ===")
    entries = load_knowledge_entries(Path("docs/Knowledge/电梯安全装置维护程序.md"))
    generator = QuestionGenerator(entries, seed=42)
    questions = generator.build_cloze()

    issues = []
    for q in questions:
        if not q.prompt or "____" not in q.prompt:
            issues.append(f"题目 {q.identifier} 缺少填空标记")
        if not q.answer_text:
            issues.append(f"题目 {q.identifier} 缺少答案")

    if issues:
        print("⚠️ 发现以下问题：")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ 填空题生成正常")

    print()


def test_answer_parsing():
    """测试答案解析逻辑"""
    print("=== 测试答案解析 ===")
    from main import _letter_to_index, _parse_multi_answer

    test_cases = [
        # (输入, 选项数量, 期望结果)
        ("A", 4, [0]),
        ("AB", 4, [0, 1]),
        ("A,B", 4, [0, 1]),
        ("A, B, C", 4, [0, 1, 2]),
        ("", 4, []),
        ("ABC", 4, [0, 1, 2]),
        ("ABCD", 4, [0, 1, 2, 3]),
        ("BCA", 4, [0, 1, 2]),  # 应该排序并去重
        ("AAB", 4, [0, 1]),  # 应该去重
    ]

    issues = []
    for input_str, option_count, expected in test_cases:
        result = _parse_multi_answer(input_str, option_count)
        if result != expected:
            issues.append(f"输入'{input_str}'期望{expected}，实际{result}")

    # 测试单字母解析
    letter_tests = [
        ("A", 0),
        ("B", 1),
        ("a", 0),  # 应该不区分大小写
        ("", None),
        ("1", None),
    ]

    for input_str, expected in letter_tests:
        result = _letter_to_index(input_str)
        if result != expected:
            issues.append(f"字母'{input_str}'期望{expected}，实际{result}")

    if issues:
        print("⚠️ 发现以下问题：")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ 答案解析逻辑正常")

    print()


def test_edge_cases():
    """测试边界情况"""
    print("=== 测试边界情况 ===")

    # 测试空知识库
    print("测试空条目...")
    from src.knowledge_loader import KnowledgeEntry

    empty_entries = [KnowledgeEntry(component="测试", raw_text="", sentences=[])]
    generator = QuestionGenerator(empty_entries, seed=42)

    questions = generator.build_question_bank()
    print(f"✓ 空条目生成了 {len(questions)} 个题目")

    # 测试单个句子的条目
    print("测试单句条目...")
    single_sentence = [
        KnowledgeEntry(
            component="单句测试",
            raw_text="这是一个测试句子。",
            sentences=["这是一个测试句子。"],
        )
    ]
    generator = QuestionGenerator(single_sentence, seed=42)
    questions = generator.build_question_bank()
    print(f"✓ 单句条目生成了 {len(questions)} 个题目")

    print()


if __name__ == "__main__":
    test_knowledge_loading()
    test_question_generation()
    test_multi_choice_logic()
    test_cloze_generation()
    test_answer_parsing()
    test_edge_cases()

    print("=== 测试完成 ===")
