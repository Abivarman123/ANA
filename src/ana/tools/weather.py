"""Weather-related tools."""

import logging

import aiohttp
from livekit.agents import RunContext, function_tool

from .base import handle_tool_error


@function_tool()
@handle_tool_error("get_weather")
async def get_weather(
    context: RunContext,  # type: ignore
    city: str,
) -> str:
    """Get the current weather for a given city."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://wttr.in/{city}?format=3") as response:
            if response.status == 200:
                text = await response.text()
                logging.info(f"Weather for {city}: {text.strip()}")
                return text.strip()
            else:
                logging.error(f"Failed to get weather for {city}: {response.status}")
                return f"Could not retrieve weather for {city}."
