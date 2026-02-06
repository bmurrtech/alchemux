"""
Storage command - Manage storage settings.
"""

import typer

from app.cli.output import ArcaneConsole
from app.core.config_manager import ConfigManager

app = typer.Typer(
    name="storage",
    help="Manage storage settings",
    no_args_is_help=True,
)


@app.command("status")
def storage_status(
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Show storage configuration status.

    Displays the current storage destination, provider configuration status,
    and output directory settings.
    """
    import os

    arcane_terms = os.getenv("ARCANE_TERMS", "true").lower() in ("1", "true", "yes")
    console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)

    config_manager = ConfigManager()

    # Get current destination
    destination = config_manager.get_storage_destination()

    # Check provider configuration
    s3_configured = config_manager.is_s3_configured()
    gcp_configured = config_manager.is_gcp_configured()

    # Get paths
    output_dir = config_manager.get("paths.output_dir", "./downloads")
    temp_dir = config_manager.get("paths.temp_dir", "./tmp")

    # Get storage policy
    fallback = config_manager.get("storage.fallback", "local")
    keep_local = (
        config_manager.get("storage.keep_local_copy", "false").lower() == "true"
    )

    # Display status
    console.console.print("\n[bold]Storage Configuration[/bold]\n")

    console.console.print(f"Destination: [cyan]{destination}[/cyan]")
    console.console.print(f"Fallback: [cyan]{fallback}[/cyan]")
    console.console.print(
        f"Keep local copy: [cyan]{'yes' if keep_local else 'no'}[/cyan]\n"
    )

    console.console.print("[bold]Provider Status:[/bold]")
    console.console.print("  Local: [green]always available[/green]")
    console.console.print(
        f"  S3:   {'[green]configured[/green]' if s3_configured else '[dim]not configured[/dim]'}"
    )
    console.console.print(
        f"  GCP:  {'[green]configured[/green]' if gcp_configured else '[dim]not configured[/dim]'}\n"
    )

    console.console.print("[bold]Paths:[/bold]")
    console.console.print(f"  Output: [cyan]{output_dir}[/cyan]")
    console.console.print(f"  Temp:   [cyan]{temp_dir}[/cyan]\n")

    if (
        destination != "local"
        and not (destination == "s3" and s3_configured)
        and not (destination == "gcp" and gcp_configured)
    ):
        console.console.print(
            f"[yellow]⚠[/yellow]  Destination '{destination}' is not configured. Will fallback to '{fallback}'"
        )


@app.command("set")
def storage_set(
    path: str = typer.Argument(
        ..., help="Output directory path (where downloaded files are saved)"
    ),
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Set the output directory path in config.toml.

    This command validates the path for your operating system and updates
    paths.output_dir in config.toml. The path will be used as the default
    location for downloaded files.

    Examples:
        alchemux storage set ~/Downloads
        alchemux storage set /home/user/media
        alchemux storage set C:\\Users\\Name\\Downloads
    """
    import os
    import sys
    from pathlib import Path
    from typing import Optional, Tuple

    arcane_terms = os.getenv("ARCANE_TERMS", "true").lower() in ("1", "true", "yes")
    console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)

    # Validate path (reuse validation logic from paths.py)
    def validate_path(path: str) -> Tuple[bool, Optional[str]]:
        if not path or not path.strip():
            return False, "Path cannot be empty"

        expanded = os.path.expanduser(path.strip())

        if sys.platform == "win32":
            if len(expanded) > 260:
                return (
                    False,
                    f"Path too long (Windows limit: 260 characters). Current: {len(expanded)}",
                )
            invalid_chars = ["<", ">", ":", '"', "|", "?", "*"]
            if any(char in expanded for char in invalid_chars):
                return (
                    False,
                    f"Path contains invalid characters for Windows: {', '.join(invalid_chars)}",
                )
            reserved = (
                ["CON", "PRN", "AUX", "NUL"]
                + [f"COM{i}" for i in range(1, 10)]
                + [f"LPT{i}" for i in range(1, 10)]
            )
            path_parts = Path(expanded).parts
            for part in path_parts:
                if part.upper().rstrip(".") in reserved:
                    return False, f"Path contains reserved Windows name: {part}"
        elif sys.platform == "darwin":
            if len(expanded) > 1024:
                return (
                    False,
                    f"Path too long (macOS limit: 1024 characters). Current: {len(expanded)}",
                )
        else:
            if len(expanded) > 4096:
                return (
                    False,
                    f"Path too long (Linux limit: 4096 characters). Current: {len(expanded)}",
                )

        try:
            path_obj = Path(expanded)
            if path_obj.exists():
                if not os.access(path_obj, os.W_OK):
                    return False, f"Path exists but is not writable: {expanded}"
            else:
                parent = path_obj.parent
                if parent.exists():
                    if not os.access(parent, os.W_OK):
                        return (
                            False,
                            f"Parent directory exists but is not writable: {parent}",
                        )
                else:
                    try:
                        parent.mkdir(parents=True, exist_ok=True)
                        if parent != path_obj:
                            try:
                                parent.rmdir()
                            except OSError:
                                pass
                    except (OSError, PermissionError) as e:
                        return False, f"Cannot create directory: {e}"
        except Exception as e:
            return False, f"Invalid path: {e}"

        return True, None

    is_valid, error_msg = validate_path(path)
    if not is_valid:
        console.print_fracture("storage", error_msg or "Invalid path")
        raise typer.Exit(code=1)

    # Expand and normalize path
    expanded_path = os.path.expanduser(path.strip())
    absolute_path = os.path.abspath(expanded_path)

    # Create directory if it doesn't exist
    try:
        Path(absolute_path).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        console.print_fracture("storage", f"Could not create directory: {e}")
        raise typer.Exit(code=1)

    # Ensure .env exists (for backward compatibility and secret storage)
    config_manager = ConfigManager()
    if not config_manager.check_env_file_exists():
        config_manager._create_env_from_example()

    # Ensure config.toml exists
    if not config_manager.check_toml_file_exists():
        config_manager._create_toml_from_example()

    try:
        # Update config.toml
        config_manager.set("paths.output_dir", absolute_path)

        console.print_success("storage", f"Output directory set to: {absolute_path}")
        console.console.print(
            "  Downloaded files will be saved to this location by default"
        )
        console.console.print(
            f"  [dim]Configuration saved to: {config_manager.toml_path}[/dim]"
        )
        console.console.print(
            "[dim]You can override this per-run using --save-path flag[/dim]"
        )
    except Exception as e:
        console.print_fracture("storage", f"Failed to update configuration: {e}")
        raise typer.Exit(code=1)


@app.command("use")
def storage_use(
    target: str = typer.Argument(..., help="Storage target: 'local', 's3', or 'gcp'"),
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Set the default storage destination.

    This is a human-friendly alias for: alchemux config set storage.destination <target>

    Examples:
        alchemux storage use local
        alchemux storage use s3
        alchemux storage use gcp
    """
    import os

    arcane_terms = os.getenv("ARCANE_TERMS", "true").lower() in ("1", "true", "yes")
    console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)

    if target not in ("local", "s3", "gcp"):
        console.print_fracture("storage", f"Invalid storage target: {target}")
        console.console.print("Valid targets: local, s3, gcp")
        raise typer.Exit(code=1)

    config_manager = ConfigManager()

    # Ensure config files exist
    if not config_manager.check_env_file_exists():
        config_manager._create_env_from_example()
    if not config_manager.check_toml_file_exists():
        config_manager._create_toml_from_example()

    try:
        # Use config.toml for storage.destination (non-secret)
        config_manager.set("storage.destination", target)
        console.print_success(
            "storage", f"Default storage destination set to {target.upper()}"
        )

        console.console.print(f"  Files will be saved to {target} by default")
        console.console.print(
            f"  [dim]Configuration saved to: {config_manager.toml_path}[/dim]"
        )

        # Warn if target is not configured
        if target == "s3" and not config_manager.is_s3_configured():
            console.console.print(
                "  [yellow]⚠[/yellow]  S3 is not configured. Run 'alchemux setup s3' to configure it."
            )
        elif target == "gcp" and not config_manager.is_gcp_configured():
            console.console.print(
                "  [yellow]⚠[/yellow]  GCP is not configured. Run 'alchemux setup gcp' to configure it."
            )

        console.console.print(
            "[dim]You can override this per-run using --local, --s3, or --gcp flags[/dim]"
        )
    except Exception as e:
        console.print_fracture("storage", f"Failed to update configuration: {e}")
        raise typer.Exit(code=1)
