# 📦 AIDE インストールガイド

## 🚀 クイックスタート（5分でセットアップ）

```bash
# 1. リポジトリをクローン
git clone https://github.com/0xchoux1/aide.git
cd aide

# 2. Python仮想環境を作成
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. セットアップスクリプトを実行
./setup_production.sh

# 4. システムを初期化
python cli.py init
```

## 📋 システム要件

### 最小要件
- **OS**: Linux (Ubuntu 20.04+) / macOS / Windows WSL2
- **Python**: 3.8以上
- **メモリ**: 8GB RAM
- **ストレージ**: 10GB空き容量

### 推奨要件
- **Python**: 3.10以上
- **メモリ**: 16GB RAM
- **ストレージ**: 50GB空き容量

## 📥 詳細インストール手順

### 1. Python環境の準備

```bash
# Pythonバージョン確認
python3 --version  # 3.8以上であることを確認

# pip を最新版に更新
python3 -m pip install --upgrade pip

# 仮想環境を作成（推奨）
python3 -m venv venv
source venv/bin/activate
```

### 2. 依存関係のインストール

```bash
# 基本依存関係をインストール
pip install -r requirements.txt

# インストールを確認
pip list
```

必須パッケージ:
- `chromadb` - ベクターデータベース（RAGシステム）
- `paramiko` - SSH接続（リモート機能）
- `psutil` - システム監視
- `requests` - HTTP通信
- `pyyaml` - 設定ファイル処理

### 3. Claude Code CLI のセットアップ

AIDEはClaude Code CLIを使用してAI機能を提供します。

```bash
# Claude Code CLI のインストール状況確認
claude --version

# Claude Code CLI がない場合はインストール
# インストール方法: https://docs.anthropic.com/en/docs/claude-code

# 認証設定
claude auth
```

### 4. 環境設定

```bash
# 環境設定ファイルをコピー
cp .env.example .env

# .env ファイルを編集
# 最低限、以下を設定:
# - AIDE_ENV=production
# - AIDE_CLAUDE_COMMAND=claude
```

### 5. ディレクトリ構造の作成

```bash
# 必要なディレクトリを作成
mkdir -p data/vectorstore data/knowledge_base logs backups

# 権限を設定
chmod 755 data logs backups
```

### 6. 初期化と動作確認

```bash
# システムを初期化
python cli.py init

# 動作確認
python cli.py status

# ヘルプを表示
python cli.py --help
```

## 🔧 オプション機能のセットアップ

### リモートサーバー機能

```bash
# SSH鍵ディレクトリを作成
mkdir -p ~/.ssh/aide_keys
chmod 700 ~/.ssh/aide_keys

# SSH鍵を配置
cp your-key.pem ~/.ssh/aide_keys/
chmod 600 ~/.ssh/aide_keys/*.pem

# サーバー設定を編集
vim config/servers.yaml

# リモート機能をテスト
aide remote list
```

### Webダッシュボード

```bash
# 追加パッケージをインストール
pip install uvicorn gunicorn

# ダッシュボードを起動
python -m src.dashboard.dashboard_server
```

## 🐳 Docker インストール（代替方法）

```bash
# Dockerイメージをビルド
docker build -t aide:latest .

# コンテナを起動
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e AIDE_ENV=production \
  aide:latest
```

## ❓ トラブルシューティング

### インストール診断

```bash
# 本番環境準備状況を診断
python check_production_ready.py

# リモート機能を診断
python diagnose_remote.py
```

### よくある問題

1. **`ModuleNotFoundError`**
   ```bash
   pip install -r requirements.txt
   ```

2. **Claude Code CLI が見つからない**
   ```bash
   # PATHに追加されているか確認
   which claude
   # 環境変数で指定
   export AIDE_CLAUDE_COMMAND=/path/to/claude
   ```

3. **権限エラー**
   ```bash
   # ディレクトリ権限を修正
   chmod -R 755 data logs
   ```

## 📖 次のステップ

1. [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md) - 本番環境の詳細設定
2. [README.md](README.md) - 機能の使い方
3. [REMOTE_TROUBLESHOOTING.md](REMOTE_TROUBLESHOOTING.md) - リモート機能のトラブルシューティング

## 🆘 サポート

問題が解決しない場合は、以下の情報と共にIssueを作成してください：

```bash
# システム情報を収集
python -c "import sys; print(sys.version)"
pip list
uname -a
```

GitHubリポジトリ: https://github.com/0xchoux1/aide