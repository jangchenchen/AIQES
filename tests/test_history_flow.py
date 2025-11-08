#!/usr/bin/env python3
"""
历史记录流程测试脚本
测试答题历史的记录、查询、展示等功能
"""

import json
import uuid
from pathlib import Path

import requests

BASE_URL = "http://localhost:5001"
DATA_DIR = Path(__file__).parent.parent / "data"


def test_history_file_exists():
    """测试历史记录文件是否存在"""
    history_file = DATA_DIR / "answer_history.jsonl"
    if not history_file.exists():
        print("⚠️  历史记录文件不存在（首次运行正常）")
    else:
        print(f"✓ 历史记录文件存在: {history_file}")


def test_desktop_history_view_loads():
    """测试桌面端历史视图是否正常加载"""
    response = requests.get(f"{BASE_URL}/app.html")
    assert response.status_code == 200, f"桌面端页面加载失败: {response.status_code}"

    html = response.text
    # 检查历史相关元素（桌面版无 drawer，为 modal）
    assert "history-view" in html, "缺少 history-view 元素"
    assert "history-list" in html, "缺少 history-list 元素"

    print("✓ 桌面端历史视图加载成功")


def test_mobile_history_view_loads():
    """测试移动端历史视图是否正常加载"""
    response = requests.get(f"{BASE_URL}/mobile.html")
    assert response.status_code == 200, f"移动端页面加载失败: {response.status_code}"

    html = response.text
    # 检查历史相关元素
    assert "history-view" in html, "缺少 history-view 元素"
    assert "history-list" in html, "缺少 history-list 元素"
    assert "history-drawer" in html, "缺少 history-drawer 元素"

    print("✓ 移动端历史视图加载成功")


def test_history_drawer_structure():
    """测试历史抽屉结构是否完整"""
    response = requests.get(f"{BASE_URL}/mobile.html")
    html = response.text

    # 检查抽屉关键元素
    required_elements = [
        "history-drawer-overlay",
        "history-drawer-close",
        "history-drawer-title",
        "history-drawer-prompt",
        "history-drawer-result",
        "history-drawer-user-answer",
        "history-drawer-correct-answer",
        "history-drawer-explanation",
        "history-drawer-prev",
        "history-drawer-next",
        "history-drawer-reuse",
    ]

    for element_id in required_elements:
        assert element_id in html, f"缺少抽屉元素: {element_id}"

    print(f"✓ 历史抽屉结构完整（{len(required_elements)} 个元素）")


def test_history_templates_exist():
    """测试历史记录模板是否存在"""
    response = requests.get(f"{BASE_URL}/mobile.html")
    html = response.text

    # 检查模板
    assert "history-entry-template" in html, "缺少 history-entry-template 模板"
    assert "history-card-template" in html, "缺少 history-card-template 模板"

    print("✓ 历史记录模板存在")


def test_history_data_structure():
    """测试历史记录数据结构"""
    history_file = DATA_DIR / "answer_history.jsonl"

    if not history_file.exists():
        print("⚠️  无历史记录文件，跳过数据结构测试")
        return

    # 读取最后一条记录
    lines = history_file.read_text(encoding="utf-8").strip().split("\n")
    if not lines or not lines[-1]:
        print("⚠️  历史记录文件为空，跳过数据结构测试")
        return

    try:
        last_entry = json.loads(lines[-1])

        # 验证必需字段
        required_fields = ["timestamp", "question", "user_answer", "is_correct"]
        for field in required_fields:
            assert field in last_entry, f"缺少字段: {field}"

        # 验证 question 结构
        question = last_entry["question"]
        assert "prompt" in question, "question 中缺少 prompt 字段"
        assert "question_type" in question, "question 中缺少 question_type 字段"

        print("✓ 历史记录数据结构正确")
        print(f"  最近一条: {question['prompt'][:50]}...")

    except json.JSONDecodeError as e:
        print(f"✗ 历史记录 JSON 解析失败: {e}")
        raise


def test_session_status_api():
    """测试会话状态 API"""
    # 使用不存在的 session_id 测试
    fake_session_id = str(uuid.uuid4())

    response = requests.post(
        f"{BASE_URL}/api/session-status",
        json={"session_id": fake_session_id},
        headers={"Content-Type": "application/json"},
    )

    # 不存在的会话应返回 404
    assert response.status_code == 404, f"期望 404，实际: {response.status_code}"

    data = response.json()
    assert "error" in data, "错误响应应包含 error 字段"

    print("✓ 会话状态 API 正常工作")


def test_history_pagination_buttons():
    """测试历史分页按钮是否存在"""
    response = requests.get(f"{BASE_URL}/mobile.html")
    html = response.text

    # 检查分页相关元素
    assert "btn-history-prev" in html, "缺少上一页按钮"
    assert "btn-history-next" in html, "缺少下一页按钮"
    assert "history-page-info" in html, "缺少页码信息"
    assert "btn-history-refresh" in html, "缺少刷新按钮"

    print("✓ 历史分页按钮存在")


def test_history_status_bar():
    """测试历史状态栏是否存在"""
    response = requests.get(f"{BASE_URL}/mobile.html")
    html = response.text

    assert "history-status-bar" in html, "缺少历史状态栏"
    assert "history-status" in html, "缺少状态显示元素"
    assert "history-loading" in html, "缺少加载状态"
    assert "history-empty" in html, "缺少空状态提示"

    print("✓ 历史状态栏完整")


def test_wrong_questions_file():
    """测试错题记录文件"""
    wrong_file = DATA_DIR / "wrong_questions.json"

    if not wrong_file.exists():
        print("⚠️  错题文件不存在（首次运行正常）")
        return

    try:
        data = json.loads(wrong_file.read_text(encoding="utf-8"))
        assert isinstance(data, list), "错题数据应为数组"

        print(f"✓ 错题文件格式正确（{len(data)} 条错题）")

        if data:
            # 验证第一条错题结构
            first = data[0]
            assert "question" in first, "错题记录缺少 question 字段"
            assert "last_wrong_at" in first, "错题记录缺少 last_wrong_at 字段"

    except json.JSONDecodeError as e:
        print(f"✗ 错题文件 JSON 解析失败: {e}")
        raise


def run_all_tests():
    """运行所有测试"""
    tests = [
        test_history_file_exists,
        test_desktop_history_view_loads,
        test_mobile_history_view_loads,
        test_history_drawer_structure,
        test_history_templates_exist,
        test_history_data_structure,
        test_session_status_api,
        test_history_pagination_buttons,
        test_history_status_bar,
        test_wrong_questions_file,
    ]

    print("\n=== 历史记录流程测试 ===\n")

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1

    print(f"\n=== 测试完成 ===")
    print(f"通过: {passed}/{len(tests)}")
    print(f"失败: {failed}/{len(tests)}")

    return failed == 0


if __name__ == "__main__":
    import sys

    success = run_all_tests()
    sys.exit(0 if success else 1)
