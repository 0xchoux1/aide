"""
AIDE メトリクス収集システム

各種メトリクスの収集、集計、保存を管理
"""

import time
import json
import threading
import queue
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import statistics
from collections import defaultdict, deque

from ..config import get_config_manager
from ..logging import get_logger
from ..self_improvement.diagnostics import SystemDiagnostics, DiagnosticResult


class MetricType(Enum):
    """メトリクスタイプ"""
    GAUGE = "gauge"          # 瞬間値（CPU使用率など）
    COUNTER = "counter"      # 累積値（リクエスト数など）
    HISTOGRAM = "histogram"  # 分布（レスポンスタイムなど）
    SUMMARY = "summary"      # 統計サマリー


@dataclass
class MetricPoint:
    """メトリクスポイント"""
    timestamp: float
    value: float
    labels: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "timestamp": self.timestamp,
            "value": self.value,
            "labels": self.labels or {}
        }


@dataclass
class MetricSeries:
    """メトリクス時系列データ"""
    name: str
    metric_type: MetricType
    description: str
    unit: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    points: List[MetricPoint] = None
    
    def __post_init__(self):
        if self.points is None:
            self.points = []
    
    def add_point(self, value: float, timestamp: Optional[float] = None, **labels):
        """データポイント追加"""
        if timestamp is None:
            timestamp = time.time()
        
        point_labels = self.labels.copy() if self.labels else {}
        point_labels.update(labels)
        
        point = MetricPoint(timestamp, value, point_labels if point_labels else None)
        self.points.append(point)
    
    def get_latest(self) -> Optional[MetricPoint]:
        """最新ポイント取得"""
        return self.points[-1] if self.points else None
    
    def get_points_in_range(self, start_time: float, end_time: float) -> List[MetricPoint]:
        """指定期間のポイント取得"""
        return [
            p for p in self.points
            if start_time <= p.timestamp <= end_time
        ]
    
    def calculate_stats(self, window_seconds: int = 300) -> Dict[str, float]:
        """統計計算"""
        if not self.points:
            return {}
        
        now = time.time()
        recent_points = self.get_points_in_range(now - window_seconds, now)
        
        if not recent_points:
            return {}
        
        values = [p.value for p in recent_points]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0
        }


class SystemMetrics:
    """システムメトリクス収集"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # psutil使用可能性チェック
        try:
            import psutil
            self.psutil = psutil
            self.psutil_available = True
        except ImportError:
            self.psutil = None
            self.psutil_available = False
            self.logger.warning("psutil未インストール - システムメトリクス制限")
    
    def collect_cpu_metrics(self) -> Dict[str, float]:
        """CPU メトリクス収集"""
        metrics = {}
        
        if self.psutil_available:
            try:
                # CPU使用率
                cpu_percent = self.psutil.cpu_percent(interval=0.1)
                metrics['cpu_usage_percent'] = cpu_percent
                
                # CPU別使用率
                cpu_per_core = self.psutil.cpu_percent(interval=0.1, percpu=True)
                for i, percent in enumerate(cpu_per_core):
                    metrics[f'cpu_core_{i}_percent'] = percent
                
                # CPUカウント
                metrics['cpu_count'] = self.psutil.cpu_count()
                metrics['cpu_count_logical'] = self.psutil.cpu_count(logical=True)
                
                # ロードアベレージ（Unix系のみ）
                if hasattr(self.psutil, 'getloadavg'):
                    load1, load5, load15 = self.psutil.getloadavg()
                    metrics['load_average_1m'] = load1
                    metrics['load_average_5m'] = load5
                    metrics['load_average_15m'] = load15
                
            except Exception as e:
                self.logger.error(f"CPU メトリクス収集エラー: {str(e)}")
        
        return metrics
    
    def collect_memory_metrics(self) -> Dict[str, float]:
        """メモリメトリクス収集"""
        metrics = {}
        
        if self.psutil_available:
            try:
                # 仮想メモリ
                vm = self.psutil.virtual_memory()
                metrics['memory_total_mb'] = vm.total / (1024 * 1024)
                metrics['memory_available_mb'] = vm.available / (1024 * 1024)
                metrics['memory_used_mb'] = vm.used / (1024 * 1024)
                metrics['memory_percent'] = vm.percent
                
                # スワップメモリ
                swap = self.psutil.swap_memory()
                metrics['swap_total_mb'] = swap.total / (1024 * 1024)
                metrics['swap_used_mb'] = swap.used / (1024 * 1024)
                metrics['swap_percent'] = swap.percent
                
            except Exception as e:
                self.logger.error(f"メモリメトリクス収集エラー: {str(e)}")
        
        return metrics
    
    def collect_disk_metrics(self) -> Dict[str, float]:
        """ディスクメトリクス収集"""
        metrics = {}
        
        if self.psutil_available:
            try:
                # ディスク使用量
                disk = self.psutil.disk_usage('/')
                metrics['disk_total_gb'] = disk.total / (1024 ** 3)
                metrics['disk_used_gb'] = disk.used / (1024 ** 3)
                metrics['disk_free_gb'] = disk.free / (1024 ** 3)
                metrics['disk_percent'] = disk.percent
                
                # ディスクI/O（利用可能な場合）
                try:
                    io_counters = self.psutil.disk_io_counters()
                    if io_counters:
                        metrics['disk_read_bytes'] = io_counters.read_bytes
                        metrics['disk_write_bytes'] = io_counters.write_bytes
                        metrics['disk_read_count'] = io_counters.read_count
                        metrics['disk_write_count'] = io_counters.write_count
                except:
                    pass
                
            except Exception as e:
                self.logger.error(f"ディスクメトリクス収集エラー: {str(e)}")
        
        return metrics
    
    def collect_network_metrics(self) -> Dict[str, float]:
        """ネットワークメトリクス収集"""
        metrics = {}
        
        if self.psutil_available:
            try:
                # ネットワークI/O
                net_io = self.psutil.net_io_counters()
                metrics['network_bytes_sent'] = net_io.bytes_sent
                metrics['network_bytes_recv'] = net_io.bytes_recv
                metrics['network_packets_sent'] = net_io.packets_sent
                metrics['network_packets_recv'] = net_io.packets_recv
                metrics['network_errin'] = net_io.errin
                metrics['network_errout'] = net_io.errout
                metrics['network_dropin'] = net_io.dropin
                metrics['network_dropout'] = net_io.dropout
                
            except Exception as e:
                self.logger.error(f"ネットワークメトリクス収集エラー: {str(e)}")
        
        return metrics
    
    def collect_all(self) -> Dict[str, float]:
        """全システムメトリクス収集"""
        all_metrics = {}
        
        all_metrics.update(self.collect_cpu_metrics())
        all_metrics.update(self.collect_memory_metrics())
        all_metrics.update(self.collect_disk_metrics())
        all_metrics.update(self.collect_network_metrics())
        
        return all_metrics


class PerformanceMetrics:
    """パフォーマンスメトリクス収集"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.response_times: deque = deque(maxlen=1000)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.operation_counts: Dict[str, int] = defaultdict(int)
        self.lock = threading.Lock()
    
    def record_response_time(self, operation: str, duration: float, success: bool = True):
        """レスポンスタイム記録"""
        with self.lock:
            self.response_times.append({
                "operation": operation,
                "duration": duration,
                "success": success,
                "timestamp": time.time()
            })
            
            self.operation_counts[operation] += 1
            
            if not success:
                self.error_counts[operation] += 1
    
    def get_response_time_stats(self, operation: Optional[str] = None, 
                               window_seconds: int = 300) -> Dict[str, Any]:
        """レスポンスタイム統計取得"""
        with self.lock:
            now = time.time()
            cutoff_time = now - window_seconds
            
            # フィルタリング
            recent_times = [
                rt for rt in self.response_times
                if rt["timestamp"] > cutoff_time and
                (operation is None or rt["operation"] == operation)
            ]
            
            if not recent_times:
                return {}
            
            durations = [rt["duration"] for rt in recent_times]
            successful = [rt for rt in recent_times if rt["success"]]
            
            return {
                "count": len(recent_times),
                "success_count": len(successful),
                "error_count": len(recent_times) - len(successful),
                "success_rate": len(successful) / len(recent_times) * 100,
                "min_ms": min(durations) * 1000,
                "max_ms": max(durations) * 1000,
                "mean_ms": statistics.mean(durations) * 1000,
                "median_ms": statistics.median(durations) * 1000,
                "p95_ms": self._percentile(durations, 95) * 1000,
                "p99_ms": self._percentile(durations, 99) * 1000
            }
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """パーセンタイル計算"""
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_error_rates(self) -> Dict[str, float]:
        """エラー率取得"""
        with self.lock:
            error_rates = {}
            
            for operation, total_count in self.operation_counts.items():
                error_count = self.error_counts.get(operation, 0)
                error_rate = (error_count / total_count * 100) if total_count > 0 else 0
                error_rates[f"{operation}_error_rate"] = error_rate
            
            return error_rates


class MetricsCollector:
    """メトリクス収集管理クラス"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger(__name__)
        
        # メトリクスストレージ
        self.series: Dict[str, MetricSeries] = {}
        self.lock = threading.Lock()
        
        # 収集モジュール
        self.system_metrics = SystemMetrics()
        self.performance_metrics = PerformanceMetrics()
        self.diagnostics = SystemDiagnostics()
        
        # 収集設定
        self.collection_interval = self.config_manager.get(
            "dashboard.collection_interval_seconds", 30
        )
        self.retention_hours = self.config_manager.get(
            "dashboard.retention_hours", 24
        )
        
        # バックグラウンド収集
        self.collection_thread = None
        self.stop_event = threading.Event()
        
        # メトリクス初期化
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """メトリクス定義初期化"""
        # システムメトリクス
        self.register_metric(
            "system_cpu_usage",
            MetricType.GAUGE,
            "CPU使用率",
            unit="percent"
        )
        
        self.register_metric(
            "system_memory_usage",
            MetricType.GAUGE,
            "メモリ使用率",
            unit="percent"
        )
        
        self.register_metric(
            "system_disk_usage",
            MetricType.GAUGE,
            "ディスク使用率",
            unit="percent"
        )
        
        # パフォーマンスメトリクス
        self.register_metric(
            "response_time",
            MetricType.HISTOGRAM,
            "レスポンスタイム",
            unit="milliseconds"
        )
        
        self.register_metric(
            "error_rate",
            MetricType.GAUGE,
            "エラー率",
            unit="percent"
        )
        
        # 診断メトリクス
        self.register_metric(
            "health_score",
            MetricType.GAUGE,
            "システムヘルススコア",
            unit="score"
        )
    
    def register_metric(self, name: str, metric_type: MetricType, 
                       description: str, unit: Optional[str] = None,
                       labels: Optional[Dict[str, str]] = None):
        """メトリクス登録"""
        with self.lock:
            if name not in self.series:
                self.series[name] = MetricSeries(
                    name=name,
                    metric_type=metric_type,
                    description=description,
                    unit=unit,
                    labels=labels
                )
                self.logger.debug(f"メトリクス登録: {name}")
    
    def record_metric(self, name: str, value: float, 
                     timestamp: Optional[float] = None, **labels):
        """メトリクス記録"""
        with self.lock:
            if name in self.series:
                self.series[name].add_point(value, timestamp, **labels)
            else:
                self.logger.warning(f"未登録メトリクス: {name}")
    
    def get_metric_series(self, name: str) -> Optional[MetricSeries]:
        """メトリクス時系列取得"""
        with self.lock:
            return self.series.get(name)
    
    def get_all_metrics(self) -> Dict[str, MetricSeries]:
        """全メトリクス取得"""
        with self.lock:
            return self.series.copy()
    
    def start_collection(self):
        """バックグラウンド収集開始"""
        if self.collection_thread is None or not self.collection_thread.is_alive():
            self.stop_event.clear()
            self.collection_thread = threading.Thread(
                target=self._collection_loop,
                daemon=True
            )
            self.collection_thread.start()
            self.logger.info("メトリクス収集開始")
    
    def stop_collection(self):
        """バックグラウンド収集停止"""
        if self.collection_thread and self.collection_thread.is_alive():
            self.stop_event.set()
            self.collection_thread.join(timeout=5.0)
            self.logger.info("メトリクス収集停止")
    
    def _collection_loop(self):
        """収集ループ"""
        while not self.stop_event.is_set():
            try:
                # システムメトリクス収集
                self._collect_system_metrics()
                
                # パフォーマンスメトリクス収集
                self._collect_performance_metrics()
                
                # 診断メトリクス収集
                self._collect_diagnostic_metrics()
                
                # 古いデータクリーンアップ
                self._cleanup_old_data()
                
            except Exception as e:
                self.logger.error(f"メトリクス収集エラー: {str(e)}")
            
            # 次回収集まで待機
            self.stop_event.wait(self.collection_interval)
    
    def _collect_system_metrics(self):
        """システムメトリクス収集"""
        try:
            metrics = self.system_metrics.collect_all()
            
            # 主要メトリクス記録
            if 'cpu_usage_percent' in metrics:
                self.record_metric("system_cpu_usage", metrics['cpu_usage_percent'])
            
            if 'memory_percent' in metrics:
                self.record_metric("system_memory_usage", metrics['memory_percent'])
            
            if 'disk_percent' in metrics:
                self.record_metric("system_disk_usage", metrics['disk_percent'])
            
            # その他のメトリクス
            for key, value in metrics.items():
                if key not in ['cpu_usage_percent', 'memory_percent', 'disk_percent']:
                    self.record_metric(f"system_{key}", value)
                    
        except Exception as e:
            self.logger.error(f"システムメトリクス収集エラー: {str(e)}")
    
    def _collect_performance_metrics(self):
        """パフォーマンスメトリクス収集"""
        try:
            # レスポンスタイム統計
            rt_stats = self.performance_metrics.get_response_time_stats()
            if rt_stats:
                self.record_metric("response_time", rt_stats.get('mean_ms', 0))
                self.record_metric("response_time_p95", rt_stats.get('p95_ms', 0))
                self.record_metric("response_time_p99", rt_stats.get('p99_ms', 0))
                self.record_metric("success_rate", rt_stats.get('success_rate', 100))
            
            # エラー率
            error_rates = self.performance_metrics.get_error_rates()
            for operation, rate in error_rates.items():
                self.record_metric("error_rate", rate, operation=operation)
                
        except Exception as e:
            self.logger.error(f"パフォーマンスメトリクス収集エラー: {str(e)}")
    
    def _collect_diagnostic_metrics(self):
        """診断メトリクス収集"""
        try:
            # ヘルス概要取得
            health_summary = self.diagnostics.get_system_health_summary()
            
            if 'health_score' in health_summary:
                self.record_metric("health_score", health_summary['health_score'])
            
            # ステータス別カウント
            if 'status_distribution' in health_summary:
                for status, count in health_summary['status_distribution'].items():
                    self.record_metric(f"diagnostic_status_{status}", count)
                    
        except Exception as e:
            self.logger.error(f"診断メトリクス収集エラー: {str(e)}")
    
    def _cleanup_old_data(self):
        """古いデータクリーンアップ"""
        cutoff_time = time.time() - (self.retention_hours * 3600)
        
        with self.lock:
            for series in self.series.values():
                # 古いポイントを削除
                series.points = [
                    p for p in series.points
                    if p.timestamp > cutoff_time
                ]
    
    def export_metrics(self, format: str = "json") -> str:
        """メトリクスエクスポート"""
        with self.lock:
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "metrics": {}
            }
            
            for name, series in self.series.items():
                latest = series.get_latest()
                stats = series.calculate_stats()
                
                export_data["metrics"][name] = {
                    "type": series.metric_type.value,
                    "description": series.description,
                    "unit": series.unit,
                    "latest_value": latest.value if latest else None,
                    "latest_timestamp": latest.timestamp if latest else None,
                    "statistics": stats,
                    "point_count": len(series.points)
                }
            
            if format == "json":
                return json.dumps(export_data, indent=2, default=str)
            else:
                # 他の形式は後で実装
                return str(export_data)


# グローバルメトリクスコレクター
_global_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """グローバルメトリクスコレクター取得"""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector()
    return _global_metrics_collector