from typing import Dict, List, Any, Optional
import chromadb
import uuid
import json
from datetime import datetime


class VectorStore:
    def __init__(self, collection_name: str = "aide_knowledge"):
        self.collection_name = collection_name
        self.client = chromadb.Client()
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        try:
            return self.client.get_collection(self.collection_name)
        except Exception:
            return self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "AIDE knowledge base collection"}
            )
    
    def add_document(self, document: Dict[str, Any]) -> bool:
        try:
            doc_id = document.get("id", str(uuid.uuid4()))
            content = document.get("content", "")
            metadata = document.get("metadata", {})
            
            # メタデータにタイムスタンプを追加
            metadata["created_at"] = datetime.now().isoformat()
            
            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id]
            )
            return True
        except Exception as e:
            print(f"Error adding document: {e}")
            return False
    
    def search_documents(self, query: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        try:
            query_params = {
                "query_texts": [query],
                "n_results": top_k
            }
            
            # フィルタが指定されている場合のみwhere句を追加
            if filters:
                query_params["where"] = filters
            
            results = self.collection.query(**query_params)
            
            documents = []
            for i, doc in enumerate(results["documents"][0]):
                documents.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i],
                    "score": results["distances"][0][i]
                })
            
            return documents
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []
    
    def update_document(self, document: Dict[str, Any]) -> bool:
        try:
            doc_id = document.get("id")
            content = document.get("content", "")
            metadata = document.get("metadata", {})
            
            # メタデータに更新タイムスタンプを追加
            metadata["updated_at"] = datetime.now().isoformat()
            
            self.collection.update(
                ids=[doc_id],
                documents=[content],
                metadatas=[metadata]
            )
            return True
        except Exception as e:
            print(f"Error updating document: {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        try:
            count = self.collection.count()
            
            # 文書タイプ別の統計を取得
            all_docs = self.collection.get()
            document_types = {}
            
            for metadata in all_docs["metadatas"]:
                doc_type = metadata.get("type", "unknown")
                document_types[doc_type] = document_types.get(doc_type, 0) + 1
            
            return {
                "total_documents": count,
                "document_types": document_types,
                "collection_name": self.collection_name
            }
        except Exception as e:
            print(f"Error getting collection info: {e}")
            return {"total_documents": 0, "document_types": {}}
    
    def bulk_add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        try:
            doc_ids = []
            contents = []
            metadatas = []
            
            for doc in documents:
                doc_ids.append(doc.get("id", str(uuid.uuid4())))
                contents.append(doc.get("content", ""))
                metadata = doc.get("metadata", {})
                metadata["created_at"] = datetime.now().isoformat()
                metadatas.append(metadata)
            
            self.collection.add(
                documents=contents,
                metadatas=metadatas,
                ids=doc_ids
            )
            return True
        except Exception as e:
            print(f"Error bulk adding documents: {e}")
            return False
    
    def clear_collection(self) -> bool:
        try:
            # 全文書を削除
            all_docs = self.collection.get()
            if all_docs["ids"]:
                self.collection.delete(ids=all_docs["ids"])
            return True
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False