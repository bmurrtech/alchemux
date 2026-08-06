"""
Audio/video metadata writing using mutagen.

Layer-2 (FR-8): after distill, enrich the sealed file with Artist, compact
comment/description, date, and SOURCE_URL from in-memory extract info + input URL.
"""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Mapping, Optional

try:
    from mutagen.id3 import COMM, ID3, TDRC, TPE1, TXXX
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4, MP4FreeForm, AtomDataType
    from mutagen import File as MutagenFile
except ImportError:
    raise ImportError("mutagen is required. Install with: pip install mutagen")

from app.core.logger import normalize_log_level, setup_logger

logger = setup_logger(__name__)

# Compact description body budget (UTF-8 bytes), excluding Source footer.
COMPACT_DESCRIPTION_MAX_BYTES = 2048

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _log_layer2_issue(message: str) -> None:
    """Surface Layer-2 issues only at verbose/debug (stricter than info)."""
    level = normalize_log_level(os.getenv("LOG_LEVEL", "warning"))
    if level in ("verbose", "debug"):
        logger.warning(message)
    else:
        logger.debug(message)


def sanitize_description_text(text: str) -> str:
    """Unicode NFC + strip controls + normalize newlines; keep emoji."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _CONTROL_RE.sub("", normalized)
    # Collapse runs of blank lines lightly; trim edges.
    lines = [line.rstrip() for line in normalized.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines).strip()


def _truncate_utf8(text: str, max_bytes: int) -> str:
    raw = text.encode("utf-8")
    if len(raw) <= max_bytes:
        return text
    cut = raw[:max_bytes]
    # Avoid splitting a multibyte character.
    while cut:
        try:
            return cut.decode("utf-8") + "…"
        except UnicodeDecodeError:
            cut = cut[:-1]
    return "…"


def build_compact_comment(description: Optional[str], source_url: str) -> str:
    """Sanitized compact description body + Source footer for universality."""
    body = sanitize_description_text(description or "")
    if body:
        body = _truncate_utf8(body, COMPACT_DESCRIPTION_MAX_BYTES)
    footer = f"Source: {source_url}" if source_url else ""
    if body and footer:
        if footer in body:
            return body
        return f"{body}\n\n{footer}"
    return body or footer


def _artist_from_info(info: Optional[Mapping[str, Any]]) -> str:
    if not info:
        return ""
    for key in ("channel", "uploader", "artist", "creator"):
        value = info.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _date_from_info(info: Optional[Mapping[str, Any]]) -> str:
    """Return YYYY-MM-DD or YYYYMMDD-as-YYYY-MM-DD when upload_date is present."""
    if not info:
        return ""
    raw = info.get("upload_date")
    if not isinstance(raw, str) or not raw.strip():
        return ""
    digits = raw.strip()
    if re.fullmatch(r"\d{8}", digits):
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return digits


def write_source_url_to_metadata(file_path: str, source_url: str) -> bool:
    """
    Write source URL to audio file metadata (legacy entry point).

    Prefer ``enrich_sealed_metadata`` for full Layer-2 policy.
    """
    return enrich_sealed_metadata(file_path, source_url, info=None)


def enrich_sealed_metadata(
    file_path: str,
    source_url: str,
    info: Optional[Mapping[str, Any]] = None,
) -> bool:
    """
    Layer-2 enrichment: Artist, compact comment, date, SOURCE_URL.

    Soft-fail: returns False on total failure; never raises to callers.
    """
    if not os.path.exists(file_path):
        _log_layer2_issue(f"Layer-2 enrich skipped; file not found: {file_path}")
        return False

    try:
        ext = Path(file_path).suffix.lower()
        artist = _artist_from_info(info)
        comment = build_compact_comment(
            (info or {}).get("description") if info else None, source_url
        )
        date = _date_from_info(info)

        if ext == ".mp3":
            return _enrich_mp3(file_path, source_url, artist, comment, date)
        if ext == ".flac":
            return _enrich_flac(file_path, source_url, artist, comment, date)
        if ext in (".mp4", ".m4a", ".m4b"):
            return _enrich_mp4(file_path, source_url, artist, comment, date)
        return _enrich_generic(file_path, source_url, artist, comment, date)
    except Exception as e:
        _log_layer2_issue(f"Layer-2 enrich failed for {file_path}: {e}")
        return False


def _enrich_mp3(
    file_path: str,
    source_url: str,
    artist: str,
    comment: str,
    date: str,
) -> bool:
    try:
        audio_file = MP3(file_path, ID3=ID3)
        if audio_file.tags is None:
            audio_file.add_tags()
        tags = audio_file.tags
        assert tags is not None

        if artist:
            tags.delall("TPE1")
            tags.add(TPE1(encoding=3, text=artist))
        if comment:
            tags.delall("COMM")
            tags.add(COMM(encoding=3, lang="eng", desc="", text=comment))
        if date:
            tags.delall("TDRC")
            tags.add(TDRC(encoding=3, text=date))
        if source_url:
            keep = [
                f for f in tags.getall("TXXX") if getattr(f, "desc", "") != "SOURCE_URL"
            ]
            tags.delall("TXXX")
            for frame in keep:
                tags.add(frame)
            tags.add(TXXX(encoding=3, desc="SOURCE_URL", text=source_url))

        audio_file.save()
        return True
    except Exception as e:
        _log_layer2_issue(f"Layer-2 MP3 enrich failed: {e}")
        return False


def _enrich_flac(
    file_path: str,
    source_url: str,
    artist: str,
    comment: str,
    date: str,
) -> bool:
    try:
        audio_file = FLAC(file_path)
        if artist:
            audio_file["ARTIST"] = [artist]
        if comment:
            audio_file["DESCRIPTION"] = [comment]
            audio_file["COMMENT"] = [comment]
        if date:
            audio_file["DATE"] = [date]
        if source_url:
            audio_file["SOURCE_URL"] = [source_url]
        audio_file.save()
        return True
    except Exception as e:
        _log_layer2_issue(f"Layer-2 FLAC enrich failed: {e}")
        return False


def _enrich_mp4(
    file_path: str,
    source_url: str,
    artist: str,
    comment: str,
    date: str,
) -> bool:
    try:
        audio_file = MP4(file_path)
        if audio_file.tags is None:
            audio_file.add_tags()
        tags = audio_file.tags
        assert tags is not None

        if artist:
            tags["\xa9ART"] = [artist]
        if comment:
            tags["\xa9cmt"] = [comment]
        if date:
            tags["\xa9day"] = [date]
        if source_url:
            tags["----:com.apple.iTunes:SOURCE_URL"] = [
                MP4FreeForm(source_url.encode("utf-8"), dataformat=AtomDataType.UTF8)
            ]
        audio_file.save()
        return True
    except Exception as e:
        _log_layer2_issue(f"Layer-2 MP4 enrich failed: {e}")
        return False


def _enrich_generic(
    file_path: str,
    source_url: str,
    artist: str,
    comment: str,
    date: str,
) -> bool:
    try:
        audio_file = MutagenFile(file_path)
        if audio_file is None:
            _log_layer2_issue(f"Layer-2 could not open: {file_path}")
            return False
        if not hasattr(audio_file, "tags") or audio_file.tags is None:
            try:
                audio_file.add_tags()
            except Exception:
                _log_layer2_issue(f"Layer-2 format has no tags: {file_path}")
                return False

        wrote = False
        tags = audio_file.tags
        for key, value in (
            ("ARTIST", artist),
            ("DESCRIPTION", comment),
            ("COMMENT", comment),
            ("DATE", date),
            ("SOURCE_URL", source_url),
        ):
            if not value:
                continue
            try:
                tags[key] = [value]
                wrote = True
            except Exception:
                continue
        if wrote:
            audio_file.save()
            return True
        # Fall back to SOURCE_URL-only attempts.
        return write_source_url_legacy_generic(file_path, source_url)
    except Exception as e:
        _log_layer2_issue(f"Layer-2 generic enrich failed: {e}")
        return False


def write_source_url_legacy_generic(file_path: str, source_url: str) -> bool:
    """Best-effort SOURCE_URL write for uncommon containers."""
    try:
        audio_file = MutagenFile(file_path)
        if (
            audio_file is None
            or not hasattr(audio_file, "tags")
            or audio_file.tags is None
        ):
            return False
        for tag_name in ("SOURCE_URL", "SOURCE", "URL", "SOURCEURL"):
            try:
                audio_file.tags[tag_name] = [source_url]
                audio_file.save()
                return True
            except (KeyError, AttributeError, TypeError, ValueError):
                continue
        return False
    except Exception:
        return False


def read_source_url_from_metadata(file_path: str) -> Optional[str]:
    """Read source URL from audio file metadata."""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None

    try:
        file_ext = Path(file_path).suffix.lower()
        if file_ext == ".mp3":
            return _read_mp3_metadata(file_path)
        if file_ext == ".flac":
            return _read_flac_metadata(file_path)
        if file_ext in (".mp4", ".m4a", ".m4b"):
            return _read_mp4_metadata(file_path)
        return _read_generic_metadata(file_path)
    except Exception as e:
        logger.warning(f"Failed to read metadata from {file_path}: {e}")
        return None


def _read_mp3_metadata(file_path: str) -> Optional[str]:
    try:
        audio_file = MP3(file_path, ID3=ID3)
        if audio_file.tags is None:
            return None
        for tag in audio_file.tags.values():
            if isinstance(tag, TXXX) and tag.desc == "SOURCE_URL":
                return tag.text[0] if tag.text else None
        return None
    except Exception as e:
        logger.warning(f"Error reading MP3 metadata: {e}")
        return None


def _read_flac_metadata(file_path: str) -> Optional[str]:
    try:
        audio_file = FLAC(file_path)
        if "SOURCE_URL" in audio_file:
            return audio_file["SOURCE_URL"][0]
        return None
    except Exception as e:
        logger.warning(f"Error reading FLAC metadata: {e}")
        return None


def _read_mp4_metadata(file_path: str) -> Optional[str]:
    try:
        audio_file = MP4(file_path)
        if not audio_file.tags:
            return None
        key = "----:com.apple.iTunes:SOURCE_URL"
        if key in audio_file.tags:
            value = audio_file.tags[key][0]
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return str(value)
        return None
    except Exception as e:
        logger.warning(f"Error reading MP4 metadata: {e}")
        return None


def _read_generic_metadata(file_path: str) -> Optional[str]:
    try:
        audio_file = MutagenFile(file_path)
        if audio_file is None or not hasattr(audio_file, "tags") or not audio_file.tags:
            return None
        for tag_name in ("SOURCE_URL", "SOURCE", "URL", "SOURCEURL"):
            if tag_name in audio_file.tags:
                value = audio_file.tags[tag_name]
                if isinstance(value, list) and value:
                    return value[0]
                if value:
                    return str(value)
        return None
    except Exception as e:
        logger.warning(f"Error reading generic metadata: {e}")
        return None
