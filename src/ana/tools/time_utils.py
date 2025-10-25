"""Date and time tools."""

import logging
from datetime import datetime

from livekit.agents import RunContext, function_tool

from .base import handle_tool_error


@function_tool()
@handle_tool_error("get_current_date")
async def get_current_date(
    context: RunContext,  # type: ignore
) -> str:
    """Get today's date in ISO format (YYYY-MM-DD)."""
    value = datetime.now().strftime("%Y-%m-%d")
    logging.info(f"Current date: {value}")
    return value


@function_tool()
@handle_tool_error("get_current_time")
async def get_current_time(
    context: RunContext,  # type: ignore
    include_seconds: bool = True,
) -> str:
    """Get the current local time in 24-hour format. Optionally include seconds."""
    fmt = "%H:%M:%S" if include_seconds else "%H:%M"
    value = datetime.now().strftime(fmt)
    logging.info(f"Current time: {value}")
    return value
