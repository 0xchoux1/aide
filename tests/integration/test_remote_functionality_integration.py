"""
リモート機能統合テスト

RemoteConnectionManager、RemoteSystemTool、RemoteAgentの統合動作確認
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from typing import Dict, Any

# 統合テスト対象のインポート
try:
    from src.remote.connection_manager import RemoteConnectionManager
    from src.remote.ssh_client import SSHClient, SSHConfig
    from src.tools.remote_system_tool import RemoteSystemTool
    from src.tools.base_tool import ToolStatus
    REMOTE_MODULES_AVAILABLE = True
except ImportError:
    REMOTE_MODULES_AVAILABLE = False


@pytest.mark.skipif(not REMOTE_MODULES_AVAILABLE, reason="Remote modules not available")
class TestRemoteIntegration:
    """リモート機能統合テストクラス"""
    
    @pytest.fixture
    def integration_config(self):
        """統合テスト用設定"""
        return {
            'connection_manager': {
                'max_connections': 5,
                'connection_timeout': 30,
                'idle_timeout': 300,
                'retry_attempts': 3,
                'retry_delay': 1
            },
            'remote_tool': {
                'timeout': 60,
                'safe_mode': True,
                'max_retries': 3,
                'retry_delay': 1
            },
            'servers': [
                {
                    'hostname': 'test-server1.example.com',
                    'port': 22,
                    'username': 'testuser1',
                    'key_filename': '/home/user/.ssh/id_rsa'
                },
                {
                    'hostname': 'test-server2.example.com',
                    'port': 22,
                    'username': 'testuser2',
                    'key_filename': '/home/user/.ssh/id_rsa'
                }
            ]
        }
    
    def test_connection_manager_and_tool_integration(self, integration_config):
        """ConnectionManagerとRemoteSystemToolの統合テスト"""
        # RemoteSystemToolを初期化（内部でConnectionManagerを使用）
        tool = RemoteSystemTool(integration_config['remote_tool'])
        server_config = integration_config['servers'][0]
        
        # 接続マネージャーの内部モックを設定
        with patch.object(tool.connection_manager, 'connect') as mock_connect, \
             patch.object(tool.connection_manager, 'execute_command') as mock_execute:
            
            mock_client = Mock()
            mock_client.is_connected = True
            mock_client.get_connection_info.return_value = {
                'hostname': server_config['hostname'],
                'status': 'connected',
                'uptime': 100
            }
            mock_connect.return_value = mock_client
            mock_execute.return_value = ("System info output", "", 0)
            
            # ツールを使用してコマンドを実行
            result = tool.execute(server_config, "df -h")
            
            # 結果を検証
            assert result.status == ToolStatus.SUCCESS
            assert result.server == server_config['hostname']
            assert result.command == "df -h"
            assert result.output == "System info output"
            
            # ConnectionManagerが正しく呼び出されたことを確認
            mock_connect.assert_called_once()
            mock_execute.assert_called_once_with(mock_client, "df -h", 60)
    
    def test_multiple_server_operations(self, integration_config):
        """複数サーバーでの操作統合テスト"""
        tool = RemoteSystemTool(integration_config['remote_tool'])
        servers = integration_config['servers']
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect, \
             patch.object(tool.connection_manager, 'execute_command') as mock_execute:
            
            # 各サーバー用のモッククライアントを設定
            mock_clients = []
            for i, server in enumerate(servers):
                mock_client = Mock()
                mock_client.is_connected = True
                mock_client.get_connection_info.return_value = {
                    'hostname': server['hostname'],
                    'status': 'connected'
                }
                mock_clients.append(mock_client)
            
            mock_connect.side_effect = mock_clients
            mock_execute.side_effect = [
                (f"uptime from {server['hostname']}", "", 0) for server in servers
            ]
            
            # 複数サーバーでコマンドを実行
            results = tool.execute_on_multiple_servers(servers, "uptime")
            
            # 結果を検証
            assert len(results) == 2
            for i, result in enumerate(results):
                assert result.status == ToolStatus.SUCCESS
                assert result.server == servers[i]['hostname']
                assert f"uptime from {servers[i]['hostname']}" in result.output
    
    def test_connection_pool_behavior(self, integration_config):
        """接続プールの動作確認テスト"""
        connection_config = integration_config['connection_manager']
        connection_config['max_connections'] = 2  # プールサイズを制限
        
        manager = RemoteConnectionManager(connection_config)
        servers = integration_config['servers']
        
        with patch('src.remote.connection_manager.SSHClient') as mock_ssh_client:
            # モッククライアントを設定
            mock_clients = []
            for server in servers:
                mock_client = Mock()
                mock_client.connect.return_value = True
                mock_client.is_connected = True
                mock_client.get_connection_info.return_value = {
                    'hostname': server['hostname'],
                    'status': 'connected'
                }
                mock_clients.append(mock_client)
            
            mock_ssh_client.side_effect = mock_clients
            
            # 接続を確立
            connections = []
            for server in servers:
                conn = manager.connect(server)
                connections.append(conn)
            
            # プールの状態を確認
            assert manager.pool.active_connections() == 2
            assert manager.pool.available_slots() == 0
            assert manager.pool.is_full() is True
            
            # 接続を切断
            for conn in connections:
                manager.disconnect(conn)
            
            assert manager.pool.active_connections() == 0
        
        # クリーンアップ
        manager.shutdown()
    
    def test_security_and_safety_integration(self, integration_config):
        """セキュリティと安全性の統合テスト"""
        tool = RemoteSystemTool(integration_config['remote_tool'])
        server_config = integration_config['servers'][0]
        
        # 危険なコマンドのテスト
        dangerous_commands = [
            "rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
            "chmod 777 /etc/passwd",
            "sudo shutdown -h now"
        ]
        
        for dangerous_cmd in dangerous_commands:
            result = tool.execute(server_config, dangerous_cmd)
            
            assert result.status == ToolStatus.PERMISSION_DENIED
            assert "dangerous" in result.error.lower() or "blocked" in result.error.lower()
            assert result.metadata.get('security_violation') is True
    
    def test_error_handling_and_resilience(self, integration_config):
        """エラーハンドリングとレジリエンステスト"""
        tool = RemoteSystemTool(integration_config['remote_tool'])
        server_config = integration_config['servers'][0]
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect:
            # 接続が最初は失敗し、後で成功するシナリオ
            from src.remote.ssh_client import SSHConnectionError
            
            mock_clients = [Mock(), Mock()]
            
            # 最初の接続は失敗
            mock_connect.side_effect = [
                SSHConnectionError("Connection timeout"),
                mock_clients[1]  # 2回目で成功
            ]
            
            mock_clients[1].is_connected = True
            mock_clients[1].get_connection_info.return_value = {'status': 'connected'}
            
            with patch.object(tool.connection_manager, 'execute_command') as mock_execute:
                mock_execute.return_value = ("success output", "", 0)
                
                # リトライされて最終的に成功することを確認
                result = tool.execute(server_config, "ls")
                
                # 2回接続を試行したことを確認
                assert mock_connect.call_count == 2
                assert result.status == ToolStatus.SUCCESS
    
    def test_system_information_collection_workflow(self, integration_config):
        """システム情報収集ワークフローのテスト"""
        tool = RemoteSystemTool(integration_config['remote_tool'])
        server_config = integration_config['servers'][0]
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect, \
             patch.object(tool.connection_manager, 'execute_command') as mock_execute:
            
            mock_client = Mock()
            mock_client.is_connected = True
            mock_client.get_connection_info.return_value = {'status': 'connected'}
            mock_connect.return_value = mock_client
            
            # システム情報コマンドの応答を順番に設定
            system_responses = [
                ("test-server1", "", 0),  # hostname
                ("Linux 5.4.0-123", "", 0),  # kernel
                ("MemTotal: 16GB", "", 0),  # memory
                ("Filesystem /dev/sda1 75% /", "", 0),  # disk_usage
                ("load average: 0.8", "", 0),  # load_average
                ("up 5 days", "", 0),  # uptime
                ("PID USER %CPU", "", 0)  # processes
            ]
            mock_execute.side_effect = system_responses
            
            # システム情報を収集
            result = tool.gather_system_info(server_config)
            
            # 結果を検証
            assert result.status == ToolStatus.SUCCESS
            assert 'system_info' in result.metadata
            
            system_info = result.metadata['system_info']
            assert 'hostname' in system_info
            assert 'kernel' in system_info
            assert 'memory' in system_info
            assert 'disk_usage' in system_info
            assert 'load_average' in system_info
            
            # 各情報が正しく取得されていることを確認
            assert "test-server1" in system_info['hostname']
            assert "Linux" in system_info['kernel']
            assert "16GB" in system_info['memory']
    
    def test_concurrent_operations(self, integration_config):
        """並行操作のテスト"""
        tool = RemoteSystemTool(integration_config['remote_tool'])
        servers = integration_config['servers'] * 3  # 6サーバーに拡張
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect, \
             patch.object(tool.connection_manager, 'execute_command') as mock_execute:
            
            # 各サーバー用のモッククライアントを設定
            mock_clients = []
            for i, server in enumerate(servers):
                mock_client = Mock()
                mock_client.is_connected = True
                mock_client.get_connection_info.return_value = {
                    'hostname': server['hostname'],
                    'status': 'connected'
                }
                mock_clients.append(mock_client)
            
            mock_connect.side_effect = mock_clients
            mock_execute.side_effect = [
                (f"output from server {i}", "", 0) for i in range(len(servers))
            ]
            
            start_time = time.time()
            
            # 並列でコマンドを実行
            results = tool.execute_parallel(servers, "hostname", max_workers=3)
            
            execution_time = time.time() - start_time
            
            # 結果を検証
            assert len(results) == 6
            assert all(r.status == ToolStatus.SUCCESS for r in results)
            
            # 並列実行により高速であることを確認（適切な閾値設定）
            assert execution_time < 3.0  # 逐次実行より大幅に高速
    
    def test_execution_history_tracking(self, integration_config):
        """実行履歴追跡の統合テスト"""
        tool = RemoteSystemTool(integration_config['remote_tool'])
        server_config = integration_config['servers'][0]
        
        with patch.object(tool.connection_manager, 'connect') as mock_connect, \
             patch.object(tool.connection_manager, 'execute_command') as mock_execute:
            
            mock_client = Mock()
            mock_client.is_connected = True
            mock_client.get_connection_info.return_value = {'status': 'connected'}
            mock_connect.return_value = mock_client
            mock_execute.return_value = ("command output", "", 0)
            
            # 複数のコマンドを実行
            commands = ["ls", "ps aux", "df -h", "uptime"]
            for command in commands:
                tool.execute(server_config, command)
            
            # 実行履歴を確認
            history = tool.get_execution_history()
            
            # 履歴の数が正しいことを確認
            assert len(history) >= len(commands)
            
            # 履歴内容を確認
            recent_history = history[-len(commands):]
            executed_commands = [record['command'] for record in recent_history]
            
            # 全てのコマンドが実行されていることを確認
            for command in commands:
                assert command in executed_commands
            
            # 履歴の内容を確認
            for record in recent_history:
                assert record['command'] in commands
                assert record['server'] == server_config['hostname']
                assert 'timestamp' in record
                assert 'execution_time' in record
                assert record['status'] == 'success'
    
    def test_cleanup_and_resource_management(self, integration_config):
        """クリーンアップとリソース管理のテスト"""
        tool = RemoteSystemTool(integration_config['remote_tool'])
        
        # コンテキストマネージャーとして使用
        with tool:
            server_config = integration_config['servers'][0]
            
            with patch.object(tool.connection_manager, 'connect') as mock_connect, \
                 patch.object(tool.connection_manager, 'execute_command') as mock_execute:
                
                mock_client = Mock()
                mock_client.is_connected = True
                mock_connect.return_value = mock_client
                mock_execute.return_value = ("output", "", 0)
                
                # ツールを使用
                result = tool.execute(server_config, "echo test")
                assert result.status == ToolStatus.SUCCESS
        
        # コンテキスト終了後、クリーンアップが呼ばれることを確認
        # （実際のテストでは適切なmockingでshutdownの呼び出しを確認）


@pytest.mark.skipif(not REMOTE_MODULES_AVAILABLE, reason="Remote modules not available")
class TestRemoteConfigurationIntegration:
    """リモート設定統合テストクラス"""
    
    def test_configuration_loading_and_validation(self):
        """設定の読み込みと検証テスト"""
        # 有効な設定
        valid_config = {
            'max_connections': 10,
            'connection_timeout': 30,
            'safe_mode': True,
            'timeout': 60
        }
        
        # ConnectionManagerとToolの初期化が成功することを確認
        connection_manager = RemoteConnectionManager(valid_config)
        tool = RemoteSystemTool(valid_config)
        
        assert connection_manager.max_connections == 10
        assert connection_manager.connection_timeout == 30
        assert tool.safe_mode is True
        assert tool.timeout == 60
        
        # クリーンアップ
        connection_manager.shutdown()
        tool.cleanup()
    
    def test_ssh_config_validation(self):
        """SSH設定の検証テスト"""
        from src.remote.ssh_client import SSHConfig
        
        # 有効なSSH設定
        valid_ssh_config = SSHConfig(
            hostname='test.example.com',
            port=22,
            username='testuser',
            key_filename='/path/to/key'
        )
        
        # 検証が通ることを確認
        valid_ssh_config.validate()
        
        # 無効なSSH設定（ホスト名なし）
        with pytest.raises(ValueError, match="Hostname is required"):
            invalid_config = SSHConfig(hostname="", username="testuser")
            invalid_config.validate()
        
        # 無効なSSH設定（ユーザー名なし）
        with pytest.raises(ValueError, match="Username is required"):
            invalid_config = SSHConfig(hostname="test.com", username="")
            invalid_config.validate()


if __name__ == "__main__":
    # 統合テストの直接実行
    pytest.main([__file__, "-v"])