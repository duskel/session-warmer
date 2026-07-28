#!/usr/bin/env bash
# Install session-warmer on a Linux host with systemd.
# Run as root:  sudo bash scripts/install.sh
set -euo pipefail

APP_DIR=/opt/session-warmer
CONF_DIR=/etc/session-warmer
STATE_DIR=/var/lib/session-warmer
USER=warmer
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $EUID -ne 0 ]]; then
  echo "run as root: sudo bash scripts/install.sh" >&2
  exit 1
fi

echo "==> creating '$USER' user"
if ! id "$USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "$STATE_DIR" --shell /bin/bash "$USER"
fi

echo "==> laying out directories"
install -d -o "$USER" -g "$USER" -m 750 "$APP_DIR" "$STATE_DIR"
install -d -o "$USER" -g "$USER" -m 750 "$CONF_DIR"

echo "==> copying application code"
rm -rf "$APP_DIR/warmer"
cp -r "$SRC/warmer" "$APP_DIR/warmer"
chown -R "$USER:$USER" "$APP_DIR"

echo "==> config"
if [[ ! -f "$CONF_DIR/config.json" ]]; then
  cp "$SRC/config.example.json" "$CONF_DIR/config.json"
  chown "$USER:$USER" "$CONF_DIR/config.json"
  chmod 640 "$CONF_DIR/config.json"
  echo "    wrote $CONF_DIR/config.json  (edit 'to' + timezone)"
else
  echo "    keeping existing $CONF_DIR/config.json"
fi

echo "==> secrets"
if [[ ! -f "$CONF_DIR/secrets.env" ]]; then
  printf 'RESEND_API_KEY=\n' > "$CONF_DIR/secrets.env"
  chown "$USER:$USER" "$CONF_DIR/secrets.env"
  chmod 600 "$CONF_DIR/secrets.env"
  echo "    wrote $CONF_DIR/secrets.env  (put your Resend key in it)"
fi

echo "==> systemd units"
cp "$SRC/systemd/session-warmer@.service" /etc/systemd/system/
cp "$SRC/systemd/session-warmer@.timer" /etc/systemd/system/
systemctl daemon-reload

cat <<EOF

Installed. Finish setup:

  1. Sign the CLIs in AS THE WARMER USER (interactive, do this yourself):
       sudo -u $USER -H claude          # then complete the login
       sudo -u $USER -H codex login

  2. Add your Resend key:
       sudoedit $CONF_DIR/secrets.env

  3. Point notifications at your inbox + confirm timezone:
       sudoedit $CONF_DIR/config.json

  4. Test, then enable the schedule:
       cd $APP_DIR && sudo -u $USER python3 -m warmer --config $CONF_DIR/config.json test-notify
       systemctl enable --now session-warmer@claude.timer session-warmer@codex.timer

  Check state any time:
       cd $APP_DIR && sudo -u $USER python3 -m warmer --config $CONF_DIR/config.json status
       systemctl list-timers 'session-warmer@*'
EOF
