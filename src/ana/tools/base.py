"""Base classes and utilities for tools."""

import functools
import logging
import time
from typing import Any, Callable, TypeVar

from ..monitoring import PerformanceMonitor, get_metrics_collector

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
            start_time = time.time()
            error_msg = None
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Error in {tool_name}: {e}")
                return f"An error occurred in {tool_name}: {error_msg}"  # type: ignore
            finally:
                # Record tool execution metrics
                duration = time.time() - start_time
                collector = get_metrics_collector()
                collector.record_tool_call(tool_name, duration, error_msg)

        return wrapper

    return decorator


def monitor_tool(tool_name: str) -> Callable:
    """Decorator for monitoring tool performance."""
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            with PerformanceMonitor(f"tool_{tool_name}", tool_name):
                return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator
