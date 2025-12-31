"""
Interactive configuration wizard for existing config.toml settings.
Allows selective reconfiguration of already-configured settings.
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from rich.prompt import Prompt, Confirm
from rich.console import Console

from app.core.config_manager import ConfigManager
from app.core.logger import setup_logger

logger = setup_logger(__name__)
console = Console()


def get_os_example_paths() -> List[str]:
    """Get OS-specific example paths for path configuration (no PII)."""
    home = Path.home()
    
    if sys.platform == "win32":
        # Use generic examples without exposing username
        return [
            f"{home}\\Downloads",
            f"{home}\\Documents\\Downloads",
            "D:\\Downloads"
        ]
    elif sys.platform == "darwin":
        return [
            f"{home}/Downloads",
            f"{home}/Documents/Downloads",
            "~/Downloads"
        ]
    else:  # Linux/Unix
        return [
            f"{home}/Downloads",
            f"{home}/Documents/Downloads",
            "~/Downloads"
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
    """Configure product settings (arcane_terms)."""
    console.print("\n[bold cyan]Product Settings[/bold cyan]")
    
    current = config.get("product.arcane_terms", "true")
    current_bool = current.lower() in ("true", "1", "yes") if isinstance(current, str) else bool(current)
    
    console.print(f"Current: arcane_terms = {current_bool}")
    console.print("  [dim]If enabled, shows arcane terminology in help/output[/dim]")
    
    if Confirm.ask("\nChange arcane_terms?", default=False):
        new_value = Confirm.ask("Enable arcane terminology?", default=current_bool)
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
        if Confirm.ask(f"  Change {key}?", default=False):
            if value_type == "bool":
                new_value = Confirm.ask(f"  Enable {key}?", default=current_bool)
                config.set(f"ui.{key}", "true" if new_value else "false")
                console.print(f"  [green]✓[/green] Set {key} = {new_value}")


def configure_logging_settings(config: ConfigManager) -> None:
    """Configure logging settings."""
    console.print("\n[bold cyan]Logging Settings[/bold cyan]")
    
    current = config.get("logging.debug", "false")
    current_bool = current.lower() in ("true", "1", "yes") if isinstance(current, str) else bool(current)
    
    console.print(f"Current: debug = {current_bool}")
    console.print("  [dim]Enable debug mode with full tracebacks[/dim]")
    
    if Confirm.ask("\nChange debug setting?", default=False):
        new_value = Confirm.ask("Enable debug mode?", default=current_bool)
        config.set("logging.debug", "true" if new_value else "false")
        console.print(f"[green]✓[/green] Set debug = {new_value}")


def configure_paths(config: ConfigManager) -> None:
    """Configure filesystem paths."""
    console.print("\n[bold cyan]Filesystem Paths[/bold cyan]")
    
    # Output directory
    current_output = config.get("paths.output_dir", "./downloads")
    console.print(f"\nCurrent output directory: {current_output}")
    console.print("  [dim]Where downloaded files are saved locally[/dim]")
    
    if Confirm.ask("\nChange output directory?", default=False):
        example_paths = get_os_example_paths()
        console.print("\n  Example paths for your OS:")
        for ex_path in example_paths:
            console.print(f"    • {ex_path}")
        
        while True:
            new_path = Prompt.ask("\n  Enter new output directory path", default=current_output)
            is_valid, error = validate_path(new_path)
            if is_valid:
                expanded = os.path.abspath(os.path.expanduser(new_path))
                Path(expanded).mkdir(parents=True, exist_ok=True)
                config.set("paths.output_dir", expanded)
                console.print(f"  [green]✓[/green] Set output_dir = {expanded}")
                break
            else:
                console.print(f"  [red]✗[/red] {error}")
                if not Confirm.ask("  Try again?", default=True):
                    break
    
    # Temp directory
    current_temp = config.get("paths.temp_dir", "./tmp")
    console.print(f"\nCurrent temp directory: {current_temp}")
    console.print("  [dim]Staging directory for processing[/dim]")
    
    if Confirm.ask("\nChange temp directory?", default=False):
        new_path = Prompt.ask("  Enter new temp directory path", default=current_temp)
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
        
        if Confirm.ask(f"  Change {key}?", default=False):
            if value_type == "str":
                if choices:
                    new_value = Prompt.ask(f"  Enter {key}", choices=choices, default=str(current))
                else:
                    new_value = Prompt.ask(f"  Enter {key}", default=str(current))
                config.set(f"media.audio.{key}", new_value)
                console.print(f"  [green]✓[/green] Set {key} = {new_value}")
            elif value_type == "int":
                while True:
                    try:
                        new_value = Prompt.ask(f"  Enter {key} (integer)", default=str(current))
                        int(new_value)  # Validate
                        config.set(f"media.audio.{key}", new_value)
                        console.print(f"  [green]✓[/green] Set {key} = {new_value}")
                        break
                    except ValueError:
                        console.print(f"  [red]✗[/red] Invalid integer. Please enter a number.")


def configure_video_settings(config: ConfigManager) -> None:
    """Configure video media settings."""
    console.print("\n[bold cyan]Video Media Settings[/bold cyan]")
    
    # Format
    current_format = config.get("media.video.format", "")
    console.print(f"\n  format: {current_format or '(empty)'} - Video container format")
    if Confirm.ask("  Change format?", default=False):
        new_format = Prompt.ask("  Enter format (e.g., mp4, mkv)", default=current_format or "")
        config.set("media.video.format", new_format)
        console.print(f"  [green]✓[/green] Set format = {new_format}")
    
    # Codec
    current_codec = config.get("media.video.codec", "")
    console.print(f"\n  codec: {current_codec or '(empty)'} - Video codec")
    if Confirm.ask("  Change codec?", default=False):
        new_codec = Prompt.ask("  Enter codec (e.g., h264, hevc)", default=current_codec or "")
        config.set("media.video.codec", new_codec)
        console.print(f"  [green]✓[/green] Set codec = {new_codec}")
    
    # Restrict filenames
    current_restrict = config.get("media.video.restrict_filenames", "true")
    current_bool = current_restrict.lower() in ("true", "1", "yes") if isinstance(current_restrict, str) else bool(current_restrict)
    console.print(f"\n  restrict_filenames: {current_bool} - Restrict filenames to ASCII")
    if Confirm.ask("  Change restrict_filenames?", default=False):
        new_value = Confirm.ask("  Restrict filenames?", default=current_bool)
        config.set("media.video.restrict_filenames", "true" if new_value else "false")
        console.print(f"  [green]✓[/green] Set restrict_filenames = {new_value}")


def configure_flac_preset(config: ConfigManager) -> None:
    """Configure FLAC preset settings."""
    console.print("\n[bold cyan]FLAC Preset Settings[/bold cyan]")
    
    current_override = config.get("presets.flac.override", "false")
    current_bool = current_override.lower() in ("true", "1", "yes") if isinstance(current_override, str) else bool(current_override)
    
    console.print(f"\nCurrent: override = {current_bool}")
    console.print("  [dim]If enabled, applies FLAC 16kHz mono preset behavior[/dim]")
    
    if Confirm.ask("\nChange FLAC preset override?", default=False):
        new_value = Confirm.ask("Enable FLAC preset override?", default=current_bool)
        config.set("presets.flac.override", "true" if new_value else "false")
        console.print(f"[green]✓[/green] Set override = {new_value}")
        
        if new_value:
            # Configure preset parameters
            current_sr = config.get("presets.flac.sample_rate", "16000")
            current_ch = config.get("presets.flac.channels", "1")
            
            console.print(f"\n  Current sample_rate: {current_sr} Hz")
            if Confirm.ask("  Change sample_rate?", default=False):
                new_sr = Prompt.ask("  Enter sample rate (Hz)", default=current_sr)
                try:
                    int(new_sr)
                    config.set("presets.flac.sample_rate", new_sr)
                    console.print(f"  [green]✓[/green] Set sample_rate = {new_sr}")
                except ValueError:
                    console.print(f"  [red]✗[/red] Invalid integer")
            
            console.print(f"\n  Current channels: {current_ch}")
            if Confirm.ask("  Change channels?", default=False):
                new_ch = Prompt.ask("  Enter number of channels", default=current_ch)
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
    
    if Confirm.ask("\nChange retries?", default=False):
        while True:
            new_retries = Prompt.ask("Enter number of retries", default=current_retries)
            try:
                int(new_retries)
                config.set("network.retries", new_retries)
                console.print(f"[green]✓[/green] Set retries = {new_retries}")
                break
            except ValueError:
                console.print(f"[red]✗[/red] Invalid integer. Please enter a number.")


def configure_storage_settings(config: ConfigManager) -> None:
    """Configure storage destination and policy."""
    console.print("\n[bold cyan]Storage Settings[/bold cyan]")
    
    # Destination
    current_dest = config.get_storage_destination()
    console.print(f"\nCurrent destination: {current_dest}")
    console.print("  [dim]Default storage destination (local|s3|gcp)[/dim]")
    
    if Confirm.ask("\nChange storage destination?", default=False):
        new_dest = Prompt.ask("Enter destination", choices=["local", "s3", "gcp"], default=current_dest)
        config.set("storage.destination", new_dest)
        console.print(f"[green]✓[/green] Set destination = {new_dest}")
        
        # Warn if not configured
        if new_dest == "s3" and not config.is_s3_configured():
            console.print(f"  [yellow]⚠[/yellow]  S3 is not configured. Run 'alchemux setup s3' to configure it.")
        elif new_dest == "gcp" and not config.is_gcp_configured():
            console.print(f"  [yellow]⚠[/yellow]  GCP is not configured. Run 'alchemux setup gcp' to configure it.")
    
    # Fallback
    current_fallback = config.get("storage.fallback", "local")
    console.print(f"\nCurrent fallback: {current_fallback}")
    console.print("  [dim]Fallback destination if primary is unavailable[/dim]")
    
    if Confirm.ask("\nChange fallback?", default=False):
        new_fallback = Prompt.ask("Enter fallback", choices=["local", "s3", "gcp", "error"], default=current_fallback)
        config.set("storage.fallback", new_fallback)
        console.print(f"[green]✓[/green] Set fallback = {new_fallback}")
    
    # Keep local copy
    current_keep = config.get("storage.keep_local_copy", "false")
    current_bool = current_keep.lower() in ("true", "1", "yes") if isinstance(current_keep, str) else bool(current_keep)
    console.print(f"\nCurrent keep_local_copy: {current_bool}")
    console.print("  [dim]Keep local copy after cloud upload[/dim]")
    
    if Confirm.ask("\nChange keep_local_copy?", default=False):
        new_value = Confirm.ask("Keep local copy after cloud upload?", default=current_bool)
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
    if Confirm.ask("Change S3 endpoint?", default=False):
        new_endpoint = Prompt.ask("Enter S3 endpoint URL", default=current_endpoint or "")
        config.set("storage.s3.endpoint", new_endpoint)
        console.print(f"[green]✓[/green] Set endpoint = {new_endpoint}")
    
    current_bucket = config.get("storage.s3.bucket", "")
    console.print(f"\nCurrent bucket: {current_bucket or '(empty)'}")
    if Confirm.ask("Change S3 bucket?", default=False):
        new_bucket = Prompt.ask("Enter S3 bucket name", default=current_bucket or "")
        config.set("storage.s3.bucket", new_bucket)
        console.print(f"[green]✓[/green] Set bucket = {new_bucket}")
    
    current_ssl = config.get("storage.s3.ssl", "true")
    current_bool = current_ssl.lower() in ("true", "1", "yes") if isinstance(current_ssl, str) else bool(current_ssl)
    console.print(f"\nCurrent SSL: {current_bool}")
    if Confirm.ask("Change S3 SSL setting?", default=False):
        new_value = Confirm.ask("Enable SSL?", default=current_bool)
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
    if Confirm.ask("Change GCP bucket?", default=False):
        new_bucket = Prompt.ask("Enter GCP bucket name", default=current_bucket or "")
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
    
    # Main menu loop
    while True:
        console.print("\n[bold]Configuration Categories:[/bold]\n")
        
        categories = [
            ("1", "Product Settings", configure_product_settings, "arcane_terms"),
            ("2", "UI Settings", configure_ui_settings, "ui.auto_open"),
            ("3", "Logging Settings", configure_logging_settings, "logging.debug"),
            ("4", "Filesystem Paths", configure_paths, "paths.output_dir"),
            ("5", "Audio Media Settings", configure_audio_settings, "media.audio.format"),
            ("6", "Video Media Settings", configure_video_settings, "media.video.format"),
            ("7", "FLAC Preset Settings", configure_flac_preset, "presets.flac.override"),
            ("8", "Network Settings", configure_network_settings, "network.retries"),
            ("9", "Storage Settings", configure_storage_settings, "storage.destination"),
            ("10", "S3 Storage Settings", configure_s3_settings, "storage.s3.bucket"),
            ("11", "GCP Storage Settings", configure_gcp_settings, "storage.gcp.bucket"),
            ("q", "Quit", None, None),
        ]
        
        for num, name, _, _ in categories:
            marker = "→" if num == "q" else " "
            console.print(f"  {marker} {num}. {name}")
        
        choice = Prompt.ask("\nSelect category", choices=[c[0] for c in categories], default="q")
        
        if choice == "q":
            break
        
        # Find and execute selected category
        for num, name, func, _ in categories:
            if choice == num:
                try:
                    func(config)
                except KeyboardInterrupt:
                    console.print("\n[yellow]Configuration cancelled.[/yellow]")
                    return False
                except Exception as e:
                    logger.error(f"Error configuring {name}: {e}")
                    console.print(f"[red]✗[/red] Error configuring {name}: {e}")
                break
    
    console.print()
    console.print("[green]✓[/green] Configuration wizard complete!")
    console.print(f"[dim]Configuration saved to: {config.toml_path}[/dim]")
    return True

