"""
Secure .env file management with chmod 600 permissions, validation, and auto-update.
"""
import os
import stat
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv, set_key, find_dotenv

from .logger import setup_logger

logger = setup_logger(__name__)


class ConfigManager:
    """Manages .env file with secure permissions and validation."""
    
    def __init__(self, env_path: Optional[str] = None):
        """
        Initialize ConfigManager.
        
        Args:
            env_path: Path to .env file (defaults to finding .env in current/project root)
        """
        if env_path:
            self.env_path = Path(env_path)
        else:
            # Try to find .env file
            env_file = find_dotenv()
            if env_file:
                self.env_path = Path(env_file)
            else:
                # Default to .env in current working directory
                self.env_path = Path.cwd() / ".env"
        
        self.env_example_path = self.env_path.parent / "env.example"
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

