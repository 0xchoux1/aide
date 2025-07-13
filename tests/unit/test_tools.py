import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from src.tools.base_tool import BaseTool, ToolResult, ToolStatus
from src.tools.system_tool import SystemTool
from src.tools.file_tool import FileTool
from src.tools.network_tool import NetworkTool


class TestBaseTool:
    def test_tool_result_creation(self):
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            output="test output",
            error=None,
            execution_time=1.5
        )
        
        assert result.status == ToolStatus.SUCCESS
        assert result.output == "test output"
        assert result.error is None
        assert result.execution_time == 1.5
        assert result.timestamp is not None
    
    def test_tool_result_to_dict(self):
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            output="test output",
            metadata={'key': 'value'}
        )
        
        result_dict = result.to_dict()
        assert result_dict['status'] == 'success'
        assert result_dict['output'] == 'test output'
        assert result_dict['metadata']['key'] == 'value'
    
    def test_tool_result_to_json(self):
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            output="test output"
        )
        
        json_str = result.to_json()
        assert '"status": "success"' in json_str
        assert '"output": "test output"' in json_str


class MockTool(BaseTool):
    def execute(self, success=True):
        if success:
            result = ToolResult(status=ToolStatus.SUCCESS, output="success")
        else:
            result = ToolResult(status=ToolStatus.FAILED, output="", error="failed")
        
        self._record_execution(result)
        return result


class TestToolHistory:
    def test_execution_history_recording(self):
        tool = MockTool("test_tool")
        
        # 成功実行
        tool.execute(success=True)
        # 失敗実行
        tool.execute(success=False)
        
        assert len(tool.execution_history) == 2
        assert tool.execution_history[0].status == ToolStatus.SUCCESS
        assert tool.execution_history[1].status == ToolStatus.FAILED
    
    def test_execution_stats(self):
        tool = MockTool("test_tool")
        
        # 複数回実行
        for i in range(10):
            tool.execute(success=(i % 2 == 0))  # 半分成功、半分失敗
        
        stats = tool.get_execution_stats()
        assert stats['total_executions'] == 10
        assert stats['success_rate'] == 0.5
        assert 'average_execution_time' in stats
        assert 'last_execution' in stats
        assert 'status_breakdown' in stats
    
    def test_recent_errors(self):
        tool = MockTool("test_tool")
        
        # 成功と失敗を混在させる
        tool.execute(success=True)
        tool.execute(success=False)
        tool.execute(success=False)
        tool.execute(success=True)
        
        recent_errors = tool.get_recent_errors(limit=2)
        assert len(recent_errors) == 2
        assert all(error.status == ToolStatus.FAILED for error in recent_errors)


class TestSystemTool:
    def test_system_tool_initialization(self):
        tool = SystemTool(timeout=60, safe_mode=True)
        assert tool.name == "system_tool"
        assert tool.timeout == 60
        assert tool.safe_mode is True
    
    def test_safe_command_checking(self):
        tool = SystemTool(safe_mode=True)
        
        # 安全なコマンド
        assert tool._is_safe_command("ls -la")
        assert tool._is_safe_command("ps aux")
        assert tool._is_safe_command("df -h")
        
        # 危険なコマンド
        assert not tool._is_safe_command("rm -rf /")
        assert not tool._is_safe_command("sudo shutdown")
        assert not tool._is_safe_command("chmod 777 /etc/passwd")
    
    @patch('subprocess.Popen')
    def test_successful_command_execution(self, mock_popen):
        # モックの設定
        mock_process = Mock()
        mock_process.communicate.return_value = ("output", "")
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        tool = SystemTool(safe_mode=False)  # テスト用に安全モード無効
        result = tool.execute("echo hello")
        
        assert result.status == ToolStatus.SUCCESS
        assert result.output == "output"
        assert result.metadata['return_code'] == 0
    
    @patch('subprocess.Popen')
    def test_failed_command_execution(self, mock_popen):
        # モックの設定
        mock_process = Mock()
        mock_process.communicate.return_value = ("", "error message")
        mock_process.returncode = 1
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        tool = SystemTool(safe_mode=False)
        result = tool.execute("false")  # 常に失敗するコマンド
        
        assert result.status == ToolStatus.FAILED
        assert result.error == "error message"
        assert result.metadata['return_code'] == 1
    
    def test_safe_mode_blocking(self):
        tool = SystemTool(safe_mode=True)
        result = tool.execute("rm dangerous_file")
        
        assert result.status == ToolStatus.PERMISSION_DENIED
        assert "安全でない" in result.error


class TestFileTool:
    def test_file_tool_initialization(self):
        tool = FileTool(safe_mode=True)
        assert tool.name == "file_tool"
        assert tool.safe_mode is True
    
    def test_read_existing_file(self):
        tool = FileTool()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write("test content\nline 2")
            temp_path = f.name
        
        try:
            result = tool.read_file(temp_path)
            assert result.status == ToolStatus.SUCCESS
            assert result.output == "test content\nline 2"
            assert result.metadata['line_count'] == 2
        finally:
            os.unlink(temp_path)
    
    def test_read_nonexistent_file(self):
        tool = FileTool()
        result = tool.read_file("/nonexistent/file.txt")
        
        assert result.status == ToolStatus.NOT_FOUND
        assert "見つかりません" in result.error
    
    def test_write_file(self):
        tool = FileTool()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test_file.txt")
            result = tool.write_file(file_path, "test content")
            
            assert result.status == ToolStatus.SUCCESS
            assert os.path.exists(file_path)
            
            # ファイル内容の確認
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert content == "test content"
    
    def test_list_directory(self):
        tool = FileTool()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # テストファイルを作成
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("test")
            
            result = tool.list_directory(temp_dir)
            
            assert result.status == ToolStatus.SUCCESS
            assert "test.txt" in result.output
            assert result.metadata['total_items'] == 1
    
    def test_protected_path_check(self):
        tool = FileTool(safe_mode=True)
        
        # 保護されたパス
        assert tool._is_protected_path(Path("/etc/passwd"))
        assert tool._is_protected_path(Path("/bin/bash"))
        
        # 保護されていないパス
        assert not tool._is_protected_path(Path("/tmp/test.txt"))
        assert not tool._is_protected_path(Path("/home/user/file.txt"))


class TestNetworkTool:
    def test_network_tool_initialization(self):
        tool = NetworkTool(timeout=15)
        assert tool.name == "network_tool"
        assert tool.timeout == 15
    
    def test_valid_host_checking(self):
        tool = NetworkTool()
        
        # 有効なIPアドレス
        assert tool._is_valid_host("192.168.1.1")
        assert tool._is_valid_host("8.8.8.8")
        
        # 有効なホスト名
        assert tool._is_valid_host("example.com")
        assert tool._is_valid_host("sub.example.org")
        
        # 無効な形式
        assert not tool._is_valid_host("invalid..host")
        assert not tool._is_valid_host("-invalid-host")
        assert not tool._is_valid_host("host-")
    
    @patch('subprocess.run')
    def test_successful_ping(self, mock_run):
        # モックの設定
        mock_run.return_value = Mock(
            returncode=0,
            stdout="PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.\n64 bytes from 8.8.8.8: icmp_seq=1 time=10.0 ms\n--- 8.8.8.8 ping statistics ---\n1 packets transmitted, 1 received, 0% packet loss, time 0ms\nround-trip min/avg/max/stddev = 10.0/10.0/10.0/0.0 ms",
            stderr=""
        )
        
        tool = NetworkTool()
        result = tool.ping("8.8.8.8", count=1)
        
        assert result.status == ToolStatus.SUCCESS
        assert "8.8.8.8" in result.output
        assert result.metadata['host'] == "8.8.8.8"
    
    @patch('subprocess.run')
    def test_failed_ping(self, mock_run):
        # モックの設定
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="ping: cannot resolve example.invalid: Name or service not known"
        )
        
        tool = NetworkTool()
        result = tool.ping("example.invalid")
        
        assert result.status == ToolStatus.FAILED
        assert result.error is not None
    
    @patch('socket.socket')
    def test_port_scan(self, mock_socket):
        # モックの設定
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0  # 接続成功
        mock_socket.return_value = mock_sock
        
        tool = NetworkTool()
        result = tool.port_scan("localhost", [80])
        
        assert result.status == ToolStatus.SUCCESS
        assert result.metadata['open_ports'] == [80]
        assert len(result.metadata['scan_results']) == 1
    
    @patch('socket.gethostbyname_ex')
    def test_dns_lookup(self, mock_gethostbyname):
        # モックの設定
        mock_gethostbyname.return_value = ("example.com", [], ["93.184.216.34"])
        
        tool = NetworkTool()
        result = tool.dns_lookup("example.com")
        
        assert result.status == ToolStatus.SUCCESS
        assert "93.184.216.34" in result.output
        assert result.metadata['ip_addresses'] == ["93.184.216.34"]