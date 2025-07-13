"""
改善エンジンモジュール

自動改善機会特定、優先度最適化、ロードマップ生成
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import math
from pathlib import Path

from .diagnostics import DiagnosticResult, SystemDiagnostics
from ..llm.claude_code_client import ClaudeCodeClient


class ImprovementType(Enum):
    """改善タイプ"""
    PERFORMANCE = "performance"
    CODE_QUALITY = "code_quality"
    LEARNING = "learning"
    SECURITY = "security"
    USABILITY = "usability"
    MAINTENANCE = "maintenance"


class Priority(Enum):
    """優先度レベル"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ImprovementOpportunity:
    """改善機会クラス"""
    id: str
    title: str
    description: str
    improvement_type: ImprovementType
    priority: Priority = Priority.MEDIUM
    
    # 影響度評価
    impact_score: float = 0.0  # 0-100
    effort_score: float = 0.0  # 0-100 (労力、低いほど簡単)
    risk_score: float = 0.0    # 0-100 (リスク、低いほど安全)
    
    # ROI計算
    roi_score: float = 0.0
    
    # 関連データ
    related_diagnostics: List[DiagnosticResult] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # 実装計画
    estimated_time_hours: float = 0.0
    complexity_level: str = "unknown"  # simple, moderate, complex
    
    # 追跡情報
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "identified"  # identified, planned, implementing, completed, failed
    
    def calculate_roi(self) -> float:
        """ROI（投資対効果）を計算"""
        if self.effort_score == 0:
            return self.impact_score
        
        # ROI = (影響度 - リスク) / 労力
        risk_adjusted_impact = max(0, self.impact_score - self.risk_score * 0.5)
        roi = risk_adjusted_impact / self.effort_score * 100
        self.roi_score = roi
        return roi
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'improvement_type': self.improvement_type.value,
            'priority': self.priority.value,
            'impact_score': self.impact_score,
            'effort_score': self.effort_score,
            'risk_score': self.risk_score,
            'roi_score': self.roi_score,
            'estimated_time_hours': self.estimated_time_hours,
            'complexity_level': self.complexity_level,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
            'dependencies': self.dependencies
        }


@dataclass 
class ImprovementRoadmap:
    """改善ロードマップ"""
    id: str
    title: str
    opportunities: List[ImprovementOpportunity]
    phases: List[Dict[str, Any]] = field(default_factory=list)
    total_estimated_time: float = 0.0
    expected_roi: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    
    def calculate_metrics(self):
        """ロードマップメトリクスを計算"""
        self.total_estimated_time = sum(opp.estimated_time_hours for opp in self.opportunities)
        self.expected_roi = sum(opp.roi_score for opp in self.opportunities) / len(self.opportunities) if self.opportunities else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'title': self.title,
            'opportunities': [opp.to_dict() for opp in self.opportunities],
            'phases': self.phases,
            'total_estimated_time': self.total_estimated_time,
            'expected_roi': self.expected_roi,
            'created_at': self.created_at.isoformat()
        }


class OpportunityIdentifier:
    """改善機会特定システム"""
    
    def __init__(self, claude_client: Optional[ClaudeCodeClient] = None):
        self.claude_client = claude_client
        self.opportunity_templates = self._load_opportunity_templates()
    
    def identify_opportunities(self, diagnostic_results: Dict[str, List[DiagnosticResult]]) -> List[ImprovementOpportunity]:
        """診断結果から改善機会を特定"""
        opportunities = []
        
        # ルールベース改善機会特定
        rule_based_opportunities = self._identify_rule_based_opportunities(diagnostic_results)
        opportunities.extend(rule_based_opportunities)
        
        # Claude Code活用AI分析
        if self.claude_client:
            try:
                ai_opportunities = self._identify_ai_opportunities(diagnostic_results)
                opportunities.extend(ai_opportunities)
            except Exception as e:
                print(f"AI分析エラー: {e}")
        
        # 重複除去と統合
        opportunities = self._deduplicate_opportunities(opportunities)
        
        return opportunities
    
    def _identify_rule_based_opportunities(self, diagnostic_results: Dict[str, List[DiagnosticResult]]) -> List[ImprovementOpportunity]:
        """ルールベース改善機会特定"""
        opportunities = []
        opportunity_id = 1
        
        for module_name, results in diagnostic_results.items():
            for result in results:
                if result.status in ["warning", "critical"]:
                    # テンプレートベース改善機会生成
                    template_opp = self._match_opportunity_template(result)
                    if template_opp:
                        opp = ImprovementOpportunity(
                            id=f"rule_{opportunity_id:03d}",
                            title=template_opp["title"].format(metric=result.metric_name),
                            description=template_opp["description"].format(
                                metric=result.metric_name,
                                value=result.value,
                                target=result.target_value
                            ),
                            improvement_type=ImprovementType(template_opp["type"]),
                            priority=Priority.CRITICAL if result.status == "critical" else Priority.HIGH,
                            related_diagnostics=[result]
                        )
                        
                        # スコア計算
                        opp.impact_score = template_opp.get("impact_score", 50.0)
                        opp.effort_score = template_opp.get("effort_score", 30.0)
                        opp.risk_score = template_opp.get("risk_score", 20.0)
                        opp.estimated_time_hours = template_opp.get("estimated_hours", 4.0)
                        opp.complexity_level = template_opp.get("complexity", "moderate")
                        
                        # Critical状態は影響度を上げる
                        if result.status == "critical":
                            opp.impact_score *= 1.5
                            opp.effort_score *= 0.8  # より簡単にする
                        
                        opp.calculate_roi()
                        opportunities.append(opp)
                        opportunity_id += 1
        
        return opportunities
    
    def _identify_ai_opportunities(self, diagnostic_results: Dict[str, List[DiagnosticResult]]) -> List[ImprovementOpportunity]:
        """AI分析による改善機会特定"""
        opportunities = []
        
        try:
            # 診断結果をClaude Codeで分析
            analysis_prompt = self._build_analysis_prompt(diagnostic_results)
            
            response = self.claude_client.generate_structured_response(
                prompt=analysis_prompt,
                output_format={
                    "opportunities": "改善機会のリスト（JSON配列）",
                    "insights": "AIによる洞察と推奨事項",
                    "priority_rationale": "優先度付けの根拠"
                }
            )
            
            if response.success and 'structured_output' in response.metadata:
                structured_data = response.metadata['structured_output']
                ai_opportunities_data = structured_data.get('opportunities', [])
                
                # AI分析結果を改善機会オブジェクトに変換
                for i, opp_data in enumerate(ai_opportunities_data):
                    if isinstance(opp_data, dict):
                        opp = ImprovementOpportunity(
                            id=f"ai_{i+1:03d}",
                            title=opp_data.get('title', 'AI特定改善機会'),
                            description=opp_data.get('description', ''),
                            improvement_type=ImprovementType(opp_data.get('type', 'performance')),
                            priority=Priority(opp_data.get('priority', 'medium')),
                            impact_score=float(opp_data.get('impact_score', 50.0)),
                            effort_score=float(opp_data.get('effort_score', 30.0)),
                            risk_score=float(opp_data.get('risk_score', 20.0)),
                            estimated_time_hours=float(opp_data.get('estimated_hours', 4.0)),
                            complexity_level=opp_data.get('complexity', 'moderate')
                        )
                        opp.calculate_roi()
                        opportunities.append(opp)
                        
        except Exception as e:
            print(f"AI改善機会特定エラー: {e}")
        
        return opportunities
    
    def _build_analysis_prompt(self, diagnostic_results: Dict[str, List[DiagnosticResult]]) -> str:
        """AI分析用プロンプト構築"""
        diagnostics_summary = []
        
        for module_name, results in diagnostic_results.items():
            for result in results:
                diagnostics_summary.append({
                    'module': module_name,
                    'metric': result.metric_name,
                    'value': result.value,
                    'target': result.target_value,
                    'status': result.status,
                    'recommendations': result.recommendations
                })
        
        prompt = f"""
AIDE自律学習型AIアシスタントのシステム診断結果を分析し、改善機会を特定してください。

診断結果:
{json.dumps(diagnostics_summary, ensure_ascii=False, indent=2)}

以下の観点で改善機会を特定し、JSON形式で出力してください：

1. パフォーマンス改善
2. コード品質向上  
3. 学習効果向上
4. セキュリティ強化
5. 保守性向上

各改善機会には以下を含めてください：
- title: 改善タイトル
- description: 詳細説明
- type: performance/code_quality/learning/security/maintenance
- priority: critical/high/medium/low
- impact_score: 影響度（0-100）
- effort_score: 労力（0-100、低いほど簡単）
- risk_score: リスク（0-100、低いほど安全）
- estimated_hours: 推定作業時間
- complexity: simple/moderate/complex

特にClaude Code統合、RAGシステム最適化、自動化可能な改善に焦点を当ててください。
"""
        
        return prompt
    
    def _match_opportunity_template(self, diagnostic_result: DiagnosticResult) -> Optional[Dict[str, Any]]:
        """診断結果をテンプレートにマッチング"""
        metric_name = diagnostic_result.metric_name.lower()
        
        for template in self.opportunity_templates:
            if any(keyword in metric_name for keyword in template.get("keywords", [])):
                return template
        
        # デフォルトテンプレート
        return {
            "title": "{metric}の改善",
            "description": "{metric}が目標値{target}に対して{value}となっています。最適化が必要です。",
            "type": "performance",
            "impact_score": 40.0,
            "effort_score": 30.0,
            "risk_score": 15.0,
            "estimated_hours": 3.0,
            "complexity": "moderate"
        }
    
    def _load_opportunity_templates(self) -> List[Dict[str, Any]]:
        """改善機会テンプレートを読み込み"""
        return [
            {
                "keywords": ["memory", "cpu", "disk"],
                "title": "システムリソース{metric}の最適化",
                "description": "システムリソース使用率が高くなっています（{value}）。目標値{target}を達成するため最適化が必要です。",
                "type": "performance",
                "impact_score": 70.0,
                "effort_score": 40.0,
                "risk_score": 25.0,
                "estimated_hours": 6.0,
                "complexity": "moderate"
            },
            {
                "keywords": ["response_time", "execution_time"],
                "title": "応答時間{metric}の改善",
                "description": "応答時間が目標を上回っています（{value}秒）。パフォーマンス最適化が必要です。",
                "type": "performance", 
                "impact_score": 80.0,
                "effort_score": 50.0,
                "risk_score": 20.0,
                "estimated_hours": 8.0,
                "complexity": "moderate"
            },
            {
                "keywords": ["error_rate", "failure"],
                "title": "エラー率{metric}の削減",
                "description": "エラー率が許容範囲を超えています（{value}%）。エラーハンドリングの改善が必要です。",
                "type": "code_quality",
                "impact_score": 85.0,
                "effort_score": 35.0, 
                "risk_score": 15.0,
                "estimated_hours": 5.0,
                "complexity": "moderate"
            },
            {
                "keywords": ["test", "coverage"],
                "title": "テスト{metric}の強化",
                "description": "テストカバレッジが不足しています（{value}%）。品質保証の強化が必要です。",
                "type": "code_quality",
                "impact_score": 75.0,
                "effort_score": 45.0,
                "risk_score": 10.0,
                "estimated_hours": 10.0,
                "complexity": "moderate"
            },
            {
                "keywords": ["learning", "knowledge"],
                "title": "学習効果{metric}の向上",
                "description": "学習システムの効果が期待値を下回っています（{value}）。学習アルゴリズムの改善が必要です。",
                "type": "learning",
                "impact_score": 90.0,
                "effort_score": 60.0,
                "risk_score": 30.0,
                "estimated_hours": 12.0,
                "complexity": "complex"
            },
            {
                "keywords": ["llm", "claude"],
                "title": "LLM統合{metric}の最適化",
                "description": "LLMバックエンドの統合に問題があります。Claude Code統合の最適化が必要です。",
                "type": "performance",
                "impact_score": 85.0,
                "effort_score": 40.0,
                "risk_score": 25.0,
                "estimated_hours": 6.0,
                "complexity": "moderate"
            }
        ]
    
    def _deduplicate_opportunities(self, opportunities: List[ImprovementOpportunity]) -> List[ImprovementOpportunity]:
        """重複する改善機会を除去・統合"""
        # 簡単な重複除去（タイトルベース）
        seen_titles = set()
        deduplicated = []
        
        # ROIでソートして高い順に処理
        sorted_opportunities = sorted(opportunities, key=lambda x: x.roi_score, reverse=True)
        
        for opp in sorted_opportunities:
            title_key = opp.title.lower().strip()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                deduplicated.append(opp)
        
        return deduplicated


class PriorityOptimizer:
    """優先度最適化システム"""
    
    def __init__(self):
        self.weight_config = {
            'impact': 0.4,      # 影響度の重み
            'effort': 0.3,      # 労力の重み（逆）
            'risk': 0.2,        # リスクの重み（逆）
            'urgency': 0.1      # 緊急度の重み
        }
    
    def optimize_priorities(self, opportunities: List[ImprovementOpportunity]) -> List[ImprovementOpportunity]:
        """改善機会の優先度を最適化"""
        
        # 各機会の総合スコアを計算
        for opp in opportunities:
            opp.priority = self._calculate_optimized_priority(opp)
        
        # 優先度とROIでソート
        priority_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        
        sorted_opportunities = sorted(
            opportunities,
            key=lambda x: (priority_order.get(x.priority.value, 1), x.roi_score),
            reverse=True
        )
        
        return sorted_opportunities
    
    def _calculate_optimized_priority(self, opportunity: ImprovementOpportunity) -> Priority:
        """最適化された優先度を計算"""
        
        # 緊急度計算（criticalな診断結果の数に基づく）
        urgency_score = sum(
            1 for diag in opportunity.related_diagnostics 
            if diag.status == "critical"
        ) * 20.0
        
        # 正規化（0-100範囲）
        impact = min(100, opportunity.impact_score)
        effort_penalty = min(100, opportunity.effort_score)
        risk_penalty = min(100, opportunity.risk_score)
        urgency = min(100, urgency_score)
        
        # 総合スコア計算
        total_score = (
            impact * self.weight_config['impact'] +
            (100 - effort_penalty) * self.weight_config['effort'] +
            (100 - risk_penalty) * self.weight_config['risk'] +
            urgency * self.weight_config['urgency']
        )
        
        # 優先度レベル決定
        if total_score >= 80:
            return Priority.CRITICAL
        elif total_score >= 65:
            return Priority.HIGH
        elif total_score >= 40:
            return Priority.MEDIUM
        else:
            return Priority.LOW
    
    def analyze_priority_distribution(self, opportunities: List[ImprovementOpportunity]) -> Dict[str, Any]:
        """優先度分布を分析"""
        priority_counts = {p.value: 0 for p in Priority}
        total_effort = 0
        total_impact = 0
        
        for opp in opportunities:
            priority_counts[opp.priority.value] += 1
            total_effort += opp.effort_score
            total_impact += opp.impact_score
        
        return {
            'distribution': priority_counts,
            'total_opportunities': len(opportunities),
            'average_effort': total_effort / len(opportunities) if opportunities else 0,
            'average_impact': total_impact / len(opportunities) if opportunities else 0,
            'high_priority_count': priority_counts['critical'] + priority_counts['high']
        }


class RoadmapGenerator:
    """改善ロードマップ生成システム"""
    
    def __init__(self, claude_client: Optional[ClaudeCodeClient] = None):
        self.claude_client = claude_client
    
    def generate_roadmap(self, opportunities: List[ImprovementOpportunity], 
                        timeframe_weeks: int = 12) -> ImprovementRoadmap:
        """改善ロードマップを生成"""
        
        # 依存関係を解決してソート
        sorted_opportunities = self._resolve_dependencies(opportunities)
        
        # フェーズに分割
        phases = self._create_phases(sorted_opportunities, timeframe_weeks)
        
        # ロードマップ作成
        roadmap = ImprovementRoadmap(
            id=f"roadmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=f"AIDE自律改善ロードマップ ({timeframe_weeks}週間)",
            opportunities=sorted_opportunities,
            phases=phases
        )
        
        roadmap.calculate_metrics()
        
        # Claude Code活用で説明を生成
        if self.claude_client:
            try:
                roadmap = self._enhance_roadmap_with_ai(roadmap)
            except Exception as e:
                print(f"AI拡張エラー: {e}")
        
        return roadmap
    
    def _resolve_dependencies(self, opportunities: List[ImprovementOpportunity]) -> List[ImprovementOpportunity]:
        """依存関係を解決してソート"""
        # 簡単な実装：依存関係がない機会から順に並べる
        independent = [opp for opp in opportunities if not opp.dependencies]
        dependent = [opp for opp in opportunities if opp.dependencies]
        
        # 独立した機会を優先度順にソート
        independent.sort(key=lambda x: (
            {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(x.priority.value, 1),
            x.roi_score
        ), reverse=True)
        
        # 依存関係のある機会は後に配置
        dependent.sort(key=lambda x: x.roi_score, reverse=True)
        
        return independent + dependent
    
    def _create_phases(self, opportunities: List[ImprovementOpportunity], 
                      timeframe_weeks: int) -> List[Dict[str, Any]]:
        """フェーズを作成"""
        phases = []
        hours_per_week = 20  # 週当たり作業時間
        total_capacity = timeframe_weeks * hours_per_week
        
        current_phase = 1
        current_phase_hours = 0
        current_phase_opportunities = []
        phase_capacity = total_capacity / 3  # 3フェーズに分割
        
        for opp in opportunities:
            if current_phase_hours + opp.estimated_time_hours <= phase_capacity:
                current_phase_opportunities.append(opp)
                current_phase_hours += opp.estimated_time_hours
            else:
                # 現在のフェーズを完了
                if current_phase_opportunities:
                    phases.append({
                        'phase': current_phase,
                        'title': f"フェーズ {current_phase}",
                        'opportunities': [opp.id for opp in current_phase_opportunities],
                        'estimated_hours': current_phase_hours,
                        'estimated_weeks': math.ceil(current_phase_hours / hours_per_week),
                        'focus_areas': list(set(opp.improvement_type.value for opp in current_phase_opportunities))
                    })
                
                # 新しいフェーズを開始
                current_phase += 1
                current_phase_opportunities = [opp]
                current_phase_hours = opp.estimated_time_hours
        
        # 最後のフェーズを追加
        if current_phase_opportunities:
            phases.append({
                'phase': current_phase,
                'title': f"フェーズ {current_phase}",
                'opportunities': [opp.id for opp in current_phase_opportunities],
                'estimated_hours': current_phase_hours,
                'estimated_weeks': math.ceil(current_phase_hours / hours_per_week),
                'focus_areas': list(set(opp.improvement_type.value for opp in current_phase_opportunities))
            })
        
        return phases
    
    def _enhance_roadmap_with_ai(self, roadmap: ImprovementRoadmap) -> ImprovementRoadmap:
        """AI分析でロードマップを拡張"""
        
        roadmap_summary = {
            'total_opportunities': len(roadmap.opportunities),
            'phases': roadmap.phases,
            'total_time': roadmap.total_estimated_time,
            'expected_roi': roadmap.expected_roi
        }
        
        enhancement_prompt = f"""
AIDE自律改善ロードマップの詳細分析と説明を生成してください。

ロードマップ概要:
{json.dumps(roadmap_summary, ensure_ascii=False, indent=2)}

以下を含む詳細分析を提供してください：
1. 戦略的な実装アプローチ
2. フェーズ間の依存関係
3. リスク評価と軽減策
4. 期待される成果
5. 成功指標

実用的で実行可能な推奨事項を含めてください。
"""
        
        try:
            response = self.claude_client.generate_response(enhancement_prompt)
            if response.success:
                # ロードマップに分析結果を追加
                roadmap.phases.append({
                    'phase': 'analysis',
                    'title': 'AI戦略分析',
                    'content': response.content,
                    'generated_at': datetime.now().isoformat()
                })
        except Exception as e:
            print(f"ロードマップ拡張エラー: {e}")
        
        return roadmap


class ImprovementEngine:
    """統合改善エンジン"""
    
    def __init__(self, diagnostics: SystemDiagnostics, 
                 claude_client: Optional[ClaudeCodeClient] = None):
        self.diagnostics = diagnostics
        self.claude_client = claude_client
        
        self.opportunity_identifier = OpportunityIdentifier(claude_client)
        self.priority_optimizer = PriorityOptimizer()
        self.roadmap_generator = RoadmapGenerator(claude_client)
        
        self.improvement_history: List[ImprovementRoadmap] = []
    
    def generate_improvement_plan(self, timeframe_weeks: int = 12) -> ImprovementRoadmap:
        """完全な改善計画を生成"""
        
        # 1. システム診断実行
        diagnostic_results = self.diagnostics.run_full_diagnosis()
        
        # 2. 改善機会特定
        opportunities = self.opportunity_identifier.identify_opportunities(diagnostic_results)
        
        # 3. 優先度最適化
        optimized_opportunities = self.priority_optimizer.optimize_priorities(opportunities)
        
        # 4. ロードマップ生成
        roadmap = self.roadmap_generator.generate_roadmap(optimized_opportunities, timeframe_weeks)
        
        # 5. 履歴に保存
        self.improvement_history.append(roadmap)
        
        return roadmap
    
    def get_improvement_summary(self) -> Dict[str, Any]:
        """改善概要を取得"""
        if not self.improvement_history:
            return {"status": "no_plans_generated"}
        
        latest_roadmap = self.improvement_history[-1]
        
        return {
            "latest_roadmap_id": latest_roadmap.id,
            "total_opportunities": len(latest_roadmap.opportunities),
            "total_estimated_time": latest_roadmap.total_estimated_time,
            "expected_roi": latest_roadmap.expected_roi,
            "phases_count": len(latest_roadmap.phases),
            "priority_distribution": self.priority_optimizer.analyze_priority_distribution(latest_roadmap.opportunities),
            "creation_date": latest_roadmap.created_at.isoformat()
        }
    
    def export_roadmap(self, roadmap: ImprovementRoadmap, output_file: str = None) -> str:
        """ロードマップをファイルに出力"""
        if output_file is None:
            output_file = f"/tmp/aide_improvement_roadmap_{roadmap.id}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(roadmap.to_dict(), f, ensure_ascii=False, indent=2, default=str)
        
        return output_file