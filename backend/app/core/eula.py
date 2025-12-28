"""
EULA acceptance logic with dual storage strategy (eula_config.json + .env).
"""
import os
import sys
import json
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from .config_manager import ConfigManager
from .logger import setup_logger

logger = setup_logger(__name__)


def is_packaged_build() -> bool:
    """
    Check if the application is running from a packaged build (PyInstaller).
    
    EULA enforcement only applies to packaged releases, not source code.
    Source code is licensed under Apache 2.0 and doesn't require EULA acceptance.
    
    Returns:
        True if running from a PyInstaller bundle, False if running from source
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


class EULAManager:
    """Manages EULA acceptance with dual storage strategy."""
    
    EULA_VERSION = "1.0"
    LICENSE_FILES = ["LICENSE.MD", "EULA.md", "TERMS.md"]
    
    def __init__(self, config_manager: ConfigManager, root_dir: Optional[Path] = None):
        """
        Initialize EULA Manager.
        
        Args:
            config_manager: ConfigManager instance
            root_dir: Root directory for eula_config.json (defaults to .env parent or cwd)
        """
        self.config = config_manager
        if root_dir:
            self.root_dir = Path(root_dir)
        else:
            # Use .env file's parent directory as root
            self.root_dir = config_manager.env_path.parent
        
        self.eula_json_path = self.root_dir / "eula_config.json"
        self._sync_storage()
    
    def _generate_acceptance_hash(self) -> str:
        """Generate a unique hash for EULA acceptance verification."""
        return hashlib.sha256(
            f"{uuid.uuid4()}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
    
    def _read_json_config(self) -> Optional[dict]:
        """Read eula_config.json if it exists."""
        if not self.eula_json_path.exists():
            return None
        
        try:
            with open(self.eula_json_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading eula_config.json: {e}")
            return None
    
    def _write_json_config(self, data: dict) -> None:
        """Write eula_config.json with proper structure."""
        try:
            with open(self.eula_json_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Wrote eula_config.json to {self.eula_json_path}")
        except IOError as e:
            logger.error(f"Error writing eula_config.json: {e}")
            raise
    
    def _sync_storage(self) -> None:
        """
        Synchronize dual storage (eula_config.json and .env).
        JSON takes precedence if conflict exists.
        """
        json_data = self._read_json_config()
        env_accepted = self.config.get("EULA_ACCEPTED", "").lower() == "true"
        env_hash = self.config.get("EULA_ACCEPTANCE_HASH", "")
        env_at = self.config.get("EULA_ACCEPTED_AT", "")
        
        # If JSON exists and indicates acceptance, ensure .env is updated
        if json_data and json_data.get("eula_accepted"):
            if not env_accepted or env_hash != json_data.get("acceptance_hash"):
                logger.debug("Syncing .env from eula_config.json")
                self.config.set("EULA_ACCEPTED", "true")
                self.config.set("EULA_ACCEPTED_AT", json_data.get("accepted_at", ""))
                self.config.set("EULA_ACCEPTANCE_HASH", json_data.get("acceptance_hash", ""))
        
        # If .env indicates acceptance but JSON is missing, recreate JSON
        elif env_accepted and env_hash:
            if not json_data or not json_data.get("eula_accepted"):
                logger.debug("Recreating eula_config.json from .env")
                self._write_json_config({
                    "eula_accepted": True,
                    "accepted_at": env_at or datetime.now(timezone.utc).isoformat(),
                    "accepted_by": "env_variable",
                    "acceptance_hash": env_hash,
                    "eula_version": self.EULA_VERSION,
                    "license_files": self.LICENSE_FILES
                })
        
        # If both indicate acceptance but hashes don't match, prompt for re-acceptance
        elif json_data and env_accepted:
            json_hash = json_data.get("acceptance_hash", "")
            if json_hash and env_hash and json_hash != env_hash:
                logger.warning("EULA acceptance hash mismatch between JSON and .env")
                # Clear both to force re-acceptance
                self._clear_acceptance()
    
    def _clear_acceptance(self) -> None:
        """Clear EULA acceptance from both storage locations."""
        # Clear .env
        self.config.set("EULA_ACCEPTED", "false")
        self.config.set("EULA_ACCEPTED_AT", "")
        self.config.set("EULA_ACCEPTANCE_HASH", "")
        
        # Clear JSON
        if self.eula_json_path.exists():
            try:
                self.eula_json_path.unlink()
            except IOError as e:
                logger.warning(f"Could not delete eula_config.json: {e}")
    
    def is_accepted(self) -> bool:
        """
        Check if EULA has been accepted.
        
        Returns:
            True if EULA is accepted, False otherwise
        """
        self._sync_storage()
        
        # Check JSON first (authoritative)
        json_data = self._read_json_config()
        if json_data and json_data.get("eula_accepted"):
            return True
        
        # Fallback to .env
        return self.config.get("EULA_ACCEPTED", "").lower() == "true"
    
    def accept(self, accepted_by: str = "user_input") -> None:
        """
        Record EULA acceptance in both storage locations.
        
        Args:
            accepted_by: How acceptance was recorded (e.g., "user_input", "flag", "env_var")
        """
        acceptance_hash = self._generate_acceptance_hash()
        accepted_at = datetime.now(timezone.utc).isoformat()
        
        # Write to JSON (authoritative proof)
        json_data = {
            "eula_accepted": True,
            "accepted_at": accepted_at,
            "accepted_by": accepted_by,
            "acceptance_hash": acceptance_hash,
            "eula_version": self.EULA_VERSION,
            "license_files": self.LICENSE_FILES
        }
        self._write_json_config(json_data)
        
        # Write to .env (runtime configuration)
        self.config.set("EULA_ACCEPTED", "true")
        self.config.set("EULA_ACCEPTED_AT", accepted_at)
        self.config.set("EULA_ACCEPTANCE_HASH", acceptance_hash)
        
        logger.info("EULA acceptance recorded in dual storage")
    
    def display_eula_summary(self) -> str:
        """
        Display EULA summary text.
        
        Returns:
            EULA summary text
        """
        return """Alchemux — Terms Notice (Authorized, Non-Commercial Use Only)

By using this software you agree to the LICENSE, TERMS.md, and EULA.md.
Use only with content you own or are authorized to access.
No warranty. You assume all risk. You agree to defend and indemnify the Provider and contributors.

To continue:
  • Type: I AGREE
Or run non-interactively:
  • amx --accept-eula (or alchemux --accept-eula)
Or set:
  • EULA_ACCEPTED=true"""
    
    def interactive_acceptance(self) -> bool:
        """
        Prompt user for interactive EULA acceptance.
        
        Returns:
            True if user accepts, False otherwise
        """
        print("\n" + "=" * 70)
        print(self.display_eula_summary())
        print("=" * 70 + "\n")
        
        while True:
            response = input("Type \"I AGREE\" to confirm you are authorized to use any content you process and you accept the LICENSE, TERMS.md, and EULA.md: ").strip()
            
            if response.upper() == "I AGREE":
                self.accept("user_input")
                print("\n✓ EULA accepted. You may now use Alchemux.\n")
                return True
            elif response.lower() in ("quit", "exit", "q", "no", "n"):
                print("\n✗ EULA not accepted. Exiting.\n")
                return False
            else:
                print("Please type exactly \"I AGREE\" to continue, or 'quit' to exit.")
    
    def check_and_require_acceptance(self, accept_flag: bool = False, env_var: bool = False) -> bool:
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
        # Skip EULA enforcement when running from source (not packaged)
        if not is_packaged_build():
            logger.debug("Running from source - EULA enforcement skipped (Apache 2.0 license applies)")
            return True
        
        # EULA enforcement only for packaged builds
        if self.is_accepted():
            return True
        
        # Check for non-interactive acceptance methods
        if accept_flag:
            self.accept("flag")
            print("✓ EULA accepted via --accept-eula flag.\n")
            return True
        
        if env_var or os.getenv("EULA_ACCEPTED", "").lower() == "true":
            self.accept("env_var")
            print("✓ EULA accepted via EULA_ACCEPTED environment variable.\n")
            return True
        
        # Require interactive acceptance
        return self.interactive_acceptance()

