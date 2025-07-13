"""
自己診断システムのユニットテスト

SystemDiagnostics, PerformanceMonitor, CodeQualityAnalyzer, LearningEffectivenessEvaluator
"""

import pytest
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.append('/home/choux1/src/github.com/0xchoux1/aide')

from src.self_improvement.diagnostics import (
    SystemDiagnostics,
    PerformanceMonitor, 
    CodeQualityAnalyzer,
    LearningEffectivenessEvaluator,
    DiagnosticResult,
    BaseDiagnosticModule
)


class TestDiagnosticResult:
    """DiagnosticResult テストクラス"""
    
    def test_diagnostic_result_creation(self):
        """DiagnosticResult の基本作成テスト"""
        result = DiagnosticResult(
            component="test_component",
            metric_name="test_metric", 
            value=75.5,
            target_value=80.0,
            status="warning"
        )
        
        assert result.component == "test_component"
        assert result.metric_name == "test_metric"
        assert result.value == 75.5
        assert result.target_value == 80.0
        assert result.status == "warning"
        assert isinstance(result.timestamp, datetime)
        assert result.recommendations == []
    
    def test_diagnostic_result_with_recommendations(self):
        """推奨事項付きDiagnosticResult テスト"""
        recommendations = ["改善1", "改善2"]
        result = DiagnosticResult(
            component="test",
            metric_name="metric",
            value=50,
            recommendations=recommendations
        )
        
        assert result.recommendations == recommendations
    
    def test_diagnostic_result_to_dict(self):
        """to_dict メソッドテスト"""
        result = DiagnosticResult(
            component="test",
            metric_name="metric",
            value=100,
            status="good"
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['component'] == "test"
        assert result_dict['metric_name'] == "metric"
        assert result_dict['value'] == 100
        assert result_dict['status'] == "good"
        assert 'timestamp' in result_dict


class TestBaseDiagnosticModule:
    """BaseDiagnosticModule テストクラス"""
    
    def test_base_module_initialization(self):
        """基底モジュール初期化テスト"""
        # Mock concrete implementation
        class MockDiagnosticModule(BaseDiagnosticModule):
            def diagnose(self):
                return []
        
        module = MockDiagnosticModule("test_module")
        
        assert module.name == "test_module"
        assert module.last_run is None
        assert module.history == []
    
    def test_get_latest_results(self):
        """最新結果取得テスト"""
        class MockDiagnosticModule(BaseDiagnosticModule):
            def diagnose(self):
                return []
        
        module = MockDiagnosticModule("test")
        
        # 履歴追加
        for i in range(15):
            result = DiagnosticResult("component", f"metric_{i}", i)
            module.history.append(result)
        
        latest = module.get_latest_results()
        
        # 最新10件のみ取得
        assert len(latest) == 10
        assert latest[0].value == 5  # 最古（インデックス5）
        assert latest[-1].value == 14  # 最新（インデックス14）
    
    def test_get_trend_analysis_insufficient_data(self):
        """トレンド分析 - データ不足テスト"""
        class MockDiagnosticModule(BaseDiagnosticModule):
            def diagnose(self):
                return []
        
        module = MockDiagnosticModule("test")
        
        # データ1件のみ
        result = DiagnosticResult("component", "metric", 100)
        module.history.append(result)
        
        trend = module.get_trend_analysis("metric", days=7)
        
        assert trend["trend"] == "insufficient_data"
        assert trend["data_points"] == 1
    
    def test_get_trend_analysis_valid(self):
        """トレンド分析 - 有効データテスト"""
        class MockDiagnosticModule(BaseDiagnosticModule):
            def diagnose(self):
                return []
        
        module = MockDiagnosticModule("test")
        
        # 改善トレンドのデータ
        base_time = datetime.now() - timedelta(days=5)
        for i, value in enumerate([50, 55, 60, 70, 80, 85]):
            result = DiagnosticResult("component", "metric", value)
            result.timestamp = base_time + timedelta(days=i)
            module.history.append(result)
        
        trend = module.get_trend_analysis("metric", days=7)
        
        assert trend["trend"] == "improving"
        assert trend["data_points"] == 6
        assert trend["first_period_avg"] < trend["second_period_avg"]


class TestPerformanceMonitor:
    """PerformanceMonitor テストクラス"""
    
    def test_performance_monitor_initialization(self):
        """PerformanceMonitor 初期化テスト"""
        monitor = PerformanceMonitor()
        
        assert monitor.name == "performance_monitor"
        assert monitor.rag_system is None
        assert monitor.response_times == []
        assert monitor.memory_snapshots == []
    
    def test_performance_monitor_with_rag_system(self):
        """RAGシステム付きPerformanceMonitor テスト"""
        mock_rag_system = Mock()
        monitor = PerformanceMonitor(mock_rag_system)
        
        assert monitor.rag_system == mock_rag_system
    
    @patch('src.self_improvement.diagnostics.PSUTIL_AVAILABLE', False)
    def test_diagnose_without_psutil(self):
        """psutil なしでの診断テスト"""
        monitor = PerformanceMonitor()
        
        results = monitor.diagnose()
        
        # psutil利用不可の結果が含まれているはず
        psutil_results = [r for r in results if "resource_monitoring_status" in r.metric_name]
        assert len(psutil_results) == 1
        assert psutil_results[0].value == "psutil_unavailable"
        assert psutil_results[0].status == "warning"
    
    @patch('src.self_improvement.diagnostics.PSUTIL_AVAILABLE', True)
    @patch('src.self_improvement.diagnostics.psutil')
    def test_diagnose_with_psutil_success(self, mock_psutil):
        """psutil ありでの正常診断テスト"""
        # Mock psutil functions
        mock_psutil.virtual_memory.return_value.percent = 60.0
        mock_psutil.cpu_percent.return_value = 45.0
        mock_psutil.disk_usage.return_value.percent = 70.0
        
        monitor = PerformanceMonitor()
        results = monitor.diagnose()
        
        # システムリソース結果が含まれているはず
        memory_results = [r for r in results if "memory_usage_percent" in r.metric_name]
        cpu_results = [r for r in results if "cpu_usage_percent" in r.metric_name]
        disk_results = [r for r in results if "disk_usage_percent" in r.metric_name]
        
        assert len(memory_results) == 1
        assert len(cpu_results) == 1
        assert len(disk_results) == 1
        
        # 良好なステータス
        assert memory_results[0].status == "good"
        assert cpu_results[0].status == "good"
        assert disk_results[0].status == "good"
    
    def test_diagnose_with_rag_system(self):
        """RAGシステム付き診断テスト"""
        mock_rag_system = Mock()
        mock_rag_system.get_system_stats.return_value = {
            'generation_stats': {
                'total_requests': 100,
                'successful_generations': 95,
                'llm_requests': 50,
                'llm_errors': 2
            },
            'llm_integration': {
                'claude_code_enabled': True,
                'llm_backend': 'claude-code'
            }
        }
        
        monitor = PerformanceMonitor(mock_rag_system)
        results = monitor.diagnose()
        
        # RAG関連結果が含まれているはず
        rag_results = [r for r in results if r.component == "rag_system"]
        assert len(rag_results) >= 2  # 成功率、LLM統合状況等
        
        # 成功率確認
        success_rate_results = [r for r in rag_results if "response_success_rate" in r.metric_name]
        assert len(success_rate_results) == 1
        assert success_rate_results[0].value == 95.0
    
    def test_measure_response_time_success(self):
        """応答時間測定 - 成功テスト"""
        monitor = PerformanceMonitor()
        
        def mock_operation(x, y):
            return x + y
        
        result, execution_time = monitor.measure_response_time(
            "addition", mock_operation, 2, 3
        )
        
        assert result == 5
        assert execution_time > 0
        assert len(monitor.response_times) == 1
        assert len(monitor.history) == 1
        
        # 履歴確認
        history_result = monitor.history[0]
        assert "response_time_addition" in history_result.metric_name
        assert history_result.value == execution_time
    
    def test_measure_response_time_error(self):
        """応答時間測定 - エラーテスト"""
        monitor = PerformanceMonitor()
        
        def failing_operation():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            monitor.measure_response_time("failing_op", failing_operation)
        
        # エラー履歴が記録されているはず
        assert len(monitor.history) == 1
        error_result = monitor.history[0]
        assert "response_time_failing_op_error" in error_result.metric_name
        assert error_result.status == "critical"


class TestCodeQualityAnalyzer:
    """CodeQualityAnalyzer テストクラス"""
    
    def test_code_quality_analyzer_initialization(self):
        """CodeQualityAnalyzer 初期化テスト"""
        analyzer = CodeQualityAnalyzer()
        
        assert analyzer.name == "code_quality_analyzer"
        assert "aide" in str(analyzer.project_root)
        assert analyzer.src_path.name == "src"
    
    def test_code_quality_analyzer_custom_path(self):
        """カスタムパス指定テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = CodeQualityAnalyzer(temp_dir)
            
            assert str(analyzer.project_root) == temp_dir
            assert analyzer.src_path == Path(temp_dir) / "src"
    
    def test_diagnose_missing_src_directory(self):
        """srcディレクトリなしでの診断テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = CodeQualityAnalyzer(temp_dir)
            
            results = analyzer.diagnose()
            
            # srcディレクトリ不足エラーが含まれているはず
            missing_results = [r for r in results if "src_directory_missing" in r.metric_name]
            assert len(missing_results) == 1
            assert missing_results[0].value == "missing"
            assert missing_results[0].status == "critical"
    
    def test_diagnose_with_python_files(self):
        """Pythonファイルありでの診断テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # srcディレクトリとPythonファイルを作成
            src_dir = Path(temp_dir) / "src"
            src_dir.mkdir()
            
            # サンプルPythonファイル
            (src_dir / "test_file.py").write_text('''
def simple_function(x):
    """Simple function."""
    return x * 2

class TestClass:
    """Test class."""
    
    def method(self):
        if True:
            return "hello"
        else:
            return "world"
''')
            
            analyzer = CodeQualityAnalyzer(temp_dir)
            results = analyzer.diagnose()
            
            # メトリクス結果確認
            metrics = {r.metric_name: r for r in results}
            
            assert "total_python_files" in metrics
            assert metrics["total_python_files"].value == 1
            assert metrics["total_python_files"].status == "good"
            
            assert "total_functions" in metrics
            assert metrics["total_functions"].value >= 1
            
            assert "total_classes" in metrics
            assert metrics["total_classes"].value >= 1
    
    def test_calculate_complexity(self):
        """複雑度計算テスト"""
        analyzer = CodeQualityAnalyzer()
        
        # 複雑な関数のAST
        complex_code = '''
def complex_function(x, y):
    if x > 0:
        for i in range(10):
            if i % 2 == 0:
                while y > 0:
                    try:
                        y -= 1
                    except ValueError:
                        pass
                    except TypeError:
                        break
    return x + y
'''
        
        import ast
        tree = ast.parse(complex_code)
        func_node = tree.body[0]
        
        complexity = analyzer._calculate_complexity(func_node)
        
        # 複数の分岐・ループがあるので複雑度は高いはず
        assert complexity >= 5


class TestLearningEffectivenessEvaluator:
    """LearningEffectivenessEvaluator テストクラス"""
    
    def test_learning_evaluator_initialization(self):
        """LearningEffectivenessEvaluator 初期化テスト"""
        evaluator = LearningEffectivenessEvaluator()
        
        assert evaluator.name == "learning_effectiveness_evaluator"
        assert evaluator.rag_system is None
    
    def test_diagnose_without_rag_system(self):
        """RAGシステムなしでの診断テスト"""
        evaluator = LearningEffectivenessEvaluator()
        
        results = evaluator.diagnose()
        
        # RAGシステム利用不可の結果
        assert len(results) == 1
        assert results[0].metric_name == "rag_system_unavailable"
        assert results[0].value == "not_configured"
        assert results[0].status == "warning"
    
    def test_diagnose_with_rag_system(self):
        """RAGシステムありでの診断テスト"""
        mock_rag_system = Mock()
        mock_rag_system.get_system_stats.return_value = {
            'knowledge_base_stats': {
                'total_items': 150,
                'average_quality_score': 0.85
            },
            'context_usage_rate': 0.92,
            'llm_integration': {
                'claude_code_enabled': True,
                'llm_stats': {
                    'success_rate': 0.97
                }
            }
        }
        
        evaluator = LearningEffectivenessEvaluator(mock_rag_system)
        results = evaluator.diagnose()
        
        # 学習効果メトリクス確認
        metrics = {r.metric_name: r for r in results}
        
        assert "knowledge_base_size" in metrics
        assert metrics["knowledge_base_size"].value == 150
        assert metrics["knowledge_base_size"].status == "good"
        
        assert "average_learning_quality" in metrics
        assert metrics["average_learning_quality"].value == 0.85
        assert metrics["average_learning_quality"].status == "good"
        
        assert "context_usage_rate" in metrics
        assert metrics["context_usage_rate"].value == 0.92
        assert metrics["context_usage_rate"].status == "good"
        
        assert "llm_success_rate" in metrics
        assert metrics["llm_success_rate"].value == 0.97
        assert metrics["llm_success_rate"].status == "good"


class TestSystemDiagnostics:
    """SystemDiagnostics テストクラス"""
    
    def test_system_diagnostics_initialization(self):
        """SystemDiagnostics 初期化テスト"""
        diagnostics = SystemDiagnostics()
        
        assert 'performance' in diagnostics.modules
        assert 'code_quality' in diagnostics.modules
        assert 'learning' in diagnostics.modules
        assert diagnostics.last_full_diagnosis is None
    
    def test_system_diagnostics_with_rag_system(self):
        """RAGシステム付きSystemDiagnostics テスト"""
        mock_rag_system = Mock()
        diagnostics = SystemDiagnostics(mock_rag_system)
        
        # RAGシステムが各モジュールに渡されているはず
        assert diagnostics.modules['performance'].rag_system == mock_rag_system
        assert diagnostics.modules['learning'].rag_system == mock_rag_system
    
    def test_run_full_diagnosis(self):
        """全診断実行テスト"""
        diagnostics = SystemDiagnostics()
        
        # モジュールをモックに置換
        mock_performance = Mock()
        mock_performance.diagnose.return_value = [
            DiagnosticResult("performance", "test_metric", 80, status="good")
        ]
        
        mock_code_quality = Mock()
        mock_code_quality.diagnose.return_value = [
            DiagnosticResult("code_quality", "test_metric", 75, status="warning")
        ]
        
        mock_learning = Mock()
        mock_learning.diagnose.return_value = [
            DiagnosticResult("learning", "test_metric", 90, status="good")
        ]
        
        diagnostics.modules = {
            'performance': mock_performance,
            'code_quality': mock_code_quality,
            'learning': mock_learning
        }
        
        results = diagnostics.run_full_diagnosis()
        
        # 全モジュールの結果が含まれているはず
        assert 'performance' in results
        assert 'code_quality' in results
        assert 'learning' in results
        
        assert len(results['performance']) == 1
        assert len(results['code_quality']) == 1
        assert len(results['learning']) == 1
        
        # 診断実行時刻が記録されているはず
        assert diagnostics.last_full_diagnosis is not None
    
    def test_run_full_diagnosis_with_module_error(self):
        """モジュールエラーありでの全診断テスト"""
        diagnostics = SystemDiagnostics()
        
        # エラーを起こすモジュール
        mock_failing_module = Mock()
        mock_failing_module.diagnose.side_effect = Exception("Test error")
        
        diagnostics.modules = {
            'failing_module': mock_failing_module
        }
        
        results = diagnostics.run_full_diagnosis()
        
        # エラー結果が含まれているはず
        assert 'failing_module' in results
        assert len(results['failing_module']) == 1
        assert results['failing_module'][0].metric_name == "module_error"
        assert results['failing_module'][0].status == "critical"
    
    def test_get_system_health_summary(self):
        """システムヘルス要約テスト"""
        diagnostics = SystemDiagnostics()
        
        # モックモジュールで固定結果を設定
        mock_module = Mock()
        mock_module.diagnose.return_value = [
            DiagnosticResult("test", "metric1", 100, status="good"),
            DiagnosticResult("test", "metric2", 70, status="warning"),
            DiagnosticResult("test", "metric3", 30, status="critical")
        ]
        
        diagnostics.modules = {'test': mock_module}
        
        summary = diagnostics.get_system_health_summary()
        
        # ヘルス要約確認
        assert summary['total_metrics'] == 3
        assert summary['status_distribution']['good'] == 1
        assert summary['status_distribution']['warning'] == 1
        assert summary['status_distribution']['critical'] == 1
        
        # ヘルススコア計算確認
        expected_score = (100 + 60 + 0) / 3  # good=100, warning=60, critical=0
        assert abs(summary['health_score'] - expected_score) < 1
        
        # 全体ステータス確認
        assert summary['overall_status'] in ['excellent', 'good', 'warning', 'critical']
    
    def test_export_diagnosis_report(self):
        """診断レポート出力テスト"""
        diagnostics = SystemDiagnostics()
        
        # 簡単な診断実行
        with patch.object(diagnostics, 'get_system_health_summary') as mock_summary:
            mock_summary.return_value = {
                'overall_status': 'good',
                'health_score': 85.0,
                'total_metrics': 5
            }
            
            report_file = diagnostics.export_diagnosis_report()
            
            # ファイルが作成されているはず
            assert report_file.startswith('/tmp/aide_diagnosis_report_')
            assert report_file.endswith('.json')
            
            # ファイル内容確認
            with open(report_file, 'r') as f:
                report_data = json.load(f)
            
            assert report_data['overall_status'] == 'good'
            assert report_data['health_score'] == 85.0
            assert report_data['total_metrics'] == 5


if __name__ == "__main__":
    pytest.main([__file__])