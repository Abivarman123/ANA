"""System control tools."""

import asyncio
import logging
import os
import subprocess
import sys

from livekit.agents import RunContext, function_tool

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
        await asyncio.sleep(1.0)  # Give time for response to be sent
        
        logger.info("Executing shutdown sequence")
        
        # Close the terminal window on Windows
        if sys.platform == "win32":
            try:
                import psutil
                
                current_pid = os.getpid()
                logger.info(f"Current PID: {current_pid}")
                
                # Find the CMD/console window by walking up the process tree
                try:
                    current_process = psutil.Process(current_pid)
                    
                    # Walk up the process tree to find cmd.exe or conhost.exe
                    process = current_process
                    cmd_pid = None
                    
                    for _ in range(10):  # Max 10 levels up
                        try:
                            parent = process.parent()
                            if not parent:
                                break
                            
                            parent_name = parent.name().lower()
                            logger.info(f"Checking parent: {parent_name} (PID: {parent.pid})")
                            
                            # Found the CMD window
                            if 'cmd.exe' in parent_name:
                                cmd_pid = parent.pid
                                logger.info(f"Found CMD window: PID {cmd_pid}")
                                break
                            
                            process = parent
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            break
                    
                    # Kill the CMD window if found
                    if cmd_pid:
                        logger.info(f"Killing CMD window: {cmd_pid}")
                        subprocess.run(
                            f'taskkill /F /PID {cmd_pid}',
                            shell=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    else:
                        # Fallback: just exit and let user close window
                        logger.info("CMD window not found in process tree, exiting normally")
                        
                except psutil.NoSuchProcess:
                    logger.warning("Could not find parent process")
                    
            except Exception as e:
                logger.error(f"Error closing terminal: {e}")
        
        # Exit the process
        os._exit(0)

    asyncio.create_task(delayed_shutdown())
    return "✓ Shutting down. Goodbye, Sir."
