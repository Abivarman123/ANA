"""Improved real-time monitoring dashboard for ANA performance metrics."""

import json
import logging
import threading
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from .monitoring import get_metrics_collector


class ImprovedMonitoringDashboard:
    """Enhanced web-based dashboard for monitoring ANA performance."""

    def __init__(self, port: int = 8080):
        self.port = port
        self.logger = logging.getLogger("ana.dashboard")
        self.metrics_collector = get_metrics_collector()
        self.setup_error_logging()

    def setup_error_logging(self):
        """Setup error logging to logs folder."""
        # Find project root
        import sys
        if hasattr(sys, '_MEIPASS'):
            project_root = Path(sys.executable).parent
        else:
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
        
        logs_dir = project_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        error_log_file = logs_dir / "dashboard.log"
        
        # Create file handler
        error_handler = logging.FileHandler(error_log_file)
        error_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        error_handler.setFormatter(formatter)
        
        self.logger.handlers.clear()
        self.logger.addHandler(error_handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

    def get_html_template(self) -> str:
        """Generate enhanced HTML template."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ANA Performance Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .dashboard { max-width: 1600px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.4);
            text-align: center;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }
        .live-indicator {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 0.4em;
            background: rgba(16, 185, 129, 0.2);
            padding: 8px 16px;
            border-radius: 20px;
            border: 2px solid #10b981;
        }
        .live-dot {
            width: 10px;
            height: 10px;
            background: #10b981;
            border-radius: 50%;
            animation: blink 2s ease-in-out infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        .metric-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            padding: 25px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: transform 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 48px rgba(102, 126, 234, 0.3);
        }
        .metric-value {
            font-size: 2.8em;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        .metric-label {
            color: #a0a0a0;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .chart-container {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            padding: 25px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 25px;
        }
        .chart-container h3 {
            color: #e0e0e0;
            margin-bottom: 20px;
            font-size: 1.3em;
        }
        .logs-container {
            background: rgba(0, 0, 0, 0.4);
            padding: 20px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 25px;
            max-height: 400px;
            overflow-y: auto;
        }
        .log-entry {
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 5px;
            background: rgba(255, 255, 255, 0.03);
            border-left: 3px solid #667eea;
        }
        .refresh-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
            transition: transform 0.2s ease;
        }
        .refresh-btn:hover { transform: translateY(-2px); }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.05); }
        ::-webkit-scrollbar-thumb { background: rgba(102, 126, 234, 0.5); border-radius: 10px; }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>
                ANA Performance Monitor
                <span class="live-indicator">
                    <span class="live-dot"></span>
                    LIVE
                </span>
            </h1>
            <p style="margin: 15px 0;">Real-time performance metrics and telemetry</p>
            <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Now</button>
            <p style="margin: 15px 0; font-size: 0.9em; opacity: 0.7;">
                Auto-refresh: Every 2 seconds | Last: <span id="last-refresh">-</span>
            </p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value" id="total-turns">0</div>
                <div class="metric-label">Total Turns</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="avg-latency">0.00s</div>
                <div class="metric-label">Avg Latency</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="token-rate">0.0</div>
                <div class="metric-label">Tokens/sec</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="error-count">0</div>
                <div class="metric-label">Total Errors</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="session-duration">0s</div>
                <div class="metric-label">Session Duration</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="tool-calls">0</div>
                <div class="metric-label">Tool Calls</div>
            </div>
        </div>
        
        <div class="logs-container">
            <h3>📋 Recent Activity Logs</h3>
            <div id="logs-content">
                <div class="log-entry">Waiting for activity...</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3>📊 Latency Trend</h3>
            <canvas id="latencyChart"></canvas>
        </div>
        
        <div class="chart-container">
            <h3>🔤 Token Generation Rate</h3>
            <canvas id="tokenChart"></canvas>
        </div>
    </div>

    <script>
        let latencyChart, tokenChart;
        let logs = [];
        
        function initCharts() {
            const chartOptions = {
                responsive: true,
                plugins: { legend: { labels: { color: '#e0e0e0' } } },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#a0a0a0' } },
                    x: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#a0a0a0' } }
                }
            };
            
            latencyChart = new Chart(document.getElementById('latencyChart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Latency (s)',
                        data: [],
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102,126,234,0.2)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: chartOptions
            });
            
            tokenChart = new Chart(document.getElementById('tokenChart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Tokens/sec',
                        data: [],
                        borderColor: '#764ba2',
                        backgroundColor: 'rgba(118,75,162,0.2)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: chartOptions
            });
        }
        
        function updateMetrics(data) {
            // Debug logging
            console.log('Dashboard received data:', data);
            if (data.debug) {
                console.log('Debug info:', data.debug);
            }
            
            document.getElementById('total-turns').textContent = data.total_turns || 0;
            document.getElementById('avg-latency').textContent = (data.avg_latency || 0).toFixed(2) + 's';
            document.getElementById('token-rate').textContent = (data.avg_tokens_per_second || 0).toFixed(1);
            document.getElementById('error-count').textContent = data.total_errors || 0;
            document.getElementById('tool-calls').textContent = data.total_tool_calls || 0;
            
            const duration = Math.floor(data.session_duration || 0);
            const hours = Math.floor(duration / 3600);
            const minutes = Math.floor((duration % 3600) / 60);
            const seconds = duration % 60;
            let durationStr = '';
            if (hours > 0) durationStr += hours + 'h ';
            if (minutes > 0) durationStr += minutes + 'm ';
            durationStr += seconds + 's';
            document.getElementById('session-duration').textContent = durationStr;
            
            if (data.detailed_metrics) {
                updateCharts(data.detailed_metrics);
                updateLogs(data);
            }
            
            document.getElementById('last-refresh').textContent = new Date().toLocaleTimeString();
        }
        
        function updateCharts(metrics) {
            const recent = metrics.slice(-20);
            latencyChart.data.labels = recent.map((_, i) => `T${i + 1}`);
            latencyChart.data.datasets[0].data = recent.map(m => m.total_latency || 0);
            latencyChart.update();
            
            tokenChart.data.labels = recent.map((_, i) => `T${i + 1}`);
            tokenChart.data.datasets[0].data = recent.map(m => m.llm_tokens_per_second || 0);
            tokenChart.update();
        }
        
        function updateLogs(data) {
            const logsContainer = document.getElementById('logs-content');
            const timestamp = new Date().toLocaleTimeString();
            
            if (data.total_turns > 0) {
                const logEntry = `[${timestamp}] Turn ${data.total_turns} - Latency: ${(data.avg_latency || 0).toFixed(2)}s, Tokens/s: ${(data.avg_tokens_per_second || 0).toFixed(1)}`;
                
                if (!logs.includes(logEntry)) {
                    logs.unshift(logEntry);
                    if (logs.length > 30) logs.pop();
                    
                    logsContainer.innerHTML = logs.map(log => 
                        `<div class="log-entry">${log}</div>`
                    ).join('');
                }
            }
        }
        
        function refreshData() {
            fetch('/metrics')
                .then(r => r.json())
                .then(data => updateMetrics(data))
                .catch(e => console.error('Error:', e));
        }
        
        window.onload = function() {
            initCharts();
            refreshData();
            setInterval(refreshData, 2000);
        };
    </script>
</body>
</html>"""

    def start_dashboard(self, auto_open: bool = True) -> str:
        """Start the improved monitoring dashboard server."""
        try:
            import logging as http_logging
            http_logging.getLogger("http.server").setLevel(logging.CRITICAL + 1)
            
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            temp_file = temp_dir / "ana_dashboard.html"
            
            with open(temp_file, "w", encoding='utf-8') as f:
                f.write(self.get_html_template())

            class DashboardHandler(SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(temp_dir), **kwargs)

                def do_GET(self):
                    try:
                        if self.path == "/metrics":
                            collector = get_metrics_collector()
                            data = collector.get_performance_summary()
                            
                            # Add debug info
                            data["debug"] = {
                                "current_turn_active": collector.current_turn is not None,
                                "metrics_history_count": len(collector.metrics_history),
                                "total_turns_counter": collector.total_turns
                            }
                            
                            data["detailed_metrics"] = [
                                {
                                    "total_latency": m.total_latency,
                                    "llm_tokens_per_second": m.llm_tokens_per_second,
                                    "tool_call_count": m.tool_call_count,
                                    "timestamp": m.timestamp.isoformat(),
                                }
                                for m in collector.metrics_history
                            ]

                            self.send_response(200)
                            self.send_header("Content-type", "application/json")
                            self.send_header("Access-Control-Allow-Origin", "*")
                            self.end_headers()
                            self.wfile.write(json.dumps(data).encode())
                        elif self.path == "/" or self.path == "/dashboard":
                            self.send_response(200)
                            self.send_header("Content-type", "text/html")
                            self.end_headers()
                            with open(temp_file, "r", encoding='utf-8') as f:
                                self.wfile.write(f.read().encode())
                        else:
                            super().do_GET()
                    except Exception as e:
                        logging.getLogger("ana.dashboard").error(f"Request error: {e}")
                        self.send_response(500)
                        self.end_headers()
                
                def log_message(self, format, *args):
                    pass

            def run_server():
                try:
                    server = HTTPServer(("localhost", self.port), DashboardHandler)
                    server.serve_forever()
                except Exception as e:
                    self.logger.error(f"Server error: {e}")

            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()

            if auto_open:
                time.sleep(1)
                try:
                    webbrowser.open(f"http://localhost:{self.port}")
                except Exception as e:
                    self.logger.error(f"Failed to open browser: {e}")

            return f"http://localhost:{self.port}"

        except Exception as e:
            self.logger.error(f"Failed to start dashboard: {e}")
            return None


def start_improved_dashboard(port: int = 8080, auto_open: bool = True) -> str:
    """Start the improved monitoring dashboard."""
    dashboard = ImprovedMonitoringDashboard(port)
    return dashboard.start_dashboard(auto_open)
