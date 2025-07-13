"""
AIDE システム耐障害性・回復機能

エラーハンドリング、サーキットブレーカー、リトライ、フォルバック機能
"""

from .error_handler import (
    ErrorHandler,
    ErrorCategory,
    ErrorSeverity,
    ErrorContext,
    get_error_handler
)

from .circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerConfig
)

from .retry_manager import (
    RetryManager,
    RetryPolicy,
    BackoffStrategy,
    RetryResult
)

from .fallback_system import (
    FallbackSystem,
    FallbackStrategy,
    FallbackResult
)

__all__ = [
    'ErrorHandler',
    'ErrorCategory', 
    'ErrorSeverity',
    'ErrorContext',
    'get_error_handler',
    'CircuitBreaker',
    'CircuitState',
    'CircuitBreakerConfig',
    'RetryManager',
    'RetryPolicy',
    'BackoffStrategy',
    'RetryResult',
    'FallbackSystem',
    'FallbackStrategy',
    'FallbackResult'
]