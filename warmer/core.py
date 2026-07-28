"""The warm/status/test-notify commands and the edge-case state machine."""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from . import config as config_mod
from . import notify as notify_mod
from . import providers as providers_mod
from . import state as state_mod


def _log(message: str) -> None:
    print(f"[warmer] {message}", file=sys.stderr)


def _now(timezone: str) -> datetime:
    return datetime.now(ZoneInfo(timezone))


def warm(provider: str, config_path: str | None = None) -> int:
    config = config_mod.load_config(config_path)
    timezone = config["timezone"]
    pc = config_mod.provider_config(config, provider)
    state = state_mod.load_state(config["state_path"])
    ps = state.setdefault(provider, {})
    now = _now(timezone)

    if not pc["enabled"]:
        _log(f"{provider}: disabled — skipping")
        return 0

    blocked_until = state_mod.parse_iso(ps.get("blocked_until"))
    if blocked_until and now < blocked_until:
        _log(f"{provider}: blocked until {blocked_until:%a %H:%M %Z} — skipping ping")
        return 0

    returncode, stdout, stderr = providers_mod.run(pc)
    status, reset_at = providers_mod.classify(pc, returncode, stdout, stderr, now)

    ps["last_ping_at"] = now.isoformat()
    ps["last_status"] = status

    if status == "ok":
        ps["blocked_until"] = None
        ps["consecutive_errors"] = 0
        _log(f"{provider}: warmed OK — window open at {now:%H:%M %Z}")
    elif status in ("limited", "weekly"):
        ps["blocked_until"] = reset_at.isoformat() if reset_at else None
        ps["consecutive_errors"] = 0
        _handle_limit(config, provider, status, reset_at, now, ps)
    else:
        ps["consecutive_errors"] = ps.get("consecutive_errors", 0) + 1
        detail = (stderr or stdout).strip()[:200]
        _log(f"{provider}: error — {detail}")
        if ps["consecutive_errors"] >= 2:
            _handle_error(config, provider, detail, now, ps)

    state_mod.save_state(config["state_path"], state)
    return 0


def _handle_limit(
    config: dict[str, Any],
    provider: str,
    status: str,
    reset_at: datetime | None,
    now: datetime,
    ps: dict[str, Any],
) -> None:
    ncfg = config.get("notify", {})
    reset_str = f"{reset_at:%a %d %b, %H:%M %Z}" if reset_at else "an unknown time"

    if status == "weekly":
        subject = f"[session-warmer] {provider}: WEEKLY limit reached"
        body = (
            f"{provider} hit its weekly limit at {now:%H:%M %Z} on {now:%a %d %b}.\n\n"
            f"Warming is paused until {reset_str}.\n"
            f"Plan the rest of your week around this — no amount of pinging brings it back."
        )
        notify_mod.notify(ncfg, ps, now, subject, body, force=True)
    else:
        subject = f"[session-warmer] {provider}: 5-hour limit reached"
        body = (
            f"{provider} hit its 5-hour limit at {now:%H:%M %Z}.\n\n"
            f"The next window unlocks around {reset_str}. Warming resumes automatically then."
        )
        notify_mod.notify(ncfg, ps, now, subject, body)

    _log(f"{provider}: {status} — blocked until {reset_str}")


def _handle_error(
    config: dict[str, Any],
    provider: str,
    detail: str,
    now: datetime,
    ps: dict[str, Any],
) -> None:
    ncfg = config.get("notify", {})
    count = ps.get("consecutive_errors", 0)
    subject = f"[session-warmer] {provider}: warming failing ({count}x)"
    body = (
        f"{provider} failed to warm {count} times in a row.\n"
        f"Last error at {now:%H:%M %Z}:\n\n{detail}\n\n"
        f"Check that the CLI is installed and signed in as the warmer user."
    )
    notify_mod.notify(ncfg, ps, now, subject, body)


def status(config_path: str | None = None) -> int:
    config = config_mod.load_config(config_path)
    state = state_mod.load_state(config["state_path"])
    now = _now(config["timezone"])
    print(f"session-warmer — {now:%a %d %b %Y %H:%M %Z}\n")

    providers = config.get("providers", {})
    if not providers:
        print("  no providers configured")
        return 0

    for name in providers:
        ps = state.get(name, {})
        last = ps.get("last_ping_at", "never")
        last_status = ps.get("last_status", "—")
        blocked = state_mod.parse_iso(ps.get("blocked_until"))
        if blocked and now < blocked:
            blocked = blocked.astimezone(ZoneInfo(config["timezone"]))
            standing = f"BLOCKED until {blocked:%a %H:%M %Z}"
        else:
            standing = "ready"
        print(f"  {name:8} {standing:32} last: {last_status} @ {last}")
    return 0


def test_notify(config_path: str | None = None) -> int:
    config = config_mod.load_config(config_path)
    ncfg = config.get("notify", {})
    now = _now(config["timezone"])
    ok = notify_mod.notify(
        ncfg,
        {},
        now,
        "[session-warmer] test notification",
        f"If you're reading this, Resend delivery works. Sent {now:%H:%M %Z}.",
        force=True,
    )
    if ok:
        print("test email sent")
        return 0
    print("test email NOT sent — check notify.enabled and RESEND_API_KEY", file=sys.stderr)
    return 1
