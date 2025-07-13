"""
AIDE 包括的エラーハンドリングシステム

エラー分類、重要度判定、自動回復、通知機能
"""

import time
import traceback
import threading
from typing import Dict, List, Optional, Any, Callable, Type, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
from contextlib import contextmanager

from ..config import get_config_manager
from ..logging import get_logger, get_audit_logger


class ErrorCategory(Enum):
    """エラーカテゴリ"""
    SYSTEM = "system"
    NETWORK = "network"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    EXTERNAL_API = "external_api"
    RESOURCE = "resource"
    LOGIC = "logic"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """エラー重要度"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


@dataclass
class ErrorContext:
    """エラーコンテキスト"""
    error_id: str
    timestamp: float
    category: ErrorCategory
    severity: ErrorSeverity
    component: str
    function_name: str
    error_type: str
    error_message: str
    traceback_str: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Dict[str, Any] = None
    retry_count: int = 0
    resolved: bool = False
    resolution_time: Optional[float] = None
    
    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['category'] = self.category.value
        data['severity'] = self.severity.value
        return data


@dataclass
class ErrorPattern:
    """エラーパターン"""
    pattern_id: str
    name: str
    category: ErrorCategory
    severity: ErrorSeverity
    error_types: List[str]
    message_patterns: List[str]
    auto_retry: bool = True
    max_retries: int = 3
    escalate_after_count: int = 5
    recovery_actions: List[Callable] = None
    
    def __post_init__(self):
        if self.recovery_actions is None:
            self.recovery_actions = []


class ErrorHandler:
    """包括的エラーハンドリングシステム"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger(__name__)
        self.audit_logger = get_audit_logger()
        
        # エラー履歴
        self.error_history: List[ErrorContext] = []
        self.max_history_size = self.config_manager.get("error_handling.max_history", 1000)
        
        # エラーパターン
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self._initialize_error_patterns()
        
        # エラー統計
        self.error_stats = {
            'total_errors': 0,
            'errors_by_category': {cat.value: 0 for cat in ErrorCategory},
            'errors_by_severity': {sev.value: 0 for sev in ErrorSeverity},
            'auto_resolved_errors': 0,
            'escalated_errors': 0
        }
        
        # エラー頻度追跡
        self.error_frequency: Dict[str, List[float]] = {}
        self.frequency_window = 3600  # 1時間
        
        # 通知設定
        self.notification_enabled = self.config_manager.get("error_handling.notifications", True)
        self.notification_threshold = ErrorSeverity(
            self.config_manager.get("error_handling.notification_threshold", 3)
        )
        
        # スレッドロック
        self.lock = threading.Lock()

    def _initialize_error_patterns(self):
        """エラーパターン初期化"""
        patterns = [
            # ネットワークエラー
            ErrorPattern(
                pattern_id="network_timeout",
                name="ネットワークタイムアウト",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                error_types=["TimeoutError", "ConnectionTimeout", "RequestTimeout"],
                message_patterns=["timeout", "timed out", "connection timeout"],
                auto_retry=True,
                max_retries=3,
                recovery_actions=[self._recover_network_connection]
            ),
            
            ErrorPattern(
                pattern_id="connection_refused",
                name="接続拒否",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                error_types=["ConnectionRefusedError", "ConnectionError"],
                message_patterns=["connection refused", "connection failed"],
                auto_retry=True,
                max_retries=5,
                recovery_actions=[self._recover_network_connection]
            ),
            
            # データベースエラー
            ErrorPattern(
                pattern_id="database_connection",
                name="データベース接続エラー",
                category=ErrorCategory.DATABASE,
                severity=ErrorSeverity.HIGH,
                error_types=["DatabaseError", "OperationalError", "ConnectionError"],
                message_patterns=["database", "connection", "sql"],
                auto_retry=True,
                max_retries=3,
                recovery_actions=[self._recover_database_connection]
            ),
            
            # リソースエラー
            ErrorPattern(
                pattern_id="memory_error",
                name="メモリ不足",
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.CRITICAL,
                error_types=["MemoryError", "OutOfMemoryError"],
                message_patterns=["memory", "out of memory"],
                auto_retry=False,
                recovery_actions=[self._recover_memory_issue]
            ),
            
            ErrorPattern(
                pattern_id="disk_space",
                name="ディスク容量不足",
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.CRITICAL,
                error_types=["OSError", "IOError"],
                message_patterns=["no space", "disk full", "device full"],
                auto_retry=False,
                recovery_actions=[self._recover_disk_space]
            ),
            
            # 認証・認可エラー
            ErrorPattern(
                pattern_id="authentication_failed",
                name="認証失敗",
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.MEDIUM,
                error_types=["AuthenticationError", "UnauthorizedError"],
                message_patterns=["authentication", "unauthorized", "invalid credentials"],
                auto_retry=False,
                recovery_actions=[self._recover_authentication]
            ),
            
            # 設定エラー
            ErrorPattern(
                pattern_id="configuration_error",
                name="設定エラー",
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                error_types=["ConfigurationError", "ValueError", "KeyError"],
                message_patterns=["configuration", "config", "missing setting"],
                auto_retry=False,
                recovery_actions=[self._recover_configuration]
            ),
            
            # 外部APIエラー
            ErrorPattern(
                pattern_id="api_rate_limit",
                name="API制限",
                category=ErrorCategory.EXTERNAL_API,
                severity=ErrorSeverity.MEDIUM,
                error_types=["RateLimitError", "TooManyRequestsError"],
                message_patterns=["rate limit", "too many requests", "quota exceeded"],
                auto_retry=True,
                max_retries=5,
                recovery_actions=[self._recover_api_rate_limit]
            ),
            
            # バリデーションエラー
            ErrorPattern(
                pattern_id="validation_error",
                name="データバリデーションエラー",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                error_types=["ValidationError", "ValueError", "TypeError"],
                message_patterns=["validation", "invalid", "malformed"],
                auto_retry=False,
                recovery_actions=[self._recover_validation_error]
            )
        ]
        
        for pattern in patterns:
            self.error_patterns[pattern.pattern_id] = pattern

    def handle_error(self, exception: Exception, component: str, 
                    function_name: str = None, user_id: str = None,
                    request_id: str = None, additional_data: Dict[str, Any] = None) -> ErrorContext:
        """エラーハンドリング実行"""
        with self.lock:
            # エラーコンテキスト作成
            error_context = self._create_error_context(
                exception, component, function_name, user_id, request_id, additional_data
            )
            
            # エラーパターンマッチング
            pattern = self._match_error_pattern(error_context)
            
            # エラー頻度追跡
            self._track_error_frequency(error_context)
            
            # エラー履歴追加
            self.error_history.append(error_context)
            if len(self.error_history) > self.max_history_size:
                self.error_history = self.error_history[-self.max_history_size:]
            
            # 統計更新
            self._update_error_stats(error_context)
            
            # ログ記録
            self._log_error(error_context, pattern)
            
            # 自動回復試行
            if pattern and pattern.auto_retry and error_context.retry_count < pattern.max_retries:
                recovery_result = self._attempt_recovery(error_context, pattern)
                if recovery_result:
                    error_context.resolved = True
                    error_context.resolution_time = time.time()
                    self.error_stats['auto_resolved_errors'] += 1
            
            # エスカレーション判定
            if pattern and self._should_escalate(error_context, pattern):
                self._escalate_error(error_context, pattern)
            
            # 通知送信
            if self._should_notify(error_context):
                self._send_notification(error_context, pattern)
            
            return error_context

    def _create_error_context(self, exception: Exception, component: str,
                            function_name: str = None, user_id: str = None,
                            request_id: str = None, additional_data: Dict[str, Any] = None) -> ErrorContext:
        """エラーコンテキスト作成"""
        error_id = f"error_{int(time.time() * 1000000)}"
        
        # エラー分類
        category = self._classify_error(exception)
        severity = self._determine_severity(exception, category)
        
        return ErrorContext(
            error_id=error_id,
            timestamp=time.time(),
            category=category,
            severity=severity,
            component=component,
            function_name=function_name or "unknown",
            error_type=type(exception).__name__,
            error_message=str(exception),
            traceback_str=traceback.format_exc(),
            user_id=user_id,
            request_id=request_id,
            additional_data=additional_data or {}
        )

    def _classify_error(self, exception: Exception) -> ErrorCategory:
        """エラー分類"""
        error_type = type(exception).__name__
        error_message = str(exception).lower()
        
        # エラータイプとメッセージに基づく分類
        if any(keyword in error_message for keyword in ["network", "connection", "timeout"]):
            return ErrorCategory.NETWORK
        elif any(keyword in error_message for keyword in ["database", "sql", "query"]):
            return ErrorCategory.DATABASE
        elif any(keyword in error_message for keyword in ["memory", "out of memory"]):
            return ErrorCategory.RESOURCE
        elif any(keyword in error_message for keyword in ["authentication", "unauthorized"]):
            return ErrorCategory.AUTHENTICATION
        elif any(keyword in error_message for keyword in ["permission", "forbidden"]):
            return ErrorCategory.AUTHORIZATION
        elif any(keyword in error_message for keyword in ["validation", "invalid"]):
            return ErrorCategory.VALIDATION
        elif any(keyword in error_message for keyword in ["configuration", "config"]):
            return ErrorCategory.CONFIGURATION
        elif any(keyword in error_message for keyword in ["api", "rate limit"]):
            return ErrorCategory.EXTERNAL_API
        elif error_type in ["OSError", "IOError", "FileNotFoundError"]:
            return ErrorCategory.SYSTEM
        else:
            return ErrorCategory.UNKNOWN

    def _determine_severity(self, exception: Exception, category: ErrorCategory) -> ErrorSeverity:
        """エラー重要度判定"""
        error_type = type(exception).__name__
        
        # 重要度の高いエラータイプ
        critical_errors = ["MemoryError", "SystemError", "KeyboardInterrupt"]
        high_errors = ["ConnectionError", "DatabaseError", "SecurityError"]
        medium_errors = ["TimeoutError", "ValueError", "TypeError"]
        
        if error_type in critical_errors:
            return ErrorSeverity.CRITICAL
        elif error_type in high_errors:
            return ErrorSeverity.HIGH
        elif error_type in medium_errors:
            return ErrorSeverity.MEDIUM
        elif category in [ErrorCategory.RESOURCE, ErrorCategory.SYSTEM]:
            return ErrorSeverity.HIGH
        elif category in [ErrorCategory.NETWORK, ErrorCategory.DATABASE]:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    def _match_error_pattern(self, error_context: ErrorContext) -> Optional[ErrorPattern]:
        """エラーパターンマッチング"""
        for pattern in self.error_patterns.values():
            # カテゴリマッチ
            if pattern.category != error_context.category:
                continue
            
            # エラータイプマッチ
            if error_context.error_type in pattern.error_types:
                return pattern
            
            # メッセージパターンマッチ
            error_message_lower = error_context.error_message.lower()
            if any(pattern_text in error_message_lower for pattern_text in pattern.message_patterns):
                return pattern
        
        return None

    def _track_error_frequency(self, error_context: ErrorContext):
        """エラー頻度追跡"""
        pattern_key = f"{error_context.category.value}_{error_context.error_type}"
        current_time = time.time()
        
        if pattern_key not in self.error_frequency:
            self.error_frequency[pattern_key] = []
        
        # 現在時刻を追加
        self.error_frequency[pattern_key].append(current_time)
        
        # 古いエントリを削除（頻度ウィンドウ外）
        cutoff_time = current_time - self.frequency_window
        self.error_frequency[pattern_key] = [
            timestamp for timestamp in self.error_frequency[pattern_key]
            if timestamp >= cutoff_time
        ]

    def _update_error_stats(self, error_context: ErrorContext):
        """エラー統計更新"""
        self.error_stats['total_errors'] += 1
        self.error_stats['errors_by_category'][error_context.category.value] += 1
        self.error_stats['errors_by_severity'][error_context.severity.value] += 1

    def _log_error(self, error_context: ErrorContext, pattern: Optional[ErrorPattern]):
        """エラーログ記録"""
        log_level = {
            ErrorSeverity.LOW: self.logger.info,
            ErrorSeverity.MEDIUM: self.logger.warning,
            ErrorSeverity.HIGH: self.logger.error,
            ErrorSeverity.CRITICAL: self.logger.critical,
            ErrorSeverity.EMERGENCY: self.logger.critical
        }[error_context.severity]
        
        log_message = (
            f"エラー発生: {error_context.error_id} - "
            f"{error_context.component}.{error_context.function_name} - "
            f"{error_context.error_type}: {error_context.error_message}"
        )
        
        log_level(log_message)
        
        # 監査ログ
        self.audit_logger.log_event(
            "error_occurred",
            log_message,
            severity="high" if error_context.severity.value >= 3 else "medium",
            error_context=error_context.to_dict(),
            pattern_matched=pattern.pattern_id if pattern else None
        )

    def _attempt_recovery(self, error_context: ErrorContext, pattern: ErrorPattern) -> bool:
        """自動回復試行"""
        error_context.retry_count += 1
        
        self.logger.info(
            f"自動回復試行: {error_context.error_id} - "
            f"試行回数: {error_context.retry_count}/{pattern.max_retries}"
        )
        
        # 回復アクション実行
        for recovery_action in pattern.recovery_actions:
            try:
                result = recovery_action(error_context)
                if result:
                    self.logger.info(f"自動回復成功: {error_context.error_id}")
                    return True
            except Exception as e:
                self.logger.error(f"回復アクション失敗: {str(e)}")
        
        return False

    def _should_escalate(self, error_context: ErrorContext, pattern: ErrorPattern) -> bool:
        """エスカレーション判定"""
        if not pattern:
            return error_context.severity.value >= 4
        
        # パターンで指定された回数を超えた場合
        pattern_key = f"{error_context.category.value}_{error_context.error_type}"
        frequency = len(self.error_frequency.get(pattern_key, []))
        
        return frequency >= pattern.escalate_after_count

    def _escalate_error(self, error_context: ErrorContext, pattern: Optional[ErrorPattern]):
        """エラーエスカレーション"""
        self.error_stats['escalated_errors'] += 1
        
        escalation_message = (
            f"エラーエスカレーション: {error_context.error_id} - "
            f"頻度が閾値を超えました"
        )
        
        self.logger.critical(escalation_message)
        
        self.audit_logger.log_event(
            "error_escalated",
            escalation_message,
            severity="critical",
            error_context=error_context.to_dict()
        )

    def _should_notify(self, error_context: ErrorContext) -> bool:
        """通知送信判定"""
        return (
            self.notification_enabled and 
            error_context.severity.value >= self.notification_threshold.value
        )

    def _send_notification(self, error_context: ErrorContext, pattern: Optional[ErrorPattern]):
        """通知送信"""
        # 簡易実装: ログによる通知
        notification_message = (
            f"🚨 AIDE システムエラー通知\n"
            f"エラーID: {error_context.error_id}\n"
            f"重要度: {error_context.severity.name}\n"
            f"カテゴリ: {error_context.category.name}\n"
            f"コンポーネント: {error_context.component}\n"
            f"エラー: {error_context.error_message}\n"
            f"時刻: {datetime.fromtimestamp(error_context.timestamp).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        self.logger.critical(f"NOTIFICATION: {notification_message}")

    # 回復アクション関数群
    def _recover_network_connection(self, error_context: ErrorContext) -> bool:
        """ネットワーク接続回復"""
        self.logger.info("ネットワーク接続回復試行")
        # 実装例: 接続リトライ待機
        time.sleep(2)
        return True

    def _recover_database_connection(self, error_context: ErrorContext) -> bool:
        """データベース接続回復"""
        self.logger.info("データベース接続回復試行")
        # 実装例: データベース接続プール再初期化
        time.sleep(1)
        return True

    def _recover_memory_issue(self, error_context: ErrorContext) -> bool:
        """メモリ問題回復"""
        self.logger.info("メモリ問題回復試行")
        # 実装例: ガベージコレクション実行
        import gc
        gc.collect()
        return True

    def _recover_disk_space(self, error_context: ErrorContext) -> bool:
        """ディスク容量回復"""
        self.logger.info("ディスク容量回復試行")
        # 実装例: 一時ファイルクリーンアップ
        return False  # 通常は手動対応が必要

    def _recover_authentication(self, error_context: ErrorContext) -> bool:
        """認証問題回復"""
        self.logger.info("認証問題回復試行")
        # 実装例: トークン再取得
        return False  # 通常は再認証が必要

    def _recover_configuration(self, error_context: ErrorContext) -> bool:
        """設定問題回復"""
        self.logger.info("設定問題回復試行")
        # 実装例: デフォルト設定適用
        return False  # 通常は設定修正が必要

    def _recover_api_rate_limit(self, error_context: ErrorContext) -> bool:
        """API制限回復"""
        self.logger.info("API制限回復試行")
        # 実装例: 待機時間を設ける
        time.sleep(60)  # 1分待機
        return True

    def _recover_validation_error(self, error_context: ErrorContext) -> bool:
        """バリデーションエラー回復"""
        self.logger.info("バリデーションエラー回復試行")
        # 実装例: データクリーニング
        return False  # 通常はデータ修正が必要

    @contextmanager
    def error_context(self, component: str, function_name: str = None, 
                     user_id: str = None, request_id: str = None,
                     additional_data: Dict[str, Any] = None):
        """エラーハンドリングコンテキスト"""
        try:
            yield
        except Exception as e:
            self.handle_error(
                e, component, function_name, user_id, request_id, additional_data
            )
            raise  # 元のエラーを再発生

    def get_error_statistics(self) -> Dict[str, Any]:
        """エラー統計取得"""
        return {
            'error_stats': self.error_stats.copy(),
            'error_history_size': len(self.error_history),
            'active_patterns': len(self.error_patterns),
            'recent_errors': [
                ctx.to_dict() for ctx in self.error_history[-10:]
            ],
            'error_frequency': {
                pattern: len(frequencies)
                for pattern, frequencies in self.error_frequency.items()
            }
        }

    def get_error_trends(self, hours: int = 24) -> Dict[str, Any]:
        """エラートレンド分析"""
        cutoff_time = time.time() - (hours * 3600)
        recent_errors = [
            ctx for ctx in self.error_history
            if ctx.timestamp >= cutoff_time
        ]
        
        # カテゴリ別トレンド
        category_trends = {}
        for category in ErrorCategory:
            category_errors = [
                ctx for ctx in recent_errors
                if ctx.category == category
            ]
            category_trends[category.value] = len(category_errors)
        
        # 時間別トレンド
        hourly_trends = {}
        for hour in range(hours):
            hour_start = cutoff_time + (hour * 3600)
            hour_end = hour_start + 3600
            hour_errors = [
                ctx for ctx in recent_errors
                if hour_start <= ctx.timestamp < hour_end
            ]
            hourly_trends[f"hour_{hour}"] = len(hour_errors)
        
        return {
            'analysis_period_hours': hours,
            'total_errors': len(recent_errors),
            'category_trends': category_trends,
            'hourly_trends': hourly_trends,
            'most_common_error_type': self._get_most_common_error_type(recent_errors),
            'most_affected_component': self._get_most_affected_component(recent_errors)
        }

    def _get_most_common_error_type(self, errors: List[ErrorContext]) -> Optional[str]:
        """最も一般的なエラータイプ取得"""
        if not errors:
            return None
        
        error_type_counts = {}
        for error in errors:
            error_type_counts[error.error_type] = error_type_counts.get(error.error_type, 0) + 1
        
        return max(error_type_counts, key=error_type_counts.get)

    def _get_most_affected_component(self, errors: List[ErrorContext]) -> Optional[str]:
        """最も影響を受けたコンポーネント取得"""
        if not errors:
            return None
        
        component_counts = {}
        for error in errors:
            component_counts[error.component] = component_counts.get(error.component, 0) + 1
        
        return max(component_counts, key=component_counts.get)


# グローバルエラーハンドラインスタンス
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """グローバルエラーハンドラインスタンス取得"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler