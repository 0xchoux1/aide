from typing import Dict, List, Any, Optional
import uuid
import json
from datetime import datetime

from src.rag.vector_store import VectorStore
from src.agents.base_agent import Task, Response


class KnowledgeBase:
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or VectorStore()
        self.knowledge_types = {
            "task_execution": "タスク実行履歴",
            "execution_pattern": "実行パターン",
            "troubleshooting": "トラブルシューティング",
            "best_practice": "ベストプラクティス",
            "error_solution": "エラー解決方法"
        }
    
    def add_task_knowledge(self, task: Task, response: Response) -> bool:
        """タスクとその実行結果を知識として追加"""
        try:
            document = {
                "id": f"task_{task.id}",
                "content": f"タスク: {task.description}\n実行結果: {response.content}",
                "metadata": {
                    "type": "task_execution",
                    "task_type": task.task_type,
                    "task_id": task.id,
                    "quality_score": response.quality_score,
                    "task_description": task.description,
                    "response_content": response.content,
                    "execution_time": response.created_at.isoformat()
                }
            }
            
            return self.vector_store.add_document(document)
        except Exception as e:
            print(f"Error adding task knowledge: {e}")
            return False
    
    def add_execution_pattern(self, pattern: Dict[str, Any]) -> bool:
        """実行パターンを知識として追加"""
        try:
            pattern_id = pattern.get("pattern_id", str(uuid.uuid4()))
            
            content = f"実行パターン: {pattern.get('task_type', 'unknown')}\n"
            content += f"成功条件: {', '.join(pattern.get('success_conditions', []))}\n"
            content += f"失敗条件: {', '.join(pattern.get('failure_conditions', []))}"
            
            document = {
                "id": f"pattern_{pattern_id}",
                "content": content,
                "metadata": {
                    "type": "execution_pattern",
                    "pattern_id": pattern_id,
                    "task_type": pattern.get("task_type"),
                    "success_conditions_text": ", ".join(pattern.get("success_conditions", [])),
                    "failure_conditions_text": ", ".join(pattern.get("failure_conditions", [])),
                    "confidence_score": pattern.get("confidence_score", 0.7)
                }
            }
            
            return self.vector_store.add_document(document)
        except Exception as e:
            print(f"Error adding execution pattern: {e}")
            return False
    
    def add_troubleshooting_knowledge(self, troubleshooting: Dict[str, Any]) -> bool:
        """トラブルシューティング知識を追加"""
        try:
            problem = troubleshooting.get("problem", "")
            solutions = troubleshooting.get("solutions", [])
            category = troubleshooting.get("category", "general")
            
            content = f"問題: {problem}\n"
            content += f"解決策: {', '.join(solutions)}\n"
            content += f"カテゴリ: {category}"
            
            document = {
                "id": f"troubleshooting_{str(uuid.uuid4())}",
                "content": content,
                "metadata": {
                    "type": "troubleshooting",
                    "problem": problem,
                    "solutions_text": ", ".join(solutions),  # リストを文字列に変換
                    "category": category,
                    "severity": troubleshooting.get("severity", "medium")
                }
            }
            
            return self.vector_store.add_document(document)
        except Exception as e:
            print(f"Error adding troubleshooting knowledge: {e}")
            return False
    
    def add_best_practice(self, practice: Dict[str, Any]) -> bool:
        """ベストプラクティスを追加"""
        try:
            title = practice.get("title", "")
            description = practice.get("description", "")
            domain = practice.get("domain", "general")
            
            content = f"ベストプラクティス: {title}\n"
            content += f"説明: {description}\n"
            content += f"分野: {domain}"
            
            document = {
                "id": f"best_practice_{str(uuid.uuid4())}",
                "content": content,
                "metadata": {
                    "type": "best_practice",
                    "title": title,
                    "description": description,
                    "domain": domain,
                    "importance": practice.get("importance", "medium")
                }
            }
            
            return self.vector_store.add_document(document)
        except Exception as e:
            print(f"Error adding best practice: {e}")
            return False
    
    def add_error_solution(self, error_info: Dict[str, Any]) -> bool:
        """エラーと解決方法を追加"""
        try:
            error_message = error_info.get("error_message", "")
            solution = error_info.get("solution", "")
            error_type = error_info.get("error_type", "unknown")
            
            content = f"エラー: {error_message}\n"
            content += f"解決方法: {solution}\n"
            content += f"エラータイプ: {error_type}"
            
            document = {
                "id": f"error_solution_{str(uuid.uuid4())}",
                "content": content,
                "metadata": {
                    "type": "error_solution",
                    "error_message": error_message,
                    "solution": solution,
                    "error_type": error_type,
                    "frequency": error_info.get("frequency", 1)
                }
            }
            
            return self.vector_store.add_document(document)
        except Exception as e:
            print(f"Error adding error solution: {e}")
            return False
    
    def search_knowledge(self, query: str, knowledge_type: Optional[str] = None, top_k: int = 10) -> List[Dict[str, Any]]:
        """知識を検索"""
        try:
            filters = None
            if knowledge_type:
                filters = {"type": knowledge_type}
            
            return self.vector_store.search_documents(query, top_k, filters)
        except Exception as e:
            print(f"Error searching knowledge: {e}")
            return []
    
    def get_knowledge_by_task_type(self, task_type: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """タスクタイプ別の知識を取得"""
        try:
            filters = {"task_type": task_type}
            return self.vector_store.search_documents(f"task_type:{task_type}", top_k, filters)
        except Exception as e:
            print(f"Error getting knowledge by task type: {e}")
            return []
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """知識ベースの統計情報を取得"""
        try:
            return self.vector_store.get_collection_info()
        except Exception as e:
            print(f"Error getting knowledge stats: {e}")
            return {"total_documents": 0, "document_types": {}}
    
    def update_knowledge_quality(self, document_id: str, quality_score: float) -> bool:
        """知識の品質スコアを更新"""
        try:
            # 既存の文書を取得
            existing_docs = self.vector_store.collection.get(ids=[document_id])
            
            if not existing_docs["ids"]:
                return False
            
            # メタデータを更新
            metadata = existing_docs["metadatas"][0]
            metadata["quality_score"] = quality_score
            metadata["updated_at"] = datetime.now().isoformat()
            
            # 文書を更新
            updated_doc = {
                "id": document_id,
                "content": existing_docs["documents"][0],
                "metadata": metadata
            }
            
            return self.vector_store.update_document(updated_doc)
        except Exception as e:
            print(f"Error updating knowledge quality: {e}")
            return False
    
    def cleanup_old_knowledge(self, days_old: int = 30) -> bool:
        """古い知識を削除"""
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # 全文書を取得
            all_docs = self.vector_store.collection.get()
            
            old_doc_ids = []
            for i, metadata in enumerate(all_docs["metadatas"]):
                created_at = metadata.get("created_at")
                if created_at:
                    doc_date = datetime.fromisoformat(created_at)
                    if doc_date < cutoff_date:
                        old_doc_ids.append(all_docs["ids"][i])
            
            # 古い文書を削除
            if old_doc_ids:
                for doc_id in old_doc_ids:
                    self.vector_store.delete_document(doc_id)
            
            return True
        except Exception as e:
            print(f"Error cleaning up old knowledge: {e}")
            return False
    
    def export_knowledge(self, knowledge_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """知識をエクスポート"""
        try:
            if knowledge_type:
                filters = {"type": knowledge_type}
                results = self.vector_store.collection.get(where=filters)
            else:
                results = self.vector_store.collection.get()
            
            exported_knowledge = []
            for i, doc_id in enumerate(results["ids"]):
                exported_knowledge.append({
                    "id": doc_id,
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i]
                })
            
            return exported_knowledge
        except Exception as e:
            print(f"Error exporting knowledge: {e}")
            return []