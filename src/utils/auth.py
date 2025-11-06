"""API 鉴权工具"""
from __future__ import annotations

import os
import secrets
from functools import wraps
from pathlib import Path
from typing import Callable, Optional

from flask import request


API_KEY_FILE = Path("data/api_key.txt")
API_KEY_ENV = "API_KEY"


def get_api_key() -> Optional[str]:
    """获取 API 密钥（优先从环境变量）"""
    # 优先从环境变量读取
    key = os.environ.get(API_KEY_ENV)
    if key:
        return key.strip()

    # 从文件读取
    if API_KEY_FILE.exists():
        return API_KEY_FILE.read_text(encoding="utf-8").strip()

    return None


def generate_api_key() -> str:
    """生成随机 API 密钥"""
    return secrets.token_urlsafe(32)


def save_api_key(key: str) -> None:
    """保存 API 密钥到文件"""
    API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    API_KEY_FILE.write_text(key, encoding="utf-8")
    print(f"✅ API 密钥已保存到 {API_KEY_FILE}")


def verify_api_key(provided_key: Optional[str]) -> bool:
    """验证提供的 API 密钥"""
    if not provided_key:
        return False

    expected_key = get_api_key()
    if not expected_key:
        # 如果未设置 API 密钥，则不进行验证（开发模式）
        return True

    return secrets.compare_digest(provided_key.strip(), expected_key)


def require_api_key(func: Callable) -> Callable:
    """装饰器：要求提供有效的 API 密钥"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 从 Header 或 Query 参数获取 API 密钥
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key")

        if not verify_api_key(api_key):
            from flask import jsonify
            return jsonify({"error": "无效的 API 密钥"}), 401

        return func(*args, **kwargs)

    return wrapper


def init_api_key_if_needed() -> None:
    """如果未设置 API 密钥，则生成并保存"""
    if not get_api_key():
        key = generate_api_key()
        save_api_key(key)
        print("=" * 60)
        print("🔑 首次启动已生成 API 密钥:")
        print(f"   {key}")
        print()
        print("请将此密钥保存在安全的地方，用于 API 鉴权。")
        print(f"也可以设置环境变量: export {API_KEY_ENV}=your-key")
        print("=" * 60)
