"""Companion info file writer (ADR 0008 / PRD 012 FR-9).

Human-readable ``<stem>.info.md`` / ``.info.txt`` beside sealed media.
Built from in-memory extract info + distill URL — no extra network.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Union

from app.core.logger import normalize_log_level, setup_logger
from app.utils.metadata import sanitize_description_text

logger = setup_logger(__name__)

PathLike = Union[str, Path]


def _log_info_file_issue(message: str) -> None:
    """Surface companion-file issues only at verbose/debug (like Layer-2)."""
    level = normalize_log_level(os.getenv("LOG_LEVEL", "warning"))
    if level in ("verbose", "debug"):
        logger.warning(message)
    else:
        logger.debug(message)


def _alchemux_version() -> str:
    try:
        from importlib.metadata import version

        return version("alchemux")
    except Exception:
        return "0.0.0+dev"


def resolve_info_file_format(raw: Optional[str]) -> str:
    """Return ``md`` or ``txt``; invalid/empty values fall back to ``md``."""
    if not raw:
        return "md"
    value = str(raw).strip().lower()
    if value in ("md", "txt"):
        return value
    _log_info_file_issue(
        f"Invalid download.info_file_format={raw!r}; falling back to md"
    )
    return "md"


def _artist_from_info(info: Optional[Mapping[str, Any]]) -> str:
    if not info:
        return ""
    for key in ("channel", "uploader", "artist", "creator"):
        value = info.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _title_from_info(info: Optional[Mapping[str, Any]]) -> str:
    if not info:
        return ""
    value = info.get("title")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return ""


def _date_from_info(info: Optional[Mapping[str, Any]]) -> str:
    if not info:
        return ""
    raw = info.get("upload_date")
    if not isinstance(raw, str) or not raw.strip():
        return ""
    digits = raw.strip()
    if len(digits) == 8 and digits.isdigit():
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return digits


def format_duration(seconds: Any) -> str:
    """Format duration seconds as HH:MM:SS, or MM:SS when under one hour."""
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return ""
    if total < 0:
        return ""
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_chapter_lines(chapters: Any) -> list[str]:
    """One ``HH:MM:SS — title`` line per chapter with title + parseable start_time."""
    if not isinstance(chapters, list):
        return []
    lines: list[str] = []
    for chapter in chapters:
        if not isinstance(chapter, Mapping):
            continue
        title = chapter.get("title")
        if not isinstance(title, str) or not title.strip():
            continue
        if "start_time" not in chapter:
            continue
        stamp = format_duration(chapter.get("start_time"))
        if not stamp:
            continue
        # Prefer HH:MM:SS for chapter lists (zero-pad hours) for stable grepping.
        if stamp.count(":") == 1:
            stamp = f"00:{stamp}"
        lines.append(f"{stamp} — {title.strip()}")
    return lines


def _downloaded_stamp(when: Optional[datetime] = None) -> str:
    dt = when or datetime.now().astimezone()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone()
    return dt.isoformat(timespec="seconds")


def _render_markdown(fields: Mapping[str, str], chapter_lines: list[str]) -> str:
    parts: list[str] = []
    order = (
        ("Title", "title"),
        ("Creator / Channel", "creator"),
        ("Published", "published"),
        ("Source URL", "source"),
        ("Duration", "duration"),
        ("Downloaded", "downloaded"),
    )
    for heading, key in order:
        value = fields.get(key, "")
        if not value:
            continue
        parts.append(f"## {heading}\n\n{value}\n")

    description = fields.get("description", "")
    if description:
        parts.append(f"## Description\n\n{description}\n")

    if chapter_lines:
        body = "\n".join(f"- {line}" for line in chapter_lines)
        parts.append(f"## Chapters\n\n{body}\n")

    footer = fields.get("footer", "")
    if footer:
        parts.append(f"---\n\n{footer}\n")
    return "\n".join(parts).rstrip() + "\n"


def _render_txt(fields: Mapping[str, str], chapter_lines: list[str]) -> str:
    lines: list[str] = []
    labels = (
        ("Title", "title"),
        ("Creator / Channel", "creator"),
        ("Published", "published"),
        ("Source URL", "source"),
        ("Duration", "duration"),
        ("Downloaded", "downloaded"),
    )
    for label, key in labels:
        value = fields.get(key, "")
        if value:
            lines.append(f"{label}: {value}")

    description = fields.get("description", "")
    if description:
        lines.append("")
        lines.append("Description:")
        lines.append(description)

    if chapter_lines:
        lines.append("")
        lines.append("Chapters:")
        lines.extend(chapter_lines)

    footer = fields.get("footer", "")
    if footer:
        lines.append("")
        lines.append(footer)
    return "\n".join(lines).rstrip() + "\n"


def write_companion_info_file(
    media_path: PathLike,
    source_url: str,
    info: Optional[Mapping[str, Any]] = None,
    *,
    fmt: str = "md",
    downloaded_at: Optional[datetime] = None,
) -> Optional[Path]:
    """
    Write ``<stem>.info.md`` or ``.info.txt`` beside the sealed media file.

    Soft-fail: returns None on failure; never raises to callers.
    """
    try:
        media = Path(media_path)
        if not media.exists():
            _log_info_file_issue(f"Companion info skipped; media missing: {media}")
            return None

        resolved = resolve_info_file_format(fmt)
        out_path = media.with_name(f"{media.stem}.info.{resolved}")

        title = _title_from_info(info)
        creator = _artist_from_info(info)
        published = _date_from_info(info)
        duration = ""
        if info and info.get("duration") is not None:
            duration = format_duration(info.get("duration"))
        description = ""
        if info:
            raw_desc = info.get("description")
            if isinstance(raw_desc, str) and raw_desc.strip():
                description = sanitize_description_text(raw_desc)
        chapter_lines = format_chapter_lines((info or {}).get("chapters"))
        fields = {
            "title": title,
            "creator": creator,
            "published": published,
            "source": (source_url or "").strip(),
            "duration": duration,
            "downloaded": _downloaded_stamp(downloaded_at),
            "description": description,
            "footer": f"Downloaded with Alchemux v{_alchemux_version()}",
        }

        if resolved == "txt":
            body = _render_txt(fields, chapter_lines)
        else:
            body = _render_markdown(fields, chapter_lines)

        out_path.write_text(body, encoding="utf-8")
        return out_path
    except Exception as e:
        _log_info_file_issue(f"Companion info write failed for {media_path}: {e}")
        return None


def maybe_write_companion_info_file(
    config: Any,
    media_path: PathLike,
    source_url: str,
    info: Optional[Mapping[str, Any]] = None,
) -> Optional[Path]:
    """
    Honor ``download.info_file`` / ``info_file_format`` then write, or skip.

    Soft-fail: returns None when disabled or on write failure.
    """
    if not config.get_bool("download.info_file", default=True):
        return None
    fmt = resolve_info_file_format(config.get("download.info_file_format") or "md")
    return write_companion_info_file(media_path, source_url, info=info, fmt=fmt)
