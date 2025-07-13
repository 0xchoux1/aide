"""
品質保証システムのユニットテスト

QualityAssurance, SafetyChecker, HumanApprovalGate, QualityMetrics
"""

import pytest
import tempfile
import json
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import sys
sys.path.append('/home/choux1/src/github.com/0xchoux1/aide')

from src.self_improvement.quality_assurance import (
    QualityAssurance,
    SafetyChecker,
    HumanApprovalGate,
    QualityMetrics,
    ApprovalRequest,
    QualityMetric,
    ApprovalStatus,
    RiskLevel
)
from src.self_improvement.improvement_engine import ImprovementOpportunity, ImprovementType, Priority
from src.self_improvement.autonomous_implementation import ImplementationResult, SafetyCheck


class TestApprovalRequest:
    """ApprovalRequest テストクラス"""
    
    def test_approval_request_creation(self):
        """ApprovalRequest 基本作成テスト"""
        opportunity = ImprovementOpportunity(
            id="test_opp",
            title="テスト改善",
            description="テスト説明",
            improvement_type=ImprovementType.PERFORMANCE
        )
        
        implementation_plan = {"approach": "テストアプローチ"}
        risk_assessment = {"overall_risk_level": "medium"}
        estimated_impact = {"impact_score": 75.0}
        
        request = ApprovalRequest(
            id="approval_001",
            opportunity=opportunity,
            implementation_plan=implementation_plan,
            risk_assessment=risk_assessment,
            estimated_impact=estimated_impact
        )
        
        assert request.id == "approval_001"
        assert request.opportunity == opportunity
        assert request.implementation_plan == implementation_plan
        assert request.risk_assessment == risk_assessment
        assert request.estimated_impact == estimated_impact
        assert request.status == ApprovalStatus.PENDING
        assert isinstance(request.created_at, datetime)
        assert isinstance(request.expires_at, datetime)
        assert request.approved_by is None
        assert request.approval_notes is None
    
    def test_approval_request_expiration(self):
        """ApprovalRequest 期限切れテスト"""
        opportunity = ImprovementOpportunity(
            id="expire_test",
            title="期限切れテスト",
            description="説明",
            improvement_type=ImprovementType.PERFORMANCE
        )
        
        request = ApprovalRequest(
            id="expire_request",
            opportunity=opportunity,
            implementation_plan={},
            risk_assessment={},
            estimated_impact={},
            expires_at=datetime.now() - timedelta(hours=1)  # 1時間前に期限切れ
        )
        
        assert request.is_expired() is True
        
        # 期限内の場合
        request.expires_at = datetime.now() + timedelta(hours=1)
        assert request.is_expired() is False
    
    def test_approval_request_to_dict(self):
        """ApprovalRequest to_dict テスト"""
        opportunity = ImprovementOpportunity(
            id="dict_test",
            title="辞書テスト",
            description="説明",
            improvement_type=ImprovementType.CODE_QUALITY
        )
        
        request = ApprovalRequest(
            id="dict_request",
            opportunity=opportunity,
            implementation_plan={"test": "plan"},
            risk_assessment={"level": "low"},
            estimated_impact={"score": 80}
        )
        
        result_dict = request.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['id'] == "dict_request"
        assert result_dict['opportunity_id'] == "dict_test"
        assert result_dict['opportunity_title'] == "辞書テスト"
        assert result_dict['status'] == "pending"
        assert 'created_at' in result_dict
        assert 'expires_at' in result_dict


class TestQualityMetric:
    """QualityMetric テストクラス"""
    
    def test_quality_metric_creation(self):
        """QualityMetric 基本作成テスト"""
        metric = QualityMetric(
            name="test_metric",
            value=75.0,
            target_value=80.0,
            unit="percent",
            category="performance"
        )
        
        assert metric.name == "test_metric"
        assert metric.value == 75.0
        assert metric.target_value == 80.0
        assert metric.unit == "percent"
        assert metric.category == "performance"
        assert isinstance(metric.timestamp, datetime)
    
    def test_quality_metric_score_normalized(self):
        """QualityMetric 正規化スコアテスト"""
        # 標準的なケース
        metric = QualityMetric("test", 80.0, 100.0)
        assert metric.score_normalized() == 80.0
        
        # 目標値超過
        metric = QualityMetric("test", 120.0, 100.0)
        assert metric.score_normalized() == 100.0  # 上限100
        
        # 負の値
        metric = QualityMetric("test", -10.0, 100.0)
        assert metric.score_normalized() == 0.0  # 下限0
        
        # 目標値ゼロ
        metric = QualityMetric("test", 0.0, 0.0)
        assert metric.score_normalized() == 100.0
        
        metric = QualityMetric("test", 5.0, 0.0)
        assert metric.score_normalized() == 0.0
    
    def test_quality_metric_status(self):
        """QualityMetric ステータス判定テスト"""
        # Excellent (90%+)
        metric = QualityMetric("test", 95.0, 100.0)
        assert metric.status() == "excellent"
        
        # Good (75-89%)
        metric = QualityMetric("test", 80.0, 100.0)
        assert metric.status() == "good"
        
        # Warning (50-74%)
        metric = QualityMetric("test", 60.0, 100.0)
        assert metric.status() == "warning"
        
        # Critical (<50%)
        metric = QualityMetric("test", 30.0, 100.0)
        assert metric.status() == "critical"
    
    def test_quality_metric_to_dict(self):
        """QualityMetric to_dict テスト"""
        metric = QualityMetric(
            name="dict_test",
            value=85.5,
            target_value=90.0,
            unit="points",
            category="test_category"
        )
        
        result_dict = metric.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['name'] == "dict_test"
        assert result_dict['value'] == 85.5
        assert result_dict['target_value'] == 90.0
        assert result_dict['unit'] == "points"
        assert result_dict['category'] == "test_category"
        assert 'score_normalized' in result_dict
        assert 'status' in result_dict
        assert 'timestamp' in result_dict


class TestSafetyChecker:
    """SafetyChecker テストクラス"""
    
    def test_safety_checker_initialization(self):
        """SafetyChecker 初期化テスト"""
        checker = SafetyChecker()
        
        assert checker.claude_client is None
        assert len(checker.safety_rules) > 0
    
    def test_safety_checker_with_claude_client(self):
        """Claude Client付きSafetyChecker テスト"""
        mock_claude_client = Mock()
        checker = SafetyChecker(mock_claude_client)
        
        assert checker.claude_client == mock_claude_client
    
    def test_check_implementation_safety_basic(self):
        """基本的な安全性チェックテスト"""
        checker = SafetyChecker()
        
        opportunity = ImprovementOpportunity(
            id="safety_test",
            title="安全性テスト",
            description="安全性チェック説明",
            improvement_type=ImprovementType.PERFORMANCE,
            risk_score=75.0,
            complexity_level="complex",
            estimated_time_hours=25.0
        )
        
        implementation_plan = {
            "steps": [
                {
                    "step": 1,
                    "files_to_modify": ["src/test1.py", "src/test2.py", "src/critical.py"],
                    "risk_level": "medium"
                }
            ]
        }
        
        checks = checker.check_implementation_safety(opportunity, implementation_plan)
        
        # 複数のチェックが実行されるはず
        assert len(checks) >= 3
        
        check_names = [check.check_name for check in checks]
        assert "high_risk_opportunity" in check_names  # リスクスコア75 > 70
        assert "complexity_level" in check_names  # complex
        assert "long_implementation" in check_names  # 25時間 > 20
    
    def test_run_basic_safety_checks(self):
        """基本安全性チェック実行テスト"""
        checker = SafetyChecker()
        
        # 高リスク機会
        high_risk_opp = ImprovementOpportunity(
            id="high_risk",
            title="高リスク改善",
            description="説明",
            improvement_type=ImprovementType.PERFORMANCE,
            risk_score=80.0,
            complexity_level="complex",
            estimated_time_hours=30.0,
            dependencies=["dep1", "dep2"]
        )
        
        implementation_plan = {}
        
        checks = checker._run_basic_safety_checks(high_risk_opp, implementation_plan)
        
        check_dict = {check.check_name: check for check in checks}
        
        # 高リスクチェック
        assert "high_risk_opportunity" in check_dict
        assert not check_dict["high_risk_opportunity"].passed
        assert check_dict["high_risk_opportunity"].severity == "warning"
        
        # 複雑度チェック
        assert "complexity_level" in check_dict
        assert check_dict["complexity_level"].passed  # 警告だが通過
        assert check_dict["complexity_level"].severity == "warning"
        
        # 長時間実装チェック
        assert "long_implementation" in check_dict
        assert check_dict["long_implementation"].passed  # 警告だが通過
        
        # 依存関係チェック
        assert "dependencies_present" in check_dict
        assert check_dict["dependencies_present"].passed
        assert check_dict["dependencies_present"].severity == "info"
    
    def test_run_code_safety_checks(self):
        """コード安全性チェック実行テスト"""
        checker = SafetyChecker()
        
        # 多数ファイル変更
        many_files_plan = {
            "steps": [
                {"files_to_modify": ["file1.py", "file2.py", "file3.py"]},
                {"files_to_modify": ["file4.py", "file5.py", "file6.py"]},
                {"files_to_modify": ["file7.py", "file8.py", "file9.py", "file10.py", "file11.py"]}
            ]
        }
        
        checks = checker._run_code_safety_checks(many_files_plan)
        
        # 多数ファイル変更警告
        many_files_checks = [c for c in checks if "many_files_modified" in c.check_name]
        assert len(many_files_checks) == 1
        assert not many_files_checks[0].passed
        assert many_files_checks[0].severity == "warning"
        
        # 重要ファイル変更
        critical_files_plan = {
            "steps": [
                {"files_to_modify": ["src/rag/rag_system.py", "src/agents/base_agent.py"]}
            ]
        }
        
        checks = checker._run_code_safety_checks(critical_files_plan)
        
        critical_checks = [c for c in checks if "critical_file_modification" in c.check_name]
        assert len(critical_checks) >= 1  # 重要ファイルごとに1つ
        for check in critical_checks:
            assert check.passed  # 警告だが通過
            assert check.severity == "warning"
    
    @patch('src.self_improvement.quality_assurance.ClaudeCodeClient')
    def test_run_ai_safety_analysis_success(self, mock_claude_class):
        """AI安全性分析成功テスト"""
        mock_claude_client = Mock()
        mock_response = Mock()
        mock_response.success = True
        mock_response.content = '''
AI安全性分析結果：

```json
{
  "overall_risk_level": "medium",
  "risk_areas": [
    {
      "area": "データ破損リスク",
      "level": "low",
      "reason": "バックアップ機能があるため",
      "mitigation": "定期的なバックアップ実行"
    },
    {
      "area": "パフォーマンス劣化リスク",
      "level": "medium",
      "reason": "大幅な変更のため",
      "mitigation": "段階的な実装"
    }
  ],
  "recommendations": ["段階的実装", "継続的監視"],
  "approval_recommended": true
}
```
'''
        mock_claude_client.generate_response.return_value = mock_response
        
        checker = SafetyChecker(mock_claude_client)
        
        opportunity = ImprovementOpportunity(
            id="ai_test",
            title="AI分析テスト",
            description="説明",
            improvement_type=ImprovementType.PERFORMANCE
        )
        
        implementation_plan = {"approach": "テストアプローチ"}
        
        checks = checker._run_ai_safety_analysis(opportunity, implementation_plan)
        
        assert len(checks) >= 3  # 全体リスク + 個別リスク領域 + 承認推奨
        
        check_names = [check.check_name for check in checks]
        assert "ai_overall_risk_assessment" in check_names
        assert "ai_approval_recommendation" in check_names
        
        # 個別リスク領域チェック
        risk_checks = [c for c in checks if c.check_name.startswith("ai_risk_")]
        assert len(risk_checks) == 2  # データ破損、パフォーマンス劣化
    
    def test_run_ai_safety_analysis_fallback(self):
        """AI安全性分析フォールバックテスト"""
        checker = SafetyChecker(None)  # Claude Clientなし
        
        opportunity = ImprovementOpportunity(
            id="fallback_test",
            title="フォールバックテスト",
            description="説明",
            improvement_type=ImprovementType.PERFORMANCE
        )
        
        implementation_plan = {}
        
        checks = checker._run_ai_safety_analysis(opportunity, implementation_plan)
        
        # フォールバックチェックが1つ
        assert len(checks) == 1
        assert checks[0].check_name == "ai_safety_fallback"
        assert checks[0].passed is True
        assert checks[0].severity == "info"
        assert "手動確認を推奨" in checks[0].message


class TestHumanApprovalGate:
    """HumanApprovalGate テストクラス"""
    
    def test_human_approval_gate_initialization(self):
        """HumanApprovalGate 初期化テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            approval_file = f"{temp_dir}/test_approvals.json"
            gate = HumanApprovalGate(approval_file)
            
            assert gate.approval_storage_path == approval_file
            assert gate.pending_approvals == {}
    
    def test_request_approval_auto_approve(self):
        """承認リクエスト - 自動承認テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            approval_file = f"{temp_dir}/test_approvals.json"
            gate = HumanApprovalGate(approval_file)
            
            # 低リスク改善機会
            opportunity = ImprovementOpportunity(
                id="auto_approve_test",
                title="自動承認テスト",
                description="低リスク改善",
                improvement_type=ImprovementType.PERFORMANCE,
                risk_score=10.0,
                complexity_level="simple",
                estimated_time_hours=2.0
            )
            
            implementation_plan = {
                "steps": [{"files_to_modify": ["single_file.py"]}]
            }
            
            safety_checks = [
                SafetyCheck("test_check", True, "成功")
            ]
            
            request = gate.request_approval(opportunity, implementation_plan, safety_checks)
            
            # 自動承認されるはず
            assert request.status == ApprovalStatus.APPROVED
            assert request.approved_by == "auto_approval_system"
            assert "自動承認" in request.approval_notes
    
    def test_request_approval_human_required(self):
        """承認リクエスト - 人間承認必要テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            approval_file = f"{temp_dir}/test_approvals.json"
            gate = HumanApprovalGate(approval_file)
            
            # 高リスク改善機会
            opportunity = ImprovementOpportunity(
                id="human_approval_test",
                title="人間承認テスト",
                description="高リスク改善",
                improvement_type=ImprovementType.PERFORMANCE,
                risk_score=80.0,
                complexity_level="complex",
                estimated_time_hours=40.0
            )
            
            implementation_plan = {
                "steps": [{"files_to_modify": [f"file_{i}.py" for i in range(10)]}]
            }
            
            safety_checks = [
                SafetyCheck("critical_check", False, "重要チェック失敗", "warning")
            ]
            
            request = gate.request_approval(opportunity, implementation_plan, safety_checks)
            
            # 人間承認待ちになるはず
            assert request.status == ApprovalStatus.PENDING
            assert request.id in gate.pending_approvals
    
    def test_approve_request(self):
        """承認リクエスト承認テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            approval_file = f"{temp_dir}/test_approvals.json"
            gate = HumanApprovalGate(approval_file)
            
            # 承認待ちリクエスト作成
            opportunity = ImprovementOpportunity(
                id="approve_test",
                title="承認テスト",
                description="説明",
                improvement_type=ImprovementType.PERFORMANCE,
                risk_score=70.0
            )
            
            request = gate.request_approval(opportunity, {}, [])
            request_id = request.id
            
            # 承認実行
            success = gate.approve_request(request_id, "test_approver", "承認理由")
            
            assert success is True
            assert request.status == ApprovalStatus.APPROVED
            assert request.approved_by == "test_approver"
            assert request.approval_notes == "承認理由"
            assert request_id not in gate.pending_approvals
    
    def test_reject_request(self):
        """承認リクエスト拒否テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            approval_file = f"{temp_dir}/test_approvals.json"
            gate = HumanApprovalGate(approval_file)
            
            # 承認待ちリクエスト作成
            opportunity = ImprovementOpportunity(
                id="reject_test",
                title="拒否テスト",
                description="説明",
                improvement_type=ImprovementType.PERFORMANCE,
                risk_score=70.0
            )
            
            request = gate.request_approval(opportunity, {}, [])
            request_id = request.id
            
            # 拒否実行
            success = gate.reject_request(request_id, "test_rejector", "拒否理由")
            
            assert success is True
            assert request.status == ApprovalStatus.REJECTED
            assert request.approved_by == "test_rejector"
            assert request.approval_notes == "拒否理由"
            assert request_id not in gate.pending_approvals
    
    def test_get_pending_approvals_with_expiration(self):
        """期限切れ含む保留承認取得テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            approval_file = f"{temp_dir}/test_approvals.json"
            gate = HumanApprovalGate(approval_file)
            
            # 期限切れリクエスト作成
            opportunity = ImprovementOpportunity(
                id="expired_test",
                title="期限切れテスト",
                description="説明",
                improvement_type=ImprovementType.PERFORMANCE,
                risk_score=70.0
            )
            
            request = gate.request_approval(opportunity, {}, [])
            request.expires_at = datetime.now() - timedelta(hours=1)  # 期限切れに設定
            gate.pending_approvals[request.id] = request
            
            # 有効なリクエスト作成
            opportunity2 = ImprovementOpportunity(
                id="valid_test",
                title="有効テスト",
                description="説明",
                improvement_type=ImprovementType.PERFORMANCE,
                risk_score=70.0
            )
            
            request2 = gate.request_approval(opportunity2, {}, [])
            
            pending = gate.get_pending_approvals()
            
            # 期限切れは除去され、有効なもののみ返される
            assert len(pending) == 1
            assert pending[0].id == request2.id
    
    def test_assess_risk(self):
        """リスク評価テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            approval_file = f"{temp_dir}/test_approvals.json"
            gate = HumanApprovalGate(approval_file)
            
            opportunity = ImprovementOpportunity(
                id="risk_test",
                title="リスクテスト",
                description="説明",
                improvement_type=ImprovementType.PERFORMANCE,
                risk_score=85.0,
                complexity_level="complex",
                estimated_time_hours=35.0
            )
            
            implementation_plan = {
                "steps": [{"files_to_modify": [f"file_{i}.py" for i in range(8)]}]
            }
            
            safety_checks = [
                SafetyCheck("critical1", False, "重要エラー1", "error"),
                SafetyCheck("warning1", False, "警告1", "warning"),
                SafetyCheck("warning2", False, "警告2", "warning")
            ]
            
            risk_assessment = gate._assess_risk(opportunity, implementation_plan, safety_checks)
            
            assert risk_assessment['overall_risk_level'] == RiskLevel.CRITICAL.value  # criticalエラー > 0
            assert risk_assessment['risk_score'] == 85.0
            assert risk_assessment['critical_safety_failures'] == 1
            assert risk_assessment['warning_safety_failures'] == 2
            assert risk_assessment['complexity_level'] == "complex"
            assert risk_assessment['files_to_modify_count'] == 8
    
    def test_should_auto_approve(self):
        """自動承認判定テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            approval_file = f"{temp_dir}/test_approvals.json"
            gate = HumanApprovalGate(approval_file)
            
            # 自動承認可能ケース
            low_risk_assessment = {
                "overall_risk_level": "low",
                "critical_safety_failures": 0,
                "complexity_level": "simple",
                "files_to_modify_count": 2,
                "estimated_time_hours": 3.0
            }
            
            safety_checks = [SafetyCheck("test", True, "成功")]
            
            should_approve = gate._should_auto_approve(low_risk_assessment, safety_checks)
            assert should_approve is True
            
            # 自動承認不可ケース（高リスク）
            high_risk_assessment = {
                "overall_risk_level": "high",
                "critical_safety_failures": 0,
                "complexity_level": "simple",
                "files_to_modify_count": 2,
                "estimated_time_hours": 3.0
            }
            
            should_approve = gate._should_auto_approve(high_risk_assessment, safety_checks)
            assert should_approve is False
            
            # 自動承認不可ケース（criticalエラー）
            critical_assessment = {
                "overall_risk_level": "low",
                "critical_safety_failures": 1,
                "complexity_level": "simple",
                "files_to_modify_count": 2,
                "estimated_time_hours": 3.0
            }
            
            should_approve = gate._should_auto_approve(critical_assessment, safety_checks)
            assert should_approve is False


class TestQualityMetrics:
    """QualityMetrics テストクラス"""
    
    def test_quality_metrics_initialization(self):
        """QualityMetrics 初期化テスト"""
        metrics = QualityMetrics()
        
        assert metrics.metrics_history == []
        assert len(metrics.target_metrics) > 0
        assert "system_health_score" in metrics.target_metrics
        assert "implementation_success_rate" in metrics.target_metrics
    
    def test_collect_current_metrics_implementation(self):
        """実装結果メトリクス収集テスト"""
        metrics = QualityMetrics()
        
        implementation_results = [
            ImplementationResult("opp1", True, execution_time=120.0, files_modified=["file1.py", "file2.py"], tests_generated=["test1.py"]),
            ImplementationResult("opp2", False, execution_time=300.0, files_modified=["file3.py"]),
            ImplementationResult("opp3", True, execution_time=180.0, files_modified=["file4.py"], tests_generated=["test2.py"])
        ]
        
        collected_metrics = metrics.collect_current_metrics({}, implementation_results)
        
        # 収集されたメトリクス確認
        metric_names = [m.name for m in collected_metrics]
        
        assert "implementation_success_rate" in metric_names
        assert "average_implementation_time" in metric_names
        assert "files_per_implementation" in metric_names
        assert "test_generation_rate" in metric_names
        
        # 実装成功率: 2/3 * 100 = 66.67%
        success_rate_metric = next(m for m in collected_metrics if m.name == "implementation_success_rate")
        assert abs(success_rate_metric.value - 66.67) < 0.1
        
        # 平均実装時間: (120+300+180)/3 = 200秒
        avg_time_metric = next(m for m in collected_metrics if m.name == "average_implementation_time")
        assert avg_time_metric.value == 200.0
        
        # テスト生成率: 2/3 * 100 = 66.67%
        test_rate_metric = next(m for m in collected_metrics if m.name == "test_generation_rate")
        assert abs(test_rate_metric.value - 66.67) < 0.1
    
    def test_collect_current_metrics_diagnostics(self):
        """診断結果メトリクス収集テスト"""
        metrics = QualityMetrics()
        
        # モック診断結果
        from src.self_improvement.diagnostics import DiagnosticResult
        
        mock_diagnostics_results = {
            'health_score': 85.0,
            'total_metrics': 10,
            'detailed_results': {
                'performance': [
                    Mock(metric_name="memory_usage", value=70.0, target_value=80.0),
                    Mock(metric_name="cpu_usage", value=45.0, target_value=70.0)
                ],
                'code_quality': [
                    Mock(metric_name="test_coverage", value=75.0, target_value=80.0)
                ]
            }
        }
        
        collected_metrics = metrics.collect_current_metrics(mock_diagnostics_results, [])
        
        # システムヘルススコア
        health_metrics = [m for m in collected_metrics if m.name == "system_health_score"]
        assert len(health_metrics) == 1
        assert health_metrics[0].value == 85.0
        assert health_metrics[0].target_value == 90.0
        
        # パフォーマンスメトリクス
        perf_metrics = [m for m in collected_metrics if m.name.startswith("performance_")]
        assert len(perf_metrics) == 2
        
        # 履歴に追加されているはず
        assert len(metrics.metrics_history) == len(collected_metrics)
    
    def test_get_metrics_summary(self):
        """メトリクス概要取得テスト"""
        metrics = QualityMetrics()
        
        # テストメトリクス追加
        test_metrics = [
            QualityMetric("metric1", 90.0, 100.0, category="performance"),
            QualityMetric("metric2", 75.0, 100.0, category="performance"),
            QualityMetric("metric3", 85.0, 100.0, category="code_quality"),
            QualityMetric("metric4", 60.0, 100.0, category="code_quality")
        ]
        
        # 履歴に追加
        metrics.metrics_history.extend(test_metrics)
        
        summary = metrics.get_metrics_summary(days=7)
        
        assert summary['total_metrics'] == 4
        assert summary['overall_score'] == 77.5  # (90+75+85+60)/4
        assert summary['status'] == "good"  # 75以上
        
        # カテゴリ別集計確認
        assert 'performance' in summary['category_summaries']
        assert 'code_quality' in summary['category_summaries']
        
        perf_summary = summary['category_summaries']['performance']
        assert perf_summary['count'] == 2
        assert perf_summary['average_score'] == 82.5  # (90+75)/2
    
    def test_get_trend_analysis(self):
        """トレンド分析テスト"""
        metrics = QualityMetrics()
        
        # 改善トレンドのデータ作成
        base_time = datetime.now() - timedelta(days=10)
        trend_metrics = []
        
        for i, value in enumerate([50, 55, 60, 65, 70, 75]):
            metric = QualityMetric("trend_test", value, 100.0)
            metric.timestamp = base_time + timedelta(days=i)
            trend_metrics.append(metric)
        
        metrics.metrics_history.extend(trend_metrics)
        
        trend_analysis = metrics.get_trend_analysis("trend_test", days=15)
        
        assert trend_analysis['trend'] == "improving"
        assert trend_analysis['data_points'] == 6
        assert trend_analysis['first_period_avg'] < trend_analysis['second_period_avg']
        assert trend_analysis['latest_value'] == 75.0
        assert trend_analysis['target_value'] == 100.0
    
    def test_get_trend_analysis_insufficient_data(self):
        """トレンド分析データ不足テスト"""
        metrics = QualityMetrics()
        
        # データ1件のみ
        single_metric = QualityMetric("insufficient_test", 80.0, 100.0)
        metrics.metrics_history.append(single_metric)
        
        trend_analysis = metrics.get_trend_analysis("insufficient_test", days=7)
        
        assert trend_analysis['trend'] == "insufficient_data"
        assert trend_analysis['data_points'] == 1


class TestQualityAssurance:
    """QualityAssurance 統合テストクラス"""
    
    def test_quality_assurance_initialization(self):
        """QualityAssurance 初期化テスト"""
        mock_claude_client = Mock()
        qa = QualityAssurance(mock_claude_client)
        
        assert qa.claude_client == mock_claude_client
        assert isinstance(qa.safety_checker, SafetyChecker)
        assert isinstance(qa.approval_gate, HumanApprovalGate)
        assert isinstance(qa.quality_metrics, QualityMetrics)
    
    def test_assess_implementation_readiness_ready(self):
        """実装準備評価 - 準備完了テスト"""
        qa = QualityAssurance(None)
        
        # 低リスク改善機会
        opportunity = ImprovementOpportunity(
            id="ready_test",
            title="準備完了テスト",
            description="低リスク改善",
            improvement_type=ImprovementType.PERFORMANCE,
            risk_score=15.0,
            complexity_level="simple",
            estimated_time_hours=3.0
        )
        
        implementation_plan = {
            "steps": [{"files_to_modify": ["simple_file.py"]}]
        }
        
        # safety_checkerとapproval_gateをモック
        qa.safety_checker = Mock()
        qa.safety_checker.check_implementation_safety.return_value = [
            SafetyCheck("test_check", True, "成功")
        ]
        
        qa.approval_gate = Mock()
        mock_approval = Mock()
        mock_approval.status = ApprovalStatus.APPROVED
        mock_approval.to_dict.return_value = {"status": "approved"}
        mock_approval.risk_assessment = {"overall_risk_level": "low"}
        qa.approval_gate.request_approval.return_value = mock_approval
        
        assessment = qa.assess_implementation_readiness(opportunity, implementation_plan)
        
        assert assessment['ready_for_implementation'] is True
        assert assessment['risk_level'] == "low"
        assert "実装準備完了" in ' '.join(assessment['next_steps'])
    
    def test_assess_implementation_readiness_not_ready(self):
        """実装準備評価 - 準備未完了テスト"""
        qa = QualityAssurance(None)
        
        # 高リスク改善機会
        opportunity = ImprovementOpportunity(
            id="not_ready_test",
            title="準備未完了テスト",
            description="高リスク改善",
            improvement_type=ImprovementType.PERFORMANCE,
            risk_score=85.0
        )
        
        implementation_plan = {}
        
        # safety_checkerとapproval_gateをモック
        qa.safety_checker = Mock()
        qa.safety_checker.check_implementation_safety.return_value = [
            SafetyCheck("critical_check", False, "重要エラー", "error")
        ]
        
        qa.approval_gate = Mock()
        mock_approval = Mock()
        mock_approval.status = ApprovalStatus.PENDING
        mock_approval.to_dict.return_value = {"status": "pending"}
        mock_approval.risk_assessment = {"overall_risk_level": "high"}
        qa.approval_gate.request_approval.return_value = mock_approval
        
        assessment = qa.assess_implementation_readiness(opportunity, implementation_plan)
        
        assert assessment['ready_for_implementation'] is False
        assert assessment['risk_level'] == "high"
        next_steps_text = ' '.join(assessment['next_steps'])
        assert "承認を待機中" in next_steps_text or "安全性問題を解決" in next_steps_text
    
    def test_post_implementation_assessment(self):
        """実装後評価テスト"""
        qa = QualityAssurance(None)
        
        implementation_result = ImplementationResult(
            opportunity_id="post_test",
            success=True,
            execution_time=240.0,  # 4分
            files_modified=["file1.py", "file2.py"],
            tests_generated=["test1.py"]
        )
        
        diagnostics_results = {
            'health_score': 88.0,
            'total_metrics': 5
        }
        
        # quality_metricsをモック
        qa.quality_metrics = Mock()
        mock_metrics = [
            QualityMetric("test_metric", 85.0, 100.0)
        ]
        qa.quality_metrics.collect_current_metrics.return_value = mock_metrics
        
        assessment = qa.post_implementation_assessment(implementation_result, diagnostics_results)
        
        assert 'implementation_result' in assessment
        assert 'quality_assessment' in assessment
        assert 'current_metrics' in assessment
        assert 'recommendations' in assessment
        assert 'overall_assessment' in assessment
        
        # 品質評価確認
        quality_assessment = assessment['quality_assessment']
        assert 'quality_scores' in quality_assessment
        assert 'overall_quality_score' in quality_assessment
        assert quality_assessment['quality_level'] in ['excellent', 'good', 'acceptable', 'poor']
    
    def test_calculate_overall_assessment(self):
        """総合評価計算テスト"""
        qa = QualityAssurance(None)
        
        # 優秀レベル
        excellent_assessment = {"overall_quality_score": 95.0}
        result = qa._calculate_overall_assessment(excellent_assessment)
        assert "優秀" in result
        
        # 良好レベル
        good_assessment = {"overall_quality_score": 80.0}
        result = qa._calculate_overall_assessment(good_assessment)
        assert "良好" in result
        
        # 許容範囲レベル
        acceptable_assessment = {"overall_quality_score": 65.0}
        result = qa._calculate_overall_assessment(acceptable_assessment)
        assert "許容範囲" in result
        
        # 要改善レベル
        poor_assessment = {"overall_quality_score": 40.0}
        result = qa._calculate_overall_assessment(poor_assessment)
        assert "要改善" in result


if __name__ == "__main__":
    pytest.main([__file__])