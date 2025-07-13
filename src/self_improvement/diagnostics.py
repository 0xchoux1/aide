"""
システム診断モジュール

自己診断、パフォーマンス監視、コード品質分析、学習効果評価
"""

import time
import subprocess

# psutilをオプショナルインポート
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutilが利用できません。システムリソース監視機能が制限されます。")
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import os
import ast
import re
from pathlib import Path

from ..agents.base_agent import BaseAgent
from ..rag.rag_system import RAGSystem
from ..llm.claude_code_client import ClaudeCodeClient


@dataclass
class DiagnosticResult:
    """診断結果の標準化フォーマット"""
    component: str
    metric_name: str
    value: Any
    target_value: Optional[Any] = None
    status: str = "unknown"  # "good", "warning", "critical", "unknown"
    recommendations: List[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.recommendations is None:
            self.recommendations = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'component': self.component,
            'metric_name': self.metric_name,
            'value': self.value,
            'target_value': self.target_value,
            'status': self.status,
            'recommendations': self.recommendations,
            'timestamp': self.timestamp.isoformat()
        }


class BaseDiagnosticModule(ABC):
    """診断モジュールの基底クラス"""
    
    def __init__(self, name: str):
        self.name = name
        self.last_run = None
        self.history: List[DiagnosticResult] = []
    
    @abstractmethod
    def diagnose(self) -> List[DiagnosticResult]:
        """診断を実行して結果を返す"""
        pass
    
    def get_latest_results(self) -> List[DiagnosticResult]:
        """最新の診断結果を取得"""
        return self.history[-10:] if self.history else []
    
    def get_trend_analysis(self, metric_name: str, days: int = 7) -> Dict[str, Any]:
        """トレンド分析を実行"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_results = [
            r for r in self.history 
            if r.metric_name == metric_name and r.timestamp >= cutoff_date
        ]
        
        if len(recent_results) < 2:
            return {"trend": "insufficient_data", "data_points": len(recent_results)}
        
        values = [r.value for r in recent_results if isinstance(r.value, (int, float))]
        if len(values) < 2:
            return {"trend": "non_numeric_data", "data_points": len(values)}
        
        # 単純な線形トレンド分析
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        trend_direction = "improving" if second_avg > first_avg else "declining"
        trend_magnitude = abs(second_avg - first_avg) / first_avg if first_avg != 0 else 0
        
        return {
            "trend": trend_direction,
            "magnitude": trend_magnitude,
            "first_period_avg": first_avg,
            "second_period_avg": second_avg,
            "data_points": len(values)
        }


class PerformanceMonitor(BaseDiagnosticModule):
    """パフォーマンス監視システム"""
    
    def __init__(self, rag_system: Optional[RAGSystem] = None):
        super().__init__("performance_monitor")
        self.rag_system = rag_system
        self.response_times: List[float] = []
        self.memory_snapshots: List[float] = []
        
    def diagnose(self) -> List[DiagnosticResult]:
        """パフォーマンス診断を実行"""
        results = []
        
        # システムリソース監視
        if PSUTIL_AVAILABLE:
            try:
                # メモリ使用量
                memory_percent = psutil.virtual_memory().percent
                results.append(DiagnosticResult(
                    component="system",
                    metric_name="memory_usage_percent",
                    value=memory_percent,
                    target_value=80.0,
                    status="good" if memory_percent < 80 else "warning" if memory_percent < 90 else "critical",
                    recommendations=["メモリ使用量を最適化する"] if memory_percent > 80 else []
                ))
                
                # CPU使用量
                cpu_percent = psutil.cpu_percent(interval=1)
                results.append(DiagnosticResult(
                    component="system",
                    metric_name="cpu_usage_percent", 
                    value=cpu_percent,
                    target_value=70.0,
                    status="good" if cpu_percent < 70 else "warning" if cpu_percent < 90 else "critical",
                    recommendations=["CPU集約的な処理を最適化する"] if cpu_percent > 70 else []
                ))
                
                # ディスク使用量
                disk_usage = psutil.disk_usage('/').percent
                results.append(DiagnosticResult(
                    component="system",
                    metric_name="disk_usage_percent",
                    value=disk_usage,
                    target_value=85.0,
                    status="good" if disk_usage < 85 else "warning" if disk_usage < 95 else "critical",
                    recommendations=["ディスク容量を拡張する", "不要ファイルを削除する"] if disk_usage > 85 else []
                ))
                
            except Exception as e:
                results.append(DiagnosticResult(
                    component="system",
                    metric_name="resource_monitoring_error",
                    value=str(e),
                    status="critical",
                    recommendations=["システムリソース監視機能を修復する"]
                ))
        else:
            # psutil利用不可時のフォールバック
            results.append(DiagnosticResult(
                component="system",
                metric_name="resource_monitoring_status",
                value="psutil_unavailable",
                status="warning",
                recommendations=["psutilをインストールしてシステムリソース監視を有効化する"]
            ))
        
        # RAGシステムパフォーマンス
        if self.rag_system:
            try:
                rag_stats = self.rag_system.get_system_stats()
                
                # 応答成功率
                total_requests = rag_stats.get('generation_stats', {}).get('total_requests', 0)
                successful_generations = rag_stats.get('generation_stats', {}).get('successful_generations', 0)
                
                success_rate = (successful_generations / total_requests * 100) if total_requests > 0 else 0
                results.append(DiagnosticResult(
                    component="rag_system",
                    metric_name="response_success_rate",
                    value=success_rate,
                    target_value=95.0,
                    status="good" if success_rate >= 95 else "warning" if success_rate >= 85 else "critical",
                    recommendations=["エラーハンドリングを改善する"] if success_rate < 95 else []
                ))
                
                # LLM統合状況
                llm_integration = rag_stats.get('llm_integration', {})
                claude_enabled = llm_integration.get('claude_code_enabled', False)
                results.append(DiagnosticResult(
                    component="rag_system",
                    metric_name="llm_integration_status",
                    value="enabled" if claude_enabled else "disabled",
                    target_value="enabled",
                    status="good" if claude_enabled else "warning",
                    recommendations=["Claude Code統合を有効化する"] if not claude_enabled else []
                ))
                
                # LLMエラー率
                llm_requests = rag_stats.get('generation_stats', {}).get('llm_requests', 0)
                llm_errors = rag_stats.get('generation_stats', {}).get('llm_errors', 0)
                
                if llm_requests > 0:
                    llm_error_rate = (llm_errors / llm_requests * 100)
                    results.append(DiagnosticResult(
                        component="rag_system",
                        metric_name="llm_error_rate",
                        value=llm_error_rate,
                        target_value=5.0,
                        status="good" if llm_error_rate <= 5 else "warning" if llm_error_rate <= 15 else "critical",
                        recommendations=["LLMエラーハンドリングを改善する", "タイムアウト設定を調整する"] if llm_error_rate > 5 else []
                    ))
                
            except Exception as e:
                results.append(DiagnosticResult(
                    component="rag_system",
                    metric_name="rag_monitoring_error",
                    value=str(e),
                    status="critical",
                    recommendations=["RAGシステム監視機能を修復する"]
                ))
        
        # 結果を履歴に追加
        self.history.extend(results)
        self.last_run = datetime.now()
        
        return results
    
    def measure_response_time(self, operation_name: str, operation_func, *args, **kwargs):
        """操作の応答時間を測定"""
        start_time = time.time()
        try:
            result = operation_func(*args, **kwargs)
            execution_time = time.time() - start_time
            self.response_times.append(execution_time)
            
            # 応答時間の診断結果を追加
            diagnostic_result = DiagnosticResult(
                component="performance",
                metric_name=f"response_time_{operation_name}",
                value=execution_time,
                target_value=1.0,  # 1秒以内
                status="good" if execution_time < 1.0 else "warning" if execution_time < 3.0 else "critical",
                recommendations=["応答時間を最適化する"] if execution_time > 1.0 else []
            )
            self.history.append(diagnostic_result)
            
            return result, execution_time
        except Exception as e:
            execution_time = time.time() - start_time
            diagnostic_result = DiagnosticResult(
                component="performance",
                metric_name=f"response_time_{operation_name}_error",
                value=execution_time,
                status="critical",
                recommendations=["操作エラーを修復する", f"エラー: {str(e)}"]
            )
            self.history.append(diagnostic_result)
            raise


class CodeQualityAnalyzer(BaseDiagnosticModule):
    """コード品質分析システム"""
    
    def __init__(self, project_root: str = "/home/choux1/src/github.com/0xchoux1/aide"):
        super().__init__("code_quality_analyzer")
        self.project_root = Path(project_root)
        self.src_path = self.project_root / "src"
    
    def diagnose(self) -> List[DiagnosticResult]:
        """コード品質診断を実行"""
        results = []
        
        # コードメトリクス収集
        try:
            metrics = self._collect_code_metrics()
            
            for metric_name, metric_data in metrics.items():
                results.append(DiagnosticResult(
                    component="code_quality",
                    metric_name=metric_name,
                    value=metric_data["value"],
                    target_value=metric_data.get("target"),
                    status=metric_data["status"],
                    recommendations=metric_data.get("recommendations", [])
                ))
                
        except Exception as e:
            results.append(DiagnosticResult(
                component="code_quality",
                metric_name="analysis_error",
                value=str(e),
                status="critical",
                recommendations=["コード分析機能を修復する"]
            ))
        
        # 結果を履歴に追加
        self.history.extend(results)
        self.last_run = datetime.now()
        
        return results
    
    def _collect_code_metrics(self) -> Dict[str, Dict[str, Any]]:
        """コードメトリクスを収集"""
        metrics = {}
        
        if not self.src_path.exists():
            return {"src_directory_missing": {
                "value": "missing",
                "status": "critical",
                "recommendations": ["srcディレクトリを作成する"]
            }}
        
        # ファイル数と行数
        py_files = list(self.src_path.rglob("*.py"))
        total_files = len(py_files)
        total_lines = 0
        total_functions = 0
        total_classes = 0
        complex_functions = 0
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = len(content.splitlines())
                    total_lines += lines
                    
                    # AST解析
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            total_functions += 1
                            # 単純な複雑度計算（分岐文の数）
                            complexity = self._calculate_complexity(node)
                            if complexity > 10:
                                complex_functions += 1
                        elif isinstance(node, ast.ClassDef):
                            total_classes += 1
                            
            except Exception as e:
                # ファイル解析エラーは警告として記録
                pass
        
        # ファイル数メトリクス
        metrics["total_python_files"] = {
            "value": total_files,
            "status": "good" if total_files > 0 else "warning",
            "recommendations": ["Pythonファイルを追加する"] if total_files == 0 else []
        }
        
        # 行数メトリクス
        avg_lines_per_file = total_lines / total_files if total_files > 0 else 0
        metrics["average_lines_per_file"] = {
            "value": avg_lines_per_file,
            "target": 200,
            "status": "good" if avg_lines_per_file < 300 else "warning",
            "recommendations": ["大きなファイルを分割する"] if avg_lines_per_file > 300 else []
        }
        
        # 関数数メトリクス
        metrics["total_functions"] = {
            "value": total_functions,
            "status": "good" if total_functions > 0 else "warning",
            "recommendations": ["関数を追加する"] if total_functions == 0 else []
        }
        
        # クラス数メトリクス  
        metrics["total_classes"] = {
            "value": total_classes,
            "status": "good" if total_classes > 0 else "warning",
            "recommendations": ["クラスを追加する"] if total_classes == 0 else []
        }
        
        # 複雑な関数の比率
        complex_ratio = (complex_functions / total_functions * 100) if total_functions > 0 else 0
        metrics["complex_functions_ratio"] = {
            "value": complex_ratio,
            "target": 10.0,
            "status": "good" if complex_ratio < 10 else "warning" if complex_ratio < 20 else "critical",
            "recommendations": ["複雑な関数をリファクタリングする"] if complex_ratio > 10 else []
        }
        
        # テストカバレッジ（概算）
        test_files = list(self.project_root.rglob("test_*.py"))
        test_ratio = (len(test_files) / total_files * 100) if total_files > 0 else 0
        metrics["test_file_ratio"] = {
            "value": test_ratio,
            "target": 50.0,
            "status": "good" if test_ratio >= 50 else "warning" if test_ratio >= 25 else "critical",
            "recommendations": ["テストファイルを追加する"] if test_ratio < 50 else []
        }
        
        return metrics
    
    def _calculate_complexity(self, func_node: ast.FunctionDef) -> int:
        """関数の循環複雑度を簡易計算"""
        complexity = 1  # 基本複雑度
        
        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.With)):
                complexity += 1
            elif isinstance(node, ast.Try):
                complexity += len(node.handlers)
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        
        return complexity


class LearningEffectivenessEvaluator(BaseDiagnosticModule):
    """学習効果評価システム"""
    
    def __init__(self, rag_system: Optional[RAGSystem] = None):
        super().__init__("learning_effectiveness_evaluator")
        self.rag_system = rag_system
    
    def diagnose(self) -> List[DiagnosticResult]:
        """学習効果診断を実行"""
        results = []
        
        if not self.rag_system:
            results.append(DiagnosticResult(
                component="learning",
                metric_name="rag_system_unavailable",
                value="not_configured",
                status="warning",
                recommendations=["RAGシステムを設定する"]
            ))
            return results
        
        try:
            # RAGシステムから学習統計を取得
            rag_stats = self.rag_system.get_system_stats()
            
            # 知識ベース統計
            kb_stats = rag_stats.get('knowledge_base_stats', {})
            
            # 知識アイテム数
            total_items = kb_stats.get('total_items', 0)
            results.append(DiagnosticResult(
                component="learning",
                metric_name="knowledge_base_size",
                value=total_items,
                target_value=100,
                status="good" if total_items >= 100 else "warning" if total_items >= 10 else "critical",
                recommendations=["知識ベースを拡充する"] if total_items < 100 else []
            ))
            
            # 学習品質スコア
            avg_quality = kb_stats.get('average_quality_score', 0.0)
            results.append(DiagnosticResult(
                component="learning",
                metric_name="average_learning_quality",
                value=avg_quality,
                target_value=0.8,
                status="good" if avg_quality >= 0.8 else "warning" if avg_quality >= 0.6 else "critical",
                recommendations=["学習品質を向上させる"] if avg_quality < 0.8 else []
            ))
            
            # コンテキスト使用率
            context_usage_rate = rag_stats.get('context_usage_rate', 0.0)
            results.append(DiagnosticResult(
                component="learning",
                metric_name="context_usage_rate",
                value=context_usage_rate,
                target_value=0.9,
                status="good" if context_usage_rate >= 0.9 else "warning" if context_usage_rate >= 0.7 else "critical",
                recommendations=["コンテキスト活用を改善する"] if context_usage_rate < 0.9 else []
            ))
            
            # LLM統合効果
            llm_integration = rag_stats.get('llm_integration', {})
            if llm_integration.get('claude_code_enabled'):
                llm_stats = llm_integration.get('llm_stats', {})
                llm_success_rate = llm_stats.get('success_rate', 0.0)
                results.append(DiagnosticResult(
                    component="learning", 
                    metric_name="llm_success_rate",
                    value=llm_success_rate,
                    target_value=0.95,
                    status="good" if llm_success_rate >= 0.95 else "warning" if llm_success_rate >= 0.8 else "critical",
                    recommendations=["LLM統合を最適化する"] if llm_success_rate < 0.95 else []
                ))
            
        except Exception as e:
            results.append(DiagnosticResult(
                component="learning",
                metric_name="evaluation_error",
                value=str(e),
                status="critical",
                recommendations=["学習効果評価機能を修復する"]
            ))
        
        # 結果を履歴に追加
        self.history.extend(results)
        self.last_run = datetime.now()
        
        return results


class SystemDiagnostics:
    """統合システム診断クラス"""
    
    def __init__(self, rag_system: Optional[RAGSystem] = None):
        self.rag_system = rag_system
        self.modules = {
            'performance': PerformanceMonitor(rag_system),
            'code_quality': CodeQualityAnalyzer(),
            'learning': LearningEffectivenessEvaluator(rag_system)
        }
        self.last_full_diagnosis = None
    
    def run_full_diagnosis(self) -> Dict[str, List[DiagnosticResult]]:
        """全モジュールの診断を実行"""
        results = {}
        
        for module_name, module in self.modules.items():
            try:
                results[module_name] = module.diagnose()
            except Exception as e:
                results[module_name] = [DiagnosticResult(
                    component=module_name,
                    metric_name="module_error",
                    value=str(e),
                    status="critical",
                    recommendations=[f"{module_name}モジュールを修復する"]
                )]
        
        self.last_full_diagnosis = datetime.now()
        return results
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """システムヘルス要約を取得"""
        diagnosis = self.run_full_diagnosis()
        
        total_metrics = 0
        status_counts = {"good": 0, "warning": 0, "critical": 0, "unknown": 0}
        all_recommendations = []
        
        for module_results in diagnosis.values():
            for result in module_results:
                total_metrics += 1
                status_counts[result.status] += 1
                all_recommendations.extend(result.recommendations)
        
        # 全体的なヘルススコア計算
        if total_metrics == 0:
            health_score = 0
        else:
            health_score = (
                (status_counts["good"] * 100 + 
                 status_counts["warning"] * 60 + 
                 status_counts["critical"] * 0 + 
                 status_counts["unknown"] * 30) / total_metrics
            )
        
        # ヘルスステータス決定
        if health_score >= 90:
            overall_status = "excellent"
        elif health_score >= 75:
            overall_status = "good"
        elif health_score >= 50:
            overall_status = "warning"
        else:
            overall_status = "critical"
        
        return {
            "overall_status": overall_status,
            "health_score": health_score,
            "total_metrics": total_metrics,
            "status_distribution": status_counts,
            "top_recommendations": list(set(all_recommendations))[:5],
            "last_diagnosis": self.last_full_diagnosis.isoformat() if self.last_full_diagnosis else None,
            "detailed_results": diagnosis
        }
    
    def export_diagnosis_report(self, output_file: str = None) -> str:
        """診断レポートをファイルに出力"""
        if output_file is None:
            output_file = f"/tmp/aide_diagnosis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        summary = self.get_system_health_summary()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
        
        return output_file