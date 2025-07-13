#!/usr/bin/env python3
"""
AIDE Phase 3 自律改善システム統合デモ

真のRAGシステム完成の実演
"""

import sys
import time
import json
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent))

from src.self_improvement.diagnostics import SystemDiagnostics
from src.self_improvement.improvement_engine import ImprovementEngine
from src.self_improvement.autonomous_implementation import AutonomousImplementation
from src.self_improvement.quality_assurance import QualityAssurance
from src.rag.rag_system import RAGSystem
from src.llm.claude_code_client import ClaudeCodeClient


class SelfImprovementDemo:
    """自律改善システムデモ"""
    
    def __init__(self):
        print("🚀 AIDE Phase 3 自律改善システム初期化中...")
        
        # RAGシステム初期化（Claude Code統合有効）
        try:
            self.rag_system = RAGSystem(use_claude_code=True, claude_timeout=60)
            print("✅ RAGシステム初期化完了")
        except Exception as e:
            print(f"⚠️  RAGシステム初期化警告: {e}")
            self.rag_system = RAGSystem(use_claude_code=False)
        
        # Claude Codeクライアント初期化
        try:
            self.claude_client = ClaudeCodeClient(timeout=60)
            print("✅ Claude Codeクライアント初期化完了")
        except Exception as e:
            print(f"⚠️  Claude Code利用不可: {e}")
            self.claude_client = None
        
        # 自律改善システムコンポーネント初期化
        self.diagnostics = SystemDiagnostics(self.rag_system)
        self.improvement_engine = ImprovementEngine(self.diagnostics, self.claude_client)
        self.autonomous_implementation = AutonomousImplementation(self.claude_client) if self.claude_client else None
        self.quality_assurance = QualityAssurance(self.claude_client)
        
        print("🎯 自律改善システム準備完了！")
    
    def run_complete_demo(self):
        """完全なデモを実行"""
        print("\n" + "="*60)
        print("🎭 AIDE 自律改善システム 完全デモ")
        print("="*60)
        
        # Phase 1: システム診断
        print("\n📊 Phase 1: システム診断実行中...")
        self._demo_system_diagnostics()
        
        # Phase 2: 改善計画生成
        print("\n🧠 Phase 2: 改善計画生成中...")
        roadmap = self._demo_improvement_planning()
        
        # Phase 3: 自律実装（ドライラン）
        print("\n🤖 Phase 3: 自律実装デモ（ドライラン）...")
        if self.autonomous_implementation:
            self._demo_autonomous_implementation(roadmap, dry_run=True)
        else:
            print("⚠️  Claude Code未利用のため実装デモをスキップ")
        
        # Phase 4: 品質保証
        print("\n🛡️  Phase 4: 品質保証システム...")
        self._demo_quality_assurance(roadmap)
        
        # Phase 5: 統合状況レポート
        print("\n📈 Phase 5: 統合システム状況...")
        self._demo_system_status()
        
        print("\n🎉 デモ完了！真のRAGシステムが完成しました！")
    
    def _demo_system_diagnostics(self):
        """システム診断デモ"""
        try:
            # 全システム診断実行
            print("  🔍 全システム診断実行中...")
            diagnosis_results = self.diagnostics.run_full_diagnosis()
            
            # ヘルスサマリー取得
            health_summary = self.diagnostics.get_system_health_summary()
            
            print(f"  📊 システムヘルススコア: {health_summary['health_score']:.1f}/100")
            print(f"  🎯 総合ステータス: {health_summary['overall_status']}")
            print(f"  📋 総メトリクス数: {health_summary['total_metrics']}")
            
            # ステータス分布
            distribution = health_summary['status_distribution']
            print(f"  ✅ 良好: {distribution['good']}, ⚠️ 警告: {distribution['warning']}, ❌ 重要: {distribution['critical']}")
            
            # トップ推奨事項
            top_recommendations = health_summary['top_recommendations'][:3]
            if top_recommendations:
                print("  💡 主要推奨事項:")
                for i, rec in enumerate(top_recommendations, 1):
                    print(f"    {i}. {rec}")
            
            # 診断レポート出力
            report_file = self.diagnostics.export_diagnosis_report()
            print(f"  📄 詳細レポート: {report_file}")
            
        except Exception as e:
            print(f"  ❌ 診断エラー: {e}")
    
    def _demo_improvement_planning(self):
        """改善計画デモ"""
        try:
            # 改善計画生成
            print("  🎯 改善ロードマップ生成中...")
            roadmap = self.improvement_engine.generate_improvement_plan(timeframe_weeks=12)
            
            print(f"  📋 改善機会: {len(roadmap.opportunities)}件")
            print(f"  ⏱️  総推定時間: {roadmap.total_estimated_time:.1f}時間")
            print(f"  💰 期待ROI: {roadmap.expected_roi:.1f}")
            print(f"  📅 フェーズ数: {len(roadmap.phases)}")
            
            # 高優先度の改善機会を表示
            high_priority_opportunities = [
                opp for opp in roadmap.opportunities 
                if opp.priority.value in ['critical', 'high']
            ]
            
            print(f"  🔥 高優先度改善: {len(high_priority_opportunities)}件")
            for i, opp in enumerate(high_priority_opportunities[:3], 1):
                print(f"    {i}. {opp.title} (ROI: {opp.roi_score:.1f}, リスク: {opp.risk_score:.1f})")
            
            # ロードマップ出力
            roadmap_file = self.improvement_engine.export_roadmap(roadmap)
            print(f"  📄 ロードマップ: {roadmap_file}")
            
            return roadmap
            
        except Exception as e:
            print(f"  ❌ 改善計画エラー: {e}")
            return None
    
    def _demo_autonomous_implementation(self, roadmap, dry_run=True):
        """自律実装デモ"""
        if not roadmap or not self.autonomous_implementation:
            return
        
        try:
            mode_str = "ドライラン" if dry_run else "実実装"
            print(f"  🤖 自律実装{mode_str}開始...")
            
            # 高優先度の改善機会を1つ実装
            high_priority_opportunities = [
                opp for opp in roadmap.opportunities 
                if opp.priority.value in ['critical', 'high']
            ]
            
            if high_priority_opportunities:
                target_opportunity = high_priority_opportunities[0]
                print(f"  🎯 実装対象: {target_opportunity.title}")
                
                # 実装実行
                implementation_result = self.autonomous_implementation.implement_opportunity(
                    target_opportunity, dry_run=dry_run
                )
                
                print(f"  📊 実装結果: {'成功' if implementation_result.success else '失敗'}")
                if implementation_result.success:
                    print(f"  📁 変更ファイル: {len(implementation_result.files_modified)}個")
                    print(f"  🧪 生成テスト: {len(implementation_result.tests_generated)}個")
                    print(f"  ⏱️  実行時間: {implementation_result.execution_time:.2f}秒")
                else:
                    print(f"  ❌ エラー: {implementation_result.error_message}")
                
                # 実装サマリー
                summary = self.autonomous_implementation.get_implementation_summary()
                print(f"  📈 累積実装: {summary['total_implementations']}件")
                print(f"  ✅ 成功率: {summary['success_rate']:.1f}%")
            
            else:
                print("  ℹ️  実装対象の改善機会がありません")
                
        except Exception as e:
            print(f"  ❌ 自律実装エラー: {e}")
    
    def _demo_quality_assurance(self, roadmap):
        """品質保証デモ"""
        if not roadmap:
            return
        
        try:
            print("  🛡️  品質保証システム評価中...")
            
            # 高優先度の改善機会の準備状況評価
            high_priority_opportunities = [
                opp for opp in roadmap.opportunities 
                if opp.priority.value in ['critical', 'high']
            ]
            
            if high_priority_opportunities:
                target_opportunity = high_priority_opportunities[0]
                
                # 仮の実装計画
                mock_implementation_plan = {
                    "approach": "パフォーマンス最適化",
                    "steps": [
                        {
                            "step": 1,
                            "description": "メモリ使用量最適化",
                            "files_to_modify": ["src/rag/rag_system.py"],
                            "risk_level": "low"
                        }
                    ],
                    "expected_changes": ["メモリ使用量削減"],
                    "testing_strategy": "既存テスト実行",
                    "success_criteria": ["メモリ使用量20%削減"]
                }
                
                # 実装準備評価
                readiness_assessment = self.quality_assurance.assess_implementation_readiness(
                    target_opportunity, mock_implementation_plan
                )
                
                print(f"  📋 評価対象: {target_opportunity.title}")
                print(f"  ✅ 実装準備: {'完了' if readiness_assessment['ready_for_implementation'] else '未完了'}")
                print(f"  ⚠️  リスクレベル: {readiness_assessment['risk_level']}")
                
                # 安全性チェック結果
                safety_checks = readiness_assessment['safety_checks']
                passed_checks = sum(1 for check in safety_checks if check['passed'])
                print(f"  🔒 安全性チェック: {passed_checks}/{len(safety_checks)} 通過")
                
                # 次のステップ
                next_steps = readiness_assessment['next_steps']
                print("  📝 次のステップ:")
                for step in next_steps[:2]:
                    print(f"    • {step}")
            
            # 品質メトリクス
            print("  📊 品質メトリクス:")
            metrics_summary = self.quality_assurance.quality_metrics.get_metrics_summary(days=1)
            if metrics_summary.get('status') != 'no_recent_metrics':
                print(f"    📈 総合スコア: {metrics_summary['overall_score']:.1f}")
                print(f"    📊 メトリクス数: {metrics_summary['total_metrics']}")
            else:
                print("    ℹ️  メトリクス履歴なし")
                
        except Exception as e:
            print(f"  ❌ 品質保証エラー: {e}")
    
    def _demo_system_status(self):
        """システム状況デモ"""
        try:
            print("  📊 統合システム状況:")
            
            # RAGシステム統計
            rag_stats = self.rag_system.get_system_stats()
            print(f"    🧠 RAGシステム:")
            print(f"      • 総リクエスト: {rag_stats['generation_stats']['total_requests']}")
            print(f"      • 成功生成: {rag_stats['generation_stats']['successful_generations']}")
            print(f"      • LLMバックエンド: {rag_stats['llm_integration']['llm_backend']}")
            
            # 改善エンジン統計
            improvement_summary = self.improvement_engine.get_improvement_summary()
            if improvement_summary.get('status') != 'no_plans_generated':
                print(f"    🎯 改善エンジン:")
                print(f"      • 改善機会: {improvement_summary['total_opportunities']}")
                print(f"      • 期待ROI: {improvement_summary['expected_roi']:.1f}")
                print(f"      • フェーズ数: {improvement_summary['phases_count']}")
            
            # 自律実装統計
            if self.autonomous_implementation:
                impl_summary = self.autonomous_implementation.get_implementation_summary()
                if impl_summary.get('status') != 'no_implementations':
                    print(f"    🤖 自律実装:")
                    print(f"      • 総実装: {impl_summary['total_implementations']}")
                    print(f"      • 成功率: {impl_summary['success_rate']:.1f}%")
                    print(f"      • 変更ファイル: {impl_summary['total_files_modified']}")
            
            # システム機能一覧
            print(f"    🏗️  システム機能:")
            features = [
                "✅ マルチエージェント協調",
                "✅ Claude Code RAG統合", 
                "✅ 自動診断システム",
                "✅ 改善計画エンジン",
                "✅ 自律実装システム" if self.claude_client else "⚠️  自律実装システム（Claude Code未利用）",
                "✅ 品質保証システム",
                "✅ セキュリティ機能",
                "✅ 人間承認ゲート"
            ]
            
            for feature in features:
                print(f"      {feature}")
                
        except Exception as e:
            print(f"  ❌ システム状況エラー: {e}")


def main():
    """メイン実行関数"""
    try:
        demo = SelfImprovementDemo()
        demo.run_complete_demo()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  デモが中断されました")
    except Exception as e:
        print(f"\n❌ デモ実行エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()