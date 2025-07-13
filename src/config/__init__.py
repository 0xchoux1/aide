"""
AIDE設定管理システム

システム設定、ユーザー設定、環境設定を統合管理
"""

from .config_manager import (
    ConfigManager,
    ConfigValidator,
    ConfigLoader,
    ConfigKey,
    ConfigError,
    ValidationError
)

from .defaults import (
    DEFAULT_CONFIG,
    ENVIRONMENT_DEFAULTS,
    PERFORMANCE_DEFAULTS,
    QUALITY_DEFAULTS,
    SECURITY_DEFAULTS,
    ConfigProfile
)

# グローバル設定管理インスタンス
_global_config_manager = None

def get_config_manager(config_dir=None):
    """グローバル設定管理インスタンス取得"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager(config_dir)
    return _global_config_manager

def set_config_manager(config_manager):
    """グローバル設定管理インスタンス設定"""
    global _global_config_manager
    _global_config_manager = config_manager

__all__ = [
    'ConfigManager',
    'ConfigValidator', 
    'ConfigLoader',
    'ConfigKey',
    'ConfigError',
    'ValidationError',
    'get_config_manager',
    'set_config_manager',
    'DEFAULT_CONFIG',
    'ENVIRONMENT_DEFAULTS',
    'PERFORMANCE_DEFAULTS',
    'QUALITY_DEFAULTS',
    'SECURITY_DEFAULTS',
    'ConfigProfile'
]