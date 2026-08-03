"""
Verbose command - Toggle verbose logging in config.toml.
"""

import typer
from rich.console import Console

from app.core.config_manager import ConfigManager
from app.core.logger import resolve_config_log_level

console = Console()


def verbose_command(
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Toggle verbose logging.

    Enables or disables verbose logging (info-level detail without full debug
    tracebacks). Saved to config.toml as `logging.level` + `logging.verbose`.
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
        currently_verbose = current_level in ("verbose", "debug")

        if currently_verbose:
            config.set("logging.level", "warning")
            config.set("logging.verbose", "false")
            config.set("logging.debug", "false")
            status = "deactivated"
            shown = "warning"
        else:
            config.set("logging.level", "verbose")
            config.set("logging.verbose", "true")
            config.set("logging.debug", "false")
            status = "activated"
            shown = "verbose"

        console.print()
        console.print(f"[green]✓[/green] Verbose logging {status}")
        console.print(f"[dim]logging.level = {shown}[/dim]")
        console.print(f"[dim]Configuration saved to: {config.toml_path}[/dim]")
        console.print()
    except Exception as e:
        console.print()
        console.print(f"[red]✗[/red] Failed to update configuration: {e}")
        console.print()
        raise typer.Exit(code=1)
