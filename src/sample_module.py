"""
サンプルモジュール

統合テストで使用されるサンプルクラスと関数を提供します。
"""

import time
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ProcessingResult:
    """処理結果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataProcessor:
    """データ処理クラス"""
    
    def __init__(self, name: str = "default_processor"):
        self.name = name
        self.processed_items = 0
        self.error_count = 0
        self.start_time = time.time()
    
    def process_item(self, item: Any) -> ProcessingResult:
        """単一アイテム処理"""
        start_time = time.time()
        
        try:
            # 処理をシミュレート
            if isinstance(item, (int, float)):
                processed_data = item * 2
            elif isinstance(item, str):
                processed_data = item.upper()
            elif isinstance(item, dict):
                processed_data = {k: v for k, v in item.items() if v is not None}
            else:
                processed_data = str(item)
            
            self.processed_items += 1
            duration = time.time() - start_time
            
            return ProcessingResult(
                success=True,
                data=processed_data,
                duration=duration,
                metadata={
                    "processor": self.name,
                    "item_type": type(item).__name__,
                    "processed_at": time.time()
                }
            )
            
        except Exception as e:
            self.error_count += 1
            duration = time.time() - start_time
            
            return ProcessingResult(
                success=False,
                error=str(e),
                duration=duration,
                metadata={
                    "processor": self.name,
                    "error_type": type(e).__name__,
                    "failed_at": time.time()
                }
            )
    
    async def process_item_async(self, item: Any) -> ProcessingResult:
        """非同期単一アイテム処理"""
        # 非同期処理をシミュレート
        await asyncio.sleep(0.1)
        return self.process_item(item)
    
    def process_batch(self, items: List[Any]) -> List[ProcessingResult]:
        """バッチ処理"""
        results = []
        
        for item in items:
            result = self.process_item(item)
            results.append(result)
        
        return results
    
    async def process_batch_async(self, items: List[Any]) -> List[ProcessingResult]:
        """非同期バッチ処理"""
        tasks = [self.process_item_async(item) for item in items]
        return await asyncio.gather(*tasks)
    
    def get_statistics(self) -> Dict[str, Any]:
        """処理統計取得"""
        total_items = self.processed_items + self.error_count
        runtime = time.time() - self.start_time
        
        return {
            "processor_name": self.name,
            "processed_items": self.processed_items,
            "error_count": self.error_count,
            "total_items": total_items,
            "success_rate": self.processed_items / total_items if total_items > 0 else 0,
            "runtime_seconds": runtime,
            "throughput": total_items / runtime if runtime > 0 else 0
        }
    
    def reset_statistics(self):
        """統計リセット"""
        self.processed_items = 0
        self.error_count = 0
        self.start_time = time.time()


def slow_function(duration: float = 2.0, should_fail: bool = False) -> str:
    """実行時間の長い関数"""
    time.sleep(duration)
    
    if should_fail:
        raise RuntimeError(f"意図的なエラー (所要時間: {duration}秒)")
    
    return f"処理完了 (所要時間: {duration}秒)"


async def slow_async_function(duration: float = 2.0, should_fail: bool = False) -> str:
    """実行時間の長い非同期関数"""
    await asyncio.sleep(duration)
    
    if should_fail:
        raise RuntimeError(f"意図的な非同期エラー (所要時間: {duration}秒)")
    
    return f"非同期処理完了 (所要時間: {duration}秒)"


def memory_intensive_operation(size: int = 1000000) -> List[int]:
    """メモリ集約的な操作"""
    # 大きなリストを作成
    data = list(range(size))
    
    # 何らかの処理をシミュレート
    processed = [x * 2 for x in data if x % 2 == 0]
    
    return processed


def cpu_intensive_operation(iterations: int = 1000000) -> int:
    """CPU集約的な操作"""
    result = 0
    
    for i in range(iterations):
        result += i ** 2
    
    return result


class ResourceIntensiveProcessor:
    """リソース集約的な処理クラス"""
    
    def __init__(self):
        self.cache = {}
        self.computation_count = 0
    
    def fibonacci(self, n: int) -> int:
        """フィボナッチ数列計算（再帰）"""
        self.computation_count += 1
        
        if n in self.cache:
            return self.cache[n]
        
        if n <= 1:
            result = n
        else:
            result = self.fibonacci(n - 1) + self.fibonacci(n - 2)
        
        self.cache[n] = result
        return result
    
    def prime_check(self, n: int) -> bool:
        """素数判定"""
        if n < 2:
            return False
        
        for i in range(2, int(n ** 0.5) + 1):
            if n % i == 0:
                return False
        
        return True
    
    def find_primes(self, limit: int) -> List[int]:
        """指定範囲の素数を検索"""
        primes = []
        
        for num in range(2, limit + 1):
            if self.prime_check(num):
                primes.append(num)
        
        return primes
    
    def clear_cache(self):
        """キャッシュクリア"""
        self.cache.clear()
        self.computation_count = 0


# テスト用のサンプルデータ
SAMPLE_DATA = [
    {"id": 1, "name": "Alice", "score": 85},
    {"id": 2, "name": "Bob", "score": 92},
    {"id": 3, "name": "Charlie", "score": 78},
    {"id": 4, "name": "Diana", "score": 96},
    {"id": 5, "name": "Eve", "score": 88}
]

SAMPLE_NUMBERS = [1, 2, 3, 4, 5, 10, 15, 20, 25, 30]

SAMPLE_STRINGS = [
    "hello world",
    "sample text",
    "test string",
    "processing data",
    "integration test"
]