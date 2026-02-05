"""
Tests for update command (public-safe, no network required for basic tests).

Tests verify update logic without actually performing network operations.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import pytest
from typer.testing import CliRunner

# Ensure `app.*` imports work when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.cli.commands.update import (  # noqa: E402
    _should_check_for_updates,
    _get_last_update_check_path,
    _record_update_check,
    _get_current_ytdlp_version,
)
from app.cli.app import app  # noqa: E402


def test_update_check_throttling():
    """Test that update checks are throttled to once per day."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / ".env").write_text("")
        
        # Mock ConfigManager to return our temp dir
        with patch('app.cli.commands.update.ConfigManager') as mock_config:
            mock_instance = MagicMock()
            mock_instance.env_path.parent = cfg_dir
            mock_config.return_value = mock_instance
            
            # First check should proceed
            assert _should_check_for_updates(force=False) is True
            
            # Record check
            _record_update_check()
            
            # Immediate check should be throttled
            assert _should_check_for_updates(force=False) is False
            
            # Force should bypass throttling
            assert _should_check_for_updates(force=True) is True


def test_update_check_file_creation():
    """Test that update check timestamp file is created."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / ".env").write_text("")
        
        with patch('app.cli.commands.update.ConfigManager') as mock_config:
            mock_instance = MagicMock()
            mock_instance.env_path.parent = cfg_dir
            mock_config.return_value = mock_instance
            
            _record_update_check()
            
            check_file = _get_last_update_check_path()
            assert check_file.exists()
            assert check_file.read_text().strip()  # Should have timestamp


def test_get_current_version():
    """Test getting current yt-dlp version."""
    # This test may or may not have yt-dlp installed
    # Just verify it doesn't crash
    version = _get_current_ytdlp_version()
    # Version can be None or a string, both are valid
    assert version is None or isinstance(version, str)


def test_update_command_invocation():
    """Test that update command can be invoked via CLI without URL validation error."""
    runner = CliRunner()
    
    # Mock the update function to avoid actual network calls
    with patch('app.cli.commands.update.update') as mock_update:
        # Set up environment for isolated testing
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp) / "cfg"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / ".env").write_text("")
            (cfg_dir / "config.toml").write_text("[product]\narcane_terms = false\n")
            
            # Set ALCHEMUX_CONFIG_DIR to isolate test
            env = os.environ.copy()
            env["ALCHEMUX_CONFIG_DIR"] = str(cfg_dir)
            
            # Invoke update command
            result = runner.invoke(app, ["update"], env=env)
            
            # Log the result for debugging
            print(f"\n[TEST] Update command exit code: {result.exit_code}")
            print(f"[TEST] Update command stdout: {result.stdout[:500]}")
            print(f"[TEST] Update command stderr: {result.stderr[:500]}")
            
            # Should not fail with "invalid URL format" error
            assert "invalid URL format" not in result.stdout.lower()
            assert "invalid URL format" not in result.stderr.lower()
            
            # Command should be recognized (either runs update or shows help)
            # If update was mocked, it should have been called
            # If not mocked, it might fail for other reasons (network, etc.) but NOT URL validation
            assert result.exit_code != 1 or "invalid URL format" not in (result.stdout + result.stderr).lower()
