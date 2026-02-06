"""
Update command - Update yt-dlp to latest stable version.

Provides reliable yt-dlp updates without requiring binary reinstallation.
"""

import sys
import subprocess
import json
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel

from app.core.config_manager import ConfigManager
from app.core.logger import setup_logger

logger = setup_logger(__name__)
console = Console()

# Throttle update checks: check at most once per day
UPDATE_CHECK_THROTTLE_HOURS = 24
LAST_UPDATE_CHECK_FILE = ".yt-dlp-last-update"


def _get_last_update_check_path() -> Path:
    """Get path to last update check timestamp file."""
    config = ConfigManager()
    config_dir = config.env_path.parent
    return config_dir / LAST_UPDATE_CHECK_FILE


def _should_check_for_updates(force: bool = False) -> bool:
    """
    Check if we should check for updates (throttle to avoid GitHub rate limits).

    Args:
        force: If True, bypass throttling

    Returns:
        True if we should check, False if throttled
    """
    if force:
        return True

    check_file = _get_last_update_check_path()
    if not check_file.exists():
        return True

    try:
        last_check_str = check_file.read_text().strip()
        last_check = datetime.fromisoformat(last_check_str)
        now = datetime.now()
        hours_since = (now - last_check).total_seconds() / 3600

        if hours_since >= UPDATE_CHECK_THROTTLE_HOURS:
            return True
    except Exception as e:
        logger.debug(f"Could not read last update check time: {e}")
        return True

    return False


def _record_update_check() -> None:
    """Record that we checked for updates (for throttling)."""
    check_file = _get_last_update_check_path()
    try:
        check_file.parent.mkdir(parents=True, exist_ok=True)
        check_file.write_text(datetime.now().isoformat())
    except Exception as e:
        logger.debug(f"Could not write update check timestamp: {e}")


def _get_current_ytdlp_version() -> Optional[str]:
    """
    Get current yt-dlp version.

    Returns:
        Version string (e.g., "2025.12.08") or None if unavailable
    """
    try:
        import yt_dlp

        # yt-dlp exposes version via __version__
        version = getattr(yt_dlp, "__version__", None)
        if version:
            return version

        # Fallback: try subprocess
        result = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.debug(f"Could not get yt-dlp version: {e}")

    return None


def _get_latest_stable_version() -> Optional[str]:
    """
    Get latest stable yt-dlp version from GitHub API.

    Returns:
        Version tag (e.g., "2025.12.08") or None if unavailable
    """
    try:
        import urllib.request
        import urllib.error

        url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github.v3+json")

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            tag_name = data.get("tag_name", "")
            # Remove 'v' prefix if present
            if tag_name.startswith("v"):
                tag_name = tag_name[1:]
            return tag_name
    except Exception as e:
        logger.debug(f"Could not fetch latest version from GitHub: {e}")
        return None


def _update_ytdlp_stable() -> Tuple[bool, Optional[str]]:
    """
    Update yt-dlp to latest stable using built-in update mechanism.

    Returns:
        Tuple of (success, message)
    """
    try:
        # Use yt-dlp's built-in update mechanism
        # This is the most reliable method as it handles platform-specific binaries
        result = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "-U", "--update-to", "stable"],
            capture_output=True,
            text=True,
            timeout=120,  # Update can take time
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            if "Updated yt-dlp" in output or "yt-dlp is up to date" in output:
                return True, output
            return True, "yt-dlp updated successfully"
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return False, f"Update failed: {error_msg}"
    except subprocess.TimeoutExpired:
        return False, "Update timed out (took longer than 2 minutes)"
    except Exception as e:
        return False, f"Update error: {str(e)}"


def update(
    force: bool = typer.Option(
        False, "--force", help="Force update check even if recently checked"
    ),
    plain: bool = typer.Option(False, "--plain", help="Disable colors"),
) -> None:
    """
    Update yt-dlp to the latest stable version.

    This command checks if yt-dlp is outdated and updates it if needed.
    Update checks are throttled to once per day to avoid GitHub rate limits.
    Use --force to bypass throttling.

    **When to use:**
    - If downloads fail with HTTP 403 or other extraction errors
    - To ensure you have the latest yt-dlp fixes and improvements
    - After yt-dlp releases new versions

    **How it works:**
    - Uses yt-dlp's built-in `--update-to stable` mechanism (most reliable)
    - Updates the Python package, not the Alchemux binary
    - Throttles checks to once per 24 hours (use --force to check immediately)

    **Note**: This updates yt-dlp without requiring a new Alchemux binary release.
    """
    # Ensure output is flushed immediately
    import sys

    sys.stdout.flush()
    sys.stderr.flush()

    console.print()
    console.print(Panel("[bold]yt-dlp Update[/bold]", border_style="cyan"))
    console.print()

    # Check if we should check (throttling)
    if not _should_check_for_updates(force=force):
        last_check_file = _get_last_update_check_path()
        try:
            last_check_str = last_check_file.read_text().strip()
            last_check = datetime.fromisoformat(last_check_str)
            hours_ago = (datetime.now() - last_check).total_seconds() / 3600
            console.print(
                f"[dim]Last checked {hours_ago:.1f} hours ago. Use --force to check again.[/dim]"
            )
            console.print("[dim]Checking anyway for this run...[/dim]")
        except Exception:
            pass

    # Get current version
    current_version = _get_current_ytdlp_version()
    if current_version:
        console.print(f"[green]>[/green] Current yt-dlp version: {current_version}")
    else:
        console.print("[yellow]![/yellow]  Could not determine current yt-dlp version")
        console.print("[dim]Proceeding with update attempt...[/dim]")

    # Get latest stable version
    console.print("[dim]Checking for latest stable version...[/dim]")
    latest_version = _get_latest_stable_version()

    if latest_version:
        console.print(f"[green]>[/green] Latest stable version: {latest_version}")

        if current_version and current_version == latest_version:
            console.print()
            console.print("[bold green]yt-dlp is already up to date![/bold green]")
            _record_update_check()
            raise typer.Exit(0)
    else:
        console.print("[yellow]![/yellow]  Could not fetch latest version from GitHub")
        console.print("[dim]Proceeding with update attempt anyway...[/dim]")

    # Perform update
    console.print()
    console.print("[dim]Updating yt-dlp to latest stable...[/dim]")
    success, message = _update_ytdlp_stable()

    if success:
        console.print()
        console.print(
            Panel(
                f"[bold green]✓ Update successful![/bold green]\n\n{message}",
                title="Success",
                border_style="green",
            )
        )
        _record_update_check()

        # Verify new version
        new_version = _get_current_ytdlp_version()
        if new_version:
            console.print(
                f"\n[green]✓[/green] Current version after update: [bold]{new_version}[/bold]"
            )
        console.print()  # Extra line for spacing
        sys.stdout.flush()
    else:
        console.print()
        console.print(
            Panel(
                f"[bold red]✗ Update failed[/bold red]\n\n{message}\n\n"
                "[dim]You may need to update manually:\n"
                "  pip install --upgrade yt-dlp[/dim]",
                title="Error",
                border_style="red",
            )
        )
        console.print()  # Extra line for spacing
        sys.stdout.flush()
        raise typer.Exit(1)
