"""
Batch command - Process multiple URLs from files, paste, or playlist.

PRD 009: Batch Mode v1. Reuses existing invoke/distill pipeline per URL;
batch-only pacing via yt-dlp sleep options. No report file by default.
"""
from pathlib import Path
from typing import List, Optional

import typer

from app.cli.url_input import SETUP_REQUIRED_MSG, is_tty

try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
except ImportError:
    inquirer = None
    Choice = None


BATCH_REQUIRES_TTY_MSG = (
    "Batch mode requires an interactive terminal. Run alchemux batch in a TTY."
)
NO_BATCH_URLS_MSG = "No URLs to process."
BATCH_SOURCE_FILES = "files"
BATCH_SOURCE_PASTE = "paste"
BATCH_SOURCE_PLAYLIST = "playlist"


def _check_prerequisites() -> bool:
    """Return True if setup is complete (config exists; EULA accepted when packaged)."""
    from app.core.config_manager import ConfigManager
    from app.core.eula import EULAManager, is_packaged_build

    config = ConfigManager()
    if not config.check_toml_file_exists():
        return False
    if is_packaged_build():
        eula = EULAManager(config)
        if not eula.is_accepted():
            return False
    return True


def batch() -> None:
    """
    Run batch transmutation: load URLs from files (TXT/CSV), paste, or playlist,
    then process each URL with the same pipeline. Delays between items are applied
    automatically via yt-dlp to reduce rate-limit risk.
    """
    if not is_tty():
        typer.echo(BATCH_REQUIRES_TTY_MSG)
        raise typer.Exit(code=1)

    if not _check_prerequisites():
        typer.echo(SETUP_REQUIRED_MSG)
        raise typer.Exit(code=1)

    if inquirer is None:
        typer.echo("Batch mode requires InquirerPy. Install with: pip install InquirerPy")
        raise typer.Exit(code=1)

    _run_batch_flow()


def _run_batch_flow() -> None:
    """Interactive batch flow: source selection, URL collection, overrides, execution."""
    try:
        source = inquirer.select(
            message="Choose batch source",
            choices=[
                Choice(BATCH_SOURCE_FILES, name="Files from config dir"),
                Choice(BATCH_SOURCE_PASTE, name="Paste URLs"),
                Choice(BATCH_SOURCE_PLAYLIST, name="Playlist URL"),
            ],
        ).execute()
    except (KeyboardInterrupt, Exception):
        typer.echo("Canceled.")
        raise typer.Exit(130)

    if source == BATCH_SOURCE_FILES:
        urls = _get_urls_from_files()
    elif source == BATCH_SOURCE_PASTE:
        urls = _get_urls_from_paste()
    else:
        urls = _get_urls_from_playlist()

    if not urls:
        typer.echo(NO_BATCH_URLS_MSG)
        raise typer.Exit(0)

    # Reuse PRD6 overrides confirm + checkbox
    from app.cli.url_input import _interactive_overrides_prompt
    try:
        overrides = _interactive_overrides_prompt()
    except typer.Exit as e:
        raise e

    _run_batch_execution(urls, overrides)


def _get_urls_from_files() -> List[str]:
    """Collect URLs from .txt/.csv files in config dir (checkbox selection). Implemented in C."""
    return _collect_urls_from_files()


def _get_urls_from_paste() -> List[str]:
    """Collect URLs from multi-line paste. Implemented in E."""
    return _collect_urls_from_paste()


def _get_urls_from_playlist() -> List[str]:
    """Expand playlist URL to entry URLs via yt-dlp. Implemented in F."""
    return _collect_urls_from_playlist()


def _format_file_size(num_bytes: int) -> str:
    """Human-readable size (e.g. 1.2 KiB)."""
    for unit in ("B", "KiB", "MiB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} GiB"


def _collect_urls_from_files() -> List[str]:
    """File discovery in config dir (.txt/.csv only) + checkbox selection + TXT/CSV parsing."""
    from app.core.config_manager import ConfigManager
    from app.cli.batch_parsing import extract_urls_from_text, extract_urls_from_csv

    config = ConfigManager()
    config_dir = config.env_path.parent
    if not config_dir.exists():
        typer.echo(f"No batch files found in {config_dir}. Place a .txt or .csv there or use Paste mode.")
        return []

    allowed_suffixes = (".txt", ".csv")
    files = sorted(
        [p for p in config_dir.iterdir() if p.is_file() and p.suffix.lower() in allowed_suffixes],
        key=lambda p: p.name,
    )
    if not files:
        typer.echo(f"No batch files found in {config_dir}. Place a .txt or .csv there or use Paste mode.")
        return []

    # Build choices: filename + mtime + size
    choices: List[Choice] = []
    for p in files:
        try:
            stat = p.stat()
            mtime = stat.st_mtime
            from datetime import datetime
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M") if mtime else "?"
            size_str = _format_file_size(stat.st_size)
            display = f"{p.name}  ({mtime_str}, {size_str})"
        except OSError:
            display = p.name
        choices.append(Choice(str(p), name=display))

    default_selected = [str(files[0])] if len(files) == 1 else None
    try:
        selected = inquirer.checkbox(
            message="Select batch file(s)",
            choices=choices,
            default=default_selected,
        ).execute()
    except (KeyboardInterrupt, Exception):
        typer.echo("Canceled.")
        raise typer.Exit(130)

    if not selected:
        return []

    all_urls: List[str] = []
    for path_str in selected:
        path = Path(path_str)
        if not path.exists():
            continue
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if path.suffix.lower() == ".csv":
            urls = extract_urls_from_csv(raw)
        else:
            urls = extract_urls_from_text(raw)
        all_urls.extend(urls)

    num_sources = len(selected)
    typer.echo(f"Loaded {len(all_urls)} URL(s) from {num_sources} source(s).")
    return all_urls


PASTE_INSTRUCTIONS = "Paste URLs (one per line). Submit an empty line to finish."
PASTE_EMPTY_MSG = "Paste one or more links. Tip: one link per line is easiest."
PASTE_NONE_VALID_MSG = "None of the pasted items look like links (must start with https://)."


def _collect_urls_from_paste() -> List[str]:
    """Multi-line paste via stdin loop + extract_urls_from_text."""
    from app.cli.batch_parsing import extract_urls_from_text

    typer.echo(PASTE_INSTRUCTIONS)
    lines: List[str] = []
    try:
        while True:
            line = input()
            if line.strip() == "":
                break
            lines.append(line)
    except (EOFError, KeyboardInterrupt):
        pass
    text = "\n".join(lines) if lines else ""
    urls = extract_urls_from_text(text)
    if not urls and text.strip():
        typer.echo(PASTE_NONE_VALID_MSG)
        return []
    if not urls:
        typer.echo(PASTE_EMPTY_MSG)
        return []
    typer.echo(f"Loaded {len(urls)} URL(s) from paste.")
    return urls


PLAYLIST_PROMPT_MSG = "Enter playlist URL"
PLAYLIST_EXPAND_FAILED_MSG = "Playlist expansion failed."
PLAYLIST_AS_SINGLE_MSG = "Process playlist URL as a single job?"


def _expand_playlist_urls(playlist_url: str) -> List[str]:
    """
    Expand playlist URL to list of entry URLs using yt-dlp (download=False, flat playlist).
    Returns [] on failure. Does not raise.
    """
    try:
        import yt_dlp
    except ImportError:
        return []
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
    }
    urls: List[str] = []
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(playlist_url.strip(), download=False)
        if not info:
            return []
        entries = info.get("entries") or []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            u = entry.get("webpage_url") or entry.get("url") or entry.get("id")
            if u and isinstance(u, str) and (u.startswith("http://") or u.startswith("https://")):
                urls.append(u)
        return urls
    except Exception:
        return []


def _collect_urls_from_playlist() -> List[str]:
    """Prompt for playlist URL, expand via yt-dlp; on failure offer process-as-single or cancel."""
    try:
        playlist_url = inquirer.text(message=PLAYLIST_PROMPT_MSG, default="").execute()
    except (KeyboardInterrupt, Exception):
        typer.echo("Canceled.")
        raise typer.Exit(130)
    if not playlist_url or not playlist_url.strip():
        return []
    playlist_url = playlist_url.strip()
    if not playlist_url.startswith("http://") and not playlist_url.startswith("https://"):
        typer.echo("That doesn't look like a URL. Paste a link that starts with https://")
        return []

    urls = _expand_playlist_urls(playlist_url)
    if urls:
        typer.echo(f"Loaded {len(urls)} URL(s) from playlist.")
        return urls

    typer.echo(PLAYLIST_EXPAND_FAILED_MSG)
    try:
        as_single = inquirer.confirm(message=PLAYLIST_AS_SINGLE_MSG, default=False).execute()
    except (KeyboardInterrupt, Exception):
        raise typer.Exit(130)
    if as_single:
        return [playlist_url]
    return []


def _run_batch_execution(urls: List[str], overrides: dict) -> None:
    """Process each URL via invoke(); continue-on-error; print summary."""
    from app.cli.url_input import domain_preview
    from app.cli.commands.invoke import invoke

    total = len(urls)
    successes = 0
    failures = 0
    # Signal batch context so downloader can add yt-dlp sleep options (see H)
    import os
    prev_batch = os.environ.get("ALCHEMUX_BATCH")
    os.environ["ALCHEMUX_BATCH"] = "1"
    try:
        for i, url in enumerate(urls):
            preview = domain_preview(url)
            typer.echo(f"({i + 1}/{total}) Processing: {preview}")
            try:
                invoke(
                    url=url,
                    audio_format=None,
                    video_format=None,
                    flac=overrides.get("flac", False),
                    save_path=None,
                    local=overrides.get("local", False),
                    s3=overrides.get("s3", False),
                    gcp=overrides.get("gcp", False),
                    debug=overrides.get("debug", False),
                    verbose=overrides.get("verbose", False),
                    plain=overrides.get("plain", False),
                )
                successes += 1
            except typer.Exit as e:
                if e.exit_code != 0:
                    failures += 1
            except Exception:
                failures += 1
    finally:
        if prev_batch is None:
            os.environ.pop("ALCHEMUX_BATCH", None)
        else:
            os.environ["ALCHEMUX_BATCH"] = prev_batch

    typer.echo(f"Batch complete: {successes} succeeded, {failures} failed, {total} total.")
