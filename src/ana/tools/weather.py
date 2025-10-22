"""Weather-related tools."""

import logging

import requests
from livekit.agents import RunContext, function_tool

from .base import handle_tool_error


@function_tool()
@handle_tool_error("get_weather")
async def get_weather(
    context: RunContext,  # type: ignore
    city: str,
) -> str:
    """Get the current weather for a given city."""
    response = requests.get(f"https://wttr.in/{city}?format=3")
    if response.status_code == 200:
        logging.info(f"Weather for {city}: {response.text.strip()}")
        return response.text.strip()
    else:
        logging.error(f"Failed to get weather for {city}: {response.status_code}")
        return f"Could not retrieve weather for {city}."
