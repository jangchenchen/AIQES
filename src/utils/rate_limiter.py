from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict


@dataclass
class RateLimitConfig:
    capacity: int
    window_seconds: float


class RateLimiter:
    """Simple sliding window rate limiter."""

    def __init__(self, config: RateLimitConfig) -> None:
        self.config = config
        self._lock = threading.RLock()
        self._allowance: DefaultDict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.config.window_seconds

        with self._lock:
            timestamps = self._allowance[key]
            # Drop expired timestamps
            idx = 0
            for idx, ts in enumerate(timestamps):
                if ts >= window_start:
                    break
            else:
                idx = len(timestamps)
            if idx:
                del timestamps[:idx]

            if len(timestamps) >= self.config.capacity:
                return False

            timestamps.append(now)
            return True

    def available(self, key: str) -> int:
        now = time.monotonic()
        window_start = now - self.config.window_seconds
        with self._lock:
            timestamps = self._allowance[key]
            remaining = [ts for ts in timestamps if ts >= window_start]
            self._allowance[key] = remaining
            return max(self.config.capacity - len(remaining), 0)

