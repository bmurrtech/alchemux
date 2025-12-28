"""
Inspect command - Display metadata from a media file.
"""
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from app.cli.output import ArcaneConsole
from app.core.logger import setup_logger
from app.utils.metadata import read_source_url_from_metadata

logger = setup_logger(__name__)


def inspect(
    file_path: str = typer.Argument(..., help="Path to media file to inspect"),
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Inspect a media vessel's metadata.
    
    This rite reveals the hidden inscriptions within a media file, displaying
    source URLs, format information, file size, and other arcane metadata.
    Use this to verify the vessel's origin and properties before further rites.
    """
    # Read arcane_terms from env, default True
    import os
    arcane_terms = os.getenv("ARCANE_TERMS", "true").lower() in ("1", "true", "yes")
    console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)
    
    file = Path(file_path)
    if not file.exists():
        console.print_fracture("inspect", f"file not found: {file_path}")
        raise typer.Exit(code=1)
    
    if not file.is_file():
        console.print_fracture("inspect", f"path is not a file: {file_path}")
        raise typer.Exit(code=1)
    
    # Read metadata
    source_url = read_source_url_from_metadata(str(file))
    
    # Get file info
    stat = file.stat()
    size_mb = stat.st_size / (1024 * 1024)
    ext = file.suffix.lower()
    
    # Create table
    table = Table(title="Media Vessel Inspection", show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Path", str(file))
    table.add_row("Size", f"{size_mb:.2f} MB")
    table.add_row("Format", ext or "unknown")
    table.add_row("Source URL", source_url or "Not inscribed")
    
    console.console.print()
    console.console.print(Panel(table, border_style="green"))
    console.console.print()

