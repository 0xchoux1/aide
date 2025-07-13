import pytest
from unittest.mock import Mock, patch
from src.agents.crew_agents import TaskAnalyzer, Executor, Learner, MultiAgentSystem
from src.agents.base_agent import Task, Response, Feedback


class TestTaskAnalyzer:
    
    def test_task_analyzer_initialization(self):
        analyzer = TaskAnalyzer()
        assert analyzer.name == "TaskAnalyzer"
        assert analyzer.role == "タスク分析スペシャリスト"
        assert analyzer.goal == "ユーザーの要求を理解し、適切なアクションを計画"
    
    def test_analyze_task_simple(self):
        analyzer = TaskAnalyzer()
        task = Task("サーバーの状態確認", "system_check")
        
        analysis = analyzer.analyze_task(task)
        
        assert analysis is not None
        assert analysis.task_type == "system_check"
        assert analysis.complexity == "simple"
        assert len(analysis.subtasks) >= 1
    
    def test_analyze_task_complex(self):
        analyzer = TaskAnalyzer()
        task = Task("アプリケーションの全体的な性能最適化", "performance_optimization")
        
        analysis = analyzer.analyze_task(task)
        
        assert analysis.complexity == "complex"
        assert len(analysis.subtasks) > 1
        assert analysis.estimated_time > 0
    
    def test_create_execution_plan(self):
        analyzer = TaskAnalyzer()
        task = Task("データベース接続エラーの調査", "troubleshooting")
        
        plan = analyzer.create_execution_plan(task)
        
        assert plan is not None
        assert len(plan.steps) > 0
        assert plan.priority == "high"


class TestExecutor:
    
    def test_executor_initialization(self):
        executor = Executor()
        assert executor.name == "Executor"
        assert executor.role == "実行エージェント"
        assert executor.goal == "計画されたタスクを実行"
    
    def test_execute_simple_task(self):
        executor = Executor()
        task = Task("ログファイルの確認", "log_analysis")
        
        result = executor.execute_task(task)
        
        assert result is not None
        assert result.status == "completed"
        assert len(result.details) > 0
    
    def test_execute_with_plan(self):
        executor = Executor()
        task = Task("システムメトリクスの収集", "monitoring")
        
        # 実行計画を含む
        plan = Mock()
        plan.steps = ["CPU使用率確認", "メモリ使用量確認", "ディスク使用量確認"]
        
        result = executor.execute_with_plan(task, plan)
        
        assert result.status == "completed"
        assert len(result.step_results) == 3
    
    def test_execute_handles_errors(self):
        executor = Executor()
        task = Task("存在しないファイルの処理", "file_operation")
        
        result = executor.execute_task(task)
        
        assert result.status in ["failed", "partial"]
        assert result.error_message is not None


class TestLearner:
    
    def test_learner_initialization(self):
        learner = Learner()
        assert learner.name == "Learner"
        assert learner.role == "学習エージェント"
        assert learner.goal == "実行結果から学習し、知識ベースを更新"
    
    def test_process_execution_result(self):
        learner = Learner()
        task = Task("サーバー監視", "monitoring")
        
        # 実行結果のモック
        execution_result = Mock()
        execution_result.status = "completed"
        execution_result.performance_metrics = {"duration": 2.5, "success_rate": 0.95}
        
        learning_outcome = learner.process_execution_result(task, execution_result)
        
        assert learning_outcome is not None
        assert learning_outcome.knowledge_gained > 0
        assert len(learning_outcome.patterns) > 0
    
    def test_update_knowledge_base(self):
        learner = Learner()
        task = Task("ネットワーク診断", "network_check")
        
        # 学習データ
        learning_data = {
            "task_type": "network_check",
            "success_patterns": ["ping確認", "ポート確認"],
            "failure_patterns": ["タイムアウト", "接続拒否"]
        }
        
        updated = learner.update_knowledge_base(task, learning_data)
        
        assert updated is True
        assert learner.knowledge_base.has_data("network_check")
    
    def test_extract_improvement_suggestions(self):
        learner = Learner()
        task = Task("アプリケーション診断", "app_diagnosis")
        
        # 実行履歴
        execution_history = [
            {"status": "failed", "error": "connection_timeout"},
            {"status": "completed", "duration": 5.0},
            {"status": "failed", "error": "permission_denied"}
        ]
        
        suggestions = learner.extract_improvement_suggestions(task, execution_history)
        
        assert len(suggestions) > 0
        assert any("タイムアウト" in s for s in suggestions)
        assert any("権限" in s for s in suggestions)


class TestMultiAgentSystem:
    
    def test_system_initialization(self):
        system = MultiAgentSystem()
        assert system.task_analyzer is not None
        assert system.executor is not None
        assert system.learner is not None
        assert system.communication_bus is not None
    
    def test_process_task_workflow(self):
        system = MultiAgentSystem()
        task = Task("システム全体の健全性チェック", "system_health")
        
        result = system.process_task(task)
        
        assert result is not None
        assert result.analysis is not None
        assert result.execution is not None
        assert result.learning is not None
        assert result.overall_status in ["completed", "partial", "failed"]
    
    def test_agent_collaboration(self):
        system = MultiAgentSystem()
        task = Task("複雑なトラブルシューティング", "troubleshooting")
        
        # エージェント間の協調動作をテスト
        collaboration_log = []
        
        def mock_communicate(sender, receiver, message):
            collaboration_log.append(f"{sender} -> {receiver}: {message}")
        
        system.communication_bus.send = mock_communicate
        
        result = system.process_task(task)
        
        assert len(collaboration_log) > 0
        assert result.collaboration_quality > 0.7
    
    def test_knowledge_sharing(self):
        system = MultiAgentSystem()
        
        # 学習データの共有テスト
        learning_data = {
            "task_type": "database_optimization",
            "best_practices": ["インデックス最適化", "クエリチューニング"],
            "common_issues": ["デッドロック", "接続プール枯渇"]
        }
        
        shared = system.share_knowledge(learning_data)
        
        assert shared is True
        assert system.task_analyzer.has_knowledge("database_optimization")
        assert system.executor.has_knowledge("database_optimization")
        assert system.learner.has_knowledge("database_optimization")
    
    def test_adaptive_workflow(self):
        system = MultiAgentSystem()
        
        # 複数タスクでの適応的ワークフロー
        tasks = [
            Task("サーバー監視", "monitoring"),
            Task("ログ分析", "log_analysis"),
            Task("パフォーマンス調整", "performance_tuning")
        ]
        
        results = []
        for task in tasks:
            result = system.process_task(task)
            results.append(result)
        
        # 後のタスクの方が品質が向上していることを確認
        assert len(results) == 3
        # 品質スコアは同じかまたは向上している
        assert results[2].execution.quality_score >= results[0].execution.quality_score - 0.1
    
    def test_error_handling_and_recovery(self):
        system = MultiAgentSystem()
        
        # エラーハンドリングテスト
        problematic_task = Task("不正なタスク", "invalid_type")
        
        result = system.process_task(problematic_task)
        
        assert result.overall_status == "failed"
        assert result.error_recovery_attempted is True
        assert len(result.fallback_actions) > 0