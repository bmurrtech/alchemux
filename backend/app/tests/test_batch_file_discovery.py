"""
Tests for batch file discovery (config dir scan, .txt/.csv only, display formatting).

Public-safe: temp config dir; no real credentials.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.cli.commands.batch import (  # noqa: E402
    _format_file_size,
    _collect_urls_from_files,
)


def test_format_file_size() -> None:
    assert "B" in _format_file_size(100)
    assert "KiB" in _format_file_size(1024)
    assert _format_file_size(0) == "0 B"


def test_collect_urls_from_files_no_config_dir_returns_empty() -> None:
    """When config dir does not exist, expect empty list and message (via typer.echo)."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "nonexistent"
        assert not cfg_dir.exists()
        with patch("app.core.config_manager.ConfigManager") as MockConfig:
            mock_config = MagicMock()
            mock_config.env_path.parent = cfg_dir
            MockConfig.return_value = mock_config
            result = _collect_urls_from_files()
        assert result == []


def test_collect_urls_from_files_no_txt_csv_returns_empty() -> None:
    """When config dir has no .txt/.csv files, expect empty list."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp)
        (cfg_dir / "config.toml").write_text('[paths]\noutput_dir = "."')
        (cfg_dir / ".env").write_text("")
        (cfg_dir / "other.pdf").write_text("")
        with patch("app.core.config_manager.ConfigManager") as MockConfig:
            mock_config = MagicMock()
            mock_config.env_path.parent = cfg_dir
            MockConfig.return_value = mock_config
            result = _collect_urls_from_files()
        assert result == []


def test_collect_urls_from_files_one_txt_extracts_urls() -> None:
    """When one .txt file exists and user 'selects' it (mocked), URLs are extracted."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp)
        (cfg_dir / "config.toml").write_text('[paths]\noutput_dir = "."')
        (cfg_dir / ".env").write_text("")
        batch_txt = cfg_dir / "urls.txt"
        batch_txt.write_text("https://a.com\nhttps://b.com\n")
        with patch("app.core.config_manager.ConfigManager") as MockConfig:
            mock_config = MagicMock()
            mock_config.env_path.parent = cfg_dir
            MockConfig.return_value = mock_config
            with patch("app.cli.commands.batch.inquirer") as mock_inq:
                mock_inq.checkbox.return_value.execute.return_value = [str(batch_txt)]
                result = _collect_urls_from_files()
        assert result == ["https://a.com", "https://b.com"]
