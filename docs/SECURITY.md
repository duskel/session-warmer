# Security

`session-warmer` runs the `claude` and `codex` CLIs, which means the host holds
**OAuth tokens to paid AI accounts**. Treat that host as sensitive: a compromise
lets someone drain those accounts.

## Threat model in one line

The tool is a **scheduler with no listening socket**. It makes outbound calls
only (to the AI providers and to Resend). There is no inbound attack surface to
harden — so most of the work is protecting the tokens at rest and keeping the
box's *other* doors shut.

## Prefer a box you control

A home mini-PC, NUC, or Raspberry Pi that's always on is a better home for these
tokens than a cloud VPS — the credentials never leave hardware you hold. Use a
VPS only if you have no always-on local machine.

## If you use a VPS

- **Dedicated non-root user** (`warmer`). The scheduler never runs as root.
- **Nothing inbound.** Do not add a web dashboard on `0.0.0.0`. If you want a UI,
  bind it to `127.0.0.1` and reach it over an SSH tunnel.
- **Firewall default-deny inbound**, allow only SSH:
  ```bash
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow OpenSSH
  ufw enable
  ```
- **Harden SSH:** key-only auth, `PermitRootLogin no`, add `fail2ban`.
- **Secrets at rest:**
  - `secrets.env` is `chmod 600`, owned by `warmer`, and holds only the Resend
    key. It is git-ignored and never logged.
  - The CLI tokens live under the warmer user's home (`/var/lib/session-warmer`),
    reachable only by that user and root.
- **Auto-patch:** enable unattended security upgrades.
- **Assume disk seizure:** most VPS disks aren't yours to encrypt. If you don't
  fully trust the provider, re-authenticate the CLIs periodically and revoke
  from the account side if the box is ever retired.

## systemd hardening (already in the shipped unit)

`session-warmer@.service` runs with `NoNewPrivileges`, `ProtectSystem=strict`,
`ProtectHome`, `PrivateTmp`, restricted address families, and a single
`ReadWritePaths` (the state dir). Keep those in place.

## What is never written to disk or logs

- The Resend API key (environment only).
- AI provider tokens (managed by the CLIs, not by this tool).
- Full CLI responses — only a short, truncated error snippet is ever logged.

## Reporting

Found an issue? Open a private security advisory on the repository rather than a
public issue.
