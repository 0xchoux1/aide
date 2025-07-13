from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import time
from datetime import datetime


class ToolStatus(Enum):
    """ツール実行ステータス"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"


@dataclass
class ToolResult:
    """ツール実行結果"""
    status: ToolStatus
    output: str
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'status': self.status.value,
            'output': self.output,
            'error': self.error,
            'execution_time': self.execution_time,
            'metadata': self.metadata or {},
            'timestamp': self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        """JSON形式に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class BaseTool(ABC):
    """ツールの基底クラス"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.execution_history = []
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> ToolResult:
        """ツールを実行する"""
        pass
    
    def _record_execution(self, result: ToolResult):
        """実行履歴を記録"""
        self.execution_history.append(result)
        
        # 履歴を最新100件まで保持
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """実行統計を取得"""
        if not self.execution_history:
            return {
                'total_executions': 0,
                'success_rate': 0.0,
                'average_execution_time': 0.0,
                'last_execution': None
            }
        
        total = len(self.execution_history)
        successful = sum(1 for r in self.execution_history if r.status == ToolStatus.SUCCESS)
        avg_time = sum(r.execution_time for r in self.execution_history) / total
        
        return {
            'total_executions': total,
            'success_rate': successful / total,
            'average_execution_time': avg_time,
            'last_execution': self.execution_history[-1].timestamp.isoformat(),
            'status_breakdown': self._get_status_breakdown()
        }
    
    def _get_status_breakdown(self) -> Dict[str, int]:
        """ステータス別の実行回数を取得"""
        breakdown = {}
        for result in self.execution_history:
            status = result.status.value
            breakdown[status] = breakdown.get(status, 0) + 1
        return breakdown
    
    def get_recent_errors(self, limit: int = 5) -> list:
        """最近のエラーを取得"""
        errors = [r for r in self.execution_history 
                 if r.status != ToolStatus.SUCCESS and r.error]
        return errors[-limit:] if errors else []
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"