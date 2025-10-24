"""Tool registry and management for ANA."""

from typing import Callable, List

from .email import send_email
from .file_manager import (
    create_file,
    delete_file,
    delete_folder,
    edit_file,
    list_files,
    read_file,
)
from .hardware import turn_led_off, turn_led_on, turn_led_on_for_duration
from .search import open_search, play_video, search_web
from .system import shutdown_agent
from .weather import get_weather


class ToolRegistry:
    """Registry for managing agent tools."""

    def __init__(self):
        self._tools: List[Callable] = []
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default tools."""
        self._tools = [
            get_weather,
            search_web,
            open_search,
            play_video,
            send_email,
            turn_led_on,
            turn_led_off,
            turn_led_on_for_duration,
            create_file,
            read_file,
            edit_file,
            list_files,
            delete_file,
            delete_folder,
            shutdown_agent,
        ]

    def register(self, tool: Callable):
        """Register a new tool."""
        if tool not in self._tools:
            self._tools.append(tool)

    def unregister(self, tool: Callable):
        """Unregister a tool."""
        if tool in self._tools:
            self._tools.remove(tool)

    def get_all(self) -> List[Callable]:
        """Get all registered tools."""
        return self._tools.copy()

    def clear(self):
        """Clear all tools."""
        self._tools.clear()


# Global tool registry instance
tool_registry = ToolRegistry()


def get_tools() -> List[Callable]:
    """Get all registered tools."""
    return tool_registry.get_all()


__all__ = [
    "ToolRegistry",
    "tool_registry",
    "get_tools",
    "get_weather",
    "search_web",
    "open_search",
    "play_video",
    "send_email",
    "turn_led_on",
    "turn_led_off",
    "turn_led_on_for_duration",
    "create_file",
    "read_file",
    "edit_file",
    "list_files",
    "delete_file",
    "delete_folder",
    "shutdown_agent",
]
