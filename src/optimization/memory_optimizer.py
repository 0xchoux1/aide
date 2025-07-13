"""
AIDE メモリ最適化システム

メモリプール、オブジェクトプール、キャッシュ管理によるメモリ最適化
"""

import gc
import sys
import time
import threading
import weakref
from typing import Dict, List, Optional, Any, Type, Callable, Generic, TypeVar, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from datetime import datetime, timedelta
import tracemalloc
from contextlib import contextmanager
import psutil

from ..config import get_config_manager
from ..logging import get_logger


T = TypeVar('T')


@dataclass
class MemoryStats:
    """メモリ統計情報"""
    total_memory_mb: float
    available_memory_mb: float
    used_memory_mb: float
    memory_percent: float
    gc_count: Dict[int, int]
    gc_collections: int
    gc_collected: int
    gc_uncollectable: int
    tracemalloc_current_mb: Optional[float] = None
    tracemalloc_peak_mb: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


class MemoryProfiler:
    """メモリプロファイラー"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.is_tracing = False
        self.snapshots = []
        
        # psutil使用可能性チェック
        try:
            import psutil
            self.psutil = psutil
            self.psutil_available = True
        except ImportError:
            self.psutil = None
            self.psutil_available = False
            self.logger.warning("psutil未インストール - メモリ監視機能制限")
    
    def start_tracing(self):
        """メモリトレース開始"""
        if not self.is_tracing:
            tracemalloc.start()
            self.is_tracing = True
            self.logger.info("メモリトレース開始")
    
    def stop_tracing(self):
        """メモリトレース停止"""
        if self.is_tracing:
            tracemalloc.stop()
            self.is_tracing = False
            self.logger.info("メモリトレース停止")
    
    def get_current_stats(self) -> MemoryStats:
        """現在のメモリ統計取得"""
        # GC統計
        gc_stats = gc.get_stats()
        gc_count = gc.get_count()
        
        # システムメモリ（psutil使用可能な場合）
        total_memory_mb = 0
        available_memory_mb = 0
        used_memory_mb = 0
        memory_percent = 0
        
        if self.psutil_available:
            try:
                vm = self.psutil.virtual_memory()
                total_memory_mb = vm.total / (1024 * 1024)
                available_memory_mb = vm.available / (1024 * 1024)
                used_memory_mb = vm.used / (1024 * 1024)
                memory_percent = vm.percent
            except Exception as e:
                self.logger.error(f"システムメモリ取得エラー: {str(e)}")
        
        # tracemalloc統計
        tracemalloc_current_mb = None
        tracemalloc_peak_mb = None
        
        if self.is_tracing:
            try:
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc_current_mb = current / (1024 * 1024)
                tracemalloc_peak_mb = peak / (1024 * 1024)
            except Exception as e:
                self.logger.error(f"tracemalloc統計取得エラー: {str(e)}")
        
        return MemoryStats(
            total_memory_mb=total_memory_mb,
            available_memory_mb=available_memory_mb,
            used_memory_mb=used_memory_mb,
            memory_percent=memory_percent,
            gc_count={i: count for i, count in enumerate(gc_count)},
            gc_collections=sum(stat['collections'] for stat in gc_stats),
            gc_collected=sum(stat['collected'] for stat in gc_stats),
            gc_uncollectable=sum(stat['uncollectable'] for stat in gc_stats),
            tracemalloc_current_mb=tracemalloc_current_mb,
            tracemalloc_peak_mb=tracemalloc_peak_mb
        )
    
    def take_snapshot(self, label: str = None) -> int:
        """メモリスナップショット取得"""
        snapshot_data = {
            'timestamp': time.time(),
            'label': label or f"snapshot_{len(self.snapshots)}",
            'stats': self.get_current_stats()
        }
        
        if self.is_tracing:
            try:
                snapshot_data['tracemalloc_snapshot'] = tracemalloc.take_snapshot()
            except Exception as e:
                self.logger.error(f"tracemalloc スナップショット取得エラー: {str(e)}")
        
        self.snapshots.append(snapshot_data)
        self.logger.debug(f"メモリスナップショット取得: {snapshot_data['label']}")
        
        return len(self.snapshots) - 1
    
    def compare_snapshots(self, snapshot1_idx: int, snapshot2_idx: int) -> Dict[str, Any]:
        """スナップショット比較"""
        if (snapshot1_idx >= len(self.snapshots) or 
            snapshot2_idx >= len(self.snapshots)):
            raise ValueError("無効なスナップショットインデックス")
        
        snap1 = self.snapshots[snapshot1_idx]
        snap2 = self.snapshots[snapshot2_idx]
        
        stats1 = snap1['stats']
        stats2 = snap2['stats']
        
        comparison = {
            'snapshot1': snap1['label'],
            'snapshot2': snap2['label'],
            'time_diff_seconds': snap2['timestamp'] - snap1['timestamp'],
            'memory_diff_mb': stats2.used_memory_mb - stats1.used_memory_mb,
            'tracemalloc_diff_mb': None,
            'gc_collections_diff': stats2.gc_collections - stats1.gc_collections,
            'gc_collected_diff': stats2.gc_collected - stats1.gc_collected
        }
        
        if (stats1.tracemalloc_current_mb is not None and 
            stats2.tracemalloc_current_mb is not None):
            comparison['tracemalloc_diff_mb'] = (
                stats2.tracemalloc_current_mb - stats1.tracemalloc_current_mb
            )
        
        # tracemalloc詳細比較
        if ('tracemalloc_snapshot' in snap1 and 
            'tracemalloc_snapshot' in snap2):
            try:
                top_stats = snap2['tracemalloc_snapshot'].compare_to(
                    snap1['tracemalloc_snapshot'], 'lineno'
                )
                
                comparison['top_differences'] = []
                for stat in top_stats[:10]:  # 上位10件
                    comparison['top_differences'].append({
                        'traceback': str(stat.traceback),
                        'size_diff_mb': stat.size_diff / (1024 * 1024),
                        'count_diff': stat.count_diff
                    })
            except Exception as e:
                self.logger.error(f"tracemalloc比較エラー: {str(e)}")
        
        return comparison
    
    @contextmanager
    def profile_memory(self, label: str = "profile"):
        """メモリプロファイリングコンテキスト"""
        start_snapshot = self.take_snapshot(f"{label}_start")
        
        try:
            yield
        finally:
            end_snapshot = self.take_snapshot(f"{label}_end")
            
            comparison = self.compare_snapshots(start_snapshot, end_snapshot)
            
            self.logger.info(
                f"メモリプロファイリング結果 ({label}): "
                f"メモリ差分={comparison['memory_diff_mb']:.2f}MB, "
                f"実行時間={comparison['time_diff_seconds']:.2f}秒"
            )


class ObjectPool(Generic[T]):
    """オブジェクトプール"""
    
    def __init__(self, factory: Callable[[], T], max_size: int = 100, 
                 reset_func: Optional[Callable[[T], None]] = None):
        self.factory = factory
        self.max_size = max_size
        self.reset_func = reset_func
        self.pool: deque = deque()
        self.lock = threading.Lock()
        self.created_count = 0
        self.reused_count = 0
        
        self.logger = get_logger(__name__)
    
    def acquire(self) -> T:
        """オブジェクト取得"""
        with self.lock:
            if self.pool:
                obj = self.pool.popleft()
                self.reused_count += 1
                self.logger.debug(f"オブジェクトプールから再利用: {type(obj).__name__}")
                return obj
            else:
                obj = self.factory()
                self.created_count += 1
                self.logger.debug(f"オブジェクトプールで新規作成: {type(obj).__name__}")
                return obj
    
    def release(self, obj: T):
        """オブジェクト返却"""
        with self.lock:
            if len(self.pool) < self.max_size:
                # リセット処理
                if self.reset_func:
                    try:
                        self.reset_func(obj)
                    except Exception as e:
                        self.logger.error(f"オブジェクトリセットエラー: {str(e)}")
                        return
                
                self.pool.append(obj)
                self.logger.debug(f"オブジェクトプールに返却: {type(obj).__name__}")
    
    @contextmanager
    def get_object(self):
        """オブジェクト取得コンテキスト"""
        obj = self.acquire()
        try:
            yield obj
        finally:
            self.release(obj)
    
    def get_stats(self) -> Dict[str, Any]:
        """プール統計取得"""
        with self.lock:
            return {
                'pool_size': len(self.pool),
                'max_size': self.max_size,
                'created_count': self.created_count,
                'reused_count': self.reused_count,
                'reuse_rate': self.reused_count / (self.created_count + self.reused_count) * 100 if (self.created_count + self.reused_count) > 0 else 0
            }
    
    def clear(self):
        """プールクリア"""
        with self.lock:
            self.pool.clear()
            self.logger.info(f"オブジェクトプールクリア: {self.created_count}個作成, {self.reused_count}個再利用")


class MemoryPool:
    """メモリプール管理"""
    
    def __init__(self, initial_size: int = 1024 * 1024):  # 1MB
        self.initial_size = initial_size
        self.pools: Dict[int, deque] = defaultdict(deque)
        self.lock = threading.Lock()
        self.allocated_count = 0
        self.reused_count = 0
        
        self.logger = get_logger(__name__)
    
    def allocate(self, size: int) -> bytearray:
        """メモリ割り当て"""
        # サイズを2の累乗に切り上げ
        pool_size = 1
        while pool_size < size:
            pool_size *= 2
        
        with self.lock:
            if self.pools[pool_size]:
                buffer = self.pools[pool_size].popleft()
                self.reused_count += 1
                self.logger.debug(f"メモリプールから再利用: {pool_size}バイト")
                
                # 必要に応じてサイズ調整
                if len(buffer) > size:
                    return buffer[:size]
                return buffer
            else:
                buffer = bytearray(pool_size)
                self.allocated_count += 1
                self.logger.debug(f"メモリプールで新規割り当て: {pool_size}バイト")
                
                if len(buffer) > size:
                    return buffer[:size]
                return buffer
    
    def deallocate(self, buffer: bytearray):
        """メモリ解放"""
        if not isinstance(buffer, bytearray):
            return
        
        pool_size = len(buffer)
        
        with self.lock:
            # プール最大サイズ制限
            if len(self.pools[pool_size]) < 10:
                # バッファクリア
                buffer[:] = b'\x00' * len(buffer)
                self.pools[pool_size].append(buffer)
                self.logger.debug(f"メモリプールに返却: {pool_size}バイト")
    
    @contextmanager
    def get_buffer(self, size: int):
        """バッファ取得コンテキスト"""
        buffer = self.allocate(size)
        try:
            yield buffer
        finally:
            self.deallocate(buffer)
    
    def get_stats(self) -> Dict[str, Any]:
        """プール統計取得"""
        with self.lock:
            total_pooled = sum(len(pool) for pool in self.pools.values())
            total_size = sum(
                size * len(pool) 
                for size, pool in self.pools.items()
            )
            
            return {
                'allocated_count': self.allocated_count,
                'reused_count': self.reused_count,
                'reuse_rate': self.reused_count / (self.allocated_count + self.reused_count) * 100 if (self.allocated_count + self.reused_count) > 0 else 0,
                'pooled_buffers': total_pooled,
                'pooled_size_mb': total_size / (1024 * 1024),
                'pool_sizes': list(self.pools.keys())
            }
    
    def clear(self):
        """プールクリア"""
        with self.lock:
            total_cleared = sum(len(pool) for pool in self.pools.values())
            self.pools.clear()
            self.logger.info(f"メモリプールクリア: {total_cleared}個のバッファを解放")


class CacheManager:
    """キャッシュ管理"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_order: deque = deque()
        self.lock = threading.Lock()
        
        self.hit_count = 0
        self.miss_count = 0
        
        self.logger = get_logger(__name__)
    
    def get(self, key: str) -> Optional[Any]:
        """キャッシュ取得"""
        with self.lock:
            if key not in self.cache:
                self.miss_count += 1
                self.logger.debug(f"キャッシュミス: {key}")
                return None
            
            entry = self.cache[key]
            
            # TTLチェック
            if time.time() > entry['expires_at']:
                del self.cache[key]
                self.access_order.remove(key)
                self.miss_count += 1
                self.logger.debug(f"キャッシュ期限切れ: {key}")
                return None
            
            # アクセス順序更新
            self.access_order.remove(key)
            self.access_order.append(key)
            
            self.hit_count += 1
            self.logger.debug(f"キャッシュヒット: {key}")
            return entry['value']
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """キャッシュ設定"""
        with self.lock:
            ttl = ttl_seconds or self.ttl_seconds
            expires_at = time.time() + ttl
            
            # 既存エントリ更新
            if key in self.cache:
                self.cache[key] = {'value': value, 'expires_at': expires_at}
                self.access_order.remove(key)
                self.access_order.append(key)
                self.logger.debug(f"キャッシュ更新: {key}")
                return
            
            # 容量チェック
            if len(self.cache) >= self.max_size:
                # LRU削除
                oldest_key = self.access_order.popleft()
                del self.cache[oldest_key]
                self.logger.debug(f"キャッシュLRU削除: {oldest_key}")
            
            # 新規エントリ追加
            self.cache[key] = {'value': value, 'expires_at': expires_at}
            self.access_order.append(key)
            self.logger.debug(f"キャッシュ追加: {key}")
    
    def delete(self, key: str) -> bool:
        """キャッシュ削除"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.access_order.remove(key)
                self.logger.debug(f"キャッシュ削除: {key}")
                return True
            return False
    
    def clear(self):
        """キャッシュクリア"""
        with self.lock:
            cleared_count = len(self.cache)
            self.cache.clear()
            self.access_order.clear()
            self.logger.info(f"キャッシュクリア: {cleared_count}個のエントリを削除")
    
    def cleanup_expired(self):
        """期限切れエントリクリーンアップ"""
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.cache.items()
                if current_time > entry['expires_at']
            ]
            
            for key in expired_keys:
                del self.cache[key]
                self.access_order.remove(key)
            
            if expired_keys:
                self.logger.info(f"期限切れキャッシュクリーンアップ: {len(expired_keys)}個")
    
    def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計取得"""
        with self.lock:
            total_requests = self.hit_count + self.miss_count
            hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_rate': hit_rate,
                'ttl_seconds': self.ttl_seconds
            }


class MemoryOptimizer:
    """メモリ最適化管理クラス"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger(__name__)
        
        # コンポーネント初期化
        self.profiler = MemoryProfiler()
        self.memory_pool = MemoryPool()
        self.cache_manager = CacheManager(
            max_size=self.config_manager.get("optimization.cache_max_size", 1000),
            ttl_seconds=self.config_manager.get("optimization.cache_ttl_seconds", 3600)
        )
        
        # オブジェクトプール
        self.object_pools: Dict[str, ObjectPool] = {}
        
        # 最適化設定
        self.gc_optimization_enabled = self.config_manager.get(
            "optimization.gc_optimization", True
        )
        self.auto_cleanup_enabled = self.config_manager.get(
            "optimization.auto_cleanup", True
        )
        
        # バックグラウンドクリーンアップ
        self.cleanup_thread = None
        self.cleanup_interval = self.config_manager.get(
            "optimization.cleanup_interval_seconds", 300
        )
        self.stop_cleanup = threading.Event()
        
        # 統計
        self.optimization_stats = {
            'gc_collections_triggered': 0,
            'memory_freed_mb': 0,
            'cache_cleanups': 0,
            'pool_cleanups': 0
        }
    
    def start_profiling(self):
        """メモリプロファイリング開始"""
        self.profiler.start_tracing()
        
        if self.auto_cleanup_enabled:
            self._start_cleanup_thread()
        
        self.logger.info("メモリ最適化開始")
    
    def stop_profiling(self):
        """メモリプロファイリング停止"""
        self.profiler.stop_tracing()
        
        if self.cleanup_thread:
            self.stop_cleanup.set()
            self.cleanup_thread.join(timeout=5.0)
        
        self.logger.info("メモリ最適化停止")
    
    def _start_cleanup_thread(self):
        """クリーンアップスレッド開始"""
        if self.cleanup_thread is None or not self.cleanup_thread.is_alive():
            self.stop_cleanup.clear()
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True
            )
            self.cleanup_thread.start()
    
    def _cleanup_loop(self):
        """クリーンアップループ"""
        while not self.stop_cleanup.is_set():
            try:
                self.cleanup_memory()
                self.stop_cleanup.wait(self.cleanup_interval)
            except Exception as e:
                self.logger.error(f"メモリクリーンアップエラー: {str(e)}")
    
    def create_object_pool(self, name: str, factory: Callable[[], T], 
                          max_size: int = 100, 
                          reset_func: Optional[Callable[[T], None]] = None) -> ObjectPool[T]:
        """オブジェクトプール作成"""
        pool = ObjectPool(factory, max_size, reset_func)
        self.object_pools[name] = pool
        self.logger.info(f"オブジェクトプール作成: {name}")
        return pool
    
    def get_object_pool(self, name: str) -> Optional[ObjectPool]:
        """オブジェクトプール取得"""
        return self.object_pools.get(name)
    
    def force_gc(self) -> Dict[str, int]:
        """強制ガベージコレクション"""
        if not self.gc_optimization_enabled:
            return {}
        
        # GC実行前の状態
        before_stats = self.profiler.get_current_stats()
        
        # 全世代のGC実行
        collected = {}
        for generation in range(3):
            collected[f'gen_{generation}'] = gc.collect(generation)
        
        # GC実行後の状態
        after_stats = self.profiler.get_current_stats()
        
        # 統計更新
        self.optimization_stats['gc_collections_triggered'] += 1
        memory_freed = before_stats.used_memory_mb - after_stats.used_memory_mb
        if memory_freed > 0:
            self.optimization_stats['memory_freed_mb'] += memory_freed
        
        self.logger.info(f"強制GC完了: {collected}, メモリ解放={memory_freed:.2f}MB")
        
        return collected
    
    def cleanup_memory(self):
        """メモリクリーンアップ"""
        try:
            # キャッシュクリーンアップ
            self.cache_manager.cleanup_expired()
            self.optimization_stats['cache_cleanups'] += 1
            
            # 弱参照クリーンアップ
            self._cleanup_weak_references()
            
            # 必要に応じてGC実行
            current_stats = self.profiler.get_current_stats()
            memory_threshold = self.config_manager.get(
                "optimization.gc_memory_threshold_percent", 80
            )
            
            if current_stats.memory_percent > memory_threshold:
                self.force_gc()
            
            self.logger.debug("メモリクリーンアップ完了")
            
        except Exception as e:
            self.logger.error(f"メモリクリーンアップエラー: {str(e)}")
    
    def _cleanup_weak_references(self):
        """弱参照クリーンアップ"""
        # 削除された弱参照をクリーンアップ
        try:
            # weakrefのガベージコレクション
            import weakref
            weakref.ref(object())  # ダミー弱参照作成でクリーンアップトリガー
        except Exception as e:
            self.logger.debug(f"弱参照クリーンアップ: {str(e)}")
    
    def optimize_memory_usage(self):
        """メモリ使用量最適化"""
        initial_stats = self.profiler.get_current_stats()
        
        # 各種クリーンアップ実行
        self.cleanup_memory()
        
        # オブジェクトプールサイズ調整
        for name, pool in self.object_pools.items():
            pool_stats = pool.get_stats()
            
            # 使用率が低い場合はプールサイズ削減
            if pool_stats['reuse_rate'] < 20:  # 20%未満
                old_size = pool.max_size
                pool.max_size = max(pool.max_size // 2, 10)
                self.logger.info(
                    f"オブジェクトプールサイズ削減: {name} {old_size} -> {pool.max_size}"
                )
        
        # メモリプールクリーンアップ
        pool_stats = self.memory_pool.get_stats()
        if pool_stats['pooled_size_mb'] > 50:  # 50MB以上
            self.memory_pool.clear()
            self.optimization_stats['pool_cleanups'] += 1
        
        # 最終統計
        final_stats = self.profiler.get_current_stats()
        memory_saved = initial_stats.used_memory_mb - final_stats.used_memory_mb
        
        self.logger.info(f"メモリ最適化完了: {memory_saved:.2f}MB削減")
        
        return {
            'memory_saved_mb': memory_saved,
            'initial_memory_mb': initial_stats.used_memory_mb,
            'final_memory_mb': final_stats.used_memory_mb,
            'memory_percent_before': initial_stats.memory_percent,
            'memory_percent_after': final_stats.memory_percent
        }
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """最適化概要取得"""
        current_stats = self.profiler.get_current_stats()
        cache_stats = self.cache_manager.get_stats()
        memory_pool_stats = self.memory_pool.get_stats()
        
        object_pool_stats = {}
        for name, pool in self.object_pools.items():
            object_pool_stats[name] = pool.get_stats()
        
        return {
            'current_memory': current_stats.to_dict(),
            'cache_stats': cache_stats,
            'memory_pool_stats': memory_pool_stats,
            'object_pool_stats': object_pool_stats,
            'optimization_stats': self.optimization_stats.copy(),
            'profiling_enabled': self.profiler.is_tracing,
            'auto_cleanup_enabled': self.auto_cleanup_enabled
        }


# グローバルメモリ最適化インスタンス
_global_memory_optimizer: Optional[MemoryOptimizer] = None


def get_memory_optimizer() -> MemoryOptimizer:
    """グローバルメモリ最適化インスタンス取得"""
    global _global_memory_optimizer
    if _global_memory_optimizer is None:
        _global_memory_optimizer = MemoryOptimizer()
    return _global_memory_optimizer


# 便利デコレータ
def memory_profile(label: str = "function"):
    """メモリプロファイリングデコレータ"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            optimizer = get_memory_optimizer()
            with optimizer.profiler.profile_memory(f"{label}_{func.__name__}"):
                return func(*args, **kwargs)
        return wrapper
    return decorator