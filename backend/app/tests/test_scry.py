"""
Tests for scry / inspect media inspection.

Seams:
- ``summarize_probe`` / ``build_health`` / formatters (no ffprobe binary required)
- ``list_media_under`` / ``discover_companions`` (temp dirs)
- ``run_ffprobe`` failure modes (mocked subprocess / missing binary)
- CLI ``dispatch_from_argv`` with mocked ``scry_file``
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from app.utils.scry import (
    build_health,
    discover_companions,
    format_bitrate,
    format_bytes,
    format_duration,
    list_media_under,
    run_ffprobe,
    ScryError,
    ScryReport,
    summarize_probe,
)


def _sample_probe(**tag_overrides: str) -> dict:
    tags = {
        "ARTIST": "Kurzgesagt – In a Nutshell",
        "DATE": "2026-08-04",
        "SOURCE_URL": "https://youtu.be/Cyl3X88KEgg",
        "comment": "Body text\n\nSource: https://youtu.be/Cyl3X88KEgg",
        "DESCRIPTION": "Body text\n\nSource: https://youtu.be/Cyl3X88KEgg",
    }
    tags.update(tag_overrides)
    return {
        "format": {
            "filename": "demo.flac",
            "format_name": "flac",
            "duration": "847.76",
            "bit_rate": "306000",
            "tags": tags,
        },
        "streams": [
            {
                "codec_type": "audio",
                "codec_name": "flac",
                "sample_rate": "16000",
                "channels": 1,
                "bit_rate": "306000",
            },
            {
                "codec_type": "video",
                "codec_name": "mjpeg",
                "disposition": {"attached_pic": 1},
            },
        ],
        "chapters": [
            {
                "id": 0,
                "start_time": "0.000000",
                "end_time": "92.000000",
                "tags": {"title": "Intro"},
            }
        ],
    }


def test_summarize_probe_maps_core_fields_and_source_url(tmp_path: Path) -> None:
    """Opinionated report surfaces artist, duration, codec, source URL, and cover art."""
    media = tmp_path / "Why Humanity.flac"
    media.write_bytes(b"flac")
    report = summarize_probe(_sample_probe(), media)
    assert report.artist == "Kurzgesagt – In a Nutshell"
    assert report.source_url == "https://youtu.be/Cyl3X88KEgg"
    assert report.date == "2026-08-04"
    assert report.codec == "FLAC"
    assert report.duration_human == "14m 08s"
    assert report.bitrate_human == "306 kb/s"
    assert report.has_cover_art is True
    assert report.description_present is True
    assert len(report.chapters) == 1
    assert report.chapters[0]["title"] == "Intro"


def test_metadata_health_marks_present_and_missing_fields(tmp_path: Path) -> None:
    """Metadata Health is derived from the summary, not raw ffprobe alone."""
    media = tmp_path / "bare.flac"
    media.write_bytes(b"x")
    rich = summarize_probe(_sample_probe(), media)
    by_label = {c.label: c.ok for c in rich.health}
    assert by_label["Artist"] is True
    assert by_label["Source URL"] is True
    assert by_label["Cover Art"] is True
    assert by_label["Chapters"] is True

    bare = summarize_probe(
        {
            "format": {"duration": "1", "tags": {}},
            "streams": [{"codec_type": "audio", "codec_name": "flac"}],
            "chapters": [],
        },
        media,
    )
    bare_health = {c.label: c.ok for c in bare.health}
    assert bare_health["Artist"] is False
    assert bare_health["Source URL"] is False
    assert bare_health["Cover Art"] is False


def test_list_media_under_sorts_newest_first(tmp_path: Path) -> None:
    """Interactive picker candidates are newest-first under the output dir."""
    older = tmp_path / "old.flac"
    newer = tmp_path / "new.mp3"
    older.write_bytes(b"a")
    newer.write_bytes(b"b")
    import os
    import time

    older_mtime = time.time() - 100
    newer_mtime = time.time()
    os.utime(older, (older_mtime, older_mtime))
    os.utime(newer, (newer_mtime, newer_mtime))
    listed = list_media_under(tmp_path)
    assert [p.name for p in listed] == ["new.mp3", "old.flac"]


def test_discover_companions_finds_info_md_beside_seal(tmp_path: Path) -> None:
    """Companion .info.md next to the seal is reported for the unified scry view."""
    media = tmp_path / "title.flac"
    companion = tmp_path / "title.info.md"
    media.write_bytes(b"x")
    companion.write_text("# title\n", encoding="utf-8")
    found = discover_companions(media)
    assert found["companion_info"] == str(companion)
    assert found["ytdlp_info_json"] is None


def test_run_ffprobe_raises_when_binary_missing(tmp_path: Path) -> None:
    """Missing ffprobe becomes a ScryError suitable for a CLI fracture."""
    media = tmp_path / "a.flac"
    media.write_bytes(b"x")
    with patch("app.utils.scry.find_ffprobe_binary", return_value=None):
        with pytest.raises(ScryError, match="ffprobe not found"):
            run_ffprobe(media)


def test_run_ffprobe_parses_json_from_subprocess(tmp_path: Path) -> None:
    """Successful ffprobe stdout JSON is returned as a dict."""
    media = tmp_path / "a.flac"
    media.write_bytes(b"x")
    payload = {"format": {"duration": "1.0"}, "streams": [], "chapters": []}
    completed = MagicMock(returncode=0, stdout=json.dumps(payload), stderr="")
    with (
        patch(
            "app.utils.scry.find_ffprobe_binary", return_value=Path("/usr/bin/ffprobe")
        ),
        patch("app.utils.scry.subprocess.run", return_value=completed) as run,
    ):
        data = run_ffprobe(media)
    assert data["format"]["duration"] == "1.0"
    assert run.called


def test_formatters_are_human_readable() -> None:
    """Duration, size, and bitrate formatters stay stable for the Rich report."""
    assert format_duration(847.76) == "14m 08s"
    assert format_duration(3661) == "1h 01m 01s"
    assert "MB" in format_bytes(2_000_000) or "KB" in format_bytes(2_000_000)
    assert format_bitrate(306000) == "306 kb/s"


def test_dispatch_from_argv_json_prints_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``scry --json FILE`` emits structured JSON without requiring a real probe."""
    media = tmp_path / "demo.flac"
    media.write_bytes(b"x")
    report = summarize_probe(_sample_probe(), media)
    with patch(
        "app.cli.commands.scry.scry_file", return_value=(report, {"format": {}})
    ):
        from app.cli.commands.scry import dispatch_from_argv

        dispatch_from_argv([str(media), "--json", "--plain"], command="scry")
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["source_url"] == "https://youtu.be/Cyl3X88KEgg"
    assert data["artist"] == "Kurzgesagt – In a Nutshell"


def test_dispatch_from_argv_missing_file_exits(
    tmp_path: Path,
) -> None:
    """Missing path fractures instead of dumping a traceback."""
    from app.cli.commands.scry import dispatch_from_argv

    with pytest.raises(typer.Exit) as exc:
        dispatch_from_argv([str(tmp_path / "nope.flac"), "--plain"], command="inspect")
    assert exc.value.exit_code == 1


def test_build_health_on_empty_report() -> None:
    """Health builder tolerates an empty report skeleton."""
    report = ScryReport(
        path="/x",
        filename="x.flac",
        size_bytes=0,
        size_human="0 B",
    )
    checks = build_health(report)
    assert all(c.ok is False for c in checks if c.label != "Chapters")
