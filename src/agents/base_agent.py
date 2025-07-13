from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid
from src.memory.short_term import ShortTermMemory
from src.learning.feedback_processor import FeedbackProcessor


@dataclass
class Task:
    description: str
    task_type: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Response:
    content: str
    quality_score: float
    task_id: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Feedback:
    task: Task
    response: Response
    rating: int  # 1-5 scale
    improvement_suggestion: str
    created_at: datetime = field(default_factory=datetime.now)


class BaseAgent:
    def __init__(self, name: str = "BaseAgent"):
        self.name = name
        self.memory = ShortTermMemory()
        self.learning_system = FeedbackProcessor()
        self.performance_metrics = {
            'tasks_completed': 0,
            'average_quality': 0.0,
            'learning_iterations': 0
        }
    
    def execute_task(self, task: Task) -> Response:
        # 関連する記憶を取得
        relevant_memories = self.memory.get_relevant_memories(task.task_type)
        
        # 学習した知識を適用
        learned_patterns = self.learning_system.get_patterns(task.task_type)
        
        # タスクを実行（基本実装）
        response_content = self._generate_response(task, relevant_memories, learned_patterns)
        
        # 品質スコアを計算
        quality_score = self._calculate_quality_score(response_content, learned_patterns)
        
        response = Response(
            content=response_content,
            quality_score=quality_score,
            task_id=task.id
        )
        
        # メモリに保存
        self.memory.store_task(task, response)
        
        # メトリクス更新
        self.performance_metrics['tasks_completed'] += 1
        self._update_average_quality(quality_score)
        
        return response
    
    def learn(self, feedback: Feedback):
        # フィードバックを処理して学習
        self.learning_system.process_feedback(feedback)
        
        # 学習回数更新
        self.performance_metrics['learning_iterations'] += 1
        
        # 改善パターンを抽出
        improvement_patterns = self.learning_system.extract_improvement_patterns(feedback)
        
        # メモリに学習内容を保存
        self.memory.store_learning(feedback, improvement_patterns)
    
    def _generate_response(self, task: Task, memories: List[Any], patterns: List[Any]) -> str:
        base_response = f"タスク「{task.description}」を実行します。"
        
        # 学習パターンを適用
        if patterns:
            for pattern in patterns:
                if pattern.get('improvement_type') == 'add_details':
                    base_response += " 詳細なメトリクスを含めます。"
                elif pattern.get('improvement_type') == 'add_context':
                    base_response += " 関連する履歴情報を参照します。"
        
        # 関連メモリを活用
        if memories:
            base_response += f" 過去の{len(memories)}件の関連作業を参考にしています。"
        
        return base_response
    
    def _calculate_quality_score(self, content: str, patterns: List[Any]) -> float:
        base_score = 0.5
        
        # 学習パターンが適用されているかチェック
        if patterns:
            for pattern in patterns:
                if pattern.get('improvement_type') == 'add_details' and '詳細' in content:
                    base_score += 0.2
                elif pattern.get('improvement_type') == 'add_context' and '履歴' in content:
                    base_score += 0.2
        
        # 内容の豊富さをチェック
        if len(content) > 50:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _update_average_quality(self, new_score: float):
        current_avg = self.performance_metrics['average_quality']
        total_tasks = self.performance_metrics['tasks_completed']
        
        self.performance_metrics['average_quality'] = (
            (current_avg * (total_tasks - 1) + new_score) / total_tasks
        )
    
    @property
    def performance_score(self) -> float:
        return self.performance_metrics['average_quality']