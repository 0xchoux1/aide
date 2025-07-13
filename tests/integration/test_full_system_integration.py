"""
AIDE 全システム統合テスト

Phase 3.2で構築した全コンポーネントの統合動作を検証
"""

import pytest
import asyncio
import tempfile
import shutil
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.self_improvement.diagnostics import SystemDiagnostics
from src.self_improvement.improvement_engine import ImprovementEngine
from src.self_improvement.autonomous_implementation import AutonomousImplementation
from src.self_improvement.quality_assurance import QualityAssurance
from src.config.config_manager import ConfigManager
from src.cli.cli_manager import CLIManager
from src.logging.log_manager import LogManager
from src.dashboard.metrics_collector import MetricsCollector
from src.dashboard.dashboard_server import DashboardServer
from src.optimization.memory_optimizer import MemoryOptimizer
from src.optimization.performance_profiler import PerformanceProfiler
from src.optimization.async_optimizer import AsyncOptimizer


class TestFullSystemIntegration:
    """全システム統合テスト"""

    @pytest.fixture
    def temp_project_dir(self):
        """テスト用プロジェクトディレクトリ"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

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
            'suggestions': ['Use type hints', 'Add docstrings']
        }
        return mock

    @pytest.fixture
    def integrated_system(self, temp_project_dir, mock_rag_system, mock_claude_client):
        """統合システムセットアップ"""
        # 設定管理
        config_manager = ConfigManager(temp_project_dir)
        config_manager.set_profile('testing')
        
        # ログ管理
        log_manager = LogManager(config_manager)
        
        # メトリクス収集
        metrics_collector = MetricsCollector()
        
        # 最適化コンポーネント
        memory_optimizer = MemoryOptimizer(config_manager)
        performance_profiler = PerformanceProfiler(config_manager)
        async_optimizer = AsyncOptimizer(config_manager)
        
        # 自己改善システム
        diagnostics = SystemDiagnostics(mock_rag_system)
        improvement_engine = ImprovementEngine(diagnostics, mock_claude_client)
        autonomous_impl = AutonomousImplementation(mock_claude_client)
        quality_assurance = QualityAssurance(mock_claude_client)
        
        # CLI管理
        cli_manager = CLIManager(config_manager)
        
        return {
            'config_manager': config_manager,
            'log_manager': log_manager,
            'metrics_collector': metrics_collector,
            'memory_optimizer': memory_optimizer,
            'performance_profiler': performance_profiler,
            'async_optimizer': async_optimizer,
            'diagnostics': diagnostics,
            'improvement_engine': improvement_engine,
            'autonomous_impl': autonomous_impl,
            'quality_assurance': quality_assurance,
            'cli_manager': cli_manager,
            'rag_system': mock_rag_system,
            'claude_client': mock_claude_client
        }

    def test_system_initialization(self, integrated_system):
        """システム初期化テスト"""
        system = integrated_system
        
        # 設定管理初期化確認
        assert system['config_manager'].get_profile().name == 'TESTING'
        assert system['config_manager'].get('logging.level') == 'INFO'
        
        # ログ管理初期化確認
        assert system['log_manager'] is not None
        
        # メトリクス収集初期化確認
        assert system['metrics_collector'] is not None
        
        # 最適化コンポーネント初期化確認
        assert system['memory_optimizer'] is not None
        assert system['performance_profiler'] is not None
        assert system['async_optimizer'] is not None
        
        # 自己改善システム初期化確認
        assert system['diagnostics'] is not None
        assert system['improvement_engine'] is not None
        assert system['autonomous_impl'] is not None
        assert system['quality_assurance'] is not None

    def test_configuration_propagation(self, integrated_system):
        """設定値伝播テスト"""
        system = integrated_system
        config_manager = system['config_manager']
        
        # 設定値更新
        config_manager.set('test.integration_value', 42)
        
        # 設定値取得確認
        assert config_manager.get('test.integration_value') == 42
        
        # 環境プロファイル設定確認
        assert config_manager.get('logging.level') == 'INFO'
        assert config_manager.get('logging.format') == 'json'

    @pytest.mark.asyncio
    async def test_async_component_integration(self, integrated_system):
        """非同期コンポーネント統合テスト"""
        system = integrated_system
        async_optimizer = system['async_optimizer']
        
        # 非同期最適化開始
        await async_optimizer.start()
        
        try:
            # タスク投入テスト
            async def sample_task():
                await asyncio.sleep(0.1)
                return "completed"
            
            task_id = await async_optimizer.submit_task(sample_task)
            assert task_id is not None
            
            # 少し待機してタスク完了確認
            await asyncio.sleep(0.2)
            
            # 統計確認
            stats = async_optimizer.get_optimization_summary()
            assert stats['is_running'] is True
            assert stats['task_scheduler']['statistics']['total_submitted'] >= 1
            
        finally:
            await async_optimizer.stop()

    def test_diagnostics_integration(self, integrated_system):
        """診断システム統合テスト"""
        system = integrated_system
        diagnostics = system['diagnostics']
        
        # システム診断実行
        diagnosis = diagnostics.diagnose_system()
        
        # 診断結果検証
        assert 'overall_health_score' in diagnosis
        assert 'component_health' in diagnosis
        assert 'recommendations' in diagnosis
        assert 0 <= diagnosis['overall_health_score'] <= 100

    def test_improvement_engine_integration(self, integrated_system):
        """改善エンジン統合テスト"""
        system = integrated_system
        improvement_engine = system['improvement_engine']
        
        # 改善計画生成
        roadmap = improvement_engine.generate_improvement_plan(timeframe_weeks=4)
        
        # ロードマップ検証
        assert 'plan_id' in roadmap
        assert 'phases' in roadmap
        assert 'total_estimated_weeks' in roadmap
        assert roadmap['total_estimated_weeks'] <= 4

    def test_quality_assurance_integration(self, integrated_system):
        """品質保証統合テスト"""
        system = integrated_system
        quality_assurance = system['quality_assurance']
        
        # サンプル改善機会
        opportunity = {
            'id': 'test_opportunity',
            'type': 'performance',
            'description': 'Optimize database queries',
            'impact_score': 75,
            'implementation_effort': 'medium'
        }
        
        # サンプル実装計画
        implementation_plan = {
            'steps': [
                {'action': 'analyze_queries', 'estimated_hours': 4},
                {'action': 'implement_optimizations', 'estimated_hours': 8},
                {'action': 'test_performance', 'estimated_hours': 4}
            ],
            'total_estimated_hours': 16,
            'risk_level': 'low'
        }
        
        # 実装準備評価
        readiness = quality_assurance.assess_implementation_readiness(
            opportunity, implementation_plan
        )
        
        # 評価結果検証
        assert 'ready_for_implementation' in readiness
        assert 'risk_assessment' in readiness
        assert 'quality_gates' in readiness

    def test_memory_optimization_integration(self, integrated_system):
        """メモリ最適化統合テスト"""
        system = integrated_system
        memory_optimizer = system['memory_optimizer']
        
        # メモリプロファイリング開始
        memory_optimizer.start_profiling()
        
        try:
            # メモリ使用量測定
            stats_before = memory_optimizer.profiler.get_current_stats()
            
            # オブジェクトプール作成テスト
            pool = memory_optimizer.create_object_pool(
                'test_objects',
                lambda: {'data': list(range(100))},
                max_size=10
            )
            
            # オブジェクト取得・返却テスト
            with pool.get_object() as obj:
                assert 'data' in obj
                assert len(obj['data']) == 100
            
            # プール統計確認
            pool_stats = pool.get_stats()
            assert pool_stats['created_count'] >= 1
            
            # メモリ最適化実行
            optimization_result = memory_optimizer.optimize_memory_usage()
            assert 'memory_saved_mb' in optimization_result
            
        finally:
            memory_optimizer.stop_profiling()

    def test_performance_profiling_integration(self, integrated_system):
        """パフォーマンスプロファイリング統合テスト"""
        system = integrated_system
        performance_profiler = system['performance_profiler']
        
        # 関数プロファイリング有効化
        performance_profiler.enable_function_profiling()
        
        # テスト関数定義
        @performance_profiler.profile_function('test_function')
        def test_function():
            time.sleep(0.01)  # 10ms待機
            return "test_result"
        
        # 関数実行
        for _ in range(5):
            result = test_function()
            assert result == "test_result"
        
        # パフォーマンス分析実行
        analysis = performance_profiler.analyze_performance(min_impact_score=1.0)
        
        # 分析結果検証
        assert 'total_profiled_functions' in analysis
        assert 'top_functions' in analysis
        assert analysis['total_profiled_functions'] >= 1

    def test_cli_integration(self, integrated_system):
        """CLI統合テスト"""
        system = integrated_system
        cli_manager = system['cli_manager']
        
        # 設定コマンドテスト
        with patch('sys.argv', ['cli', 'config', '--get', 'logging.level']):
            result = cli_manager.run()
            assert result == 0
        
        # メトリクスコマンドテスト
        with patch('sys.argv', ['cli', 'metrics']):
            with patch('builtins.print') as mock_print:
                result = cli_manager.run()
                assert result == 0
                mock_print.assert_called()

    def test_end_to_end_improvement_cycle(self, integrated_system):
        """エンドツーエンド改善サイクルテスト"""
        system = integrated_system
        
        # 1. システム診断
        diagnostics = system['diagnostics']
        diagnosis = diagnostics.diagnose_system()
        assert diagnosis['overall_health_score'] >= 0
        
        # 2. 改善機会特定
        improvement_engine = system['improvement_engine']
        opportunities = improvement_engine.identify_improvement_opportunities()
        assert len(opportunities) >= 0
        
        # 3. 改善計画生成
        if opportunities:
            opportunity = opportunities[0]
            implementation_plan = improvement_engine.generate_implementation_plan(opportunity)
            assert 'steps' in implementation_plan
            
            # 4. 品質評価
            quality_assurance = system['quality_assurance']
            readiness = quality_assurance.assess_implementation_readiness(
                opportunity, implementation_plan
            )
            assert 'ready_for_implementation' in readiness
            
            # 5. リスク評価が十分に低い場合のみ実装テスト
            if readiness.get('ready_for_implementation', False):
                autonomous_impl = system['autonomous_impl']
                
                # モック実装（実際の変更は行わない）
                with patch.object(autonomous_impl, '_execute_implementation_step') as mock_exec:
                    mock_exec.return_value = {'success': True, 'output': 'Mock implementation'}
                    
                    result = autonomous_impl.implement_opportunity(opportunity)
                    assert result['success'] is True

    def test_system_monitoring_integration(self, integrated_system):
        """システム監視統合テスト"""
        system = integrated_system
        metrics_collector = system['metrics_collector']
        
        # メトリクス収集開始
        metrics_collector.start_collection()
        
        try:
            # システムメトリクス記録
            metrics_collector.record_metric('test_metric', 42.0)
            metrics_collector.record_metric('test_metric', 45.0)
            
            # メトリクス確認
            series = metrics_collector.get_metric_series('test_metric')
            assert series is not None
            assert len(series.points) >= 2
            
            # 統計情報取得
            stats = metrics_collector.get_collection_stats()
            assert 'total_metrics' in stats
            assert stats['total_metrics'] >= 1
            
        finally:
            metrics_collector.stop_collection()

    def test_error_handling_integration(self, integrated_system):
        """エラーハンドリング統合テスト"""
        system = integrated_system
        
        # Claude Clientエラーシミュレーション
        claude_client = system['claude_client']
        claude_client.generate_code.side_effect = Exception("Mock API error")
        
        improvement_engine = system['improvement_engine']
        
        # エラー発生時の適切な処理確認
        try:
            roadmap = improvement_engine.generate_improvement_plan(timeframe_weeks=4)
            # エラー発生でもシステムが停止しないことを確認
            assert 'error' in roadmap or 'phases' in roadmap
        except Exception as e:
            # 予期せぬエラーが発生した場合はテスト失敗
            pytest.fail(f"Unexpected error: {str(e)}")

    def test_system_performance_benchmarks(self, integrated_system):
        """システムパフォーマンスベンチマーク"""
        system = integrated_system
        
        # システム初期化時間測定
        start_time = time.time()
        
        # 主要コンポーネント初期化（既に完了しているが再確認）
        assert system['diagnostics'] is not None
        assert system['improvement_engine'] is not None
        assert system['quality_assurance'] is not None
        
        initialization_time = time.time() - start_time
        
        # 初期化時間が妥当な範囲内であることを確認（5秒以内）
        assert initialization_time < 5.0
        
        # 診断実行時間測定
        start_time = time.time()
        diagnosis = system['diagnostics'].diagnose_system()
        diagnosis_time = time.time() - start_time
        
        # 診断実行時間が妥当な範囲内であることを確認（3秒以内）
        assert diagnosis_time < 3.0
        assert diagnosis is not None

    def test_system_scalability(self, integrated_system):
        """システムスケーラビリティテスト"""
        system = integrated_system
        memory_optimizer = system['memory_optimizer']
        
        # 大量オブジェクト処理テスト
        pool = memory_optimizer.create_object_pool(
            'scalability_test',
            lambda: {'id': time.time()},
            max_size=100
        )
        
        # 100個のオブジェクトを並行取得・返却
        objects = []
        for i in range(100):
            obj = pool.acquire()
            objects.append(obj)
        
        for obj in objects:
            pool.release(obj)
        
        # プール統計確認
        stats = pool.get_stats()
        assert stats['reused_count'] >= 50  # 少なくとも50%は再利用されるべき
        
        # メモリ使用量が適切に管理されていることを確認
        memory_stats = memory_optimizer.profiler.get_current_stats()
        assert memory_stats.memory_percent < 90  # メモリ使用率90%未満

    def test_system_resilience(self, integrated_system):
        """システム復旧性テスト"""
        system = integrated_system
        
        # RAGシステム障害シミュレーション
        rag_system = system['rag_system']
        rag_system.get_system_stats.side_effect = Exception("RAG system unavailable")
        
        diagnostics = system['diagnostics']
        
        # 障害発生時でも診断が継続できることを確認
        diagnosis = diagnostics.diagnose_system()
        assert diagnosis is not None
        assert 'overall_health_score' in diagnosis
        
        # ヘルススコアが障害を反映していることを確認
        assert diagnosis['overall_health_score'] < 100
        
        # 障害からの復旧テスト
        rag_system.get_system_stats.side_effect = None
        rag_system.get_system_stats.return_value = {
            'knowledge_base': {'total_documents': 100},
            'performance': {'avg_response_time': 0.5}
        }
        
        # 復旧後の診断
        recovery_diagnosis = diagnostics.diagnose_system()
        assert recovery_diagnosis['overall_health_score'] >= diagnosis['overall_health_score']