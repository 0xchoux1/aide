"""
自律実装システムのユニットテスト

AutonomousImplementation, CodeGenerator, TestAutomation, DeploymentManager
"""

import pytest
import tempfile
import shutil
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime
from pathlib import Path

import sys
sys.path.append('/home/choux1/src/github.com/0xchoux1/aide')

from src.self_improvement.autonomous_implementation import (
    AutonomousImplementation,
    CodeGenerator,
    TestAutomation,
    DeploymentManager,
    ImplementationResult,
    SafetyCheck
)
from src.self_improvement.improvement_engine import ImprovementOpportunity, ImprovementType, Priority


class TestImplementationResult:
    """ImplementationResult テストクラス"""
    
    def test_implementation_result_creation(self):
        """ImplementationResult 基本作成テスト"""
        result = ImplementationResult(
            opportunity_id="test_opp_001",
            success=True
        )
        
        assert result.opportunity_id == "test_opp_001"
        assert result.success is True
        assert result.changes_made == []
        assert result.files_modified == []
        assert result.tests_generated == []
        assert result.error_message is None
        assert result.execution_time == 0.0
        assert result.rollback_info is None
        assert isinstance(result.timestamp, datetime)
    
    def test_implementation_result_with_data(self):
        """データ付きImplementationResult テスト"""
        result = ImplementationResult(
            opportunity_id="test_opp_002",
            success=False,
            changes_made=["変更1", "変更2"],
            files_modified=["file1.py", "file2.py"],
            tests_generated=["test_file1.py"],
            error_message="テストエラー",
            execution_time=15.5,
            rollback_info={"backup_path": "/tmp/backup"}
        )
        
        assert result.opportunity_id == "test_opp_002"
        assert result.success is False
        assert len(result.changes_made) == 2
        assert len(result.files_modified) == 2
        assert len(result.tests_generated) == 1
        assert result.error_message == "テストエラー"
        assert result.execution_time == 15.5
        assert result.rollback_info["backup_path"] == "/tmp/backup"
    
    def test_implementation_result_to_dict(self):
        """to_dict メソッドテスト"""
        result = ImplementationResult(
            opportunity_id="dict_test",
            success=True,
            changes_made=["変更テスト"],
            execution_time=5.0
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['opportunity_id'] == "dict_test"
        assert result_dict['success'] is True
        assert result_dict['changes_made'] == ["変更テスト"]
        assert result_dict['execution_time'] == 5.0
        assert 'timestamp' in result_dict


class TestSafetyCheck:
    """SafetyCheck テストクラス"""
    
    def test_safety_check_creation(self):
        """SafetyCheck 基本作成テスト"""
        check = SafetyCheck(
            check_name="test_check",
            passed=True,
            message="テストチェック成功"
        )
        
        assert check.check_name == "test_check"
        assert check.passed is True
        assert check.message == "テストチェック成功"
        assert check.severity == "info"
    
    def test_safety_check_with_severity(self):
        """重要度付きSafetyCheck テスト"""
        check = SafetyCheck(
            check_name="critical_check",
            passed=False,
            message="重要なチェック失敗",
            severity="error"
        )
        
        assert check.check_name == "critical_check"
        assert check.passed is False
        assert check.message == "重要なチェック失敗"
        assert check.severity == "error"
    
    def test_safety_check_to_dict(self):
        """to_dict メソッドテスト"""
        check = SafetyCheck(
            check_name="dict_test",
            passed=True,
            message="辞書テスト",
            severity="warning"
        )
        
        check_dict = check.to_dict()
        
        assert isinstance(check_dict, dict)
        assert check_dict['check_name'] == "dict_test"
        assert check_dict['passed'] is True
        assert check_dict['message'] == "辞書テスト"
        assert check_dict['severity'] == "warning"


class TestCodeGenerator:
    """CodeGenerator テストクラス"""
    
    def test_code_generator_initialization(self):
        """CodeGenerator 初期化テスト"""
        mock_claude_client = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = CodeGenerator(mock_claude_client, temp_dir)
            
            assert generator.claude_client == mock_claude_client
            assert str(generator.project_root) == temp_dir
            assert generator.file_tool is not None
    
    def test_analyze_current_code(self):
        """現在コード分析テスト"""
        mock_claude_client = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # テストファイル作成
            src_dir = Path(temp_dir) / "src"
            src_dir.mkdir()
            test_file = src_dir / "test_module.py"
            test_file.write_text("def test_function():\n    return 'test'")
            
            generator = CodeGenerator(mock_claude_client, temp_dir)
            
            # テスト改善機会
            opportunity = ImprovementOpportunity(
                id="test_opp",
                title="テスト改善",
                description="テスト説明",
                improvement_type=ImprovementType.PERFORMANCE
            )
            
            context = generator._analyze_current_code(opportunity)
            
            assert isinstance(context, dict)
            assert 'related_files' in context
            assert 'project_structure' in context
            assert 'src_modules' in context['project_structure']
    
    def test_identify_related_files(self):
        """関連ファイル特定テスト"""
        mock_claude_client = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # プロジェクト構造作成
            src_dir = Path(temp_dir) / "src"
            rag_dir = src_dir / "rag"
            rag_dir.mkdir(parents=True)
            
            (rag_dir / "rag_system.py").write_text("# RAG system")
            (rag_dir / "knowledge_base.py").write_text("# Knowledge base")
            
            generator = CodeGenerator(mock_claude_client, temp_dir)
            
            # RAG関連の改善機会
            from src.self_improvement.diagnostics import DiagnosticResult
            opportunity = ImprovementOpportunity(
                id="rag_opp",
                title="RAG改善",
                description="RAG説明",
                improvement_type=ImprovementType.PERFORMANCE,
                related_diagnostics=[
                    DiagnosticResult("rag_system", "test_metric", 50)
                ]
            )
            
            related_files = generator._identify_related_files(opportunity)
            
            assert len(related_files) >= 1
            rag_files = [f for f in related_files if "rag" in str(f)]
            assert len(rag_files) > 0
    
    @patch('src.self_improvement.autonomous_implementation.ClaudeCodeClient')
    def test_generate_implementation_plan_success(self, mock_claude_class):
        """実装計画生成成功テスト"""
        mock_claude_client = Mock()
        mock_response = Mock()
        mock_response.success = True
        mock_response.content = '''
実装計画を生成します。

```json
{
  "approach": "パフォーマンス最適化アプローチ",
  "steps": [
    {
      "step": 1,
      "description": "メモリ使用量分析",
      "files_to_modify": ["src/rag/rag_system.py"],
      "risk_level": "low"
    }
  ],
  "expected_changes": ["メモリ使用量20%削減"],
  "testing_strategy": "既存テスト実行",
  "rollback_plan": "バックアップから復旧",
  "success_criteria": ["メモリ使用量目標達成"]
}
```
'''
        mock_claude_client.generate_response.return_value = mock_response
        
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = CodeGenerator(mock_claude_client, temp_dir)
            
            opportunity = ImprovementOpportunity(
                id="plan_test",
                title="計画テスト",
                description="計画テスト説明",
                improvement_type=ImprovementType.PERFORMANCE
            )
            
            context = {}
            plan = generator._generate_implementation_plan(opportunity, context)
            
            assert isinstance(plan, dict)
            assert plan['approach'] == "パフォーマンス最適化アプローチ"
            assert len(plan['steps']) == 1
            assert plan['steps'][0]['step'] == 1
            assert 'expected_changes' in plan
            assert 'testing_strategy' in plan
    
    def test_generate_fallback_plan(self):
        """フォールバック計画生成テスト"""
        mock_claude_client = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = CodeGenerator(mock_claude_client, temp_dir)
            
            opportunity = ImprovementOpportunity(
                id="fallback_test",
                title="フォールバックテスト", 
                description="フォールバック説明",
                improvement_type=ImprovementType.CODE_QUALITY
            )
            
            plan = generator._generate_fallback_plan(opportunity)
            
            assert isinstance(plan, dict)
            assert plan['approach'] == "code_qualityの基本的な改善"
            assert len(plan['steps']) >= 2
            assert 'expected_changes' in plan
            assert 'testing_strategy' in plan
    
    def test_apply_code_changes_success(self):
        """コード変更適用成功テスト"""
        mock_claude_client = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # テストファイル作成
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def old_function():\n    return 'old'")
            
            generator = CodeGenerator(mock_claude_client, temp_dir)
            
            opportunity = ImprovementOpportunity(
                id="change_test",
                title="変更テスト",
                description="変更説明",
                improvement_type=ImprovementType.PERFORMANCE
            )
            
            # モックfile_toolの設定
            generator.file_tool = Mock()
            generator.file_tool.read_file.return_value = {
                'success': True,
                'content': "def old_function():\n    return 'old'"
            }
            generator.file_tool.write_file.return_value = {'success': True}
            
            code_changes = [
                {
                    'file_path': 'test.py',
                    'change_type': 'modify',
                    'description': 'テスト関数更新',
                    'old_code': "def old_function():\n    return 'old'",
                    'new_code': "def new_function():\n    return 'new'"
                }
            ]
            
            result = generator._apply_code_changes(opportunity, code_changes)
            
            assert result.opportunity_id == "change_test"
            assert result.success is True
            assert len(result.files_modified) == 1
            assert result.files_modified[0] == 'test.py'
            assert len(result.changes_made) == 1
    
    def test_apply_single_change_modify(self):
        """単一ファイル変更（修正）テスト"""
        mock_claude_client = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "modify_test.py"
            
            generator = CodeGenerator(mock_claude_client, temp_dir)
            
            # モックfile_tool
            generator.file_tool = Mock()
            generator.file_tool.read_file.return_value = {
                'success': True,
                'content': "original_code = 'test'"
            }
            generator.file_tool.write_file.return_value = {'success': True}
            
            change = {
                'change_type': 'modify',
                'old_code': "original_code = 'test'",
                'new_code': "new_code = 'updated'"
            }
            
            success = generator._apply_single_change(test_file, change)
            
            assert success is True
            generator.file_tool.read_file.assert_called_once()
            generator.file_tool.write_file.assert_called_once()
    
    def test_apply_single_change_add(self):
        """単一ファイル変更（追加）テスト"""
        mock_claude_client = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "add_test.py"
            
            generator = CodeGenerator(mock_claude_client, temp_dir)
            
            # モックfile_tool
            generator.file_tool = Mock()
            generator.file_tool.read_file.return_value = {
                'success': True,
                'content': "existing_code = 'test'"
            }
            generator.file_tool.write_file.return_value = {'success': True}
            
            change = {
                'change_type': 'add',
                'new_code': "added_code = 'new'"
            }
            
            success = generator._apply_single_change(test_file, change)
            
            assert success is True
            # 追加の場合、元の内容 + 新しい内容で書き込まれるはず
            call_args = generator.file_tool.write_file.call_args
            assert "existing_code = 'test'" in call_args[0][1]
            assert "added_code = 'new'" in call_args[0][1]


class TestTestAutomation:
    """TestAutomation テストクラス"""
    
    def test_test_automation_initialization(self):
        """TestAutomation 初期化テスト"""
        mock_claude_client = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            automation = TestAutomation(mock_claude_client, temp_dir)
            
            assert automation.claude_client == mock_claude_client
            assert str(automation.project_root) == temp_dir
            assert automation.system_tool is not None
    
    def test_determine_test_file_path(self):
        """テストファイルパス決定テスト"""
        mock_claude_client = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            automation = TestAutomation(mock_claude_client, temp_dir)
            
            # src配下のファイル
            source_file = "src/rag/rag_system.py"
            test_path = automation._determine_test_file_path(source_file)
            
            assert test_path == "tests/unit/rag/test_rag_system.py"
            
            # その他のファイル
            other_file = "utils/helper.py"
            test_path = automation._determine_test_file_path(other_file)
            
            assert test_path == "tests/test_helper.py"
    
    @patch('src.self_improvement.autonomous_implementation.ClaudeCodeClient')
    def test_generate_test_file_success(self, mock_claude_class):
        """テストファイル生成成功テスト"""
        mock_claude_client = Mock()
        mock_response = Mock()
        mock_response.success = True
        mock_response.content = '''
テストを生成します。

```python
import pytest
from src.test_module import TestClass

class TestTestClass:
    def test_basic_functionality(self):
        test_obj = TestClass()
        result = test_obj.method()
        assert result is not None
    
    def test_error_handling(self):
        test_obj = TestClass()
        with pytest.raises(ValueError):
            test_obj.error_method()
```
'''
        mock_claude_client.generate_response.return_value = mock_response
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # ソースファイル作成
            src_file = Path(temp_dir) / "src" / "test_module.py"
            src_file.parent.mkdir(parents=True)
            src_file.write_text('''
class TestClass:
    def method(self):
        return "result"
    
    def error_method(self):
        raise ValueError("test error")
''')
            
            automation = TestAutomation(mock_claude_client, temp_dir)
            
            implementation_result = ImplementationResult(
                opportunity_id="test_opp",
                success=True,
                files_modified=["src/test_module.py"],
                changes_made=["TestClass追加"]
            )
            
            test_file = automation._generate_test_file("src/test_module.py", implementation_result)
            
            assert test_file is not None
            assert test_file == "tests/unit/test_test_module.py"
            
            # テストファイルが作成されているはず
            test_file_path = Path(temp_dir) / test_file
            assert test_file_path.exists()
            
            # ファイル内容確認
            content = test_file_path.read_text()
            assert "import pytest" in content
            assert "TestTestClass" in content
    
    def test_generate_tests_for_implementation(self):
        """実装対応テスト生成テスト"""
        mock_claude_client = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            automation = TestAutomation(mock_claude_client, temp_dir)
            
            # _generate_test_fileをモック
            automation._generate_test_file = Mock()
            automation._generate_test_file.return_value = "tests/test_generated.py"
            
            implementation_result = ImplementationResult(
                opportunity_id="multi_test",
                success=True,
                files_modified=["src/file1.py", "src/file2.py"]
            )
            
            generated_tests = automation.generate_tests_for_implementation(implementation_result)
            
            assert len(generated_tests) == 2
            assert all("tests/test_generated.py" == test for test in generated_tests)
            assert automation._generate_test_file.call_count == 2
    
    def test_run_tests_all(self):
        """全テスト実行テスト"""
        mock_claude_client = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            automation = TestAutomation(mock_claude_client, temp_dir)
            
            # system_toolをモック
            automation.system_tool = Mock()
            automation.system_tool.execute_command.return_value = {
                'success': True,
                'output': 'test output',
                'error': ''
            }
            
            result = automation.run_tests()
            
            assert result['success'] is True
            assert 'stdout' in result
            assert result['command'] == "python -m pytest tests/ -v"
            automation.system_tool.execute_command.assert_called_once()
    
    def test_run_tests_specific_files(self):
        """特定ファイルテスト実行テスト"""
        mock_claude_client = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            automation = TestAutomation(mock_claude_client, temp_dir)
            
            # system_toolをモック
            automation.system_tool = Mock()
            automation.system_tool.execute_command.return_value = {
                'success': True,
                'output': 'specific test output'
            }
            
            test_files = ["tests/test_file1.py", "tests/test_file2.py"]
            result = automation.run_tests(test_files)
            
            assert result['success'] is True
            assert "tests/test_file1.py tests/test_file2.py" in result['command']


class TestDeploymentManager:
    """DeploymentManager テストクラス"""
    
    def test_deployment_manager_initialization(self):
        """DeploymentManager 初期化テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DeploymentManager(temp_dir)
            
            assert str(manager.project_root) == temp_dir
            assert manager.system_tool is not None
    
    def test_create_deployment_backup(self):
        """デプロイメントバックアップ作成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # プロジェクト構造作成
            src_dir = Path(temp_dir) / "src"
            src_dir.mkdir()
            (src_dir / "test_file.py").write_text("# test content")
            
            manager = DeploymentManager(temp_dir)
            
            backup_path = manager.create_deployment_backup()
            
            assert backup_path.startswith("/tmp/aide_backup_")
            assert Path(backup_path).exists()
            
            # バックアップ内容確認
            backup_src = Path(backup_path) / "src"
            assert backup_src.exists()
            assert (backup_src / "test_file.py").exists()
    
    def test_validate_deployment(self):
        """デプロイメント検証テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 有効なPythonファイル作成
            src_dir = Path(temp_dir) / "src"
            src_dir.mkdir()
            (src_dir / "valid_file.py").write_text("def valid_function():\n    return True")
            
            manager = DeploymentManager(temp_dir)
            
            implementation_results = [
                ImplementationResult(
                    opportunity_id="test_opp",
                    success=True,
                    files_modified=["src/valid_file.py"]
                )
            ]
            
            # system_toolをモック（テスト実行成功）
            manager.system_tool = Mock()
            manager.system_tool.execute_command.return_value = {'success': True}
            
            checks = manager.validate_deployment(implementation_results)
            
            assert len(checks) >= 3  # 構文、インポート、テスト、設定チェック
            
            # 各チェックタイプが含まれているはず
            check_names = [check.check_name for check in checks]
            assert "python_syntax" in check_names
            assert "imports" in check_names
            assert "existing_tests" in check_names
            assert "configuration" in check_names
    
    def test_check_python_syntax_valid(self):
        """Python構文チェック（有効）テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 有効なPythonファイル
            src_dir = Path(temp_dir) / "src"
            src_dir.mkdir()
            (src_dir / "valid.py").write_text("def test():\n    return 42")
            
            manager = DeploymentManager(temp_dir)
            
            implementation_results = [
                ImplementationResult(
                    opportunity_id="syntax_test",
                    success=True,
                    files_modified=["src/valid.py"]
                )
            ]
            
            check = manager._check_python_syntax(implementation_results)
            
            assert check.check_name == "python_syntax"
            assert check.passed is True
            assert "構文チェック完了" in check.message
    
    def test_check_python_syntax_invalid(self):
        """Python構文チェック（無効）テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 無効なPythonファイル
            src_dir = Path(temp_dir) / "src"
            src_dir.mkdir()
            (src_dir / "invalid.py").write_text("def invalid_syntax(\n    return invalid")
            
            manager = DeploymentManager(temp_dir)
            
            implementation_results = [
                ImplementationResult(
                    opportunity_id="syntax_error_test",
                    success=True,
                    files_modified=["src/invalid.py"]
                )
            ]
            
            check = manager._check_python_syntax(implementation_results)
            
            assert check.check_name == "python_syntax"
            assert check.passed is False
            assert check.severity == "error"
            assert "構文エラー" in check.message
    
    def test_rollback_deployment(self):
        """デプロイメントロールバックテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 元のプロジェクト作成
            original_file = Path(temp_dir) / "original.txt"
            original_file.write_text("original content")
            
            # バックアップ作成
            with tempfile.TemporaryDirectory() as backup_dir:
                backup_file = Path(backup_dir) / "original.txt"
                backup_file.write_text("original content")
                
                # プロジェクトを変更
                original_file.write_text("modified content")
                
                manager = DeploymentManager(temp_dir)
                
                # ロールバック実行
                success = manager.rollback_deployment(backup_dir)
                
                assert success is True
                # 元の内容に戻っているはず
                assert original_file.read_text() == "original content"


class TestAutonomousImplementation:
    """AutonomousImplementation テストクラス"""
    
    def test_autonomous_implementation_initialization(self):
        """AutonomousImplementation 初期化テスト"""
        mock_claude_client = Mock()
        
        implementation = AutonomousImplementation(mock_claude_client)
        
        assert implementation.claude_client == mock_claude_client
        assert isinstance(implementation.code_generator, CodeGenerator)
        assert isinstance(implementation.test_automation, TestAutomation)
        assert isinstance(implementation.deployment_manager, DeploymentManager)
        assert implementation.implementation_history == []
    
    def test_simulate_implementation(self):
        """実装シミュレーション（ドライラン）テスト"""
        mock_claude_client = Mock()
        implementation = AutonomousImplementation(mock_claude_client)
        
        opportunity = ImprovementOpportunity(
            id="sim_test",
            title="シミュレーションテスト",
            description="ドライラン説明",
            improvement_type=ImprovementType.PERFORMANCE
        )
        
        result = implementation._simulate_implementation(opportunity)
        
        assert result.opportunity_id == "sim_test"
        assert result.success is True
        assert "[DRY RUN]" in result.changes_made[0]
        assert result.files_modified == []
        assert result.tests_generated == []
        assert result.execution_time == 0.1
    
    def test_implement_opportunity_dry_run(self):
        """改善機会実装（ドライラン）テスト"""
        mock_claude_client = Mock()
        implementation = AutonomousImplementation(mock_claude_client)
        
        opportunity = ImprovementOpportunity(
            id="dry_run_test",
            title="ドライランテスト",
            description="ドライラン説明",
            improvement_type=ImprovementType.CODE_QUALITY
        )
        
        result = implementation.implement_opportunity(opportunity, dry_run=True)
        
        assert result.opportunity_id == "dry_run_test"
        assert result.success is True
        assert len(implementation.implementation_history) == 1
    
    @patch('src.self_improvement.autonomous_implementation.DeploymentManager')
    @patch('src.self_improvement.autonomous_implementation.CodeGenerator')
    def test_implement_opportunity_real_success(self, mock_code_gen_class, mock_deploy_class):
        """改善機会実装（実際）成功テスト"""
        mock_claude_client = Mock()
        
        # DeploymentManagerモック
        mock_deploy_manager = Mock()
        mock_deploy_manager.create_deployment_backup.return_value = "/tmp/backup_test"
        mock_deploy_manager.validate_deployment.return_value = [
            SafetyCheck("test_check", True, "成功")
        ]
        mock_deploy_class.return_value = mock_deploy_manager
        
        # CodeGeneratorモック
        mock_code_generator = Mock()
        mock_impl_result = ImplementationResult("test_opp", True)
        mock_impl_result.rollback_info = {'backup_path': '/tmp/backup_test'}
        mock_code_generator.generate_implementation.return_value = mock_impl_result
        mock_code_gen_class.return_value = mock_code_generator
        
        implementation = AutonomousImplementation(mock_claude_client)
        
        opportunity = ImprovementOpportunity(
            id="real_test",
            title="実際のテスト",
            description="実際の実装テスト",
            improvement_type=ImprovementType.PERFORMANCE
        )
        
        result = implementation.implement_opportunity(opportunity, dry_run=False)
        
        assert result.opportunity_id == "real_test"
        assert result.success is True
        mock_deploy_manager.create_deployment_backup.assert_called_once()
        mock_code_generator.generate_implementation.assert_called_once()
        mock_deploy_manager.validate_deployment.assert_called_once()
    
    def test_implement_roadmap(self):
        """ロードマップ実装テスト"""
        mock_claude_client = Mock()
        implementation = AutonomousImplementation(mock_claude_client)
        
        # implement_opportunityをモック
        implementation.implement_opportunity = Mock()
        
        success_result = ImplementationResult("success_opp", True)
        failure_result = ImplementationResult("failure_opp", False, error_message="テストエラー")
        
        implementation.implement_opportunity.side_effect = [success_result, failure_result]
        
        from src.self_improvement.improvement_engine import ImprovementRoadmap
        
        opportunities = [
            ImprovementOpportunity("success_opp", "成功改善", "説明", ImprovementType.PERFORMANCE, priority=Priority.CRITICAL),
            ImprovementOpportunity("failure_opp", "失敗改善", "説明", ImprovementType.PERFORMANCE, priority=Priority.HIGH),
            ImprovementOpportunity("skip_opp", "スキップ改善", "説明", ImprovementType.PERFORMANCE, priority=Priority.LOW)
        ]
        
        roadmap = ImprovementRoadmap("test_roadmap", "テストロードマップ", opportunities)
        
        results = implementation.implement_roadmap(roadmap, dry_run=True)
        
        # Critical/Highのみ実装され、失敗で停止するはず
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        
        # 2回だけ呼ばれるはず（失敗で停止）
        assert implementation.implement_opportunity.call_count == 2
    
    def test_get_implementation_summary(self):
        """実装概要取得テスト"""
        mock_claude_client = Mock()
        implementation = AutonomousImplementation(mock_claude_client)
        
        # 履歴なしテスト
        summary = implementation.get_implementation_summary()
        assert summary["status"] == "no_implementations"
        
        # 履歴ありテスト
        results = [
            ImplementationResult("opp1", True, files_modified=["file1.py"], tests_generated=["test1.py"]),
            ImplementationResult("opp2", False, files_modified=["file2.py"]),
            ImplementationResult("opp3", True, files_modified=["file3.py", "file4.py"], tests_generated=["test2.py", "test3.py"])
        ]
        
        implementation.implementation_history = results
        
        summary = implementation.get_implementation_summary()
        
        assert summary["total_implementations"] == 3
        assert summary["successful_implementations"] == 2
        assert summary["success_rate"] == 2/3 * 100
        assert summary["total_files_modified"] == 4  # file1, file2, file3, file4
        assert summary["total_tests_generated"] == 3  # test1, test2, test3
        assert summary["latest_implementation"] is not None


if __name__ == "__main__":
    pytest.main([__file__])