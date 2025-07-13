import socket
import subprocess
import time
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from .base_tool import BaseTool, ToolResult, ToolStatus


class NetworkTool(BaseTool):
    """ネットワーク診断ツール"""
    
    def __init__(self, timeout: int = 10):
        super().__init__(
            name="network_tool",
            description="ネットワーク接続とサービスの診断ツール"
        )
        self.timeout = timeout
    
    def execute(self, operation: str, *args, **kwargs) -> ToolResult:
        """ネットワーク操作を実行"""
        if operation == "ping":
            return self.ping(*args, **kwargs)
        elif operation == "port_scan":
            return self.port_scan(*args, **kwargs)
        elif operation == "dns_lookup":
            return self.dns_lookup(*args, **kwargs)
        elif operation == "http_test":
            return self.test_http_connection(*args, **kwargs)
        elif operation == "connectivity_check":
            return self.check_network_connectivity(*args, **kwargs)
        else:
            return ToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"未対応の操作: {operation}",
                execution_time=0.0
            )
    
    def ping(self, host: str, count: int = 4) -> ToolResult:
        """pingによる接続テスト"""
        start_time = time.time()
        
        try:
            # ホスト名のバリデーション
            if not self._is_valid_host(host):
                return ToolResult(
                    status=ToolStatus.FAILED,
                    output="",
                    error=f"無効なホスト名またはIPアドレス: {host}",
                    execution_time=time.time() - start_time
                )
            
            # pingコマンド実行
            cmd = f"ping -c {count} {host}"
            process = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            # 結果解析
            if process.returncode == 0:
                # ping統計を抽出
                output = process.stdout
                stats = self._parse_ping_output(output)
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=output,
                    execution_time=time.time() - start_time,
                    metadata={
                        'host': host,
                        'count': count,
                        'stats': stats
                    }
                )
            else:
                return ToolResult(
                    status=ToolStatus.FAILED,
                    output=process.stdout,
                    error=process.stderr,
                    execution_time=time.time() - start_time,
                    metadata={'host': host, 'count': count}
                )
                
        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.TIMEOUT,
                output="",
                error=f"ping がタイムアウトしました ({self.timeout}秒)",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"ping実行エラー: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def port_scan(self, host: str, ports: List[int]) -> ToolResult:
        """ポートスキャン"""
        start_time = time.time()
        
        try:
            if not self._is_valid_host(host):
                return ToolResult(
                    status=ToolStatus.FAILED,
                    output="",
                    error=f"無効なホスト名またはIPアドレス: {host}",
                    execution_time=time.time() - start_time
                )
            
            open_ports = []
            closed_ports = []
            scan_results = []
            
            for port in ports:
                port_start = time.time()
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)  # 2秒タイムアウト
                    result = sock.connect_ex((host, port))
                    sock.close()
                    
                    port_time = time.time() - port_start
                    
                    if result == 0:
                        open_ports.append(port)
                        scan_results.append({
                            'port': port,
                            'status': 'open',
                            'response_time': port_time
                        })
                    else:
                        closed_ports.append(port)
                        scan_results.append({
                            'port': port,
                            'status': 'closed',
                            'response_time': port_time
                        })
                        
                except Exception as e:
                    scan_results.append({
                        'port': port,
                        'status': 'error',
                        'error': str(e),
                        'response_time': time.time() - port_start
                    })
            
            # 結果のフォーマット
            output_lines = [f"ポートスキャン結果 for {host}:"]
            for result in scan_results:
                if result['status'] == 'open':
                    output_lines.append(f"  ポート {result['port']}: 開いています ({result['response_time']:.3f}s)")
                elif result['status'] == 'closed':
                    output_lines.append(f"  ポート {result['port']}: 閉じています")
                else:
                    output_lines.append(f"  ポート {result['port']}: エラー - {result.get('error', 'unknown')}")
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output='\n'.join(output_lines),
                execution_time=time.time() - start_time,
                metadata={
                    'host': host,
                    'total_ports': len(ports),
                    'open_ports': open_ports,
                    'closed_ports': closed_ports,
                    'scan_results': scan_results
                }
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"ポートスキャンエラー: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def dns_lookup(self, hostname: str) -> ToolResult:
        """DNS名前解決"""
        start_time = time.time()
        
        try:
            # 前方解決（ホスト名 -> IPアドレス）
            try:
                ip_addresses = socket.gethostbyname_ex(hostname)
                resolved_ips = ip_addresses[2]
            except socket.gaierror as e:
                return ToolResult(
                    status=ToolStatus.FAILED,
                    output="",
                    error=f"DNS解決失敗: {str(e)}",
                    execution_time=time.time() - start_time
                )
            
            # 逆引き（IPアドレス -> ホスト名）
            reverse_lookups = []
            for ip in resolved_ips:
                try:
                    reverse_name = socket.gethostbyaddr(ip)[0]
                    reverse_lookups.append({
                        'ip': ip,
                        'hostname': reverse_name
                    })
                except socket.herror:
                    reverse_lookups.append({
                        'ip': ip,
                        'hostname': None
                    })
            
            # 結果のフォーマット
            output_lines = [f"DNS解決結果 for {hostname}:"]
            output_lines.append(f"  IPアドレス: {', '.join(resolved_ips)}")
            output_lines.append("  逆引き結果:")
            for lookup in reverse_lookups:
                if lookup['hostname']:
                    output_lines.append(f"    {lookup['ip']} -> {lookup['hostname']}")
                else:
                    output_lines.append(f"    {lookup['ip']} -> (逆引き不可)")
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output='\n'.join(output_lines),
                execution_time=time.time() - start_time,
                metadata={
                    'hostname': hostname,
                    'ip_addresses': resolved_ips,
                    'reverse_lookups': reverse_lookups
                }
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"DNS解決エラー: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def test_http_connection(self, url: str, timeout: Optional[int] = None) -> ToolResult:
        """HTTP接続テスト"""
        start_time = time.time()
        timeout = timeout or self.timeout
        
        try:
            # URLの解析
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ToolResult(
                    status=ToolStatus.FAILED,
                    output="",
                    error=f"無効なURL: {url}",
                    execution_time=time.time() - start_time
                )
            
            # curlコマンドでHTTP接続テスト
            cmd = [
                'curl',
                '-s',  # サイレントモード
                '-w', '%{http_code},%{time_total},%{time_namelookup},%{time_connect},%{size_download}',
                '-o', '/dev/null',  # レスポンスボディは破棄
                '--max-time', str(timeout),
                url
            ]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 5  # curlのタイムアウト + 余裕
            )
            
            if process.returncode == 0:
                # curl出力をパース
                stats = process.stdout.strip().split(',')
                if len(stats) >= 5:
                    http_code = int(stats[0])
                    total_time = float(stats[1])
                    dns_time = float(stats[2])
                    connect_time = float(stats[3])
                    size = int(float(stats[4]))
                    
                    # HTTPステータスで成功/失敗を判定
                    if 200 <= http_code < 400:
                        status = ToolStatus.SUCCESS
                        error = None
                    else:
                        status = ToolStatus.FAILED
                        error = f"HTTPエラー: {http_code}"
                    
                    output = f"HTTP接続テスト成功: {url}\n"
                    output += f"  HTTPステータス: {http_code}\n"
                    output += f"  レスポンス時間: {total_time:.3f}s\n"
                    output += f"  DNS解決時間: {dns_time:.3f}s\n"
                    output += f"  接続時間: {connect_time:.3f}s\n"
                    output += f"  レスポンスサイズ: {size} bytes"
                    
                    return ToolResult(
                        status=status,
                        output=output,
                        error=error,
                        execution_time=time.time() - start_time,
                        metadata={
                            'url': url,
                            'http_code': http_code,
                            'total_time': total_time,
                            'dns_time': dns_time,
                            'connect_time': connect_time,
                            'response_size': size
                        }
                    )
                else:
                    return ToolResult(
                        status=ToolStatus.FAILED,
                        output="",
                        error="curl出力の解析に失敗",
                        execution_time=time.time() - start_time
                    )
            else:
                return ToolResult(
                    status=ToolStatus.FAILED,
                    output="",
                    error=f"HTTP接続失敗: {process.stderr}",
                    execution_time=time.time() - start_time
                )
                
        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.TIMEOUT,
                output="",
                error=f"HTTP接続がタイムアウト ({timeout}秒)",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                output="",
                error=f"HTTP接続テストエラー: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def check_network_connectivity(self) -> ToolResult:
        """基本的なネットワーク接続性チェック"""
        start_time = time.time()
        
        # テスト対象
        tests = [
            ('Google DNS', 'ping', '8.8.8.8'),
            ('Cloudflare DNS', 'ping', '1.1.1.1'),
            ('Google HTTP', 'http', 'https://www.google.com'),
            ('GitHub HTTP', 'http', 'https://github.com')
        ]
        
        results = []
        for name, test_type, target in tests:
            if test_type == 'ping':
                result = self.ping(target, count=2)
            elif test_type == 'http':
                result = self.test_http_connection(target, timeout=5)
            
            results.append({
                'name': name,
                'type': test_type,
                'target': target,
                'status': result.status.value,
                'success': result.status == ToolStatus.SUCCESS,
                'execution_time': result.execution_time,
                'error': result.error
            })
        
        # 結果集約
        successful_tests = sum(1 for r in results if r['success'])
        total_tests = len(results)
        
        output_lines = ["ネットワーク接続性チェック結果:"]
        for result in results:
            status_icon = "✓" if result['success'] else "✗"
            output_lines.append(f"  {status_icon} {result['name']}: {result['status']}")
            if result['error']:
                output_lines.append(f"    エラー: {result['error']}")
        
        output_lines.append(f"\n成功: {successful_tests}/{total_tests}")
        
        overall_status = ToolStatus.SUCCESS if successful_tests == total_tests else ToolStatus.FAILED
        
        return ToolResult(
            status=overall_status,
            output='\n'.join(output_lines),
            execution_time=time.time() - start_time,
            metadata={
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate': successful_tests / total_tests,
                'detailed_results': results
            }
        )
    
    def _is_valid_host(self, host: str) -> bool:
        """ホスト名/IPアドレスの妥当性チェック"""
        # IPアドレス形式かチェック
        try:
            socket.inet_aton(host)
            return True
        except socket.error:
            pass
        
        # ホスト名として有効かチェック（より厳密）
        if not re.match(r'^[a-zA-Z0-9.-]+$', host):
            return False
        if host.startswith('-') or host.endswith('-'):
            return False
        if '..' in host:  # 連続するドットは無効
            return False
        if host.startswith('.') or host.endswith('.'):
            return False
        
        return True
    
    def _parse_ping_output(self, output: str) -> Dict[str, Any]:
        """ping出力を解析して統計を抽出"""
        stats = {}
        
        # パケット統計を抽出
        packet_pattern = r'(\d+) packets transmitted, (\d+) (?:packets )?received'
        packet_match = re.search(packet_pattern, output)
        if packet_match:
            transmitted = int(packet_match.group(1))
            received = int(packet_match.group(2))
            stats['packets_transmitted'] = transmitted
            stats['packets_received'] = received
            stats['packet_loss'] = ((transmitted - received) / transmitted) * 100 if transmitted > 0 else 100
        
        # RTT統計を抽出
        rtt_pattern = r'round-trip min/avg/max/stddev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms'
        rtt_match = re.search(rtt_pattern, output)
        if rtt_match:
            stats['rtt_min'] = float(rtt_match.group(1))
            stats['rtt_avg'] = float(rtt_match.group(2))
            stats['rtt_max'] = float(rtt_match.group(3))
            stats['rtt_stddev'] = float(rtt_match.group(4))
        
        return stats