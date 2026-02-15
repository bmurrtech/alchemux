"""
Tests for video opt-in behavior (`media.video.enabled`).
"""

import sys
import tempfile
from pathlib import Path

# Ensure `app.*` imports work when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config_manager import ConfigManager  # noqa: E402
from app.core.downloader import MediaDownloader  # noqa: E402


def _write_cfg(tmpdir: Path, toml_text: str) -> ConfigManager:
    cfg_dir = tmpdir / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / ".env").write_text("")
    (cfg_dir / "config.toml").write_text(toml_text)
    return ConfigManager(env_path=str(cfg_dir / ".env"))


def test_video_disabled_by_default_routes_to_audio_path() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _write_cfg(
            Path(tmp),
            """
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"

[media.audio]
format = "mp3"

[media.video]
enabled = false
format = "mp4"
enabled_formats = ["mp4"]
""".strip(),
        )
        dl = MediaDownloader(cfg)
        opts = dl._build_ydl_opts("artifact", audio_format="mp3", video_format="mp4")

        assert opts.get("merge_output_format") is None
        assert opts.get("extractaudio") is True
        postprocessors = opts.get("postprocessors", [])
        assert any(pp.get("key") == "FFmpegExtractAudio" for pp in postprocessors)


def test_legacy_config_without_enabled_stays_disabled() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _write_cfg(
            Path(tmp),
            """
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"

[media.audio]
format = "mp3"

[media.video]
format = "mp4"
enabled_formats = ["mp4"]
""".strip(),
        )
        dl = MediaDownloader(cfg)
        opts = dl._build_ydl_opts("artifact", audio_format="mp3", video_format="mp4")

        assert opts.get("merge_output_format") is None
        postprocessors = opts.get("postprocessors", [])
        assert any(pp.get("key") == "FFmpegExtractAudio" for pp in postprocessors)


def test_enabled_true_activates_video_pipeline() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _write_cfg(
            Path(tmp),
            """
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"

[media.audio]
format = "mp3"

[media.video]
enabled = true
format = "mp4"
enabled_formats = ["mp4"]
""".strip(),
        )
        dl = MediaDownloader(cfg)
        opts = dl._build_ydl_opts("artifact", audio_format="mp3", video_format="mp4")

        assert opts.get("merge_output_format") == "mp4"
        assert opts.get("extractaudio") is None
        postprocessors = opts.get("postprocessors", [])
        assert all(pp.get("key") != "FFmpegExtractAudio" for pp in postprocessors)


def test_runtime_video_override_activates_video_pipeline() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _write_cfg(
            Path(tmp),
            """
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"

[media.audio]
format = "flac"

[media.video]
enabled = false
format = ""
enabled_formats = []
""".strip(),
        )
        dl = MediaDownloader(cfg)
        opts = dl._build_ydl_opts(
            "artifact",
            audio_format="flac",
            video_format="mp4",
            video_enabled_override=True,
        )

        assert opts.get("merge_output_format") == "mp4"
        assert opts.get("extractaudio") is None
        postprocessors = opts.get("postprocessors", [])
        assert all(pp.get("key") != "FFmpegExtractAudio" for pp in postprocessors)
