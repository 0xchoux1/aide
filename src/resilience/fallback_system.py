"""
AIDE フォルバックシステム

メイン処理が失敗した場合の代替処理機能
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import functools

from ..config import get_config_manager
from ..logging import get_logger


class FallbackStrategy(Enum):
    """フォルバック戦略"""
    RETURN_DEFAULT = "return_default"
    CALL_FUNCTION = "call_function"
    RAISE_EXCEPTION = "raise_exception"
    CACHE_RESULT = "cache_result"
    DEGRADED_SERVICE = "degraded_service"


@dataclass
class FallbackConfig:
    """フォルバック設定"""
    strategy: FallbackStrategy
    default_value: Any = None
    fallback_function: Optional[Callable] = None
    fallback_exception: Optional[Exception] = None
    cache_key: Optional[str] = None
    cache_ttl: int = 300  # 5分
    enable_logging: bool = True
    
    def __post_init__(self):
        if self.strategy == FallbackStrategy.RETURN_DEFAULT and self.default_value is None:
            raise ValueError("default_value is required for RETURN_DEFAULT strategy")
        elif self.strategy == FallbackStrategy.CALL_FUNCTION and self.fallback_function is None:
            raise ValueError("fallback_function is required for CALL_FUNCTION strategy")
        elif self.strategy == FallbackStrategy.RAISE_EXCEPTION and self.fallback_exception is None:
            raise ValueError("fallback_exception is required for RAISE_EXCEPTION strategy")


@dataclass
class FallbackResult:
    """フォルバック結果"""
    success: bool
    strategy_used: FallbackStrategy
    result: Any = None
    exception: Optional[Exception] = None
    execution_time: float = 0.0
    from_cache: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['strategy_used'] = self.strategy_used.value
        data['exception_type'] = type(self.exception).__name__ if self.exception else None
        data['exception_message'] = str(self.exception) if self.exception else None
        # 実際のオブジェクトは除外
        del data['result']
        del data['exception']
        return data


class FallbackCache:
    """フォルバック用キャッシュ"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger(__name__)

    def get(self, key: str) -> Optional[Any]:
        """キャッシュ取得"""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() < entry['expires_at']:
                self.logger.debug(f"フォルバックキャッシュヒット: {key}")
                return entry['value']
            else:
                # 期限切れエントリ削除
                del self.cache[key]
                self.logger.debug(f"フォルバックキャッシュ期限切れ: {key}")
        
        return None

    def set(self, key: str, value: Any, ttl: int = 300):
        """キャッシュ設定"""
        expires_at = time.time() + ttl
        self.cache[key] = {
            'value': value,
            'expires_at': expires_at,
            'created_at': time.time()
        }
        self.logger.debug(f"フォルバックキャッシュ設定: {key} (TTL: {ttl}秒)")

    def clear(self):
        """キャッシュクリア"""
        cleared_count = len(self.cache)
        self.cache.clear()
        self.logger.info(f"フォルバックキャッシュクリア: {cleared_count}エントリ")

    def cleanup_expired(self):
        """期限切れエントリクリーンアップ"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time >= entry['expires_at']
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            self.logger.debug(f"期限切れフォルバックキャッシュクリーンアップ: {len(expired_keys)}エントリ")

    def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計取得"""
        return {
            'total_entries': len(self.cache),
            'entries': list(self.cache.keys())
        }


class FallbackSystem:
    """フォルバックシステム"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger(__name__)
        
        # フォルバックキャッシュ
        self.cache = FallbackCache()
        
        # フォルバック統計
        self.fallback_stats = {
            'total_fallbacks': 0,
            'successful_fallbacks': 0,
            'failed_fallbacks': 0,
            'strategy_usage': {strategy.value: 0 for strategy in FallbackStrategy}
        }
        
        # 登録済みフォルバック設定
        self.named_configs: Dict[str, FallbackConfig] = {}
        
        # デフォルト設定
        self._initialize_default_configs()

    def _initialize_default_configs(self):
        """デフォルト設定初期化"""
        self.named_configs.update({
            'return_empty_list': FallbackConfig(
                strategy=FallbackStrategy.RETURN_DEFAULT,
                default_value=[]
            ),
            'return_empty_dict': FallbackConfig(
                strategy=FallbackStrategy.RETURN_DEFAULT,
                default_value={}
            ),
            'return_none': FallbackConfig(
                strategy=FallbackStrategy.RETURN_DEFAULT,
                default_value=None
            ),
            'return_false': FallbackConfig(
                strategy=FallbackStrategy.RETURN_DEFAULT,
                default_value=False
            ),
            'return_zero': FallbackConfig(
                strategy=FallbackStrategy.RETURN_DEFAULT,
                default_value=0
            )
        })

    def execute_fallback(self, config: FallbackConfig, 
                        original_exception: Exception = None,
                        context: Dict[str, Any] = None) -> FallbackResult:
        """フォルバック実行"""
        start_time = time.perf_counter()
        context = context or {}
        
        self.fallback_stats['total_fallbacks'] += 1
        self.fallback_stats['strategy_usage'][config.strategy.value] += 1
        
        if config.enable_logging:
            self.logger.info(
                f"フォルバック実行: {config.strategy.value} - "
                f"元エラー: {type(original_exception).__name__ if original_exception else 'Unknown'}"
            )
        
        try:
            if config.strategy == FallbackStrategy.RETURN_DEFAULT:
                result = self._execute_return_default(config)
                
            elif config.strategy == FallbackStrategy.CALL_FUNCTION:
                result = self._execute_call_function(config, original_exception, context)
                
            elif config.strategy == FallbackStrategy.RAISE_EXCEPTION:
                result = self._execute_raise_exception(config)
                
            elif config.strategy == FallbackStrategy.CACHE_RESULT:
                result = self._execute_cache_result(config, context)
                
            elif config.strategy == FallbackStrategy.DEGRADED_SERVICE:
                result = self._execute_degraded_service(config, original_exception, context)
                
            else:
                raise ValueError(f"Unknown fallback strategy: {config.strategy}")
            
            execution_time = (time.perf_counter() - start_time)
            result.execution_time = execution_time
            
            if result.success:
                self.fallback_stats['successful_fallbacks'] += 1
            else:
                self.fallback_stats['failed_fallbacks'] += 1
            
            return result
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time)
            self.fallback_stats['failed_fallbacks'] += 1
            
            self.logger.error(f"フォルバック実行エラー: {config.strategy.value} - {str(e)}")
            
            return FallbackResult(
                success=False,
                strategy_used=config.strategy,
                exception=e,
                execution_time=execution_time
            )

    async def execute_fallback_async(self, config: FallbackConfig, 
                                   original_exception: Exception = None,
                                   context: Dict[str, Any] = None) -> FallbackResult:
        """非同期フォルバック実行"""
        start_time = time.perf_counter()
        context = context or {}
        
        self.fallback_stats['total_fallbacks'] += 1
        self.fallback_stats['strategy_usage'][config.strategy.value] += 1
        
        if config.enable_logging:
            self.logger.info(
                f"非同期フォルバック実行: {config.strategy.value} - "
                f"元エラー: {type(original_exception).__name__ if original_exception else 'Unknown'}"
            )
        
        try:
            if config.strategy == FallbackStrategy.RETURN_DEFAULT:
                result = self._execute_return_default(config)
                
            elif config.strategy == FallbackStrategy.CALL_FUNCTION:
                result = await self._execute_call_function_async(config, original_exception, context)
                
            elif config.strategy == FallbackStrategy.RAISE_EXCEPTION:
                result = self._execute_raise_exception(config)
                
            elif config.strategy == FallbackStrategy.CACHE_RESULT:
                result = self._execute_cache_result(config, context)
                
            elif config.strategy == FallbackStrategy.DEGRADED_SERVICE:
                result = await self._execute_degraded_service_async(config, original_exception, context)
                
            else:
                raise ValueError(f"Unknown fallback strategy: {config.strategy}")
            
            execution_time = (time.perf_counter() - start_time)
            result.execution_time = execution_time
            
            if result.success:
                self.fallback_stats['successful_fallbacks'] += 1
            else:
                self.fallback_stats['failed_fallbacks'] += 1
            
            return result
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time)
            self.fallback_stats['failed_fallbacks'] += 1
            
            self.logger.error(f"非同期フォルバック実行エラー: {config.strategy.value} - {str(e)}")
            
            return FallbackResult(
                success=False,
                strategy_used=config.strategy,
                exception=e,
                execution_time=execution_time
            )

    def _execute_return_default(self, config: FallbackConfig) -> FallbackResult:
        """デフォルト値返却実行"""
        return FallbackResult(
            success=True,
            strategy_used=config.strategy,
            result=config.default_value
        )

    def _execute_call_function(self, config: FallbackConfig, 
                             original_exception: Exception = None,
                             context: Dict[str, Any] = None) -> FallbackResult:
        """フォルバック関数呼び出し実行"""
        try:
            # コンテキスト情報を関数に渡す
            if config.fallback_function:
                result = config.fallback_function(original_exception, context)
                
                return FallbackResult(
                    success=True,
                    strategy_used=config.strategy,
                    result=result
                )
            else:
                raise ValueError("fallback_function is not set")
                
        except Exception as e:
            return FallbackResult(
                success=False,
                strategy_used=config.strategy,
                exception=e
            )

    async def _execute_call_function_async(self, config: FallbackConfig, 
                                         original_exception: Exception = None,
                                         context: Dict[str, Any] = None) -> FallbackResult:
        """非同期フォルバック関数呼び出し実行"""
        try:
            if config.fallback_function:
                if asyncio.iscoroutinefunction(config.fallback_function):
                    result = await config.fallback_function(original_exception, context)
                else:
                    result = config.fallback_function(original_exception, context)
                
                return FallbackResult(
                    success=True,
                    strategy_used=config.strategy,
                    result=result
                )
            else:
                raise ValueError("fallback_function is not set")
                
        except Exception as e:
            return FallbackResult(
                success=False,
                strategy_used=config.strategy,
                exception=e
            )

    def _execute_raise_exception(self, config: FallbackConfig) -> FallbackResult:
        """例外発生実行"""
        if config.fallback_exception:
            raise config.fallback_exception
        else:
            raise ValueError("fallback_exception is not set")

    def _execute_cache_result(self, config: FallbackConfig, 
                            context: Dict[str, Any] = None) -> FallbackResult:
        """キャッシュ結果実行"""
        if not config.cache_key:
            raise ValueError("cache_key is required for CACHE_RESULT strategy")
        
        cached_result = self.cache.get(config.cache_key)
        
        if cached_result is not None:
            return FallbackResult(
                success=True,
                strategy_used=config.strategy,
                result=cached_result,
                from_cache=True
            )
        else:
            return FallbackResult(
                success=False,
                strategy_used=config.strategy,
                exception=Exception(f"No cached result found for key: {config.cache_key}")
            )

    def _execute_degraded_service(self, config: FallbackConfig, 
                                original_exception: Exception = None,
                                context: Dict[str, Any] = None) -> FallbackResult:
        """劣化サービス実行"""
        # 劣化サービスの簡易実装
        degraded_result = {
            'status': 'degraded',
            'message': 'Service is running in degraded mode',
            'original_error': str(original_exception) if original_exception else None,
            'timestamp': time.time()
        }
        
        return FallbackResult(
            success=True,
            strategy_used=config.strategy,
            result=degraded_result
        )

    async def _execute_degraded_service_async(self, config: FallbackConfig, 
                                            original_exception: Exception = None,
                                            context: Dict[str, Any] = None) -> FallbackResult:
        """非同期劣化サービス実行"""
        # 非同期劣化サービスの簡易実装
        degraded_result = {
            'status': 'degraded',
            'message': 'Async service is running in degraded mode',
            'original_error': str(original_exception) if original_exception else None,
            'timestamp': time.time()
        }
        
        return FallbackResult(
            success=True,
            strategy_used=config.strategy,
            result=degraded_result
        )

    def with_fallback(self, func: Callable, config: FallbackConfig, 
                     context: Dict[str, Any] = None):
        """フォルバック付き関数実行"""
        try:
            return func()
        except Exception as e:
            self.logger.debug(f"メイン処理失敗、フォルバック実行: {func.__name__} - {type(e).__name__}")
            fallback_result = self.execute_fallback(config, e, context)
            
            if fallback_result.success:
                return fallback_result.result
            else:
                # フォルバックも失敗した場合は元の例外を再発生
                raise e

    async def with_fallback_async(self, func: Callable, config: FallbackConfig, 
                                 context: Dict[str, Any] = None):
        """非同期フォルバック付き関数実行"""
        try:
            if asyncio.iscoroutinefunction(func):
                return await func()
            else:
                return func()
        except Exception as e:
            self.logger.debug(f"非同期メイン処理失敗、フォルバック実行: {func.__name__} - {type(e).__name__}")
            fallback_result = await self.execute_fallback_async(config, e, context)
            
            if fallback_result.success:
                return fallback_result.result
            else:
                # フォルバックも失敗した場合は元の例外を再発生
                raise e

    def register_config(self, name: str, config: FallbackConfig):
        """名前付き設定登録"""
        self.named_configs[name] = config
        self.logger.info(f"フォルバック設定登録: {name}")

    def get_config(self, name: str) -> Optional[FallbackConfig]:
        """名前付き設定取得"""
        return self.named_configs.get(name)

    def with_named_fallback(self, func: Callable, config_name: str, 
                           context: Dict[str, Any] = None):
        """名前付き設定でフォルバック実行"""
        config = self.get_config(config_name)
        if not config:
            raise ValueError(f"Unknown fallback config: {config_name}")
        
        return self.with_fallback(func, config, context)

    async def with_named_fallback_async(self, func: Callable, config_name: str, 
                                       context: Dict[str, Any] = None):
        """名前付き設定で非同期フォルバック実行"""
        config = self.get_config(config_name)
        if not config:
            raise ValueError(f"Unknown fallback config: {config_name}")
        
        return await self.with_fallback_async(func, config, context)

    def cache_result(self, key: str, value: Any, ttl: int = None):
        """結果キャッシュ"""
        ttl = ttl or 300
        self.cache.set(key, value, ttl)

    def get_statistics(self) -> Dict[str, Any]:
        """フォルバック統計取得"""
        total_fallbacks = self.fallback_stats['total_fallbacks']
        success_rate = (
            self.fallback_stats['successful_fallbacks'] / total_fallbacks * 100
            if total_fallbacks > 0 else 0
        )
        
        return {
            'fallback_statistics': self.fallback_stats.copy(),
            'success_rate': success_rate,
            'registered_configs': list(self.named_configs.keys()),
            'cache_stats': self.cache.get_stats()
        }

    def clear_statistics(self):
        """統計クリア"""
        self.fallback_stats = {
            'total_fallbacks': 0,
            'successful_fallbacks': 0,
            'failed_fallbacks': 0,
            'strategy_usage': {strategy.value: 0 for strategy in FallbackStrategy}
        }
        self.logger.info("フォルバック統計クリア")

    def clear_cache(self):
        """キャッシュクリア"""
        self.cache.clear()


# グローバルフォルバックシステムインスタンス
_global_fallback_system: Optional[FallbackSystem] = None


def get_fallback_system() -> FallbackSystem:
    """グローバルフォルバックシステムインスタンス取得"""
    global _global_fallback_system
    if _global_fallback_system is None:
        _global_fallback_system = FallbackSystem()
    return _global_fallback_system


# 便利デコレータ
def fallback(config: FallbackConfig = None, config_name: str = None):
    """フォルバックデコレータ"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                system = get_fallback_system()
                
                async def target_func():
                    return await func(*args, **kwargs)
                
                if config_name:
                    return await system.with_named_fallback_async(target_func, config_name)
                elif config:
                    return await system.with_fallback_async(target_func, config)
                else:
                    raise ValueError("Either config or config_name must be provided")
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                system = get_fallback_system()
                
                def target_func():
                    return func(*args, **kwargs)
                
                if config_name:
                    return system.with_named_fallback(target_func, config_name)
                elif config:
                    return system.with_fallback(target_func, config)
                else:
                    raise ValueError("Either config or config_name must be provided")
            
            return sync_wrapper
    
    return decorator


def fallback_to_default(default_value: Any):
    """デフォルト値フォルバックデコレータ"""
    config = FallbackConfig(
        strategy=FallbackStrategy.RETURN_DEFAULT,
        default_value=default_value
    )
    return fallback(config)