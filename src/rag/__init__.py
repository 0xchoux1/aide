"""
AIDE RAG (Retrieval-Augmented Generation) システム

知識ベース管理とベクトル検索機能を提供
"""

from typing import Optional

try:
    from .rag_system import RAGSystem
    from .knowledge_base import KnowledgeBase
    from .vector_store import VectorStore
    from .retriever import Retriever
    
    __all__ = [
        'RAGSystem',
        'KnowledgeBase', 
        'VectorStore',
        'Retriever',
        'get_rag_system',
        'get_knowledge_base',
        'get_vector_store'
    ]
except ImportError:
    # モジュールが未実装の場合のフォールバック
    RAGSystem = None
    KnowledgeBase = None
    VectorStore = None
    Retriever = None


def get_rag_system(config: Optional[dict] = None) -> Optional['RAGSystem']:
    """RAGシステムのインスタンスを取得"""
    if RAGSystem is None:
        return None
    return RAGSystem(config or {})


def get_knowledge_base(config: Optional[dict] = None) -> Optional['KnowledgeBase']:
    """知識ベースのインスタンスを取得"""
    if KnowledgeBase is None:
        return None
    return KnowledgeBase(config or {})


def get_vector_store(config: Optional[dict] = None) -> Optional['VectorStore']:
    """ベクトルストアのインスタンスを取得"""
    if VectorStore is None:
        return None
    return VectorStore(config or {})