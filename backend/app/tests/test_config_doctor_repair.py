"""
Tests for config doctor diagnostics and guided repair (PRD7 FR-3/FR-4).

Public-safe tests using temp directories only. No secrets or real user configs.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure `app.*` imports work when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config_manager import ConfigManager  # noqa: E402
from app.core.toml_config import read_toml, write_toml  # noqa: E402


def _seed_minimal_config(cfg_dir: Path) -> None:
    """Create minimal valid config files."""
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / ".env").write_text("")
    (cfg_dir / "config.toml").write_text(
        "[paths]\n"
        'output_dir = "./downloads"\n'
        'temp_dir = "./tmp"\n'
    )


def test_backup_creation():
    """Test that backup is created and overwrites previous backup (single-latest policy)."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_minimal_config(cfg_dir)
        
        config = ConfigManager(env_path=str(cfg_dir / ".env"))
        
        # Create first backup
        backup1 = config.create_backup()
        assert backup1 is not None
        assert (backup1 / "config.toml").exists()
        
        # Modify config
        config.set("paths.output_dir", "/new/path")
        
        # Create second backup (should overwrite)
        backup2 = config.create_backup()
        assert backup2 == backup1  # Same directory
        
        # Verify latest backup has new value
        backup_toml = read_toml(backup2 / "config.toml")
        assert backup_toml.get("paths", {}).get("output_dir") == "/new/path"


def test_restore_from_backup():
    """Test restore from backup functionality."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_minimal_config(cfg_dir)
        
        config = ConfigManager(env_path=str(cfg_dir / ".env"))
        
        # Set initial value
        config.set("paths.output_dir", "/original/path")
        
        # Create backup
        backup_dir = config.create_backup()
        assert backup_dir is not None
        
        # Modify config
        config.set("paths.output_dir", "/modified/path")
        
        # Restore
        restored = config.restore_from_backup()
        assert restored is True
        
        # Verify restored value
        assert config.get("paths.output_dir") == "/original/path"


def test_restore_without_backup():
    """Test restore when no backup exists."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_minimal_config(cfg_dir)
        
        config = ConfigManager(env_path=str(cfg_dir / ".env"))
        
        restored = config.restore_from_backup()
        assert restored is False


def test_has_backup():
    """Test backup existence check."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_minimal_config(cfg_dir)
        
        config = ConfigManager(env_path=str(cfg_dir / ".env"))
        
        assert config.has_backup() is False
        
        config.create_backup()
        assert config.has_backup() is True


def test_doctor_detects_missing_toml():
    """Test that doctor detects missing config.toml."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / ".env").write_text("")
        
        config = ConfigManager(env_path=str(cfg_dir / ".env"))
        
        # Doctor should detect missing toml
        assert not config.check_toml_file_exists()


def test_doctor_detects_invalid_toml():
    """Test that doctor detects corrupted/invalid TOML."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_minimal_config(cfg_dir)
        
        # Write invalid TOML
        (cfg_dir / "config.toml").write_text("invalid toml content [unclosed")
        
        config = ConfigManager(env_path=str(cfg_dir / ".env"))
        
        # Should still detect file exists
        assert config.check_toml_file_exists()
        
        # But reading should fail
        try:
            read_toml(config.toml_path)
            assert False, "Should have raised exception"
        except Exception:
            pass  # Expected


def test_arcane_terms_config_precedence():
    """
    Regression test: config.toml product.arcane_terms should take precedence over env.
    
    PRD6 regression prevention: ensure ConfigManager.get() is used, not os.getenv().
    """
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_minimal_config(cfg_dir)
        
        # Set in config.toml
        config = ConfigManager(env_path=str(cfg_dir / ".env"))
        config.set("product.arcane_terms", "false")
        
        # Set env var (should be ignored)
        env_backup = os.environ.get("ARCANE_TERMS")
        try:
            os.environ["ARCANE_TERMS"] = "true"
            
            # Should read from config.toml, not env
            value = config.get("product.arcane_terms")
            assert value == "false"
        finally:
            if env_backup is not None:
                os.environ["ARCANE_TERMS"] = env_backup
            elif "ARCANE_TERMS" in os.environ:
                del os.environ["ARCANE_TERMS"]


def test_backup_includes_both_files():
    """Test that backup includes both config.toml and .env."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_minimal_config(cfg_dir)
        
        # Add content to .env
        (cfg_dir / ".env").write_text("TEST_KEY=test_value\n")
        
        config = ConfigManager(env_path=str(cfg_dir / ".env"))
        backup_dir = config.create_backup()
        
        assert backup_dir is not None
        assert (backup_dir / "config.toml").exists()
        assert (backup_dir / ".env").exists()
        
        # Verify content
        backup_env_content = (backup_dir / ".env").read_text()
        assert "TEST_KEY=test_value" in backup_env_content
