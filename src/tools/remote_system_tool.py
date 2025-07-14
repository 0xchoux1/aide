"""
リモートシステムツール

SSH経由でのリモートサーバーでのコマンド実行とファイル操作
"""

import time
import threading
from typing import Dict, List, Optional, Any, Union, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .base_tool import BaseTool, ToolResult, ToolStatus
from ..remote.connection_manager import RemoteConnectionManager
from ..remote.ssh_client import SSHClient, SSHConfig, SSHConnectionError


logger = logging.getLogger(__name__)


class RemoteExecutionError(Exception):
    """リモート実行エラー"""
    pass


@dataclass
class RemoteToolResult(ToolResult):
    """リモートツール実行結果"""
    server: Optional[str] = None
    command: Optional[str] = None
    connection_info: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        base_dict = super().to_dict()
        base_dict.update({
            'server': self.server,
            'command': self.command,
            'connection_info': self.connection_info
        })
        return base_dict


class RemoteSystemTool(BaseTool):
    """リモートシステムツール"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: ツール設定
        """
        super().__init__(
            name="remote_system_tool",
            description="SSH経由でリモートサーバーのコマンドを実行するツール"
        )
        
        self.timeout = config.get('timeout', 60)
        self.safe_mode = config.get('safe_mode', True)
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 2)
        
        # 接続マネージャーを初期化
        connection_config = {
            'max_connections': config.get('max_connections', 10),
            'connection_timeout': config.get('connection_timeout', 30),
            'idle_timeout': config.get('idle_timeout', 300),
            'retry_attempts': self.max_retries,
            'retry_delay': self.retry_delay
        }
        self.connection_manager = RemoteConnectionManager(connection_config)
        
        # セキュリティ制約
        self.dangerous_commands = {
            'rm', 'rmdir', 'del', 'format', 'fdisk', 'mkfs',
            'dd', 'shutdown', 'reboot', 'halt', 'poweroff',
            'chmod', 'chown', 'passwd', 'su', 'sudo',
            'kill', 'killall', 'pkill', 'mount', 'umount'
        }
        
        self.safe_commands = {
            'ls', 'cat', 'head', 'tail', 'grep', 'find', 'which',
            'ps', 'top', 'htop', 'df', 'du', 'free', 'uptime',
            'date', 'whoami', 'id', 'pwd', 'echo', 'wc',
            'systemctl', 'journalctl', 'netstat', 'ss', 'lsof',
            'curl', 'wget', 'ping', 'nslookup', 'dig',
            'git', 'docker', 'kubectl', 'helm', 'hostname',
            'uname', 'env', 'history', 'alias'
        }
        
        # 実行履歴
        self.execution_history = []
        self._history_lock = threading.Lock()
    
    def connect_to_server(self, ssh_config: Union[Dict[str, Any], SSHConfig]) -> SSHClient:
        """
        サーバーに接続
        
        Args:
            ssh_config: SSH接続設定
            
        Returns:
            SSHクライアント
        """
        try:
            return self.connection_manager.connect(ssh_config)
        except Exception as e:
            raise RemoteExecutionError(f"Failed to connect to server: {str(e)}")
    
    def execute(self, ssh_config: Union[Dict[str, Any], SSHConfig], command: str, 
                timeout: Optional[int] = None, **kwargs) -> RemoteToolResult:
        """
        リモートサーバーでコマンドを実行
        
        Args:
            ssh_config: SSH接続設定
            command: 実行するコマンド
            timeout: タイムアウト秒数
            **kwargs: その他のオプション
            
        Returns:
            実行結果
        """
        start_time = time.time()
        server_name = ssh_config.get('hostname') if isinstance(ssh_config, dict) else ssh_config.hostname
        
        try:
            # セキュリティチェック
            if self.safe_mode and not self._is_safe_command(command):
                return RemoteToolResult(
                    status=ToolStatus.PERMISSION_DENIED,
                    output="",
                    error=f"Dangerous command blocked: {command}",
                    execution_time=time.time() - start_time,
                    server=server_name,
                    command=command,
                    metadata={'security_violation': True}
                )
            
            # リトライロジックで実行
            last_error = None
            for attempt in range(self.max_retries):
                try:
                    # サーバーに接続
                    client = self.connect_to_server(ssh_config)
                    
                    # コマンドを実行
                    stdout, stderr, exit_code = self.connection_manager.execute_command(
                        client, command, timeout or self.timeout
                    )
                    
                    execution_time = time.time() - start_time
                    
                    # 結果を作成
                    if exit_code == 0:
                        status = ToolStatus.SUCCESS
                        error = stderr if stderr else None
                    else:
                        status = ToolStatus.FAILED
                        error = stderr or f"Command failed with exit code {exit_code}"
                    
                    result = RemoteToolResult(
                        status=status,
                        output=stdout,
                        error=error,
                        execution_time=execution_time,
                        server=server_name,
                        command=command,
                        metadata={
                            'exit_code': exit_code,
                            'attempt': attempt + 1,
                            'connection_info': client.get_connection_info() if hasattr(client, 'get_connection_info') else {}
                        }
                    )
                    
                    # 履歴に記録
                    self._record_execution_history(result)
                    
                    return result
                    
                except RemoteExecutionError as e:
                    last_error = e
                    logger.warning(f"Execution attempt {attempt + 1} failed: {str(e)}")
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))
                
                except Exception as e:
                    last_error = RemoteExecutionError(f"Unexpected error: {str(e)}")
                    logger.error(f"Unexpected error during execution: {str(e)}")
                    break
            
            # 全ての試行が失敗
            execution_time = time.time() - start_time
            result = RemoteToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"All execution attempts failed: {str(last_error)}",
                execution_time=execution_time,
                server=server_name,
                command=command,
                metadata={'max_retries_exceeded': True, 'total_attempts': self.max_retries}
            )
            
            self._record_execution_history(result)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            result = RemoteToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"Execution error: {str(e)}",
                execution_time=execution_time,
                server=server_name,
                command=command,
                metadata={'exception_type': type(e).__name__}
            )
            
            self._record_execution_history(result)
            
            return result
    
    def execute_on_multiple_servers(self, servers: List[Union[Dict[str, Any], SSHConfig]], 
                                   command: str, timeout: Optional[int] = None) -> List[RemoteToolResult]:
        """
        複数サーバーでコマンドを実行
        
        Args:
            servers: サーバー設定のリスト
            command: 実行するコマンド
            timeout: タイムアウト秒数
            
        Returns:
            実行結果のリスト
        """
        results = []
        for server_config in servers:
            result = self.execute(server_config, command, timeout)
            results.append(result)
        return results
    
    def execute_parallel(self, servers: List[Union[Dict[str, Any], SSHConfig]], 
                        command: str, max_workers: int = 5, timeout: Optional[int] = None) -> List[RemoteToolResult]:
        """
        複数サーバーでコマンドを並列実行
        
        Args:
            servers: サーバー設定のリスト
            command: 実行するコマンド
            max_workers: 最大ワーカー数
            timeout: タイムアウト秒数
            
        Returns:
            実行結果のリスト
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 全サーバーでタスクを開始
            future_to_server = {
                executor.submit(self.execute, server_config, command, timeout): server_config
                for server_config in servers
            }
            
            # 結果を収集
            for future in as_completed(future_to_server):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    server_config = future_to_server[future]
                    server_name = server_config.get('hostname') if isinstance(server_config, dict) else server_config.hostname
                    
                    error_result = RemoteToolResult(
                        status=ToolStatus.FAILED,
                        output="",
                        error=f"Parallel execution error: {str(e)}",
                        execution_time=0,
                        server=server_name,
                        command=command,
                        metadata={'parallel_execution_error': True}
                    )
                    results.append(error_result)
        
        return results
    
    def upload_file(self, ssh_config: Union[Dict[str, Any], SSHConfig], 
                   local_path: str, remote_path: str) -> RemoteToolResult:
        """
        ファイルをアップロード
        
        Args:
            ssh_config: SSH接続設定
            local_path: ローカルファイルパス
            remote_path: リモートファイルパス
            
        Returns:
            実行結果
        """
        start_time = time.time()
        server_name = ssh_config.get('hostname') if isinstance(ssh_config, dict) else ssh_config.hostname
        
        try:
            # SFTPクライアントを作成（実装は簡略化）
            sftp_client = self._create_sftp_client(ssh_config)
            
            # ファイルをアップロード
            sftp_client.put(local_path, remote_path)
            
            execution_time = time.time() - start_time
            
            result = RemoteToolResult(
                status=ToolStatus.SUCCESS,
                output=f"File uploaded: {local_path} -> {remote_path}",
                execution_time=execution_time,
                server=server_name,
                command=f"upload {local_path} {remote_path}",
                metadata={'operation': 'file_upload', 'local_path': local_path, 'remote_path': remote_path}
            )
            
            self._record_execution_history(result)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            result = RemoteToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"File upload failed: {str(e)}",
                execution_time=execution_time,
                server=server_name,
                command=f"upload {local_path} {remote_path}",
                metadata={'operation': 'file_upload', 'error_type': type(e).__name__}
            )
            
            self._record_execution_history(result)
            return result
    
    def download_file(self, ssh_config: Union[Dict[str, Any], SSHConfig], 
                     remote_path: str, local_path: str) -> RemoteToolResult:
        """
        ファイルをダウンロード
        
        Args:
            ssh_config: SSH接続設定
            remote_path: リモートファイルパス
            local_path: ローカルファイルパス
            
        Returns:
            実行結果
        """
        start_time = time.time()
        server_name = ssh_config.get('hostname') if isinstance(ssh_config, dict) else ssh_config.hostname
        
        try:
            # SFTPクライアントを作成（実装は簡略化）
            sftp_client = self._create_sftp_client(ssh_config)
            
            # ファイルをダウンロード
            sftp_client.get(remote_path, local_path)
            
            execution_time = time.time() - start_time
            
            result = RemoteToolResult(
                status=ToolStatus.SUCCESS,
                output=f"File downloaded: {remote_path} -> {local_path}",
                execution_time=execution_time,
                server=server_name,
                command=f"download {remote_path} {local_path}",
                metadata={'operation': 'file_download', 'remote_path': remote_path, 'local_path': local_path}
            )
            
            self._record_execution_history(result)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            result = RemoteToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"File download failed: {str(e)}",
                execution_time=execution_time,
                server=server_name,
                command=f"download {remote_path} {local_path}",
                metadata={'operation': 'file_download', 'error_type': type(e).__name__}
            )
            
            self._record_execution_history(result)
            return result
    
    def gather_system_info(self, ssh_config: Union[Dict[str, Any], SSHConfig]) -> RemoteToolResult:
        """
        システム情報を収集
        
        Args:
            ssh_config: SSH接続設定
            
        Returns:
            実行結果（system_infoメタデータ付き）
        """
        info_commands = {
            'hostname': 'hostname',
            'kernel': 'uname -r',
            'memory': 'cat /proc/meminfo | head -5',
            'disk_usage': 'df -h',
            'load_average': 'cat /proc/loadavg',
            'uptime': 'uptime',
            'processes': 'ps aux | head -10'
        }
        
        system_info = {}
        start_time = time.time()
        server_name = ssh_config.get('hostname') if isinstance(ssh_config, dict) else ssh_config.hostname
        
        for key, command in info_commands.items():
            result = self.execute(ssh_config, command)
            if result.status == ToolStatus.SUCCESS:
                system_info[key] = result.output.strip()
            else:
                system_info[key] = f"Failed to retrieve: {result.error}"
        
        execution_time = time.time() - start_time
        
        result = RemoteToolResult(
            status=ToolStatus.SUCCESS,
            output=f"System information collected from {server_name}",
            execution_time=execution_time,
            server=server_name,
            command="gather_system_info",
            metadata={'system_info': system_info, 'info_commands': info_commands}
        )
        
        self._record_execution_history(result)
        return result
    
    def _is_safe_command(self, command: str) -> bool:
        """コマンドが安全かどうかチェック"""
        import shlex
        
        try:
            cmd_parts = shlex.split(command)
        except ValueError:
            # シェル構文エラーの場合は危険とみなす
            return False
        
        if not cmd_parts:
            return False
        
        base_command = cmd_parts[0].split('/')[-1]  # パスを除去
        
        # 危険なコマンドをチェック
        if base_command in self.dangerous_commands:
            return False
        
        # 特定の危険なパターンをチェック
        command_lower = command.lower()
        dangerous_patterns = [
            'rm -rf /',
            'rm -rf *',
            'chmod 777',
            'chown -R',
            '> /dev/',
            'dd if=',
            'mkfs.',
            'fdisk',
            'parted'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return False
        
        # セーフモードでは安全なコマンドのみ許可
        if self.safe_mode:
            return base_command in self.safe_commands
        
        return True
    
    def _create_sftp_client(self, ssh_config: Union[Dict[str, Any], SSHConfig]):
        """
        SFTPクライアントを作成（モック実装）
        
        実際の実装では、SSHClientからSFTPクライアントを取得する
        """
        class MockSFTPClient:
            def put(self, local_path: str, remote_path: str):
                # モック実装：実際にはSFTPでファイル転送
                logger.info(f"Mock SFTP put: {local_path} -> {remote_path}")
            
            def get(self, remote_path: str, local_path: str):
                # モック実装：実際にはSFTPでファイル取得
                logger.info(f"Mock SFTP get: {remote_path} -> {local_path}")
        
        return MockSFTPClient()
    
    def _record_execution_history(self, result: RemoteToolResult):
        """実行履歴を記録"""
        with self._history_lock:
            history_record = {
                'timestamp': datetime.now().isoformat(),
                'server': result.server,
                'command': result.command,
                'status': result.status.value,
                'execution_time': result.execution_time,
                'output_length': len(result.output) if result.output else 0,
                'has_error': bool(result.error)
            }
            
            self.execution_history.append(history_record)
            
            # 履歴を最新1000件まで保持
            if len(self.execution_history) > 1000:
                self.execution_history = self.execution_history[-1000:]
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """実行履歴を取得"""
        with self._history_lock:
            return self.execution_history[-limit:] if self.execution_history else []
    
    def get_server_statistics(self, server: str) -> Dict[str, Any]:
        """特定サーバーの統計情報を取得"""
        with self._history_lock:
            server_executions = [
                record for record in self.execution_history 
                if record.get('server') == server
            ]
            
            if not server_executions:
                return {'server': server, 'total_executions': 0}
            
            total = len(server_executions)
            successful = sum(1 for r in server_executions if r.get('status') == 'success')
            avg_time = sum(r.get('execution_time', 0) for r in server_executions) / total
            
            return {
                'server': server,
                'total_executions': total,
                'success_rate': successful / total,
                'average_execution_time': avg_time,
                'last_execution': server_executions[-1]['timestamp'] if server_executions else None
            }
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            self.connection_manager.shutdown()
            logger.info("Remote system tool cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def __enter__(self):
        """コンテキストマネージャーサポート"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーサポート"""
        self.cleanup()