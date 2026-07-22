#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${MODBOT_APP_DIR:-/opt/modbot}"
SERVICE="${MODBOT_SERVICE:-modbot}"
BRANCH="${MODBOT_BRANCH:-main}"
REPO_URL="${MODBOT_REPO_URL:-https://github.com/nerochristian/modbot.git}"
BOT_ENTRYPOINT="${MODBOT_ENTRYPOINT:-bot.py}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
UPDATE_SERVICE="${MODBOT_UPDATE_SERVICE:-${SERVICE}-autoupdate}"
UPDATE_TIMER="${MODBOT_UPDATE_TIMER:-${UPDATE_SERVICE}.timer}"
UPDATE_ENV="${MODBOT_UPDATE_ENV:-/etc/${UPDATE_SERVICE}.env}"
DEPLOY_LOCK="${MODBOT_DEPLOY_LOCK:-/tmp/${SERVICE}-deploy.lock}"

SERVICE="${SERVICE%.service}"
UPDATE_SERVICE="${UPDATE_SERVICE%.service}"
UPDATE_TIMER="${UPDATE_TIMER%.timer}.timer"

case "${SERVICE}" in
  modbot-autoupdate|*-autoupdate)
    echo "MODBOT_SERVICE must be the bot service name, not an autoupdate service name." >&2
    exit 1
    ;;
esac

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with sudo/root on the VPS." >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1 || ! "${PYTHON_BIN}" -m venv --help >/dev/null 2>&1; then
  apt-get update
  apt-get install -y python3 python3-venv python3-pip
fi

if [[ ! -d "${APP_DIR}/.git" ]]; then
  mkdir -p "$(dirname "${APP_DIR}")"
  git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
fi

chmod +x "${APP_DIR}/scripts/vps_deploy.sh"

cat >"${UPDATE_ENV}" <<EOF
MODBOT_APP_DIR=${APP_DIR}
MODBOT_REPO_URL=${REPO_URL}
MODBOT_BRANCH=${BRANCH}
MODBOT_SERVICE=${SERVICE}
MODBOT_ENTRYPOINT=${BOT_ENTRYPOINT}
MODBOT_DEPLOY_LOCK=${DEPLOY_LOCK}
PYTHON_BIN=${PYTHON_BIN}
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
ExecStart=${APP_DIR}/.venv/bin/python ${APP_DIR}/${BOT_ENTRYPOINT}
Restart=always
RestartSec=10
KillSignal=SIGINT
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

cat >"/etc/systemd/system/${UPDATE_SERVICE}.service" <<EOF
[Unit]
Description=Deploy latest ${SERVICE} commit from GitHub
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=-${UPDATE_ENV}
ExecStart=/usr/bin/env bash ${APP_DIR}/scripts/vps_deploy.sh
EOF

cat >"/etc/systemd/system/${UPDATE_TIMER}" <<EOF
[Unit]
Description=Check GitHub for ${SERVICE} updates every minute

[Timer]
OnBootSec=30
OnUnitActiveSec=60
AccuracySec=10
Persistent=true
Unit=${UPDATE_SERVICE}.service

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now "${SERVICE}.service"
systemctl enable --now "${UPDATE_TIMER}"
systemctl start "${UPDATE_SERVICE}.service"

systemctl --no-pager --full status "${SERVICE}.service" || true
systemctl --no-pager --full status "${UPDATE_TIMER}" || true
