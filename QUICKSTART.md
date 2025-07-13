# AIDE クイックスタートガイド

## 🚀 依存関係のインストールと実行

### 1. 仮想環境で依存関係をインストール

AIDEは仮想環境が推奨されます。現在のvenv環境内で：

```bash
# 依存関係をインストール
pip install psutil chromadb crewai pydantic pyyaml python-dotenv pytest pytest-cov

# または pyproject.toml から一括インストール
pip install -e .
```

### 2. 代替インストール方法

#### 方法A: 仮想環境内でのpipインストール
```bash
# 現在のvenv環境内で実行
python -m pip install psutil chromadb crewai pydantic

# 全依存関係
python -m pip install psutil chromadb crewai pydantic pyyaml python-dotenv pytest pytest-cov
```

#### 方法B: システムインストール（非推奨）
```bash
# --break-system-packages フラグ使用（注意が必要）
python3 -m pip install --break-system-packages psutil chromadb crewai pydantic
```

#### 方法C: 要件ファイル使用
```bash
# requirements.txt を作成してインストール
pip install -r requirements.txt
```

## 🎯 デモの実行

### Phase 3 自律改善システムデモ
```bash
python demo_self_improvement.py
```

### その他のデモ
```bash
# 基本学習システム
python demo.py

# マルチエージェントシステム  
python demo_phase2.py

# RAGシステム
python demo_rag_system.py

# ツールシステム
python demo_tools.py
```

## 🔧 トラブルシューティング

### エラー: ModuleNotFoundError
**原因**: 必要なPythonパッケージが未インストール

**解決策**:
1. 仮想環境がアクティブか確認: `which python`
2. 依存関係をインストール: `pip install <パッケージ名>`
3. プロジェクトをeditableでインストール: `pip install -e .`

### よくある不足パッケージ
- `psutil`: システムリソース監視
- `chromadb`: ベクトルデータベース  
- `crewai`: マルチエージェントフレームワーク
- `pydantic`: データ検証
- `pyyaml`: YAML設定ファイル処理

### 制限機能での実行
一部パッケージが不足している場合でも、フォールバック機能により基本機能は動作します：

- `psutil`不足: システムリソース監視が制限
- `chromadb`不足: RAG機能が制限
- `crewai`不足: マルチエージェント機能が制限

## 💡 推奨インストール手順

### 完全インストール
```bash
# 1. 仮想環境確認
echo $VIRTUAL_ENV

# 2. パッケージ更新  
pip install --upgrade pip

# 3. 全依存関係インストール
pip install psutil chromadb crewai pydantic pyyaml python-dotenv pytest pytest-cov

# 4. プロジェクトインストール
pip install -e .

# 5. デモ実行
python demo_self_improvement.py
```

### 最小インストール（RAG機能のみ）
```bash
pip install psutil pydantic pyyaml
python demo_self_improvement.py
```

## 📋 システム要件

- Python 3.8+
- 仮想環境推奨
- 最低512MB RAM
- Claude Code（オプション、LLM機能用）

## 🎉 成功の確認

デモ実行時に以下が表示されれば成功：

```
🚀 AIDE Phase 3 自律改善システム初期化中...
✅ RAGシステム初期化完了
✅ Claude Codeクライアント初期化完了
🎯 自律改善システム準備完了！
```