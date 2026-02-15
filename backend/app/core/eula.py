"""
EULA acceptance logic with dual storage strategy (eula_config.json + .env).
"""

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config_manager import ConfigManager
from .logger import setup_logger

logger = setup_logger(__name__)


def is_packaged_build() -> bool:
    """
    Legacy: always False. EULA is not enforced for PyPI/uv installs; use of the app
    is treated as acceptance. Retained for backward compatibility with --accept-eula.
    """
    return False


class EULAManager:
    """Manages EULA acceptance using config.toml."""

    EULA_VERSION = "1.0"
    LICENSE_FILES = ["LICENSE.MD", "EULA.md"]

    def __init__(self, config_manager: ConfigManager, root_dir: Optional[Path] = None):
        """
        Initialize EULA Manager.

        Args:
            config_manager: ConfigManager instance
            root_dir: Ignored (legacy parameter)
        """
        self.config = config_manager

    def _generate_acceptance_hash(self) -> str:
        """Generate a unique hash for EULA acceptance verification."""
        return hashlib.sha256(
            f"{uuid.uuid4()}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]

    def is_accepted(self) -> bool:
        """
        Check if EULA has been accepted.

        Returns:
            True if EULA is accepted, False otherwise
        """
        return self.config.get("eula.accepted", "").lower() == "true"

    def accept(self, accepted_by: str = "user_input") -> None:
        """
        Record EULA acceptance in config.toml.

        Args:
            accepted_by: How acceptance was recorded (e.g., "user_input", "flag", "env_var")
        """
        acceptance_hash = self._generate_acceptance_hash()
        accepted_at = datetime.now(timezone.utc).isoformat()

        # Write to config.toml
        self.config.set("eula.accepted", "true")
        self.config.set("eula.accepted_at", accepted_at)
        self.config.set("eula.acceptance_hash", acceptance_hash)

        logger.info("EULA acceptance recorded in config.toml")

    def display_eula_summary(self) -> str:
        """
        Display EULA summary text for the Rich Panel.

        Returns:
            EULA summary text (without interactive instructions - those are shown separately)
        """
        return """By using this software you agree to the LICENSE and EULA.md.

Use only with content you own or are authorized to access.

No warranty. You assume all risk. You agree to defend
and indemnify the Provider and contributors."""

    def interactive_acceptance(self) -> bool:
        """
        Prompt user for interactive EULA acceptance using the prompt wrapper (InquirerPy or Rich).

        Uses Rich Panel to display EULA summary and confirm prompt for y/n acceptance.
        On decline, shows clear next steps for accepting later.

        Returns:
            True if user accepts, False otherwise
        """
        from rich.console import Console
        from rich.panel import Panel

        from app.cli.prompts import confirm

        console = Console()

        # Display EULA summary in a panel
        console.print()
        console.print(
            Panel(
                self.display_eula_summary(),
                title="[bold yellow]EULA Acceptance Required[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        console.print()

        # y/n confirmation via prompt wrapper (InquirerPy or Rich fallback)
        accepted = confirm(
            "Do you accept the EULA terms?",
            default=False,
        )
        if accepted is None:
            console.print("\n[yellow]![/yellow] EULA acceptance interrupted.")
            accepted = False

        if accepted:
            self.accept("user_input")
            console.print(
                "\n[green]>[/green] EULA accepted. You may now use Alchemux.\n"
            )
            return True
        else:
            console.print("\n[yellow]![/yellow] EULA not accepted.")
            console.print("[dim]To accept later, run:[/dim]")
            console.print("  [cyan]alchemux setup[/cyan]")
            console.print()
            return False

    def check_and_require_acceptance(
        self, accept_flag: bool = False, env_var: bool = False
    ) -> bool:
        """
        Check EULA acceptance and require it if not accepted.

        EULA enforcement only applies to packaged releases. When running from source
        (Apache 2.0 licensed), this check is skipped automatically.

        Args:
            accept_flag: True if --accept-eula flag was provided
            env_var: True if EULA_ACCEPTED=true in environment

        Returns:
            True if EULA is accepted (or was just accepted), False if user declined
        """
        # EULA not enforced for PyPI/uv installs; use of app = acceptance
        logger.debug("EULA enforcement disabled (acceptance by use)")
        return True
