# session-warmer

Keep your Claude Code and Codex CLI **usage windows aligned to your day**.

Both tools meter usage in a **5-hour rolling window that starts on your first
message**. If that first message lands at a random time, your reset boundaries
drift into the middle of your work. `session-warmer` sends one tiny prompt at
each boundary so windows open at predictable local times — and when a limit is
actually hit, it stops pinging and emails you when the reset is.

It is a **scheduler, not a server**: nothing listens on a port, so there is
almost no attack surface to secure.

> It does **not** bypass, extend, or inflate any limit — that's not possible.
> It only chooses *when* the rolling window begins, and tells you when you're
> blocked. Keep it to one ping per boundary; that's all it does.

## How the window works (why this helps)

Send a message at 07:00 → your window runs 07:00–12:00. The next window only
starts on your first message after 12:00. Anchoring the first ping at a fixed
hour tiles the day cleanly:

| Ping (local) | Window |
| --- | --- |
| 07:00 | 07:00–12:00 |
| 12:00 | 12:00–17:00 |
| 17:00 | 17:00–22:00 |
| 22:00 | 22:00–03:00 *(optional)* |

The weekly cap is separate and can't be warmed around — so the tool instead
**watches for it** and emails you the moment you hit it.

## Install (Linux + systemd)

```bash
git clone https://github.com/duskel/session-warmer
cd session-warmer
sudo bash scripts/install.sh
```

Then finish the three manual steps the installer prints:

1. **Sign the CLIs in as the warmer user** (interactive — you do this):
   ```bash
   sudo -u warmer -H claude       # complete the login
   sudo -u warmer -H codex login
   ```
2. Put your **Resend API key** in `/etc/session-warmer/secrets.env`.
3. Set your **timezone** and notification **`to`** address in
   `/etc/session-warmer/config.json`.

Test and enable:

```bash
cd /opt/session-warmer
sudo -u warmer python3 -m warmer --config /etc/session-warmer/config.json test-notify
systemctl enable --now session-warmer@claude.timer session-warmer@codex.timer
systemctl list-timers 'session-warmer@*'
```

## Configuration

Everything except secrets lives in `config.json`:

- `timezone` — IANA name, e.g. `Asia/Karachi`. Drives both scheduling and the
  timestamps in emails.
- `notify` — Resend `from`/`to`, and `min_interval_minutes` throttle. The API
  key is **never** in this file; it's read from the environment.
- `providers.<name>.command` — the warm command (tune freely).
- `providers.<name>.limit_patterns` / `weekly_patterns` / `reset_patterns` —
  regexes that classify a CLI's output. If a CLI changes its wording, edit these
  — no code change needed.

The schedule itself lives in `systemd/session-warmer@.timer` (`OnCalendar`).
Edit it and `systemctl daemon-reload` to change hours.

## Commands

```bash
python3 -m warmer warm --provider claude   # what the timer runs
python3 -m warmer status                   # per-provider standing
python3 -m warmer test-notify              # verify Resend delivery
```

## Edge cases it handles

- **5-hour limit hit** → records the reported reset, skips pings until then,
  emails you the unlock time.
- **Weekly limit hit** → pauses warming for that provider and sends an immediate
  (un-throttled) alert.
- **Box was down at a boundary** → the missed ping is *not* fired late
  (`Persistent=false`), so a window never opens at the wrong hour.
- **CLI not installed / signed out** → after two consecutive failures, emails
  you the error instead of failing silently.

## Security

This holds OAuth tokens to paid AI accounts. Read [`docs/SECURITY.md`](docs/SECURITY.md)
before deploying — short version: dedicated non-root user, no inbound service,
secrets `600`, hardened systemd unit, and a preference for a box you control.

## License

MIT © Duskel
