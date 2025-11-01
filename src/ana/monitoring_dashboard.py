"""Real-time monitoring dashboard for ANA performance metrics."""

import json
import logging
import threading
import time
import webbrowser
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict

from .monitoring import get_metrics_collector


class MonitoringDashboard:
    """Simple web-based dashboard for monitoring ANA performance."""

    def __init__(self, port: int = 8080):
        self.port = port
        self.logger = logging.getLogger("ana.dashboard")
        self.metrics_collector = get_metrics_collector()
        self.html_template = self._get_html_template()
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
        
        error_log_file = logs_dir / "dashboard_errors.log"
        
        # Create file handler for dashboard errors
        error_handler = logging.FileHandler(error_log_file)
        error_handler.setLevel(logging.ERROR)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        error_handler.setFormatter(formatter)
        
        # Configure logger to ONLY use file handler
        self.logger.handlers.clear()  # Remove all existing handlers
        self.logger.addHandler(error_handler)
        self.logger.setLevel(logging.ERROR)
        self.logger.propagate = False  # Prevent propagation to root logger

    def _get_html_template(self) -> str:
        """Generate the HTML template for the dashboard."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ANA Performance Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        .metric-label {
            color: #666;
            margin-top: 5px;
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        .status-good { background: #10b981; }
        .status-warning { background: #f59e0b; }
        .status-error { background: #ef4444; }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        .refresh-btn:hover {
            background: #5a67d8;
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>ANA Performance Monitor <span style="color: #10b981; font-size: 0.8em;">[LIVE]</span></h1>
            <p>Real-time performance metrics and telemetry (auto-refreshes every 3 seconds)</p>
            <button class="refresh-btn" onclick="refreshData()">Refresh Data</button>
            <p style="margin: 10px 0; font-size: 0.9em; color: #666;">Last refresh: <span id="last-refresh">-</span></p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value" id="total-turns">-</div>
                <div class="metric-label">Total Turns</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="avg-latency">-</div>
                <div class="metric-label">Avg Latency (s)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="token-rate">-</div>
                <div class="metric-label">Tokens/sec</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="error-count">-</div>
                <div class="metric-label">Total Errors</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3>Latency Trend</h3>
            <canvas id="latencyChart" width="400" height="200"></canvas>
        </div>
        
        <div class="chart-container">
            <h3>Token Usage</h3>
            <canvas id="tokenChart" width="400" height="200"></canvas>
        </div>
        
        <div class="chart-container">
            <h3>Tool Usage</h3>
            <canvas id="toolChart" width="400" height="200"></canvas>
        </div>
        
        <div class="metric-card">
            <h3>System Status</h3>
            <div id="system-status">
                <p><span class="status-indicator status-good"></span>Agent Running</p>
                <p><span class="status-indicator status-good"></span>Metrics Collection Active</p>
                <p>Last Update: <span id="last-update">-</span></p>
            </div>
        </div>
    </div>

    <script>
        let latencyChart, tokenChart, toolChart;
        
        function initCharts() {
            // Latency Chart
            const latencyCtx = document.getElementById('latencyChart').getContext('2d');
            latencyChart = new Chart(latencyCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Latency (s)',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
            
            // Token Chart
            const tokenCtx = document.getElementById('tokenChart').getContext('2d');
            tokenChart = new Chart(tokenCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Tokens per Second',
                        data: [],
                        borderColor: 'rgb(153, 102, 255)',
                        backgroundColor: 'rgba(153, 102, 255, 0.2)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
            
            // Tool Chart
            const toolCtx = document.getElementById('toolChart').getContext('2d');
            toolChart = new Chart(toolCtx, {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: [
                            '#FF6384',
                            '#36A2EB',
                            '#FFCE56',
                            '#4BC0C0',
                            '#9966FF',
                            '#FF9F40'
                        ]
                    }]
                },
                options: {
                    responsive: true
                }
            });
        }
        
        function updateMetrics(data) {
            // Update metric cards
            document.getElementById('total-turns').textContent = data.total_turns || 0;
            document.getElementById('avg-latency').textContent = (data.avg_latency || 0).toFixed(2);
            document.getElementById('token-rate').textContent = (data.avg_tokens_per_second || 0).toFixed(1);
            document.getElementById('error-count').textContent = data.total_errors || 0;
            
            // Update charts
            if (data.detailed_metrics) {
                updateLatencyChart(data.detailed_metrics);
                updateTokenChart(data.detailed_metrics);
                updateToolChart(data.detailed_metrics);
            }
            
            // Update status
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
        }
        
        function updateLatencyChart(metrics) {
            const latencies = metrics.filter(m => m.total_latency).slice(-20);
            latencyChart.data.labels = latencies.map((_, i) => `Turn ${i + 1}`);
            latencyChart.data.datasets[0].data = latencies.map(m => m.total_latency);
            latencyChart.update();
        }
        
        function updateTokenChart(metrics) {
            const tokenRates = metrics.filter(m => m.llm_tokens_per_second).slice(-20);
            tokenChart.data.labels = tokenRates.map((_, i) => `Turn ${i + 1}`);
            tokenChart.data.datasets[0].data = tokenRates.map(m => m.llm_tokens_per_second);
            tokenChart.update();
        }
        
        function updateToolChart(metrics) {
            const toolCounts = {};
            metrics.forEach(m => {
                if (m.tool_call_count > 0) {
                    toolCounts['Tools Used'] = (toolCounts['Tools Used'] || 0) + m.tool_call_count;
                }
            });
            
            toolChart.data.labels = Object.keys(toolCounts);
            toolChart.data.datasets[0].data = Object.values(toolCounts);
            toolChart.update();
        }
        
        function refreshData() {
            fetch('/metrics')
                .then(response => response.json())
                .then(data => updateMetrics(data))
                .catch(error => console.error('Error fetching metrics:', error));
        }
        
        // Initialize on load
        window.onload = function() {
            initCharts();
            
            // Load initial data if available
            if (window.initialMetrics) {
                updateMetrics(window.initialMetrics);
            }
            
            refreshData();
            // Auto-refresh every 3 seconds
            setInterval(refreshData, 3000);
        };
    </script>
</body>
</html>
        """

    def generate_dashboard_html(self, metrics_file: str = None) -> str:
        """Generate dashboard HTML with current metrics."""
        try:
            # Load latest metrics if file provided
            if metrics_file and Path(metrics_file).exists():
                with open(metrics_file, 'r') as f:
                    latest_metrics = json.load(f)
            else:
                latest_metrics = get_metrics_collector().get_performance_summary()
                
            # Generate HTML with real-time data
            html_template = self._get_html_template()
            
            # Inject initial data into the HTML
            initial_data_script = f"""
            <script>
                window.initialMetrics = {json.dumps(latest_metrics)};
            </script>
            """
            
            # Insert the script before the closing head tag
            html_with_data = html_template.replace('</head>', initial_data_script + '</head>')
            
            return html_with_data
            
        except Exception as e:
            self.logger.error(f"Failed to generate dashboard HTML: {e}")
            return self._get_error_page(e)

    def _get_error_page(self, error: Exception) -> str:
        """Generate error page when dashboard fails."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Error</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 40px; background: #f5f5f5; }}
        .error-container {{ background: white; padding: 30px; border-radius: 10px; max-width: 600px; margin: 0 auto; }}
        .error-title {{ color: #ef4444; margin-bottom: 20px; }}
        .error-message {{ color: #666; margin-bottom: 20px; }}
        .error-details {{ background: #f9f9f9; padding: 15px; border-radius: 5px; font-family: monospace; }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1 class="error-title">Dashboard Error</h1>
        <p class="error-message">The monitoring dashboard encountered an error:</p>
        <div class="error-details">{str(error)}</div>
        <p style="margin-top: 20px;">
            <small>Check the logs folder for detailed error information.</small>
        </p>
    </div>
</body>
</html>
        """

    def start_dashboard(self, auto_open: bool = True) -> str:
        """Start the monitoring dashboard server."""
        try:
            # Suppress HTTP server logs
            import logging as http_logging
            http_logging.getLogger("http.server").setLevel(logging.CRITICAL + 1)
            http_logging.getLogger("socketserver").setLevel(logging.CRITICAL + 1)
            
            # Suppress deprecation warnings
            import warnings
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            
            # Create temporary HTML file
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            temp_file = temp_dir / "ana_dashboard.html"
            
            # Generate and write HTML
            html_content = self.generate_dashboard_html()
            with open(temp_file, "w", encoding='utf-8') as f:
                f.write(html_content)

            # Create custom handler
            class DashboardHandler(SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(temp_dir), **kwargs)

                def do_GET(self):
                    try:
                        if self.path == "/metrics":
                            # Serve metrics as JSON
                            collector = get_metrics_collector()
                            data = collector.get_performance_summary()
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
                            # Serve dashboard HTML
                            self.send_response(200)
                            self.send_header("Content-type", "text/html")
                            self.end_headers()
                            with open(temp_file, "r", encoding='utf-8') as f:
                                self.wfile.write(f.read().encode())
                        else:
                            super().do_GET()
                    except Exception as e:
                        # Log error to file only
                        logging.getLogger("ana.dashboard").error(f"Dashboard request error: {e}")
                        self.send_response(500)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        error_html = f"""
                        <h1>Dashboard Error</h1>
                        <p>Request failed: {str(e)}</p>
                        <p>Check logs folder for details.</p>
                        """
                        self.wfile.write(error_html.encode())
                
                def log_message(self, format, *args):
                    # Suppress all HTTP server logs
                    pass

            # Start server in background thread
            def run_server():
                try:
                    server = HTTPServer(("localhost", self.port), DashboardHandler)
                    # Dashboard started silently
                    server.serve_forever()
                except Exception as e:
                    self.logger.error(f"Failed to start dashboard server: {e}")

            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()

            # Auto-open browser
            if auto_open:
                time.sleep(1)  # Give server time to start
                try:
                    webbrowser.open(f"http://localhost:{self.port}")
                except Exception as e:
                    self.logger.error(f"Failed to open browser: {e}")

            return f"http://localhost:{self.port}"

        except Exception as e:
            self.logger.error(f"Failed to start dashboard: {e}")
            return None

    def export_report(self, output_path: str = None):
        """Export comprehensive performance report."""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"ana_performance_report_{timestamp}.html"

        try:
            data = self.metrics_collector.get_performance_summary()
            html_report = self._generate_report_html(data)

            with open(output_path, "w") as f:
                f.write(html_report)

            self.logger.info(f"Performance report exported to {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to export report: {e}")
            return None

    def _generate_report_html(self, data: Dict[str, Any]) -> str:
        """Generate comprehensive HTML report."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>ANA Performance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .metric {{ margin: 10px 0; padding: 10px; background: #f9f9f9; border-left: 4px solid #007cba; }}
        .good {{ border-left-color: #28a745; }}
        .warning {{ border-left-color: #ffc107; }}
        .error {{ border-left-color: #dc3545; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ANA Performance Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <h2>Session Summary</h2>
    <div class="metric">Session Duration: {data.get('session_duration', 0):.2f} seconds</div>
    <div class="metric">Total Turns: {data.get('total_turns', 0)}</div>
    
    <h2>Performance Metrics</h2>
    <div class="metric {'good' if data.get('avg_latency', 0) < 2 else 'warning' if data.get('avg_latency', 0) < 5 else 'error'}">
        Average Latency: {data.get('avg_latency', 0):.2f} seconds
    </div>
    <div class="metric">Min Latency: {data.get('min_latency', 0):.2f} seconds</div>
    <div class="metric">Max Latency: {data.get('max_latency', 0):.2f} seconds</div>
    <div class="metric">95th Percentile Latency: {data.get('p95_latency', 0):.2f} seconds</div>
    <div class="metric">Average Tokens/sec: {data.get('avg_tokens_per_second', 0):.1f}</div>
    
    <h2>Usage Statistics</h2>
    <div class="metric">Total Tool Calls: {data.get('total_tool_calls', 0)}</div>
    <div class="metric">Total Errors: {data.get('total_errors', 0)}</div>
    
    <h2>Error Breakdown</h2>
    {"".join([f"<div class='metric error'>{tool}: {count}</div>" for tool, count in data.get('error_breakdown', {}).items()])}
    
    <h2>Usage Summary</h2>
    <pre>{json.dumps(data.get('usage_summary', {}), indent=2)}</pre>
</body>
</html>
                        """


def start_dashboard(port: int = 8080, auto_open: bool = True) -> str:
    """Start the monitoring dashboard."""
    dashboard = MonitoringDashboard(port)
    return dashboard.start_dashboard(auto_open)


def export_performance_report(output_path: str = None) -> str:
    """Export performance report to HTML."""
    dashboard = MonitoringDashboard()
    return dashboard.export_report(output_path)
