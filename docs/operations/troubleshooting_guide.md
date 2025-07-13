# AIDE トラブルシューティングガイド

## 概要

このドキュメントは、AIDE システムで発生する一般的な問題の診断と解決方法を提供します。システム管理者と開発者が迅速に問題を特定し、適切な対応を取れるよう設計されています。

## 目次

1. [緊急時対応](#緊急時対応)
2. [システム起動問題](#システム起動問題)
3. [パフォーマンス問題](#パフォーマンス問題)
4. [エラー・例外処理](#エラー例外処理)
5. [ネットワーク関連問題](#ネットワーク関連問題)
6. [メモリ・リソース問題](#メモリリソース問題)
7. [設定関連問題](#設定関連問題)
8. [ログ・監査問題](#ログ監査問題)
9. [セキュリティ問題](#セキュリティ問題)
10. [診断ツールと手順](#診断ツールと手順)

## 緊急時対応

### システム完全停止

**症状**: システムが全く応答しない

**即座実行すべき診断**:
```python
# システム状態確認
from src.dashboard.enhanced_monitor import get_enhanced_monitor

try:
    monitor = get_enhanced_monitor()
    health = monitor.get_system_health()
    print(f"システム状態: {health.overall_status.value if health else 'UNAVAILABLE'}")
except Exception as e:
    print(f"監視システムエラー: {e}")
```

**緊急対応手順**:
1. **即座停止**: すべての処理を停止
2. **ログ収集**: 直近のエラーログを保存
3. **バックアップ確認**: 最新バックアップの確認
4. **エスカレーション**: 開発チームへの緊急連絡

**緊急時コマンド**:
```bash
# システム緊急停止
python -c "
import sys
sys.path.append('/home/choux1/src/github.com/0xchoux1/aide')
try:
    from src.dashboard.enhanced_monitor import get_enhanced_monitor
    monitor = get_enhanced_monitor()
    monitor.stop_monitoring_system()
    print('システム監視停止完了')
except Exception as e:
    print(f'停止エラー: {e}')
"

# 緊急ログ収集
python -c "
import sys, json, datetime
sys.path.append('/home/choux1/src/github.com/0xchoux1/aide')
try:
    from src.resilience.error_handler import get_error_handler
    error_handler = get_error_handler()
    stats = error_handler.get_error_statistics()
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(f'emergency_dump_{timestamp}.json', 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    print(f'緊急ダンプ完了: emergency_dump_{timestamp}.json')
except Exception as e:
    print(f'ダンプエラー: {e}')
"
```

### 高負荷状態

**症状**: システム応答が極端に遅い、CPU/メモリ使用率が90%超

**即座診断**:
```python
import psutil
import time

def emergency_resource_check():
    """緊急リソースチェック"""
    print("=== 緊急リソース診断 ===")
    
    # CPU使用率
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"CPU使用率: {cpu_percent}%")
    
    # メモリ使用率
    memory = psutil.virtual_memory()
    print(f"メモリ使用率: {memory.percent}% ({memory.used/1024/1024/1024:.1f}GB使用)")
    
    # ディスク使用率
    disk = psutil.disk_usage('/')
    print(f"ディスク使用率: {disk.percent}%")
    
    # プロセス確認
    processes = sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']), 
                      key=lambda p: p.info['cpu_percent'], reverse=True)
    
    print("\n高CPU使用プロセス（上位5）:")
    for proc in processes[:5]:
        try:
            print(f"  PID {proc.info['pid']}: {proc.info['name']} - CPU: {proc.info['cpu_percent']:.1f}%")
        except:
            pass

emergency_resource_check()
```

**緊急対応**:
```python
def emergency_load_reduction():
    """緊急負荷軽減"""
    try:
        # サーキットブレーカー強制オープン
        from src.resilience.circuit_breaker import get_circuit_breaker_manager
        manager = get_circuit_breaker_manager()
        
        for name, breaker in manager.circuit_breakers.items():
            breaker.force_open()
            print(f"サーキットブレーカー {name} を強制オープン")
        
        # システム最適化緊急実行
        from src.optimization.system_optimizer import get_system_optimizer
        import asyncio
        
        async def emergency_optimize():
            optimizer = get_system_optimizer()
            await optimizer.run_optimization_cycle(['memory_optimization', 'cpu_optimization'])
        
        asyncio.run(emergency_optimize())
        print("緊急最適化実行完了")
        
    except Exception as e:
        print(f"緊急対応エラー: {e}")

emergency_load_reduction()
```

## システム起動問題

### 起動時設定エラー

**症状**: システム起動時に設定関連エラー

**診断手順**:
```python
def diagnose_startup_issues():
    """起動問題診断"""
    print("=== 起動問題診断 ===")
    
    try:
        from src.config import get_config_manager
        config = get_config_manager()
        print("✓ 設定管理システム正常")
        
        # 必須設定確認
        required_configs = [
            'system.name',
            'logging.level',
            'monitoring.enabled'
        ]
        
        for req_config in required_configs:
            value = config.get(req_config)
            if value is not None:
                print(f"✓ {req_config}: {value}")
            else:
                print(f"✗ {req_config}: 未設定")
                
    except Exception as e:
        print(f"✗ 設定管理エラー: {e}")
    
    try:
        from src.logging import get_logger
        logger = get_logger(__name__)
        logger.info("ログシステム初期化テスト")
        print("✓ ログシステム正常")
    except Exception as e:
        print(f"✗ ログシステムエラー: {e}")

diagnose_startup_issues()
```

**解決策**:
1. **設定ファイル確認**: `config/` ディレクトリの存在と権限
2. **デフォルト設定適用**: 最小限設定での起動試行
3. **段階的起動**: コンポーネント毎の個別起動確認

### 依存関係エラー

**症状**: モジュールインポートエラー、依存パッケージ不足

**診断と解決**:
```python
def check_dependencies():
    """依存関係チェック"""
    required_packages = [
        'psutil',
        'asyncio',
        'threading',
        'dataclasses',
        'enum',
        'typing',
        'json',
        'time'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - 未インストール")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n不足パッケージ: {', '.join(missing_packages)}")
        print("pip install <package_name> で解決してください")
    else:
        print("\n✓ 全依存関係正常")

check_dependencies()
```

## パフォーマンス問題

### 応答時間遅延

**症状**: システム応答が通常より遅い（3秒以上）

**診断手順**:
```python
from src.optimization.benchmark_system import PerformanceBenchmark
import time

def diagnose_performance_issues():
    """パフォーマンス問題診断"""
    benchmark = PerformanceBenchmark()
    
    # 基本診断ベンチマーク
    def basic_diagnosis():
        from src.diagnosis.intelligent_diagnostics import get_intelligent_diagnostics
        diag = get_intelligent_diagnostics()
        return diag.diagnose_system()
    
    print("=== パフォーマンス診断 ===")
    
    # ベンチマーク実行
    result = benchmark.benchmark_function(basic_diagnosis, iterations=3, warmup=1)
    
    print(f"平均実行時間: {result.avg_time:.3f}秒")
    print(f"最小/最大時間: {result.min_time:.3f}秒 / {result.max_time:.3f}秒")
    
    # 判定
    if result.avg_time > 3.0:
        print("⚠️  パフォーマンス低下検出")
        
        # 詳細分析
        print("\n詳細分析:")
        
        # メモリ使用量
        import psutil
        memory = psutil.virtual_memory()
        if memory.percent > 80:
            print(f"⚠️  高メモリ使用率: {memory.percent}%")
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80:
            print(f"⚠️  高CPU使用率: {cpu_percent}%")
        
        # エラー率確認
        from src.resilience.error_handler import get_error_handler
        error_stats = get_error_handler().get_error_statistics()
        total_errors = error_stats['error_stats']['total_errors']
        if total_errors > 10:
            print(f"⚠️  高エラー数: {total_errors}")
    
    else:
        print("✓ パフォーマンス正常")

diagnose_performance_issues()
```

**解決策**:
```python
async def resolve_performance_issues():
    """パフォーマンス問題解決"""
    print("=== パフォーマンス最適化実行 ===")
    
    try:
        from src.optimization.system_optimizer import get_system_optimizer
        optimizer = get_system_optimizer()
        
        # 段階的最適化
        optimization_steps = [
            ['memory_optimization'],
            ['cpu_optimization'],
            ['async_optimization'],
            ['cache_optimization']
        ]
        
        for step in optimization_steps:
            print(f"最適化実行: {step}")
            summary = await optimizer.run_optimization_cycle(step)
            print(f"  改善項目数: {len(summary.improvements)}")
            
            # 効果確認
            time.sleep(2)
            
    except Exception as e:
        print(f"最適化エラー: {e}")

# 最適化実行
# import asyncio
# asyncio.run(resolve_performance_issues())
```

### メモリリーク

**症状**: メモリ使用量が継続的に増加

**診断手順**:
```python
import gc
import tracemalloc
import psutil

def diagnose_memory_leak():
    """メモリリーク診断"""
    print("=== メモリリーク診断 ===")
    
    # 初期メモリ状態
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"初期メモリ使用量: {initial_memory:.1f} MB")
    
    # メモリトレース開始
    tracemalloc.start()
    
    # システム処理実行（複数回）
    for i in range(10):
        try:
            from src.diagnosis.intelligent_diagnostics import get_intelligent_diagnostics
            diag = get_intelligent_diagnostics()
            result = diag.diagnose_system()
            
            # ガベージコレクション
            collected = gc.collect()
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            print(f"実行 {i+1}: {current_memory:.1f} MB (GC: {collected})")
            
        except Exception as e:
            print(f"実行 {i+1} エラー: {e}")
    
    # 最終メモリ状態
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    print(f"\n最終メモリ使用量: {final_memory:.1f} MB")
    print(f"メモリ増加量: {memory_increase:.1f} MB")
    
    # メモリリーク判定
    if memory_increase > 50:  # 50MB以上の増加
        print("⚠️  メモリリークの可能性")
        
        # トレース情報取得
        current, peak = tracemalloc.get_traced_memory()
        print(f"トレース - 現在: {current/1024/1024:.1f}MB, ピーク: {peak/1024/1024:.1f}MB")
    else:
        print("✓ メモリ使用量正常")
    
    tracemalloc.stop()

diagnose_memory_leak()
```

## エラー・例外処理

### 高エラー率

**症状**: エラー率が5%を超過

**診断手順**:
```python
def diagnose_high_error_rate():
    """高エラー率診断"""
    print("=== エラー率診断 ===")
    
    from src.resilience.error_handler import get_error_handler
    error_handler = get_error_handler()
    
    # エラー統計取得
    stats = error_handler.get_error_statistics()
    total_errors = stats['error_stats']['total_errors']
    
    print(f"総エラー数: {total_errors}")
    
    # カテゴリ別エラー分析
    print("\nカテゴリ別エラー:")
    for category, count in stats['error_stats']['errors_by_category'].items():
        if count > 0:
            print(f"  {category}: {count}")
    
    # 重要度別エラー分析
    print("\n重要度別エラー:")
    for severity, count in stats['error_stats']['errors_by_severity'].items():
        if count > 0:
            print(f"  レベル{severity}: {count}")
    
    # 最近のエラー詳細
    recent_errors = stats['recent_errors']
    if recent_errors:
        print(f"\n最近のエラー（最新{len(recent_errors)}件）:")
        for error in recent_errors[-5:]:
            print(f"  - {error['error_type']}: {error['component']} - {error['error_message'][:50]}...")
    
    # エラートレンド分析
    trends = error_handler.get_error_trends(hours=24)
    print(f"\n24時間のエラートレンド:")
    print(f"  総エラー数: {trends['total_errors']}")
    print(f"  最多エラータイプ: {trends['most_common_error_type']}")
    print(f"  最も影響を受けたコンポーネント: {trends['most_affected_component']}")

diagnose_high_error_rate()
```

**解決策**:
```python
def resolve_high_error_rate():
    """高エラー率解決"""
    print("=== エラー率改善 ===")
    
    from src.resilience.error_handler import get_error_handler
    from src.resilience.circuit_breaker import get_circuit_breaker_manager
    from src.resilience.retry_manager import get_retry_manager
    
    # 1. サーキットブレーカー状態確認
    circuit_manager = get_circuit_breaker_manager()
    circuit_health = circuit_manager.get_health_summary()
    
    print(f"サーキットブレーカー状態:")
    print(f"  正常: {circuit_health['healthy_circuits']}")
    print(f"  異常: {circuit_health['unhealthy_circuits']}")
    
    if circuit_health['unhealthy_circuits'] > 0:
        print("  → 異常サーキットをリセット")
        circuit_manager.reset_all_circuits()
    
    # 2. リトライ設定最適化
    retry_manager = get_retry_manager()
    retry_stats = retry_manager.get_statistics()
    
    print(f"\nリトライ統計:")
    print(f"  成功率: {retry_stats['success_rate']:.1f}%")
    
    if retry_stats['success_rate'] < 80:
        print("  → リトライポリシーを調整推奨")
    
    # 3. エラーパターン分析
    error_handler = get_error_handler()
    trends = error_handler.get_error_trends(hours=6)
    
    if trends['most_common_error_type']:
        print(f"\n最頻出エラー: {trends['most_common_error_type']}")
        print("  → 該当エラーの個別対応が必要")

resolve_high_error_rate()
```

### サーキットブレーカー大量オープン

**症状**: 複数のサーキットブレーカーが OPEN 状態

**診断と解決**:
```python
def diagnose_circuit_breaker_issues():
    """サーキットブレーカー問題診断"""
    print("=== サーキットブレーカー診断 ===")
    
    from src.resilience.circuit_breaker import get_circuit_breaker_manager
    manager = get_circuit_breaker_manager()
    
    # 全サーキットブレーカー状態確認
    all_stats = manager.get_all_stats()
    
    open_circuits = []
    half_open_circuits = []
    healthy_circuits = []
    
    for name, stats in all_stats.items():
        if stats.state.value == 'open':
            open_circuits.append((name, stats))
        elif stats.state.value == 'half_open':
            half_open_circuits.append((name, stats))
        else:
            healthy_circuits.append((name, stats))
    
    print(f"OPEN状態: {len(open_circuits)}")
    print(f"HALF_OPEN状態: {len(half_open_circuits)}")
    print(f"正常状態: {len(healthy_circuits)}")
    
    # OPEN状態の詳細分析
    if open_circuits:
        print("\nOPEN状態サーキット詳細:")
        for name, stats in open_circuits:
            print(f"  {name}:")
            print(f"    連続失敗数: {stats.consecutive_failures}")
            print(f"    総失敗数: {stats.failure_count}")
            print(f"    最終失敗時刻: {stats.last_failure_time}")
            
            # 自動回復可能性チェック
            import time
            if stats.last_failure_time and (time.time() - stats.last_failure_time) > 300:  # 5分経過
                print(f"    → 自動回復試行可能")
            else:
                print(f"    → 待機中")

def reset_problematic_circuits():
    """問題のあるサーキット強制リセット"""
    print("=== サーキットブレーカーリセット ===")
    
    from src.resilience.circuit_breaker import get_circuit_breaker_manager
    manager = get_circuit_breaker_manager()
    
    # 管理者判断によるリセット（注意して使用）
    choice = input("全サーキットブレーカーをリセットしますか？ (y/N): ")
    if choice.lower() == 'y':
        manager.reset_all_circuits()
        print("全サーキットブレーカーリセット完了")
    else:
        print("リセットをキャンセル")

diagnose_circuit_breaker_issues()
# reset_problematic_circuits()  # 必要時のみ実行
```

## ネットワーク関連問題

### 接続タイムアウト

**症状**: 外部サービス接続でタイムアウト頻発

**診断手順**:
```python
import asyncio
import aiohttp
import time

async def diagnose_network_issues():
    """ネットワーク問題診断"""
    print("=== ネットワーク診断 ===")
    
    # テスト用エンドポイント（実際の環境に合わせて調整）
    test_endpoints = [
        'https://httpbin.org/status/200',
        'https://httpbin.org/delay/1',
        'https://httpbin.org/delay/5'
    ]
    
    timeout = aiohttp.ClientTimeout(total=10, connect=5)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for endpoint in test_endpoints:
            try:
                start_time = time.time()
                async with session.get(endpoint) as response:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    print(f"✓ {endpoint}: {response.status} ({duration:.2f}秒)")
                    
            except asyncio.TimeoutError:
                print(f"✗ {endpoint}: タイムアウト")
            except Exception as e:
                print(f"✗ {endpoint}: エラー ({type(e).__name__})")
    
    # DNS解決テスト
    try:
        import socket
        test_domains = ['google.com', 'github.com']
        
        print("\nDNS解決テスト:")
        for domain in test_domains:
            try:
                ip = socket.gethostbyname(domain)
                print(f"✓ {domain} → {ip}")
            except Exception as e:
                print(f"✗ {domain}: DNS解決失敗")
                
    except Exception as e:
        print(f"DNS テスト失敗: {e}")

# ネットワーク診断実行
# asyncio.run(diagnose_network_issues())
```

**解決策**:
```python
def optimize_network_settings():
    """ネットワーク設定最適化"""
    print("=== ネットワーク設定最適化 ===")
    
    from src.resilience.retry_manager import get_retry_manager, RetryPolicy, BackoffStrategy
    
    # ネットワーク向けリトライポリシー作成
    network_retry_policy = RetryPolicy(
        max_attempts=5,
        base_delay=2.0,
        max_delay=30.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
        jitter=True,
        retry_on_exceptions=[
            ConnectionError, 
            TimeoutError,
            OSError
        ]
    )
    
    retry_manager = get_retry_manager()
    retry_manager.register_policy('network_optimized', network_retry_policy)
    
    print("ネットワーク最適化リトライポリシー登録完了")
    
    # タイムアウト設定推奨値
    recommended_timeouts = {
        'connect_timeout': 10,  # 接続タイムアウト
        'read_timeout': 30,     # 読み取りタイムアウト
        'total_timeout': 60     # 総タイムアウト
    }
    
    print("推奨タイムアウト設定:")
    for setting, value in recommended_timeouts.items():
        print(f"  {setting}: {value}秒")

optimize_network_settings()
```

## メモリ・リソース問題

### ディスク容量不足

**症状**: ディスク使用率が90%を超過

**診断と解決**:
```python
import os
import shutil
import glob
from datetime import datetime, timedelta

def diagnose_disk_usage():
    """ディスク使用量診断"""
    print("=== ディスク使用量診断 ===")
    
    import psutil
    
    # 全ディスクの使用量確認
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            percent = usage.used / usage.total * 100
            
            print(f"{partition.mountpoint}:")
            print(f"  使用量: {percent:.1f}% ({usage.used/1024/1024/1024:.1f}GB / {usage.total/1024/1024/1024:.1f}GB)")
            
            if percent > 90:
                print(f"  ⚠️  危険: 容量不足")
            elif percent > 80:
                print(f"  ⚠️  注意: 容量少ない")
            else:
                print(f"  ✓ 正常")
                
        except Exception as e:
            print(f"{partition.mountpoint}: アクセスエラー")
    
    # 大容量ディレクトリ特定
    print("\n大容量ディレクトリ調査:")
    directories_to_check = ['.', 'logs', 'cache', 'temp', '/tmp']
    
    for directory in directories_to_check:
        if os.path.exists(directory):
            try:
                size = get_directory_size(directory)
                size_mb = size / 1024 / 1024
                if size_mb > 100:  # 100MB以上
                    print(f"  {directory}: {size_mb:.1f}MB")
            except Exception as e:
                print(f"  {directory}: 測定エラー")

def get_directory_size(path):
    """ディレクトリサイズ取得"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except (OSError, FileNotFoundError):
                pass
    return total_size

def cleanup_disk_space():
    """ディスク容量クリーンアップ"""
    print("=== ディスク容量クリーンアップ ===")
    
    cleanup_tasks = []
    
    # 古いログファイル削除候補
    log_patterns = [
        'logs/*.log.*',
        '*.log.old',
        '*.log.*.gz'
    ]
    
    for pattern in log_patterns:
        files = glob.glob(pattern)
        for file in files:
            try:
                # 7日より古いファイル
                if os.path.getctime(file) < (datetime.now() - timedelta(days=7)).timestamp():
                    file_size = os.path.getsize(file) / 1024 / 1024
                    cleanup_tasks.append(('log', file, file_size))
            except Exception:
                pass
    
    # 一時ファイル削除候補
    temp_patterns = [
        '/tmp/aide_*',
        'temp/*',
        '*.tmp'
    ]
    
    for pattern in temp_patterns:
        files = glob.glob(pattern)
        for file in files:
            try:
                if os.path.getctime(file) < (datetime.now() - timedelta(hours=24)).timestamp():
                    file_size = os.path.getsize(file) / 1024 / 1024
                    cleanup_tasks.append(('temp', file, file_size))
            except Exception:
                pass
    
    # クリーンアップ候補表示
    if cleanup_tasks:
        total_size = sum(task[2] for task in cleanup_tasks)
        print(f"クリーンアップ候補: {len(cleanup_tasks)}ファイル ({total_size:.1f}MB)")
        
        for task_type, filepath, size_mb in cleanup_tasks[:10]:  # 上位10件表示
            print(f"  [{task_type}] {filepath} ({size_mb:.1f}MB)")
        
        # 確認後に実際のクリーンアップ実行
        # choice = input("クリーンアップを実行しますか？ (y/N): ")
        # if choice.lower() == 'y':
        #     for task_type, filepath, size_mb in cleanup_tasks:
        #         try:
        #             os.remove(filepath)
        #             print(f"削除: {filepath}")
        #         except Exception as e:
        #             print(f"削除失敗: {filepath} - {e}")
    else:
        print("クリーンアップ候補なし")

diagnose_disk_usage()
cleanup_disk_space()
```

## 設定関連問題

### 設定ファイル破損

**症状**: 設定読み込み時にエラー

**診断と修復**:
```python
def diagnose_config_issues():
    """設定問題診断"""
    print("=== 設定診断 ===")
    
    import json
    import os
    
    # 設定ファイル存在確認
    config_files = [
        'config/default.json',
        'config/development.json',
        'config/production.json'
    ]
    
    for config_file in config_files:
        print(f"\n{config_file}:")
        
        if not os.path.exists(config_file):
            print("  ✗ ファイルが存在しません")
            continue
        
        # ファイル読み取り権限確認
        if not os.access(config_file, os.R_OK):
            print("  ✗ 読み取り権限なし")
            continue
        
        # JSON構文確認
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            print("  ✓ JSON構文正常")
            print(f"  設定項目数: {len(config_data)}")
            
            # 必須設定項目確認
            required_keys = ['system', 'logging']
            missing_keys = [key for key in required_keys if key not in config_data]
            
            if missing_keys:
                print(f"  ⚠️  不足項目: {missing_keys}")
            else:
                print("  ✓ 必須項目存在")
                
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON構文エラー: {e}")
        except Exception as e:
            print(f"  ✗ 読み取りエラー: {e}")

def create_backup_and_restore_config():
    """設定バックアップと復旧"""
    print("=== 設定復旧 ===")
    
    # バックアップ確認
    backup_files = glob.glob('backup/config_*')
    if backup_files:
        latest_backup = max(backup_files, key=os.path.getctime)
        print(f"最新バックアップ: {latest_backup}")
        
        choice = input("バックアップから復旧しますか？ (y/N): ")
        if choice.lower() == 'y':
            try:
                import shutil
                shutil.copytree(latest_backup, 'config/', dirs_exist_ok=True)
                print("設定復旧完了")
            except Exception as e:
                print(f"復旧エラー: {e}")
    else:
        print("バックアップファイルなし")
        
        # 最小設定作成
        choice = input("最小設定を作成しますか？ (y/N): ")
        if choice.lower() == 'y':
            create_minimal_config()

def create_minimal_config():
    """最小設定作成"""
    minimal_config = {
        "system": {
            "name": "AIDE",
            "version": "3.3.0",
            "environment": "development"
        },
        "logging": {
            "level": "INFO",
            "file": "logs/aide.log"
        },
        "monitoring": {
            "enabled": True,
            "health_check_interval": 30
        }
    }
    
    os.makedirs('config', exist_ok=True)
    
    with open('config/default.json', 'w', encoding='utf-8') as f:
        json.dump(minimal_config, f, indent=2, ensure_ascii=False)
    
    print("最小設定ファイル作成完了: config/default.json")

diagnose_config_issues()
# create_backup_and_restore_config()  # 必要時のみ実行
```

## ログ・監査問題

### ログ出力停止

**症状**: ログファイルが更新されない

**診断と解決**:
```python
def diagnose_logging_issues():
    """ログ問題診断"""
    print("=== ログ診断 ===")
    
    import os
    import stat
    from datetime import datetime, timedelta
    
    # ログディレクトリ確認
    log_directories = ['logs', '/var/log/aide']
    
    for log_dir in log_directories:
        if os.path.exists(log_dir):
            print(f"\n{log_dir}:")
            
            # ディレクトリ権限確認
            dir_stat = os.stat(log_dir)
            if stat.S_IMODE(dir_stat.st_mode) & stat.S_IWUSR:
                print("  ✓ 書き込み権限あり")
            else:
                print("  ✗ 書き込み権限なし")
            
            # ログファイル確認
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
            
            for log_file in log_files:
                log_path = os.path.join(log_dir, log_file)
                
                # ファイル更新時刻
                mtime = os.path.getmtime(log_path)
                last_modified = datetime.fromtimestamp(mtime)
                age = datetime.now() - last_modified
                
                print(f"  {log_file}:")
                print(f"    最終更新: {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    経過時間: {age}")
                
                if age > timedelta(hours=1):
                    print("    ⚠️  更新が停止している可能性")
                else:
                    print("    ✓ 正常")
                
                # ファイルサイズ
                file_size = os.path.getsize(log_path)
                print(f"    サイズ: {file_size/1024:.1f}KB")
        else:
            print(f"\n{log_dir}: ディレクトリが存在しません")
    
    # ログシステムテスト
    print("\nログシステムテスト:")
    try:
        from src.logging import get_logger
        test_logger = get_logger('troubleshooting')
        test_logger.info("ログシステムテスト - 正常")
        print("✓ ログ出力成功")
    except Exception as e:
        print(f"✗ ログ出力失敗: {e}")

def fix_logging_permissions():
    """ログ権限修正"""
    print("=== ログ権限修正 ===")
    
    import stat
    
    # ログディレクトリ作成・権限設定
    os.makedirs('logs', exist_ok=True)
    
    try:
        os.chmod('logs', stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
        print("ログディレクトリ権限修正完了")
    except Exception as e:
        print(f"権限修正エラー: {e}")

diagnose_logging_issues()
# fix_logging_permissions()  # 必要時のみ実行
```

## セキュリティ問題

### 異常なアクセスパターン

**症状**: 不審なアクセスログや認証失敗

**診断手順**:
```python
def diagnose_security_issues():
    """セキュリティ問題診断"""
    print("=== セキュリティ診断 ===")
    
    # 認証失敗パターン確認
    from src.resilience.error_handler import get_error_handler
    error_handler = get_error_handler()
    
    trends = error_handler.get_error_trends(hours=24)
    
    # 認証関連エラー確認
    auth_errors = trends['category_trends'].get('authentication', 0)
    if auth_errors > 10:
        print(f"⚠️  認証エラー多発: {auth_errors}件/24時間")
    else:
        print(f"✓ 認証エラー正常: {auth_errors}件/24時間")
    
    # システムエラー確認
    system_errors = trends['category_trends'].get('system', 0)
    if system_errors > 20:
        print(f"⚠️  システムエラー多発: {system_errors}件/24時間")
    else:
        print(f"✓ システムエラー正常: {system_errors}件/24時間")
    
    # セキュリティ設定確認
    print("\nセキュリティ設定確認:")
    
    try:
        from src.config import get_config_manager
        config = get_config_manager()
        
        security_settings = {
            'authentication.timeout': config.get('security.auth_timeout', 3600),
            'max_login_attempts': config.get('security.max_attempts', 5),
            'encryption.enabled': config.get('security.encryption', True),
            'audit.enabled': config.get('audit.enabled', True)
        }
        
        for setting, value in security_settings.items():
            print(f"  {setting}: {value}")
            
    except Exception as e:
        print(f"設定確認エラー: {e}")

def security_hardening_check():
    """セキュリティ強化チェック"""
    print("=== セキュリティ強化チェック ===")
    
    checks = {
        'ファイル権限': check_file_permissions,
        'ネットワーク設定': check_network_security,
        '設定値検証': check_security_config,
        'ログ監査': check_audit_logging
    }
    
    for check_name, check_func in checks.items():
        try:
            result = check_func()
            status = "✓" if result else "⚠️"
            print(f"{status} {check_name}")
        except Exception as e:
            print(f"✗ {check_name}: エラー ({e})")

def check_file_permissions():
    """ファイル権限チェック"""
    import stat
    import os
    
    sensitive_files = ['config/', 'logs/']
    
    for file_path in sensitive_files:
        if os.path.exists(file_path):
            file_stat = os.stat(file_path)
            mode = stat.S_IMODE(file_stat.st_mode)
            
            # 他者読み取り権限チェック
            if mode & stat.S_IROTH:
                return False  # 他者読み取り可能は危険
    
    return True

def check_network_security():
    """ネットワークセキュリティチェック"""
    # 簡易実装
    return True

def check_security_config():
    """セキュリティ設定チェック"""
    try:
        from src.config import get_config_manager
        config = get_config_manager()
        
        # 必須セキュリティ設定
        encryption_enabled = config.get('security.encryption', False)
        audit_enabled = config.get('audit.enabled', False)
        
        return encryption_enabled and audit_enabled
    except:
        return False

def check_audit_logging():
    """監査ログチェック"""
    # 監査ログが有効かチェック
    try:
        from src.logging import get_audit_logger
        audit_logger = get_audit_logger()
        return True
    except:
        return False

diagnose_security_issues()
security_hardening_check()
```

## 診断ツールと手順

### 包括的システム診断

```python
def comprehensive_system_diagnosis():
    """包括的システム診断"""
    print("=" * 50)
    print("AIDE システム包括診断")
    print("=" * 50)
    
    diagnosis_modules = [
        ("システム起動", diagnose_startup_issues),
        ("パフォーマンス", diagnose_performance_issues),
        ("エラー率", diagnose_high_error_rate),
        ("メモリ", diagnose_memory_leak),
        ("ディスク", diagnose_disk_usage),
        ("ネットワーク", lambda: asyncio.run(diagnose_network_issues())),
        ("設定", diagnose_config_issues),
        ("ログ", diagnose_logging_issues),
        ("セキュリティ", diagnose_security_issues)
    ]
    
    diagnosis_results = {}
    
    for module_name, diagnosis_func in diagnosis_modules:
        print(f"\n{'-' * 20} {module_name} 診断 {'-' * 20}")
        
        try:
            start_time = time.time()
            diagnosis_func()
            end_time = time.time()
            
            diagnosis_results[module_name] = {
                'status': 'completed',
                'duration': end_time - start_time
            }
            
        except Exception as e:
            print(f"✗ {module_name} 診断エラー: {e}")
            diagnosis_results[module_name] = {
                'status': 'error',
                'error': str(e)
            }
    
    # 診断結果サマリー
    print("\n" + "=" * 50)
    print("診断結果サマリー")
    print("=" * 50)
    
    for module_name, result in diagnosis_results.items():
        if result['status'] == 'completed':
            print(f"✓ {module_name}: 完了 ({result['duration']:.2f}秒)")
        else:
            print(f"✗ {module_name}: エラー - {result['error']}")

# 包括診断実行
comprehensive_system_diagnosis()
```

### 緊急時診断スクリプト

```python
def emergency_quick_diagnosis():
    """緊急時クイック診断"""
    print("=== 緊急時クイック診断 ===")
    
    import time
    start_time = time.time()
    
    # 1. システム基本状態
    try:
        from src.dashboard.enhanced_monitor import get_enhanced_monitor
        monitor = get_enhanced_monitor()
        health = monitor.get_system_health()
        if health:
            print(f"システム状態: {health.overall_status.value} (スコア: {health.overall_score})")
        else:
            print("⚠️  システム状態取得不可")
    except Exception as e:
        print(f"✗ システム状態エラー: {e}")
    
    # 2. リソース状態
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        print(f"リソース: CPU {cpu}%, Memory {memory.percent}%")
        
        if cpu > 90 or memory.percent > 90:
            print("⚠️  リソース枯渇警告")
    except Exception as e:
        print(f"✗ リソース確認エラー: {e}")
    
    # 3. 最近のエラー
    try:
        from src.resilience.error_handler import get_error_handler
        error_handler = get_error_handler()
        stats = error_handler.get_error_statistics()
        recent_errors = len(stats['recent_errors'])
        print(f"最近のエラー: {recent_errors}件")
        
        if recent_errors > 10:
            print("⚠️  エラー多発警告")
    except Exception as e:
        print(f"✗ エラー確認失敗: {e}")
    
    # 4. サーキットブレーカー状態
    try:
        from src.resilience.circuit_breaker import get_circuit_breaker_manager
        circuit_manager = get_circuit_breaker_manager()
        health_summary = circuit_manager.get_health_summary()
        print(f"サーキットブレーカー: {health_summary['healthy_circuits']}/{health_summary['total_circuits']} 正常")
        
        if health_summary['unhealthy_circuits'] > 0:
            print("⚠️  サーキットブレーカー異常")
    except Exception as e:
        print(f"✗ サーキットブレーカー確認エラー: {e}")
    
    duration = time.time() - start_time
    print(f"\n診断完了: {duration:.2f}秒")

# 緊急診断実行
emergency_quick_diagnosis()
```

## エスカレーション手順

### レベル1: 自動対応

- 自動回復機能の実行
- サーキットブレーカーのリセット
- キャッシュクリア
- ガベージコレクション

### レベル2: システム管理者対応

- 詳細診断の実行
- 設定調整
- リソース追加
- 手動最適化

### レベル3: 開発チームエスカレーション

- コード修正が必要な問題
- アーキテクチャ変更が必要な問題
- 新機能の要求

### レベル4: 緊急時対策本部

- システム全体停止
- データ復旧
- 災害時対応

## 問い合わせ時の情報収集

トラブル報告時は以下の情報を提供してください：

1. **発生時刻と状況**
2. **エラーメッセージの全文**
3. **システム状態**（CPU、メモリ使用率）
4. **直近の操作履歴**
5. **診断結果**（本ガイドの診断実行結果）

```bash
# 情報収集スクリプト
python -c "
import sys, json, datetime
sys.path.append('/home/choux1/src/github.com/0xchoux1/aide')

print('=== AIDE トラブル情報収集 ===')
print(f'収集時刻: {datetime.datetime.now()}')

# システム情報収集
try:
    from src.dashboard.enhanced_monitor import get_enhanced_monitor
    from src.resilience.error_handler import get_error_handler
    import psutil
    
    info = {
        'timestamp': datetime.datetime.now().isoformat(),
        'system_health': get_enhanced_monitor().get_system_health().to_dict() if get_enhanced_monitor().get_system_health() else None,
        'error_stats': get_error_handler().get_error_statistics(),
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent
    }
    
    filename = f'trouble_info_{datetime.datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.json'
    with open(filename, 'w') as f:
        json.dump(info, f, indent=2, default=str)
    
    print(f'情報収集完了: {filename}')
    
except Exception as e:
    print(f'情報収集エラー: {e}')
"
```

---

このトラブルシューティングガイドは、AIDE システムの安定運用を支援します。問題が解決しない場合は、収集した診断情報と共に開発チームにお問い合わせください。