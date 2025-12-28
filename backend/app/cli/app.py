"""
Root Typer app for Alchemux CLI.
"""
import sys
import os
import typer
from typing import Optional
from pathlib import Path

# Version constant (shared with main.py)
VERSION = "0.1.0-alpha"

# Detect app name from binary invocation
# When invoked as symlink, sys.argv[0] contains the symlink name
def get_app_name() -> str:
    """Detect app name from how the binary was invoked."""
    if len(sys.argv) > 0:
        # Get the binary name from argv[0]
        binary_name = Path(sys.argv[0]).name
        # Remove extension if present (.exe on Windows)
        binary_name = binary_name.replace('.exe', '')
        # Accept either 'amx' or 'alchemux'
        if binary_name in ('amx', 'alchemux'):
            return binary_name
    # Default fallback
    return "alchemux"

APP_NAME = get_app_name()

# Create root app with dynamic name
app = typer.Typer(
    name=APP_NAME,
    help="Arcane media transmutation",
    add_completion=False,
    no_args_is_help=False,  # Allow default command to handle no args
)

# Import commands (but don't register as visible subcommands)
# These are internal/linear processing stages, not standalone commands
from app.cli.commands import distill, invoke, mux, seal, inspect, setup

# Register commands as hidden subcommands (for internal use only)
# They won't appear in --help but can still be invoked programmatically
app.command("distill", hidden=True)(distill.distill)
app.command("invoke", hidden=True)(invoke.invoke)
app.command("mux", hidden=True)(mux.mux)
app.command("seal", hidden=True)(seal.seal)
app.command("inspect", hidden=True)(inspect.inspect)
# Setup is the only visible command (for configuration)
app.command("setup")(setup.setup)

# Version callback
def version_callback(value: bool) -> None:
    """Display version information."""
    if value:
        # Use detected app name for version display
        display_name = APP_NAME.capitalize() if APP_NAME == "amx" else "Alchemux"
        typer.echo(f"{display_name} {VERSION}")
        raise typer.Exit()

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        help="Show version and exit",
        is_eager=True,
    ),
    help: Optional[bool] = typer.Option(
        None,
        "--help",
        "-h",
        help="Show this message and exit",
        is_eager=True,
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode with full tracebacks",
    ),
    # Backward compatibility: accept old-style arguments at root
    url: Optional[str] = typer.Argument(None, help="Source URL to transmute"),
    format: str = typer.Option("mp3", "--format", "-f", help="Audio codec/format"),
    audio_format: Optional[str] = typer.Option(None, "--audio-format", help="Audio codec/format (alias for --format)"),
    video_format: Optional[str] = typer.Option(None, "--video-format", help="Video container"),
    flac: bool = typer.Option(False, "--flac", help="FLAC 16kHz mono conversion"),
    save_path: Optional[str] = typer.Option(None, "--save-path", help="Custom save location"),
    gcp: bool = typer.Option(False, "--gcp", help="Enable GCP Cloud Storage upload"),
    accept_eula: bool = typer.Option(False, "--accept-eula", help="Accept EULA non-interactively"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging"),
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
    setup: Optional[str] = typer.Option(
        None,
        "--setup",
        help="Run setup wizard (use 'gcp' or 's3' for cloud storage, or use '--setup' alone for minimal setup)",
    ),
) -> None:
    """
    Arcane media transmutation.
    
    Transmute URLs into purified media vessels through the rites of distillation,
    muxing, and sealing. Each rite serves a distinct purpose in the transmutation
    process, from initial validation to final sealing.
    
    For backward compatibility, you can use the old argument style:
    alchemux --flac <url>  # Routes to invoke command
    """
    import os
    if debug or verbose:
        os.environ["LOG_LEVEL"] = "debug"
        os.environ["ALCHEMUX_DEBUG"] = "true"
    
    # Handle --help flag (eager, so it runs before other logic)
    if help:
        typer.echo(ctx.get_help())
        raise typer.Exit()
    
    # Banner is printed in main.py before Typer processes args
    # This ensures it shows for all commands including --help
    
    # If a subcommand was invoked, don't run default behavior
    # Note: "setup" is handled in main.py before Typer processes args to avoid
    # it being matched to the url argument. Other subcommands work normally.
    if ctx.invoked_subcommand is not None:
        return
    
    # Handle --setup flag
    # Typer requires a value for string options, so we check sys.argv manually
    # to detect if --setup was used without a value
    if "--setup" in sys.argv:
        from app.cli.commands.setup import setup as setup_cmd
        # Find --setup in argv and check if there's a value after it
        setup_idx = sys.argv.index("--setup")
        # If there's a next arg that's not a flag, use it as target
        if setup_idx + 1 < len(sys.argv) and not sys.argv[setup_idx + 1].startswith("-"):
            target = sys.argv[setup_idx + 1]
        else:
            # No value provided - use parsed value or None for minimal setup
            target = setup if setup else None
        setup_cmd(target=target, plain=plain)
        return
    
    # If URL provided, route to invoke for backward compatibility
    # But skip if URL is "setup" (that's a command, not a URL)
    if url and url != "setup":
        # Use audio_format if provided, otherwise format
        actual_format = audio_format or format
        from app.cli.commands.invoke import invoke
        invoke(
            url=url,
            format=actual_format,
            video_format=video_format,
            flac=flac,
            save_path=save_path,
            gcp=gcp,
            accept_eula=accept_eula,
            verbose=verbose,
            plain=plain,
        )
        return
    
    # No URL and no subcommand - show help
    if not url:
        typer.echo(ctx.get_help())
        raise typer.Exit()

