"""System control tools."""

import asyncio
import logging
import os
import platform
import subprocess
import sys

import psutil
from livekit.agents import RunContext, function_tool, get_job_context

from .hardware import cleanup_hardware

logger = logging.getLogger(__name__)


@function_tool()
async def get_system_info(
    context: RunContext,  # type: ignore
) -> str:
    """Get comprehensive system information.

    Returns detailed information about:
    - CPU usage and core count
    - RAM usage (total, used, available, percentage)
    - Storage usage for all drives
    - Top 5 processes by memory usage
    - Operating system and Python version
    """
    logger.info("System info tool called")

    try:
        info_parts = []

        # System and Software Version
        info_parts.append("=== SYSTEM INFORMATION ===")
        info_parts.append(
            f"OS: {platform.system()} {platform.release()} ({platform.version()})"
        )
        info_parts.append(f"Architecture: {platform.machine()}")
        info_parts.append(f"Python Version: {platform.python_version()}")
        info_parts.append(f"Hostname: {platform.node()}")

        # CPU Information
        info_parts.append("\n=== CPU INFORMATION ===")
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        cpu_freq = psutil.cpu_freq()

        info_parts.append(f"CPU Usage: {cpu_percent}%")
        info_parts.append(f"Physical Cores: {cpu_count_physical}")
        info_parts.append(f"Logical Cores: {cpu_count_logical}")
        if cpu_freq:
            info_parts.append(
                f"CPU Frequency: {cpu_freq.current:.2f} MHz (Max: {cpu_freq.max:.2f} MHz)"
            )

        # RAM Information
        info_parts.append("\n=== MEMORY (RAM) INFORMATION ===")
        memory = psutil.virtual_memory()
        info_parts.append(f"Total RAM: {memory.total / (1024**3):.2f} GB")
        info_parts.append(f"Used RAM: {memory.used / (1024**3):.2f} GB")
        info_parts.append(f"Available RAM: {memory.available / (1024**3):.2f} GB")
        info_parts.append(f"RAM Usage: {memory.percent}%")

        # Storage Information
        info_parts.append("\n=== STORAGE INFORMATION ===")
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                info_parts.append(
                    f"\nDrive {partition.device} ({partition.mountpoint}):"
                )
                info_parts.append(f"  File System: {partition.fstype}")
                info_parts.append(f"  Total: {usage.total / (1024**3):.2f} GB")
                info_parts.append(f"  Used: {usage.used / (1024**3):.2f} GB")
                info_parts.append(f"  Free: {usage.free / (1024**3):.2f} GB")
                info_parts.append(f"  Usage: {usage.percent}%")
            except PermissionError:
                # Skip drives that can't be accessed
                continue

        # Top Processes by Memory
        info_parts.append("\n=== TOP 5 PROCESSES BY MEMORY USAGE ===")
        processes = []
        for proc in psutil.process_iter(
            ["pid", "name", "memory_percent", "cpu_percent"]
        ):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by memory usage
        top_processes = sorted(
            processes, key=lambda x: x["memory_percent"] or 0, reverse=True
        )[:5]

        for i, proc in enumerate(top_processes, 1):
            mem_percent = proc["memory_percent"] or 0
            cpu_percent = proc["cpu_percent"] or 0
            info_parts.append(f"{i}. {proc['name']} (PID: {proc['pid']})")
            info_parts.append(
                f"   Memory: {mem_percent:.2f}% | CPU: {cpu_percent:.1f}%"
            )

        # Network Information (optional)
        info_parts.append("\n=== NETWORK INFORMATION ===")
        net_io = psutil.net_io_counters()
        info_parts.append(f"Bytes Sent: {net_io.bytes_sent / (1024**3):.2f} GB")
        info_parts.append(f"Bytes Received: {net_io.bytes_recv / (1024**3):.2f} GB")

        result = "\n".join(info_parts)
        logger.info("System info retrieved successfully")
        return result

    except Exception as e:
        error_msg = f"Error retrieving system information: {str(e)}"
        logger.error(error_msg)
        return error_msg


@function_tool()
async def shutdown_agent(
    context: RunContext,  # type: ignore
) -> str:
    """Shut down the agent and close the terminal window."""
    cleanup_hardware()

    async def delayed_shutdown():
        await asyncio.sleep(1.5)
        logger.info("Executing shutdown sequence - triggering graceful shutdown")

        # Trigger graceful shutdown to run all registered callbacks:
        # 1. save_conversation_to_mem0 - saves memories
        # 2. close_terminal_window - closes the terminal
        try:
            job_ctx = get_job_context()
            job_ctx.shutdown(reason="User requested shutdown")
        except Exception as e:
            logger.error(f"Could not trigger graceful shutdown: {e}")
            os._exit(0)

    asyncio.create_task(delayed_shutdown())
    return "✓ Shutting down. Goodbye, Sir."


async def close_terminal_window():
    """Close the terminal window after shutdown on Windows."""
    if sys.platform != "win32":
        return

    try:
        current_pid = os.getpid()
        current_process = psutil.Process(current_pid)

        # Walk up the process tree to find cmd.exe
        process = current_process
        cmd_pid = None

        for _ in range(10):  # Max 10 levels up
            try:
                parent = process.parent()
                if not parent:
                    break

                parent_name = parent.name().lower()

                # Found the CMD window
                if "cmd.exe" in parent_name:
                    cmd_pid = parent.pid
                    break

                process = parent
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

        # Kill the CMD window if found
        if cmd_pid:
            subprocess.run(
                f"taskkill /F /PID {cmd_pid}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            await asyncio.sleep(0.3)
            os._exit(0)
        else:
            os._exit(0)

    except Exception as e:
        logging.error(f"Error closing terminal: {e}")
        os._exit(0)
