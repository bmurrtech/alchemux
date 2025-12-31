"""
Interactive setup wizards for configuration.
Includes secret masking for sensitive inputs.
Uses Rich for visual enhancements.
"""
import os
import sys
import getpass
from pathlib import Path
from typing import Optional, TYPE_CHECKING, Tuple

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text

from app.core.config_manager import ConfigManager
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


def interactive_gcp_setup(config: ConfigManager) -> bool:
    """
    Interactive GCP setup wizard.
    
    Args:
        config: ConfigManager instance
        
    Returns:
        True if setup completed successfully
    """
    rich_console.print()
    rich_console.print(Panel.fit("[bold cyan]GCP Cloud Storage Setup[/bold cyan]", border_style="cyan"))
    rich_console.print("\nThis wizard will help you configure GCP upload functionality.")
    rich_console.print("You'll need:")
    rich_console.print("  1. A GCP Storage bucket name")
    rich_console.print("  2. A service account key (JSON) encoded as base64")
    rich_console.print()
    
    # Get bucket name (from config.toml storage.gcp.bucket)
    current_bucket = config.get("storage.gcp.bucket", "")
    if current_bucket:
        rich_console.print(f"[dim]Current bucket:[/dim] {current_bucket}")
        use_current = Confirm.ask("Use current bucket?", default=True)
        if use_current:
            bucket_name = current_bucket
        else:
            bucket_name = Prompt.ask("Enter GCP Storage bucket name")
    else:
        bucket_name = Prompt.ask("Enter GCP Storage bucket name")
    
    if not bucket_name:
        rich_console.print("[red]❌ Bucket name is required[/red]")
        return False
    
    # Get service account key
    current_key = config.get("GCP_SA_KEY_BASE64", "")
    if current_key:
        rich_console.print(f"\n[dim]Current service account key:[/dim] {mask_secret(current_key)}")
        use_current = Confirm.ask("Use current key?", default=True)
        if use_current:
            sa_key = current_key
        else:
            rich_console.print("\nEnter service account key:")
            rich_console.print("  Option 1: Paste base64-encoded JSON key")
            rich_console.print("  Option 2: Enter path to JSON key file (will be encoded)")
            choice = Prompt.ask("Choice", choices=["1", "2"], default="1")
            
            if choice == "2":
                key_path = Prompt.ask("Enter path to JSON key file")
                if os.path.exists(key_path):
                    try:
                        import base64
                        with open(key_path, 'rb') as f:
                            key_data = f.read()
                        sa_key = base64.b64encode(key_data).decode('utf-8')
                        rich_console.print("[green]✓[/green] Key file encoded successfully")
                    except Exception as e:
                        rich_console.print(f"[red]❌ Error reading key file:[/red] {e}")
                        return False
                else:
                    rich_console.print(f"[red]❌ File not found:[/red] {key_path}")
                    return False
            else:
                rich_console.print("Paste base64-encoded service account key (input will be hidden):")
                sa_key = getpass.getpass("Key: ").strip()
    else:
        rich_console.print("\nEnter service account key:")
        rich_console.print("  Option 1: Paste base64-encoded JSON key")
        rich_console.print("  Option 2: Enter path to JSON key file (will be encoded)")
        choice = Prompt.ask("Choice", choices=["1", "2"], default="1")
        
        if choice == "2":
            key_path = Prompt.ask("Enter path to JSON key file")
            if os.path.exists(key_path):
                try:
                    import base64
                    with open(key_path, 'rb') as f:
                        key_data = f.read()
                    sa_key = base64.b64encode(key_data).decode('utf-8')
                    rich_console.print("[green]✓[/green] Key file encoded successfully")
                except Exception as e:
                    rich_console.print(f"[red]❌ Error reading key file:[/red] {e}")
                    return False
            else:
                rich_console.print(f"[red]❌ File not found:[/red] {key_path}")
                return False
        else:
            rich_console.print("Paste base64-encoded service account key (input will be hidden):")
            sa_key = getpass.getpass("Key: ").strip()
    
    if not sa_key:
        rich_console.print("[red]❌ Service account key is required[/red]")
        return False
    
    # Validate configuration
    rich_console.print("\n[dim]Validating configuration...[/dim]")
    try:
        import base64
        decoded = base64.b64decode(sa_key)
        import json
        key_json = json.loads(decoded)
        if "type" not in key_json or key_json.get("type") != "service_account":
            rich_console.print("[yellow]⚠[/yellow]  Warning: Key doesn't appear to be a service account key")
        else:
            rich_console.print("[green]✓[/green] Key format is valid")
    except Exception as e:
        rich_console.print(f"[yellow]⚠[/yellow]  Warning: Could not validate key format: {e}")
        continue_anyway = Confirm.ask("Continue anyway?", default=False)
        if not continue_anyway:
            return False
    
    # Save configuration
    rich_console.print("\n[dim]Saving configuration...[/dim]")
    config.set("storage.gcp.bucket", bucket_name)
    config.set("GCP_SA_KEY_BASE64", sa_key)
    
    rich_console.print(f"[green]✓[/green] Configuration saved:")
    rich_console.print(f"  Bucket: {bucket_name}")
    rich_console.print(f"  Key: {mask_secret(sa_key)}")
    rich_console.print("\n[green]✅ GCP setup complete![/green]")
    
    return True


def interactive_s3_setup(config: ConfigManager) -> bool:
    """
    Interactive S3-compatible storage setup wizard.
    
    Args:
        config: ConfigManager instance
        
    Returns:
        True if setup completed successfully
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
    
    # Get endpoint (from config.toml storage.s3.endpoint)
    current_endpoint = config.get("storage.s3.endpoint", "")
    if current_endpoint:
        rich_console.print(f"[dim]Current endpoint:[/dim] {current_endpoint}")
        use_current = Confirm.ask("Use current endpoint?", default=True)
        if use_current:
            endpoint = current_endpoint
        else:
            endpoint = Prompt.ask("Enter S3 endpoint URL")
    else:
        endpoint = Prompt.ask("Enter S3 endpoint URL")
    
    if not endpoint:
        rich_console.print("[red]❌ Endpoint is required[/red]")
        return False
    
    # Get access key
    current_access_key = config.get("S3_ACCESS_KEY", "")
    if current_access_key:
        rich_console.print(f"\n[dim]Current access key:[/dim] {mask_secret(current_access_key)}")
        use_current = Confirm.ask("Use current access key?", default=True)
        if use_current:
            access_key = current_access_key
        else:
            rich_console.print("Enter S3 access key (input will be hidden):")
            access_key = getpass.getpass("Access key: ").strip()
    else:
        rich_console.print("\nEnter S3 access key (input will be hidden):")
        access_key = getpass.getpass("Access key: ").strip()
    
    if not access_key:
        rich_console.print("[red]❌ Access key is required[/red]")
        return False
    
    # Get secret key
    current_secret_key = config.get("S3_SECRET_KEY", "")
    if current_secret_key:
        rich_console.print(f"\n[dim]Current secret key:[/dim] {mask_secret(current_secret_key)}")
        use_current = Confirm.ask("Use current secret key?", default=True)
        if use_current:
            secret_key = current_secret_key
        else:
            rich_console.print("Enter S3 secret key (input will be hidden):")
            secret_key = getpass.getpass("Secret key: ").strip()
    else:
        rich_console.print("\nEnter S3 secret key (input will be hidden):")
        secret_key = getpass.getpass("Secret key: ").strip()
    
    if not secret_key:
        rich_console.print("[red]❌ Secret key is required[/red]")
        return False
    
    # Get bucket name (from config.toml storage.s3.bucket)
    current_bucket = config.get("storage.s3.bucket", "")
    if current_bucket:
        rich_console.print(f"\n[dim]Current bucket:[/dim] {current_bucket}")
        use_current = Confirm.ask("Use current bucket?", default=True)
        if use_current:
            bucket_name = current_bucket
        else:
            bucket_name = Prompt.ask("Enter S3 bucket name")
    else:
        bucket_name = Prompt.ask("\nEnter S3 bucket name")
    
    if not bucket_name:
        rich_console.print("[red]❌ Bucket name is required[/red]")
        return False
    
    # Get SSL setting (from config.toml storage.s3.ssl)
    current_ssl_str = config.get("storage.s3.ssl", "true")
    current_ssl = current_ssl_str.lower() == "true" if isinstance(current_ssl_str, str) else bool(current_ssl_str)
    rich_console.print(f"\n[dim]Current SSL:[/dim] {current_ssl}")
    ssl_enabled = Confirm.ask("Enable SSL?", default=current_ssl)
    
    # Save configuration
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
    rich_console.print("\n[green]✅ S3 setup complete![/green]")
    
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
    # Ensure config files exist
    env_exists = config.check_env_file_exists()
    toml_exists = config.check_toml_file_exists()
    env_example_path = config.env_path.parent / "env.example"
    
    if not env_exists:
        rich_console.print("\n[dim]No .env file detected. Creating from env.example...[/dim]")
        try:
            if env_example_path.exists():
                config._create_env_from_example()
                rich_console.print(f"[green]✓[/green] Created .env from {env_example_path}")
            else:
                config._create_env_from_example()  # Creates minimal .env
                rich_console.print("[green]✓[/green] Created minimal .env file")
            from dotenv import load_dotenv
            load_dotenv(config.env_path)
        except (IOError, OSError, PermissionError) as e:
            rich_console.print(f"[red]❌[/red] Failed to create .env file: {e}")
            rich_console.print(f"[dim]This may be a permission issue. Try running with appropriate permissions or create {config.env_path} manually.[/dim]")
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
            rich_console.print(f"[red]❌[/red] Could not create config.toml: {e}")
            rich_console.print(f"[dim]This may be a permission issue. Try running with appropriate permissions or create {config.toml_path} manually.[/dim]")
            return False
        except Exception as e:
            logger.warning(f"Could not create config.toml: {e}")
            rich_console.print(f"[yellow]⚠[/yellow]  Could not create config.toml: {e}")
    
    # Check EULA (skip if eula_config.json exists)
    eula_json_path = config.env_path.parent / "eula_config.json"
    if is_packaged_build() and not eula_json_path.exists():
        eula_manager = EULAManager(config)
        if not eula_manager.is_accepted():
            rich_console.print("\n[yellow]⚠[/yellow]  EULA acceptance required")
            if not eula_manager.interactive_acceptance():
                rich_console.print("[red]✗[/red] EULA not accepted. Setup cancelled.")
                return False
            rich_console.print("[green]✓[/green] EULA accepted")
    
    # Setup refresh wizard
    rich_console.print()
    rich_console.print(Panel.fit("[bold cyan]Alchemux Setup Wizard[/bold cyan]", border_style="cyan"))
    rich_console.print("\n[dim]Configure your preferences. Press Enter to skip or use defaults.[/dim]\n")
    
    # Arcane terminology
    current_arcane = config.get("product.arcane_terms", "true")
    current_arcane_bool = current_arcane.lower() in ("true", "1", "yes") if isinstance(current_arcane, str) else bool(current_arcane)
    rich_console.print(f"[bold]Use arcane terminology?[/bold] [dim](current: {current_arcane_bool})[/dim]")
    if Confirm.ask("  Enable arcane terminology?", default=current_arcane_bool):
        config.set("product.arcane_terms", "true")
        rich_console.print("  [green]✓[/green] Arcane terminology enabled")
    else:
        config.set("product.arcane_terms", "false")
        rich_console.print("  [green]✓[/green] Arcane terminology disabled")
    
    # Auto-open folder
    current_auto_open = config.get("ui.auto_open", "true")
    current_auto_open_bool = current_auto_open.lower() in ("true", "1", "yes") if isinstance(current_auto_open, str) else bool(current_auto_open)
    rich_console.print(f"\n[bold]Auto-open download folder?[/bold] [dim](current: {current_auto_open_bool})[/dim]")
    if Confirm.ask("  Auto-open folder after download?", default=current_auto_open_bool):
        config.set("ui.auto_open", "true")
        rich_console.print("  [green]✓[/green] Auto-open enabled")
    else:
        config.set("ui.auto_open", "false")
        rich_console.print("  [green]✓[/green] Auto-open disabled")
    
    # Output directory
    default_path = "./downloads"
    current_path = config.get("paths.output_dir", default_path)
    rich_console.print(f"\n[bold]Output directory[/bold] [dim](current: {current_path})[/dim]")
    example_paths = get_os_example_paths()
    rich_console.print("  [dim]Example paths for your OS:[/dim]")
    for ex_path in example_paths:
        rich_console.print(f"    • {ex_path}")
    
    new_path = Prompt.ask(f"\n  Enter path", default=current_path)
    if new_path and new_path.strip():
        is_valid, error = validate_path(new_path)
        if is_valid:
            expanded = os.path.abspath(os.path.expanduser(new_path.strip()))
            Path(expanded).mkdir(parents=True, exist_ok=True)
            config.set("paths.output_dir", expanded)
            rich_console.print(f"  [green]✓[/green] Output directory set to: {expanded}")
        else:
            rich_console.print(f"  [yellow]⚠[/yellow]  {error}, keeping current: {current_path}")
    else:
        config.set("paths.output_dir", default_path)
        rich_console.print(f"  [green]✓[/green] Using default: {default_path}")
    
    # Cloud storage setup
    rich_console.print(f"\n[bold]Setup cloud storage?[/bold]")
    setup_cloud = Confirm.ask("  Configure cloud storage?", default=False)
    
    if setup_cloud:
        cloud_choice = Prompt.ask("  Choose cloud provider", choices=["gcp", "s3"], default="gcp")
        
        if cloud_choice == "gcp":
            if interactive_gcp_setup(config):
                rich_console.print("[green]✓[/green] GCP configured")
                # Ask about S3
                rich_console.print(f"\n[bold]Configure S3 storage?[/bold]")
                if Confirm.ask("  Setup S3 storage?", default=False):
                    if interactive_s3_setup(config):
                        rich_console.print("[green]✓[/green] S3 configured")
        else:  # s3
            if interactive_s3_setup(config):
                rich_console.print("[green]✓[/green] S3 configured")
                # Ask about GCP
                rich_console.print(f"\n[bold]Configure GCP storage?[/bold]")
                if Confirm.ask("  Setup GCP storage?", default=False):
                    if interactive_gcp_setup(config):
                        rich_console.print("[green]✓[/green] GCP configured")
    
    rich_console.print()
    rich_console.print("[green]✅ Setup complete![/green]")
    rich_console.print(f"\n[dim]Configuration files:[/dim]")
    rich_console.print(f"  • config.toml: {config.toml_path}")
    rich_console.print(f"  • .env: {config.env_path}")
    rich_console.print(f"\n[dim]Run 'alchemux config' to reconfigure settings interactively.[/dim]")
    
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
