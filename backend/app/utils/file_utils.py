"""
File management utilities for save path, directory creation, and file organization.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional

from app.core.logger import setup_logger

logger = setup_logger(__name__)


def get_media_folder(source_type: str) -> str:
    """
    Get folder name for organizing files by source type.

    Args:
        source_type: Source type (youtube, facebook, etc.)

    Returns:
        Folder name for organization
    """
    mapping = {
        "youtube": "youtube",
        "facebook": "facebook",
        "soundcloud": "soundcloud",
        "spotify": "spotify",
        "apple_podcasts": "podcasts",
        "unknown": "other",
    }
    return mapping.get(source_type, "other")


def ensure_directory(path: str) -> Path:
    """
    Ensure directory exists, creating it if necessary.

    Args:
        path: Directory path (can be relative or absolute)

    Returns:
        Path object for the directory
    """
    path_obj = Path(path).expanduser().resolve()
    path_obj.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured directory exists: {path_obj}")
    return path_obj


def get_download_path(base_path: str, source_type: str, filename: str) -> Path:
    """
    Get full download path for a file, organized by source type.

    Args:
        base_path: Base download directory
        source_type: Source type (youtube, facebook, etc.)
        filename: Filename

    Returns:
        Full Path object for the file
    """
    base = ensure_directory(base_path)
    media_folder = get_media_folder(source_type)
    folder = base / media_folder
    ensure_directory(str(folder))

    file_path = folder / filename
    logger.debug(f"Download path: {file_path}")
    return file_path


def detect_source_type(url: str) -> str:
    """
    Detect media source type from URL.

    Args:
        url: Media URL

    Returns:
        Source type (youtube, facebook, soundcloud, etc.)
    """
    url_lower = url.lower()
    if any(d in url_lower for d in ["youtube.com", "youtu.be"]):
        return "youtube"
    if any(d in url_lower for d in ["facebook.com", "fb.watch", "m.facebook.com"]):
        return "facebook"
    if "soundcloud.com" in url_lower:
        return "soundcloud"
    if "spotify.com" in url_lower:
        return "spotify"
    if "podcasts.apple.com" in url_lower:
        return "apple_podcasts"
    return "unknown"


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize filename for cross-platform compatibility.

    Args:
        filename: Original filename
        max_length: Maximum filename length

    Returns:
        Sanitized filename
    """
    import re

    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")
    # Limit length
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[: max_length - len(ext)] + ext

    logger.debug(f"Sanitized filename: {filename}")
    return filename


def get_resource_path(relative_path: str) -> Path:
    """
    Get absolute path to resource, works for dev and for PyInstaller.

    When running as PyInstaller binary, resources are extracted to _MEIPASS.
    When running from source, resources are relative to the project root.

    Args:
        relative_path: Relative path to resource (e.g., 'ffmpeg' or 'ffmpeg.exe')

    Returns:
        Absolute Path to resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # Running from source
        base_path = Path(__file__).parent.parent.parent.parent

    return base_path / relative_path


def find_ffmpeg_binary() -> Optional[Path]:
    """
    Find ffmpeg binary, checking bundled location first, then system PATH.

    Returns:
        Path to ffmpeg binary, or None if not found
    """
    # Determine binary name based on platform
    if sys.platform == "win32":
        binary_name = "ffmpeg.exe"
    else:
        binary_name = "ffmpeg"

    # First, check if bundled with PyInstaller
    try:
        bundled_path = get_resource_path(binary_name)
        if bundled_path.exists() and os.access(bundled_path, os.X_OK):
            logger.debug(f"Found bundled ffmpeg: {bundled_path}")
            return bundled_path
    except Exception as e:
        logger.debug(f"Could not check bundled ffmpeg: {e}")

    # Fall back to system PATH
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        logger.debug(f"Found ffmpeg in PATH: {ffmpeg_path}")
        return Path(ffmpeg_path)

    logger.warning("ffmpeg not found in bundled location or system PATH")
    return None


def find_ffprobe_binary() -> Optional[Path]:
    """
    Find ffprobe binary, checking bundled location first, then system PATH.

    Returns:
        Path to ffprobe binary, or None if not found
    """
    # Determine binary name based on platform
    if sys.platform == "win32":
        binary_name = "ffprobe.exe"
    else:
        binary_name = "ffprobe"

    # First, check if bundled with PyInstaller
    try:
        bundled_path = get_resource_path(binary_name)
        if bundled_path.exists() and os.access(bundled_path, os.X_OK):
            logger.debug(f"Found bundled ffprobe: {bundled_path}")
            return bundled_path
    except Exception as e:
        logger.debug(f"Could not check bundled ffprobe: {e}")

    # Fall back to system PATH
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path:
        logger.debug(f"Found ffprobe in PATH: {ffprobe_path}")
        return Path(ffprobe_path)

    logger.warning("ffprobe not found in bundled location or system PATH")
    return None


def get_ffmpeg_location() -> Optional[str]:
    """
    Get ffmpeg location for yt-dlp, handling bundled, system, and custom paths.

    Checks in order:
    1. FFMPEG_PATH (if FFMPEG_CUSTOM_PATH=true)
    2. Bundled ffmpeg/ffprobe (PyInstaller)
    3. System PATH

    Returns:
        Directory path containing ffmpeg/ffprobe, or None if not found
    """
    # Check if custom path is enabled
    custom_path_enabled = os.getenv("FFMPEG_CUSTOM_PATH", "false").lower() == "true"

    if custom_path_enabled:
        # Check for custom FFMPEG_PATH in environment
        ffmpeg_env = os.getenv("FFMPEG_PATH", "").strip()
        if ffmpeg_env:
            # If it's a file path, use its parent directory
            # If it's a directory, use it directly
            env_path = Path(ffmpeg_env)
            if env_path.is_file():
                logger.debug(f"Using FFMPEG_PATH from environment (file): {env_path}")
                return str(env_path.parent)
            elif env_path.is_dir():
                logger.debug(
                    f"Using FFMPEG_PATH from environment (directory): {env_path}"
                )
                return str(env_path)
            else:
                logger.warning(f"FFMPEG_PATH set but path not found: {ffmpeg_env}")
        else:
            logger.warning("FFMPEG_CUSTOM_PATH=true but FFMPEG_PATH is not set")

    # Fall back to bundled or system ffmpeg
    ffmpeg_path = find_ffmpeg_binary()
    if ffmpeg_path:
        # Return the directory containing ffmpeg
        return str(ffmpeg_path.parent)
    return None
