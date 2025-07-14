"""
AIDE リモートエージェント

リモートサーバーでの調査・操作・管理を行うエージェント
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

try:
    from ..config import get_config_manager
    from ..remote.connection_manager import ConnectionPool
    from ..tools.remote_system_tool import RemoteSystemTool, RemoteToolResult, ToolStatus
except ImportError as e:
    # 相対インポートエラーの場合の代替処理
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from src.config import get_config_manager
    from src.remote.connection_manager import ConnectionPool
    from src.tools.remote_system_tool import RemoteSystemTool, RemoteToolResult, ToolStatus

logger = logging.getLogger(__name__)


class RemoteAgentError(Exception):
    """リモートエージェント関連エラー"""
    pass


@dataclass
class ServerGroup:
    """サーバーグループ"""
    name: str
    servers: List[Dict[str, Any]]
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "servers": self.servers.copy(),
            "description": self.description,
            "tags": self.tags.copy()
        }


@dataclass
class InvestigationResult:
    """調査結果"""
    server: str
    status: str = 'pending'
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    collected_data: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "server": self.server,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time": self.execution_time,
            "collected_data": self.collected_data.copy(),
            "findings": self.findings.copy(),
            "recommendations": self.recommendations.copy()
        }


class RemoteAgent:
    """リモートサーバー調査・管理エージェント"""
    
    def __init__(self, config_manager=None, connection_pool=None):
        self.config_manager = config_manager or get_config_manager()
        self.connection_pool = connection_pool or ConnectionPool()
        
        # 設定取得
        self.agent_config = self.config_manager.get("remote_operations", {})
        self.investigation_config = self.agent_config.copy()
        
        # コンポーネント初期化
        self.remote_tool = RemoteSystemTool(self.connection_pool)
        
        # サーバーグループ管理
        self.server_groups: Dict[str, ServerGroup] = {}
        
        # 調査履歴
        self.investigation_history: List[InvestigationResult] = []
        self._history_lock = threading.Lock()
        
        # 並行処理設定
        self.max_concurrent_servers = self.investigation_config.get('max_concurrent_servers', 5)
        self._executor = ThreadPoolExecutor(max_workers=self.max_concurrent_servers)
    
    def add_server_group(self, name: str, servers: List[Dict[str, Any]], 
                        description: str = "", tags: List[str] = None) -> ServerGroup:
        """
        サーバーグループを追加
        
        Args:
            name: グループ名
            servers: サーバー設定のリスト
            description: グループの説明
            tags: グループのタグ
            
        Returns:
            作成されたサーバーグループ
        """
        group = ServerGroup(
            name=name,
            servers=servers.copy(),
            description=description,
            tags=tags or []
        )
        self.server_groups[name] = group
        logger.info(f"Server group '{name}' added with {len(servers)} servers")
        return group
    
    def get_server_group(self, name: str) -> Optional[ServerGroup]:
        """サーバーグループを取得"""
        return self.server_groups.get(name)
    
    def execute_on_server(self, server_config: Dict[str, Any], command: str, 
                         timeout: Optional[int] = None, **kwargs) -> RemoteToolResult:
        """
        単一サーバーでコマンドを実行
        
        Args:
            server_config: サーバー設定
            command: 実行するコマンド
            timeout: タイムアウト秒数
            **kwargs: その他のオプション
            
        Returns:
            実行結果
        """
        return self.remote_tool.execute(server_config, command, timeout, **kwargs)
    
    def execute_on_group(self, group_name: str, command: str, 
                        timeout: Optional[int] = None) -> List[RemoteToolResult]:
        """
        サーバーグループでコマンドを実行
        
        Args:
            group_name: グループ名
            command: 実行するコマンド
            timeout: タイムアウト秒数
            
        Returns:
            実行結果のリスト
        """
        group = self.server_groups.get(group_name)
        if not group:
            raise RemoteAgentError(f"Server group '{group_name}' not found")
        
        return self.remote_tool.execute_on_multiple_servers(group.servers, command, timeout)
    
    def investigate_server(self, server_config: Dict[str, Any], 
                          investigation_type: str = 'basic') -> InvestigationResult:
        """
        サーバーを調査
        
        Args:
            server_config: サーバー設定
            investigation_type: 調査タイプ ('basic', 'performance', 'security')
            
        Returns:
            調査結果
        """
        start_time = datetime.now()
        server_name = server_config.get('hostname', 'unknown')
        
        investigation = InvestigationResult(
            server=server_name,
            status='running',
            start_time=start_time
        )
        
        try:
            if investigation_type == 'basic':
                self._investigate_basic(server_config, investigation)
            elif investigation_type == 'performance':
                self._investigate_performance(server_config, investigation)
            elif investigation_type == 'security':
                self._investigate_security(server_config, investigation)
            else:
                raise RemoteAgentError(f"Unknown investigation type: {investigation_type}")
            
            investigation.status = 'completed'
            investigation.end_time = datetime.now()
            investigation.execution_time = (investigation.end_time - start_time).total_seconds()
            
        except Exception as e:
            investigation.status = 'failed'
            investigation.end_time = datetime.now()
            investigation.execution_time = (investigation.end_time - start_time).total_seconds()
            investigation.findings.append({
                'issue_type': 'investigation_error',
                'severity': 'high',
                'description': f"Investigation failed: {str(e)}"
            })
            logger.error(f"Investigation failed for {server_name}: {str(e)}")
        
        # 履歴に記録
        self._record_investigation_history(investigation)
        
        return investigation
    
    def investigate_performance_issue(self, server_config: Dict[str, Any]) -> InvestigationResult:
        """パフォーマンス問題を調査"""
        return self.investigate_server(server_config, 'performance')
    
    def analyze_security_status(self, server_config: Dict[str, Any]) -> InvestigationResult:
        """セキュリティ状態を分析"""
        return self.investigate_server(server_config, 'security')
    
    def investigate_group_parallel(self, group_name: str, investigation_type: str = 'basic',
                                  max_workers: Optional[int] = None) -> List[InvestigationResult]:
        """
        グループを並列で調査
        
        Args:
            group_name: グループ名
            investigation_type: 調査タイプ
            max_workers: 最大ワーカー数
            
        Returns:
            調査結果のリスト
        """
        group = self.server_groups.get(group_name)
        if not group:
            raise RemoteAgentError(f"Server group '{group_name}' not found")
        
        return self.investigate_multiple_servers(group.servers, investigation_type, max_workers)
    
    def investigate_multiple_servers(self, servers: List[Dict[str, Any]], 
                                   investigation_type: str = 'basic',
                                   max_workers: Optional[int] = None) -> List[InvestigationResult]:
        """
        複数サーバーを調査
        
        Args:
            servers: サーバー設定のリスト
            investigation_type: 調査タイプ
            max_workers: 最大ワーカー数
            
        Returns:
            調査結果のリスト
        """
        if max_workers is None:
            max_workers = min(self.max_concurrent_servers, len(servers))
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 全サーバーで調査を開始
            future_to_server = {
                executor.submit(self._investigate_single_server, server, investigation_type): server
                for server in servers
            }
            
            # 結果を収集
            for future in as_completed(future_to_server):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    server = future_to_server[future]
                    server_name = server.get('hostname', 'unknown')
                    
                    error_result = InvestigationResult(
                        server=server_name,
                        status='failed',
                        start_time=datetime.now(),
                        end_time=datetime.now()
                    )
                    error_result.findings.append({
                        'issue_type': 'investigation_error',
                        'severity': 'high',
                        'description': f"Investigation failed: {str(e)}"
                    })
                    results.append(error_result)
                    logger.error(f"Investigation failed for {server_name}: {str(e)}")
        
        return results
    
    def _investigate_single_server(self, server_config: Dict[str, Any], 
                                  investigation_type: str) -> InvestigationResult:
        """単一サーバーの調査（並列実行用）"""
        return self.investigate_server(server_config, investigation_type)
    
    def _investigate_basic(self, server_config: Dict[str, Any], investigation: InvestigationResult):
        """基本調査を実行"""
        # システム情報を収集
        if self.investigation_config.get('auto_collect_basic_info', True):
            system_info_result = self.remote_tool.gather_system_info(server_config)
            if system_info_result.status == ToolStatus.SUCCESS:
                investigation.collected_data['system_info'] = system_info_result.metadata.get('system_info', {})
            
            # 基本的なログ分析
            if self.investigation_config.get('auto_analyze_logs', True):
                log_commands = [
                    'tail -n 50 /var/log/syslog',
                    'tail -n 50 /var/log/messages',
                    'journalctl -n 50 --no-pager'
                ]
                
                log_data = {}
                for command in log_commands:
                    result = self.remote_tool.execute(server_config, command)
                    if result.status == ToolStatus.SUCCESS:
                        log_data[command] = result.output
                
                investigation.collected_data['log_analysis'] = log_data
            
            # 基本的な問題を検出
            self._analyze_basic_issues(investigation)
    
    def _investigate_performance(self, server_config: Dict[str, Any], investigation: InvestigationResult):
        """パフォーマンス調査を実行"""
        performance_commands = {
            'cpu_usage': 'top -bn1 | head -20',
            'memory_usage': 'free -h',
            'disk_io': 'iostat -x 1 3',
            'network_stats': 'netstat -i',
            'process_list': 'ps aux --sort=-%cpu | head -10',
            'load_average': 'uptime',
            'disk_usage': 'df -h'
        }
        
        performance_data = {}
        for key, command in performance_commands.items():
            result = self.remote_tool.execute(server_config, command)
            if result.status == ToolStatus.SUCCESS:
                performance_data[key] = result.output
            else:
                performance_data[key] = f"Failed to execute: {result.error}"
        
        investigation.collected_data['performance_analysis'] = performance_data
        
        # パフォーマンス問題を分析
        self._analyze_performance_issues(investigation)
    
    def _investigate_security(self, server_config: Dict[str, Any], investigation: InvestigationResult):
        """セキュリティ調査を実行"""
        security_commands = {
            'recent_logins': 'last -n 20',
            'open_ports': 'netstat -tuln',
            'running_services': 'ps aux | grep -E "(ssh|httpd|nginx|apache)"',
            'world_readable_files': 'find /etc -name "*.conf" -perm -004 2>/dev/null | head -10',
            'firewall_status': 'iptables -L 2>/dev/null || ufw status 2>/dev/null || echo "No firewall info"'
        }
        
        security_data = {}
        for key, command in security_commands.items():
            result = self.remote_tool.execute(server_config, command)
            if result.status == ToolStatus.SUCCESS:
                security_data[key] = result.output
            else:
                security_data[key] = f"Failed to execute: {result.error}"
        
        investigation.collected_data['security_analysis'] = security_data
        
        # セキュリティ問題を分析
        self._analyze_security_issues(investigation)
    
    def _analyze_basic_issues(self, investigation: InvestigationResult):
        """基本的な問題を分析"""
        system_info = investigation.collected_data.get('system_info', {})
        
        # ディスク使用量チェック
        disk_usage = system_info.get('disk_usage', '')
        if '9[0-9]%' in disk_usage or '100%' in disk_usage:
            investigation.findings.append({
                'issue_type': 'disk_space_critical',
                'severity': 'high',
                'description': 'Disk usage is critically high (>90%)'
            })
        elif '8[0-9]%' in disk_usage:
            investigation.findings.append({
                'issue_type': 'disk_space_warning',
                'severity': 'medium',
                'description': 'Disk usage is high (>80%)'
            })
        
        # アップタイム分析
        uptime = system_info.get('uptime', '')
        if 'min' in uptime or 'hour' in uptime:
            investigation.findings.append({
                'issue_type': 'recent_reboot',
                'severity': 'low',
                'description': 'Server was recently rebooted'
            })
        
        # 推奨事項を追加
        if investigation.findings:
            investigation.recommendations.extend([
                'Monitor disk usage regularly',
                'Check system logs for errors',
                'Verify all services are running correctly'
            ])
    
    def _analyze_performance_issues(self, investigation: InvestigationResult):
        """パフォーマンス問題を分析"""
        perf_data = investigation.collected_data.get('performance_analysis', {})
        
        # CPU使用率チェック
        cpu_info = perf_data.get('cpu_usage', '')
        if any(line for line in cpu_info.split('\n') if 'Cpu(s):' in line and '90.' in line):
            investigation.findings.append({
                'issue_type': 'high_cpu',
                'severity': 'high',
                'description': 'High CPU usage detected (>90%)'
            })
        
        # メモリ使用量チェック
        memory_info = perf_data.get('memory_usage', '')
        if 'Mem:' in memory_info:
            # 簡単なメモリ使用率チェック（実際の実装では正規表現を使用）
            if '9[0-9]' in memory_info:
                investigation.findings.append({
                    'issue_type': 'high_memory',
                    'severity': 'high',
                    'description': 'High memory usage detected'
                })
        
        # 推奨事項を追加
        if investigation.findings:
            investigation.recommendations.extend([
                'Identify high resource consuming processes',
                'Consider upgrading hardware resources',
                'Optimize application performance'
            ])
    
    def _analyze_security_issues(self, investigation: InvestigationResult):
        """セキュリティ問題を分析"""
        security_data = investigation.collected_data.get('security_analysis', {})
        
        # 開放ポートチェック
        open_ports = security_data.get('open_ports', '')
        common_unsafe_ports = ['21', '23', '80', '3389']
        for port in common_unsafe_ports:
            if f':{port} ' in open_ports:
                investigation.findings.append({
                    'issue_type': 'unsafe_port_open',
                    'severity': 'medium',
                    'description': f'Potentially unsafe port {port} is open'
                })
        
        # ファイアウォール状態チェック
        firewall_status = security_data.get('firewall_status', '')
        if 'inactive' in firewall_status.lower() or 'no firewall' in firewall_status.lower():
            investigation.findings.append({
                'issue_type': 'firewall_disabled',
                'severity': 'high',
                'description': 'Firewall appears to be disabled'
            })
        
        # 推奨事項を追加
        if investigation.findings:
            investigation.recommendations.extend([
                'Review and secure open ports',
                'Enable and configure firewall',
                'Regular security audits'
            ])
    
    def auto_remediate(self, server_config: Dict[str, Any], issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        自動修復を実行
        
        Args:
            server_config: サーバー設定
            issue: 修復する問題
            
        Returns:
            修復結果
        """
        if not issue.get('auto_fixable', False):
            return {
                'status': 'skipped',
                'reason': 'Issue is not auto-fixable'
            }
        
        fix_commands = issue.get('fix_commands', [])
        if not fix_commands:
            return {
                'status': 'skipped',
                'reason': 'No fix commands available'
            }
        
        applied_fixes = []
        for command in fix_commands:
            result = self.remote_tool.execute(server_config, command)
            fix_result = {
                'command': command,
                'status': 'success' if result.status == ToolStatus.SUCCESS else 'failed',
                'output': result.output,
                'error': result.error
            }
            applied_fixes.append(fix_result)
        
        overall_status = 'success' if all(fix['status'] == 'success' for fix in applied_fixes) else 'partial'
        
        return {
            'status': overall_status,
            'applied_fixes': applied_fixes,
            'issue_type': issue.get('type'),
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_investigation_report(self, investigation: InvestigationResult) -> Dict[str, Any]:
        """
        調査レポートを生成
        
        Args:
            investigation: 調査結果
            
        Returns:
            生成されたレポート
        """
        report = {
            'metadata': {
                'server': investigation.server,
                'investigation_time': investigation.start_time.isoformat() if investigation.start_time else None,
                'duration': investigation.execution_time,
                'status': investigation.status
            },
            'executive_summary': self._generate_executive_summary(investigation),
            'system_overview': investigation.collected_data.get('system_info', {}),
            'findings_and_issues': investigation.findings,
            'recommendations': investigation.recommendations,
            'technical_details': investigation.collected_data
        }
        
        return report
    
    def _generate_executive_summary(self, investigation: InvestigationResult) -> str:
        """エグゼクティブサマリを生成"""
        high_issues = [f for f in investigation.findings if f.get('severity') == 'high']
        medium_issues = [f for f in investigation.findings if f.get('severity') == 'medium']
        
        summary = f"Investigation completed for {investigation.server}.\n"
        
        if high_issues:
            summary += f"Critical issues found: {len(high_issues)}\n"
        if medium_issues:
            summary += f"Medium priority issues found: {len(medium_issues)}\n"
        
        if not investigation.findings:
            summary += "No significant issues detected.\n"
        
        if investigation.recommendations:
            summary += f"Recommendations provided: {len(investigation.recommendations)}\n"
        
        return summary
    
    def _record_investigation_history(self, investigation: InvestigationResult):
        """調査履歴を記録"""
        with self._history_lock:
            self.investigation_history.append(investigation)
            
            # 履歴を最新1000件まで保持
            if len(self.investigation_history) > 1000:
                self.investigation_history = self.investigation_history[-1000:]
    
    def get_investigation_history(self, limit: int = 100) -> List[InvestigationResult]:
        """調査履歴を取得"""
        with self._history_lock:
            return self.investigation_history[-limit:] if self.investigation_history else []
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            self.remote_tool.cleanup()
            self._executor.shutdown(wait=True)
            logger.info("Remote agent cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def __enter__(self):
        """コンテキストマネージャーサポート"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーサポート"""
        self.cleanup()