#!/usr/bin/env python3
"""
自律学習型AIアシスタント デモンストレーション
フェーズ1: 基礎システムの動作確認
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.base_agent import BaseAgent, Task, Feedback
import time


def main():
    print("=== 自律学習型AIアシスタント デモンストレーション ===")
    print("フェーズ1: 基礎システムの動作確認\n")
    
    # エージェントの初期化
    agent = BaseAgent("InfrastructureAgent")
    print(f"エージェント '{agent.name}' を初期化しました")
    
    # 初期状態の確認
    print(f"初期パフォーマンススコア: {agent.performance_score:.2f}")
    print(f"タスク完了数: {agent.performance_metrics['tasks_completed']}")
    print(f"学習回数: {agent.performance_metrics['learning_iterations']}\n")
    
    # シナリオ1: 基本的なタスク実行
    print("=== シナリオ1: 基本的なタスク実行 ===")
    task1 = Task(
        description="サーバーの状態を確認",
        task_type="system_check"
    )
    
    response1 = agent.execute_task(task1)
    print(f"タスク: {task1.description}")
    print(f"実行結果: {response1.content}")
    print(f"品質スコア: {response1.quality_score:.2f}\n")
    
    # シナリオ2: フィードバックによる学習
    print("=== シナリオ2: フィードバックによる学習 ===")
    feedback1 = Feedback(
        task=task1,
        response=response1,
        rating=3,
        improvement_suggestion="もっと詳細な情報が必要"
    )
    
    print(f"フィードバック提供: 評価={feedback1.rating}, 改善提案='{feedback1.improvement_suggestion}'")
    agent.learn(feedback1)
    print("学習処理を実行しました\n")
    
    # シナリオ3: 学習効果の確認
    print("=== シナリオ3: 学習効果の確認 ===")
    task2 = Task(
        description="サーバーの状態を確認",
        task_type="system_check"
    )
    
    response2 = agent.execute_task(task2)
    print(f"タスク: {task2.description}")
    print(f"実行結果: {response2.content}")
    print(f"品質スコア: {response2.quality_score:.2f}")
    print(f"品質改善: {response2.quality_score - response1.quality_score:.2f}\n")
    
    # シナリオ4: 複数タスクでの学習パターン構築
    print("=== シナリオ4: 複数タスクでの学習パターン構築 ===")
    for i in range(3):
        task = Task(
            description=f"サーバー{i+1}の状態確認",
            task_type="system_check"
        )
        
        response = agent.execute_task(task)
        
        # 高評価のフィードバックを提供
        feedback = Feedback(
            task=task,
            response=response,
            rating=4,
            improvement_suggestion="詳細なメトリクスを含める"
        )
        
        agent.learn(feedback)
        print(f"タスク{i+1}: 品質スコア={response.quality_score:.2f}")
        time.sleep(0.1)  # 処理の可視化
    
    print()
    
    # シナリオ5: 学習パターンの適用確認
    print("=== シナリオ5: 学習パターンの適用確認 ===")
    final_task = Task(
        description="新サーバーの状態確認",
        task_type="system_check"
    )
    
    final_response = agent.execute_task(final_task)
    print(f"タスク: {final_task.description}")
    print(f"実行結果: {final_response.content}")
    print(f"品質スコア: {final_response.quality_score:.2f}\n")
    
    # 最終統計の表示
    print("=== 最終統計 ===")
    print(f"最終パフォーマンススコア: {agent.performance_score:.2f}")
    print(f"タスク完了数: {agent.performance_metrics['tasks_completed']}")
    print(f"学習回数: {agent.performance_metrics['learning_iterations']}")
    print(f"平均品質スコア: {agent.performance_metrics['average_quality']:.2f}")
    
    # メモリ統計
    memory_stats = agent.memory.get_statistics()
    print(f"\nメモリ統計:")
    print(f"- 保存されたタスク数: {memory_stats['total_tasks']}")
    print(f"- 学習項目数: {memory_stats['total_learnings']}")
    print(f"- タスクタイプ別内訳: {memory_stats['task_types']}")
    
    # 学習システム統計
    learning_stats = agent.learning_system.get_learning_statistics()
    print(f"\n学習システム統計:")
    print(f"- 総フィードバック数: {learning_stats['total_feedback']}")
    print(f"- パターン数: {learning_stats['patterns_by_type']}")
    print(f"- 平均評価: {learning_stats['average_ratings']}")
    
    print("\n=== デモンストレーション完了 ===")
    print("フェーズ1の基礎システムが正常に動作しています！")
    
    # 次のステップの案内
    print("\n=== 次のステップ ===")
    print("フェーズ2: CrewAIとRAGの統合")
    print("- マルチエージェントシステムの実装")
    print("- ベクターデータベースとの連携")
    print("- 知識ベースの構築")


if __name__ == "__main__":
    main()