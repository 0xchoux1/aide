"""
AIDE CLI コマンド実装

各種コマンドの具体的な実装
"""

import argparse
import sys
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import time
import asyncio

from .cli_manager import CLICommand, CommandResult, CLIArgument, CommandType
from .formatters import ProgressFormatter, TableFormatter, format_duration
from ..config import get_config_manager, ConfigProfile
from ..self_improvement.diagnostics import SystemDiagnostics
from ..self_improvement.improvement_engine import ImprovementEngine
from ..self_improvement.autonomous_implementation import AutonomousImplementation
from ..self_improvement.quality_assurance import QualityAssurance


class DiagnosticsCommand(CLICommand):
    """診断コマンド"""
    
    def __init__(self):
        super().__init__(
            name="diagnose",
            description="システム診断を実行",
            command_type=CommandType.DIAGNOSTICS
        )
        
        self.add_argument(CLIArgument(
            name="--full",
            help="完全診断を実行",
            action="store_true"
        ))
        
        self.add_argument(CLIArgument(
            name="--component",
            help="特定コンポーネントのみ診断",
            choices=["performance", "code_quality", "learning"],
            type=str
        ))
        
        self.add_argument(CLIArgument(
            name="--export",
            help="結果をファイルに出力",
            type=str,
            metavar="FILE"
        ))
        
        self.add_argument(CLIArgument(
            name="--format",
            help="出力形式",
            choices=["text", "json", "table"],
            default="text"
        ))
    
    def execute(self, args: argparse.Namespace) -> CommandResult:
        """診断実行"""
        try:
            config_manager = get_config_manager()
            
            # RAGシステム設定
            rag_system = None
            if config_manager.get("rag_system.enabled", True):
                # RAGシステムの初期化は実際の実装に依存
                pass
            
            # 診断システム初期化
            diagnostics = SystemDiagnostics(rag_system)
            
            # プログレス表示
            progress_formatter = ProgressFormatter()
            
            if args.component:
                # 特定コンポーネント診断
                progress_formatter.show_progress({
                    "current": 0,
                    "total": 1, 
                    "message": f"{args.component}診断開始"
                })
                
                if args.component in diagnostics.modules:
                    module = diagnostics.modules[args.component]
                    results = {args.component: module.diagnose()}
                else:
                    return CommandResult(
                        success=False,
                        message=f"不明なコンポーネント: {args.component}",
                        exit_code=1
                    )
                
                progress_formatter.finish_progress("診断完了")
            
            elif args.full:
                # 完全診断
                progress_formatter.show_progress({
                    "current": 0,
                    "total": 3,
                    "message": "完全診断開始"
                })
                
                results = diagnostics.run_full_diagnosis()
                
                progress_formatter.finish_progress("完全診断完了")
            
            else:
                # 基本診断（パフォーマンスのみ）
                progress_formatter.show_progress({
                    "current": 0,
                    "total": 1,
                    "message": "基本診断開始"
                })
                
                perf_results = diagnostics.modules['performance'].diagnose()
                results = {'performance': perf_results}
                
                progress_formatter.finish_progress("基本診断完了")
            
            # 結果フォーマット
            output_data = self._format_diagnosis_results(results, args.format)
            
            # ファイル出力
            if args.export:
                self._export_results(results, args.export)
            
            return CommandResult(
                success=True,
                message="診断が正常に完了しました",
                data=output_data
            )
        
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"診断エラー: {str(e)}",
                exit_code=1
            )
    
    def _format_diagnosis_results(self, results: Dict[str, List], format_type: str) -> Dict[str, Any]:
        """診断結果をフォーマット"""
        if format_type == "table":
            table_data = []
            for component, component_results in results.items():
                for result in component_results:
                    table_data.append({
                        "コンポーネント": component,
                        "メトリクス": result.metric_name,
                        "値": result.value,
                        "ステータス": result.status,
                        "タイムスタンプ": result.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    })
            return {"table_data": table_data}
        
        else:
            # 標準形式
            formatted = {}
            for component, component_results in results.items():
                formatted[component] = [
                    {
                        "metric_name": result.metric_name,
                        "value": result.value,
                        "status": result.status,
                        "target_value": result.target_value,
                        "timestamp": result.timestamp.isoformat(),
                        "recommendations": result.recommendations
                    }
                    for result in component_results
                ]
            return formatted
    
    def _export_results(self, results: Dict[str, List], file_path: str):
        """結果をファイルにエクスポート"""
        output_path = Path(file_path)
        
        export_data = {}
        for component, component_results in results.items():
            export_data[component] = [result.to_dict() for result in component_results]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)


class ImprovementCommand(CLICommand):
    """改善コマンド"""
    
    def __init__(self):
        super().__init__(
            name="improve",
            description="システム改善を実行",
            command_type=CommandType.IMPROVEMENT
        )
        
        self.add_argument(CLIArgument(
            name="--plan-only",
            help="改善計画のみ生成（実装しない）",
            action="store_true"
        ))
        
        self.add_argument(CLIArgument(
            name="--dry-run",
            help="ドライラン実行",
            action="store_true"
        ))
        
        self.add_argument(CLIArgument(
            name="--timeframe",
            help="改善期間（週数）",
            type=int,
            default=4
        ))
        
        self.add_argument(CLIArgument(
            name="--max-opportunities",
            help="最大改善機会数",
            type=int,
            default=10
        ))
        
        self.add_argument(CLIArgument(
            name="--auto-approve",
            help="低リスク改善を自動承認",
            action="store_true"
        ))
    
    def execute(self, args: argparse.Namespace) -> CommandResult:
        """改善実行"""
        try:
            config_manager = get_config_manager()
            
            # Claude Clientの設定
            claude_client = None  # 実際の実装に依存
            
            # 診断システム初期化
            diagnostics = SystemDiagnostics()
            
            # 改善エンジン初期化
            improvement_engine = ImprovementEngine(diagnostics, claude_client)
            
            # プログレス表示
            progress_formatter = ProgressFormatter()
            
            # 1. 診断実行
            progress_formatter.show_progress({
                "current": 1,
                "total": 4,
                "message": "システム診断実行中..."
            })
            
            # 2. 改善計画生成
            progress_formatter.show_progress({
                "current": 2,
                "total": 4,
                "message": "改善計画生成中..."
            })
            
            roadmap = improvement_engine.generate_improvement_plan(
                timeframe_weeks=args.timeframe
            )
            
            if args.plan_only:
                progress_formatter.finish_progress("改善計画生成完了")
                
                return CommandResult(
                    success=True,
                    message="改善計画が正常に生成されました",
                    data={
                        "roadmap_id": roadmap.id,
                        "title": roadmap.title,
                        "total_opportunities": len(roadmap.opportunities),
                        "estimated_time": roadmap.total_estimated_time,
                        "phases": len(roadmap.phases),
                        "opportunities": [
                            {
                                "id": opp.id,
                                "title": opp.title,
                                "type": opp.improvement_type.value,
                                "priority": opp.priority.value,
                                "impact_score": opp.impact_score,
                                "estimated_hours": opp.estimated_time_hours
                            }
                            for opp in roadmap.opportunities[:args.max_opportunities]
                        ]
                    }
                )
            
            # 3. 自律実装準備
            progress_formatter.show_progress({
                "current": 3,
                "total": 4,
                "message": "自律実装準備中..."
            })
            
            autonomous_impl = AutonomousImplementation(claude_client)
            
            # 4. 改善実装
            progress_formatter.show_progress({
                "current": 4,
                "total": 4,
                "message": "改善実装中..."
            })
            
            implementation_results = autonomous_impl.implement_roadmap(
                roadmap, 
                dry_run=args.dry_run
            )
            
            progress_formatter.finish_progress("改善実装完了")
            
            # 結果集計
            successful_implementations = sum(1 for result in implementation_results if result.success)
            total_implementations = len(implementation_results)
            
            return CommandResult(
                success=True,
                message=f"改善処理が完了しました ({successful_implementations}/{total_implementations} 成功)",
                data={
                    "roadmap_id": roadmap.id,
                    "total_implementations": total_implementations,
                    "successful_implementations": successful_implementations,
                    "success_rate": successful_implementations / total_implementations * 100 if total_implementations > 0 else 0,
                    "dry_run": args.dry_run,
                    "implementation_results": [
                        {
                            "opportunity_id": result.opportunity_id,
                            "success": result.success,
                            "files_modified": len(result.files_modified),
                            "execution_time": result.execution_time,
                            "error_message": result.error_message
                        }
                        for result in implementation_results
                    ]
                }
            )
        
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"改善エラー: {str(e)}",
                exit_code=1
            )


class ConfigCommand(CLICommand):
    """設定コマンド"""
    
    def __init__(self):
        super().__init__(
            name="config",
            description="設定管理",
            command_type=CommandType.CONFIG
        )
        
        # show サブコマンド
        show_cmd = CLICommand("show", "設定表示", CommandType.CONFIG)
        show_cmd.add_argument(CLIArgument(
            name="--key",
            help="特定キーのみ表示",
            type=str
        ))
        self.add_subcommand(show_cmd)
        
        # set サブコマンド  
        set_cmd = CLICommand("set", "設定変更", CommandType.CONFIG)
        set_cmd.add_argument(CLIArgument(
            name="key",
            help="設定キー"
        ))
        set_cmd.add_argument(CLIArgument(
            name="value",
            help="設定値"
        ))
        self.add_subcommand(set_cmd)
        
        # profile サブコマンド
        profile_cmd = CLICommand("profile", "プロファイル管理", CommandType.CONFIG)
        profile_cmd.add_argument(CLIArgument(
            name="--list",
            help="利用可能なプロファイル一覧",
            action="store_true"
        ))
        profile_cmd.add_argument(CLIArgument(
            name="--switch",
            help="プロファイル切り替え",
            choices=["development", "production", "testing", "safe_mode"]
        ))
        self.add_subcommand(profile_cmd)
    
    def execute(self, args: argparse.Namespace) -> CommandResult:
        """設定コマンド実行"""
        if not hasattr(args, 'subcommand') or not args.subcommand:
            return CommandResult(
                success=False,
                message="サブコマンドが必要です: show, set, profile",
                exit_code=1
            )
        
        config_manager = get_config_manager()
        
        try:
            if args.subcommand == "show":
                return self._handle_show(config_manager, args)
            elif args.subcommand == "set":
                return self._handle_set(config_manager, args)
            elif args.subcommand == "profile":
                return self._handle_profile(config_manager, args)
            else:
                return CommandResult(
                    success=False,
                    message=f"不明なサブコマンド: {args.subcommand}",
                    exit_code=1
                )
        
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"設定エラー: {str(e)}",
                exit_code=1
            )
    
    def _handle_show(self, config_manager, args) -> CommandResult:
        """設定表示処理"""
        if args.key:
            value = config_manager.get(args.key)
            if value is None:
                return CommandResult(
                    success=False,
                    message=f"設定キーが見つかりません: {args.key}",
                    exit_code=1
                )
            
            return CommandResult(
                success=True,
                data={args.key: value}
            )
        else:
            summary = config_manager.get_config_summary()
            return CommandResult(
                success=True,
                message="現在の設定",
                data=summary
            )
    
    def _handle_set(self, config_manager, args) -> CommandResult:
        """設定変更処理"""
        # 値の型変換試行
        value = args.value
        
        # ブール値
        if value.lower() in ('true', 'false'):
            value = value.lower() == 'true'
        # 数値
        elif value.isdigit():
            value = int(value)
        elif '.' in value:
            try:
                value = float(value)
            except ValueError:
                pass
        
        success = config_manager.set(args.key, value)
        
        if success:
            return CommandResult(
                success=True,
                message=f"設定を更新しました: {args.key} = {value}"
            )
        else:
            return CommandResult(
                success=False,
                message=f"設定更新に失敗しました: {args.key}",
                exit_code=1
            )
    
    def _handle_profile(self, config_manager, args) -> CommandResult:
        """プロファイル処理"""
        if args.list:
            profiles = [profile.value for profile in ConfigProfile]
            current = config_manager.get_profile().value
            
            return CommandResult(
                success=True,
                message="利用可能なプロファイル",
                data={
                    "current_profile": current,
                    "available_profiles": profiles
                }
            )
        
        elif args.switch:
            try:
                new_profile = ConfigProfile(args.switch)
                config_manager.switch_profile(new_profile)
                
                return CommandResult(
                    success=True,
                    message=f"プロファイルを {args.switch} に切り替えました"
                )
            
            except ValueError:
                return CommandResult(
                    success=False,
                    message=f"無効なプロファイル: {args.switch}",
                    exit_code=1
                )
        
        else:
            current = config_manager.get_profile().value
            return CommandResult(
                success=True,
                message=f"現在のプロファイル: {current}"
            )


class SystemCommand(CLICommand):
    """システムコマンド"""
    
    def __init__(self):
        super().__init__(
            name="system",
            description="システム情報・制御",
            command_type=CommandType.SYSTEM
        )
        
        # status サブコマンド
        status_cmd = CLICommand("status", "システム状態表示", CommandType.SYSTEM)
        self.add_subcommand(status_cmd)
        
        # health サブコマンド
        health_cmd = CLICommand("health", "ヘルスチェック", CommandType.SYSTEM)
        self.add_subcommand(health_cmd)
        
        # info サブコマンド
        info_cmd = CLICommand("info", "システム情報", CommandType.SYSTEM)
        self.add_subcommand(info_cmd)
    
    def execute(self, args: argparse.Namespace) -> CommandResult:
        """システムコマンド実行"""
        if not hasattr(args, 'subcommand') or not args.subcommand:
            return self._handle_info()
        
        try:
            if args.subcommand == "status":
                return self._handle_status()
            elif args.subcommand == "health":
                return self._handle_health()
            elif args.subcommand == "info":
                return self._handle_info()
            else:
                return CommandResult(
                    success=False,
                    message=f"不明なサブコマンド: {args.subcommand}",
                    exit_code=1
                )
        
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"システムエラー: {str(e)}",
                exit_code=1
            )
    
    def _handle_status(self) -> CommandResult:
        """システム状態処理"""
        config_manager = get_config_manager()
        
        status_data = {
            "version": config_manager.get("system.version"),
            "environment": config_manager.get("system.environment"),
            "debug_mode": config_manager.get("system.debug_mode"),
            "uptime": "実装予定",  # 実際の稼働時間計算
            "components": {
                "diagnostics": "active",
                "improvement_engine": "active", 
                "autonomous_implementation": "standby",
                "quality_assurance": "active"
            }
        }
        
        return CommandResult(
            success=True,
            message="システム状態",
            data=status_data
        )
    
    def _handle_health(self) -> CommandResult:
        """ヘルスチェック処理"""
        diagnostics = SystemDiagnostics()
        
        try:
            health_summary = diagnostics.get_system_health_summary()
            
            return CommandResult(
                success=True,
                message="システムヘルス",
                data=health_summary
            )
        
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"ヘルスチェック失敗: {str(e)}",
                exit_code=1
            )
    
    def _handle_info(self) -> CommandResult:
        """システム情報処理"""
        config_manager = get_config_manager()
        
        info_data = {
            "aide_version": config_manager.get("system.version"),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": sys.platform,
            "project_root": str(Path.cwd()),
            "config_profile": config_manager.get_profile().value,
            "features": {
                "claude_integration": config_manager.get("claude_integration.enabled"),
                "rag_system": config_manager.get("rag_system.enabled"),
                "auto_implementation": config_manager.get("features.auto_implementation", True)
            }
        }
        
        return CommandResult(
            success=True,
            message="システム情報",
            data=info_data
        )


class InteractiveCommand(CLICommand):
    """インタラクティブモードコマンド"""
    
    def __init__(self):
        super().__init__(
            name="interactive",
            description="インタラクティブモード開始",
            command_type=CommandType.INTERACTIVE
        )
    
    def execute(self, args: argparse.Namespace) -> CommandResult:
        """インタラクティブモード実行"""
        try:
            from .interactive import InteractiveMode
            
            interactive_mode = InteractiveMode()
            interactive_mode.start()
            
            return CommandResult(
                success=True,
                message="インタラクティブモードを終了しました"
            )
        
        except KeyboardInterrupt:
            return CommandResult(
                success=True,
                message="インタラクティブモードが中断されました"
            )
        
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"インタラクティブモードエラー: {str(e)}",
                exit_code=1
            )