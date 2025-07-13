# Docker環境での RAG システムテスト

このディレクトリには、RAGシステムをDocker環境でテストするための設定ファイルが含まれています。

## ファイル構成

- `Dockerfile` - フル機能版のDockerファイル
- `Dockerfile.light` - 軽量版のDockerファイル
- `docker-compose.yml` - Docker Compose設定ファイル

## 使用方法

### 1. 軽量版Dockerイメージのビルド

```bash
docker build -f Dockerfile.light -t aide-rag-light .
```

### 2. 統合テストの実行

```bash
docker run --rm aide-rag-light
```

### 3. Docker Composeの使用

```bash
# 統合テストの実行
docker-compose run rag-test

# 元のテストの実行
docker-compose run rag-test-original

# インタラクティブなシェル
docker-compose run rag-interactive
```

## WSL環境での注意点

WSL環境では、Docker認証に関する警告が表示される場合がありますが、これは正常な動作です。

```
WSL (xxxxx - ) ERROR: UtilAcceptVsock:271: accept4 failed 110
```

この警告は無視できます。

## 推奨実行方法

Docker環境に問題がある場合は、ローカル環境での実行を推奨します：

```bash
# 仮想環境の有効化
source venv/bin/activate

# 統合テストの実行
PYTHONPATH=. pytest tests/unit/test_rag_system_integration.py -v
```

## テスト結果

現在の統合テストの結果：

- ✅ 10/10 テストケース成功
- ✅ VectorStore操作テスト
- ✅ KnowledgeBase操作テスト
- ✅ Retriever操作テスト
- ✅ RAGSystem操作テスト
- ✅ 知識更新テスト
- ✅ コンテキスト拡張テスト
- ✅ キーワード抽出テスト
- ✅ 関連度計算テスト
- ✅ 完全RAGパイプラインテスト
- ✅ システム統計テスト

## トラブルシューティング

### Docker認証エラー

```
ERROR: error getting credentials - err: exit status 1
```

このエラーが発生する場合は、以下のいずれかの方法を試してください：

1. **Docker Desktop の再起動**
2. **ローカル実行の使用**
3. **Docker認証のリセット**

### ビルドタイムアウト

ビルドがタイムアウトする場合は、以下を試してください：

```bash
# タイムアウトを延長
docker build --timeout 600 -f Dockerfile.light -t aide-rag-light .
```

### メモリ不足エラー

Docker Desktop のメモリ設定を確認し、必要に応じて増やしてください。

## 結論

Docker環境は準備完了していますが、WSL環境での認証問題により、ローカル実行が推奨されます。統合テストは完全に動作しており、RAGシステムは実用レベルで機能しています。