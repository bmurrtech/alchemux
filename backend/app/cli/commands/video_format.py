"""
Video format command - Interactive video format selection using Rich.
"""
import os
import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

from app.core.config_manager import ConfigManager

# Supported video formats
SUPPORTED_VIDEO_FORMATS = [
    "mp4",
    "mkv",
    "webm",
    "mov",
    "avi",
    "flv",
    "gif",
]


def video_format_command(
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Interactive video format selection.

    Displays a list of supported video containers for you to select from.
    Your selection will be saved as the default format in config.toml.
    """
    config = ConfigManager()

    # Ensure config files exist
    if not config.check_env_file_exists():
        config._create_env_from_example()
    if not config.check_toml_file_exists():
        config._create_toml_from_example()

    # Get current format
    current_format = config.get("media.video.format", "")

    console = Console(force_terminal=not plain, no_color=plain)

    # Display selection UI
    console.print()
    console.print(Panel.fit("[bold cyan]Video Format Selection[/bold cyan]", border_style="cyan"))
    console.print(f"\n[dim]Current default format:[/dim] [bold]{current_format or '(none/default)'}[/bold]\n")
    console.print("[bold]Supported video formats:[/bold]\n")

    # Show options (0 = none/default)
    console.print(f"   0. (none/default)")
    for i, fmt in enumerate(SUPPORTED_VIDEO_FORMATS, 1):
        marker = ">" if fmt == current_format else " "
        style = "bold cyan" if fmt == current_format else ""
        console.print(f"  {marker} {i}. {fmt}", style=style)

    console.print()

    # Get user selection
    while True:
        default_display = str(current_format) if current_format else "0"
        choice = Prompt.ask(
            "Select format (enter number or format name, or press Enter for current)",
            default=default_display,
            console=console,
        )

        # If Enter was pressed with default, use current
        if not choice.strip():
            selected_format = current_format
            break

        # Try to parse as number
        try:
            choice_num = int(choice)
            if choice_num == 0:
                selected_format = ""
                break
            elif 1 <= choice_num <= len(SUPPORTED_VIDEO_FORMATS):
                selected_format = SUPPORTED_VIDEO_FORMATS[choice_num - 1]
                break
        except ValueError:
            pass

        # Try to match format name
        choice_lower = choice.lower().strip()
        if choice_lower in SUPPORTED_VIDEO_FORMATS:
            selected_format = choice_lower
            break
        elif choice_lower in ("none", "default", ""):
            selected_format = ""
            break

        console.print(f"[red]Invalid selection. Please enter a number (0-{len(SUPPORTED_VIDEO_FORMATS)}) or format name.[/red]")

    # Save to config
    try:
        config.set("media.video.format", selected_format)

        # Show confirmation
        console.print()
        if selected_format:
            console.print(f"[green]✓[/green] Default video format set to: [bold]{selected_format}[/bold]")
        else:
            console.print(f"[green]✓[/green] Video format set to: [bold](none/default)[/bold]")
        console.print(f"[dim]Configuration saved to: {config.toml_path}[/dim]")
        console.print()
    except Exception as e:
        console.print()
        console.print(f"[red]✗[/red] Failed to save configuration: {e}")
        console.print()
        raise typer.Exit(code=1)
