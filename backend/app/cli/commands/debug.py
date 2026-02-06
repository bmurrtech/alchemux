"""
Debug command - Toggle debug mode in config.toml.
"""

import typer
from rich.console import Console

from app.core.config_manager import ConfigManager

console = Console()


def debug_command(
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Toggle debug mode.

    Enables or disables debug mode with full tracebacks.
    The setting is saved to config.toml.
    """
    config = ConfigManager()

    # Ensure config files exist
    if not config.check_env_file_exists():
        config._create_env_from_example()
    if not config.check_toml_file_exists():
        config._create_toml_from_example()

    try:
        # Get current debug setting
        current_debug = config.get("logging.debug", "false")
        current_debug_bool = (
            current_debug.lower() in ("true", "1", "yes")
            if isinstance(current_debug, str)
            else bool(current_debug)
        )

        # Toggle the setting
        new_value = "false" if current_debug_bool else "true"
        config.set("logging.debug", new_value)

        # Show confirmation
        status = "activated" if new_value.lower() == "true" else "deactivated"
        console.print()
        console.print(f"[green]✓[/green] Debug mode {status}")
        console.print(f"[dim]Configuration saved to: {config.toml_path}[/dim]")
        console.print()
    except Exception as e:
        console.print()
        console.print(f"[red]✗[/red] Failed to update configuration: {e}")
        console.print()
        raise typer.Exit(code=1)
