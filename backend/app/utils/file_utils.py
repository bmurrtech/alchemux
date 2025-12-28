"""
File management utilities for save path, directory creation, and file organization.
"""
import os
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
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    # Limit length
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    
    logger.debug(f"Sanitized filename: {filename}")
    return filename

