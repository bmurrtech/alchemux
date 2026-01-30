"""
Tests for batch command (CLI registration, prereq gating, non-TTY exit).

Public-safe: temp config dir; mocks for InquirerPy; no network.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import typer
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.cli.app import app  # noqa: E402
from app.cli.commands import batch as batch_module  # noqa: E402

runner = CliRunner()


def test_batch_in_help() -> None:
    """--help must list batch command."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "batch" in result.output


def test_batch_requires_tty_exits_with_message() -> None:
    """When not TTY, batch exits with code 1."""
    with patch.object(batch_module, "is_tty", return_value=False):
        with pytest.raises(typer.Exit) as exc_info:
            batch_module.batch()
        assert exc_info.value.exit_code == 1


def test_batch_requires_prereqs_exits_with_setup_message() -> None:
    """When TTY but config/EULA not satisfied, batch exits with code 1."""
    with patch.object(batch_module, "is_tty", return_value=True):
        with patch.object(batch_module, "_check_prerequisites", return_value=False):
            with pytest.raises(typer.Exit) as exc_info:
                batch_module.batch()
            assert exc_info.value.exit_code == 1


def test_batch_prereqs_ok_calls_flow() -> None:
    """When TTY and prereqs OK, batch enters flow (mocked inquirer to avoid hang)."""
    with patch.object(batch_module, "is_tty", return_value=True):
        with patch.object(batch_module, "_check_prerequisites", return_value=True):
            mock_inq = MagicMock()
            mock_inq.select.return_value.execute.side_effect = typer.Exit(130)
            with patch.object(batch_module, "inquirer", mock_inq):
                with pytest.raises(typer.Exit):
                    batch_module.batch()
    assert mock_inq.select.called
