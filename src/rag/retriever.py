from typing import Dict, List, Any, Optional
import re
from collections import Counter

from src.rag.knowledge_base import KnowledgeBase


class Retriever:
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None, 
                 similarity_threshold: float = 0.3, max_results: int = 10):
        self.knowledge_base = knowledge_base or KnowledgeBase()
        self.similarity_threshold = similarity_threshold
        self.max_results = max_results
    
    def retrieve_relevant_knowledge(self, query: str, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """クエリに関連する知識を検索"""
        try:
            # 知識ベースから関連文書を検索
            raw_results = self.knowledge_base.search_knowledge(query, knowledge_type=None, top_k=self.max_results)
            
            # 関連度でフィルタリング
            filtered_results = self._filter_by_relevance(raw_results)
            
            # 結果をフォーマット
            formatted_results = []
            for doc in filtered_results:
                formatted_results.append({
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "relevance_score": 1.0 - doc["score"]  # ChromaDBのスコアは距離なので反転
                })
            
            return formatted_results
        except Exception as e:
            print(f"Error retrieving relevant knowledge: {e}")
            return []
    
    def retrieve_by_task_type(self, task_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """タスクタイプ別の知識を検索"""
        try:
            raw_results = self.knowledge_base.get_knowledge_by_task_type(task_type, limit)
            
            formatted_results = []
            for doc in raw_results:
                formatted_results.append({
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "relevance_score": 1.0 - doc["score"]
                })
            
            return formatted_results
        except Exception as e:
            print(f"Error retrieving by task type: {e}")
            return []
    
    def retrieve_execution_patterns(self, task_type: str) -> List[Dict[str, Any]]:
        """実行パターンを検索"""
        try:
            raw_results = self.knowledge_base.search_knowledge(
                f"execution_pattern {task_type}", 
                knowledge_type="execution_pattern",
                top_k=self.max_results
            )
            
            formatted_results = []
            for doc in raw_results:
                formatted_results.append({
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "pattern_id": doc["metadata"].get("pattern_id"),
                    "confidence_score": doc["metadata"].get("confidence_score", 0.7)
                })
            
            return formatted_results
        except Exception as e:
            print(f"Error retrieving execution patterns: {e}")
            return []
    
    def retrieve_troubleshooting_knowledge(self, problem_description: str) -> List[Dict[str, Any]]:
        """トラブルシューティング知識を検索"""
        try:
            raw_results = self.knowledge_base.search_knowledge(
                problem_description, 
                knowledge_type="troubleshooting",
                top_k=self.max_results
            )
            
            formatted_results = []
            for doc in raw_results:
                formatted_results.append({
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "problem": doc["metadata"].get("problem"),
                    "solutions": doc["metadata"].get("solutions", []),
                    "category": doc["metadata"].get("category", "general")
                })
            
            return formatted_results
        except Exception as e:
            print(f"Error retrieving troubleshooting knowledge: {e}")
            return []
    
    def retrieve_best_practices(self, domain: str) -> List[Dict[str, Any]]:
        """ベストプラクティスを検索"""
        try:
            raw_results = self.knowledge_base.search_knowledge(
                f"best_practice {domain}", 
                knowledge_type="best_practice",
                top_k=self.max_results
            )
            
            formatted_results = []
            for doc in raw_results:
                formatted_results.append({
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "title": doc["metadata"].get("title"),
                    "description": doc["metadata"].get("description"),
                    "domain": doc["metadata"].get("domain"),
                    "importance": doc["metadata"].get("importance", "medium")
                })
            
            return formatted_results
        except Exception as e:
            print(f"Error retrieving best practices: {e}")
            return []
    
    def retrieve_similar_tasks(self, task_description: str, task_type: str) -> List[Dict[str, Any]]:
        """類似タスクを検索"""
        try:
            query = f"{task_description} {task_type}"
            raw_results = self.knowledge_base.search_knowledge(
                query, 
                knowledge_type="task_execution",
                top_k=self.max_results
            )
            
            formatted_results = []
            for doc in raw_results:
                formatted_results.append({
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "task_description": doc["metadata"].get("task_description"),
                    "quality_score": doc["metadata"].get("quality_score", 0.5),
                    "similarity_score": 1.0 - doc["score"]
                })
            
            return formatted_results
        except Exception as e:
            print(f"Error retrieving similar tasks: {e}")
            return []
    
    def _filter_by_relevance(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """関連度でフィルタリング"""
        try:
            # ChromaDBのスコアは距離（小さい方が類似度高い）
            # similarity_threshold=0.3なので、距離の閾値を2.0に設定（緩い設定）
            threshold_score = 2.0
            
            filtered = []
            for doc in documents:
                # 距離がthreshold_score以下の文書を採用
                if doc["score"] <= threshold_score:
                    filtered.append(doc)
            
            return filtered
        except Exception as e:
            print(f"Error filtering by relevance: {e}")
            return documents
    
    def _extract_keywords(self, text: str) -> List[str]:
        """テキストからキーワードを抽出"""
        try:
            # 日本語と英語の単語を抽出
            japanese_words = re.findall(r'[ぁ-んァ-ヶ一-龠]+', text)
            english_words = re.findall(r'[a-zA-Z]+', text)
            
            # 短すぎる単語を除去
            keywords = [word for word in japanese_words + english_words if len(word) > 1]
            
            # 頻度順でソート
            word_freq = Counter(keywords)
            return [word for word, freq in word_freq.most_common(10)]
        except Exception as e:
            print(f"Error extracting keywords: {e}")
            return []
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """セマンティック類似度を計算（簡易版）"""
        try:
            # キーワードベースの類似度計算
            keywords1 = set(self._extract_keywords(text1))
            keywords2 = set(self._extract_keywords(text2))
            
            if not keywords1 or not keywords2:
                return 0.0
            
            intersection = keywords1.intersection(keywords2)
            union = keywords1.union(keywords2)
            
            jaccard_similarity = len(intersection) / len(union)
            return jaccard_similarity
        except Exception as e:
            print(f"Error calculating semantic similarity: {e}")
            return 0.0
    
    def _rank_by_context_relevance(self, documents: List[Dict[str, Any]], 
                                  context: str) -> List[Dict[str, Any]]:
        """コンテキストに基づいてランキング"""
        try:
            for doc in documents:
                content = doc["content"]
                context_similarity = self._calculate_semantic_similarity(content, context)
                
                # 既存の関連度スコアと組み合わせ
                original_score = doc.get("relevance_score", 0.5)
                combined_score = (original_score + context_similarity) / 2
                doc["relevance_score"] = combined_score
            
            # スコア順でソート
            return sorted(documents, key=lambda x: x["relevance_score"], reverse=True)
        except Exception as e:
            print(f"Error ranking by context relevance: {e}")
            return documents
    
    def retrieve_with_context(self, query: str, context: str, 
                            task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """コンテキストを考慮した検索"""
        try:
            # 基本的な検索
            results = self.retrieve_relevant_knowledge(query, task_type)
            
            # コンテキストに基づいてランキング
            contextualized_results = self._rank_by_context_relevance(results, context)
            
            return contextualized_results
        except Exception as e:
            print(f"Error retrieving with context: {e}")
            return []