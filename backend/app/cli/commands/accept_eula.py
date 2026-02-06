"""
Accept EULA command - Accept EULA non-interactively.
"""

import typer
from rich.console import Console

from app.core.config_manager import ConfigManager
from app.core.eula import EULAManager

console = Console()


def accept_eula_command(
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Accept EULA non-interactively.

    Records EULA acceptance in both eula_config.json and config.toml.
    """
    config = ConfigManager()

    # Ensure config files exist
    if not config.check_env_file_exists():
        config._create_env_from_example()
    if not config.check_toml_file_exists():
        config._create_toml_from_example()

    # Accept EULA
    eula_manager = EULAManager(config)
    eula_manager.accept("command")

    # Show confirmation
    console.print()
    console.print("[green]✓[/green] EULA accepted")
    console.print(f"[dim]Configuration saved to: {config.toml_path}[/dim]")
    console.print()
