"""
Batch URL extraction from text, CSV, and raw value lists.

Pure functions for easy testing. Used by batch command for TXT/CSV files and paste input.
"""

import csv
import io
from typing import Iterable, List, Union


# Comment line prefixes (yt-dlp batch-file convention)
COMMENT_PREFIXES = ("#", ";", "]")


def filter_url_candidates(values: Iterable[str]) -> List[str]:
    """
    Keep only strings that start with http:// or https:// (after strip).
    Preserves order. Does not dedupe.
    """
    result: List[str] = []
    for v in values:
        if not isinstance(v, str):
            continue
        s = v.strip()
        if s.startswith("http://") or s.startswith("https://"):
            result.append(s)
    return result


def _is_comment_line(line: str) -> bool:
    """True if line is blank or starts with a comment prefix."""
    s = line.strip()
    if not s:
        return True
    return s.startswith(COMMENT_PREFIXES)


def extract_urls_from_text(text: str) -> List[str]:
    """
    Extract URLs from plain text: newline-separated, optional comma-separated on a line.
    Ignores blank lines and comment lines (# ; ]). Keeps only http(s):// values.
    Preserves order.
    """
    if not text or not isinstance(text, str):
        return []
    urls: List[str] = []
    for line in text.splitlines():
        if _is_comment_line(line):
            continue
        # Split on comma for convenience, then filter
        for part in line.split(","):
            s = part.strip()
            if s.startswith("http://") or s.startswith("https://"):
                urls.append(s)
    return urls


def extract_urls_from_csv(bytes_or_text: Union[bytes, str]) -> List[str]:
    """
    Read CSV (all cells), collect any cell value that after strip starts with http(s)://.
    Uses Python stdlib csv. Preserves order of first occurrence.
    """
    if bytes_or_text is None:
        return []
    if isinstance(bytes_or_text, bytes):
        text = bytes_or_text.decode("utf-8", errors="replace")
    else:
        text = bytes_or_text
    if not text.strip():
        return []
    reader = csv.reader(io.StringIO(text))
    candidates: List[str] = []
    for row in reader:
        for cell in row:
            if isinstance(cell, str):
                candidates.append(cell.strip())
            else:
                candidates.append(str(cell).strip())
    return filter_url_candidates(candidates)
