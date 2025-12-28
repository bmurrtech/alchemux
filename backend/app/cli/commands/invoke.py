"""
Invoke command - Orchestrates the full pipeline: scribe → scry → profile → distill → mux → seal.
"""
import os
from typing import Optional

import typer

from app.cli.commands.distill import distill
from app.cli.output import ArcaneConsole


def invoke(
    url: str = typer.Argument(..., help="Source URL to transmute"),
    format: str = typer.Option("mp3", "--format", "-f", help="Audio codec/format"),
    video_format: Optional[str] = typer.Option(None, "--video-format", help="Video container"),
    flac: bool = typer.Option(False, "--flac", help="FLAC 16kHz mono conversion"),
    save_path: Optional[str] = typer.Option(None, "--save-path", help="Custom save location"),
    gcp: bool = typer.Option(False, "--gcp", help="Enable GCP Cloud Storage upload"),
    accept_eula: bool = typer.Option(False, "--accept-eula", help="Accept EULA non-interactively"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging"),
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Invoke the full transmutation ritual.
    
    This rite orchestrates the complete pipeline: scribing, scrying, profiling,
    distillation, muxing, and sealing. It is the primary invocation for transforming
    a source URL into a purified media vessel.
    """
    # Invoke distill which handles the full pipeline
    distill(
        url=url,
        format=format,
        video_format=video_format,
        flac=flac,
        save_path=save_path,
        gcp=gcp,
        accept_eula=accept_eula,
        verbose=verbose,
        plain=plain,
    )

