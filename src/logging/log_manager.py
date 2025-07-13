"""
AIDE ログ管理システム

統合ログ管理、構造化ログ、複数出力先対応
"""

import os
import sys
import json
import logging
try:
    import logging.handlers
except ImportError:
    # Python環境によってlogging.handlersが利用できない場合の対応
    logging.handlers = None
from typing import Dict, List, Optional, Any, Union, TextIO
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import time
from contextlib import contextmanager

from ..config import get_config_manager


class LogLevel(Enum):
    """ログレベル"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """ログ形式"""
    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"


@dataclass
class LogRecord:
    """構造化ログレコード"""
    timestamp: str
    level: str
    logger_name: str
    message: str
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    thread_id: Optional[int] = None
    process_id: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)
    
    def to_json(self) -> str:
        """JSON形式に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class LogFormatter:
    """ログフォーマッター"""
    
    def __init__(self, format_type: LogFormat = LogFormat.TEXT, include_colors: bool = True):
        self.format_type = format_type
        self.include_colors = include_colors and sys.stdout.isatty()
        
        # 色定義
        self.colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m'      # Reset
        }
    
    def format(self, record: LogRecord) -> str:
        """ログレコードをフォーマット"""
        if self.format_type == LogFormat.JSON:
            return record.to_json()
        
        elif self.format_type == LogFormat.STRUCTURED:
            return self._format_structured(record)
        
        else:  # TEXT
            return self._format_text(record)
    
    def _format_text(self, record: LogRecord) -> str:
        """テキスト形式でフォーマット"""
        # 基本フォーマット
        formatted = f"[{record.timestamp}] {record.level:8} {record.logger_name}: {record.message}"
        
        # 詳細情報追加
        if record.module:
            formatted += f" [{record.module}"
            if record.function:
                formatted += f".{record.function}"
            if record.line_number:
                formatted += f":{record.line_number}"
            formatted += "]"
        
        # 追加データ
        if record.extra_data:
            extra_str = " | ".join(f"{k}={v}" for k, v in record.extra_data.items())
            formatted += f" | {extra_str}"
        
        # 色付け
        if self.include_colors and record.level in self.colors:
            color = self.colors[record.level]
            reset = self.colors['RESET']
            formatted = f"{color}{formatted}{reset}"
        
        return formatted
    
    def _format_structured(self, record: LogRecord) -> str:
        """構造化形式でフォーマット"""
        parts = [
            f"time={record.timestamp}",
            f"level={record.level}",
            f"logger={record.logger_name}",
            f"msg=\"{record.message}\""
        ]
        
        if record.module:
            parts.append(f"module={record.module}")
        if record.function:
            parts.append(f"func={record.function}")
        if record.line_number:
            parts.append(f"line={record.line_number}")
        
        if record.extra_data:
            for key, value in record.extra_data.items():
                if isinstance(value, str):
                    parts.append(f"{key}=\"{value}\"")
                else:
                    parts.append(f"{key}={value}")
        
        return " ".join(parts)


class LogHandler:
    """ログハンドラー基底クラス"""
    
    def __init__(self, formatter: Optional[LogFormatter] = None):
        self.formatter = formatter or LogFormatter()
        self.level = LogLevel.INFO
    
    def set_level(self, level: LogLevel):
        """ログレベル設定"""
        self.level = level
    
    def should_log(self, level: LogLevel) -> bool:
        """ログ出力判定"""
        level_values = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.WARNING: 30,
            LogLevel.ERROR: 40,
            LogLevel.CRITICAL: 50
        }
        return level_values[level] >= level_values[self.level]
    
    def handle(self, record: LogRecord):
        """ログレコード処理"""
        if self.should_log(LogLevel(record.level)):
            formatted = self.formatter.format(record)
            self.emit(formatted)
    
    def emit(self, formatted_message: str):
        """ログ出力（サブクラスで実装）"""
        raise NotImplementedError


class ConsoleHandler(LogHandler):
    """コンソールハンドラー"""
    
    def __init__(self, stream: TextIO = None, formatter: Optional[LogFormatter] = None):
        super().__init__(formatter)
        self.stream = stream or sys.stdout
    
    def emit(self, formatted_message: str):
        """コンソールに出力"""
        print(formatted_message, file=self.stream)
        self.stream.flush()


class FileHandler(LogHandler):
    """ファイルハンドラー"""
    
    def __init__(self, file_path: Union[str, Path], formatter: Optional[LogFormatter] = None,
                 max_size: int = 10 * 1024 * 1024, backup_count: int = 5):
        super().__init__(formatter)
        self.file_path = Path(file_path)
        self.max_size = max_size
        self.backup_count = backup_count
        
        # ディレクトリ作成
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ローテーションハンドラー
        self._setup_rotation()
    
    def _setup_rotation(self):
        """ログローテーション設定"""
        self.rotation_handler = logging.handlers.RotatingFileHandler(
            self.file_path,
            maxBytes=self.max_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
    
    def emit(self, formatted_message: str):
        """ファイルに出力"""
        with open(self.file_path, 'a', encoding='utf-8') as f:
            f.write(formatted_message + '\n')
            f.flush()
        
        # ローテーションチェック
        if self.file_path.stat().st_size > self.max_size:
            self._rotate_logs()
    
    def _rotate_logs(self):
        """ログファイルローテーション"""
        for i in range(self.backup_count - 1, 0, -1):
            src = self.file_path.with_suffix(f'.{i}')
            dst = self.file_path.with_suffix(f'.{i + 1}')
            if src.exists():
                src.rename(dst)
        
        # 現在のログファイルをバックアップ
        if self.file_path.exists():
            backup_path = self.file_path.with_suffix('.1')
            self.file_path.rename(backup_path)


class AsyncLogHandler(LogHandler):
    """非同期ログハンドラー"""
    
    def __init__(self, target_handler: LogHandler, queue_size: int = 1000):
        super().__init__(target_handler.formatter)
        self.target_handler = target_handler
        self.log_queue = queue.Queue(maxsize=queue_size)
        self.worker_thread = None
        self.stop_event = threading.Event()
        
        self._start_worker()
    
    def _start_worker(self):
        """ワーカースレッド開始"""
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    
    def _worker(self):
        """ワーカースレッド処理"""
        while not self.stop_event.is_set():
            try:
                record = self.log_queue.get(timeout=0.1)
                if record is not None:
                    self.target_handler.handle(record)
                self.log_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"ログ処理エラー: {e}", file=sys.stderr)
    
    def handle(self, record: LogRecord):
        """ログレコードをキューに追加"""
        try:
            self.log_queue.put_nowait(record)
        except queue.Full:
            # キューが満杯の場合は古いレコードを破棄
            try:
                self.log_queue.get_nowait()
                self.log_queue.put_nowait(record)
            except queue.Empty:
                pass
    
    def stop(self):
        """ハンドラー停止"""
        self.stop_event.set()
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)


class StructuredLogger:
    """構造化ログ出力クラス"""
    
    def __init__(self, name: str, handlers: Optional[List[LogHandler]] = None):
        self.name = name
        self.handlers = handlers or []
        self.extra_context: Dict[str, Any] = {}
    
    def add_handler(self, handler: LogHandler):
        """ハンドラー追加"""
        self.handlers.append(handler)
    
    def set_context(self, **kwargs):
        """コンテキスト情報設定"""
        self.extra_context.update(kwargs)
    
    def clear_context(self):
        """コンテキスト情報クリア"""
        self.extra_context.clear()
    
    def _create_record(self, level: LogLevel, message: str, **kwargs) -> LogRecord:
        """ログレコード作成"""
        # スタック情報取得
        import inspect
        frame = inspect.currentframe()
        caller_frame = frame.f_back.f_back  # 2つ上のフレーム
        
        module = caller_frame.f_globals.get('__name__')
        function = caller_frame.f_code.co_name
        line_number = caller_frame.f_lineno
        
        # 追加データ統合
        extra_data = {**self.extra_context, **kwargs}
        
        return LogRecord(
            timestamp=datetime.now().isoformat(),
            level=level.value,
            logger_name=self.name,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            thread_id=threading.get_ident(),
            process_id=os.getpid(),
            extra_data=extra_data if extra_data else None
        )
    
    def log(self, level: LogLevel, message: str, **kwargs):
        """ログ出力"""
        record = self._create_record(level, message, **kwargs)
        
        for handler in self.handlers:
            try:
                handler.handle(record)
            except Exception as e:
                print(f"ログハンドラーエラー: {e}", file=sys.stderr)
    
    def debug(self, message: str, **kwargs):
        """デバッグログ"""
        self.log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """情報ログ"""
        self.log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告ログ"""
        self.log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """エラーログ"""
        self.log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """重要ログ"""
        self.log(LogLevel.CRITICAL, message, **kwargs)
    
    @contextmanager
    def context(self, **kwargs):
        """一時的なコンテキスト設定"""
        old_context = self.extra_context.copy()
        self.set_context(**kwargs)
        try:
            yield self
        finally:
            self.extra_context = old_context


class LogManager:
    """ログ管理クラス"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self.loggers: Dict[str, StructuredLogger] = {}
        self.handlers: List[LogHandler] = []
        
        self._setup_default_logging()
    
    def _setup_default_logging(self):
        """デフォルトログ設定"""
        # ログディレクトリ作成
        log_dir = Path(self.config_manager.get("paths.logs_directory", "logs"))
        log_dir.mkdir(exist_ok=True)
        
        # ログレベル設定
        log_level_str = self.config_manager.get("system.log_level", "INFO")
        log_level = LogLevel(log_level_str.upper())
        
        # コンソールハンドラー
        console_formatter = LogFormatter(LogFormat.TEXT, include_colors=True)
        console_handler = ConsoleHandler(formatter=console_formatter)
        console_handler.set_level(log_level)
        self.handlers.append(console_handler)
        
        # ファイルハンドラー
        file_formatter = LogFormatter(LogFormat.JSON, include_colors=False)
        file_handler = FileHandler(
            log_dir / "aide.log",
            formatter=file_formatter
        )
        file_handler.set_level(LogLevel.DEBUG)
        
        # 非同期化
        async_file_handler = AsyncLogHandler(file_handler)
        self.handlers.append(async_file_handler)
        
        # エラー専用ファイル
        error_formatter = LogFormatter(LogFormat.STRUCTURED, include_colors=False)
        error_handler = FileHandler(
            log_dir / "errors.log",
            formatter=error_formatter
        )
        error_handler.set_level(LogLevel.ERROR)
        
        async_error_handler = AsyncLogHandler(error_handler)
        self.handlers.append(async_error_handler)
    
    def get_logger(self, name: str) -> StructuredLogger:
        """ログ取得"""
        if name not in self.loggers:
            logger = StructuredLogger(name)
            
            # デフォルトハンドラー追加
            for handler in self.handlers:
                logger.add_handler(handler)
            
            self.loggers[name] = logger
        
        return self.loggers[name]
    
    def create_logger(self, name: str, handlers: Optional[List[LogHandler]] = None) -> StructuredLogger:
        """カスタムログ作成"""
        logger = StructuredLogger(name, handlers or [])
        self.loggers[name] = logger
        return logger
    
    def add_global_handler(self, handler: LogHandler):
        """グローバルハンドラー追加"""
        self.handlers.append(handler)
        
        # 既存ロガーに追加
        for logger in self.loggers.values():
            logger.add_handler(handler)
    
    def set_global_level(self, level: LogLevel):
        """グローバルレベル設定"""
        for handler in self.handlers:
            handler.set_level(level)
    
    def shutdown(self):
        """ログシステム終了"""
        for handler in self.handlers:
            if isinstance(handler, AsyncLogHandler):
                handler.stop()


# グローバルログマネージャー
_log_manager: Optional[LogManager] = None


def get_log_manager() -> LogManager:
    """グローバルログマネージャー取得"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager


def get_logger(name: str) -> StructuredLogger:
    """ログ取得（便利関数）"""
    return get_log_manager().get_logger(name)


# エイリアス
Logger = StructuredLogger