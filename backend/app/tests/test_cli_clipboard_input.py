"""
Tests for PRD6 clipboard URL input (-p/--clipboard).

Public-safe: mock pyperclip; never read or assert on real clipboard content.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.cli.app import app  # noqa: E402
from app.cli.url_input import (  # noqa: E402
    validate_url_like,
    _read_clipboard,
    CLIPBOARD_EMPTY_MSG,
    CLIPBOARD_UNSUPPORTED_MSG,
)


def _seed_temp_config(cfg_dir: Path) -> None:
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / ".env").write_text("S3_ACCESS_KEY=\nS3_SECRET_KEY=\n")
    (cfg_dir / "config.toml").write_text(
        '[product]\narcane_terms = true\n\n[paths]\noutput_dir = "./downloads"\ntemp_dir = "./tmp"\n'
    )


def test_clipboard_empty_exits_with_message() -> None:
    """When clipboard is empty, _read_clipboard returns (None, CLIPBOARD_EMPTY_MSG)."""
    with patch("app.cli.url_input.pyperclip") as m_pyperclip:
        m_pyperclip.paste.return_value = ""
        content, err = _read_clipboard()
        assert content is None
        assert CLIPBOARD_EMPTY_MSG in (err or "")


def test_clipboard_not_url_like_exits_with_message() -> None:
    """When clipboard content is not URL-like, acquisition should surface CLIPBOARD_NOT_URL_MSG or reprompt."""
    with patch("app.cli.url_input.pyperclip") as m_pyperclip:
        m_pyperclip.paste.return_value = "not a url"
        content, err = _read_clipboard()
        assert content == "not a url"
        assert err is None
    assert validate_url_like("not a url") is False


def test_clipboard_unavailable_returns_error_message() -> None:
    """When pyperclip.paste raises, _read_clipboard returns (None, CLIPBOARD_UNSUPPORTED_MSG)."""
    with patch("app.cli.url_input.pyperclip") as m_pyperclip:
        m_pyperclip.paste.side_effect = RuntimeError("clipboard unavailable")
        content, err = _read_clipboard()
        assert content is None
        assert err == CLIPBOARD_UNSUPPORTED_MSG


def test_cli_no_url_non_interactive_exits_with_hint() -> None:
    """Invoke root with no URL and no TTY (CliRunner) → exit 1 and NO_URL_NONINTERACTIVE_MSG."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_temp_config(cfg_dir)
        env = os.environ.copy()
        env["ALCHEMUX_CONFIG_DIR"] = str(cfg_dir)

        result = runner.invoke(app, [], env=env)
        assert result.exit_code == 1
        assert "No URL provided" in result.stdout


def test_cli_clipboard_flag_help() -> None:
    """--help shows -p/--clipboard."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--clipboard" in result.stdout
    assert "-p" in result.stdout
