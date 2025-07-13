from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json


@dataclass
class MemoryItem:
    task_id: str
    task_type: str
    description: str
    response_content: str
    quality_score: float
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningItem:
    feedback_id: str
    task_type: str
    improvement_patterns: List[Dict[str, Any]]
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class ShortTermMemory:
    def __init__(self, max_items: int = 1000, retention_hours: int = 24):
        self.max_items = max_items
        self.retention_hours = retention_hours
        self.task_memories: List[MemoryItem] = []
        self.learning_memories: List[LearningItem] = []
    
    def store_task(self, task, response):
        memory_item = MemoryItem(
            task_id=task.id,
            task_type=task.task_type,
            description=task.description,
            response_content=response.content,
            quality_score=response.quality_score,
            created_at=task.created_at
        )
        
        self.task_memories.append(memory_item)
        self._cleanup_old_memories()
    
    def store_learning(self, feedback, improvement_patterns):
        learning_item = LearningItem(
            feedback_id=str(feedback.created_at.timestamp()),
            task_type=feedback.task.task_type,
            improvement_patterns=improvement_patterns,
            created_at=feedback.created_at
        )
        
        self.learning_memories.append(learning_item)
        self._cleanup_old_memories()
    
    def get_task_history(self) -> List[MemoryItem]:
        return self.task_memories.copy()
    
    def get_relevant_memories(self, task_type: str) -> List[MemoryItem]:
        return [
            memory for memory in self.task_memories
            if memory.task_type == task_type
        ]
    
    def get_learning_history(self, task_type: Optional[str] = None) -> List[LearningItem]:
        if task_type:
            return [
                learning for learning in self.learning_memories
                if learning.task_type == task_type
            ]
        return self.learning_memories.copy()
    
    def _cleanup_old_memories(self):
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        
        # 古いタスクメモリを削除
        self.task_memories = [
            memory for memory in self.task_memories
            if memory.created_at > cutoff_time
        ]
        
        # 古い学習メモリを削除
        self.learning_memories = [
            learning for learning in self.learning_memories
            if learning.created_at > cutoff_time
        ]
        
        # 最大数を超えた場合は古いものから削除
        if len(self.task_memories) > self.max_items:
            self.task_memories = self.task_memories[-self.max_items:]
        
        if len(self.learning_memories) > self.max_items:
            self.learning_memories = self.learning_memories[-self.max_items:]
    
    def get_statistics(self) -> Dict[str, Any]:
        task_types = {}
        total_quality = 0
        
        for memory in self.task_memories:
            task_types[memory.task_type] = task_types.get(memory.task_type, 0) + 1
            total_quality += memory.quality_score
        
        avg_quality = total_quality / len(self.task_memories) if self.task_memories else 0
        
        return {
            'total_tasks': len(self.task_memories),
            'total_learnings': len(self.learning_memories),
            'average_quality': avg_quality,
            'task_types': task_types,
            'memory_usage': {
                'task_memories': len(self.task_memories),
                'learning_memories': len(self.learning_memories),
                'max_items': self.max_items
            }
        }