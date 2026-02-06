"""
Setup command - Interactive configuration wizard.
"""

from typing import Optional
import os
import typer
from rich.console import Console

from app.cli.output import ArcaneConsole
from app.cli.prompts import confirm
from app.core.config_manager import ConfigManager
from app.core.setup_wizard import (
    interactive_gcp_setup,
    interactive_s3_setup,
    smart_setup,
)


def setup(
    target: Optional[str] = typer.Argument(
        default=None,
        help="Setup target: 'gcp' or 's3' for cloud storage, or omit for minimal setup",
    ),
    reset: bool = typer.Option(
        False, "--reset", help="Restore default configuration (deletes existing config)"
    ),
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

    Flags:
    - --reset: Restore default configuration (with confirmation)
    """
    rich_console = Console()

    # Read arcane_terms from env, default True
    arcane_terms = os.getenv("ARCANE_TERMS", "true").lower() in ("1", "true", "yes")
    console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)

    config_manager = ConfigManager()

    # Handle --reset flag first
    if reset:
        rich_console.print()
        rich_console.print(
            "[bold yellow]This will reset all configuration to defaults.[/bold yellow]"
        )
        rich_console.print("Config files to delete:")
        rich_console.print(f"  - {config_manager.toml_path}")
        rich_console.print(f"  - {config_manager.env_path}")
        rich_console.print()

        if confirm("Continue with reset?", default=False) is True:
            # Delete existing config files
            if config_manager.toml_path.exists():
                config_manager.toml_path.unlink()
                rich_console.print(
                    f"[green]>[/green] Removed {config_manager.toml_path}"
                )
            if config_manager.env_path.exists():
                config_manager.env_path.unlink()
                rich_console.print(
                    f"[green]>[/green] Removed {config_manager.env_path}"
                )

            # Recreate from templates
            try:
                config_manager._create_toml_from_example()
                rich_console.print("[green]>[/green] Created config.toml from template")
            except Exception as e:
                rich_console.print(
                    f"[yellow]![/yellow] Could not create config.toml: {e}"
                )

            try:
                config_manager._create_env_from_example()
                rich_console.print("[green]>[/green] Created .env from template")
            except Exception as e:
                rich_console.print(f"[yellow]![/yellow] Could not create .env: {e}")

            rich_console.print()
            rich_console.print("[green]>[/green] Configuration reset to defaults")
            rich_console.print("[dim]Run 'alchemux setup' to reconfigure.[/dim]")
        else:
            rich_console.print("[yellow]Reset cancelled.[/yellow]")
        raise typer.Exit(code=0)

    # Handle specific cloud storage targets
    if target == "gcp":
        console.console.print("Configuring GCP Cloud Storage upload...")
        if interactive_gcp_setup(config_manager):
            console.print_success("setup", "GCP configuration complete")
        else:
            console.print_fracture("setup", "GCP configuration failed")
            raise typer.Exit(code=1)
    elif target == "s3":
        console.console.print("Configuring S3-compatible storage upload...")
        if interactive_s3_setup(config_manager):
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
        # No target specified - run smart setup (full refresh)
        try:
            if smart_setup(config_manager, console):
                console.print_success("setup", "Setup complete")
                raise typer.Exit(code=0)
            else:
                console.print_fracture("setup", "Setup failed")
                raise typer.Exit(code=1)
        except typer.Exit:
            # Re-raise typer.Exit to ensure proper exit
            raise
        except Exception as e:
            if os.getenv("LOG_LEVEL", "").lower() == "debug":
                error_msg = str(e) if e else "Unknown error"
                console.print_fracture("setup", f"Setup error: {error_msg}")
                import traceback

                traceback.print_exc()
            raise typer.Exit(code=1)
