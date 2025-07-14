"""
AIDE リモートサーバー操作モジュール

SSH経由でのリモートサーバー接続、調査、対応機能を提供
"""

from typing import Optional

try:
    from .connection_manager import RemoteConnectionManager, ConnectionPool
    from .ssh_client import SSHClient, SSHConfig
    __all__ = [
        'RemoteConnectionManager',
        'ConnectionPool',
        'SSHClient',
        'SSHConfig'
    ]
except ImportError:
    # モジュールが未実装の場合のフォールバック
    RemoteConnectionManager = None
    ConnectionPool = None
    SSHClient = None
    SSHConfig = None


def get_connection_manager(config: Optional[dict] = None) -> Optional['RemoteConnectionManager']:
    """リモート接続マネージャーのインスタンスを取得"""
    if RemoteConnectionManager is None:
        return None
    return RemoteConnectionManager(config or {})