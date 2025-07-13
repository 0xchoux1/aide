"""
テスト用モジュール

統合テストで使用されるサンプルクラスと関数を提供します。
"""

import time
import random
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class TestData:
    """テストデータクラス"""
    id: int
    name: str
    value: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TestClass:
    """テスト用クラス"""
    
    def __init__(self, name: str = "test"):
        self.name = name
        self.data: List[TestData] = []
        self.processed = False
    
    def add_data(self, data: TestData):
        """データ追加"""
        self.data.append(data)
    
    def process_data(self) -> Dict[str, Any]:
        """データ処理"""
        if not self.data:
            return {"processed": 0, "total": 0}
        
        total = len(self.data)
        processed = 0
        
        for item in self.data:
            # 簡単な処理をシミュレート
            if item.value > 0:
                processed += 1
        
        self.processed = True
        
        return {
            "processed": processed,
            "total": total,
            "success_rate": processed / total if total > 0 else 0
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報取得"""
        if not self.processed:
            return {"error": "データが未処理です"}
        
        values = [item.value for item in self.data]
        
        return {
            "count": len(values),
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "avg": sum(values) / len(values) if values else 0
        }
    
    def simulate_error(self, error_type: str = "generic"):
        """エラーシミュレーション"""
        if error_type == "value":
            raise ValueError("テスト用値エラー")
        elif error_type == "runtime":
            raise RuntimeError("テスト用ランタイムエラー")
        elif error_type == "connection":
            raise ConnectionError("テスト用接続エラー")
        else:
            raise Exception("テスト用一般エラー")


def slow_function(duration: float = 1.0) -> str:
    """実行時間の長い関数（テスト用）"""
    time.sleep(duration)
    return f"処理完了 (所要時間: {duration}秒)"


def generate_test_data(count: int = 10) -> List[TestData]:
    """テストデータ生成"""
    data = []
    
    for i in range(count):
        item = TestData(
            id=i,
            name=f"test_item_{i}",
            value=random.uniform(-10, 100),
            metadata={
                "created_at": time.time(),
                "category": random.choice(["A", "B", "C"]),
                "priority": random.randint(1, 5)
            }
        )
        data.append(item)
    
    return data


def memory_intensive_function(size: int = 1000000) -> List[int]:
    """メモリを大量に使用する関数（テスト用）"""
    return list(range(size))


def cpu_intensive_function(iterations: int = 1000000) -> int:
    """CPU集約的な関数（テスト用）"""
    result = 0
    for i in range(iterations):
        result += i * i
    return result


class DataProcessor:
    """データ処理クラス（テスト用）"""
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
    
    def process_item(self, item: TestData) -> Dict[str, Any]:
        """単一アイテム処理"""
        try:
            # 処理をシミュレート
            result = {
                "id": item.id,
                "processed_value": item.value * 2,
                "status": "success"
            }
            
            self.processed_count += 1
            return result
            
        except Exception as e:
            self.error_count += 1
            return {
                "id": getattr(item, 'id', 'unknown'),
                "error": str(e),
                "status": "error"
            }
    
    def process_batch(self, items: List[TestData]) -> List[Dict[str, Any]]:
        """バッチ処理"""
        results = []
        
        for item in items:
            result = self.process_item(item)
            results.append(result)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """処理統計"""
        total = self.processed_count + self.error_count
        
        return {
            "processed": self.processed_count,
            "errors": self.error_count,
            "total": total,
            "success_rate": self.processed_count / total if total > 0 else 0
        }


# テスト用のモックデータ
SAMPLE_CONFIG = {
    "test_mode": True,
    "debug": True,
    "timeout": 30,
    "max_retries": 3
}

SAMPLE_METRICS = {
    "cpu_usage": 45.2,
    "memory_usage": 68.7,
    "disk_usage": 23.1,
    "network_latency": 12.5
}