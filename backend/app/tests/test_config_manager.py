"""
Tests for config_manager.py - config discovery, pointer files, and platformdirs integration.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest import mock

# Add parent to path for imports when running tests directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config_manager import (
    get_user_config_dir,
    get_default_output_dir,
    get_pointer_file_path,
    read_config_pointer,
    write_config_pointer,
    get_config_location,
    ConfigManager,
)


class TestGetUserConfigDir:
    """Tests for get_user_config_dir()."""

    def test_returns_path_object(self):
        """Should return a Path object."""
        result = get_user_config_dir()
        assert isinstance(result, Path)

    def test_directory_is_created(self):
        """Should create the directory if it doesn't exist."""
        result = get_user_config_dir()
        assert result.exists()
        assert result.is_dir()

    def test_contains_alchemux_in_path(self):
        """Path should contain Alchemux (case-insensitive)."""
        result = get_user_config_dir()
        assert "alchemux" in str(result).lower()


class TestGetDefaultOutputDir:
    """Tests for get_default_output_dir()."""

    def test_returns_path_object(self):
        """Should return a Path object."""
        result = get_default_output_dir()
        assert isinstance(result, Path)

    def test_contains_alchemux(self):
        """Path should contain Alchemux."""
        result = get_default_output_dir()
        assert "Alchemux" in str(result) or "alchemux" in str(result).lower()

    def test_is_under_downloads(self):
        """Path should be under Downloads directory."""
        result = get_default_output_dir()
        # Case-insensitive check for "downloads" in path
        assert "downloads" in str(result).lower()


class TestPointerFile:
    """Tests for pointer file read/write operations."""

    def test_get_pointer_file_path_returns_path(self):
        """Should return a Path object."""
        result = get_pointer_file_path()
        assert isinstance(result, Path)

    def test_get_pointer_file_path_has_txt_extension(self):
        """Pointer file should have .txt extension."""
        result = get_pointer_file_path()
        assert result.suffix == ".txt"
        assert result.name == "config_path.txt"

    def test_read_config_pointer_returns_none_when_missing(self):
        """Should return None when pointer file doesn't exist."""
        # Use a mock to ensure pointer file doesn't exist
        with mock.patch("app.core.config_manager.get_pointer_file_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/path/config_path.txt")
            result = read_config_pointer()
            assert result is None

    def test_write_and_read_config_pointer(self):
        """Should be able to write and read pointer file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config_dir = Path(tmpdir) / "test_config"
            test_config_dir.mkdir()
            pointer_file = Path(tmpdir) / "pointer" / "config_path.txt"

            with mock.patch(
                "app.core.config_manager.get_pointer_file_path"
            ) as mock_path:
                mock_path.return_value = pointer_file

                # Write pointer
                write_config_pointer(test_config_dir)

                # Read pointer
                result = read_config_pointer()

                assert result is not None
                assert result == test_config_dir.resolve()

    def test_read_config_pointer_returns_none_for_invalid_target(self):
        """Should return None when pointer points to non-existent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pointer_file = Path(tmpdir) / "config_path.txt"
            # Write a path that doesn't exist
            pointer_file.write_text("/nonexistent/config/directory")

            with mock.patch(
                "app.core.config_manager.get_pointer_file_path"
            ) as mock_path:
                mock_path.return_value = pointer_file
                result = read_config_pointer()
                assert result is None


class TestGetConfigLocationPriority:
    """Tests for get_config_location() priority order."""

    def test_env_var_takes_priority(self):
        """ALCHEMUX_CONFIG_DIR env var should take highest priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_env = {"ALCHEMUX_CONFIG_DIR": tmpdir}

            with mock.patch.dict(os.environ, test_env, clear=False):
                result = get_config_location()
                assert result == Path(tmpdir) / ".env"

    def test_pointer_file_takes_priority_over_default(self):
        """Pointer file should be used when env var is not set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config_dir = Path(tmpdir) / "custom_config"
            test_config_dir.mkdir()

            # Ensure no env var
            env_without_config = {
                k: v for k, v in os.environ.items() if k != "ALCHEMUX_CONFIG_DIR"
            }

            with mock.patch.dict(os.environ, env_without_config, clear=True):
                with mock.patch(
                    "app.core.config_manager.read_config_pointer"
                ) as mock_read:
                    mock_read.return_value = test_config_dir

                    result = get_config_location()
                    assert result == test_config_dir / ".env"

    def test_falls_back_to_default_when_no_pointer(self):
        """Should use default OS config when no env var or pointer."""
        # Clear env var and mock no pointer
        env_without_config = {
            k: v for k, v in os.environ.items() if k != "ALCHEMUX_CONFIG_DIR"
        }

        with mock.patch.dict(os.environ, env_without_config, clear=True):
            with mock.patch("app.core.config_manager.read_config_pointer") as mock_read:
                mock_read.return_value = None

                # For source mode (not frozen), it tries find_dotenv first
                # We mock that to return None to test the fallback
                with mock.patch("app.core.config_manager.find_dotenv") as mock_find:
                    mock_find.return_value = None

                    with mock.patch("pathlib.Path.exists") as mock_exists:
                        mock_exists.return_value = False

                        # Just verify it doesn't crash and returns a path
                        result = get_config_location()
                        assert isinstance(result, Path)
                        assert result.name == ".env"


class TestConfigManager:
    """Tests for ConfigManager class."""

    def test_init_sets_env_path(self):
        """ConfigManager should set env_path on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("TEST=value\n")

            config = ConfigManager(env_path=str(env_path))
            assert config.env_path == env_path

    def test_init_sets_toml_path(self):
        """ConfigManager should set toml_path on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("TEST=value\n")

            config = ConfigManager(env_path=str(env_path))
            assert config.toml_path is not None
            assert config.toml_path.suffix == ".toml"

    def test_is_secret_key_detects_secrets(self):
        """Should correctly identify secret keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("")

            config = ConfigManager(env_path=str(env_path))

            # Should be secrets
            assert config._is_secret_key("S3_ACCESS_KEY") is True
            assert config._is_secret_key("GCP_SA_KEY_BASE64") is True
            assert config._is_secret_key("API_SECRET") is True
            assert config._is_secret_key("PASSWORD") is True
            assert config._is_secret_key("TOKEN") is True

            # Should NOT be secrets
            assert config._is_secret_key("paths.output_dir") is False
            assert config._is_secret_key("ui.auto_open") is False
            assert config._is_secret_key("media.audio.format") is False


class TestNoSecretsInLogs:
    """Tests to ensure secrets are not logged."""

    def test_secret_values_not_in_debug_output(self):
        """Secret values should be masked in debug output."""
        import logging

        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("S3_SECRET_KEY=super_secret_value_12345\n")

            # Capture log output
            log_capture = []

            class LogCapture(logging.Handler):
                def emit(self, record):
                    log_capture.append(record.getMessage())

            # Get the logger and add our capture handler
            import app.core.config_manager

            test_logger = logging.getLogger(app.core.config_manager.__name__)
            original_level = test_logger.level
            test_logger.setLevel(logging.DEBUG)
            handler = LogCapture()
            test_logger.addHandler(handler)

            try:
                config = ConfigManager(env_path=str(env_path))
                # This should log with masked value
                _ = config.get("S3_SECRET_KEY")

                # Check that the secret value is not in any log message
                all_logs = " ".join(log_capture)
                assert "super_secret_value_12345" not in all_logs

                # But "***" should appear (masked)
                assert "***" in all_logs or len(log_capture) == 0
            finally:
                test_logger.removeHandler(handler)
                test_logger.setLevel(original_level)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
