"""Email notifications via Resend, using only urllib (no SDK).

The API key is read from the environment (never from disk config). Sending is
throttled per provider so a flapping error can't spam the inbox — except weekly
limits, which always send because you need to know immediately.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from typing import Any

RESEND_ENDPOINT = "https://api.resend.com/emails"
# Resend sits behind Cloudflare, which 403s the default "Python-urllib/x.y"
# User-Agent. Send an explicit one so the request is accepted.
USER_AGENT = "session-warmer/1.0 (+https://github.com/duskel/session-warmer)"


def _should_send(ncfg: dict[str, Any], provider_state: dict[str, Any], now: datetime, force: bool) -> bool:
    if not ncfg.get("enabled", False):
        return False
    if force:
        return True
    last = provider_state.get("last_notify_at")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
        except ValueError:
            return True
        window = timedelta(minutes=ncfg.get("min_interval_minutes", 60))
        if now - last_dt < window:
            return False
    return True


def send_email(ncfg: dict[str, Any], subject: str, body: str) -> int:
    key = os.environ.get(ncfg.get("resend_api_key_env", "RESEND_API_KEY"))
    if not key:
        raise RuntimeError("Resend API key is not set in the environment")

    recipients = ncfg["to"]
    if isinstance(recipients, str):
        recipients = [recipients]

    payload = {"from": ncfg["from"], "to": recipients, "subject": subject, "text": body}
    request = urllib.request.Request(
        RESEND_ENDPOINT,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status


def notify(
    ncfg: dict[str, Any],
    provider_state: dict[str, Any],
    now: datetime,
    subject: str,
    body: str,
    force: bool = False,
) -> bool:
    if not _should_send(ncfg, provider_state, now, force):
        return False
    try:
        send_email(ncfg, subject, body)
        provider_state["last_notify_at"] = now.isoformat()
        return True
    except (urllib.error.URLError, RuntimeError, KeyError) as exc:
        print(f"[warmer] notify failed: {exc}", file=sys.stderr)
        return False
