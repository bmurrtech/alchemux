"""UX polish behavior specs: paths, FFmpeg hints, arcane wording, quiet errors.

Seams under test (confirmed for this module):
- ``validate_output_path`` / ``looks_like_windows_abs_path`` — output-dir validation
- ``detect_ffmpeg_install_command`` / ``INSTALL_FFMPEG_URL`` — detect-only FFmpeg hints
- ``ArcaneConsole.translate_message`` — arcane vs technical wording
- ``normalize_log_level`` / ``resolve_config_log_level`` / ``log_error`` — log level + quiet errors

Vocabulary: see repo-root ``CONTEXT.md``.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from app.cli.output import ArcaneConsole
from app.core.logger import (
    is_debug_logging,
    log_error,
    normalize_log_level,
    resolve_config_log_level,
)
from app.utils.deps import INSTALL_FFMPEG_URL, detect_ffmpeg_install_command
from app.utils.file_utils import looks_like_windows_abs_path, validate_output_path


# --- Output dir / WSL path rejection -----------------------------------------


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (r"C:\Users\ben\Downloads", True),
        ("C:/Users/ben/Downloads", True),
        ("/mnt/c/Users/ben/Downloads", False),
        ("~/Downloads/Alchemux", False),
        ("./downloads", False),
    ],
)
def test_windows_style_absolute_paths_are_recognized(path: str, expected: bool) -> None:
    assert looks_like_windows_abs_path(path) is expected


def test_wsl_rejects_windows_style_output_path_with_mnt_guidance() -> None:
    with patch("app.utils.file_utils.is_wsl", return_value=True):
        ok, err = validate_output_path(r"C:\Users\Ben\Downloads\Alchemux")

    assert ok is False
    assert err is not None
    assert "WSL" in err
    assert "/mnt/c/" in err


def test_wsl_path_rejection_does_not_apply_outside_wsl() -> None:
    """Outside WSL, a Windows-looking path must not fail with the WSL-specific fracture."""
    with patch("app.utils.file_utils.is_wsl", return_value=False):
        ok, err = validate_output_path(r"C:\Users\Ben\Downloads\Alchemux")

    if not ok:
        assert err is not None
        assert "WSL" not in err
        assert "/mnt/c/" not in err
    else:
        assert err is None


# --- FFmpeg check (detect-only) ----------------------------------------------


def test_ffmpeg_install_hint_uses_brew_on_macos_when_brew_is_present() -> None:
    with (
        patch("app.utils.deps.sys.platform", "darwin"),
        patch("app.utils.deps._have", side_effect=lambda c: c == "brew"),
    ):
        assert detect_ffmpeg_install_command() == "brew install ffmpeg"


def test_ffmpeg_install_guide_points_at_repo_install_docs() -> None:
    assert INSTALL_FFMPEG_URL.startswith(
        "https://github.com/bmurrtech/alchemux/blob/main/docs/install.md"
    )
    assert "ffmpeg" in INSTALL_FFMPEG_URL.lower()


# --- Arcane vs technical terms -----------------------------------------------


def test_technical_terms_map_distill_spinner_to_download() -> None:
    console = ArcaneConsole(arcane_terms=False, plain=True)
    assert console.translate_message("distilling...") == "downloading..."
    assert console.translate_message("attunement complete") == "file located"
    assert console.translate_message("locating output...") == "locating file..."


def test_arcane_terms_keep_distill_wording() -> None:
    console = ArcaneConsole(arcane_terms=True, plain=True)
    assert console.translate_message("distilling...") == "distilling..."


# --- Log level + quiet errors ------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "canonical"),
    [
        ("q", "quiet"),
        ("silent", "quiet"),
        ("error", "quiet"),
        ("warn", "warning"),
        ("default", "warning"),
        ("i", "info"),
        ("normal", "info"),
        ("v", "verbose"),
        ("d", "debug"),
        ("trace", "debug"),
        ("true", "debug"),
        (True, "debug"),
    ],
)
def test_log_level_aliases_normalize_to_canonical(raw: object, canonical: str) -> None:
    assert normalize_log_level(raw) == canonical


def test_unknown_log_level_falls_back_to_default() -> None:
    assert normalize_log_level("nope", default="warning") == "warning"


def test_logging_debug_bool_overrides_level() -> None:
    assert (
        resolve_config_log_level(level="warning", debug=True, verbose=False) == "debug"
    )


def test_logging_verbose_bool_overrides_level() -> None:
    assert (
        resolve_config_log_level(level="warning", debug=False, verbose=True)
        == "verbose"
    )


def test_log_level_used_when_bool_aliases_are_false() -> None:
    assert resolve_config_log_level(level="info", debug=False, verbose=False) == "info"
    assert resolve_config_log_level(level="warn") == "warning"


def _capture_log_error(logger_name: str) -> logging.LogRecord:
    records: list[logging.LogRecord] = []

    class Handler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.addHandler(Handler())
    logger.setLevel(logging.DEBUG)
    try:
        raise ValueError("boom")
    except ValueError:
        log_error(logger, "handled failure")
    assert len(records) == 1
    return records[0]


def test_quiet_errors_omit_traceback_outside_debug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("VERBOSE", raising=False)
    monkeypatch.delenv("ALCHEMUX_DEBUG", raising=False)
    assert is_debug_logging() is False

    record = _capture_log_error("test_quiet_errors_omit_traceback")
    assert not record.exc_info


def test_quiet_errors_include_traceback_in_debug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert is_debug_logging() is True

    record = _capture_log_error("test_quiet_errors_include_traceback")
    assert record.exc_info is not None
    assert record.exc_info[0] is ValueError
