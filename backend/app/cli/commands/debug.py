"""
Debug command - Toggle debug mode in config.toml.
"""

import typer
from rich.console import Console

from app.core.config_manager import ConfigManager
from app.core.logger import resolve_config_log_level

console = Console()


def debug_command(
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Toggle debug mode.

    Enables or disables debug mode with full tracebacks.
    The setting is saved to config.toml (`logging.level` + `logging.debug` alias).
    """
    config = ConfigManager()

    # Ensure config files exist
    if not config.check_env_file_exists():
        config._create_env_from_example()
    if not config.check_toml_file_exists():
        config._create_toml_from_example()

    try:
        current_level = resolve_config_log_level(
            level=config.get("logging.level"),
            debug=config.get("logging.debug"),
            verbose=config.get("logging.verbose"),
        )
        currently_debug = current_level == "debug"

        if currently_debug:
            config.set("logging.level", "warning")
            config.set("logging.debug", "false")
            config.set("logging.verbose", "false")
            status = "deactivated"
        else:
            config.set("logging.level", "debug")
            config.set("logging.debug", "true")
            config.set("logging.verbose", "false")
            status = "activated"

        console.print()
        console.print(f"[green]✓[/green] Debug mode {status}")
        console.print(
            "[dim]logging.level = "
            f"{'debug' if status == 'activated' else 'warning'}[/dim]"
        )
        console.print(f"[dim]Configuration saved to: {config.toml_path}[/dim]")
        console.print()
    except Exception as e:
        console.print()
        console.print(f"[red]✗[/red] Failed to update configuration: {e}")
        console.print()
        raise typer.Exit(code=1)
