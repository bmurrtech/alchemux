"""
Plain command - Toggle plain mode (disable colors/animations) in config.toml.
"""
import typer
from rich.console import Console

from app.core.config_manager import ConfigManager

console = Console()


def plain_command(
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Toggle plain mode.
    
    Enables or disables plain mode (no colors or animations).
    The setting is saved to config.toml.
    """
    config = ConfigManager()
    
    # Ensure config files exist
    if not config.check_env_file_exists():
        config._create_env_from_example()
    if not config.check_toml_file_exists():
        config._create_toml_from_example()
    
    try:
        # Get current plain setting
        current_plain = config.get("ui.plain", "false")
        current_plain_bool = current_plain.lower() in ("true", "1", "yes") if isinstance(current_plain, str) else bool(current_plain)
        
        # Toggle the setting
        new_value = "false" if current_plain_bool else "true"
        config.set("ui.plain", new_value)
        
        # Show confirmation
        status = "activated" if new_value.lower() == "true" else "deactivated"
        console.print()
        console.print(f"[green]✓[/green] Plain mode {status}")
        console.print(f"[dim]Configuration saved to: {config.toml_path}[/dim]")
        console.print()
    except Exception as e:
        console.print()
        console.print(f"[red]✗[/red] Failed to update configuration: {e}")
        console.print()
        raise typer.Exit(code=1)
