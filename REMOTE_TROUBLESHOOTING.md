# 🔧 リモート機能トラブルシューティングガイド

## 📋 概要

このガイドでは、AIDE Phase 3.3のリモートサーバー機能が本番環境で動作しない場合の診断と解決方法を説明します。

## 🚨 よくある問題と解決方法

### 1. paramikoがインストールされていない

**症状**: リモート機能が常にモックモードで動作する

**診断**:
```bash
# paramikoがインストールされているか確認
pip show paramiko

# Pythonでインポートテスト
python -c "import paramiko; print('paramiko version:', paramiko.__version__)"
```

**解決方法**:
```bash
# paramikoをインストール
pip install paramiko>=3.0.0

# または requirements.txt から全依存関係をインストール
pip install -r requirements.txt
```

### 2. SSH鍵ファイルが見つからない

**症状**: `FileNotFoundError` または `SSH key file not found` エラー

**診断**:
```bash
# servers.yaml で指定された鍵ファイルパスを確認
grep key_filename config/servers.yaml

# 鍵ファイルの存在と権限を確認
ls -la /path/to/ssh/key.pem
```

**解決方法**:
```bash
# 正しいパスに鍵ファイルを配置
cp your-key.pem ~/.ssh/aide_keys/

# 適切な権限を設定
chmod 600 ~/.ssh/aide_keys/*.pem

# servers.yaml を更新
vim config/servers.yaml
```

### 3. SSH接続が失敗する

**症状**: `Connection failed` または `Authentication failed` エラー

**診断**:
```bash
# 手動でSSH接続をテスト
ssh -i /path/to/key.pem username@hostname "uptime"

# デバッグモードで AIDE を実行
export AIDE_DEBUG=true
aide remote execute server-name "uptime"
```

**解決方法**:
```bash
# SSH設定を確認
cat ~/.ssh/config

# known_hosts をクリア（必要な場合）
ssh-keygen -R hostname

# 詳細なSSHデバッグ
ssh -vvv -i /path/to/key.pem username@hostname
```

### 4. モックモードから本番モードに切り替わらない

**症状**: 常に "Mock connection" メッセージが表示される

**診断**:
```bash
# 環境変数を確認
echo $AIDE_REMOTE_MOCK_MODE

# Pythonでモード確認
python -c "
from src.remote.ssh_client import SSH_AVAILABLE, FORCE_MOCK_MODE
print('SSH_AVAILABLE:', SSH_AVAILABLE)
print('FORCE_MOCK_MODE:', FORCE_MOCK_MODE)
"
```

**解決方法**:
```bash
# モックモードを無効化
export AIDE_REMOTE_MOCK_MODE=false

# または .env ファイルで設定
echo "AIDE_REMOTE_MOCK_MODE=false" >> .env
```

## 🔍 詳細診断スクリプト

以下のスクリプトで環境を診断できます：

```python
#!/usr/bin/env python3
"""リモート機能診断スクリプト"""

import sys
import os

# パスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def diagnose_remote_functionality():
    print("=== AIDE リモート機能診断 ===\n")
    
    # 1. paramiko の確認
    print("1. Paramiko チェック:")
    try:
        import paramiko
        print(f"  ✅ Paramiko インストール済み (version: {paramiko.__version__})")
    except ImportError:
        print("  ❌ Paramiko がインストールされていません")
        print("     解決方法: pip install paramiko>=3.0.0")
    
    # 2. SSH クライアントの確認
    print("\n2. SSH クライアントチェック:")
    try:
        from src.remote.ssh_client import SSH_AVAILABLE, FORCE_MOCK_MODE
        print(f"  - SSH_AVAILABLE: {SSH_AVAILABLE}")
        print(f"  - FORCE_MOCK_MODE: {FORCE_MOCK_MODE}")
        print(f"  - AIDE_REMOTE_MOCK_MODE env: {os.getenv('AIDE_REMOTE_MOCK_MODE', 'not set')}")
    except Exception as e:
        print(f"  ❌ エラー: {e}")
    
    # 3. 設定ファイルの確認
    print("\n3. 設定ファイルチェック:")
    if os.path.exists('config/servers.yaml'):
        print("  ✅ config/servers.yaml 存在")
        # サンプルサーバー設定を表示
        try:
            import yaml
            with open('config/servers.yaml', 'r') as f:
                config = yaml.safe_load(f)
                servers = config.get('server_groups', {})
                for group_name, group_data in servers.items():
                    print(f"  - グループ: {group_name}")
                    for server in group_data.get('servers', []):
                        print(f"    - {server.get('name')}: {server.get('hostname')}")
        except Exception as e:
            print(f"  ⚠️  servers.yaml 読み込みエラー: {e}")
    else:
        print("  ❌ config/servers.yaml が見つかりません")
    
    # 4. 接続テスト
    print("\n4. 接続テスト:")
    try:
        from src.remote.ssh_client import SSHClient, SSHConfig
        
        # テスト設定
        test_config = SSHConfig(
            hostname="test.example.com",
            username="test",
            key_filename="/tmp/test.pem"
        )
        
        client = SSHClient(test_config)
        print(f"  - クライアントモード: {'MOCK' if client.mock_mode else 'REAL'}")
        
        if client.mock_mode:
            print("  ⚠️  モックモードで動作中")
            print("     本番モードに切り替えるには:")
            print("     1. paramiko をインストール")
            print("     2. export AIDE_REMOTE_MOCK_MODE=false")
    except Exception as e:
        print(f"  ❌ 接続テストエラー: {e}")
    
    print("\n=== 診断完了 ===")

if __name__ == "__main__":
    diagnose_remote_functionality()
```

## 🚀 クイックフィックス

本番環境でリモート機能を有効にする最速の手順：

```bash
# 1. 依存関係をインストール
pip install -r requirements.txt

# 2. モックモードを無効化
export AIDE_REMOTE_MOCK_MODE=false

# 3. SSH鍵の権限を修正
chmod 600 ~/.ssh/aide_keys/*.pem

# 4. 接続テスト
aide remote list

# 5. 実際のサーバーでテスト
aide remote execute your-server-name "uptime"
```

## 📝 ログの確認

詳細なログを確認するには：

```bash
# ログレベルを DEBUG に設定
export AIDE_LOG_LEVEL=DEBUG

# 実行してログを確認
aide remote investigate server-name --type basic 2>&1 | tee remote_debug.log

# ログファイルを確認
grep -E "(SSH|Remote|Connection)" logs/aide.log
```

## 🆘 それでも解決しない場合

1. **環境情報を収集**:
   ```bash
   python --version
   pip list | grep -E "(paramiko|cryptography|bcrypt)"
   uname -a
   ```

2. **最小限のテストケース作成**:
   ```python
   import paramiko
   client = paramiko.SSHClient()
   client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
   client.connect('your-server', username='your-user', key_filename='your-key.pem')
   stdin, stdout, stderr = client.exec_command('uptime')
   print(stdout.read().decode())
   client.close()
   ```

3. **Issue を作成**: 上記の情報を含めて GitHub に Issue を作成してください。

## 🔐 セキュリティ注意事項

- SSH鍵は常に適切な権限（600）で保護してください
- 本番環境では `AutoAddPolicy` の使用を避け、known_hosts を適切に管理してください
- パスワード認証よりも鍵認証を推奨します
- ログにセンシティブな情報が含まれないよう注意してください