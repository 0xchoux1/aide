"""
AIDE ログシステム

構造化ログ、監査ログ、パフォーマンス追跡を提供
"""

import logging

from .log_manager import (
    LogManager
)

from .audit_logger import (
    AuditLogger,
    AuditEvent,
    AuditEventType
)

# グローバルロガー管理
_global_log_manager = None

def get_logger(name: str = None) -> logging.Logger:
    """ロガー取得"""
    return logging.getLogger(name or __name__)

def get_log_manager():
    """グローバルログマネージャー取得"""
    global _global_log_manager
    if _global_log_manager is None:
        from ..config import get_config_manager
        _global_log_manager = LogManager(get_config_manager())
    return _global_log_manager

def get_audit_logger():
    """監査ロガー取得"""
    return AuditLogger()

__all__ = [
    'LogManager',
    'AuditLogger',
    'AuditEvent', 
    'AuditEventType',
    'get_logger',
    'get_log_manager',
    'get_audit_logger'
]