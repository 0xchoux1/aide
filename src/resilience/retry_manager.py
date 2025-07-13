"""
AIDE リトライ管理システム

指数バックオフ、ジッター、条件付きリトライの包括的実装
"""

import time
import random
import asyncio
from typing import Dict, List, Optional, Any, Callable, Type, Union
from dataclasses import dataclass, asdict
from enum import Enum
import functools

from ..config import get_config_manager
from ..logging import get_logger


class BackoffStrategy(Enum):
    """バックオフ戦略"""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"


@dataclass
class RetryPolicy:
    """リトライポリシー"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter: bool = True
    retry_on_exceptions: List[Type[Exception]] = None
    retry_on_result: Optional[Callable[[Any], bool]] = None
    stop_on_exceptions: List[Type[Exception]] = None
    
    def __post_init__(self):
        if self.retry_on_exceptions is None:
            self.retry_on_exceptions = [Exception]
        if self.stop_on_exceptions is None:
            self.stop_on_exceptions = []


@dataclass
class RetryAttempt:
    """リトライ試行情報"""
    attempt_number: int
    timestamp: float
    delay: float
    exception: Optional[Exception] = None
    success: bool = False
    result: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['exception_type'] = type(self.exception).__name__ if self.exception else None
        data['exception_message'] = str(self.exception) if self.exception else None
        # 実際の例外オブジェクトは除外
        del data['exception']
        del data['result']  # 結果も除外（大きい可能性があるため）
        return data


@dataclass
class RetryResult:
    """リトライ結果"""
    success: bool
    final_result: Any = None
    final_exception: Optional[Exception] = None
    total_attempts: int = 0
    total_duration: float = 0.0
    attempts: List[RetryAttempt] = None
    
    def __post_init__(self):
        if self.attempts is None:
            self.attempts = []
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['final_exception_type'] = type(self.final_exception).__name__ if self.final_exception else None
        data['final_exception_message'] = str(self.final_exception) if self.final_exception else None
        data['attempts'] = [attempt.to_dict() for attempt in self.attempts]
        # 実際のオブジェクトは除外
        del data['final_result']
        del data['final_exception']
        return data


class RetryManager:
    """リトライ管理システム"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger(__name__)
        
        # デフォルトポリシー
        self.default_policy = RetryPolicy(
            max_attempts=self.config_manager.get("retry.max_attempts", 3),
            base_delay=self.config_manager.get("retry.base_delay", 1.0),
            max_delay=self.config_manager.get("retry.max_delay", 60.0),
            backoff_strategy=BackoffStrategy(
                self.config_manager.get("retry.backoff_strategy", "exponential")
            ),
            jitter=self.config_manager.get("retry.jitter", True)
        )
        
        # リトライ統計
        self.retry_stats = {
            'total_retry_attempts': 0,
            'successful_retries': 0,
            'failed_retries': 0,
            'total_functions_retried': 0
        }
        
        # 登録済みリトライポリシー
        self.named_policies: Dict[str, RetryPolicy] = {}

    def retry(self, func: Callable, policy: RetryPolicy = None, 
             context: Dict[str, Any] = None) -> RetryResult:
        """同期関数のリトライ実行"""
        policy = policy or self.default_policy
        context = context or {}
        
        result = RetryResult()
        start_time = time.time()
        
        self.logger.debug(f"リトライ開始: {func.__name__} (最大{policy.max_attempts}回)")
        
        for attempt in range(1, policy.max_attempts + 1):
            attempt_start = time.time()
            
            try:
                # 関数実行
                function_result = func()
                
                # 結果チェック
                if policy.retry_on_result and policy.retry_on_result(function_result):
                    # 結果に基づくリトライ
                    if attempt < policy.max_attempts:
                        delay = self._calculate_delay(attempt, policy)
                        
                        attempt_info = RetryAttempt(
                            attempt_number=attempt,
                            timestamp=time.time(),
                            delay=delay,
                            success=False
                        )
                        result.attempts.append(attempt_info)
                        
                        self.logger.debug(f"結果によるリトライ: {func.__name__} 試行{attempt} - {delay:.2f}秒後に再試行")
                        time.sleep(delay)
                        continue
                
                # 成功
                result.success = True
                result.final_result = function_result
                result.total_attempts = attempt
                
                attempt_info = RetryAttempt(
                    attempt_number=attempt,
                    timestamp=time.time(),
                    delay=0,
                    success=True,
                    result=function_result
                )
                result.attempts.append(attempt_info)
                
                self.retry_stats['successful_retries'] += 1
                self.logger.debug(f"リトライ成功: {func.__name__} 試行{attempt}")
                break
                
            except Exception as e:
                # 停止例外チェック
                if any(isinstance(e, exc_type) for exc_type in policy.stop_on_exceptions):
                    result.success = False
                    result.final_exception = e
                    result.total_attempts = attempt
                    
                    attempt_info = RetryAttempt(
                        attempt_number=attempt,
                        timestamp=time.time(),
                        delay=0,
                        exception=e,
                        success=False
                    )
                    result.attempts.append(attempt_info)
                    
                    self.logger.info(f"停止例外によりリトライ中断: {func.__name__} - {type(e).__name__}")
                    break
                
                # リトライ対象例外チェック
                should_retry = any(isinstance(e, exc_type) for exc_type in policy.retry_on_exceptions)
                
                if should_retry and attempt < policy.max_attempts:
                    delay = self._calculate_delay(attempt, policy)
                    
                    attempt_info = RetryAttempt(
                        attempt_number=attempt,
                        timestamp=time.time(),
                        delay=delay,
                        exception=e,
                        success=False
                    )
                    result.attempts.append(attempt_info)
                    
                    self.logger.warning(
                        f"リトライ実行: {func.__name__} 試行{attempt} - "
                        f"{type(e).__name__}: {str(e)} - {delay:.2f}秒後に再試行"
                    )
                    time.sleep(delay)
                    self.retry_stats['total_retry_attempts'] += 1
                    
                else:
                    # 最終試行または非対象例外
                    result.success = False
                    result.final_exception = e
                    result.total_attempts = attempt
                    
                    attempt_info = RetryAttempt(
                        attempt_number=attempt,
                        timestamp=time.time(),
                        delay=0,
                        exception=e,
                        success=False
                    )
                    result.attempts.append(attempt_info)
                    
                    if attempt >= policy.max_attempts:
                        self.retry_stats['failed_retries'] += 1
                        self.logger.error(f"リトライ上限到達: {func.__name__} - 最終エラー: {type(e).__name__}")
                    else:
                        self.logger.info(f"非対象例外によりリトライ停止: {func.__name__} - {type(e).__name__}")
                    break
        
        result.total_duration = time.time() - start_time
        self.retry_stats['total_functions_retried'] += 1
        
        return result

    async def retry_async(self, func: Callable, policy: RetryPolicy = None, 
                         context: Dict[str, Any] = None) -> RetryResult:
        """非同期関数のリトライ実行"""
        policy = policy or self.default_policy
        context = context or {}
        
        result = RetryResult()
        start_time = time.time()
        
        self.logger.debug(f"非同期リトライ開始: {func.__name__} (最大{policy.max_attempts}回)")
        
        for attempt in range(1, policy.max_attempts + 1):
            try:
                # 非同期関数実行
                function_result = await func()
                
                # 結果チェック
                if policy.retry_on_result and policy.retry_on_result(function_result):
                    if attempt < policy.max_attempts:
                        delay = self._calculate_delay(attempt, policy)
                        
                        attempt_info = RetryAttempt(
                            attempt_number=attempt,
                            timestamp=time.time(),
                            delay=delay,
                            success=False
                        )
                        result.attempts.append(attempt_info)
                        
                        self.logger.debug(f"結果による非同期リトライ: {func.__name__} 試行{attempt} - {delay:.2f}秒後に再試行")
                        await asyncio.sleep(delay)
                        continue
                
                # 成功
                result.success = True
                result.final_result = function_result
                result.total_attempts = attempt
                
                attempt_info = RetryAttempt(
                    attempt_number=attempt,
                    timestamp=time.time(),
                    delay=0,
                    success=True,
                    result=function_result
                )
                result.attempts.append(attempt_info)
                
                self.retry_stats['successful_retries'] += 1
                self.logger.debug(f"非同期リトライ成功: {func.__name__} 試行{attempt}")
                break
                
            except Exception as e:
                # 停止例外チェック
                if any(isinstance(e, exc_type) for exc_type in policy.stop_on_exceptions):
                    result.success = False
                    result.final_exception = e
                    result.total_attempts = attempt
                    
                    attempt_info = RetryAttempt(
                        attempt_number=attempt,
                        timestamp=time.time(),
                        delay=0,
                        exception=e,
                        success=False
                    )
                    result.attempts.append(attempt_info)
                    
                    self.logger.info(f"停止例外により非同期リトライ中断: {func.__name__} - {type(e).__name__}")
                    break
                
                # リトライ対象例外チェック
                should_retry = any(isinstance(e, exc_type) for exc_type in policy.retry_on_exceptions)
                
                if should_retry and attempt < policy.max_attempts:
                    delay = self._calculate_delay(attempt, policy)
                    
                    attempt_info = RetryAttempt(
                        attempt_number=attempt,
                        timestamp=time.time(),
                        delay=delay,
                        exception=e,
                        success=False
                    )
                    result.attempts.append(attempt_info)
                    
                    self.logger.warning(
                        f"非同期リトライ実行: {func.__name__} 試行{attempt} - "
                        f"{type(e).__name__}: {str(e)} - {delay:.2f}秒後に再試行"
                    )
                    await asyncio.sleep(delay)
                    self.retry_stats['total_retry_attempts'] += 1
                    
                else:
                    # 最終試行または非対象例外
                    result.success = False
                    result.final_exception = e
                    result.total_attempts = attempt
                    
                    attempt_info = RetryAttempt(
                        attempt_number=attempt,
                        timestamp=time.time(),
                        delay=0,
                        exception=e,
                        success=False
                    )
                    result.attempts.append(attempt_info)
                    
                    if attempt >= policy.max_attempts:
                        self.retry_stats['failed_retries'] += 1
                        self.logger.error(f"非同期リトライ上限到達: {func.__name__} - 最終エラー: {type(e).__name__}")
                    else:
                        self.logger.info(f"非対象例外により非同期リトライ停止: {func.__name__} - {type(e).__name__}")
                    break
        
        result.total_duration = time.time() - start_time
        self.retry_stats['total_functions_retried'] += 1
        
        return result

    def _calculate_delay(self, attempt: int, policy: RetryPolicy) -> float:
        """遅延時間計算"""
        if policy.backoff_strategy == BackoffStrategy.FIXED:
            delay = policy.base_delay
            
        elif policy.backoff_strategy == BackoffStrategy.LINEAR:
            delay = policy.base_delay * attempt
            
        elif policy.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = policy.base_delay * (2 ** (attempt - 1))
            
        elif policy.backoff_strategy == BackoffStrategy.EXPONENTIAL_JITTER:
            base_delay = policy.base_delay * (2 ** (attempt - 1))
            if policy.jitter:
                # Full jitter: 0 to base_delay
                delay = random.uniform(0, base_delay)
            else:
                delay = base_delay
        
        else:
            delay = policy.base_delay
        
        # 最大遅延時間制限
        delay = min(delay, policy.max_delay)
        
        # ジッター追加（EXPONENTIAL_JITTER以外）
        if policy.jitter and policy.backoff_strategy != BackoffStrategy.EXPONENTIAL_JITTER:
            jitter_range = delay * 0.1  # 10%のジッター
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # 負の値を防ぐ
        
        return delay

    def register_policy(self, name: str, policy: RetryPolicy):
        """名前付きポリシー登録"""
        self.named_policies[name] = policy
        self.logger.info(f"リトライポリシー登録: {name}")

    def get_policy(self, name: str) -> Optional[RetryPolicy]:
        """名前付きポリシー取得"""
        return self.named_policies.get(name)

    def retry_with_policy(self, policy_name: str, func: Callable, 
                         context: Dict[str, Any] = None) -> RetryResult:
        """名前付きポリシーでリトライ"""
        policy = self.get_policy(policy_name)
        if not policy:
            raise ValueError(f"Unknown retry policy: {policy_name}")
        
        return self.retry(func, policy, context)

    async def retry_async_with_policy(self, policy_name: str, func: Callable, 
                                     context: Dict[str, Any] = None) -> RetryResult:
        """名前付きポリシーで非同期リトライ"""
        policy = self.get_policy(policy_name)
        if not policy:
            raise ValueError(f"Unknown retry policy: {policy_name}")
        
        return await self.retry_async(func, policy, context)

    def get_statistics(self) -> Dict[str, Any]:
        """リトライ統計取得"""
        total_retries = self.retry_stats['successful_retries'] + self.retry_stats['failed_retries']
        success_rate = (
            self.retry_stats['successful_retries'] / total_retries * 100
            if total_retries > 0 else 0
        )
        
        return {
            'retry_statistics': self.retry_stats.copy(),
            'success_rate': success_rate,
            'registered_policies': list(self.named_policies.keys()),
            'default_policy': {
                'max_attempts': self.default_policy.max_attempts,
                'base_delay': self.default_policy.base_delay,
                'backoff_strategy': self.default_policy.backoff_strategy.value
            }
        }

    def clear_statistics(self):
        """統計クリア"""
        self.retry_stats = {
            'total_retry_attempts': 0,
            'successful_retries': 0,
            'failed_retries': 0,
            'total_functions_retried': 0
        }
        self.logger.info("リトライ統計クリア")


# グローバルリトライ管理インスタンス
_global_retry_manager: Optional[RetryManager] = None


def get_retry_manager() -> RetryManager:
    """グローバルリトライ管理インスタンス取得"""
    global _global_retry_manager
    if _global_retry_manager is None:
        _global_retry_manager = RetryManager()
    return _global_retry_manager


# 便利デコレータ
def retry(policy: RetryPolicy = None, policy_name: str = None):
    """リトライデコレータ"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                manager = get_retry_manager()
                
                async def target_func():
                    return await func(*args, **kwargs)
                
                if policy_name:
                    result = await manager.retry_async_with_policy(policy_name, target_func)
                else:
                    result = await manager.retry_async(target_func, policy)
                
                if result.success:
                    return result.final_result
                else:
                    raise result.final_exception
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                manager = get_retry_manager()
                
                def target_func():
                    return func(*args, **kwargs)
                
                if policy_name:
                    result = manager.retry_with_policy(policy_name, target_func)
                else:
                    result = manager.retry(target_func, policy)
                
                if result.success:
                    return result.final_result
                else:
                    raise result.final_exception
            
            return sync_wrapper
    
    return decorator


def retry_on_exception(*exception_types, max_attempts: int = 3, 
                      base_delay: float = 1.0, backoff: str = "exponential"):
    """例外ベースリトライデコレータ"""
    policy = RetryPolicy(
        max_attempts=max_attempts,
        base_delay=base_delay,
        backoff_strategy=BackoffStrategy(backoff),
        retry_on_exceptions=list(exception_types)
    )
    return retry(policy)