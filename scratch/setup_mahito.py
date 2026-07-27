"""One-shot Mahito auto-deploy setup (deleted after use). UTF-8 safe.

Installs a DORMANT auto-deploy pipeline for Mahito (PM2 `modbot`, /root/modbot):
  * backs up /root/modbot (code+config) to /root/modbot.pre-autodeploy.tgz
  * /usr/local/sbin/mahito-autodeploy.sh   (git fetch -> ff-only -> deps -> compile -> pm2 restart, with rollback)
  * /etc/mahito-autodeploy.env
  * systemd service + 60s timer (enabled), but the script NO-OPS until /root/modbot is a git repo linked to origin/guild.
Does NOT touch the running bot. Live->GitHub push + initial git linkage happen after.
"""
from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import paramiko

HOST = "docketbot.xyz"
USER = "root"
PASSWORD = os.environ["MODBOT_VPS_PASS"]

DEPLOY_SCRIPT = r"""#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${MAHITO_APP_DIR:-/root/modbot}"
REPO_URL="${MAHITO_REPO_URL:-https://github.com/nerochristian/guild.git}"
REMOTE="${MAHITO_REMOTE:-origin}"
BRANCH="${MAHITO_BRANCH:-guild}"
PM2_APP="${MAHITO_PM2_APP:-modbot}"
LOCK_FILE="${MAHITO_DEPLOY_LOCK:-/tmp/${PM2_APP}-autodeploy.lock}"
PYTHON_BIN="${MAHITO_PYTHON_BIN:-python3}"

log() { printf '[%s] %s\n' "$(date -Is)" "$*"; }

(
  flock -n 9 || { log "Another Mahito deploy is already running."; exit 0; }

  # Dormant until /root/modbot is linked to origin/guild (initial manual sync).
  if [[ ! -d "${APP_DIR}/.git" ]]; then
    log "Not a git repo yet (${APP_DIR}); waiting for initial Live->GitHub sync."
    exit 0
  fi

  cd "${APP_DIR}"

  if ! git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
    log "No upstream configured for ${APP_DIR}; waiting for initial sync."
    exit 0
  fi

  log "Fetching ${REMOTE}/${BRANCH}."
  git fetch --prune "${REMOTE}" "${BRANCH}"

  current_commit="$(git rev-parse HEAD)"
  target_commit="$(git rev-parse "${REMOTE}/${BRANCH}")"

  if [[ "${current_commit}" == "${target_commit}" ]]; then
    log "Already up to date at ${current_commit}."
    exit 0
  fi

  # Discard any local tracked edits (GitHub is source of truth); keep untracked
  # runtime files (.env, data, db, backups, LifeSimBot) intact.
  git reset --hard "${current_commit}"

  log "Deploying ${current_commit} -> ${target_commit}."
  if ! git merge --ff-only "${REMOTE}/${BRANCH}"; then
    log "Fast-forward failed (history diverged). Refusing to force; manual sync needed."
    exit 1
  fi

  rollback() {
    log "Deploy failed; rolling back to ${current_commit}."
    git reset --hard "${current_commit}" || true
    pm2 restart "${PM2_APP}" --update-env || true
    pm2 save || true
  }

  if git diff --name-only "${current_commit}" "${target_commit}" | grep -q '^requirements.txt$'; then
    log "requirements.txt changed; installing dependencies."
    if ! "${PYTHON_BIN}" -m pip install --disable-pip-version-check -r requirements.txt; then
      rollback; exit 1
    fi
  fi

  if ! "${PYTHON_BIN}" -m compileall -q -x '(^|/)(\.git|python-embed|LifeSimBot|data|backups|scratch)(/|$)' .; then
    log "Compile check failed."
    rollback; exit 1
  fi

  if ! pm2 restart "${PM2_APP}" --update-env; then
    log "pm2 restart failed."
    rollback; exit 1
  fi
  pm2 save || true

  sleep 3
  if pm2 describe "${PM2_APP}" 2>/dev/null | grep -q 'online'; then
    log "Deploy complete at $(git rev-parse --short HEAD); ${PM2_APP} restarted and online."
    exit 0
  fi

  log "${PM2_APP} not online after restart."
  rollback
  exit 1
) 9>"${LOCK_FILE}"
"""

ENV_FILE = """MAHITO_APP_DIR=/root/modbot
MAHITO_REPO_URL=https://github.com/nerochristian/guild.git
MAHITO_BRANCH=guild
MAHITO_PM2_APP=modbot
"""

SERVICE_UNIT = """[Unit]
Description=Deploy latest Mahito (guild) commit from GitHub
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
Environment=HOME=/root
EnvironmentFile=-/etc/mahito-autodeploy.env
ExecStart=/usr/bin/env bash /usr/local/sbin/mahito-autodeploy.sh
"""

TIMER_UNIT = """[Unit]
Description=Check GitHub for Mahito (guild) updates every minute

[Timer]
OnBootSec=45
OnUnitActiveSec=60
AccuracySec=10
Persistent=true
Unit=mahito-autodeploy.service

[Install]
WantedBy=timers.target
"""


def run(cmd: str, *, timeout: int = 180) -> tuple[int, str, str]:
    print(f"\n===== $ {cmd}", flush=True)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout, get_pty=False)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out, end="", flush=True)
    if err:
        print(f"(stderr) {err}", end="", file=sys.stderr, flush=True)
    print(f"[exit {rc}]", flush=True)
    return rc, out, err


def sftp_write(remote_path: str, content: str, mode: int | None = None) -> None:
    print(f"\n===== SFTP write {remote_path} ({len(content)} bytes)", flush=True)
    with sftp.open(remote_path, "w") as f:
        f.write(content)
    if mode is not None:
        sftp.chmod(remote_path, mode)
    print("written.", flush=True)


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"Connecting to {USER}@{HOST} ...", flush=True)
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)
print("Connected.", flush=True)
sftp = ssh.open_sftp()

# 1. Safety backup of live Mahito (code + config, exclude big/regenerable runtime).
run(
    "tar czf /root/modbot.pre-autodeploy.tgz "
    "--exclude='modbot/python-embed' --exclude='modbot/python-embed.zip' "
    "--exclude='modbot/__pycache__' --exclude='modbot/*/__pycache__' "
    "--exclude='modbot/data' --exclude='modbot/backups' --exclude='*.pyc' "
    "-C /root modbot 2>&1 | tail -3; ls -lh /root/modbot.pre-autodeploy.tgz"
)

# 2. Install deploy script + config + units.
sftp_write("/usr/local/sbin/mahito-autodeploy.sh", DEPLOY_SCRIPT, mode=0o755)
sftp_write("/etc/mahito-autodeploy.env", ENV_FILE, mode=0o644)
sftp_write("/etc/systemd/system/mahito-autodeploy.service", SERVICE_UNIT, mode=0o644)
sftp_write("/etc/systemd/system/mahito-autodeploy.timer", TIMER_UNIT, mode=0o644)

# 3. Syntax-check the script before enabling.
run("bash -n /usr/local/sbin/mahito-autodeploy.sh && echo SCRIPT_SYNTAX_OK")

# 4. Enable + start the timer (dormant until git linkage exists).
run("systemctl daemon-reload")
run("systemctl enable --now mahito-autodeploy.timer")
run("systemctl is-enabled mahito-autodeploy.timer; systemctl is-active mahito-autodeploy.timer")

# 5. Fire the service once to prove it no-ops safely (not a git repo yet).
run("systemctl start mahito-autodeploy.service; sleep 1")
run("journalctl -u mahito-autodeploy.service -n 8 --no-pager 2>&1 | tail -8")

# 6. Confirm the live bot is untouched.
run("pm2 describe modbot 2>&1 | grep -E 'status|uptime|script path' || echo NO_pm2_modbot")

sftp.close()
ssh.close()
print("\nMahito auto-deploy (dormant) setup complete.", flush=True)
