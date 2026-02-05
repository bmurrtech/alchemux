"""
Save default storage command - Interactive default storage selection.
"""
from typing import Optional
import typer
from rich.console import Console
from rich.prompt import Prompt

from app.cli.output import ArcaneConsole
from app.core.config_manager import ConfigManager


def save_default(
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Set default storage destination interactively.
    
    This rite allows you to configure the default storage destination for all
    future transmutations. You can choose to save locally, upload to GCP, or
    upload to S3 by default. This setting can be overridden per-run using
    the --gcp, --s3, or --local flags.
    """
    # Read arcane_terms from env, default True
    import os
    arcane_terms = os.getenv("ARCANE_TERMS", "true").lower() in ("1", "true", "yes")
    console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)
    
    config_manager = ConfigManager()
    
    # Get current defaults
    gcp_enabled = config_manager.get("GCP_UPLOAD_ENABLED", "false").lower() == "true"
    s3_enabled = config_manager.get("S3_UPLOAD_ENABLED", "false").lower() == "true"
    
    # Determine current default
    if gcp_enabled:
        current_default = "GCP"
    elif s3_enabled:
        current_default = "S3"
    else:
        current_default = "Local"
    
    # Display current setting
    console.console.print(f"\n[bold]Current default storage:[/bold] [cyan]{current_default}[/cyan]")
    console.console.print("\nSelect new default storage destination:\n")
    
    # Show options
    options = [
        ("1", "Local", "Save files locally only (no cloud upload)"),
        ("2", "GCP", "Upload to Google Cloud Platform by default"),
        ("3", "S3", "Upload to S3-compatible storage by default"),
    ]
    
    for num, name, desc in options:
        marker = "→" if name == current_default else " "
        console.console.print(f"  {marker} {num}. {name:<6} - {desc}")
    
    # Get user selection
    console.console.print()
    choice = Prompt.ask(
        "Select option (1-3)",
        choices=["1", "2", "3"],
        default="1" if current_default == "Local" else ("2" if current_default == "GCP" else "3")
    )
    
    # Update configuration based on selection
    if choice == "1":
        # Local
        config_manager.set("GCP_UPLOAD_ENABLED", "false")
        config_manager.set("S3_UPLOAD_ENABLED", "false")
        console.print_success("config", "Default storage set to Local")
        console.console.print("  Files will be saved locally only (no cloud upload)")
    elif choice == "2":
        # GCP
        config_manager.set("GCP_UPLOAD_ENABLED", "true")
        config_manager.set("S3_UPLOAD_ENABLED", "false")
        console.print_success("config", "Default storage set to GCP")
        console.console.print("  Files will be uploaded to Google Cloud Platform by default")
        console.console.print("  [dim]Note: GCP must be configured with 'alchemux setup gcp'[/dim]")
    elif choice == "3":
        # S3
        config_manager.set("GCP_UPLOAD_ENABLED", "false")
        config_manager.set("S3_UPLOAD_ENABLED", "true")
        console.print_success("config", "Default storage set to S3")
        console.console.print("  Files will be uploaded to S3-compatible storage by default")
        console.console.print("  [dim]Note: S3 must be configured with 'alchemux setup s3'[/dim]")
    
    console.console.print(f"\n[dim]Configuration saved to: {config_manager.env_path}[/dim]")
    console.console.print("[dim]You can override this default per-run using --gcp, --s3, or --local flags[/dim]")

