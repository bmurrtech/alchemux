"""Detect installed browsers for yt-dlp cookies-from-browser opt-in.

Uses pathlib probes of known profile roots only — no new dependencies and no
cookie decryption. Advanced browser:path overrides stay in TOML/env.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

# yt-dlp SUPPORTED_BROWSERS subset we probe for. Order is the fallback priority
# when no OS-specific default is present among detected names.
BROWSER_PRIORITY: tuple[str, ...] = (
    "chrome",
    "firefox",
    "brave",
    "edge",
    "safari",
    "chromium",
    "opera",
    "vivaldi",
    "whale",
)


def _home() -> Path:
    return Path.home()


def _profile_roots_for_platform() -> dict[str, tuple[Path, ...]]:
    """Return candidate profile roots keyed by yt-dlp browser name."""
    home = _home()
    platform = sys.platform

    if platform == "darwin":
        app_support = home / "Library" / "Application Support"
        return {
            "chrome": (app_support / "Google" / "Chrome",),
            "chromium": (app_support / "Chromium",),
            "brave": (app_support / "BraveSoftware" / "Brave-Browser",),
            "edge": (app_support / "Microsoft Edge",),
            "firefox": (app_support / "Firefox",),
            "opera": (app_support / "com.operasoftware.Opera",),
            "vivaldi": (app_support / "Vivaldi",),
            "whale": (app_support / "Naver" / "Whale",),
            "safari": (
                home / "Library" / "Cookies",
                home
                / "Library"
                / "Containers"
                / "com.apple.Safari"
                / "Data"
                / "Library"
                / "Cookies",
            ),
        }

    if platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        roaming = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        return {
            "chrome": (local / "Google" / "Chrome" / "User Data",),
            "chromium": (local / "Chromium" / "User Data",),
            "brave": (local / "BraveSoftware" / "Brave-Browser" / "User Data",),
            "edge": (local / "Microsoft" / "Edge" / "User Data",),
            "firefox": (roaming / "Mozilla" / "Firefox",),
            "opera": (roaming / "Opera Software" / "Opera Stable",),
            "vivaldi": (local / "Vivaldi" / "User Data",),
            "whale": (local / "Naver" / "Naver Whale" / "User Data",),
        }

    # Linux and other Unix-like
    config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    return {
        "chrome": (config / "google-chrome",),
        "chromium": (config / "chromium",),
        "brave": (config / "BraveSoftware" / "Brave-Browser",),
        "edge": (config / "microsoft-edge",),
        "firefox": (home / ".mozilla" / "firefox",),
        "opera": (config / "opera",),
        "vivaldi": (config / "vivaldi",),
        "whale": (config / "naver-whale",),
    }


def _os_preferred_browsers() -> tuple[str, ...]:
    # OS defaults only (PRD 012 FR-3). When none of these are detected,
    # pick_cookie_browser falls through to BROWSER_PRIORITY.
    if sys.platform == "darwin":
        return ("safari", "chrome")
    if sys.platform == "win32":
        return ("edge", "chrome")
    return ("firefox", "chrome")


def detect_cookie_browsers(
    *,
    roots: Optional[dict[str, Sequence[Path]]] = None,
) -> list[str]:
    """Return yt-dlp browser names whose profile roots exist on disk."""
    table = roots if roots is not None else _profile_roots_for_platform()
    found: list[str] = []
    for name in BROWSER_PRIORITY:
        candidates = table.get(name, ())
        if any(Path(path).exists() for path in candidates):
            found.append(name)
    return found


def pick_cookie_browser(
    detected: Iterable[str],
    *,
    preferred: Optional[Sequence[str]] = None,
) -> Optional[str]:
    """Auto-pick one browser name from a detected set.

    Prefers OS defaults when present, otherwise the first name in
    ``BROWSER_PRIORITY`` that appears in ``detected``.
    """
    names = [n for n in detected if n]
    if not names:
        return None
    if len(names) == 1:
        return names[0]

    name_set = set(names)
    for candidate in preferred or _os_preferred_browsers():
        if candidate in name_set:
            return candidate
    for candidate in BROWSER_PRIORITY:
        if candidate in name_set:
            return candidate
    return names[0]
