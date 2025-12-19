"""Countdown tool."""

import logging
from datetime import datetime

from livekit.agents import RunContext, function_tool

from .base import handle_tool_error


@function_tool()
@handle_tool_error("countdown")
async def countdown(
    context: RunContext,  # type: ignore
    date: str,
) -> str:
    """Calculates the number of days remaining until the specified date.

    Args:
        date: The target date in YYYY-MM-DD format.
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        today = datetime.now()

        if target_date < today:
            return f"The date {date} is in the past."

        delta = target_date - today
        days_remaining = delta.days
        return f"There are {days_remaining} days remaining until {date}."
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD."
    except Exception as e:
        logging.error(f"Error in countdown tool: {e}")
        return f"An error occurred: {e}"
