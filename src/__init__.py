"""
AIDE (Autonomous Intelligent Development Environment)

自律学習型AIアシスタント
"""

__version__ = "3.3.0"
__author__ = "AIDE Development Team"
__description__ = "Autonomous Intelligent Development Environment"

# 基本設定とロギング
from .config import get_config_manager
from .logging import get_logger, get_audit_logger

# 利用可能な場合のみインポート (オプショナル)
def _safe_import(module_path, function_name):
    """安全なインポート関数"""
    try:
        module = __import__(module_path, fromlist=[function_name])
        return getattr(module, function_name, None)
    except ImportError:
        return None

# オプショナルインポート
get_system_optimizer = _safe_import('src.optimization.system_optimizer', 'get_system_optimizer')
get_enhanced_monitor = _safe_import('src.dashboard.enhanced_monitor', 'get_enhanced_monitor')
get_metrics_collector = _safe_import('src.dashboard.metrics_collector', 'get_metrics_collector')

__all__ = [
    # Core
    'get_config_manager',
    'get_logger', 
    'get_audit_logger',
    
    # Optional (may be None if modules not available)
    'get_system_optimizer',
    'get_enhanced_monitor',
    'get_metrics_collector',
]