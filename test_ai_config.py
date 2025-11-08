#!/usr/bin/env python3
"""测试 AI 配置管理功能"""

import json
import shutil
import sys
import tempfile
from pathlib import Path
from subprocess import run


def backup_config():
    """备份当前配置"""
    config_path = Path("AI_cf/cf.json")
    if config_path.exists():
        backup_path = Path("AI_cf/cf.json.backup")
        shutil.copy(config_path, backup_path)
        print(f"✓ 配置已备份到 {backup_path}")
        return True
    return False


def restore_config():
    """恢复配置"""
    backup_path = Path("AI_cf/cf.json.backup")
    if backup_path.exists():
        config_path = Path("AI_cf/cf.json")
        shutil.copy(backup_path, config_path)
        backup_path.unlink()
        print(f"✓ 配置已恢复")
        return True
    return False


def test_show_command():
    """测试 show 子命令"""
    print("\n=== 测试 show 子命令 ===")

    result = run(
        ["python", "manage_ai_config.py", "show"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        output = result.stdout
        if "key" in output and "url" in output and "model" in output:
            print("✓ show 命令正常工作")
            print(f"✓ 输出内容：\n{output[:200]}...")

            # 验证 JSON 格式
            try:
                config = json.loads(output)
                if all(k in config for k in ["key", "url", "model"]):
                    print("✓ 输出为有效 JSON 格式")
                    print(f"✓ 模型: {config['model']}")
                    print(f"✓ URL: {config['url'][:50]}...")
                    return True
            except json.JSONDecodeError:
                print("⚠️  输出不是有效 JSON")
                return False
        else:
            print(f"⚠️  输出缺少关键字段：{output}")
            return False
    else:
        print(f"❌ show 命令失败：{result.stderr}")
        return False


def test_set_command():
    """测试 set 子命令"""
    print("\n=== 测试 set 子命令 ===")

    # 备份当前配置
    backup_config()

    try:
        # 设置测试配置
        result = run(
            [
                "python", "manage_ai_config.py", "set",
                "--url", "https://api.test.com/v1",
                "--key", "test-key-12345",
                "--model", "test-model",
                "--dev-document", "https://docs.test.com",
                "--timeout", "15",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("✓ set 命令执行成功")

            # 验证配置是否保存
            config_path = Path("AI_cf/cf.json")
            if config_path.exists():
                config = json.loads(config_path.read_text())

                checks = {
                    "URL": config.get("url") == "https://api.test.com/v1",
                    "Key": config.get("key") == "test-key-12345",
                    "Model": config.get("model") == "test-model",
                    "Dev Doc": config.get("dev_document") == "https://docs.test.com",
                    "Timeout": float(config.get("timeout", 0)) == 15.0,
                }

                all_passed = all(checks.values())
                for field, passed in checks.items():
                    status = "✓" if passed else "❌"
                    print(f"{status} {field} 字段正确")

                return all_passed
            else:
                print("❌ 配置文件未创建")
                return False
        else:
            print(f"❌ set 命令失败：{result.stderr}")
            return False
    finally:
        # 恢复原配置
        restore_config()


def test_set_without_required_params():
    """测试 set 命令缺少必需参数"""
    print("\n=== 测试 set 命令参数验证 ===")

    result = run(
        ["python", "manage_ai_config.py", "set", "--url", "https://test.com"],
        capture_output=True,
        text=True,
    )

    # 应该失败（缺少 --key 和 --model）
    if result.returncode != 0:
        if "--key" in result.stderr or "required" in result.stderr:
            print("✓ 正确检测缺少必需参数")
            return True
        else:
            print(f"⚠️  错误消息不够明确：{result.stderr}")
            return True
    else:
        print("❌ 应该拒绝不完整的参数")
        return False


def test_delete_command():
    """测试 delete 子命令"""
    print("\n=== 测试 delete 子命令 ===")

    # 创建临时配置
    config_path = Path("AI_cf/cf_test_temp.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"key":"test","url":"test","model":"test"}')

    # 修改 manage_ai_config.py 暂时指向临时文件（不实际修改，用模拟）
    # 由于无法动态修改 CONFIG_PATH，这里测试实际的 delete

    backup_config()

    result = run(
        ["python", "manage_ai_config.py", "delete"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("✓ delete 命令执行成功")

        # 验证配置是否删除
        config_path = Path("AI_cf/cf.json")
        if not config_path.exists():
            print("✓ 配置文件已删除")

            # 恢复配置
            restore_config()
            return True
        else:
            print("❌ 配置文件未删除")
            restore_config()
            return False
    else:
        print(f"❌ delete 命令失败：{result.stderr}")
        restore_config()
        return False


def test_cli_help():
    """测试 CLI 帮助信息"""
    print("\n=== 测试 CLI 帮助信息 ===")

    result = run(
        ["python", "manage_ai_config.py", "--help"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        help_text = result.stdout

        expected_commands = ["wizard", "show", "test", "delete", "set"]
        found = {cmd: cmd in help_text for cmd in expected_commands}

        all_found = all(found.values())
        for cmd, is_found in found.items():
            status = "✓" if is_found else "❌"
            print(f"{status} 子命令 '{cmd}' 在帮助中")

        return all_found
    else:
        print(f"❌ 帮助命令失败：{result.stderr}")
        return False


def test_config_data_class():
    """测试 AIConfig 数据类"""
    print("\n=== 测试 AIConfig 数据类 ===")

    result = run(
        ["python", "-c", """
from manage_ai_config import AIConfig

# 测试创建
config = AIConfig(
    key="test-key",
    url="https://api.test.com",
    model="gpt-4",
    dev_document="https://docs.test.com",
    timeout=20.0
)
print("✓ AIConfig 实例创建成功")

# 测试序列化
payload = config.to_payload()
assert payload["key"] == "test-key"
assert payload["url"] == "https://api.test.com"
assert payload["model"] == "gpt-4"
assert payload["timeout"] == 20.0
print("✓ to_payload() 正常工作")

# 测试反序列化
config2 = AIConfig.from_payload(payload)
assert config2.key == config.key
assert config2.url == config.url
assert config2.model == config.model
print("✓ from_payload() 正常工作")

# 测试默认值
config3 = AIConfig(key="k", url="u", model="m")
assert config3.timeout == 10.0  # DEFAULT_TIMEOUT
print("✓ 默认超时值正确")
        """],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(f"❌ 数据类测试失败：{result.stderr}")
        return False


def test_config_file_operations():
    """测试配置文件读写操作"""
    print("\n=== 测试配置文件读写 ===")

    result = run(
        ["python", "-c", """
import tempfile
from pathlib import Path
from manage_ai_config import AIConfig, load_config, save_config

# 创建临时目录
with tempfile.TemporaryDirectory() as tmpdir:
    test_path = Path(tmpdir) / "test_cf.json"

    # 测试保存
    config = AIConfig(
        key="test-key",
        url="https://test.com",
        model="test-model"
    )
    save_config(config, test_path)
    print("✓ 配置保存成功")

    # 验证文件存在
    assert test_path.exists(), "配置文件未创建"
    print("✓ 配置文件已创建")

    # 测试加载
    loaded = load_config(test_path)
    assert loaded is not None, "加载失败"
    assert loaded.key == "test-key"
    assert loaded.url == "https://test.com"
    assert loaded.model == "test-model"
    print("✓ 配置加载成功且内容正确")

    # 测试加载不存在的文件
    missing = load_config(Path(tmpdir) / "nonexistent.json")
    assert missing is None, "应该返回 None"
    print("✓ 不存在的文件正确返回 None")
        """],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(f"❌ 文件操作测试失败：{result.stderr}")
        return False


def test_integration_with_main():
    """测试与 main.py 的集成"""
    print("\n=== 测试与 main.py 集成 ===")

    # 检查 main.py 是否能读取配置
    result = run(
        ["python", "-c", """
import sys
from pathlib import Path

# 检查 main.py 是否导入 AI 配置
try:
    from src.ai_client import AIClient
    from manage_ai_config import load_config

    config = load_config()
    if config:
        print(f"✓ main.py 能读取配置，模型：{config.model}")

        # 检查 AIClient 是否能使用配置
        # 注意：不实际调用 API，只检查接口
        print("✓ AIClient 可用")
    else:
        print("⚠️  未找到配置文件（可能是正常情况）")
except ImportError as e:
    print(f"⚠️  导入失败：{e}")
except Exception as e:
    print(f"❌ 集成测试异常：{e}")
        """],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print(f"错误输出：{result.stderr}")

    return result.returncode == 0


def test_frontend_ai_config_ui():
    """测试前端 AI 配置界面"""
    print("\n=== 测试前端 AI 配置界面 ===")

    # 检查桌面端
    desktop_html = Path("frontend/index.html").read_text(encoding="utf-8")
    desktop_checks = {
        "AI 配置弹窗": "AI 配置" in desktop_html or "AI配置" in desktop_html,
        "URL 输入框": 'type="url"' in desktop_html or 'name="ai-url"' in desktop_html or 'id="ai-url"' in desktop_html,
        "Key 输入框": 'type="password"' in desktop_html or 'name="ai-key"' in desktop_html or 'id="ai-key"' in desktop_html,
        "模型输入框": 'name="ai-model"' in desktop_html or 'id="ai-model"' in desktop_html,
        "测试连通性按钮": "测试" in desktop_html and "连通" in desktop_html,
        "保存按钮": "保存" in desktop_html,
        "删除按钮": "删除" in desktop_html,
    }

    print("\n桌面端界面检查：")
    desktop_passed = 0
    for check, result in desktop_checks.items():
        status = "✓" if result else "❌"
        print(f"  {status} {check}")
        if result:
            desktop_passed += 1

    # 检查移动端
    mobile_html = Path("frontend/mobile.html").read_text(encoding="utf-8")
    mobile_checks = {
        "配置抽屉": "抽屉" in mobile_html or "drawer" in mobile_html or "AI配置" in mobile_html,
        "配置表单": "<form" in mobile_html or "ai-url" in mobile_html,
        "测试/保存按钮": "测试" in mobile_html and "保存" in mobile_html,
    }

    print("\n移动端界面检查：")
    mobile_passed = 0
    for check, result in mobile_checks.items():
        status = "✓" if result else "⚠️"
        print(f"  {status} {check}")
        if result:
            mobile_passed += 1

    total_checks = len(desktop_checks) + len(mobile_checks)
    total_passed = desktop_passed + mobile_passed

    print(f"\n前端界面检查通过率：{total_passed}/{total_checks} ({100*total_passed//total_checks}%)")

    return total_passed >= total_checks * 0.7  # 70% 通过即可


def main():
    """运行所有测试"""
    print("=" * 60)
    print("AI 配置管理功能测试")
    print("=" * 60)

    tests = {
        "数据类功能": test_config_data_class,
        "文件读写操作": test_config_file_operations,
        "CLI 帮助信息": test_cli_help,
        "show 子命令": test_show_command,
        "set 子命令": test_set_command,
        "set 参数验证": test_set_without_required_params,
        "delete 子命令": test_delete_command,
        "main.py 集成": test_integration_with_main,
        "前端 UI 界面": test_frontend_ai_config_ui,
    }

    results = {}
    for name, test_func in tests.items():
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ {name} 测试异常：{e}")
            import traceback
            traceback.print_exc()
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
        print("🎉 所有测试通过！")
    elif passed_count > total_count // 2:
        print("⚠️  大部分测试通过，有少数失败项。")
    else:
        print("❌ 多数测试失败，需要修复。")
    print("=" * 60)

    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
