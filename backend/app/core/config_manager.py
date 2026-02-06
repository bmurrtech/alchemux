"""
Secure .env file management with chmod 600 permissions, validation, and auto-update.
Supports portable binaries with hybrid config location detection.
Uses platformdirs for cross-platform user config paths.
"""

import os
import stat
import sys
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv, set_key, find_dotenv

# platformdirs for cross-platform config paths
# Reference: https://platformdirs.readthedocs.io/en/latest/api.html
try:
    from platformdirs import user_config_path, user_downloads_path

    PLATFORMDIRS_AVAILABLE = True
except ImportError:
    PLATFORMDIRS_AVAILABLE = False

from .logger import setup_logger
from .toml_config import (
    get_toml_path,
    read_toml,
    write_toml,
    get_nested_value,
    set_nested_value,
)

logger = setup_logger(__name__)

# App identity for platformdirs
APP_NAME = "Alchemux"
APP_AUTHOR = False  # Don't use author subdirectory


def get_user_config_dir() -> Path:
    """
    Get platform-specific user config directory using platformdirs.

    Returns:
        - macOS: ~/Library/Application Support/Alchemux/
        - Linux: ~/.config/alchemux/ (or $XDG_CONFIG_HOME/alchemux/)
        - Windows: %APPDATA%\\Alchemux\\ (Roaming)

    Reference: https://platformdirs.readthedocs.io/en/latest/api.html#user-config-directory
    """
    if PLATFORMDIRS_AVAILABLE:
        # roaming=True for Windows to use %APPDATA% (Roaming) instead of %LOCALAPPDATA%
        config_dir = user_config_path(
            appname=APP_NAME, appauthor=APP_AUTHOR, roaming=True, ensure_exists=True
        )
        return config_dir

    # Fallback if platformdirs not available
    if sys.platform == "darwin":  # macOS
        config_dir = Path.home() / "Library" / "Application Support" / "Alchemux"
    elif sys.platform == "win32":  # Windows - use APPDATA (Roaming)
        config_dir = (
            Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "Alchemux"
        )
    else:  # Linux and others - XDG compliant
        xdg_config = os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")
        config_dir = Path(xdg_config) / "alchemux"

    # Create directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_default_output_dir() -> Path:
    """
    Get platform-specific default output directory.

    Returns:
        - All platforms: ~/Downloads/Alchemux/ (user-friendly default)

    Reference: https://platformdirs.readthedocs.io/en/latest/api.html#user-downloads-directory
    """
    if PLATFORMDIRS_AVAILABLE:
        downloads = user_downloads_path()
        output_dir = downloads / "Alchemux"
    else:
        output_dir = Path.home() / "Downloads" / "Alchemux"

    return output_dir


def get_pointer_file_path() -> Path:
    """
    Get path to config pointer file (stable location).

    The pointer file stores the absolute path to the active config directory,
    allowing users to relocate config without breaking the app.

    Returns:
        Path to pointer file in default OS config directory
    """
    default_config = get_user_config_dir()
    return default_config / "config_path.txt"


def read_config_pointer() -> Optional[Path]:
    """
    Read config directory path from pointer file.

    Returns:
        Path to active config directory, or None if pointer doesn't exist or is invalid
    """
    pointer_file = get_pointer_file_path()
    if pointer_file.exists():
        try:
            pointer_content = pointer_file.read_text().strip()
            if pointer_content:
                pointer_path = Path(pointer_content)
                if pointer_path.exists():
                    return pointer_path
                else:
                    logger.warning(
                        f"Config pointer target does not exist: {pointer_path}"
                    )
        except Exception as e:
            logger.warning(f"Could not read config pointer: {e}")
    return None


def write_config_pointer(config_dir: Path) -> None:
    """
    Write config directory path to pointer file.

    Args:
        config_dir: Path to active config directory
    """
    pointer_file = get_pointer_file_path()
    try:
        pointer_file.parent.mkdir(parents=True, exist_ok=True)
        pointer_file.write_text(str(config_dir.resolve()))
        logger.debug(f"Wrote config pointer: {pointer_file} -> {config_dir}")
    except Exception as e:
        logger.warning(f"Could not write config pointer: {e}")


def get_config_location() -> Path:
    """
    Determine config file location with priority order.

    Priority:
    1. CLI flag --config-dir <path> (via ALCHEMUX_CONFIG_DIR env var)
    2. Environment var ALCHEMUX_CONFIG_DIR
    3. Pointer file in default OS config dir
    4. If packaged binary AND .env exists next to binary in writable location -> portable mode
    5. Default OS config directory (via platformdirs)

    For source development: prioritize existing .env, then project root

    Returns:
        Path to .env file location
    """
    # Priority 1 & 2: Environment variable (set by CLI flag or directly)
    env_config_dir = os.getenv("ALCHEMUX_CONFIG_DIR")
    if env_config_dir:
        config_path = Path(env_config_dir) / ".env"
        logger.debug(f"Using config from ALCHEMUX_CONFIG_DIR: {config_path}")
        return config_path

    # Priority 3: Pointer file
    pointer_config = read_config_pointer()
    if pointer_config:
        config_path = pointer_config / ".env"
        logger.debug(f"Using config from pointer file: {config_path}")
        return config_path

    # Detect if running as packaged binary
    if getattr(sys, "frozen", False):
        # Running as PyInstaller binary: default to same path as binary
        binary_path = Path(sys.executable)
        binary_dir = binary_path.parent
        if os.access(binary_dir, os.W_OK):
            portable_env = binary_dir / ".env"
            logger.debug(
                f"Using config next to binary (default for portable): {portable_env}"
            )
            return portable_env
        # Fallback if binary dir not writable
        user_config = get_user_config_dir() / ".env"
        logger.debug(
            f"Binary dir not writable, using OS config directory: {user_config}"
        )
        return user_config
    else:
        # Running from source: prioritize existing .env, then project root, then CWD
        # First, try to find existing .env file (searches upward from CWD)
        env_file = find_dotenv()
        if env_file:
            env_path = Path(env_file)
            # If .env exists, use its location
            if env_path.exists():
                logger.debug(f"Running from source, found existing .env: {env_path}")
                return env_path
            else:
                # find_dotenv() found a path but file doesn't exist - use its parent directory
                logger.debug(
                    f"Running from source, using .env location from find_dotenv: {env_path}"
                )
                return env_path

        # No .env found - check if we're in a project root (has env.example)
        cwd = Path.cwd()
        env_example_in_cwd = cwd / "env.example"
        if env_example_in_cwd.exists():
            logger.debug(
                f"Running from source, using project root (has env.example): {cwd / '.env'}"
            )
            return cwd / ".env"

        # Default to current working directory
        logger.debug(f"Running from source, using CWD: {cwd / '.env'}")
        return cwd / ".env"


class ConfigManager:
    """Manages .env file with secure permissions and validation."""

    def __init__(self, env_path: Optional[str] = None):
        """
        Initialize ConfigManager.

        Args:
            env_path: Path to .env file (if None, uses smart detection for portable binaries)
        """
        # Ensure env_path is a string (handle Typer OptionInfo objects)
        if env_path is not None:
            # Check if it's an OptionInfo object (when option not provided)
            if hasattr(env_path, "__class__") and "OptionInfo" in str(type(env_path)):
                # OptionInfo object means option was not provided, treat as None
                self.env_path = get_config_location()
            elif isinstance(env_path, str):
                # Check if string is OptionInfo representation
                if env_path.startswith("<typer.models.OptionInfo"):
                    # String representation of OptionInfo, treat as None
                    self.env_path = get_config_location()
                elif env_path.strip():
                    # Valid string path
                    self.env_path = Path(env_path)
                else:
                    # Empty string treated as None
                    self.env_path = get_config_location()
            else:
                # Try to convert to string, but check result
                env_path_str = str(env_path)
                if env_path_str.startswith("<typer.models.OptionInfo"):
                    # Conversion resulted in OptionInfo representation, treat as None
                    self.env_path = get_config_location()
                elif env_path_str.strip():
                    self.env_path = Path(env_path_str)
                else:
                    # Empty string treated as None
                    self.env_path = get_config_location()
        else:
            # Smart detection for portable binaries
            self.env_path = get_config_location()

        # For env.example, try binary directory first, then user config, then .env parent
        if getattr(sys, "frozen", False):
            binary_dir = Path(sys.executable).parent
            self.env_example_path = binary_dir / "env.example"
            if not self.env_example_path.exists():
                self.env_example_path = get_user_config_dir() / "env.example"
        else:
            # Running from source: env.example should be in same directory as .env
            # If .env is in repo root, env.example should be there too
            self.env_example_path = self.env_path.parent / "env.example"
            # Fallback: also check current working directory (for cases where .env is in subdirectory)
            if not self.env_example_path.exists():
                cwd_example = Path.cwd() / "env.example"
                if cwd_example.exists():
                    self.env_example_path = cwd_example

        self._ensure_secure_permissions()
        load_dotenv(self.env_path)

        # Initialize TOML config path
        self.toml_path = get_toml_path(self.env_path)
        self.toml_example_path = self.toml_path.parent / "config.toml.example"
        self._toml_cache = None

    def _ensure_secure_permissions(self) -> None:
        """Ensure .env file has secure permissions (chmod 600 on Unix, user-only on Windows)."""
        if not self.env_path.exists():
            return

        try:
            if os.name != "nt":  # Unix-like systems
                # Set to 600 (read/write for owner only)
                os.chmod(self.env_path, stat.S_IRUSR | stat.S_IWUSR)
                logger.debug(f"Set secure permissions on {self.env_path}")
        except OSError as e:
            logger.warning(f"Could not set secure permissions on {self.env_path}: {e}")

    def _load_toml_cache(self) -> Dict[str, Any]:
        """Load TOML config into cache."""
        if self._toml_cache is None:
            self._toml_cache = read_toml(self.toml_path)
        return self._toml_cache

    def _is_secret_key(self, key: str) -> bool:
        """
        Determine if a key should be stored in .env (secrets) vs config.toml.

        Args:
            key: Configuration key

        Returns:
            True if key is a secret and should go in .env
        """
        secret_patterns = [
            "KEY",
            "SECRET",
            "TOKEN",
            "PASSWORD",
            "CREDENTIAL",
            "COOKIE",
            "OAUTH",
            "SA_KEY",
            "ACCESS_KEY",
            "SECRET_KEY",
        ]
        key_upper = key.upper()
        return any(pattern in key_upper for pattern in secret_patterns)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get configuration value from config.toml (non-secrets) or .env (secrets).

        Priority:
        1. For secrets: .env file
        2. For non-secrets: config.toml (using dot notation), then .env fallback

        Args:
            key: Configuration key (supports dot notation for TOML, e.g., "audio.format")
            default: Default value if not set

        Returns:
            Value from config.toml or .env, or default
        """
        # Check if it's a secret key (always use .env)
        if self._is_secret_key(key):
            value = os.getenv(key, default)
            logger.debug(f"Config get (secret): {key} = ***")
            return value

        # For non-secrets, try TOML first (supports dot notation)
        toml_config = self._load_toml_cache()
        if toml_config:
            toml_value = get_nested_value(toml_config, key)
            if toml_value is not None:
                # Convert to string for consistency
                value = (
                    str(toml_value) if not isinstance(toml_value, str) else toml_value
                )
                logger.debug(f"Config get (toml): {key} = {value}")
                return value

        # Fallback to .env
        value = os.getenv(key, default)
        logger.debug(
            f"Config get (env): {key} = {'***' if 'key' in key.lower() or 'secret' in key.lower() else value}"
        )
        return value

    def get_list(self, key: str, default: Optional[list] = None) -> list:
        """
        Get a list value from config.toml (e.g. media.audio.enabled_formats).
        Returns the raw list; does not convert to string. Use for enabled_formats etc.
        """
        if default is None:
            default = []
        toml_config = self._load_toml_cache()
        if not toml_config:
            return list(default) if default is not None else []
        raw = get_nested_value(toml_config, key)
        if isinstance(raw, list):
            return list(raw)
        return list(default) if default is not None else []

    def _create_env_from_example(self) -> None:
        """
        Create .env file from env.example by copying the full file.
        Ensures required variables are set if missing.

        Raises:
            IOError: If file creation fails (permission issues, etc.)
        """
        try:
            # Ensure parent directory exists
            self.env_path.parent.mkdir(parents=True, exist_ok=True)

            if not self.env_example_path.exists():
                # Create minimal .env with same placeholder keys as env.example (secrets only)
                with open(self.env_path, "w") as f:
                    f.write(
                        "# Alchemux .env (secrets only). Non-secret settings go in config.toml.\n"
                    )
                    f.write("# OAUTH\nOAUTH_CLIENT_ID=\nOAUTH_CLIENT_SECRET=\n")
                    f.write("# GCP\nGCP_SA_KEY_BASE64=\n")
                    f.write("# S3\nS3_ACCESS_KEY=\nS3_SECRET_KEY=\n")
                self._ensure_secure_permissions()
                logger.info(f"Created minimal .env file at {self.env_path}")
                return

            logger.info(f"Creating .env from {self.env_example_path}")

            # Copy the full example file
            import shutil

            shutil.copy2(self.env_example_path, self.env_path)

            self._ensure_secure_permissions()
            logger.info(
                f"Created .env file at {self.env_path} from {self.env_example_path}"
            )
        except (IOError, OSError, PermissionError) as e:
            logger.error(f"Failed to create .env file at {self.env_path}: {e}")
            raise IOError(
                f"Cannot create .env file: {e}. Check permissions for {self.env_path.parent}"
            )

    def _create_toml_from_example(self) -> None:
        """
        Create config.toml file from config.toml.example.
        Simply copies the example file if it exists, otherwise creates minimal config.
        """
        if not self.toml_example_path.exists():
            # If example doesn't exist, create minimal config.toml
            from .toml_config import write_toml

            minimal_config = {
                "product": {"arcane_terms": True},
                "ui": {"auto_open": True, "plain": False},
                "logging": {"debug": False},
                "eula": {"accepted": False, "accepted_at": "", "acceptance_hash": ""},
                "paths": {"output_dir": "./downloads", "temp_dir": "./tmp"},
                "media": {
                    "audio": {
                        "format": "mp3",
                        "quality": "192k",
                        "sample_rate": 0,
                        "channels": 0,
                    },
                    "video": {"format": "", "codec": "", "restrict_filenames": True},
                },
                "presets": {
                    "flac": {"override": False, "sample_rate": 16000, "channels": 1}
                },
                "network": {"retries": 3},
                "download": {"write_info_json": False},
                "storage": {
                    "destination": "local",
                    "fallback": "local",
                    "keep_local_copy": False,
                },
            }
            try:
                write_toml(self.toml_path, minimal_config)
                logger.info(f"Created minimal config.toml at {self.toml_path}")
            except Exception as e:
                logger.warning(f"Could not create config.toml: {e}")
            return

        # Copy example file to config.toml
        try:
            import shutil

            shutil.copy2(self.toml_example_path, self.toml_path)
            logger.info(f"Created config.toml from {self.toml_example_path}")
        except Exception as e:
            logger.error(f"Error copying config.toml.example to config.toml: {e}")
            raise

    def check_toml_file_exists(self) -> bool:
        """Check if config.toml file exists."""
        return self.toml_path.exists()

    def is_s3_configured(self) -> bool:
        """
        Check if S3 is configured (has required config keys + credentials).

        Returns:
            True if S3 has bucket/endpoint in config.toml and credentials in .env
        """
        # Check for required config keys
        bucket = self.get("storage.s3.bucket")
        _endpoint = self.get("storage.s3.endpoint")

        # S3 requires bucket, endpoint is optional (can be inferred)
        if not bucket:
            return False

        # Check for credentials in .env
        access_key = self.get("S3_ACCESS_KEY")
        secret_key = self.get("S3_SECRET_KEY")

        return bool(access_key and secret_key)

    def is_gcp_configured(self) -> bool:
        """
        Check if GCP is configured (has required config keys + credentials).

        Returns:
            True if GCP has bucket in config.toml and credentials in .env
        """
        # Check for required config keys
        bucket = self.get("storage.gcp.bucket")

        if not bucket:
            return False

        # Check for credentials in .env
        sa_key = self.get("GCP_SA_KEY_BASE64")

        return bool(sa_key)

    def get_storage_destination(self) -> str:
        """
        Get the configured storage destination.

        Returns:
            Storage destination: "local", "s3", or "gcp"
        """
        dest = self.get("storage.destination", "local")
        if dest not in ("local", "s3", "gcp"):
            return "local"
        return dest

    def set(self, key: str, value: str, update_env: bool = True) -> None:
        """
        Set configuration value in config.toml (non-secrets) or .env (secrets).

        Args:
            key: Configuration key (supports dot notation for TOML, e.g., "audio.format")
            value: Value to set
            update_env: Also update os.environ (default: True)
        """
        # Check if it's a secret key (always use .env)
        if self._is_secret_key(key):
            if not self.env_path.exists():
                # Create .env from example if it exists
                self._create_env_from_example()

            # Update .env file
            set_key(str(self.env_path), key, value)
            self._ensure_secure_permissions()

            # Update os.environ if requested
            if update_env:
                os.environ[key] = value

            logger.debug(f"Config set (secret): {key} = ***")
            return

        # For non-secrets, write to config.toml
        toml_config = self._load_toml_cache()
        set_nested_value(toml_config, key, value)

        # Write TOML file
        try:
            write_toml(self.toml_path, toml_config)
            # Invalidate cache
            self._toml_cache = None
            logger.debug(f"Config set (toml): {key} = {value}")
        except Exception as e:
            logger.error(f"Failed to write to config.toml: {e}")
            # Fallback to .env if TOML write fails
            if not self.env_path.exists():
                self._create_env_from_example()
            set_key(str(self.env_path), key, value)
            self._ensure_secure_permissions()
            logger.debug(f"Config set (env fallback): {key} = {value}")

        # Update os.environ if requested
        if update_env:
            os.environ[key] = value

    def validate_required(self, required_vars: list[str]) -> tuple[bool, list[str]]:
        """
        Validate that required environment variables are set.

        Args:
            required_vars: List of required variable names

        Returns:
            Tuple of (is_valid, missing_vars)
        """
        missing = []
        for var in required_vars:
            value = self.get(var)
            if not value or value.strip() == "":
                missing.append(var)

        if missing:
            logger.warning(f"Missing required configuration variables: {missing}")
            return False, missing

        return True, []

    def check_env_file_exists(self) -> bool:
        """Check if .env file exists."""
        return self.env_path.exists()

    def get_env_file_error_message(self) -> str:
        """
        Get helpful error message if .env file is missing or incomplete.

        Returns:
            Error message with remediation steps
        """
        if not self.env_path.exists():
            return f"""❌ Configuration file (.env) not found.

To set up:
1. Copy the template: cp env.example .env
2. Edit .env and set required variables
3. Or run setup wizard: alchemux setup

Expected location: {self.env_path}"""

        # Check for required configuration (paths.output_dir in config.toml or DOWNLOAD_PATH in .env)
        output_dir = self.get("paths.output_dir") or self.get("DOWNLOAD_PATH")
        if not output_dir or not output_dir.strip():
            return """❌ Missing required configuration: paths.output_dir

To fix:
1. Run setup wizard: alchemux setup
2. Or set manually: alchemux paths set <path>
3. Or edit config.toml and set paths.output_dir = "./downloads\""""

        return ""

    def update_download_path(self, path: str) -> None:
        """
        Update paths.output_dir in config.toml (legacy method for backward compatibility).

        Args:
            path: New output directory path
        """
        # Normalize path
        path = os.path.expanduser(path)
        path = os.path.abspath(path)

        # Create directory if it doesn't exist
        Path(path).mkdir(parents=True, exist_ok=True)

        # Update config.toml (non-secret, so goes to TOML)
        self.set("paths.output_dir", path)
        logger.info(f"Updated paths.output_dir in config.toml to: {path}")

    def create_backup(self) -> Optional[Path]:
        """
        Create a single-latest backup of config files.

        Backups are stored at <config_dir>/.backups/latest/
        This method overwrites any existing backup (single-latest policy).

        Returns:
            Path to backup directory, or None if backup creation failed
        """
        backup_dir = self.env_path.parent / ".backups" / "latest"
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Backup config.toml if it exists
            if self.toml_path.exists():
                shutil.copy2(self.toml_path, backup_dir / "config.toml")
                logger.debug(f"Backed up config.toml to {backup_dir / 'config.toml'}")

            # Backup .env if it exists
            if self.env_path.exists():
                shutil.copy2(self.env_path, backup_dir / ".env")
                logger.debug(f"Backed up .env to {backup_dir / '.env'}")

            logger.info(f"Created backup at {backup_dir}")
            return backup_dir
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def restore_from_backup(self) -> bool:
        """
        Restore config files from the latest backup.

        Returns:
            True if restore succeeded, False otherwise
        """
        backup_dir = self.env_path.parent / ".backups" / "latest"

        if not backup_dir.exists():
            logger.warning("No backup directory found")
            return False

        try:
            # Restore config.toml if backup exists
            backup_toml = backup_dir / "config.toml"
            if backup_toml.exists():
                shutil.copy2(backup_toml, self.toml_path)
                logger.info("Restored config.toml from backup")

            # Restore .env if backup exists
            backup_env = backup_dir / ".env"
            if backup_env.exists():
                shutil.copy2(backup_env, self.env_path)
                self._ensure_secure_permissions()
                logger.info("Restored .env from backup")

            # Invalidate cache to force reload
            self._toml_cache = None
            load_dotenv(self.env_path)

            logger.info(f"Restored config from backup at {backup_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False

    def has_backup(self) -> bool:
        """
        Check if a backup exists.

        Returns:
            True if backup directory exists and contains at least one file
        """
        backup_dir = self.env_path.parent / ".backups" / "latest"
        if not backup_dir.exists():
            return False

        # Check if at least one backup file exists
        return (backup_dir / "config.toml").exists() or (backup_dir / ".env").exists()
