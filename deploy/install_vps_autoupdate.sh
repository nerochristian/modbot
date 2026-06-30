#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${MODBOT_APP_DIR:-/opt/modbot}"
SERVICE="${MODBOT_SERVICE:-modbot}"
BRANCH="${MODBOT_BRANCH:-main}"
REPO_URL="${MODBOT_REPO_URL:-https://github.com/nerochristian/modbot.git}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with sudo/root on the VPS." >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git
fi

if ! command -v python3 >/dev/null 2>&1 || ! python3 -m venv --help >/dev/null 2>&1; then
  apt-get update
  apt-get install -y python3 python3-venv python3-pip
fi

if [[ ! -d "${APP_DIR}/.git" ]]; then
  mkdir -p "$(dirname "${APP_DIR}")"
  git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
fi

chmod +x "${APP_DIR}/scripts/vps_deploy.sh"

cat >/etc/modbot-autoupdate.env <<EOF
MODBOT_APP_DIR=${APP_DIR}
MODBOT_REPO_URL=${REPO_URL}
MODBOT_BRANCH=${BRANCH}
MODBOT_SERVICE=${SERVICE}
EOF

cat >"/etc/systemd/system/${SERVICE}.service" <<EOF
[Unit]
Description=ModBot Discord bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
EnvironmentFile=-${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/python ${APP_DIR}/bot.py
Restart=always
RestartSec=10
KillSignal=SIGINT
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/modbot-autoupdate.service <<EOF
[Unit]
Description=Deploy latest ModBot commit from GitHub
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=-/etc/modbot-autoupdate.env
ExecStart=/usr/bin/env bash ${APP_DIR}/scripts/vps_deploy.sh
EOF

install -m 0644 "${APP_DIR}/deploy/modbot-autoupdate.timer" /etc/systemd/system/modbot-autoupdate.timer

systemctl daemon-reload
systemctl enable --now "${SERVICE}.service"
systemctl enable --now modbot-autoupdate.timer
systemctl start modbot-autoupdate.service

systemctl --no-pager --full status "${SERVICE}.service" || true
systemctl --no-pager --full status modbot-autoupdate.timer || true
