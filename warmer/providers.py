"""Run a provider's warm command and classify what came back.

Classification is driven by regex patterns in the config so a change in a CLI's
wording is a config edit, not a code change. Everything falls back to a safe
default (never crash on an unparseable reset phrase).
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timedelta
from typing import Any

Status = str  # "ok" | "limited" | "weekly" | "error"


def run(pc: dict[str, Any]) -> tuple[int | None, str, str]:
    """Execute the warm command. Returns (returncode, stdout, stderr).

    The command runs in ``cwd`` (a neutral directory) when set, so an agentic
    CLI can't wander into a real project and start doing work.
    """
    try:
        proc = subprocess.run(
            pc["command"],
            capture_output=True,
            text=True,
            timeout=pc["timeout_seconds"],
            stdin=subprocess.DEVNULL,
            cwd=pc.get("cwd") or None,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return None, "", "command timed out"
    except FileNotFoundError:
        return None, "", f"command not found: {pc['command'][0]}"


def classify(
    pc: dict[str, Any],
    returncode: int | None,
    stdout: str,
    stderr: str,
    now: datetime,
) -> tuple[Status, datetime | None]:
    text = f"{stdout}\n{stderr}".lower()

    def matches(patterns: list[str]) -> bool:
        return any(re.search(p, text) for p in patterns)

    if matches(pc["weekly_patterns"]):
        return "weekly", _parse_reset(pc, text, now, default=now + timedelta(days=1))
    if matches(pc["limit_patterns"]):
        return "limited", _parse_reset(pc, text, now, default=now + timedelta(hours=5))
    if returncode not in (0,):
        return "error", None
    return "ok", None


def _parse_reset(
    pc: dict[str, Any], text: str, now: datetime, default: datetime
) -> datetime:
    for pattern in pc.get("reset_patterns", []):
        match = re.search(pattern, text)
        if match and match.groups():
            parsed = _parse_phrase(match.group(1).strip(), now)
            if parsed:
                return parsed
    return default


def _parse_phrase(phrase: str, now: datetime) -> datetime | None:
    relative = re.search(r"(\d+)\s*(hour|hr|h|minute|min|m)", phrase)
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2)
        if unit.startswith("h"):
            return now + timedelta(hours=amount)
        return now + timedelta(minutes=amount)

    clock = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", phrase)
    if clock:
        hour = int(clock.group(1))
        minute = int(clock.group(2) or 0)
        meridiem = clock.group(3)
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now:
                candidate += timedelta(days=1)
            return candidate
    return None
