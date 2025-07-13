# Python 3.13をベースとする
FROM python:3.13-slim

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリの設定
WORKDIR /app

# Pythonの依存関係ファイルをコピー
COPY requirements.txt .

# Pythonパッケージのインストール（タイムアウトを長くし、インデックスを指定）
RUN pip install --no-cache-dir --timeout=300 --index-url https://pypi.org/simple/ -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# テスト用のディレクトリを作成
RUN mkdir -p /app/test_data

#環境変数の設定
ENV PYTHONPATH=/app
ENV CHROMA_DB_PATH=/app/test_data
ENV PYTHONUNBUFFERED=1

# ヘルスチェック用のスクリプト
RUN echo '#!/bin/bash\npython -c "import chromadb; print(\"ChromaDB imported successfully\")"' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# デフォルトコマンド
CMD ["python", "-m", "pytest", "tests/unit/test_rag_system_integration.py", "-v", "--tb=short"]