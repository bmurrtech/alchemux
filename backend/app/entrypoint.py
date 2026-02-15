"""
Package-native CLI entry point for Alchemux.

Used by the installed console scripts (alchemux, amx). No sys.path modification.
"""

import os
import sys
import warnings


def _only_help_or_version(argv: list[str]) -> bool:
    """True if argv implies only --help or --version (no config needed)."""
    if "--help" in argv or "-h" in argv:
        return True
    if "--version" in argv or "-v" in argv:
        return True
    return False


def _apply_gcp_warning_suppression() -> None:
    """Suppress google.api_core FutureWarning when GCP is not configured."""
    if os.getenv("GCP_STORAGE_BUCKET") or os.getenv("GCP_SA_KEY_BASE64"):
        return
    if "--setup" in sys.argv:
        idx = sys.argv.index("--setup")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1] == "gcp":
            return
    if "--gcp" in sys.argv or "-gcp" in sys.argv:
        return
    try:
        from app.core.config_manager import get_config_location

        config_path = get_config_location()
        if config_path.exists():
            from dotenv import load_dotenv

            load_dotenv(config_path)
            if os.getenv("GCP_STORAGE_BUCKET") or os.getenv("GCP_SA_KEY_BASE64"):
                return
    except Exception:
        pass
    warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")
    import logging

    logging.captureWarnings(True)

    class GCPWarningFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            msg = record.getMessage()
            if "google.api_core" in msg or "Python version" in msg:
                return os.getenv("LOG_LEVEL", "").lower() == "debug"
            return True

    warnings_logger = logging.getLogger("py.warnings")
    if not any(isinstance(f, GCPWarningFilter) for f in warnings_logger.filters):
        warnings_logger.addFilter(GCPWarningFilter())


def _is_debug_mode(argv: list[str]) -> bool:
    """Resolve debug mode from CLI flag, env, or config."""
    if "--debug" in argv:
        return True
    if os.getenv("LOG_LEVEL", "").lower() == "debug":
        return True
    try:
        from app.core.config_manager import ConfigManager

        config = ConfigManager()
        return config.get_bool("logging.debug", default=False)
    except Exception:
        return False


def main() -> None:
    """Entry point for alchemux/amx console scripts."""
    debug_mode = _is_debug_mode(sys.argv)
    from app.core.tracebacks import install_traceback_handler, print_fracture_summary

    install_traceback_handler(debug=debug_mode)

    # Help/version only: no config or GCP suppression needed
    if _only_help_or_version(sys.argv):
        from app.cli.app import app

        app()
        return

    _apply_gcp_warning_suppression()

    import typer
    from app.cli.app import app
    from app.cli.output import ArcaneConsole

    _banner_shown = False

    try:
        if "config" in sys.argv:
            config_idx = sys.argv.index("config")
            rest = [
                a for a in sys.argv[config_idx + 1 :] if a and not a.startswith("-")
            ]
            if not rest:
                from app.core.config_manager import ConfigManager
                from app.core.config_wizard import interactive_config_wizard

                plain_mode = "--plain" in sys.argv or os.getenv(
                    "NO_COLOR", ""
                ).lower() in ("1", "true", "yes")
                if (
                    not _banner_shown
                    and os.getenv("ALCHEMUX_SHOW_BANNER", "true").lower() == "true"
                ):
                    if not any(arg in sys.argv for arg in ["--version", "-v"]):
                        console = ArcaneConsole(plain=plain_mode)
                        console.print_banner()
                        _banner_shown = True
                config_manager = ConfigManager()
                if not config_manager.check_toml_file_exists():
                    ArcaneConsole(plain=plain_mode).print_fracture(
                        "config", "config.toml not found. Run 'alchemux setup' first."
                    )
                    sys.exit(1)
                try:
                    success = interactive_config_wizard(config_manager)
                    sys.exit(0 if success else 1)
                except KeyboardInterrupt:
                    sys.exit(130)
                except Exception as e:
                    if not debug_mode:
                        print_fracture_summary("config", e)
                    sys.exit(1)

        if "setup" in sys.argv:
            setup_idx = sys.argv.index("setup")
            if setup_idx + 1 < len(sys.argv) and not sys.argv[setup_idx + 1].startswith(
                "-"
            ):
                target = sys.argv[setup_idx + 1]
            else:
                target = None

            from app.cli.commands.setup import setup as setup_cmd

            plain_mode = "--plain" in sys.argv or os.getenv("NO_COLOR", "").lower() in (
                "1",
                "true",
                "yes",
            )
            if (
                not _banner_shown
                and os.getenv("ALCHEMUX_SHOW_BANNER", "true").lower() == "true"
            ):
                if not any(arg in sys.argv for arg in ["--version", "-v"]):
                    console = ArcaneConsole(plain=plain_mode)
                    console.print_banner()
                    _banner_shown = True
            try:
                setup_cmd(target=target, plain=plain_mode, reset=False)
                sys.exit(0)
            except SystemExit:
                raise
            except typer.Exit as e:
                sys.exit(getattr(e, "exit_code", 0))
            except Exception as e:
                if not debug_mode:
                    print_fracture_summary("setup", e)
                sys.exit(1)

        if (
            not _banner_shown
            and os.getenv("ALCHEMUX_SHOW_BANNER", "true").lower() == "true"
        ):
            if not any(arg in sys.argv for arg in ["--version", "-v"]):
                plain_mode = "--plain" in sys.argv or os.getenv(
                    "NO_COLOR", ""
                ).lower() in ("1", "true", "yes")
                console = ArcaneConsole(plain=plain_mode)
                console.print_banner()
                _banner_shown = True

        app()
    except KeyboardInterrupt:
        from rich.console import Console

        Console(stderr=True).print("\n\n[dim]Interrupted by user. Goodbye![/dim]")
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as e:
        if not debug_mode:
            print_fracture_summary("main", e)
        if debug_mode:
            raise
        sys.exit(1)
