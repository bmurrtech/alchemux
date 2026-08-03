"""
Structured logging with LOG_LEVEL / config.toml support.
Includes yt-dlp logger adapter for verbose output.
Uses RichHandler for clean, styled log output that doesn't interfere with progress bars.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Optional

try:
    from rich.logging import RichHandler
    from rich.console import Console

    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Console = None  # type: ignore[misc, assignment]

if TYPE_CHECKING:
    from rich.console import Console

# Canonical level → accepted aliases (lowercase)
LEVEL_ALIASES: dict[str, frozenset[str]] = {
    "quiet": frozenset({"quiet", "q", "silent", "error"}),
    "warning": frozenset({"warning", "warn", "default"}),
    "info": frozenset({"info", "i", "normal"}),
    "verbose": frozenset({"verbose", "v"}),
    "debug": frozenset({"debug", "d", "trace"}),
}

CANONICAL_LEVELS = ("quiet", "warning", "info", "verbose", "debug")


def normalize_log_level(value: Any, default: str = "warning") -> str:
    """
    Normalize a config/env log level string (or bool) to a canonical level name.

    Accepts aliases listed in LEVEL_ALIASES. Unknown values fall back to default.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return "debug" if value else default
    raw = str(value).strip().lower()
    if not raw:
        return default
    # Boolean-ish strings used historically for logging.debug
    if raw in ("true", "1", "yes", "on"):
        return "debug"
    if raw in ("false", "0", "no", "off"):
        return default
    for canonical, aliases in LEVEL_ALIASES.items():
        if raw in aliases:
            return canonical
    return default


def resolve_config_log_level(
    *,
    level: Any = None,
    debug: Any = None,
    verbose: Any = None,
    default: str = "warning",
) -> str:
    """
    Resolve effective level from config keys.

    Precedence: logging.debug=true → debug; logging.verbose=true → verbose;
    else logging.level (with aliases); else default.
    """

    def _truthy(val: Any) -> bool:
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        return str(val).strip().lower() in ("true", "1", "yes", "on")

    if _truthy(debug):
        return "debug"
    if _truthy(verbose):
        return "verbose"
    if level is not None and str(level).strip() != "":
        return normalize_log_level(level, default=default)
    return default


def apply_log_level_to_environ(level: str) -> None:
    """
    Mirror canonical level into process env for setup_logger / yt-dlp / is_debug_logging.

    Does not override an explicit LOG_LEVEL already set by CLI flags.
    """
    canonical = normalize_log_level(level)
    if os.getenv("LOG_LEVEL"):
        # CLI / caller already set level for this run
        return
    if canonical == "debug":
        os.environ["LOG_LEVEL"] = "debug"
        os.environ.setdefault("ALCHEMUX_DEBUG", "true")
    elif canonical == "verbose":
        os.environ["LOG_LEVEL"] = "verbose"
        os.environ["VERBOSE"] = "true"
    elif canonical == "info":
        os.environ["LOG_LEVEL"] = "info"
    elif canonical == "quiet":
        os.environ["LOG_LEVEL"] = "quiet"
    else:
        # warning (default UX): WARNING+ on console without debug noise
        os.environ["LOG_LEVEL"] = "warning"


def apply_logging_config(config: Any) -> str:
    """
    Read [logging] from ConfigManager-like object and apply to environ.

    Returns the canonical level applied (or already present via env).
    """
    try:
        level = config.get("logging.level")
        debug = config.get("logging.debug")
        verbose = config.get("logging.verbose")
    except Exception:
        level = debug = verbose = None

    # If CLI already forced debug, honor that
    existing = os.getenv("LOG_LEVEL", "").strip().lower()
    if existing in LEVEL_ALIASES["debug"] or existing == "debug":
        return "debug"
    if os.getenv("ALCHEMUX_DEBUG", "").lower() in ("1", "true", "yes"):
        return "debug"
    if os.getenv("VERBOSE", "").lower() in ("1", "true", "yes"):
        if existing in LEVEL_ALIASES["debug"]:
            return "debug"
        return "verbose"

    canonical = resolve_config_log_level(level=level, debug=debug, verbose=verbose)
    apply_log_level_to_environ(canonical)
    return canonical


def is_debug_logging() -> bool:
    """True when LOG_LEVEL resolves to debug or ALCHEMUX_DEBUG is set."""
    level = normalize_log_level(os.getenv("LOG_LEVEL", ""), default="")
    if level == "debug":
        return True
    if os.getenv("ALCHEMUX_DEBUG", "").lower() in ("1", "true", "yes"):
        return True
    return False


def is_verbose_logging() -> bool:
    """True for verbose or debug modes (show more than WARNING-only default)."""
    if is_debug_logging():
        return True
    if os.getenv("VERBOSE", "").lower() in ("1", "true", "yes"):
        return True
    level = normalize_log_level(os.getenv("LOG_LEVEL", "warning"))
    return level in ("info", "verbose", "debug")


def log_error(
    logger: logging.Logger, msg: str, *, exc_info: bool | None = None
) -> None:
    """
    Log an error; include exception traceback only in debug mode.

    Use instead of logger.exception() for handled failures so the default
    terminal UX stays a short message without a Rich traceback wall.
    """
    if exc_info is None:
        exc_info = is_debug_logging()
    logger.error(msg, exc_info=exc_info)


class YTDLLogger:
    """
    Logger adapter so yt-dlp can call .debug/.info/.warning/.error methods
    which will be forwarded to the module logger. Enabled when LOG_LEVEL=debug.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def debug(self, msg: str) -> None:
        self.logger.debug(msg)

    def info(self, msg: str) -> None:
        self.logger.info(msg)

    def warning(self, msg: str) -> None:
        self.logger.warning(msg)

    def error(self, msg: str) -> None:
        self.logger.error(msg)


def setup_logger(
    name: str = __name__,
    console: Optional["Console"] = None,
    verbose: bool = False,
) -> logging.Logger:
    """
    Set up structured logging with LOG_LEVEL env var support.
    Uses RichHandler for styled log output that doesn't interfere with progress bars.

    Args:
        name: Logger name (typically __name__)
        console: Optional Rich Console instance (creates new one if not provided)
        verbose: If True, show logs even in default mode.

    Returns:
        Configured logger instance
    """
    env_raw = os.getenv("LOG_LEVEL", "warning")
    log_level_str = normalize_log_level(env_raw, default="warning")

    verbose_mode = (
        verbose
        or os.getenv("VERBOSE", "").lower() in ("1", "true", "yes")
        or log_level_str == "verbose"
    )
    debug_mode = is_debug_logging() or log_level_str == "debug"

    if debug_mode:
        log_level = logging.DEBUG
    elif verbose_mode or log_level_str == "info":
        log_level = logging.INFO
    elif log_level_str == "quiet":
        log_level = logging.ERROR
    else:
        # warning (default): WARNING and above only
        log_level = logging.WARNING

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    show_tracebacks = debug_mode
    if not logger.handlers:
        if HAS_RICH and console is not None:
            handler = RichHandler(
                console=console,
                rich_tracebacks=show_tracebacks,
                show_time=False,
                show_level=True,
                show_path=False,
                markup=True,
            )
        elif HAS_RICH:
            rich_console = Console(stderr=True)
            handler = RichHandler(
                console=rich_console,
                rich_tracebacks=show_tracebacks,
                show_time=False,
                show_level=True,
                show_path=False,
                markup=True,
            )
        else:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(message)s", datefmt="[%X]")
            handler.setFormatter(formatter)

        handler.setLevel(log_level)
        logger.addHandler(handler)

    if not debug_mode:

        def filter_warnings(record: logging.LogRecord) -> bool:
            if record.levelno == logging.WARNING:
                if (
                    "[youtube]" in record.getMessage()
                    or "yt-dlp" in record.name.lower()
                ):
                    return False
            return True

        logger.addFilter(filter_warnings)

    return logger


def get_ytdl_logger(logger: logging.Logger) -> Optional[YTDLLogger]:
    """
    Get yt-dlp logger adapter if debug logging is enabled.

    Args:
        logger: Base logger instance

    Returns:
        YTDLLogger instance if debug logging is on, None otherwise
    """
    if is_debug_logging():
        return YTDLLogger(logger)
    return None


# Module-level logger
_logger = setup_logger(__name__)
