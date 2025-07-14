"""
RemoteConnectionManagerのユニットテスト

SSH接続管理、プール化、認証、エラーハンドリングのテスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from datetime import datetime
from typing import Dict, Any

# テスト対象のインポート（まだ実装されていないのでパスする）
try:
    from src.remote.connection_manager import (
        RemoteConnectionManager,
        ConnectionPool,
        ConnectionStatus,
        SSHConnectionError
    )
    from src.remote.ssh_client import SSHClient, SSHConfig
except ImportError:
    # 実装前なのでモックで代替
    RemoteConnectionManager = None
    ConnectionPool = None
    ConnectionStatus = None
    SSHConnectionError = Exception
    SSHClient = None
    SSHConfig = None


class TestRemoteConnectionManager:
    """RemoteConnectionManagerのテストクラス"""
    
    @pytest.fixture
    def default_config(self):
        """デフォルト設定"""
        return {
            'max_connections': 10,
            'connection_timeout': 30,
            'idle_timeout': 300,
            'retry_attempts': 3,
            'retry_delay': 2
        }
    
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
    
    @pytest.mark.skipif(RemoteConnectionManager is None, reason="RemoteConnectionManager not implemented yet")
    def test_connection_manager_initialization(self, default_config):
        """接続マネージャーの初期化テスト"""
        manager = RemoteConnectionManager(default_config)
        
        assert manager.max_connections == 10
        assert manager.connection_timeout == 30
        assert manager.idle_timeout == 300
        assert manager.retry_attempts == 3
        assert manager.retry_delay == 2
        assert isinstance(manager.pool, ConnectionPool)
    
    @pytest.mark.skipif(RemoteConnectionManager is None, reason="RemoteConnectionManager not implemented yet")
    def test_connect_to_server(self, default_config, ssh_config):
        """サーバーへの接続テスト"""
        manager = RemoteConnectionManager(default_config)
        
        with patch('src.remote.connection_manager.SSHClient') as mock_ssh_client:
            mock_client = Mock()
            mock_ssh_client.return_value = mock_client
            mock_client.connect.return_value = True
            mock_client.is_connected = True
            
            # 接続を確立
            connection = manager.connect(ssh_config)
            
            assert connection is not None
            assert connection == mock_client
            mock_client.connect.assert_called_once()
    
    @pytest.mark.skipif(RemoteConnectionManager is None, reason="RemoteConnectionManager not implemented yet")
    def test_connection_pool_management(self, default_config, ssh_config):
        """接続プール管理のテスト"""
        manager = RemoteConnectionManager(default_config)
        
        with patch('src.remote.connection_manager.SSHClient') as mock_ssh_client:
            # 複数の接続を作成
            connections = []
            for i in range(3):
                mock_client = Mock()
                mock_client.connect.return_value = True
                mock_client.is_connected = True
                mock_ssh_client.return_value = mock_client
                
                conn = manager.connect({**ssh_config, 'hostname': f'server{i}.example.com'})
                connections.append(conn)
            
            # プール内の接続数を確認
            assert manager.pool.active_connections() == 3
            assert manager.pool.available_slots() == 7
            
            # 接続を解放
            for conn in connections:
                manager.disconnect(conn)
            
            assert manager.pool.active_connections() == 0
    
    @pytest.mark.skipif(RemoteConnectionManager is None, reason="RemoteConnectionManager not implemented yet")
    def test_connection_retry_on_failure(self, default_config, ssh_config):
        """接続失敗時のリトライテスト"""
        default_config['retry_delay'] = 0.1  # テスト高速化
        manager = RemoteConnectionManager(default_config)
        
        with patch('src.remote.connection_manager.SSHClient') as mock_ssh_client:
            # 呼び出し毎に異なるmockを返すようにする
            mock_clients = []
            for i in range(3):
                mock_client = Mock()
                if i < 2:
                    # 最初の2回は失敗
                    mock_client.connect.side_effect = SSHConnectionError("Connection failed")
                else:
                    # 3回目で成功
                    mock_client.connect.return_value = True
                    mock_client.is_connected = True
                mock_clients.append(mock_client)
            
            mock_ssh_client.side_effect = mock_clients
            
            # リトライして最終的に成功することを確認
            connection = manager.connect(ssh_config)
            
            assert connection is not None
            assert mock_ssh_client.call_count == 3
    
    @pytest.mark.skipif(RemoteConnectionManager is None, reason="RemoteConnectionManager not implemented yet")
    def test_connection_timeout(self, default_config, ssh_config):
        """接続タイムアウトのテスト"""
        default_config['connection_timeout'] = 1  # 1秒でタイムアウト
        manager = RemoteConnectionManager(default_config)
        
        with patch('src.remote.ssh_client.SSHClient') as mock_ssh_client:
            mock_client = Mock()
            # タイムアウトをシミュレート
            def slow_connect(*args, **kwargs):
                time.sleep(2)
                return True
            
            mock_client.connect.side_effect = slow_connect
            mock_ssh_client.return_value = mock_client
            
            # タイムアウトエラーが発生することを確認
            with pytest.raises(SSHConnectionError, match="Connection timeout"):
                manager.connect(ssh_config)
    
    @pytest.mark.skipif(RemoteConnectionManager is None, reason="RemoteConnectionManager not implemented yet")
    def test_idle_connection_cleanup(self, default_config, ssh_config):
        """アイドル接続のクリーンアップテスト"""
        default_config['idle_timeout'] = 1  # 1秒でアイドルタイムアウト
        manager = RemoteConnectionManager(default_config)
        
        with patch('src.remote.ssh_client.SSHClient') as mock_ssh_client:
            mock_client = Mock()
            mock_client.connect.return_value = True
            mock_client.is_connected.return_value = True
            mock_ssh_client.return_value = mock_client
            
            # 接続を確立
            connection = manager.connect(ssh_config)
            
            # アイドル状態をシミュレート
            time.sleep(2)
            
            # クリーンアップを実行
            manager.cleanup_idle_connections()
            
            # 接続が閉じられたことを確認
            mock_client.disconnect.assert_called_once()
    
    @pytest.mark.skipif(RemoteConnectionManager is None, reason="RemoteConnectionManager not implemented yet")
    def test_get_connection_status(self, default_config, ssh_config):
        """接続ステータスの取得テスト"""
        manager = RemoteConnectionManager(default_config)
        
        with patch('src.remote.ssh_client.SSHClient') as mock_ssh_client:
            mock_client = Mock()
            mock_client.connect.return_value = True
            mock_client.is_connected.return_value = True
            mock_client.get_transport.return_value = Mock(is_active=Mock(return_value=True))
            mock_ssh_client.return_value = mock_client
            
            # 接続を確立
            connection = manager.connect(ssh_config)
            
            # ステータスを取得
            status = manager.get_connection_status(connection)
            
            assert status is not None
            assert status.is_active is True
            assert status.hostname == 'test-server.example.com'
            assert status.uptime > 0
    
    @pytest.mark.skipif(RemoteConnectionManager is None, reason="RemoteConnectionManager not implemented yet")
    def test_execute_command_on_connection(self, default_config, ssh_config):
        """接続を使用したコマンド実行テスト"""
        manager = RemoteConnectionManager(default_config)
        
        with patch('src.remote.ssh_client.SSHClient') as mock_ssh_client:
            mock_client = Mock()
            mock_client.connect.return_value = True
            mock_client.is_connected.return_value = True
            mock_client.execute_command.return_value = ("Hello, World!", "", 0)
            mock_ssh_client.return_value = mock_client
            
            # 接続を確立
            connection = manager.connect(ssh_config)
            
            # コマンドを実行
            stdout, stderr, exit_code = manager.execute_command(
                connection, 
                "echo 'Hello, World!'"
            )
            
            assert stdout == "Hello, World!"
            assert stderr == ""
            assert exit_code == 0
            mock_client.execute_command.assert_called_once_with("echo 'Hello, World!'")
    
    @pytest.mark.skipif(RemoteConnectionManager is None, reason="RemoteConnectionManager not implemented yet")
    def test_connection_health_check(self, default_config, ssh_config):
        """接続の健全性チェックテスト"""
        manager = RemoteConnectionManager(default_config)
        
        with patch('src.remote.ssh_client.SSHClient') as mock_ssh_client:
            mock_client = Mock()
            mock_client.connect.return_value = True
            mock_client.is_connected.return_value = True
            mock_client.execute_command.return_value = ("", "", 0)
            mock_ssh_client.return_value = mock_client
            
            # 接続を確立
            connection = manager.connect(ssh_config)
            
            # ヘルスチェック
            is_healthy = manager.health_check(connection)
            
            assert is_healthy is True
            mock_client.execute_command.assert_called_with("echo 'health_check'", timeout=5)
    
    @pytest.mark.skipif(RemoteConnectionManager is None, reason="RemoteConnectionManager not implemented yet")
    def test_concurrent_connections(self, default_config):
        """同時接続のテスト"""
        default_config['max_connections'] = 5
        manager = RemoteConnectionManager(default_config)
        
        with patch('src.remote.ssh_client.SSHClient') as mock_ssh_client:
            # 最大接続数まで接続を作成
            connections = []
            for i in range(5):
                mock_client = Mock()
                mock_client.connect.return_value = True
                mock_client.is_connected.return_value = True
                mock_ssh_client.return_value = mock_client
                
                conn = manager.connect({
                    'hostname': f'server{i}.example.com',
                    'username': 'testuser',
                    'port': 22
                })
                connections.append(conn)
            
            # 接続数が上限に達したことを確認
            assert manager.pool.is_full() is True
            
            # さらに接続しようとするとエラー
            with pytest.raises(SSHConnectionError, match="Connection pool is full"):
                manager.connect({
                    'hostname': 'extra-server.example.com',
                    'username': 'testuser',
                    'port': 22
                })


class TestConnectionPool:
    """ConnectionPoolのテストクラス"""
    
    @pytest.mark.skipif(ConnectionPool is None, reason="ConnectionPool not implemented yet")
    def test_pool_initialization(self):
        """プールの初期化テスト"""
        pool = ConnectionPool(max_connections=5)
        
        assert pool.max_connections == 5
        assert pool.active_connections() == 0
        assert pool.available_slots() == 5
        assert pool.is_full() is False
    
    @pytest.mark.skipif(ConnectionPool is None, reason="ConnectionPool not implemented yet")
    def test_add_remove_connection(self):
        """接続の追加と削除テスト"""
        pool = ConnectionPool(max_connections=5)
        
        # モック接続を作成
        conn1 = Mock()
        conn2 = Mock()
        
        # 接続を追加
        pool.add_connection("server1", conn1)
        pool.add_connection("server2", conn2)
        
        assert pool.active_connections() == 2
        assert pool.get_connection("server1") == conn1
        assert pool.get_connection("server2") == conn2
        
        # 接続を削除
        pool.remove_connection("server1")
        
        assert pool.active_connections() == 1
        assert pool.get_connection("server1") is None
        assert pool.get_connection("server2") == conn2
    
    @pytest.mark.skipif(ConnectionPool is None, reason="ConnectionPool not implemented yet")
    def test_pool_statistics(self):
        """プール統計情報のテスト"""
        pool = ConnectionPool(max_connections=5)
        
        # 接続を追加
        for i in range(3):
            pool.add_connection(f"server{i}", Mock())
        
        stats = pool.get_statistics()
        
        assert stats['max_connections'] == 5
        assert stats['active_connections'] == 3
        assert stats['available_slots'] == 2
        assert stats['utilization'] == 0.6  # 3/5 = 0.6
        assert 'connections' in stats
        assert len(stats['connections']) == 3


# モックSSH設定クラス（実装前のテスト用）
if SSHConfig is None:
    @pytest.fixture
    def mock_ssh_config():
        """モックSSH設定"""
        return {
            'hostname': 'test-server.example.com',
            'port': 22,
            'username': 'testuser',
            'key_filename': '/home/user/.ssh/id_rsa',
            'timeout': 30
        }
else:
    @pytest.fixture
    def mock_ssh_config():
        """実際のSSH設定オブジェクト"""
        return SSHConfig(
            hostname='test-server.example.com',
            port=22,
            username='testuser',
            key_filename='/home/user/.ssh/id_rsa',
            timeout=30
        )