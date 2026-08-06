"""Scry / inspect — reveal what Alchemux knows about a sealed media file."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from app.cli.output import ArcaneConsole
from app.cli.prompts import select
from app.core.config_manager import ConfigManager, get_default_output_dir
from app.core.logger import setup_logger
from app.utils.scry import ScryError, ScryReport, list_media_under, scry_file

logger = setup_logger(__name__)


def _arcane_terms() -> bool:
    return os.getenv("ARCANE_TERMS", "true").lower() in ("1", "true", "yes")


def _resolve_output_dir(config: ConfigManager) -> Path:
    raw = config.get("paths.output_dir") or str(get_default_output_dir())
    return Path(raw).expanduser().resolve()


def _fracture_stage(console: ArcaneConsole) -> str:
    """Pipeline 'scry' means detect-source; command fractures use scry/inspect by mode."""
    return "scry" if console.arcane_terms else "inspect"


def _pick_media_interactively(output_dir: Path, console: ArcaneConsole) -> Path:
    media = list_media_under(output_dir)
    if not media:
        console.print_fracture(
            _fracture_stage(console),
            f"no media files found under {output_dir}",
        )
        raise typer.Exit(code=1)

    # Prefer short labels relative to output dir when possible.
    choices: list[tuple[str, str]] = []
    for path in media:
        try:
            label = str(path.relative_to(output_dir))
        except ValueError:
            label = str(path)
        choices.append((str(path), label))

    picked = select(
        message="Select media to inspect",
        choices=choices,
        default=choices[0][0] if choices else None,
    )
    if not picked:
        console.print_fracture(_fracture_stage(console), "no selection")
        raise typer.Exit(code=1)
    return Path(picked)


def _kv_table(rows: list[tuple[str, str]], title: str) -> Table:
    table = Table(title=title, show_header=False, box=None, padding=(0, 2))
    table.add_column("key", style="cyan", no_wrap=True)
    table.add_column("value", style="green")
    for key, value in rows:
        if value:
            table.add_row(key, value)
    return table


def _render_report(
    report: ScryReport,
    *,
    console: Console,
    verbose: bool,
) -> None:
    console.print()
    console.print(Rule("[bold]Media Information[/bold]"))
    console.print()

    general = [
        ("File", report.filename),
        ("Path", report.path),
        ("Size", report.size_human),
        ("Container", report.format_name),
    ]
    console.print(_kv_table(general, "General"))

    media_rows = [
        ("Duration", report.duration_human),
        ("Codec", report.codec),
        ("Bitrate", report.bitrate_human),
    ]
    if report.sample_rate:
        media_rows.append(("Sample rate", f"{report.sample_rate} Hz"))
    if report.channels is not None:
        media_rows.append(("Channels", str(report.channels)))
    if report.width and report.height:
        media_rows.append(("Resolution", f"{report.width}×{report.height}"))
    console.print()
    console.print(_kv_table(media_rows, "Media"))

    meta_rows = [
        ("Title", report.title),
        ("Artist", report.artist),
        ("Album", report.album),
        ("Published", report.date),
        ("Source", report.source_url),
        (
            "Description",
            "yes" if report.description_present else "no",
        ),
        ("Cover art", "yes" if report.has_cover_art else "no"),
        ("Chapters", str(len(report.chapters))),
    ]
    console.print()
    console.print(_kv_table(meta_rows, "Embedded Metadata"))

    if report.description_present and verbose and report.description:
        console.print()
        console.print(
            Panel(
                report.description[:4000],
                title="Description / Comment",
                border_style="dim",
            )
        )

    if report.chapters:
        console.print()
        ch_table = Table(title="Chapters", show_header=True, header_style="bold")
        ch_table.add_column("#", style="dim", width=4)
        ch_table.add_column("Start")
        ch_table.add_column("Title")
        for i, ch in enumerate(report.chapters, start=1):
            start = ch.get("start")
            try:
                start_s = f"{float(start):.2f}s" if start is not None else ""
            except (TypeError, ValueError):
                start_s = str(start or "")
            ch_table.add_row(str(i), start_s, str(ch.get("title") or ""))
        console.print(ch_table)

    companions: list[tuple[str, str]] = []
    if report.companion_info:
        companions.append(("Companion info", report.companion_info))
    if report.ytdlp_info_json:
        companions.append(("yt-dlp info.json", report.ytdlp_info_json))
    if companions:
        console.print()
        console.print(_kv_table(companions, "Sidecars"))

    if report.health:
        console.print()
        health = Table(title="Metadata Health", show_header=False, box=None)
        health.add_column("mark", width=2)
        health.add_column("label", style="cyan")
        health.add_column("detail", style="dim")
        for check in report.health:
            mark = "[green]✓[/green]" if check.ok else "[red]✗[/red]"
            health.add_row(mark, check.label, check.detail)
        console.print(health)

    if verbose and report.tags:
        console.print()
        tag_table = Table(title="All Tags", show_header=True, header_style="bold")
        tag_table.add_column("Key", style="cyan")
        tag_table.add_column("Value", style="green")
        for key in sorted(report.tags.keys(), key=str.lower):
            val = report.tags[key]
            if len(val) > 200:
                val = val[:197] + "…"
            tag_table.add_row(key, val)
        console.print(tag_table)

    console.print()


def _run_scry(
    file_path: Optional[str],
    *,
    verbose: bool,
    raw: bool,
    as_json: bool,
    plain: bool,
) -> None:
    arcane = _arcane_terms()
    try:
        config = ConfigManager()
        if config.check_toml_file_exists():
            # Prefer product.arcane_terms when config is available.
            val = config.get("product.arcane_terms")
            if val is not None and str(val).strip() != "":
                arcane = str(val).strip().lower() in ("1", "true", "yes")
    except Exception:
        config = ConfigManager()

    console = ArcaneConsole(plain=plain, arcane_terms=arcane)
    rich = console.console

    path: Optional[Path] = Path(file_path).expanduser() if file_path else None
    if path is None:
        output_dir = _resolve_output_dir(config)
        path = _pick_media_interactively(output_dir, console)
    elif not path.exists():
        console.print_fracture(_fracture_stage(console), f"file not found: {path}")
        raise typer.Exit(code=1)
    elif not path.is_file():
        console.print_fracture(_fracture_stage(console), f"path is not a file: {path}")
        raise typer.Exit(code=1)

    try:
        report, probe = scry_file(path)
    except ScryError as e:
        console.print_fracture(_fracture_stage(console), str(e))
        raise typer.Exit(code=1) from e

    if raw or as_json:
        payload: dict[str, Any]
        if raw and not as_json:
            payload = probe
        elif as_json and raw:
            payload = {"report": report.to_dict(), "ffprobe": probe}
        else:
            payload = report.to_dict()
        # Machine-readable stdout (no banner noise beyond what entrypoint already printed).
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    _render_report(report, console=rich, verbose=verbose)


def dispatch_from_argv(argv: list[str], *, command: str = "scry") -> None:
    """
    Run scry/inspect from argv tokens after the command name.

    Used when the root ``[URL]`` argument steals ``scry`` / ``inspect``.
    """
    file_path: Optional[str] = None
    verbose = False
    raw = False
    as_json = False
    plain = False
    show_help = False
    for token in argv:
        if token in ("--help", "-h"):
            show_help = True
        elif token == "--verbose":
            verbose = True
        elif token == "--raw":
            raw = True
        elif token == "--json":
            as_json = True
        elif token == "--plain":
            plain = True
        elif token.startswith("-"):
            continue
        elif file_path is None:
            file_path = token

    if show_help:
        name = "scry" if command == "scry" else "inspect"
        typer.echo(
            f"Usage: alchemux {name} [OPTIONS] [FILE]\n\n"
            "Inspect a media file (ffprobe + embedded tags + companion presence).\n\n"
            "Arguments:\n"
            "  FILE  Media path (omit to pick from paths.output_dir)\n\n"
            "Options:\n"
            "  --verbose  Full description + all tags\n"
            "  --raw      Raw ffprobe JSON\n"
            "  --json     Structured JSON summary\n"
            "  --plain    Disable colors\n"
            "  --help     Show this message\n"
        )
        raise typer.Exit(code=0)

    _run_scry(
        file_path,
        verbose=verbose,
        raw=raw,
        as_json=as_json,
        plain=plain,
    )


def scry(
    file_path: Optional[str] = typer.Argument(
        None,
        help="Media file to inspect (omit to pick from paths.output_dir)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Include full description text and all tag keys",
    ),
    raw: bool = typer.Option(
        False,
        "--raw",
        help="Print raw ffprobe JSON",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Print structured JSON summary (combine with --raw for both)",
    ),
    plain: bool = typer.Option(
        False,
        "--plain",
        help="Disable colors and animations",
    ),
) -> None:
    """
    Scry a media vessel — inspect embedded tags, streams, and companions.

    Technical alias: ``inspect``.
    """
    _run_scry(
        file_path,
        verbose=verbose,
        raw=raw,
        as_json=as_json,
        plain=plain,
    )


def inspect(
    file_path: Optional[str] = typer.Argument(
        None,
        help="Media file to inspect (omit to pick from paths.output_dir)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Include full description text and all tag keys",
    ),
    raw: bool = typer.Option(
        False,
        "--raw",
        help="Print raw ffprobe JSON",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Print structured JSON summary (combine with --raw for both)",
    ),
    plain: bool = typer.Option(
        False,
        "--plain",
        help="Disable colors and animations",
    ),
) -> None:
    """
    Inspect a media file (technical alias for ``scry``).
    """
    _run_scry(
        file_path,
        verbose=verbose,
        raw=raw,
        as_json=as_json,
        plain=plain,
    )
