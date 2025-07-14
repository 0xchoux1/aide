"""
AIDE デフォルト設定定義

各モジュールのデフォルト設定値とプロファイルを定義
"""

from typing import Dict, Any, List
from enum import Enum


class ConfigProfile(Enum):
    """設定プロファイル"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"
    SAFE_MODE = "safe_mode"


class LogLevel(Enum):
    """ログレベル"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# 基本システム設定
DEFAULT_CONFIG = {
    "system": {
        "version": "3.2.0",
        "environment": "development",
        "debug_mode": True,
        "log_level": LogLevel.INFO.value,
        "max_workers": 4,
        "timeout_seconds": 300,
        "auto_save": True,
        "backup_enabled": True,
        "backup_retention_days": 30
    },
    
    "paths": {
        "project_root": ".",
        "src_directory": "src",
        "tests_directory": "tests",
        "logs_directory": "logs",
        "backups_directory": "backups",
        "config_directory": "config",
        "cache_directory": ".aide_cache",
        "temp_directory": "/tmp/aide"
    },
    
    "claude_integration": {
        "enabled": True,
        "model": "claude-sonnet-4",
        "max_tokens": 4000,
        "temperature": 0.1,
        "timeout_seconds": 60,
        "retry_attempts": 3,
        "retry_delay": 1.0,
        "rate_limit_requests_per_minute": 30
    },
    
    "rag_system": {
        "enabled": True,
        "knowledge_base_path": "knowledge_base",
        "max_context_length": 8000,
        "similarity_threshold": 0.7,
        "max_retrieval_items": 10,
        "update_interval_hours": 24,
        "auto_learning": True
    },
    
    "remote_operations": {
        "enabled": True,
        "max_connections": 10,
        "connection_timeout": 30,
        "idle_timeout": 300,
        "retry_attempts": 3,
        "retry_delay": 2,
        "tool_timeout": 60,
        "safe_mode": True,
        "max_retries": 3,
        "auto_collect_basic_info": True,
        "auto_analyze_logs": True,
        "max_concurrent_servers": 5,
        "servers_config_path": "config/servers.yaml",
        "agent_name": "aide_remote_agent",
        "agent_role": "リモートシステム管理者",
        "agent_goal": "リモートサーバーの調査と問題解決"
    }
}

# 環境別設定
ENVIRONMENT_DEFAULTS = {
    ConfigProfile.DEVELOPMENT.value: {
        "system": {
            "debug_mode": True,
            "log_level": LogLevel.DEBUG.value,
            "auto_save": True
        },
        "diagnostics": {
            "run_interval_minutes": 30,
            "detailed_analysis": True
        },
        "improvement_engine": {
            "aggressive_optimization": False,
            "human_approval_required": True
        }
    },
    
    ConfigProfile.PRODUCTION.value: {
        "system": {
            "debug_mode": False,
            "log_level": LogLevel.INFO.value,
            "auto_save": True
        },
        "diagnostics": {
            "run_interval_minutes": 60,
            "detailed_analysis": False
        },
        "improvement_engine": {
            "aggressive_optimization": True,
            "human_approval_required": True
        }
    },
    
    ConfigProfile.TESTING.value: {
        "system": {
            "debug_mode": True,
            "log_level": LogLevel.WARNING.value,
            "auto_save": False
        },
        "diagnostics": {
            "run_interval_minutes": 5,
            "detailed_analysis": True
        },
        "improvement_engine": {
            "aggressive_optimization": False,
            "human_approval_required": False
        }
    },
    
    ConfigProfile.SAFE_MODE.value: {
        "system": {
            "debug_mode": True,
            "log_level": LogLevel.INFO.value
        },
        "diagnostics": {
            "run_interval_minutes": 120,
            "detailed_analysis": False
        },
        "improvement_engine": {
            "aggressive_optimization": False,
            "human_approval_required": True,
            "dry_run_only": True
        },
        "autonomous_implementation": {
            "enabled": False
        }
    }
}

# パフォーマンス設定
PERFORMANCE_DEFAULTS = {
    "diagnostics": {
        "run_interval_minutes": 60,
        "max_history_items": 1000,
        "cleanup_interval_hours": 24,
        "memory_threshold_percent": 80,
        "cpu_threshold_percent": 70,
        "disk_threshold_percent": 85,
        "response_time_threshold_seconds": 2.0,
        "parallel_diagnostics": True,
        "cache_results": True,
        "cache_ttl_minutes": 15
    },
    
    "improvement_engine": {
        "max_opportunities_per_cycle": 10,
        "priority_calculation_threads": 2,
        "roadmap_generation_timeout": 120,
        "ai_analysis_timeout": 60,
        "batch_processing_enabled": True,
        "cache_improvement_plans": True
    },
    
    "autonomous_implementation": {
        "max_concurrent_implementations": 3,
        "implementation_timeout_minutes": 30,
        "code_generation_timeout": 180,
        "test_execution_timeout": 300,
        "rollback_timeout": 60,
        "backup_before_implementation": True
    },
    
    "quality_assurance": {
        "safety_check_timeout": 30,
        "parallel_safety_checks": True,
        "approval_timeout_hours": 24,
        "quality_metrics_cache_minutes": 10
    }
}

# 品質設定
QUALITY_DEFAULTS = {
    "code_quality": {
        "min_test_coverage_percent": 80,
        "max_complexity_score": 10,
        "max_function_length": 50,
        "max_class_length": 500,
        "docstring_required": True,
        "type_hints_required": True,
        "lint_enabled": True,
        "format_check_enabled": True
    },
    
    "improvement_quality": {
        "min_impact_score": 30.0,
        "max_risk_score": 70.0,
        "min_roi_threshold": 50.0,
        "require_justification": True,
        "require_test_plan": True,
        "require_rollback_plan": True
    },
    
    "safety_checks": {
        "syntax_validation": True,
        "import_validation": True,
        "security_scan": True,
        "dependency_check": True,
        "permission_check": True,
        "data_validation": True,
        "api_compatibility_check": True
    }
}

# セキュリティ設定
SECURITY_DEFAULTS = {
    "access_control": {
        "require_authentication": False,  # 開発段階では無効
        "session_timeout_minutes": 120,
        "max_login_attempts": 3,
        "lockout_duration_minutes": 15
    },
    
    "data_protection": {
        "encrypt_sensitive_data": True,
        "secure_temp_files": True,
        "auto_cleanup_temp": True,
        "log_sensitive_data": False,
        "backup_encryption": True
    },
    
    "execution_safety": {
        "sandbox_enabled": True,
        "restricted_imports": [
            "os.system",
            "subprocess.run",
            "eval",
            "exec"
        ],
        "allowed_file_extensions": [
            ".py", ".yaml", ".yml", ".json", ".txt", ".md"
        ],
        "max_file_size_mb": 10,
        "network_access_restricted": True
    },
    
    "audit": {
        "log_all_actions": True,
        "log_file_changes": True,
        "log_system_access": True,
        "retention_days": 90,
        "real_time_monitoring": True
    }
}

# 機能フラグ
FEATURE_FLAGS = {
    "ai_enhanced_analysis": True,
    "auto_implementation": True,
    "advanced_diagnostics": True,
    "real_time_monitoring": True,
    "experimental_features": False,
    "beta_optimizations": False,
    "debug_features": True
}

# 統合設定プロファイル
CONFIG_PROFILES = {
    profile.value: {
        **DEFAULT_CONFIG,
        **ENVIRONMENT_DEFAULTS.get(profile.value, {}),
        "performance": PERFORMANCE_DEFAULTS,
        "quality": QUALITY_DEFAULTS,
        "security": SECURITY_DEFAULTS,
        "features": FEATURE_FLAGS
    }
    for profile in ConfigProfile
}

# 設定キー定数
class ConfigKeys:
    """設定キー定数クラス"""
    
    # システム設定
    SYSTEM_VERSION = "system.version"
    SYSTEM_ENVIRONMENT = "system.environment"
    SYSTEM_DEBUG_MODE = "system.debug_mode"
    SYSTEM_LOG_LEVEL = "system.log_level"
    SYSTEM_MAX_WORKERS = "system.max_workers"
    
    # パス設定
    PATHS_PROJECT_ROOT = "paths.project_root"
    PATHS_SRC_DIR = "paths.src_directory"
    PATHS_TESTS_DIR = "paths.tests_directory"
    PATHS_LOGS_DIR = "paths.logs_directory"
    
    # Claude統合
    CLAUDE_ENABLED = "claude_integration.enabled"
    CLAUDE_MODEL = "claude_integration.model"
    CLAUDE_MAX_TOKENS = "claude_integration.max_tokens"
    CLAUDE_TIMEOUT = "claude_integration.timeout_seconds"
    
    # 診断設定
    DIAGNOSTICS_INTERVAL = "diagnostics.run_interval_minutes"
    DIAGNOSTICS_MEMORY_THRESHOLD = "diagnostics.memory_threshold_percent"
    DIAGNOSTICS_CPU_THRESHOLD = "diagnostics.cpu_threshold_percent"
    
    # 改善エンジン
    IMPROVEMENT_MAX_OPPORTUNITIES = "improvement_engine.max_opportunities_per_cycle"
    IMPROVEMENT_HUMAN_APPROVAL = "improvement_engine.human_approval_required"
    IMPROVEMENT_AGGRESSIVE = "improvement_engine.aggressive_optimization"
    
    # 品質保証
    QUALITY_MIN_COVERAGE = "quality.code_quality.min_test_coverage_percent"
    QUALITY_MAX_COMPLEXITY = "quality.code_quality.max_complexity_score"
    QUALITY_MIN_IMPACT = "quality.improvement_quality.min_impact_score"
    
    # セキュリティ
    SECURITY_SANDBOX_ENABLED = "security.execution_safety.sandbox_enabled"
    SECURITY_ENCRYPT_DATA = "security.data_protection.encrypt_sensitive_data"
    SECURITY_AUDIT_ENABLED = "security.audit.log_all_actions"
    
    # リモート操作
    REMOTE_ENABLED = "remote_operations.enabled"
    REMOTE_MAX_CONNECTIONS = "remote_operations.max_connections"
    REMOTE_CONNECTION_TIMEOUT = "remote_operations.connection_timeout"
    REMOTE_SAFE_MODE = "remote_operations.safe_mode"
    REMOTE_MAX_CONCURRENT_SERVERS = "remote_operations.max_concurrent_servers"
    REMOTE_SERVERS_CONFIG = "remote_operations.servers_config_path"


# バリデーションルール
VALIDATION_RULES = {
    "system.max_workers": {
        "type": int,
        "min": 1,
        "max": 16
    },
    "system.timeout_seconds": {
        "type": int,
        "min": 10,
        "max": 3600
    },
    "claude_integration.max_tokens": {
        "type": int,
        "min": 100,
        "max": 8000
    },
    "claude_integration.temperature": {
        "type": float,
        "min": 0.0,
        "max": 1.0
    },
    "diagnostics.memory_threshold_percent": {
        "type": [int, float],
        "min": 50,
        "max": 95
    },
    "quality.code_quality.min_test_coverage_percent": {
        "type": [int, float],
        "min": 0,
        "max": 100
    },
    "improvement_engine.max_opportunities_per_cycle": {
        "type": int,
        "min": 1,
        "max": 50
    },
    "remote_operations.max_connections": {
        "type": int,
        "min": 1,
        "max": 100
    },
    "remote_operations.connection_timeout": {
        "type": int,
        "min": 5,
        "max": 300
    },
    "remote_operations.max_concurrent_servers": {
        "type": int,
        "min": 1,
        "max": 50
    }
}