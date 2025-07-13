"""
AIDE 監査ログシステム

セキュリティ監査、操作追跡、コンプライアンス対応
"""

import json
import hashlib
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading
import uuid

from .log_manager import LogHandler, LogFormatter, LogFormat, get_log_manager


class AuditEventType(Enum):
    """監査イベントタイプ"""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    CONFIG_CHANGE = "config_change"
    FILE_ACCESS = "file_access"
    FILE_MODIFY = "file_modify"
    FILE_DELETE = "file_delete"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    IMPROVEMENT_START = "improvement_start"
    IMPROVEMENT_COMPLETE = "improvement_complete"
    DIAGNOSTIC_RUN = "diagnostic_run"
    SECURITY_VIOLATION = "security_violation"
    ERROR_OCCURRED = "error_occurred"
    PERMISSION_DENIED = "permission_denied"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"


class AuditSeverity(Enum):
    """監査重要度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """監査イベント"""
    event_id: str
    timestamp: str
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    session_id: Optional[str]
    source_ip: Optional[str]
    resource: Optional[str]
    action: str
    result: str  # success, failure, error
    details: Dict[str, Any]
    
    # セキュリティ用ハッシュ
    checksum: Optional[str] = None
    
    def __post_init__(self):
        """チェックサム計算"""
        if self.checksum is None:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """イベントのチェックサム計算"""
        # チェックサム対象データ
        data = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "action": self.action,
            "result": self.result
        }
        
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        return data
    
    def to_json(self) -> str:
        """JSON形式に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)
    
    def verify_integrity(self) -> bool:
        """イベントの整合性検証"""
        expected_checksum = self._calculate_checksum()
        return self.checksum == expected_checksum


class AuditLogFormatter(LogFormatter):
    """監査ログ専用フォーマッター"""
    
    def __init__(self, include_signature: bool = True):
        super().__init__(LogFormat.JSON, include_colors=False)
        self.include_signature = include_signature
    
    def format_audit_event(self, event: AuditEvent) -> str:
        """監査イベントをフォーマット"""
        event_dict = event.to_dict()
        
        # タイムスタンプの正規化
        event_dict['@timestamp'] = event.timestamp
        event_dict['@version'] = '1'
        event_dict['@type'] = 'audit'
        
        if self.include_signature:
            event_dict['@signature'] = event.checksum
        
        return json.dumps(event_dict, ensure_ascii=False, separators=(',', ':'))


class AuditLogHandler(LogHandler):
    """監査ログ専用ハンドラー"""
    
    def __init__(self, file_path: Union[str, Path], max_size: int = 50 * 1024 * 1024):
        formatter = AuditLogFormatter()
        super().__init__(formatter)
        
        self.file_path = Path(file_path)
        self.max_size = max_size
        self.lock = threading.Lock()
        
        # ディレクトリ作成
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def emit(self, formatted_message: str):
        """監査ログ出力"""
        with self.lock:
            with open(self.file_path, 'a', encoding='utf-8') as f:
                f.write(formatted_message + '\n')
                f.flush()
            
            # ファイルサイズチェック
            if self.file_path.stat().st_size > self.max_size:
                self._archive_log()
    
    def _archive_log(self):
        """ログファイルアーカイブ"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.file_path.with_suffix(f'.{timestamp}.log')
        self.file_path.rename(archive_path)


class AuditLogger:
    """監査ログクラス"""
    
    def __init__(self, audit_file: Optional[Union[str, Path]] = None):
        self.session_id = str(uuid.uuid4())
        self.user_id = None
        self.source_ip = "127.0.0.1"  # デフォルト
        
        # 監査ログハンドラー設定
        if audit_file:
            self.audit_handler = AuditLogHandler(audit_file)
        else:
            from ..config import get_config_manager
            config = get_config_manager()
            log_dir = Path(config.get("paths.logs_directory", "logs"))
            self.audit_handler = AuditLogHandler(log_dir / "audit.log")
        
        # 通常ログも併用
        self.logger = get_log_manager().get_logger("audit")
        
        # セッション開始イベント
        self._log_system_event(AuditEventType.SYSTEM_START, "監査セッション開始")
    
    def set_user_context(self, user_id: str, source_ip: Optional[str] = None):
        """ユーザーコンテキスト設定"""
        self.user_id = user_id
        if source_ip:
            self.source_ip = source_ip
    
    def log_event(self, 
                  event_type: AuditEventType,
                  action: str,
                  result: str = "success",
                  severity: AuditSeverity = AuditSeverity.MEDIUM,
                  resource: Optional[str] = None,
                  **details) -> str:
        """監査イベントログ"""
        
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            severity=severity,
            user_id=self.user_id,
            session_id=self.session_id,
            source_ip=self.source_ip,
            resource=resource,
            action=action,
            result=result,
            details=details
        )
        
        # 監査ログ出力
        formatted = self.audit_handler.formatter.format_audit_event(event)
        self.audit_handler.emit(formatted)
        
        # 通常ログにも出力
        log_level = self._get_log_level(severity)
        self.logger.log(
            log_level,
            f"監査イベント: {action}",
            event_type=event_type.value,
            result=result,
            resource=resource,
            **details
        )
        
        return event.event_id
    
    def _get_log_level(self, severity: AuditSeverity):
        """重要度からログレベル決定"""
        from .log_manager import LogLevel
        mapping = {
            AuditSeverity.LOW: LogLevel.DEBUG,
            AuditSeverity.MEDIUM: LogLevel.INFO,
            AuditSeverity.HIGH: LogLevel.WARNING,
            AuditSeverity.CRITICAL: LogLevel.ERROR
        }
        return mapping.get(severity, LogLevel.INFO)
    
    # 便利メソッド
    def log_user_login(self, user_id: str, source_ip: str, success: bool = True):
        """ユーザーログイン記録"""
        self.set_user_context(user_id, source_ip)
        
        self.log_event(
            AuditEventType.USER_LOGIN,
            "ユーザーログイン",
            result="success" if success else "failure",
            severity=AuditSeverity.MEDIUM if success else AuditSeverity.HIGH,
            login_time=datetime.now().isoformat()
        )
    
    def log_user_logout(self):
        """ユーザーログアウト記録"""
        self.log_event(
            AuditEventType.USER_LOGOUT,
            "ユーザーログアウト",
            logout_time=datetime.now().isoformat()
        )
    
    def log_config_change(self, config_key: str, old_value: Any, new_value: Any):
        """設定変更記録"""
        self.log_event(
            AuditEventType.CONFIG_CHANGE,
            f"設定変更: {config_key}",
            severity=AuditSeverity.HIGH,
            resource=config_key,
            old_value=str(old_value),
            new_value=str(new_value)
        )
    
    def log_file_access(self, file_path: str, access_type: str = "read"):
        """ファイルアクセス記録"""
        event_type_map = {
            "read": AuditEventType.FILE_ACCESS,
            "write": AuditEventType.FILE_MODIFY,
            "delete": AuditEventType.FILE_DELETE
        }
        
        self.log_event(
            event_type_map.get(access_type, AuditEventType.FILE_ACCESS),
            f"ファイル{access_type}: {file_path}",
            severity=AuditSeverity.LOW if access_type == "read" else AuditSeverity.MEDIUM,
            resource=file_path,
            access_type=access_type
        )
    
    def log_improvement_start(self, improvement_id: str, improvement_type: str):
        """改善開始記録"""
        self.log_event(
            AuditEventType.IMPROVEMENT_START,
            f"改善開始: {improvement_type}",
            severity=AuditSeverity.MEDIUM,
            resource=improvement_id,
            improvement_type=improvement_type,
            start_time=datetime.now().isoformat()
        )
    
    def log_improvement_complete(self, improvement_id: str, success: bool, changes_made: List[str]):
        """改善完了記録"""
        self.log_event(
            AuditEventType.IMPROVEMENT_COMPLETE,
            f"改善完了: {improvement_id}",
            result="success" if success else "failure",
            severity=AuditSeverity.MEDIUM,
            resource=improvement_id,
            changes_made=changes_made,
            end_time=datetime.now().isoformat()
        )
    
    def log_diagnostic_run(self, diagnostic_type: str, component: str, results_summary: Dict[str, Any]):
        """診断実行記録"""
        self.log_event(
            AuditEventType.DIAGNOSTIC_RUN,
            f"診断実行: {diagnostic_type} - {component}",
            severity=AuditSeverity.LOW,
            resource=component,
            diagnostic_type=diagnostic_type,
            results_summary=results_summary
        )
    
    def log_security_violation(self, violation_type: str, details: Dict[str, Any]):
        """セキュリティ違反記録"""
        self.log_event(
            AuditEventType.SECURITY_VIOLATION,
            f"セキュリティ違反: {violation_type}",
            result="failure",
            severity=AuditSeverity.CRITICAL,
            violation_type=violation_type,
            **details
        )
    
    def log_permission_denied(self, resource: str, attempted_action: str):
        """権限拒否記録"""
        self.log_event(
            AuditEventType.PERMISSION_DENIED,
            f"権限拒否: {attempted_action}",
            result="failure",
            severity=AuditSeverity.HIGH,
            resource=resource,
            attempted_action=attempted_action
        )
    
    def log_data_export(self, data_type: str, export_format: str, record_count: int):
        """データエクスポート記録"""
        self.log_event(
            AuditEventType.DATA_EXPORT,
            f"データエクスポート: {data_type}",
            severity=AuditSeverity.HIGH,
            data_type=data_type,
            export_format=export_format,
            record_count=record_count,
            export_time=datetime.now().isoformat()
        )
    
    def _log_system_event(self, event_type: AuditEventType, action: str):
        """システムイベント記録"""
        self.log_event(
            event_type,
            action,
            severity=AuditSeverity.MEDIUM,
            system_event=True
        )
    
    def close_session(self):
        """監査セッション終了"""
        self._log_system_event(AuditEventType.SYSTEM_STOP, "監査セッション終了")


class SecurityAuditLogger(AuditLogger):
    """セキュリティ専用監査ログ"""
    
    def __init__(self, security_log_file: Optional[Union[str, Path]] = None):
        if security_log_file:
            super().__init__(security_log_file)
        else:
            from ..config import get_config_manager
            config = get_config_manager()
            log_dir = Path(config.get("paths.logs_directory", "logs"))
            super().__init__(log_dir / "security_audit.log")
    
    def log_failed_authentication(self, user_id: str, source_ip: str, reason: str):
        """認証失敗記録"""
        self.log_event(
            AuditEventType.USER_LOGIN,
            "認証失敗",
            result="failure",
            severity=AuditSeverity.HIGH,
            user_id=user_id,
            source_ip=source_ip,
            failure_reason=reason,
            timestamp=datetime.now().isoformat()
        )
    
    def log_suspicious_activity(self, activity_type: str, details: Dict[str, Any]):
        """不審活動記録"""
        self.log_security_violation(f"不審活動: {activity_type}", details)
    
    def log_privilege_escalation(self, user_id: str, from_role: str, to_role: str, authorized: bool):
        """権限昇格記録"""
        self.log_event(
            AuditEventType.SECURITY_VIOLATION if not authorized else AuditEventType.CONFIG_CHANGE,
            "権限昇格",
            result="success" if authorized else "violation",
            severity=AuditSeverity.CRITICAL if not authorized else AuditSeverity.HIGH,
            user_id=user_id,
            from_role=from_role,
            to_role=to_role,
            authorized=authorized
        )


# グローバル監査ログインスタンス
_global_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """グローバル監査ログ取得"""
    global _global_audit_logger
    if _global_audit_logger is None:
        _global_audit_logger = AuditLogger()
    return _global_audit_logger


def get_security_audit_logger() -> SecurityAuditLogger:
    """セキュリティ監査ログ取得"""
    return SecurityAuditLogger()