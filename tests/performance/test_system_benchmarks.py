"""
AIDE システム全体ベンチマークテスト

主要コンポーネントのパフォーマンス測定
"""

import pytest
import asyncio
import time
import tempfile
import shutil
from unittest.mock import Mock, patch
from pathlib import Path

from src.optimization.benchmark_system import PerformanceBenchmark, get_performance_benchmark
from src.self_improvement.diagnostics import SystemDiagnostics
from src.self_improvement.improvement_engine import ImprovementEngine
from src.self_improvement.autonomous_implementation import AutonomousImplementation
from src.self_improvement.quality_assurance import QualityAssurance
from src.config.config_manager import ConfigManager
from src.dashboard.metrics_collector import MetricsCollector
from src.optimization.memory_optimizer import MemoryOptimizer
from src.optimization.performance_profiler import PerformanceProfiler
from src.optimization.async_optimizer import AsyncOptimizer


class TestSystemBenchmarks:
    """システムベンチマークテスト"""

    @pytest.fixture
    def temp_workspace(self):
        """テスト用ワークスペース"""
        temp_dir = tempfile.mkdtemp()
        workspace = Path(temp_dir)
        
        # 必要なディレクトリ作成
        (workspace / 'benchmark_results').mkdir()
        (workspace / 'config').mkdir()
        (workspace / 'logs').mkdir()
        
        yield workspace
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def benchmark_tool(self, temp_workspace):
        """ベンチマークツール"""
        config_manager = ConfigManager(temp_workspace)
        config_manager.set_profile('testing')
        config_manager.set('benchmark.default_iterations', 5)
        config_manager.set('benchmark.warmup_iterations', 2)
        config_manager.set('benchmark.results_dir', str(temp_workspace / 'benchmark_results'))
        
        return PerformanceBenchmark(config_manager)

    @pytest.fixture
    def mock_rag_system(self):
        """モックRAGシステム"""
        mock = Mock()
        mock.get_system_stats.return_value = {
            'knowledge_base': {'total_documents': 100},
            'performance': {'avg_response_time': 0.5}
        }
        return mock

    @pytest.fixture
    def mock_claude_client(self):
        """モックClaude Codeクライアント"""
        mock = Mock()
        mock.generate_code.return_value = {
            'success': True,
            'code': 'def improved_function(): pass',
            'explanation': 'Improved implementation'
        }
        mock.analyze_code.return_value = {
            'quality_score': 85,
            'suggestions': ['Use type hints']
        }
        return mock

    def test_diagnostics_benchmark(self, benchmark_tool, mock_rag_system):
        """診断システムベンチマーク"""
        diagnostics = SystemDiagnostics(mock_rag_system)
        
        # 診断処理ベンチマーク
        result = benchmark_tool.benchmark_function(
            func=diagnostics.diagnose_system,
            iterations=10,
            name="system_diagnosis"
        )
        
        # 結果検証
        assert result.success is True
        assert result.avg_iteration_ms < 1000  # 1秒以内
        assert result.throughput_ops_per_sec > 1  # 1 ops/sec以上
        assert result.iterations == 10
        
        print(f"システム診断ベンチマーク: {result.avg_iteration_ms:.2f}ms平均")

    def test_improvement_engine_benchmark(self, benchmark_tool, mock_rag_system, mock_claude_client):
        """改善エンジンベンチマーク"""
        diagnostics = SystemDiagnostics(mock_rag_system)
        improvement_engine = ImprovementEngine(diagnostics, mock_claude_client)
        
        # 改善機会特定ベンチマーク
        result1 = benchmark_tool.benchmark_function(
            func=improvement_engine.identify_improvement_opportunities,
            iterations=5,
            name="identify_opportunities"
        )
        
        assert result1.success is True
        assert result1.avg_iteration_ms < 2000  # 2秒以内
        
        # 改善計画生成ベンチマーク
        def generate_plan():
            return improvement_engine.generate_improvement_plan(timeframe_weeks=4)
        
        result2 = benchmark_tool.benchmark_function(
            func=generate_plan,
            iterations=3,
            name="generate_improvement_plan"
        )
        
        assert result2.success is True
        assert result2.avg_iteration_ms < 3000  # 3秒以内
        
        print(f"改善機会特定: {result1.avg_iteration_ms:.2f}ms平均")
        print(f"改善計画生成: {result2.avg_iteration_ms:.2f}ms平均")

    def test_quality_assurance_benchmark(self, benchmark_tool, mock_claude_client):
        """品質保証ベンチマーク"""
        quality_assurance = QualityAssurance(mock_claude_client)
        
        # サンプルデータ
        opportunity = {
            'id': 'test_opportunity',
            'type': 'performance',
            'description': 'Optimize database queries',
            'impact_score': 75
        }
        
        implementation_plan = {
            'steps': [
                {'action': 'analyze_queries', 'estimated_hours': 4},
                {'action': 'implement_optimizations', 'estimated_hours': 8}
            ],
            'total_estimated_hours': 12,
            'risk_level': 'low'
        }
        
        # 実装準備評価ベンチマーク
        def assess_readiness():
            return quality_assurance.assess_implementation_readiness(
                opportunity, implementation_plan
            )
        
        result = benchmark_tool.benchmark_function(
            func=assess_readiness,
            iterations=8,
            name="assess_implementation_readiness"
        )
        
        assert result.success is True
        assert result.avg_iteration_ms < 1500  # 1.5秒以内
        
        print(f"実装準備評価: {result.avg_iteration_ms:.2f}ms平均")

    def test_memory_optimizer_benchmark(self, benchmark_tool):
        """メモリ最適化ベンチマーク"""
        config_manager = ConfigManager()
        config_manager.set_profile('testing')
        memory_optimizer = MemoryOptimizer(config_manager)
        
        # オブジェクトプール作成ベンチマーク
        def create_pool():
            return memory_optimizer.create_object_pool(
                'benchmark_pool',
                lambda: {'data': list(range(100))},
                max_size=50
            )
        
        result1 = benchmark_tool.benchmark_function(
            func=create_pool,
            iterations=5,
            name="create_object_pool"
        )
        
        assert result1.success is True
        
        # オブジェクト取得・返却ベンチマーク
        pool = memory_optimizer.create_object_pool(
            'test_pool',
            lambda: {'data': list(range(50))},
            max_size=20
        )
        
        def pool_operations():
            obj = pool.acquire()
            # 簡単な処理
            obj['data'][0] = 42
            pool.release(obj)
        
        result2 = benchmark_tool.benchmark_function(
            func=pool_operations,
            iterations=100,
            name="object_pool_operations"
        )
        
        assert result2.success is True
        assert result2.avg_iteration_ms < 10  # 10ms以内
        
        print(f"オブジェクトプール作成: {result1.avg_iteration_ms:.2f}ms平均")
        print(f"プール操作: {result2.avg_iteration_ms:.2f}ms平均")

    @pytest.mark.asyncio
    async def test_async_optimizer_benchmark(self, benchmark_tool):
        """非同期最適化ベンチマーク"""
        config_manager = ConfigManager()
        config_manager.set_profile('testing')
        async_optimizer = AsyncOptimizer(config_manager)
        
        await async_optimizer.start()
        
        try:
            # タスク投入ベンチマーク
            async def submit_task():
                async def dummy_task():
                    await asyncio.sleep(0.01)
                    return "completed"
                
                task_id = await async_optimizer.submit_task(dummy_task)
                return task_id
            
            result = await benchmark_tool.benchmark_async_function(
                func=submit_task,
                iterations=20,
                name="async_task_submission"
            )
            
            assert result.success is True
            assert result.avg_iteration_ms < 100  # 100ms以内
            
            print(f"非同期タスク投入: {result.avg_iteration_ms:.2f}ms平均")
            
        finally:
            await async_optimizer.stop()

    def test_metrics_collector_benchmark(self, benchmark_tool):
        """メトリクス収集ベンチマーク"""
        metrics_collector = MetricsCollector()
        metrics_collector.start_collection()
        
        try:
            # メトリクス記録ベンチマーク
            def record_metric():
                metrics_collector.record_metric('test_metric', 42.5)
            
            result1 = benchmark_tool.benchmark_function(
                func=record_metric,
                iterations=1000,
                name="metric_recording"
            )
            
            assert result1.success is True
            assert result1.avg_iteration_ms < 5  # 5ms以内
            
            # メトリクス取得ベンチマーク
            def get_metric():
                return metrics_collector.get_metric_series('test_metric')
            
            result2 = benchmark_tool.benchmark_function(
                func=get_metric,
                iterations=100,
                name="metric_retrieval"
            )
            
            assert result2.success is True
            assert result2.avg_iteration_ms < 10  # 10ms以内
            
            print(f"メトリクス記録: {result1.avg_iteration_ms:.2f}ms平均")
            print(f"メトリクス取得: {result2.avg_iteration_ms:.2f}ms平均")
            
        finally:
            metrics_collector.stop_collection()

    def test_configuration_benchmark(self, benchmark_tool, temp_workspace):
        """設定管理ベンチマーク"""
        config_manager = ConfigManager(temp_workspace)
        
        # 設定値設定ベンチマーク
        def set_config():
            config_manager.set('benchmark.test_value', 42)
        
        result1 = benchmark_tool.benchmark_function(
            func=set_config,
            iterations=1000,
            name="config_set_operation"
        )
        
        assert result1.success is True
        assert result1.avg_iteration_ms < 5  # 5ms以内
        
        # 設定値取得ベンチマーク
        def get_config():
            return config_manager.get('benchmark.test_value')
        
        result2 = benchmark_tool.benchmark_function(
            func=get_config,
            iterations=1000,
            name="config_get_operation"
        )
        
        assert result2.success is True
        assert result2.avg_iteration_ms < 2  # 2ms以内
        
        print(f"設定値設定: {result1.avg_iteration_ms:.2f}ms平均")
        print(f"設定値取得: {result2.avg_iteration_ms:.2f}ms平均")

    def test_load_test_benchmark(self, benchmark_tool, mock_rag_system):
        """負荷テストベンチマーク"""
        diagnostics = SystemDiagnostics(mock_rag_system)
        
        # システム診断の負荷テスト
        result = benchmark_tool.benchmark_load_test(
            func=diagnostics.diagnose_system,
            concurrent_count=5,
            duration_seconds=10,
            name="system_diagnosis_load_test"
        )
        
        assert result.success is True
        assert result.throughput_ops_per_sec > 2  # 2 ops/sec以上
        assert result.metadata['error_count'] == 0
        
        print(f"システム診断負荷テスト: {result.throughput_ops_per_sec:.1f} ops/sec")
        print(f"並行数: {result.metadata['concurrent_count']}")
        print(f"実行時間: {result.metadata['duration_seconds']}秒")

    def test_complete_benchmark_suite(self, benchmark_tool, mock_rag_system, mock_claude_client):
        """完全ベンチマークスイート"""
        print("\n=== 完全システムベンチマーク実行 ===")
        
        # システムコンポーネント初期化
        diagnostics = SystemDiagnostics(mock_rag_system)
        improvement_engine = ImprovementEngine(diagnostics, mock_claude_client)
        quality_assurance = QualityAssurance(mock_claude_client)
        
        # 1. 基本機能ベンチマーク
        benchmark_tool.benchmark_function(
            func=diagnostics.diagnose_system,
            iterations=5,
            name="complete_system_diagnosis"
        )
        
        benchmark_tool.benchmark_function(
            func=improvement_engine.identify_improvement_opportunities,
            iterations=3,
            name="complete_opportunity_identification"
        )
        
        # 2. 負荷テスト
        benchmark_tool.benchmark_load_test(
            func=diagnostics.diagnose_system,
            concurrent_count=3,
            duration_seconds=5,
            name="complete_diagnosis_load_test"
        )
        
        # 3. ベンチマークスイート作成
        suite = benchmark_tool.create_benchmark_suite("complete_system_benchmark")
        
        # 4. 結果検証
        assert suite.total_tests >= 3
        assert suite.passed_tests > 0
        assert suite.failed_tests == 0
        
        # 5. レポート生成
        report = benchmark_tool.generate_benchmark_report(suite)
        assert len(report) > 100  # レポートが生成されている
        
        print(f"ベンチマークスイート完了:")
        print(f"- 総テスト数: {suite.total_tests}")
        print(f"- 成功: {suite.passed_tests}")
        print(f"- 失敗: {suite.failed_tests}")
        print(f"- 総実行時間: {suite.total_duration_ms:.2f}ms")
        
        # パフォーマンス目標確認
        avg_duration = suite.total_duration_ms / suite.total_tests
        assert avg_duration < 5000  # 平均5秒以内
        
        return suite

    def test_benchmark_comparison(self, benchmark_tool, mock_rag_system):
        """ベンチマーク比較テスト"""
        diagnostics = SystemDiagnostics(mock_rag_system)
        
        # 最初のベンチマーク実行
        benchmark_tool.benchmark_function(
            func=diagnostics.diagnose_system,
            iterations=5,
            name="comparison_test"
        )
        
        suite1 = benchmark_tool.create_benchmark_suite("benchmark_v1")
        
        # 2回目のベンチマーク実行（同じテスト）
        benchmark_tool.benchmark_function(
            func=diagnostics.diagnose_system,
            iterations=5,
            name="comparison_test"
        )
        
        suite2 = benchmark_tool.create_benchmark_suite("benchmark_v2")
        
        # 比較実行
        comparison = benchmark_tool.compare_benchmark_suites(suite1, suite2)
        
        # 比較結果検証
        assert 'test_comparisons' in comparison
        assert 'summary' in comparison
        assert comparison['summary']['total_common_tests'] >= 1
        
        print(f"ベンチマーク比較:")
        print(f"- 共通テスト数: {comparison['summary']['total_common_tests']}")
        print(f"- 改善テスト数: {comparison['summary']['improved_tests']}")
        print(f"- 劣化テスト数: {comparison['summary']['degraded_tests']}")

    def test_performance_regression_detection(self, benchmark_tool, mock_rag_system):
        """パフォーマンス回帰検出テスト"""
        diagnostics = SystemDiagnostics(mock_rag_system)
        
        # ベースラインベンチマーク
        benchmark_tool.benchmark_function(
            func=diagnostics.diagnose_system,
            iterations=10,
            name="regression_test"
        )
        
        baseline_suite = benchmark_tool.create_benchmark_suite("baseline")
        
        # 人工的な遅延を追加（回帰シミュレーション）
        def slow_diagnose():
            time.sleep(0.1)  # 100ms遅延追加
            return diagnostics.diagnose_system()
        
        benchmark_tool.benchmark_function(
            func=slow_diagnose,
            iterations=10,
            name="regression_test"
        )
        
        regression_suite = benchmark_tool.create_benchmark_suite("regression")
        
        # 比較分析
        comparison = benchmark_tool.compare_benchmark_suites(baseline_suite, regression_suite)
        
        # 回帰検出確認
        test_comparison = comparison['test_comparisons']['regression_test']
        assert test_comparison['degraded'] is True  # 劣化が検出される
        assert test_comparison['duration_change_percent'] > 50  # 50%以上の劣化
        
        print(f"回帰検出テスト:")
        print(f"- 実行時間変化: {test_comparison['duration_change_percent']:+.1f}%")
        print(f"- 劣化検出: {test_comparison['degraded']}")

    def test_memory_performance_benchmark(self, benchmark_tool):
        """メモリパフォーマンスベンチマーク"""
        config_manager = ConfigManager()
        memory_optimizer = MemoryOptimizer(config_manager)
        
        # 大容量データ処理ベンチマーク
        def memory_intensive_operation():
            # 大きなオブジェクトプール作成
            pool = memory_optimizer.create_object_pool(
                'memory_test',
                lambda: {'data': list(range(1000))},
                max_size=100
            )
            
            # 大量のオブジェクト操作
            objects = []
            for _ in range(50):
                obj = pool.acquire()
                objects.append(obj)
            
            for obj in objects:
                pool.release(obj)
            
            return len(objects)
        
        result = benchmark_tool.benchmark_function(
            func=memory_intensive_operation,
            iterations=5,
            name="memory_intensive_benchmark"
        )
        
        assert result.success is True
        assert result.memory_usage_mb >= 0  # メモリ使用量が測定されている
        assert result.avg_iteration_ms < 1000  # 1秒以内
        
        print(f"メモリ集約処理: {result.avg_iteration_ms:.2f}ms平均")
        print(f"メモリ使用量: {result.memory_usage_mb:.2f}MB")

    def test_benchmark_persistence(self, benchmark_tool, temp_workspace):
        """ベンチマーク永続化テスト"""
        # ベンチマーク実行
        def simple_test():
            time.sleep(0.01)
            return "test"
        
        benchmark_tool.benchmark_function(
            func=simple_test,
            iterations=3,
            name="persistence_test"
        )
        
        # スイート作成（自動保存される）
        suite = benchmark_tool.create_benchmark_suite("persistence_test_suite")
        
        # 保存ファイル確認
        results_dir = temp_workspace / 'benchmark_results'
        saved_files = list(results_dir.glob("*.json"))
        assert len(saved_files) >= 1
        
        # ベンチマーク読み込み
        loaded_suite = benchmark_tool.load_benchmark_suite(saved_files[0])
        assert loaded_suite is not None
        assert loaded_suite.suite_name == suite.suite_name
        assert len(loaded_suite.results) == len(suite.results)
        
        print(f"ベンチマーク永続化テスト完了: {saved_files[0]}")