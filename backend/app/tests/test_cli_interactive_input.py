"""
Tests for PRD6 interactive URL input (no-args flow).

Public-safe: temp config dir, mocks for InquirerPy and prerequisites.
Never read real clipboard; never log clipboard content.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import typer

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.cli.url_input import (  # noqa: E402
    validate_url_like,
    domain_preview,
    acquire_url,
    is_tty,
    CLIPBOARD_UNSUPPORTED_MSG,
)


def _seed_temp_config(cfg_dir: Path) -> None:
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / ".env").write_text("S3_ACCESS_KEY=\nS3_SECRET_KEY=\n")
    (cfg_dir / "config.toml").write_text(
        '[product]\narcane_terms = true\n\n[paths]\noutput_dir = "./downloads"\ntemp_dir = "./tmp"\n'
    )


def test_validate_url_like() -> None:
    assert validate_url_like("https://example.com/path") is True
    assert validate_url_like("http://youtube.com/watch?v=1") is True
    assert validate_url_like("  https://a.co  ") is True
    assert validate_url_like("") is False
    assert validate_url_like("   ") is False
    assert validate_url_like("not a url") is False
    assert validate_url_like("ftp://x.y") is False  # only http(s)


def test_domain_preview() -> None:
    assert "youtube.com" in domain_preview("https://www.youtube.com/shorts/abc")
    assert "example.com" in domain_preview("https://example.com/path?q=1")
    assert domain_preview("") == "unknown"


def test_is_tty() -> None:
    # In pytest/CliRunner stdin is not a TTY
    assert isinstance(is_tty(), bool)


def test_acquire_url_no_url_non_tty_exits_with_message() -> None:
    """No URL and non-TTY must exit with code 1 (no prompts)."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_temp_config(cfg_dir)
        env = os.environ.copy()
        env["ALCHEMUX_CONFIG_DIR"] = str(cfg_dir)

        with patch("app.cli.url_input.is_tty", return_value=False):
            with pytest.raises(typer.Exit) as exc_info:
                acquire_url(url_arg=None, use_clipboard=False, is_tty=False)
            assert exc_info.value.exit_code == 1


def test_acquire_url_no_url_no_prereqs_exits_setup_message() -> None:
    """No URL, TTY, but config missing → exit with code 1, no interactive prompts."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / ".env").write_text("")
        # No config.toml
        env = os.environ.copy()
        env["ALCHEMUX_CONFIG_DIR"] = str(cfg_dir)

        with patch("app.cli.url_input.is_tty", return_value=True):
            with patch("app.cli.url_input._check_prerequisites", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    acquire_url(url_arg=None, use_clipboard=False, is_tty=True)
                assert exc_info.value.exit_code == 1


def test_acquire_url_clipboard_unavailable_non_tty_exits_message() -> None:
    """-p/--clipboard with clipboard unavailable and no TTY → exit code 1 (no --stdin)."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_temp_config(cfg_dir)
        env = os.environ.copy()
        env["ALCHEMUX_CONFIG_DIR"] = str(cfg_dir)

        with patch("app.cli.url_input.is_tty", return_value=False):
            with patch(
                "app.cli.url_input._read_clipboard",
                return_value=(None, CLIPBOARD_UNSUPPORTED_MSG),
            ):
                with pytest.raises(typer.Exit) as exc_info:
                    acquire_url(url_arg=None, use_clipboard=True, is_tty=False)
                assert exc_info.value.exit_code == 1


def test_acquire_url_clipboard_valid_returns_url_and_overrides() -> None:
    """Clipboard returns valid URL → acquire_url returns (url, overrides); overrides prompt called when inquirer present."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_temp_config(cfg_dir)

        with patch("app.cli.url_input.is_tty", return_value=True):
            with patch(
                "app.cli.url_input._read_clipboard",
                return_value=("https://example.com/v", None),
            ):
                with patch("app.cli.url_input.inquirer", None):
                    url, overrides = acquire_url(
                        url_arg=None, use_clipboard=True, is_tty=True
                    )
                    assert url == "https://example.com/v"
                    assert overrides == {}
                mock_inquirer = MagicMock()
                mock_inquirer.confirm.return_value.execute.return_value = True
                with patch("app.cli.url_input.inquirer", mock_inquirer):
                    with patch(
                        "app.cli.url_input._interactive_overrides_prompt",
                        return_value={"verbose": True},
                    ) as m_overrides:
                        url2, overrides2 = acquire_url(
                            url_arg=None, use_clipboard=True, is_tty=True
                        )
                        assert url2 == "https://example.com/v"
                        assert overrides2.get("verbose") is True
                        m_overrides.assert_called_once()


def test_acquire_url_interactive_returns_url_when_prereqs_ok() -> None:
    """No URL, no clipboard, TTY, prereqs ok → interactive prompt returns URL (mocked)."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_temp_config(cfg_dir)
        env = os.environ.copy()
        env["ALCHEMUX_CONFIG_DIR"] = str(cfg_dir)

        with patch("app.cli.url_input.is_tty", return_value=True):
            with patch("app.cli.url_input._check_prerequisites", return_value=True):
                with patch(
                    "app.cli.url_input._interactive_url_prompt",
                    return_value="https://youtube.com/watch?v=1",
                ):
                    with patch(
                        "app.cli.url_input._interactive_overrides_prompt",
                        return_value={},
                    ):
                        url, overrides = acquire_url(
                            url_arg=None, use_clipboard=False, is_tty=True
                        )
                        assert url == "https://youtube.com/watch?v=1"
                        assert overrides == {}
