"""
URL input acquisition layer for PRD6: interactive mode and clipboard (-p/--clipboard).

Priority: (1) positional URL handled by caller; (2) clipboard if -p/--clipboard;
(3) interactive if TTY else exit with hint. Never persists overrides; never logs clipboard.
"""

import sys
from typing import Optional, Tuple
from urllib.parse import urlparse

import typer

# Optional pyperclip; degrade gracefully if unavailable
try:
    import pyperclip
except ImportError:
    pyperclip = None

# InquirerPy for interactive prompts
try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
except ImportError:
    inquirer = None
    Choice = None


# Override keys matching invoke() kwargs (storage: at most one of local, s3, gcp)
OVERRIDE_KEYS = ("debug", "flac", "local", "s3", "gcp", "verbose", "plain")
STORAGE_KEYS = ("local", "s3", "gcp")

# User-facing messages (PRD6)
SETUP_REQUIRED_MSG = "It looks like Alchemux isn't set up yet. Run alchemux setup to accept the EULA and create your configuration."
URL_INVALID_MSG = (
    "That doesn't look like a URL. Paste a full link starting with https://"
)
CANCEL_HINT_MSG = (
    'Canceled. Tip: You can also run alchemux -- "URL" if your link contains & or ?.'
)
CLIPBOARD_EMPTY_MSG = (
    "Clipboard is empty. Copy a media URL first, or run alchemux to paste it manually."
)
CLIPBOARD_NOT_URL_MSG = "Clipboard doesn't look like a URL. Copy a link that starts with https://\nRun alchemux to paste it manually."
CLIPBOARD_UNSUPPORTED_MSG = 'Clipboard unsupported. Retry with `alchemux` or `alchemux "https://your_URL_here"` instead.'
NO_URL_NONINTERACTIVE_MSG = (
    "No URL provided. In non-interactive mode, pass a URL as an argument."
)
STORAGE_ONE_ONLY_MSG = "Choose only one storage destination override."


def validate_url_like(text: str) -> bool:
    """Return True if trimmed input looks like a URL (http(s) and has hostname)."""
    if not text or not isinstance(text, str):
        return False
    s = text.strip()
    if not s:
        return False
    if not (s.startswith("http://") or s.startswith("https://")):
        return False
    try:
        parsed = urlparse(s)
        return bool(parsed.netloc)
    except Exception:
        return False


def domain_preview(url: str, max_path: int = 40) -> str:
    """Safe preview: domain + short path, no query string. Never log full URL."""
    try:
        parsed = urlparse(url.strip())
        netloc = parsed.netloc or ""
        path = (parsed.path or "").strip("/")
        if len(path) > max_path:
            path = path[: max_path - 3] + "..."
        if path:
            return f"{netloc}/{path}"
        return netloc or "unknown"
    except Exception:
        return "unknown"


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


def _read_clipboard() -> Tuple[Optional[str], Optional[str]]:
    """
    Attempt to read clipboard. Return (content, None) on success, (None, error_message) on failure.
    Never log or print clipboard content.
    """
    if pyperclip is None:
        return None, CLIPBOARD_UNSUPPORTED_MSG
    try:
        raw = pyperclip.paste()
        if raw is None:
            return None, CLIPBOARD_EMPTY_MSG
        s = (raw if isinstance(raw, str) else str(raw)).strip()
        if not s:
            return None, CLIPBOARD_EMPTY_MSG
        return s, None
    except Exception:
        return None, CLIPBOARD_UNSUPPORTED_MSG


def _interactive_url_prompt() -> Optional[str]:
    """InquirerPy text prompt for URL with validation and reprompt. Returns None on cancel."""
    if inquirer is None:
        return None
    while True:
        try:
            value = inquirer.text(message="Enter URL", default="").execute()
        except (KeyboardInterrupt, Exception):
            return None
        if value is None:
            return None
        s = (value or "").strip()
        if validate_url_like(s):
            return s
        typer.echo(URL_INVALID_MSG)


def _interactive_overrides_prompt() -> dict:
    """Confirm then checkbox for one-time overrides. Enforce at most one storage. Returns dict of override key -> True."""
    if inquirer is None:
        return {}
    try:
        apply_overrides = inquirer.confirm(
            message="Apply overrides?",
            default=False,
        ).execute()
    except (KeyboardInterrupt, Exception):
        raise typer.Exit(130)
    if not apply_overrides:
        return {}

    choices = [
        Choice("debug", name="--debug — Enable debug mode with full tracebacks"),
        Choice("flac", name="--flac — FLAC 16kHz mono conversion (one-time override)"),
        Choice("local", name="--local — Save to local storage (one-time override)"),
        Choice("s3", name="--s3 — Upload to S3 storage (one-time override)"),
        Choice("gcp", name="--gcp — Upload to GCP storage (one-time override)"),
        Choice(
            "verbose", name="--verbose — Enable verbose logging (one-time override)"
        ),
        Choice(
            "plain", name="--plain — Disable colors and animations (one-time override)"
        ),
    ]

    while True:
        try:
            selected = inquirer.checkbox(
                message="Select overrides (space to toggle, enter to confirm)",
                choices=choices,
                validate=lambda x: sum(1 for k in STORAGE_KEYS if k in (x or [])) <= 1,
                invalid_message=STORAGE_ONE_ONLY_MSG,
            ).execute()
        except (KeyboardInterrupt, Exception):
            typer.echo("Canceled.")
            raise typer.Exit(130)
        if selected is None:
            return {}
        storage_count = sum(1 for k in STORAGE_KEYS if k in selected)
        if storage_count <= 1:
            return {k: True for k in (selected or []) if k in OVERRIDE_KEYS}
        typer.echo(STORAGE_ONE_ONLY_MSG)


def acquire_url(
    url_arg: Optional[str],
    use_clipboard: bool,
    is_tty: bool,
) -> Tuple[str, dict]:
    """
    Resolve URL and optional one-time overrides when no positional URL was provided.

    Caller must not call this when url_arg is set; caller handles positional URL.
    When url_arg is None:
      - If use_clipboard: try clipboard; on failure, fall back to interactive if is_tty else exit with CLIPBOARD_UNSUPPORTED_MSG.
      - Else: if is_tty run interactive (prereq check first); else exit with NO_URL_NONINTERACTIVE_MSG.

    Returns (url, overrides_dict). overrides_dict has keys in OVERRIDE_KEYS with value True for selected.
    Raises typer.Exit on failure or cancel.
    """
    if url_arg and validate_url_like(url_arg):
        return url_arg.strip(), {}

    if use_clipboard:
        content, err = _read_clipboard()
        if err and not content:
            if is_tty:
                # Fallback to interactive URL prompt
                typer.echo(err)
                if not _check_prerequisites():
                    typer.echo(SETUP_REQUIRED_MSG)
                    raise typer.Exit(1)
                url = _interactive_url_prompt()
                if url is None:
                    typer.echo(CANCEL_HINT_MSG)
                    raise typer.Exit(130)
                overrides = _interactive_overrides_prompt()
                return url, overrides
            typer.echo(CLIPBOARD_UNSUPPORTED_MSG)
            raise typer.Exit(1)
        if not validate_url_like(content):
            typer.echo(CLIPBOARD_NOT_URL_MSG)
            if is_tty:
                if not _check_prerequisites():
                    typer.echo(SETUP_REQUIRED_MSG)
                    raise typer.Exit(1)
                url = _interactive_url_prompt()
                if url is None:
                    typer.echo(CANCEL_HINT_MSG)
                    raise typer.Exit(130)
                overrides = _interactive_overrides_prompt()
                return url, overrides
            raise typer.Exit(1)
        # Optional: domain preview and confirm "Use this URL? (Y/n)"
        if is_tty and inquirer:
            preview = domain_preview(content)
            try:
                use_it = inquirer.confirm(
                    message=f"Detected URL from clipboard: {preview}\nUse this URL?",
                    default=True,
                ).execute()
            except (KeyboardInterrupt, Exception):
                typer.echo(CANCEL_HINT_MSG)
                raise typer.Exit(130)
            if not use_it:
                url = _interactive_url_prompt()
                if url is None:
                    typer.echo(CANCEL_HINT_MSG)
                    raise typer.Exit(130)
                overrides = _interactive_overrides_prompt()
                return url, overrides
        # Use clipboard URL without confirm (non-TTY or no inquirer)
        overrides = _interactive_overrides_prompt() if is_tty and inquirer else {}
        return content.strip(), overrides

    # No URL, no clipboard
    if not is_tty:
        typer.echo(NO_URL_NONINTERACTIVE_MSG)
        raise typer.Exit(1)
    if not _check_prerequisites():
        typer.echo(SETUP_REQUIRED_MSG)
        raise typer.Exit(1)
    url = _interactive_url_prompt()
    if url is None:
        typer.echo(CANCEL_HINT_MSG)
        raise typer.Exit(130)
    overrides = _interactive_overrides_prompt()
    return url, overrides


def is_tty() -> bool:
    """True if stdin is a TTY (interactive)."""
    return hasattr(sys.stdin, "isatty") and sys.stdin.isatty()
