# AIDE システム運用管理ガイド

## 概要

このドキュメントは、AIDE (Autonomous Intelligent Development Environment) システムの運用管理者向けの包括的なガイドです。システムの監視、保守、トラブルシューティング、最適化に関する詳細な手順を提供します。

## 目次

1. [システム概要](#システム概要)
2. [日常監視](#日常監視)
3. [ヘルス管理](#ヘルス管理)
4. [パフォーマンス監視](#パフォーマンス監視)
5. [エラー管理](#エラー管理)
6. [最適化管理](#最適化管理)
7. [トラブルシューティング](#トラブルシューティング)
8. [定期メンテナンス](#定期メンテナンス)
9. [セキュリティ管理](#セキュリティ管理)
10. [バックアップ・リストア](#バックアップリストア)

## システム概要

### アーキテクチャ概要

AIDE システムは以下の主要コンポーネントで構成されています：

- **診断エンジン**: システム分析とパフォーマンス診断
- **改善エンジン**: 自動最適化と改善提案
- **ダッシュボード**: リアルタイム監視と制御
- **レジリエンス**: エラーハンドリング、サーキットブレーカー、リトライ、フォルバック
- **設定管理**: 動的設定とプロファイル管理
- **監査・ログ**: 包括的なログ記録と監査証跡

### コア機能

- 自動システム診断
- パフォーマンス最適化
- エラー自動回復
- リアルタイム監視
- 設定動的更新
- セキュリティ監査

## 日常監視

### システム状態確認

```python
from src.dashboard.enhanced_monitor import get_enhanced_monitor

# 強化監視システムの状態確認
monitor = get_enhanced_monitor()

# システムヘルス取得
health = monitor.get_system_health()
print(f"システム状態: {health.overall_status.value}")
print(f"ヘルススコア: {health.overall_score}")

# 監視概要確認
summary = monitor.get_monitoring_summary()
print(f"監視モード: {summary['monitoring_mode']}")
print(f"アクティブ問題数: {len(health.active_issues)}")
```

### 推奨監視頻度

| 項目 | 頻度 | 重要度 |
|------|------|--------|
| システムヘルス | 5分毎 | 高 |
| パフォーマンスメトリクス | 15分毎 | 高 |
| エラー統計 | 10分毎 | 高 |
| リソース使用量 | 5分毎 | 中 |
| セキュリティイベント | 1分毎 | 高 |

### アラート設定

```python
from src.dashboard.enhanced_monitor import AlertRule, AlertRule

# カスタムアラートルール設定例
critical_alert = AlertRule(
    rule_id="system_critical",
    name="システム重要アラート",
    description="システムヘルススコアが50を下回りました",
    metric_name="health_score",
    condition="< 50",
    severity="critical",
    cooldown_minutes=2
)

monitor.add_custom_alert_rule(critical_alert)
```

## ヘルス管理

### コンポーネント別ヘルス確認

```python
from src.resilience.error_handler import get_error_handler
from src.resilience.circuit_breaker import get_circuit_breaker_manager
from src.resilience.retry_manager import get_retry_manager
from src.resilience.fallback_system import get_fallback_system

# エラーハンドラー統計
error_stats = get_error_handler().get_error_statistics()
print(f"総エラー数: {error_stats['error_stats']['total_errors']}")
print(f"自動解決数: {error_stats['error_stats']['auto_resolved_errors']}")

# サーキットブレーカー状態
circuit_summary = get_circuit_breaker_manager().get_health_summary()
print(f"正常サーキット: {circuit_summary['healthy_circuits']}")
print(f"異常サーキット: {circuit_summary['unhealthy_circuits']}")

# リトライシステム統計
retry_stats = get_retry_manager().get_statistics()
print(f"リトライ成功率: {retry_stats['success_rate']:.1f}%")

# フォルバックシステム統計
fallback_stats = get_fallback_system().get_statistics()
print(f"フォルバック成功率: {fallback_stats['success_rate']:.1f}%")
```

### ヘルススコア基準

| スコア範囲 | ステータス | 対応レベル |
|------------|------------|------------|
| 90-100 | HEALTHY | 通常監視 |
| 70-89 | DEGRADED | 注意監視 |
| 40-69 | UNHEALTHY | 即座対応 |
| 0-39 | CRITICAL | 緊急対応 |

## パフォーマンス監視

### メトリクス収集確認

```python
from src.dashboard.metrics_collector import get_metrics_collector

metrics = get_metrics_collector()

# 主要メトリクス確認
health_metrics = metrics.get_metric_series("health_score")
if health_metrics:
    latest = health_metrics.get_latest()
    print(f"最新ヘルススコア: {latest.value} ({latest.timestamp})")

# システム統計
stats = metrics.get_collection_stats()
print(f"収集中: {stats['is_collecting']}")
print(f"総メトリクス数: {stats['total_metrics']}")
```

### ベンチマーク実行

```python
from src.optimization.benchmark_system import PerformanceBenchmark

benchmark = PerformanceBenchmark()

# システム診断ベンチマーク
def test_function():
    from src.diagnosis.intelligent_diagnostics import get_intelligent_diagnostics
    diag = get_intelligent_diagnostics()
    return diag.diagnose_system()

result = benchmark.benchmark_function(test_function, iterations=10)
print(f"平均実行時間: {result.avg_time:.3f}秒")
print(f"スループット: {result.throughput:.1f} ops/sec")
```

### パフォーマンス閾値

| メトリクス | 正常範囲 | 警告閾値 | 重要閾値 |
|------------|----------|----------|----------|
| 応答時間 | < 1秒 | 1-3秒 | > 3秒 |
| スループット | > 100 ops/sec | 50-100 | < 50 |
| エラー率 | < 1% | 1-5% | > 5% |
| CPU使用率 | < 70% | 70-85% | > 85% |
| メモリ使用率 | < 80% | 80-90% | > 90% |

## エラー管理

### エラートレンド分析

```python
from src.resilience.error_handler import get_error_handler

error_handler = get_error_handler()

# 24時間のエラートレンド
trends = error_handler.get_error_trends(hours=24)
print(f"直近24時間のエラー総数: {trends['total_errors']}")
print(f"最多エラータイプ: {trends['most_common_error_type']}")
print(f"最も影響を受けたコンポーネント: {trends['most_affected_component']}")

# カテゴリ別エラー分布
for category, count in trends['category_trends'].items():
    if count > 0:
        print(f"{category}: {count}件")
```

### エラー対応手順

1. **即座対応が必要なエラー**:
   - CRITICAL, EMERGENCY レベル
   - システム停止の可能性
   - セキュリティ関連エラー

2. **計画的対応が必要なエラー**:
   - HIGH レベル
   - 機能制限の可能性
   - パフォーマンス低下

3. **監視継続**:
   - MEDIUM, LOW レベル
   - 自動回復が有効
   - トレンド監視

### エラー回復アクション

```python
# サーキットブレーカーリセット（緊急時）
circuit_manager = get_circuit_breaker_manager()
circuit_manager.reset_all_circuits()

# エラー統計クリア（メンテナンス時）
error_handler.clear_statistics()

# リトライ統計クリア
retry_manager = get_retry_manager()
retry_manager.clear_statistics()
```

## 最適化管理

### システム最適化実行

```python
from src.optimization.system_optimizer import get_system_optimizer

optimizer = get_system_optimizer()

# 最適化サイクル実行
summary = await optimizer.run_optimization_cycle()
print(f"実行された最適化ルール: {len(summary.executed_rules)}")
print(f"改善項目数: {len(summary.improvements)}")

# 手動最適化（特定ルールのみ）
cpu_summary = await optimizer.run_optimization_cycle(['cpu_optimization'])
memory_summary = await optimizer.run_optimization_cycle(['memory_optimization'])
```

### 最適化レベル設定

```python
# 保守的最適化（本番環境推奨）
optimizer.set_optimization_level('conservative')

# バランス最適化（標準環境）
optimizer.set_optimization_level('balanced')

# 積極的最適化（開発・テスト環境のみ）
optimizer.set_optimization_level('aggressive')
```

## トラブルシューティング

### 一般的な問題と解決策

#### 1. システムヘルススコア低下

**症状**: ヘルススコアが70未満
**調査手順**:
```python
# 詳細な問題分析
health = monitor.get_system_health()
for issue in health.active_issues:
    print(f"問題: {issue['component']} - {issue['description']}")
    print(f"詳細: {issue.get('details', {})}")

# 推奨事項確認
for recommendation in health.recommendations:
    print(f"推奨: {recommendation}")
```

**解決策**:
- コンポーネント別対応
- 設定調整
- リソース追加

#### 2. エラー率上昇

**症状**: エラー率が5%を超過
**調査手順**:
```python
# エラー詳細分析
error_stats = error_handler.get_error_statistics()
recent_errors = error_stats['recent_errors']
for error in recent_errors[-5:]:
    print(f"エラー: {error['error_type']} - {error['component']}")
```

**解決策**:
- エラーパターン追加
- 回復アクション改善
- 外部依存関係確認

#### 3. パフォーマンス低下

**症状**: 応答時間が3秒を超過
**調査手順**:
```python
# ベンチマーク実行
result = benchmark.benchmark_function(test_function)
print(f"平均実行時間: {result.avg_time}秒")

# ボトルネック分析
bottlenecks = result.performance_analysis.get('bottlenecks', [])
for bottleneck in bottlenecks:
    print(f"ボトルネック: {bottleneck}")
```

**解決策**:
- 最適化実行
- リソース監視
- 設定チューニング

## 定期メンテナンス

### 日次メンテナンス

```bash
# システムヘルス確認
python -c "
from src.dashboard.enhanced_monitor import get_enhanced_monitor
monitor = get_enhanced_monitor()
health = monitor.get_system_health()
print(f'システム状態: {health.overall_status.value} (スコア: {health.overall_score})')
"

# ログローテーション確認
# 古いログファイルのアーカイブ
# 統計データのバックアップ
```

### 週次メンテナンス

```bash
# 包括的システム診断
python -c "
from src.diagnosis.intelligent_diagnostics import get_intelligent_diagnostics
diag = get_intelligent_diagnostics()
result = diag.diagnose_system()
print(f'診断完了: {len(result.recommendations)}件の推奨事項')
"

# パフォーマンスベンチマーク
# 設定最適化レビュー
# セキュリティスキャン
```

### 月次メンテナンス

```bash
# 全コンポーネント統合テスト
python -m pytest tests/integration/

# システム最適化実行
python -c "
import asyncio
from src.optimization.system_optimizer import get_system_optimizer
async def optimize():
    optimizer = get_system_optimizer()
    summary = await optimizer.run_optimization_cycle()
    print(f'最適化完了: {len(summary.improvements)}件の改善')
asyncio.run(optimize())
"

# 統計データ分析とレポート作成
# 容量計画レビュー
```

## セキュリティ管理

### セキュリティ監視

```python
from src.logging import get_audit_logger

audit_logger = get_audit_logger()

# セキュリティイベント確認
# 注意: 実際の実装では適切なクエリメソッドを使用
print("セキュリティ監査ログの確認...")
print("- 認証失敗の監視")
print("- 権限昇格の検出")
print("- 異常アクセスパターンの分析")
```

### アクセス制御

- 最小権限の原則
- 定期的な権限レビュー
- 監査証跡の保持

### セキュリティ設定

```python
from src.config import get_config_manager

config = get_config_manager()

# セキュリティ関連設定確認
security_settings = {
    'authentication_timeout': config.get('security.auth_timeout', 3600),
    'max_login_attempts': config.get('security.max_login_attempts', 3),
    'audit_retention_days': config.get('security.audit_retention', 90),
    'encryption_enabled': config.get('security.encryption', True)
}

for setting, value in security_settings.items():
    print(f"{setting}: {value}")
```

## バックアップ・リストア

### データバックアップ

```bash
# 設定ファイルバックアップ
cp -r config/ backup/config_$(date +%Y%m%d)/

# ログファイルアーカイブ
tar -czf backup/logs_$(date +%Y%m%d).tar.gz logs/

# 統計データバックアップ
python -c "
import json
import datetime
from src.dashboard.metrics_collector import get_metrics_collector
from src.resilience.error_handler import get_error_handler

# メトリクス統計
metrics = get_metrics_collector()
stats = metrics.get_collection_stats()

# エラー統計
error_handler = get_error_handler()
error_stats = error_handler.get_error_statistics()

backup_data = {
    'timestamp': datetime.datetime.now().isoformat(),
    'metrics_stats': stats,
    'error_stats': error_stats
}

with open(f'backup/stats_{datetime.date.today().strftime(\"%Y%m%d\")}.json', 'w') as f:
    json.dump(backup_data, f, indent=2)
"
```

### システムリストア

```bash
# 設定リストア
cp -r backup/config_YYYYMMDD/* config/

# システム再起動
python -c "
from src.dashboard.enhanced_monitor import get_enhanced_monitor
monitor = get_enhanced_monitor()
monitor.stop_monitoring_system()
# ... システム再初期化 ...
monitor.start_monitoring()
"
```

## 運用チェックリスト

### 日次チェック

- [ ] システムヘルス確認
- [ ] アクティブアラート確認
- [ ] エラー率チェック
- [ ] パフォーマンスメトリクス確認
- [ ] セキュリティイベント確認

### 週次チェック

- [ ] 包括的システム診断実行
- [ ] パフォーマンスベンチマーク
- [ ] エラートレンド分析
- [ ] 設定最適化レビュー
- [ ] ログファイル管理

### 月次チェック

- [ ] 統合テスト実行
- [ ] システム最適化実行
- [ ] 容量計画レビュー
- [ ] セキュリティ監査
- [ ] 運用手順更新

## 緊急時対応

### 緊急連絡先

- システム管理者: [連絡先]
- セキュリティ担当: [連絡先]
- 開発チーム: [連絡先]

### エスカレーション手順

1. **レベル1**: 自動回復試行
2. **レベル2**: システム管理者対応
3. **レベル3**: 開発チーム エスカレーション
4. **レベル4**: 緊急時対策本部設置

### 緊急時コマンド

```bash
# システム即座停止
python -c "
from src.dashboard.enhanced_monitor import get_enhanced_monitor
monitor = get_enhanced_monitor()
monitor.stop_monitoring_system()
print('監視停止完了')
"

# 全サーキットブレーカー強制オープン
python -c "
from src.resilience.circuit_breaker import get_circuit_breaker_manager
manager = get_circuit_breaker_manager()
for name, breaker in manager.circuit_breakers.items():
    breaker.force_open()
print('全サーキットブレーカーオープン')
"

# 緊急ログ収集
python -c "
import datetime
from src.resilience.error_handler import get_error_handler
error_handler = get_error_handler()
stats = error_handler.get_error_statistics()
with open(f'emergency_log_{datetime.datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.json', 'w') as f:
    import json
    json.dump(stats, f, indent=2)
print('緊急ログ収集完了')
"
```

## 参考資料

- [AIDE 設定管理ガイド](configuration_guide.md)
- [AIDE パフォーマンスチューニングガイド](performance_tuning.md)
- [AIDE セキュリティガイド](security_guide.md)
- [AIDE トラブルシューティングガイド](troubleshooting_guide.md)
- [AIDE API リファレンス](../api/README.md)

---

このドキュメントは定期的に更新されます。最新版は公式リポジトリで確認してください。