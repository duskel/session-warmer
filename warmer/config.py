"""Configuration loading and validation.

Config is a single JSON file (stdlib only, no TOML dependency so it runs on any
Python 3.9+). Secrets never live here — the Resend API key comes from the
environment, injected by systemd's EnvironmentFile.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = "/etc/session-warmer/config.json"


class ConfigError(Exception):
    """Raised when the config file is missing or malformed."""


def load_config(path: str | None = None) -> dict[str, Any]:
    resolved = path or os.environ.get("WARMER_CONFIG", DEFAULT_CONFIG_PATH)
    file = Path(resolved)
    if not file.is_file():
        raise ConfigError(f"config not found: {resolved}")
    try:
        data = json.loads(file.read_text())
    except json.JSONDecodeError as exc:
        raise ConfigError(f"config is not valid JSON: {exc}") from exc

    data.setdefault("timezone", "UTC")
    data.setdefault("state_path", "/var/lib/session-warmer/state.json")
    data.setdefault("providers", {})
    data.setdefault("notify", {})
    return data


def provider_config(config: dict[str, Any], name: str) -> dict[str, Any]:
    providers = config.get("providers", {})
    if name not in providers:
        raise ConfigError(f"unknown provider '{name}' (known: {', '.join(providers) or 'none'})")

    pc = providers[name]
    pc.setdefault("enabled", True)
    pc.setdefault("timeout_seconds", 120)
    pc.setdefault("limit_patterns", [])
    pc.setdefault("weekly_patterns", [])
    pc.setdefault("reset_patterns", [])
    if not pc.get("command"):
        raise ConfigError(f"provider '{name}' has no command")
    return pc
