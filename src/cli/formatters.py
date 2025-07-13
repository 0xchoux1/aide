"""
AIDE CLI 出力フォーマッター

様々な形式での出力を管理
"""

import sys
import json
import yaml
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import termcolor
from tabulate import tabulate


class OutputFormat(Enum):
    """出力形式"""
    TEXT = "text"
    JSON = "json"
    YAML = "yaml"
    TABLE = "table"


class MessageType(Enum):
    """メッセージタイプ"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


@dataclass
class ProgressInfo:
    """プログレス情報"""
    current: int
    total: int
    message: str
    percentage: Optional[float] = None
    
    def __post_init__(self):
        if self.percentage is None:
            self.percentage = (self.current / self.total * 100) if self.total > 0 else 0


class BaseFormatter(ABC):
    """フォーマッター基底クラス"""
    
    def __init__(self, colored: bool = True):
        self.colored = colored and sys.stdout.isatty()
    
    @abstractmethod
    def format_message(self, message: str, msg_type: MessageType) -> str:
        """メッセージをフォーマット"""
        pass
    
    @abstractmethod
    def format_data(self, data: Dict[str, Any]) -> str:
        """データをフォーマット"""
        pass
    
    def output(self, content: str):
        """出力"""
        print(content)
    
    def info(self, message: str):
        """情報メッセージ"""
        formatted = self.format_message(message, MessageType.INFO)
        self.output(formatted)
    
    def success(self, message: str):
        """成功メッセージ"""
        formatted = self.format_message(message, MessageType.SUCCESS)
        self.output(formatted)
    
    def warning(self, message: str):
        """警告メッセージ"""
        formatted = self.format_message(message, MessageType.WARNING)
        print(formatted, file=sys.stderr)
    
    def error(self, message: str):
        """エラーメッセージ"""
        formatted = self.format_message(message, MessageType.ERROR)
        print(formatted, file=sys.stderr)
    
    def debug(self, message: str):
        """デバッグメッセージ"""
        formatted = self.format_message(message, MessageType.DEBUG)
        self.output(formatted)
    
    def output_data(self, data: Dict[str, Any]):
        """データ出力"""
        formatted = self.format_data(data)
        self.output(formatted)


class OutputFormatter(BaseFormatter):
    """標準テキスト出力フォーマッター"""
    
    def __init__(self, colored: bool = True):
        super().__init__(colored)
        self.color_map = {
            MessageType.INFO: 'cyan',
            MessageType.SUCCESS: 'green',
            MessageType.WARNING: 'yellow',
            MessageType.ERROR: 'red',
            MessageType.DEBUG: 'magenta'
        }
    
    def format_message(self, message: str, msg_type: MessageType) -> str:
        """メッセージをフォーマット"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix_map = {
            MessageType.INFO: "ℹ️",
            MessageType.SUCCESS: "✅",
            MessageType.WARNING: "⚠️",
            MessageType.ERROR: "❌",
            MessageType.DEBUG: "🐛"
        }
        
        prefix = prefix_map.get(msg_type, "")
        formatted = f"[{timestamp}] {prefix} {message}"
        
        if self.colored:
            color = self.color_map.get(msg_type)
            if color:
                formatted = termcolor.colored(formatted, color)
        
        return formatted
    
    def format_data(self, data: Dict[str, Any]) -> str:
        """データをフォーマット"""
        return self._format_dict(data)
    
    def _format_dict(self, data: Dict[str, Any], indent: int = 0) -> str:
        """辞書を再帰的にフォーマット"""
        lines = []
        spaces = "  " * indent
        
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{spaces}{key}:")
                lines.append(self._format_dict(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{spaces}{key}:")
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        lines.append(f"{spaces}  [{i}]:")
                        lines.append(self._format_dict(item, indent + 2))
                    else:
                        lines.append(f"{spaces}  - {item}")
            else:
                lines.append(f"{spaces}{key}: {value}")
        
        return "\n".join(lines)


class JSONFormatter(BaseFormatter):
    """JSON出力フォーマッター"""
    
    def __init__(self, colored: bool = True, indent: int = 2):
        super().__init__(colored)
        self.indent = indent
    
    def format_message(self, message: str, msg_type: MessageType) -> str:
        """メッセージをJSONフォーマット"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "type": msg_type.value,
            "message": message
        }
        return json.dumps(data, indent=self.indent, ensure_ascii=False)
    
    def format_data(self, data: Dict[str, Any]) -> str:
        """データをJSONフォーマット"""
        return json.dumps(data, indent=self.indent, ensure_ascii=False, default=str)


class TableFormatter(BaseFormatter):
    """テーブル出力フォーマッター"""
    
    def __init__(self, colored: bool = True, table_format: str = "grid"):
        super().__init__(colored)
        self.table_format = table_format
    
    def format_message(self, message: str, msg_type: MessageType) -> str:
        """メッセージをフォーマット（通常のテキスト形式）"""
        output_formatter = OutputFormatter(self.colored)
        return output_formatter.format_message(message, msg_type)
    
    def format_data(self, data: Dict[str, Any]) -> str:
        """データをテーブルフォーマット"""
        if self._is_tabular_data(data):
            return self._format_as_table(data)
        else:
            # テーブル形式でない場合は通常フォーマット
            output_formatter = OutputFormatter(self.colored)
            return output_formatter.format_data(data)
    
    def _is_tabular_data(self, data: Dict[str, Any]) -> bool:
        """テーブル形式のデータか判定"""
        # リストの辞書、または辞書のリストの場合はテーブル形式
        if isinstance(data, list) and all(isinstance(item, dict) for item in data):
            return True
        
        if isinstance(data, dict):
            values = list(data.values())
            if values and isinstance(values[0], list) and all(isinstance(v, list) for v in values):
                return True
        
        return False
    
    def _format_as_table(self, data: Union[List[Dict], Dict[str, List]]) -> str:
        """テーブル形式でフォーマット"""
        if isinstance(data, list):
            # リストの辞書の場合
            if not data:
                return "データがありません"
            
            headers = list(data[0].keys())
            rows = [[str(item.get(header, "")) for header in headers] for item in data]
            
            return tabulate(
                rows,
                headers=headers,
                tablefmt=self.table_format,
                numalign="right",
                stralign="left"
            )
        
        elif isinstance(data, dict):
            # 辞書のリストの場合
            headers = list(data.keys())
            max_length = max(len(values) for values in data.values()) if data else 0
            
            rows = []
            for i in range(max_length):
                row = []
                for header in headers:
                    values = data[header]
                    value = values[i] if i < len(values) else ""
                    row.append(str(value))
                rows.append(row)
            
            return tabulate(
                rows,
                headers=headers,
                tablefmt=self.table_format,
                numalign="right",
                stralign="left"
            )
        
        return str(data)


class ProgressFormatter:
    """プログレスバーフォーマッター"""
    
    def __init__(self, width: int = 50, colored: bool = True):
        self.width = width
        self.colored = colored and sys.stdout.isatty()
    
    def format_progress(self, progress: ProgressInfo) -> str:
        """プログレスバーをフォーマット"""
        percentage = min(100, max(0, progress.percentage or 0))
        filled_width = int(self.width * percentage / 100)
        
        bar = "█" * filled_width + "░" * (self.width - filled_width)
        
        if self.colored:
            if percentage < 50:
                bar = termcolor.colored(bar, 'red')
            elif percentage < 80:
                bar = termcolor.colored(bar, 'yellow')
            else:
                bar = termcolor.colored(bar, 'green')
        
        return f"{bar} {percentage:6.1f}% ({progress.current}/{progress.total}) {progress.message}"
    
    def show_progress(self, progress: ProgressInfo):
        """プログレスバーを表示"""
        formatted = self.format_progress(progress)
        print(f"\r{formatted}", end="", flush=True)
    
    def finish_progress(self, final_message: str = "完了"):
        """プログレス表示を終了"""
        print(f"\n{final_message}")


class YAMLFormatter(BaseFormatter):
    """YAML出力フォーマッター"""
    
    def __init__(self, colored: bool = True):
        super().__init__(colored)
    
    def format_message(self, message: str, msg_type: MessageType) -> str:
        """メッセージをYAMLフォーマット"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "type": msg_type.value,
            "message": message
        }
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)
    
    def format_data(self, data: Dict[str, Any]) -> str:
        """データをYAMLフォーマット"""
        return yaml.dump(data, default_flow_style=False, allow_unicode=True, default=str)


class CompactFormatter(BaseFormatter):
    """コンパクト出力フォーマッター"""
    
    def __init__(self, colored: bool = True):
        super().__init__(colored)
    
    def format_message(self, message: str, msg_type: MessageType) -> str:
        """メッセージをコンパクトフォーマット"""
        symbols = {
            MessageType.INFO: "I",
            MessageType.SUCCESS: "✓",
            MessageType.WARNING: "!",
            MessageType.ERROR: "✗",
            MessageType.DEBUG: "D"
        }
        
        symbol = symbols.get(msg_type, "")
        formatted = f"{symbol} {message}"
        
        if self.colored:
            colors = {
                MessageType.INFO: 'cyan',
                MessageType.SUCCESS: 'green',
                MessageType.WARNING: 'yellow',
                MessageType.ERROR: 'red',
                MessageType.DEBUG: 'magenta'
            }
            color = colors.get(msg_type)
            if color:
                formatted = termcolor.colored(formatted, color)
        
        return formatted
    
    def format_data(self, data: Dict[str, Any]) -> str:
        """データをコンパクトフォーマット"""
        return json.dumps(data, separators=(',', ':'), ensure_ascii=False)


# フォーマッターファクトリー
def create_formatter(format_type: OutputFormat, **kwargs) -> BaseFormatter:
    """フォーマッターを作成"""
    if format_type == OutputFormat.TEXT:
        return OutputFormatter(**kwargs)
    elif format_type == OutputFormat.JSON:
        return JSONFormatter(**kwargs)
    elif format_type == OutputFormat.YAML:
        return YAMLFormatter(**kwargs)
    elif format_type == OutputFormat.TABLE:
        return TableFormatter(**kwargs)
    else:
        raise ValueError(f"サポートされていない出力形式: {format_type}")


# 便利関数
def format_file_size(size_bytes: int) -> str:
    """ファイルサイズを人間可読形式でフォーマット"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    """時間を人間可読形式でフォーマット"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}時間"


def format_percentage(value: float, total: float) -> str:
    """パーセンテージをフォーマット"""
    if total == 0:
        return "0.0%"
    percentage = (value / total) * 100
    return f"{percentage:.1f}%"