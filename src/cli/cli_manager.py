"""
AIDE CLI マネージャー

コマンドライン操作の統合管理
"""

import sys
import argparse
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import traceback
from pathlib import Path

from ..config import get_config_manager, ConfigManager
from .formatters import OutputFormatter, TableFormatter, JSONFormatter


class CLIError(Exception):
    """CLI関連エラー"""
    pass


class CommandType(Enum):
    """コマンドタイプ"""
    SYSTEM = "system"
    DIAGNOSTICS = "diagnostics"
    IMPROVEMENT = "improvement"
    CONFIG = "config"
    INTERACTIVE = "interactive"
    REMOTE = "remote"


@dataclass
class CLIArgument:
    """CLI引数定義"""
    name: str
    short_name: Optional[str] = None
    help_text: str = ""
    required: bool = False
    default: Any = None
    type: type = str
    choices: Optional[List[str]] = None
    action: str = "store"


@dataclass
class CommandResult:
    """コマンド実行結果"""
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    exit_code: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "exit_code": self.exit_code
        }


class CLICommand(ABC):
    """CLI コマンド基底クラス"""
    
    def __init__(self, name: str, description: str, command_type: CommandType):
        self.name = name
        self.description = description
        self.command_type = command_type
        self.arguments: List[CLIArgument] = []
        self.subcommands: Dict[str, 'CLICommand'] = {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    def add_argument(self, argument: CLIArgument):
        """引数を追加"""
        self.arguments.append(argument)
    
    def add_subcommand(self, command: 'CLICommand'):
        """サブコマンドを追加"""
        self.subcommands[command.name] = command
    
    @abstractmethod
    def execute(self, args: argparse.Namespace) -> CommandResult:
        """コマンドを実行"""
        pass
    
    def setup_parser(self, parser: argparse.ArgumentParser):
        """パーサーを設定"""
        for arg in self.arguments:
            kwargs = {
                'help': arg.help_text,
                'default': arg.default,
                'type': arg.type,
                'action': arg.action
            }
            
            if arg.required:
                kwargs['required'] = True
            
            if arg.choices:
                kwargs['choices'] = arg.choices
            
            # 位置引数 vs オプション引数
            if arg.name.startswith('-'):
                if arg.short_name:
                    parser.add_argument(arg.short_name, arg.name, **kwargs)
                else:
                    parser.add_argument(arg.name, **kwargs)
            else:
                kwargs.pop('required', None)  # 位置引数には不要
                parser.add_argument(arg.name, **kwargs)
        
        # サブコマンド設定
        if self.subcommands:
            subparsers = parser.add_subparsers(dest='subcommand', help='利用可能なサブコマンド')
            for subcmd in self.subcommands.values():
                subparser = subparsers.add_parser(subcmd.name, help=subcmd.description)
                subcmd.setup_parser(subparser)


class CLIManager:
    """メインCLI管理クラス"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or get_config_manager()
        self.commands: Dict[str, CLICommand] = {}
        self.formatter = OutputFormatter()
        self.logger = logging.getLogger(__name__)
        
        # ログ設定
        self._setup_logging()
    
    def _setup_logging(self):
        """ログ設定"""
        log_level = self.config_manager.get("system.log_level", "info").upper()
        debug_mode = self.config_manager.get("system.debug_mode", False)
        
        if debug_mode:
            log_level = "DEBUG"
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def register_command(self, command: CLICommand):
        """コマンドを登録"""
        self.commands[command.name] = command
        self.logger.debug(f"コマンド登録: {command.name}")
    
    def create_parser(self) -> argparse.ArgumentParser:
        """メインパーサーを作成"""
        parser = argparse.ArgumentParser(
            prog='aide',
            description='AIDE - AI-Driven Development Environment',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
使用例:
  aide diagnose --full          # 完全診断実行
  aide improve --plan-only      # 改善計画のみ生成
  aide config show              # 設定表示
  aide interactive              # インタラクティブモード
  aide --help                   # ヘルプ表示
            """
        )
        
        # グローバル引数
        parser.add_argument(
            '--version', '-v',
            action='version',
            version=f"AIDE {self.config_manager.get('system.version', '3.2.0')}"
        )
        
        parser.add_argument(
            '--config-file', '-c',
            help='設定ファイルパス',
            type=str,
            metavar='FILE'
        )
        
        parser.add_argument(
            '--profile', '-p',
            help='設定プロファイル',
            choices=['development', 'production', 'testing', 'safe_mode'],
            default='development'
        )
        
        parser.add_argument(
            '--verbose',
            help='詳細出力',
            action='store_true'
        )
        
        parser.add_argument(
            '--quiet', '-q',
            help='静粛モード',
            action='store_true'
        )
        
        parser.add_argument(
            '--output-format',
            help='出力形式',
            choices=['text', 'json', 'yaml'],
            default='text'
        )
        
        # サブコマンド
        if self.commands:
            subparsers = parser.add_subparsers(
                dest='command',
                help='利用可能なコマンド',
                metavar='COMMAND'
            )
            
            for command in self.commands.values():
                subparser = subparsers.add_parser(
                    command.name,
                    help=command.description,
                    description=command.description
                )
                command.setup_parser(subparser)
        
        return parser
    
    def run(self, argv: Optional[List[str]] = None) -> int:
        """CLI実行"""
        try:
            parser = self.create_parser()
            args = parser.parse_args(argv)
            
            # グローバル設定適用
            if args.verbose:
                self.config_manager.set("system.log_level", "debug")
                self._setup_logging()
            
            if args.quiet:
                self.config_manager.set("system.log_level", "error")
                self._setup_logging()
            
            # 出力フォーマッター設定
            if args.output_format == 'json':
                self.formatter = JSONFormatter()
            elif args.output_format == 'yaml':
                self.formatter = OutputFormatter()  # YAML対応は後で追加
            
            # コマンド実行
            if not hasattr(args, 'command') or args.command is None:
                parser.print_help()
                return 0
            
            if args.command not in self.commands:
                self.formatter.error(f"不明なコマンド: {args.command}")
                return 1
            
            command = self.commands[args.command]
            result = self._execute_command(command, args)
            
            # 結果出力
            self._output_result(result)
            
            return result.exit_code
        
        except KeyboardInterrupt:
            self.formatter.warning("操作が中断されました")
            return 130
        
        except Exception as e:
            self.logger.error(f"予期しないエラー: {str(e)}")
            if self.config_manager.get("system.debug_mode", False):
                self.formatter.error(f"エラー詳細:\n{traceback.format_exc()}")
            else:
                self.formatter.error(f"エラーが発生しました: {str(e)}")
            return 1
    
    def _execute_command(self, command: CLICommand, args: argparse.Namespace) -> CommandResult:
        """コマンド実行"""
        try:
            # サブコマンド処理
            if hasattr(args, 'subcommand') and args.subcommand:
                if args.subcommand in command.subcommands:
                    subcommand = command.subcommands[args.subcommand]
                    return self._execute_command(subcommand, args)
                else:
                    return CommandResult(
                        success=False,
                        message=f"不明なサブコマンド: {args.subcommand}",
                        exit_code=1
                    )
            
            # メインコマンド実行
            self.logger.info(f"コマンド実行: {command.name}")
            result = command.execute(args)
            
            if result.success:
                self.logger.info(f"コマンド完了: {command.name}")
            else:
                self.logger.error(f"コマンド失敗: {command.name} - {result.message}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"コマンド実行エラー {command.name}: {str(e)}")
            return CommandResult(
                success=False,
                message=f"コマンド実行中にエラーが発生: {str(e)}",
                exit_code=1
            )
    
    def _output_result(self, result: CommandResult):
        """結果出力"""
        if result.success:
            if result.message:
                self.formatter.success(result.message)
            
            if result.data:
                self.formatter.output_data(result.data)
        else:
            self.formatter.error(result.message)
    
    def get_command_help(self, command_name: str) -> str:
        """コマンドヘルプ取得"""
        if command_name not in self.commands:
            return f"コマンド '{command_name}' が見つかりません"
        
        command = self.commands[command_name]
        
        help_text = f"""
コマンド: {command.name}
説明: {command.description}
タイプ: {command.command_type.value}

引数:
"""
        
        for arg in command.arguments:
            required = " [必須]" if arg.required else ""
            help_text += f"  {arg.name}: {arg.help_text}{required}\n"
        
        if command.subcommands:
            help_text += "\nサブコマンド:\n"
            for subcmd in command.subcommands.values():
                help_text += f"  {subcmd.name}: {subcmd.description}\n"
        
        return help_text
    
    def list_commands(self) -> Dict[str, str]:
        """利用可能なコマンド一覧"""
        return {
            name: command.description 
            for name, command in self.commands.items()
        }


# 便利関数
def create_cli_manager() -> CLIManager:
    """CLI管理インスタンスを作成"""
    return CLIManager()


def run_cli(argv: Optional[List[str]] = None) -> int:
    """CLIを実行"""
    cli_manager = create_cli_manager()
    
    # 標準コマンドを登録
    from .commands import (
        DiagnosticsCommand,
        ImprovementCommand, 
        ConfigCommand,
        SystemCommand,
        InteractiveCommand,
        RemoteCommand
    )
    
    cli_manager.register_command(DiagnosticsCommand())
    cli_manager.register_command(ImprovementCommand())
    cli_manager.register_command(ConfigCommand())
    cli_manager.register_command(SystemCommand())
    cli_manager.register_command(InteractiveCommand())
    
    # リモートコマンドは可用性を確認してから登録
    try:
        cli_manager.register_command(RemoteCommand())
    except ImportError:
        # リモート機能が利用できない場合はスキップ
        pass
    
    return cli_manager.run(argv)