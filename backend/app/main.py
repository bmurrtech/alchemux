#!/usr/bin/env python3
"""
Alchemux - URL to MP3 Converter CLI
Main entry point with Typer CLI and ALCHEMUX stylized output.
"""

import sys
import os
import warnings
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import typer

# Import Rich traceback handler
from app.core.tracebacks import install_traceback_handler, print_fracture_summary


# Suppress google.api_core FutureWarning unless GCP is actually configured
# Check if GCP is configured before suppressing warnings
def should_suppress_gcp_warning() -> bool:
    """Check if GCP warning should be suppressed (i.e., GCP is not configured)."""
    # Check environment variables first (fastest)
    if os.getenv("GCP_STORAGE_BUCKET") or os.getenv("GCP_SA_KEY_BASE64"):
        return False  # GCP is configured, don't suppress

    # Check if --setup gcp was used
    if "--setup" in sys.argv:
        setup_idx = sys.argv.index("--setup")
        if setup_idx + 1 < len(sys.argv) and sys.argv[setup_idx + 1] == "gcp":
            return False  # GCP setup is being run, don't suppress

    # Check if --gcp flag is used
    if "--gcp" in sys.argv or "-gcp" in sys.argv:
        return False  # GCP flag is used, don't suppress

    # Try to load config to check (only if .env might exist)
    try:
        from app.core.config_manager import get_config_location

        config_path = get_config_location()
        if config_path.exists():
            from dotenv import load_dotenv

            load_dotenv(config_path)
            if os.getenv("GCP_STORAGE_BUCKET") or os.getenv("GCP_SA_KEY_BASE64"):
                return False  # GCP is configured in .env
    except Exception:
        pass  # If config loading fails, assume not configured

    # GCP is not configured, suppress warning to debug level
    return True


# Suppress FutureWarning from google.api_core if GCP is not configured
if should_suppress_gcp_warning():
    # Filter FutureWarning from google.api_core - suppress by default, show only in debug mode
    warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")
    # Also capture warnings to logging and filter there
    import logging

    logging.captureWarnings(True)

    # Create a custom filter for google.api_core warnings in the warnings logger
    class GCPWarningFilter(logging.Filter):
        def filter(self, record):
            # Only show in debug mode
            msg = record.getMessage()
            if "google.api_core" in msg or "Python version" in msg:
                return os.getenv("LOG_LEVEL", "").lower() == "debug"
            return True

    # Apply filter to warnings logger
    warnings_logger = logging.getLogger("py.warnings")
    if not any(isinstance(f, GCPWarningFilter) for f in warnings_logger.filters):
        warnings_logger.addFilter(GCPWarningFilter())

from app.cli import app  # noqa: E402
from app.cli.output import ArcaneConsole  # noqa: E402

# Track if banner has been shown (only show once per session)
_banner_shown = False

if __name__ == "__main__":
    # Detect debug mode early for traceback handler
    debug_mode = "--debug" in sys.argv or os.getenv("LOG_LEVEL", "").lower() == "debug"

    # Install Rich traceback handler before anything else
    install_traceback_handler(debug=debug_mode)

    try:
        # Check for "config" with no subcommand: run config wizard and exit
        if "config" in sys.argv:
            config_idx = sys.argv.index("config")
            rest = [
                a for a in sys.argv[config_idx + 1 :] if a and not a.startswith("-")
            ]
            if not rest:
                from app.core.config_manager import ConfigManager
                from app.core.config_wizard import interactive_config_wizard

                plain_mode = "--plain" in sys.argv or os.getenv(
                    "NO_COLOR", ""
                ).lower() in ("1", "true", "yes")
                if (
                    not _banner_shown
                    and os.getenv("ALCHEMUX_SHOW_BANNER", "true").lower() == "true"
                ):
                    if not any(arg in sys.argv for arg in ["--version", "-v"]):
                        console = ArcaneConsole(plain=plain_mode)
                        console.print_banner()
                        _banner_shown = True
                config_manager = ConfigManager()
                if not config_manager.check_toml_file_exists():
                    ArcaneConsole(plain=plain_mode).print_fracture(
                        "config", "config.toml not found. Run 'alchemux setup' first."
                    )
                    sys.exit(1)
                try:
                    success = interactive_config_wizard(config_manager)
                    sys.exit(0 if success else 1)
                except KeyboardInterrupt:
                    sys.exit(130)
                except Exception as e:
                    if not debug_mode:
                        print_fracture_summary("config", e)
                    sys.exit(1)

        # Check for "setup" command BEFORE Typer processes arguments
        # This prevents "setup" from being matched to the url argument in the callback
        if "setup" in sys.argv:
            setup_idx = sys.argv.index("setup")
            # Check if there's a target after "setup" (like "gcp" or "s3")
            if setup_idx + 1 < len(sys.argv) and not sys.argv[setup_idx + 1].startswith(
                "-"
            ):
                target = sys.argv[setup_idx + 1]
            else:
                target = None

            # Import and run setup directly, bypassing Typer's argument parsing
            from app.cli.commands.setup import setup as setup_cmd

            plain_mode = "--plain" in sys.argv or os.getenv("NO_COLOR", "").lower() in (
                "1",
                "true",
                "yes",
            )

            # Print banner if needed
            if (
                not _banner_shown
                and os.getenv("ALCHEMUX_SHOW_BANNER", "true").lower() == "true"
            ):
                should_skip = any(arg in sys.argv for arg in ["--version", "-v"])
                if not should_skip:
                    console = ArcaneConsole(plain=plain_mode)
                    console.print_banner()
                    _banner_shown = True

            # Run setup command directly (pass reset=False so Typer Option default
            # is not used when called programmatically)
            try:
                setup_cmd(target=target, plain=plain_mode, reset=False)
                sys.exit(0)
            except SystemExit:
                # Re-raise SystemExit to preserve exit code
                raise
            except typer.Exit as e:
                # Typer/Click Exit: exit with code, do not treat as fracture
                sys.exit(getattr(e, "exit_code", 0))
            except Exception as e:
                # In debug mode, the Rich traceback handler shows full trace
                # In normal mode, show friendly summary
                if not debug_mode:
                    print_fracture_summary("setup", e)
                sys.exit(1)

        # Print banner only once on initial startup (not for every command)
        if (
            not _banner_shown
            and os.getenv("ALCHEMUX_SHOW_BANNER", "true").lower() == "true"
        ):
            # Skip banner only for --version flag (keep it for --help)
            should_skip = any(arg in sys.argv for arg in ["--version", "-v"])
            if not should_skip:
                # Check for --plain flag early
                plain_mode = "--plain" in sys.argv or os.getenv(
                    "NO_COLOR", ""
                ).lower() in ("1", "true", "yes")
                console = ArcaneConsole(plain=plain_mode)
                console.print_banner()
                _banner_shown = True

        # Run Typer app
        app()
    except KeyboardInterrupt:
        from rich.console import Console

        Console(stderr=True).print("\n\n[dim]Interrupted by user. Goodbye![/dim]")
        sys.exit(130)
    except SystemExit:
        # Re-raise SystemExit to preserve exit codes from Typer
        raise
    except Exception as e:
        # In debug mode, the Rich traceback handler shows full trace automatically
        # In normal mode, show friendly summary
        if not debug_mode:
            print_fracture_summary("main", e)
        # Re-raise to let Rich traceback handler show the full trace in debug mode
        if debug_mode:
            raise
        sys.exit(1)
