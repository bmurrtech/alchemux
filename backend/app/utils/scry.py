"""Scry: inspect sealed media via ffprobe (+ companion presence).

Public seam for the ``scry`` / ``inspect`` CLI. Opinionated summary by default;
raw ffprobe JSON available for automation.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Union

from app.utils.file_utils import find_ffprobe_binary
from app.utils.metadata import read_source_url_from_metadata

PathLike = Union[str, Path]

# Extensions Alchemux commonly seals / users may inspect.
MEDIA_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".flac",
        ".mp3",
        ".m4a",
        ".m4b",
        ".aac",
        ".opus",
        ".ogg",
        ".wav",
        ".mp4",
        ".mkv",
        ".webm",
        ".mov",
        ".avi",
    }
)


@dataclass
class HealthCheck:
    """One Metadata Health row."""

    label: str
    ok: bool
    detail: str = ""


@dataclass
class ScryReport:
    """Opinionated media inspection summary."""

    path: str
    filename: str
    size_bytes: int
    size_human: str
    duration_seconds: Optional[float] = None
    duration_human: str = ""
    format_name: str = ""
    codec: str = ""
    bitrate_human: str = ""
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    title: str = ""
    artist: str = ""
    album: str = ""
    date: str = ""
    description: str = ""
    description_present: bool = False
    comment: str = ""
    source_url: str = ""
    chapters: list[dict[str, Any]] = field(default_factory=list)
    has_cover_art: bool = False
    tags: dict[str, str] = field(default_factory=dict)
    companion_info: Optional[str] = None
    ytdlp_info_json: Optional[str] = None
    health: list[HealthCheck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


class ScryError(Exception):
    """ffprobe or path failure suitable for a CLI fracture."""


def format_bytes(n: int) -> str:
    """Human-readable file size."""
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{n} B"


def format_duration(seconds: Optional[float]) -> str:
    """Format duration as ``14m 07s`` or ``1h 02m 03s``."""
    if seconds is None:
        return ""
    try:
        total = int(round(float(seconds)))
    except (TypeError, ValueError):
        return ""
    if total < 0:
        return ""
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes}m {secs:02d}s"


def format_bitrate(bits_per_sec: Any) -> str:
    try:
        bps = int(float(bits_per_sec))
    except (TypeError, ValueError):
        return ""
    if bps <= 0:
        return ""
    kbps = bps / 1000.0
    if kbps >= 1000:
        return f"{kbps / 1000.0:.2f} Mb/s"
    return f"{kbps:.0f} kb/s"


def _tag_map(raw: Mapping[str, Any] | None) -> dict[str, str]:
    if not raw:
        return {}
    out: dict[str, str] = {}
    for key, value in raw.items():
        if value is None:
            continue
        text = str(value).strip()
        if text:
            out[str(key)] = text
    return out


def _tag_get(tags: Mapping[str, str], *names: str) -> str:
    lower = {k.lower(): v for k, v in tags.items()}
    for name in names:
        hit = lower.get(name.lower())
        if hit:
            return hit
    return ""


def run_ffprobe(file_path: PathLike) -> dict[str, Any]:
    """
    Invoke ffprobe ``-print_format json`` for format + streams + chapters.

    Raises:
        ScryError: ffprobe missing, file missing, or non-zero exit.
    """
    path = Path(file_path)
    if not path.is_file():
        raise ScryError(f"file not found: {path}")

    probe_bin = find_ffprobe_binary()
    if probe_bin is None:
        raise ScryError("ffprobe not found on PATH — see docs/install.md")

    cmd = [
        str(probe_bin),
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        "-show_chapters",
        str(path),
    ]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except OSError as e:
        raise ScryError(f"ffprobe failed to start: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise ScryError("ffprobe timed out") from e

    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "").strip()
        raise ScryError(err or f"ffprobe exited {completed.returncode}")

    try:
        data = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as e:
        raise ScryError(f"ffprobe returned invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ScryError("ffprobe JSON root was not an object")
    return data


def _pick_primary_stream(
    streams: Sequence[Mapping[str, Any]], prefer: str
) -> Optional[Mapping[str, Any]]:
    for stream in streams:
        if stream.get("codec_type") == prefer:
            return stream
    return streams[0] if streams else None


def _has_cover_art(streams: Sequence[Mapping[str, Any]]) -> bool:
    for stream in streams:
        if stream.get("codec_type") != "video":
            continue
        disposition = stream.get("disposition") or {}
        if disposition.get("attached_pic") in (1, True, "1"):
            return True
        # Some containers mark cover as mjpeg / png still without disposition.
        codec = str(stream.get("codec_name") or "").lower()
        if codec in ("mjpeg", "png", "bmp", "gif") and stream.get("nb_frames") in (
            "1",
            1,
        ):
            return True
    return False


def discover_companions(media_path: PathLike) -> dict[str, Optional[str]]:
    """Return paths to companion / yt-dlp sidecars when present beside the seal."""
    path = Path(media_path)
    stem = path.with_suffix("")
    parent = path.parent
    info_md = stem.with_suffix(".info.md")
    info_txt = stem.with_suffix(".info.txt")
    # Title-folder layout sometimes places companions as sibling with same stem name.
    alt_md = parent / f"{path.stem}.info.md"
    alt_txt = parent / f"{path.stem}.info.txt"
    info_json = stem.with_suffix(".info.json")
    alt_json = parent / f"{path.stem}.info.json"

    companion: Optional[str] = None
    for candidate in (info_md, alt_md, info_txt, alt_txt):
        if candidate.is_file():
            companion = str(candidate)
            break

    ytdlp: Optional[str] = None
    for candidate in (info_json, alt_json):
        if candidate.is_file():
            ytdlp = str(candidate)
            break

    return {"companion_info": companion, "ytdlp_info_json": ytdlp}


def build_health(report: ScryReport) -> list[HealthCheck]:
    """Alchemux Metadata Health — opinionated presence checks."""
    checks = [
        HealthCheck("Title", bool(report.title), report.title or "missing"),
        HealthCheck("Artist", bool(report.artist), report.artist or "missing"),
        HealthCheck(
            "Cover Art",
            report.has_cover_art,
            "present" if report.has_cover_art else "missing",
        ),
        HealthCheck(
            "Source URL",
            bool(report.source_url),
            report.source_url or "missing",
        ),
        HealthCheck(
            "Description",
            report.description_present,
            "present" if report.description_present else "missing",
        ),
        HealthCheck(
            "Chapters",
            bool(report.chapters),
            f"{len(report.chapters)} chapter(s)" if report.chapters else "none",
        ),
        HealthCheck("Publish Date", bool(report.date), report.date or "missing"),
    ]
    return checks


def summarize_probe(
    probe: Mapping[str, Any],
    file_path: PathLike,
    *,
    source_url_override: Optional[str] = None,
) -> ScryReport:
    """Build an opinionated report from ffprobe JSON + filesystem."""
    path = Path(file_path)
    fmt = probe.get("format") if isinstance(probe.get("format"), dict) else {}
    streams = probe.get("streams") if isinstance(probe.get("streams"), list) else []
    chapters_raw = (
        probe.get("chapters") if isinstance(probe.get("chapters"), list) else []
    )

    tags = _tag_map(fmt.get("tags") if isinstance(fmt, dict) else None)
    # Merge stream tags (some containers put metadata on streams).
    for stream in streams:
        if isinstance(stream, dict):
            tags = {**_tag_map(stream.get("tags")), **tags}

    audio = _pick_primary_stream([s for s in streams if isinstance(s, dict)], "audio")
    video = _pick_primary_stream(
        [
            s
            for s in streams
            if isinstance(s, dict)
            and s.get("codec_type") == "video"
            and not (s.get("disposition") or {}).get("attached_pic")
        ],
        "video",
    )

    duration_raw = fmt.get("duration") if isinstance(fmt, dict) else None
    try:
        duration_seconds = float(duration_raw) if duration_raw is not None else None
    except (TypeError, ValueError):
        duration_seconds = None

    bitrate = ""
    if isinstance(fmt, dict) and fmt.get("bit_rate"):
        bitrate = format_bitrate(fmt.get("bit_rate"))
    elif audio and audio.get("bit_rate"):
        bitrate = format_bitrate(audio.get("bit_rate"))

    codec = ""
    if audio and audio.get("codec_name"):
        codec = str(audio.get("codec_name")).upper()
    elif video and video.get("codec_name"):
        codec = str(video.get("codec_name")).upper()

    sample_rate = None
    channels = None
    if audio:
        try:
            sample_rate = (
                int(audio.get("sample_rate")) if audio.get("sample_rate") else None
            )
        except (TypeError, ValueError):
            sample_rate = None
        try:
            channels = int(audio.get("channels")) if audio.get("channels") else None
        except (TypeError, ValueError):
            channels = None

    width = height = None
    if video:
        try:
            width = int(video.get("width")) if video.get("width") else None
            height = int(video.get("height")) if video.get("height") else None
        except (TypeError, ValueError):
            width = height = None

    title = _tag_get(tags, "title", "TITLE")
    if not title:
        title = path.stem
    artist = _tag_get(tags, "artist", "ARTIST", "album_artist", "ALBUMARTIST")
    album = _tag_get(tags, "album", "ALBUM")
    date = _tag_get(tags, "date", "DATE", "creation_time")
    description = _tag_get(tags, "description", "DESCRIPTION", "synopsis", "SYNOPSIS")
    comment = _tag_get(tags, "comment", "COMMENT")
    description_present = bool(description or comment)

    source_url = (
        source_url_override
        or _tag_get(tags, "SOURCE_URL", "source_url", "source")
        or (read_source_url_from_metadata(str(path)) or "")
    )

    chapters: list[dict[str, Any]] = []
    for ch in chapters_raw:
        if not isinstance(ch, dict):
            continue
        ch_tags = _tag_map(ch.get("tags") if isinstance(ch.get("tags"), dict) else None)
        chapters.append(
            {
                "id": ch.get("id"),
                "start": ch.get("start_time"),
                "end": ch.get("end_time"),
                "title": ch_tags.get("title") or ch_tags.get("TITLE") or "",
            }
        )

    size_bytes = path.stat().st_size if path.is_file() else 0
    companions = discover_companions(path)

    report = ScryReport(
        path=str(path.resolve()) if path.exists() else str(path),
        filename=path.name,
        size_bytes=size_bytes,
        size_human=format_bytes(size_bytes),
        duration_seconds=duration_seconds,
        duration_human=format_duration(duration_seconds),
        format_name=str((fmt or {}).get("format_name") or path.suffix.lstrip(".")),
        codec=codec,
        bitrate_human=bitrate,
        sample_rate=sample_rate,
        channels=channels,
        width=width,
        height=height,
        title=title,
        artist=artist,
        album=album,
        date=date,
        description=description or comment,
        description_present=description_present,
        comment=comment,
        source_url=source_url,
        chapters=chapters,
        has_cover_art=_has_cover_art([s for s in streams if isinstance(s, dict)]),
        tags=tags,
        companion_info=companions.get("companion_info"),
        ytdlp_info_json=companions.get("ytdlp_info_json"),
    )
    report.health = build_health(report)
    return report


def scry_file(file_path: PathLike) -> tuple[ScryReport, dict[str, Any]]:
    """Run ffprobe and return (report, raw probe dict)."""
    path = Path(file_path)
    probe = run_ffprobe(path)
    return summarize_probe(probe, path), probe


def list_media_under(root: PathLike, *, limit: int = 200) -> list[Path]:
    """
    Enumerate supported media under ``root``, newest mtime first.

    Caps at ``limit`` for interactive pickers.
    """
    base = Path(root).expanduser()
    if not base.is_dir():
        return []
    found: list[tuple[float, Path]] = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        found.append((mtime, path))
    found.sort(key=lambda item: item[0], reverse=True)
    return [p for _, p in found[:limit]]
