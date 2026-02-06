"""
Invoke command - Orchestrates the full pipeline: scribe → scry → profile → distill → mux → seal.
"""

import os
from typing import Optional

import typer

from app.cli.commands.distill import distill


def invoke(
    url: str = typer.Argument(..., help="Source URL to transmute"),
    audio_format: Optional[str] = typer.Option(
        None, "--audio-format", "-a", help="Audio codec/format"
    ),
    video_format: Optional[str] = typer.Option(
        None, "--video-format", help="Video container"
    ),
    flac: bool = typer.Option(False, "--flac", help="FLAC 16kHz mono conversion"),
    save_path: Optional[str] = typer.Option(
        None,
        "--save-path",
        help="Custom output directory for this run (one-time override)",
    ),
    local: bool = typer.Option(
        False, "--local", help="Save to local storage (one-time override)"
    ),
    s3: bool = typer.Option(
        False, "--s3", help="Upload to S3 storage (one-time override)"
    ),
    gcp: bool = typer.Option(
        False, "--gcp", help="Upload to GCP storage (one-time override)"
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug mode with full tracebacks"
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose logging"),
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Invoke the full transmutation ritual.

    This rite orchestrates the complete pipeline: scribing, scrying, profiling,
    distillation, muxing, and sealing. It is the primary invocation for transforming
    a source URL into a purified media vessel.
    """
    # Set verbose logging if flag is set
    if verbose:
        os.environ["LOG_LEVEL"] = "debug"

    # Invoke distill which handles the full pipeline
    distill(
        url=url,
        audio_format=audio_format,
        video_format=video_format,
        flac=flac,
        save_path=save_path,
        local=local,
        s3=s3,
        gcp=gcp,
        debug=debug,
        plain=plain,
    )
