from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path("AI_cf/cf.json")
DEFAULT_TIMEOUT = 10


@dataclass
class AIConfig:
    key: str
    url: str
    model: str
    dev_document: Optional[str] = None
    timeout: float = DEFAULT_TIMEOUT

    def to_payload(self) -> dict:
        payload = {
            "key": self.key,
            "url": self.url,
            "model": self.model,
        }
        if self.dev_document:
            payload["dev_document"] = self.dev_document
        payload["timeout"] = self.timeout
        return payload

    @classmethod
    def from_payload(cls, payload: dict) -> "AIConfig":
        return cls(
            key=payload["key"],
            url=payload["url"],
            model=payload["model"],
            dev_document=payload.get("dev_document"),
            timeout=float(payload.get("timeout", DEFAULT_TIMEOUT)),
        )


def load_config(path: Path = CONFIG_PATH) -> Optional[AIConfig]:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AIConfig.from_payload(payload)


def save_config(config: AIConfig, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_payload(), ensure_ascii=False, indent=2), encoding="utf-8")


def delete_config(path: Path = CONFIG_PATH) -> bool:
    if path.exists():
        path.unlink()
        return True
    return False


def test_connectivity(config: AIConfig, endpoint: Optional[str] = None) -> tuple[bool, str]:
    target = endpoint or config.url
    request = urllib.request.Request(target, method="GET")
    request.add_header("Authorization", f"Bearer {config.key}")
    try:
        with urllib.request.urlopen(request, timeout=config.timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
            return True, f"连通性测试成功，HTTP 状态 {status}。"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        return False, f"HTTP {exc.code}: {detail or exc.reason}"
    except urllib.error.URLError as exc:
        return False, f"无法连接：{exc.reason}"
    except Exception as exc:  # pragma: no cover - 防御
        return False, f"测试失败：{exc}"


def prompt_input(prompt: str, default: Optional[str] = None, secret: bool = False) -> str:
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    try:
        if secret:
            import getpass

            value = getpass.getpass(prompt)
        else:
            value = input(prompt)
    except EOFError:
        value = ""
    if not value and default is not None:
        return default
    return value.strip()


def run_wizard(args: argparse.Namespace) -> int:
    existing = load_config()
    print("当前配置：")
    if existing:
        print(json.dumps(existing.to_payload(), ensure_ascii=False, indent=2))
    else:
        print("  （未设置）")
    print()

    url = prompt_input("请输入 API URL", existing.url if existing else None) or ""
    key = prompt_input("请输入 API Key", existing.key if existing else None, secret=True) or ""
    model = prompt_input("请输入模型名称", existing.model if existing else None) or ""
    dev_doc = prompt_input("开发者文档链接（可选）", existing.dev_document if existing else None)
    timeout_raw = prompt_input("请求超时（秒，默认10）", str(existing.timeout if existing else DEFAULT_TIMEOUT))
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = DEFAULT_TIMEOUT

    config = AIConfig(key=key, url=url, model=model, dev_document=dev_doc or None, timeout=timeout)

    print("\n配置预览：")
    print(json.dumps(config.to_payload(), ensure_ascii=False, indent=2))
    confirm = prompt_input("是否立即测试连通性？(y/N)").lower()
    if confirm == "y":
        ok, message = test_connectivity(config)
        print(message)
    save_confirm = prompt_input("是否保存上述配置？(Y/n)").lower()
    if save_confirm in {"", "y", "yes"}:
        save_config(config)
        print(f"配置已保存至 {CONFIG_PATH}")
    else:
        print("已取消保存。")
    return 0


def run_show(_: argparse.Namespace) -> int:
    config = load_config()
    if not config:
        print("当前未配置 AI。")
        return 0
    print(json.dumps(config.to_payload(), ensure_ascii=False, indent=2))
    return 0


def run_test(args: argparse.Namespace) -> int:
    config = load_config()
    if not config:
        print("当前未配置 AI，请先运行 wizard 或 set。")
        return 1
    endpoint = args.endpoint
    ok, message = test_connectivity(config, endpoint=endpoint)
    print(message)
    return 0 if ok else 2


def run_delete(_: argparse.Namespace) -> int:
    if delete_config():
        print("已删除 AI 配置。")
    else:
        print("未找到配置文件，无需删除。")
    return 0


def run_set(args: argparse.Namespace) -> int:
    key = args.key
    url = args.url
    model = args.model
    if not all([key, url, model]):
        print("--url、--key、--model 必须全部提供。")
        return 1
    config = AIConfig(key=key, url=url, model=model, dev_document=args.dev_document, timeout=args.timeout)
    save_config(config)
    print(f"配置已保存至 {CONFIG_PATH}")
    if args.test:
        ok, message = test_connectivity(config)
        print(message)
        return 0 if ok else 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI 配置工具")
    subparsers = parser.add_subparsers(dest="command")

    wizard = subparsers.add_parser("wizard", help="交互式配置引导")
    wizard.set_defaults(func=run_wizard)

    show = subparsers.add_parser("show", help="查看当前配置")
    show.set_defaults(func=run_show)

    test = subparsers.add_parser("test", help="测试与当前配置的连通性")
    test.add_argument("--endpoint", help="自定义测试地址，默认为配置中的 URL")
    test.set_defaults(func=run_test)

    delete = subparsers.add_parser("delete", help="删除配置文件")
    delete.set_defaults(func=run_delete)

    set_cmd = subparsers.add_parser("set", help="通过命令行参数直接写入配置")
    set_cmd.add_argument("--url", required=True)
    set_cmd.add_argument("--key", required=True)
    set_cmd.add_argument("--model", required=True)
    set_cmd.add_argument("--dev-document")
    set_cmd.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    set_cmd.add_argument("--test", action="store_true", help="保存后立即测试连通性")
    set_cmd.set_defaults(func=run_set)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
