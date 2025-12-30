#!/usr/bin/env python3
"""
PyInstaller build script for Alchemux binary.
Creates a single-file executable with bundled ffmpeg/ffprobe.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# Get project root (parent of backend/)
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DIST_DIR = PROJECT_ROOT / "dist" / "macos"
BUILD_DIR = PROJECT_ROOT / "build"


def clean_build_dirs():
    """Clean build and dist directories."""
    print("Cleaning build directories...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    print("✓ Cleaned")


def find_ffmpeg_binaries():
    """
    Find ffmpeg and ffprobe binaries on the system.
    
    Returns:
        Tuple of (ffmpeg_path, ffprobe_path) or (None, None) if not found
    """
    # Determine binary names based on platform
    if sys.platform == "win32":
        ffmpeg_name = "ffmpeg.exe"
        ffprobe_name = "ffprobe.exe"
    else:
        ffmpeg_name = "ffmpeg"
        ffprobe_name = "ffprobe"
    
    # Find binaries in PATH
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    
    if ffmpeg_path and ffprobe_path:
        print(f"✓ Found ffmpeg: {ffmpeg_path}")
        print(f"✓ Found ffprobe: {ffprobe_path}")
        return Path(ffmpeg_path), Path(ffprobe_path)
    else:
        print("⚠️  Warning: ffmpeg/ffprobe not found in PATH")
        print("   The binary will still work but may require system ffmpeg installation.")
        return None, None


def build_binary():
    """Build binaries using PyInstaller (both amx and alchemux) with bundled ffmpeg/ffprobe."""
    print("\nBuilding binaries with PyInstaller...")
    
    # Find ffmpeg binaries to bundle
    ffmpeg_path, ffprobe_path = find_ffmpeg_binaries()
    
    binaries = ["amx", "alchemux"]
    built_binaries = []
    
    for binary_name in binaries:
        print(f"\nBuilding {binary_name}...")
        # PyInstaller command
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--name", binary_name,
            "--onefile",
            "--clean",
            "--noconfirm",
            "--distpath", str(DIST_DIR),
            "--workpath", str(BUILD_DIR / binary_name),
            "--specpath", str(BUILD_DIR / binary_name),
            # Entry point
            str(BACKEND_DIR / "app" / "main.py"),
        ]
    
        # Hidden imports (PyInstaller may not detect these automatically)
        hidden_imports = [
            "yt_dlp",
            "mutagen",
            "mutagen.id3",
            "mutagen.mp3",
            "mutagen.flac",
            "google.cloud.storage",
            "dotenv",
        ]
        
        for imp in hidden_imports:
            cmd.extend(["--hidden-import", imp])
        
        # Add ffmpeg/ffprobe binaries if found (included by default)
        if ffmpeg_path and ffprobe_path:
            # PyInstaller --add-binary format: "source:dest"
            # For onefile mode, binaries are extracted to temp directory
            # Use "." to place them in the root of the extracted bundle
            if sys.platform == "win32":
                cmd.extend(["--add-binary", f"{ffmpeg_path};."])
                cmd.extend(["--add-binary", f"{ffprobe_path};."])
            else:
                cmd.extend(["--add-binary", f"{ffmpeg_path}:."])
                cmd.extend(["--add-binary", f"{ffprobe_path}:."])
            print(f"  Including ffmpeg/ffprobe binaries...")
        
        # Collect all data files (if needed)
        # cmd.extend(["--collect-all", "yt_dlp"])
        
        print(f"Running: {' '.join(cmd[:10])}...")  # Show first part of command
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        
        if result.returncode != 0:
            print(f"❌ Build failed for {binary_name}!")
            return False
        
        binary_path = DIST_DIR / binary_name
        if binary_path.exists():
            built_binaries.append(binary_name)
            print(f"✓ {binary_name} built successfully")
    
    print(f"\n✓ All binaries built: {', '.join(built_binaries)}")
    return True


def create_launchers():
    """Create macOS .command launchers for double-click execution."""
    launchers = [
        ("amx.command", "amx"),
        ("alchemux.command", "alchemux")
    ]
    
    for launcher_name, binary_name in launchers:
        launcher_path = DIST_DIR / launcher_name
        
        launcher_content = f"""#!/bin/bash
# Alchemux launcher for macOS ({binary_name})
cd "$(dirname "$0")"
./{binary_name} "$@"
"""
        
        with open(launcher_path, 'w') as f:
            f.write(launcher_content)
        
        # Make executable
        os.chmod(launcher_path, 0o755)
        print(f"✓ Created launcher: {launcher_path}")


def main():
    """Main build function."""
    print("=" * 70)
    print("Alchemux macOS Binary Build")
    print("=" * 70)
    
    # Check PyInstaller is installed
    try:
        import PyInstaller
        print(f"✓ PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller not found. Install with: pip install pyinstaller")
        return 1
    
    # Clean
    clean_build_dirs()
    
    # Build
    if not build_binary():
        return 1
    
    # Create launchers
    create_launchers()
    
    # Summary
    amx_path = DIST_DIR / "amx"
    alchemux_path = DIST_DIR / "alchemux"
    
    if amx_path.exists() and alchemux_path.exists():
        amx_size = amx_path.stat().st_size / (1024 * 1024)
        alchemux_size = alchemux_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ Build successful!")
        print(f"   Binaries:")
        print(f"     - {amx_path} ({amx_size:.1f} MB)")
        print(f"     - {alchemux_path} ({alchemux_size:.1f} MB)")
        print(f"   Launchers:")
        print(f"     - {DIST_DIR / 'amx.command'}")
        print(f"     - {DIST_DIR / 'alchemux.command'}")
        print(f"\nTo test:")
        print(f"   {amx_path} --version")
        print(f"   {alchemux_path} --version")
        return 0
    else:
        print("❌ Binaries not found after build!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

