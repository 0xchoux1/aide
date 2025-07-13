#!/usr/bin/env python3
"""
RAGシステムのデモンストレーション
Docker環境で動作するRAGシステムの実用例
"""

import sys
import os
import time
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

from src.rag.rag_system import RAGSystem
from src.rag.knowledge_base import KnowledgeBase
from src.rag.retriever import Retriever
from src.agents.base_agent import Task, Response


def main():
    print("🚀 RAGシステム デモンストレーション")
    print("=" * 50)
    
    # 1. システム初期化
    print("\n1. システム初期化中...")
    try:
        rag = RAGSystem()
        print("✅ RAGシステムが正常に初期化されました")
    except Exception as e:
        print(f"❌ システム初期化エラー: {e}")
        return 1
    
    # 2. 知識ベースの構築
    print("\n2. 知識ベースの構築中...")
    knowledge_items = [
        {
            "problem": "データベース接続エラー",
            "solutions": ["接続文字列確認", "権限確認", "ネットワーク確認", "ファイアウォール設定"],
            "category": "database"
        },
        {
            "problem": "API応答遅延",
            "solutions": ["キャッシュ実装", "クエリ最適化", "インデックス追加", "負荷分散"],
            "category": "performance"
        },
        {
            "problem": "メモリ不足エラー",
            "solutions": ["メモリ使用量監視", "プロセス最適化", "ガベージコレクション", "メモリ増設"],
            "category": "system"
        },
        {
            "problem": "SSL証明書エラー",
            "solutions": ["証明書更新", "証明書パス確認", "中間証明書設定", "証明書権限確認"],
            "category": "security"
        },
        {
            "problem": "Docker コンテナ起動失敗",
            "solutions": ["イメージ確認", "ポート競合確認", "ボリュームマウント確認", "リソース確認"],
            "category": "docker"
        }
    ]
    
    for i, knowledge in enumerate(knowledge_items, 1):
        success = rag.knowledge_base.add_troubleshooting_knowledge(knowledge)
        if success:
            print(f"✅ 知識 {i}: {knowledge['problem']}")
        else:
            print(f"❌ 知識 {i}: 追加失敗")
    
    # 3. ベストプラクティスの追加
    print("\n3. ベストプラクティスの追加中...")
    best_practices = [
        {
            "title": "効率的なデータベース設計",
            "description": "正規化とインデックス設計による性能最適化",
            "domain": "database",
            "importance": "high"
        },
        {
            "title": "セキュアなAPI設計",
            "description": "認証・認可・暗号化による安全なAPI構築",
            "domain": "security",
            "importance": "high"
        },
        {
            "title": "コンテナ最適化",
            "description": "軽量イメージとマルチステージビルドによる最適化",
            "domain": "docker",
            "importance": "medium"
        }
    ]
    
    for i, practice in enumerate(best_practices, 1):
        success = rag.knowledge_base.add_best_practice(practice)
        if success:
            print(f"✅ ベストプラクティス {i}: {practice['title']}")
        else:
            print(f"❌ ベストプラクティス {i}: 追加失敗")
    
    # 4. システム統計の表示
    print("\n4. システム統計:")
    stats = rag.get_system_stats()
    print(f"   📊 知識ベース文書数: {stats['knowledge_base_stats']['total_documents']}")
    print(f"   🔧 コンテキストウィンドウサイズ: {stats['context_window_size']}")
    print(f"   📈 生成要求数: {stats['generation_stats']['total_requests']}")
    
    # 5. 実用的なRAG動作デモ
    print("\n5. RAG動作デモ:")
    print("-" * 30)
    
    test_queries = [
        "データベースに接続できません",
        "APIの応答が遅すぎます",
        "サーバーのメモリが不足しています",
        "SSL証明書のエラーが発生しています",
        "Dockerコンテナが立ち上がりません"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 クエリ {i}: {query}")
        
        # タスクを作成
        task = Task(query, "troubleshooting")
        
        # RAGシステムで応答を生成
        start_time = time.time()
        response = rag.generate_context_aware_response(task)
        end_time = time.time()
        
        # 結果を表示
        print(f"   ⏱️  応答時間: {end_time - start_time:.2f}秒")
        print(f"   📊 品質スコア: {response.quality_score:.2f}")
        print(f"   🔍 取得コンテキスト数: {len(response.metadata['retrieved_contexts'])}")
        print(f"   💬 応答: {response.content[:100]}...")
        
        # 取得されたコンテキストの詳細表示
        if response.metadata['retrieved_contexts']:
            print(f"   📋 関連情報:")
            for j, ctx in enumerate(response.metadata['retrieved_contexts'][:2], 1):
                print(f"      {j}. {ctx['content'][:80]}...")
    
    # 6. 高度なコンテキスト拡張デモ
    print("\n6. 高度なコンテキスト拡張デモ:")
    print("-" * 30)
    
    complex_task = Task("新しいマイクロサービスを Docker で構築する際の セキュリティ対策", "architecture")
    enhanced_task = rag.enhance_task_with_context(complex_task)
    
    print(f"   📝 元のタスク: {complex_task.description}")
    print(f"   🔍 拡張されたコンテキスト数: {len(enhanced_task.metadata.get('context', []))}")
    print(f"   🏗️  実行パターン数: {len(enhanced_task.metadata.get('execution_patterns', []))}")
    print(f"   ⭐ ベストプラクティス数: {len(enhanced_task.metadata.get('best_practices', []))}")
    
    # 7. 学習機能のデモ
    print("\n7. 学習機能デモ:")
    print("-" * 30)
    
    # 成功事例を学習
    success_task = Task("データベース接続問題の解決", "troubleshooting")
    success_response = Response("接続文字列を修正し、権限を確認して問題を解決しました", 0.95, success_task.id)
    
    learn_success = rag.update_knowledge_from_execution(success_task, success_response)
    print(f"   ✅ 成功事例の学習: {learn_success}")
    
    # 失敗事例を学習
    failure_task = Task("複雑なシステム分析", "analysis")
    failure_response = Response("分析に失敗しました", 0.2, failure_task.id)
    
    learn_failure = rag.update_knowledge_from_execution(failure_task, failure_response)
    print(f"   ❌ 失敗事例の学習: {learn_failure}")
    
    # 8. 最終統計
    print("\n8. 最終統計:")
    print("-" * 30)
    final_stats = rag.get_system_stats()
    print(f"   📊 最終文書数: {final_stats['knowledge_base_stats']['total_documents']}")
    print(f"   🎯 成功率: {final_stats['generation_stats']['successful_generations']}/{final_stats['generation_stats']['total_requests']}")
    print(f"   📈 コンテキスト使用率: {final_stats['context_usage_rate']:.2f}")
    
    print("\n🎉 RAGシステムデモンストレーション完了!")
    print("=" * 50)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())