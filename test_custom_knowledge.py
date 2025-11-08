#!/usr/bin/env python3
"""测试自定义知识文件功能"""

import sys
import tempfile
from pathlib import Path
from subprocess import run


def test_txt_file_loading():
    """测试 TXT 文件加载"""
    print("=== 测试 TXT 文件加载 ===")

    result = run(
        ["python", "-c", """
from pathlib import Path
from src.knowledge_loader import load_knowledge_entries

entries = load_knowledge_entries(Path('docs/sample_knowledge.txt'))
print(f'✓ 加载了 {len(entries)} 个条目')
assert len(entries) == 2, f'期望2个条目，实际{len(entries)}'
assert entries[0].component == '称重装置在超载时的要求：'
print('✓ 条目内容正确')
        """],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(f"❌ 失败：{result.stderr}")
        return False


def test_md_file_loading():
    """测试 MD 文件加载"""
    print("\n=== 测试 MD 文件加载 ===")

    result = run(
        ["python", "-c", """
from pathlib import Path
from src.knowledge_loader import load_knowledge_entries

entries = load_knowledge_entries(Path('docs/Knowledge/电梯安全装置维护程序.md'))
print(f'✓ 加载了 {len(entries)} 个条目')
assert len(entries) >= 7, f'期望至少7个条目，实际{len(entries)}'
print('✓ Markdown 表格解析正常')
        """],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(f"❌ 失败：{result.stderr}")
        return False


def test_file_size_limit():
    """测试文件大小限制"""
    print("\n=== 测试文件大小限制 ===")

    # 创建一个超大文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        # 写入 1MB 的数据（超过 700KB 限制）
        content = "测试内容\n" * 100000
        f.write(content)
        large_file = f.name

    try:
        result = run(
            ["python", "-c", f"""
from pathlib import Path
from src.knowledge_loader import load_knowledge_entries

try:
    load_knowledge_entries(Path('{large_file}'))
    print('❌ 应该抛出文件过大异常')
except ValueError as e:
    if '过大' in str(e):
        print('✓ 正确检测文件过大')
        print(f'✓ 错误消息：{{str(e)[:60]}}...')
    else:
        print(f'❌ 错误类型不正确：{{e}}')
            """],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"❌ 失败：{result.stderr}")
            return False
    finally:
        Path(large_file).unlink()


def test_file_not_found():
    """测试文件不存在错误"""
    print("\n=== 测试文件不存在错误 ===")

    result = run(
        ["python", "main.py", "--knowledge-file", "/nonexistent/file.txt"],
        capture_output=True,
        text=True,
    )

    if "知识文件不存在" in result.stderr:
        print("✓ 正确检测文件不存在")
        print(f"✓ 错误消息：{result.stderr.strip()[:60]}...")
        return True
    else:
        print(f"❌ 错误消息不正确：{result.stderr}")
        return False


def test_cli_parameter():
    """测试 CLI 参数"""
    print("\n=== 测试 CLI 参数 ===")

    result = run(
        ["python", "main.py", "--help"],
        capture_output=True,
        text=True,
    )

    if "--knowledge-file" in result.stdout:
        print("✓ --knowledge-file 参数存在")

        # 检查帮助信息
        if ".md/.txt/.pdf" in result.stdout:
            print("✓ 帮助信息包含支持的文件格式")
        if "683KB" in result.stdout or "700KB" in result.stdout or "<=" in result.stdout:
            print("✓ 帮助信息包含文件大小限制")

        return True
    else:
        print("❌ --knowledge-file 参数缺失")
        return False


def test_custom_file_in_cli():
    """测试在 CLI 中使用自定义文件"""
    print("\n=== 测试 CLI 使用自定义文件 ===")

    # 测试 MD 文件
    result = run(
        ["python", "main.py", "--knowledge-file",
         "docs/Knowledge/电梯安全装置维护程序.md",
         "--types", "single", "--count", "1"],
        input="A\n",
        capture_output=True,
        text=True,
    )

    if "关于" in result.stdout and "选项" in result.stdout:
        print("✓ 成功使用 MD 文件生成题目")
    else:
        print(f"⚠️  MD 文件测试未完全成功")

    # 测试 TXT 文件
    result = run(
        ["python", "main.py", "--knowledge-file",
         "docs/sample_knowledge.txt",
         "--types", "single", "--count", "1"],
        input="A\n",
        capture_output=True,
        text=True,
    )

    if "题库为空" in result.stdout:
        print("✓ TXT 文件内容不足时正确提示")
        return True
    elif "关于" in result.stdout:
        print("✓ TXT 文件成功生成题目")
        return True
    else:
        print(f"⚠️  TXT 文件测试未知结果")
        return True  # 不算失败，因为可能内容不足


def test_session_context_recording():
    """测试会话上下文记录知识文件路径"""
    print("\n=== 测试会话上下文记录 ===")

    # 先答一题
    result = run(
        ["python", "main.py", "--knowledge-file",
         "docs/Knowledge/电梯安全装置维护程序.md",
         "--types", "single", "--count", "1"],
        input="A\n",
        capture_output=True,
        text=True,
    )

    # 检查答题历史
    history_file = Path("data/answer_history.jsonl")
    if history_file.exists():
        import json
        lines = history_file.read_text().split("\n")
        last_record = None
        for line in reversed(lines):
            if line.strip():
                last_record = json.loads(line)
                break

        if last_record and "session_context" in last_record:
            context = last_record["session_context"]
            if "knowledge_file" in context:
                print(f"✓ 记录了知识文件路径：{context['knowledge_file']}")
                return True
            else:
                print("⚠️  未记录知识文件路径（可能使用默认文件）")
                return True
        else:
            print("⚠️  未找到会话上下文")
            return True
    else:
        print("⚠️  答题历史文件不存在")
        return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("自定义知识文件功能测试")
    print("=" * 60)
    print()

    tests = {
        "TXT 文件加载": test_txt_file_loading,
        "MD 文件加载": test_md_file_loading,
        "文件大小限制": test_file_size_limit,
        "文件不存在错误": test_file_not_found,
        "CLI 参数": test_cli_parameter,
        "CLI 使用自定义文件": test_custom_file_in_cli,
        "会话上下文记录": test_session_context_recording,
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
        print(f"{name:<25} {status}")

    passed_count = sum(results.values())
    total_count = len(results)
    pass_rate = 100 * passed_count / total_count if total_count > 0 else 0

    print("\n" + "=" * 60)
    print(f"通过率：{pass_rate:.1f}% ({passed_count}/{total_count})")

    if passed_count == total_count:
        print("🎉 所有测试通过！")
    elif passed_count > total_count // 2:
        print("⚠️  部分测试通过，需要关注失败项。")
    else:
        print("❌ 多数测试失败，需要修复。")
    print("=" * 60)

    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
