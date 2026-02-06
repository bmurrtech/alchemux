#!/usr/bin/env python3
"""
CI helper: print platform and CPU arch for artifact naming.
Output: two lines, platform then arch (e.g. darwin\\narm64).
Used by .github/workflows/release.yml. ASCII-only for Windows cp1252.
"""

import platform
import sys


def get_platform() -> str:
    """Return platform name: darwin, linux, or windows."""
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform == "win32":
        return "windows"
    return "linux"


def get_arch() -> str:
    """Return normalized CPU arch: x86_64, arm64, or raw machine string lowercased."""
    m = (platform.machine() or "").strip().lower()
    if m in ("x86_64", "amd64", "x64"):
        return "x86_64"
    if m in ("arm64", "aarch64"):
        return "arm64"
    if m in ("i686", "i386", "x86"):
        return "x86_64"  # treat 32-bit x86 as x86_64 for naming
    return m or "unknown"


if __name__ == "__main__":
    print(get_platform())
    print(get_arch())
