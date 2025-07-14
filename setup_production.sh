#!/bin/bash
#
# AIDE 本番環境セットアップスクリプト
#
# このスクリプトは、AIDE を本番環境で動作させるために必要な
# ディレクトリ構造の作成と初期設定を行います。
#

set -e  # エラーで停止

echo "=========================================="
echo "AIDE 本番環境セットアップ"
echo "=========================================="

# 1. Python バージョン確認
echo -e "\n1. Python バージョン確認..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python version: $python_version"

# 2. 必要なディレクトリを作成
echo -e "\n2. 必要なディレクトリを作成..."
directories=(
    "data"
    "data/vectorstore"
    "data/knowledge_base"
    "logs"
    "backups"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "   ✅ Created: $dir"
    else
        echo "   ⚠️  Already exists: $dir"
    fi
done

# 3. 環境設定ファイルの準備
echo -e "\n3. 環境設定ファイルの準備..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "   ✅ .env ファイルを作成しました"
        echo "   ⚠️  .env ファイルを編集して本番環境の設定を行ってください"
    else
        echo "   ❌ .env.example が見つかりません"
    fi
else
    echo "   ⚠️  .env ファイルは既に存在します"
fi

# 4. 依存関係のインストール
echo -e "\n4. Python 依存関係のインストール..."
echo "   実行中: pip install -r requirements.txt"
pip install -r requirements.txt

# 5. 権限設定
echo -e "\n5. ディレクトリ権限の設定..."
chmod 755 data logs backups
chmod 755 data/vectorstore data/knowledge_base
echo "   ✅ ディレクトリ権限を設定しました"

# 6. SSH 鍵ディレクトリの準備（リモート機能用）
echo -e "\n6. SSH 鍵ディレクトリの準備..."
ssh_key_dir="$HOME/.ssh/aide_keys"
if [ ! -d "$ssh_key_dir" ]; then
    mkdir -p "$ssh_key_dir"
    chmod 700 "$ssh_key_dir"
    echo "   ✅ SSH鍵ディレクトリを作成: $ssh_key_dir"
    echo "   ⚠️  SSH鍵を $ssh_key_dir に配置し、chmod 600 で権限設定してください"
else
    echo "   ⚠️  SSH鍵ディレクトリは既に存在: $ssh_key_dir"
fi

# 7. Claude Code CLI の確認
echo -e "\n7. Claude Code CLI の確認..."
if command -v claude &> /dev/null; then
    claude_version=$(claude --version 2>&1 || echo "version unknown")
    echo "   ✅ Claude Code CLI が見つかりました: $claude_version"
    echo "   ⚠️  'claude auth' で認証を設定してください"
else
    echo "   ❌ Claude Code CLI が見つかりません"
    echo "      インストール方法: https://docs.anthropic.com/en/docs/claude-code"
fi

# 8. 診断の実行
echo -e "\n8. 本番環境準備状況の診断..."
if [ -f "check_production_ready.py" ]; then
    echo "   診断スクリプトを実行します..."
    python3 check_production_ready.py
else
    echo "   ⚠️  診断スクリプトが見つかりません"
fi

echo -e "\n=========================================="
echo "セットアップ完了"
echo "=========================================="
echo ""
echo "次のステップ:"
echo "1. .env ファイルを編集して本番環境の設定を行う"
echo "2. Claude Code CLI で認証: claude auth"
echo "3. SSH鍵を ~/.ssh/aide_keys/ に配置（リモート機能を使用する場合）"
echo "4. python cli.py init でシステムを初期化"
echo "5. python cli.py status でシステム状態を確認"
echo ""
echo "詳細は PRODUCTION_SETUP.md を参照してください。"