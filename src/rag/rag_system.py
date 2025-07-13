from typing import Dict, List, Any, Optional
import re
from collections import Counter
from datetime import datetime

from src.rag.knowledge_base import KnowledgeBase
from src.rag.retriever import Retriever
from src.agents.base_agent import Task, Response

# LLM統合をオプショナルとして追加
try:
    from src.llm.claude_code_client import ClaudeCodeClient
    CLAUDE_CODE_AVAILABLE = True
except ImportError:
    CLAUDE_CODE_AVAILABLE = False
    ClaudeCodeClient = None


class RAGSystem:
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None,
                 retriever: Optional[Retriever] = None,
                 context_window_size: int = 4000,
                 use_claude_code: bool = True,
                 claude_timeout: int = 60):
        self.knowledge_base = knowledge_base or KnowledgeBase()
        self.retriever = retriever or Retriever(self.knowledge_base)
        self.context_window_size = context_window_size
        self.generation_stats = {
            "total_requests": 0,
            "successful_generations": 0,
            "context_usage_rate": 0.0,
            "llm_requests": 0,
            "llm_errors": 0
        }
        
        # Claude Code統合設定
        self.use_claude_code = use_claude_code and CLAUDE_CODE_AVAILABLE
        self.claude_client = None
        
        if self.use_claude_code:
            try:
                self.claude_client = ClaudeCodeClient(timeout=claude_timeout)
                print("Claude Code LLMバックエンドが正常に初期化されました")
            except Exception as e:
                print(f"Claude Code初期化エラー: {e}")
                print("フォールバックモード（ルールベース）で動作します")
                self.use_claude_code = False
    
    def generate_context_aware_response(self, task: Task) -> Response:
        """コンテキストを考慮した応答を生成"""
        try:
            self.generation_stats["total_requests"] += 1
            
            # 関連知識を検索
            relevant_contexts = self.retriever.retrieve_relevant_knowledge(
                task.description, 
                task.task_type
            )
            
            # コンテキストウィンドウを構築
            context_text = self._build_context_window(relevant_contexts)
            
            # 応答を生成
            response_content = self._generate_response_with_context(task, context_text)
            
            # 品質スコアを計算
            quality_score = self._calculate_response_quality(response_content, relevant_contexts)
            
            self.generation_stats["successful_generations"] += 1
            
            response = Response(
                content=response_content,
                quality_score=quality_score,
                task_id=task.id,
                metadata={
                    "retrieved_contexts": relevant_contexts,
                    "context_length": len(context_text),
                    "context_sources": len(relevant_contexts)
                }
            )
            
            return response
        except Exception as e:
            print(f"Error generating context-aware response: {e}")
            return Response(
                content=f"タスク「{task.description}」の実行中にエラーが発生しました",
                quality_score=0.3,
                task_id=task.id
            )
    
    def enhance_task_with_context(self, task: Task) -> Task:
        """タスクにコンテキスト情報を追加"""
        try:
            # 関連知識を検索
            relevant_contexts = self.retriever.retrieve_relevant_knowledge(
                task.description, 
                task.task_type
            )
            
            # 実行パターンを検索
            execution_patterns = self.retriever.retrieve_execution_patterns(task.task_type)
            
            # ベストプラクティスを検索
            best_practices = self.retriever.retrieve_best_practices(task.task_type)
            
            # タスクのメタデータに追加
            enhanced_metadata = task.metadata.copy()
            enhanced_metadata.update({
                "context": relevant_contexts,
                "execution_patterns": execution_patterns,
                "best_practices": best_practices,
                "enhanced_at": datetime.now().isoformat()
            })
            
            # 新しいタスクオブジェクトを作成
            enhanced_task = Task(
                description=task.description,
                task_type=task.task_type,
                metadata=enhanced_metadata
            )
            enhanced_task.id = task.id  # 同じIDを保持
            
            return enhanced_task
        except Exception as e:
            print(f"Error enhancing task with context: {e}")
            return task
    
    def update_knowledge_from_execution(self, task: Task, response) -> bool:
        """実行結果から知識を更新"""
        try:
            # ExecutionResultからResponseオブジェクトを作成
            if hasattr(response, 'content'):
                # 既にResponseオブジェクトの場合
                response_obj = response
            else:
                # ExecutionResultの場合、Responseオブジェクトを作成
                response_obj = Response(
                    content=getattr(response, 'result', str(response)),
                    quality_score=getattr(response, 'quality_score', 0.7),
                    task_id=task.id
                )
            
            # タスク実行知識を追加
            task_added = self.knowledge_base.add_task_knowledge(task, response_obj)
            
            # 実行パターンを抽出・追加
            if response_obj.quality_score > 0.8:
                pattern = self._extract_execution_pattern(task, response_obj)
                if pattern:
                    self.knowledge_base.add_execution_pattern(pattern)
            
            # エラーが発生した場合は解決方法を記録
            if response_obj.quality_score < 0.5:
                error_info = self._extract_error_info(task, response_obj)
                if error_info:
                    self.knowledge_base.add_error_solution(error_info)
            
            return task_added
        except Exception as e:
            print(f"Error updating knowledge from execution: {e}")
            return False
    
    def _build_context_window(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        """コンテキストウィンドウを構築"""
        try:
            if not retrieved_docs:
                return ""
            
            # 関連度順でソート
            sorted_docs = sorted(retrieved_docs, key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            context_parts = []
            current_length = 0
            
            for doc in sorted_docs:
                content = doc["content"]
                content_length = len(content)
                
                # コンテキストウィンドウサイズを超えない範囲で追加
                if current_length + content_length <= self.context_window_size:
                    context_parts.append(content)
                    current_length += content_length
                else:
                    # 残りの容量で切り詰める
                    remaining_space = self.context_window_size - current_length
                    if remaining_space > 100:  # 最低限の長さがある場合のみ
                        context_parts.append(content[:remaining_space])
                    break
            
            return "\n\n".join(context_parts)
        except Exception as e:
            print(f"Error building context window: {e}")
            return ""
    
    def _generate_response_with_context(self, task: Task, context: str) -> str:
        """コンテキストを使用して応答を生成"""
        try:
            # Claude Codeが利用可能な場合は、LLMを使用
            if self.use_claude_code and self.claude_client:
                return self._generate_llm_response(task, context)
            else:
                # フォールバック: ルールベース応答生成
                return self._generate_rule_based_response(task, context)
        except Exception as e:
            print(f"Error generating response with context: {e}")
            # エラー時のフォールバック
            return self._generate_rule_based_response(task, context)
    
    def _generate_llm_response(self, task: Task, context: str) -> str:
        """Claude Codeを使用してLLM応答を生成"""
        try:
            self.generation_stats["llm_requests"] += 1
            
            # Claude CodeのRAG特化メソッドを使用
            llm_response = self.claude_client.generate_rag_response(
                task_description=task.description,
                retrieved_context=context,
                task_type=task.task_type
            )
            
            if llm_response.success:
                return llm_response.content
            else:
                print(f"LLM生成エラー: {llm_response.error_message}")
                self.generation_stats["llm_errors"] += 1
                # エラー時はルールベースにフォールバック
                return self._generate_rule_based_response(task, context)
                
        except Exception as e:
            print(f"LLM呼び出しエラー: {e}")
            self.generation_stats["llm_errors"] += 1
            # エラー時はルールベースにフォールバック
            return self._generate_rule_based_response(task, context)
    
    def _generate_rule_based_response(self, task: Task, context: str) -> str:
        """ルールベース応答生成（フォールバック）"""
        base_response = f"タスク「{task.description}」を実行します。"
        
        if context:
            # コンテキストから関連情報を抽出
            keywords = self._extract_keywords(task.description)
            context_insights = self._extract_insights_from_context(context, keywords)
            
            if context_insights:
                base_response += f"\n\n関連情報に基づいて以下を実行します：\n{context_insights}"
            
            # 過去の成功パターンを参照
            if "成功" in context or "完了" in context:
                base_response += "\n\n過去の成功パターンを参考にして実行します。"
        
        return base_response
    
    def _calculate_response_quality(self, response_content: str, contexts: List[Dict[str, Any]]) -> float:
        """応答品質を計算"""
        try:
            base_score = 0.6
            
            # コンテキストの活用度
            if contexts:
                base_score += 0.2
                
                # 高品質なコンテキストの使用
                high_quality_contexts = [c for c in contexts if c.get("relevance_score", 0) > 0.8]
                if high_quality_contexts:
                    base_score += 0.1
            
            # 応答の詳細度
            if len(response_content) > 100:
                base_score += 0.1
            
            # 構造化された応答
            if "実行" in response_content and "参考" in response_content:
                base_score += 0.1
            
            return min(base_score, 1.0)
        except Exception as e:
            print(f"Error calculating response quality: {e}")
            return 0.5
    
    def _extract_keywords(self, text: str) -> List[str]:
        """テキストからキーワードを抽出"""
        try:
            # 重要なキーワードパターンを定義
            important_keywords = [
                "データベース", "接続", "エラー", "設定", "ファイル", "確認", "システム", "性能", 
                "監視", "サーバー", "ネットワーク", "アプリケーション", "ログ", "分析"
            ]
            
            keywords = []
            
            # 重要キーワードの完全一致をチェック
            for keyword in important_keywords:
                if keyword in text:
                    keywords.append(keyword)
            
            # 日本語と英語の単語を抽出
            japanese_chunks = re.findall(r'[ぁ-んァ-ヶ一-龠ー]+', text)
            english_words = re.findall(r'[a-zA-Z]+', text)
            
            # 日本語チャンクから意味のある単語を抽出（助詞で分割）
            for chunk in japanese_chunks:
                # 助詞で分割
                parts = re.split(r'[のをにはでがとからへより]', chunk)
                for part in parts:
                    if len(part) >= 2 and part not in keywords:
                        keywords.append(part)
            
            # 英語単語を追加
            keywords.extend([word for word in english_words if len(word) >= 2 and word not in keywords])
            
            # 重複を削除
            keywords = list(set(keywords))
            
            return keywords[:10]  # 上位10個のキーワードを返す
        except Exception as e:
            print(f"Error extracting keywords: {e}")
            return []
    
    def _extract_insights_from_context(self, context: str, keywords: List[str]) -> str:
        """コンテキストから洞察を抽出"""
        try:
            insights = []
            
            # キーワードに関連する文を抽出
            sentences = context.split('。')
            for sentence in sentences:
                if any(keyword in sentence for keyword in keywords):
                    insights.append(sentence.strip())
            
            return "\n".join(insights[:3])  # 最大3つの洞察
        except Exception as e:
            print(f"Error extracting insights from context: {e}")
            return ""
    
    def _calculate_context_relevance(self, context: str, task_query: str) -> float:
        """コンテキストの関連度を計算"""
        try:
            context_keywords = set(self._extract_keywords(context))
            query_keywords = set(self._extract_keywords(task_query))
            
            if not context_keywords or not query_keywords:
                return 0.0
            
            intersection = context_keywords.intersection(query_keywords)
            union = context_keywords.union(query_keywords)
            
            jaccard_similarity = len(intersection) / len(union)
            return jaccard_similarity
        except Exception as e:
            print(f"Error calculating context relevance: {e}")
            return 0.0
    
    def _extract_execution_pattern(self, task: Task, response: Response) -> Optional[Dict[str, Any]]:
        """実行パターンを抽出"""
        try:
            if response.quality_score < 0.8:
                return None
            
            pattern = {
                "pattern_id": f"pattern_{task.id}_{int(datetime.now().timestamp())}",
                "task_type": task.task_type,
                "success_conditions": [
                    "正常実行",
                    f"品質スコア: {response.quality_score:.2f}"
                ],
                "failure_conditions": [],
                "confidence_score": response.quality_score
            }
            
            return pattern
        except Exception as e:
            print(f"Error extracting execution pattern: {e}")
            return None
    
    def _extract_error_info(self, task: Task, response: Response) -> Optional[Dict[str, Any]]:
        """エラー情報を抽出"""
        try:
            if response.quality_score >= 0.5:
                return None
            
            error_info = {
                "error_message": f"タスク実行品質低下: {task.description}",
                "solution": "タスクの詳細確認と再実行を推奨",
                "error_type": "quality_degradation",
                "frequency": 1
            }
            
            return error_info
        except Exception as e:
            print(f"Error extracting error info: {e}")
            return None
    
    def get_system_stats(self) -> Dict[str, Any]:
        """システム統計を取得"""
        try:
            knowledge_stats = self.knowledge_base.get_knowledge_stats()
            
            context_usage_rate = 0.0
            if self.generation_stats["total_requests"] > 0:
                context_usage_rate = (
                    self.generation_stats["successful_generations"] / 
                    self.generation_stats["total_requests"]
                )
            
            stats = {
                "generation_stats": self.generation_stats,
                "context_usage_rate": context_usage_rate,
                "knowledge_base_stats": knowledge_stats,
                "context_window_size": self.context_window_size,
                "llm_integration": {
                    "claude_code_available": CLAUDE_CODE_AVAILABLE,
                    "claude_code_enabled": self.use_claude_code,
                    "llm_backend": "claude-code" if self.use_claude_code else "rule-based"
                }
            }
            
            # Claude Code統計を追加（利用可能な場合）
            if self.use_claude_code and self.claude_client:
                try:
                    llm_stats = self.claude_client.get_usage_stats()
                    stats["llm_integration"]["llm_stats"] = llm_stats
                except Exception as e:
                    stats["llm_integration"]["llm_stats_error"] = str(e)
            
            return stats
        except Exception as e:
            print(f"Error getting system stats: {e}")
            return {}