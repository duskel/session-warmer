"""Durable per-provider state (last ping, status, blocked-until, notify throttle).

Written atomically so a crash mid-write can never corrupt the file that decides
whether we're allowed to ping.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


def load_state(path: str) -> dict[str, Any]:
    file = Path(path)
    if not file.is_file():
        return {}
    try:
        return json.loads(file.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(path: str, state: dict[str, Any]) -> None:
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(file.parent), prefix=".state-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
        os.replace(tmp, file)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
