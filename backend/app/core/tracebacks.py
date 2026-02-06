"""
Rich traceback handler with secret filtering.

Provides global traceback installation and user-friendly error summaries.
Reference: https://rich.readthedocs.io/en/stable/traceback.html

SECURITY NOTE: By default, locals are NOT shown in tracebacks to prevent
accidental exposure of secrets (API keys, tokens, passwords).
To enable locals in debug mode, set ALCHEMUX_TRACEBACK_LOCALS=1 (use with caution).
"""
import os
import sys
from typing import Optional
from rich.console import Console
from rich.traceback import install as install_rich_traceback


def install_traceback_handler(debug: bool = False) -> None:
    """
    Install Rich traceback handler globally.

    Args:
        debug: If True, show full tracebacks.
               If False, show simplified tracebacks.

    SECURITY: Locals are never shown by default, even in debug mode.
    To enable locals display (NOT RECOMMENDED in shared environments):
        export ALCHEMUX_TRACEBACK_LOCALS=1

    Reference: https://rich.readthedocs.io/en/stable/traceback.html
    """
    console = Console(stderr=True)

    # Only show locals if explicitly opted-in via env var
    # This prevents accidental exposure of secrets in variables
    show_locals = os.getenv("ALCHEMUX_TRACEBACK_LOCALS", "").lower() in ("1", "true", "yes")

    if show_locals:
        # Log a warning that locals display is enabled
        console.print(
            "[dim yellow]Warning: Traceback locals display is enabled. "
            "Secrets may be visible in error output.[/dim yellow]"
        )

    install_rich_traceback(
        console=console,
        show_locals=show_locals,
        locals_max_length=10 if show_locals else 0,
        locals_max_string=80 if show_locals else 0,
        suppress=[],  # Don't suppress any modules
        width=None,   # Use terminal width
        extra_lines=3 if debug else 1,
        theme=None,   # Use default theme
        word_wrap=True,
    )


def print_fracture_summary(
    stage: str,
    error: Exception,
    console: Optional[Console] = None
) -> None:
    """
    Print user-friendly error summary (fracture detected format).

    This provides a clean, non-technical error message for normal mode,
    while full tracebacks are shown in debug mode.

    Args:
        stage: Stage name where error occurred (e.g., "distill", "mux")
        error: The exception that was raised
        console: Optional Console instance (defaults to stderr)
    """
    if console is None:
        console = Console(stderr=True)

    # Get error message, ensuring we don't expose sensitive data
    error_msg = str(error)

    # Basic sanitization - mask anything that looks like a secret
    secret_patterns = ['key=', 'token=', 'password=', 'secret=']
    for pattern in secret_patterns:
        if pattern in error_msg.lower():
            # Find the value after the pattern and mask it
            idx = error_msg.lower().find(pattern)
            end_idx = error_msg.find(' ', idx + len(pattern))
            if end_idx == -1:
                end_idx = len(error_msg)
            error_msg = error_msg[:idx + len(pattern)] + '***' + error_msg[end_idx:]

    console.print(f"[bold red]<x> {stage} | fracture detected[/bold red]")
    console.print(f"[red]    cause: {error_msg}[/red]")

    # Hint for debug mode
    if os.getenv("LOG_LEVEL", "").lower() != "debug":
        console.print("[dim]    run with --debug for full traceback[/dim]")
