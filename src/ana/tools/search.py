"""Web search tools."""

import logging

from langchain_community.tools import DuckDuckGoSearchRun
from livekit.agents import RunContext, function_tool

from .base import handle_tool_error


@function_tool()
@handle_tool_error("search_web")
async def search_web(
    context: RunContext,  # type: ignore
    query: str,
) -> str:
    """Search the web using DuckDuckGo."""
    results = DuckDuckGoSearchRun().run(tool_input=query)
    logging.info(f"Search results for '{query}': {results}")
    return results
