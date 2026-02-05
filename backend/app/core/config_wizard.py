"""
Interactive configuration wizard for existing config.toml settings.
Allows selective reconfiguration of already-configured settings.
Uses InquirerPy-backed prompts (app.cli.prompts) and Rich for output.
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from rich.console import Console
from rich.panel import Panel

from app.cli.prompts import confirm, select, checkbox, text, filepath
from app.core.config_manager import ConfigManager
from app.core.logger import setup_logger

logger = setup_logger(__name__)
console = Console()


def get_os_example_paths() -> List[str]:
    """Get OS-specific example paths for path configuration. Uses tilde form only (no PII)."""
    if sys.platform == "win32":
        return [
            "~\\Downloads",
            "~\\Documents\\Downloads",
            "D:\\Downloads"
        ]
    return [
        "~/Downloads",
        "~/Documents/Downloads",
        "~/Documents"
    ]


def validate_path(path: str) -> Tuple[bool, Optional[str]]:
    """Validate a filesystem path."""
    if not path or not path.strip():
        return False, "Path cannot be empty"
    
    expanded = os.path.expanduser(path.strip())
    
    try:
        path_obj = Path(expanded)
        if path_obj.exists():
            if not os.access(path_obj, os.W_OK):
                return False, f"Path exists but is not writable: {expanded}"
        else:
            parent = path_obj.parent
            if parent.exists():
                if not os.access(parent, os.W_OK):
                    return False, f"Parent directory exists but is not writable: {parent}"
    except Exception as e:
        return False, f"Invalid path: {e}"
    
    return True, None


def configure_product_settings(config: ConfigManager) -> None:
    """Configure terminology settings (arcane_terms)."""
    console.print("\n[bold cyan]Terminology Setting[/bold cyan]")

    current = config.get("product.arcane_terms", "true")
    current_bool = current.lower() in ("true", "1", "yes") if isinstance(current, str) else bool(current)

    console.print(f"Current: arcane_terms = {current_bool}")
    console.print("  [dim]If enabled, shows arcane terminology in help/output[/dim]")

    if confirm("\nChange arcane_terms?", default=False) is True:
        new_value = confirm("Enable arcane terminology?", default=current_bool)
        if new_value is not None:
            config.set("product.arcane_terms", "true" if new_value else "false")
            console.print(f"[green]✓[/green] Set arcane_terms = {new_value}")


def configure_ui_settings(config: ConfigManager) -> None:
    """Configure UI settings."""
    console.print("\n[bold cyan]UI Settings[/bold cyan]")

    settings = {
        "auto_open": ("Auto-open folder after download", "bool"),
        "plain": ("Disable colors/animations by default", "bool"),
        "animations": ("Enable animations", "bool"),
        "colors": ("Enable colors", "bool"),
    }

    for key, (description, value_type) in settings.items():
        current = config.get(f"ui.{key}", "true" if key == "auto_open" else "false")
        current_bool = current.lower() in ("true", "1", "yes") if isinstance(current, str) else bool(current)

        console.print(f"\n  {key}: {current_bool} - {description}")
        if confirm(f"  Change {key}?", default=False) is True:
            if value_type == "bool":
                new_value = confirm(f"  Enable {key}?", default=current_bool)
                if new_value is not None:
                    config.set(f"ui.{key}", "true" if new_value else "false")
                    console.print(f"  [green]✓[/green] Set {key} = {new_value}")


def configure_logging_settings(config: ConfigManager) -> None:
    """Configure logging settings."""
    console.print("\n[bold cyan]Logging Settings[/bold cyan]")

    current = config.get("logging.debug", "false")
    current_bool = current.lower() in ("true", "1", "yes") if isinstance(current, str) else bool(current)

    console.print(f"Current: debug = {current_bool}")
    console.print("  [dim]Enable debug mode with full tracebacks[/dim]")

    if confirm("\nChange debug setting?", default=False) is True:
        new_value = confirm("Enable debug mode?", default=current_bool)
        if new_value is not None:
            config.set("logging.debug", "true" if new_value else "false")
            console.print(f"[green]✓[/green] Set debug = {new_value}")


def _path_validate(s: str) -> bool:
    ok, _ = validate_path(s)
    return ok


def configure_paths(config: ConfigManager) -> None:
    """Configure filesystem paths."""
    console.print("\n[bold cyan]Filesystem Paths[/bold cyan]")

    current_output = config.get("paths.output_dir", "./downloads")
    console.print(f"\nCurrent output directory: {current_output}")
    console.print("  [dim]Where downloaded files are saved locally[/dim]")

    if confirm("\nChange output directory?", default=False) is True:
        example_paths = get_os_example_paths()
        console.print("\n  Example paths for your OS:")
        for ex_path in example_paths:
            console.print(f"    • {ex_path}")
        new_path = filepath(
            message="Enter new output directory path",
            default=current_output,
            only_directories=True,
            validate=_path_validate,
            invalid_message="Invalid path",
        )
        if new_path and new_path.strip():
            is_valid, error = validate_path(new_path)
            if is_valid:
                expanded = os.path.abspath(os.path.expanduser(new_path))
                Path(expanded).mkdir(parents=True, exist_ok=True)
                config.set("paths.output_dir", expanded)
                console.print(f"  [green]✓[/green] Set output_dir = {expanded}")
            else:
                console.print(f"  [red]✗[/red] {error}")

    current_temp = config.get("paths.temp_dir", "./tmp")
    console.print(f"\nCurrent temp directory: {current_temp}")
    console.print("  [dim]Staging directory for processing[/dim]")

    if confirm("\nChange temp directory?", default=False) is True:
        new_path = filepath(
            message="Enter new temp directory path",
            default=current_temp,
            only_directories=True,
            validate=_path_validate,
            invalid_message="Invalid path",
        )
        if new_path and new_path.strip():
            is_valid, error = validate_path(new_path)
            if is_valid:
                expanded = os.path.abspath(os.path.expanduser(new_path))
                Path(expanded).mkdir(parents=True, exist_ok=True)
                config.set("paths.temp_dir", expanded)
                console.print(f"  [green]✓[/green] Set temp_dir = {expanded}")
            else:
                console.print(f"  [red]✗[/red] {error}")


def configure_audio_settings(config: ConfigManager) -> None:
    """Configure audio media settings."""
    console.print("\n[bold cyan]Audio Media Settings[/bold cyan]")

    settings = {
        "format": ("Audio format/codec", "str", ["mp3", "flac", "wav", "aac", "alac", "m4a", "opus", "vorbis"]),
        "quality": ("Audio quality", "str", None),
        "sample_rate": ("Sample rate (Hz, 0 = source/default)", "int", None),
        "channels": ("Number of channels (0 = source/default)", "int", None),
    }

    for key, (description, value_type, choices) in settings.items():
        current = config.get(f"media.audio.{key}", "mp3" if key == "format" else ("192k" if key == "quality" else "0"))
        console.print(f"\n  {key}: {current} - {description}")

        if confirm(f"  Change {key}?", default=False) is True:
            if value_type == "str":
                if choices:
                    new_value = select(f"  Select {key}", choices=[(c, c) for c in choices], default=str(current))
                else:
                    new_value = text(f"  Enter {key}", default=str(current))
                if new_value is not None:
                    config.set(f"media.audio.{key}", str(new_value))
                    console.print(f"  [green]✓[/green] Set {key} = {new_value}")
            elif value_type == "int":
                new_value = text(f"  Enter {key} (integer)", default=str(current), validate=lambda x: x.strip() == "" or x.lstrip("-").isdigit(), invalid_message="Invalid integer")
                if new_value is not None and new_value.strip():
                    try:
                        int(new_value)
                        config.set(f"media.audio.{key}", new_value)
                        console.print(f"  [green]✓[/green] Set {key} = {new_value}")
                    except ValueError:
                        console.print(f"  [red]✗[/red] Invalid integer. Please enter a number.")


def configure_video_settings(config: ConfigManager) -> None:
    """Configure video media settings."""
    console.print("\n[bold cyan]Video Media Settings[/bold cyan]")

    current_format = config.get("media.video.format", "")
    console.print(f"\n  format: {current_format or '(empty)'} - Video container format")
    if confirm("  Change format?", default=False) is True:
        new_format = text("  Enter format (e.g., mp4, mkv)", default=current_format or "")
        if new_format is not None:
            config.set("media.video.format", new_format)
            console.print(f"  [green]✓[/green] Set format = {new_format}")

    current_codec = config.get("media.video.codec", "")
    console.print(f"\n  codec: {current_codec or '(empty)'} - Video codec")
    if confirm("  Change codec?", default=False) is True:
        new_codec = text("  Enter codec (e.g., h264, hevc)", default=current_codec or "")
        if new_codec is not None:
            config.set("media.video.codec", new_codec)
            console.print(f"  [green]✓[/green] Set codec = {new_codec}")

    current_restrict = config.get("media.video.restrict_filenames", "true")
    current_bool = current_restrict.lower() in ("true", "1", "yes") if isinstance(current_restrict, str) else bool(current_restrict)
    console.print(f"\n  restrict_filenames: {current_bool} - Restrict filenames to ASCII")
    if confirm("  Change restrict_filenames?", default=False) is True:
        new_value = confirm("  Restrict filenames?", default=current_bool)
        if new_value is not None:
            config.set("media.video.restrict_filenames", "true" if new_value else "false")
            console.print(f"  [green]✓[/green] Set restrict_filenames = {new_value}")


def configure_flac_preset(config: ConfigManager) -> None:
    """Configure FLAC preset settings."""
    console.print("\n[bold cyan]FLAC Preset Settings[/bold cyan]")

    current_override = config.get("presets.flac.override", "false")
    current_bool = current_override.lower() in ("true", "1", "yes") if isinstance(current_override, str) else bool(current_override)

    console.print(f"\nCurrent: override = {current_bool}")
    console.print("  [dim]If enabled, applies FLAC 16kHz mono preset behavior[/dim]")

    if confirm("\nChange FLAC preset override?", default=False) is True:
        new_value = confirm("Enable FLAC preset override?", default=current_bool)
        if new_value is not None:
            config.set("presets.flac.override", "true" if new_value else "false")
            console.print(f"[green]✓[/green] Set override = {new_value}")

        if new_value:
            current_sr = config.get("presets.flac.sample_rate", "16000")
            current_ch = config.get("presets.flac.channels", "1")
            console.print(f"\n  Current sample_rate: {current_sr} Hz")
            if confirm("  Change sample_rate?", default=False) is True:
                new_sr = text("  Enter sample rate (Hz)", default=current_sr, validate=lambda x: x.strip() == "" or x.isdigit(), invalid_message="Invalid integer")
                if new_sr and new_sr.strip():
                    try:
                        int(new_sr)
                        config.set("presets.flac.sample_rate", new_sr)
                        console.print(f"  [green]✓[/green] Set sample_rate = {new_sr}")
                    except ValueError:
                        console.print(f"  [red]✗[/red] Invalid integer")
            console.print(f"\n  Current channels: {current_ch}")
            if confirm("  Change channels?", default=False) is True:
                new_ch = text("  Enter number of channels", default=current_ch, validate=lambda x: x.strip() == "" or x.isdigit(), invalid_message="Invalid integer")
                if new_ch and new_ch.strip():
                    try:
                        int(new_ch)
                        config.set("presets.flac.channels", new_ch)
                        console.print(f"  [green]✓[/green] Set channels = {new_ch}")
                    except ValueError:
                        console.print(f"  [red]✗[/red] Invalid integer")


def configure_network_settings(config: ConfigManager) -> None:
    """Configure network settings."""
    console.print("\n[bold cyan]Network Settings[/bold cyan]")

    current_retries = config.get("network.retries", "3")
    console.print(f"Current: retries = {current_retries}")
    console.print("  [dim]Number of retry attempts for network operations[/dim]")

    if confirm("\nChange retries?", default=False) is True:
        new_retries = text("Enter number of retries", default=current_retries, validate=lambda x: x.strip() == "" or x.isdigit(), invalid_message="Invalid integer")
        if new_retries is not None and new_retries.strip():
            try:
                int(new_retries)
                config.set("network.retries", new_retries)
                console.print(f"[green]✓[/green] Set retries = {new_retries}")
            except ValueError:
                console.print(f"[red]✗[/red] Invalid integer. Please enter a number.")


def configure_storage_settings(config: ConfigManager) -> None:
    """Configure storage destination and policy."""
    console.print("\n[bold cyan]Storage Settings[/bold cyan]")

    current_dest = config.get_storage_destination()
    console.print(f"\nCurrent destination: {current_dest}")
    console.print("  [dim]Default storage destination (local|s3|gcp)[/dim]")

    if confirm("\nChange storage destination?", default=False) is True:
        new_dest = select("Enter destination", choices=[("local", "local"), ("s3", "s3"), ("gcp", "gcp")], default=current_dest)
        if new_dest is not None:
            config.set("storage.destination", new_dest)
            console.print(f"[green]✓[/green] Set destination = {new_dest}")
            if new_dest == "s3" and not config.is_s3_configured():
                console.print(f"  [yellow]⚠[/yellow]  S3 is not configured. Run 'alchemux setup s3' to configure it.")
            elif new_dest == "gcp" and not config.is_gcp_configured():
                console.print(f"  [yellow]⚠[/yellow]  GCP is not configured. Run 'alchemux setup gcp' to configure it.")

    current_fallback = config.get("storage.fallback", "local")
    console.print(f"\nCurrent fallback: {current_fallback}")
    console.print("  [dim]Fallback destination if primary is unavailable[/dim]")

    if confirm("\nChange fallback?", default=False) is True:
        new_fallback = select("Enter fallback", choices=[("local", "local"), ("s3", "s3"), ("gcp", "gcp"), ("error", "error")], default=current_fallback)
        if new_fallback is not None:
            config.set("storage.fallback", new_fallback)
            console.print(f"[green]✓[/green] Set fallback = {new_fallback}")

    current_keep = config.get("storage.keep_local_copy", "false")
    current_bool = current_keep.lower() in ("true", "1", "yes") if isinstance(current_keep, str) else bool(current_keep)
    console.print(f"\nCurrent keep_local_copy: {current_bool}")
    console.print("  [dim]Keep local copy after cloud upload[/dim]")

    if confirm("\nChange keep_local_copy?", default=False) is True:
        new_value = confirm("Keep local copy after cloud upload?", default=current_bool)
        if new_value is not None:
            config.set("storage.keep_local_copy", "true" if new_value else "false")
            console.print(f"[green]✓[/green] Set keep_local_copy = {new_value}")


def configure_s3_settings(config: ConfigManager) -> None:
    """Configure S3 storage settings (if configured)."""
    if not config.is_s3_configured():
        console.print("\n[dim]S3 is not configured. Run 'alchemux setup s3' to configure it first.[/dim]")
        return

    console.print("\n[bold cyan]S3 Storage Settings[/bold cyan]")

    current_endpoint = config.get("storage.s3.endpoint", "")
    console.print(f"\nCurrent endpoint: {current_endpoint or '(empty)'}")
    if confirm("Change S3 endpoint?", default=False) is True:
        new_endpoint = text("Enter S3 endpoint URL", default=current_endpoint or "")
        if new_endpoint is not None:
            config.set("storage.s3.endpoint", new_endpoint)
            console.print(f"[green]✓[/green] Set endpoint = {new_endpoint}")

    current_bucket = config.get("storage.s3.bucket", "")
    console.print(f"\nCurrent bucket: {current_bucket or '(empty)'}")
    if confirm("Change S3 bucket?", default=False) is True:
        new_bucket = text("Enter S3 bucket name", default=current_bucket or "")
        if new_bucket is not None:
            config.set("storage.s3.bucket", new_bucket)
            console.print(f"[green]✓[/green] Set bucket = {new_bucket}")

    current_ssl = config.get("storage.s3.ssl", "true")
    current_bool = current_ssl.lower() in ("true", "1", "yes") if isinstance(current_ssl, str) else bool(current_ssl)
    console.print(f"\nCurrent SSL: {current_bool}")
    if confirm("Change S3 SSL setting?", default=False) is True:
        new_value = confirm("Enable SSL?", default=current_bool)
        if new_value is not None:
            config.set("storage.s3.ssl", "true" if new_value else "false")
            console.print(f"[green]✓[/green] Set ssl = {new_value}")


def configure_gcp_settings(config: ConfigManager) -> None:
    """Configure GCP storage settings (if configured)."""
    if not config.is_gcp_configured():
        console.print("\n[dim]GCP is not configured. Run 'alchemux setup gcp' to configure it first.[/dim]")
        return

    console.print("\n[bold cyan]GCP Storage Settings[/bold cyan]")

    current_bucket = config.get("storage.gcp.bucket", "")
    console.print(f"\nCurrent bucket: {current_bucket or '(empty)'}")
    if confirm("Change GCP bucket?", default=False) is True:
        new_bucket = text("Enter GCP bucket name", default=current_bucket or "")
        if new_bucket is not None:
            config.set("storage.gcp.bucket", new_bucket)
            console.print(f"[green]✓[/green] Set bucket = {new_bucket}")


def interactive_config_wizard(config: ConfigManager) -> bool:
    """
    Interactive configuration wizard for existing config.toml settings.
    
    Args:
        config: ConfigManager instance
        
    Returns:
        True if wizard completed successfully
    """
    console.print()
    console.print(Panel.fit("[bold cyan]Alchemux Configuration Wizard[/bold cyan]", border_style="cyan"))
    console.print("\nThis wizard allows you to selectively reconfigure existing settings.")
    console.print("You'll be prompted to choose which settings to modify.\n")
    
    # Check if config.toml exists
    if not config.check_toml_file_exists():
        console.print("[yellow]⚠[/yellow]  config.toml not found. Run 'alchemux setup' first to create it.")
        return False
    
    # Add "Show Configurations" as first option (special action, not a category)
    def show_configurations(config: ConfigManager) -> None:
        """Show current configuration (same as 'alchemux config show')."""
        from app.cli.commands.config import config_show
        # Import console from config module
        from app.cli.commands.config import console as config_console
        # Call config_show but we need to handle it differently
        # Since config_show uses its own console, we'll call it directly
        config_show(plain=False)
    
    categories = [
        ("show", "Show Configurations", show_configurations),
        ("product", "Terminology Setting", configure_product_settings),
        ("ui", "UI Settings", configure_ui_settings),
        ("logging", "Logging Settings", configure_logging_settings),
        ("paths", "Filesystem Paths", configure_paths),
        ("audio", "Audio Media Settings", configure_audio_settings),
        ("video", "Video Media Settings", configure_video_settings),
        ("flac", "FLAC Preset Settings", configure_flac_preset),
        ("network", "Network Settings", configure_network_settings),
        ("storage", "Storage Settings", configure_storage_settings),
        ("s3", "S3 Storage Settings", configure_s3_settings),
        ("gcp", "GCP Storage Settings", configure_gcp_settings),
    ]

    console.print("\n[bold]Select an action or configuration categories to modify:[/bold]")
    console.print("[dim]Use spacebar to toggle, Enter to confirm[/dim]\n")
    
    # Present checkbox menu
    category_choices = [(cat_id, name) for cat_id, name, _ in categories]
    selected = checkbox(
        message="Select action or categories (at least one required)",
        choices=category_choices,
        default_selected=None,
    )
    
    if not selected or len(selected) == 0:
        console.print("\n[yellow]No selection made. Configuration cancelled.[/yellow]")
        return False
    
    # If "show" is selected, run it and exit (don't modify config)
    if "show" in selected:
        show_configurations(config)
        return True
    
    # Remove "show" from selected if it was there (it's already handled)
    selected = [s for s in selected if s != "show"]
    
    if not selected:
        # Only "show" was selected, already handled above
        return True
    
    # Create mapping for quick lookup
    category_map = {cat_id: (name, func) for cat_id, name, func in categories}
    
    # Run selected category handlers sequentially
    console.print()
    console.print(f"[dim]Processing {len(selected)} selection(s)...[/dim]\n")
    
    for cat_id in selected:
        if cat_id not in category_map:
            continue
        
        name, func = category_map[cat_id]
        try:
            func(config)
        except KeyboardInterrupt:
            console.print("\n[yellow]Configuration cancelled.[/yellow]")
            return False
        except Exception as e:
            logger.error(f"Error processing {name}: {e}")
            console.print(f"[red]✗[/red] Error processing {name}: {e}")
    
    console.print()
    console.print("[green]✓[/green] Configuration wizard complete!")
    console.print(f"[dim]Configuration saved to: {config.toml_path}[/dim]")
    return True

