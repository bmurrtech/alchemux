"""
Tests for root argv normalization and fallback CLI hinting.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import entrypoint  # noqa: E402
from app.cli.argv_normalize import normalize_argv  # noqa: E402


def test_normalize_moves_root_flags_before_url() -> None:
    url = "https://youtu.be/PlN86TvzGy4"
    argv = ["alchemux", url, "--no-config", "--download-dir", "."]

    normalized = normalize_argv(argv)

    assert normalized == ["alchemux", "--no-config", "--download-dir", ".", url]


def test_normalize_keeps_flags_first_invocation() -> None:
    url = "https://youtu.be/PlN86TvzGy4"
    argv = ["alchemux", "--no-config", "--download-dir", ".", url]

    normalized = normalize_argv(argv)

    assert normalized == argv


def test_normalize_keeps_subcommand_invocation_unchanged() -> None:
    argv = ["alchemux", "batch", "--help"]

    normalized = normalize_argv(argv)

    assert normalized == argv


def test_normalize_keeps_scry_help_flags_after_command() -> None:
    """``scry --help`` must not be reordered to ``--help scry`` (would break dispatch)."""
    argv = ["alchemux", "scry", "--help"]

    assert normalize_argv(argv) == argv
    assert normalize_argv(["alchemux", "inspect", "file.flac", "--json"]) == [
        "alchemux",
        "inspect",
        "file.flac",
        "--json",
    ]


def test_normalize_preserves_tokens_after_double_dash() -> None:
    argv = ["alchemux", "--", "https://example.com?a=1&b=2", "--no-config"]

    normalized = normalize_argv(argv)

    assert normalized == argv


def test_entrypoint_handles_url_before_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_invoke(**kwargs: object) -> None:
        called.update(kwargs)

    monkeypatch.setattr("app.cli.commands.invoke.invoke", fake_invoke)
    monkeypatch.setenv("ALCHEMUX_SHOW_BANNER", "false")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alchemux",
            "https://youtu.be/PlN86TvzGy4",
            "--no-config",
            "--download-dir",
            ".",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        entrypoint.main()

    assert exc.value.code == 0

    assert called["url"] == "https://youtu.be/PlN86TvzGy4"
    assert called["no_config"] is True
    assert called["download_dir_override"] == "."


def test_entrypoint_prints_ordering_hint_on_parse_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ALCHEMUX_SHOW_BANNER", "false")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alchemux",
            "https://youtu.be/PlN86TvzGy4",
            "--not-a-real-flag",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        entrypoint.main()

    assert exc.value.code == 2
    assert "Hint: place flags before URL" in capsys.readouterr().err


@pytest.mark.parametrize("subcommand", ["show", "doctor", "mv"])
def test_entrypoint_dispatches_config_subcommands_to_config_app(
    monkeypatch: pytest.MonkeyPatch, subcommand: str
) -> None:
    """Root [URL] must not steal ``config``; show|doctor|mv go to the config Typer app."""
    called: dict[str, object] = {}

    def fake_config_app(*, args: list[str], prog_name: str) -> None:
        called["args"] = list(args)
        called["prog_name"] = prog_name

    monkeypatch.setenv("ALCHEMUX_SHOW_BANNER", "false")
    monkeypatch.setattr(sys, "argv", ["alchemux", "config", subcommand])
    monkeypatch.setattr("app.cli.commands.config.app", fake_config_app)

    with pytest.raises(SystemExit) as exc:
        entrypoint.main()

    assert exc.value.code == 0
    assert called["prog_name"] == "config"
    assert called["args"] == [subcommand]


def test_entrypoint_allows_config_subcommand_help(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``config … --help`` must not be short-circuited as root-only help."""
    called: dict[str, object] = {}

    def fake_config_app(*, args: list[str], prog_name: str) -> None:
        called["args"] = list(args)
        called["prog_name"] = prog_name

    monkeypatch.setenv("ALCHEMUX_SHOW_BANNER", "false")
    monkeypatch.setattr(sys, "argv", ["alchemux", "config", "mv", "--help"])
    monkeypatch.setattr("app.cli.commands.config.app", fake_config_app)

    assert (
        entrypoint._only_help_or_version(["alchemux", "config", "mv", "--help"])
        is False
    )

    with pytest.raises(SystemExit) as exc:
        entrypoint.main()

    assert exc.value.code == 0
    assert called["args"] == ["mv", "--help"]
    assert called["prog_name"] == "config"
