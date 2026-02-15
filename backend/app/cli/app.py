"""
Root Typer app for Alchemux CLI.
"""

import os
import sys
import typer
from typing import Optional
from pathlib import Path


def _get_version() -> str:
    """Single source of truth: installed package metadata, or dev fallback."""
    try:
        from importlib.metadata import version

        return version("alchemux")
    except Exception:
        return "0.0.0+dev"


VERSION = _get_version()


# Detect app name from binary invocation
# When invoked as symlink, sys.argv[0] contains the symlink name
def get_app_name() -> str:
    """Detect app name from how the binary was invoked."""
    if len(sys.argv) > 0:
        # Get the binary name from argv[0]
        binary_name = Path(sys.argv[0]).name
        # Remove extension if present (.exe on Windows)
        binary_name = binary_name.replace(".exe", "")
        # Accept either 'amx' or 'alchemux'
        if binary_name in ("amx", "alchemux"):
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
from app.cli.commands import distill, invoke, mux, seal, inspect, setup  # noqa: E402

# Register commands as hidden subcommands (for internal use only)
# They won't appear in --help but can still be invoked programmatically
app.command("distill", hidden=True)(distill.distill)
app.command("invoke", hidden=True)(invoke.invoke)
app.command("mux", hidden=True)(mux.mux)
app.command("seal", hidden=True)(seal.seal)
app.command("inspect", hidden=True)(inspect.inspect)
# Setup is a visible command (for configuration)
app.command("setup")(setup.setup)

# Import and register config command
from app.cli.commands import config, update, doctor, batch  # noqa: E402

# Config is now a Typer sub-app with subcommands (show, mv) + wizard default
app.add_typer(
    config.app, name="config", help="Manage configuration location and diagnostics"
)
# Doctor command (standalone, moved from config doctor)
app.command("doctor", help="Run configuration diagnostics and guided repairs")(
    doctor.doctor
)
# Update command for yt-dlp
app.command("update", help="Update yt-dlp to latest stable version")(update.update)
# Batch command (PRD 009): files / paste / playlist → per-URL pipeline
app.command("batch", help="Process multiple URLs from files, paste, or playlist")(
    batch.batch
)

# Note: Removed commands per simplified CLI design (pm/notes/simplified-cli-design.md):
# - audio-format, video-format: Use `alchemux config` wizard instead
# - debug, verbose, plain: Use flags (--debug, --verbose, --plain) or `alchemux config` wizard
# - storage: Use `alchemux config` wizard instead


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
    clipboard: bool = typer.Option(
        False, "--clipboard", "-p", help="Use URL from clipboard (paste)"
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode (one-time override)",
    ),
    accept_eula: bool = typer.Option(
        False,
        "--accept-eula",
        help="No-op: EULA is accepted by use (retained for backward compatibility)",
        hidden=True,
    ),
    # Backward compatibility: accept old-style arguments at root
    url: Optional[str] = typer.Argument(None, help="Source URL to transmute"),
    flac: bool = typer.Option(
        False, "--flac", help="FLAC 16kHz mono conversion (one-time override)"
    ),
    video: bool = typer.Option(
        False, "--video", help="Enable video download (one-time override)"
    ),
    local: bool = typer.Option(
        False, "--local", help="Save to local storage (one-time override)"
    ),
    s3: bool = typer.Option(
        False, "--s3", help="Upload to S3 storage (one-time override)"
    ),
    gcp: bool = typer.Option(
        False, "--gcp", help="Upload to GCP storage (one-time override)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", help="Enable verbose logging (one-time override)"
    ),
    plain: bool = typer.Option(
        False, "--plain", help="Disable colors and animations (one-time override)"
    ),
    no_config: bool = typer.Option(
        False,
        "--no-config",
        help="Ephemeral mode; use with --download-dir",
    ),
    download_dir: Optional[str] = typer.Option(
        None,
        "--download-dir",
        help="Directory for downloaded/converted files",
    ),
    # Note: Removed --audio-format, --video-format, --save-path per simplified CLI design
    # Use `alchemux config` wizard for persistent configuration changes
) -> None:
    """
    Arcane media transmutation.

    Transmute URLs into purified media vessels through the rites of distillation,
    muxing, and sealing. Each rite serves a distinct purpose in the transmutation
    process, from initial validation to final sealing.

    For backward compatibility, you can use the old argument style:
    alchemux --flac <url>  # Routes to invoke command
    """
    if debug:
        os.environ["LOG_LEVEL"] = "debug"
        os.environ["ALCHEMUX_DEBUG"] = "true"

    if no_config and not download_dir:
        import tempfile

        download_dir = tempfile.mkdtemp(prefix="alchemux-")
        typer.echo(f"[dim]Using temporary download directory: {download_dir}[/dim]")

    if accept_eula:
        typer.echo("EULA is accepted by use. No action needed.")
        if ctx.invoked_subcommand is None and url is None:
            raise typer.Exit()

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
        command_names = [
            "setup",
            "config",
            "doctor",
            "update",
            "batch",
            "distill",
            "invoke",
            "mux",
            "seal",
            "inspect",
        ]
        if url not in command_names:
            # Route to invoke (audio_format and video_format now come from config, not flags)
            from app.cli.commands.invoke import invoke

            invoke(
                url=url,
                audio_format=None,
                video_format=None,
                flac=flac,
                video=video,
                save_path=download_dir if no_config else None,
                local=local,
                s3=s3,
                gcp=gcp,
                debug=debug,
                verbose=verbose,
                plain=plain,
                no_config=no_config,
                download_dir_override=download_dir,
            )
            return
        # Typer parsed the command name as the optional url argument (e.g. "alchemux batch").
        # Dispatch to the intended command so batch/doctor/update work from the CLI.
        if url == "batch":
            from app.cli.commands.batch import batch

            batch()
            return
        if url == "doctor":
            from app.cli.commands.doctor import doctor

            doctor()
            return
        if url == "update":
            from app.cli.commands.update import update

            update()
            return
        # config/setup are handled elsewhere; other names fall through to help below

    # No URL and no subcommand: interactive mode or clipboard (PRD6)
    if not url and ctx.invoked_subcommand is None:
        from app.cli.url_input import acquire_url, is_tty

        try:
            resolved_url, overrides = acquire_url(
                url_arg=url,
                use_clipboard=clipboard,
                is_tty=is_tty(),
            )
        except typer.Exit as e:
            raise e

        # Merge interactive overrides with existing flags (overrides take effect for this run only)
        flac_final = flac or overrides.get("flac", False)
        video_final = video or overrides.get("video", False)
        local_final = local or overrides.get("local", False)
        s3_final = s3 or overrides.get("s3", False)
        gcp_final = gcp or overrides.get("gcp", False)
        debug_final = debug or overrides.get("debug", False)
        verbose_final = verbose or overrides.get("verbose", False)
        plain_final = plain or overrides.get("plain", False)

        from app.cli.commands.invoke import invoke

        invoke(
            url=resolved_url,
            audio_format=None,
            video_format=None,
            flac=flac_final,
            video=video_final,
            save_path=download_dir if no_config else None,
            local=local_final,
            s3=s3_final,
            gcp=gcp_final,
            debug=debug_final,
            verbose=verbose_final,
            plain=plain_final,
            no_config=no_config,
            download_dir_override=download_dir,
        )
        return

    # No URL and no subcommand (fallback: e.g. non-TTY and no clipboard) - show help
    if not url:
        typer.echo(ctx.get_help())
        raise typer.Exit()
