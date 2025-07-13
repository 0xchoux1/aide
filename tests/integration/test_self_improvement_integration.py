"""
自己改善システム統合テスト

各コンポーネント間の統合とエンドツーエンドのワークフローをテスト
"""

import pytest
import tempfile
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.append('/home/choux1/src/github.com/0xchoux1/aide')

from src.self_improvement.diagnostics import (
    SystemDiagnostics,
    PerformanceMonitor,
    CodeQualityAnalyzer,
    LearningEffectivenessEvaluator,
    DiagnosticResult
)
from src.self_improvement.improvement_engine import (
    ImprovementEngine,
    OpportunityIdentifier,
    PriorityOptimizer,
    RoadmapGenerator,
    ImprovementOpportunity,
    ImprovementRoadmap,
    ImprovementType,
    Priority
)
from src.self_improvement.autonomous_implementation import (
    AutonomousImplementation,
    CodeGenerator,
    TestAutomation,
    DeploymentManager,
    ImplementationResult,
    SafetyCheck
)
from src.self_improvement.quality_assurance import (
    QualityAssurance,
    SafetyChecker,
    HumanApprovalGate,
    QualityMetrics,
    ApprovalRequest,
    ApprovalStatus,
    RiskLevel
)


class TestSelfImprovementWorkflow:
    """自己改善ワークフロー統合テスト"""
    
    @pytest.fixture
    def mock_rag_system(self):
        """RAGシステムモック"""
        mock_rag = Mock()
        mock_rag.get_system_stats.return_value = {
            'generation_stats': {
                'total_requests': 100,
                'successful_generations': 95,
                'llm_requests': 50,
                'llm_errors': 2
            },
            'knowledge_base_stats': {
                'total_items': 150,
                'average_quality_score': 0.85
            },
            'context_usage_rate': 0.92,
            'llm_integration': {
                'claude_code_enabled': True,
                'llm_backend': 'claude-code',
                'llm_stats': {
                    'success_rate': 0.97
                }
            }
        }
        return mock_rag
    
    @pytest.fixture
    def mock_claude_client(self):
        """Claude Clientモック"""
        mock_client = Mock()
        
        # 構造化レスポンス用モック
        mock_structured_response = Mock()
        mock_structured_response.success = True
        mock_structured_response.metadata = {
            'structured_output': {
                'opportunities': [
                    {
                        'title': 'パフォーマンス最適化',
                        'description': 'メモリ使用量を20%削減',
                        'type': 'performance',
                        'priority': 'high',
                        'impact_score': 85.0,
                        'effort_score': 30.0,
                        'risk_score': 15.0,
                        'estimated_hours': 8.0,
                        'complexity': 'moderate'
                    }
                ]
            }
        }
        mock_client.generate_structured_response.return_value = mock_structured_response
        
        # 通常レスポンス用モック
        mock_response = Mock()
        mock_response.success = True
        mock_response.content = '''
改善計画を生成します。

```json
{
  "approach": "メモリ最適化アプローチ",
  "steps": [
    {
      "step": 1,
      "description": "メモリ使用量分析",
      "files_to_modify": ["src/rag/rag_system.py"],
      "risk_level": "low"
    }
  ],
  "expected_changes": ["メモリ使用量20%削減"],
  "testing_strategy": "既存テスト実行",
  "rollback_plan": "バックアップから復旧",
  "success_criteria": ["メモリ使用量目標達成"]
}
```
'''
        mock_client.generate_response.return_value = mock_response
        
        return mock_client
    
    @pytest.fixture
    def temp_project_dir(self):
        """一時プロジェクトディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # プロジェクト構造作成
            project_path = Path(temp_dir)
            
            # src ディレクトリ
            src_dir = project_path / "src"
            src_dir.mkdir()
            
            rag_dir = src_dir / "rag"
            rag_dir.mkdir()
            
            # サンプルファイル作成
            (rag_dir / "rag_system.py").write_text('''
"""RAGシステムメインファイル"""

class RAGSystem:
    def __init__(self):
        self.memory_cache = {}
        
    def process_query(self, query):
        # メモリ使用量が多いコード（改善対象）
        large_data = [i for i in range(10000)]
        return f"Response for: {query}"
        
    def get_system_stats(self):
        return {"requests": 100}
''')
            
            # tests ディレクトリ
            tests_dir = project_path / "tests"
            tests_dir.mkdir()
            
            unit_dir = tests_dir / "unit"
            unit_dir.mkdir()
            
            yield temp_dir
    
    def test_end_to_end_improvement_cycle(self, mock_rag_system, mock_claude_client, temp_project_dir):
        """エンドツーエンド改善サイクルテスト"""
        
        # 1. システム診断
        diagnostics = SystemDiagnostics(mock_rag_system)
        
        # パフォーマンス監視モック（高メモリ使用量を報告）
        with patch.object(diagnostics.modules['performance'], 'diagnose') as mock_perf_diagnose:
            mock_perf_diagnose.return_value = [
                DiagnosticResult(
                    "performance", "memory_usage_percent", 85.0,
                    target_value=80.0, status="warning",
                    recommendations=["メモリ最適化を検討"]
                ),
                DiagnosticResult(
                    "rag_system", "response_success_rate", 95.0,
                    target_value=90.0, status="good"
                )
            ]
            
            # コード品質分析モック
            with patch.object(diagnostics.modules['code_quality'], 'diagnose') as mock_code_diagnose:
                mock_code_diagnose.return_value = [
                    DiagnosticResult(
                        "code_quality", "total_python_files", 5,
                        status="good"
                    )
                ]
                
                # 学習効果評価モック
                with patch.object(diagnostics.modules['learning'], 'diagnose') as mock_learning_diagnose:
                    mock_learning_diagnose.return_value = [
                        DiagnosticResult(
                            "learning", "knowledge_base_size", 150,
                            status="good"
                        )
                    ]
                    
                    # 2. 改善計画生成
                    improvement_engine = ImprovementEngine(diagnostics, mock_claude_client)
                    roadmap = improvement_engine.generate_improvement_plan(timeframe_weeks=4)
                    
                    # 改善計画が生成されているはず
                    assert isinstance(roadmap, ImprovementRoadmap)
                    assert len(roadmap.opportunities) > 0
                    assert roadmap.total_estimated_time > 0
                    
                    # 高優先度の改善機会があるはず
                    high_priority_opportunities = [
                        opp for opp in roadmap.opportunities 
                        if opp.priority in [Priority.HIGH, Priority.CRITICAL]
                    ]
                    assert len(high_priority_opportunities) > 0
    
    def test_autonomous_implementation_integration(self, mock_claude_client, temp_project_dir):
        """自律実装システム統合テスト"""
        
        # 改善機会作成
        opportunity = ImprovementOpportunity(
            id="integration_test_opp",
            title="メモリ最適化実装",
            description="RAGシステムのメモリ使用量を削減",
            improvement_type=ImprovementType.PERFORMANCE,
            priority=Priority.HIGH,
            estimated_time_hours=4.0
        )
        
        # 自律実装システム初期化
        autonomous_impl = AutonomousImplementation(mock_claude_client, temp_project_dir)
        
        # システムツール・ファイルツールモック
        with patch.object(autonomous_impl.deployment_manager, 'system_tool') as mock_system_tool:
            with patch.object(autonomous_impl.code_generator, 'file_tool') as mock_file_tool:
                
                mock_system_tool.execute_command.return_value = {
                    'success': True,
                    'output': 'Tests passed'
                }
                
                mock_file_tool.read_file.return_value = {
                    'success': True,
                    'content': 'original_code = "test"'
                }
                
                mock_file_tool.write_file.return_value = {'success': True}
                
                # ドライラン実行
                dry_result = autonomous_impl.implement_opportunity(opportunity, dry_run=True)
                
                assert dry_result.success is True
                assert dry_result.opportunity_id == "integration_test_opp"
                assert "[DRY RUN]" in dry_result.changes_made[0]
                
                # 実装履歴が記録されているはず
                assert len(autonomous_impl.implementation_history) == 1
    
    def test_quality_assurance_integration(self, mock_claude_client, temp_project_dir):
        """品質保証システム統合テスト"""
        
        # 改善機会と実装計画
        opportunity = ImprovementOpportunity(
            id="qa_test_opp",
            title="品質保証テスト",
            description="テスト用改善機会",
            improvement_type=ImprovementType.CODE_QUALITY,
            risk_score=25.0,  # 中リスク
            complexity_level="moderate",
            estimated_time_hours=6.0
        )
        
        implementation_plan = {
            "approach": "段階的実装",
            "steps": [{"step": 1, "description": "コード修正"}],
            "risk_level": "medium"
        }
        
        # 品質保証システム初期化
        qa_system = QualityAssurance(mock_claude_client, temp_project_dir)
        
        # 実装結果作成
        implementation_result = ImplementationResult(
            opportunity_id="qa_test_opp",
            success=True,
            files_modified=["src/test_file.py"],
            changes_made=["テスト変更"]
        )
        
        # 安全性チェック
        safety_checks = qa_system.safety_checker.run_safety_checks(
            opportunity, implementation_plan, implementation_result
        )
        
        # 安全性チェック結果確認
        assert len(safety_checks) > 0
        
        # 品質メトリクス評価
        quality_metrics = qa_system.quality_metrics.evaluate_implementation_quality(
            implementation_result
        )
        
        assert quality_metrics is not None
        assert "overall_score" in quality_metrics
        
        # 承認要求作成
        approval_request = qa_system.human_approval_gate.request_approval(
            opportunity, implementation_plan, safety_checks
        )
        
        assert approval_request.opportunity == opportunity
        assert approval_request.implementation_plan == implementation_plan
        # 中リスクなので手動承認が必要
        assert approval_request.status == ApprovalStatus.PENDING
    
    def test_component_interaction_and_data_flow(self, mock_rag_system, mock_claude_client, temp_project_dir):
        """コンポーネント間の相互作用とデータフロー統合テスト"""
        
        # 1. 診断結果の生成
        diagnostics = SystemDiagnostics(mock_rag_system)
        
        # モック診断結果
        performance_results = [
            DiagnosticResult("performance", "memory_usage", 90.0, status="critical"),
            DiagnosticResult("performance", "response_time", 2.5, status="warning")
        ]
        
        code_quality_results = [
            DiagnosticResult("code_quality", "test_coverage", 45.0, status="warning")
        ]
        
        learning_results = [
            DiagnosticResult("learning", "learning_rate", 0.8, status="good")
        ]
        
        with patch.object(diagnostics, 'run_full_diagnosis') as mock_full_diag:
            mock_full_diag.return_value = {
                'performance': performance_results,
                'code_quality': code_quality_results,
                'learning': learning_results
            }
            
            # 2. 改善エンジンで機会特定
            improvement_engine = ImprovementEngine(diagnostics, mock_claude_client)
            
            # OpportunityIdentifierのモック
            with patch.object(improvement_engine.opportunity_identifier, 'identify_opportunities') as mock_identify:
                mock_opportunities = [
                    ImprovementOpportunity(
                        "perf_opp_1", "メモリ最適化", "メモリ使用量削減",
                        ImprovementType.PERFORMANCE, priority=Priority.CRITICAL,
                        impact_score=90.0, effort_score=30.0, risk_score=20.0,
                        related_diagnostics=performance_results[:1]
                    ),
                    ImprovementOpportunity(
                        "code_opp_1", "テストカバレッジ向上", "テスト追加",
                        ImprovementType.CODE_QUALITY, priority=Priority.HIGH,
                        impact_score=70.0, effort_score=40.0, risk_score=10.0,
                        related_diagnostics=code_quality_results
                    )
                ]
                
                mock_identify.return_value = mock_opportunities
                
                # 3. ロードマップ生成
                roadmap = improvement_engine.generate_improvement_plan(timeframe_weeks=6)
                
                # ロードマップ検証
                assert isinstance(roadmap, ImprovementRoadmap)
                assert len(roadmap.opportunities) == 2
                
                # 優先度順であることを確認
                assert roadmap.opportunities[0].priority == Priority.CRITICAL
                assert roadmap.opportunities[1].priority == Priority.HIGH
                
                # 4. 自律実装の検証
                autonomous_impl = AutonomousImplementation(mock_claude_client, temp_project_dir)
                
                # 最高優先度の機会を実装
                critical_opportunity = roadmap.opportunities[0]
                
                with patch.object(autonomous_impl.code_generator, 'file_tool') as mock_file_tool:
                    with patch.object(autonomous_impl.deployment_manager, 'system_tool') as mock_system_tool:
                        
                        mock_file_tool.read_file.return_value = {'success': True, 'content': 'code'}
                        mock_file_tool.write_file.return_value = {'success': True}
                        mock_system_tool.execute_command.return_value = {'success': True}
                        
                        impl_result = autonomous_impl.implement_opportunity(
                            critical_opportunity, dry_run=True
                        )
                        
                        # 実装結果検証
                        assert impl_result.success is True
                        assert impl_result.opportunity_id == "perf_opp_1"
                        
                        # 5. 品質保証の検証
                        qa_system = QualityAssurance(mock_claude_client, temp_project_dir)
                        
                        # 安全性チェック実行
                        safety_checks = qa_system.safety_checker.run_safety_checks(
                            critical_opportunity, 
                            {"approach": "test"}, 
                            impl_result
                        )
                        
                        # 高リスク機会なので安全性チェックが実行されるはず
                        assert len(safety_checks) > 0
                        
                        # 品質メトリクス評価
                        quality_score = qa_system.quality_metrics.evaluate_implementation_quality(impl_result)
                        assert quality_score is not None
    
    def test_error_handling_and_recovery(self, mock_claude_client, temp_project_dir):
        """エラーハンドリングと復旧機能の統合テスト"""
        
        # エラーを起こす改善機会
        problematic_opportunity = ImprovementOpportunity(
            "error_test_opp",
            "エラーテスト",
            "エラー発生テスト",
            ImprovementType.PERFORMANCE,
            priority=Priority.MEDIUM
        )
        
        # 自律実装システム
        autonomous_impl = AutonomousImplementation(mock_claude_client, temp_project_dir)
        
        # ファイル操作エラーのシミュレーション
        with patch.object(autonomous_impl.code_generator, 'file_tool') as mock_file_tool:
            mock_file_tool.read_file.side_effect = Exception("ファイル読み込みエラー")
            
            # エラー発生時の実装
            impl_result = autonomous_impl.implement_opportunity(
                problematic_opportunity, dry_run=False
            )
            
            # エラーが適切にハンドリングされているはず
            assert impl_result.success is False
            assert "ファイル読み込みエラー" in impl_result.error_message
            assert impl_result.opportunity_id == "error_test_opp"
            
            # ロールバック情報が設定されているはず
            assert impl_result.rollback_info is not None
    
    def test_concurrent_improvement_handling(self, mock_claude_client, temp_project_dir):
        """並行改善処理の統合テスト"""
        
        # 複数の改善機会
        opportunities = [
            ImprovementOpportunity(
                f"concurrent_opp_{i}",
                f"改善{i}",
                f"説明{i}",
                ImprovementType.PERFORMANCE,
                priority=Priority.HIGH,
                estimated_time_hours=2.0
            )
            for i in range(3)
        ]
        
        # ロードマップ作成
        from src.self_improvement.improvement_engine import ImprovementRoadmap
        roadmap = ImprovementRoadmap(
            "concurrent_test",
            "並行テストロードマップ",
            opportunities
        )
        
        # 自律実装システム
        autonomous_impl = AutonomousImplementation(mock_claude_client, temp_project_dir)
        
        with patch.object(autonomous_impl, 'implement_opportunity') as mock_implement:
            # 成功・失敗・成功のパターン
            mock_implement.side_effect = [
                ImplementationResult("concurrent_opp_0", True),
                ImplementationResult("concurrent_opp_1", False, error_message="テストエラー"),
                ImplementationResult("concurrent_opp_2", True)
            ]
            
            # ロードマップ実装
            results = autonomous_impl.implement_roadmap(roadmap, dry_run=True)
            
            # 結果検証
            assert len(results) == 2  # 失敗で停止するので2つまで
            assert results[0].success is True
            assert results[1].success is False
            
            # 実装は失敗で停止するはず
            assert mock_implement.call_count == 2
    
    def test_performance_monitoring_during_improvement(self, mock_rag_system, mock_claude_client, temp_project_dir):
        """改善中のパフォーマンス監視統合テスト"""
        
        # パフォーマンス監視付きシステム診断
        diagnostics = SystemDiagnostics(mock_rag_system)
        performance_monitor = diagnostics.modules['performance']
        
        # 改善機会
        opportunity = ImprovementOpportunity(
            "perf_monitor_test",
            "パフォーマンス監視テスト",
            "改善中の監視テスト",
            ImprovementType.PERFORMANCE
        )
        
        # 自律実装システム
        autonomous_impl = AutonomousImplementation(mock_claude_client, temp_project_dir)
        
        with patch.object(autonomous_impl.code_generator, 'file_tool') as mock_file_tool:
            with patch.object(autonomous_impl.deployment_manager, 'system_tool') as mock_system_tool:
                
                mock_file_tool.read_file.return_value = {'success': True, 'content': 'code'}
                mock_file_tool.write_file.return_value = {'success': True}
                mock_system_tool.execute_command.return_value = {'success': True}
                
                # 実装前のパフォーマンス測定
                def mock_operation():
                    time.sleep(0.01)  # 短時間の遅延
                    return "結果"
                
                result, exec_time = performance_monitor.measure_response_time(
                    "test_operation", mock_operation
                )
                
                # 測定結果が記録されているはず
                assert result == "結果"
                assert exec_time > 0
                assert len(performance_monitor.response_times) == 1
                assert len(performance_monitor.history) == 1
                
                # 改善実装
                impl_result = autonomous_impl.implement_opportunity(opportunity, dry_run=True)
                
                # 実装後の検証
                assert impl_result.success is True
                assert impl_result.execution_time > 0


class TestSystemIntegrationEdgeCases:
    """システム統合エッジケーステスト"""
    
    def test_invalid_diagnostic_data_handling(self, mock_claude_client):
        """無効な診断データの処理テスト"""
        
        # 診断システム
        diagnostics = SystemDiagnostics()
        
        # 破損した診断結果をシミュレート
        with patch.object(diagnostics, 'run_full_diagnosis') as mock_diagnosis:
            mock_diagnosis.return_value = {
                'performance': [],  # 空の結果
                'code_quality': [
                    DiagnosticResult("invalid", "metric", "not_a_number", status="unknown")
                ]
            }
            
            # 改善エンジンは無効データを適切に処理するはず
            improvement_engine = ImprovementEngine(diagnostics, mock_claude_client)
            
            # エラーを起こさずに実行されるはず
            roadmap = improvement_engine.generate_improvement_plan()
            
            assert isinstance(roadmap, ImprovementRoadmap)
            # 無効データからは改善機会が特定されないはず
            assert len(roadmap.opportunities) == 0
    
    def test_resource_exhaustion_scenarios(self, mock_claude_client, temp_project_dir):
        """リソース枯渇シナリオテスト"""
        
        # 多数の改善機会を作成（リソース枯渇をシミュレート）
        opportunities = [
            ImprovementOpportunity(
                f"resource_test_{i}",
                f"改善{i}",
                f"説明{i}",
                ImprovementType.PERFORMANCE,
                estimated_time_hours=10.0  # 大きな時間コスト
            )
            for i in range(50)  # 大量の機会
        ]
        
        # ロードマップ生成
        roadmap_generator = RoadmapGenerator()
        roadmap = roadmap_generator.generate_roadmap(
            opportunities, 
            timeframe_weeks=2  # 短い期間
        )
        
        # リソース制約内で適切にフィルタリングされているはず
        assert len(roadmap.opportunities) < len(opportunities)
        assert roadmap.total_estimated_time <= 2 * 40  # 2週間 * 40時間/週
    
    def test_cyclic_dependency_resolution(self):
        """循環依存解決テスト"""
        
        # 循環依存のある改善機会
        opp_a = ImprovementOpportunity(
            "opp_a", "改善A", "説明A", ImprovementType.PERFORMANCE,
            dependencies=["opp_b"]
        )
        
        opp_b = ImprovementOpportunity(
            "opp_b", "改善B", "説明B", ImprovementType.PERFORMANCE,
            dependencies=["opp_c"]
        )
        
        opp_c = ImprovementOpportunity(
            "opp_c", "改善C", "説明C", ImprovementType.PERFORMANCE,
            dependencies=["opp_a"]  # 循環依存
        )
        
        opportunities = [opp_a, opp_b, opp_c]
        
        # ロードマップ生成器の依存関係解決
        roadmap_generator = RoadmapGenerator()
        
        # 循環依存が検出され、適切に処理されるはず
        sorted_opportunities = roadmap_generator._resolve_dependencies(opportunities)
        
        # 循環依存は解決され、すべての機会が含まれるはず
        assert len(sorted_opportunities) == 3
        
        # 依存関係エラーは発生しないはず
        roadmap = roadmap_generator.generate_roadmap(sorted_opportunities)
        assert isinstance(roadmap, ImprovementRoadmap)


if __name__ == "__main__":
    pytest.main([__file__])