"""System control tools."""

import asyncio
import logging
import os
import subprocess
import sys

from livekit.agents import RunContext, function_tool, get_job_context

from .hardware import cleanup_hardware

logger = logging.getLogger(__name__)


@function_tool()
async def shutdown_agent(
    context: RunContext,  # type: ignore
) -> str:
    """Shut down the agent and close the terminal window."""
    logger.info("Shutdown agent tool called")
    cleanup_hardware()

    async def delayed_shutdown():
        await asyncio.sleep(1.5)  # Give time for response to be sent
        
        logger.info("Executing shutdown sequence - triggering graceful shutdown")
        
        # Use the job context to trigger a graceful shutdown
        # This will run all registered shutdown callbacks:
        # 1. save_conversation_to_mem0 - saves memories
        # 2. close_terminal_window - closes the terminal
        try:
            job_ctx = get_job_context()
            logger.info("Calling ctx.shutdown() for graceful shutdown")
            job_ctx.shutdown(reason="User requested shutdown")
            # Callbacks will handle everything including terminal closing
        except Exception as e:
            logger.error(f"Could not trigger graceful shutdown: {e}")
            logger.info("Falling back to direct exit")
            os._exit(0)

    asyncio.create_task(delayed_shutdown())
    return "✓ Shutting down. Goodbye, Sir."


async def close_terminal_window():
    """Close the terminal window after shutdown on Windows."""
    if sys.platform != "win32":
        return

    logging.info("Closing terminal window...")

    try:
        import psutil

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
                    logging.info(f"Found CMD window: PID {cmd_pid}")
                    break

                process = parent
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

        # Kill the CMD window if found
        if cmd_pid:
            logging.info(f"Killing CMD window: {cmd_pid}")
            subprocess.run(
                f"taskkill /F /PID {cmd_pid}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Give taskkill a moment to execute, then force exit
            await asyncio.sleep(0.3)
            logging.info("Forcing process exit...")
            os._exit(0)
        else:
            logging.info("CMD window not found, exiting normally")
            os._exit(0)

    except Exception as e:
        logging.error(f"Error closing terminal: {e}")
        os._exit(0)
