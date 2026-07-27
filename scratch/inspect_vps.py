"""Read-only VPS inspection probe (deleted after use)."""
from __future__ import annotations

import os
import sys

import paramiko

HOST = "docketbot.xyz"
USER = "root"
PASSWORD = os.environ["MODBOT_VPS_PASS"]


def run(cmd: str, *, timeout: int = 60) -> None:
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


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"Connecting to {USER}@{HOST} ...", flush=True)
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)
print("Connected.\n", flush=True)

# --- DocketBot (/opt/modbot) ---
print("########## DOCKETBOT (/opt/modbot) ##########")
run("cd /opt/modbot && echo '--- remote ---' && git remote -v && echo '--- branch ---' && git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD")
run("cd /opt/modbot && echo '--- dirty tracked ---' && git status --porcelain --untracked-files=no && echo '(end dirty)'")
run("ls -la /opt/modbot/scripts/ 2>/dev/null")
run("test -f /opt/modbot/scripts/vps_deploy.sh && echo DEPLOY_SCRIPT_PRESENT || echo DEPLOY_SCRIPT_MISSING")
run("systemctl cat modbot 2>/dev/null | head -40")

# --- Existing auto-update machinery ---
print("\n########## EXISTING AUTO-UPDATE MACHINERY ##########")
run("systemctl list-timers --all --no-pager 2>/dev/null | head -40")
run("systemctl cat modbot-autoupdate.service 2>/dev/null || echo NO_modbot-autoupdate.service")
run("systemctl cat modbot-autoupdate.timer 2>/dev/null || echo NO_modbot-autoupdate.timer")
run("systemctl list-units --type=service --all --no-pager 2>/dev/null | grep -i -E 'update|deploy|autodeploy|github' || echo NO_update_units")
run("crontab -l 2>/dev/null || echo NO_root_crontab")
run("ls -la /etc/cron.d/ 2>/dev/null")
run("grep -rIl -E 'modbot|guild|mahito|deploy' /etc/cron.d/ /etc/cron.daily/ /etc/cron.hourly/ 2>/dev/null || echo NO_cron_matches")

# --- Mahito (/root/modbot) ---
print("\n########## MAHITO (/root/modbot) ##########")
run("cd /root/modbot && echo '--- remote ---' && git remote -v && echo '--- branch ---' && git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD")
run("cd /root/modbot && echo '--- dirty tracked ---' && git status --porcelain --untracked-files=no && echo '(end dirty)'")
run("ls -la /root/modbot/ 2>/dev/null | head -40")
run("test -f /root/modbot/requirements.txt && echo HAS_requirements || echo NO_requirements")
run("test -d /root/modbot/.venv && echo HAS_.venv || echo NO_.venv")

# --- PM2 ---
print("\n########## PM2 ##########")
run("command -v pm2 && pm2 -v")
run("pm2 jlist 2>/dev/null")
run("pm2 describe modbot 2>/dev/null | head -60 || echo NO_pm2_modbot")
run("cat /root/modbot/ecosystem.config.* 2>/dev/null || echo NO_mahito_ecosystem")
run("cat /opt/modbot/dashboard/ecosystem.config.cjs 2>/dev/null || echo NO_dashboard_ecosystem")

ssh.close()
print("\nInspection complete.", flush=True)
