"""Configuration management for ANA."""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Main application configuration loaded from JSON."""

    def __init__(self, config_path: str = "config.json"):
        """Load configuration from JSON file and environment variables."""
        # Find config.json in project root
        project_root = Path(__file__).parent.parent.parent
        config_file = project_root / config_path

        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        # Load JSON config
        with open(config_file, "r") as f:
            self._config: dict[str, Any] = json.load(f)

        # Override sensitive credentials from environment
        self._config["email"]["user"] = os.getenv("GMAIL_USER")
        self._config["email"]["password"] = os.getenv("GMAIL_APP_PASSWORD")

    @property
    def email(self) -> dict[str, Any]:
        """Email configuration."""
        return self._config["email"]

    @property
    def hardware(self) -> dict[str, Any]:
        """Hardware configuration."""
        return self._config["hardware"]

    @property
    def model(self) -> dict[str, Any]:
        """Model configuration."""
        return self._config["model"]

    def is_email_configured(self) -> bool:
        """Check if email credentials are configured."""
        return bool(self.email.get("user") and self.email.get("password"))

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key."""
        return self._config.get(key, default)


# Global configuration instance
config = Config()
