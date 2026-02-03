"""Configuration for PromptElo client."""

import json
import os
from pathlib import Path
from typing import Optional

# Default server URL (update this after deploying to Render)
DEFAULT_SERVER_URL = "https://promptelo-api.onrender.com"

# Config file location
CONFIG_DIR = Path.home() / ".promptelo"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_config() -> dict:
    """Load configuration from file or return defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    return {
        "server_url": DEFAULT_SERVER_URL,
        "user_id": None,
        "timeout": 5.0
    }


def save_config(config: dict) -> None:
    """Save configuration to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_server_url() -> str:
    """Get the configured server URL."""
    # Environment variable takes precedence
    env_url = os.getenv("PROMPTELO_SERVER_URL")
    if env_url:
        return env_url

    config = get_config()
    return config.get("server_url", DEFAULT_SERVER_URL)


def get_user_id() -> Optional[str]:
    """Get the configured user ID for personal stats tracking."""
    env_user = os.getenv("PROMPTELO_USER_ID")
    if env_user:
        return env_user

    config = get_config()
    return config.get("user_id")


def get_timeout() -> float:
    """Get the configured request timeout."""
    config = get_config()
    return config.get("timeout", 5.0)
