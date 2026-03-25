"""
NiziPOS Configuration Manager
Handles API key generation, persistence, and platform detection.
"""

import os
import secrets
import json
import platform
import logging
from pathlib import Path
from platformdirs import user_config_dir

logger = logging.getLogger(__name__)

APP_NAME = "NiziPOS"
APP_AUTHOR = "Yarsa"

class Config:
    def __init__(self):
        self.config_dir = Path(user_config_dir(APP_NAME, APP_AUTHOR))
        self.config_file = self.config_dir / "config.json"
        self._config = {}
        self.load()

    def load(self):
        """Load configuration from disk, creating defaults if missing."""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)

        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self._config = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                self._config = {}
        else:
            self._config = {}

        # Ensure config exists for other settings if any (none yet but good to keep)
        pass

    def save(self):
        """Save configuration to disk."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self._config, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    @property
    def api_key(self) -> str:
        # Fixed secret token hardcoded in the app as requested.
        return "Z8uVovI2eftp65dO9JoxEstKcWggSlTAza4erAQhELmSC761rVtp5IIzaXOxWNw0ycPCICYCnJBCVPCzvdT8fbJvWIWm69fhHveZesIiDEIeI0BkdSspMPimWYNWs25D"


    @property
    def is_windows(self) -> bool:
        return platform.system() == "Windows"

    @property
    def is_macos(self) -> bool:
        return platform.system() == "Darwin"

    @property
    def is_linux(self) -> bool:
        return platform.system() == "Linux"

    @property
    def server_host(self) -> str:
        # Hardcoded to localhost for security
        return "127.0.0.1"

    @property
    def server_port(self) -> int:
        return 9121

    @property
    def github_repo(self) -> str:
        """
        GitHub repo in the form: "owner/name" used for OTA updates.

        You can set it in two ways:
        1) Environment variable: `NIZIPOS_GITHUB_REPO=owner/name`
        2) In config file: `{ "github_repo": "owner/name" }`

        If empty, OTA updates are disabled.
        """
        return (
            os.environ.get("NIZIPOS_GITHUB_REPO")
            or self._config.get("github_repo")
            or ""
        )

# Global singleton
config = Config()
