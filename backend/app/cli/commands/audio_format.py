"""
Audio format command - Interactive audio format selection using Rich.
"""
import os
import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

from app.core.config_manager import ConfigManager

# Supported audio formats
SUPPORTED_AUDIO_FORMATS = [
    "mp3",
    "aac",
    "alac",
    "flac",
    "m4a",
    "opus",
    "vorbis",
    "wav",
]


def audio_format_command(
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Interactive audio format selection.
    
    Displays a list of supported audio codecs for you to select from.
    Your selection will be saved as the default format in config.toml.
    """
    config = ConfigManager()
    
    # Ensure config files exist
    if not config.check_env_file_exists():
        config._create_env_from_example()
    if not config.check_toml_file_exists():
        config._create_toml_from_example()
    
    # Get current format
    current_format = config.get("media.audio.format", "mp3")
    
    console = Console(force_terminal=not plain, no_color=plain)
    
    # Display selection UI
    console.print()
    console.print(Panel.fit("[bold cyan]Audio Format Selection[/bold cyan]", border_style="cyan"))
    console.print(f"\n[dim]Current default format:[/dim] [bold]{current_format}[/bold]\n")
    console.print("[bold]Supported audio formats:[/bold]\n")
    
    for i, fmt in enumerate(SUPPORTED_AUDIO_FORMATS, 1):
        marker = ">" if fmt == current_format else " "
        style = "bold cyan" if fmt == current_format else ""
        console.print(f"  {marker} {i}. {fmt}", style=style)
    
    console.print()
    
    # Get user selection
    while True:
        choice = Prompt.ask(
            "Select format (enter number or format name, or press Enter for current)",
            default=current_format,
            console=console,
        )
        
        # If Enter was pressed with default, use current
        if not choice.strip():
            selected_format = current_format
            break
        
        # Try to parse as number
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(SUPPORTED_AUDIO_FORMATS):
                selected_format = SUPPORTED_AUDIO_FORMATS[choice_num - 1]
                break
        except ValueError:
            pass
        
        # Try to match format name
        choice_lower = choice.lower().strip()
        if choice_lower in SUPPORTED_AUDIO_FORMATS:
            selected_format = choice_lower
            break
        
        console.print(f"[red]Invalid selection. Please enter a number (1-{len(SUPPORTED_AUDIO_FORMATS)}) or format name.[/red]")
    
    # Save to config if changed
    if selected_format != current_format:
        try:
            config.set("media.audio.format", selected_format)
            
            # Show confirmation
            console.print()
            console.print(f"[green]✓[/green] Default audio format set to: [bold]{selected_format}[/bold]")
            console.print(f"[dim]Configuration saved to: {config.toml_path}[/dim]")
            console.print()
        except Exception as e:
            console.print()
            console.print(f"[red]✗[/red] Failed to save configuration: {e}")
            console.print()
            raise typer.Exit(code=1)
    else:
        console.print()
        console.print(f"[dim]Audio format unchanged: {current_format}[/dim]")
        console.print()
