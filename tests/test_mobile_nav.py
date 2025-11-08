#!/usr/bin/env python3
"""
移动端导航测试脚本
测试移动端 Tab 导航、粘贴入口等功能
"""

import requests
import re


BASE_URL = "http://localhost:5001"


def test_mobile_page_loads():
    """测试移动端页面是否正常加载"""
    response = requests.get(f"{BASE_URL}/mobile.html")
    assert response.status_code == 200, f"移动端页面加载失败: {response.status_code}"
    print("✓ 移动端页面加载成功")


def test_mobile_nav_structure():
    """测试移动端导航结构"""
    response = requests.get(f"{BASE_URL}/mobile.html")
    html = response.text

    # 检查底部导航按钮
    nav_buttons = re.findall(r'class="mobile-nav__item"', html)
    assert len(nav_buttons) >= 3, f"导航按钮不足: {len(nav_buttons)}"
    print(f"✓ 找到 {len(nav_buttons)} 个导航按钮")

    # 检查 Tab 区域
    tab_sections = re.findall(r'class="mobile-tabs', html)
    assert len(tab_sections) >= 3, f"Tab 区域不足: {len(tab_sections)}"
    print(f"✓ 找到 {len(tab_sections)} 个 Tab 区域")


def test_paste_helper_exists():
    """测试粘贴入口帮助文本是否存在"""
    response = requests.get(f"{BASE_URL}/mobile.html")
    html = response.text

    # 检查粘贴帮助链接
    assert 'form-helper__link' in html, "粘贴帮助链接不存在"
    assert '查看示例' in html, "查看示例文本不存在"
    print("✓ 粘贴帮助链接存在")

    # 检查示例模板
    assert 'knowledge-example-template' in html, "示例模板不存在"
    print("✓ 知识示例模板存在")


def test_ai_config_container():
    """测试 AI 配置容器是否存在"""
    response = requests.get(f"{BASE_URL}/mobile.html")
    html = response.text

    assert 'mobile-ai-config-container' in html, "移动端 AI 配置容器不存在"
    print("✓ 移动端 AI 配置容器存在")


def test_knowledge_manager_module():
    """测试知识管理模块是否可访问"""
    response = requests.head(f"{BASE_URL}/assets/modules/knowledgeManager.js")
    assert response.status_code == 200, f"知识管理模块无法访问: {response.status_code}"
    print("✓ 知识管理模块可访问")


def test_history_store_module():
    """测试历史存储模块是否可访问"""
    response = requests.head(f"{BASE_URL}/assets/modules/historyStore.js")
    assert response.status_code == 200, f"历史存储模块无法访问: {response.status_code}"
    print("✓ 历史存储模块可访问")


def test_wrong_book_module():
    """测试错题本模块是否可访问"""
    response = requests.head(f"{BASE_URL}/assets/modules/wrongBook.js")
    assert response.status_code == 200, f"错题本模块无法访问: {response.status_code}"
    print("✓ 错题本模块可访问")


def run_all_tests():
    """运行所有测试"""
    tests = [
        test_mobile_page_loads,
        test_mobile_nav_structure,
        test_paste_helper_exists,
        test_ai_config_container,
        test_knowledge_manager_module,
        test_history_store_module,
        test_wrong_book_module,
    ]

    print("\n=== 移动端导航测试 ===\n")

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
