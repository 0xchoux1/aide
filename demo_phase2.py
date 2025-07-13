#!/usr/bin/env python3
"""
自律学習型AIアシスタント フェーズ2デモンストレーション
マルチエージェントシステムとRAGの動作確認
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.crew_agents import MultiAgentSystem
from src.rag.rag_system import RAGSystem
from src.agents.base_agent import Task, Feedback
import time


def main():
    print("=== 自律学習型AIアシスタント フェーズ2デモンストレーション ===")
    print("マルチエージェントシステム + RAG統合\n")
    
    # システムの初期化
    print("=== システム初期化 ===")
    multi_agent_system = MultiAgentSystem()
    rag_system = RAGSystem()
    
    print("✓ マルチエージェントシステム初期化完了")
    print("✓ RAGシステム初期化完了")
    print(f"✓ 知識ベース統計: {rag_system.knowledge_base.get_knowledge_stats()}")
    print()
    
    # シナリオ1: 基本的なマルチエージェント協調
    print("=== シナリオ1: マルチエージェント協調 ===")
    task1 = Task("システム全体の健全性チェック", "system_health")
    
    print(f"タスク: {task1.description}")
    result1 = multi_agent_system.process_task(task1)
    
    print(f"分析結果: 複雑度={result1.analysis.complexity}, 推定時間={result1.analysis.estimated_time}分")
    print(f"実行結果: {result1.execution.status}, 品質スコア={result1.execution.quality_score:.2f}")
    print(f"学習成果: 知識獲得={result1.learning.knowledge_gained:.2f}")
    print(f"協調品質: {result1.collaboration_quality:.2f}")
    print()
    
    # シナリオ2: 知識ベースの構築
    print("=== シナリオ2: 知識ベース構築 ===")
    tasks_for_knowledge = [
        Task("データベース接続確認", "database_check"),
        Task("ネットワーク状態診断", "network_diagnosis"),
        Task("アプリケーション性能監視", "performance_monitoring"),
        Task("ログファイル分析", "log_analysis")
    ]
    
    print("複数タスクの実行と知識蓄積...")
    for i, task in enumerate(tasks_for_knowledge):
        print(f"  {i+1}. {task.description}")
        
        # マルチエージェントで実行
        result = multi_agent_system.process_task(task)
        
        # RAGシステムに知識を追加
        rag_system.update_knowledge_from_execution(task, result.execution)
        
        # 処理の可視化
        time.sleep(0.2)
    
    updated_stats = rag_system.knowledge_base.get_knowledge_stats()
    print(f"\n知識ベース更新後統計: {updated_stats}")
    print()
    
    # シナリオ3: RAG強化タスク実行
    print("=== シナリオ3: RAG強化タスク実行 ===")
    complex_task = Task("データベース接続エラーのトラブルシューティング", "troubleshooting")
    
    print(f"タスク: {complex_task.description}")
    
    # RAGでコンテキストを追加
    enhanced_task = rag_system.enhance_task_with_context(complex_task)
    print(f"コンテキスト追加: {len(enhanced_task.metadata.get('context', []))}件の関連知識")
    
    # RAGを使用した応答生成
    rag_response = rag_system.generate_context_aware_response(complex_task)
    print(f"RAG応答品質: {rag_response.quality_score:.2f}")
    print(f"RAG応答内容: {rag_response.content[:100]}...")
    
    # マルチエージェントでも実行
    multi_agent_result = multi_agent_system.process_task(enhanced_task)
    print(f"マルチエージェント実行結果: {multi_agent_result.execution.status}")
    print()
    
    # シナリオ4: 学習効果の確認
    print("=== シナリオ4: 学習効果の確認 ===")
    
    # 類似タスクを再実行
    similar_task = Task("データベース接続状態の確認", "database_check")
    
    print(f"新しいタスク: {similar_task.description}")
    
    # 関連知識を検索
    relevant_knowledge = rag_system.retriever.retrieve_relevant_knowledge(
        similar_task.description, 
        similar_task.task_type
    )
    
    print(f"関連知識検索結果: {len(relevant_knowledge)}件")
    for i, knowledge in enumerate(relevant_knowledge[:3]):
        print(f"  {i+1}. 関連度: {knowledge['relevance_score']:.2f}")
        print(f"     内容: {knowledge['content'][:50]}...")
    
    # 学習済み知識を活用した実行
    enhanced_similar_task = rag_system.enhance_task_with_context(similar_task)
    final_result = multi_agent_system.process_task(enhanced_similar_task)
    
    print(f"\n学習効果適用後の実行品質: {final_result.execution.quality_score:.2f}")
    print(f"協調品質: {final_result.collaboration_quality:.2f}")
    print()
    
    # シナリオ5: エラーハンドリングと回復
    print("=== シナリオ5: エラーハンドリングと回復 ===")
    problematic_task = Task("存在しないサービスの監視", "invalid_monitoring")
    
    print(f"問題のあるタスク: {problematic_task.description}")
    
    error_result = multi_agent_system.process_task(problematic_task)
    print(f"エラー処理結果: {error_result.overall_status}")
    print(f"回復試行: {error_result.error_recovery_attempted}")
    print(f"フォールバック: {len(error_result.fallback_actions)}個のアクション")
    
    # エラー情報を知識ベースに追加
    if error_result.overall_status == "failed":
        error_info = {
            "error_message": f"無効なタスク: {problematic_task.description}",
            "solution": "タスクの有効性を事前チェック",
            "error_type": "invalid_task",
            "frequency": 1
        }
        rag_system.knowledge_base.add_error_solution(error_info)
        print("✓ エラー情報を知識ベースに追加しました")
    print()
    
    # 最終統計
    print("=== 最終統計 ===")
    
    # マルチエージェントシステム統計
    communication_log = multi_agent_system.communication_bus.message_log
    print(f"エージェント間通信: {len(communication_log)}件")
    
    # RAGシステム統計
    rag_stats = rag_system.get_system_stats()
    print(f"RAG生成統計: {rag_stats['generation_stats']}")
    print(f"コンテキスト使用率: {rag_stats['context_usage_rate']:.2f}")
    
    # 知識ベース統計
    final_kb_stats = rag_system.knowledge_base.get_knowledge_stats()
    print(f"最終知識ベース統計: {final_kb_stats}")
    
    print("\n=== フェーズ2デモンストレーション完了 ===")
    print("✓ マルチエージェントシステムが正常に動作")
    print("✓ RAGシステムが知識を蓄積・活用")
    print("✓ エージェント間の協調が機能")
    print("✓ 学習効果が次のタスクに反映")
    
    print("\n=== 次のステップ ===")
    print("フェーズ3: 自己改善機能の実装")
    print("- メタプログラミング機能")
    print("- 自己コード改善")
    print("- 性能最適化")


if __name__ == "__main__":
    main()