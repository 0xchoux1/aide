"""
AIDE サーキットブレーカーシステム

障害の連鎖を防ぐためのサーキットブレーカーパターン実装
"""

import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta

from ..config import get_config_manager
from ..logging import get_logger


class CircuitState(Enum):
    """サーキット状態"""
    CLOSED = "closed"      # 正常状態
    OPEN = "open"          # 障害状態（呼び出し遮断）
    HALF_OPEN = "half_open"  # 回復試行状態


@dataclass
class CircuitBreakerConfig:
    """サーキットブレーカー設定"""
    failure_threshold: int = 5      # 失敗閾値
    recovery_timeout: float = 60.0  # 回復試行タイムアウト（秒）
    success_threshold: int = 3      # 回復成功閾値
    monitoring_window: float = 300.0  # 監視ウィンドウ（秒）
    expected_exceptions: List[str] = None  # 予期される例外タイプ
    
    def __post_init__(self):
        if self.expected_exceptions is None:
            self.expected_exceptions = []


@dataclass
class CircuitBreakerStats:
    """サーキットブレーカー統計"""
    circuit_name: str
    state: CircuitState
    failure_count: int
    success_count: int
    total_calls: int
    last_failure_time: Optional[float]
    last_success_time: Optional[float]
    state_changed_time: float
    consecutive_failures: int
    consecutive_successes: int
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['state'] = self.state.value
        return data


class CircuitBreakerException(Exception):
    """サーキットブレーカー例外"""
    def __init__(self, circuit_name: str, state: CircuitState):
        self.circuit_name = circuit_name
        self.state = state
        super().__init__(f"Circuit breaker '{circuit_name}' is {state.value}")


class CircuitBreaker:
    """サーキットブレーカー実装"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.logger = get_logger(__name__)
        
        # 状態管理
        self.state = CircuitState.CLOSED
        self.state_changed_time = time.time()
        
        # 統計情報
        self.failure_count = 0
        self.success_count = 0
        self.total_calls = 0
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        
        # 実行履歴
        self.call_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
        
        # スレッドロック
        self.lock = threading.Lock()
        
        self.logger.info(f"サーキットブレーカー初期化: {self.name}")

    def call(self, func: Callable, *args, **kwargs):
        """保護された関数呼び出し"""
        with self.lock:
            self.total_calls += 1
            
            # 現在の状態チェック
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    self._record_blocked_call()
                    raise CircuitBreakerException(self.name, self.state)
            
            elif self.state == CircuitState.HALF_OPEN:
                # HALF_OPEN状態では限定的な呼び出しのみ許可
                pass
        
        # 関数実行
        call_start_time = time.time()
        try:
            result = func(*args, **kwargs)
            
            # 成功時の処理
            with self.lock:
                self._record_success(call_start_time)
            
            return result
            
        except Exception as e:
            # 失敗時の処理
            with self.lock:
                self._record_failure(e, call_start_time)
            
            raise

    def _should_attempt_reset(self) -> bool:
        """リセット試行判定"""
        return (time.time() - self.state_changed_time) >= self.config.recovery_timeout

    def _transition_to_half_open(self):
        """HALF_OPEN状態に遷移"""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.state_changed_time = time.time()
        self.consecutive_successes = 0
        
        self.logger.info(f"サーキットブレーカー状態変更: {self.name} {old_state.value} -> {self.state.value}")

    def _record_blocked_call(self):
        """ブロックされた呼び出し記録"""
        call_record = {
            'timestamp': time.time(),
            'type': 'blocked',
            'state': self.state.value
        }
        
        self._add_call_history(call_record)
        
        self.logger.debug(f"サーキットブレーカーによる呼び出しブロック: {self.name}")

    def _record_success(self, call_start_time: float):
        """成功記録"""
        call_duration = time.time() - call_start_time
        self.success_count += 1
        self.last_success_time = time.time()
        self.consecutive_failures = 0
        self.consecutive_successes += 1
        
        call_record = {
            'timestamp': time.time(),
            'type': 'success',
            'duration': call_duration,
            'state': self.state.value
        }
        
        self._add_call_history(call_record)
        
        # 状態遷移チェック
        if self.state == CircuitState.HALF_OPEN:
            if self.consecutive_successes >= self.config.success_threshold:
                self._transition_to_closed()
        
        self.logger.debug(f"サーキットブレーカー成功記録: {self.name}")

    def _record_failure(self, exception: Exception, call_start_time: float):
        """失敗記録"""
        call_duration = time.time() - call_start_time
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.consecutive_successes = 0
        self.consecutive_failures += 1
        
        call_record = {
            'timestamp': time.time(),
            'type': 'failure',
            'duration': call_duration,
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'state': self.state.value
        }
        
        self._add_call_history(call_record)
        
        # 状態遷移チェック
        if self.state == CircuitState.CLOSED:
            if self._should_open_circuit():
                self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            # HALF_OPEN中の失敗は即座にOPENに戻す
            self._transition_to_open()
        
        self.logger.warning(f"サーキットブレーカー失敗記録: {self.name} - {type(exception).__name__}")

    def _should_open_circuit(self) -> bool:
        """サーキットオープン判定"""
        # 連続失敗数チェック
        if self.consecutive_failures >= self.config.failure_threshold:
            return True
        
        # 監視ウィンドウ内の失敗率チェック
        window_start = time.time() - self.config.monitoring_window
        recent_calls = [
            call for call in self.call_history
            if call['timestamp'] >= window_start and call['type'] in ['success', 'failure']
        ]
        
        if len(recent_calls) >= self.config.failure_threshold:
            failure_calls = [call for call in recent_calls if call['type'] == 'failure']
            failure_rate = len(failure_calls) / len(recent_calls)
            
            # 失敗率が50%を超えた場合
            return failure_rate > 0.5
        
        return False

    def _transition_to_closed(self):
        """CLOSED状態に遷移"""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.state_changed_time = time.time()
        self.consecutive_failures = 0
        
        self.logger.info(f"サーキットブレーカー回復: {self.name} {old_state.value} -> {self.state.value}")

    def _transition_to_open(self):
        """OPEN状態に遷移"""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.state_changed_time = time.time()
        
        self.logger.error(f"サーキットブレーカーオープン: {self.name} {old_state.value} -> {self.state.value}")

    def _add_call_history(self, call_record: Dict[str, Any]):
        """呼び出し履歴追加"""
        self.call_history.append(call_record)
        
        # 履歴サイズ制限
        if len(self.call_history) > self.max_history_size:
            self.call_history = self.call_history[-self.max_history_size:]

    def get_stats(self) -> CircuitBreakerStats:
        """統計情報取得"""
        with self.lock:
            return CircuitBreakerStats(
                circuit_name=self.name,
                state=self.state,
                failure_count=self.failure_count,
                success_count=self.success_count,
                total_calls=self.total_calls,
                last_failure_time=self.last_failure_time,
                last_success_time=self.last_success_time,
                state_changed_time=self.state_changed_time,
                consecutive_failures=self.consecutive_failures,
                consecutive_successes=self.consecutive_successes
            )

    def reset(self):
        """サーキットブレーカーリセット"""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.state_changed_time = time.time()
            self.failure_count = 0
            self.success_count = 0
            self.consecutive_failures = 0
            self.consecutive_successes = 0
            self.call_history.clear()
            
            self.logger.info(f"サーキットブレーカーリセット: {self.name}")

    def force_open(self):
        """強制オープン"""
        with self.lock:
            self._transition_to_open()

    def force_close(self):
        """強制クローズ"""
        with self.lock:
            self._transition_to_closed()

    def get_call_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """呼び出し履歴取得"""
        with self.lock:
            return self.call_history[-limit:]

    def get_health_report(self) -> Dict[str, Any]:
        """ヘルスレポート取得"""
        stats = self.get_stats()
        
        # 成功率計算
        total_attempts = stats.success_count + stats.failure_count
        success_rate = (stats.success_count / total_attempts * 100) if total_attempts > 0 else 0
        
        # 最近の呼び出し分析
        recent_window = 300  # 5分
        recent_start = time.time() - recent_window
        recent_calls = [
            call for call in self.call_history
            if call['timestamp'] >= recent_start
        ]
        
        recent_successes = len([call for call in recent_calls if call['type'] == 'success'])
        recent_failures = len([call for call in recent_calls if call['type'] == 'failure'])
        recent_total = recent_successes + recent_failures
        recent_success_rate = (recent_successes / recent_total * 100) if recent_total > 0 else 0
        
        # 平均応答時間
        duration_calls = [call for call in recent_calls if 'duration' in call]
        avg_response_time = (
            sum(call['duration'] for call in duration_calls) / len(duration_calls)
            if duration_calls else 0
        )
        
        return {
            'circuit_name': self.name,
            'current_state': stats.state.value,
            'overall_success_rate': success_rate,
            'recent_success_rate': recent_success_rate,
            'avg_response_time_ms': avg_response_time * 1000,
            'total_calls': stats.total_calls,
            'consecutive_failures': stats.consecutive_failures,
            'time_since_last_failure': (
                time.time() - stats.last_failure_time
                if stats.last_failure_time else None
            ),
            'health_status': self._determine_health_status(stats, success_rate, recent_success_rate)
        }

    def _determine_health_status(self, stats: CircuitBreakerStats, 
                               success_rate: float, recent_success_rate: float) -> str:
        """ヘルス状態判定"""
        if stats.state == CircuitState.OPEN:
            return "unhealthy"
        elif stats.state == CircuitState.HALF_OPEN:
            return "recovering"
        elif success_rate >= 95 and recent_success_rate >= 90:
            return "healthy"
        elif success_rate >= 80 and recent_success_rate >= 70:
            return "degraded"
        else:
            return "unhealthy"


class CircuitBreakerManager:
    """サーキットブレーカー管理"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger(__name__)
        
        # サーキットブレーカー登録
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # デフォルト設定
        self.default_config = CircuitBreakerConfig(
            failure_threshold=self.config_manager.get("circuit_breaker.failure_threshold", 5),
            recovery_timeout=self.config_manager.get("circuit_breaker.recovery_timeout", 60.0),
            success_threshold=self.config_manager.get("circuit_breaker.success_threshold", 3),
            monitoring_window=self.config_manager.get("circuit_breaker.monitoring_window", 300.0)
        )

    def get_circuit_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """サーキットブレーカー取得（なければ作成）"""
        if name not in self.circuit_breakers:
            breaker_config = config or self.default_config
            self.circuit_breakers[name] = CircuitBreaker(name, breaker_config)
            self.logger.info(f"新しいサーキットブレーカー作成: {name}")
        
        return self.circuit_breakers[name]

    def call_with_circuit_breaker(self, circuit_name: str, func: Callable, 
                                 *args, config: CircuitBreakerConfig = None, **kwargs):
        """サーキットブレーカー付き関数呼び出し"""
        circuit_breaker = self.get_circuit_breaker(circuit_name, config)
        return circuit_breaker.call(func, *args, **kwargs)

    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """全サーキットブレーカー統計取得"""
        return {
            name: breaker.get_stats()
            for name, breaker in self.circuit_breakers.items()
        }

    def get_health_summary(self) -> Dict[str, Any]:
        """全体ヘルス概要取得"""
        all_reports = {
            name: breaker.get_health_report()
            for name, breaker in self.circuit_breakers.items()
        }
        
        # 全体統計計算
        total_circuits = len(all_reports)
        healthy_circuits = len([r for r in all_reports.values() if r['health_status'] == 'healthy'])
        unhealthy_circuits = len([r for r in all_reports.values() if r['health_status'] == 'unhealthy'])
        
        return {
            'total_circuits': total_circuits,
            'healthy_circuits': healthy_circuits,
            'unhealthy_circuits': unhealthy_circuits,
            'overall_health_rate': (healthy_circuits / total_circuits * 100) if total_circuits > 0 else 0,
            'circuit_reports': all_reports
        }

    def reset_all_circuits(self):
        """全サーキットブレーカーリセット"""
        for breaker in self.circuit_breakers.values():
            breaker.reset()
        
        self.logger.info("全サーキットブレーカーリセット")

    def remove_circuit_breaker(self, name: str) -> bool:
        """サーキットブレーカー削除"""
        if name in self.circuit_breakers:
            del self.circuit_breakers[name]
            self.logger.info(f"サーキットブレーカー削除: {name}")
            return True
        return False


# グローバルサーキットブレーカー管理インスタンス
_global_circuit_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """グローバルサーキットブレーカー管理インスタンス取得"""
    global _global_circuit_breaker_manager
    if _global_circuit_breaker_manager is None:
        _global_circuit_breaker_manager = CircuitBreakerManager()
    return _global_circuit_breaker_manager


# 便利デコレータ
def circuit_breaker(name: str, config: CircuitBreakerConfig = None):
    """サーキットブレーカーデコレータ"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            manager = get_circuit_breaker_manager()
            return manager.call_with_circuit_breaker(name, func, *args, config=config, **kwargs)
        return wrapper
    return decorator