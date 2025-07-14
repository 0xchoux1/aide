#!/usr/bin/env python3
"""
AIDE リモート機能診断スクリプト

本番環境でリモート機能が動作しない場合の診断に使用
"""

import sys
import os
import subprocess

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_command_exists(command):
    """コマンドが存在するかチェック"""
    try:
        subprocess.run([command, "--version"], capture_output=True, check=False)
        return True
    except FileNotFoundError:
        return False

def diagnose_remote_functionality():
    """リモート機能の診断を実行"""
    print("=" * 60)
    print("AIDE リモート機能診断ツール v1.0")
    print("=" * 60)
    
    errors = []
    warnings = []
    
    # 1. Python バージョンチェック
    print("\n1. Python環境チェック:")
    python_version = sys.version_info
    print(f"   Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        errors.append("Python 3.8以上が必要です")
    
    # 2. paramiko チェック
    print("\n2. Paramiko チェック:")
    try:
        import paramiko
        print(f"   ✅ Paramiko インストール済み (version: {paramiko.__version__})")
    except ImportError:
        print("   ❌ Paramiko がインストールされていません")
        errors.append("paramiko がインストールされていません。'pip install paramiko>=3.0.0' を実行してください")
    
    # 3. SSH クライアントモジュールチェック
    print("\n3. SSH クライアントモジュールチェック:")
    try:
        from src.remote.ssh_client import SSH_AVAILABLE, FORCE_MOCK_MODE
        print(f"   - SSH_AVAILABLE: {SSH_AVAILABLE}")
        print(f"   - FORCE_MOCK_MODE: {FORCE_MOCK_MODE}")
        
        mock_mode_env = os.getenv('AIDE_REMOTE_MOCK_MODE', 'not set')
        print(f"   - AIDE_REMOTE_MOCK_MODE 環境変数: {mock_mode_env}")
        
        if not SSH_AVAILABLE:
            warnings.append("SSH_AVAILABLE が False です。paramiko が正しくインポートできません")
        if FORCE_MOCK_MODE:
            warnings.append("FORCE_MOCK_MODE が True です。環境変数 AIDE_REMOTE_MOCK_MODE を確認してください")
            
    except Exception as e:
        print(f"   ❌ SSH クライアントモジュールのインポートエラー: {e}")
        errors.append(f"SSH クライアントモジュールのインポートエラー: {e}")
    
    # 4. 設定ファイルチェック
    print("\n4. 設定ファイルチェック:")
    servers_yaml_path = 'config/servers.yaml'
    if os.path.exists(servers_yaml_path):
        print(f"   ✅ {servers_yaml_path} 存在")
        try:
            import yaml
            with open(servers_yaml_path, 'r') as f:
                config = yaml.safe_load(f)
                server_groups = config.get('server_groups', {})
                print(f"   - サーバーグループ数: {len(server_groups)}")
                
                # 各グループのサーバー数を表示
                for group_name, group_data in server_groups.items():
                    servers = group_data.get('servers', [])
                    print(f"   - {group_name}: {len(servers)} サーバー")
                    
                    # 鍵ファイルの存在確認
                    for server in servers:
                        key_file = server.get('key_filename')
                        if key_file:
                            if os.path.exists(os.path.expanduser(key_file)):
                                print(f"     ✅ {server['name']}: 鍵ファイル存在")
                            else:
                                print(f"     ❌ {server['name']}: 鍵ファイルが見つかりません: {key_file}")
                                warnings.append(f"鍵ファイルが見つかりません: {key_file}")
                                
        except ImportError:
            warnings.append("yaml モジュールがインストールされていません")
        except Exception as e:
            warnings.append(f"servers.yaml の読み込みエラー: {e}")
    else:
        print(f"   ❌ {servers_yaml_path} が見つかりません")
        errors.append(f"{servers_yaml_path} が見つかりません")
    
    # 5. SSH コマンドチェック
    print("\n5. システムSSHコマンドチェック:")
    if check_command_exists("ssh"):
        print("   ✅ ssh コマンド利用可能")
    else:
        warnings.append("ssh コマンドが見つかりません")
    
    # 6. 依存関係チェック
    print("\n6. 依存関係チェック:")
    try:
        import cryptography
        print(f"   ✅ cryptography インストール済み (version: {cryptography.__version__})")
    except ImportError:
        warnings.append("cryptography がインストールされていません（paramiko の依存関係）")
    
    # 7. 簡単な接続テスト
    print("\n7. 接続テスト（モックモード）:")
    try:
        from src.remote.ssh_client import SSHClient, SSHConfig
        
        test_config = SSHConfig(
            hostname="test.example.com",
            username="test",
            port=22
        )
        
        # モックモードで接続テスト
        client = SSHClient(test_config, mock_mode=True)
        print(f"   - テストクライアント作成: 成功")
        print(f"   - クライアントモード: {'MOCK' if client.mock_mode else 'REAL'}")
        
        if client.connect():
            print("   ✅ モック接続テスト: 成功")
            client.disconnect()
        else:
            errors.append("モック接続テストが失敗しました")
            
    except Exception as e:
        print(f"   ❌ 接続テストエラー: {e}")
        errors.append(f"接続テストエラー: {e}")
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("診断結果サマリー:")
    print("=" * 60)
    
    if not errors and not warnings:
        print("✅ すべてのチェックに合格しました！")
        print("\n本番環境でリモート機能を有効にするには:")
        print("1. export AIDE_REMOTE_MOCK_MODE=false")
        print("2. aide remote list")
    else:
        if errors:
            print(f"\n❌ エラー: {len(errors)}件")
            for i, error in enumerate(errors, 1):
                print(f"   {i}. {error}")
        
        if warnings:
            print(f"\n⚠️  警告: {len(warnings)}件")
            for i, warning in enumerate(warnings, 1):
                print(f"   {i}. {warning}")
        
        print("\n推奨される修正手順:")
        print("1. pip install -r requirements.txt")
        print("2. config/servers.yaml で正しいサーバー情報を設定")
        print("3. SSH鍵ファイルを正しい場所に配置し、chmod 600 で権限設定")
        print("4. export AIDE_REMOTE_MOCK_MODE=false")
        print("5. aide remote list でテスト")

if __name__ == "__main__":
    diagnose_remote_functionality()