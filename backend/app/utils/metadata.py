"""
Audio metadata writing using mutagen.
Injects source URL into MP3 ID3 tags and FLAC Vorbis comments.
"""
import os
from pathlib import Path
from typing import Optional

try:
    from mutagen.id3 import ID3, TXXX, TIT2, TPE1, TALB
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen import File as MutagenFile
except ImportError:
    raise ImportError("mutagen is required. Install with: pip install mutagen")

from app.core.logger import setup_logger

logger = setup_logger(__name__)


def write_source_url_to_metadata(file_path: str, source_url: str) -> bool:
    """
    Write source URL to audio file metadata.
    
    Supports:
    - MP3: ID3 tags (TXXX frame)
    - FLAC: Vorbis comments
    
    Args:
        file_path: Path to audio file
        source_url: Source URL to store
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    try:
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == ".mp3":
            return _write_mp3_metadata(file_path, source_url)
        elif file_ext == ".flac":
            return _write_flac_metadata(file_path, source_url)
        else:
            # Try generic mutagen File for other formats
            return _write_generic_metadata(file_path, source_url)
    
    except Exception as e:
        logger.warning(f"Failed to write metadata to {file_path}: {e}")
        return False


def _write_mp3_metadata(file_path: str, source_url: str) -> bool:
    """Write source URL to MP3 ID3 tags."""
    try:
        audio_file = MP3(file_path, ID3=ID3)
        
        # Create ID3 tag if it doesn't exist
        if audio_file.tags is None:
            audio_file.add_tags()
        
        # Add source URL as TXXX frame (user-defined text)
        audio_file.tags.add(TXXX(encoding=3, desc="SOURCE_URL", text=source_url))
        
        # Save
        audio_file.save()
        logger.debug(f"Wrote source URL to MP3 metadata: {file_path}")
        return True
    
    except Exception as e:
        logger.warning(f"Error writing MP3 metadata: {e}")
        return False


def _write_flac_metadata(file_path: str, source_url: str) -> bool:
    """Write source URL to FLAC Vorbis comments."""
    try:
        audio_file = FLAC(file_path)
        
        # Add source URL as Vorbis comment
        audio_file["SOURCE_URL"] = [source_url]
        
        # Save
        audio_file.save()
        logger.debug(f"Wrote source URL to FLAC metadata: {file_path}")
        return True
    
    except Exception as e:
        logger.warning(f"Error writing FLAC metadata: {e}")
        return False


def _write_generic_metadata(file_path: str, source_url: str) -> bool:
    """Write source URL using generic mutagen File (for other formats)."""
    try:
        audio_file = MutagenFile(file_path)
        
        if audio_file is None:
            logger.warning(f"Could not open file with mutagen: {file_path}")
            return False
        
        # Try to add source URL (format-dependent)
        if hasattr(audio_file, 'tags'):
            if audio_file.tags is None:
                # Some formats don't support tags
                logger.debug(f"File format does not support tags: {file_path}")
                return False
            
            # Try common tag names
            tag_names = ["SOURCE_URL", "SOURCE", "URL", "SOURCEURL"]
            for tag_name in tag_names:
                try:
                    audio_file.tags[tag_name] = [source_url]
                    audio_file.save()
                    logger.debug(f"Wrote source URL to metadata: {file_path}")
                    return True
                except (KeyError, AttributeError):
                    continue
        
        logger.warning(f"Could not write metadata to {file_path} (format may not support tags)")
        return False
    
    except Exception as e:
        logger.warning(f"Error writing generic metadata: {e}")
        return False


def read_source_url_from_metadata(file_path: str) -> Optional[str]:
    """
    Read source URL from audio file metadata.
    
    Supports:
    - MP3: ID3 tags (TXXX frame)
    - FLAC: Vorbis comments
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Source URL if found, None otherwise
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
    
    try:
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == ".mp3":
            return _read_mp3_metadata(file_path)
        elif file_ext == ".flac":
            return _read_flac_metadata(file_path)
        else:
            # Try generic mutagen File for other formats
            return _read_generic_metadata(file_path)
    
    except Exception as e:
        logger.warning(f"Failed to read metadata from {file_path}: {e}")
        return None


def _read_mp3_metadata(file_path: str) -> Optional[str]:
    """Read source URL from MP3 ID3 tags."""
    try:
        audio_file = MP3(file_path, ID3=ID3)
        
        if audio_file.tags is None:
            return None
        
        # Look for TXXX frame with SOURCE_URL description
        for tag in audio_file.tags.values():
            if isinstance(tag, TXXX) and tag.desc == "SOURCE_URL":
                return tag.text[0] if tag.text else None
        
        return None
    
    except Exception as e:
        logger.warning(f"Error reading MP3 metadata: {e}")
        return None


def _read_flac_metadata(file_path: str) -> Optional[str]:
    """Read source URL from FLAC Vorbis comments."""
    try:
        audio_file = FLAC(file_path)
        
        if "SOURCE_URL" in audio_file:
            return audio_file["SOURCE_URL"][0]
        
        return None
    
    except Exception as e:
        logger.warning(f"Error reading FLAC metadata: {e}")
        return None


def _read_generic_metadata(file_path: str) -> Optional[str]:
    """Read source URL using generic mutagen File (for other formats)."""
    try:
        audio_file = MutagenFile(file_path)
        
        if audio_file is None:
            return None
        
        if hasattr(audio_file, 'tags') and audio_file.tags:
            # Try common tag names
            tag_names = ["SOURCE_URL", "SOURCE", "URL", "SOURCEURL"]
            for tag_name in tag_names:
                if tag_name in audio_file.tags:
                    value = audio_file.tags[tag_name]
                    if isinstance(value, list) and value:
                        return value[0]
                    elif value:
                        return str(value)
        
        return None
    
    except Exception as e:
        logger.warning(f"Error reading generic metadata: {e}")
        return None

