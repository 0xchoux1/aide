import subprocess
import os
import signal
import shlex
import time
from typing import List, Dict, Any, Optional
from .base_tool import BaseTool, ToolResult, ToolStatus


class SystemTool(BaseTool):
    """システムコマンド実行ツール"""
    
    def __init__(self, timeout: int = 30, safe_mode: bool = True):
        super().__init__(
            name="system_tool",
            description="システムコマンドを安全に実行するツール"
        )
        self.timeout = timeout
        self.safe_mode = safe_mode
        
        # 安全でないコマンドのブラックリスト
        self.dangerous_commands = {
            'rm', 'rmdir', 'del', 'format', 'fdisk', 'mkfs',
            'dd', 'shutdown', 'reboot', 'halt', 'poweroff',
            'chmod', 'chown', 'passwd', 'su', 'sudo',
            'kill', 'killall', 'pkill'
        }
        
        # 許可されるコマンドのホワイトリスト（安全モード時）
        self.safe_commands = {
            'ls', 'cat', 'head', 'tail', 'grep', 'find', 'which',
            'ps', 'top', 'htop', 'df', 'du', 'free', 'uptime',
            'date', 'whoami', 'id', 'pwd', 'echo', 'wc',
            'systemctl', 'journalctl', 'netstat', 'ss', 'lsof',
            'curl', 'wget', 'ping', 'nslookup', 'dig',
            'git', 'docker', 'kubectl', 'helm'
        }
    
    def execute(self, command: str, working_dir: Optional[str] = None, 
                env_vars: Optional[Dict[str, str]] = None) -> ToolResult:
        """コマンドを実行"""
        start_time = time.time()
        
        try:
            # コマンドの安全性チェック
            if self.safe_mode and not self._is_safe_command(command):
                return ToolResult(
                    status=ToolStatus.PERMISSION_DENIED,
                    output="",
                    error=f"コマンド '{command}' は安全でないため実行できません",
                    execution_time=time.time() - start_time
                )
            
            # 環境変数の設定
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
            
            # コマンド実行
            process = subprocess.Popen(
                shlex.split(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir,
                env=env,
                preexec_fn=os.setsid  # プロセスグループを作成
            )
            
            try:
                stdout, stderr = process.communicate(timeout=self.timeout)
                execution_time = time.time() - start_time
                
                # 結果を判定
                if process.returncode == 0:
                    status = ToolStatus.SUCCESS
                    error = stderr if stderr else None
                else:
                    status = ToolStatus.FAILED
                    error = stderr or f"コマンドが終了コード {process.returncode} で失敗"
                
                result = ToolResult(
                    status=status,
                    output=stdout,
                    error=error,
                    execution_time=execution_time,
                    metadata={
                        'command': command,
                        'return_code': process.returncode,
                        'working_dir': working_dir,
                        'pid': process.pid
                    }
                )
                
            except subprocess.TimeoutExpired:
                # タイムアウト時はプロセスグループ全体を終了
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                
                result = ToolResult(
                    status=ToolStatus.TIMEOUT,
                    output="",
                    error=f"コマンド実行がタイムアウト ({self.timeout}秒)",
                    execution_time=time.time() - start_time,
                    metadata={
                        'command': command,
                        'timeout': self.timeout
                    }
                )
            
        except FileNotFoundError:
            result = ToolResult(
                status=ToolStatus.NOT_FOUND,
                output="",
                error=f"コマンドが見つかりません: {command.split()[0]}",
                execution_time=time.time() - start_time,
                metadata={'command': command}
            )
        except PermissionError:
            result = ToolResult(
                status=ToolStatus.PERMISSION_DENIED,
                output="",
                error=f"権限がありません: {command}",
                execution_time=time.time() - start_time,
                metadata={'command': command}
            )
        except Exception as e:
            result = ToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"予期しないエラー: {str(e)}",
                execution_time=time.time() - start_time,
                metadata={'command': command, 'exception': str(e)}
            )
        
        self._record_execution(result)
        return result
    
    def _is_safe_command(self, command: str) -> bool:
        """コマンドが安全かどうかチェック"""
        cmd_parts = shlex.split(command)
        if not cmd_parts:
            return False
        
        base_command = os.path.basename(cmd_parts[0])
        
        # 危険なコマンドはブロック
        if base_command in self.dangerous_commands:
            return False
        
        # 安全なコマンドリストをチェック
        return base_command in self.safe_commands
    
    def run_system_check(self) -> ToolResult:
        """基本的なシステムチェックを実行"""
        checks = [
            "uptime",
            "df -h",
            "free -h", 
            "ps aux --sort=-%cpu | head -10",
            "systemctl status --no-pager"
        ]
        
        results = []
        start_time = time.time()
        
        for check in checks:
            result = self.execute(check)
            results.append({
                'command': check,
                'status': result.status.value,
                'output': result.output,
                'error': result.error
            })
        
        # 全体の結果を集約
        all_success = all(r['status'] == 'success' for r in results)
        status = ToolStatus.SUCCESS if all_success else ToolStatus.FAILED
        
        return ToolResult(
            status=status,
            output=f"システムチェック完了: {len([r for r in results if r['status'] == 'success'])}/{len(results)} 成功",
            error=None if all_success else "一部のチェックが失敗しました",
            execution_time=time.time() - start_time,
            metadata={'checks': results}
        )
    
    def get_system_info(self) -> ToolResult:
        """システム情報を取得"""
        info_commands = {
            'hostname': 'hostname',
            'os_info': 'cat /etc/os-release',
            'kernel': 'uname -r',
            'cpu_info': 'cat /proc/cpuinfo | grep "model name" | head -1',
            'memory': 'cat /proc/meminfo | grep -E "MemTotal|MemAvailable"',
            'disk_usage': 'df -h /',
            'load_average': 'cat /proc/loadavg'
        }
        
        system_info = {}
        start_time = time.time()
        
        for key, command in info_commands.items():
            result = self.execute(command)
            if result.status == ToolStatus.SUCCESS:
                system_info[key] = result.output.strip()
            else:
                system_info[key] = f"取得失敗: {result.error}"
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"システム情報を取得しました ({len(system_info)} 項目)",
            execution_time=time.time() - start_time,
            metadata={'system_info': system_info}
        )
    
    def monitor_process(self, process_name: str) -> ToolResult:
        """プロセスの監視"""
        command = f"ps aux | grep '{process_name}' | grep -v grep"
        return self.execute(command)