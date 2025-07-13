"""
AIDE テストパッケージ

このパッケージには、AIDE システムの包括的なテストスイートが含まれています。

テスト構造:
- unit/: 単体テスト
- integration/: 統合テスト
- performance/: パフォーマンステスト
"""

__version__ = "3.3.0"

# テスト用のユーティリティ関数
import os
import tempfile
import shutil
from pathlib import Path

def create_test_config():
    """テスト用設定作成"""
    return {
        "system": {
            "name": "AIDE_TEST",
            "version": "3.3.0",
            "environment": "testing"
        },
        "logging": {
            "level": "DEBUG",
            "file": "test_aide.log"
        },
        "testing": {
            "enabled": True,
            "mock_external_calls": True
        }
    }

def create_temp_workspace():
    """一時テストワークスペース作成"""
    temp_dir = tempfile.mkdtemp(prefix="aide_test_")
    workspace_path = Path(temp_dir)
    
    # 基本ディレクトリ構造作成
    (workspace_path / "config").mkdir(exist_ok=True)
    (workspace_path / "logs").mkdir(exist_ok=True)
    (workspace_path / "data").mkdir(exist_ok=True)
    
    return workspace_path

def cleanup_temp_workspace(workspace_path):
    """一時テストワークスペースクリーンアップ"""
    if workspace_path.exists():
        shutil.rmtree(workspace_path)