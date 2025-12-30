#!/usr/bin/env python3
"""
Alchemux - URL to MP3 Converter CLI
Main entry point with Typer CLI and ALCHEMUX stylized output.
"""
import sys
import os
import traceback
import warnings
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

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

from app.cli import app
from app.cli.output import ArcaneConsole

# Track if banner has been shown (only show once per session)
_banner_shown = False

if __name__ == "__main__":
    try:
        # Check for "setup" command BEFORE Typer processes arguments
        # This prevents "setup" from being matched to the url argument in the callback
        if "setup" in sys.argv:
            setup_idx = sys.argv.index("setup")
            # Check if there's a target after "setup" (like "gcp" or "s3")
            if setup_idx + 1 < len(sys.argv) and not sys.argv[setup_idx + 1].startswith("-"):
                target = sys.argv[setup_idx + 1]
            else:
                target = None
            
            # Import and run setup directly, bypassing Typer's argument parsing
            from app.cli.commands.setup import setup as setup_cmd
            plain_mode = "--plain" in sys.argv or os.getenv("NO_COLOR", "").lower() in ("1", "true", "yes")
            
            # Print banner if needed
            if not _banner_shown and os.getenv("ALCHEMUX_SHOW_BANNER", "true").lower() == "true":
                should_skip = any(arg in sys.argv for arg in ["--version", "-v"])
                if not should_skip:
                    console = ArcaneConsole(plain=plain_mode)
                    console.print_banner()
                    _banner_shown = True
            
            # Run setup command directly
            setup_cmd(target=target, plain=plain_mode)
            sys.exit(0)
        
        # Print banner only once on initial startup (not for every command)
        if not _banner_shown and os.getenv("ALCHEMUX_SHOW_BANNER", "true").lower() == "true":
            # Skip banner only for --version flag (keep it for --help)
            should_skip = any(arg in sys.argv for arg in ["--version", "-v"])
            if not should_skip:
                # Check for --plain flag early
                plain_mode = "--plain" in sys.argv or os.getenv("NO_COLOR", "").lower() in ("1", "true", "yes")
                console = ArcaneConsole(plain=plain_mode)
                console.print_banner()
                _banner_shown = True
        
        # Run Typer app
        app()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if os.getenv("LOG_LEVEL", "").lower() == "debug":
            traceback.print_exc()
        sys.exit(1)
