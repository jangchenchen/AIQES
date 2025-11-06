"""应用监控指标收集"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional


@dataclass
class MetricPoint:
    """单个指标点"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Counter:
    """计数器"""
    name: str
    help: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)

    def inc(self, amount: float = 1.0) -> None:
        """增加计数"""
        self.value += amount


@dataclass
class Gauge:
    """仪表盘（当前值）"""
    name: str
    help: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)

    def set(self, value: float) -> None:
        """设置值"""
        self.value = value

    def inc(self, amount: float = 1.0) -> None:
        """增加"""
        self.value += amount

    def dec(self, amount: float = 1.0) -> None:
        """减少"""
        self.value -= amount


@dataclass
class Histogram:
    """直方图（延迟分布）"""
    name: str
    help: str
    buckets: List[float]
    counts: List[int] = field(default_factory=list)
    sum: float = 0.0
    count: int = 0
    labels: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.counts:
            self.counts = [0] * len(self.buckets)

    def observe(self, value: float) -> None:
        """记录观察值"""
        self.sum += value
        self.count += 1

        for i, bucket in enumerate(self.buckets):
            if value <= bucket:
                self.counts[i] += 1


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self._lock = Lock()
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._timeseries: Dict[str, List[MetricPoint]] = defaultdict(list)

    def counter(
        self,
        name: str,
        help: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Counter:
        """获取或创建计数器"""
        key = f"{name}:{labels}" if labels else name

        with self._lock:
            if key not in self._counters:
                self._counters[key] = Counter(name, help, labels=labels or {})
            return self._counters[key]

    def gauge(
        self,
        name: str,
        help: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Gauge:
        """获取或创建仪表盘"""
        key = f"{name}:{labels}" if labels else name

        with self._lock:
            if key not in self._gauges:
                self._gauges[key] = Gauge(name, help, labels=labels or {})
            return self._gauges[key]

    def histogram(
        self,
        name: str,
        help: str,
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Histogram:
        """获取或创建直方图"""
        if buckets is None:
            # 默认延迟桶：10ms, 50ms, 100ms, 500ms, 1s, 5s, 10s
            buckets = [0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]

        key = f"{name}:{labels}" if labels else name

        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = Histogram(
                    name, help, buckets=buckets, labels=labels or {}
                )
            return self._histograms[key]

    def record_timeseries(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        max_points: int = 1000
    ) -> None:
        """记录时间序列数据"""
        point = MetricPoint(
            timestamp=datetime.utcnow(),
            value=value,
            labels=labels or {}
        )

        with self._lock:
            series = self._timeseries[name]
            series.append(point)

            # 保持最新的 N 个点
            if len(series) > max_points:
                series.pop(0)

    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        with self._lock:
            return {
                "counters": {k: {"value": c.value, "labels": c.labels} for k, c in self._counters.items()},
                "gauges": {k: {"value": g.value, "labels": g.labels} for k, g in self._gauges.items()},
                "histograms": {
                    k: {
                        "sum": h.sum,
                        "count": h.count,
                        "buckets": dict(zip(h.buckets, h.counts)),
                        "labels": h.labels,
                    }
                    for k, h in self._histograms.items()
                },
                "timeseries": {
                    name: [
                        {"timestamp": p.timestamp.isoformat(), "value": p.value, "labels": p.labels}
                        for p in points
                    ]
                    for name, points in self._timeseries.items()
                },
            }

    def get_prometheus_metrics(self) -> str:
        """导出 Prometheus 格式的指标"""
        lines = []

        with self._lock:
            # Counters
            for counter in self._counters.values():
                lines.append(f"# HELP {counter.name} {counter.help}")
                lines.append(f"# TYPE {counter.name} counter")
                labels_str = self._format_labels(counter.labels)
                lines.append(f"{counter.name}{labels_str} {counter.value}")

            # Gauges
            for gauge in self._gauges.values():
                lines.append(f"# HELP {gauge.name} {gauge.help}")
                lines.append(f"# TYPE {gauge.name} gauge")
                labels_str = self._format_labels(gauge.labels)
                lines.append(f"{gauge.name}{labels_str} {gauge.value}")

            # Histograms
            for histogram in self._histograms.values():
                lines.append(f"# HELP {histogram.name} {histogram.help}")
                lines.append(f"# TYPE {histogram.name} histogram")
                labels_str = self._format_labels(histogram.labels)

                for i, bucket in enumerate(histogram.buckets):
                    bucket_labels = {**histogram.labels, "le": str(bucket)}
                    bucket_str = self._format_labels(bucket_labels)
                    lines.append(f"{histogram.name}_bucket{bucket_str} {histogram.counts[i]}")

                lines.append(f"{histogram.name}_sum{labels_str} {histogram.sum}")
                lines.append(f"{histogram.name}_count{labels_str} {histogram.count}")

        return "\n".join(lines) + "\n"

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """格式化 Prometheus 标签"""
        if not labels:
            return ""

        label_pairs = [f'{k}="{v}"' for k, v in labels.items()]
        return "{" + ",".join(label_pairs) + "}"


# 全局指标收集器
metrics = MetricsCollector()


# 应用指标定义
class AppMetrics:
    """应用指标"""

    # HTTP 请求
    http_requests_total = metrics.counter(
        "http_requests_total",
        "Total HTTP requests",
    )

    http_request_duration = metrics.histogram(
        "http_request_duration_seconds",
        "HTTP request latency",
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
    )

    # API 调用
    api_calls_total = metrics.counter(
        "api_calls_total",
        "Total API calls",
    )

    api_errors_total = metrics.counter(
        "api_errors_total",
        "Total API errors",
    )

    # AI 调用
    ai_calls_total = metrics.counter(
        "ai_calls_total",
        "Total AI API calls",
    )

    ai_call_duration = metrics.histogram(
        "ai_call_duration_seconds",
        "AI API call latency",
        buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    )

    ai_tokens_used = metrics.counter(
        "ai_tokens_used_total",
        "Total AI tokens consumed",
    )

    ai_errors_total = metrics.counter(
        "ai_errors_total",
        "Total AI call errors",
    )

    # 会话
    active_sessions = metrics.gauge(
        "active_sessions",
        "Number of active sessions",
    )

    session_duration = metrics.histogram(
        "session_duration_seconds",
        "Session duration",
        buckets=[60, 300, 600, 1800, 3600, 7200],
    )

    # 文件上传
    file_uploads_total = metrics.counter(
        "file_uploads_total",
        "Total file uploads",
    )

    file_upload_errors = metrics.counter(
        "file_upload_errors_total",
        "Total file upload errors",
    )

    file_upload_size = metrics.histogram(
        "file_upload_size_bytes",
        "File upload size",
        buckets=[1024, 10240, 102400, 512000, 1048576],
    )

    # 数据库
    db_queries_total = metrics.counter(
        "db_queries_total",
        "Total database queries",
    )

    db_query_duration = metrics.histogram(
        "db_query_duration_seconds",
        "Database query latency",
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    )

    # 错题
    wrong_questions_total = metrics.gauge(
        "wrong_questions_total",
        "Total wrong questions in database",
    )


class Timer:
    """计时器上下文管理器"""

    def __init__(self, histogram: Histogram):
        self.histogram = histogram
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.histogram.observe(duration)


def track_request(func):
    """装饰器：追踪请求"""
    def wrapper(*args, **kwargs):
        AppMetrics.http_requests_total.inc()

        with Timer(AppMetrics.http_request_duration):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                AppMetrics.api_errors_total.inc()
                raise

    return wrapper


def track_ai_call(func):
    """装饰器：追踪 AI 调用"""
    def wrapper(*args, **kwargs):
        AppMetrics.ai_calls_total.inc()

        with Timer(AppMetrics.ai_call_duration):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                AppMetrics.ai_errors_total.inc()
                raise

    return wrapper
