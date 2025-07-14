"""
RemoteSystemToolのユニットテスト

リモートサーバーでのコマンド実行、ファイル操作、セキュリティ制約のテスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from datetime import datetime
from typing import Dict, Any

# テスト対象のインポート（まだ実装されていないのでパスする）
try:
    from src.tools.remote_system_tool import (
        RemoteSystemTool,
        RemoteToolResult,
        RemoteExecutionError
    )
    from src.remote.connection_manager import RemoteConnectionManager
    from src.remote.ssh_client import SSHClient, SSHConfig
    from src.tools.base_tool import ToolStatus
except ImportError:
    # 実装前なのでモックで代替
    RemoteSystemTool = None
    RemoteToolResult = None
    RemoteExecutionError = Exception
    RemoteConnectionManager = None
    SSHClient = None
    SSHConfig = None
    ToolStatus = None


class TestRemoteSystemTool:
    """RemoteSystemToolのテストクラス"""
    
    @pytest.fixture
    def ssh_config(self):
        """SSH接続設定"""
        return {
            'hostname': 'test-server.example.com',
            'port': 22,
            'username': 'testuser',
            'key_filename': '/home/user/.ssh/id_rsa',
            'timeout': 30
        }
    
    @pytest.fixture
    def tool_config(self):
        """ツール設定"""
        return {
            'timeout': 60,
            'safe_mode': True,
            'max_retries': 3,
            'retry_delay': 1
        }
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_remote_tool_initialization(self, tool_config):
        """リモートツールの初期化テスト"""
        tool = RemoteSystemTool(tool_config)
        
        assert tool.timeout == 60
        assert tool.safe_mode is True
        assert tool.max_retries == 3
        assert tool.retry_delay == 1
        assert tool.connection_manager is not None
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_connect_to_server(self, tool_config, ssh_config):
        """サーバーへの接続テスト"""
        tool = RemoteSystemTool(tool_config)
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect:
            mock_client = Mock()
            mock_client.is_connected = True
            mock_connect.return_value = mock_client
            
            # サーバーに接続
            client = tool.connect_to_server(ssh_config)
            
            assert client is not None
            assert client == mock_client
            mock_connect.assert_called_once()
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_execute_safe_command(self, tool_config, ssh_config):
        """安全なコマンドの実行テスト"""
        tool = RemoteSystemTool(tool_config)
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect, \
             patch.object(tool.connection_manager, 'execute_command') as mock_execute:
            
            mock_client = Mock()
            mock_connect.return_value = mock_client
            mock_execute.return_value = ("test output", "", 0)
            
            # 安全なコマンドを実行
            result = tool.execute(ssh_config, "ls -la")
            
            assert result.status == ToolStatus.SUCCESS
            assert result.output == "test output"
            assert result.error is None
            mock_execute.assert_called_once_with(mock_client, "ls -la", 60)
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_block_dangerous_command(self, tool_config, ssh_config):
        """危険なコマンドのブロックテスト"""
        tool = RemoteSystemTool(tool_config)
        
        # 危険なコマンドを実行しようとする
        result = tool.execute(ssh_config, "rm -rf /")
        
        assert result.status == ToolStatus.PERMISSION_DENIED
        assert "dangerous command" in result.error.lower()
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_command_with_custom_timeout(self, tool_config, ssh_config):
        """カスタムタイムアウトでのコマンド実行テスト"""
        tool = RemoteSystemTool(tool_config)
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect, \
             patch.object(tool.connection_manager, 'execute_command') as mock_execute:
            
            mock_client = Mock()
            mock_connect.return_value = mock_client
            mock_execute.return_value = ("output", "", 0)
            
            # カスタムタイムアウトでコマンドを実行
            result = tool.execute(ssh_config, "ps aux", timeout=120)
            
            assert result.status == ToolStatus.SUCCESS
            mock_execute.assert_called_once_with(mock_client, "ps aux", 120)
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_command_execution_failure(self, tool_config, ssh_config):
        """コマンド実行失敗のテスト"""
        tool = RemoteSystemTool(tool_config)
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect, \
             patch.object(tool.connection_manager, 'execute_command') as mock_execute:
            
            mock_client = Mock()
            mock_connect.return_value = mock_client
            mock_execute.return_value = ("", "Command not found", 127)
            
            # 失敗するコマンドを実行（安全なコマンドを使用）
            result = tool.execute(ssh_config, "ls /nonexistent_directory")
            
            assert result.status == ToolStatus.FAILED
            assert result.error == "Command not found"
            assert "ls /nonexistent_directory" in result.metadata['command']
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_connection_retry_on_failure(self, tool_config, ssh_config):
        """接続失敗時のリトライテスト"""
        tool_config['retry_delay'] = 0.1  # テスト高速化
        tool = RemoteSystemTool(tool_config)
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect, \
             patch.object(tool.connection_manager, 'execute_command') as mock_execute:
            
            # 最初の2回は接続失敗、3回目で成功
            mock_connect.side_effect = [
                RemoteExecutionError("Connection failed"),
                RemoteExecutionError("Connection failed"),
                Mock()
            ]
            mock_execute.return_value = ("success", "", 0)
            
            # リトライして最終的に成功することを確認
            result = tool.execute(ssh_config, "echo test")
            
            assert result.status == ToolStatus.SUCCESS
            assert mock_connect.call_count == 3
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_multiple_servers_execution(self, tool_config):
        """複数サーバーでのコマンド実行テスト"""
        tool = RemoteSystemTool(tool_config)
        
        servers = [
            {'hostname': 'server1.example.com', 'username': 'user1'},
            {'hostname': 'server2.example.com', 'username': 'user2'},
            {'hostname': 'server3.example.com', 'username': 'user3'}
        ]
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect, \
             patch.object(tool.connection_manager, 'execute_command') as mock_execute:
            
            # 各サーバーで異なる応答を設定
            mock_clients = [Mock() for _ in servers]
            mock_connect.side_effect = mock_clients
            mock_execute.side_effect = [
                (f"output from {server['hostname']}", "", 0) for server in servers
            ]
            
            # 複数サーバーでコマンドを実行
            results = tool.execute_on_multiple_servers(servers, "hostname")
            
            assert len(results) == 3
            for i, result in enumerate(results):
                assert result.status == ToolStatus.SUCCESS
                assert f"server{i+1}.example.com" in result.output
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_file_transfer_operations(self, tool_config, ssh_config):
        """ファイル転送操作のテスト"""
        tool = RemoteSystemTool(tool_config)
        
        with patch.object(tool, '_create_sftp_client') as mock_sftp:
            mock_sftp_client = Mock()
            mock_sftp.return_value = mock_sftp_client
            
            # ファイルアップロード
            result = tool.upload_file(
                ssh_config, 
                "/local/path/file.txt", 
                "/remote/path/file.txt"
            )
            
            assert result.status == ToolStatus.SUCCESS
            mock_sftp_client.put.assert_called_once_with(
                "/local/path/file.txt", 
                "/remote/path/file.txt"
            )
            
            # ファイルダウンロード
            result = tool.download_file(
                ssh_config, 
                "/remote/path/file.txt", 
                "/local/path/downloaded.txt"
            )
            
            assert result.status == ToolStatus.SUCCESS
            mock_sftp_client.get.assert_called_once_with(
                "/remote/path/file.txt", 
                "/local/path/downloaded.txt"
            )
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_system_information_gathering(self, tool_config, ssh_config):
        """システム情報収集のテスト"""
        tool = RemoteSystemTool(tool_config)
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect, \
             patch.object(tool.connection_manager, 'execute_command') as mock_execute:
            
            mock_client = Mock()
            mock_connect.return_value = mock_client
            
            # システム情報コマンドの応答を設定
            mock_execute.side_effect = [
                ("test-server", "", 0),  # hostname
                ("Linux test-server 5.4.0", "", 0),  # uname
                ("MemTotal: 8GB", "", 0),  # memory info
                ("Filesystem /dev/sda1 50% /", "", 0),  # disk usage
                ("load average: 0.5 0.3 0.2", "", 0)  # load average
            ]
            
            # システム情報を収集
            result = tool.gather_system_info(ssh_config)
            
            assert result.status == ToolStatus.SUCCESS
            assert 'system_info' in result.metadata
            system_info = result.metadata['system_info']
            assert 'hostname' in system_info
            assert 'kernel' in system_info
            assert 'memory' in system_info
            assert 'disk_usage' in system_info
            assert 'load_average' in system_info
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_security_constraints(self, tool_config, ssh_config):
        """セキュリティ制約のテスト"""
        tool = RemoteSystemTool(tool_config)
        
        # 危険なコマンドのリスト
        dangerous_commands = [
            "rm -rf /",
            "chmod 777 /etc/passwd",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
            "shutdown -h now",
            "sudo rm /etc/shadow"
        ]
        
        for command in dangerous_commands:
            result = tool.execute(ssh_config, command)
            assert result.status == ToolStatus.PERMISSION_DENIED
            assert "dangerous" in result.error.lower() or "not allowed" in result.error.lower()
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_safe_mode_toggle(self, tool_config, ssh_config):
        """セーフモードの切り替えテスト"""
        # セーフモード有効
        tool_safe = RemoteSystemTool({**tool_config, 'safe_mode': True})
        result = tool_safe.execute(ssh_config, "rm /tmp/testfile")
        assert result.status == ToolStatus.PERMISSION_DENIED
        
        # セーフモード無効
        tool_unsafe = RemoteSystemTool({**tool_config, 'safe_mode': False})
        with patch.object(tool_unsafe.connection_manager, 'connect') as mock_connect, \
             patch.object(tool_unsafe.connection_manager, 'execute_command') as mock_execute:
            
            mock_client = Mock()
            mock_connect.return_value = mock_client
            mock_execute.return_value = ("file removed", "", 0)
            
            result = tool_unsafe.execute(ssh_config, "rm /tmp/testfile")
            assert result.status == ToolStatus.SUCCESS
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_command_history_tracking(self, tool_config, ssh_config):
        """コマンド履歴追跡のテスト"""
        tool = RemoteSystemTool(tool_config)
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect, \
             patch.object(tool.connection_manager, 'execute_command') as mock_execute:
            
            mock_client = Mock()
            mock_connect.return_value = mock_client
            mock_execute.return_value = ("output", "", 0)
            
            # 複数のコマンドを実行
            commands = ["ls", "pwd", "whoami", "date"]
            for command in commands:
                tool.execute(ssh_config, command)
            
            # 実行履歴を確認
            history = tool.get_execution_history()
            assert len(history) == len(commands)
            
            for i, record in enumerate(history):
                assert record['command'] == commands[i]
                assert record['server'] == ssh_config['hostname']
                assert 'timestamp' in record
                assert 'execution_time' in record
    
    @pytest.mark.skipif(RemoteSystemTool is None, reason="RemoteSystemTool not implemented yet")
    def test_concurrent_command_execution(self, tool_config):
        """並列コマンド実行のテスト"""
        tool = RemoteSystemTool(tool_config)
        
        servers = [
            {'hostname': f'server{i}.example.com', 'username': 'testuser'} 
            for i in range(1, 6)
        ]
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect, \
             patch.object(tool.connection_manager, 'execute_command') as mock_execute:
            
            mock_clients = [Mock() for _ in servers]
            mock_connect.side_effect = mock_clients
            mock_execute.side_effect = [("output", "", 0) for _ in servers]
            
            start_time = time.time()
            
            # 並列でコマンドを実行
            results = tool.execute_parallel(servers, "uptime", max_workers=3)
            
            execution_time = time.time() - start_time
            
            assert len(results) == 5
            assert all(r.status == ToolStatus.SUCCESS for r in results)
            # 並列実行により、逐次実行より高速であることを確認
            assert execution_time < 2.0  # 適切な閾値を設定


class TestRemoteToolResult:
    """RemoteToolResultのテストクラス"""
    
    @pytest.mark.skipif(RemoteToolResult is None, reason="RemoteToolResult not implemented yet")
    def test_result_creation(self):
        """結果オブジェクトの作成テスト"""
        result = RemoteToolResult(
            status=ToolStatus.SUCCESS,
            output="test output",
            server="test-server.example.com",
            command="ls -la",
            execution_time=1.5
        )
        
        assert result.status == ToolStatus.SUCCESS
        assert result.output == "test output"
        assert result.server == "test-server.example.com"
        assert result.command == "ls -la"
        assert result.execution_time == 1.5
    
    @pytest.mark.skipif(RemoteToolResult is None, reason="RemoteToolResult not implemented yet")
    def test_result_serialization(self):
        """結果のシリアライゼーションテスト"""
        result = RemoteToolResult(
            status=ToolStatus.SUCCESS,
            output="test output",
            server="test-server.example.com",
            command="ls -la"
        )
        
        # 辞書形式への変換
        result_dict = result.to_dict()
        assert result_dict['status'] == 'success'
        assert result_dict['output'] == 'test output'
        assert result_dict['server'] == 'test-server.example.com'
        assert result_dict['command'] == 'ls -la'
        
        # JSON形式への変換
        result_json = result.to_json()
        assert isinstance(result_json, str)
        assert 'test output' in result_json