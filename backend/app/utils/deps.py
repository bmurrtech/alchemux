"""
Lightweight system dependency checks (ffmpeg/ffprobe).

Detect-only: never installs packages or shells out to package managers.
Used by setup (orchestrator loop) and doctor / runtime hints.
"""

from __future__ import annotations

import shutil
import sys
import webbrowser
from dataclasses import dataclass
from typing import Optional, Tuple

from app.utils.file_utils import find_ffmpeg_binary, find_ffprobe_binary

# Canonical install guide (GitHub; not a product marketing site)
INSTALL_FFMPEG_URL = (
    "https://github.com/bmurrtech/alchemux/blob/main/docs/install.md"
    "#2-install-ffmpeg-required"
)


@dataclass(frozen=True)
class DepStatus:
    """Result of checking a required system binary."""

    name: str
    found: bool
    path: Optional[str] = None


def check_ffmpeg() -> DepStatus:
    path = find_ffmpeg_binary()
    return DepStatus("ffmpeg", path is not None, str(path) if path else None)


def check_ffprobe() -> DepStatus:
    path = find_ffprobe_binary()
    return DepStatus("ffprobe", path is not None, str(path) if path else None)


def check_media_deps() -> Tuple[DepStatus, DepStatus]:
    """Return (ffmpeg, ffprobe) status."""
    return check_ffmpeg(), check_ffprobe()


def media_deps_ok() -> bool:
    ffmpeg, ffprobe = check_media_deps()
    return ffmpeg.found and ffprobe.found


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def detect_ffmpeg_install_command() -> Optional[str]:
    """
    Return one tailored install command for the current OS/package manager, or None.

    Detection is PATH-only (shutil.which) — no elevated probes.
    """
    system = sys.platform

    if system == "darwin":
        if _have("brew"):
            return "brew install ffmpeg"
        return None

    if system == "win32":
        if _have("choco"):
            return "choco install ffmpeg"
        if _have("winget"):
            return "winget install ffmpeg"
        return None

    # Linux / WSL
    if _have("apt-get") or _have("apt"):
        return "sudo apt update && sudo apt install ffmpeg"
    if _have("dnf"):
        return "sudo dnf install ffmpeg"
    if _have("pacman"):
        return "sudo pacman -S ffmpeg"
    if _have("brew"):
        # Linuxbrew
        return "brew install ffmpeg"
    return None


def ffmpeg_install_hint_lines() -> list[str]:
    """Human-readable hint lines for missing FFmpeg (terminal copy-paste)."""
    cmd = detect_ffmpeg_install_command()
    lines: list[str] = []
    if cmd:
        lines.append("Install it using the command below:")
        lines.append("")
        lines.append(f"  {cmd}")
    else:
        lines.append(
            "Install FFmpeg for your OS, then ensure ffmpeg and ffprobe are on PATH."
        )
    lines.append("")
    lines.append("Need more help?")
    lines.append(f"  {INSTALL_FFMPEG_URL}")
    return lines


def open_ffmpeg_install_guide() -> bool:
    """Open the FFmpeg section of install.md in the default browser. Returns True if launched."""
    try:
        webbrowser.open(INSTALL_FFMPEG_URL)
        return True
    except Exception:
        return False


def format_missing_ffmpeg_message() -> str:
    """Single-block message for runtime fracture / doctor."""
    parts = ["FFmpeg was not found on PATH."]
    parts.extend(ffmpeg_install_hint_lines())
    return "\n".join(parts)


def prompt_ffmpeg_until_ready(console) -> bool:
    """
    Setup orchestrator: block until ffmpeg+ffprobe are on PATH, or user quits.

    Keys:
      ENTER — re-check
      O     — open install guide in browser
      Q     — quit setup (returns False)

    Returns:
        True if deps are satisfied, False if user quit.
    """
    from rich.prompt import Prompt

    first = True
    while True:
        ffmpeg, ffprobe = check_media_deps()
        if ffmpeg.found and ffprobe.found:
            if not first:
                console.print("\n[green]✓[/green] ffmpeg")
                console.print("[green]✓[/green] ffprobe")
                console.print("\nContinuing setup...\n")
            return True

        missing = []
        if not ffmpeg.found:
            missing.append("ffmpeg")
        if not ffprobe.found:
            missing.append("ffprobe")

        console.print()
        if first:
            console.print("[bold yellow]⚠ Required dependency missing[/bold yellow]")
            console.print()
            console.print(
                "FFmpeg was not found."
                if "ffmpeg" in missing
                else "ffprobe was not found."
            )
            console.print()
            console.print("Alchemux requires FFmpeg to:")
            console.print("  • download and merge media")
            console.print("  • convert formats")
            console.print("  • inspect media files")
            console.print()
            for line in ffmpeg_install_hint_lines():
                console.print(line)
            console.print()
            console.print("When installation is complete,")
            console.print("return to this window and press ENTER.")
        else:
            console.print("[bold yellow]FFmpeg is still not available.[/bold yellow]")
            if missing:
                console.print(f"  Missing: {', '.join(missing)}")
            console.print()
            console.print("Make sure:")
            console.print("  • installation completed")
            console.print("  • your terminal was restarted if required")
            cmd = detect_ffmpeg_install_command()
            if cmd:
                console.print()
                console.print(f"  {cmd}")
            console.print()
            console.print(f"  {INSTALL_FFMPEG_URL}")

        console.print()
        console.print("Press ENTER to check again.")
        console.print("Press O to open the installation guide.")
        console.print("Press Q to quit setup.")

        choice = Prompt.ask("", default="", show_default=False)
        key = (choice or "").strip().lower()

        if key in ("q", "quit"):
            return False
        if key in ("o", "open"):
            console.print(f"\nOpening...\n  {INSTALL_FFMPEG_URL}\n")
            if not open_ffmpeg_install_guide():
                console.print(
                    "[yellow]Could not open browser. Visit the URL above manually.[/yellow]"
                )
            first = False
            continue

        # ENTER or anything else → re-check
        console.print("\nChecking...")
        first = False
