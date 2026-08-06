"""
EULA acceptance logic stored in config.toml.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config_manager import ConfigManager
from .logger import setup_logger

logger = setup_logger(__name__)

EULA_GITHUB_URL = "https://github.com/bmurrtech/alchemux/blob/main/EULA.md"


def is_packaged_build() -> bool:
    """
    Legacy helper retained for callers. Setup always offers EULA acceptance;
    packaged vs source no longer gates the setup prompt.
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

        self.config.set("eula.accepted", "true")
        self.config.set("eula.accepted_at", accepted_at)
        self.config.set("eula.acceptance_hash", acceptance_hash)
        # Keep a non-secret breadcrumb of how acceptance was recorded.
        self.config.set("eula.accepted_by", accepted_by)

        logger.info("EULA acceptance recorded in config.toml")

    def display_eula_summary(self) -> str:
        """
        Display EULA summary text for the Rich Panel.

        Returns:
            EULA summary text (without interactive instructions - those are shown separately)
        """
        return (
            "By using Alchemux you agree to the End User Terms for Official Releases "
            f"({EULA_GITHUB_URL}) and the repository LICENSE.\n\n"
            "Use only with content you own or are authorized to access.\n\n"
            "No warranty. You assume all risk. You agree to defend and indemnify "
            "the Distributor and contributors."
        )

    def interactive_acceptance(self) -> bool:
        """
        Prompt user for interactive EULA acceptance using the prompt wrapper.

        Shows a short summary with the GitHub EULA link, then a Y/n confirm.
        On accept, writes eula.* keys to config.toml.

        Returns:
            True if user accepts, False otherwise
        """
        from rich.console import Console
        from rich.panel import Panel

        from app.cli.prompts import confirm

        console = Console()

        console.print()
        console.print(
            Panel(
                self.display_eula_summary(),
                title="[bold yellow]EULA Acceptance Required[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        console.print(f"[dim]Full terms:[/dim] [cyan]{EULA_GITHUB_URL}[/cyan]")
        console.print()

        accepted = confirm(
            f"Accept the Alchemux End User Terms for Official Releases? ({EULA_GITHUB_URL})",
            default=False,
        )
        if accepted is None:
            console.print("\n[yellow]![/yellow] EULA acceptance interrupted.")
            accepted = False

        if accepted:
            self.accept("user_input")
            console.print(
                "\n[green]✓[/green] EULA accepted and saved to config.toml.\n"
            )
            return True

        console.print("\n[yellow]![/yellow] EULA not accepted.")
        console.print("[dim]To accept later, run:[/dim]")
        console.print("  [cyan]alchemux setup[/cyan]")
        console.print()
        return False

    def check_and_require_acceptance(
        self, accept_flag: bool = False, env_var: bool = False
    ) -> bool:
        """
        Check EULA acceptance for non-setup entry points.

        Prefer interactive acceptance during ``alchemux setup``. Non-interactive
        ``--accept-eula`` / env paths still record acceptance when requested.
        """
        if self.is_accepted():
            return True
        if accept_flag or env_var:
            how = "flag" if accept_flag else "env_var"
            self.accept(how)
            return True
        return self.is_accepted()
