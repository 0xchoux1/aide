"""
AIDE CLI インターフェース

コマンドライン操作とインタラクティブインターフェースを提供
"""

from .cli_manager import (
    CLIManager,
    CLICommand,
    CLIArgument,
    CLIError,
    CommandResult
)

from .commands import (
    DiagnosticsCommand,
    ImprovementCommand,
    ConfigCommand,
    SystemCommand,
    InteractiveCommand
)

from .interactive import (
    InteractiveMode,
    InteractiveSession,
    MenuOption,
    UserInput
)

from .formatters import (
    OutputFormatter,
    TableFormatter,
    JSONFormatter,
    ProgressFormatter
)

__all__ = [
    'CLIManager',
    'CLICommand',
    'CLIArgument', 
    'CLIError',
    'CommandResult',
    'DiagnosticsCommand',
    'ImprovementCommand',
    'ConfigCommand',
    'SystemCommand',
    'InteractiveCommand',
    'InteractiveMode',
    'InteractiveSession',
    'MenuOption',
    'UserInput',
    'OutputFormatter',
    'TableFormatter',
    'JSONFormatter',
    'ProgressFormatter'
]