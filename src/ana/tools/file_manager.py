"""Safe Desktop File Manager tools for ANA.

This module provides file management capabilities within a sandboxed environment.
All operations are restricted to ~/Desktop for security.
"""

import logging
from pathlib import Path

from livekit.agents import RunContext, function_tool
from send2trash import send2trash

from ..config import config
from .base import handle_tool_error

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".csv",
    ".log",
    ".py",
    ".js",
    ".html",
    ".css",
    ".xml",
    ".yaml",
    ".yml",
    ".pdf",
    ".doc",
    ".docx",
    ".sql",
    ".db",
}

BLOCKED_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".sh",
    ".ps1",
    ".msi",
    ".app",
    ".dmg",
    ".vbs",
    ".wsf",
    ".scr",
    ".pif",
    ".com",
    ".sys",
    ".dll",
    ".so",
    ".dylib",
}


class FileManagerError(Exception):
    """Custom exception for file manager errors."""

    pass


def _get_sandbox_path() -> Path:
    """Get the sandbox directory path from config."""
    sandbox = config.get("file_manager", {}).get("sandbox_path", "~/Desktop")
    return Path(sandbox).expanduser().resolve()


def _validate_path(file_path: str) -> Path:
    """Validate and sanitize file path to prevent directory traversal."""
    sandbox = _get_sandbox_path()
    file_path = file_path.strip()

    if ".." in file_path or file_path.startswith(("/", "\\")):
        raise FileManagerError(
            "Invalid path: Directory traversal detected. Paths must be relative to Desktop."
        )

    full_path = (sandbox / file_path).resolve()

    try:
        full_path.relative_to(sandbox)
    except ValueError:
        raise FileManagerError(f"Access denied: Path must be within {sandbox}")

    return full_path


def _validate_extension(file_path: Path) -> None:
    """Validate file extension for safety."""
    extension = file_path.suffix.lower()

    if extension in BLOCKED_EXTENSIONS:
        raise FileManagerError(
            f"Blocked file type: {extension} files are not allowed for security reasons."
        )

    if extension and extension not in ALLOWED_EXTENSIONS:
        raise FileManagerError(
            f"Unsupported file type: {extension}. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )


def _validate_size(size: int, item_name: str = "File") -> None:
    """Validate size doesn't exceed maximum."""
    if size > MAX_FILE_SIZE:
        size_mb = size / (1024 * 1024)
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        raise FileManagerError(
            f"{item_name} too large: {size_mb:.2f}MB exceeds {max_mb}MB limit."
        )


@function_tool()
@handle_tool_error("create_file")
async def create_file(context: RunContext, file_path: str, content: str = "") -> str:
    """Create a new file with given content in the Desktop sandbox."""
    logging.info(f"create_file: {file_path}, content_length={len(content)}")

    full_path = _validate_path(file_path)
    _validate_extension(full_path)
    _validate_size(len(content.encode("utf-8")), "Content")

    if full_path.exists():
        raise FileManagerError(f"File already exists: {file_path}")

    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")

    logging.info(f"✓ Created: {full_path}")
    return f"✓ File created successfully: {file_path}"


@function_tool()
@handle_tool_error("read_file")
async def read_file(context: RunContext, file_path: str) -> str:
    """Read content from a file in the Desktop sandbox."""
    full_path = _validate_path(file_path)
    _validate_extension(full_path)

    if not full_path.exists():
        raise FileManagerError(f"File not found: {file_path}")
    if not full_path.is_file():
        raise FileManagerError(f"Not a file: {file_path}")

    _validate_size(full_path.stat().st_size)

    try:
        content = full_path.read_text(encoding="utf-8")
        logging.info(f"Read: {full_path}")
        return f"Content of {file_path}:\n\n{content}"
    except UnicodeDecodeError:
        raise FileManagerError(
            f"{file_path} is not a text file or has invalid encoding"
        )


@function_tool()
@handle_tool_error("edit_file")
async def edit_file(context: RunContext, file_path: str, content: str) -> str:
    """Edit an existing file by replacing its content."""
    full_path = _validate_path(file_path)
    _validate_extension(full_path)
    _validate_size(len(content.encode("utf-8")), "Content")

    if not full_path.exists():
        raise FileManagerError(
            f"File not found: {file_path}. Use create_file to create new files."
        )
    if not full_path.is_file():
        raise FileManagerError(f"Not a file: {file_path}")

    full_path.write_text(content, encoding="utf-8")
    logging.info(f"Edited: {full_path}")
    return f"✓ File edited successfully: {file_path}"


@function_tool()
@handle_tool_error("list_files")
async def list_files(context: RunContext, directory: str = "") -> str:
    """List all files in a directory within the Desktop sandbox."""
    # Handle special case: "Desktop" means root
    if directory.lower() in ("desktop", ""):
        directory = ""

    full_path = _validate_path(directory) if directory else _get_sandbox_path()

    if not full_path.exists():
        raise FileManagerError(f"Directory not found: {directory or 'Desktop'}")
    if not full_path.is_dir():
        raise FileManagerError(f"Not a directory: {directory}")

    sandbox = _get_sandbox_path()
    items = []

    for item in sorted(full_path.iterdir()):
        try:
            rel_path = item.relative_to(sandbox)
            if item.is_dir():
                items.append(f"📁 {rel_path}/")
            else:
                size = item.stat().st_size
                size_str = (
                    f"{size / 1024:.1f}KB"
                    if size < 1024 * 1024
                    else f"{size / (1024 * 1024):.1f}MB"
                )
                items.append(f"📄 {rel_path} ({size_str})")
        except Exception as e:
            logging.warning(f"Skipped item {item}: {e}")

    if not items:
        return f"Directory is empty: {directory or 'Desktop'}"

    location = directory or "Desktop"
    logging.info(f"Listed: {full_path}")
    return f"Contents of {location}:\n\n" + "\n".join(items)


@function_tool()
@handle_tool_error("delete_file")
async def delete_file(context: RunContext, file_path: str) -> str:
    """Move a file to the recycle bin from the Desktop sandbox."""
    full_path = _validate_path(file_path)

    if not full_path.exists():
        raise FileManagerError(f"File not found: {file_path}")
    if not full_path.is_file():
        raise FileManagerError(
            f"Not a file: {file_path}. Use this only for files, not directories."
        )

    send2trash(str(full_path))
    logging.info(f"Moved to recycle bin: {full_path}")
    return f"✓ File moved to recycle bin: {file_path}"


@function_tool()
@handle_tool_error("delete_folder")
async def delete_folder(context: RunContext, folder_path: str) -> str:
    """Move a folder and all its contents to the recycle bin from the Desktop sandbox."""
    full_path = _validate_path(folder_path)

    if not full_path.exists():
        raise FileManagerError(f"Folder not found: {folder_path}")
    if not full_path.is_dir():
        raise FileManagerError(
            f"Not a folder: {folder_path}. Use delete_file for files."
        )

    send2trash(str(full_path))
    logging.info(f"Moved folder to recycle bin: {full_path}")
    return f"✓ Folder moved to recycle bin: {folder_path}"
