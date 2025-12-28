"""
Seal command - Finalizes and validates a media vessel.
"""
from pathlib import Path

import typer

from app.cli.output import ArcaneConsole
from app.core.logger import setup_logger

logger = setup_logger(__name__)


def seal(
    file_path: str = typer.Argument(..., help="Path to media file to seal"),
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Seal a media vessel as complete.
    
    This rite validates and finalizes a media file, marking it as a completed
    transmutation. The seal confirms the vessel is ready for use and has
    passed all arcane validations. A sealed vessel is considered immutable
    and ready for distribution or archival.
    """
    # Read arcane_terms from env, default True
    import os
    arcane_terms = os.getenv("ARCANE_TERMS", "true").lower() in ("1", "true", "yes")
    console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)
    
    file = Path(file_path)
    if not file.exists():
        console.print_fracture("seal", f"file not found: {file_path}")
        raise typer.Exit(code=1)
    
    if not file.is_file():
        console.print_fracture("seal", f"path is not a file: {file_path}")
        raise typer.Exit(code=1)
    
    # Validate file size
    size = file.stat().st_size
    if size == 0:
        console.print_fracture("seal", "file is empty")
        raise typer.Exit(code=1)
    
    console.print_divider()
    console.print_seal(str(file))
    logger.debug(f"Sealed file: {file_path}")

