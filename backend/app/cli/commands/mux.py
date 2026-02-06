"""
Mux command - Inscribes metadata into media files.
"""

from pathlib import Path
from typing import Optional

import typer

from app.cli.output import ArcaneConsole
from app.core.logger import setup_logger
from app.utils.metadata import write_source_url_to_metadata

logger = setup_logger(__name__)


def mux(
    file_path: str = typer.Argument(..., help="Path to media file"),
    source_url: Optional[str] = typer.Option(
        None, "--source-url", help="Source URL to inscribe"
    ),
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Inscribe metadata into a media vessel.

    This rite writes source information and other arcane inscriptions into
    an existing media file. The metadata becomes part of the vessel's essence,
    allowing future inspection to reveal its origin. Without a source URL,
    the rite cannot proceed, as there is nothing to inscribe.
    """
    # Read arcane_terms from env, default True
    import os

    arcane_terms = os.getenv("ARCANE_TERMS", "true").lower() in ("1", "true", "yes")
    console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)

    file = Path(file_path)
    if not file.exists():
        console.print_fracture("mux", f"file not found: {file_path}")
        raise typer.Exit(code=1)

    if not source_url:
        console.print_fracture("mux", "source URL required (use --source-url)")
        raise typer.Exit(code=1)

    console.print_phase_header("⌘ MUXING")
    console.print_stage("mux", "inscribing metadata...")

    success = write_source_url_to_metadata(str(file), source_url)

    if success:
        console.print_success("mux", "inscription complete")
        logger.debug(f"Source URL written to metadata: {file_path}")
    else:
        console.print_fracture("mux", "metadata write failed")
        raise typer.Exit(code=1)
