"""
AIDE ダッシュボードサーバー

Webベースのメトリクスダッシュボードを提供
"""

import json
import asyncio
import threading
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Web フレームワーク（軽量版実装）
try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs
    import socketserver
    WEB_SERVER_AVAILABLE = True
except ImportError:
    WEB_SERVER_AVAILABLE = False

from ..config import get_config_manager
from ..logging import get_logger
from .metrics_collector import get_metrics_collector, MetricsCollector


@dataclass
class DashboardConfig:
    """ダッシュボード設定"""
    host: str = "localhost"
    port: int = 8080
    title: str = "AIDE Dashboard"
    refresh_interval: int = 30  # 秒
    max_data_points: int = 100
    enable_realtime: bool = True
    enable_alerts: bool = True
    theme: str = "dark"  # dark, light


class MetricsEndpoint:
    """メトリクスAPI エンドポイント"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.logger = get_logger(__name__)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """現在のメトリクス取得"""
        all_metrics = self.metrics_collector.get_all_metrics()
        
        current_data = {
            "timestamp": time.time(),
            "metrics": {}
        }
        
        for name, series in all_metrics.items():
            latest = series.get_latest()
            stats = series.calculate_stats()
            
            current_data["metrics"][name] = {
                "name": name,
                "type": series.metric_type.value,
                "description": series.description,
                "unit": series.unit,
                "current_value": latest.value if latest else None,
                "timestamp": latest.timestamp if latest else None,
                "statistics": stats
            }
        
        return current_data
    
    def get_metric_history(self, metric_name: str, 
                          duration_minutes: int = 60) -> Dict[str, Any]:
        """メトリクス履歴取得"""
        series = self.metrics_collector.get_metric_series(metric_name)
        
        if not series:
            return {"error": f"Metric not found: {metric_name}"}
        
        # 指定期間のデータポイント取得
        end_time = time.time()
        start_time = end_time - (duration_minutes * 60)
        points = series.get_points_in_range(start_time, end_time)
        
        return {
            "metric_name": metric_name,
            "type": series.metric_type.value,
            "description": series.description,
            "unit": series.unit,
            "start_time": start_time,
            "end_time": end_time,
            "data_points": [point.to_dict() for point in points],
            "statistics": series.calculate_stats(duration_minutes * 60)
        }
    
    def get_system_overview(self) -> Dict[str, Any]:
        """システム概要取得"""
        current_metrics = self.get_current_metrics()["metrics"]
        
        overview = {
            "system_status": "healthy",  # 後でロジック実装
            "uptime": time.time(),  # 簡易実装
            "total_metrics": len(current_metrics),
            "last_update": time.time(),
            "key_metrics": {}
        }
        
        # 主要メトリクス抽出
        key_metric_names = [
            "system_cpu_usage",
            "system_memory_usage", 
            "system_disk_usage",
            "health_score",
            "response_time"
        ]
        
        for metric_name in key_metric_names:
            if metric_name in current_metrics:
                overview["key_metrics"][metric_name] = current_metrics[metric_name]
        
        return overview


class DashboardHTTPHandler(BaseHTTPRequestHandler):
    """ダッシュボード HTTP ハンドラー"""
    
    def __init__(self, *args, metrics_endpoint=None, config=None, **kwargs):
        self.metrics_endpoint = metrics_endpoint
        self.config = config or DashboardConfig()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """GET リクエスト処理"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        params = parse_qs(parsed_path.query)
        
        try:
            if path == "/" or path == "/dashboard":
                self._serve_dashboard_html()
            elif path == "/api/metrics":
                self._serve_current_metrics()
            elif path == "/api/metrics/history":
                self._serve_metrics_history(params)
            elif path == "/api/overview":
                self._serve_system_overview()
            elif path.startswith("/static/"):
                self._serve_static_file(path)
            else:
                self._send_404()
        except Exception as e:
            self._send_error(500, str(e))
    
    def _serve_dashboard_html(self):
        """ダッシュボードHTML配信"""
        html_content = self._generate_dashboard_html()
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def _serve_current_metrics(self):
        """現在のメトリクス配信"""
        if not self.metrics_endpoint:
            self._send_error(500, "Metrics endpoint not available")
            return
        
        data = self.metrics_endpoint.get_current_metrics()
        self._send_json_response(data)
    
    def _serve_metrics_history(self, params):
        """メトリクス履歴配信"""
        if not self.metrics_endpoint:
            self._send_error(500, "Metrics endpoint not available")
            return
        
        metric_name = params.get('metric', [''])[0]
        duration = int(params.get('duration', ['60'])[0])
        
        if not metric_name:
            self._send_error(400, "metric parameter required")
            return
        
        data = self.metrics_endpoint.get_metric_history(metric_name, duration)
        self._send_json_response(data)
    
    def _serve_system_overview(self):
        """システム概要配信"""
        if not self.metrics_endpoint:
            self._send_error(500, "Metrics endpoint not available")
            return
        
        data = self.metrics_endpoint.get_system_overview()
        self._send_json_response(data)
    
    def _serve_static_file(self, path):
        """静的ファイル配信"""
        # 簡易実装（実際は適切な静的ファイル配信が必要）
        self._send_404()
    
    def _send_json_response(self, data):
        """JSON レスポンス送信"""
        json_data = json.dumps(data, default=str, ensure_ascii=False)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))
    
    def _send_404(self):
        """404エラー送信"""
        self.send_response(404)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h1>404 Not Found</h1>')
    
    def _send_error(self, code, message):
        """エラーレスポンス送信"""
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        error_data = {"error": message, "code": code}
        self.wfile.write(json.dumps(error_data).encode('utf-8'))
    
    def _generate_dashboard_html(self) -> str:
        """ダッシュボードHTML生成"""
        return f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.title}</title>
    <style>
        {self._get_dashboard_css()}
    </style>
</head>
<body class="{self.config.theme}">
    <div class="dashboard">
        <header>
            <h1>{self.config.title}</h1>
            <div class="status-indicator" id="status">●</div>
        </header>
        
        <div class="overview-section">
            <div class="metric-card" id="cpu-card">
                <h3>CPU使用率</h3>
                <div class="metric-value" id="cpu-value">--%</div>
            </div>
            
            <div class="metric-card" id="memory-card">
                <h3>メモリ使用率</h3>
                <div class="metric-value" id="memory-value">--%</div>
            </div>
            
            <div class="metric-card" id="disk-card">
                <h3>ディスク使用率</h3>
                <div class="metric-value" id="disk-value">--%</div>
            </div>
            
            <div class="metric-card" id="health-card">
                <h3>ヘルススコア</h3>
                <div class="metric-value" id="health-value">--</div>
            </div>
        </div>
        
        <div class="charts-section">
            <div class="chart-container">
                <h3>システムメトリクス (時系列)</h3>
                <canvas id="system-chart"></canvas>
            </div>
            
            <div class="chart-container">
                <h3>パフォーマンスメトリクス</h3>
                <canvas id="performance-chart"></canvas>
            </div>
        </div>
        
        <div class="details-section">
            <h3>詳細メトリクス</h3>
            <div id="metrics-table"></div>
        </div>
    </div>
    
    <script>
        {self._get_dashboard_js()}
    </script>
</body>
</html>
        """
    
    def _get_dashboard_css(self) -> str:
        """ダッシュボードCSS"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
        }
        
        .dark {
            background-color: #1a1a1a;
            color: #e0e0e0;
        }
        
        .light {
            background-color: #f5f5f5;
            color: #333;
        }
        
        .dashboard {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #333;
        }
        
        .dark header {
            border-bottom-color: #333;
        }
        
        .light header {
            border-bottom-color: #ddd;
        }
        
        h1 {
            font-size: 2.5rem;
            font-weight: 300;
        }
        
        .status-indicator {
            font-size: 2rem;
            color: #4CAF50;
        }
        
        .overview-section {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .light .metric-card {
            background: rgba(0, 0, 0, 0.05);
            border-color: rgba(0, 0, 0, 0.1);
        }
        
        .metric-card h3 {
            margin-bottom: 10px;
            color: #888;
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #4CAF50;
        }
        
        .charts-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .chart-container {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .light .chart-container {
            background: rgba(0, 0, 0, 0.05);
            border-color: rgba(0, 0, 0, 0.1);
        }
        
        .chart-container h3 {
            margin-bottom: 15px;
            color: #888;
        }
        
        canvas {
            width: 100%;
            height: 300px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 5px;
        }
        
        .details-section {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .light .details-section {
            background: rgba(0, 0, 0, 0.05);
            border-color: rgba(0, 0, 0, 0.1);
        }
        
        .details-section h3 {
            margin-bottom: 15px;
            color: #888;
        }
        
        #metrics-table {
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .light th, .light td {
            border-bottom-color: rgba(0, 0, 0, 0.1);
        }
        
        th {
            background: rgba(255, 255, 255, 0.1);
            font-weight: 600;
        }
        
        .light th {
            background: rgba(0, 0, 0, 0.05);
        }
        
        @media (max-width: 768px) {
            .charts-section {
                grid-template-columns: 1fr;
            }
            
            h1 {
                font-size: 2rem;
            }
        }
        """
    
    def _get_dashboard_js(self) -> str:
        """ダッシュボードJavaScript"""
        return f"""
        class AIDEDashboard {{
            constructor() {{
                this.refreshInterval = {self.config.refresh_interval * 1000};
                this.init();
            }}
            
            init() {{
                this.updateMetrics();
                setInterval(() => this.updateMetrics(), this.refreshInterval);
            }}
            
            async updateMetrics() {{
                try {{
                    const response = await fetch('/api/metrics');
                    const data = await response.json();
                    
                    this.updateOverview(data.metrics);
                    this.updateStatus('healthy');
                    this.updateDetailsTable(data.metrics);
                    
                }} catch (error) {{
                    console.error('メトリクス更新エラー:', error);
                    this.updateStatus('error');
                }}
            }}
            
            updateOverview(metrics) {{
                // CPU使用率
                if (metrics.system_cpu_usage) {{
                    document.getElementById('cpu-value').textContent = 
                        metrics.system_cpu_usage.current_value.toFixed(1) + '%';
                }}
                
                // メモリ使用率
                if (metrics.system_memory_usage) {{
                    document.getElementById('memory-value').textContent = 
                        metrics.system_memory_usage.current_value.toFixed(1) + '%';
                }}
                
                // ディスク使用率
                if (metrics.system_disk_usage) {{
                    document.getElementById('disk-value').textContent = 
                        metrics.system_disk_usage.current_value.toFixed(1) + '%';
                }}
                
                // ヘルススコア
                if (metrics.health_score) {{
                    document.getElementById('health-value').textContent = 
                        metrics.health_score.current_value.toFixed(0);
                }}
            }}
            
            updateStatus(status) {{
                const indicator = document.getElementById('status');
                if (status === 'healthy') {{
                    indicator.style.color = '#4CAF50';
                    indicator.title = 'システム正常';
                }} else {{
                    indicator.style.color = '#F44336';
                    indicator.title = 'システム異常';
                }}
            }}
            
            updateDetailsTable(metrics) {{
                const container = document.getElementById('metrics-table');
                
                let html = `
                    <table>
                        <thead>
                            <tr>
                                <th>メトリクス名</th>
                                <th>現在値</th>
                                <th>単位</th>
                                <th>説明</th>
                                <th>最終更新</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                Object.values(metrics).forEach(metric => {{
                    const timestamp = metric.timestamp ? 
                        new Date(metric.timestamp * 1000).toLocaleTimeString() : '-';
                    const value = metric.current_value !== null ? 
                        metric.current_value.toFixed(2) : '-';
                    const unit = metric.unit || '';
                    
                    html += `
                        <tr>
                            <td>${{metric.name}}</td>
                            <td>${{value}}</td>
                            <td>${{unit}}</td>
                            <td>${{metric.description}}</td>
                            <td>${{timestamp}}</td>
                        </tr>
                    `;
                }});
                
                html += '</tbody></table>';
                container.innerHTML = html;
            }}
        }}
        
        // ダッシュボード初期化
        document.addEventListener('DOMContentLoaded', () => {{
            new AIDEDashboard();
        }});
        """
    
    def log_message(self, format, *args):
        """ログメッセージ（標準出力抑制）"""
        pass


class DashboardServer:
    """ダッシュボードサーバー"""
    
    def __init__(self, config: Optional[DashboardConfig] = None, 
                 metrics_collector: Optional[MetricsCollector] = None):
        self.config = config or DashboardConfig()
        self.metrics_collector = metrics_collector or get_metrics_collector()
        self.logger = get_logger(__name__)
        
        # API エンドポイント
        self.metrics_endpoint = MetricsEndpoint(self.metrics_collector)
        
        # サーバー
        self.server = None
        self.server_thread = None
        self.is_running = False
    
    def start(self):
        """サーバー開始"""
        if not WEB_SERVER_AVAILABLE:
            self.logger.error("Web サーバー機能が利用できません")
            return False
        
        if self.is_running:
            self.logger.warning("サーバーは既に起動中です")
            return True
        
        try:
            # ハンドラーファクトリー
            def handler_factory(*args, **kwargs):
                return DashboardHTTPHandler(
                    *args,
                    metrics_endpoint=self.metrics_endpoint,
                    config=self.config,
                    **kwargs
                )
            
            # サーバー作成
            self.server = HTTPServer((self.config.host, self.config.port), handler_factory)
            
            # バックグラウンドスレッドで起動
            self.server_thread = threading.Thread(
                target=self.server.serve_forever,
                daemon=True
            )
            self.server_thread.start()
            
            self.is_running = True
            self.logger.info(f"ダッシュボードサーバー開始: http://{self.config.host}:{self.config.port}")
            
            # メトリクス収集も開始
            self.metrics_collector.start_collection()
            
            return True
            
        except Exception as e:
            self.logger.error(f"サーバー開始エラー: {str(e)}")
            return False
    
    def stop(self):
        """サーバー停止"""
        if not self.is_running:
            return
        
        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
            
            if self.server_thread:
                self.server_thread.join(timeout=5.0)
            
            # メトリクス収集停止
            self.metrics_collector.stop_collection()
            
            self.is_running = False
            self.logger.info("ダッシュボードサーバー停止")
            
        except Exception as e:
            self.logger.error(f"サーバー停止エラー: {str(e)}")
    
    def get_url(self) -> str:
        """ダッシュボードURL取得"""
        return f"http://{self.config.host}:{self.config.port}"


# WebSocketハンドラー（将来の拡張用）
class WebSocketHandler:
    """WebSocket ハンドラー（リアルタイム更新用）"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.clients: Set[Any] = set()
        self.logger = get_logger(__name__)
    
    async def handle_connection(self, websocket, path):
        """WebSocket接続処理"""
        self.clients.add(websocket)
        self.logger.info(f"WebSocket クライアント接続: {len(self.clients)} 接続中")
        
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
            self.logger.info(f"WebSocket クライアント切断: {len(self.clients)} 接続中")
    
    async def broadcast_metrics(self):
        """メトリクス配信"""
        if not self.clients:
            return
        
        current_metrics = self.metrics_collector.get_all_metrics()
        
        # 配信データ作成
        data = {
            "type": "metrics_update",
            "timestamp": time.time(),
            "metrics": {}
        }
        
        for name, series in current_metrics.items():
            latest = series.get_latest()
            if latest:
                data["metrics"][name] = {
                    "value": latest.value,
                    "timestamp": latest.timestamp
                }
        
        # 全クライアントに配信
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(json.dumps(data))
            except:
                disconnected_clients.add(client)
        
        # 切断されたクライアントを削除
        self.clients -= disconnected_clients


# 便利関数
def create_dashboard_server(host: str = "localhost", port: int = 8080) -> DashboardServer:
    """ダッシュボードサーバー作成"""
    config = DashboardConfig(host=host, port=port)
    return DashboardServer(config)