"""
Secure .env file management with chmod 600 permissions, validation, and auto-update.
Supports portable binaries with hybrid config location detection.
"""
import os
import stat
import sys
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv, set_key, find_dotenv

from .logger import setup_logger
from .toml_config import (
    get_toml_path,
    read_toml,
    write_toml,
    get_nested_value,
    set_nested_value,
)

logger = setup_logger(__name__)


def get_user_config_dir() -> Path:
    """
    Get platform-specific user config directory.
    
    Returns:
        Path to user config directory (created if needed)
    """
    if sys.platform == "darwin":  # macOS
        config_dir = Path.home() / "Library" / "Application Support" / "alchemux"
    elif sys.platform == "win32":  # Windows
        config_dir = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "alchemux"
    else:  # Linux and others
        config_dir = Path.home() / ".config" / "alchemux"
    
    # Create directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_location() -> Path:
    """
    Determine config file location for portable binaries.
    
    Priority:
    1. If binary is in writable location → config next to binary
    2. If binary is in system path → user config directory
    3. Fallback → current working directory (for source/dev)
    
    Returns:
        Path to .env file location
    """
    # Detect if running as packaged binary
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller binary
        binary_path = Path(sys.executable)
        binary_dir = binary_path.parent
        
        # Check if binary directory is writable
        if os.access(binary_dir, os.W_OK):
            # Portable mode: config next to binary
            logger.debug(f"Portable binary detected, using config next to binary: {binary_dir / '.env'}")
            return binary_dir / ".env"
        else:
            # System install: use user config directory
            user_config = get_user_config_dir() / ".env"
            logger.debug(f"System binary detected, using user config: {user_config}")
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
                logger.debug(f"Running from source, using .env location from find_dotenv: {env_path}")
                return env_path
        
        # No .env found - check if we're in a project root (has env.example)
        cwd = Path.cwd()
        env_example_in_cwd = cwd / "env.example"
        if env_example_in_cwd.exists():
            logger.debug(f"Running from source, using project root (has env.example): {cwd / '.env'}")
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
            if hasattr(env_path, '__class__') and 'OptionInfo' in str(type(env_path)):
                # OptionInfo object means option was not provided, treat as None
                self.env_path = get_config_location()
            elif isinstance(env_path, str):
                # Check if string is OptionInfo representation
                if env_path.startswith('<typer.models.OptionInfo'):
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
                if env_path_str.startswith('<typer.models.OptionInfo'):
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
        if getattr(sys, 'frozen', False):
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
            if os.name != 'nt':  # Unix-like systems
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
            'KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'CREDENTIAL',
            'COOKIE', 'OAUTH', 'SA_KEY', 'ACCESS_KEY', 'SECRET_KEY'
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
                value = str(toml_value) if not isinstance(toml_value, str) else toml_value
                logger.debug(f"Config get (toml): {key} = {value}")
                return value
        
        # Fallback to .env
        value = os.getenv(key, default)
        logger.debug(f"Config get (env): {key} = {'***' if 'key' in key.lower() or 'secret' in key.lower() else value}")
        return value
    
    def _create_env_from_example(self) -> None:
        """
        Create .env file from env.example, commenting out optional variables.
        Only minimal required variables are uncommented by default.
        
        Raises:
            IOError: If file creation fails (permission issues, etc.)
        """
        try:
            # Ensure parent directory exists
            self.env_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not self.env_example_path.exists():
                # Create empty .env file with minimal required vars
                with open(self.env_path, 'w') as f:
                    # Note: paths.output_dir should be set in config.toml, not .env
                    # This is kept for backward compatibility only
                    f.write("# DOWNLOAD_PATH is now in config.toml as paths.output_dir\n")
                    f.write("AUTO_OPEN=true\n")
                    f.write("ARCANE_TERMS=true\n")
                self._ensure_secure_permissions()
                logger.info(f"Created minimal .env file at {self.env_path}")
                return
            
            logger.info(f"Creating .env from {self.env_example_path}")
            
            # Required variables with default values
            required_defaults = {
                # DOWNLOAD_PATH moved to config.toml as paths.output_dir
                "AUTO_OPEN": "true",
                "ARCANE_TERMS": "true"
            }
            
            # Read env.example and process it
            with open(self.env_example_path, 'r') as f:
                lines = f.readlines()
            
            # Track which required vars we've written
            written_required = set()
            
            # Write to .env with optional variables commented out
            with open(self.env_path, 'w') as f:
                for line in lines:
                    stripped = line.strip()
                    
                    # Keep comments and empty lines as-is
                    if not stripped or stripped.startswith('#'):
                        f.write(line)
                        continue
                    
                    # Check if this is a variable assignment
                    if '=' in stripped:
                        var_name = stripped.split('=')[0].strip()
                        
                        # If it's a required variable, uncomment it with default value
                        if var_name in required_defaults:
                            # Write with default value (only once)
                            if var_name not in written_required:
                                f.write(f"{var_name}={required_defaults[var_name]}\n")
                                written_required.add(var_name)
                            # Skip the original line (we've written the default)
                            continue
                        else:
                            # Comment out optional variables
                            if not line.strip().startswith('#'):
                                f.write(f"# {line}")
                            else:
                                f.write(line)
                    else:
                        f.write(line)
                
                # Ensure all required vars are written (in case they weren't in example)
                for var_name, default_value in required_defaults.items():
                    if var_name not in written_required:
                        f.write(f"{var_name}={default_value}\n")
            
            self._ensure_secure_permissions()
            logger.info(f"Created .env file at {self.env_path}")
        except (IOError, OSError, PermissionError) as e:
            logger.error(f"Failed to create .env file at {self.env_path}: {e}")
            raise IOError(f"Cannot create .env file: {e}. Check permissions for {self.env_path.parent}")
    
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
                    "audio": {"format": "mp3", "quality": "192k", "sample_rate": 0, "channels": 0},
                    "video": {"format": "", "codec": "", "restrict_filenames": True}
                },
                "presets": {
                    "flac": {"override": False, "sample_rate": 16000, "channels": 1}
                },
                "network": {"retries": 3},
                "storage": {
                    "destination": "local",
                    "fallback": "local",
                    "keep_local_copy": False
                }
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
        endpoint = self.get("storage.s3.endpoint")
        
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
            return f"""❌ Missing required configuration: paths.output_dir

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

