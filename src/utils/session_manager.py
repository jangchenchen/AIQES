"""会话管理工具（包含线程安全和 TTL）"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional


class SessionManager:
    """线程安全的会话管理器，支持 TTL"""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        """
        初始化会话管理器

        Args:
            ttl_seconds: 会话过期时间（秒），默认 1 小时
        """
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._ttl = ttl_seconds
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()

    def start_cleanup_thread(self) -> None:
        """启动后台清理线程"""
        if self._cleanup_thread is not None:
            return

        def cleanup_loop():
            while not self._stop_cleanup.wait(timeout=60):  # 每分钟清理一次
                self.cleanup_expired()

        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        print(f"✅ 会话清理线程已启动（TTL: {self._ttl}秒）")

    def stop_cleanup_thread(self) -> None:
        """停止后台清理线程"""
        if self._cleanup_thread is None:
            return

        self._stop_cleanup.set()
        self._cleanup_thread.join(timeout=2)
        self._cleanup_thread = None

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话数据"""
        with self._lock:
            if session_id not in self._sessions:
                return None

            # 检查是否过期
            if self._is_expired(session_id):
                self._remove_session(session_id)
                return None

            # 更新访问时间
            self._access_times[session_id] = time.time()
            return self._sessions[session_id]

    def set(self, session_id: str, data: Dict[str, Any]) -> None:
        """设置会话数据"""
        with self._lock:
            self._sessions[session_id] = data
            self._access_times[session_id] = time.time()

    def update(self, session_id: str, data: Dict[str, Any]) -> bool:
        """更新会话数据（如果存在且未过期）"""
        with self._lock:
            if session_id not in self._sessions:
                return False

            if self._is_expired(session_id):
                self._remove_session(session_id)
                return False

            self._sessions[session_id].update(data)
            self._access_times[session_id] = time.time()
            return True

    def delete(self, session_id: str) -> bool:
        """删除会话"""
        with self._lock:
            if session_id in self._sessions:
                self._remove_session(session_id)
                return True
            return False

    def exists(self, session_id: str) -> bool:
        """检查会话是否存在且未过期"""
        with self._lock:
            if session_id not in self._sessions:
                return False

            if self._is_expired(session_id):
                self._remove_session(session_id)
                return False

            return True

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话（仅用于序列化）"""
        with self._lock:
            # 清理过期会话
            self.cleanup_expired()
            return self._sessions.copy()

    def load_all(self, sessions: Dict[str, Dict[str, Any]]) -> None:
        """加载所有会话（仅用于反序列化）"""
        with self._lock:
            self._sessions = sessions.copy()
            now = time.time()
            for session_id in self._sessions:
                self._access_times[session_id] = now

    def cleanup_expired(self) -> int:
        """清理过期会话，返回清理数量"""
        with self._lock:
            expired_ids = [
                session_id
                for session_id in self._sessions
                if self._is_expired(session_id)
            ]

            for session_id in expired_ids:
                self._remove_session(session_id)

            if expired_ids:
                print(f"🗑️  清理了 {len(expired_ids)} 个过期会话")

            return len(expired_ids)

    def count(self) -> int:
        """获取当前会话数量"""
        with self._lock:
            return len(self._sessions)

    def _is_expired(self, session_id: str) -> bool:
        """检查会话是否过期"""
        last_access = self._access_times.get(session_id)
        if last_access is None:
            return True

        return (time.time() - last_access) > self._ttl

    def _remove_session(self, session_id: str) -> None:
        """移除会话（内部方法，不加锁）"""
        self._sessions.pop(session_id, None)
        self._access_times.pop(session_id, None)
