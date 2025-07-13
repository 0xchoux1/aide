# AIDE 高度な機能ガイド

## 概要

このガイドでは、AIDE システムの高度な機能と設定について詳しく説明します。基本機能を理解したユーザーが、より効果的にシステムを活用するための実践的な情報を提供します。

## 目次

1. [高度な診断機能](#高度な診断機能)
2. [カスタム最適化ルール](#カスタム最適化ルール)
3. [プロファイリングと分析](#プロファイリングと分析)
4. [イベント駆動アーキテクチャ](#イベント駆動アーキテクチャ)
5. [プラグインシステム](#プラグインシステム)
6. [高度な監視設定](#高度な監視設定)
7. [カスタムメトリクス](#カスタムメトリクス)
8. [自動化ワークフロー](#自動化ワークフロー)
9. [パフォーマンスチューニング](#パフォーマンスチューニング)
10. [トラブルシューティング](#トラブルシューティング)

## 高度な診断機能

### 詳細診断の実行

```python
from src.diagnosis.intelligent_diagnostics import get_intelligent_diagnostics
import asyncio

async def advanced_diagnostics():
    """高度な診断機能の使用例"""
    diagnostics = get_intelligent_diagnostics()
    
    # 1. 包括的システム診断
    comprehensive_result = diagnostics.diagnose_system()
    print(f"システム診断完了: {len(comprehensive_result.recommendations)}件の推奨事項")
    
    # 2. パフォーマンス特化診断
    performance_result = diagnostics.diagnose_performance()
    print(f"パフォーマンス診断: {len(performance_result.issues)}件の問題")
    
    # 3. セキュリティ診断
    security_result = diagnostics.diagnose_security()
    print(f"セキュリティ診断: {len(security_result.vulnerabilities)}件の脆弱性")
    
    # 4. カスタムルールでの診断
    custom_rules = ['memory_usage', 'disk_space', 'network_latency']
    custom_result = diagnostics.diagnose_with_custom_rules(custom_rules)
    
    return {
        'comprehensive': comprehensive_result,
        'performance': performance_result,
        'security': security_result,
        'custom': custom_result
    }

# 診断実行
results = asyncio.run(advanced_diagnostics())
```

### 診断ルールのカスタマイズ

```python
from src.diagnosis.rule_engine import DiagnosticRule, RuleCondition

class CustomDiagnosticRule(DiagnosticRule):
    """カスタム診断ルールの例"""
    
    def __init__(self):
        super().__init__(
            rule_id="custom_memory_check",
            name="カスタムメモリチェック",
            category="performance",
            severity="medium"
        )
    
    def evaluate(self, context):
        """ルール評価ロジック"""
        import psutil
        
        memory = psutil.virtual_memory()
        
        if memory.percent > 85:
            return {
                'triggered': True,
                'message': f"メモリ使用率が高い: {memory.percent}%",
                'recommendations': [
                    "不要なプロセスを終了してください",
                    "メモリ最適化を実行してください"
                ],
                'metrics': {
                    'memory_percent': memory.percent,
                    'available_gb': memory.available / 1024**3
                }
            }
        
        return {'triggered': False}

# カスタムルールの登録
diagnostics = get_intelligent_diagnostics()
custom_rule = CustomDiagnosticRule()
diagnostics.register_custom_rule(custom_rule)
```

### 診断結果の詳細分析

```python
def analyze_diagnosis_results(diagnosis_result):
    """診断結果の詳細分析"""
    
    print("=== 診断結果詳細分析 ===")
    
    # 重要度別分類
    severity_counts = {}
    for recommendation in diagnosis_result.recommendations:
        severity = getattr(recommendation, 'severity', 'unknown')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    print("重要度別推奨事項:")
    for severity, count in sorted(severity_counts.items()):
        print(f"  {severity}: {count}件")
    
    # カテゴリ別分類
    category_counts = {}
    for recommendation in diagnosis_result.recommendations:
        category = getattr(recommendation, 'category', 'unknown')
        category_counts[category] = category_counts.get(category, 0) + 1
    
    print("\nカテゴリ別推奨事項:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}件")
    
    # 実行可能な改善提案
    actionable_recommendations = [
        rec for rec in diagnosis_result.recommendations
        if getattr(rec, 'actionable', False)
    ]
    
    print(f"\n実行可能な改善提案: {len(actionable_recommendations)}件")
    
    return {
        'severity_distribution': severity_counts,
        'category_distribution': category_counts,
        'actionable_count': len(actionable_recommendations)
    }

# 分析実行
analysis = analyze_diagnosis_results(comprehensive_result)
```

## カスタム最適化ルール

### 独自最適化ルールの作成

```python
from src.optimization.rule_engine import OptimizationRule
import asyncio

class CustomMemoryOptimizationRule(OptimizationRule):
    """カスタムメモリ最適化ルール"""
    
    def __init__(self):
        super().__init__(
            rule_id="custom_memory_optimization",
            name="カスタムメモリ最適化",
            category="memory",
            priority=5
        )
    
    async def can_apply(self, context):
        """適用可能性の判定"""
        import psutil
        memory = psutil.virtual_memory()
        
        # メモリ使用率が70%を超える場合に適用
        return memory.percent > 70
    
    async def apply(self, context):
        """最適化の実行"""
        improvements = []
        
        # ガベージコレクション実行
        import gc
        collected = gc.collect()
        
        if collected > 0:
            improvements.append({
                'description': f'ガベージコレクション実行: {collected}オブジェクト回収',
                'impact_score': min(collected / 100, 10),
                'category': 'memory'
            })
        
        # キャッシュクリア
        try:
            from src.resilience.fallback_system import get_fallback_system
            fallback_system = get_fallback_system()
            fallback_system.clear_cache()
            
            improvements.append({
                'description': 'フォルバックキャッシュクリア',
                'impact_score': 2,
                'category': 'memory'
            })
        except Exception as e:
            print(f"キャッシュクリアエラー: {e}")
        
        return improvements

# カスタムルールの登録と使用
async def use_custom_optimization():
    from src.optimization.system_optimizer import get_system_optimizer
    
    optimizer = get_system_optimizer()
    custom_rule = CustomMemoryOptimizationRule()
    
    # ルール登録
    optimizer.register_rule(custom_rule)
    
    # カスタムルールを含む最適化実行
    summary = await optimizer.run_optimization_cycle(['custom_memory_optimization'])
    
    print(f"カスタム最適化結果: {len(summary.improvements)}件の改善")
    for improvement in summary.improvements:
        print(f"- {improvement['description']} (効果: {improvement['impact_score']})")

# 実行
asyncio.run(use_custom_optimization())
```

### 最適化チェーンの構築

```python
class OptimizationChain:
    """最適化チェーンの管理"""
    
    def __init__(self):
        self.chains = {}
    
    def define_chain(self, chain_name, rules, conditions=None):
        """最適化チェーンの定義"""
        self.chains[chain_name] = {
            'rules': rules,
            'conditions': conditions or {},
            'execution_order': list(range(len(rules)))
        }
    
    async def execute_chain(self, chain_name, context=None):
        """チェーンの実行"""
        if chain_name not in self.chains:
            raise ValueError(f"Unknown chain: {chain_name}")
        
        chain = self.chains[chain_name]
        results = []
        
        from src.optimization.system_optimizer import get_system_optimizer
        optimizer = get_system_optimizer()
        
        for rule_id in chain['rules']:
            try:
                # 個別ルール実行
                summary = await optimizer.run_optimization_cycle([rule_id])
                results.append({
                    'rule_id': rule_id,
                    'improvements': summary.improvements,
                    'execution_time': summary.execution_time
                })
                
                print(f"✓ {rule_id} 完了: {len(summary.improvements)}件の改善")
                
            except Exception as e:
                print(f"✗ {rule_id} エラー: {e}")
                results.append({
                    'rule_id': rule_id,
                    'error': str(e)
                })
        
        return results

# 使用例
async def setup_optimization_chains():
    chain_manager = OptimizationChain()
    
    # パフォーマンス重視チェーン
    chain_manager.define_chain(
        'performance_focus',
        ['memory_optimization', 'cpu_optimization', 'async_optimization'],
        conditions={'min_memory_free': '1GB', 'max_cpu_usage': '80%'}
    )
    
    # 安定性重視チェーン
    chain_manager.define_chain(
        'stability_focus',
        ['error_reduction', 'circuit_breaker_optimization', 'retry_optimization'],
        conditions={'error_rate_threshold': '5%'}
    )
    
    # チェーン実行
    performance_results = await chain_manager.execute_chain('performance_focus')
    
    return chain_manager, performance_results

# チェーン設定と実行
chain_manager, results = asyncio.run(setup_optimization_chains())
```

## プロファイリングと分析

### 詳細パフォーマンスプロファイリング

```python
import cProfile
import pstats
import io
from contextlib import contextmanager

@contextmanager
def performance_profiler(sort_by='cumulative', limit=20):
    """パフォーマンスプロファイラー"""
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        yield profiler
    finally:
        profiler.disable()
        
        # 結果の分析
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats(sort_by)
        ps.print_stats(limit)
        
        print("=== パフォーマンスプロファイル ===")
        print(s.getvalue())

# 使用例
async def profile_system_operations():
    """システム操作のプロファイリング"""
    
    # 診断のプロファイリング
    with performance_profiler() as profiler:
        from src.diagnosis.intelligent_diagnostics import get_intelligent_diagnostics
        diagnostics = get_intelligent_diagnostics()
        result = diagnostics.diagnose_system()
    
    print(f"診断処理完了: {len(result.recommendations)}件の推奨事項")
    
    # 最適化のプロファイリング
    with performance_profiler(sort_by='tottime') as profiler:
        from src.optimization.system_optimizer import get_system_optimizer
        optimizer = get_system_optimizer()
        summary = await optimizer.run_optimization_cycle(['memory_optimization'])
    
    print(f"最適化処理完了: {len(summary.improvements)}件の改善")

asyncio.run(profile_system_operations())
```

### メモリ使用量分析

```python
import tracemalloc
import gc

class MemoryAnalyzer:
    """メモリ使用量分析ツール"""
    
    def __init__(self):
        self.snapshots = []
        self.tracking = False
    
    def start_tracking(self):
        """メモリトラッキング開始"""
        tracemalloc.start()
        self.tracking = True
        self.take_snapshot("initial")
    
    def take_snapshot(self, label):
        """スナップショット取得"""
        if not self.tracking:
            return
        
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append({
            'label': label,
            'snapshot': snapshot,
            'timestamp': time.time()
        })
    
    def analyze_memory_growth(self):
        """メモリ増加分析"""
        if len(self.snapshots) < 2:
            print("分析には最低2つのスナップショットが必要です")
            return
        
        print("=== メモリ増加分析 ===")
        
        for i in range(1, len(self.snapshots)):
            prev_snapshot = self.snapshots[i-1]['snapshot']
            curr_snapshot = self.snapshots[i]['snapshot']
            
            top_stats = curr_snapshot.compare_to(prev_snapshot, 'lineno')
            
            print(f"\n{self.snapshots[i-1]['label']} → {self.snapshots[i]['label']}:")
            print("メモリ増加上位10:")
            
            for index, stat in enumerate(top_stats[:10]):
                print(f"  {index+1}. {stat}")
    
    def get_current_memory_usage(self):
        """現在のメモリ使用量"""
        import psutil
        process = psutil.Process()
        
        return {
            'rss': process.memory_info().rss / 1024 / 1024,  # MB
            'vms': process.memory_info().vms / 1024 / 1024,  # MB
            'percent': process.memory_percent(),
            'gc_objects': len(gc.get_objects())
        }
    
    def stop_tracking(self):
        """トラッキング停止"""
        if self.tracking:
            self.take_snapshot("final")
            tracemalloc.stop()
            self.tracking = False

# 使用例
async def analyze_memory_usage():
    analyzer = MemoryAnalyzer()
    analyzer.start_tracking()
    
    # 初期状態
    print(f"初期メモリ使用量: {analyzer.get_current_memory_usage()}")
    
    # システム診断実行
    analyzer.take_snapshot("before_diagnosis")
    diagnostics = get_intelligent_diagnostics()
    result = diagnostics.diagnose_system()
    analyzer.take_snapshot("after_diagnosis")
    
    # 最適化実行
    analyzer.take_snapshot("before_optimization")
    optimizer = get_system_optimizer()
    summary = await optimizer.run_optimization_cycle()
    analyzer.take_snapshot("after_optimization")
    
    # 最終状態
    print(f"最終メモリ使用量: {analyzer.get_current_memory_usage()}")
    
    # 分析結果表示
    analyzer.analyze_memory_growth()
    analyzer.stop_tracking()

asyncio.run(analyze_memory_usage())
```

## イベント駆動アーキテクチャ

### イベントシステムの活用

```python
import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Dict, List
from datetime import datetime

@dataclass
class SystemEvent:
    """システムイベント"""
    event_type: str
    component: str
    data: Dict[str, Any]
    timestamp: datetime
    severity: str = "info"

class EventBus:
    """イベントバスシステム"""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_history: List[SystemEvent] = []
        self.max_history = 1000
    
    def subscribe(self, event_type: str, handler: Callable):
        """イベント購読"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    async def publish(self, event: SystemEvent):
        """イベント発行"""
        # 履歴に追加
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]
        
        # 購読者に通知
        if event.event_type in self.subscribers:
            tasks = []
            for handler in self.subscribers[event.event_type]:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(handler(event))
                else:
                    tasks.append(asyncio.to_thread(handler, event))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_events_by_type(self, event_type: str, hours: int = 24):
        """タイプ別イベント取得"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            event for event in self.event_history
            if event.event_type == event_type and event.timestamp >= cutoff
        ]

# グローバルイベントバス
event_bus = EventBus()

# イベントハンドラーの定義
async def handle_performance_degradation(event: SystemEvent):
    """パフォーマンス低下イベントハンドラー"""
    print(f"🔥 パフォーマンス低下検出: {event.data}")
    
    # 自動最適化実行
    try:
        from src.optimization.system_optimizer import get_system_optimizer
        optimizer = get_system_optimizer()
        summary = await optimizer.run_optimization_cycle(['memory_optimization', 'cpu_optimization'])
        
        # 改善イベント発行
        improvement_event = SystemEvent(
            event_type="optimization_completed",
            component="auto_optimizer",
            data={
                'triggered_by': event.data,
                'improvements': len(summary.improvements),
                'execution_time': summary.execution_time
            },
            timestamp=datetime.now()
        )
        await event_bus.publish(improvement_event)
        
    except Exception as e:
        print(f"自動最適化エラー: {e}")

def handle_error_spike(event: SystemEvent):
    """エラー急増イベントハンドラー"""
    print(f"⚠️ エラー急増検出: {event.data}")
    
    # サーキットブレーカーの状態確認
    from src.resilience.circuit_breaker import get_circuit_breaker_manager
    circuit_manager = get_circuit_breaker_manager()
    health_summary = circuit_manager.get_health_summary()
    
    if health_summary['unhealthy_circuits'] > 0:
        print(f"異常サーキット数: {health_summary['unhealthy_circuits']}")
        # 必要に応じてリセット
        # circuit_manager.reset_all_circuits()

# イベント購読設定
event_bus.subscribe("performance_degradation", handle_performance_degradation)
event_bus.subscribe("error_spike", handle_error_spike)

# イベント発行例
async def monitor_and_emit_events():
    """監視とイベント発行"""
    from src.dashboard.enhanced_monitor import get_enhanced_monitor
    
    monitor = get_enhanced_monitor()
    
    while True:
        health = monitor.get_system_health()
        
        if health and health.overall_score < 70:
            # パフォーマンス低下イベント
            event = SystemEvent(
                event_type="performance_degradation",
                component="system_monitor",
                data={
                    'health_score': health.overall_score,
                    'active_issues': len(health.active_issues)
                },
                timestamp=datetime.now(),
                severity="warning"
            )
            await event_bus.publish(event)
        
        await asyncio.sleep(30)  # 30秒間隔

# イベント駆動監視の開始
# asyncio.create_task(monitor_and_emit_events())
```

## プラグインシステム

### プラグインアーキテクチャ

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import importlib
import os

class AIDePlugin(ABC):
    """AIDE プラグインベースクラス"""
    
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.enabled = True
        self.config = {}
    
    @abstractmethod
    async def initialize(self, context: Dict[str, Any]) -> bool:
        """プラグイン初期化"""
        pass
    
    @abstractmethod
    async def execute(self, data: Any) -> Any:
        """プラグイン実行"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """プラグインクリーンアップ"""
        pass
    
    def configure(self, config: Dict[str, Any]):
        """プラグイン設定"""
        self.config.update(config)

class PluginManager:
    """プラグイン管理システム"""
    
    def __init__(self):
        self.plugins: Dict[str, AIDePlugin] = {}
        self.plugin_hooks: Dict[str, List[str]] = {}
    
    def register_plugin(self, plugin: AIDePlugin):
        """プラグイン登録"""
        self.plugins[plugin.name] = plugin
        print(f"プラグイン登録: {plugin.name} v{plugin.version}")
    
    def register_hook(self, hook_name: str, plugin_name: str):
        """フック登録"""
        if hook_name not in self.plugin_hooks:
            self.plugin_hooks[hook_name] = []
        self.plugin_hooks[hook_name].append(plugin_name)
    
    async def initialize_all(self, context: Dict[str, Any]):
        """全プラグイン初期化"""
        for plugin in self.plugins.values():
            try:
                if plugin.enabled:
                    success = await plugin.initialize(context)
                    if not success:
                        print(f"プラグイン初期化失敗: {plugin.name}")
                        plugin.enabled = False
            except Exception as e:
                print(f"プラグイン初期化エラー {plugin.name}: {e}")
                plugin.enabled = False
    
    async def execute_hook(self, hook_name: str, data: Any) -> List[Any]:
        """フック実行"""
        results = []
        
        if hook_name in self.plugin_hooks:
            for plugin_name in self.plugin_hooks[hook_name]:
                plugin = self.plugins.get(plugin_name)
                if plugin and plugin.enabled:
                    try:
                        result = await plugin.execute(data)
                        results.append(result)
                    except Exception as e:
                        print(f"プラグイン実行エラー {plugin_name}: {e}")
        
        return results
    
    def load_plugins_from_directory(self, plugin_dir: str):
        """ディレクトリからプラグイン読み込み"""
        if not os.path.exists(plugin_dir):
            return
        
        for filename in os.listdir(plugin_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(
                        module_name, 
                        os.path.join(plugin_dir, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # プラグインクラスを検索
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, AIDePlugin) and 
                            attr != AIDePlugin):
                            
                            plugin = attr()
                            self.register_plugin(plugin)
                            
                except Exception as e:
                    print(f"プラグイン読み込みエラー {filename}: {e}")

# プラグインの実装例
class CustomMetricsPlugin(AIDePlugin):
    """カスタムメトリクス収集プラグイン"""
    
    def __init__(self):
        super().__init__("custom_metrics", "1.0.0")
        self.metrics_cache = {}
    
    async def initialize(self, context: Dict[str, Any]) -> bool:
        """初期化"""
        try:
            from src.dashboard.metrics_collector import get_metrics_collector
            self.metrics_collector = get_metrics_collector()
            return True
        except Exception as e:
            print(f"カスタムメトリクスプラグイン初期化エラー: {e}")
            return False
    
    async def execute(self, data: Any) -> Any:
        """カスタムメトリクス収集実行"""
        import psutil
        import time
        
        # システムメトリクス収集
        metrics = {
            'timestamp': time.time(),
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'network_io': psutil.net_io_counters()._asdict(),
            'process_count': len(psutil.pids())
        }
        
        # メトリクス記録
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)):
                self.metrics_collector.record_metric(f"custom_{metric_name}", value)
        
        self.metrics_cache['latest'] = metrics
        return metrics
    
    async def cleanup(self) -> None:
        """クリーンアップ"""
        self.metrics_cache.clear()

# プラグインマネージャーの使用
async def setup_plugin_system():
    plugin_manager = PluginManager()
    
    # カスタムプラグイン登録
    custom_metrics = CustomMetricsPlugin()
    plugin_manager.register_plugin(custom_metrics)
    plugin_manager.register_hook("metrics_collection", "custom_metrics")
    
    # プラグインディレクトリから読み込み
    # plugin_manager.load_plugins_from_directory("plugins/")
    
    # 初期化
    context = {"config": {}, "version": "3.3.0"}
    await plugin_manager.initialize_all(context)
    
    # フック実行例
    results = await plugin_manager.execute_hook("metrics_collection", {})
    print(f"メトリクス収集結果: {len(results)}件")
    
    return plugin_manager

# プラグインシステム設定
# plugin_manager = asyncio.run(setup_plugin_system())
```

## 高度な監視設定

### カスタム監視ダッシュボード

```python
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

class CustomDashboard:
    """カスタム監視ダッシュボード"""
    
    def __init__(self):
        self.widgets = {}
        self.refresh_intervals = {}
        self.data_sources = {}
    
    def add_widget(self, widget_id: str, widget_config: Dict[str, Any]):
        """ウィジェット追加"""
        self.widgets[widget_id] = widget_config
        self.refresh_intervals[widget_id] = widget_config.get('refresh_interval', 30)
    
    def add_data_source(self, source_id: str, source_func: callable):
        """データソース追加"""
        self.data_sources[source_id] = source_func
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """ダッシュボードデータ取得"""
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'widgets': {}
        }
        
        for widget_id, widget_config in self.widgets.items():
            try:
                data_source = widget_config.get('data_source')
                if data_source and data_source in self.data_sources:
                    data = await self._execute_data_source(data_source)
                    dashboard_data['widgets'][widget_id] = {
                        'config': widget_config,
                        'data': data,
                        'last_updated': datetime.now().isoformat()
                    }
            except Exception as e:
                dashboard_data['widgets'][widget_id] = {
                    'config': widget_config,
                    'error': str(e),
                    'last_updated': datetime.now().isoformat()
                }
        
        return dashboard_data
    
    async def _execute_data_source(self, source_id: str):
        """データソース実行"""
        source_func = self.data_sources[source_id]
        if asyncio.iscoroutinefunction(source_func):
            return await source_func()
        else:
            return source_func()

# データソース関数の定義
async def get_system_health_data():
    """システムヘルスデータ取得"""
    from src.dashboard.enhanced_monitor import get_enhanced_monitor
    
    monitor = get_enhanced_monitor()
    health = monitor.get_system_health()
    
    if health:
        return {
            'overall_score': health.overall_score,
            'status': health.overall_status.value,
            'active_issues_count': len(health.active_issues),
            'components': {
                component: info.get('score', 0)
                for component, info in health.component_health.items()
                if 'score' in info
            }
        }
    return None

def get_resource_usage_data():
    """リソース使用量データ取得"""
    import psutil
    
    return {
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent,
        'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
    }

async def get_error_statistics_data():
    """エラー統計データ取得"""
    from src.resilience.error_handler import get_error_handler
    
    error_handler = get_error_handler()
    stats = error_handler.get_error_statistics()
    trends = error_handler.get_error_trends(hours=24)
    
    return {
        'total_errors': stats['error_stats']['total_errors'],
        'error_rate': stats['error_stats']['total_errors'] / max(1, 24 * 3600),  # エラー/秒
        'category_distribution': trends['category_trends'],
        'recent_errors_count': len(stats['recent_errors'])
    }

# カスタムダッシュボードの設定
async def setup_custom_dashboard():
    dashboard = CustomDashboard()
    
    # データソース登録
    dashboard.add_data_source('system_health', get_system_health_data)
    dashboard.add_data_source('resource_usage', get_resource_usage_data)
    dashboard.add_data_source('error_statistics', get_error_statistics_data)
    
    # ウィジェット追加
    dashboard.add_widget('health_overview', {
        'title': 'システムヘルス概要',
        'type': 'gauge',
        'data_source': 'system_health',
        'refresh_interval': 15
    })
    
    dashboard.add_widget('resource_monitor', {
        'title': 'リソース監視',
        'type': 'multi_gauge',
        'data_source': 'resource_usage',
        'refresh_interval': 5
    })
    
    dashboard.add_widget('error_trends', {
        'title': 'エラー傾向',
        'type': 'line_chart',
        'data_source': 'error_statistics',
        'refresh_interval': 60
    })
    
    # ダッシュボードデータ取得
    data = await dashboard.get_dashboard_data()
    
    print("=== カスタムダッシュボード ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    return dashboard

# ダッシュボード設定
# dashboard = asyncio.run(setup_custom_dashboard())
```

### アラートの詳細設定

```python
from src.dashboard.enhanced_monitor import AlertRule, get_enhanced_monitor
from dataclasses import dataclass
from typing import List, Callable, Optional

@dataclass
class AdvancedAlertRule:
    """高度なアラートルール"""
    rule_id: str
    name: str
    description: str
    conditions: List[Dict[str, Any]]  # 複数条件
    severity: str
    cooldown_minutes: int = 5
    escalation_rules: Optional[List[Dict[str, Any]]] = None
    notification_channels: Optional[List[str]] = None
    auto_actions: Optional[List[Callable]] = None
    enabled: bool = True

class AdvancedAlertManager:
    """高度なアラート管理"""
    
    def __init__(self):
        self.rules: Dict[str, AdvancedAlertRule] = {}
        self.alert_history: List[Dict[str, Any]] = []
        self.notification_channels = {}
        self.auto_actions = {}
    
    def add_rule(self, rule: AdvancedAlertRule):
        """アラートルール追加"""
        self.rules[rule.rule_id] = rule
    
    def add_notification_channel(self, channel_id: str, handler: Callable):
        """通知チャネル追加"""
        self.notification_channels[channel_id] = handler
    
    def add_auto_action(self, action_id: str, action_func: Callable):
        """自動アクション追加"""
        self.auto_actions[action_id] = action_func
    
    async def evaluate_rules(self, metrics: Dict[str, Any]):
        """ルール評価"""
        triggered_alerts = []
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            try:
                if await self._evaluate_conditions(rule.conditions, metrics):
                    alert = {
                        'rule_id': rule.rule_id,
                        'name': rule.name,
                        'description': rule.description,
                        'severity': rule.severity,
                        'timestamp': datetime.now().isoformat(),
                        'metrics': metrics
                    }
                    
                    triggered_alerts.append(alert)
                    await self._handle_alert(rule, alert)
                    
            except Exception as e:
                print(f"ルール評価エラー {rule.rule_id}: {e}")
        
        return triggered_alerts
    
    async def _evaluate_conditions(self, conditions: List[Dict[str, Any]], 
                                 metrics: Dict[str, Any]) -> bool:
        """条件評価"""
        for condition in conditions:
            operator = condition.get('operator', 'and')
            metric_name = condition.get('metric')
            threshold = condition.get('threshold')
            comparison = condition.get('comparison', '>')
            
            if metric_name not in metrics:
                continue
            
            value = metrics[metric_name]
            
            # 比較実行
            if comparison == '>':
                condition_met = value > threshold
            elif comparison == '<':
                condition_met = value < threshold
            elif comparison == '>=':
                condition_met = value >= threshold
            elif comparison == '<=':
                condition_met = value <= threshold
            elif comparison == '==':
                condition_met = value == threshold
            elif comparison == '!=':
                condition_met = value != threshold
            else:
                condition_met = False
            
            if operator == 'and' and not condition_met:
                return False
            elif operator == 'or' and condition_met:
                return True
        
        return True
    
    async def _handle_alert(self, rule: AdvancedAlertRule, alert: Dict[str, Any]):
        """アラートハンドリング"""
        # 履歴に追加
        self.alert_history.append(alert)
        
        # 通知送信
        if rule.notification_channels:
            for channel_id in rule.notification_channels:
                if channel_id in self.notification_channels:
                    try:
                        handler = self.notification_channels[channel_id]
                        await handler(alert)
                    except Exception as e:
                        print(f"通知送信エラー {channel_id}: {e}")
        
        # 自動アクション実行
        if rule.auto_actions:
            for action in rule.auto_actions:
                try:
                    if asyncio.iscoroutinefunction(action):
                        await action(alert)
                    else:
                        action(alert)
                except Exception as e:
                    print(f"自動アクション実行エラー: {e}")

# 通知ハンドラーの定義
async def email_notification_handler(alert: Dict[str, Any]):
    """メール通知ハンドラー"""
    print(f"📧 メール通知: {alert['name']} - {alert['severity']}")
    # 実際のメール送信実装...

async def slack_notification_handler(alert: Dict[str, Any]):
    """Slack通知ハンドラー"""
    print(f"💬 Slack通知: {alert['name']} - {alert['severity']}")
    # 実際のSlack API呼び出し実装...

# 自動アクションの定義
async def auto_optimization_action(alert: Dict[str, Any]):
    """自動最適化アクション"""
    print(f"🔧 自動最適化実行: {alert['rule_id']}")
    
    try:
        from src.optimization.system_optimizer import get_system_optimizer
        optimizer = get_system_optimizer()
        
        # アラートの種類に応じた最適化
        if 'memory' in alert['name'].lower():
            await optimizer.run_optimization_cycle(['memory_optimization'])
        elif 'cpu' in alert['name'].lower():
            await optimizer.run_optimization_cycle(['cpu_optimization'])
        else:
            await optimizer.run_optimization_cycle()
            
    except Exception as e:
        print(f"自動最適化エラー: {e}")

def auto_circuit_breaker_reset_action(alert: Dict[str, Any]):
    """サーキットブレーカー自動リセットアクション"""
    print(f"⚡ サーキットブレーカー自動リセット: {alert['rule_id']}")
    
    try:
        from src.resilience.circuit_breaker import get_circuit_breaker_manager
        manager = get_circuit_breaker_manager()
        manager.reset_all_circuits()
    except Exception as e:
        print(f"サーキットブレーカーリセットエラー: {e}")

# 高度なアラート設定
async def setup_advanced_alerts():
    alert_manager = AdvancedAlertManager()
    
    # 通知チャネル登録
    alert_manager.add_notification_channel('email', email_notification_handler)
    alert_manager.add_notification_channel('slack', slack_notification_handler)
    
    # 自動アクション登録
    alert_manager.add_auto_action('auto_optimize', auto_optimization_action)
    alert_manager.add_auto_action('reset_circuit_breaker', auto_circuit_breaker_reset_action)
    
    # 複合条件アラート
    complex_alert = AdvancedAlertRule(
        rule_id="performance_critical",
        name="パフォーマンス危険",
        description="CPU高使用率かつメモリ不足の複合条件",
        conditions=[
            {'metric': 'cpu_percent', 'comparison': '>', 'threshold': 80, 'operator': 'and'},
            {'metric': 'memory_percent', 'comparison': '>', 'threshold': 85, 'operator': 'and'}
        ],
        severity="critical",
        cooldown_minutes=10,
        notification_channels=['email', 'slack'],
        auto_actions=[auto_optimization_action]
    )
    
    alert_manager.add_rule(complex_alert)
    
    # エスカレーション付きアラート
    escalating_alert = AdvancedAlertRule(
        rule_id="error_rate_escalating",
        name="エラー率エスカレーション",
        description="エラー率上昇のエスカレーション",
        conditions=[
            {'metric': 'error_rate', 'comparison': '>', 'threshold': 0.05}  # 5%
        ],
        severity="high",
        escalation_rules=[
            {'after_minutes': 5, 'severity': 'critical', 'channels': ['email']},
            {'after_minutes': 15, 'severity': 'emergency', 'channels': ['email', 'slack']}
        ],
        notification_channels=['slack'],
        auto_actions=[auto_circuit_breaker_reset_action]
    )
    
    alert_manager.add_rule(escalating_alert)
    
    return alert_manager

# アラート設定
# alert_manager = asyncio.run(setup_advanced_alerts())
```

このガイドでは、AIDE システムの高度な機能について詳しく説明しました。これらの機能を活用することで、より効果的なシステム管理と最適化が可能になります。

各機能の実装においては、システムの安定性とパフォーマンスを考慮し、段階的に導入することを推奨します。また、本番環境での使用前には、必ず開発・テスト環境での十分な検証を行ってください。

---

次は、[統合ガイド](integration_guide.md)で他システムとの連携方法を確認することをお勧めします。