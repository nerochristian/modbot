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

install -m 0755 "${APP_DIR}/scripts/vps_deploy.sh" /usr/local/bin/modbot-deploy
ln -sf /usr/local/bin/modbot-deploy "${APP_DIR}/scripts/vps_deploy.sh"

cat >/etc/modbot-autoupdate.env <<EOF
MODBOT_APP_DIR=${APP_DIR}
MODBOT_REPO_URL=${REPO_URL}
MODBOT_BRANCH=${BRANCH}
MODBOT_SERVICE=${SERVICE}
EOF

install -m 0644 "${APP_DIR}/deploy/modbot.service" "/etc/systemd/system/${SERVICE}.service"
install -m 0644 "${APP_DIR}/deploy/modbot-autoupdate.service" /etc/systemd/system/modbot-autoupdate.service
install -m 0644 "${APP_DIR}/deploy/modbot-autoupdate.timer" /etc/systemd/system/modbot-autoupdate.timer

systemctl daemon-reload
systemctl enable --now "${SERVICE}.service"
systemctl enable --now modbot-autoupdate.timer
systemctl start modbot-autoupdate.service

systemctl --no-pager --full status "${SERVICE}.service" || true
systemctl --no-pager --full status modbot-autoupdate.timer || true
