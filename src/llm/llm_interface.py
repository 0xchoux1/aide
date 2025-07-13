from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class LLMResponse:
    """LLM応答の標準化されたフォーマット"""
    content: str
    metadata: Optional[Dict[str, Any]] = None
    usage_stats: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    success: bool = True
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'content': self.content,
            'metadata': self.metadata or {},
            'usage_stats': self.usage_stats or {},
            'timestamp': self.timestamp.isoformat(),
            'success': self.success,
            'error_message': self.error_message
        }
    
    def to_json(self) -> str:
        """JSON形式に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class LLMInterface(ABC):
    """LLMサービスの統一インターフェース"""
    
    def __init__(self, model_name: str = "default", **kwargs):
        self.model_name = model_name
        self.config = kwargs
        self.request_count = 0
        self.total_tokens = 0
        self.error_count = 0
    
    @abstractmethod
    def generate_response(self, prompt: str, context: Optional[str] = None, 
                         max_tokens: Optional[int] = None, 
                         temperature: float = 0.7,
                         **kwargs) -> LLMResponse:
        """
        テキスト生成を実行
        
        Args:
            prompt: メインプロンプト
            context: 追加コンテキスト（RAG用）
            max_tokens: 最大トークン数
            temperature: 生成の多様性
            **kwargs: その他のパラメータ
            
        Returns:
            LLMResponse: 統一された応答形式
        """
        pass
    
    @abstractmethod
    def generate_structured_response(self, prompt: str, 
                                   output_format: Dict[str, str],
                                   context: Optional[str] = None,
                                   **kwargs) -> LLMResponse:
        """
        構造化された応答を生成
        
        Args:
            prompt: メインプロンプト
            output_format: 期待する出力形式の説明
            context: 追加コンテキスト
            **kwargs: その他のパラメータ
            
        Returns:
            LLMResponse: 構造化された応答
        """
        pass
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """使用統計を取得"""
        return {
            'request_count': self.request_count,
            'total_tokens': self.total_tokens,
            'error_count': self.error_count,
            'success_rate': (self.request_count - self.error_count) / self.request_count if self.request_count > 0 else 0.0,
            'model_name': self.model_name
        }
    
    def _update_stats(self, tokens_used: int = 0, is_error: bool = False):
        """統計を更新"""
        self.request_count += 1
        self.total_tokens += tokens_used
        if is_error:
            self.error_count += 1
    
    def reset_stats(self):
        """統計をリセット"""
        self.request_count = 0
        self.total_tokens = 0
        self.error_count = 0