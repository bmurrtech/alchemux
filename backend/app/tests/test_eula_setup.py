"""Behavior specs for EULA acceptance during setup.

Seams under test:
- ``EULAManager.interactive_acceptance`` persistence into config.toml;
- ``interactive_setup_refresh`` prompts for EULA as the first confirm when not accepted.
"""

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load a CLI command module first so ``app.cli`` finishes initializing before
# ``setup_wizard`` imports ``app.cli.prompts`` (circular import via cli.__init__).
import app.cli.commands.distill  # noqa: E402, F401
from app.core.config_manager import ConfigManager  # noqa: E402
from app.core.eula import EULA_GITHUB_URL, EULAManager  # noqa: E402
from app.core.setup_wizard import interactive_setup_refresh  # noqa: E402
from app.core.toml_config import read_toml  # noqa: E402


def test_eula_summary_and_prompt_include_github_url() -> None:
    """Users always see the canonical GitHub EULA link in the acceptance copy."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        cfg_dir.mkdir()
        (cfg_dir / ".env").write_text("")
        (cfg_dir / "config.toml").write_text('[paths]\noutput_dir = "./d"\n')
        manager = EULAManager(ConfigManager(env_path=str(cfg_dir / ".env")))

    summary = manager.display_eula_summary()
    assert EULA_GITHUB_URL in summary
    assert "github.com/bmurrtech/alchemux" in summary


def test_interactive_eula_acceptance_writes_config_toml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accepting the EULA prompt persists acceptance flags in config.toml."""
    monkeypatch.delenv("eula.accepted", raising=False)
    monkeypatch.delenv("eula.accepted_at", raising=False)
    monkeypatch.delenv("eula.acceptance_hash", raising=False)
    monkeypatch.delenv("eula.accepted_by", raising=False)
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        cfg_dir.mkdir()
        env_path = cfg_dir / ".env"
        toml_path = cfg_dir / "config.toml"
        env_path.write_text("")
        toml_path.write_text('[paths]\noutput_dir = "./downloads"\n')
        config = ConfigManager(env_path=str(env_path))
        manager = EULAManager(config)

        monkeypatch.setattr(
            "app.cli.prompts.confirm",
            lambda message, default=False: True,
        )

        assert manager.interactive_acceptance() is True
        stored = read_toml(toml_path)
        assert stored["eula"]["accepted"] in (True, "true")
        assert stored["eula"]["accepted_at"]
        assert stored["eula"]["acceptance_hash"]
        assert manager.is_accepted() is True


def test_setup_asks_eula_first_and_cancels_when_declined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setup's first confirm is EULA; declining cancels before preferences."""
    monkeypatch.delenv("eula.accepted", raising=False)
    monkeypatch.delenv("eula.accepted_at", raising=False)
    monkeypatch.delenv("eula.acceptance_hash", raising=False)
    monkeypatch.delenv("eula.accepted_by", raising=False)
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        output_dir = Path(tmp) / "output"
        cfg_dir.mkdir()
        output_dir.mkdir()
        env_path = cfg_dir / ".env"
        toml_path = cfg_dir / "config.toml"
        env_path.write_text("")
        toml_path.write_text(
            '[paths]\noutput_dir = "./downloads"\ntemp_dir = "./tmp"\n'
        )
        config = ConfigManager(env_path=str(env_path))
        confirm_messages: list[str] = []

        def confirm(message: str, default: bool = False) -> bool:
            confirm_messages.append(message)
            return False

        monkeypatch.setattr("app.core.setup_wizard.confirm", confirm)
        monkeypatch.setattr(
            "app.cli.prompts.confirm",
            confirm,
        )
        monkeypatch.setattr("app.core.setup_wizard.is_packaged_build", lambda: False)
        monkeypatch.setattr(
            "app.core.setup_wizard.check_media_deps",
            lambda: (SimpleNamespace(found=True), SimpleNamespace(found=True)),
        )

        assert interactive_setup_refresh(config) is False

    assert confirm_messages, "expected an EULA confirm prompt"
    assert "End User Terms" in confirm_messages[0]
    assert EULA_GITHUB_URL in confirm_messages[0]
    stored = read_toml(toml_path)
    assert str(stored.get("eula", {}).get("accepted", "false")).lower() != "true"


def test_setup_skips_eula_prompt_when_already_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-running setup does not re-prompt when eula.accepted is already true."""
    monkeypatch.setenv("eula.accepted", "true")
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        output_dir = Path(tmp) / "output"
        cfg_dir.mkdir()
        output_dir.mkdir()
        env_path = cfg_dir / ".env"
        toml_path = cfg_dir / "config.toml"
        env_path.write_text("")
        toml_path.write_text(
            '[paths]\noutput_dir = "./downloads"\ntemp_dir = "./tmp"\n\n'
            '[eula]\naccepted = "true"\n'
        )
        config = ConfigManager(env_path=str(env_path))
        eula_prompts = 0

        def confirm(message: str, default: bool = False) -> bool:
            nonlocal eula_prompts
            if "End User Terms" in message:
                eula_prompts += 1
                return True
            return False

        def select(message: str, choices: object, default: object = None) -> object:
            if message == "Output directory":
                return "custom"
            return default

        monkeypatch.setattr("app.core.setup_wizard.confirm", confirm)
        monkeypatch.setattr("app.core.setup_wizard.select", select)
        monkeypatch.setattr(
            "app.core.setup_wizard.filepath", lambda **_kwargs: str(output_dir)
        )
        monkeypatch.setattr("app.core.setup_wizard.is_packaged_build", lambda: False)
        monkeypatch.setattr(
            "app.core.setup_wizard.check_media_deps",
            lambda: (SimpleNamespace(found=True), SimpleNamespace(found=True)),
        )

        assert interactive_setup_refresh(config) is True

    assert eula_prompts == 0
