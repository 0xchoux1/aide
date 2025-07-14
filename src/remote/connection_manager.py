"""
リモート接続マネージャー

SSH接続のプール管理、リトライ、タイムアウト処理を提供
"""

import time
import threading
from typing import Dict, Optional, List, Tuple, Any, Union
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
import logging

from .ssh_client import SSHClient, SSHConfig, SSHConnectionError, ConnectionStatus


logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """接続情報"""
    client: SSHClient
    identifier: str
    created_at: float
    last_used: float
    usage_count: int = 0


class ConnectionPool:
    """接続プール"""
    
    def __init__(self, max_connections: int = 10):
        """
        初期化
        
        Args:
            max_connections: 最大接続数
        """
        self.max_connections = max_connections
        self._connections: Dict[str, ConnectionInfo] = {}
        self._lock = threading.RLock()
    
    def add_connection(self, identifier: str, client: SSHClient) -> bool:
        """
        接続を追加
        
        Args:
            identifier: 接続識別子
            client: SSHクライアント
            
        Returns:
            追加に成功したか
        """
        with self._lock:
            if self.is_full():
                return False
            
            if identifier in self._connections:
                return False
            
            self._connections[identifier] = ConnectionInfo(
                client=client,
                identifier=identifier,
                created_at=time.time(),
                last_used=time.time()
            )
            return True
    
    def get_connection(self, identifier: str) -> Optional[SSHClient]:
        """接続を取得"""
        with self._lock:
            conn_info = self._connections.get(identifier)
            if conn_info:
                conn_info.last_used = time.time()
                conn_info.usage_count += 1
                return conn_info.client
            return None
    
    def remove_connection(self, identifier: str) -> Optional[SSHClient]:
        """接続を削除"""
        with self._lock:
            conn_info = self._connections.pop(identifier, None)
            return conn_info.client if conn_info else None
    
    def active_connections(self) -> int:
        """アクティブな接続数"""
        with self._lock:
            return len(self._connections)
    
    def available_slots(self) -> int:
        """利用可能なスロット数"""
        return self.max_connections - self.active_connections()
    
    def is_full(self) -> bool:
        """プールが満杯か確認"""
        return self.active_connections() >= self.max_connections
    
    def get_all_connections(self) -> Dict[str, ConnectionInfo]:
        """全ての接続情報を取得"""
        with self._lock:
            return self._connections.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        with self._lock:
            connections = []
            for identifier, info in self._connections.items():
                connections.append({
                    'identifier': identifier,
                    'uptime': time.time() - info.created_at,
                    'idle_time': time.time() - info.last_used,
                    'usage_count': info.usage_count,
                    'status': info.client.status.value
                })
            
            active = self.active_connections()
            return {
                'max_connections': self.max_connections,
                'active_connections': active,
                'available_slots': self.available_slots(),
                'utilization': active / self.max_connections if self.max_connections > 0 else 0,
                'connections': connections
            }


class RemoteConnectionManager:
    """リモート接続マネージャー"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: 設定辞書
        """
        self.max_connections = config.get('max_connections', 10)
        self.connection_timeout = config.get('connection_timeout', 30)
        self.idle_timeout = config.get('idle_timeout', 300)
        self.retry_attempts = config.get('retry_attempts', 3)
        self.retry_delay = config.get('retry_delay', 2)
        
        self.pool = ConnectionPool(self.max_connections)
        self._executor = ThreadPoolExecutor(max_workers=self.max_connections)
        self._cleanup_thread = None
        self._running = True
        
        # クリーンアップスレッドを開始
        self._start_cleanup_thread()
    
    def connect(self, ssh_config: Union[Dict[str, Any], SSHConfig]) -> SSHClient:
        """
        サーバーに接続
        
        Args:
            ssh_config: SSH接続設定
            
        Returns:
            SSHクライアント
        """
        # 辞書の場合はSSHConfigに変換
        if isinstance(ssh_config, dict):
            config = SSHConfig(**ssh_config)
        else:
            config = ssh_config
        
        # 接続識別子を生成
        identifier = f"{config.hostname}:{config.port}:{config.username}"
        
        # 既存の接続を確認
        existing = self.pool.get_connection(identifier)
        if existing and existing.is_connected:
            logger.info(f"Reusing existing connection: {identifier}")
            return existing
        
        # プールが満杯か確認
        if self.pool.is_full():
            raise SSHConnectionError("Connection pool is full")
        
        # リトライロジックで新規接続
        last_error = None
        for attempt in range(self.retry_attempts):
            try:
                client = self._create_connection_with_timeout(config)
                
                # プールに追加
                if self.pool.add_connection(identifier, client):
                    logger.info(f"New connection established: {identifier}")
                    return client
                else:
                    # 追加に失敗した場合は切断
                    client.disconnect()
                    raise SSHConnectionError("Failed to add connection to pool")
                    
            except TimeoutError:
                last_error = SSHConnectionError("Connection timeout")
                logger.warning(f"Connection attempt {attempt + 1} timed out")
            except SSHConnectionError as e:
                last_error = e
                logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
            except Exception as e:
                last_error = SSHConnectionError(f"Unexpected error: {str(e)}")
                logger.error(f"Unexpected error during connection: {str(e)}")
            
            if attempt < self.retry_attempts - 1:
                time.sleep(self.retry_delay * (attempt + 1))
        
        raise last_error or SSHConnectionError("Connection failed after all retries")
    
    def _create_connection_with_timeout(self, config: SSHConfig) -> SSHClient:
        """タイムアウト付きで接続を作成"""
        def connect_task():
            client = SSHClient(config)
            if not client.connect():
                raise SSHConnectionError("Connection failed")
            return client
        
        future = self._executor.submit(connect_task)
        try:
            return future.result(timeout=self.connection_timeout)
        except TimeoutError:
            future.cancel()
            raise TimeoutError("Connection timeout")
    
    def disconnect(self, client: SSHClient):
        """接続を切断"""
        if not client:
            return
        
        # プールから削除
        for identifier, conn_info in self.pool.get_all_connections().items():
            if conn_info.client == client:
                self.pool.remove_connection(identifier)
                break
        
        # 切断
        try:
            client.disconnect()
            logger.info(f"Disconnected: {client}")
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
    
    def execute_command(self, client: SSHClient, command: str, timeout: Optional[int] = None) -> Tuple[str, str, int]:
        """
        コマンドを実行
        
        Args:
            client: SSHクライアント
            command: 実行するコマンド
            timeout: タイムアウト秒数
            
        Returns:
            stdout, stderr, exit_code のタプル
        """
        if not client or not client.is_connected:
            raise SSHConnectionError("Client not connected")
        
        return client.execute_command(command, timeout)
    
    def health_check(self, client: SSHClient) -> bool:
        """
        接続の健全性をチェック
        
        Args:
            client: SSHクライアント
            
        Returns:
            健全かどうか
        """
        try:
            stdout, stderr, exit_code = client.execute_command("echo 'health_check'", timeout=5)
            return exit_code == 0 and stdout.strip() == "health_check"
        except Exception as e:
            logger.warning(f"Health check failed: {str(e)}")
            return False
    
    def get_connection_status(self, client: SSHClient) -> Optional[Dict[str, Any]]:
        """
        接続ステータスを取得
        
        Args:
            client: SSHクライアント
            
        Returns:
            ステータス情報
        """
        if not client:
            return None
        
        info = client.get_connection_info()
        
        # ヘルスチェック結果を追加
        if client.is_connected:
            info['is_active'] = self.health_check(client)
        else:
            info['is_active'] = False
        
        return info
    
    def cleanup_idle_connections(self):
        """アイドル接続をクリーンアップ"""
        current_time = time.time()
        connections_to_remove = []
        
        for identifier, conn_info in self.pool.get_all_connections().items():
            idle_time = current_time - conn_info.last_used
            
            if idle_time > self.idle_timeout:
                connections_to_remove.append(identifier)
                logger.info(f"Cleaning up idle connection: {identifier} (idle: {idle_time:.1f}s)")
        
        for identifier in connections_to_remove:
            client = self.pool.remove_connection(identifier)
            if client:
                try:
                    client.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting idle connection: {str(e)}")
    
    def _cleanup_thread_worker(self):
        """クリーンアップスレッドのワーカー"""
        while self._running:
            try:
                time.sleep(30)  # 30秒ごとにチェック
                self.cleanup_idle_connections()
            except Exception as e:
                logger.error(f"Error in cleanup thread: {str(e)}")
    
    def _start_cleanup_thread(self):
        """クリーンアップスレッドを開始"""
        if not self._cleanup_thread or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_thread_worker,
                daemon=True
            )
            self._cleanup_thread.start()
    
    def shutdown(self):
        """マネージャーをシャットダウン"""
        logger.info("Shutting down connection manager")
        self._running = False
        
        # 全ての接続を切断
        for identifier in list(self.pool.get_all_connections().keys()):
            client = self.pool.remove_connection(identifier)
            if client:
                try:
                    client.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting during shutdown: {str(e)}")
        
        # エグゼキューターをシャットダウン
        self._executor.shutdown(wait=True)
        
        logger.info("Connection manager shut down complete")
    
    def __enter__(self):
        """コンテキストマネージャーサポート"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーサポート"""
        self.shutdown()


