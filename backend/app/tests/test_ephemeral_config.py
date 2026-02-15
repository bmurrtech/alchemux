"""
Tests for EphemeralConfig (--no-config mode).
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config_manager import EphemeralConfig


def test_ephemeral_config_returns_download_dir_for_paths() -> None:
    cfg = EphemeralConfig("/tmp/amx-out")
    assert cfg.get("paths.output_dir") == "/tmp/amx-out"
    assert cfg.get("paths.temp_dir") == "/tmp/amx-out"


def test_ephemeral_config_storage_local() -> None:
    cfg = EphemeralConfig("/tmp/out")
    assert cfg.get_storage_destination() == "local"
    assert cfg.is_s3_configured() is False
    assert cfg.is_gcp_configured() is False


def test_ephemeral_config_check_toml_exists() -> None:
    cfg = EphemeralConfig("/tmp/out")
    assert cfg.check_toml_file_exists() is True
    assert cfg.check_env_file_exists() is True


def test_ephemeral_config_validate_required() -> None:
    cfg = EphemeralConfig("/tmp/out")
    valid, missing = cfg.validate_required(["paths.output_dir"])
    assert valid is True
    assert missing == []


def test_ephemeral_config_get_list_defaults() -> None:
    cfg = EphemeralConfig("/tmp/out")
    assert cfg.get_list("media.audio.enabled_formats") == ["flac"]
    assert cfg.get_list("media.video.enabled_formats") == []


def test_ephemeral_config_video_disabled_by_default() -> None:
    cfg = EphemeralConfig("/tmp/out")
    assert cfg.get("media.video.enabled") == "false"
    assert cfg.get_bool("media.video.enabled", default=True) is False
