#!/usr/bin/env python3
"""
Alchemux - URL to MP3 Converter CLI
Main entry point with Typer CLI and ALCHEMUX stylized output.
"""
import sys
import os
import traceback
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

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
                should_skip = any(arg in sys.argv for arg in ["--help", "-h", "--version", "-v"])
                if not should_skip:
                    console = ArcaneConsole(plain=plain_mode)
                    console.print_banner()
                    _banner_shown = True
            
            # Run setup command directly
            setup_cmd(target=target, plain=plain_mode)
            sys.exit(0)
        
        # Print banner only once on initial startup (not for every command)
        if not _banner_shown and os.getenv("ALCHEMUX_SHOW_BANNER", "true").lower() == "true":
            # Skip banner for --help, --version flags
            should_skip = any(arg in sys.argv for arg in ["--help", "-h", "--version", "-v"])
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
