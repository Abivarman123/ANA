"""Application launcher tools for ANA.

This module provides tools to open various applications on Windows.
"""

import logging
import os
import subprocess
import sys
from typing import Optional

from livekit.agents import RunContext, function_tool

from .base import handle_tool_error

logger = logging.getLogger(__name__)

# Common application paths and aliases for Windows
APP_REGISTRY = {
    # Browsers
    "chrome": {
        "paths": [
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        ],
        "aliases": ["google chrome", "google", "browser"],
    },
    # IDEs and Editors
    "vscode": {
        "paths": [
            os.path.expandvars("%LOCALAPPDATA%/Programs/Microsoft VS Code/Code.exe"),
            "C:/Program Files/Microsoft VS Code/Code.exe",
        ],
        "aliases": ["visual studio code", "vs code", "code"],
        "command": "code",  # Also available via command line
    },
    "notepad": {
        "paths": ["notepad.exe"],
        "aliases": ["text editor", "notepad"],
    },
    # System Utilities
    "explorer": {
        "paths": ["explorer.exe"],
        "aliases": [
            "file explorer",
            "files",
            "my computer",
            "this pc",
            "windows explorer",
        ],
    },
    "cmd": {
        "paths": ["cmd.exe"],
        "aliases": ["command prompt", "terminal", "command line"],
    },
    "powershell": {
        "paths": ["powershell.exe"],
        "aliases": ["ps", "posh", "windows powershell"],
    },
    "terminal": {
        "paths": [
            os.path.expandvars("%LOCALAPPDATA%/Microsoft/WindowsApps/wt.exe"),
        ],
        "aliases": ["windows terminal", "wt"],
        "command": "wt",
    },
    "task_manager": {
        "paths": ["taskmgr.exe"],
        "aliases": ["task manager", "taskmgr", "processes"],
    },
    "settings": {
        "paths": ["ms-settings:"],
        "aliases": ["windows settings", "system settings"],
        "shell_execute": True,
    },
    "control_panel": {
        "paths": ["control.exe"],
        "aliases": ["control panel", "control"],
    },
    # Microsoft Office
    "word": {
        "paths": [
            "C:/Program Files/Microsoft Office/root/Office16/WINWORD.EXE",
            "C:/Program Files (x86)/Microsoft Office/root/Office16/WINWORD.EXE",
        ],
        "aliases": ["microsoft word", "ms word", "winword"],
    },
    "excel": {
        "paths": [
            "C:/Program Files/Microsoft Office/root/Office16/EXCEL.EXE",
            "C:/Program Files (x86)/Microsoft Office/root/Office16/EXCEL.EXE",
        ],
        "aliases": ["microsoft excel", "ms excel"],
    },
    "powerpoint": {
        "paths": [
            "C:/Program Files/Microsoft Office/root/Office16/POWERPNT.EXE",
            "C:/Program Files (x86)/Microsoft Office/root/Office16/POWERPNT.EXE",
        ],
        "aliases": ["microsoft powerpoint", "ms powerpoint", "ppt"],
    },
    # Communication
    "discord": {
        "paths": [
            os.path.expandvars("%LOCALAPPDATA%/Discord/Update.exe"),
        ],
        "aliases": [],
        "args": ["--processStart", "Discord.exe"],
    },
    # Media
    "vlc": {
        "paths": [
            "C:/Program Files/VideoLAN/VLC/vlc.exe",
            "C:/Program Files (x86)/VideoLAN/VLC/vlc.exe",
        ],
        "aliases": ["vlc media player", "media player"],
    },
    # Utilities
    "calculator": {
        "paths": ["calc.exe"],
        "aliases": ["calc"],
    },
    "paint": {
        "paths": ["mspaint.exe"],
        "aliases": ["ms paint", "microsoft paint"],
    },
    "snipping_tool": {
        "paths": ["snippingtool.exe"],
        "aliases": ["snipping tool", "screenshot", "snip"],
    },
}


def _normalize_app_name(app_name: str) -> str:
    """Normalize app name for matching."""
    return app_name.lower().strip().replace("-", "_").replace(" ", "_")


def _find_app(app_name: str) -> Optional[dict]:
    """Find application config by name or alias."""
    normalized = _normalize_app_name(app_name)

    # Direct match
    if normalized in APP_REGISTRY:
        return APP_REGISTRY[normalized]

    # Search through aliases
    for name, config in APP_REGISTRY.items():
        for alias in config.get("aliases", []):
            if normalized == _normalize_app_name(alias):
                return config

    return None


def _find_executable(paths: list[str]) -> Optional[str]:
    """Find the first existing executable path."""
    for path in paths:
        expanded = os.path.expandvars(path)
        if os.path.exists(expanded):
            return expanded
    return None


@function_tool()
@handle_tool_error("open_application")
async def open_application(
    context: RunContext,
    app_name: str,
    path: str = "",
) -> str:
    """Open an application on the computer.

    Use this tool to launch desktop applications like Chrome, VSCode, Explorer, etc.

    Args:
        app_name: Name of the application to open (e.g., "chrome", "vscode", "explorer",
                  "spotify", "discord", "terminal", "notepad", "calculator", etc.)
        path: Optional file or folder path to open with the application
              (e.g., open vscode with a specific folder, or explorer with a path)

    Returns:
        Success message or error if application not found
    """
    logger.info(f"Opening application: {app_name}, path: {path}")

    app_config = _find_app(app_name)

    if app_config:
        # Check if it's a shell execute command (like ms-settings:)
        if app_config.get("shell_execute"):
            if sys.platform != "win32":
                return "This feature is only available on Windows."
            target = app_config["paths"][0]
            os.startfile(target)
            logger.info(f"✓ Opened {app_name} via shell")
            return f"✓ Opened {app_name}"

        # Try to find executable path
        exe_path = _find_executable(app_config["paths"])

        # Try command-line fallback if available
        if not exe_path and app_config.get("command"):
            try:
                cmd = [app_config["command"]]
                if path:
                    cmd.append(path)
                subprocess.Popen(cmd, shell=False)
                logger.info(f"✓ Opened {app_name} via command: {app_config['command']}")
                return f"✓ Opened {app_name}" + (f" with {path}" if path else "")
            except Exception as e:
                logger.warning(f"Command fallback failed: {e}")
        if exe_path:
            try:
                cmd = [exe_path]
                # Add extra args if defined
                if args := app_config.get("args"):
                    cmd.extend(args)
                # Add path argument if provided
                if path:
                    cmd.append(path)

                subprocess.Popen(cmd)
                logger.info(f"✓ Opened {app_name}: {exe_path}")
                return f"✓ Opened {app_name}" + (f" with {path}" if path else "")
            except Exception as e:
                logger.error(f"Failed to open {app_name}: {e}")
                return f"Failed to open {app_name}: {str(e)}"
        else:
            return (
                f"Could not find {app_name}. It may not be installed on this computer."
            )

    # Try to open as a direct command/executable
    try:
        cmd = [app_name]
        if path:
            cmd.append(path)
        subprocess.Popen(cmd, shell=False)
        logger.info(f"✓ Opened {app_name} as direct command")
        return f"✓ Opened {app_name}" + (f" with {path}" if path else "")
    except Exception as e:
        logger.warning(f"Direct command failed: {e}")


@function_tool()
@handle_tool_error("list_applications")
async def list_applications(
    context: RunContext,
) -> str:
    """List all available applications that can be opened.

    Returns a list of application names that can be used with the open_application tool.
    """
    categories = {
        "Browsers": ["chrome", "firefox", "edge", "brave"],
        "IDEs & Editors": ["vscode", "cursor", "notepad", "notepad++"],
        "System Utilities": [
            "explorer",
            "cmd",
            "powershell",
            "terminal",
            "task_manager",
            "settings",
            "control_panel",
        ],
        "Microsoft Office": ["word", "excel", "powerpoint"],
        "Communication": ["discord"],
        "Media": ["vlc"],
        "Utilities": ["calculator", "paint", "snipping_tool"],
    }

    result = "Available applications:\n\n"
    seen_apps = set()

    for category, apps in categories.items():
        available = []
        for app_name in apps:
            seen_apps.add(app_name)
            app_config = _find_app(app_name)
            if app_config:
                exe_path = _find_executable(app_config["paths"])
                status = "✓" if exe_path or app_config.get("shell_execute") else "?"
                available.append(f"{status} {app_name}")
            else:
                # App name from categories not in registry, still show it as ?
                available.append(f"? {app_name}")

        if available:
            result += f"**{category}:**\n"
            result += "  " + ", ".join(available) + "\n\n"

    # Add any apps in registry that weren't in categories
    other_apps = []
    for app in APP_REGISTRY:
        if app not in seen_apps:
            exe_path = _find_executable(APP_REGISTRY[app]["paths"])
            status = "✓" if exe_path or APP_REGISTRY[app].get("shell_execute") else "?"
            other_apps.append(f"{status} {app}")

    if other_apps:
        result += "**Other:**\n"
        result += "  " + ", ".join(other_apps) + "\n\n"

    result += "✓ = Installed/Available, ? = May not be installed\n"
    result += "\nUse: open_application(app_name='chrome') to open an app"

    return result


@function_tool()
@handle_tool_error("close_application")
async def close_application(
    context: RunContext,
    app_name: str,
) -> str:
    """Close a running application.

    Args:
        app_name: Name of the application to close (e.g., "chrome", "vscode", "spotify")

    Returns:
        Success message or error if application not found/not running
    """
    logger.info(f"Closing application: {app_name}")

    if sys.platform != "win32":
        return "This feature is only available on Windows."

    # Map app names to process names
    process_names = {
        "chrome": ["chrome.exe"],
        "firefox": ["firefox.exe"],
        "edge": ["msedge.exe"],
        "brave": ["brave.exe"],
        "vscode": ["Code.exe"],
        "cursor": ["Cursor.exe"],
        "notepad": ["notepad.exe"],
        "notepad++": ["notepad++.exe"],
        "explorer": ["explorer.exe"],
        "discord": ["Discord.exe"],
        "slack": ["slack.exe"],
        "teams": ["Teams.exe"],
        "spotify": ["Spotify.exe"],
        "vlc": ["vlc.exe"],
        "steam": ["steam.exe"],
    }

    normalized = _normalize_app_name(app_name)
    targets = process_names.get(normalized, [f"{normalized}.exe"])

    closed = False
    for process_name in targets:
        try:
            result = subprocess.run(
                ["taskkill", "/IM", process_name, "/F"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                closed = True
                logger.info(f"✓ Closed {process_name}")
        except Exception as e:
            logger.warning(f"Failed to close {process_name}: {e}")

    if closed:
        return f"✓ Closed {app_name}"
    else:
        return f"Could not close {app_name}. It may not be running."
