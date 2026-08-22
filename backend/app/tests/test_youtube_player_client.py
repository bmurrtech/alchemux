"""YouTube player_client / fracture-cause seams for HTTP 403 mitigation.

Seams under test:
- ``MediaDownloader._build_ydl_opts`` — default and overrideable youtube player_client
- ``_normalize_fracture_cause`` — 403 user-facing cause (no residential-CDN claim)
- ``_update_ytdlp_stable`` — pip/wheel fallback when yt-dlp ``-U`` refuses
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.cli.commands.distill import _normalize_fracture_cause  # noqa: E402
from app.cli.commands.update import _update_ytdlp_stable  # noqa: E402
from app.core.config_manager import ConfigManager  # noqa: E402
from app.core.downloader import MediaDownloader  # noqa: E402


def _downloader(tmpdir: Path, toml: str = "") -> MediaDownloader:
    cfg = tmpdir / "cfg"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / ".env").write_text("")
    body = toml.strip() or ('[paths]\noutput_dir = "./downloads"\ntemp_dir = "./tmp"\n')
    (cfg / "config.toml").write_text(body)
    return MediaDownloader(ConfigManager(env_path=str(cfg / ".env")))


def test_ydl_opts_default_youtube_player_client_android_web() -> None:
    """Default distill opts ask yt-dlp for android then web YouTube clients."""
    with tempfile.TemporaryDirectory() as tmp:
        opts = _downloader(Path(tmp))._build_ydl_opts("artifact", audio_format="mp3")

    assert opts["extractor_args"]["youtube"]["player_client"] == ["android", "web"]


def test_ydl_opts_player_client_env_overrides_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """YTDL_PLAYER_CLIENT replaces the default client list for one run."""
    monkeypatch.setenv("YTDL_PLAYER_CLIENT", "ios,web")
    with tempfile.TemporaryDirectory() as tmp:
        opts = _downloader(Path(tmp))._build_ydl_opts("artifact", audio_format="mp3")

    assert opts["extractor_args"]["youtube"]["player_client"] == ["ios", "web"]


def test_ydl_opts_player_client_config_overrides_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """config.toml [ytdl] player_client overrides the built-in default."""
    monkeypatch.delenv("YTDL_PLAYER_CLIENT", raising=False)
    with tempfile.TemporaryDirectory() as tmp:
        opts = _downloader(
            Path(tmp),
            """
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"

[ytdl]
player_client = "web"
""",
        )._build_ydl_opts("artifact", audio_format="mp3")

    assert opts["extractor_args"]["youtube"]["player_client"] == ["web"]


def test_ydl_opts_player_client_default_keyword_skips_extractor_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """player_client=default leaves yt-dlp's own client selection alone."""
    monkeypatch.setenv("YTDL_PLAYER_CLIENT", "default")
    with tempfile.TemporaryDirectory() as tmp:
        opts = _downloader(Path(tmp))._build_ydl_opts("artifact", audio_format="mp3")

    assert "extractor_args" not in opts


def test_fracture_cause_403_points_to_update_not_residential_ip() -> None:
    """403 fractures advise update / player_client, not residential CDN relocation."""
    cause = _normalize_fracture_cause(
        "ERROR: unable to download video data: HTTP Error 403: Forbidden"
    )
    assert "403" in cause
    assert "residential" not in cause.lower()
    assert "cdn blocked" not in cause.lower()
    assert "update" in cause.lower() or "player_client" in cause.lower()


def test_update_falls_back_to_pip_when_ytdlp_self_update_refuses_pip_install() -> None:
    """When yt-dlp -U says use pip, Alchemux upgrades via python -m pip."""
    refuse = MagicMock(
        returncode=1,
        stdout="",
        stderr=(
            "ERROR: You installed yt-dlp with pip or using the wheel from PyPi; "
            "Use that to update"
        ),
    )
    pip_ok = MagicMock(
        returncode=0, stdout="Successfully installed yt-dlp-2026.8.19", stderr=""
    )

    with patch(
        "app.cli.commands.update.subprocess.run", side_effect=[refuse, pip_ok]
    ) as run:
        ok, msg = _update_ytdlp_stable()

    assert ok is True
    assert msg is not None
    pip_calls = [
        call.args[0]
        for call in run.call_args_list
        if call.args
        and len(call.args[0]) >= 4
        and call.args[0][:4] == [sys.executable, "-m", "pip", "install"]
    ]
    assert pip_calls, "expected pip install fallback after yt-dlp -U refusal"
    assert "--upgrade" in pip_calls[0]
    assert "yt-dlp" in pip_calls[0]
