"""
Config command - Interactive configuration wizard.
"""
import typer

from app.cli.output import ArcaneConsole
from app.core.config_manager import ConfigManager

app = typer.Typer(
    name="config",
    help="Interactive configuration wizard for config.toml",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def config_main(
    ctx: typer.Context,
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Interactive configuration wizard for existing config.toml settings.
    
    Launches an interactive wizard that allows you to selectively reconfigure
    existing settings in config.toml. For direct editing, modify config.toml manually.
    
    Example:
        alchemux config    # Launch interactive wizard
    """
    import os
    arcane_terms = os.getenv("ARCANE_TERMS", "true").lower() in ("1", "true", "yes")
    console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)
    
    config_manager = ConfigManager()
    
    # Check if config.toml exists
    if not config_manager.check_toml_file_exists():
        console.print_fracture("config", "config.toml not found. Run 'alchemux setup' first to create it.")
        raise typer.Exit(code=1)
    
    from app.core.config_wizard import interactive_config_wizard
    
    try:
        success = interactive_config_wizard(config_manager)
        if not success:
            raise typer.Exit(code=1)
    except KeyboardInterrupt:
        console.console.print("\n[yellow]Configuration cancelled.[/yellow]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print_fracture("config", f"Configuration wizard failed: {e}")
        raise typer.Exit(code=1)

