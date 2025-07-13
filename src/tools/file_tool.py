import os
import shutil
import stat
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from .base_tool import BaseTool, ToolResult, ToolStatus


class FileTool(BaseTool):
    """ファイル操作ツール"""
    
    def __init__(self, safe_mode: bool = True):
        super().__init__(
            name="file_tool",
            description="ファイルとディレクトリの安全な操作ツール"
        )
        self.safe_mode = safe_mode
        
        # 保護されるディレクトリ（安全モード時）
        self.protected_paths = {
            '/etc', '/bin', '/sbin', '/usr/bin', '/usr/sbin',
            '/boot', '/sys', '/proc', '/dev', '/root'
        }
    
    def execute(self, operation: str, *args, **kwargs) -> ToolResult:
        """ファイル操作を実行"""
        if operation == "read":
            return self.read_file(*args, **kwargs)
        elif operation == "write":
            return self.write_file(*args, **kwargs)
        elif operation == "list":
            return self.list_directory(*args, **kwargs)
        elif operation == "info":
            return self.get_file_info(*args, **kwargs)
        elif operation == "search":
            return self.search_files(*args, **kwargs)
        else:
            return ToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"未対応の操作: {operation}",
                execution_time=0.0
            )
    
    def read_file(self, file_path: str, encoding: str = 'utf-8', 
                  max_size: int = 1024*1024) -> ToolResult:  # 1MBまで
        """ファイルを読み取り"""
        start_time = time.time()
        
        try:
            path = Path(file_path)
            
            if not path.exists():
                return ToolResult(
                    status=ToolStatus.NOT_FOUND,
                    output="",
                    error=f"ファイルが見つかりません: {file_path}",
                    execution_time=time.time() - start_time
                )
            
            if not path.is_file():
                return ToolResult(
                    status=ToolStatus.FAILED,
                    output="",
                    error=f"指定されたパスはファイルではありません: {file_path}",
                    execution_time=time.time() - start_time
                )
            
            # ファイルサイズチェック
            file_size = path.stat().st_size
            if file_size > max_size:
                return ToolResult(
                    status=ToolStatus.FAILED,
                    output="",
                    error=f"ファイルサイズが上限を超えています: {file_size} > {max_size} bytes",
                    execution_time=time.time() - start_time
                )
            
            # ファイル読み取り
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=content,
                execution_time=time.time() - start_time,
                metadata={
                    'file_path': str(path.absolute()),
                    'file_size': file_size,
                    'encoding': encoding,
                    'line_count': content.count('\n') + 1
                }
            )
            
        except PermissionError:
            return ToolResult(
                status=ToolStatus.PERMISSION_DENIED,
                output="",
                error=f"ファイルの読み取り権限がありません: {file_path}",
                execution_time=time.time() - start_time
            )
        except UnicodeDecodeError as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"文字エンコーディングエラー: {e}",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"ファイル読み取りエラー: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def write_file(self, file_path: str, content: str, 
                   encoding: str = 'utf-8', backup: bool = True) -> ToolResult:
        """ファイルに書き込み"""
        start_time = time.time()
        
        try:
            path = Path(file_path)
            
            # 安全性チェック
            if self.safe_mode and self._is_protected_path(path):
                return ToolResult(
                    status=ToolStatus.PERMISSION_DENIED,
                    output="",
                    error=f"保護されたパスへの書き込みは禁止されています: {file_path}",
                    execution_time=time.time() - start_time
                )
            
            # 親ディレクトリの作成
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # バックアップの作成
            backup_path = None
            if backup and path.exists():
                backup_path = path.with_suffix(f"{path.suffix}.backup")
                shutil.copy2(path, backup_path)
            
            # ファイル書き込み
            with open(path, 'w', encoding=encoding) as f:
                f.write(content)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"ファイルを書き込みました: {file_path}",
                execution_time=time.time() - start_time,
                metadata={
                    'file_path': str(path.absolute()),
                    'content_size': len(content.encode(encoding)),
                    'backup_created': backup_path is not None,
                    'backup_path': str(backup_path) if backup_path else None
                }
            )
            
        except PermissionError:
            return ToolResult(
                status=ToolStatus.PERMISSION_DENIED,
                output="",
                error=f"ファイルの書き込み権限がありません: {file_path}",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"ファイル書き込みエラー: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def list_directory(self, dir_path: str, include_hidden: bool = False,
                      recursive: bool = False) -> ToolResult:
        """ディレクトリの内容を一覧表示"""
        start_time = time.time()
        
        try:
            path = Path(dir_path)
            
            if not path.exists():
                return ToolResult(
                    status=ToolStatus.NOT_FOUND,
                    output="",
                    error=f"ディレクトリが見つかりません: {dir_path}",
                    execution_time=time.time() - start_time
                )
            
            if not path.is_dir():
                return ToolResult(
                    status=ToolStatus.FAILED,
                    output="",
                    error=f"指定されたパスはディレクトリではありません: {dir_path}",
                    execution_time=time.time() - start_time
                )
            
            files = []
            
            if recursive:
                pattern = "**/*"
                if include_hidden:
                    # 隠しファイルも含める場合の処理
                    for item in path.rglob("*"):
                        files.append(item)
                else:
                    files = list(path.rglob("*"))
            else:
                if include_hidden:
                    files = list(path.iterdir())
                else:
                    files = [f for f in path.iterdir() if not f.name.startswith('.')]
            
            # ファイル情報を収集
            file_info = []
            for file_path in sorted(files):
                try:
                    stat_info = file_path.stat()
                    file_info.append({
                        'name': file_path.name,
                        'path': str(file_path.relative_to(path)) if recursive else file_path.name,
                        'type': 'directory' if file_path.is_dir() else 'file',
                        'size': stat_info.st_size,
                        'permissions': oct(stat_info.st_mode)[-3:],
                        'modified': stat_info.st_mtime
                    })
                except (PermissionError, OSError):
                    file_info.append({
                        'name': file_path.name,
                        'path': str(file_path.relative_to(path)) if recursive else file_path.name,
                        'type': 'unknown',
                        'size': None,
                        'permissions': None,
                        'modified': None,
                        'error': 'Permission denied'
                    })
            
            # 結果のフォーマット
            output_lines = []
            for info in file_info:
                if info.get('error'):
                    output_lines.append(f"{info['name']} (アクセス不可)")
                else:
                    type_indicator = 'd' if info['type'] == 'directory' else 'f'
                    size_str = f"{info['size']:>8}" if info['size'] is not None else "     n/a"
                    output_lines.append(f"{type_indicator} {info['permissions']} {size_str} {info['name']}")
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output='\n'.join(output_lines),
                execution_time=time.time() - start_time,
                metadata={
                    'directory': str(path.absolute()),
                    'total_items': len(file_info),
                    'directories': sum(1 for f in file_info if f['type'] == 'directory'),
                    'files': sum(1 for f in file_info if f['type'] == 'file'),
                    'recursive': recursive,
                    'include_hidden': include_hidden,
                    'items': file_info
                }
            )
            
        except PermissionError:
            return ToolResult(
                status=ToolStatus.PERMISSION_DENIED,
                output="",
                error=f"ディレクトリのアクセス権限がありません: {dir_path}",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"ディレクトリ一覧エラー: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def get_file_info(self, file_path: str) -> ToolResult:
        """ファイル情報を取得"""
        start_time = time.time()
        
        try:
            path = Path(file_path)
            
            if not path.exists():
                return ToolResult(
                    status=ToolStatus.NOT_FOUND,
                    output="",
                    error=f"ファイルが見つかりません: {file_path}",
                    execution_time=time.time() - start_time
                )
            
            stat_info = path.stat()
            
            # ファイル情報を収集
            info = {
                'path': str(path.absolute()),
                'name': path.name,
                'type': 'directory' if path.is_dir() else 'file',
                'size': stat_info.st_size,
                'permissions': oct(stat_info.st_mode),
                'owner_readable': os.access(path, os.R_OK),
                'owner_writable': os.access(path, os.W_OK),
                'owner_executable': os.access(path, os.X_OK),
                'created': stat_info.st_ctime,
                'modified': stat_info.st_mtime,
                'accessed': stat_info.st_atime
            }
            
            # ファイルの場合はハッシュも計算
            if path.is_file() and stat_info.st_size < 100*1024*1024:  # 100MB未満
                try:
                    with open(path, 'rb') as f:
                        content = f.read()
                        info['md5'] = hashlib.md5(content).hexdigest()
                        info['sha256'] = hashlib.sha256(content).hexdigest()
                except:
                    info['md5'] = None
                    info['sha256'] = None
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"ファイル情報: {path.name}",
                execution_time=time.time() - start_time,
                metadata={'file_info': info}
            )
            
        except PermissionError:
            return ToolResult(
                status=ToolStatus.PERMISSION_DENIED,
                output="",
                error=f"ファイルのアクセス権限がありません: {file_path}",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"ファイル情報取得エラー: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def _is_protected_path(self, path: Path) -> bool:
        """保護されたパスかどうかチェック"""
        path_str = str(path.absolute())
        return any(path_str.startswith(protected) for protected in self.protected_paths)
    
    def search_files(self, directory: str, pattern: str, 
                    case_sensitive: bool = True) -> ToolResult:
        """ファイル検索"""
        start_time = time.time()
        
        try:
            from fnmatch import fnmatch
            path = Path(directory)
            
            if not path.exists() or not path.is_dir():
                return ToolResult(
                    status=ToolStatus.NOT_FOUND,
                    output="",
                    error=f"検索ディレクトリが見つかりません: {directory}",
                    execution_time=time.time() - start_time
                )
            
            matches = []
            for item in path.rglob("*"):
                if item.is_file():
                    name = item.name if case_sensitive else item.name.lower()
                    search_pattern = pattern if case_sensitive else pattern.lower()
                    
                    if fnmatch(name, search_pattern):
                        matches.append(str(item.relative_to(path)))
            
            output = '\n'.join(matches) if matches else "マッチするファイルが見つかりませんでした"
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=output,
                execution_time=time.time() - start_time,
                metadata={
                    'search_directory': directory,
                    'pattern': pattern,
                    'case_sensitive': case_sensitive,
                    'matches_count': len(matches),
                    'matches': matches
                }
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"ファイル検索エラー: {str(e)}",
                execution_time=time.time() - start_time
            )