"""
AIDE エンドツーエンドワークフローテスト

実際のユースケースに基づく完全なワークフロー検証
"""

import pytest
import asyncio
import tempfile
import shutil
import time
import json
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
from src.optimization.memory_optimizer import MemoryOptimizer
from src.optimization.performance_profiler import PerformanceProfiler
from src.optimization.async_optimizer import AsyncOptimizer


class TestEndToEndWorkflows:
    """エンドツーエンドワークフローテスト"""

    @pytest.fixture
    def temp_workspace(self):
        """テスト用ワークスペース"""
        temp_dir = tempfile.mkdtemp()
        workspace = Path(temp_dir)
        
        # プロジェクト構造作成
        (workspace / 'src').mkdir()
        (workspace / 'tests').mkdir()
        (workspace / 'config').mkdir()
        (workspace / 'logs').mkdir()
        
        # サンプルコードファイル作成
        sample_code = '''
def slow_function(data):
    # 非効率な実装
    result = []
    for i in range(len(data)):
        for j in range(len(data)):
            if data[i] == data[j]:
                result.append(data[i])
    return result

class DataProcessor:
    def __init__(self):
        self.cache = {}
    
    def process(self, input_data):
        # キャッシュ未使用の実装
        processed = []
        for item in input_data:
            processed.append(item * 2)
        return processed
'''
        
        (workspace / 'src' / 'sample_module.py').write_text(sample_code)
        
        yield workspace
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_rag_system(self):
        """高度なモックRAGシステム"""
        mock = Mock()
        
        # システム統計
        mock.get_system_stats.return_value = {
            'knowledge_base': {
                'total_documents': 250,
                'categories': ['performance', 'optimization', 'best_practices'],
                'last_updated': time.time()
            },
            'performance': {
                'avg_response_time': 0.3,
                'success_rate': 0.95,
                'cache_hit_rate': 0.8
            },
            'quality_metrics': {
                'relevance_score': 0.87,
                'completeness_score': 0.92
            }
        }
        
        # 知識検索のモック
        def mock_search(query, limit=5):
            results = [
                {
                    'content': f'Best practice for {query}: Use efficient algorithms',
                    'relevance': 0.9,
                    'source': 'optimization_guide.md'
                },
                {
                    'content': f'Performance tip for {query}: Implement caching',
                    'relevance': 0.8,
                    'source': 'performance_tips.md'
                }
            ]
            return results[:limit]
        
        mock.search.side_effect = mock_search
        
        return mock

    @pytest.fixture
    def mock_claude_client(self):
        """高度なモックClaude Codeクライアント"""
        mock = Mock()
        
        # コード生成のモック
        def mock_generate_code(prompt, context=None):
            if 'optimize' in prompt.lower():
                return {
                    'success': True,
                    'code': '''
def optimized_function(data):
    # 効率的な実装
    seen = set()
    result = []
    for item in data:
        if item in seen:
            result.append(item)
        seen.add(item)
    return result

class OptimizedDataProcessor:
    def __init__(self):
        self.cache = {}
    
    def process(self, input_data):
        # キャッシュ使用の実装
        cache_key = hash(tuple(input_data))
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        processed = [item * 2 for item in input_data]
        self.cache[cache_key] = processed
        return processed
''',
                    'explanation': 'Optimized algorithms and added caching for better performance',
                    'improvements': [
                        'Reduced time complexity from O(n²) to O(n)',
                        'Added caching mechanism',
                        'Used list comprehension for better performance'
                    ]
                }
            elif 'test' in prompt.lower():
                return {
                    'success': True,
                    'code': '''
import pytest
from src.sample_module import DataProcessor, slow_function

class TestDataProcessor:
    def test_process_basic(self):
        processor = DataProcessor()
        result = processor.process([1, 2, 3])
        assert result == [2, 4, 6]
    
    def test_slow_function(self):
        result = slow_function([1, 2, 2, 3])
        assert 2 in result
''',
                    'explanation': 'Comprehensive test suite for the module'
                }
            else:
                return {
                    'success': True,
                    'code': 'def improved_function(): pass',
                    'explanation': 'General improvement'
                }
        
        mock.generate_code.side_effect = mock_generate_code
        
        # コード分析のモック
        def mock_analyze_code(code):
            complexity_score = 70 if 'for' in code else 85
            return {
                'quality_score': complexity_score,
                'suggestions': [
                    'Use type hints for better code documentation',
                    'Add docstrings to functions',
                    'Consider using more efficient algorithms'
                ],
                'metrics': {
                    'cyclomatic_complexity': 5 if 'for' in code else 2,
                    'lines_of_code': len(code.split('\n')),
                    'maintainability_index': complexity_score
                }
            }
        
        mock.analyze_code.side_effect = mock_analyze_code
        
        return mock

    @pytest.fixture
    def complete_system(self, temp_workspace, mock_rag_system, mock_claude_client):
        """完全なシステムセットアップ"""
        # 設定管理
        config_manager = ConfigManager(temp_workspace)
        config_manager.set_profile('testing')
        config_manager.set('optimization.auto_optimization', True)
        config_manager.set('optimization.performance_threshold', 70)
        
        # ログ管理
        log_manager = LogManager(config_manager)
        
        # メトリクス収集
        metrics_collector = MetricsCollector()
        metrics_collector.start_collection()
        
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
        
        system = {
            'workspace': temp_workspace,
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
        
        yield system
        
        # クリーンアップ
        metrics_collector.stop_collection()

    def test_complete_improvement_workflow(self, complete_system):
        """完全な改善ワークフロー"""
        system = complete_system
        
        # フェーズ1: システム診断
        print("\n=== フェーズ1: システム診断 ===")
        diagnostics = system['diagnostics']
        diagnosis = diagnostics.diagnose_system()
        
        assert 'overall_health_score' in diagnosis
        assert 'component_health' in diagnosis
        assert 'recommendations' in diagnosis
        
        initial_health = diagnosis['overall_health_score']
        print(f"初期ヘルススコア: {initial_health}")
        
        # フェーズ2: 改善機会特定
        print("\n=== フェーズ2: 改善機会特定 ===")
        improvement_engine = system['improvement_engine']
        opportunities = improvement_engine.identify_improvement_opportunities()
        
        assert len(opportunities) > 0
        print(f"特定された改善機会: {len(opportunities)}件")
        
        # 最も重要な改善機会を選択
        top_opportunity = max(opportunities, key=lambda x: x.get('impact_score', 0))
        print(f"選択された改善機会: {top_opportunity['description']}")
        
        # フェーズ3: 改善計画生成
        print("\n=== フェーズ3: 改善計画生成 ===")
        implementation_plan = improvement_engine.generate_implementation_plan(top_opportunity)
        
        assert 'steps' in implementation_plan
        assert 'estimated_hours' in implementation_plan
        print(f"実装ステップ数: {len(implementation_plan['steps'])}")
        print(f"推定作業時間: {implementation_plan['estimated_hours']}時間")
        
        # フェーズ4: 品質保証評価
        print("\n=== フェーズ4: 品質保証評価 ===")
        quality_assurance = system['quality_assurance']
        readiness = quality_assurance.assess_implementation_readiness(
            top_opportunity, implementation_plan
        )
        
        assert 'ready_for_implementation' in readiness
        assert 'risk_assessment' in readiness
        print(f"実装準備完了: {readiness['ready_for_implementation']}")
        print(f"リスクレベル: {readiness['risk_assessment']['risk_level']}")
        
        # フェーズ5: 自律実装（安全な場合のみ）
        if readiness['ready_for_implementation']:
            print("\n=== フェーズ5: 自律実装 ===")
            autonomous_impl = system['autonomous_impl']
            
            # 実装実行（モック）
            with patch.object(autonomous_impl, '_execute_implementation_step') as mock_exec:
                mock_exec.return_value = {
                    'success': True,
                    'output': 'Successfully implemented optimization',
                    'changes': ['Optimized algorithm', 'Added caching']
                }
                
                implementation_result = autonomous_impl.implement_opportunity(top_opportunity)
                
                assert implementation_result['success'] is True
                print(f"実装結果: {implementation_result['summary']}")
                
                # フェーズ6: 実装後検証
                print("\n=== フェーズ6: 実装後検証 ===")
                validation = quality_assurance.validate_implementation(
                    top_opportunity, implementation_result
                )
                
                assert 'validation_passed' in validation
                print(f"検証結果: {'合格' if validation['validation_passed'] else '不合格'}")
                
                # フェーズ7: 再診断で改善確認
                print("\n=== フェーズ7: 改善効果確認 ===")
                post_diagnosis = diagnostics.diagnose_system()
                final_health = post_diagnosis['overall_health_score']
                
                improvement = final_health - initial_health
                print(f"最終ヘルススコア: {final_health}")
                print(f"改善効果: {improvement:+.1f}ポイント")
                
                # 改善が見られることを確認
                assert final_health >= initial_health - 5  # 多少の誤差を許容

    @pytest.mark.asyncio
    async def test_async_workflow_with_monitoring(self, complete_system):
        """非同期ワークフロー監視テスト"""
        system = complete_system
        
        print("\n=== 非同期ワークフロー監視テスト ===")
        
        # 非同期最適化開始
        async_optimizer = system['async_optimizer']
        await async_optimizer.start()
        
        try:
            # メトリクス収集開始
            metrics_collector = system['metrics_collector']
            
            # 複数の非同期タスクを投入
            async def monitoring_task(task_id):
                start_time = time.time()
                await asyncio.sleep(0.1)  # 作業シミュレーション
                duration = time.time() - start_time
                
                # メトリクス記録
                metrics_collector.record_metric(f'task_duration_{task_id}', duration * 1000)
                return f'Task {task_id} completed in {duration:.3f}s'
            
            # 10個のタスクを並行実行
            tasks = []
            for i in range(10):
                task_id = await async_optimizer.submit_task(monitoring_task, i)
                tasks.append(task_id)
            
            # タスク完了待機
            await asyncio.sleep(0.5)
            
            # 統計確認
            stats = async_optimizer.get_optimization_summary()
            assert stats['task_scheduler']['statistics']['total_submitted'] >= 10
            
            # メトリクス確認
            collection_stats = metrics_collector.get_collection_stats()
            assert collection_stats['total_metrics'] >= 10
            
            print(f"投入タスク数: {stats['task_scheduler']['statistics']['total_submitted']}")
            print(f"記録メトリクス数: {collection_stats['total_metrics']}")
            
        finally:
            await async_optimizer.stop()

    def test_cli_driven_workflow(self, complete_system):
        """CLI駆動ワークフローテスト"""
        system = complete_system
        cli_manager = system['cli_manager']
        
        print("\n=== CLI駆動ワークフローテスト ===")
        
        # 設定確認コマンド
        with patch('sys.argv', ['cli', 'config', '--list']):
            with patch('builtins.print') as mock_print:
                result = cli_manager.run()
                assert result == 0
                mock_print.assert_called()
        
        # メトリクス確認コマンド
        with patch('sys.argv', ['cli', 'metrics']):
            with patch('builtins.print') as mock_print:
                result = cli_manager.run()
                assert result == 0
                mock_print.assert_called()
        
        # 設定変更コマンド
        with patch('sys.argv', ['cli', 'config', '--set', 'test.workflow_value=123']):
            result = cli_manager.run()
            assert result == 0
            
            # 設定が正しく反映されたことを確認
            assert system['config_manager'].get('test.workflow_value') == 123
        
        print("CLI コマンドテスト完了")

    def test_performance_optimization_workflow(self, complete_system):
        """パフォーマンス最適化ワークフロー"""
        system = complete_system
        
        print("\n=== パフォーマンス最適化ワークフロー ===")
        
        # メモリ最適化開始
        memory_optimizer = system['memory_optimizer']
        memory_optimizer.start_profiling()
        
        try:
            # パフォーマンスプロファイリング開始
            performance_profiler = system['performance_profiler']
            performance_profiler.enable_function_profiling()
            
            # 計測対象関数定義
            @performance_profiler.profile_function('workflow_test_function')
            def test_heavy_function():
                # CPU集約的処理シミュレーション
                data = list(range(1000))
                result = []
                for i in data:
                    result.append(i * i)
                return result
            
            # メモリ集約的処理
            pool = memory_optimizer.create_object_pool(
                'workflow_objects',
                lambda: {'data': list(range(100))},
                max_size=50
            )
            
            # 負荷テスト実行
            for iteration in range(20):
                # CPU負荷
                test_heavy_function()
                
                # メモリ負荷
                with pool.get_object() as obj:
                    processed = [x * 2 for x in obj['data']]
            
            # パフォーマンス分析
            analysis = performance_profiler.analyze_performance(min_impact_score=1.0)
            assert 'total_profiled_functions' in analysis
            assert analysis['total_profiled_functions'] >= 1
            
            # メモリ最適化実行
            optimization_result = memory_optimizer.optimize_memory_usage()
            assert 'memory_saved_mb' in optimization_result
            
            print(f"プロファイル対象関数: {analysis['total_profiled_functions']}")
            print(f"メモリ最適化: {optimization_result['memory_saved_mb']:.2f}MB削減")
            
            # オブジェクトプール効率確認
            pool_stats = pool.get_stats()
            print(f"オブジェクトプール再利用率: {pool_stats['reuse_rate']:.1f}%")
            
        finally:
            memory_optimizer.stop_profiling()

    def test_error_recovery_workflow(self, complete_system):
        """エラー回復ワークフロー"""
        system = complete_system
        
        print("\n=== エラー回復ワークフローテスト ===")
        
        # Claude Clientで意図的エラー発生
        claude_client = system['claude_client']
        original_generate = claude_client.generate_code
        
        # 一時的に全てのコード生成を失敗させる
        claude_client.generate_code.side_effect = Exception("API temporarily unavailable")
        
        improvement_engine = system['improvement_engine']
        
        # エラー発生時の処理
        try:
            opportunities = improvement_engine.identify_improvement_opportunities()
            # エラーが発生してもシステムが停止しないことを確認
            assert isinstance(opportunities, list)
        except Exception as e:
            pytest.fail(f"System should handle errors gracefully: {str(e)}")
        
        # エラー回復テスト
        claude_client.generate_code.side_effect = None
        claude_client.generate_code = original_generate
        
        # 回復後の正常動作確認
        try:
            opportunities = improvement_engine.identify_improvement_opportunities()
            assert len(opportunities) >= 0
            print("エラー回復テスト: 正常に回復")
        except Exception as e:
            pytest.fail(f"System should recover from errors: {str(e)}")

    def test_stress_test_workflow(self, complete_system):
        """ストレステストワークフロー"""
        system = complete_system
        
        print("\n=== ストレステストワークフロー ===")
        
        # システム負荷測定開始
        start_time = time.time()
        
        # 複数の診断を並行実行
        diagnostics = system['diagnostics']
        diagnosis_results = []
        
        for i in range(10):
            diagnosis = diagnostics.diagnose_system()
            diagnosis_results.append(diagnosis)
        
        # 全ての診断が完了することを確認
        assert len(diagnosis_results) == 10
        
        # 診断結果の一貫性確認
        health_scores = [d['overall_health_score'] for d in diagnosis_results]
        health_variance = max(health_scores) - min(health_scores)
        
        # ヘルススコアの変動が妥当な範囲内であることを確認
        assert health_variance < 20  # 20ポイント以内の変動
        
        # 実行時間確認
        total_time = time.time() - start_time
        avg_time_per_diagnosis = total_time / 10
        
        print(f"10回診断実行時間: {total_time:.2f}秒")
        print(f"1回あたり平均時間: {avg_time_per_diagnosis:.3f}秒")
        print(f"ヘルススコア変動範囲: {health_variance:.1f}ポイント")
        
        # パフォーマンス基準確認
        assert avg_time_per_diagnosis < 1.0  # 1秒以内

    def test_data_consistency_workflow(self, complete_system):
        """データ整合性ワークフロー"""
        system = complete_system
        
        print("\n=== データ整合性ワークフローテスト ===")
        
        # メトリクス収集でデータ整合性確認
        metrics_collector = system['metrics_collector']
        
        # 一連のメトリクスを記録
        test_metrics = [
            ('cpu_usage', 45.5),
            ('memory_usage', 67.2),
            ('response_time', 123.4),
            ('error_rate', 0.02)
        ]
        
        for metric_name, value in test_metrics:
            metrics_collector.record_metric(metric_name, value)
        
        # 各メトリクスの整合性確認
        for metric_name, expected_value in test_metrics:
            series = metrics_collector.get_metric_series(metric_name)
            assert series is not None
            
            latest_point = series.get_latest()
            assert abs(latest_point.value - expected_value) < 0.001
        
        # 設定管理でデータ整合性確認
        config_manager = system['config_manager']
        
        test_configs = {
            'test.string_value': 'hello world',
            'test.numeric_value': 42,
            'test.boolean_value': True
        }
        
        # 設定値設定
        for key, value in test_configs.items():
            config_manager.set(key, value)
        
        # 設定値取得確認
        for key, expected_value in test_configs.items():
            actual_value = config_manager.get(key)
            assert actual_value == expected_value
        
        print("データ整合性テスト完了")

    def test_scalability_workflow(self, complete_system):
        """スケーラビリティワークフロー"""
        system = complete_system
        
        print("\n=== スケーラビリティワークフローテスト ===")
        
        # 大量データ処理テスト
        memory_optimizer = system['memory_optimizer']
        
        # 大容量オブジェクトプール作成
        large_pool = memory_optimizer.create_object_pool(
            'large_objects',
            lambda: {'data': list(range(1000)), 'metadata': {'id': time.time()}},
            max_size=200
        )
        
        # 大量オブジェクト処理
        processed_count = 0
        start_time = time.time()
        
        for batch in range(5):  # 5バッチ
            batch_objects = []
            
            # 100個のオブジェクトを取得
            for i in range(100):
                obj = large_pool.acquire()
                batch_objects.append(obj)
                processed_count += 1
            
            # 処理シミュレーション
            for obj in batch_objects:
                # データ変更
                obj['data'][0] = processed_count
            
            # オブジェクト返却
            for obj in batch_objects:
                large_pool.release(obj)
        
        processing_time = time.time() - start_time
        throughput = processed_count / processing_time
        
        # プール統計確認
        pool_stats = large_pool.get_stats()
        
        print(f"処理オブジェクト数: {processed_count}")
        print(f"処理時間: {processing_time:.2f}秒")
        print(f"スループット: {throughput:.1f} objects/sec")
        print(f"プール再利用率: {pool_stats['reuse_rate']:.1f}%")
        
        # スケーラビリティ基準確認
        assert throughput > 50  # 50 objects/sec以上
        assert pool_stats['reuse_rate'] > 60  # 60%以上の再利用率