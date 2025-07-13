#!/usr/bin/env python3
"""
AIDE CLI エントリーポイント

コマンドライン インターフェース for AIDE システム
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List

# プロジェクトのルートディレクトリをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.config import get_config_manager
    from src.logging import get_logger
    from src.agents.ai_agent import get_ai_agent
    from src.agents.learning_agent import get_learning_agent
    from src.agents.coordination_agent import get_coordination_agent
    from src.memory.vector_store import get_vector_store
    from src.memory.knowledge_base import get_knowledge_base
except ImportError as e:
    print(f"⚠️  インポートエラー: {e}")
    print("📋 基本的な初期化を行います...")
    
    # 基本的なモックファンスを定義
    def get_config_manager():
        class ConfigManager:
            def get_config(self):
                return {"system": {"name": "AIDE", "version": "0.1.0", "environment": "development"}}
        return ConfigManager()
    
    def get_logger(name):
        import logging
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)
    
    def get_ai_agent():
        class MockAgent:
            def process_query(self, query): return f"Mock response to: {query}"
        return MockAgent()
    
    def get_learning_agent():
        class MockLearningAgent:
            def start_learning(self): pass
            def stop_learning(self): pass
            def get_learning_status(self): return "停止中"
        return MockLearningAgent()
    
    def get_coordination_agent():
        class MockCoordinationAgent:
            def orchestrate_agents(self): return "協調実行完了"
        return MockCoordinationAgent()
    
    def get_vector_store():
        class MockVectorStore: pass
        return MockVectorStore()
    
    def get_knowledge_base():
        class MockKnowledgeBase: pass
        return MockKnowledgeBase()


def init_command(args):
    """AIDE システム初期化"""
    logger = get_logger(__name__)
    
    print("🚀 AIDE システムを初期化しています...")
    
    try:
        # 設定管理の初期化
        config_manager = get_config_manager()
        config = config_manager.get_config()
        
        print(f"✅ 設定読み込み完了: {config.get('system', {}).get('name', 'AIDE')}")
        
        # ベクターストア初期化
        vector_store = get_vector_store()
        print("✅ ベクターストア初期化完了")
        
        # 知識ベース初期化
        knowledge_base = get_knowledge_base()
        print("✅ 知識ベース初期化完了")
        
        # エージェント初期化
        ai_agent = get_ai_agent()
        learning_agent = get_learning_agent()
        coordination_agent = get_coordination_agent()
        
        print("✅ AIエージェント初期化完了")
        print("✅ 学習エージェント初期化完了")
        print("✅ 協調エージェント初期化完了")
        
        print("\n🎉 AIDE システムの初期化が完了しました！")
        print("\n使用可能なコマンド:")
        print("  aide agent    - エージェント操作")
        print("  aide learn    - 学習機能")
        print("  aide status   - システム状態確認")
        print("  aide --help   - ヘルプ表示")
        
    except Exception as e:
        logger.error(f"初期化エラー: {e}")
        print(f"❌ 初期化中にエラーが発生しました: {e}")
        sys.exit(1)


def agent_command(args):
    """エージェント操作"""
    logger = get_logger(__name__)
    
    try:
        if args.type == "ai":
            agent = get_ai_agent()
            if args.query:
                result = agent.process_query(args.query)
                print(f"AI応答: {result}")
            else:
                print("AIエージェントが利用可能です")
                
        elif args.type == "learning":
            agent = get_learning_agent()
            if args.action == "start":
                agent.start_learning()
                print("学習を開始しました")
            elif args.action == "status":
                status = agent.get_learning_status()
                print(f"学習状況: {status}")
            else:
                print("学習エージェントが利用可能です")
                
        elif args.type == "coordination":
            agent = get_coordination_agent()
            if args.action == "orchestrate":
                result = agent.orchestrate_agents()
                print(f"協調実行結果: {result}")
            else:
                print("協調エージェントが利用可能です")
                
        else:
            print("利用可能なエージェント: ai, learning, coordination")
            
    except Exception as e:
        logger.error(f"エージェント実行エラー: {e}")
        print(f"❌ エラーが発生しました: {e}")


def learn_command(args):
    """学習機能"""
    logger = get_logger(__name__)
    
    try:
        learning_agent = get_learning_agent()
        
        if args.action == "start":
            learning_agent.start_learning()
            print("学習プロセスを開始しました")
            
        elif args.action == "stop":
            learning_agent.stop_learning()
            print("学習プロセスを停止しました")
            
        elif args.action == "status":
            status = learning_agent.get_learning_status()
            print(f"学習状況: {status}")
            
        else:
            print("利用可能なアクション: start, stop, status")
            
    except Exception as e:
        logger.error(f"学習機能エラー: {e}")
        print(f"❌ エラーが発生しました: {e}")


def status_command(args):
    """システム状態確認"""
    logger = get_logger(__name__)
    
    try:
        print("📊 AIDE システム状態")
        print("=" * 50)
        
        # 設定状態
        config_manager = get_config_manager()
        config = config_manager.get_config()
        print(f"システム名: {config.get('system', {}).get('name', 'AIDE')}")
        print(f"バージョン: {config.get('system', {}).get('version', '0.1.0')}")
        print(f"環境: {config.get('system', {}).get('environment', 'development')}")
        
        # エージェント状態
        print("\nエージェント状態:")
        try:
            ai_agent = get_ai_agent()
            print("  ✅ AIエージェント: 利用可能")
        except:
            print("  ❌ AIエージェント: エラー")
            
        try:
            learning_agent = get_learning_agent()
            status = learning_agent.get_learning_status()
            print(f"  ✅ 学習エージェント: {status}")
        except:
            print("  ❌ 学習エージェント: エラー")
            
        try:
            coordination_agent = get_coordination_agent()
            print("  ✅ 協調エージェント: 利用可能")
        except:
            print("  ❌ 協調エージェント: エラー")
            
        # ストレージ状態
        print("\nストレージ状態:")
        try:
            vector_store = get_vector_store()
            print("  ✅ ベクターストア: 利用可能")
        except:
            print("  ❌ ベクターストア: エラー")
            
        try:
            knowledge_base = get_knowledge_base()
            print("  ✅ 知識ベース: 利用可能")
        except:
            print("  ❌ 知識ベース: エラー")
            
    except Exception as e:
        logger.error(f"状態確認エラー: {e}")
        print(f"❌ エラーが発生しました: {e}")


def create_parser():
    """コマンドライン引数パーサー作成"""
    parser = argparse.ArgumentParser(
        description="AIDE - Autonomous Intelligent Development Environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  aide init                     # システム初期化
  aide agent ai --query "質問"  # AI エージェントに質問
  aide learn start              # 学習開始
  aide status                   # システム状態確認
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="利用可能なコマンド")
    
    # init コマンド
    init_parser = subparsers.add_parser("init", help="システム初期化")
    
    # agent コマンド
    agent_parser = subparsers.add_parser("agent", help="エージェント操作")
    agent_parser.add_argument("type", choices=["ai", "learning", "coordination"], 
                             help="エージェントタイプ")
    agent_parser.add_argument("--query", "-q", help="AI エージェントへの質問")
    agent_parser.add_argument("--action", "-a", 
                             choices=["start", "stop", "status", "orchestrate"],
                             help="実行するアクション")
    
    # learn コマンド
    learn_parser = subparsers.add_parser("learn", help="学習機能")
    learn_parser.add_argument("action", choices=["start", "stop", "status"],
                             help="学習アクション")
    
    # status コマンド
    status_parser = subparsers.add_parser("status", help="システム状態確認")
    
    return parser


def main():
    """メイン関数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # ロガー初期化
    logger = get_logger(__name__)
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "init":
            init_command(args)
        elif args.command == "agent":
            agent_command(args)
        elif args.command == "learn":
            learn_command(args)
        elif args.command == "status":
            status_command(args)
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\n\n⏹️  処理を中断しました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        print(f"❌ 予期しないエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()