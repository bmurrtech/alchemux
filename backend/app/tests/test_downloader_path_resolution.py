"""
Regression tests for output-path resolution (public-safe, no network).

Focus: when multiple formats exist in the output dir, the downloader must return
the path for the expected extension (e.g., .flac should not incorrectly return .mp3).
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure `app.*` imports work when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config_manager import ConfigManager  # noqa: E402
from app.core.downloader import MediaDownloader  # noqa: E402


def test_find_downloaded_file_prefers_expected_ext() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / ".env").write_text("")
        (cfg_dir / "config.toml").write_text(
            "[paths]\n" f'output_dir = "{cfg_dir.as_posix()}"\n' 'temp_dir = "./tmp"\n'
        )

        # Point ConfigManager to a temp .env so no real user config is touched.
        config = ConfigManager(env_path=str(cfg_dir / ".env"))
        dl = MediaDownloader(config)

        # Create two candidate outputs with different extensions.
        base = cfg_dir / "artifact"
        flac = base.with_suffix(".flac")
        mp3 = base.with_suffix(".mp3")

        # Ensure both exist and are non-empty (>0 bytes).
        flac.write_bytes(b"flac-bytes")
        mp3.write_bytes(b"mp3-bytes")

        # Provide minimal ydl_opts needed by the resolver.
        ydl_opts = {"paths": {"home": str(cfg_dir)}}

        resolved = dl._find_downloaded_file(
            output_path=str(base),
            downloaded_files=[],
            ydl_opts=ydl_opts,
            expected_ext=".flac",
        )

        assert resolved is not None
        assert resolved.endswith(".flac")
        assert os.path.basename(resolved) == "artifact.flac"
