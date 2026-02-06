"""
TOML configuration file management.
Handles reading and writing config.toml for non-secret configuration.
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Union

from .logger import setup_logger

logger = setup_logger(__name__)

# Try to import TOML Kit (preserves comments), fallback to stdlib/tomli
try:
    import tomlkit
    TOMLKIT_AVAILABLE = True
except ImportError:
    TOMLKIT_AVAILABLE = False

# Try to import TOML library (prefer tomllib for Python 3.11+, fallback to tomli)
try:
    if sys.version_info >= (3, 11):
        import tomllib
        TOML_READ_AVAILABLE = True
        TOML_READ_FUNC = tomllib.load
    else:
        try:
            import tomli as tomllib
            TOML_READ_AVAILABLE = True
            TOML_READ_FUNC = tomllib.load
        except ImportError:
            TOML_READ_AVAILABLE = False
            TOML_READ_FUNC = None
except ImportError:
    TOML_READ_AVAILABLE = False
    TOML_READ_FUNC = None

# Try to import TOML write library
try:
    import tomli_w
    TOML_WRITE_AVAILABLE = True
    TOML_WRITE_FUNC = tomli_w.dumps
except ImportError:
    TOML_WRITE_AVAILABLE = False
    TOML_WRITE_FUNC = None


def get_toml_path(env_path: Optional[Path] = None) -> Path:
    """
    Get path to config.toml file.

    Args:
        env_path: Path to .env file (config.toml will be in same directory)

    Returns:
        Path to config.toml
    """
    if env_path:
        return env_path.parent / "config.toml"

    # Use same logic as get_config_location for .env
    from .config_manager import get_config_location
    env_location = get_config_location()
    return env_location.parent / "config.toml"


def read_toml(toml_path: Path) -> Dict[str, Any]:
    """
    Read config.toml file.

    Args:
        toml_path: Path to config.toml

    Returns:
        Dictionary of configuration values
    """
    if not toml_path.exists():
        logger.debug(f"config.toml not found at {toml_path}")
        return {}

    # Prefer TOMLKit for comment preservation
    if TOMLKIT_AVAILABLE:
        try:
            with open(toml_path, 'r', encoding='utf-8') as f:
                return tomlkit.load(f)
        except Exception as e:
            logger.warning(f"TOMLKit read failed, falling back: {e}")
            pass

    if not TOML_READ_AVAILABLE:
        logger.warning("TOML read library not available. Install tomli for Python < 3.11")
        return {}

    try:
        with open(toml_path, 'rb') as f:
            return TOML_READ_FUNC(f)
    except Exception as e:
        logger.error(f"Error reading config.toml: {e}")
        return {}


def write_toml(toml_path: Path, config: Dict[str, Any]) -> None:
    """
    Write config.toml file.

    Args:
        toml_path: Path to config.toml
        config: Dictionary of configuration values (nested structure)
    """
    try:
        # Ensure parent directory exists
        toml_path.parent.mkdir(parents=True, exist_ok=True)

        # Prefer TOMLKit for comment preservation
        if TOMLKIT_AVAILABLE:
            with open(toml_path, 'w', encoding='utf-8') as f:
                tomlkit.dump(config, f)
            logger.debug(f"Wrote config.toml to {toml_path} (tomlkit)")
            return

        if not TOML_WRITE_AVAILABLE:
            logger.warning("TOML write library not available. Install tomli-w")
            raise ImportError("tomli-w is required for writing config.toml")

        # Convert dict to TOML string
        toml_content = TOML_WRITE_FUNC(config)

        # Write to file
        with open(toml_path, 'wb') as f:
            f.write(toml_content.encode('utf-8'))

        logger.debug(f"Wrote config.toml to {toml_path}")
    except Exception as e:
        logger.error(f"Error writing config.toml: {e}")
        raise


def get_nested_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get a nested value from config dict using dot notation.

    Args:
        config: Configuration dictionary
        key_path: Dot-separated key path (e.g., "audio.format" or "storage.default")
        default: Default value if key not found

    Returns:
        Value at key path, or default
    """
    keys = key_path.split('.')
    current = config

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


def set_nested_value(config: Dict[str, Any], key_path: str, value: Any) -> None:
    """
    Set a nested value in config dict using dot notation.

    Args:
        config: Configuration dictionary (modified in place)
        key_path: Dot-separated key path (e.g., "audio.format")
        value: Value to set
    """
    keys = key_path.split('.')
    current = config

    # Navigate/create nested structure
    for i, key in enumerate(keys[:-1]):
        if key not in current:
            current[key] = {}
        elif not isinstance(current[key], dict):
            # Convert existing value to dict if needed
            current[key] = {}
        current = current[key]

    # Set final value
    final_key = keys[-1]
    current[final_key] = value
