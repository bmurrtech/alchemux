"""
Structured logging with DEBUG/INFO levels via LOG_LEVEL env var.
Includes yt-dlp logger adapter for verbose output.
Uses RichHandler for clean, styled log output that doesn't interfere with progress bars.
"""

import os
import logging
from typing import Optional

try:
    from rich.logging import RichHandler
    from rich.console import Console

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


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
    name: str = __name__, console: Optional[Console] = None, verbose: bool = False
) -> logging.Logger:
    """
    Set up structured logging with LOG_LEVEL env var support.
    Uses RichHandler for clean, styled output that doesn't interfere with progress bars.

    Args:
        name: Logger name (typically __name__)
        console: Optional Rich Console instance (creates new one if not provided)
        verbose: If True, show logs even in default mode. If False, only show in debug mode.

    Returns:
        Configured logger instance
    """
    log_level_str = os.getenv("LOG_LEVEL", "info").lower()
    verbose_mode = verbose or os.getenv("VERBOSE", "").lower() in ("1", "true", "yes")

    # In default mode (not verbose), only show WARNING and above unless verbose is True
    if not verbose_mode and log_level_str != "debug":
        log_level = logging.WARNING
    else:
        log_level = logging.DEBUG if log_level_str == "debug" else logging.INFO

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Avoid adding multiple handlers if logger already configured
    if not logger.handlers:
        if HAS_RICH and console is not None:
            # Use RichHandler for styled, clean output
            handler = RichHandler(
                console=console,
                rich_tracebacks=True,
                show_time=False,  # No timestamps in default mode
                show_level=True,
                show_path=False,
                markup=True,
            )
        elif HAS_RICH:
            # Create console for RichHandler if not provided
            rich_console = Console(stderr=True)
            handler = RichHandler(
                console=rich_console,
                rich_tracebacks=True,
                show_time=False,
                show_level=True,
                show_path=False,
                markup=True,
            )
        else:
            # Fallback to standard handler if Rich not available
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(message)s", datefmt="[%X]")
            handler.setFormatter(formatter)

        handler.setLevel(log_level)
        logger.addHandler(handler)

    # Suppress yt-dlp warnings in INFO mode by filtering them
    if log_level_str != "debug" and not verbose_mode:
        # Filter out WARNING level messages from yt-dlp in INFO mode
        def filter_warnings(record: logging.LogRecord) -> bool:
            # Allow warnings from our own code, but suppress yt-dlp warnings
            if record.levelno == logging.WARNING:
                # Check if it's from yt-dlp (usually has [youtube] or similar tags)
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
        YTDLLogger instance if LOG_LEVEL=debug, None otherwise
    """
    log_level_str = os.getenv("LOG_LEVEL", "info").lower()
    if log_level_str == "debug":
        return YTDLLogger(logger)
    return None


# Module-level logger
_logger = setup_logger(__name__)
