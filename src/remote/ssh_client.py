"""
SSHクライアント実装

SSH接続、コマンド実行、ファイル転送機能を提供
"""

import os
import time
import socket
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

# SSH実装の選択（paramiko使用を想定、ただしモックモードも提供）
try:
    import paramiko
    SSH_AVAILABLE = True
except ImportError:
    paramiko = None
    SSH_AVAILABLE = False


logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """接続状態"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CONNECTING = "connecting"
    DISCONNECTING = "disconnecting"


class SSHConnectionError(Exception):
    """SSH接続エラー"""
    pass


@dataclass
class SSHConfig:
    """SSH接続設定"""
    hostname: str
    port: int = 22
    username: str = None
    password: Optional[str] = None
    key_filename: Optional[str] = None
    timeout: int = 30
    allow_agent: bool = True
    look_for_keys: bool = True
    
    def validate(self):
        """設定を検証"""
        if not self.hostname:
            raise ValueError("Hostname is required")
        
        if not self.username:
            raise ValueError("Username is required")
        
        if not self.password and not self.key_filename and not self.allow_agent:
            raise ValueError("Authentication method required (password, key, or agent)")


class SSHClient:
    """SSHクライアント"""
    
    def __init__(self, config: SSHConfig, mock_mode: bool = False):
        """
        初期化
        
        Args:
            config: SSH接続設定
            mock_mode: モックモードで動作するか
        """
        self.config = config
        self.mock_mode = mock_mode or not SSH_AVAILABLE
        self._client = None
        self._status = ConnectionStatus.DISCONNECTED
        self._connected_at = None
        self._last_activity = None
        
        if not self.mock_mode:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    @property
    def status(self) -> ConnectionStatus:
        """接続状態を取得"""
        return self._status
    
    @property
    def is_connected(self) -> bool:
        """接続されているか確認"""
        if self.mock_mode:
            return self._status == ConnectionStatus.CONNECTED
        
        if self._client and self._status == ConnectionStatus.CONNECTED:
            try:
                transport = self._client.get_transport()
                return transport and transport.is_active()
            except:
                return False
        return False
    
    def connect(self) -> bool:
        """サーバーに接続"""
        try:
            self.config.validate()
            self._status = ConnectionStatus.CONNECTING
            
            if self.mock_mode:
                # モックモードでは常に成功
                logger.info(f"Mock connection to {self.config.hostname}:{self.config.port}")
                time.sleep(0.1)  # 接続をシミュレート
                self._status = ConnectionStatus.CONNECTED
                self._connected_at = time.time()
                self._last_activity = time.time()
                return True
            
            # 実際のSSH接続
            connect_kwargs = {
                'hostname': self.config.hostname,
                'port': self.config.port,
                'username': self.config.username,
                'timeout': self.config.timeout,
                'allow_agent': self.config.allow_agent,
                'look_for_keys': self.config.look_for_keys,
            }
            
            if self.config.password:
                connect_kwargs['password'] = self.config.password
            
            if self.config.key_filename:
                if os.path.exists(self.config.key_filename):
                    connect_kwargs['key_filename'] = self.config.key_filename
                else:
                    raise SSHConnectionError(f"Key file not found: {self.config.key_filename}")
            
            self._client.connect(**connect_kwargs)
            self._status = ConnectionStatus.CONNECTED
            self._connected_at = time.time()
            self._last_activity = time.time()
            
            logger.info(f"Connected to {self.config.hostname}:{self.config.port}")
            return True
            
        except socket.timeout:
            self._status = ConnectionStatus.ERROR
            raise SSHConnectionError(f"Connection timeout to {self.config.hostname}")
        except paramiko.AuthenticationException as e:
            self._status = ConnectionStatus.ERROR
            raise SSHConnectionError(f"Authentication failed: {str(e)}")
        except Exception as e:
            self._status = ConnectionStatus.ERROR
            raise SSHConnectionError(f"Connection failed: {str(e)}")
    
    def disconnect(self):
        """接続を切断"""
        if self._status != ConnectionStatus.CONNECTED:
            return
        
        try:
            self._status = ConnectionStatus.DISCONNECTING
            
            if self.mock_mode:
                logger.info(f"Mock disconnect from {self.config.hostname}")
                time.sleep(0.1)
            elif self._client:
                self._client.close()
                logger.info(f"Disconnected from {self.config.hostname}")
            
        finally:
            self._status = ConnectionStatus.DISCONNECTED
            self._connected_at = None
            self._last_activity = None
    
    def execute_command(self, command: str, timeout: Optional[int] = None) -> Tuple[str, str, int]:
        """
        コマンドを実行
        
        Args:
            command: 実行するコマンド
            timeout: タイムアウト秒数
            
        Returns:
            stdout, stderr, exit_code のタプル
        """
        if not self.is_connected:
            raise SSHConnectionError("Not connected")
        
        self._last_activity = time.time()
        
        if self.mock_mode:
            # モックモードでの応答
            logger.info(f"Mock execute: {command}")
            
            # 一般的なコマンドに対するモック応答
            if command.strip() == "echo 'health_check'":
                return "health_check", "", 0
            elif command.startswith("echo"):
                # echoコマンドの内容を返す
                content = command[5:].strip().strip("'\"")
                return content, "", 0
            elif command == "whoami":
                return self.config.username or "mockuser", "", 0
            elif command == "hostname":
                return self.config.hostname, "", 0
            elif command == "pwd":
                return "/home/mockuser", "", 0
            else:
                return f"Mock output for: {command}", "", 0
        
        # 実際のコマンド実行
        try:
            stdin, stdout, stderr = self._client.exec_command(
                command, 
                timeout=timeout or self.config.timeout
            )
            
            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8', errors='replace')
            stderr_data = stderr.read().decode('utf-8', errors='replace')
            
            return stdout_data, stderr_data, exit_code
            
        except socket.timeout:
            raise SSHConnectionError(f"Command timeout: {command}")
        except Exception as e:
            raise SSHConnectionError(f"Command execution failed: {str(e)}")
    
    def get_transport(self):
        """トランスポートオブジェクトを取得（互換性のため）"""
        if self.mock_mode:
            # モックトランスポート
            class MockTransport:
                def is_active(self):
                    return True
            return MockTransport()
        
        return self._client.get_transport() if self._client else None
    
    def get_connection_info(self) -> Dict[str, Any]:
        """接続情報を取得"""
        info = {
            'hostname': self.config.hostname,
            'port': self.config.port,
            'username': self.config.username,
            'status': self._status.value,
            'mock_mode': self.mock_mode,
        }
        
        if self._connected_at:
            info['connected_at'] = self._connected_at
            info['uptime'] = time.time() - self._connected_at
        
        if self._last_activity:
            info['last_activity'] = self._last_activity
            info['idle_time'] = time.time() - self._last_activity
        
        return info
    
    def __enter__(self):
        """コンテキストマネージャーサポート"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーサポート"""
        self.disconnect()
    
    def __repr__(self):
        return f"SSHClient(host={self.config.hostname}, status={self._status.value})"