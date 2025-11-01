"""Monitoring and diagnostic tools for ANA."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from livekit.agents import RunContext, function_tool

from ..monitoring import get_metrics_collector
from ..monitoring_dashboard import export_performance_report, start_dashboard
from .base import handle_tool_error, monitor_tool


@function_tool()
@handle_tool_error("get_performance_metrics")
@monitor_tool("get_performance_metrics")
async def get_performance_metrics(context: RunContext) -> str:
    """Get current performance metrics and statistics."""
    collector = get_metrics_collector()
    summary = collector.get_performance_summary()

    if summary.get("status") == "no_data":
        return "No performance data available yet. Start a conversation to collect metrics."

    # Format metrics for user-friendly display
    formatted = [
        "**Performance Summary**",
        f"• Session Duration: {summary.get('session_duration', 0):.1f}s",
        f"• Total Turns: {summary.get('total_turns', 0)}",
        f"• Average Latency: {summary.get('avg_latency', 0):.2f}s",
        f"• Min/Max Latency: {summary.get('min_latency', 0):.2f}s / {summary.get('max_latency', 0):.2f}s",
        f"• 95th Percentile: {summary.get('p95_latency', 0):.2f}s",
        f"• Avg Tokens/sec: {summary.get('avg_tokens_per_second', 0):.1f}",
        f"• Total Tool Calls: {summary.get('total_tool_calls', 0)}",
        f"• Total Errors: {summary.get('total_errors', 0)}"
    ]
    
    # Add error breakdown if there are errors
    error_breakdown = summary.get('error_breakdown', {})
    if error_breakdown:
        formatted.append("\n**Error Breakdown:**")
        for tool, count in error_breakdown.items():
            formatted.append(f"• {tool}: {count} errors")

    return "\n".join(formatted)


@function_tool()
@handle_tool_error("export_performance_report")
@monitor_tool("export_performance_report")
async def export_performance_report(context: RunContext, file_path: Optional[str] = None) -> str:
    """Export detailed performance report to HTML file."""
    try:
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"ana_performance_report_{timestamp}.html"

        exported_path = export_performance_report(file_path)

        if exported_path:
            return f"Performance report exported to: {exported_path}"
        else:
            return "Failed to export performance report"

    except Exception as e:
        return f"Error exporting report: {str(e)}"


@function_tool()
@handle_tool_error("start_monitoring_dashboard")
@monitor_tool("start_monitoring_dashboard")
async def start_monitoring_dashboard(context: RunContext, port: int = 8080, auto_open: bool = True) -> str:
    """Start real-time monitoring dashboard in browser."""
    try:
        dashboard_url = start_dashboard(port, auto_open)

        if dashboard_url:
            return f"Monitoring dashboard started at: {dashboard_url}"
        else:
            return "Failed to start monitoring dashboard"

    except Exception as e:
        return f"Error starting dashboard: {str(e)}"


@function_tool()
@handle_tool_error("get_detailed_metrics")
@monitor_tool("get_detailed_metrics")
async def get_detailed_metrics(context: RunContext, limit: int = 10) -> str:
    """Get detailed metrics for recent turns."""
    collector = get_metrics_collector()

    if not collector.metrics_history:
        return "No detailed metrics available yet."

    # Get recent metrics
    recent_metrics = list(collector.metrics_history)[-limit:]

    formatted = [f"**Detailed Metrics (Last {len(recent_metrics)} turns)**"]

    for i, metrics in enumerate(recent_metrics, 1):
        formatted.append(f"\n**Turn {i}:** {metrics.speech_id}")
        formatted.append(f"• Time: {metrics.timestamp.strftime('%H:%M:%S')}")

        if metrics.total_latency:
            formatted.append(f"• Total Latency: {metrics.total_latency:.2f}s")

        if metrics.llm_ttft:
            formatted.append(f"• LLM Time to First Token: {metrics.llm_ttft:.2f}s")

        if metrics.llm_tokens_per_second:
            formatted.append(
                f"• Token Rate: {metrics.llm_tokens_per_second:.1f} tokens/s"
            )

        if metrics.tts_ttfb:
            formatted.append(f"• TTS Time to First Byte: {metrics.tts_ttfb:.2f}s")

        formatted.append(f"• Tool Calls: {metrics.tool_call_count}")

        if metrics.error_count > 0:
            formatted.append(f"• Errors: {metrics.error_count}")
            for error in metrics.error_messages[:2]:  # Show first 2 errors
                formatted.append(f"  - {error}")

    return "\n".join(formatted)


@function_tool()
@handle_tool_error("reset_metrics")
@monitor_tool("reset_metrics")
async def reset_metrics(context: RunContext) -> str:
    """Reset all collected metrics and start fresh."""
    try:
        collector = get_metrics_collector()

        # Clear history
        collector.metrics_history.clear()
        collector.latency_history.clear()
        collector.token_usage_history.clear()
        collector.error_counts.clear()

        # Reset counters
        collector.session_start_time = datetime.now().timestamp()
        collector.total_turns = 0

        # Reset usage collector
        collector.usage_collector = collector.usage_collector.__class__()

        return "All metrics have been reset. Starting fresh collection."

    except Exception as e:
        return f"Error resetting metrics: {str(e)}"


@function_tool()
@handle_tool_error("get_system_health")
@monitor_tool("get_system_health")
async def get_system_health(context: RunContext) -> str:
    """Get system health and performance status."""
    collector = get_metrics_collector()
    summary = collector.get_performance_summary()

    health_status = "HEALTHY"
    warnings = []

    # Check latency thresholds
    avg_latency = summary.get("avg_latency", 0)
    if avg_latency > 5.0:
        health_status = "CRITICAL"
        warnings.append("High average latency detected")
    elif avg_latency > 2.0:
        health_status = "WARNING"
        warnings.append("Elevated latency levels")

    # Check error rates
    total_errors = summary.get("total_errors", 0)
    total_turns = summary.get("total_turns", 1)
    error_rate = total_errors / total_turns if total_turns > 0 else 0

    if error_rate > 0.1:  # More than 10% error rate
        if health_status == "HEALTHY":
            health_status = "WARNING"
        warnings.append(f"High error rate: {error_rate:.1%}")

    # Format health report
    formatted = [
        f"{health_status} **ANA System Health**",
        f"• Status: {health_status}",
        f"• Session Uptime: {summary.get('session_duration', 0):.1f}s",
        f"• Total Turns: {summary.get('total_turns', 0)}",
        f"• Average Latency: {avg_latency:.2f}s",
        f"• Error Rate: {error_rate:.1%}",
        f"• Token Generation Rate: {summary.get('avg_tokens_per_second', 0):.1f} tokens/s"
    ]

    if warnings:
        formatted.append("\n**Warnings:**")
        for warning in warnings:
            formatted.append(f"• {warning}")

    # Add recommendations
    if warnings:
        formatted.append("\n**Recommendations:**")
        if "High average latency" in str(warnings):
            formatted.append("• Consider reducing context window size")
            formatted.append("• Check network connectivity")
            formatted.append("• Monitor system resources")
        if "High error rate" in str(warnings):
            formatted.append("• Check tool configurations")
            formatted.append("• Review error logs for patterns")
            formatted.append("• Verify API credentials and limits")

    return "\n".join(formatted)
