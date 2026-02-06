"""
Interactive setup wizards for configuration.
Includes secret masking for sensitive inputs.
Uses InquirerPy (via app.cli.prompts) for interactive prompts and Rich for panels.
"""
import os
import sys
import base64
import json
import shutil
from pathlib import Path
from typing import Optional, TYPE_CHECKING, Tuple

from rich.console import Console
from rich.panel import Panel

from app.cli.prompts import confirm, select, checkbox, text, secret, filepath
from app.core.config_manager import ConfigManager, write_config_pointer, read_config_pointer
from app.core.logger import setup_logger
from app.core.eula import EULAManager, is_packaged_build

if TYPE_CHECKING:
    from app.cli.output import ArcaneConsole

logger = setup_logger(__name__)
rich_console = Console()


def mask_secret(secret: str, show_chars: int = 4) -> str:
    """
    Mask secret for display (show first N and last N characters).

    Args:
        secret: Secret string to mask
        show_chars: Number of characters to show at start and end

    Returns:
        Masked string (e.g., "abcd...xyz")
    """
    if not secret or len(secret) <= show_chars * 2:
        return "***"
    return f"{secret[:show_chars]}...{secret[-show_chars:]}"


def get_os_example_paths() -> list:
    """Example paths for output directory. ./downloads is the default (same path as Alchemux)."""
    if sys.platform == "win32":
        return ["~\\Downloads", ".\\downloads"]
    return ["~/Downloads", "./downloads"]


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


def _path_validator(msg: str = "Invalid path"):
    """Return a callable (str)->bool for use with filepath/text validate."""

    def _v(s: str) -> bool:
        ok, _ = validate_path(s)
        return ok

    return _v


def _secret_with_confirm(prompt_message: str, default: str = "") -> Optional[str]:
    """Prompt for a secret, then confirm; if user says no, re-prompt. Returns None on cancel."""
    while True:
        val = secret(message=prompt_message, default=default)
        if val is None:
            return None
        if not val.strip():
            return val
        ok = confirm("Confirm?", default=True)
        if ok is not None and ok:
            return val


def interactive_gcp_setup(config: ConfigManager) -> bool:
    """
    Interactive GCP setup wizard using InquirerPy-backed prompts.
    Uses secret+confirm loop per PRD6 for service account key.
    """
    rich_console.print()
    rich_console.print(Panel.fit("[bold cyan]GCP Cloud Storage Setup[/bold cyan]", border_style="cyan"))
    rich_console.print("\nThis wizard will help you configure GCP upload functionality.")
    rich_console.print("You'll need:")
    rich_console.print("  1. A GCP Storage bucket name")
    rich_console.print("  2. A service account key (JSON) encoded as base64")
    rich_console.print()

    current_bucket = config.get("storage.gcp.bucket", "")
    if current_bucket:
        rich_console.print(f"[dim]Current bucket:[/dim] {current_bucket}")
        use_current = confirm("Use current bucket?", default=True)
        if use_current:
            bucket_name = current_bucket
        else:
            bucket_name = text("Enter GCP Storage bucket name", default="") or ""
    else:
        bucket_name = text("Enter GCP Storage bucket name", default="") or ""

    if not bucket_name:
        rich_console.print("[red]✗ Bucket name is required[/red]")
        return False

    current_key = config.get("GCP_SA_KEY_BASE64", "")
    sa_key: Optional[str] = None
    if current_key:
        rich_console.print(f"\n[dim]Current service account key:[/dim] {mask_secret(current_key)}")
        use_current = confirm("Use current key?", default=True)
        if use_current:
            sa_key = current_key
    if sa_key is None:
        rich_console.print("\nEnter service account key:")
        rich_console.print("  Option 1: Paste base64-encoded JSON key")
        rich_console.print("  Option 2: Enter path to JSON key file (will be encoded)")
        choice = select("Choice", [("1", "Paste base64 key"), ("2", "Path to JSON key file")], default="1")
        if choice is None:
            return False
        if choice == "2":
            def _is_file(s: str) -> bool:
                if not s or not s.strip():
                    return False
                return os.path.isfile(os.path.expanduser(s.strip()))

            key_path = filepath(
                "Enter path to JSON key file",
                default="",
                only_files=True,
                validate=_is_file,
                invalid_message="Path is not a valid file",
            )
            if key_path is None:
                return False
            if key_path and os.path.exists(key_path):
                try:
                    with open(key_path, "rb") as f:
                        key_data = f.read()
                    sa_key = base64.b64encode(key_data).decode("utf-8")
                    rich_console.print("[green]✓[/green] Key file encoded successfully")
                except Exception as e:
                    rich_console.print(f"[red]✗ Error reading key file:[/red] {e}")
                    return False
            else:
                rich_console.print(f"[red]✗ File not found:[/red] {key_path}")
                return False
        else:
            sa_key = _secret_with_confirm("Paste base64-encoded service account key (input hidden)")
            if sa_key is None:
                return False

    if not sa_key or not sa_key.strip():
        rich_console.print("[red]✗ Service account key is required[/red]")
        return False

    rich_console.print("\n[dim]Validating configuration...[/dim]")
    try:
        decoded = base64.b64decode(sa_key)
        key_json = json.loads(decoded)
        if "type" not in key_json or key_json.get("type") != "service_account":
            rich_console.print("[yellow]![/yellow]  Warning: Key doesn't appear to be a service account key")
        else:
            rich_console.print("[green]✓[/green] Key format is valid")
    except Exception as e:
        rich_console.print(f"[yellow]![/yellow]  Warning: Could not validate key format: {e}")
        continue_anyway = confirm("Continue anyway?", default=False)
        if continue_anyway is not True:
            return False

    rich_console.print("\n[dim]Saving configuration...[/dim]")
    config.set("storage.gcp.bucket", bucket_name)
    config.set("GCP_SA_KEY_BASE64", sa_key)
    rich_console.print(f"[green]✓[/green] Configuration saved:")
    rich_console.print(f"  Bucket: {bucket_name}")
    rich_console.print(f"  Key: {mask_secret(sa_key)}")
    rich_console.print("\n[green]GCP setup complete![/green]")
    return True


def interactive_s3_setup(config: ConfigManager) -> bool:
    """
    Interactive S3-compatible storage setup wizard using InquirerPy-backed prompts.
    Uses secret+confirm loop per PRD6 for access key and secret key.
    """
    rich_console.print()
    rich_console.print(Panel.fit("[bold cyan]S3-Compatible Storage Setup[/bold cyan]", border_style="cyan"))
    rich_console.print("\nThis wizard will help you configure S3-compatible storage upload functionality.")
    rich_console.print("You'll need:")
    rich_console.print("  1. S3 endpoint URL (e.g., https://your-minio.cloudron.app)")
    rich_console.print("  2. Access key")
    rich_console.print("  3. Secret key")
    rich_console.print("  4. Bucket name")
    rich_console.print("  5. SSL enabled (true/false)")
    rich_console.print()

    current_endpoint = config.get("storage.s3.endpoint", "")
    if current_endpoint:
        rich_console.print(f"[dim]Current endpoint:[/dim] {current_endpoint}")
        use_current = confirm("Use current endpoint?", default=True)
        if use_current:
            endpoint = current_endpoint
        else:
            endpoint = text("Enter S3 endpoint URL", default="") or ""
    else:
        endpoint = text("Enter S3 endpoint URL", default="") or ""

    if not endpoint:
        rich_console.print("[red]✗ Endpoint is required[/red]")
        return False

    current_access_key = config.get("S3_ACCESS_KEY", "")
    if current_access_key:
        rich_console.print(f"\n[dim]Current access key:[/dim] {mask_secret(current_access_key)}")
        use_current = confirm("Use current access key?", default=True)
        if use_current:
            access_key = current_access_key
        else:
            access_key = _secret_with_confirm("S3 access key", default="") or ""
    else:
        access_key = _secret_with_confirm("S3 access key", default="") or ""

    if not access_key:
        rich_console.print("[red]✗ Access key is required[/red]")
        return False

    current_secret_key = config.get("S3_SECRET_KEY", "")
    if current_secret_key:
        rich_console.print(f"\n[dim]Current secret key:[/dim] {mask_secret(current_secret_key)}")
        use_current = confirm("Use current secret key?", default=True)
        if use_current:
            secret_key = current_secret_key
        else:
            secret_key = _secret_with_confirm("S3 secret key", default="") or ""
    else:
        secret_key = _secret_with_confirm("S3 secret key", default="") or ""

    if not secret_key:
        rich_console.print("[red]✗ Secret key is required[/red]")
        return False

    current_bucket = config.get("storage.s3.bucket", "")
    if current_bucket:
        rich_console.print(f"\n[dim]Current bucket:[/dim] {current_bucket}")
        use_current = confirm("Use current bucket?", default=True)
        if use_current:
            bucket_name = current_bucket
        else:
            bucket_name = text("Enter S3 bucket name", default="") or ""
    else:
        bucket_name = text("Enter S3 bucket name", default="") or ""

    if not bucket_name:
        rich_console.print("[red]✗ Bucket name is required[/red]")
        return False

    current_ssl_str = config.get("storage.s3.ssl", "true")
    current_ssl = current_ssl_str.lower() == "true" if isinstance(current_ssl_str, str) else bool(current_ssl_str)
    rich_console.print(f"\n[dim]Current SSL:[/dim] {current_ssl}")
    ssl_ans = confirm("Enable SSL?", default=current_ssl)
    ssl_enabled = ssl_ans is True

    rich_console.print("\n[dim]Saving configuration...[/dim]")
    config.set("storage.s3.endpoint", endpoint)
    config.set("storage.s3.bucket", bucket_name)
    config.set("storage.s3.ssl", "true" if ssl_enabled else "false")
    config.set("S3_ACCESS_KEY", access_key)
    config.set("S3_SECRET_KEY", secret_key)
    rich_console.print(f"[green]✓[/green] Configuration saved:")
    rich_console.print(f"  Endpoint: {endpoint}")
    rich_console.print(f"  Bucket: {bucket_name}")
    rich_console.print(f"  Access Key: {mask_secret(access_key)}")
    rich_console.print(f"  SSL: {ssl_enabled}")
    rich_console.print("\n[green]S3 setup complete![/green]")
    return True


def interactive_setup_refresh(config: ConfigManager) -> bool:
    """
    Interactive setup refresh wizard for existing configuration.
    Updates only what the user opts to change, doesn't delete existing configs.

    Args:
        config: ConfigManager instance

    Returns:
        True if setup completed successfully
    """
    # Ensure config files exist - always create if missing
    env_exists = config.check_env_file_exists()
    toml_exists = config.check_toml_file_exists()
    env_example_path = config.env_path.parent / "env.example"

    if not env_exists:
        rich_console.print("\n[dim]No .env file detected. Creating from env.example...[/dim]")
        try:
            config._create_env_from_example()
            if env_example_path.exists():
                rich_console.print(f"[green]✓[/green] Created .env from {env_example_path}")
            else:
                rich_console.print("[green]✓[/green] Created minimal .env file")
            from dotenv import load_dotenv
            load_dotenv(config.env_path)
        except (IOError, OSError, PermissionError) as e:
            rich_console.print(f"[red]✗[/red] Failed to create .env file: {e}")
            rich_console.print(f"[dim]This may be a permission issue. Try running with appropriate permissions or create {config.env_path} manually.[/dim]")
            return False
        except Exception as e:
            logger.warning(f"Could not create .env: {e}")
            rich_console.print(f"[yellow]![/yellow]  Could not create .env: {e}")
            return False

    if not toml_exists:
        rich_console.print("\n[dim]No config.toml file detected. Creating from config.toml.example...[/dim]")
        try:
            config._create_toml_from_example()
            if config.toml_example_path.exists():
                rich_console.print(f"[green]✓[/green] Created config.toml from {config.toml_example_path}")
            else:
                rich_console.print(f"[green]✓[/green] Created minimal config.toml file")
        except (IOError, OSError, PermissionError) as e:
            logger.warning(f"Could not create config.toml: {e}")
            rich_console.print(f"[red]✗[/red] Could not create config.toml: {e}")
            rich_console.print(f"[dim]This may be a permission issue. Try running with appropriate permissions or create {config.toml_path} manually.[/dim]")
            return False
        except Exception as e:
            logger.warning(f"Could not create config.toml: {e}")
            rich_console.print(f"[yellow]![/yellow]  Could not create config.toml: {e}")
            return False

    # Check EULA
    if is_packaged_build():
        eula_manager = EULAManager(config)
        if not eula_manager.is_accepted():
            rich_console.print("\n[yellow]![/yellow]  EULA acceptance required")
            if not eula_manager.interactive_acceptance():
                rich_console.print("[red]✗[/red] EULA not accepted. Setup cancelled.")
                return False
            rich_console.print("[green]✓[/green] EULA accepted")

    # Setup refresh wizard (InquirerPy-backed prompts per PRD6)
    rich_console.print()
    rich_console.print(Panel.fit("[bold cyan]Alchemux Setup Wizard[/bold cyan]", border_style="cyan"))
    rich_console.print("\n[dim]Configure your preferences. Press Enter to skip or use defaults.[/dim]\n")

    # Arcane terminology: select prompt (Arcane vs Technical) with example terms per PRD6
    current_arcane = config.get("product.arcane_terms", "true")
    arcane_default = "arcane" if current_arcane.lower() in ("true", "1", "yes") else "technical"
    term_choice = select(
        message="Choose your terminology preference. (current: arcane enabled)" if arcane_default == "arcane" else "Choose your terminology preference. (current: technical)",
        choices=[
            ("arcane", "Arcane (scribe / scry / distill)"),
            ("technical", "Tech (validate / detect / download)"),
        ],
        default=arcane_default,
    )
    if term_choice is not None:
        config.set("product.arcane_terms", "true" if term_choice == "arcane" else "false")
        rich_console.print("  [green]✓[/green] Terminology set to " + ("arcane" if term_choice == "arcane" else "technical"))
    rich_console.print("  [dim]See docs/legend.md for full mapping.[/dim]")

    # Auto-open folder: confirm prompt
    current_auto_open = config.get("ui.auto_open", "true")
    current_auto_open_bool = current_auto_open.lower() in ("true", "1", "yes") if isinstance(current_auto_open, str) else bool(current_auto_open)
    auto_open_ans = confirm("Auto-open folder after download?", default=current_auto_open_bool)
    if auto_open_ans is not None:
        config.set("ui.auto_open", "true" if auto_open_ans else "false")
        rich_console.print("  [green]✓[/green] Auto-open " + ("enabled" if auto_open_ans else "disabled"))

    # Output directory: filepath prompt with validation (default ./downloads or current)
    default_path = "./downloads"
    current_path = config.get("paths.output_dir", default_path)
    rich_console.print(f"\n[bold]Output directory[/bold] [dim](current: {current_path})[/dim]")
    example_paths = get_os_example_paths()
    rich_console.print("  [dim]Example paths:[/dim]")
    for ex_path in example_paths:
        rich_console.print(f"    - {ex_path}")
    rich_console.print("  [dim dim]default: creates folder in same path as Alchemux[/dim dim]")
    new_path = filepath(
        message="Enter path (leave empty and Enter for default)",
        default=current_path or default_path,
        only_directories=True,
        validate=lambda s: not s.strip() or validate_path(s)[0],
        invalid_message="Invalid path",
    )
    if new_path is not None:
        if new_path and new_path.strip():
            is_valid, error = validate_path(new_path)
            if is_valid:
                expanded = os.path.abspath(os.path.expanduser(new_path.strip()))
                Path(expanded).mkdir(parents=True, exist_ok=True)
                config.set("paths.output_dir", expanded)
                rich_console.print(f"  [green]✓[/green] Output directory set to: {expanded}")
            else:
                rich_console.print(f"  [yellow]![/yellow]  {error}, keeping current: {current_path}")
        else:
            config.set("paths.output_dir", default_path)
            rich_console.print(f"  [green]✓[/green] Using default: {default_path}")

    # Audio format: confirm then checkbox (PRD6)
    current_audio = config.get("media.audio.format", "mp3")
    change_audio = confirm(f"Change default audio output? (current: .{current_audio})", default=False)
    if change_audio is True:
        selected_audio = checkbox(
            message="Select audio formats (select/deselect with spacebar)",
            choices=[("mp3", "MP3"), ("flac", "FLAC"), ("wav", "WAV"), ("aac", "AAC"), ("m4a", "M4A")],
            default_selected=[current_audio if current_audio in ("mp3", "flac", "wav", "aac", "m4a") else "mp3"],
        )
        if selected_audio and len(selected_audio) > 0:
            config.set("media.audio.format", selected_audio[0])
            # Store enabled list for future multi-format output
            from app.core.toml_config import read_toml, write_toml
            tom = read_toml(config.toml_path) if config.toml_path.exists() else {}
            if "media" not in tom:
                tom["media"] = {}
            if "audio" not in tom["media"]:
                tom["media"]["audio"] = {}
            tom["media"]["audio"]["enabled_formats"] = list(selected_audio)
            write_toml(config.toml_path, tom)
            config._toml_cache = None
            rich_console.print(f"  [green]✓[/green] Audio format(s): {', '.join(selected_audio)}")

    # Video: confirm "Save video too?" then optional codec checkbox (PRD6)
    save_video = confirm("Save video file, too?", default=False)
    if save_video is True:
        current_video = config.get("media.video.format", "mp4") or "mp4"
        change_video = confirm(f"Change default video codec? (current: .{current_video})", default=False)
        if change_video is True:
            selected_video = checkbox(
                message="Select video codecs (select/deselect with spacebar)",
                choices=[("mp4", "MP4"), ("mkv", "MKV"), ("webm", "WebM")],
                default_selected=[current_video if current_video in ("mp4", "mkv", "webm") else "mp4"],
            )
            if selected_video and len(selected_video) > 0:
                config.set("media.video.format", selected_video[0])
                from app.core.toml_config import read_toml, write_toml
                tom = read_toml(config.toml_path) if config.toml_path.exists() else {}
                if "media" not in tom:
                    tom["media"] = {}
                if "video" not in tom["media"]:
                    tom["media"]["video"] = {}
                tom["media"]["video"]["enabled_formats"] = list(selected_video)
                write_toml(config.toml_path, tom)
                config._toml_cache = None
                rich_console.print(f"  [green]✓[/green] Video codec(s): {', '.join(selected_video)}")
        else:
            config.set("media.video.format", current_video)
        rich_console.print("  [green]✓[/green] Video output enabled")
    else:
        config.set("media.video.format", "")
        from app.core.toml_config import read_toml, write_toml
        tom = read_toml(config.toml_path) if config.toml_path.exists() else {}
        if "media" not in tom:
            tom["media"] = {}
        if "video" not in tom["media"]:
            tom["media"]["video"] = {}
        tom["media"]["video"]["enabled_formats"] = []
        write_toml(config.toml_path, tom)
        config._toml_cache = None
        rich_console.print("  [dim]Video output disabled[/dim]")

    # Config location (after output dir): keep next to binary or choose path
    config_dir_for_summary = str(config.toml_path.parent)
    if is_packaged_build():
        binary_dir = Path(sys.executable).resolve().parent
        binary_path_display = str(binary_dir)
        keep_next_to_binary = confirm(
            f"Keep config files in same path as Alchemux ({binary_path_display})?",
            default=True,
        )
        if keep_next_to_binary is True:
            write_config_pointer(binary_dir)
            config_dir_for_summary = binary_path_display
            rich_console.print("  [green]✓[/green] Config will stay next to Alchemux binary")
        elif keep_next_to_binary is False:
            while True:
                custom = filepath(
                    message="Enter path to save configs (e.g. folder/path/to/alchemux/[configs here]):",
                    default="",
                    only_directories=True,
                    invalid_message="Invalid path",
                    mandatory=False,
                )
                if custom is None or (custom and not custom.strip()):
                    break
                custom_path = Path(custom.strip()).expanduser().resolve()
                ok = confirm("Confirm?", default=True)
                if ok is True:
                    custom_path.mkdir(parents=True, exist_ok=True)
                    write_config_pointer(custom_path)
                    if config.toml_path.exists():
                        shutil.copy2(config.toml_path, custom_path / "config.toml")
                    if config.env_path.exists():
                        shutil.copy2(config.env_path, custom_path / ".env")
                    config_dir_for_summary = str(custom_path)
                    rich_console.print(f"  [green]✓[/green] Config location set to: {custom_path}")
                    break

    # Cloud storage: confirm then checkbox (local, s3, gcp); local always on by default
    current_dest = config.get("storage.destination", "local")
    configure_cloud = confirm("Configure cloud storage?", default=False)
    if configure_cloud is True:
        selected = checkbox(
            message="Select storage providers (select/deselect with spacebar)",
            choices=[("local", "Local"), ("s3", "S3"), ("gcp", "GCP")],
            default_selected=["local"],
        )
        if selected is not None and len(selected) > 0:
            has_local = "local" in selected
            config.set("storage.keep_local_copy", "true" if has_local else "false")
            if "gcp" in selected:
                config.set("storage.destination", "gcp")
                if interactive_gcp_setup(config):
                    rich_console.print("[green]>[/green] GCP configured")
            if "s3" in selected:
                if "gcp" not in selected:
                    config.set("storage.destination", "s3")
                if interactive_s3_setup(config):
                    rich_console.print("[green]>[/green] S3 configured")
            if "gcp" not in selected and "s3" not in selected:
                config.set("storage.destination", "local")
                rich_console.print("  [green]>[/green] Using local storage only")
        else:
            config.set("storage.destination", "local")
            config.set("storage.keep_local_copy", "false")
            rich_console.print("  [green]>[/green] Using local storage")
    else:
        config.set("storage.destination", "local")
        config.set("storage.keep_local_copy", "true")
        rich_console.print("  [green]>[/green] Using local storage")

    # Ensure config.toml has full example content - merge example with current config
    if config.toml_example_path.exists() and config.toml_path.exists():
        from app.core.toml_config import read_toml, write_toml, get_nested_value, set_nested_value
        # Read current config (has user's changes)
        current_config = read_toml(config.toml_path)
        # Read example config (has all default sections)
        example_config = read_toml(config.toml_example_path)
        # Merge: example as base, current as overrides (preserve user's changes)
        merged_config = example_config.copy()
        # Deep merge: copy all top-level sections from example, then overlay user's changes
        for section_key in example_config:
            if section_key not in merged_config:
                merged_config[section_key] = example_config[section_key].copy() if isinstance(example_config[section_key], dict) else example_config[section_key]
            elif isinstance(example_config[section_key], dict) and isinstance(current_config.get(section_key), dict):
                # Merge nested dicts: example as base, current as overrides
                merged_section = example_config[section_key].copy()
                merged_section.update(current_config[section_key])
                merged_config[section_key] = merged_section
        # Overlay any top-level keys from current that aren't in example
        for key in current_config:
            if key not in merged_config:
                merged_config[key] = current_config[key]
        # Write merged config
        write_toml(config.toml_path, merged_config)
        # Invalidate cache
        config._toml_cache = None

    # If user chose a custom config path, ensure final files are there
    pointer_dir = read_config_pointer()
    if pointer_dir and pointer_dir.resolve() != config.toml_path.parent.resolve():
        pointer_dir.mkdir(parents=True, exist_ok=True)
        if config.toml_path.exists():
            shutil.copy2(config.toml_path, pointer_dir / "config.toml")
        if config.env_path.exists():
            shutil.copy2(config.env_path, pointer_dir / ".env")
        config_dir_for_summary = str(pointer_dir)

    # End-of-wizard summary panel with all paths and helpful commands
    output_dir = config.get("paths.output_dir", "./downloads")
    storage_dest = config.get("storage.destination", "local")
    arcane_mode = config.get("product.arcane_terms", "true")
    summary_config_dir = config_dir_for_summary

    rich_console.print()
    rich_console.print(Panel(
        f"[bold]Configuration files:[/bold]\n"
        f"  [dim]-[/dim] config.toml: {summary_config_dir}/config.toml\n"
        f"  [dim]-[/dim] .env: {summary_config_dir}/.env\n"
        f"  [dim]-[/dim] Config location: {summary_config_dir}\n\n"
        f"[bold]Settings:[/bold]\n"
        f"  [dim]-[/dim] Output directory: {output_dir}\n"
        f"  [dim]-[/dim] Storage: {storage_dest}\n"
        f"  [dim]-[/dim] Arcane mode: {'enabled' if arcane_mode == 'true' else 'disabled'}\n\n"
        f"[bold]Useful commands:[/bold]\n"
        f"  [cyan]alchemux config show[/cyan]   - View all settings\n"
        f"  [cyan]alchemux config doctor[/cyan] - Run diagnostics\n"
        f"  [cyan]alchemux config mv[/cyan] [path] - Relocate config (interactive path if omitted)\n"
        f"  [cyan]alchemux setup s3[/cyan]      - Configure S3 storage\n"
        f"  [cyan]alchemux setup gcp[/cyan]     - Configure GCP storage",
        title="[green]Setup Complete[/green]",
        border_style="green",
        padding=(0, 1)
    ))

    return True


def interactive_setup_minimal(config: ConfigManager) -> bool:
    """
    Minimal setup for auto-setup cases (when config is missing).
    Only sets essential defaults without interactive prompts.

    Args:
        config: ConfigManager instance

    Returns:
        True if setup completed successfully
    """
    # Ensure config files exist
    env_exists = config.check_env_file_exists()
    toml_exists = config.check_toml_file_exists()
    env_example_path = config.env_path.parent / "env.example"

    if not env_exists:
        if env_example_path.exists():
            config._create_env_from_example()
        from dotenv import load_dotenv
        load_dotenv(config.env_path)

    if not toml_exists:
        try:
            config._create_toml_from_example()
        except Exception as e:
            logger.warning(f"Could not create config.toml: {e}")

    # Set minimal defaults
    if not config.get("paths.output_dir"):
        config.set("paths.output_dir", "./downloads")

    return True


def smart_setup(config: ConfigManager, console: "ArcaneConsole") -> bool:
    """
    Intelligent setup that detects existing .env and handles EULA acceptance.
    Delegates to interactive_setup_refresh for full setup.

    Args:
        config: ConfigManager instance
        console: ArcaneConsole instance for output

    Returns:
        True if setup completed successfully
    """
    return interactive_setup_refresh(config)
