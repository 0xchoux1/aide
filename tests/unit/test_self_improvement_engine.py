"""
改善エンジンシステムのユニットテスト

ImprovementEngine, OpportunityIdentifier, PriorityOptimizer, RoadmapGenerator
"""

import pytest
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import sys
sys.path.append('/home/choux1/src/github.com/0xchoux1/aide')

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
from src.self_improvement.diagnostics import DiagnosticResult, SystemDiagnostics


class TestImprovementOpportunity:
    """ImprovementOpportunity テストクラス"""
    
    def test_improvement_opportunity_creation(self):
        """ImprovementOpportunity 基本作成テスト"""
        opportunity = ImprovementOpportunity(
            id="test_001",
            title="テスト改善機会",
            description="テスト用の改善機会です",
            improvement_type=ImprovementType.PERFORMANCE
        )
        
        assert opportunity.id == "test_001"
        assert opportunity.title == "テスト改善機会"
        assert opportunity.description == "テスト用の改善機会です"
        assert opportunity.improvement_type == ImprovementType.PERFORMANCE
        assert opportunity.priority == Priority.MEDIUM
        assert opportunity.impact_score == 0.0
        assert opportunity.effort_score == 0.0
        assert opportunity.risk_score == 0.0
        assert opportunity.roi_score == 0.0
        assert isinstance(opportunity.created_at, datetime)
        assert opportunity.status == "identified"
    
    def test_improvement_opportunity_with_scores(self):
        """スコア付きImprovementOpportunity テスト"""
        opportunity = ImprovementOpportunity(
            id="test_002",
            title="高影響度改善",
            description="高い影響度の改善",
            improvement_type=ImprovementType.CODE_QUALITY,
            priority=Priority.HIGH,
            impact_score=85.0,
            effort_score=40.0,
            risk_score=15.0
        )
        
        assert opportunity.impact_score == 85.0
        assert opportunity.effort_score == 40.0
        assert opportunity.risk_score == 15.0
        assert opportunity.priority == Priority.HIGH
    
    def test_calculate_roi(self):
        """ROI計算テスト"""
        opportunity = ImprovementOpportunity(
            id="test_roi",
            title="ROIテスト",
            description="ROI計算テスト",
            improvement_type=ImprovementType.PERFORMANCE,
            impact_score=80.0,
            effort_score=20.0,
            risk_score=10.0
        )
        
        roi = opportunity.calculate_roi()
        
        # ROI = (80 - 10*0.5) / 20 * 100 = 375
        expected_roi = (80.0 - 10.0 * 0.5) / 20.0 * 100
        assert abs(roi - expected_roi) < 1.0
        assert opportunity.roi_score == roi
    
    def test_calculate_roi_zero_effort(self):
        """労力ゼロでのROI計算テスト"""
        opportunity = ImprovementOpportunity(
            id="test_zero",
            title="ゼロ労力",
            description="労力ゼロテスト",
            improvement_type=ImprovementType.PERFORMANCE,
            impact_score=90.0,
            effort_score=0.0,
            risk_score=5.0
        )
        
        roi = opportunity.calculate_roi()
        
        # 労力ゼロの場合は影響度そのまま
        assert roi == 90.0
    
    def test_to_dict(self):
        """to_dict メソッドテスト"""
        opportunity = ImprovementOpportunity(
            id="test_dict",
            title="辞書テスト",
            description="辞書変換テスト",
            improvement_type=ImprovementType.LEARNING,
            dependencies=["dep1", "dep2"]
        )
        
        result_dict = opportunity.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['id'] == "test_dict"
        assert result_dict['title'] == "辞書テスト"
        assert result_dict['improvement_type'] == "learning"
        assert result_dict['dependencies'] == ["dep1", "dep2"]
        assert 'created_at' in result_dict


class TestImprovementRoadmap:
    """ImprovementRoadmap テストクラス"""
    
    def test_improvement_roadmap_creation(self):
        """ImprovementRoadmap 基本作成テスト"""
        opportunities = [
            ImprovementOpportunity("opp1", "改善1", "説明1", ImprovementType.PERFORMANCE),
            ImprovementOpportunity("opp2", "改善2", "説明2", ImprovementType.CODE_QUALITY)
        ]
        
        roadmap = ImprovementRoadmap(
            id="roadmap_001",
            title="テストロードマップ",
            opportunities=opportunities
        )
        
        assert roadmap.id == "roadmap_001"
        assert roadmap.title == "テストロードマップ"
        assert len(roadmap.opportunities) == 2
        assert roadmap.phases == []
        assert roadmap.total_estimated_time == 0.0
        assert roadmap.expected_roi == 0.0
        assert isinstance(roadmap.created_at, datetime)
    
    def test_calculate_metrics(self):
        """メトリクス計算テスト"""
        opportunities = [
            ImprovementOpportunity("opp1", "改善1", "説明1", ImprovementType.PERFORMANCE, 
                                 estimated_time_hours=5.0, impact_score=80.0, effort_score=20.0),
            ImprovementOpportunity("opp2", "改善2", "説明2", ImprovementType.CODE_QUALITY,
                                 estimated_time_hours=3.0, impact_score=60.0, effort_score=15.0)
        ]
        
        # ROI計算
        for opp in opportunities:
            opp.calculate_roi()
        
        roadmap = ImprovementRoadmap(
            id="metrics_test",
            title="メトリクステスト",
            opportunities=opportunities
        )
        
        roadmap.calculate_metrics()
        
        assert roadmap.total_estimated_time == 8.0  # 5.0 + 3.0
        assert roadmap.expected_roi > 0  # ROIの平均
    
    def test_to_dict(self):
        """to_dict メソッドテスト"""
        opportunities = [
            ImprovementOpportunity("opp1", "改善1", "説明1", ImprovementType.PERFORMANCE)
        ]
        
        phases = [{"phase": 1, "title": "Phase 1", "opportunities": ["opp1"]}]
        
        roadmap = ImprovementRoadmap(
            id="dict_test",
            title="辞書テスト",
            opportunities=opportunities,
            phases=phases
        )
        
        result_dict = roadmap.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['id'] == "dict_test"
        assert result_dict['title'] == "辞書テスト"
        assert len(result_dict['opportunities']) == 1
        assert len(result_dict['phases']) == 1
        assert 'created_at' in result_dict


class TestOpportunityIdentifier:
    """OpportunityIdentifier テストクラス"""
    
    def test_opportunity_identifier_initialization(self):
        """OpportunityIdentifier 初期化テスト"""
        identifier = OpportunityIdentifier()
        
        assert identifier.claude_client is None
        assert len(identifier.opportunity_templates) > 0
    
    def test_opportunity_identifier_with_claude_client(self):
        """Claude Client付きOpportunityIdentifier テスト"""
        mock_claude_client = Mock()
        identifier = OpportunityIdentifier(mock_claude_client)
        
        assert identifier.claude_client == mock_claude_client
    
    def test_identify_opportunities_rule_based(self):
        """ルールベース改善機会特定テスト"""
        identifier = OpportunityIdentifier()
        
        # 診断結果を作成（警告・重要ステータス）
        diagnostic_results = {
            'performance': [
                DiagnosticResult("performance", "memory_usage_percent", 85.0, 
                               target_value=80.0, status="warning",
                               recommendations=["メモリ最適化"]),
                DiagnosticResult("performance", "response_time", 2.5,
                               target_value=1.0, status="critical",
                               recommendations=["応答時間改善"])
            ],
            'code_quality': [
                DiagnosticResult("code_quality", "test_coverage", 45.0,
                               target_value=80.0, status="warning",
                               recommendations=["テスト追加"])
            ]
        }
        
        opportunities = identifier.identify_opportunities(diagnostic_results)
        
        # 改善機会が特定されているはず
        assert len(opportunities) >= 2  # 少なくとも警告・重要な問題分
        
        # 各改善機会の内容確認
        memory_opps = [opp for opp in opportunities if "memory" in opp.title.lower()]
        assert len(memory_opps) >= 1
        
        response_time_opps = [opp for opp in opportunities if "response_time" in opp.title.lower() or "応答時間" in opp.title]
        assert len(response_time_opps) >= 1
    
    def test_identify_opportunities_no_issues(self):
        """問題なしでの改善機会特定テスト"""
        identifier = OpportunityIdentifier()
        
        # 良好な診断結果
        diagnostic_results = {
            'performance': [
                DiagnosticResult("performance", "memory_usage", 60.0,
                               target_value=80.0, status="good"),
                DiagnosticResult("performance", "cpu_usage", 45.0,
                               target_value=70.0, status="good")
            ]
        }
        
        opportunities = identifier.identify_opportunities(diagnostic_results)
        
        # 問題がないので改善機会は少ないはず
        assert len(opportunities) == 0
    
    @patch('src.self_improvement.improvement_engine.ClaudeCodeClient')
    def test_identify_ai_opportunities_success(self, mock_claude_class):
        """AI分析による改善機会特定成功テスト"""
        # Claude Clientモック設定
        mock_claude_client = Mock()
        mock_response = Mock()
        mock_response.success = True
        mock_response.metadata = {
            'structured_output': {
                'opportunities': [
                    {
                        'title': 'AI特定改善1',
                        'description': 'AI分析による改善機会',
                        'type': 'performance',
                        'priority': 'high',
                        'impact_score': 85.0,
                        'effort_score': 30.0,
                        'risk_score': 15.0,
                        'estimated_hours': 6.0,
                        'complexity': 'moderate'
                    }
                ]
            }
        }
        mock_claude_client.generate_structured_response.return_value = mock_response
        
        identifier = OpportunityIdentifier(mock_claude_client)
        
        diagnostic_results = {
            'performance': [
                DiagnosticResult("performance", "memory_usage", 85.0, status="warning")
            ]
        }
        
        opportunities = identifier.identify_opportunities(diagnostic_results)
        
        # AI分析による改善機会が含まれているはず
        ai_opportunities = [opp for opp in opportunities if opp.id.startswith('ai_')]
        assert len(ai_opportunities) >= 1
        
        ai_opp = ai_opportunities[0]
        assert ai_opp.title == 'AI特定改善1'
        assert ai_opp.improvement_type == ImprovementType.PERFORMANCE
        assert ai_opp.priority == Priority.HIGH
    
    def test_match_opportunity_template(self):
        """改善機会テンプレートマッチングテスト"""
        identifier = OpportunityIdentifier()
        
        # メモリ関連の診断結果
        memory_result = DiagnosticResult("system", "memory_usage_percent", 90.0)
        
        template = identifier._match_opportunity_template(memory_result)
        
        assert template is not None
        assert "memory" in template.get("keywords", [])
        assert "type" in template
        assert "impact_score" in template
    
    def test_deduplicate_opportunities(self):
        """改善機会重複除去テスト"""
        identifier = OpportunityIdentifier()
        
        opportunities = [
            ImprovementOpportunity("opp1", "メモリ最適化", "説明", ImprovementType.PERFORMANCE, roi_score=90.0),
            ImprovementOpportunity("opp2", "メモリ最適化", "説明", ImprovementType.PERFORMANCE, roi_score=80.0),  # 重複
            ImprovementOpportunity("opp3", "CPU最適化", "説明", ImprovementType.PERFORMANCE, roi_score=70.0)
        ]
        
        deduplicated = identifier._deduplicate_opportunities(opportunities)
        
        # 重複が除去され、高ROIが残っているはず
        assert len(deduplicated) == 2
        titles = [opp.title for opp in deduplicated]
        assert "メモリ最適化" in titles
        assert "CPU最適化" in titles
        
        # 高ROIの方が残っているはず
        memory_opp = next(opp for opp in deduplicated if opp.title == "メモリ最適化")
        assert memory_opp.roi_score == 90.0


class TestPriorityOptimizer:
    """PriorityOptimizer テストクラス"""
    
    def test_priority_optimizer_initialization(self):
        """PriorityOptimizer 初期化テスト"""
        optimizer = PriorityOptimizer()
        
        assert 'impact' in optimizer.weight_config
        assert 'effort' in optimizer.weight_config
        assert 'risk' in optimizer.weight_config
        assert 'urgency' in optimizer.weight_config
        
        # 重みの合計が1.0になるはず
        total_weight = sum(optimizer.weight_config.values())
        assert abs(total_weight - 1.0) < 0.01
    
    def test_optimize_priorities(self):
        """優先度最適化テスト"""
        optimizer = PriorityOptimizer()
        
        opportunities = [
            ImprovementOpportunity("low_impact", "低影響", "説明", ImprovementType.PERFORMANCE,
                                 impact_score=30.0, effort_score=20.0, risk_score=10.0),
            ImprovementOpportunity("high_impact", "高影響", "説明", ImprovementType.PERFORMANCE,
                                 impact_score=90.0, effort_score=30.0, risk_score=15.0),
            ImprovementOpportunity("medium_impact", "中影響", "説明", ImprovementType.PERFORMANCE,
                                 impact_score=60.0, effort_score=25.0, risk_score=20.0)
        ]
        
        # Critical診断結果を高影響機会に追加
        critical_diag = DiagnosticResult("test", "critical_issue", 0, status="critical")
        opportunities[1].related_diagnostics = [critical_diag]
        
        optimized = optimizer.optimize_priorities(opportunities)
        
        # 優先度順にソートされているはず
        assert len(optimized) == 3
        
        # 高影響度（緊急度も高い）が最優先のはず
        assert optimized[0].id == "high_impact"
        assert optimized[0].priority.value in ['critical', 'high']
    
    def test_calculate_optimized_priority(self):
        """最適化優先度計算テスト"""
        optimizer = PriorityOptimizer()
        
        # 高スコア機会
        high_priority_opp = ImprovementOpportunity(
            "high_test", "高優先度", "説明", ImprovementType.PERFORMANCE,
            impact_score=95.0, effort_score=15.0, risk_score=5.0
        )
        
        # Critical診断結果追加
        critical_diag = DiagnosticResult("test", "critical", 0, status="critical")
        high_priority_opp.related_diagnostics = [critical_diag]
        
        priority = optimizer._calculate_optimized_priority(high_priority_opp)
        
        assert priority in [Priority.CRITICAL, Priority.HIGH]
        
        # 低スコア機会
        low_priority_opp = ImprovementOpportunity(
            "low_test", "低優先度", "説明", ImprovementType.PERFORMANCE,
            impact_score=20.0, effort_score=80.0, risk_score=60.0
        )
        
        priority = optimizer._calculate_optimized_priority(low_priority_opp)
        
        assert priority in [Priority.LOW, Priority.MEDIUM]
    
    def test_analyze_priority_distribution(self):
        """優先度分布分析テスト"""
        optimizer = PriorityOptimizer()
        
        opportunities = [
            ImprovementOpportunity("opp1", "改善1", "説明", ImprovementType.PERFORMANCE, priority=Priority.CRITICAL, impact_score=90.0, effort_score=20.0),
            ImprovementOpportunity("opp2", "改善2", "説明", ImprovementType.PERFORMANCE, priority=Priority.HIGH, impact_score=80.0, effort_score=30.0),
            ImprovementOpportunity("opp3", "改善3", "説明", ImprovementType.PERFORMANCE, priority=Priority.MEDIUM, impact_score=60.0, effort_score=40.0),
            ImprovementOpportunity("opp4", "改善4", "説明", ImprovementType.PERFORMANCE, priority=Priority.LOW, impact_score=30.0, effort_score=50.0)
        ]
        
        analysis = optimizer.analyze_priority_distribution(opportunities)
        
        assert analysis['total_opportunities'] == 4
        assert analysis['distribution']['critical'] == 1
        assert analysis['distribution']['high'] == 1
        assert analysis['distribution']['medium'] == 1
        assert analysis['distribution']['low'] == 1
        assert analysis['high_priority_count'] == 2  # critical + high
        assert analysis['average_impact'] == 65.0  # (90+80+60+30)/4
        assert analysis['average_effort'] == 35.0  # (20+30+40+50)/4


class TestRoadmapGenerator:
    """RoadmapGenerator テストクラス"""
    
    def test_roadmap_generator_initialization(self):
        """RoadmapGenerator 初期化テスト"""
        generator = RoadmapGenerator()
        
        assert generator.claude_client is None
    
    def test_roadmap_generator_with_claude_client(self):
        """Claude Client付きRoadmapGenerator テスト"""
        mock_claude_client = Mock()
        generator = RoadmapGenerator(mock_claude_client)
        
        assert generator.claude_client == mock_claude_client
    
    def test_generate_roadmap(self):
        """ロードマップ生成テスト"""
        generator = RoadmapGenerator()
        
        opportunities = [
            ImprovementOpportunity("opp1", "改善1", "説明1", ImprovementType.PERFORMANCE,
                                 priority=Priority.CRITICAL, estimated_time_hours=8.0),
            ImprovementOpportunity("opp2", "改善2", "説明2", ImprovementType.CODE_QUALITY,
                                 priority=Priority.HIGH, estimated_time_hours=6.0),
            ImprovementOpportunity("opp3", "改善3", "説明3", ImprovementType.LEARNING,
                                 priority=Priority.MEDIUM, estimated_time_hours=4.0),
            ImprovementOpportunity("opp4", "改善4", "説明4", ImprovementType.MAINTENANCE,
                                 priority=Priority.LOW, estimated_time_hours=2.0)
        ]
        
        roadmap = generator.generate_roadmap(opportunities, timeframe_weeks=12)
        
        assert isinstance(roadmap, ImprovementRoadmap)
        assert roadmap.id.startswith("roadmap_")
        assert "12週間" in roadmap.title
        assert len(roadmap.opportunities) == 4
        assert len(roadmap.phases) > 0
        assert roadmap.total_estimated_time == 20.0  # 8+6+4+2
        assert roadmap.expected_roi >= 0
    
    def test_resolve_dependencies(self):
        """依存関係解決テスト"""
        generator = RoadmapGenerator()
        
        opportunities = [
            ImprovementOpportunity("dep_opp", "依存改善", "説明", ImprovementType.PERFORMANCE,
                                 dependencies=["indep_opp"], priority=Priority.HIGH),
            ImprovementOpportunity("indep_opp", "独立改善", "説明", ImprovementType.PERFORMANCE,
                                 dependencies=[], priority=Priority.MEDIUM)
        ]
        
        sorted_opportunities = generator._resolve_dependencies(opportunities)
        
        # 独立した機会が先に来るはず
        assert len(sorted_opportunities) == 2
        assert sorted_opportunities[0].id == "indep_opp"
        assert sorted_opportunities[1].id == "dep_opp"
    
    def test_create_phases(self):
        """フェーズ作成テスト"""
        generator = RoadmapGenerator()
        
        opportunities = [
            ImprovementOpportunity("opp1", "改善1", "説明1", ImprovementType.PERFORMANCE, estimated_time_hours=40.0),
            ImprovementOpportunity("opp2", "改善2", "説明2", ImprovementType.CODE_QUALITY, estimated_time_hours=35.0),
            ImprovementOpportunity("opp3", "改善3", "説明3", ImprovementType.LEARNING, estimated_time_hours=30.0)
        ]
        
        phases = generator._create_phases(opportunities, timeframe_weeks=12)
        
        # 複数フェーズに分割されているはず
        assert len(phases) >= 2
        
        # 各フェーズに必要情報が含まれているはず
        for phase in phases:
            assert 'phase' in phase
            assert 'title' in phase
            assert 'opportunities' in phase
            assert 'estimated_hours' in phase
            assert 'estimated_weeks' in phase
            assert 'focus_areas' in phase
    
    @patch('src.self_improvement.improvement_engine.ClaudeCodeClient')
    def test_enhance_roadmap_with_ai(self, mock_claude_class):
        """AI拡張ロードマップテスト"""
        # Claude Clientモック設定
        mock_claude_client = Mock()
        mock_response = Mock()
        mock_response.success = True
        mock_response.content = "AI分析による戦略的推奨事項：\n1. 段階的実装\n2. リスク軽減\n3. 継続的評価"
        mock_claude_client.generate_response.return_value = mock_response
        
        generator = RoadmapGenerator(mock_claude_client)
        
        # 基本ロードマップ
        opportunities = [
            ImprovementOpportunity("opp1", "改善1", "説明1", ImprovementType.PERFORMANCE, estimated_time_hours=10.0)
        ]
        roadmap = ImprovementRoadmap("test_roadmap", "テストロードマップ", opportunities)
        roadmap.calculate_metrics()
        
        enhanced_roadmap = generator._enhance_roadmap_with_ai(roadmap)
        
        # AI分析フェーズが追加されているはず
        ai_phases = [phase for phase in enhanced_roadmap.phases if phase.get('phase') == 'analysis']
        assert len(ai_phases) == 1
        assert 'AI戦略分析' in ai_phases[0]['title']
        assert 'content' in ai_phases[0]


class TestImprovementEngine:
    """ImprovementEngine テストクラス"""
    
    def test_improvement_engine_initialization(self):
        """ImprovementEngine 初期化テスト"""
        mock_diagnostics = Mock()
        mock_claude_client = Mock()
        
        engine = ImprovementEngine(mock_diagnostics, mock_claude_client)
        
        assert engine.diagnostics == mock_diagnostics
        assert engine.claude_client == mock_claude_client
        assert isinstance(engine.opportunity_identifier, OpportunityIdentifier)
        assert isinstance(engine.priority_optimizer, PriorityOptimizer)
        assert isinstance(engine.roadmap_generator, RoadmapGenerator)
        assert engine.improvement_history == []
    
    def test_generate_improvement_plan(self):
        """改善計画生成テスト"""
        # Mock dependencies
        mock_diagnostics = Mock()
        mock_diagnostics.run_full_diagnosis.return_value = {
            'performance': [
                DiagnosticResult("performance", "memory_usage", 85.0, status="warning")
            ]
        }
        
        engine = ImprovementEngine(mock_diagnostics, None)
        
        # Mock internal components
        mock_opportunity = ImprovementOpportunity(
            "test_opp", "テスト改善", "説明", ImprovementType.PERFORMANCE,
            priority=Priority.HIGH, estimated_time_hours=5.0
        )
        mock_opportunity.calculate_roi()
        
        with patch.object(engine.opportunity_identifier, 'identify_opportunities') as mock_identify:
            with patch.object(engine.priority_optimizer, 'optimize_priorities') as mock_optimize:
                with patch.object(engine.roadmap_generator, 'generate_roadmap') as mock_generate:
                    
                    mock_identify.return_value = [mock_opportunity]
                    mock_optimize.return_value = [mock_opportunity]
                    
                    mock_roadmap = ImprovementRoadmap("test_roadmap", "テストロードマップ", [mock_opportunity])
                    mock_roadmap.calculate_metrics()
                    mock_generate.return_value = mock_roadmap
                    
                    roadmap = engine.generate_improvement_plan(timeframe_weeks=8)
                    
                    # 各ステップが呼ばれているはず
                    mock_diagnostics.run_full_diagnosis.assert_called_once()
                    mock_identify.assert_called_once()
                    mock_optimize.assert_called_once()
                    mock_generate.assert_called_once()
                    
                    # 結果確認
                    assert isinstance(roadmap, ImprovementRoadmap)
                    assert roadmap.id == "test_roadmap"
                    assert len(engine.improvement_history) == 1
    
    def test_get_improvement_summary(self):
        """改善概要取得テスト"""
        mock_diagnostics = Mock()
        engine = ImprovementEngine(mock_diagnostics, None)
        
        # 履歴なしテスト
        summary = engine.get_improvement_summary()
        assert summary["status"] == "no_plans_generated"
        
        # 履歴ありテスト
        mock_opportunity = ImprovementOpportunity(
            "test_opp", "テスト改善", "説明", ImprovementType.PERFORMANCE,
            priority=Priority.HIGH, estimated_time_hours=5.0
        )
        mock_opportunity.calculate_roi()
        
        mock_roadmap = ImprovementRoadmap("test_roadmap", "テストロードマップ", [mock_opportunity])
        mock_roadmap.phases = [{"phase": 1}]
        mock_roadmap.calculate_metrics()
        
        engine.improvement_history.append(mock_roadmap)
        
        summary = engine.get_improvement_summary()
        
        assert summary["latest_roadmap_id"] == "test_roadmap"
        assert summary["total_opportunities"] == 1
        assert summary["total_estimated_time"] == 5.0
        assert summary["phases_count"] == 1
        assert "priority_distribution" in summary
        assert "creation_date" in summary
    
    def test_export_roadmap(self):
        """ロードマップ出力テスト"""
        mock_diagnostics = Mock()
        engine = ImprovementEngine(mock_diagnostics, None)
        
        mock_opportunity = ImprovementOpportunity(
            "test_opp", "テスト改善", "説明", ImprovementType.PERFORMANCE
        )
        roadmap = ImprovementRoadmap("export_test", "出力テスト", [mock_opportunity])
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = f"{temp_dir}/test_roadmap.json"
            result_file = engine.export_roadmap(roadmap, output_file)
            
            assert result_file == output_file
            assert Path(output_file).exists()
            
            # ファイル内容確認
            with open(output_file, 'r') as f:
                data = json.load(f)
            
            assert data['id'] == "export_test"
            assert data['title'] == "出力テスト"
            assert len(data['opportunities']) == 1


if __name__ == "__main__":
    pytest.main([__file__])