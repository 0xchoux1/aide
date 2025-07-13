"""
自律実装システム

Claude Code活用による自動コード生成、テスト生成、デプロイメント管理
"""

import os
import subprocess
import tempfile
import shutil
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
import json
import re
import ast

from .improvement_engine import ImprovementOpportunity, ImprovementRoadmap
from ..llm.claude_code_client import ClaudeCodeClient
from ..tools.system_tool import SystemTool
from ..tools.file_tool import FileTool


@dataclass
class ImplementationResult:
    """実装結果クラス"""
    opportunity_id: str
    success: bool
    changes_made: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    tests_generated: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    execution_time: float = 0.0
    rollback_info: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'opportunity_id': self.opportunity_id,
            'success': self.success,
            'changes_made': self.changes_made,
            'files_modified': self.files_modified,
            'tests_generated': self.tests_generated,
            'error_message': self.error_message,
            'execution_time': self.execution_time,
            'rollback_info': self.rollback_info,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class SafetyCheck:
    """安全性チェック結果"""
    check_name: str
    passed: bool
    message: str
    severity: str = "info"  # info, warning, error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'check_name': self.check_name,
            'passed': self.passed,
            'message': self.message,
            'severity': self.severity
        }


class CodeGenerator:
    """Claude Code活用コード生成システム"""
    
    def __init__(self, claude_client: ClaudeCodeClient, project_root: str):
        self.claude_client = claude_client
        self.project_root = Path(project_root)
        self.file_tool = FileTool()
    
    def generate_implementation(self, opportunity: ImprovementOpportunity) -> ImplementationResult:
        """改善機会の実装を生成"""
        start_time = datetime.now()
        
        try:
            # 1. 現在のコード状況を分析
            context = self._analyze_current_code(opportunity)
            
            # 2. 実装計画を生成
            implementation_plan = self._generate_implementation_plan(opportunity, context)
            
            # 3. コード変更を生成
            code_changes = self._generate_code_changes(opportunity, implementation_plan, context)
            
            # 4. 変更を適用
            result = self._apply_code_changes(opportunity, code_changes)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ImplementationResult(
                opportunity_id=opportunity.id,
                success=False,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _analyze_current_code(self, opportunity: ImprovementOpportunity) -> Dict[str, Any]:
        """現在のコード状況を分析"""
        context = {
            'related_files': [],
            'current_metrics': {},
            'dependencies': [],
            'architecture_info': {}
        }
        
        try:
            # 関連ファイルを特定
            related_files = self._identify_related_files(opportunity)
            context['related_files'] = related_files
            
            # ファイル内容を読み込み
            for file_path in related_files[:5]:  # 最大5ファイル
                try:
                    content = self.file_tool.read_file(str(file_path))
                    if content['success']:
                        context[f'file_content_{file_path.name}'] = content['content'][:2000]  # 最初の2000文字
                except Exception:
                    pass
            
            # プロジェクト構造情報
            context['project_structure'] = self._get_project_structure()
            
        except Exception as e:
            context['analysis_error'] = str(e)
        
        return context
    
    def _identify_related_files(self, opportunity: ImprovementOpportunity) -> List[Path]:
        """改善機会に関連するファイルを特定"""
        related_files = []
        
        # 診断結果から関連コンポーネントを特定
        for diag in opportunity.related_diagnostics:
            component = diag.component
            
            if component == "rag_system":
                related_files.extend(self.project_root.glob("src/rag/*.py"))
            elif component == "performance":
                related_files.extend(self.project_root.glob("src/**/*.py"))
            elif component == "code_quality":
                related_files.extend(self.project_root.glob("src/**/*.py"))
            elif component == "learning":
                related_files.extend(self.project_root.glob("src/learning/*.py"))
                related_files.extend(self.project_root.glob("src/agents/*.py"))
        
        # 重複除去
        return list(set(related_files))[:10]  # 最大10ファイル
    
    def _get_project_structure(self) -> Dict[str, Any]:
        """プロジェクト構造情報を取得"""
        structure = {}
        
        try:
            # src配下の構造
            src_path = self.project_root / "src"
            if src_path.exists():
                structure['src_modules'] = [d.name for d in src_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
            
            # 主要設定ファイル
            config_files = ['pyproject.toml', 'requirements.txt', 'CLAUDE.md']
            for config_file in config_files:
                config_path = self.project_root / config_file
                if config_path.exists():
                    structure[f'has_{config_file}'] = True
            
        except Exception as e:
            structure['error'] = str(e)
        
        return structure
    
    def _generate_implementation_plan(self, opportunity: ImprovementOpportunity, 
                                    context: Dict[str, Any]) -> Dict[str, Any]:
        """実装計画を生成"""
        
        planning_prompt = f"""
AIDE自律改善システムの改善機会実装計画を生成してください。

改善機会:
- ID: {opportunity.id}
- タイトル: {opportunity.title}
- 説明: {opportunity.description}
- タイプ: {opportunity.improvement_type.value}
- 複雑度: {opportunity.complexity_level}
- 推定時間: {opportunity.estimated_time_hours}時間

現在のコンテキスト:
{json.dumps(context, ensure_ascii=False, indent=2)[:2000]}

以下の形式で実装計画を生成してください：

```json
{{
  "approach": "実装アプローチの説明",
  "steps": [
    {{"step": 1, "description": "ステップ説明", "files_to_modify": ["ファイルパス"], "risk_level": "low/medium/high"}},
    {{"step": 2, "description": "ステップ説明", "files_to_modify": ["ファイルパス"], "risk_level": "low/medium/high"}}
  ],
  "expected_changes": ["変更内容1", "変更内容2"],
  "testing_strategy": "テスト戦略",
  "rollback_plan": "ロールバック計画",
  "success_criteria": ["成功基準1", "成功基準2"]
}}
```

実用的で安全な実装計画を生成してください。
"""
        
        try:
            response = self.claude_client.generate_response(planning_prompt)
            
            if response.success:
                # JSONを抽出
                json_match = re.search(r'```json\s*\n(.*?)\n```', response.content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
            
            # フォールバック計画
            return self._generate_fallback_plan(opportunity)
            
        except Exception as e:
            print(f"実装計画生成エラー: {e}")
            return self._generate_fallback_plan(opportunity)
    
    def _generate_fallback_plan(self, opportunity: ImprovementOpportunity) -> Dict[str, Any]:
        """フォールバック実装計画"""
        return {
            "approach": f"{opportunity.improvement_type.value}の基本的な改善",
            "steps": [
                {
                    "step": 1,
                    "description": "関連ファイルの特定と分析",
                    "files_to_modify": [],
                    "risk_level": "low"
                },
                {
                    "step": 2, 
                    "description": "改善実装",
                    "files_to_modify": [],
                    "risk_level": "medium"
                }
            ],
            "expected_changes": [opportunity.description],
            "testing_strategy": "既存テストの実行",
            "rollback_plan": "変更前の状態にロールバック",
            "success_criteria": ["改善目標の達成"]
        }
    
    def _generate_code_changes(self, opportunity: ImprovementOpportunity, 
                             implementation_plan: Dict[str, Any],
                             context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """コード変更を生成"""
        code_changes = []
        
        for step in implementation_plan.get('steps', []):
            files_to_modify = step.get('files_to_modify', [])
            
            for file_path in files_to_modify:
                try:
                    change = self._generate_file_change(opportunity, file_path, step, context)
                    if change:
                        code_changes.append(change)
                except Exception as e:
                    print(f"ファイル変更生成エラー {file_path}: {e}")
        
        return code_changes
    
    def _generate_file_change(self, opportunity: ImprovementOpportunity,
                            file_path: str, step: Dict[str, Any],
                            context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """個別ファイルの変更を生成"""
        
        full_path = self.project_root / file_path
        if not full_path.exists():
            return None
        
        # 現在のファイル内容を読み込み
        try:
            current_content = self.file_tool.read_file(str(full_path))
            if not current_content['success']:
                return None
            
            file_content = current_content['content']
            
        except Exception:
            return None
        
        # コード変更生成プロンプト
        change_prompt = f"""
ファイル: {file_path}
改善目標: {opportunity.title}
実装ステップ: {step['description']}

現在のファイル内容:
```python
{file_content[:1500]}
```

このファイルに対して必要な変更を生成してください。以下の形式で出力してください：

```json
{{
  "change_type": "modify/add/delete",
  "description": "変更の説明",
  "old_code": "変更前のコード（modify/deleteの場合）",
  "new_code": "変更後のコード（modify/addの場合）",
  "line_number": "変更箇所の行番号（推定）"
}}
```

安全で最小限の変更を提案してください。
"""
        
        try:
            response = self.claude_client.generate_response(change_prompt)
            
            if response.success:
                # JSONを抽出
                json_match = re.search(r'```json\s*\n(.*?)\n```', response.content, re.DOTALL)
                if json_match:
                    change_data = json.loads(json_match.group(1))
                    change_data['file_path'] = file_path
                    return change_data
            
        except Exception as e:
            print(f"コード変更生成エラー: {e}")
        
        return None
    
    def _apply_code_changes(self, opportunity: ImprovementOpportunity,
                          code_changes: List[Dict[str, Any]]) -> ImplementationResult:
        """コード変更を適用"""
        
        result = ImplementationResult(opportunity_id=opportunity.id, success=True)
        
        # バックアップ情報
        backup_info = {}
        
        try:
            for change in code_changes:
                file_path = change.get('file_path')
                if not file_path:
                    continue
                
                full_path = self.project_root / file_path
                
                # バックアップ作成
                if full_path.exists():
                    backup_content = self.file_tool.read_file(str(full_path))
                    if backup_content['success']:
                        backup_info[file_path] = backup_content['content']
                
                # 変更適用
                success = self._apply_single_change(full_path, change)
                
                if success:
                    result.files_modified.append(file_path)
                    result.changes_made.append(change.get('description', 'コード変更'))
                else:
                    result.success = False
                    result.error_message = f"ファイル変更失敗: {file_path}"
                    break
            
            # ロールバック情報を保存
            result.rollback_info = backup_info
            
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            
            # エラー時はロールバック実行
            self._rollback_changes(backup_info)
        
        return result
    
    def _apply_single_change(self, file_path: Path, change: Dict[str, Any]) -> bool:
        """単一ファイルの変更を適用"""
        try:
            change_type = change.get('change_type', 'modify')
            
            if change_type == 'modify':
                return self._modify_file_content(file_path, change)
            elif change_type == 'add':
                return self._add_to_file(file_path, change)
            elif change_type == 'delete':
                return self._delete_from_file(file_path, change)
            
            return False
            
        except Exception as e:
            print(f"ファイル変更適用エラー: {e}")
            return False
    
    def _modify_file_content(self, file_path: Path, change: Dict[str, Any]) -> bool:
        """ファイル内容を修正"""
        try:
            old_code = change.get('old_code', '')
            new_code = change.get('new_code', '')
            
            if not old_code or not new_code:
                return False
            
            # ファイル読み込み
            content_result = self.file_tool.read_file(str(file_path))
            if not content_result['success']:
                return False
            
            content = content_result['content']
            
            # 文字列置換
            if old_code in content:
                new_content = content.replace(old_code, new_code)
                
                # ファイル書き込み
                write_result = self.file_tool.write_file(str(file_path), new_content)
                return write_result['success']
            
            return False
            
        except Exception:
            return False
    
    def _add_to_file(self, file_path: Path, change: Dict[str, Any]) -> bool:
        """ファイルに内容を追加"""
        try:
            new_code = change.get('new_code', '')
            if not new_code:
                return False
            
            # ファイル読み込み
            content_result = self.file_tool.read_file(str(file_path))
            if not content_result['success']:
                return False
            
            content = content_result['content']
            
            # 末尾に追加
            new_content = content + '\n\n' + new_code
            
            # ファイル書き込み
            write_result = self.file_tool.write_file(str(file_path), new_content)
            return write_result['success']
            
        except Exception:
            return False
    
    def _delete_from_file(self, file_path: Path, change: Dict[str, Any]) -> bool:
        """ファイルから内容を削除"""
        try:
            old_code = change.get('old_code', '')
            if not old_code:
                return False
            
            # ファイル読み込み
            content_result = self.file_tool.read_file(str(file_path))
            if not content_result['success']:
                return False
            
            content = content_result['content']
            
            # 削除
            if old_code in content:
                new_content = content.replace(old_code, '')
                
                # ファイル書き込み
                write_result = self.file_tool.write_file(str(file_path), new_content)
                return write_result['success']
            
            return False
            
        except Exception:
            return False
    
    def _rollback_changes(self, backup_info: Dict[str, str]):
        """変更をロールバック"""
        for file_path, original_content in backup_info.items():
            try:
                full_path = self.project_root / file_path
                self.file_tool.write_file(str(full_path), original_content)
            except Exception as e:
                print(f"ロールバックエラー {file_path}: {e}")


class TestAutomation:
    """テスト自動化システム"""
    
    def __init__(self, claude_client: ClaudeCodeClient, project_root: str):
        self.claude_client = claude_client
        self.project_root = Path(project_root)
        self.system_tool = SystemTool()
    
    def generate_tests_for_implementation(self, implementation_result: ImplementationResult) -> List[str]:
        """実装に対するテストを生成"""
        generated_tests = []
        
        for file_path in implementation_result.files_modified:
            try:
                test_file = self._generate_test_file(file_path, implementation_result)
                if test_file:
                    generated_tests.append(test_file)
            except Exception as e:
                print(f"テスト生成エラー {file_path}: {e}")
        
        return generated_tests
    
    def _generate_test_file(self, file_path: str, implementation_result: ImplementationResult) -> Optional[str]:
        """個別ファイルのテストを生成"""
        
        source_path = self.project_root / file_path
        if not source_path.exists():
            return None
        
        # テストファイルパス決定
        test_file_path = self._determine_test_file_path(file_path)
        
        # ソースコード読み込み
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                source_content = f.read()
        except Exception:
            return None
        
        # テスト生成プロンプト
        test_prompt = f"""
Pythonファイルのユニットテストを生成してください。

ソースファイル: {file_path}
実装された変更: {', '.join(implementation_result.changes_made)}

ソースコード:
```python
{source_content[:1500]}
```

pytest形式のユニットテストを生成してください。以下を含めてください：
1. 基本機能のテスト
2. エラーケースのテスト  
3. 境界値のテスト
4. 実装された変更の検証

テストファイル名: {test_file_path}
"""
        
        try:
            response = self.claude_client.generate_response(test_prompt)
            
            if response.success:
                # コードブロックを抽出
                code_match = re.search(r'```python\s*\n(.*?)\n```', response.content, re.DOTALL)
                if code_match:
                    test_content = code_match.group(1)
                    
                    # テストファイル作成
                    full_test_path = self.project_root / test_file_path
                    full_test_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(full_test_path, 'w', encoding='utf-8') as f:
                        f.write(test_content)
                    
                    return test_file_path
            
        except Exception as e:
            print(f"テストファイル生成エラー: {e}")
        
        return None
    
    def _determine_test_file_path(self, source_file_path: str) -> str:
        """テストファイルパスを決定"""
        source_path = Path(source_file_path)
        
        # src/module/file.py -> tests/unit/test_file.py
        if source_path.parts[0] == 'src':
            module_parts = source_path.parts[1:-1]  # src除去、ファイル名除去
            file_name = source_path.stem
            
            test_path = Path('tests') / 'unit'
            for part in module_parts:
                test_path = test_path / part
            
            test_path = test_path / f'test_{file_name}.py'
            return str(test_path)
        
        # フォールバック
        return f'tests/test_{source_path.stem}.py'
    
    def run_tests(self, test_files: List[str] = None) -> Dict[str, Any]:
        """テストを実行"""
        if test_files is None:
            # 全テストを実行
            test_command = "python -m pytest tests/ -v"
        else:
            # 指定テストのみ実行
            test_paths = ' '.join(test_files)
            test_command = f"python -m pytest {test_paths} -v"
        
        try:
            result = self.system_tool.execute_command(test_command)
            
            return {
                'success': result['success'],
                'stdout': result.get('output', ''),
                'stderr': result.get('error', ''),
                'command': test_command
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'command': test_command
            }


class DeploymentManager:
    """デプロイメント管理システム"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.system_tool = SystemTool()
        
    def create_deployment_backup(self) -> str:
        """デプロイメント前のバックアップを作成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f"/tmp/aide_backup_{timestamp}"
        
        try:
            # プロジェクトディレクトリをバックアップ
            shutil.copytree(self.project_root, backup_dir, 
                          ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git', 'venv'))
            return backup_dir
            
        except Exception as e:
            raise RuntimeError(f"バックアップ作成失敗: {e}")
    
    def validate_deployment(self, implementation_results: List[ImplementationResult]) -> List[SafetyCheck]:
        """デプロイメント前の検証"""
        checks = []
        
        # 1. 構文チェック
        syntax_check = self._check_python_syntax(implementation_results)
        checks.append(syntax_check)
        
        # 2. インポートチェック
        import_check = self._check_imports(implementation_results)
        checks.append(import_check)
        
        # 3. テストチェック
        test_check = self._check_existing_tests()
        checks.append(test_check)
        
        # 4. 設定チェック
        config_check = self._check_configuration()
        checks.append(config_check)
        
        return checks
    
    def _check_python_syntax(self, implementation_results: List[ImplementationResult]) -> SafetyCheck:
        """Python構文チェック"""
        errors = []
        
        for result in implementation_results:
            for file_path in result.files_modified:
                full_path = self.project_root / file_path
                if full_path.exists() and full_path.suffix == '.py':
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # AST解析で構文チェック
                        ast.parse(content)
                        
                    except SyntaxError as e:
                        errors.append(f"{file_path}: {str(e)}")
                    except Exception as e:
                        errors.append(f"{file_path}: {str(e)}")
        
        if errors:
            return SafetyCheck(
                check_name="python_syntax",
                passed=False,
                message=f"構文エラー: {'; '.join(errors)}",
                severity="error"
            )
        
        return SafetyCheck(
            check_name="python_syntax",
            passed=True,
            message="全ファイルの構文チェック完了"
        )
    
    def _check_imports(self, implementation_results: List[ImplementationResult]) -> SafetyCheck:
        """インポートチェック"""
        # 簡易的なインポートチェック
        try:
            # 基本的なAIDEモジュールのインポートテスト
            import_test_script = '''
import sys
sys.path.append('src')

try:
    from agents.base_agent import BaseAgent
    from rag.rag_system import RAGSystem
    from self_improvement.diagnostics import SystemDiagnostics
    print("Import test passed")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)
'''
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(import_test_script)
                test_file = f.name
            
            try:
                result = subprocess.run(
                    ['python', test_file],
                    cwd=str(self.project_root),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                os.unlink(test_file)
                
                if result.returncode == 0:
                    return SafetyCheck(
                        check_name="imports",
                        passed=True,
                        message="インポートチェック完了"
                    )
                else:
                    return SafetyCheck(
                        check_name="imports",
                        passed=False,
                        message=f"インポートエラー: {result.stderr}",
                        severity="error"
                    )
                    
            except subprocess.TimeoutExpired:
                os.unlink(test_file)
                return SafetyCheck(
                    check_name="imports",
                    passed=False,
                    message="インポートテストタイムアウト",
                    severity="warning"
                )
                
        except Exception as e:
            return SafetyCheck(
                check_name="imports",
                passed=False,
                message=f"インポートチェック失敗: {e}",
                severity="error"
            )
    
    def _check_existing_tests(self) -> SafetyCheck:
        """既存テストの実行チェック"""
        try:
            result = self.system_tool.execute_command("python -m pytest tests/ --tb=short -q")
            
            if result['success']:
                return SafetyCheck(
                    check_name="existing_tests",
                    passed=True,
                    message="既存テスト実行成功"
                )
            else:
                return SafetyCheck(
                    check_name="existing_tests",
                    passed=False,
                    message=f"テスト失敗: {result.get('error', 'Unknown error')}",
                    severity="error"
                )
                
        except Exception as e:
            return SafetyCheck(
                check_name="existing_tests",
                passed=False,
                message=f"テスト実行エラー: {e}",
                severity="warning"
            )
    
    def _check_configuration(self) -> SafetyCheck:
        """設定ファイルチェック"""
        required_files = ['pyproject.toml', 'CLAUDE.md']
        missing_files = []
        
        for file_name in required_files:
            file_path = self.project_root / file_name
            if not file_path.exists():
                missing_files.append(file_name)
        
        if missing_files:
            return SafetyCheck(
                check_name="configuration",
                passed=False,
                message=f"設定ファイル不足: {', '.join(missing_files)}",
                severity="warning"
            )
        
        return SafetyCheck(
            check_name="configuration",
            passed=True,
            message="設定ファイルチェック完了"
        )
    
    def rollback_deployment(self, backup_path: str) -> bool:
        """デプロイメントをロールバック"""
        try:
            if not os.path.exists(backup_path):
                raise RuntimeError(f"バックアップが見つかりません: {backup_path}")
            
            # 現在のプロジェクトを一時的に移動
            temp_current = f"{self.project_root}_rollback_temp"
            shutil.move(str(self.project_root), temp_current)
            
            try:
                # バックアップから復元
                shutil.copytree(backup_path, str(self.project_root))
                
                # 一時ディレクトリを削除
                shutil.rmtree(temp_current)
                
                return True
                
            except Exception as e:
                # 復元失敗時は元に戻す
                if os.path.exists(str(self.project_root)):
                    shutil.rmtree(str(self.project_root))
                shutil.move(temp_current, str(self.project_root))
                raise e
                
        except Exception as e:
            print(f"ロールバック失敗: {e}")
            return False


class AutonomousImplementation:
    """統合自律実装システム"""
    
    def __init__(self, claude_client: ClaudeCodeClient, 
                 project_root: str = "/home/choux1/src/github.com/0xchoux1/aide"):
        self.claude_client = claude_client
        self.project_root = project_root
        
        self.code_generator = CodeGenerator(claude_client, project_root)
        self.test_automation = TestAutomation(claude_client, project_root)
        self.deployment_manager = DeploymentManager(project_root)
        
        self.implementation_history: List[ImplementationResult] = []
    
    def implement_opportunity(self, opportunity: ImprovementOpportunity, 
                            dry_run: bool = False) -> ImplementationResult:
        """改善機会を実装"""
        
        if dry_run:
            return self._simulate_implementation(opportunity)
        
        # 1. バックアップ作成
        try:
            backup_path = self.deployment_manager.create_deployment_backup()
        except Exception as e:
            return ImplementationResult(
                opportunity_id=opportunity.id,
                success=False,
                error_message=f"バックアップ作成失敗: {e}"
            )
        
        # 2. 実装実行
        implementation_result = self.code_generator.generate_implementation(opportunity)
        implementation_result.rollback_info = {'backup_path': backup_path}
        
        if not implementation_result.success:
            return implementation_result
        
        # 3. 安全性チェック
        safety_checks = self.deployment_manager.validate_deployment([implementation_result])
        failed_checks = [check for check in safety_checks if not check.passed and check.severity == "error"]
        
        if failed_checks:
            # 安全性チェック失敗時はロールバック
            self.deployment_manager.rollback_deployment(backup_path)
            implementation_result.success = False
            implementation_result.error_message = f"安全性チェック失敗: {'; '.join(check.message for check in failed_checks)}"
            return implementation_result
        
        # 4. テスト生成・実行
        try:
            generated_tests = self.test_automation.generate_tests_for_implementation(implementation_result)
            implementation_result.tests_generated = generated_tests
            
            # 既存テスト実行
            test_result = self.test_automation.run_tests()
            if not test_result['success']:
                print(f"テスト警告: {test_result.get('error', 'Unknown error')}")
            
        except Exception as e:
            print(f"テスト実行エラー: {e}")
        
        # 5. 履歴に記録
        self.implementation_history.append(implementation_result)
        
        return implementation_result
    
    def _simulate_implementation(self, opportunity: ImprovementOpportunity) -> ImplementationResult:
        """実装のシミュレーション（ドライラン）"""
        return ImplementationResult(
            opportunity_id=opportunity.id,
            success=True,
            changes_made=[f"[DRY RUN] {opportunity.title}の実装"],
            files_modified=[],
            tests_generated=[],
            execution_time=0.1
        )
    
    def implement_roadmap(self, roadmap: ImprovementRoadmap, 
                         dry_run: bool = False) -> List[ImplementationResult]:
        """ロードマップ全体を実装"""
        results = []
        
        for opportunity in roadmap.opportunities:
            # Critical/Highのみ実装
            if opportunity.priority.value in ['critical', 'high']:
                try:
                    result = self.implement_opportunity(opportunity, dry_run)
                    results.append(result)
                    
                    # 実装失敗時は停止
                    if not result.success:
                        print(f"実装失敗により停止: {opportunity.id}")
                        break
                        
                except Exception as e:
                    error_result = ImplementationResult(
                        opportunity_id=opportunity.id,
                        success=False,
                        error_message=str(e)
                    )
                    results.append(error_result)
                    print(f"実装エラーにより停止: {opportunity.id}")
                    break
        
        return results
    
    def get_implementation_summary(self) -> Dict[str, Any]:
        """実装概要を取得"""
        if not self.implementation_history:
            return {"status": "no_implementations"}
        
        total_implementations = len(self.implementation_history)
        successful_implementations = sum(1 for r in self.implementation_history if r.success)
        
        return {
            "total_implementations": total_implementations,
            "successful_implementations": successful_implementations,
            "success_rate": successful_implementations / total_implementations * 100,
            "total_files_modified": sum(len(r.files_modified) for r in self.implementation_history),
            "total_tests_generated": sum(len(r.tests_generated) for r in self.implementation_history),
            "latest_implementation": self.implementation_history[-1].to_dict() if self.implementation_history else None
        }