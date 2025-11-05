"""Base classes and utilities for tools."""

import functools
import logging
from typing import Any, Callable, TypeVar

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

T = TypeVar("T")


def handle_tool_error(tool_name: str) -> Callable:
    """Decorator for consistent error handling in tools."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Error in {tool_name}: {e}")
                return f"An error occurred in {tool_name}: {e}"  # type: ignore

        return wrapper

    return decorator
