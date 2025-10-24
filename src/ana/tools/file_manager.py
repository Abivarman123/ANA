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

# Constants for safety
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB in bytes
ALLOWED_EXTENSIONS = {
    # Text files
    ".txt", ".md", ".json", ".csv", ".log",
    # Code files
    ".py", ".js", ".html", ".css", ".xml", ".yaml", ".yml",
    # Documents
    ".pdf", ".doc", ".docx",
    # Data
    ".sql", ".db",
}

BLOCKED_EXTENSIONS = {
    # Executables
    ".exe", ".bat", ".cmd", ".sh", ".ps1", ".msi", ".app", ".dmg",
    # Scripts that can execute
    ".vbs", ".wsf", ".scr", ".pif", ".com",
    # System files
    ".sys", ".dll", ".so", ".dylib",
}


class FileManagerError(Exception):
    """Custom exception for file manager errors."""
    pass


def _get_sandbox_path() -> Path:
    """Get the sandbox directory path from config."""
    sandbox = config.get("file_manager", {}).get("sandbox_path", "~/Desktop")
    return Path(sandbox).expanduser().resolve()


def _validate_path(file_path: str) -> Path:
    """
    Validate and sanitize file path to prevent directory traversal.
    
    Args:
        file_path: User-provided file path
        
    Returns:
        Validated absolute Path object
        
    Raises:
        FileManagerError: If path is invalid or outside sandbox
    """
    sandbox = _get_sandbox_path()
    
    # Remove any leading/trailing whitespace
    file_path = file_path.strip()
    
    # Check for directory traversal attempts
    if ".." in file_path or file_path.startswith("/") or file_path.startswith("\\"):
        raise FileManagerError(
            "Invalid path: Directory traversal detected. Paths must be relative to Desktop."
        )
    
    # Resolve the full path
    full_path = (sandbox / file_path).resolve()
    
    # Ensure the resolved path is still within sandbox
    try:
        full_path.relative_to(sandbox)
    except ValueError:
        raise FileManagerError(
            f"Access denied: Path must be within {sandbox}"
        )
    
    return full_path


def _validate_extension(file_path: Path) -> None:
    """
    Validate file extension for safety.
    
    Args:
        file_path: Path object to validate
        
    Raises:
        FileManagerError: If extension is blocked or not allowed
    """
    extension = file_path.suffix.lower()
    
    # Check blocked extensions first
    if extension in BLOCKED_EXTENSIONS:
        raise FileManagerError(
            f"Blocked file type: {extension} files are not allowed for security reasons."
        )
    
    # Check if extension is in allowed list
    if extension and extension not in ALLOWED_EXTENSIONS:
        raise FileManagerError(
            f"Unsupported file type: {extension}. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )


def _validate_file_size(file_path: Path) -> None:
    """
    Validate file size doesn't exceed maximum.
    
    Args:
        file_path: Path to file to check
        
    Raises:
        FileManagerError: If file exceeds size limit
    """
    if file_path.exists():
        size = file_path.stat().st_size
        if size > MAX_FILE_SIZE:
            size_mb = size / (1024 * 1024)
            max_mb = MAX_FILE_SIZE / (1024 * 1024)
            raise FileManagerError(
                f"File too large: {size_mb:.2f}MB exceeds {max_mb}MB limit."
            )


def _validate_content_size(content: str) -> None:
    """
    Validate content size before writing.
    
    Args:
        content: Content to validate
        
    Raises:
        FileManagerError: If content exceeds size limit
    """
    size = len(content.encode('utf-8'))
    if size > MAX_FILE_SIZE:
        size_mb = size / (1024 * 1024)
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        raise FileManagerError(
            f"Content too large: {size_mb:.2f}MB exceeds {max_mb}MB limit."
        )


@function_tool()
@handle_tool_error("create_file")
async def create_file(
    context: RunContext,  # type: ignore
    file_path: str,
    content: str = "",
) -> str:
    """
    Create a new file with given content in the Desktop sandbox.
    
    Args:
        file_path: Relative path to file (e.g., "notes.txt" or "projects/todo.md")
        content: Content to write to the file (optional, defaults to empty)
        
    Returns:
        Success message with file path
    """
    logging.info(f"create_file tool called with file_path='{file_path}', content_length={len(content)}")
    try:
        # Validate path and extension
        full_path = _validate_path(file_path)
        logging.info(f"Validated path: {full_path}")
        _validate_extension(full_path)
        _validate_content_size(content)
        
        # Check if file already exists
        if full_path.exists():
            raise FileManagerError(f"File already exists: {file_path}")
        
        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content to file
        full_path.write_text(content, encoding='utf-8')
        
        logging.info(f"✓ Successfully created file: {full_path}")
        return f"✓ File created successfully: {file_path}"
        
    except FileManagerError as e:
        logging.error(f"File creation failed: {e}")
        return f"✗ Failed to create file: {str(e)}"


@function_tool()
@handle_tool_error("read_file")
async def read_file(
    context: RunContext,  # type: ignore
    file_path: str,
) -> str:
    """
    Read content from a file in the Desktop sandbox.
    
    Args:
        file_path: Relative path to file to read
        
    Returns:
        File content or error message
    """
    try:
        # Validate path and extension
        full_path = _validate_path(file_path)
        _validate_extension(full_path)
        
        # Check if file exists
        if not full_path.exists():
            raise FileManagerError(f"File not found: {file_path}")
        
        if not full_path.is_file():
            raise FileManagerError(f"Not a file: {file_path}")
        
        # Validate file size
        _validate_file_size(full_path)
        
        # Read and return content
        content = full_path.read_text(encoding='utf-8')
        logging.info(f"Read file: {full_path}")
        
        return f"Content of {file_path}:\n\n{content}"
        
    except FileManagerError as e:
        logging.error(f"File read failed: {e}")
        return f"✗ Failed to read file: {str(e)}"
    except UnicodeDecodeError:
        return f"✗ Cannot read file: {file_path} is not a text file or has invalid encoding."


@function_tool()
@handle_tool_error("edit_file")
async def edit_file(
    context: RunContext,  # type: ignore
    file_path: str,
    content: str,
) -> str:
    """
    Edit an existing file by replacing its content.
    
    Args:
        file_path: Relative path to file to edit
        content: New content to write to the file
        
    Returns:
        Success message or error
    """
    try:
        # Validate path and extension
        full_path = _validate_path(file_path)
        _validate_extension(full_path)
        _validate_content_size(content)
        
        # Check if file exists
        if not full_path.exists():
            raise FileManagerError(f"File not found: {file_path}. Use create_file to create new files.")
        
        if not full_path.is_file():
            raise FileManagerError(f"Not a file: {file_path}")
        
        # Write new content
        full_path.write_text(content, encoding='utf-8')
        
        logging.info(f"Edited file: {full_path}")
        return f"✓ File edited successfully: {file_path}"
        
    except FileManagerError as e:
        logging.error(f"File edit failed: {e}")
        return f"✗ Failed to edit file: {str(e)}"


@function_tool()
@handle_tool_error("list_files")
async def list_files(
    context: RunContext,  # type: ignore
    directory: str = "",
) -> str:
    """
    List all files in a directory within the Desktop sandbox.
    
    Args:
        directory: Relative path to directory (empty string or "Desktop" for Desktop root)
        
    Returns:
        Formatted list of files and directories
    """
    try:
        # Handle special case: "Desktop" means root
        if directory.lower() in ("desktop", ""):
            directory = ""
        
        # Validate path
        full_path = _validate_path(directory) if directory else _get_sandbox_path()
        
        # Check if directory exists
        if not full_path.exists():
            raise FileManagerError(f"Directory not found: {directory or 'Desktop'}")
        
        if not full_path.is_dir():
            raise FileManagerError(f"Not a directory: {directory}")
        
        # List contents
        items = []
        for item in sorted(full_path.iterdir()):
            try:
                # Get relative path from sandbox
                rel_path = item.relative_to(_get_sandbox_path())
                
                if item.is_dir():
                    items.append(f"📁 {rel_path}/")
                else:
                    size = item.stat().st_size
                    size_str = f"{size / 1024:.1f}KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f}MB"
                    items.append(f"📄 {rel_path} ({size_str})")
            except Exception as e:
                logging.warning(f"Skipped item {item}: {e}")
                continue
        
        if not items:
            return f"Directory is empty: {directory or 'Desktop'}"
        
        location = directory or "Desktop"
        result = f"Contents of {location}:\n\n" + "\n".join(items)
        
        logging.info(f"Listed directory: {full_path}")
        return result
        
    except FileManagerError as e:
        logging.error(f"Directory listing failed: {e}")
        return f"✗ Failed to list directory: {str(e)}"


@function_tool()
@handle_tool_error("delete_file")
async def delete_file(
    context: RunContext,  # type: ignore
    file_path: str,
) -> str:
    """
    Move a file to the recycle bin from the Desktop sandbox.
    
    Args:
        file_path: Relative path to file to delete
        
    Returns:
        Success message or error
    """
    try:
        # Validate path
        full_path = _validate_path(file_path)
        
        # Check if file exists
        if not full_path.exists():
            raise FileManagerError(f"File not found: {file_path}")
        
        if not full_path.is_file():
            raise FileManagerError(f"Not a file: {file_path}. Use this only for files, not directories.")
        
        # Move file to recycle bin instead of permanent deletion
        send2trash(str(full_path))
        
        logging.info(f"Moved file to recycle bin: {full_path}")
        return f"✓ File moved to recycle bin: {file_path}"
        
    except FileManagerError as e:
        logging.error(f"File deletion failed: {e}")
        return f"✗ Failed to delete file: {str(e)}"


@function_tool()
@handle_tool_error("delete_folder")
async def delete_folder(
    context: RunContext,  # type: ignore
    folder_path: str,
) -> str:
    """
    Move a folder and all its contents to the recycle bin from the Desktop sandbox.
    
    Args:
        folder_path: Relative path to folder to delete
        
    Returns:
        Success message or error
    """
    try:
        # Validate path
        full_path = _validate_path(folder_path)
        
        # Check if folder exists
        if not full_path.exists():
            raise FileManagerError(f"Folder not found: {folder_path}")
        
        if not full_path.is_dir():
            raise FileManagerError(f"Not a folder: {folder_path}. Use delete_file for files.")
        
        # Move folder and all contents to recycle bin instead of permanent deletion
        send2trash(str(full_path))
        
        logging.info(f"Moved folder to recycle bin: {full_path}")
        return f"✓ Folder moved to recycle bin: {folder_path}"
        
    except FileManagerError as e:
        logging.error(f"Folder deletion failed: {e}")
        return f"✗ Failed to delete folder: {str(e)}"
