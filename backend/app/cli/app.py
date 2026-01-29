"""
Root Typer app for Alchemux CLI.
"""
import sys
import os
import typer
from typing import Optional
from pathlib import Path

# Version constant (shared with main.py)
VERSION = "0.1.1-alpha"

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
# Setup is a visible command (for configuration)
app.command("setup")(setup.setup)

# Import and register config and storage commands
from app.cli.commands import config, storage
# Config is now a Typer sub-app with subcommands (show, doctor, mv) + wizard default
app.add_typer(config.app, name="config", help="Manage configuration location and diagnostics")
app.add_typer(storage.app, name="storage", help="Manage storage settings and paths")

# Import and register new configuration commands
from app.cli.commands import audio_format, video_format, debug as debug_cmd, verbose as verbose_cmd, plain as plain_cmd
app.command("audio-format", help="Interactive audio format selection")(audio_format.audio_format_command)
app.command("video-format", help="Interactive video format selection")(video_format.video_format_command)
app.command("debug", help="Toggle debug mode")(debug_cmd.debug_command)
app.command("verbose", help="Toggle verbose logging")(verbose_cmd.verbose_command)
app.command("plain", help="Toggle plain mode (disable colors/animations)")(plain_cmd.plain_command)

# Version callback
def version_callback(value: bool) -> None:
    """Display version information."""
    if value:
        # Always display as Alchemux
        typer.echo(f"Alchemux {VERSION}")
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
    audio_format: Optional[str] = typer.Option(None, "--audio-format", "-a", help="Audio codec/format"),
    video_format: Optional[str] = typer.Option(None, "--video-format", help="Video container"),
    flac: bool = typer.Option(False, "--flac", help="FLAC 16kHz mono conversion"),
    save_path: Optional[str] = typer.Option(None, "--save-path", help="Custom output directory for this run (one-time override)"),
    local: bool = typer.Option(False, "--local", help="Save to local storage (one-time override)"),
    s3: bool = typer.Option(False, "--s3", help="Upload to S3 storage (one-time override)"),
    gcp: bool = typer.Option(False, "--gcp", help="Upload to GCP storage (one-time override)"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose logging"),
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
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
    if debug:
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
    
    # If URL provided, route to invoke for backward compatibility
    # But skip if URL is a command name (like "setup", "audio-format", etc.)
    # Only process URL if we have a valid URL and no command was invoked
    if url and ctx.invoked_subcommand is None:
        # Check if URL is actually a command name
        command_names = ["setup", "audio-format", "video-format", "debug", "verbose", "plain", "config", "storage", "distill", "invoke", "mux", "seal", "inspect"]
        if url not in command_names:
            # Use audio_format if provided, otherwise default from config
            from app.cli.commands.invoke import invoke
            invoke(
                url=url,
                audio_format=audio_format,
                video_format=video_format,
                flac=flac,
                save_path=save_path,
                local=local,
                s3=s3,
                gcp=gcp,
                debug=debug,
                verbose=verbose,
                plain=plain,
            )
            return
    
    # No URL and no subcommand - show help
    if not url:
        typer.echo(ctx.get_help())
        raise typer.Exit()

