"""
AIDE 非同期処理最適化システム

非同期タスクスケジューリング、コネクションプール、バッチ処理最適化
"""

import asyncio
import threading
import time
import queue
from typing import Dict, List, Optional, Any, Callable, Awaitable, Union, TypeVar, Generic
from dataclasses import dataclass, asdict
from collections import deque
from datetime import datetime, timedelta
from enum import Enum
import concurrent.futures
import weakref

from ..config import get_config_manager
from ..logging import get_logger


T = TypeVar('T')
R = TypeVar('R')


class TaskPriority(Enum):
    """タスク優先度"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """タスク状態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncTask:
    """非同期タスク"""
    task_id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority = TaskPriority.NORMAL
    timeout_seconds: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['func_name'] = getattr(self.func, '__name__', str(self.func))
        # 実行可能オブジェクトは除外
        del data['func']
        del data['args']
        del data['kwargs']
        return data


class TaskScheduler:
    """非同期タスクスケジューラー"""
    
    def __init__(self, max_concurrent_tasks: int = 10, max_queue_size: int = 1000):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_queue_size = max_queue_size
        
        # 優先度別キュー
        self.task_queues = {
            priority: asyncio.Queue(maxsize=max_queue_size)
            for priority in TaskPriority
        }
        
        self.running_tasks: Dict[str, AsyncTask] = {}
        self.completed_tasks: deque = deque(maxlen=1000)
        
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.is_running = False
        self.scheduler_task = None
        
        # 統計
        self.stats = {
            'total_submitted': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_cancelled': 0,
            'total_retries': 0
        }
        
        self.logger = get_logger(__name__)
    
    async def start(self):
        """スケジューラー開始"""
        if self.is_running:
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        self.logger.info("非同期タスクスケジューラー開始")
    
    async def stop(self):
        """スケジューラー停止"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 実行中タスクの完了を待つ
        if self.running_tasks:
            await asyncio.gather(
                *[task._asyncio_task for task in self.running_tasks.values()
                  if hasattr(task, '_asyncio_task')],
                return_exceptions=True
            )
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("非同期タスクスケジューラー停止")
    
    async def submit_task(self, func: Callable, *args, 
                         priority: TaskPriority = TaskPriority.NORMAL,
                         timeout_seconds: Optional[float] = None,
                         max_retries: int = 3,
                         **kwargs) -> str:
        """タスク投入"""
        task_id = f"task_{int(time.time() * 1000000)}"
        
        task = AsyncTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries
        )
        
        # 優先度別キューに追加
        try:
            await self.task_queues[priority].put(task)
            self.stats['total_submitted'] += 1
            self.logger.debug(f"タスク投入: {task_id} (優先度: {priority.name})")
            return task_id
        except asyncio.QueueFull:
            raise Exception(f"タスクキューが満杯です (priority: {priority.name})")
    
    async def _scheduler_loop(self):
        """スケジューラーメインループ"""
        while self.is_running:
            try:
                # 優先度順でタスク取得
                task = await self._get_next_task()
                
                if task:
                    # セマフォで同時実行数制御
                    await self.semaphore.acquire()
                    
                    # タスク実行
                    asyncio_task = asyncio.create_task(self._execute_task(task))
                    task._asyncio_task = asyncio_task
                    self.running_tasks[task.task_id] = task
                
                else:
                    # タスクがない場合は少し待機
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                self.logger.error(f"スケジューラーループエラー: {str(e)}")
                await asyncio.sleep(1)
    
    async def _get_next_task(self) -> Optional[AsyncTask]:
        """次のタスク取得（優先度順）"""
        # 優先度が高い順にキューをチェック
        for priority in sorted(TaskPriority, key=lambda p: p.value, reverse=True):
            queue = self.task_queues[priority]
            
            try:
                task = queue.get_nowait()
                return task
            except asyncio.QueueEmpty:
                continue
        
        return None
    
    async def _execute_task(self, task: AsyncTask):
        """タスク実行"""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        
        try:
            # タイムアウト設定
            if task.timeout_seconds:
                result = await asyncio.wait_for(
                    self._run_task_function(task),
                    timeout=task.timeout_seconds
                )
            else:
                result = await self._run_task_function(task)
            
            # 成功
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            self.stats['total_completed'] += 1
            
            self.logger.debug(f"タスク完了: {task.task_id}")
            
        except asyncio.TimeoutError:
            await self._handle_task_failure(task, Exception("タスクタイムアウト"))
            
        except Exception as e:
            await self._handle_task_failure(task, e)
            
        finally:
            # クリーンアップ
            self.running_tasks.pop(task.task_id, None)
            self.completed_tasks.append(task)
            self.semaphore.release()
    
    async def _run_task_function(self, task: AsyncTask):
        """タスク関数実行"""
        if asyncio.iscoroutinefunction(task.func):
            return await task.func(*task.args, **task.kwargs)
        else:
            # 同期関数を非同期実行
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, 
                lambda: task.func(*task.args, **task.kwargs)
            )
    
    async def _handle_task_failure(self, task: AsyncTask, error: Exception):
        """タスク失敗処理"""
        task.error = error
        
        # リトライ判定
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            self.stats['total_retries'] += 1
            
            # 指数バックオフでリトライ
            delay = min(2 ** task.retry_count, 60)  # 最大60秒
            await asyncio.sleep(delay)
            
            # リトライキューに再投入
            await self.task_queues[task.priority].put(task)
            
            self.logger.warning(
                f"タスクリトライ: {task.task_id} ({task.retry_count}/{task.max_retries})"
            )
        else:
            # リトライ上限に達した場合
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            self.stats['total_failed'] += 1
            
            self.logger.error(f"タスク失敗: {task.task_id} - {str(error)}")
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """タスク状態取得"""
        # 実行中タスク確認
        if task_id in self.running_tasks:
            return self.running_tasks[task_id].to_dict()
        
        # 完了タスク確認
        for task in self.completed_tasks:
            if task.task_id == task_id:
                return task.to_dict()
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報取得"""
        pending_count = sum(
            queue.qsize() for queue in self.task_queues.values()
        )
        
        return {
            'is_running': self.is_running,
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'running_tasks': len(self.running_tasks),
            'pending_tasks': pending_count,
            'completed_tasks': len(self.completed_tasks),
            'statistics': self.stats.copy()
        }


class ConnectionPool(Generic[T]):
    """コネクションプール"""
    
    def __init__(self, connection_factory: Callable[[], Awaitable[T]],
                 max_connections: int = 10,
                 min_connections: int = 2,
                 max_idle_time: float = 300.0,
                 connection_timeout: float = 30.0):
        
        self.connection_factory = connection_factory
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.max_idle_time = max_idle_time
        self.connection_timeout = connection_timeout
        
        self.available_connections: asyncio.Queue = asyncio.Queue(maxsize=max_connections)
        self.active_connections: Dict[int, Dict[str, Any]] = {}
        self.connection_counter = 0
        
        self.stats = {
            'created_connections': 0,
            'destroyed_connections': 0,
            'acquired_connections': 0,
            'released_connections': 0,
            'connection_errors': 0
        }
        
        self.logger = get_logger(__name__)
        self._maintenance_task = None
        self._is_running = False
    
    async def start(self):
        """コネクションプール開始"""
        if self._is_running:
            return
        
        self._is_running = True
        
        # 最小コネクション数を作成
        for _ in range(self.min_connections):
            try:
                await self._create_connection()
            except Exception as e:
                self.logger.error(f"初期コネクション作成エラー: {str(e)}")
        
        # メンテナンスタスク開始
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())
        
        self.logger.info(f"コネクションプール開始: {self.available_connections.qsize()}個のコネクション")
    
    async def stop(self):
        """コネクションプール停止"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # メンテナンスタスク停止
        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass
        
        # 全コネクション閉鎖
        while not self.available_connections.empty():
            try:
                conn_info = self.available_connections.get_nowait()
                await self._destroy_connection(conn_info)
            except asyncio.QueueEmpty:
                break
        
        # アクティブコネクション強制閉鎖
        for conn_info in list(self.active_connections.values()):
            await self._destroy_connection(conn_info)
        
        self.logger.info("コネクションプール停止")
    
    async def acquire_connection(self) -> T:
        """コネクション取得"""
        try:
            # 利用可能コネクション取得
            try:
                conn_info = self.available_connections.get_nowait()
            except asyncio.QueueEmpty:
                # 新規コネクション作成
                if len(self.active_connections) < self.max_connections:
                    conn_info = await self._create_connection()
                else:
                    # 制限に達している場合は待機
                    conn_info = await asyncio.wait_for(
                        self.available_connections.get(),
                        timeout=self.connection_timeout
                    )
            
            # アクティブに移動
            conn_id = conn_info['id']
            conn_info['acquired_at'] = time.time()
            self.active_connections[conn_id] = conn_info
            
            self.stats['acquired_connections'] += 1
            self.logger.debug(f"コネクション取得: {conn_id}")
            
            return conn_info['connection']
            
        except asyncio.TimeoutError:
            raise Exception("コネクション取得タイムアウト")
        except Exception as e:
            self.stats['connection_errors'] += 1
            raise Exception(f"コネクション取得エラー: {str(e)}")
    
    async def release_connection(self, connection: T):
        """コネクション返却"""
        # アクティブコネクションから検索
        conn_id = None
        for cid, conn_info in self.active_connections.items():
            if conn_info['connection'] is connection:
                conn_id = cid
                break
        
        if conn_id is None:
            self.logger.warning("不明なコネクションの返却試行")
            return
        
        conn_info = self.active_connections.pop(conn_id)
        conn_info['released_at'] = time.time()
        
        # プールに返却
        try:
            self.available_connections.put_nowait(conn_info)
            self.stats['released_connections'] += 1
            self.logger.debug(f"コネクション返却: {conn_id}")
        except asyncio.QueueFull:
            # プールが満杯の場合は破棄
            await self._destroy_connection(conn_info)
    
    async def _create_connection(self) -> Dict[str, Any]:
        """コネクション作成"""
        try:
            connection = await self.connection_factory()
            
            self.connection_counter += 1
            conn_info = {
                'id': self.connection_counter,
                'connection': connection,
                'created_at': time.time(),
                'last_used_at': time.time()
            }
            
            self.stats['created_connections'] += 1
            self.logger.debug(f"コネクション作成: {conn_info['id']}")
            
            return conn_info
            
        except Exception as e:
            self.stats['connection_errors'] += 1
            raise Exception(f"コネクション作成エラー: {str(e)}")
    
    async def _destroy_connection(self, conn_info: Dict[str, Any]):
        """コネクション破棄"""
        try:
            connection = conn_info['connection']
            
            # コネクション固有の閉鎖処理
            if hasattr(connection, 'close'):
                if asyncio.iscoroutinefunction(connection.close):
                    await connection.close()
                else:
                    connection.close()
            
            self.stats['destroyed_connections'] += 1
            self.logger.debug(f"コネクション破棄: {conn_info['id']}")
            
        except Exception as e:
            self.logger.error(f"コネクション破棄エラー: {str(e)}")
    
    async def _maintenance_loop(self):
        """メンテナンスループ"""
        while self._is_running:
            try:
                await self._cleanup_idle_connections()
                await asyncio.sleep(60)  # 1分間隔
            except Exception as e:
                self.logger.error(f"メンテナンスエラー: {str(e)}")
    
    async def _cleanup_idle_connections(self):
        """アイドルコネクションクリーンアップ"""
        current_time = time.time()
        expired_connections = []
        
        # 利用可能コネクションから期限切れを検索
        temp_queue = asyncio.Queue()
        
        while not self.available_connections.empty():
            try:
                conn_info = self.available_connections.get_nowait()
                
                if (current_time - conn_info.get('last_used_at', 0)) > self.max_idle_time:
                    expired_connections.append(conn_info)
                else:
                    await temp_queue.put(conn_info)
            except asyncio.QueueEmpty:
                break
        
        # 期限切れでないコネクションを戻す
        while not temp_queue.empty():
            conn_info = await temp_queue.get()
            await self.available_connections.put(conn_info)
        
        # 期限切れコネクション破棄
        for conn_info in expired_connections:
            await self._destroy_connection(conn_info)
        
        if expired_connections:
            self.logger.info(f"アイドルコネクションクリーンアップ: {len(expired_connections)}個")
    
    async def get_connection_context(self):
        """コネクションコンテキスト"""
        class ConnectionContext:
            def __init__(self, pool):
                self.pool = pool
                self.connection = None
            
            async def __aenter__(self):
                self.connection = await self.pool.acquire_connection()
                return self.connection
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self.connection:
                    await self.pool.release_connection(self.connection)
        
        return ConnectionContext(self)
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報取得"""
        return {
            'max_connections': self.max_connections,
            'min_connections': self.min_connections,
            'available_connections': self.available_connections.qsize(),
            'active_connections': len(self.active_connections),
            'total_connections': self.available_connections.qsize() + len(self.active_connections),
            'statistics': self.stats.copy()
        }


class BatchProcessor(Generic[T, R]):
    """バッチ処理最適化"""
    
    def __init__(self, 
                 batch_func: Callable[[List[T]], Awaitable[List[R]]],
                 batch_size: int = 100,
                 max_wait_time: float = 1.0,
                 max_concurrent_batches: int = 5):
        
        self.batch_func = batch_func
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.max_concurrent_batches = max_concurrent_batches
        
        self.pending_items: List[Dict[str, Any]] = []
        self.pending_futures: List[asyncio.Future] = []
        
        self.semaphore = asyncio.Semaphore(max_concurrent_batches)
        self.lock = asyncio.Lock()
        
        self.stats = {
            'total_items': 0,
            'total_batches': 0,
            'avg_batch_size': 0,
            'total_processing_time': 0
        }
        
        self.logger = get_logger(__name__)
        self._processor_task = None
        self._is_running = False
    
    async def start(self):
        """バッチプロセッサー開始"""
        if self._is_running:
            return
        
        self._is_running = True
        self._processor_task = asyncio.create_task(self._processor_loop())
        self.logger.info("バッチプロセッサー開始")
    
    async def stop(self):
        """バッチプロセッサー停止"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # 残りのアイテムを処理
        if self.pending_items:
            await self._process_batch()
        
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("バッチプロセッサー停止")
    
    async def submit_item(self, item: T) -> R:
        """アイテム投入"""
        future = asyncio.Future()
        
        async with self.lock:
            self.pending_items.append({
                'item': item,
                'future': future,
                'submitted_at': time.time()
            })
            self.pending_futures.append(future)
            
            # バッチサイズに達した場合は即座に処理
            if len(self.pending_items) >= self.batch_size:
                asyncio.create_task(self._process_batch())
        
        return await future
    
    async def _processor_loop(self):
        """プロセッサーループ"""
        while self._is_running:
            try:
                await asyncio.sleep(self.max_wait_time)
                
                if self.pending_items:
                    await self._process_batch()
                    
            except Exception as e:
                self.logger.error(f"バッチプロセッサーエラー: {str(e)}")
    
    async def _process_batch(self):
        """バッチ処理実行"""
        async with self.lock:
            if not self.pending_items:
                return
            
            # 処理対象アイテムを取得
            items_to_process = self.pending_items[:self.batch_size]
            self.pending_items = self.pending_items[self.batch_size:]
        
        await self.semaphore.acquire()
        try:
            start_time = time.time()
            
            # バッチ関数実行
            items = [item_info['item'] for item_info in items_to_process]
            results = await self.batch_func(items)
            
            # 結果を対応するFutureに設定
            for item_info, result in zip(items_to_process, results):
                if not item_info['future'].done():
                    item_info['future'].set_result(result)
            
            # 統計更新
            processing_time = time.time() - start_time
            self.stats['total_items'] += len(items)
            self.stats['total_batches'] += 1
            self.stats['avg_batch_size'] = self.stats['total_items'] / self.stats['total_batches']
            self.stats['total_processing_time'] += processing_time
            
            self.logger.debug(
                f"バッチ処理完了: {len(items)}アイテム, {processing_time:.2f}秒"
            )
            
        except Exception as e:
            # エラーの場合は全Futureにエラーを設定
            for item_info in items_to_process:
                if not item_info['future'].done():
                    item_info['future'].set_exception(e)
            
            self.logger.error(f"バッチ処理エラー: {str(e)}")
            
        finally:
            self.semaphore.release()
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報取得"""
        return {
            'is_running': self._is_running,
            'batch_size': self.batch_size,
            'max_wait_time': self.max_wait_time,
            'pending_items': len(self.pending_items),
            'statistics': self.stats.copy()
        }


class WorkerPool:
    """ワーカープール"""
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.logger = get_logger(__name__)
    
    async def run_in_executor(self, func: Callable, *args, **kwargs):
        """エグゼキューターでの実行"""
        loop = asyncio.get_event_loop()
        
        if kwargs:
            # kwargsがある場合は部分適用
            import functools
            bound_func = functools.partial(func, **kwargs)
            return await loop.run_in_executor(self.executor, bound_func, *args)
        else:
            return await loop.run_in_executor(self.executor, func, *args)
    
    def shutdown(self, wait: bool = True):
        """ワーカープール終了"""
        self.executor.shutdown(wait=wait)
        self.logger.info("ワーカープール終了")


class AsyncOptimizer:
    """非同期処理最適化管理クラス"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger(__name__)
        
        # コンポーネント
        self.task_scheduler = TaskScheduler(
            max_concurrent_tasks=self.config_manager.get("async.max_concurrent_tasks", 10)
        )
        
        self.connection_pools: Dict[str, ConnectionPool] = {}
        self.batch_processors: Dict[str, BatchProcessor] = {}
        self.worker_pool = WorkerPool(
            max_workers=self.config_manager.get("async.max_workers", 10)
        )
        
        self.is_running = False
    
    async def start(self):
        """非同期最適化開始"""
        if self.is_running:
            return
        
        await self.task_scheduler.start()
        
        for pool in self.connection_pools.values():
            await pool.start()
        
        for processor in self.batch_processors.values():
            await processor.start()
        
        self.is_running = True
        self.logger.info("非同期処理最適化開始")
    
    async def stop(self):
        """非同期最適化停止"""
        if not self.is_running:
            return
        
        await self.task_scheduler.stop()
        
        for pool in self.connection_pools.values():
            await pool.stop()
        
        for processor in self.batch_processors.values():
            await processor.stop()
        
        self.worker_pool.shutdown()
        
        self.is_running = False
        self.logger.info("非同期処理最適化停止")
    
    def create_connection_pool(self, name: str, connection_factory: Callable,
                              max_connections: int = 10) -> ConnectionPool:
        """コネクションプール作成"""
        pool = ConnectionPool(
            connection_factory=connection_factory,
            max_connections=max_connections
        )
        self.connection_pools[name] = pool
        
        if self.is_running:
            asyncio.create_task(pool.start())
        
        return pool
    
    def create_batch_processor(self, name: str, batch_func: Callable,
                              batch_size: int = 100) -> BatchProcessor:
        """バッチプロセッサー作成"""
        processor = BatchProcessor(
            batch_func=batch_func,
            batch_size=batch_size
        )
        self.batch_processors[name] = processor
        
        if self.is_running:
            asyncio.create_task(processor.start())
        
        return processor
    
    async def submit_task(self, func: Callable, *args, **kwargs) -> str:
        """タスク投入"""
        return await self.task_scheduler.submit_task(func, *args, **kwargs)
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """最適化概要取得"""
        return {
            'is_running': self.is_running,
            'task_scheduler': self.task_scheduler.get_statistics(),
            'connection_pools': {
                name: pool.get_statistics()
                for name, pool in self.connection_pools.items()
            },
            'batch_processors': {
                name: processor.get_statistics()
                for name, processor in self.batch_processors.items()
            },
            'worker_pool_max_workers': self.worker_pool.max_workers
        }


# グローバル非同期最適化インスタンス
_global_async_optimizer: Optional[AsyncOptimizer] = None


def get_async_optimizer() -> AsyncOptimizer:
    """グローバル非同期最適化インスタンス取得"""
    global _global_async_optimizer
    if _global_async_optimizer is None:
        _global_async_optimizer = AsyncOptimizer()
    return _global_async_optimizer