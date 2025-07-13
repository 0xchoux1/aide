"""
AIDE パフォーマンスベンチマークシステム

システム全体の性能測定と比較分析
"""

import time
import asyncio
import statistics
import gc
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import json
from pathlib import Path

from ..config import get_config_manager
from ..logging import get_logger


@dataclass
class BenchmarkResult:
    """ベンチマーク結果"""
    test_name: str
    duration_ms: float
    memory_usage_mb: float
    success: bool
    iterations: int
    avg_iteration_ms: float
    min_iteration_ms: float
    max_iteration_ms: float
    std_dev_ms: float
    throughput_ops_per_sec: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


@dataclass
class BenchmarkSuite:
    """ベンチマークスイート"""
    suite_name: str
    timestamp: float
    total_duration_ms: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    results: List[BenchmarkResult]
    system_info: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['results'] = [r.to_dict() for r in self.results]
        return data


class PerformanceBenchmark:
    """パフォーマンスベンチマークツール"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger(__name__)
        
        # ベンチマーク設定
        self.default_iterations = self.config_manager.get("benchmark.default_iterations", 10)
        self.warmup_iterations = self.config_manager.get("benchmark.warmup_iterations", 3)
        self.timeout_seconds = self.config_manager.get("benchmark.timeout_seconds", 60)
        
        # 結果保存設定
        self.save_results = self.config_manager.get("benchmark.save_results", True)
        self.results_dir = Path(self.config_manager.get("benchmark.results_dir", "benchmark_results"))
        
        # 現在のベンチマーク結果
        self.current_results: List[BenchmarkResult] = []
        
        # システム情報
        self.system_info = self._collect_system_info()

    def _collect_system_info(self) -> Dict[str, Any]:
        """システム情報収集"""
        import platform
        import sys
        
        try:
            import psutil
            cpu_count = psutil.cpu_count()
            memory_total = psutil.virtual_memory().total / (1024**3)  # GB
        except ImportError:
            cpu_count = "unknown"
            memory_total = "unknown"
        
        return {
            'platform': platform.platform(),
            'python_version': sys.version,
            'cpu_count': cpu_count,
            'memory_total_gb': memory_total,
            'timestamp': time.time()
        }

    def benchmark_function(self, func: Callable, iterations: int = None, 
                          warmup: int = None, name: str = None) -> BenchmarkResult:
        """関数ベンチマーク実行"""
        iterations = iterations or self.default_iterations
        warmup = warmup or self.warmup_iterations
        name = name or func.__name__
        
        self.logger.info(f"ベンチマーク開始: {name} ({iterations}回実行)")
        
        try:
            # ウォームアップ実行
            for _ in range(warmup):
                func()
            
            # GC実行でメモリ状態リセット
            gc.collect()
            
            # メモリ使用量測定開始
            try:
                import psutil
                process = psutil.Process()
                memory_before = process.memory_info().rss / (1024**2)  # MB
            except ImportError:
                memory_before = 0
            
            # ベンチマーク実行
            durations = []
            start_time = time.perf_counter()
            
            for i in range(iterations):
                iteration_start = time.perf_counter()
                func()
                iteration_end = time.perf_counter()
                
                duration = (iteration_end - iteration_start) * 1000  # ms
                durations.append(duration)
                
                # タイムアウトチェック
                if (time.perf_counter() - start_time) > self.timeout_seconds:
                    self.logger.warning(f"ベンチマークタイムアウト: {name}")
                    break
            
            total_duration = (time.perf_counter() - start_time) * 1000  # ms
            
            # メモリ使用量測定終了
            try:
                memory_after = process.memory_info().rss / (1024**2)  # MB
                memory_usage = memory_after - memory_before
            except (ImportError, NameError):
                memory_usage = 0
            
            # 統計計算
            avg_duration = statistics.mean(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            std_dev = statistics.stdev(durations) if len(durations) > 1 else 0
            throughput = len(durations) / (total_duration / 1000)  # ops/sec
            
            result = BenchmarkResult(
                test_name=name,
                duration_ms=total_duration,
                memory_usage_mb=memory_usage,
                success=True,
                iterations=len(durations),
                avg_iteration_ms=avg_duration,
                min_iteration_ms=min_duration,
                max_iteration_ms=max_duration,
                std_dev_ms=std_dev,
                throughput_ops_per_sec=throughput
            )
            
            self.current_results.append(result)
            self.logger.info(f"ベンチマーク完了: {name} - {avg_duration:.2f}ms平均")
            
            return result
            
        except Exception as e:
            error_result = BenchmarkResult(
                test_name=name,
                duration_ms=0,
                memory_usage_mb=0,
                success=False,
                iterations=0,
                avg_iteration_ms=0,
                min_iteration_ms=0,
                max_iteration_ms=0,
                std_dev_ms=0,
                throughput_ops_per_sec=0,
                error_message=str(e)
            )
            
            self.current_results.append(error_result)
            self.logger.error(f"ベンチマークエラー: {name} - {str(e)}")
            
            return error_result

    async def benchmark_async_function(self, func: Callable, iterations: int = None, 
                                     warmup: int = None, name: str = None) -> BenchmarkResult:
        """非同期関数ベンチマーク実行"""
        iterations = iterations or self.default_iterations
        warmup = warmup or self.warmup_iterations
        name = name or func.__name__
        
        self.logger.info(f"非同期ベンチマーク開始: {name} ({iterations}回実行)")
        
        try:
            # ウォームアップ実行
            for _ in range(warmup):
                await func()
            
            # GC実行
            gc.collect()
            
            # メモリ使用量測定開始
            try:
                import psutil
                process = psutil.Process()
                memory_before = process.memory_info().rss / (1024**2)  # MB
            except ImportError:
                memory_before = 0
            
            # ベンチマーク実行
            durations = []
            start_time = time.perf_counter()
            
            for i in range(iterations):
                iteration_start = time.perf_counter()
                await func()
                iteration_end = time.perf_counter()
                
                duration = (iteration_end - iteration_start) * 1000  # ms
                durations.append(duration)
                
                # タイムアウトチェック
                if (time.perf_counter() - start_time) > self.timeout_seconds:
                    self.logger.warning(f"非同期ベンチマークタイムアウト: {name}")
                    break
            
            total_duration = (time.perf_counter() - start_time) * 1000  # ms
            
            # メモリ使用量測定終了
            try:
                memory_after = process.memory_info().rss / (1024**2)  # MB
                memory_usage = memory_after - memory_before
            except (ImportError, NameError):
                memory_usage = 0
            
            # 統計計算
            avg_duration = statistics.mean(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            std_dev = statistics.stdev(durations) if len(durations) > 1 else 0
            throughput = len(durations) / (total_duration / 1000)  # ops/sec
            
            result = BenchmarkResult(
                test_name=name,
                duration_ms=total_duration,
                memory_usage_mb=memory_usage,
                success=True,
                iterations=len(durations),
                avg_iteration_ms=avg_duration,
                min_iteration_ms=min_duration,
                max_iteration_ms=max_duration,
                std_dev_ms=std_dev,
                throughput_ops_per_sec=throughput
            )
            
            self.current_results.append(result)
            self.logger.info(f"非同期ベンチマーク完了: {name} - {avg_duration:.2f}ms平均")
            
            return result
            
        except Exception as e:
            error_result = BenchmarkResult(
                test_name=name,
                duration_ms=0,
                memory_usage_mb=0,
                success=False,
                iterations=0,
                avg_iteration_ms=0,
                min_iteration_ms=0,
                max_iteration_ms=0,
                std_dev_ms=0,
                throughput_ops_per_sec=0,
                error_message=str(e)
            )
            
            self.current_results.append(error_result)
            self.logger.error(f"非同期ベンチマークエラー: {name} - {str(e)}")
            
            return error_result

    def benchmark_load_test(self, func: Callable, concurrent_count: int = 10, 
                           duration_seconds: int = 30, name: str = None) -> BenchmarkResult:
        """負荷テストベンチマーク"""
        name = name or f"{func.__name__}_load_test"
        self.logger.info(f"負荷テスト開始: {name} ({concurrent_count}並行, {duration_seconds}秒)")
        
        results = []
        errors = []
        stop_event = threading.Event()
        
        def worker():
            """ワーカースレッド"""
            while not stop_event.is_set():
                try:
                    start_time = time.perf_counter()
                    func()
                    end_time = time.perf_counter()
                    results.append((end_time - start_time) * 1000)  # ms
                except Exception as e:
                    errors.append(str(e))
        
        try:
            # メモリ使用量測定開始
            try:
                import psutil
                process = psutil.Process()
                memory_before = process.memory_info().rss / (1024**2)  # MB
            except ImportError:
                memory_before = 0
            
            # ワーカースレッド開始
            threads = []
            start_time = time.perf_counter()
            
            for _ in range(concurrent_count):
                thread = threading.Thread(target=worker, daemon=True)
                thread.start()
                threads.append(thread)
            
            # 指定時間待機
            time.sleep(duration_seconds)
            
            # 停止シグナル送信
            stop_event.set()
            
            # 全スレッド終了待機
            for thread in threads:
                thread.join(timeout=1.0)
            
            total_duration = (time.perf_counter() - start_time) * 1000  # ms
            
            # メモリ使用量測定終了
            try:
                memory_after = process.memory_info().rss / (1024**2)  # MB
                memory_usage = memory_after - memory_before
            except (ImportError, NameError):
                memory_usage = 0
            
            # 統計計算
            if results:
                avg_duration = statistics.mean(results)
                min_duration = min(results)
                max_duration = max(results)
                std_dev = statistics.stdev(results) if len(results) > 1 else 0
                throughput = len(results) / (duration_seconds)  # ops/sec
            else:
                avg_duration = min_duration = max_duration = std_dev = throughput = 0
            
            result = BenchmarkResult(
                test_name=name,
                duration_ms=total_duration,
                memory_usage_mb=memory_usage,
                success=len(errors) == 0,
                iterations=len(results),
                avg_iteration_ms=avg_duration,
                min_iteration_ms=min_duration,
                max_iteration_ms=max_duration,
                std_dev_ms=std_dev,
                throughput_ops_per_sec=throughput,
                metadata={
                    'concurrent_count': concurrent_count,
                    'duration_seconds': duration_seconds,
                    'error_count': len(errors),
                    'errors': errors[:10]  # 最初の10個のエラーのみ保存
                }
            )
            
            self.current_results.append(result)
            self.logger.info(f"負荷テスト完了: {name} - {throughput:.1f} ops/sec")
            
            return result
            
        except Exception as e:
            error_result = BenchmarkResult(
                test_name=name,
                duration_ms=0,
                memory_usage_mb=0,
                success=False,
                iterations=0,
                avg_iteration_ms=0,
                min_iteration_ms=0,
                max_iteration_ms=0,
                std_dev_ms=0,
                throughput_ops_per_sec=0,
                error_message=str(e)
            )
            
            self.current_results.append(error_result)
            self.logger.error(f"負荷テストエラー: {name} - {str(e)}")
            
            return error_result

    def create_benchmark_suite(self, suite_name: str = None) -> BenchmarkSuite:
        """ベンチマークスイート作成"""
        suite_name = suite_name or f"benchmark_suite_{int(time.time())}"
        
        # 統計計算
        total_duration = sum(r.duration_ms for r in self.current_results)
        total_tests = len(self.current_results)
        passed_tests = len([r for r in self.current_results if r.success])
        failed_tests = total_tests - passed_tests
        
        suite = BenchmarkSuite(
            suite_name=suite_name,
            timestamp=time.time(),
            total_duration_ms=total_duration,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            results=self.current_results.copy(),
            system_info=self.system_info
        )
        
        # 結果保存
        if self.save_results:
            self._save_benchmark_suite(suite)
        
        # 現在の結果クリア
        self.current_results.clear()
        
        return suite

    def _save_benchmark_suite(self, suite: BenchmarkSuite):
        """ベンチマークスイート保存"""
        try:
            self.results_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.fromtimestamp(suite.timestamp).strftime("%Y%m%d_%H%M%S")
            filename = f"{suite.suite_name}_{timestamp}.json"
            filepath = self.results_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(suite.to_dict(), f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"ベンチマーク結果保存: {filepath}")
            
        except Exception as e:
            self.logger.error(f"ベンチマーク結果保存エラー: {str(e)}")

    def load_benchmark_suite(self, filepath: Path) -> Optional[BenchmarkSuite]:
        """ベンチマークスイート読み込み"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # BenchmarkResultオブジェクト復元
            results = []
            for result_data in data['results']:
                result = BenchmarkResult(**result_data)
                results.append(result)
            
            # BenchmarkSuiteオブジェクト復元
            suite_data = data.copy()
            suite_data['results'] = results
            suite = BenchmarkSuite(**suite_data)
            
            return suite
            
        except Exception as e:
            self.logger.error(f"ベンチマークスイート読み込みエラー: {str(e)}")
            return None

    def compare_benchmark_suites(self, suite1: BenchmarkSuite, 
                                suite2: BenchmarkSuite) -> Dict[str, Any]:
        """ベンチマークスイート比較"""
        comparison = {
            'suite1_name': suite1.suite_name,
            'suite2_name': suite2.suite_name,
            'comparison_timestamp': time.time(),
            'test_comparisons': {},
            'summary': {}
        }
        
        # テスト別比較
        suite1_tests = {r.test_name: r for r in suite1.results}
        suite2_tests = {r.test_name: r for r in suite2.results}
        
        common_tests = set(suite1_tests.keys()) & set(suite2_tests.keys())
        
        for test_name in common_tests:
            result1 = suite1_tests[test_name]
            result2 = suite2_tests[test_name]
            
            if result1.success and result2.success:
                duration_change = ((result2.avg_iteration_ms - result1.avg_iteration_ms) / 
                                 result1.avg_iteration_ms) * 100
                throughput_change = ((result2.throughput_ops_per_sec - result1.throughput_ops_per_sec) / 
                                   result1.throughput_ops_per_sec) * 100
                memory_change = result2.memory_usage_mb - result1.memory_usage_mb
                
                comparison['test_comparisons'][test_name] = {
                    'duration_change_percent': duration_change,
                    'throughput_change_percent': throughput_change,
                    'memory_change_mb': memory_change,
                    'improved': duration_change < -5 or throughput_change > 5,  # 5%以上の改善
                    'degraded': duration_change > 5 or throughput_change < -5   # 5%以上の劣化
                }
        
        # サマリー計算
        comparisons = list(comparison['test_comparisons'].values())
        if comparisons:
            avg_duration_change = statistics.mean([c['duration_change_percent'] for c in comparisons])
            avg_throughput_change = statistics.mean([c['throughput_change_percent'] for c in comparisons])
            total_memory_change = sum([c['memory_change_mb'] for c in comparisons])
            
            improved_count = len([c for c in comparisons if c['improved']])
            degraded_count = len([c for c in comparisons if c['degraded']])
            
            comparison['summary'] = {
                'total_common_tests': len(common_tests),
                'avg_duration_change_percent': avg_duration_change,
                'avg_throughput_change_percent': avg_throughput_change,
                'total_memory_change_mb': total_memory_change,
                'improved_tests': improved_count,
                'degraded_tests': degraded_count,
                'stable_tests': len(common_tests) - improved_count - degraded_count,
                'overall_improvement': improved_count > degraded_count
            }
        
        return comparison

    def generate_benchmark_report(self, suite: BenchmarkSuite) -> str:
        """ベンチマークレポート生成"""
        report = []
        report.append(f"# ベンチマークレポート: {suite.suite_name}")
        report.append(f"実行日時: {datetime.fromtimestamp(suite.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"総実行時間: {suite.total_duration_ms:.2f}ms")
        report.append(f"テスト数: {suite.total_tests} (成功: {suite.passed_tests}, 失敗: {suite.failed_tests})")
        report.append("")
        
        # システム情報
        report.append("## システム情報")
        report.append(f"プラットフォーム: {suite.system_info.get('platform', 'unknown')}")
        report.append(f"Python バージョン: {suite.system_info.get('python_version', 'unknown')}")
        report.append(f"CPU コア数: {suite.system_info.get('cpu_count', 'unknown')}")
        report.append(f"メモリ容量: {suite.system_info.get('memory_total_gb', 'unknown')}GB")
        report.append("")
        
        # テスト結果詳細
        report.append("## テスト結果詳細")
        
        # 成功したテストを性能順でソート
        successful_tests = [r for r in suite.results if r.success]
        successful_tests.sort(key=lambda x: x.avg_iteration_ms)
        
        for result in successful_tests:
            report.append(f"### {result.test_name}")
            report.append(f"- 平均実行時間: {result.avg_iteration_ms:.2f}ms")
            report.append(f"- スループット: {result.throughput_ops_per_sec:.1f} ops/sec")
            report.append(f"- メモリ使用量: {result.memory_usage_mb:.2f}MB")
            report.append(f"- 実行回数: {result.iterations}")
            report.append(f"- 標準偏差: {result.std_dev_ms:.2f}ms")
            report.append("")
        
        # 失敗したテスト
        failed_tests = [r for r in suite.results if not r.success]
        if failed_tests:
            report.append("## 失敗テスト")
            for result in failed_tests:
                report.append(f"### {result.test_name}")
                report.append(f"エラー: {result.error_message}")
                report.append("")
        
        return "\n".join(report)


# グローバルベンチマークインスタンス
_global_benchmark: Optional[PerformanceBenchmark] = None


def get_performance_benchmark() -> PerformanceBenchmark:
    """グローバルベンチマークインスタンス取得"""
    global _global_benchmark
    if _global_benchmark is None:
        _global_benchmark = PerformanceBenchmark()
    return _global_benchmark


# 便利デコレータ
def benchmark(iterations: int = None, name: str = None):
    """ベンチマークデコレータ"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            benchmark_tool = get_performance_benchmark()
            
            # 引数付きの場合は関数をラップ
            def benchmark_func():
                return func(*args, **kwargs)
            
            benchmark_tool.benchmark_function(
                benchmark_func, 
                iterations=iterations, 
                name=name or func.__name__
            )
            
            # 元の結果も返す
            return func(*args, **kwargs)
        
        return wrapper
    return decorator