"""
Interactive setup wizards for configuration.
Includes secret masking for sensitive inputs.
"""
import os
import getpass
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from app.core.config_manager import ConfigManager
from app.core.logger import setup_logger
from app.core.eula import EULAManager

if TYPE_CHECKING:
    from app.cli.output import ArcaneConsole

logger = setup_logger(__name__)


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


def interactive_gcp_setup(config: ConfigManager) -> bool:
    """
    Interactive GCP setup wizard.
    
    Args:
        config: ConfigManager instance
        
    Returns:
        True if setup completed successfully
    """
    print("\n" + "=" * 70)
    print("GCP Cloud Storage Setup")
    print("=" * 70)
    print("\nThis wizard will help you configure GCP upload functionality.")
    print("You'll need:")
    print("  1. A GCP Storage bucket name")
    print("  2. A service account key (JSON) encoded as base64")
    print()
    
    # Get bucket name
    current_bucket = config.get("GCP_STORAGE_BUCKET", "")
    if current_bucket:
        print(f"Current bucket: {current_bucket}")
        use_current = input("Use current bucket? (y/n, default: y): ").strip().lower()
        if use_current != 'n':
            bucket_name = current_bucket
        else:
            bucket_name = input("Enter GCP Storage bucket name: ").strip()
    else:
        bucket_name = input("Enter GCP Storage bucket name: ").strip()
    
    if not bucket_name:
        print("❌ Bucket name is required")
        return False
    
    # Get service account key
    current_key = config.get("GCP_SA_KEY_BASE64", "")
    if current_key:
        print(f"\nCurrent service account key: {mask_secret(current_key)}")
        use_current = input("Use current key? (y/n, default: y): ").strip().lower()
        if use_current != 'n':
            sa_key = current_key
        else:
            print("\nEnter service account key:")
            print("  Option 1: Paste base64-encoded JSON key")
            print("  Option 2: Enter path to JSON key file (will be encoded)")
            choice = input("Choice (1/2, default: 1): ").strip() or "1"
            
            if choice == "2":
                key_path = input("Enter path to JSON key file: ").strip()
                if os.path.exists(key_path):
                    try:
                        import base64
                        with open(key_path, 'rb') as f:
                            key_data = f.read()
                        sa_key = base64.b64encode(key_data).decode('utf-8')
                        print("✓ Key file encoded successfully")
                    except Exception as e:
                        print(f"❌ Error reading key file: {e}")
                        return False
                else:
                    print(f"❌ File not found: {key_path}")
                    return False
            else:
                print("Paste base64-encoded service account key (input will be hidden):")
                sa_key = getpass.getpass("Key: ").strip()
    else:
        print("\nEnter service account key:")
        print("  Option 1: Paste base64-encoded JSON key")
        print("  Option 2: Enter path to JSON key file (will be encoded)")
        choice = input("Choice (1/2, default: 1): ").strip() or "1"
        
        if choice == "2":
            key_path = input("Enter path to JSON key file: ").strip()
            if os.path.exists(key_path):
                try:
                    import base64
                    with open(key_path, 'rb') as f:
                        key_data = f.read()
                    sa_key = base64.b64encode(key_data).decode('utf-8')
                    print("✓ Key file encoded successfully")
                except Exception as e:
                    print(f"❌ Error reading key file: {e}")
                    return False
            else:
                print(f"❌ File not found: {key_path}")
                return False
        else:
            print("Paste base64-encoded service account key (input will be hidden):")
            sa_key = getpass.getpass("Key: ").strip()
    
    if not sa_key:
        print("❌ Service account key is required")
        return False
    
    # Validate configuration
    print("\nValidating configuration...")
    try:
        # Try to decode the key
        import base64
        decoded = base64.b64decode(sa_key)
        import json
        key_json = json.loads(decoded)
        if "type" not in key_json or key_json.get("type") != "service_account":
            print("⚠️  Warning: Key doesn't appear to be a service account key")
        else:
            print("✓ Key format is valid")
    except Exception as e:
        print(f"⚠️  Warning: Could not validate key format: {e}")
        continue_anyway = input("Continue anyway? (y/n, default: n): ").strip().lower()
        if continue_anyway != 'y':
            return False
    
    # Save configuration
    print("\nSaving configuration...")
    config.set("GCP_STORAGE_BUCKET", bucket_name)
    config.set("GCP_SA_KEY_BASE64", sa_key)
    
    print(f"✓ Configuration saved:")
    print(f"  Bucket: {bucket_name}")
    print(f"  Key: {mask_secret(sa_key)}")
    print("\n✅ GCP setup complete!")
    
    return True


def interactive_setup_minimal(config: ConfigManager) -> bool:
    """
    Interactive setup for minimal required configuration.
    Only asks for essential variables with sensible defaults.
    
    Args:
        config: ConfigManager instance
        
    Returns:
        True if setup completed successfully
    """
    print("\n" + "=" * 70)
    print("Alchemux Setup Wizard")
    print("=" * 70)
    print("\nThis wizard will configure the minimal settings needed to get started.")
    print("All other options can be configured later in your .env file.\n")
    
    # Download path (required, with default)
    default_path = "./downloads"
    current_path = config.get("DOWNLOAD_PATH", default_path)
    
    print(f"Download path (where files will be saved):")
    print(f"  Default: {default_path}")
    if current_path != default_path:
        print(f"  Current: {current_path}")
    
    new_path = input(f"Enter path (or press Enter for default '{default_path}'): ").strip()
    
    if new_path:
        config.update_download_path(new_path)
        print(f"✓ Download path set to: {new_path}")
    else:
        config.update_download_path(default_path)
        print(f"✓ Using default download path: {default_path}")
    
    print("\n✅ Setup complete!")
    print(f"\nYour configuration has been saved to: {config.env_path}")
    print("\nOptional: Run 'amx setup gcp' (or 'alchemux setup gcp') later to configure cloud upload.")
    print("          Or edit .env directly to customize other settings.")
    
    return True


def interactive_s3_setup(config: ConfigManager) -> bool:
    """
    Interactive S3-compatible storage setup wizard.
    
    Args:
        config: ConfigManager instance
        
    Returns:
        True if setup completed successfully
    """
    print("\n" + "=" * 70)
    print("S3-Compatible Storage Setup")
    print("=" * 70)
    print("\nThis wizard will help you configure S3-compatible storage upload functionality.")
    print("You'll need:")
    print("  1. S3 endpoint URL (e.g., https://your-minio.cloudron.app)")
    print("  2. Access key")
    print("  3. Secret key")
    print("  4. Bucket name")
    print("  5. SSL enabled (true/false)")
    print()
    
    # Get endpoint
    current_endpoint = config.get("S3_ENDPOINT", "")
    if current_endpoint:
        print(f"Current endpoint: {current_endpoint}")
        use_current = input("Use current endpoint? (y/n, default: y): ").strip().lower()
        if use_current != 'n':
            endpoint = current_endpoint
        else:
            endpoint = input("Enter S3 endpoint URL: ").strip()
    else:
        endpoint = input("Enter S3 endpoint URL: ").strip()
    
    if not endpoint:
        print("❌ Endpoint is required")
        return False
    
    # Get access key
    current_access_key = config.get("S3_ACCESS_KEY", "")
    if current_access_key:
        print(f"\nCurrent access key: {mask_secret(current_access_key)}")
        use_current = input("Use current access key? (y/n, default: y): ").strip().lower()
        if use_current != 'n':
            access_key = current_access_key
        else:
            print("Enter S3 access key (input will be hidden):")
            access_key = getpass.getpass("Access key: ").strip()
    else:
        print("\nEnter S3 access key (input will be hidden):")
        access_key = getpass.getpass("Access key: ").strip()
    
    if not access_key:
        print("❌ Access key is required")
        return False
    
    # Get secret key
    current_secret_key = config.get("S3_SECRET_KEY", "")
    if current_secret_key:
        print(f"\nCurrent secret key: {mask_secret(current_secret_key)}")
        use_current = input("Use current secret key? (y/n, default: y): ").strip().lower()
        if use_current != 'n':
            secret_key = current_secret_key
        else:
            print("Enter S3 secret key (input will be hidden):")
            secret_key = getpass.getpass("Secret key: ").strip()
    else:
        print("\nEnter S3 secret key (input will be hidden):")
        secret_key = getpass.getpass("Secret key: ").strip()
    
    if not secret_key:
        print("❌ Secret key is required")
        return False
    
    # Get bucket name
    current_bucket = config.get("S3_BUCKET", "")
    if current_bucket:
        print(f"\nCurrent bucket: {current_bucket}")
        use_current = input("Use current bucket? (y/n, default: y): ").strip().lower()
        if use_current != 'n':
            bucket_name = current_bucket
        else:
            bucket_name = input("Enter S3 bucket name: ").strip()
    else:
        bucket_name = input("\nEnter S3 bucket name: ").strip()
    
    if not bucket_name:
        print("❌ Bucket name is required")
        return False
    
    # Get SSL setting
    current_ssl = config.get("S3_SSL", "true").lower() == "true"
    print(f"\nSSL enabled (current: {current_ssl}):")
    ssl_input = input("Enable SSL? (y/n, default: y): ").strip().lower()
    ssl_enabled = ssl_input != 'n'
    
    # Save configuration
    print("\nSaving configuration...")
    config.set("S3_ENDPOINT", endpoint)
    config.set("S3_ACCESS_KEY", access_key)
    config.set("S3_SECRET_KEY", secret_key)
    config.set("S3_BUCKET", bucket_name)
    config.set("S3_SSL", "true" if ssl_enabled else "false")
    
    print(f"✓ Configuration saved:")
    print(f"  Endpoint: {endpoint}")
    print(f"  Bucket: {bucket_name}")
    print(f"  Access Key: {mask_secret(access_key)}")
    print(f"  SSL: {ssl_enabled}")
    print("\n✅ S3 setup complete!")
    
    return True


def smart_setup(config: ConfigManager, console: "ArcaneConsole") -> bool:
    """
    Intelligent setup that detects existing .env and handles EULA acceptance.
    
    - If .env doesn't exist, creates it from env.example automatically
    - Checks if minimal required variables are set
    - Handles EULA acceptance on first run
    - If .env exists with minimal config, informs user and advises next steps
    
    Args:
        config: ConfigManager instance
        console: ArcaneConsole instance for output
        
    Returns:
        True if setup completed successfully
    """
    env_exists = config.check_env_file_exists()
    env_example_path = config.env_path.parent / "env.example"
    
    # If .env doesn't exist, create it from env.example
    if not env_exists:
        console.console.print("\n[dim]No .env file detected. Creating from env.example...[/dim]")
        
        if env_example_path.exists():
            # Use the existing method to create .env from example
            config._create_env_from_example()
            console.console.print(f"[green]✓[/green] Created .env from {env_example_path}")
        else:
            # Create minimal .env if example doesn't exist
            config.set("DOWNLOAD_PATH", "./downloads")
            config.set("AUTO_OPEN", "true")
            config.set("ARCANE_TERMS", "true")
            console.console.print("[green]✓[/green] Created minimal .env file")
        
        # Reload to get the new values
        from dotenv import load_dotenv
        load_dotenv(config.env_path)
    
    # Check EULA acceptance (only required for packaged builds)
    from app.core.eula import is_packaged_build
    if is_packaged_build():
        eula_manager = EULAManager(config)
        if not eula_manager.is_accepted():
            console.console.print("\n[yellow]⚠[/yellow]  EULA acceptance required for first run")
            if not eula_manager.interactive_acceptance():
                console.print_fracture("setup", "EULA not accepted. Setup cancelled.")
                return False
            console.console.print("[green]✓[/green] EULA accepted")
    else:
        # Running from source - EULA not required (Apache 2.0 license applies)
        logger.debug("Running from source - EULA check skipped")
    
    # Check if minimal required variables are set
    required_vars = ["DOWNLOAD_PATH"]
    is_valid, missing = config.validate_required(required_vars)
    
    if not is_valid:
        # Missing required variables - run minimal interactive setup
        console.console.print("\n[dim]Some required configuration is missing. Running minimal setup...[/dim]")
        return interactive_setup_minimal(config)
    
    # .env exists and has minimal required config
    console.console.print("\n[green]✓[/green] Configuration detected")
    console.console.print(f"[dim]Using .env file at: {config.env_path}[/dim]")
    
    # Check what's configured
    download_path = config.get("DOWNLOAD_PATH", "./downloads")
    gcp_configured = bool(config.get("GCP_STORAGE_BUCKET") and config.get("GCP_SA_KEY_BASE64"))
    s3_configured = bool(
        config.get("S3_ENDPOINT") and 
        config.get("S3_ACCESS_KEY") and 
        config.get("S3_SECRET_KEY") and 
        config.get("S3_BUCKET")
    )
    
    console.console.print(f"\n[bold]Current configuration:[/bold]")
    console.console.print(f"  Download path: {download_path}")
    console.console.print(f"  GCP storage: {'[green]configured[/green]' if gcp_configured else '[dim]not configured[/dim]'}")
    console.console.print(f"  S3 storage: {'[green]configured[/green]' if s3_configured else '[dim]not configured[/dim]'}")
    
    console.console.print("\n[bold]Next steps:[/bold]")
    console.console.print("  • To configure cloud storage, run:")
    if not gcp_configured:
        console.console.print("    [cyan]alchemux setup gcp[/cyan]  (for Google Cloud Platform)")
    if not s3_configured:
        console.console.print("    [cyan]alchemux setup s3[/cyan]   (for S3-compatible storage)")
    console.console.print("  • To customize other settings, edit .env directly")
    console.console.print(f"    [dim]Location: {config.env_path}[/dim]")
    
    return True

