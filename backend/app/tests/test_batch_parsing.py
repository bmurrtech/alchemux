"""
Tests for batch URL parsing (TXT/CSV and filter_url_candidates).

Public-safe: pure functions only; no network or config.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.cli.batch_parsing import (  # noqa: E402
    filter_url_candidates,
    extract_urls_from_text,
    extract_urls_from_csv,
)


def test_filter_url_candidates_empty() -> None:
    assert filter_url_candidates([]) == []
    assert filter_url_candidates(iter([])) == []


def test_filter_url_candidates_keeps_http_https() -> None:
    assert filter_url_candidates(["https://a.co", "http://b.com"]) == [
        "https://a.co",
        "http://b.com",
    ]
    assert filter_url_candidates(["  https://x.y  "]) == ["https://x.y"]


def test_filter_url_candidates_ignores_non_urls() -> None:
    assert filter_url_candidates(["not a url", "ftp://x.y", ""]) == []
    assert filter_url_candidates(["https://ok.com", "nope", "http://yes.com"]) == [
        "https://ok.com",
        "http://yes.com",
    ]


def test_extract_urls_from_text_empty() -> None:
    assert extract_urls_from_text("") == []
    assert extract_urls_from_text("   \n\n  ") == []
    assert extract_urls_from_text(None) == []  # type: ignore


def test_extract_urls_from_text_newlines() -> None:
    text = "https://a.com\nhttps://b.com\n"
    assert extract_urls_from_text(text) == ["https://a.com", "https://b.com"]


def test_extract_urls_from_text_comma_separated() -> None:
    text = "https://a.com, https://b.com"
    assert extract_urls_from_text(text) == ["https://a.com", "https://b.com"]


def test_extract_urls_from_text_comment_lines() -> None:
    text = "# comment\nhttps://a.com\n; another\nhttps://b.com\n] also\n"
    assert extract_urls_from_text(text) == ["https://a.com", "https://b.com"]


def test_extract_urls_from_text_blank_lines_ignored() -> None:
    text = "https://a.com\n\n\nhttps://b.com\n"
    assert extract_urls_from_text(text) == ["https://a.com", "https://b.com"]


def test_extract_urls_from_text_invalid_tokens_ignored() -> None:
    text = "https://ok.com\nnot a link\nhttps://yes.com\n"
    assert extract_urls_from_text(text) == ["https://ok.com", "https://yes.com"]


def test_extract_urls_from_csv_empty() -> None:
    assert extract_urls_from_csv("") == []
    assert extract_urls_from_csv(b"") == []
    assert extract_urls_from_csv(None) == []  # type: ignore


def test_extract_urls_from_csv_single_cell() -> None:
    assert extract_urls_from_csv("https://a.com") == ["https://a.com"]


def test_extract_urls_from_csv_multiple_cells() -> None:
    csv_text = "a,https://b.com,c\nhttps://d.com,e,f"
    assert extract_urls_from_csv(csv_text) == ["https://b.com", "https://d.com"]


def test_extract_urls_from_csv_bytes_utf8() -> None:
    assert extract_urls_from_csv(b"https://x.com") == ["https://x.com"]
