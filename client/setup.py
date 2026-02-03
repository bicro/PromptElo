#!/usr/bin/env python3
"""PromptElo first-run setup script.

This script runs on SessionStart to show a welcome message on first run
and auto-generate an anonymous user ID.
"""

import json
import sys
import uuid
from pathlib import Path

CONFIG_DIR = Path.home() / ".promptelo"
CONFIG_FILE = CONFIG_DIR / "config.json"

WELCOME_MESSAGE = """Welcome to PromptElo! Your prompts are now scored with Elo ratings.

Defaults:
  - Server: Global rankings (promptelo-api.onrender.com)
  - Identity: Anonymous (auto-generated ID)

To customize: Run /promptelo:setup
To view detailed stats: Run /promptelo"""


def load_config() -> dict:
    """Load existing config or return empty dict."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_config(config: dict) -> None:
    """Save config to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def generate_user_id() -> str:
    """Generate an anonymous user ID."""
    return f"anon-{uuid.uuid4().hex[:12]}"


def main():
    """Run first-time setup if needed."""
    config = load_config()

    # Check if setup already complete
    if config.get("setup_complete"):
        # Already set up, exit silently
        return

    # First run - show welcome message
    output = {
        "systemMessage": WELCOME_MESSAGE
    }
    print(json.dumps(output))

    # Generate anonymous user ID if not set
    if not config.get("user_id"):
        config["user_id"] = generate_user_id()

    # Set defaults
    config.setdefault("server_url", "https://promptelo-api.onrender.com")
    config.setdefault("timeout", 5.0)
    config["setup_complete"] = True

    # Save updated config
    save_config(config)


if __name__ == "__main__":
    main()
