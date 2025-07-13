import pytest
from unittest.mock import Mock, patch
from src.agents.base_agent import BaseAgent, Task, Feedback


class TestBaseAgent:
    
    def test_agent_initialization(self):
        agent = BaseAgent()
        assert agent.name == "BaseAgent"
        assert agent.memory is not None
        assert agent.learning_system is not None
    
    def test_execute_task_returns_response(self):
        agent = BaseAgent()
        task = Task(description="サーバーの状態を確認", task_type="system_check")
        
        response = agent.execute_task(task)
        
        assert response is not None
        assert hasattr(response, 'content')
        assert hasattr(response, 'quality_score')
    
    def test_agent_learns_from_feedback(self):
        agent = BaseAgent()
        task = Task(description="サーバーの状態を確認", task_type="system_check")
        
        # 初回実行
        initial_response = agent.execute_task(task)
        initial_quality = initial_response.quality_score
        
        # フィードバック提供
        feedback = Feedback(
            task=task,
            response=initial_response,
            rating=3,
            improvement_suggestion="もっと詳細な情報が必要"
        )
        
        # 学習処理
        agent.learn(feedback)
        
        # 改善された実行
        improved_response = agent.execute_task(task)
        
        # 品質向上の確認
        assert improved_response.quality_score > initial_quality
    
    def test_agent_stores_task_history(self):
        agent = BaseAgent()
        task = Task(description="ログファイルの確認", task_type="log_analysis")
        
        agent.execute_task(task)
        
        assert len(agent.memory.get_task_history()) == 1
        assert agent.memory.get_task_history()[0].description == task.description
    
    def test_agent_retrieves_relevant_memories(self):
        agent = BaseAgent()
        
        # 関連するタスクを実行
        task1 = Task(description="CPU使用率の確認", task_type="system_check")
        task2 = Task(description="メモリ使用率の確認", task_type="system_check")
        
        agent.execute_task(task1)
        agent.execute_task(task2)
        
        # 関連メモリの取得
        memories = agent.memory.get_relevant_memories("system_check")
        
        assert len(memories) == 2
        assert all(memory.task_type == "system_check" for memory in memories)
    
    def test_agent_applies_learned_patterns(self):
        agent = BaseAgent()
        
        # パターンを学習
        for i in range(5):
            task = Task(description=f"サーバー{i}の状態確認", task_type="system_check")
            response = agent.execute_task(task)
            
            feedback = Feedback(
                task=task,
                response=response,
                rating=4,
                improvement_suggestion="詳細なメトリクスを含める"
            )
            agent.learn(feedback)
        
        # 新しいタスクで学習した知識を適用
        new_task = Task(description="新サーバーの状態確認", task_type="system_check")
        response = agent.execute_task(new_task)
        
        # 学習済みパターンが適用されているか確認
        assert "メトリクス" in response.content or "詳細" in response.content
        assert response.quality_score > 0.7