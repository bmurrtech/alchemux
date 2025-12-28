"""
Setup command - Interactive configuration wizard.
"""
from typing import Optional
import typer

from app.cli.output import ArcaneConsole
from app.core.config_manager import ConfigManager
from app.core.setup_wizard import (
    interactive_gcp_setup,
    interactive_s3_setup,
    interactive_setup_minimal,
    smart_setup,
)


def setup(
    target: Optional[str] = typer.Argument(None, help="Setup target: 'gcp' or 's3' for cloud storage, or omit for minimal setup"),
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Run interactive setup wizard.
    
    This rite guides you through the initial configuration of Alchemux,
    setting up download paths, cloud storage credentials, and other arcane
    parameters required for the transmutation rituals. The wizard ensures
    all necessary components are properly bound before use.
    
    Available targets:
    - (none): Minimal setup - creates .env if missing, handles EULA acceptance
    - gcp: Configure Google Cloud Platform storage for uploads
    - s3: Configure S3-compatible storage for uploads
    """
    # Read arcane_terms from env, default True
    import os
    arcane_terms = os.getenv("ARCANE_TERMS", "true").lower() in ("1", "true", "yes")
    console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)
    config = ConfigManager()
    
    # Handle specific cloud storage targets
    if target == "gcp":
        console.console.print("Configuring GCP Cloud Storage upload...")
        if interactive_gcp_setup(config):
            console.print_success("setup", "GCP configuration complete")
        else:
            console.print_fracture("setup", "GCP configuration failed")
            raise typer.Exit(code=1)
    elif target == "s3":
        console.console.print("Configuring S3-compatible storage upload...")
        if interactive_s3_setup(config):
            console.print_success("setup", "S3 configuration complete")
        else:
            console.print_fracture("setup", "S3 configuration failed")
            raise typer.Exit(code=1)
    elif target is not None:
        # Unknown target
        console.print_fracture("setup", f"Unknown setup target: {target}")
        console.console.print("\nAvailable targets:")
        console.console.print("  (none) - Minimal setup")
        console.console.print("  gcp    - Google Cloud Platform storage")
        console.console.print("  s3     - S3-compatible storage")
        raise typer.Exit(code=1)
    else:
        # No target specified - run smart setup
        if smart_setup(config, console):
            console.print_success("setup", "Setup complete")
        else:
            console.print_fracture("setup", "Setup failed")
            raise typer.Exit(code=1)

