"""
AIDE パフォーマンスプロファイラー

関数・コード実行時間の詳細分析とボトルネック特定
"""

import time
import cProfile
import pstats
import io
import threading
import functools
from typing import Dict, List, Optional, Any, Callable, NamedTuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from datetime import datetime
import sys
import traceback
import linecache

from ..config import get_config_manager
from ..logging import get_logger


@dataclass
class ProfileResult:
    """プロファイル結果"""
    function_name: str
    filename: str
    line_number: int
    call_count: int
    total_time: float
    cumulative_time: float
    avg_time: float
    percentage: float
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


@dataclass
class BottleneckInfo:
    """ボトルネック情報"""
    function_name: str
    total_time: float
    call_count: int
    avg_time: float
    impact_score: float  # ボトルネックの影響度
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


class ExecutionTimer:
    """実行時間測定"""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.elapsed_time = 0
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.elapsed_time = self.end_time - self.start_time
    
    def get_elapsed_ms(self) -> float:
        """経過時間（ミリ秒）取得"""
        return self.elapsed_time * 1000


class FunctionProfiler:
    """関数レベルプロファイラー"""
    
    def __init__(self):
        self.execution_times: Dict[str, List[float]] = defaultdict(list)
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.lock = threading.Lock()
        self.enabled = True
        
        self.logger = get_logger(__name__)
    
    def profile_function(self, func_name: str = None):
        """関数プロファイリングデコレータ"""
        def decorator(func):
            name = func_name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.perf_counter()
                    execution_time = end_time - start_time
                    
                    with self.lock:
                        self.execution_times[name].append(execution_time)
                        self.call_counts[name] += 1
                        
                        # 履歴サイズ制限
                        if len(self.execution_times[name]) > 1000:
                            self.execution_times[name] = self.execution_times[name][-500:]
            
            return wrapper
        return decorator
    
    def record_execution(self, function_name: str, execution_time: float):
        """実行時間記録"""
        with self.lock:
            self.execution_times[function_name].append(execution_time)
            self.call_counts[function_name] += 1
    
    def get_stats(self, function_name: str = None) -> Dict[str, Any]:
        """統計取得"""
        with self.lock:
            if function_name:
                if function_name not in self.execution_times:
                    return {}
                
                times = self.execution_times[function_name]
                return self._calculate_stats(function_name, times)
            else:
                stats = {}
                for func_name, times in self.execution_times.items():
                    stats[func_name] = self._calculate_stats(func_name, times)
                return stats
    
    def _calculate_stats(self, function_name: str, times: List[float]) -> Dict[str, Any]:
        """統計計算"""
        if not times:
            return {}
        
        total_time = sum(times)
        avg_time = total_time / len(times)
        min_time = min(times)
        max_time = max(times)
        
        # パーセンタイル計算
        sorted_times = sorted(times)
        p50_idx = len(sorted_times) // 2
        p90_idx = int(len(sorted_times) * 0.9)
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)
        
        return {
            'function_name': function_name,
            'call_count': len(times),
            'total_time_ms': total_time * 1000,
            'avg_time_ms': avg_time * 1000,
            'min_time_ms': min_time * 1000,
            'max_time_ms': max_time * 1000,
            'p50_time_ms': sorted_times[p50_idx] * 1000,
            'p90_time_ms': sorted_times[p90_idx] * 1000,
            'p95_time_ms': sorted_times[p95_idx] * 1000,
            'p99_time_ms': sorted_times[p99_idx] * 1000
        }
    
    def get_top_functions(self, limit: int = 10, sort_by: str = 'total_time') -> List[Dict[str, Any]]:
        """トップ関数取得"""
        all_stats = self.get_stats()
        
        # ソート
        if sort_by == 'total_time':
            sorted_stats = sorted(
                all_stats.items(),
                key=lambda x: x[1].get('total_time_ms', 0),
                reverse=True
            )
        elif sort_by == 'avg_time':
            sorted_stats = sorted(
                all_stats.items(),
                key=lambda x: x[1].get('avg_time_ms', 0),
                reverse=True
            )
        elif sort_by == 'call_count':
            sorted_stats = sorted(
                all_stats.items(),
                key=lambda x: x[1].get('call_count', 0),
                reverse=True
            )
        else:
            sorted_stats = list(all_stats.items())
        
        return [stats for _, stats in sorted_stats[:limit]]
    
    def clear_stats(self):
        """統計クリア"""
        with self.lock:
            self.execution_times.clear()
            self.call_counts.clear()
            self.logger.info("関数プロファイル統計クリア")


class CodeProfiler:
    """コードレベルプロファイラー"""
    
    def __init__(self):
        self.profiler = None
        self.profiling_active = False
        self.profile_data = None
        
        self.logger = get_logger(__name__)
    
    def start_profiling(self):
        """プロファイリング開始"""
        if self.profiling_active:
            self.logger.warning("プロファイリングは既に開始されています")
            return
        
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        self.profiling_active = True
        
        self.logger.info("コードプロファイリング開始")
    
    def stop_profiling(self):
        """プロファイリング停止"""
        if not self.profiling_active:
            self.logger.warning("プロファイリングが開始されていません")
            return
        
        self.profiler.disable()
        self.profiling_active = False
        
        # プロファイルデータ処理
        self._process_profile_data()
        
        self.logger.info("コードプロファイリング停止")
    
    def _process_profile_data(self):
        """プロファイルデータ処理"""
        if not self.profiler:
            return
        
        # StringIOにプロファイル結果出力
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats()
        
        self.profile_data = s.getvalue()
        s.close()
    
    def get_profile_results(self, limit: int = 50) -> List[ProfileResult]:
        """プロファイル結果取得"""
        if not self.profiler:
            return []
        
        ps = pstats.Stats(self.profiler)
        ps.sort_stats('cumulative')
        
        results = []
        total_time = ps.total_tt
        
        for (filename, line_number, function_name), (call_count, _, total_time_func, cumulative_time) in ps.stats.items():
            if len(results) >= limit:
                break
            
            avg_time = total_time_func / call_count if call_count > 0 else 0
            percentage = (cumulative_time / total_time * 100) if total_time > 0 else 0
            
            result = ProfileResult(
                function_name=function_name,
                filename=filename,
                line_number=line_number,
                call_count=call_count,
                total_time=total_time_func,
                cumulative_time=cumulative_time,
                avg_time=avg_time,
                percentage=percentage
            )
            
            results.append(result)
        
        return results
    
    def get_hotspots(self, threshold_ms: float = 10.0) -> List[ProfileResult]:
        """ホットスポット取得"""
        results = self.get_profile_results()
        
        # 閾値以上の関数をフィルタ
        hotspots = [
            result for result in results
            if result.total_time * 1000 >= threshold_ms
        ]
        
        return sorted(hotspots, key=lambda x: x.cumulative_time, reverse=True)
    
    def profile_code_block(self, code_block: Callable):
        """コードブロックプロファイリング"""
        self.start_profiling()
        try:
            result = code_block()
            return result
        finally:
            self.stop_profiling()
    
    def get_profile_summary(self) -> Dict[str, Any]:
        """プロファイル概要取得"""
        if not self.profiler:
            return {}
        
        ps = pstats.Stats(self.profiler)
        
        return {
            'total_calls': ps.total_calls,
            'primitive_calls': ps.prim_calls,
            'total_time': ps.total_tt,
            'profiling_active': self.profiling_active,
            'top_functions_count': len(ps.stats)
        }


class BottleneckAnalyzer:
    """ボトルネック分析"""
    
    def __init__(self, function_profiler: FunctionProfiler, code_profiler: CodeProfiler):
        self.function_profiler = function_profiler
        self.code_profiler = code_profiler
        self.logger = get_logger(__name__)
    
    def analyze_bottlenecks(self, min_total_time_ms: float = 100.0) -> List[BottleneckInfo]:
        """ボトルネック分析"""
        bottlenecks = []
        
        # 関数レベル分析
        function_stats = self.function_profiler.get_stats()
        
        for func_name, stats in function_stats.items():
            total_time_ms = stats.get('total_time_ms', 0)
            
            if total_time_ms < min_total_time_ms:
                continue
            
            call_count = stats.get('call_count', 0)
            avg_time_ms = stats.get('avg_time_ms', 0)
            
            # 影響度スコア計算
            impact_score = self._calculate_impact_score(
                total_time_ms, call_count, avg_time_ms
            )
            
            # 推奨事項生成
            recommendations = self._generate_recommendations(stats)
            
            bottleneck = BottleneckInfo(
                function_name=func_name,
                total_time=total_time_ms,
                call_count=call_count,
                avg_time=avg_time_ms,
                impact_score=impact_score,
                recommendations=recommendations
            )
            
            bottlenecks.append(bottleneck)
        
        # 影響度順でソート
        return sorted(bottlenecks, key=lambda x: x.impact_score, reverse=True)
    
    def _calculate_impact_score(self, total_time_ms: float, call_count: int, avg_time_ms: float) -> float:
        """影響度スコア計算"""
        # 複数要素を考慮したスコア計算
        time_score = min(total_time_ms / 1000, 100)  # 総実行時間（秒）
        frequency_score = min(call_count / 100, 10)   # 呼び出し頻度
        avg_time_score = min(avg_time_ms / 100, 10)   # 平均実行時間
        
        # 重み付き平均
        impact_score = (
            time_score * 0.5 +        # 総時間を重視
            frequency_score * 0.3 +   # 頻度も重要
            avg_time_score * 0.2      # 平均時間
        )
        
        return impact_score
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """推奨事項生成"""
        recommendations = []
        
        call_count = stats.get('call_count', 0)
        avg_time_ms = stats.get('avg_time_ms', 0)
        total_time_ms = stats.get('total_time_ms', 0)
        
        # 高頻度呼び出し
        if call_count > 1000:
            recommendations.append("呼び出し頻度が高い - キャッシュやメモ化を検討")
        
        # 平均実行時間が長い
        if avg_time_ms > 50:
            recommendations.append("平均実行時間が長い - アルゴリズム最適化を検討")
        
        # 総実行時間が長い
        if total_time_ms > 5000:  # 5秒
            recommendations.append("総実行時間が長い - 並列処理や非同期化を検討")
        
        # バラツキが大きい場合
        p99_time = stats.get('p99_time_ms', 0)
        p50_time = stats.get('p50_time_ms', 0)
        
        if p99_time > p50_time * 3:  # P99がP50の3倍以上
            recommendations.append("実行時間のバラツキが大きい - 入力データや処理分岐を確認")
        
        if not recommendations:
            recommendations.append("パフォーマンス改善の余地があります")
        
        return recommendations
    
    def get_performance_report(self) -> Dict[str, Any]:
        """パフォーマンスレポート取得"""
        bottlenecks = self.analyze_bottlenecks()
        top_functions = self.function_profiler.get_top_functions(limit=10)
        
        # コードプロファイル情報
        code_summary = self.code_profiler.get_profile_summary()
        
        return {
            'analysis_timestamp': datetime.now().isoformat(),
            'bottlenecks': [b.to_dict() for b in bottlenecks[:10]],
            'top_functions_by_total_time': top_functions,
            'code_profile_summary': code_summary,
            'total_bottlenecks': len(bottlenecks),
            'high_impact_bottlenecks': len([b for b in bottlenecks if b.impact_score > 10])
        }


class PerformanceProfiler:
    """メインパフォーマンスプロファイラー"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger(__name__)
        
        # プロファイラーコンポーネント
        self.function_profiler = FunctionProfiler()
        self.code_profiler = CodeProfiler()
        self.bottleneck_analyzer = BottleneckAnalyzer(
            self.function_profiler, 
            self.code_profiler
        )
        
        # 設定
        self.auto_profiling_enabled = self.config_manager.get(
            "profiling.auto_enabled", True
        )
        self.profiling_threshold_ms = self.config_manager.get(
            "profiling.threshold_ms", 10.0
        )
        
        # プロファイリング履歴
        self.profiling_sessions = deque(maxlen=100)
        
        # 統計
        self.session_count = 0
        self.total_profiled_functions = 0
    
    def enable_function_profiling(self):
        """関数プロファイリング有効化"""
        self.function_profiler.enabled = True
        self.logger.info("関数プロファイリング有効化")
    
    def disable_function_profiling(self):
        """関数プロファイリング無効化"""
        self.function_profiler.enabled = False
        self.logger.info("関数プロファイリング無効化")
    
    def profile_function(self, func_name: str = None):
        """関数プロファイリングデコレータ"""
        return self.function_profiler.profile_function(func_name)
    
    def start_code_profiling(self):
        """コードプロファイリング開始"""
        self.code_profiler.start_profiling()
        self.session_count += 1
    
    def stop_code_profiling(self) -> Dict[str, Any]:
        """コードプロファイリング停止"""
        self.code_profiler.stop_profiling()
        
        # セッション情報記録
        session_info = {
            'session_id': self.session_count,
            'timestamp': datetime.now().isoformat(),
            'summary': self.code_profiler.get_profile_summary()
        }
        
        self.profiling_sessions.append(session_info)
        
        return session_info
    
    def profile_code_execution(self, func: Callable, *args, **kwargs):
        """コード実行プロファイリング"""
        self.start_code_profiling()
        try:
            with ExecutionTimer("code_execution") as timer:
                result = func(*args, **kwargs)
            
            execution_time = timer.get_elapsed_ms()
            self.logger.info(f"コード実行完了: {execution_time:.2f}ms")
            
            return result
        finally:
            self.stop_code_profiling()
    
    def analyze_performance(self, min_impact_score: float = 5.0) -> Dict[str, Any]:
        """パフォーマンス分析"""
        try:
            # ボトルネック分析
            bottlenecks = self.bottleneck_analyzer.analyze_bottlenecks()
            
            # 高影響ボトルネック抽出
            high_impact_bottlenecks = [
                b for b in bottlenecks 
                if b.impact_score >= min_impact_score
            ]
            
            # トップ関数取得
            top_functions = self.function_profiler.get_top_functions(limit=20)
            
            # 分析結果
            analysis_result = {
                'analysis_timestamp': datetime.now().isoformat(),
                'total_profiled_functions': len(self.function_profiler.execution_times),
                'total_bottlenecks': len(bottlenecks),
                'high_impact_bottlenecks': len(high_impact_bottlenecks),
                'bottlenecks': [b.to_dict() for b in high_impact_bottlenecks],
                'top_functions': top_functions,
                'performance_summary': self._generate_performance_summary(bottlenecks)
            }
            
            self.logger.info(
                f"パフォーマンス分析完了: {len(high_impact_bottlenecks)}個の高影響ボトルネック検出"
            )
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"パフォーマンス分析エラー: {str(e)}")
            return {'error': str(e)}
    
    def _generate_performance_summary(self, bottlenecks: List[BottleneckInfo]) -> Dict[str, Any]:
        """パフォーマンス概要生成"""
        if not bottlenecks:
            return {
                'status': 'excellent',
                'message': 'パフォーマンスボトルネックは検出されませんでした'
            }
        
        total_impact = sum(b.impact_score for b in bottlenecks)
        avg_impact = total_impact / len(bottlenecks)
        
        if avg_impact > 20:
            status = 'critical'
            message = '重大なパフォーマンス問題が検出されました'
        elif avg_impact > 10:
            status = 'warning'
            message = 'パフォーマンス改善が推奨されます'
        elif avg_impact > 5:
            status = 'info'
            message = '軽微なパフォーマンス最適化機会があります'
        else:
            status = 'good'
            message = 'パフォーマンスは良好です'
        
        return {
            'status': status,
            'message': message,
            'total_impact_score': total_impact,
            'average_impact_score': avg_impact,
            'bottleneck_count': len(bottlenecks)
        }
    
    def get_profiling_statistics(self) -> Dict[str, Any]:
        """プロファイリング統計取得"""
        function_stats = self.function_profiler.get_stats()
        
        return {
            'session_count': self.session_count,
            'profiled_functions': len(function_stats),
            'auto_profiling_enabled': self.auto_profiling_enabled,
            'threshold_ms': self.profiling_threshold_ms,
            'recent_sessions': list(self.profiling_sessions)[-5:],  # 最新5セッション
            'function_profiler_enabled': self.function_profiler.enabled,
            'code_profiler_active': self.code_profiler.profiling_active
        }
    
    def clear_profiling_data(self):
        """プロファイリングデータクリア"""
        self.function_profiler.clear_stats()
        self.profiling_sessions.clear()
        self.session_count = 0
        
        self.logger.info("プロファイリングデータクリア")
    
    def export_profile_data(self, format: str = "json") -> str:
        """プロファイルデータエクスポート"""
        analysis_result = self.analyze_performance()
        statistics = self.get_profiling_statistics()
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'performance_analysis': analysis_result,
            'profiling_statistics': statistics
        }
        
        if format == "json":
            import json
            return json.dumps(export_data, indent=2, default=str)
        else:
            return str(export_data)


# グローバルプロファイラーインスタンス
_global_performance_profiler: Optional[PerformanceProfiler] = None


def get_performance_profiler() -> PerformanceProfiler:
    """グローバルプロファイラーインスタンス取得"""
    global _global_performance_profiler
    if _global_performance_profiler is None:
        _global_performance_profiler = PerformanceProfiler()
    return _global_performance_profiler


# 便利デコレータ
def profile_performance(func_name: str = None):
    """パフォーマンスプロファイリングデコレータ"""
    profiler = get_performance_profiler()
    return profiler.profile_function(func_name)


def profile_execution_time(threshold_ms: float = 10.0):
    """実行時間プロファイリングデコレータ"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with ExecutionTimer(func.__name__) as timer:
                result = func(*args, **kwargs)
            
            if timer.get_elapsed_ms() >= threshold_ms:
                logger = get_logger(__name__)
                logger.warning(
                    f"長時間実行検出: {func.__name__} - {timer.get_elapsed_ms():.2f}ms"
                )
            
            return result
        return wrapper
    return decorator