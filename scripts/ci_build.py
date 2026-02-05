#!/usr/bin/env python3
"""
CI PyInstaller build script for Alchemux.
Used by GitHub Actions; lives in scripts/ (committed). Local builds use pm/scripts/build.py.
Creates a single-file executable with bundled ffmpeg/ffprobe.
Requires DIST_DIR in CI; defaults to repo root/dist when run locally.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# Project root: scripts/ is one level under repo root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
# CI sets DIST_DIR (e.g. $GITHUB_WORKSPACE/dist); local test defaults to repo root/dist
DIST_DIR = Path(os.environ["DIST_DIR"]).resolve() if os.environ.get("DIST_DIR") else (PROJECT_ROOT / "dist")
BUILD_DIR = PROJECT_ROOT / "build"


def clean_build_dirs():
    """Clean build and dist directories."""
    print("Cleaning build directories...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    print("[OK] Cleaned")


def find_ffmpeg_binaries():
    """
    Find ffmpeg and ffprobe binaries on the system.
    Returns (ffmpeg_path, ffprobe_path) or (None, None) if not found.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if ffmpeg_path and ffprobe_path:
        print(f"[OK] Found ffmpeg: {ffmpeg_path}")
        print(f"[OK] Found ffprobe: {ffprobe_path}")
        return Path(ffmpeg_path), Path(ffprobe_path)
    print("[!] Warning: ffmpeg/ffprobe not found in PATH")
    return None, None


def build_binary():
    """Build binary using PyInstaller (alchemux only) with bundled ffmpeg/ffprobe."""
    print("\nBuilding binaries with PyInstaller...")
    ffmpeg_path, ffprobe_path = find_ffmpeg_binaries()
    binary_name = "alchemux"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", binary_name,
        "--onefile",
        "--clean",
        "--noconfirm",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / binary_name),
        "--specpath", str(BUILD_DIR / binary_name),
        str(BACKEND_DIR / "app" / "main.py"),
    ]

    hidden_imports = [
        "yt_dlp", "mutagen", "mutagen.id3", "mutagen.mp3", "mutagen.flac",
        "google.cloud.storage", "dotenv", "platformdirs", "tomlkit",
        "InquirerPy", "InquirerPy.prompts", "InquirerPy.prompts.list",
        "InquirerPy.prompts.input", "InquirerPy.prompts.filepath",
        "InquirerPy.validator", "InquirerPy.base.control",
        "prompt_toolkit", "prompt_toolkit.application", "prompt_toolkit.key_binding",
        "prompt_toolkit.formatted_text", "prompt_toolkit.completion",
        "prompt_toolkit.completion.filesystem",
    ]
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    try:
        import InquirerPy  # noqa: F401
        cmd.extend(["--collect-all", "InquirerPy"])
    except ImportError:
        pass
    try:
        import prompt_toolkit  # noqa: F401
        cmd.extend(["--collect-all", "prompt_toolkit"])
    except ImportError:
        pass

    if ffmpeg_path and ffprobe_path:
        sep = ";" if sys.platform == "win32" else ":"
        cmd.extend(["--add-binary", f"{ffmpeg_path}{sep}."])
        cmd.extend(["--add-binary", f"{ffprobe_path}{sep}."])

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        return False

    binary_path = DIST_DIR / (binary_name + (".exe" if sys.platform == "win32" else ""))
    if binary_path.exists():
        print(f"[OK] {binary_name} built successfully")
    return True


def create_launchers():
    """Create macOS .command launcher for double-click execution."""
    launcher_path = DIST_DIR / "alchemux.command"
    with open(launcher_path, "w") as f:
        f.write('#!/bin/bash\ncd "$(dirname "$0")"\n./alchemux "$@"\n')
    os.chmod(launcher_path, 0o755)
    print(f"[OK] Created launcher: {launcher_path}")


def main():
    print("=" * 70)
    print("Alchemux CI Binary Build")
    print("=" * 70)
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("[X] PyInstaller not found. pip install pyinstaller")
        return 1

    clean_build_dirs()
    if not build_binary():
        return 1
    if sys.platform == "darwin":
        create_launchers()

    alchemux_path = DIST_DIR / ("alchemux.exe" if sys.platform == "win32" else "alchemux")
    if alchemux_path.exists():
        print(f"\n[OK] Build successful: {alchemux_path}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
