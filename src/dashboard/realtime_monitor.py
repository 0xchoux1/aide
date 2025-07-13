"""
AIDE リアルタイム監視システム

メトリクス監視、アラート、通知機能
"""

import time
import threading
import json
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import queue
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..config import get_config_manager
from ..logging import get_logger, get_audit_logger
from .metrics_collector import get_metrics_collector, MetricsCollector, MetricSeries


class AlertSeverity(Enum):
    """アラート重要度"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ThresholdType(Enum):
    """閾値タイプ"""
    ABSOLUTE = "absolute"      # 絶対値
    PERCENTAGE = "percentage"  # パーセンテージ
    RATE = "rate"             # 変化率
    TREND = "trend"           # トレンド


class ComparisonOperator(Enum):
    """比較演算子"""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "=="
    NOT_EQUAL = "!="


@dataclass
class MetricThreshold:
    """メトリクス閾値"""
    metric_name: str
    operator: ComparisonOperator
    value: float
    threshold_type: ThresholdType = ThresholdType.ABSOLUTE
    duration_seconds: int = 60  # 継続時間
    description: str = ""
    
    def check(self, current_value: float, historical_values: List[float] = None) -> bool:
        """閾値チェック"""
        if self.threshold_type == ThresholdType.ABSOLUTE:
            return self._compare(current_value, self.value)
        
        elif self.threshold_type == ThresholdType.PERCENTAGE:
            # パーセンテージ変化
            if not historical_values or len(historical_values) < 2:
                return False
            
            previous_value = historical_values[-2]
            if previous_value == 0:
                return False
            
            percentage_change = ((current_value - previous_value) / previous_value) * 100
            return self._compare(percentage_change, self.value)
        
        elif self.threshold_type == ThresholdType.RATE:
            # 変化率
            if not historical_values or len(historical_values) < 2:
                return False
            
            previous_value = historical_values[-2]
            rate_of_change = current_value - previous_value
            return self._compare(rate_of_change, self.value)
        
        elif self.threshold_type == ThresholdType.TREND:
            # トレンド分析（簡易実装）
            if not historical_values or len(historical_values) < 3:
                return False
            
            # 直近3点の平均傾向
            recent_values = historical_values[-3:]
            trend = (recent_values[-1] - recent_values[0]) / 2
            return self._compare(trend, self.value)
        
        return False
    
    def _compare(self, value1: float, value2: float) -> bool:
        """値比較"""
        if self.operator == ComparisonOperator.GREATER_THAN:
            return value1 > value2
        elif self.operator == ComparisonOperator.LESS_THAN:
            return value1 < value2
        elif self.operator == ComparisonOperator.GREATER_EQUAL:
            return value1 >= value2
        elif self.operator == ComparisonOperator.LESS_EQUAL:
            return value1 <= value2
        elif self.operator == ComparisonOperator.EQUAL:
            return abs(value1 - value2) < 0.001  # 浮動小数点誤差考慮
        elif self.operator == ComparisonOperator.NOT_EQUAL:
            return abs(value1 - value2) >= 0.001
        
        return False


@dataclass
class AlertRule:
    """アラートルール"""
    rule_id: str
    name: str
    description: str
    threshold: MetricThreshold
    severity: AlertSeverity
    enabled: bool = True
    cooldown_minutes: int = 10  # クールダウン期間
    notification_channels: List[str] = None
    
    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = []
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['threshold']['operator'] = self.threshold.operator.value
        data['threshold']['threshold_type'] = self.threshold.threshold_type.value
        data['severity'] = self.severity.value
        return data


@dataclass
class AlertEvent:
    """アラートイベント"""
    event_id: str
    rule_id: str
    metric_name: str
    severity: AlertSeverity
    message: str
    current_value: float
    threshold_value: float
    timestamp: float
    resolved: bool = False
    resolved_timestamp: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['severity'] = self.severity.value
        return data


class NotificationChannel:
    """通知チャネル基底クラス"""
    
    def __init__(self, channel_id: str, name: str):
        self.channel_id = channel_id
        self.name = name
        self.logger = get_logger(__name__)
    
    async def send_notification(self, alert: AlertEvent, rule: AlertRule) -> bool:
        """通知送信（サブクラスで実装）"""
        raise NotImplementedError


class ConsoleNotificationChannel(NotificationChannel):
    """コンソール通知チャネル"""
    
    def __init__(self):
        super().__init__("console", "Console Output")
    
    async def send_notification(self, alert: AlertEvent, rule: AlertRule) -> bool:
        """コンソール通知"""
        severity_icons = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
            AlertSeverity.EMERGENCY: "🆘"
        }
        
        icon = severity_icons.get(alert.severity, "🔔")
        timestamp = datetime.fromtimestamp(alert.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n{icon} ALERT [{alert.severity.value.upper()}] - {timestamp}")
        print(f"Rule: {rule.name}")
        print(f"Metric: {alert.metric_name}")
        print(f"Current Value: {alert.current_value}")
        print(f"Threshold: {rule.threshold.operator.value} {alert.threshold_value}")
        print(f"Message: {alert.message}")
        print("-" * 50)
        
        return True


class EmailNotificationChannel(NotificationChannel):
    """メール通知チャネル"""
    
    def __init__(self, smtp_server: str, smtp_port: int, 
                 username: str, password: str, from_email: str, to_emails: List[str]):
        super().__init__("email", "Email Notification")
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
    
    async def send_notification(self, alert: AlertEvent, rule: AlertRule) -> bool:
        """メール通知"""
        try:
            # メール作成
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"AIDE Alert: {rule.name} [{alert.severity.value.upper()}]"
            
            # メール本文
            body = self._create_email_body(alert, rule)
            msg.attach(MIMEText(body, 'html'))
            
            # SMTP送信
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            self.logger.info(f"アラートメール送信成功: {alert.event_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"メール送信エラー: {str(e)}")
            return False
    
    def _create_email_body(self, alert: AlertEvent, rule: AlertRule) -> str:
        """メール本文作成"""
        timestamp = datetime.fromtimestamp(alert.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        severity_colors = {
            AlertSeverity.INFO: "#17a2b8",
            AlertSeverity.WARNING: "#ffc107",
            AlertSeverity.CRITICAL: "#dc3545",
            AlertSeverity.EMERGENCY: "#6f42c1"
        }
        
        color = severity_colors.get(alert.severity, "#6c757d")
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 20px;">
                <h2 style="color: {color};">AIDE システムアラート</h2>
                
                <table style="border-collapse: collapse; width: 100%; margin-top: 20px;">
                    <tr>
                        <td style="padding: 8px; font-weight: bold; background-color: #f8f9fa;">重要度:</td>
                        <td style="padding: 8px; color: {color}; font-weight: bold;">{alert.severity.value.upper()}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; background-color: #f8f9fa;">ルール名:</td>
                        <td style="padding: 8px;">{rule.name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; background-color: #f8f9fa;">メトリクス:</td>
                        <td style="padding: 8px;">{alert.metric_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; background-color: #f8f9fa;">現在値:</td>
                        <td style="padding: 8px;">{alert.current_value}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; background-color: #f8f9fa;">閾値:</td>
                        <td style="padding: 8px;">{rule.threshold.operator.value} {alert.threshold_value}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; background-color: #f8f9fa;">時刻:</td>
                        <td style="padding: 8px;">{timestamp}</td>
                    </tr>
                </table>
                
                <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                    <strong>メッセージ:</strong><br>
                    {alert.message}
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background-color: #e9ecef; border-radius: 5px;">
                    <strong>説明:</strong><br>
                    {rule.description}
                </div>
            </div>
            
            <p style="margin-top: 30px; font-size: 12px; color: #6c757d;">
                このメールはAIDEシステムから自動送信されました。
            </p>
        </body>
        </html>
        """


class WebhookNotificationChannel(NotificationChannel):
    """Webhook通知チャネル"""
    
    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        super().__init__("webhook", "Webhook Notification")
        self.webhook_url = webhook_url
        self.headers = headers or {}
    
    async def send_notification(self, alert: AlertEvent, rule: AlertRule) -> bool:
        """Webhook通知"""
        try:
            import requests
            
            payload = {
                "alert": alert.to_dict(),
                "rule": rule.to_dict(),
                "timestamp": alert.timestamp,
                "source": "AIDE"
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"Webhook通知送信成功: {alert.event_id}")
                return True
            else:
                self.logger.error(f"Webhook通知失敗: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Webhook送信エラー: {str(e)}")
            return False


class RealtimeMonitor:
    """リアルタイム監視システム"""
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        self.metrics_collector = metrics_collector or get_metrics_collector()
        self.logger = get_logger(__name__)
        self.audit_logger = get_audit_logger()
        
        # アラートルール
        self.alert_rules: Dict[str, AlertRule] = {}
        
        # 通知チャネル
        self.notification_channels: Dict[str, NotificationChannel] = {}
        
        # アクティブアラート
        self.active_alerts: Dict[str, AlertEvent] = {}
        
        # アラート履歴
        self.alert_history: List[AlertEvent] = []
        
        # クールダウン管理
        self.cooldown_tracker: Dict[str, float] = {}
        
        # 監視スレッド
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self.is_running = False
        
        # 設定
        self.config_manager = get_config_manager()
        self.check_interval = self.config_manager.get(
            "monitoring.check_interval_seconds", 30
        )
        
        # デフォルト通知チャネル追加
        self.add_notification_channel(ConsoleNotificationChannel())
        
        # デフォルトルール追加
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """デフォルトアラートルール設定"""
        # CPU使用率アラート
        self.add_alert_rule(AlertRule(
            rule_id="cpu_high",
            name="CPU使用率高",
            description="CPU使用率が80%を超えています",
            threshold=MetricThreshold(
                metric_name="system_cpu_usage",
                operator=ComparisonOperator.GREATER_THAN,
                value=80.0,
                duration_seconds=60
            ),
            severity=AlertSeverity.WARNING,
            notification_channels=["console"]
        ))
        
        # メモリ使用率アラート
        self.add_alert_rule(AlertRule(
            rule_id="memory_high",
            name="メモリ使用率高",
            description="メモリ使用率が85%を超えています",
            threshold=MetricThreshold(
                metric_name="system_memory_usage",
                operator=ComparisonOperator.GREATER_THAN,
                value=85.0,
                duration_seconds=60
            ),
            severity=AlertSeverity.CRITICAL,
            notification_channels=["console"]
        ))
        
        # ディスク使用率アラート
        self.add_alert_rule(AlertRule(
            rule_id="disk_high",
            name="ディスク使用率高",
            description="ディスク使用率が90%を超えています",
            threshold=MetricThreshold(
                metric_name="system_disk_usage",
                operator=ComparisonOperator.GREATER_THAN,
                value=90.0,
                duration_seconds=60
            ),
            severity=AlertSeverity.CRITICAL,
            notification_channels=["console"]
        ))
        
        # レスポンス時間アラート
        self.add_alert_rule(AlertRule(
            rule_id="response_time_high",
            name="レスポンス時間高",
            description="平均レスポンス時間が2秒を超えています",
            threshold=MetricThreshold(
                metric_name="response_time",
                operator=ComparisonOperator.GREATER_THAN,
                value=2000.0,  # ミリ秒
                duration_seconds=120
            ),
            severity=AlertSeverity.WARNING,
            notification_channels=["console"]
        ))
        
        # ヘルススコア低下アラート
        self.add_alert_rule(AlertRule(
            rule_id="health_score_low",
            name="ヘルススコア低下",
            description="システムヘルススコアが50を下回りました",
            threshold=MetricThreshold(
                metric_name="health_score",
                operator=ComparisonOperator.LESS_THAN,
                value=50.0,
                duration_seconds=60
            ),
            severity=AlertSeverity.CRITICAL,
            notification_channels=["console"]
        ))
    
    def add_alert_rule(self, rule: AlertRule):
        """アラートルール追加"""
        self.alert_rules[rule.rule_id] = rule
        self.logger.info(f"アラートルール追加: {rule.name}")
    
    def remove_alert_rule(self, rule_id: str):
        """アラートルール削除"""
        if rule_id in self.alert_rules:
            rule = self.alert_rules.pop(rule_id)
            self.logger.info(f"アラートルール削除: {rule.name}")
            return True
        return False
    
    def add_notification_channel(self, channel: NotificationChannel):
        """通知チャネル追加"""
        self.notification_channels[channel.channel_id] = channel
        self.logger.info(f"通知チャネル追加: {channel.name}")
    
    def start_monitoring(self):
        """監視開始"""
        if self.is_running:
            self.logger.warning("監視は既に開始されています")
            return
        
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitor_thread.start()
        self.is_running = True
        
        self.logger.info("リアルタイム監視開始")
        self.audit_logger.log_system_event("monitoring_start", "リアルタイム監視開始")
    
    def stop_monitoring(self):
        """監視停止"""
        if not self.is_running:
            return
        
        self.stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        self.is_running = False
        self.logger.info("リアルタイム監視停止")
        self.audit_logger.log_system_event("monitoring_stop", "リアルタイム監視停止")
    
    def _monitoring_loop(self):
        """監視ループ"""
        while not self.stop_event.is_set():
            try:
                self._check_all_rules()
                self._resolve_alerts()
            except Exception as e:
                self.logger.error(f"監視ループエラー: {str(e)}")
            
            self.stop_event.wait(self.check_interval)
    
    def _check_all_rules(self):
        """全ルールチェック"""
        for rule in self.alert_rules.values():
            if not rule.enabled:
                continue
            
            # クールダウンチェック
            if self._is_in_cooldown(rule.rule_id):
                continue
            
            self._check_rule(rule)
    
    def _check_rule(self, rule: AlertRule):
        """個別ルールチェック"""
        metric_series = self.metrics_collector.get_metric_series(rule.threshold.metric_name)
        
        if not metric_series or not metric_series.points:
            return
        
        # 現在値取得
        latest_point = metric_series.get_latest()
        current_value = latest_point.value
        
        # 履歴値取得（トレンド分析用）
        now = time.time()
        historical_points = metric_series.get_points_in_range(
            now - rule.threshold.duration_seconds, 
            now
        )
        historical_values = [p.value for p in historical_points]
        
        # 閾値チェック
        if rule.threshold.check(current_value, historical_values):
            self._trigger_alert(rule, current_value)
    
    def _trigger_alert(self, rule: AlertRule, current_value: float):
        """アラート発生"""
        # 既存のアクティブアラートチェック
        if rule.rule_id in self.active_alerts:
            return
        
        # アラートイベント作成
        event_id = f"{rule.rule_id}_{int(time.time())}"
        alert = AlertEvent(
            event_id=event_id,
            rule_id=rule.rule_id,
            metric_name=rule.threshold.metric_name,
            severity=rule.severity,
            message=f"{rule.name}: {rule.threshold.metric_name} = {current_value} {rule.threshold.operator.value} {rule.threshold.value}",
            current_value=current_value,
            threshold_value=rule.threshold.value,
            timestamp=time.time()
        )
        
        # アクティブアラートに追加
        self.active_alerts[rule.rule_id] = alert
        self.alert_history.append(alert)
        
        # ログ記録
        self.logger.warning(f"アラート発生: {alert.message}")
        self.audit_logger.log_event(
            "alert_triggered",
            f"アラート発生: {rule.name}",
            severity="high",
            rule_id=rule.rule_id,
            metric_name=rule.threshold.metric_name,
            current_value=current_value,
            threshold_value=rule.threshold.value
        )
        
        # 通知送信
        self._send_notifications(alert, rule)
        
        # クールダウン設定
        self.cooldown_tracker[rule.rule_id] = time.time() + (rule.cooldown_minutes * 60)
    
    def _send_notifications(self, alert: AlertEvent, rule: AlertRule):
        """通知送信"""
        for channel_id in rule.notification_channels:
            if channel_id in self.notification_channels:
                channel = self.notification_channels[channel_id]
                
                try:
                    # 非同期実行（簡易実装）
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    success = loop.run_until_complete(
                        channel.send_notification(alert, rule)
                    )
                    loop.close()
                    
                    if success:
                        self.logger.info(f"通知送信成功: {channel.name}")
                    else:
                        self.logger.error(f"通知送信失敗: {channel.name}")
                        
                except Exception as e:
                    self.logger.error(f"通知送信エラー ({channel.name}): {str(e)}")
    
    def _resolve_alerts(self):
        """アラート解決チェック"""
        resolved_alerts = []
        
        for rule_id, alert in self.active_alerts.items():
            rule = self.alert_rules.get(rule_id)
            if not rule:
                resolved_alerts.append(rule_id)
                continue
            
            # メトリクス確認
            metric_series = self.metrics_collector.get_metric_series(rule.threshold.metric_name)
            if not metric_series or not metric_series.points:
                continue
            
            latest_point = metric_series.get_latest()
            current_value = latest_point.value
            
            # 履歴値取得
            now = time.time()
            historical_points = metric_series.get_points_in_range(
                now - rule.threshold.duration_seconds,
                now
            )
            historical_values = [p.value for p in historical_points]
            
            # 閾値を下回った場合は解決
            if not rule.threshold.check(current_value, historical_values):
                alert.resolved = True
                alert.resolved_timestamp = time.time()
                resolved_alerts.append(rule_id)
                
                self.logger.info(f"アラート解決: {alert.message}")
                self.audit_logger.log_event(
                    "alert_resolved",
                    f"アラート解決: {rule.name}",
                    severity="medium",
                    rule_id=rule_id,
                    resolution_time=alert.resolved_timestamp - alert.timestamp
                )
        
        # 解決済みアラートを削除
        for rule_id in resolved_alerts:
            self.active_alerts.pop(rule_id, None)
    
    def _is_in_cooldown(self, rule_id: str) -> bool:
        """クールダウン中か判定"""
        if rule_id not in self.cooldown_tracker:
            return False
        
        return time.time() < self.cooldown_tracker[rule_id]
    
    def get_active_alerts(self) -> List[AlertEvent]:
        """アクティブアラート取得"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[AlertEvent]:
        """アラート履歴取得"""
        return self.alert_history[-limit:]
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """監視状態取得"""
        return {
            "is_running": self.is_running,
            "total_rules": len(self.alert_rules),
            "enabled_rules": len([r for r in self.alert_rules.values() if r.enabled]),
            "active_alerts": len(self.active_alerts),
            "notification_channels": len(self.notification_channels),
            "check_interval": self.check_interval,
            "alert_history_count": len(self.alert_history)
        }


# グローバル監視インスタンス
_global_monitor: Optional[RealtimeMonitor] = None


def get_realtime_monitor() -> RealtimeMonitor:
    """グローバル監視インスタンス取得"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = RealtimeMonitor()
    return _global_monitor