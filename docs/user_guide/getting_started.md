# AIDE ユーザーガイド - はじめに

## 概要

AIDE (Autonomous Intelligent Development Environment) は、ソフトウェア開発環境の自動診断・最適化・改善を行うインテリジェントシステムです。このガイドでは、AIDE の基本的な使い方から高度な機能まで、ユーザーの皆様が効果的にシステムを活用できるよう詳しく説明します。

## 目次

1. [AIDE とは](#aide-とは)
2. [システム要件](#システム要件)
3. [インストールと初期設定](#インストールと初期設定)
4. [基本的な使い方](#基本的な使い方)
5. [主要機能の概要](#主要機能の概要)
6. [クイックスタートガイド](#クイックスタートガイド)
7. [次のステップ](#次のステップ)

## AIDE とは

### 主な特徴

- **自動診断**: システムのパフォーマンス、設定、リソース使用状況を自動的に分析
- **インテリジェント最適化**: AI 駆動の最適化提案と自動実行
- **リアルタイム監視**: システム状態の継続的な監視とアラート
- **自動回復**: エラーの自動検出と回復処理
- **設定管理**: 動的な設定変更とプロファイル管理

### 対象ユーザー

- **ソフトウェア開発者**: 開発環境の最適化と生産性向上
- **システム管理者**: インフラの監視と保守の自動化
- **DevOps エンジニア**: CI/CD パイプラインの最適化
- **プロジェクトマネージャー**: 開発プロセスの可視化と改善

## システム要件

### 最小要件

- **OS**: Linux, macOS, Windows 10+
- **Python**: 3.8 以上
- **メモリ**: 2GB RAM
- **ストレージ**: 1GB 空き容量
- **ネットワーク**: インターネット接続（オプション）

### 推奨要件

- **OS**: Linux (Ubuntu 20.04+, CentOS 8+)
- **Python**: 3.10 以上
- **メモリ**: 8GB RAM
- **ストレージ**: 10GB 空き容量（SSD 推奨）
- **CPU**: 4コア以上

### 必要なパッケージ

```bash
# 基本パッケージ
pip install psutil asyncio typing dataclasses

# オプションパッケージ（高性能化）
pip install uvloop aiohttp
```

## インストールと初期設定

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-org/aide.git
cd aide
```

### 2. 依存関係のインストール

```bash
# Python 仮想環境の作成（推奨）
python -m venv aide_env
source aide_env/bin/activate  # Linux/macOS
# aide_env\Scripts\activate  # Windows

# 依存関係のインストール
pip install -r requirements.txt
```

### 3. 初期設定

```bash
# 設定ディレクトリの作成
mkdir -p config logs

# デフォルト設定の生成
python -c "
import json
import os

# 基本設定
config = {
    'system': {
        'name': 'AIDE',
        'version': '3.3.0',
        'environment': 'development'
    },
    'logging': {
        'level': 'INFO',
        'file': 'logs/aide.log',
        'rotation': True
    },
    'monitoring': {
        'enabled': True,
        'health_check_interval': 30,
        'metrics_retention_hours': 24
    },
    'optimization': {
        'auto_enabled': True,
        'level': 'balanced',
        'schedule_interval': 3600
    }
}

os.makedirs('config', exist_ok=True)
with open('config/default.json', 'w') as f:
    json.dump(config, f, indent=2)

print('設定ファイル作成完了: config/default.json')
"
```

### 4. システムの動作確認

```python
# システム初期化テスト
python -c "
import sys
sys.path.append('.')

try:
    from src.config import get_config_manager
    from src.logging import get_logger
    
    # 設定管理初期化
    config = get_config_manager()
    print(f'✓ 設定管理初期化完了: {config.get_profile().name}')
    
    # ログシステム初期化
    logger = get_logger('test')
    logger.info('システム初期化テスト')
    print('✓ ログシステム初期化完了')
    
    print('\\n🎉 AIDE システム初期化成功！')
    
except Exception as e:
    print(f'✗ 初期化エラー: {e}')
    print('設定やインストールを確認してください。')
"
```

## 基本的な使い方

### システム診断の実行

```python
from src.diagnosis.intelligent_diagnostics import get_intelligent_diagnostics

# 診断システムの取得
diagnostics = get_intelligent_diagnostics()

# システム診断の実行
diagnosis_result = diagnostics.diagnose_system()

# 結果の表示
print(f"診断完了: {len(diagnosis_result.recommendations)}件の推奨事項")
for recommendation in diagnosis_result.recommendations:
    print(f"- {recommendation}")
```

### システム最適化の実行

```python
import asyncio
from src.optimization.system_optimizer import get_system_optimizer

async def run_optimization():
    # 最適化システムの取得
    optimizer = get_system_optimizer()
    
    # 最適化の実行
    summary = await optimizer.run_optimization_cycle()
    
    # 結果の表示
    print(f"最適化完了: {len(summary.improvements)}件の改善")
    for improvement in summary.improvements:
        print(f"- {improvement.description} (効果: {improvement.impact_score})")

# 非同期実行
asyncio.run(run_optimization())
```

### システム監視の開始

```python
from src.dashboard.enhanced_monitor import get_enhanced_monitor

# 監視システムの取得
monitor = get_enhanced_monitor()

# 監視開始
monitor.start_monitoring()
print("システム監視開始")

# システム状態確認
health = monitor.get_system_health()
if health:
    print(f"システム状態: {health.overall_status.value}")
    print(f"ヘルススコア: {health.overall_score}")
    
    if health.active_issues:
        print("アクティブな問題:")
        for issue in health.active_issues:
            print(f"- {issue['description']}")
else:
    print("システム状態を取得できませんでした")
```

## 主要機能の概要

### 1. 自動診断エンジン

**機能**: システムの包括的な分析と問題の特定

**使用例**:
```python
# 基本診断
diagnosis = diagnostics.diagnose_system()

# 特定コンポーネントの診断
performance_diagnosis = diagnostics.diagnose_performance()
security_diagnosis = diagnostics.diagnose_security()
```

**主な診断項目**:
- パフォーマンス分析
- リソース使用状況
- 設定の妥当性
- セキュリティ状態
- エラー傾向分析

### 2. インテリジェント最適化

**機能**: AI 駆動の自動最適化とチューニング

**使用例**:
```python
# 全体最適化
await optimizer.run_optimization_cycle()

# 特定カテゴリの最適化
await optimizer.run_optimization_cycle(['memory_optimization'])
await optimizer.run_optimization_cycle(['cpu_optimization'])

# 最適化レベルの設定
optimizer.set_optimization_level('conservative')  # 保守的
optimizer.set_optimization_level('balanced')      # バランス
optimizer.set_optimization_level('aggressive')    # 積極的
```

### 3. リアルタイム監視

**機能**: システム状態の継続的な監視とアラート

**使用例**:
```python
# 監視開始
monitor.start_monitoring()

# システム状態取得
health = monitor.get_system_health()

# 監視概要取得
summary = monitor.get_monitoring_summary()

# カスタムアラート設定
from src.dashboard.enhanced_monitor import AlertRule
custom_alert = AlertRule(
    rule_id="cpu_high",
    name="CPU使用率高",
    description="CPU使用率が80%を超えました",
    metric_name="cpu_usage",
    condition="> 80",
    severity="high"
)
monitor.add_custom_alert_rule(custom_alert)
```

### 4. エラー処理・回復

**機能**: 自動エラー検出と回復処理

**使用例**:
```python
from src.resilience.error_handler import get_error_handler

# エラーハンドラーの使用
error_handler = get_error_handler()

# エラー統計確認
stats = error_handler.get_error_statistics()
print(f"総エラー数: {stats['error_stats']['total_errors']}")
print(f"自動回復数: {stats['error_stats']['auto_resolved_errors']}")

# エラーコンテキストの使用
with error_handler.error_context('my_component', 'my_function'):
    # エラーが発生する可能性のある処理
    risky_operation()
```

### 5. 設定管理

**機能**: 動的設定管理とプロファイル切り替え

**使用例**:
```python
from src.config import get_config_manager

config = get_config_manager()

# 設定値の取得
log_level = config.get('logging.level', 'INFO')

# 設定値の変更
config.set('monitoring.enabled', True)

# プロファイルの切り替え
config.load_profile('production')
config.save_profile('my_custom_profile')
```

## クイックスタートガイド

### 5分で始める AIDE

以下の手順で、5分でAIDEの基本機能を体験できます：

```python
#!/usr/bin/env python3
"""
AIDE クイックスタート - 5分体験プログラム
"""

import asyncio
import time

def quick_start_demo():
    print("🚀 AIDE クイックスタートデモ")
    print("=" * 50)
    
    # 1. システム初期化
    print("\n1. システム初期化中...")
    from src.config import get_config_manager
    from src.logging import get_logger
    
    config = get_config_manager()
    logger = get_logger('quickstart')
    logger.info("クイックスタートデモ開始")
    print("✓ 初期化完了")
    
    # 2. システム診断
    print("\n2. システム診断実行中...")
    from src.diagnosis.intelligent_diagnostics import get_intelligent_diagnostics
    
    diagnostics = get_intelligent_diagnostics()
    diagnosis_result = diagnostics.diagnose_system()
    
    print(f"✓ 診断完了: {len(diagnosis_result.recommendations)}件の推奨事項")
    if diagnosis_result.recommendations:
        print("主な推奨事項:")
        for i, rec in enumerate(diagnosis_result.recommendations[:3], 1):
            print(f"  {i}. {rec}")
    
    # 3. 監視開始
    print("\n3. 監視システム開始中...")
    from src.dashboard.enhanced_monitor import get_enhanced_monitor
    
    monitor = get_enhanced_monitor()
    monitor.start_monitoring()
    
    # 少し待ってから状態確認
    time.sleep(3)
    health = monitor.get_system_health()
    
    if health:
        print(f"✓ 監視開始完了")
        print(f"  システム状態: {health.overall_status.value}")
        print(f"  ヘルススコア: {health.overall_score:.1f}")
    
    # 4. 最適化実行
    print("\n4. システム最適化実行中...")
    
    async def run_quick_optimization():
        from src.optimization.system_optimizer import get_system_optimizer
        optimizer = get_system_optimizer()
        
        # メモリ最適化のみ実行（高速）
        summary = await optimizer.run_optimization_cycle(['memory_optimization'])
        return summary
    
    optimization_summary = asyncio.run(run_quick_optimization())
    print(f"✓ 最適化完了: {len(optimization_summary.improvements)}件の改善")
    
    # 5. 結果サマリー
    print("\n5. デモ結果サマリー")
    print("=" * 50)
    
    # エラー統計
    from src.resilience.error_handler import get_error_handler
    error_stats = get_error_handler().get_error_statistics()
    
    print(f"📊 システム統計:")
    print(f"  - 診断推奨事項: {len(diagnosis_result.recommendations)}件")
    print(f"  - システムヘルス: {health.overall_score:.1f}/100" if health else "  - システムヘルス: 取得不可")
    print(f"  - 最適化改善: {len(optimization_summary.improvements)}件")
    print(f"  - 総エラー数: {error_stats['error_stats']['total_errors']}件")
    
    print(f"\n🎉 クイックスタートデモ完了!")
    print(f"📚 詳細な使い方は docs/user_guide/ を参照してください。")
    
    # 監視停止
    monitor.stop_monitoring_system()
    print("✓ 監視システム停止")

if __name__ == "__main__":
    quick_start_demo()
```

このスクリプトを `quickstart_demo.py` として保存し、実行してください：

```bash
python quickstart_demo.py
```

### 基本的なワークフロー

1. **毎日の確認**:
   ```python
   # 日次ヘルスチェック
   health = monitor.get_system_health()
   print(f"今日のヘルススコア: {health.overall_score}")
   ```

2. **週次の最適化**:
   ```python
   # 週次最適化実行
   summary = await optimizer.run_optimization_cycle()
   ```

3. **月次の包括分析**:
   ```python
   # 月次総合診断
   comprehensive_diagnosis = diagnostics.diagnose_system()
   trends = error_handler.get_error_trends(hours=24*30)  # 30日間
   ```

## よくある質問 (FAQ)

### Q: AIDE はどのような環境で使用できますか？

A: AIDE は以下の環境で動作します：
- **開発環境**: ローカル開発マシン、Docker コンテナ
- **ステージング環境**: テスト・統合環境
- **本番環境**: プロダクションサーバー（設定調整推奨）

### Q: システムに負荷をかけませんか？

A: AIDE は軽量設計されており、通常の監視では CPU 使用率 1-2% 程度です。最適化レベルを調整することで負荷をコントロールできます。

### Q: 設定をカスタマイズできますか？

A: はい。JSON ベースの設定ファイルで詳細にカスタマイズ可能です。環境別の設定プロファイルもサポートしています。

### Q: エラーが発生した場合の対処法は？

A: エラー発生時は以下を確認してください：
1. ログファイル（`logs/aide.log`）の確認
2. システム要件の再確認
3. [トラブルシューティングガイド](../operations/troubleshooting_guide.md)の参照

## 次のステップ

AIDE の基本操作を理解したら、以下の高度な機能を探索してください：

1. **[詳細な機能ガイド](advanced_features.md)**: 高度な設定と機能
2. **[API リファレンス](../api/README.md)**: プログラマティックな使用
3. **[設定ガイド](../operations/configuration_guide.md)**: 詳細な設定方法
4. **[統合ガイド](integration_guide.md)**: 他システムとの統合

## サポート

### コミュニティ

- **GitHub Issues**: バグレポートと機能要求
- **Discord**: リアルタイムサポート
- **フォーラム**: 技術的な質問と議論

### ドキュメント

- **ユーザーガイド**: 本ドキュメントシリーズ
- **運用ガイド**: システム管理者向け
- **開発者ガイド**: 拡張とカスタマイズ

### コントリビューション

AIDE は OSS プロジェクトです。皆様の貢献をお待ちしています：
- バグレポート
- 機能提案
- ドキュメント改善
- コードコントリビューション

---

AIDE を使い始めるための準備が整いました。ご質問がありましたら、お気軽にコミュニティまでお問い合わせください！