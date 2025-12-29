"""File search tools for ANA using ripgrep (rg) and fd.

This module provides powerful file search capabilities using:
- ripgrep (rg): For searching file contents with regex support
- fd: For finding files by name with intuitive syntax
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path

from livekit.agents import RunContext, function_tool

from ..config import config
from .base import handle_tool_error

logger = logging.getLogger(__name__)

# Default search directory (Desktop sandbox or home)
DEFAULT_SEARCH_DIR = Path.home() / "Desktop"

# Maximum results to return to avoid overwhelming output
MAX_RESULTS = 50

# Maximum file size to search (for content search)
MAX_SEARCH_SIZE = "10M"


def _check_tool_installed(tool_name: str) -> bool:
    """Check if a command-line tool is installed."""
    return shutil.which(tool_name) is not None


def _get_search_base() -> Path:
    """Get the base search directory from config or default to Desktop."""
    sandbox = config.get("file_manager", {}).get("sandbox_path", "~/Desktop")
    return Path(sandbox).expanduser().resolve()


async def _run_command(cmd: list[str], timeout: int = 30) -> tuple[str, str, int]:
    """Run a command asynchronously and return (stdout, stderr, returncode)."""
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return (
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
            process.returncode or 0,
        )
    except asyncio.TimeoutError:
        process.kill()
        return "", "Search timed out", 1
    except Exception as e:
        return "", str(e), 1


@function_tool()
@handle_tool_error("search_file_contents")
async def search_file_contents(
    context: RunContext,
    query: str,
    directory: str = "",
    file_type: str = "",
    case_sensitive: bool = False,
    regex: bool = False,
    max_results: int = 20,
) -> str:
    """Search for text/patterns within files using ripgrep (rg).

    This is a powerful content search tool. Use it to find text inside files.

    Args:
        query: The text or pattern to search for inside files
        directory: Directory to search in (relative to Desktop or absolute path)
                   Leave empty to search the entire Desktop folder
        file_type: Optional file extension to filter (e.g., "py", "txt", "js")
                   Leave empty to search all text files
        case_sensitive: Whether the search should be case-sensitive (default: False)
        regex: Whether to treat query as a regular expression (default: False)
        max_results: Maximum number of results to return (default: 20, max: 50)

    Returns:
        Matching lines with file paths and line numbers

    Examples:
        - Search for "TODO" in all files: search_file_contents(query="TODO")
        - Search in Python files only: search_file_contents(query="import", file_type="py")
        - Regex search for emails: search_file_contents(query=r"\\w+@\\w+\\.\\w+", regex=True)
    """
    logger.info(
        f"Searching file contents: query='{query}', dir='{directory}', type='{file_type}'"
    )

    if not _check_tool_installed("rg"):
        return "❌ ripgrep (rg) is not installed. Please install it: https://github.com/BurntSushi/ripgrep/releases"

    # Build search path
    base_dir = _get_search_base()
    if directory:
        if os.path.isabs(directory):
            search_dir = Path(directory)
        else:
            search_dir = base_dir / directory
    else:
        search_dir = base_dir

    if not search_dir.exists():
        return f"❌ Directory not found: {search_dir}"

    # Cap results
    max_results = min(max_results, MAX_RESULTS)

    # Build ripgrep command
    cmd = [
        "rg",
        "--line-number",
        "--with-filename",
        "--max-filesize",
        MAX_SEARCH_SIZE,
        "--color",
        "never",
    ]

    if not case_sensitive:
        cmd.append("--ignore-case")

    if not regex:
        cmd.append("--fixed-strings")

    if file_type:
        # Remove leading dot if present
        ext = file_type.lstrip(".")
        cmd.extend(["--type-add", f"custom:*.{ext}", "--type", "custom"])

    cmd.append(query)
    cmd.append(str(search_dir))

    stdout, stderr, returncode = await _run_command(cmd)

    if returncode == 1 and not stdout:
        return f"No matches found for '{query}' in {search_dir.name}"

    if returncode == 2:
        return f"❌ Search error: {stderr}"

    if not stdout.strip():
        return f"No matches found for '{query}' in {search_dir.name}"

    # Format results
    lines = stdout.strip().split("\n")
    result_count = len(lines)

    # Truncate if needed
    if result_count > max_results:
        lines = lines[:max_results]
        truncated = True
    else:
        truncated = False

    # Make paths relative to search dir for cleaner output
    formatted_lines = []
    for line in lines:
        try:
            # Try to make path relative
            if str(search_dir) in line:
                line = line.replace(str(search_dir) + "\\", "").replace(
                    str(search_dir) + "/", ""
                )
        except Exception:
            pass
        formatted_lines.append(f"  {line}")

    header = f"🔍 Found {result_count} match{'es' if result_count != 1 else ''} for '{query}'"
    if file_type:
        header += f" in .{file_type} files"
    header += f" ({search_dir.name}):"

    result = header + "\n\n" + "\n".join(formatted_lines)

    if truncated:
        result += f"\n\n... (showing first {max_results} results)"

    return result


@function_tool()
@handle_tool_error("find_files")
async def find_files(
    context: RunContext,
    pattern: str = "",
    directory: str = "",
    file_type: str = "",
    extension: str = "",
    hidden: bool = False,
    max_depth: int = 0,
    max_results: int = 30,
) -> str:
    """Find files by name using fd.

    This is a fast file finder. Use it to locate files by name or pattern.

    Args:
        pattern: Search pattern for file/folder names (supports regex)
                 Leave empty to list all files
        directory: Directory to search in (relative to Desktop or absolute path)
                   Leave empty to search the entire Desktop folder
        file_type: Filter by type - "file" (or "f"), "directory" (or "d"),
                   "symlink" (or "l"), or empty for all
        extension: Filter by file extension (e.g., "py", "txt", "pdf")
                   Can specify multiple separated by comma: "py,js,ts"
        hidden: Whether to include hidden files (default: False)
        max_depth: Maximum depth to search (0 = unlimited)
        max_results: Maximum number of results to return (default: 30, max: 50)

    Returns:
        List of matching file paths

    Examples:
        - Find all Python files: find_files(extension="py")
        - Find files containing "test": find_files(pattern="test")
        - Find only directories: find_files(file_type="directory")
        - Find PDFs in specific folder: find_files(extension="pdf", directory="Documents")
    """
    logger.info(
        f"Finding files: pattern='{pattern}', dir='{directory}', ext='{extension}'"
    )

    if not _check_tool_installed("fd"):
        return "❌ fd is not installed. Please install it: https://github.com/sharkdp/fd/releases"

    # Build search path
    base_dir = _get_search_base()
    if directory:
        if os.path.isabs(directory):
            search_dir = Path(directory)
        else:
            search_dir = base_dir / directory
    else:
        search_dir = base_dir

    if not search_dir.exists():
        return f"❌ Directory not found: {search_dir}"

    # Cap results
    max_results = min(max_results, MAX_RESULTS)

    # Build fd command
    cmd = [
        "fd",
        "--max-results",
        str(max_results),
        "--color",
        "never",
    ]

    if hidden:
        cmd.append("--hidden")

    if max_depth > 0:
        cmd.extend(["--max-depth", str(max_depth)])

    # File type filter
    type_map = {
        "file": "f",
        "f": "f",
        "directory": "d",
        "dir": "d",
        "d": "d",
        "folder": "d",
        "symlink": "l",
        "link": "l",
        "l": "l",
    }
    if file_type:
        ft = type_map.get(file_type.lower(), "f")
        cmd.extend(["--type", ft])

    # Extension filter
    if extension:
        for ext in extension.split(","):
            ext = ext.strip().lstrip(".")
            cmd.extend(["--extension", ext])

    # Add pattern if provided
    if pattern:
        cmd.append(pattern)

    # Add search directory
    cmd.append(str(search_dir))

    stdout, stderr, returncode = await _run_command(cmd)

    if returncode != 0 and stderr:
        return f"❌ Search error: {stderr}"

    if not stdout.strip():
        msg = "No files found"
        if pattern:
            msg += f" matching '{pattern}'"
        if extension:
            msg += f" with extension .{extension}"
        msg += f" in {search_dir.name}"
        return msg

    # Format results
    lines = stdout.strip().split("\n")
    result_count = len(lines)

    # Make paths relative and add icons
    formatted_lines = []
    for line in lines:
        path = Path(line.strip())
        try:
            rel_path = path.relative_to(search_dir)
        except ValueError:
            rel_path = path

        if path.is_dir():
            formatted_lines.append(f"  📁 {rel_path}/")
        else:
            size = ""
            try:
                size_bytes = path.stat().st_size
                if size_bytes < 1024:
                    size = f" ({size_bytes}B)"
                elif size_bytes < 1024 * 1024:
                    size = f" ({size_bytes / 1024:.1f}KB)"
                else:
                    size = f" ({size_bytes / (1024 * 1024):.1f}MB)"
            except Exception:
                pass
            formatted_lines.append(f"  📄 {rel_path}{size}")

    header = f"📂 Found {result_count} item{'s' if result_count != 1 else ''}"
    if pattern:
        header += f" matching '{pattern}'"
    if extension:
        header += f" with extension .{extension}"
    header += f" in {search_dir.name}:"

    result = header + "\n\n" + "\n".join(formatted_lines)

    if result_count >= max_results:
        result += f"\n\n... (showing first {max_results} results)"

    return result


@function_tool()
@handle_tool_error("search_everywhere")
async def search_everywhere(
    context: RunContext,
    query: str,
    directory: str = "",
    max_results: int = 15,
) -> str:
    """Combined search: finds files by name AND searches inside files.

    This tool performs both a filename search (fd) and content search (rg)
    for the query, giving you comprehensive results.

    Args:
        query: What to search for (in filenames and file contents)
        directory: Directory to search in (relative to Desktop or absolute path)
        max_results: Maximum results per search type (default: 15)

    Returns:
        Combined results from both filename and content searches

    Examples:
        - Find anything related to "config": search_everywhere(query="config")
        - Search in a specific folder: search_everywhere(query="password", directory="notes")
    """
    logger.info(f"Searching everywhere for: '{query}'")

    results = []

    # Check tools are available
    has_fd = _check_tool_installed("fd")
    has_rg = _check_tool_installed("rg")

    if not has_fd and not has_rg:
        return "❌ Neither fd nor ripgrep (rg) are installed. Please install at least one:\n- fd: https://github.com/sharkdp/fd/releases\n- rg: https://github.com/BurntSushi/ripgrep/releases"

    # Run both searches
    if has_fd:
        file_results = await find_files(
            context=context,
            pattern=query,
            directory=directory,
            max_results=max_results,
        )
        results.append("🔎 **Files matching name:**\n" + file_results)

    if has_rg:
        content_results = await search_file_contents(
            context=context,
            query=query,
            directory=directory,
            max_results=max_results,
        )
        results.append("🔍 **Files containing text:**\n" + content_results)

    return "\n\n" + "\n\n".join(results)


@function_tool()
@handle_tool_error("check_search_tools")
async def check_search_tools(
    context: RunContext,
) -> str:
    """Check if file search tools (fd, rg) are installed.

    Returns installation status and instructions for missing tools.
    """
    tools = {
        "fd": {
            "installed": _check_tool_installed("fd"),
            "description": "Fast file finder by name",
            "url": "https://github.com/sharkdp/fd/releases",
            "install": "winget install sharkdp.fd",
        },
        "rg (ripgrep)": {
            "installed": _check_tool_installed("rg"),
            "description": "Fast content search in files",
            "url": "https://github.com/BurntSushi/ripgrep/releases",
            "install": "winget install BurntSushi.ripgrep.MSVC",
        },
    }

    result = "🔧 **File Search Tools Status:**\n\n"

    all_installed = True
    for name, info in tools.items():
        status = "✅" if info["installed"] else "❌"
        result += f"{status} **{name}**: {info['description']}\n"
        if not info["installed"]:
            all_installed = False
            result += f"   Install: `{info['install']}`\n"
            result += f"   Download: {info['url']}\n"
        result += "\n"

    if all_installed:
        result += "✨ All search tools are installed and ready!"
    else:
        result += "💡 Install missing tools for full search capabilities."

    return result
