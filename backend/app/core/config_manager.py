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
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable value.
        
        Args:
            key: Environment variable name
            default: Default value if not set
            
        Returns:
            Value from .env or environment, or default
        """
        # .env file takes precedence (already loaded by load_dotenv)
        value = os.getenv(key, default)
        logger.debug(f"Config get: {key} = {'***' if 'key' in key.lower() or 'secret' in key.lower() else value}")
        return value
    
    def _create_env_from_example(self) -> None:
        """
        Create .env file from env.example, commenting out optional variables.
        Only DOWNLOAD_PATH, AUTO_OPEN, and ARCANE_TERMS are uncommented by default with default values.
        """
        if not self.env_example_path.exists():
            # Create empty .env file with minimal required vars
            with open(self.env_path, 'w') as f:
                f.write("DOWNLOAD_PATH=./downloads\n")
                f.write("AUTO_OPEN=true\n")
                f.write("ARCANE_TERMS=true\n")
            self._ensure_secure_permissions()
            return
        
        logger.info(f"Creating .env from {self.env_example_path}")
        
        # Required variables with default values
        required_defaults = {
            "DOWNLOAD_PATH": "./downloads",
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
    
    def set(self, key: str, value: str, update_env: bool = True) -> None:
        """
        Set environment variable in .env file and optionally update os.environ.
        
        Args:
            key: Environment variable name
            value: Value to set
            update_env: Also update os.environ (default: True)
        """
        if not self.env_path.exists():
            # Create .env from example if it exists
            self._create_env_from_example()
        
        # Update .env file
        set_key(str(self.env_path), key, value)
        self._ensure_secure_permissions()
        
        # Update os.environ if requested
        if update_env:
            os.environ[key] = value
        
        logger.debug(f"Config set: {key} = {'***' if 'key' in key.lower() or 'secret' in key.lower() else value}")
    
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
3. Or run setup wizard: amx --setup (or alchemux --setup)

Expected location: {self.env_path}"""
        
        # Check for required variables
        required = ["DOWNLOAD_PATH"]
        is_valid, missing = self.validate_required(required)
        
        if not is_valid:
            return f"""❌ Missing required configuration: {', '.join(missing)}

To fix:
1. Edit {self.env_path} and set {missing[0]}=./downloads
2. Or run setup wizard: amx --setup (or alchemux --setup)"""
        
        return ""
    
    def update_download_path(self, path: str) -> None:
        """
        Update DOWNLOAD_PATH in .env file (called when --save-path flag is used).
        
        Args:
            path: New download path
        """
        # Normalize path
        path = os.path.expanduser(path)
        path = os.path.abspath(path)
        
        # Create directory if it doesn't exist
        Path(path).mkdir(parents=True, exist_ok=True)
        
        # Update .env
        self.set("DOWNLOAD_PATH", path)
        logger.info(f"Updated DOWNLOAD_PATH in .env to: {path}")

