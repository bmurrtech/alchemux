"""
Public-safe CLI smoke tests (no network, no secrets).

These tests simulate user actions at a high level using Typer's CliRunner.
They intentionally:
- use a temporary config directory via ALCHEMUX_CONFIG_DIR
- write only synthetic config values
- avoid printing any secret-like values
"""

import os
import sys
import tempfile
from pathlib import Path

from typer.testing import CliRunner

# Ensure `app.*` imports work when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.cli.commands import config as config_cmd  # noqa: E402


def _maybe_print(msg: str) -> None:
    if os.getenv("ALCHEMUX_TEST_VERBOSE", "").lower() in ("1", "true", "yes"):
        # Must remain public-safe: only print non-sensitive test metadata.
        print(msg)


def _seed_temp_config_dir(cfg_dir: Path) -> None:
    cfg_dir.mkdir(parents=True, exist_ok=True)

    # Secrets file: keep empty placeholders only (never real creds).
    (cfg_dir / ".env").write_text(
        "OAUTH_CLIENT_ID=\n"
        "OAUTH_CLIENT_SECRET=\n"
        "GCP_SA_KEY_BASE64=\n"
        "S3_ACCESS_KEY=\n"
        "S3_SECRET_KEY=\n"
    )

    # Non-secret config: minimal keys required for safe CLI flows.
    (cfg_dir / "config.toml").write_text(
        "[product]\n"
        "arcane_terms = true\n\n"
        "[paths]\n"
        'output_dir = "./downloads"\n'
        'temp_dir = "./tmp"\n'
    )


def test_config_show_smoke() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_temp_config_dir(cfg_dir)

        env = os.environ.copy()
        env["ALCHEMUX_CONFIG_DIR"] = str(cfg_dir)

        _maybe_print(f"ALCHEMUX_CONFIG_DIR={cfg_dir}")

        # Invoke the config sub-app directly to avoid root URL positional ambiguity.
        result = runner.invoke(config_cmd.app, ["show"], env=env)
        assert result.exit_code == 0
        assert "Configuration" in result.stdout
        # Rich tables may truncate long paths; just assert key rows exist.
        assert "config.toml" in result.stdout
        assert ".env" in result.stdout


def test_config_doctor_smoke() -> None:
    """
    Doctor should run without requiring secrets, printing a report.

    This test is intentionally tolerant: as PRD7 evolves, doctor may become
    interactive and offer guided repairs. The smoke requirement is simply that
    it produces a diagnostic report and exits cleanly in a non-interactive run.
    """
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        _seed_temp_config_dir(cfg_dir)

        env = os.environ.copy()
        env["ALCHEMUX_CONFIG_DIR"] = str(cfg_dir)

        # Invoke the config sub-app directly to avoid root URL positional ambiguity.
        result = runner.invoke(config_cmd.app, ["doctor"], env=env, input="n\n")
        assert result.exit_code == 0
        assert "Configuration Diagnostics" in result.stdout

