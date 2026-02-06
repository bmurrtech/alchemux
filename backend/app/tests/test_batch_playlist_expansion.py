"""
Tests for batch playlist expansion (_expand_playlist_urls).

Public-safe: mock yt_dlp; no network.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.cli.commands.batch import _expand_playlist_urls  # noqa: E402


def _mock_ytdl_with_info(info: dict):
    """Context manager that mocks yt_dlp so extract_info returns info."""
    mock_ydl_ctx = MagicMock()
    mock_ydl_ctx.extract_info.return_value = info
    mock_ydl_ctx.__enter__ = MagicMock(return_value=mock_ydl_ctx)
    mock_ydl_ctx.__exit__ = MagicMock(return_value=False)
    mock_ytdl = MagicMock()
    mock_ytdl.YoutubeDL.return_value = mock_ydl_ctx
    return patch.dict("sys.modules", {"yt_dlp": mock_ytdl})


def test_expand_playlist_urls_extracts_entry_urls() -> None:
    """When yt-dlp returns entries with webpage_url, they are extracted."""
    fake_entries = [
        {"webpage_url": "https://youtube.com/watch?v=a", "id": "a"},
        {"webpage_url": "https://youtube.com/watch?v=b", "id": "b"},
    ]
    with _mock_ytdl_with_info({"entries": fake_entries}):
        result = _expand_playlist_urls("https://youtube.com/playlist?list=1")
    assert result == ["https://youtube.com/watch?v=a", "https://youtube.com/watch?v=b"]


def test_expand_playlist_urls_fallback_to_url() -> None:
    """Entries with url but no webpage_url still yield url."""
    fake_entries = [{"url": "https://youtube.com/watch?v=x"}]
    with _mock_ytdl_with_info({"entries": fake_entries}):
        result = _expand_playlist_urls("https://youtube.com/playlist?list=1")
    assert result == ["https://youtube.com/watch?v=x"]


def test_expand_playlist_urls_returns_empty_on_failure() -> None:
    """When extract_info raises, returns []."""
    mock_ydl_ctx = MagicMock()
    mock_ydl_ctx.extract_info.side_effect = Exception("network error")
    mock_ydl_ctx.__enter__ = MagicMock(return_value=mock_ydl_ctx)
    mock_ydl_ctx.__exit__ = MagicMock(return_value=False)
    mock_ytdl = MagicMock()
    mock_ytdl.YoutubeDL.return_value = mock_ydl_ctx
    with patch.dict("sys.modules", {"yt_dlp": mock_ytdl}):
        result = _expand_playlist_urls("https://invalid.example/playlist")
    assert result == []


def test_expand_playlist_urls_empty_entries() -> None:
    """When info has no entries, returns []."""
    with _mock_ytdl_with_info({}):
        result = _expand_playlist_urls("https://youtube.com/playlist?list=1")
    assert result == []
