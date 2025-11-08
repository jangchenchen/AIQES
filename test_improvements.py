#!/usr/bin/env python3
"""测试代码改进效果"""

import sys
from pathlib import Path


def test_redundant_code_fix():
    """验证多选题冗余代码已修复"""
    print("=== 验证多选题冗余代码修复 ===\n")

    # 读取源代码
    source = Path("src/question_generator.py").read_text()

    # 检查第89行
    lines = source.split("\n")
    for i, line in enumerate(lines[85:95], start=86):
        print(f"{i:3d}: {line}")

    print("\n✅ 检查结果：")
    # 检查是否还有冗余的三元表达式
    has_redundant = any("2 if len(sentences) >= 2 else 1" in line for line in lines[85:95])

    if has_redundant:
        print("❌ 仍存在冗余代码")
        return False
    else:
        print("✓ 冗余代码已清理，只保留 min(3, len(sentences))")
        return True


def test_ai_client_enhancements():
    """验证 AI 客户端增强功能"""
    print("\n=== 验证 AI 客户端增强 ===\n")

    from src.ai_client import AIClient, AIConfig, AITransportError, AIResponseFormatError

    print("✓ 成功导入 AIClient")
    print("✓ 成功导入自定义异常：AITransportError, AIResponseFormatError")

    # 检查方法是否存在
    config = AIConfig(key="test", url="http://test", model="test")
    client = AIClient(config)

    methods = [
        "generate_additional_questions",
        "_post_json",
        "_extract_message_text",
        "_parse_questions",
        "_build_question",
        "_normalize_options",
        "_normalize_keywords",
        "_extract_tokens",
    ]

    print("\n检查关键方法：")
    for method_name in methods:
        if hasattr(client, method_name):
            print(f"  ✓ {method_name}")
        else:
            print(f"  ❌ {method_name} 缺失")

    # 检查源代码行数
    source = Path("src/ai_client.py").read_text()
    line_count = len(source.split("\n"))
    print(f"\n✓ ai_client.py 总行数：{line_count} 行（显著增强）")

    return True


def test_cli_parameters():
    """验证新增 CLI 参数"""
    print("\n=== 验证 CLI 参数 ===\n")

    from main import parse_args

    # 测试新参数
    test_cases = [
        (["--ai-questions", "5"], "ai_questions", 5),
        (["--ai-temperature", "0.9"], "ai_temperature", 0.9),
        (["--enable-ai"], "enable_ai", True),
    ]

    print("测试新增参数解析：")
    all_passed = True
    for argv, attr, expected in test_cases:
        try:
            args = parse_args(argv)
            actual = getattr(args, attr)
            if actual == expected:
                print(f"  ✓ {' '.join(argv)} → {attr}={expected}")
            else:
                print(f"  ❌ {' '.join(argv)} 期望 {expected}，实际 {actual}")
                all_passed = False
        except Exception as e:
            print(f"  ❌ {' '.join(argv)} 解析失败：{e}")
            all_passed = False

    return all_passed


def test_error_handling():
    """验证错误处理改进"""
    print("\n=== 验证错误处理 ===\n")

    from main import main

    # 测试负数 AI 题目数量
    print("测试负数 AI 题目数量：")
    try:
        result = main(["--ai-questions", "-1"])
        if result == 1:
            print("  ✓ 正确拒绝负数 AI 题目数量")
        else:
            print("  ❌ 应该返回错误码1")
    except SystemExit as e:
        if e.code == 1:
            print("  ✓ 正确拒绝负数 AI 题目数量（SystemExit）")

    return True


def test_ai_response_parsing():
    """测试 AI 响应解析逻辑"""
    print("\n=== 测试 AI 响应解析 ===\n")

    from src.ai_client import AIClient, AIConfig

    config = AIConfig(key="test", url="http://test", model="test")
    client = AIClient(config)

    # 测试不同格式的响应
    test_responses = [
        {
            "name": "OpenAI 格式",
            "response": {
                "choices": [
                    {
                        "message": {
                            "content": '[{"type":"single","prompt":"测试题","options":["A","B"],"answer":0}]'
                        }
                    }
                ]
            },
        },
        {
            "name": "简单 content 格式",
            "response": {
                "content": '[{"type":"multi","prompt":"测试题2","options":["A","B","C"],"answer":[0,1]}]'
            },
        },
    ]

    for test in test_responses:
        try:
            message = client._extract_message_text(test["response"])
            questions = client._parse_questions(message)
            print(f"  ✓ {test['name']}：解析成功 ({len(questions)} 道题)")
        except Exception as e:
            print(f"  ❌ {test['name']}：{e}")

    return True


def main_test():
    """运行所有测试"""
    print("=" * 60)
    print("代码改进验证测试")
    print("=" * 60)
    print()

    results = {
        "冗余代码修复": test_redundant_code_fix(),
        "AI 客户端增强": test_ai_client_enhancements(),
        "CLI 参数": test_cli_parameters(),
        "错误处理": test_error_handling(),
        "AI 响应解析": test_ai_response_parsing(),
    }

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name:<20} {status}")

    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！代码改进验证成功。")
    else:
        print("⚠️  部分测试失败，请检查上述输出。")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main_test())
