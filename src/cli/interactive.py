"""
AIDE インタラクティブモード

対話型ユーザーインターフェース
"""

import sys
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import readline  # コマンド履歴とタブ補完のため

from .formatters import OutputFormatter, TableFormatter, ProgressFormatter
from ..config import get_config_manager
from ..self_improvement.diagnostics import SystemDiagnostics
from ..self_improvement.improvement_engine import ImprovementEngine


class MenuType(Enum):
    """メニュータイプ"""
    MAIN = "main"
    DIAGNOSTICS = "diagnostics"
    IMPROVEMENT = "improvement"
    CONFIG = "config"
    SYSTEM = "system"


@dataclass
class MenuOption:
    """メニューオプション"""
    key: str
    label: str
    description: str
    action: Callable
    submenu: Optional[MenuType] = None


@dataclass
class UserInput:
    """ユーザー入力"""
    value: str
    is_valid: bool = True
    error_message: Optional[str] = None


class InteractiveSession:
    """インタラクティブセッション管理"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.formatter = OutputFormatter()
        self.table_formatter = TableFormatter()
        self.progress_formatter = ProgressFormatter()
        
        self.current_menu = MenuType.MAIN
        self.session_data: Dict[str, Any] = {}
        self.command_history: List[str] = []
        
        # セッション開始時刻
        self.start_time = time.time()
    
    def get_user_input(self, prompt: str, validation_func: Optional[Callable[[str], bool]] = None) -> UserInput:
        """ユーザー入力を取得"""
        try:
            while True:
                user_input = input(f"{prompt}: ").strip()
                self.command_history.append(user_input)
                
                if validation_func:
                    if validation_func(user_input):
                        return UserInput(user_input)
                    else:
                        self.formatter.warning("無効な入力です。再度入力してください。")
                        continue
                
                return UserInput(user_input)
        
        except (EOFError, KeyboardInterrupt):
            return UserInput("", is_valid=False, error_message="入力が中断されました")
    
    def get_menu_choice(self, options: List[MenuOption]) -> Optional[MenuOption]:
        """メニュー選択を取得"""
        print("\n" + "="*50)
        print("利用可能なオプション:")
        print("-"*50)
        
        for option in options:
            print(f"  {option.key}: {option.label}")
            if option.description:
                print(f"      {option.description}")
        
        print("\n  q: 戻る/終了")
        print("="*50)
        
        user_input = self.get_user_input("選択")
        
        if not user_input.is_valid:
            return None
        
        if user_input.value.lower() == 'q':
            return None
        
        # 選択されたオプションを検索
        for option in options:
            if option.key == user_input.value:
                return option
        
        self.formatter.warning("無効な選択です")
        return self.get_menu_choice(options)
    
    def confirm_action(self, message: str) -> bool:
        """アクション確認"""
        user_input = self.get_user_input(f"{message} (y/n)", 
                                       lambda x: x.lower() in ['y', 'n', 'yes', 'no'])
        
        if not user_input.is_valid:
            return False
        
        return user_input.value.lower() in ['y', 'yes']
    
    def display_data(self, data: Dict[str, Any], title: str = "データ"):
        """データ表示"""
        print(f"\n{title}:")
        print("-" * len(title))
        self.formatter.output_data(data)
    
    def display_table(self, data: List[Dict[str, Any]], title: str = "テーブル"):
        """テーブル表示"""
        if not data:
            self.formatter.info("表示するデータがありません")
            return
        
        print(f"\n{title}:")
        print("-" * len(title))
        formatted_table = self.table_formatter.format_data(data)
        print(formatted_table)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """セッション概要を取得"""
        duration = time.time() - self.start_time
        
        return {
            "session_duration": f"{duration:.1f}秒",
            "commands_executed": len(self.command_history),
            "current_menu": self.current_menu.value,
            "session_data_keys": list(self.session_data.keys())
        }


class InteractiveMode:
    """メインインタラクティブモードクラス"""
    
    def __init__(self):
        self.session = InteractiveSession()
        self.formatter = OutputFormatter()
        
        # システム初期化
        self.diagnostics = SystemDiagnostics()
        self.improvement_engine = None  # 必要時に初期化
        
        # メニュー定義
        self.menus = self._setup_menus()
    
    def _setup_menus(self) -> Dict[MenuType, List[MenuOption]]:
        """メニューを設定"""
        return {
            MenuType.MAIN: [
                MenuOption("1", "システム診断", "システムの健康状態を確認", self._handle_diagnostics_menu),
                MenuOption("2", "改善提案", "システム改善案を生成・実行", self._handle_improvement_menu),
                MenuOption("3", "設定管理", "システム設定の確認・変更", self._handle_config_menu),
                MenuOption("4", "システム情報", "システム状態・情報表示", self._handle_system_menu),
                MenuOption("5", "ヘルプ", "使用方法とヒント", self._handle_help)
            ],
            
            MenuType.DIAGNOSTICS: [
                MenuOption("1", "クイック診断", "基本的なパフォーマンス診断", self._run_quick_diagnosis),
                MenuOption("2", "完全診断", "すべてのコンポーネントを診断", self._run_full_diagnosis),
                MenuOption("3", "コンポーネント診断", "特定コンポーネントのみ診断", self._run_component_diagnosis),
                MenuOption("4", "診断履歴", "過去の診断結果表示", self._show_diagnosis_history),
                MenuOption("5", "ヘルス概要", "システム健康状態概要", self._show_health_summary)
            ],
            
            MenuType.IMPROVEMENT: [
                MenuOption("1", "改善計画生成", "新しい改善計画を生成", self._generate_improvement_plan),
                MenuOption("2", "計画実行", "既存の改善計画を実行", self._execute_improvement_plan),
                MenuOption("3", "改善履歴", "過去の改善履歴表示", self._show_improvement_history),
                MenuOption("4", "ドライラン", "改善のシミュレーション実行", self._run_dry_run),
                MenuOption("5", "設定調整", "改善エンジン設定の調整", self._adjust_improvement_settings)
            ],
            
            MenuType.CONFIG: [
                MenuOption("1", "設定表示", "現在の設定を表示", self._show_config),
                MenuOption("2", "設定変更", "設定値を変更", self._modify_config),
                MenuOption("3", "プロファイル", "設定プロファイル管理", self._manage_profiles),
                MenuOption("4", "設定リセット", "設定をデフォルトに戻す", self._reset_config),
                MenuOption("5", "設定エクスポート", "設定をファイルに保存", self._export_config)
            ],
            
            MenuType.SYSTEM: [
                MenuOption("1", "システム状態", "現在のシステム状態", self._show_system_status),
                MenuOption("2", "リソース使用量", "CPU・メモリ使用状況", self._show_resource_usage),
                MenuOption("3", "ログ表示", "システムログ表示", self._show_logs),
                MenuOption("4", "統計情報", "システム統計・メトリクス", self._show_statistics),
                MenuOption("5", "システム情報", "バージョン・環境情報", self._show_system_info)
            ]
        }
    
    def start(self):
        """インタラクティブモード開始"""
        self._show_welcome()
        
        try:
            while True:
                if self.session.current_menu == MenuType.MAIN:
                    if not self._handle_main_menu():
                        break
                else:
                    if not self._handle_submenu():
                        self.session.current_menu = MenuType.MAIN
        
        except KeyboardInterrupt:
            self.formatter.warning("\nセッションが中断されました")
        
        finally:
            self._show_goodbye()
    
    def _show_welcome(self):
        """ウェルカムメッセージ"""
        print("\n" + "="*60)
        print("🤖 AIDE インタラクティブモード")
        print("="*60)
        print("AIドリブン開発環境へようこそ！")
        print("システム診断、改善提案、設定管理が可能です。")
        print("'q' でメニューを戻る、Ctrl+C で終了できます。")
        print("="*60)
    
    def _show_goodbye(self):
        """終了メッセージ"""
        summary = self.session.get_session_summary()
        
        print("\n" + "="*60)
        print("🙏 ありがとうございました！")
        print("="*60)
        print(f"セッション時間: {summary['session_duration']}")
        print(f"実行コマンド数: {summary['commands_executed']}")
        print("="*60)
    
    def _handle_main_menu(self) -> bool:
        """メインメニュー処理"""
        options = self.menus[MenuType.MAIN]
        choice = self.session.get_menu_choice(options)
        
        if choice is None:
            return False  # 終了
        
        try:
            choice.action()
            return True
        except Exception as e:
            self.formatter.error(f"エラーが発生しました: {str(e)}")
            return True
    
    def _handle_submenu(self) -> bool:
        """サブメニュー処理"""
        options = self.menus[self.session.current_menu]
        choice = self.session.get_menu_choice(options)
        
        if choice is None:
            return False  # メインメニューに戻る
        
        try:
            choice.action()
            return True
        except Exception as e:
            self.formatter.error(f"エラーが発生しました: {str(e)}")
            return True
    
    # メニューハンドラー
    def _handle_diagnostics_menu(self):
        """診断メニューへ移行"""
        self.session.current_menu = MenuType.DIAGNOSTICS
        self.formatter.info("診断メニューに移動しました")
    
    def _handle_improvement_menu(self):
        """改善メニューへ移行"""
        self.session.current_menu = MenuType.IMPROVEMENT
        self.formatter.info("改善メニューに移動しました")
    
    def _handle_config_menu(self):
        """設定メニューへ移行"""
        self.session.current_menu = MenuType.CONFIG
        self.formatter.info("設定メニューに移動しました")
    
    def _handle_system_menu(self):
        """システムメニューへ移行"""
        self.session.current_menu = MenuType.SYSTEM
        self.formatter.info("システムメニューに移動しました")
    
    def _handle_help(self):
        """ヘルプ表示"""
        help_text = """
🔍 AIDE インタラクティブモード ヘルプ

【基本操作】
- 数字を入力してメニューを選択
- 'q' で前のメニューに戻る
- Ctrl+C で終了

【主な機能】
1. システム診断
   - パフォーマンス、コード品質、学習効率を分析
   - 問題の特定と改善提案

2. 改善提案・実行
   - AI による改善機会の特定
   - 自動実装とテスト
   - 安全性チェック

3. 設定管理
   - システム設定の表示・変更
   - プロファイル切り替え
   - 設定のエクスポート・インポート

4. システム情報
   - リアルタイムステータス
   - リソース使用量
   - ログとメトリクス

【ヒント】
- 初回利用時は「クイック診断」から開始することをお勧めします
- 改善実行前には必ず「ドライラン」で確認してください
- 設定変更後は「システム状態」で正常性を確認してください
"""
        print(help_text)
    
    # 診断機能
    def _run_quick_diagnosis(self):
        """クイック診断"""
        self.formatter.info("クイック診断を開始します...")
        
        self.session.progress_formatter.show_progress({
            "current": 0,
            "total": 1,
            "message": "パフォーマンス診断中..."
        })
        
        try:
            results = self.diagnostics.modules['performance'].diagnose()
            
            self.session.progress_formatter.finish_progress("診断完了")
            
            # 結果表示
            diagnosis_data = [
                {
                    "メトリクス": result.metric_name,
                    "値": result.value,
                    "ステータス": result.status,
                    "推奨事項": ", ".join(result.recommendations) if result.recommendations else "なし"
                }
                for result in results
            ]
            
            self.session.display_table(diagnosis_data, "クイック診断結果")
            
            # セッションデータに保存
            self.session.session_data['last_quick_diagnosis'] = diagnosis_data
            
        except Exception as e:
            self.formatter.error(f"診断エラー: {str(e)}")
    
    def _run_full_diagnosis(self):
        """完全診断"""
        if not self.session.confirm_action("完全診断を実行しますか？（時間がかかる場合があります）"):
            return
        
        self.formatter.info("完全診断を開始します...")
        
        try:
            total_modules = len(self.diagnostics.modules)
            
            for i, (module_name, module) in enumerate(self.diagnostics.modules.items()):
                self.session.progress_formatter.show_progress({
                    "current": i + 1,
                    "total": total_modules,
                    "message": f"{module_name} 診断中..."
                })
                
                time.sleep(0.5)  # 視覚的な遅延
            
            results = self.diagnostics.run_full_diagnosis()
            
            self.session.progress_formatter.finish_progress("完全診断完了")
            
            # 結果表示
            for component, component_results in results.items():
                diagnosis_data = [
                    {
                        "メトリクス": result.metric_name,
                        "値": result.value,
                        "ステータス": result.status,
                        "推奨事項": ", ".join(result.recommendations) if result.recommendations else "なし"
                    }
                    for result in component_results
                ]
                
                self.session.display_table(diagnosis_data, f"{component} 診断結果")
            
            # ヘルス概要
            health_summary = self.diagnostics.get_system_health_summary()
            self.session.display_data(health_summary, "システムヘルス概要")
            
        except Exception as e:
            self.formatter.error(f"完全診断エラー: {str(e)}")
    
    def _run_component_diagnosis(self):
        """コンポーネント診断"""
        components = list(self.diagnostics.modules.keys())
        
        print("診断するコンポーネントを選択してください:")
        for i, component in enumerate(components, 1):
            print(f"  {i}: {component}")
        
        user_input = self.session.get_user_input("コンポーネント番号")
        
        if not user_input.is_valid:
            return
        
        try:
            component_index = int(user_input.value) - 1
            if 0 <= component_index < len(components):
                component_name = components[component_index]
                module = self.diagnostics.modules[component_name]
                
                self.formatter.info(f"{component_name} 診断を開始します...")
                
                results = module.diagnose()
                
                diagnosis_data = [
                    {
                        "メトリクス": result.metric_name,
                        "値": result.value,
                        "ステータス": result.status,
                        "推奨事項": ", ".join(result.recommendations) if result.recommendations else "なし"
                    }
                    for result in results
                ]
                
                self.session.display_table(diagnosis_data, f"{component_name} 診断結果")
            else:
                self.formatter.warning("無効なコンポーネント番号です")
        
        except ValueError:
            self.formatter.warning("数字を入力してください")
        except Exception as e:
            self.formatter.error(f"コンポーネント診断エラー: {str(e)}")
    
    def _show_diagnosis_history(self):
        """診断履歴表示"""
        self.formatter.info("診断履歴機能は実装中です")
    
    def _show_health_summary(self):
        """ヘルス概要表示"""
        try:
            health_summary = self.diagnostics.get_system_health_summary()
            self.session.display_data(health_summary, "システムヘルス概要")
        except Exception as e:
            self.formatter.error(f"ヘルス概要取得エラー: {str(e)}")
    
    # 改善機能（実装例）
    def _generate_improvement_plan(self):
        """改善計画生成"""
        self.formatter.info("改善計画生成機能は実装中です")
    
    def _execute_improvement_plan(self):
        """改善計画実行"""
        self.formatter.info("改善計画実行機能は実装中です")
    
    def _show_improvement_history(self):
        """改善履歴表示"""
        self.formatter.info("改善履歴機能は実装中です")
    
    def _run_dry_run(self):
        """ドライラン実行"""
        self.formatter.info("ドライラン機能は実装中です")
    
    def _adjust_improvement_settings(self):
        """改善設定調整"""
        self.formatter.info("改善設定調整機能は実装中です")
    
    # 設定機能
    def _show_config(self):
        """設定表示"""
        summary = self.session.config_manager.get_config_summary()
        self.session.display_data(summary, "現在の設定")
    
    def _modify_config(self):
        """設定変更"""
        self.formatter.info("設定変更機能は実装中です")
    
    def _manage_profiles(self):
        """プロファイル管理"""
        self.formatter.info("プロファイル管理機能は実装中です")
    
    def _reset_config(self):
        """設定リセット"""
        self.formatter.info("設定リセット機能は実装中です")
    
    def _export_config(self):
        """設定エクスポート"""
        self.formatter.info("設定エクスポート機能は実装中です")
    
    # システム機能
    def _show_system_status(self):
        """システム状態表示"""
        status_data = {
            "バージョン": self.session.config_manager.get("system.version"),
            "環境": self.session.config_manager.get("system.environment"),
            "デバッグモード": self.session.config_manager.get("system.debug_mode"),
            "プロファイル": self.session.config_manager.get_profile().value,
            "稼働時間": f"{time.time() - self.session.start_time:.1f}秒"
        }
        
        self.session.display_data(status_data, "システム状態")
    
    def _show_resource_usage(self):
        """リソース使用量表示"""
        self.formatter.info("リソース使用量機能は実装中です")
    
    def _show_logs(self):
        """ログ表示"""
        self.formatter.info("ログ表示機能は実装中です")
    
    def _show_statistics(self):
        """統計情報表示"""
        self.formatter.info("統計情報機能は実装中です")
    
    def _show_system_info(self):
        """システム情報表示"""
        info_data = {
            "Python バージョン": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "プラットフォーム": sys.platform,
            "AIDE バージョン": self.session.config_manager.get("system.version"),
            "設定ファイル": str(self.session.config_manager.config_dir),
            "機能フラグ": {
                "Claude統合": self.session.config_manager.get("claude_integration.enabled"),
                "RAGシステム": self.session.config_manager.get("rag_system.enabled")
            }
        }
        
        self.session.display_data(info_data, "システム情報")