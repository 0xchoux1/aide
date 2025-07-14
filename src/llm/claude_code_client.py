import subprocess
import tempfile
import os
import time
import json
import re
from typing import Dict, Any, Optional, List
from .llm_interface import LLMInterface, LLMResponse


class ClaudeCodeClient(LLMInterface):
    """Claude CodeをLLMバックエンドとして利用するクライアント"""
    
    def __init__(self, claude_command: str = None, 
                 timeout: int = None,
                 working_dir: Optional[str] = None,
                 max_retries: int = None,
                 retry_delay: float = None,
                 **kwargs):
        super().__init__(model_name="claude-code", **kwargs)
        
        # 環境変数から設定を読み込み（引数で上書き可能）
        self.claude_command = claude_command or os.getenv('AIDE_CLAUDE_COMMAND', 'claude')
        self.timeout = timeout or int(os.getenv('AIDE_CLAUDE_TIMEOUT', '120'))
        self.working_dir = working_dir or os.getcwd()
        self.session_count = 0
        self.max_retries = max_retries or int(os.getenv('AIDE_CLAUDE_MAX_RETRIES', '3'))
        self.retry_delay = retry_delay or float(os.getenv('AIDE_CLAUDE_RETRY_DELAY', '2.0'))
        self.consecutive_failures = 0  # 連続失敗回数
        self.last_successful_call = time.time()
        
        # Claude Codeの可用性確認
        self._verify_claude_availability()
    
    def _verify_claude_availability(self):
        """Claude Codeが利用可能かチェック"""
        try:
            result = subprocess.run(
                [self.claude_command, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"Claude Code not available: {result.stderr}")
        except FileNotFoundError:
            raise RuntimeError("Claude Code command not found. Please ensure it's installed and in PATH.")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude Code command timed out during availability check.")
    
    def generate_response(self, prompt: str, context: Optional[str] = None, 
                         max_tokens: Optional[int] = None, 
                         temperature: float = 0.7,
                         **kwargs) -> LLMResponse:
        """
        Claude Codeを使用してテキスト生成（リトライ機能付き）
        """
        start_time = time.time()
        last_error = None
        
        # リトライループ
        for attempt in range(self.max_retries + 1):
            try:
                # プロンプトを構築
                full_prompt = self._build_prompt(prompt, context, **kwargs)
                
                # Claude Codeを実行（タイムアウト対策）
                result = self._execute_claude_with_retry(full_prompt, attempt)
                
                # 応答をパース
                response_content = self._parse_response(result.stdout)
                
                # 成功時の統計更新
                execution_time = time.time() - start_time
                self._update_stats(tokens_used=len(response_content.split()), is_error=False)
                self.consecutive_failures = 0  # 失敗カウンターリセット
                self.last_successful_call = time.time()
                
                return LLMResponse(
                    content=response_content,
                    metadata={
                        'execution_time': execution_time,
                        'prompt_length': len(full_prompt),
                        'response_length': len(response_content),
                        'session_id': self.session_count,
                        'retry_attempt': attempt,
                        'consecutive_failures_before': self.consecutive_failures
                    },
                    usage_stats={
                        'estimated_tokens': len(full_prompt.split()) + len(response_content.split()),
                        'execution_time': execution_time
                    },
                    success=True
                )
                
            except Exception as e:
                last_error = e
                self.consecutive_failures += 1
                
                # 最後の試行でない場合はリトライ待機
                if attempt < self.max_retries:
                    retry_delay = self._calculate_retry_delay(attempt)
                    print(f"Claude Code呼び出し失敗 (試行 {attempt + 1}/{self.max_retries + 1}): {str(e)}")
                    print(f"{retry_delay:.1f}秒後にリトライします...")
                    time.sleep(retry_delay)
                    continue
        
        # 全ての試行が失敗した場合
        execution_time = time.time() - start_time
        self._update_stats(is_error=True)
        
        return LLMResponse(
            content="",
            success=False,
            error_message=f"全ての試行が失敗: {str(last_error)}",
            metadata={
                'execution_time': execution_time,
                'error_type': type(last_error).__name__ if last_error else 'Unknown',
                'total_attempts': self.max_retries + 1,
                'consecutive_failures': self.consecutive_failures
            }
        )
    
    def generate_structured_response(self, prompt: str, 
                                   output_format: Dict[str, str],
                                   context: Optional[str] = None,
                                   **kwargs) -> LLMResponse:
        """
        構造化された応答を生成
        """
        # 構造化出力のためのプロンプトを作成
        format_description = self._format_structure_prompt(output_format)
        
        structured_prompt = f"""
{prompt}

出力形式要求:
{format_description}

応答は必ず以下のJSON形式で返してください：
```json
{{
{', '.join([f'"{key}": "{description}"' for key, description in output_format.items()])}
}}
```

重要: 応答はJSONコードブロック内に含めてください。
"""
        
        response = self.generate_response(structured_prompt, context, **kwargs)
        
        if response.success:
            # JSON応答を抽出してパース
            try:
                parsed_structure = self._extract_json_from_response(response.content)
                response.metadata['structured_output'] = parsed_structure
                response.metadata['format_requested'] = output_format
            except Exception as e:
                response.metadata['structure_parse_error'] = str(e)
        
        return response
    
    def _build_prompt(self, prompt: str, context: Optional[str] = None, **kwargs) -> str:
        """プロンプトを構築"""
        parts = []
        
        # システムメッセージ（コンテキストがある場合）
        if context:
            parts.append(f"参考情報:\n{context}\n")
        
        # メインプロンプト
        parts.append(f"タスク:\n{prompt}")
        
        # 追加の指示があれば含める
        if 'instructions' in kwargs:
            parts.append(f"\n指示:\n{kwargs['instructions']}")
        
        # 応答形式の指定
        if 'response_format' in kwargs:
            parts.append(f"\n応答形式:\n{kwargs['response_format']}")
        
        return "\n\n".join(parts)
    
    def _execute_claude_with_retry(self, prompt: str, attempt: int) -> subprocess.CompletedProcess:
        """リトライ機能付きClaude Code実行"""
        return self._execute_claude(prompt)
    
    def _execute_claude(self, prompt: str) -> subprocess.CompletedProcess:
        """Claude Codeを実行"""
        self.session_count += 1
        
        # 一時ファイルにプロンプトを保存
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(prompt)
            prompt_file = f.name
        
        try:
            # Claude Codeを実行
            result = subprocess.run(
                [self.claude_command, f"@{prompt_file}"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.working_dir
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Claude Code execution failed: {result.stderr}")
            
            return result
            
        finally:
            # 一時ファイルを削除
            try:
                os.unlink(prompt_file)
            except OSError:
                pass
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """リトライ遅延時間を計算（指数バックオフ）"""
        base_delay = self.retry_delay
        # 指数バックオフ: base_delay * (2 ^ attempt) + ランダム性
        import random
        exponential_delay = base_delay * (2 ** attempt)
        # 最大30秒まで、ランダム性を追加
        jitter = random.uniform(0.1, 0.5)
        return min(30.0, exponential_delay + jitter)
    
    def is_healthy(self) -> bool:
        """Claude Codeクライアントの健康状態を確認"""
        # 連続失敗が5回以下、かつ最後の成功呼び出しが10分以内
        return (self.consecutive_failures < 5 and 
                (time.time() - self.last_successful_call) < 600)
    
    def get_health_status(self) -> Dict[str, Any]:
        """ヘルスステータス詳細を取得"""
        time_since_success = time.time() - self.last_successful_call
        return {
            'is_healthy': self.is_healthy(),
            'consecutive_failures': self.consecutive_failures,
            'time_since_last_success_seconds': time_since_success,
            'session_count': self.session_count,
            'timeout_configured': self.timeout,
            'max_retries_configured': self.max_retries
        }
    
    def _parse_response(self, raw_output: str) -> str:
        """Claude Codeの生出力から応答を抽出"""
        # Claude Codeの出力から実際の応答部分を抽出
        # (出力にはシステムメッセージなどが含まれる可能性がある)
        
        lines = raw_output.strip().split('\n')
        
        # 空行や短すぎる行を除外
        content_lines = [line for line in lines if line.strip() and len(line.strip()) > 10]
        
        if not content_lines:
            return raw_output.strip()
        
        return '\n'.join(content_lines)
    
    def _format_structure_prompt(self, output_format: Dict[str, str]) -> str:
        """構造化出力形式をプロンプト用にフォーマット"""
        format_lines = []
        for key, description in output_format.items():
            format_lines.append(f"- {key}: {description}")
        return '\n'.join(format_lines)
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """応答からJSONを抽出"""
        # JSONコードブロックを探す
        json_pattern = r'```json\s*\n(.*?)\n```'
        match = re.search(json_pattern, response, re.DOTALL)
        
        if match:
            json_content = match.group(1)
            return json.loads(json_content)
        
        # コードブロックがない場合、JSON形式の文字列を探す
        json_pattern = r'\{.*?\}'
        match = re.search(json_pattern, response, re.DOTALL)
        
        if match:
            json_content = match.group(0)
            return json.loads(json_content)
        
        raise ValueError("No valid JSON found in response")
    
    def test_connection(self) -> LLMResponse:
        """接続テスト"""
        test_prompt = "「Hello, AIDE!」と応答してください。"
        return self.generate_response(test_prompt)
    
    def generate_rag_response(self, task_description: str, 
                            retrieved_context: str,
                            task_type: Optional[str] = None) -> LLMResponse:
        """RAG用の特化した応答生成"""
        
        rag_prompt = f"""
あなたはAIDE（自律学習型AIアシスタント）のインフラエンジニアリング支援システムです。

タスクタイプ: {task_type or '不明'}
タスク内容: {task_description}

以下の参考情報を活用して、このタスクを実行するための具体的で実用的な応答を生成してください：

参考情報:
{retrieved_context}

応答要件:
1. 実行可能な具体的な手順を含める
2. 参考情報を適切に活用する
3. 潜在的な問題点と対策を含める
4. 簡潔で分かりやすい説明にする

応答:
"""
        
        return self.generate_response(
            rag_prompt,
            instructions="インフラエンジニアリングの専門知識を活用し、実用的で安全な手順を提供してください。"
        )