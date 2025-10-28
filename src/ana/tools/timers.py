"""Timer tools for background timers."""

import logging
import time
from livekit.agents import RunContext, function_tool

from ..background_tasks import background_timer
from .base import handle_tool_error


@function_tool()
@handle_tool_error("set_timer")
async def set_timer(
    context: RunContext,  # type: ignore
    duration_seconds: int,
    message: str,
    timer_name: str = None,
) -> str:
    """Set a background timer that alerts you after the specified duration.
    
    The timer runs in the background while conversation continues.
    
    Args:
        duration_seconds: How long to wait (in seconds)
        message: What to say when the timer goes off
        timer_name: Optional name for the timer
    """
    if timer_name is None:
        timer_name = f"timer_{int(time.time())}"
    
    result = background_timer.set_timer(timer_name, duration_seconds, message)
    logging.info(f"Timer set: {timer_name} for {duration_seconds}s")
    return result


@function_tool()
@handle_tool_error("cancel_timer")
async def cancel_timer(
    context: RunContext,  # type: ignore
    timer_name: str,
) -> str:
    """Cancel an active timer."""
    return background_timer.cancel_timer(timer_name)


@function_tool()
@handle_tool_error("list_active_timers")
async def list_active_timers(
    context: RunContext,  # type: ignore
) -> str:
    """List all currently active timers."""
    timers = background_timer.list_timers()
    if not timers:
        return "No active timers"
    return f"Active timers: {', '.join(timers)}"
