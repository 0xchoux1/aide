"""
RemoteAgentのユニットテスト

リモートサーバー操作エージェント、マルチサーバー管理、自動調査機能のテスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from datetime import datetime
from typing import Dict, List, Any

# テスト対象のインポート（まだ実装されていないのでパスする）
try:
    from src.agents.remote_agent import (
        RemoteAgent,
        InvestigationResult,
        RemoteAgentError,
        ServerGroup
    )
    from src.tools.remote_system_tool import RemoteSystemTool, RemoteToolResult
    from src.remote.connection_manager import RemoteConnectionManager
    from src.tools.base_tool import ToolStatus
except ImportError:
    # 実装前なのでモックで代替
    RemoteAgent = None
    InvestigationResult = None
    RemoteAgentError = Exception
    ServerGroup = None
    RemoteSystemTool = None
    RemoteToolResult = None
    RemoteConnectionManager = None
    ToolStatus = None


class TestRemoteAgent:
    """RemoteAgentのテストクラス"""
    
    @pytest.fixture
    def agent_config(self):
        """エージェント設定"""
        return {
            'name': 'test_remote_agent',
            'role': 'システム管理者',
            'goal': 'リモートサーバーの調査と問題解決',
            'backstory': 'Linux環境の専門知識を持つシステム管理者エージェント',
            'tools_config': {
                'timeout': 60,
                'safe_mode': True,
                'max_retries': 3
            },
            'investigation': {
                'auto_collect_basic_info': True,
                'auto_analyze_logs': True,
                'max_concurrent_servers': 5
            }
        }
    
    @pytest.fixture
    def server_configs(self):
        """サーバー設定リスト"""
        return [
            {
                'hostname': 'web-server-01.example.com',
                'port': 22,
                'username': 'admin',
                'key_filename': '/path/to/key1.pem',
                'group': 'web-servers',
                'tags': ['production', 'web']
            },
            {
                'hostname': 'db-server-01.example.com',
                'port': 22,
                'username': 'dbadmin',
                'key_filename': '/path/to/key2.pem',
                'group': 'database-servers',
                'tags': ['production', 'database']
            },
            {
                'hostname': 'app-server-01.example.com',
                'port': 22,
                'username': 'appuser',
                'key_filename': '/path/to/key3.pem',
                'group': 'app-servers',
                'tags': ['production', 'application']
            }
        ]
    
    @pytest.mark.skipif(RemoteAgent is None, reason="RemoteAgent not implemented yet")
    def test_remote_agent_initialization(self, agent_config):
        """リモートエージェントの初期化テスト"""
        agent = RemoteAgent(agent_config)
        
        assert agent.name == 'test_remote_agent'
        assert agent.role == 'システム管理者'
        assert agent.goal == 'リモートサーバーの調査と問題解決'
        assert agent.backstory == 'Linux環境の専門知識を持つシステム管理者エージェント'
        assert isinstance(agent.remote_tool, RemoteSystemTool)
        assert agent.server_groups == {}
        assert agent.investigation_history == []
    
    @pytest.mark.skipif(RemoteAgent is None, reason="RemoteAgent not implemented yet")
    def test_add_server_group(self, agent_config, server_configs):
        """サーバーグループの追加テスト"""
        agent = RemoteAgent(agent_config)
        
        # Webサーバーグループを追加
        web_servers = [s for s in server_configs if 'web' in s.get('tags', [])]
        agent.add_server_group('web-servers', web_servers, description='Webサーバー群')
        
        assert 'web-servers' in agent.server_groups
        group = agent.server_groups['web-servers']
        assert group.name == 'web-servers'
        assert group.description == 'Webサーバー群'
        assert len(group.servers) == 1
        assert group.servers[0]['hostname'] == 'web-server-01.example.com'
    
    @pytest.mark.skipif(RemoteAgent is None, reason="RemoteAgent not implemented yet")
    def test_execute_on_server(self, agent_config):
        """単一サーバーでのコマンド実行テスト"""
        agent = RemoteAgent(agent_config)
        
        server_config = {
            'hostname': 'test-server.example.com',
            'username': 'testuser',
            'port': 22
        }
        
        with patch.object(agent.remote_tool, 'execute') as mock_execute:
            mock_result = Mock()
            mock_result.status = ToolStatus.SUCCESS
            mock_result.output = "test output"
            mock_result.server = "test-server.example.com"
            mock_execute.return_value = mock_result
            
            # コマンドを実行
            result = agent.execute_on_server(server_config, "ls -la")
            
            assert result.status == ToolStatus.SUCCESS
            assert result.output == "test output"
            assert result.server == "test-server.example.com"
            mock_execute.assert_called_once_with(server_config, "ls -la")
    
    @pytest.mark.skipif(RemoteAgent is None, reason="RemoteAgent not implemented yet")
    def test_execute_on_group(self, agent_config, server_configs):
        """サーバーグループでのコマンド実行テスト"""
        agent = RemoteAgent(agent_config)
        
        # サーバーグループを追加
        agent.add_server_group('production-servers', server_configs)
        
        with patch.object(agent.remote_tool, 'execute_on_multiple_servers') as mock_execute:
            mock_results = []
            for i, server in enumerate(server_configs):
                mock_result = Mock()
                mock_result.status = ToolStatus.SUCCESS
                mock_result.output = f"output from {server['hostname']}"
                mock_result.server = server['hostname']
                mock_results.append(mock_result)
            
            mock_execute.return_value = mock_results
            
            # グループでコマンドを実行
            results = agent.execute_on_group('production-servers', 'uptime')
            
            assert len(results) == 3
            for i, result in enumerate(results):
                assert result.status == ToolStatus.SUCCESS
                assert server_configs[i]['hostname'] in result.output
            
            mock_execute.assert_called_once_with(server_configs, 'uptime')
    
    @pytest.mark.skipif(RemoteAgent is None, reason="RemoteAgent not implemented yet")
    def test_investigate_server_basic(self, agent_config):
        """基本的なサーバー調査テスト"""
        agent = RemoteAgent(agent_config)
        
        server_config = {
            'hostname': 'target-server.example.com',
            'username': 'admin',
            'port': 22
        }
        
        with patch.object(agent.remote_tool, 'gather_system_info') as mock_gather_info, \
             patch.object(agent.remote_tool, 'execute') as mock_execute:
            
            # システム情報の応答を設定
            mock_info_result = Mock()
            mock_info_result.status = ToolStatus.SUCCESS
            mock_info_result.metadata = {
                'system_info': {
                    'hostname': 'target-server',
                    'kernel': 'Linux 5.4.0-123',
                    'memory': 'MemTotal: 16GB',
                    'disk_usage': 'Filesystem /dev/sda1 75% /',
                    'load_average': 'load average: 0.8',
                    'uptime': 'up 5 days'
                }
            }
            mock_gather_info.return_value = mock_info_result
            
            # ログ分析の応答を設定
            mock_log_result = Mock()
            mock_log_result.status = ToolStatus.SUCCESS
            mock_log_result.output = "Recent log entries..."
            mock_execute.return_value = mock_log_result
            
            # 調査を実行
            investigation = agent.investigate_server(server_config)
            
            assert investigation.status == 'completed'
            assert investigation.server == 'target-server.example.com'
            assert 'system_info' in investigation.collected_data
            assert 'log_analysis' in investigation.collected_data
            assert len(investigation.findings) > 0
            
            mock_gather_info.assert_called_once()
    
    @pytest.mark.skipif(RemoteAgent is None, reason="RemoteAgent not implemented yet")
    def test_investigate_performance_issue(self, agent_config):
        """パフォーマンス問題の調査テスト"""
        agent = RemoteAgent(agent_config)
        
        server_config = {
            'hostname': 'slow-server.example.com',
            'username': 'admin',
            'port': 22
        }
        
        with patch.object(agent.remote_tool, 'execute') as mock_execute:
            # 高負荷を示すモックデータ
            command_responses = {
                'top -bn1 | head -20': ('PID USER %CPU %MEM\n1234 apache 95.0 10.2 httpd', '', 0),
                'iostat -x 1 3': ('Device: sda1 %util 98.5', '', 0),
                'free -h': ('Mem: 15G 14G 1.0G', '', 0),
                'ps aux --sort=-%cpu | head -10': ('High CPU processes...', '', 0),
                'netstat -tuln | grep LISTEN': ('Open ports...', '', 0)
            }
            
            def mock_execute_side_effect(server_config, command, **kwargs):
                result = Mock()
                result.status = ToolStatus.SUCCESS
                result.output, result.error, exit_code = command_responses.get(command, ('', '', 0))
                return result
            
            mock_execute.side_effect = mock_execute_side_effect
            
            # パフォーマンス調査を実行
            investigation = agent.investigate_performance_issue(server_config)
            
            assert investigation.status == 'completed'
            assert 'performance_analysis' in investigation.collected_data
            assert any('high_cpu' in finding.get('issue_type', '') for finding in investigation.findings)
    
    @pytest.mark.skipif(RemoteAgent is None, reason="RemoteAgent not implemented yet")
    def test_investigate_group_parallel(self, agent_config, server_configs):
        """グループ並列調査テスト"""
        agent = RemoteAgent(agent_config)
        
        # サーバーグループを追加
        agent.add_server_group('production-group', server_configs)
        
        with patch.object(agent.remote_tool, 'execute_parallel') as mock_execute_parallel:
            # 並列実行の応答を設定
            mock_results = []
            for server in server_configs:
                mock_result = Mock()
                mock_result.status = ToolStatus.SUCCESS
                mock_result.output = f"System status from {server['hostname']}"
                mock_result.server = server['hostname']
                mock_results.append(mock_result)
            
            mock_execute_parallel.return_value = mock_results
            
            # 並列調査を実行
            investigations = agent.investigate_group_parallel('production-group', max_workers=3)
            
            assert len(investigations) == 3
            for investigation in investigations:
                assert investigation.status == 'completed'
                assert investigation.server in [s['hostname'] for s in server_configs]
    
    @pytest.mark.skipif(RemoteAgent is None, reason="RemoteAgent not implemented yet")
    def test_analyze_security_status(self, agent_config):
        """セキュリティ状態分析テスト"""
        agent = RemoteAgent(agent_config)
        
        server_config = {
            'hostname': 'security-check.example.com',
            'username': 'admin',
            'port': 22
        }
        
        with patch.object(agent.remote_tool, 'execute') as mock_execute:
            # セキュリティ関連コマンドの応答
            security_responses = {
                'last -n 20': ('Recent logins...', '', 0),
                'netstat -tuln': ('Open ports: 22, 80, 443', '', 0),
                'ps aux | grep -E "(ssh|httpd|nginx)"': ('Running services...', '', 0),
                'find /etc -name "*.conf" -perm -004': ('World readable configs...', '', 0),
                'iptables -L': ('Firewall rules...', '', 0)
            }
            
            def mock_execute_side_effect(server_config, command, **kwargs):
                result = Mock()
                result.status = ToolStatus.SUCCESS
                result.output, result.error, exit_code = security_responses.get(command, ('', '', 0))
                return result
            
            mock_execute.side_effect = mock_execute_side_effect
            
            # セキュリティ分析を実行
            analysis = agent.analyze_security_status(server_config)
            
            assert analysis.status == 'completed'
            assert 'security_analysis' in analysis.collected_data
            assert 'open_ports' in analysis.collected_data['security_analysis']
            assert 'recent_logins' in analysis.collected_data['security_analysis']
    
    @pytest.mark.skipif(RemoteAgent is None, reason="RemoteAgent not implemented yet")
    def test_auto_remediation(self, agent_config):
        """自動修復テスト"""
        agent = RemoteAgent(agent_config)
        
        server_config = {
            'hostname': 'remediation-test.example.com',
            'username': 'admin',
            'port': 22
        }
        
        # 修復可能な問題を検出
        issue = {
            'type': 'disk_space_warning',
            'severity': 'medium',
            'description': '/tmp directory is 85% full',
            'auto_fixable': True,
            'fix_commands': [
                'find /tmp -type f -mtime +7 -delete',
                'systemctl restart tmpfiles-clean'
            ]
        }
        
        with patch.object(agent.remote_tool, 'execute') as mock_execute:
            mock_result = Mock()
            mock_result.status = ToolStatus.SUCCESS
            mock_result.output = "Cleanup completed"
            mock_execute.return_value = mock_result
            
            # 自動修復を実行
            remediation_result = agent.auto_remediate(server_config, issue)
            
            assert remediation_result['status'] == 'success'
            assert len(remediation_result['applied_fixes']) == 2
            assert all(fix['status'] == 'success' for fix in remediation_result['applied_fixes'])
    
    @pytest.mark.skipif(RemoteAgent is None, reason="RemoteAgent not implemented yet")
    def test_generate_investigation_report(self, agent_config):
        """調査レポート生成テスト"""
        agent = RemoteAgent(agent_config)
        
        # モック調査結果を作成
        investigation = Mock()
        investigation.server = 'report-test.example.com'
        investigation.status = 'completed'
        investigation.start_time = datetime.now()
        investigation.end_time = datetime.now()
        investigation.collected_data = {
            'system_info': {'hostname': 'report-test', 'uptime': '5 days'},
            'performance_analysis': {'cpu_usage': '75%', 'memory_usage': '60%'}
        }
        investigation.findings = [
            {
                'issue_type': 'performance',
                'severity': 'medium',
                'description': 'High CPU usage detected'
            }
        ]
        investigation.recommendations = [
            'Consider upgrading CPU resources',
            'Investigate high CPU processes'
        ]
        
        # レポートを生成
        report = agent.generate_investigation_report(investigation)
        
        assert 'executive_summary' in report
        assert 'system_overview' in report
        assert 'findings_and_issues' in report
        assert 'recommendations' in report
        assert 'technical_details' in report
        assert report['metadata']['server'] == 'report-test.example.com'
    
    @pytest.mark.skipif(RemoteAgent is None, reason="RemoteAgent not implemented yet")
    def test_filter_servers_by_criteria(self, agent_config, server_configs):
        """サーバーフィルタリングテスト"""
        agent = RemoteAgent(agent_config)
        
        # サーバーグループを追加
        agent.add_server_group('all-servers', server_configs)
        
        # タグでフィルタリング
        web_servers = agent.filter_servers_by_criteria(
            'all-servers', 
            tags=['web']
        )
        assert len(web_servers) == 1
        assert web_servers[0]['hostname'] == 'web-server-01.example.com'
        
        # グループでフィルタリング
        db_servers = agent.filter_servers_by_criteria(
            'all-servers',
            group='database-servers'
        )
        assert len(db_servers) == 1
        assert db_servers[0]['hostname'] == 'db-server-01.example.com'
        
        # 複合条件でフィルタリング
        prod_servers = agent.filter_servers_by_criteria(
            'all-servers',
            tags=['production']
        )
        assert len(prod_servers) == 3  # 全サーバーがproductionタグを持つ
    
    @pytest.mark.skipif(RemoteAgent is None, reason="RemoteAgent not implemented yet")
    def test_execution_history_tracking(self, agent_config):
        """実行履歴追跡テスト"""
        agent = RemoteAgent(agent_config)
        
        server_config = {'hostname': 'history-test.example.com', 'username': 'admin'}
        
        with patch.object(agent.remote_tool, 'execute') as mock_execute:
            mock_result = Mock()
            mock_result.status = ToolStatus.SUCCESS
            mock_result.output = "command output"
            mock_result.execution_time = 1.5
            mock_execute.return_value = mock_result
            
            # 複数のコマンドを実行
            commands = ['ps aux', 'df -h', 'netstat -tuln']
            for command in commands:
                agent.execute_on_server(server_config, command)
            
            # 実行履歴を確認
            history = agent.get_execution_history()
            assert len(history) >= len(commands)
            
            # 特定サーバーの履歴を確認
            server_history = agent.get_server_execution_history('history-test.example.com')
            assert len(server_history) == len(commands)
    
    @pytest.mark.skipif(RemoteAgent is None, reason="RemoteAgent not implemented yet")
    def test_concurrent_investigation_limits(self, agent_config, server_configs):
        """同時調査数制限テスト"""
        agent_config['investigation']['max_concurrent_servers'] = 2
        agent = RemoteAgent(agent_config)
        
        # 多数のサーバーで同時調査を開始
        with patch.object(agent, '_investigate_single_server') as mock_investigate:
            mock_investigate.return_value = Mock(status='completed')
            
            # 5台のサーバーで調査を開始（制限は2台）
            investigations = agent.investigate_multiple_servers(server_configs[:5])
            
            # 調査が完了することを確認
            assert len(investigations) == 5
            assert all(inv.status == 'completed' for inv in investigations)
            
            # 並行度が制限されていることを確認（詳細な検証は実装時に）
            assert mock_investigate.call_count == 5


class TestInvestigationResult:
    """InvestigationResultのテストクラス"""
    
    @pytest.mark.skipif(InvestigationResult is None, reason="InvestigationResult not implemented yet")
    def test_investigation_result_creation(self):
        """調査結果オブジェクトの作成テスト"""
        result = InvestigationResult(
            server='test-server.example.com',
            status='completed',
            start_time=datetime.now(),
            collected_data={'system_info': {'hostname': 'test-server'}},
            findings=[{'issue': 'high_cpu', 'severity': 'medium'}]
        )
        
        assert result.server == 'test-server.example.com'
        assert result.status == 'completed'
        assert 'system_info' in result.collected_data
        assert len(result.findings) == 1
        assert result.findings[0]['issue'] == 'high_cpu'
    
    @pytest.mark.skipif(InvestigationResult is None, reason="InvestigationResult not implemented yet")
    def test_investigation_result_serialization(self):
        """調査結果のシリアライゼーションテスト"""
        result = InvestigationResult(
            server='test-server.example.com',
            status='completed',
            collected_data={'uptime': '5 days'},
            findings=[],
            recommendations=['Check memory usage']
        )
        
        # 辞書形式への変換
        result_dict = result.to_dict()
        assert result_dict['server'] == 'test-server.example.com'
        assert result_dict['status'] == 'completed'
        assert 'uptime' in result_dict['collected_data']
        assert len(result_dict['recommendations']) == 1
        
        # JSON形式への変換
        result_json = result.to_json()
        assert isinstance(result_json, str)
        assert 'test-server.example.com' in result_json


class TestServerGroup:
    """ServerGroupのテストクラス"""
    
    @pytest.mark.skipif(ServerGroup is None, reason="ServerGroup not implemented yet")
    def test_server_group_creation(self):
        """サーバーグループの作成テスト"""
        servers = [
            {'hostname': 'server1.example.com', 'tags': ['web']},
            {'hostname': 'server2.example.com', 'tags': ['web']}
        ]
        
        group = ServerGroup(
            name='web-servers',
            servers=servers,
            description='Web server group'
        )
        
        assert group.name == 'web-servers'
        assert len(group.servers) == 2
        assert group.description == 'Web server group'
        assert all('web' in server['tags'] for server in group.servers)
    
    @pytest.mark.skipif(ServerGroup is None, reason="ServerGroup not implemented yet")
    def test_server_group_filtering(self):
        """サーバーグループのフィルタリングテスト"""
        servers = [
            {'hostname': 'web1.example.com', 'tags': ['web', 'production'], 'group': 'frontend'},
            {'hostname': 'web2.example.com', 'tags': ['web', 'staging'], 'group': 'frontend'},
            {'hostname': 'db1.example.com', 'tags': ['database', 'production'], 'group': 'backend'}
        ]
        
        group = ServerGroup('mixed-servers', servers)
        
        # タグでフィルタリング
        production_servers = group.filter_by_tags(['production'])
        assert len(production_servers) == 2
        
        # グループでフィルタリング
        frontend_servers = group.filter_by_group('frontend')
        assert len(frontend_servers) == 2
        
        # 複合条件でフィルタリング
        production_web = group.filter_by_tags(['production', 'web'])
        assert len(production_web) == 1
        assert production_web[0]['hostname'] == 'web1.example.com'


if __name__ == "__main__":
    # RemoteAgentテストの直接実行
    pytest.main([__file__, "-v"])