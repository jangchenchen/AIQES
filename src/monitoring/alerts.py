"""监控告警系统"""

from __future__ import annotations

import json
import smtplib
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib import request as urllib_request


class AlertSeverity(Enum):
    """告警严重级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警"""

    name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class AlertRule:
    """告警规则"""

    def __init__(
        self,
        name: str,
        condition: Callable[[], bool],
        severity: AlertSeverity,
        message: str,
        cooldown_seconds: int = 300,
    ):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.message = message
        self.cooldown_seconds = cooldown_seconds
        self._last_triggered: Optional[datetime] = None
        self._active_alert: Optional[Alert] = None

    def check(self) -> Optional[Alert]:
        """检查规则"""
        # 冷却期检查
        if self._last_triggered:
            elapsed = (datetime.utcnow() - self._last_triggered).total_seconds()
            if elapsed < self.cooldown_seconds:
                return None

        # 条件检查
        try:
            if self.condition():
                self._last_triggered = datetime.utcnow()
                alert = Alert(
                    name=self.name,
                    severity=self.severity,
                    message=self.message,
                )
                self._active_alert = alert
                return alert
            else:
                # 条件不满足，如果有活跃告警则标记为已解决
                if self._active_alert and not self._active_alert.resolved:
                    self._active_alert.resolved = True
                    self._active_alert.resolved_at = datetime.utcnow()
        except Exception as e:
            print(f"⚠️  规则检查失败 [{self.name}]: {e}")

        return None


class AlertChannel(ABC):
    """告警通道基类"""

    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """发送告警"""
        pass


class ConsoleChannel(AlertChannel):
    """控制台告警通道"""

    def send(self, alert: Alert) -> bool:
        """打印到控制台"""
        icon = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🚨",
        }[alert.severity]

        print(f"\n{icon} ALERT [{alert.severity.value.upper()}] {alert.name}")
        print(f"   {alert.message}")
        print(f"   Time: {alert.timestamp.isoformat()}")
        if alert.labels:
            print(f"   Labels: {alert.labels}")
        print()

        return True


class FileChannel(AlertChannel):
    """文件告警通道"""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def send(self, alert: Alert) -> bool:
        """写入日志文件"""
        try:
            entry = {
                "timestamp": alert.timestamp.isoformat(),
                "name": alert.name,
                "severity": alert.severity.value,
                "message": alert.message,
                "labels": alert.labels,
                "resolved": alert.resolved,
            }

            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            return True
        except Exception as e:
            print(f"❌ 文件通道发送失败: {e}")
            return False


class WebhookChannel(AlertChannel):
    """Webhook 告警通道（Slack, Discord, 钉钉等）"""

    def __init__(self, webhook_url: str, timeout: int = 10):
        self.webhook_url = webhook_url
        self.timeout = timeout

    def send(self, alert: Alert) -> bool:
        """发送到 Webhook"""
        try:
            payload = {
                "text": f"[{alert.severity.value.upper()}] {alert.name}",
                "attachments": [
                    {
                        "color": self._get_color(alert.severity),
                        "fields": [
                            {"title": "Message", "value": alert.message},
                            {"title": "Time", "value": alert.timestamp.isoformat()},
                        ],
                    }
                ],
            }

            data = json.dumps(payload).encode("utf-8")
            req = urllib_request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )

            with urllib_request.urlopen(req, timeout=self.timeout) as response:
                return response.status == 200

        except Exception as e:
            print(f"❌ Webhook 通道发送失败: {e}")
            return False

    def _get_color(self, severity: AlertSeverity) -> str:
        """获取告警颜色"""
        return {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ffcc00",
            AlertSeverity.ERROR: "#ff6600",
            AlertSeverity.CRITICAL: "#ff0000",
        }[severity]


class EmailChannel(AlertChannel):
    """邮件告警通道"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str],
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    def send(self, alert: Alert) -> bool:
        """发送邮件"""
        try:
            subject = f"[{alert.severity.value.upper()}] {alert.name}"
            body = f"""
告警名称: {alert.name}
严重级别: {alert.severity.value}
时间: {alert.timestamp.isoformat()}

消息:
{alert.message}

标签:
{json.dumps(alert.labels, indent=2, ensure_ascii=False)}
            """.strip()

            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"❌ 邮件通道发送失败: {e}")
            return False


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self._rules: List[AlertRule] = []
        self._channels: List[AlertChannel] = []
        self._alerts: List[Alert] = []
        self._check_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        self._rules.append(rule)

    def add_channel(self, channel: AlertChannel) -> None:
        """添加告警通道"""
        self._channels.append(channel)

    def trigger_alert(self, alert: Alert) -> None:
        """手动触发告警"""
        self._alerts.append(alert)

        for channel in self._channels:
            try:
                channel.send(alert)
            except Exception as e:
                print(f"⚠️  告警发送失败: {e}")

    def start(self, interval_seconds: int = 60) -> None:
        """启动定期检查"""

        def check_loop():
            while not self._stop_event.wait(timeout=interval_seconds):
                self._check_rules()

        self._check_thread = threading.Thread(target=check_loop, daemon=True)
        self._check_thread.start()
        print(f"✅ 告警监控已启动（检查间隔: {interval_seconds}秒）")

    def stop(self) -> None:
        """停止检查"""
        if self._check_thread:
            self._stop_event.set()
            self._check_thread.join(timeout=2)
            print("🛑 告警监控已停止")

    def _check_rules(self) -> None:
        """检查所有规则"""
        for rule in self._rules:
            alert = rule.check()
            if alert:
                self.trigger_alert(alert)

    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return [a for a in self._alerts if not a.resolved]

    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """获取告警历史"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [a for a in self._alerts if a.timestamp > cutoff]


# 全局告警管理器
alert_manager = AlertManager()


# 预定义告警规则
def create_default_rules(metrics_collector) -> List[AlertRule]:
    """创建默认告警规则"""
    from .metrics import metrics

    rules = []

    # 高错误率告警
    rules.append(
        AlertRule(
            name="high_error_rate",
            condition=lambda: _check_error_rate(metrics_collector),
            severity=AlertSeverity.ERROR,
            message="API 错误率超过 10%",
            cooldown_seconds=600,
        )
    )

    # AI 调用失败告警
    rules.append(
        AlertRule(
            name="ai_call_failures",
            condition=lambda: _check_ai_failures(metrics_collector),
            severity=AlertSeverity.WARNING,
            message="AI 调用失败次数过多",
            cooldown_seconds=300,
        )
    )

    # 响应时间告警
    rules.append(
        AlertRule(
            name="slow_responses",
            condition=lambda: _check_slow_responses(metrics_collector),
            severity=AlertSeverity.WARNING,
            message="响应时间超过阈值",
            cooldown_seconds=300,
        )
    )

    return rules


def _check_error_rate(metrics_collector) -> bool:
    """检查错误率"""
    metrics_data = metrics_collector.get_metrics()
    counters = metrics_data.get("counters", {})

    total = counters.get("http_requests_total", {}).get("value", 0)
    errors = counters.get("api_errors_total", {}).get("value", 0)

    if total > 100:  # 至少100个请求
        error_rate = errors / total
        return error_rate > 0.1  # 10%

    return False


def _check_ai_failures(metrics_collector) -> bool:
    """检查 AI 调用失败"""
    metrics_data = metrics_collector.get_metrics()
    counters = metrics_data.get("counters", {})

    ai_calls = counters.get("ai_calls_total", {}).get("value", 0)
    ai_errors = counters.get("ai_errors_total", {}).get("value", 0)

    if ai_calls > 10:
        failure_rate = ai_errors / ai_calls
        return failure_rate > 0.2  # 20%

    return False


def _check_slow_responses(metrics_collector) -> bool:
    """检查响应时间"""
    metrics_data = metrics_collector.get_metrics()
    histograms = metrics_data.get("histograms", {})

    request_duration = histograms.get("http_request_duration_seconds", {})
    count = request_duration.get("count", 0)
    total = request_duration.get("sum", 0)

    if count > 100:
        avg_duration = total / count
        return avg_duration > 2.0  # 平均超过2秒

    return False
