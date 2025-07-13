"""
品質保証システム

安全性チェック、人間承認ゲート、品質メトリクス管理
"""

import os
import json
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import re
import ast
from pathlib import Path

from .improvement_engine import ImprovementOpportunity, ImprovementRoadmap
from .autonomous_implementation import ImplementationResult, SafetyCheck
from ..llm.claude_code_client import ClaudeCodeClient


class ApprovalStatus(Enum):
    """承認ステータス"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class RiskLevel(Enum):
    """リスクレベル"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ApprovalRequest:
    """承認リクエスト"""
    id: str
    opportunity: ImprovementOpportunity
    implementation_plan: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    estimated_impact: Dict[str, Any]
    
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approval_notes: Optional[str] = None
    
    def __post_init__(self):
        if self.expires_at is None:
            # デフォルトで24時間後に期限切れ
            self.expires_at = self.created_at + timedelta(hours=24)
    
    def is_expired(self) -> bool:
        """期限切れチェック"""
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'opportunity_id': self.opportunity.id,
            'opportunity_title': self.opportunity.title,
            'risk_assessment': self.risk_assessment,
            'estimated_impact': self.estimated_impact,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'approved_by': self.approved_by,
            'approval_notes': self.approval_notes
        }


@dataclass
class QualityMetric:
    """品質メトリクス"""
    name: str
    value: float
    target_value: float
    unit: str = ""
    category: str = "general"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def score_normalized(self) -> float:
        """正規化スコア（0-100）"""
        if self.target_value == 0:
            return 100 if self.value == 0 else 0
        
        score = (self.value / self.target_value) * 100
        return min(100, max(0, score))
    
    def status(self) -> str:
        """ステータス判定"""
        score = self.score_normalized()
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 50:
            return "warning"
        else:
            return "critical"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'target_value': self.target_value,
            'unit': self.unit,
            'category': self.category,
            'score_normalized': self.score_normalized(),
            'status': self.status(),
            'timestamp': self.timestamp.isoformat()
        }


class SafetyChecker:
    """安全性チェックシステム"""
    
    def __init__(self, claude_client: Optional[ClaudeCodeClient] = None):
        self.claude_client = claude_client
        self.safety_rules = self._load_safety_rules()
        
    def check_implementation_safety(self, opportunity: ImprovementOpportunity,
                                  implementation_plan: Dict[str, Any]) -> List[SafetyCheck]:
        """実装の安全性をチェック"""
        checks = []
        
        # 1. 基本的な安全性チェック
        basic_checks = self._run_basic_safety_checks(opportunity, implementation_plan)
        checks.extend(basic_checks)
        
        # 2. コード安全性チェック
        code_checks = self._run_code_safety_checks(implementation_plan)
        checks.extend(code_checks)
        
        # 3. 影響範囲チェック
        impact_checks = self._run_impact_checks(opportunity, implementation_plan)
        checks.extend(impact_checks)
        
        # 4. AI分析による安全性チェック
        if self.claude_client:
            try:
                ai_checks = self._run_ai_safety_analysis(opportunity, implementation_plan)
                checks.extend(ai_checks)
            except Exception as e:
                checks.append(SafetyCheck(
                    check_name="ai_safety_analysis",
                    passed=False,
                    message=f"AI安全性分析エラー: {e}",
                    severity="warning"
                ))
        
        return checks
    
    def _run_basic_safety_checks(self, opportunity: ImprovementOpportunity,
                                implementation_plan: Dict[str, Any]) -> List[SafetyCheck]:
        """基本的な安全性チェック"""
        checks = []
        
        # リスクレベルチェック
        if opportunity.risk_score > 70:
            checks.append(SafetyCheck(
                check_name="high_risk_opportunity",
                passed=False,
                message=f"高リスクの改善機会です（リスクスコア: {opportunity.risk_score}）",
                severity="warning"
            ))
        
        # 複雑度チェック
        if opportunity.complexity_level == "complex":
            checks.append(SafetyCheck(
                check_name="complexity_level",
                passed=True,
                message="複雑な実装です。慎重に進めてください",
                severity="warning"
            ))
        
        # 実装時間チェック
        if opportunity.estimated_time_hours > 20:
            checks.append(SafetyCheck(
                check_name="long_implementation",
                passed=True,
                message=f"長時間の実装が予想されます（{opportunity.estimated_time_hours}時間）",
                severity="info"
            ))
        
        # 依存関係チェック
        if opportunity.dependencies:
            checks.append(SafetyCheck(
                check_name="dependencies_present",
                passed=True,
                message=f"依存関係があります: {', '.join(opportunity.dependencies)}",
                severity="info"
            ))
        
        return checks
    
    def _run_code_safety_checks(self, implementation_plan: Dict[str, Any]) -> List[SafetyCheck]:
        """コード安全性チェック"""
        checks = []
        
        # 変更ファイル数チェック
        total_files = 0
        for step in implementation_plan.get('steps', []):
            total_files += len(step.get('files_to_modify', []))
        
        if total_files > 10:
            checks.append(SafetyCheck(
                check_name="many_files_modified",
                passed=False,
                message=f"多数のファイルが変更されます（{total_files}ファイル）",
                severity="warning"
            ))
        elif total_files > 5:
            checks.append(SafetyCheck(
                check_name="moderate_files_modified",
                passed=True,
                message=f"中程度のファイル変更が予定されています（{total_files}ファイル）",
                severity="info"
            ))
        
        # 重要ファイルチェック
        critical_files = ['__init__.py', 'base_agent.py', 'rag_system.py', 'claude_code_client.py']
        
        for step in implementation_plan.get('steps', []):
            for file_path in step.get('files_to_modify', []):
                if any(critical_file in file_path for critical_file in critical_files):
                    checks.append(SafetyCheck(
                        check_name="critical_file_modification",
                        passed=True,
                        message=f"重要ファイルが変更されます: {file_path}",
                        severity="warning"
                    ))
        
        return checks
    
    def _run_impact_checks(self, opportunity: ImprovementOpportunity,
                          implementation_plan: Dict[str, Any]) -> List[SafetyCheck]:
        """影響範囲チェック"""
        checks = []
        
        # 影響度チェック
        if opportunity.impact_score > 80:
            checks.append(SafetyCheck(
                check_name="high_impact",
                passed=True,
                message=f"高い影響度が期待されます（{opportunity.impact_score}）",
                severity="info"
            ))
        
        # コンポーネント影響チェック
        affected_components = set()
        for diag in opportunity.related_diagnostics:
            affected_components.add(diag.component)
        
        if len(affected_components) > 3:
            checks.append(SafetyCheck(
                check_name="multiple_components_affected",
                passed=True,
                message=f"複数のコンポーネントに影響します: {', '.join(affected_components)}",
                severity="warning"
            ))
        
        return checks
    
    def _run_ai_safety_analysis(self, opportunity: ImprovementOpportunity,
                               implementation_plan: Dict[str, Any]) -> List[SafetyCheck]:
        """AI分析による安全性チェック"""
        
        analysis_prompt = f"""
以下の改善実装の安全性を分析してください。

改善機会:
- タイトル: {opportunity.title}
- 説明: {opportunity.description}
- リスクスコア: {opportunity.risk_score}
- 複雑度: {opportunity.complexity_level}

実装計画:
{json.dumps(implementation_plan, ensure_ascii=False, indent=2)}

以下の観点で安全性リスクを評価してください：
1. データ破損リスク
2. システム停止リスク
3. セキュリティリスク
4. パフォーマンス劣化リスク
5. 互換性破綻リスク

各リスクについて、リスクレベル（low/medium/high）と理由を説明してください。
また、リスク軽減のための推奨事項を含めてください。

JSON形式で出力してください：
```json
{{
  "overall_risk_level": "low/medium/high",
  "risk_areas": [
    {{"area": "リスク領域", "level": "low/medium/high", "reason": "理由", "mitigation": "軽減策"}}
  ],
  "recommendations": ["推奨事項1", "推奨事項2"],
  "approval_recommended": true/false
}}
```
"""
        
        try:
            response = self.claude_client.generate_response(analysis_prompt)
            
            if response.success:
                # JSONを抽出
                json_match = re.search(r'```json\s*\n(.*?)\n```', response.content, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group(1))
                    
                    checks = []
                    
                    # 全体的なリスクレベル
                    overall_risk = analysis_data.get('overall_risk_level', 'medium')
                    checks.append(SafetyCheck(
                        check_name="ai_overall_risk_assessment",
                        passed=overall_risk in ['low', 'medium'],
                        message=f"AI分析による全体リスク: {overall_risk}",
                        severity="error" if overall_risk == "high" else "warning" if overall_risk == "medium" else "info"
                    ))
                    
                    # 個別リスク領域
                    for risk_area in analysis_data.get('risk_areas', []):
                        area_name = risk_area.get('area', 'unknown')
                        risk_level = risk_area.get('level', 'medium')
                        reason = risk_area.get('reason', '')
                        
                        checks.append(SafetyCheck(
                            check_name=f"ai_risk_{area_name.lower().replace(' ', '_')}",
                            passed=risk_level == 'low',
                            message=f"{area_name}: {reason}",
                            severity="error" if risk_level == "high" else "warning" if risk_level == "medium" else "info"
                        ))
                    
                    # 承認推奨
                    approval_recommended = analysis_data.get('approval_recommended', True)
                    checks.append(SafetyCheck(
                        check_name="ai_approval_recommendation",
                        passed=approval_recommended,
                        message="AI分析による承認推奨" if approval_recommended else "AI分析により承認非推奨",
                        severity="info" if approval_recommended else "warning"
                    ))
                    
                    return checks
        
        except Exception as e:
            print(f"AI安全性分析エラー: {e}")
        
        # フォールバック
        return [SafetyCheck(
            check_name="ai_safety_fallback",
            passed=True,
            message="AI分析が利用できないため、追加的な手動確認を推奨します",
            severity="info"
        )]
    
    def _load_safety_rules(self) -> List[Dict[str, Any]]:
        """安全性ルールを読み込み"""
        return [
            {
                "name": "no_system_commands",
                "pattern": r"(rm\s+-rf|sudo|chmod\s+777|> /dev)",
                "severity": "critical",
                "message": "危険なシステムコマンドが検出されました"
            },
            {
                "name": "no_hardcoded_passwords",
                "pattern": r"(password\s*=\s*['\"][^'\"]+['\"]|api_key\s*=\s*['\"][^'\"]+['\"])",
                "severity": "error",
                "message": "ハードコードされた認証情報が検出されました"
            },
            {
                "name": "no_eval_exec",
                "pattern": r"(eval\s*\(|exec\s*\()",
                "severity": "warning",
                "message": "動的コード実行が検出されました"
            }
        ]


class HumanApprovalGate:
    """人間承認ゲートシステム"""
    
    def __init__(self, approval_storage_path: str = "/tmp/aide_approvals.json"):
        self.approval_storage_path = approval_storage_path
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self._load_approvals()
    
    def request_approval(self, opportunity: ImprovementOpportunity,
                        implementation_plan: Dict[str, Any],
                        safety_checks: List[SafetyCheck]) -> ApprovalRequest:
        """承認をリクエスト"""
        
        # リスク評価
        risk_assessment = self._assess_risk(opportunity, implementation_plan, safety_checks)
        
        # 影響度評価
        impact_assessment = self._assess_impact(opportunity, implementation_plan)
        
        # 承認リクエスト作成
        approval_request = ApprovalRequest(
            id=f"approval_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{opportunity.id}",
            opportunity=opportunity,
            implementation_plan=implementation_plan,
            risk_assessment=risk_assessment,
            estimated_impact=impact_assessment
        )
        
        # 自動承認チェック
        if self._should_auto_approve(risk_assessment, safety_checks):
            approval_request.status = ApprovalStatus.APPROVED
            approval_request.approved_by = "auto_approval_system"
            approval_request.approval_notes = "低リスクのため自動承認"
        else:
            # 人間承認が必要
            self.pending_approvals[approval_request.id] = approval_request
            self._save_approvals()
            
            # 承認リクエスト通知
            self._notify_approval_required(approval_request)
        
        return approval_request
    
    def approve_request(self, approval_id: str, approver: str, notes: str = "") -> bool:
        """承認リクエストを承認"""
        if approval_id in self.pending_approvals:
            request = self.pending_approvals[approval_id]
            
            if request.is_expired():
                request.status = ApprovalStatus.EXPIRED
                return False
            
            request.status = ApprovalStatus.APPROVED
            request.approved_by = approver
            request.approval_notes = notes
            
            del self.pending_approvals[approval_id]
            self._save_approvals()
            
            return True
        
        return False
    
    def reject_request(self, approval_id: str, approver: str, notes: str = "") -> bool:
        """承認リクエストを拒否"""
        if approval_id in self.pending_approvals:
            request = self.pending_approvals[approval_id]
            
            request.status = ApprovalStatus.REJECTED
            request.approved_by = approver
            request.approval_notes = notes
            
            del self.pending_approvals[approval_id]
            self._save_approvals()
            
            return True
        
        return False
    
    def get_pending_approvals(self) -> List[ApprovalRequest]:
        """保留中の承認リクエストを取得"""
        # 期限切れチェック
        expired_ids = []
        for approval_id, request in self.pending_approvals.items():
            if request.is_expired():
                request.status = ApprovalStatus.EXPIRED
                expired_ids.append(approval_id)
        
        # 期限切れを削除
        for approval_id in expired_ids:
            del self.pending_approvals[approval_id]
        
        if expired_ids:
            self._save_approvals()
        
        return list(self.pending_approvals.values())
    
    def _assess_risk(self, opportunity: ImprovementOpportunity,
                    implementation_plan: Dict[str, Any],
                    safety_checks: List[SafetyCheck]) -> Dict[str, Any]:
        """リスク評価"""
        
        # 安全性チェック結果の分析
        critical_failures = sum(1 for check in safety_checks if not check.passed and check.severity == "error")
        warning_failures = sum(1 for check in safety_checks if not check.passed and check.severity == "warning")
        
        # 全体的なリスクレベル決定
        if critical_failures > 0:
            overall_risk = RiskLevel.CRITICAL
        elif opportunity.risk_score > 70 or warning_failures > 3:
            overall_risk = RiskLevel.HIGH
        elif opportunity.risk_score > 40 or warning_failures > 1:
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.LOW
        
        return {
            "overall_risk_level": overall_risk.value,
            "risk_score": opportunity.risk_score,
            "critical_safety_failures": critical_failures,
            "warning_safety_failures": warning_failures,
            "complexity_level": opportunity.complexity_level,
            "estimated_time_hours": opportunity.estimated_time_hours,
            "files_to_modify_count": sum(len(step.get('files_to_modify', [])) for step in implementation_plan.get('steps', []))
        }
    
    def _assess_impact(self, opportunity: ImprovementOpportunity,
                      implementation_plan: Dict[str, Any]) -> Dict[str, Any]:
        """影響度評価"""
        
        affected_components = set()
        for diag in opportunity.related_diagnostics:
            affected_components.add(diag.component)
        
        return {
            "impact_score": opportunity.impact_score,
            "improvement_type": opportunity.improvement_type.value,
            "affected_components": list(affected_components),
            "expected_roi": opportunity.roi_score,
            "business_value": "高" if opportunity.impact_score > 70 else "中" if opportunity.impact_score > 40 else "低"
        }
    
    def _should_auto_approve(self, risk_assessment: Dict[str, Any],
                           safety_checks: List[SafetyCheck]) -> bool:
        """自動承認すべきかチェック"""
        
        # 安全性チェックでクリティカルな問題がある場合は自動承認しない
        critical_failures = risk_assessment.get("critical_safety_failures", 0)
        if critical_failures > 0:
            return False
        
        # 高リスクの場合は自動承認しない
        overall_risk = risk_assessment.get("overall_risk_level", "medium")
        if overall_risk in ["high", "critical"]:
            return False
        
        # 複雑な実装は自動承認しない
        complexity = risk_assessment.get("complexity_level", "moderate")
        if complexity == "complex":
            return False
        
        # 多数のファイル変更は自動承認しない
        files_count = risk_assessment.get("files_to_modify_count", 0)
        if files_count > 5:
            return False
        
        # 長時間の実装は自動承認しない
        estimated_hours = risk_assessment.get("estimated_time_hours", 0)
        if estimated_hours > 8:
            return False
        
        return True
    
    def _notify_approval_required(self, approval_request: ApprovalRequest):
        """承認必要通知"""
        # 簡単な通知実装（コンソール出力）
        print(f"""
=== 承認が必要です ===
ID: {approval_request.id}
改善機会: {approval_request.opportunity.title}
リスクレベル: {approval_request.risk_assessment['overall_risk_level']}
影響度: {approval_request.estimated_impact['impact_score']}
期限: {approval_request.expires_at.strftime('%Y-%m-%d %H:%M:%S')}

承認するには: approval_gate.approve_request('{approval_request.id}', '承認者名', '承認理由')
拒否するには: approval_gate.reject_request('{approval_request.id}', '拒否者名', '拒否理由')
===================
""")
    
    def _save_approvals(self):
        """承認データを保存"""
        try:
            data = {
                approval_id: request.to_dict()
                for approval_id, request in self.pending_approvals.items()
            }
            
            with open(self.approval_storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"承認データ保存エラー: {e}")
    
    def _load_approvals(self):
        """承認データを読み込み"""
        try:
            if os.path.exists(self.approval_storage_path):
                with open(self.approval_storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # ApprovalRequestオブジェクトに復元
                for approval_id, request_data in data.items():
                    # 簡易復元（実際の実装では完全な復元が必要）
                    self.pending_approvals[approval_id] = request_data
                    
        except Exception as e:
            print(f"承認データ読み込みエラー: {e}")


class QualityMetrics:
    """品質メトリクス管理システム"""
    
    def __init__(self):
        self.metrics_history: List[QualityMetric] = []
        self.target_metrics = self._define_target_metrics()
    
    def collect_current_metrics(self, diagnostics_results: Dict[str, Any],
                              implementation_results: List[ImplementationResult]) -> List[QualityMetric]:
        """現在のメトリクスを収集"""
        metrics = []
        
        # 診断結果からメトリクスを抽出
        if diagnostics_results:
            diag_metrics = self._extract_diagnostics_metrics(diagnostics_results)
            metrics.extend(diag_metrics)
        
        # 実装結果からメトリクスを抽出
        if implementation_results:
            impl_metrics = self._extract_implementation_metrics(implementation_results)
            metrics.extend(impl_metrics)
        
        # 履歴に追加
        self.metrics_history.extend(metrics)
        
        return metrics
    
    def _extract_diagnostics_metrics(self, diagnostics_results: Dict[str, Any]) -> List[QualityMetric]:
        """診断結果からメトリクスを抽出"""
        metrics = []
        
        try:
            # システムヘルス概要から
            if 'health_score' in diagnostics_results:
                metrics.append(QualityMetric(
                    name="system_health_score",
                    value=diagnostics_results['health_score'],
                    target_value=90.0,
                    unit="points",
                    category="system_health"
                ))
            
            # 詳細結果から
            detailed_results = diagnostics_results.get('detailed_results', {})
            
            # パフォーマンスメトリクス
            performance_results = detailed_results.get('performance', [])
            for result in performance_results:
                if hasattr(result, 'metric_name') and hasattr(result, 'value'):
                    target = getattr(result, 'target_value', None)
                    if target and isinstance(result.value, (int, float)):
                        metrics.append(QualityMetric(
                            name=f"performance_{result.metric_name}",
                            value=float(result.value),
                            target_value=float(target),
                            category="performance"
                        ))
            
            # コード品質メトリクス
            code_quality_results = detailed_results.get('code_quality', [])
            for result in code_quality_results:
                if hasattr(result, 'metric_name') and hasattr(result, 'value'):
                    target = getattr(result, 'target_value', None)
                    if target and isinstance(result.value, (int, float)):
                        metrics.append(QualityMetric(
                            name=f"code_quality_{result.metric_name}",
                            value=float(result.value),
                            target_value=float(target),
                            category="code_quality"
                        ))
            
            # 学習効果メトリクス
            learning_results = detailed_results.get('learning', [])
            for result in learning_results:
                if hasattr(result, 'metric_name') and hasattr(result, 'value'):
                    target = getattr(result, 'target_value', None)
                    if target and isinstance(result.value, (int, float)):
                        metrics.append(QualityMetric(
                            name=f"learning_{result.metric_name}",
                            value=float(result.value),
                            target_value=float(target),
                            category="learning"
                        ))
        
        except Exception as e:
            print(f"診断メトリクス抽出エラー: {e}")
        
        return metrics
    
    def _extract_implementation_metrics(self, implementation_results: List[ImplementationResult]) -> List[QualityMetric]:
        """実装結果からメトリクスを抽出"""
        metrics = []
        
        if not implementation_results:
            return metrics
        
        try:
            # 実装成功率
            total_implementations = len(implementation_results)
            successful_implementations = sum(1 for r in implementation_results if r.success)
            success_rate = (successful_implementations / total_implementations) * 100
            
            metrics.append(QualityMetric(
                name="implementation_success_rate",
                value=success_rate,
                target_value=95.0,
                unit="percent",
                category="implementation"
            ))
            
            # 平均実装時間
            total_time = sum(r.execution_time for r in implementation_results)
            avg_time = total_time / total_implementations
            
            metrics.append(QualityMetric(
                name="average_implementation_time",
                value=avg_time,
                target_value=300.0,  # 5分
                unit="seconds",
                category="implementation"
            ))
            
            # ファイル変更効率
            total_files = sum(len(r.files_modified) for r in implementation_results)
            if total_files > 0:
                files_per_implementation = total_files / successful_implementations if successful_implementations > 0 else 0
                
                metrics.append(QualityMetric(
                    name="files_per_implementation",
                    value=files_per_implementation,
                    target_value=3.0,  # 平均3ファイル以下
                    unit="files",
                    category="implementation"
                ))
            
            # テスト生成率
            implementations_with_tests = sum(1 for r in implementation_results if r.tests_generated)
            test_generation_rate = (implementations_with_tests / total_implementations) * 100
            
            metrics.append(QualityMetric(
                name="test_generation_rate",
                value=test_generation_rate,
                target_value=80.0,
                unit="percent",
                category="testing"
            ))
        
        except Exception as e:
            print(f"実装メトリクス抽出エラー: {e}")
        
        return metrics
    
    def _define_target_metrics(self) -> Dict[str, float]:
        """目標メトリクスを定義"""
        return {
            "system_health_score": 90.0,
            "implementation_success_rate": 95.0,
            "average_implementation_time": 300.0,  # 5分
            "files_per_implementation": 3.0,
            "test_generation_rate": 80.0,
            "performance_response_time": 1.0,  # 1秒
            "performance_memory_usage": 80.0,  # 80%以下
            "code_quality_test_ratio": 50.0,  # 50%以上
            "learning_knowledge_base_size": 100,
            "learning_average_quality": 0.8
        }
    
    def get_metrics_summary(self, days: int = 7) -> Dict[str, Any]:
        """メトリクス概要を取得"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_date]
        
        if not recent_metrics:
            return {"status": "no_recent_metrics", "days": days}
        
        # カテゴリ別集計
        categories = {}
        for metric in recent_metrics:
            if metric.category not in categories:
                categories[metric.category] = []
            categories[metric.category].append(metric)
        
        category_summaries = {}
        for category, metrics in categories.items():
            scores = [m.score_normalized() for m in metrics]
            category_summaries[category] = {
                "count": len(metrics),
                "average_score": sum(scores) / len(scores),
                "min_score": min(scores),
                "max_score": max(scores)
            }
        
        # 全体スコア
        all_scores = [m.score_normalized() for m in recent_metrics]
        overall_score = sum(all_scores) / len(all_scores)
        
        return {
            "period_days": days,
            "total_metrics": len(recent_metrics),
            "overall_score": overall_score,
            "category_summaries": category_summaries,
            "status": "excellent" if overall_score >= 90 else "good" if overall_score >= 75 else "warning" if overall_score >= 50 else "critical"
        }
    
    def get_trend_analysis(self, metric_name: str, days: int = 30) -> Dict[str, Any]:
        """メトリクストレンド分析"""
        cutoff_date = datetime.now() - timedelta(days=days)
        relevant_metrics = [
            m for m in self.metrics_history
            if m.name == metric_name and m.timestamp >= cutoff_date
        ]
        
        if len(relevant_metrics) < 2:
            return {"trend": "insufficient_data", "data_points": len(relevant_metrics)}
        
        # 時系列でソート
        relevant_metrics.sort(key=lambda x: x.timestamp)
        
        # トレンド計算
        values = [m.score_normalized() for m in relevant_metrics]
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        trend_direction = "improving" if second_avg > first_avg else "declining"
        trend_magnitude = abs(second_avg - first_avg)
        
        return {
            "trend": trend_direction,
            "magnitude": trend_magnitude,
            "first_period_avg": first_avg,
            "second_period_avg": second_avg,
            "data_points": len(relevant_metrics),
            "latest_value": values[-1],
            "target_value": relevant_metrics[-1].target_value
        }


class QualityAssurance:
    """統合品質保証システム"""
    
    def __init__(self, claude_client: Optional[ClaudeCodeClient] = None):
        self.claude_client = claude_client
        self.safety_checker = SafetyChecker(claude_client)
        self.approval_gate = HumanApprovalGate()
        self.quality_metrics = QualityMetrics()
    
    def assess_implementation_readiness(self, opportunity: ImprovementOpportunity,
                                      implementation_plan: Dict[str, Any]) -> Dict[str, Any]:
        """実装準備状況を評価"""
        
        # 1. 安全性チェック
        safety_checks = self.safety_checker.check_implementation_safety(opportunity, implementation_plan)
        
        # 2. 承認リクエスト
        approval_request = self.approval_gate.request_approval(opportunity, implementation_plan, safety_checks)
        
        # 3. 実装可否判定
        ready_for_implementation = (
            approval_request.status == ApprovalStatus.APPROVED and
            not any(check for check in safety_checks if not check.passed and check.severity == "error")
        )
        
        return {
            "ready_for_implementation": ready_for_implementation,
            "approval_request": approval_request.to_dict(),
            "safety_checks": [check.to_dict() for check in safety_checks],
            "risk_level": approval_request.risk_assessment["overall_risk_level"],
            "next_steps": self._determine_next_steps(ready_for_implementation, approval_request, safety_checks)
        }
    
    def _determine_next_steps(self, ready: bool, approval_request: ApprovalRequest,
                            safety_checks: List[SafetyCheck]) -> List[str]:
        """次のステップを決定"""
        steps = []
        
        if not ready:
            if approval_request.status == ApprovalStatus.PENDING:
                steps.append("人間の承認を待機中")
            elif approval_request.status == ApprovalStatus.REJECTED:
                steps.append("承認が拒否されました。計画を見直してください")
            elif approval_request.status == ApprovalStatus.EXPIRED:
                steps.append("承認期限が切れました。再度承認をリクエストしてください")
            
            # 安全性チェックエラーがある場合
            critical_checks = [c for c in safety_checks if not c.passed and c.severity == "error"]
            if critical_checks:
                steps.append(f"重大な安全性問題を解決してください: {', '.join(c.check_name for c in critical_checks)}")
        else:
            steps.append("実装準備完了")
            steps.append("実装を開始できます")
        
        return steps
    
    def post_implementation_assessment(self, implementation_result: ImplementationResult,
                                     diagnostics_results: Dict[str, Any]) -> Dict[str, Any]:
        """実装後評価"""
        
        # 1. 品質メトリクス更新
        current_metrics = self.quality_metrics.collect_current_metrics(
            diagnostics_results, [implementation_result]
        )
        
        # 2. 実装品質評価
        quality_assessment = self._assess_implementation_quality(implementation_result, current_metrics)
        
        # 3. 改善推奨事項
        recommendations = self._generate_post_implementation_recommendations(
            implementation_result, quality_assessment
        )
        
        return {
            "implementation_result": implementation_result.to_dict(),
            "quality_assessment": quality_assessment,
            "current_metrics": [m.to_dict() for m in current_metrics],
            "recommendations": recommendations,
            "overall_assessment": self._calculate_overall_assessment(quality_assessment)
        }
    
    def _assess_implementation_quality(self, implementation_result: ImplementationResult,
                                     current_metrics: List[QualityMetric]) -> Dict[str, Any]:
        """実装品質を評価"""
        
        quality_scores = {}
        
        # 実装成功度
        quality_scores["implementation_success"] = 100 if implementation_result.success else 0
        
        # 実行時間効率
        if implementation_result.execution_time > 0:
            # 5分以内は満点、それ以上は減点
            time_score = max(0, 100 - (implementation_result.execution_time - 300) / 10)
            quality_scores["execution_efficiency"] = min(100, time_score)
        
        # 変更範囲適切性
        files_modified = len(implementation_result.files_modified)
        if files_modified <= 3:
            quality_scores["change_scope"] = 100
        elif files_modified <= 5:
            quality_scores["change_scope"] = 80
        elif files_modified <= 10:
            quality_scores["change_scope"] = 60
        else:
            quality_scores["change_scope"] = 40
        
        # テスト生成
        quality_scores["test_coverage"] = 100 if implementation_result.tests_generated else 50
        
        # メトリクス改善
        metrics_score = 75  # デフォルト
        if current_metrics:
            metric_scores = [m.score_normalized() for m in current_metrics]
            metrics_score = sum(metric_scores) / len(metric_scores)
        quality_scores["metrics_improvement"] = metrics_score
        
        # 総合品質スコア
        overall_quality = sum(quality_scores.values()) / len(quality_scores)
        
        return {
            "quality_scores": quality_scores,
            "overall_quality_score": overall_quality,
            "quality_level": "excellent" if overall_quality >= 90 else "good" if overall_quality >= 75 else "acceptable" if overall_quality >= 60 else "poor"
        }
    
    def _generate_post_implementation_recommendations(self, implementation_result: ImplementationResult,
                                                   quality_assessment: Dict[str, Any]) -> List[str]:
        """実装後推奨事項を生成"""
        recommendations = []
        
        quality_scores = quality_assessment.get("quality_scores", {})
        
        # 実装成功度が低い場合
        if quality_scores.get("implementation_success", 100) < 100:
            recommendations.append("実装が失敗しました。エラーを分析し、修正してください")
        
        # 実行時間が長い場合
        if quality_scores.get("execution_efficiency", 100) < 80:
            recommendations.append("実行時間が長すぎます。実装アプローチを最適化してください")
        
        # 変更範囲が広い場合
        if quality_scores.get("change_scope", 100) < 80:
            recommendations.append("変更ファイル数が多すぎます。影響範囲を狭める方法を検討してください")
        
        # テストが生成されていない場合
        if quality_scores.get("test_coverage", 100) < 100:
            recommendations.append("テストが生成されていません。手動でテストを追加してください")
        
        # メトリクス改善が不十分な場合
        if quality_scores.get("metrics_improvement", 100) < 70:
            recommendations.append("メトリクスの改善が不十分です。追加の最適化を検討してください")
        
        # 成功した場合の推奨事項
        if implementation_result.success and quality_assessment.get("overall_quality_score", 0) >= 80:
            recommendations.append("実装が成功しました。システムを監視して効果を確認してください")
            recommendations.append("学習した内容を他の改善機会に応用できるか検討してください")
        
        return recommendations
    
    def _calculate_overall_assessment(self, quality_assessment: Dict[str, Any]) -> str:
        """総合評価を計算"""
        overall_score = quality_assessment.get("overall_quality_score", 0)
        
        if overall_score >= 90:
            return "優秀: 実装は非常に成功しており、期待を上回る結果です"
        elif overall_score >= 75:
            return "良好: 実装は成功しており、満足できる結果です"
        elif overall_score >= 60:
            return "許容範囲: 実装は完了していますが、改善の余地があります"
        else:
            return "要改善: 実装に問題があり、見直しが必要です"