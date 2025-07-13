# 🚀 AIDE 本番環境セットアップガイド

## 📋 概要

このガイドでは、AIDE をモックモードから本番環境に移行するための詳細な手順を説明します。

## 🎯 前提条件

### システム要件
- **OS**: Linux (Ubuntu 20.04+推奨) / macOS / Windows WSL2
- **Python**: 3.8 以上 (3.10+ 推奨)
- **RAM**: 16GB以上 (32GB推奨)
- **Storage**: 50GB以上の空き容量
- **Network**: インターネット接続 (AI API アクセス用)

### 必要なサービス
- **AI API**: OpenAI API または Azure OpenAI (必須)
- **PostgreSQL**: 本格運用時推奨 (SQLite でも可)
- **Redis**: キャッシュ・セッション管理用 (オプション)

## 🔧 ステップ1: 環境設定ファイルの作成

### 1.1 環境設定ファイルをコピー
```bash
cp .env.example .env
```

### 1.2 必須設定項目の編集

#### Claude Code CLI 設定 (最重要)
```bash
# Claude Code CLI 設定
AIDE_CLAUDE_COMMAND=claude
AIDE_CLAUDE_TIMEOUT=120
AIDE_ENV=production
```

**Claude Code CLI セットアップ手順:**
1. **Claude Code CLI インストール確認**: `claude --version`
2. **Claude Code CLI 認証**: `claude auth`
   - Claude Code CLI が独自の認証プロセスを実行
   - ブラウザでログイン画面が開きます
   - Anthropic アカウントでログイン
3. **認証確認**: `claude` でテスト実行
4. **環境変数設定は不要** - Claude Code CLI が認証を管理

**重要**: AIDE は Claude Code CLI を直接呼び出すため、API キーの環境変数設定は不要です。

#### 基本システム設定
```bash
AIDE_ENV=production
AIDE_DEBUG=false
AIDE_LOG_LEVEL=INFO
```

#### セキュリティ設定
```bash
# 強力なランダム文字列を生成して設定
AIDE_SECRET_KEY=$(openssl rand -hex 32)
AIDE_JWT_SECRET=$(openssl rand -hex 32)
```

## 🗄️ ステップ2: データベース設定

### 2.1 SQLite設定 (小規模運用)
```bash
# .env ファイル
AIDE_KNOWLEDGE_DB_PATH=./data/knowledge.db
AIDE_KNOWLEDGE_DB_TYPE=sqlite
```

### 2.2 PostgreSQL設定 (推奨・本格運用)

#### PostgreSQLインストール (Ubuntu例)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### データベース設定
```bash
sudo -u postgres psql
CREATE DATABASE aide_production;
CREATE USER aide_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE aide_production TO aide_user;
\q
```

#### 環境変数設定
```bash
# .env ファイル
AIDE_DB_TYPE=postgresql
AIDE_DB_HOST=localhost
AIDE_DB_PORT=5432
AIDE_DB_NAME=aide_production
AIDE_DB_USER=aide_user
AIDE_DB_PASSWORD=your_secure_password
```

## 📦 ステップ3: 依存関係のインストール

### 3.1 本番用追加パッケージ
```bash
# 本番用依存関係を requirements.txt に追加
echo "
# 本番環境用追加パッケージ
psycopg2-binary>=2.9.0
redis>=4.5.0
gunicorn>=20.1.0
uvicorn[standard]>=0.20.0
prometheus-client>=0.16.0
" >> requirements_production.txt

# インストール
pip install -r requirements.txt -r requirements_production.txt
```

### 3.2 システムサービス用パッケージ
```bash
# Redis インストール (Ubuntu例)
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Nginx インストール (リバースプロキシ用)
sudo apt install nginx
```

## 🔄 ステップ4: データディレクトリの準備

```bash
# データディレクトリ作成
mkdir -p data/vectorstore
mkdir -p data/knowledge_base
mkdir -p logs
mkdir -p backups

# 権限設定
chmod 755 data logs backups
chmod 644 .env
```

## 🚀 ステップ5: 本番モード起動設定

### 5.1 設定マネージャーの修正

**src/config/config_manager.py** を編集：

```python
import os
from typing import Dict, Any
from pathlib import Path

class ConfigManager:
    def __init__(self):
        self.load_env_file()
        
    def load_env_file(self):
        """環境変数ファイルを読み込み"""
        env_file = Path('.env')
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
    
    def get_config(self) -> Dict[str, Any]:
        """設定を取得"""
        return {
            "system": {
                "name": "AIDE",
                "version": "3.3.0",
                "environment": os.getenv("AIDE_ENV", "development"),
                "debug": os.getenv("AIDE_DEBUG", "false").lower() == "true"
            },
            "ai": {
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
                "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "4096")),
                "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
            },
            "database": {
                "type": os.getenv("AIDE_DB_TYPE", "sqlite"),
                "path": os.getenv("AIDE_KNOWLEDGE_DB_PATH", "./data/knowledge.db"),
                "host": os.getenv("AIDE_DB_HOST", "localhost"),
                "port": int(os.getenv("AIDE_DB_PORT", "5432")),
                "name": os.getenv("AIDE_DB_NAME", "aide"),
                "user": os.getenv("AIDE_DB_USER", "aide"),
                "password": os.getenv("AIDE_DB_PASSWORD", "")
            },
            "web": {
                "host": os.getenv("AIDE_WEB_HOST", "0.0.0.0"),
                "port": int(os.getenv("AIDE_WEB_PORT", "8080")),
                "debug": os.getenv("AIDE_WEB_DEBUG", "false").lower() == "true"
            }
        }

def get_config_manager():
    return ConfigManager()
```

### 5.2 本番モード検出の実装

**cli.py** の修正：

```python
def try_import_real_modules():
    """実際のモジュールのインポートを試行"""
    # 環境変数チェック
    if os.getenv("AIDE_ENV") == "production" and os.getenv("OPENAI_API_KEY"):
        print("🚀 本番モードで起動します...")
        try:
            # 実際のモジュールをインポート
            from src.config.config_manager import get_config_manager as real_config
            from src.agents.ai_agent import get_ai_agent as real_ai_agent
            # ... 他の実装
            print("✅ 本番モジュール読み込み完了")
            return True
        except ImportError as e:
            print(f"⚠️ 本番モジュール読み込み失敗: {e}")
            print("📋 モックモードで継続...")
    else:
        print("📋 開発モードまたは設定不足のため、モックモードで動作します")
    
    return False
```

## 🔐 ステップ6: セキュリティ設定

### 6.1 ファイアウォール設定
```bash
# UFW設定例
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 8080/tcp    # AIDE Web Interface
sudo ufw allow 9090/tcp    # Metrics
sudo ufw --force enable
```

### 6.2 SSL/TLS証明書設定 (Nginx例)
```bash
# Let's Encrypt証明書取得
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 6.3 Nginx設定例
```nginx
# /etc/nginx/sites-available/aide
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📊 ステップ7: 監視設定

### 7.1 systemd サービス設定
```bash
# /etc/systemd/system/aide.service
[Unit]
Description=AIDE AI Assistant
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=aide
WorkingDirectory=/opt/aide
Environment=PATH=/opt/aide/venv/bin
ExecStart=/opt/aide/venv/bin/python cli.py daemon
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 7.2 ログローテーション設定
```bash
# /etc/logrotate.d/aide
/opt/aide/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 aide aide
    postrotate
        systemctl reload aide
    endscript
}
```

## 🧪 ステップ8: 本番環境テスト

### 8.1 Claude Code CLI 確認
```bash
# Claude Code CLI 動作確認
claude --version

# 認証状態確認
claude "Hello, AIDE!" || echo "認証が必要: claude auth を実行してください"

# AIDE 環境変数確認
python -c "
import os
print('Environment:', os.getenv('AIDE_ENV'))
print('Claude Command:', os.getenv('AIDE_CLAUDE_COMMAND', 'claude'))
print('DB Type:', os.getenv('AIDE_DB_TYPE', 'sqlite'))
"
```

### 8.2 AIDE システムテスト
```bash
# 基本動作テスト（モックモード）
python cli.py init

# システム状態確認
python cli.py status

# AI エージェントテスト（モックモード）
python cli.py agent ai --query "システムの動作確認"

# 本番モード設定確認
AIDE_ENV=production python cli.py init
```

### 8.3 Claude Code 連携テスト
```bash
# Claude Code が利用可能な場合の実際のテスト
# 注意: 実際のClaude APIを使用するため慎重に実行
claude "AIDE システムの動作確認テストです"
```

## 🚀 ステップ9: 本番デプロイメント

### 9.1 サービス開始
```bash
sudo systemctl daemon-reload
sudo systemctl start aide
sudo systemctl enable aide
sudo systemctl status aide
```

### 9.2 動作確認
```bash
# システム状態確認
python cli.py status

# ヘルスチェック
curl http://localhost:8080/health

# メトリクス確認
curl http://localhost:9090/metrics
```

## 📈 ステップ10: 運用・保守

### 10.1 定期バックアップ設定
```bash
# バックアップスクリプト例
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/aide/backups"

# データベースバックアップ
pg_dump aide_production > "$BACKUP_DIR/db_backup_$DATE.sql"

# 設定ファイルバックアップ
tar -czf "$BACKUP_DIR/config_backup_$DATE.tar.gz" .env config/

# 古いバックアップ削除（30日以上）
find "$BACKUP_DIR" -type f -mtime +30 -delete
```

### 10.2 監視アラート設定
```bash
# .env での監視設定
AIDE_SLACK_ENABLED=true
AIDE_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
AIDE_EMAIL_ENABLED=true
AIDE_EMAIL_TO=admin@your-domain.com
```

## ❌ トラブルシューティング

### よくある問題と解決方法

**1. Claude Code CLI 接続エラー**
```bash
# Claude Code CLI 確認
claude --version

# 認証状態確認
claude auth

# 簡単なテスト
claude "Hello"
```

**2. データベース接続エラー**
```bash
# PostgreSQL状態確認
sudo systemctl status postgresql
# 接続テスト
psql -h localhost -U aide_user -d aide_production
```

**3. メモリ不足エラー**
```bash
# メモリ使用量確認
free -h
# スワップ追加
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 📝 本番環境チェックリスト

- [ ] Claude Code CLI インストール・認証完了
- [ ] `.env` ファイル作成・設定完了
- [ ] Claude Code CLI 動作テスト完了
- [ ] データベース設定・接続確認
- [ ] セキュリティ設定（ファイアウォール、SSL）
- [ ] システムサービス設定
- [ ] 監視・アラート設定
- [ ] バックアップ設定
- [ ] 本番起動テスト完了
- [ ] ドキュメント整備

## 🆘 サポート

本番環境で問題が発生した場合：

1. **ログ確認**: `tail -f logs/aide.log`
2. **システム状態**: `python cli.py status`
3. **GitHub Issues**: https://github.com/0xchoux1/aide/issues

---

**本番環境での AIDE 運用準備完了！** 🎉