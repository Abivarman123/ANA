"""System control tools."""

import asyncio
import os

from livekit.agents import RunContext, function_tool

from .hardware import cleanup_hardware


@function_tool()
async def shutdown_agent(
    context: RunContext,  # type: ignore
) -> str:
    """Shut down the agent."""
    cleanup_hardware()

    async def delayed_shutdown():
        await asyncio.sleep(0.5)
        os._exit(0)

    asyncio.create_task(delayed_shutdown())
    return "✓ Shutting down. Goodbye, Sir."
