"""Read-only VPS inspection probe (deleted after use). UTF-8 safe."""
from __future__ import annotations

import os
import sys

# Force UTF-8 console output so systemd "●" glyphs don't crash cp1252 consoles.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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

# --- soul-update machinery (who/what does it update?) ---
print("########## soul-update machinery ##########")
run("systemctl cat soul-update.service 2>/dev/null || echo NO_soul-update.service")
run("systemctl cat soul-update.timer 2>/dev/null || echo NO_soul-update.timer")
run("cat /etc/modbot-autoupdate.env 2>/dev/null || echo NO_/etc/modbot-autoupdate.env")
run("cat /etc/soul-update.env 2>/dev/null || echo NO_/etc/soul-update.env")

# --- Confirm existing DocketBot autoupdate is working ---
print("\n########## DocketBot autoupdate recent log ##########")
run("journalctl -u modbot-autoupdate.service -n 20 --no-pager 2>/dev/null || echo NO_autoupdate_log")
run("systemctl is-enabled modbot-autoupdate.timer 2>/dev/null; systemctl is-active modbot-autoupdate.timer 2>/dev/null")

# --- Mahito (/root/modbot) ---
print("\n########## MAHITO (/root/modbot) ##########")
run("cd /root/modbot && echo '--- remote ---' && git remote -v && echo '--- branch ---' && git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD")
run("cd /root/modbot && echo '--- dirty tracked ---' && git status --porcelain --untracked-files=no && echo '(end dirty)'")
run("ls -la /root/modbot/ 2>/dev/null | head -40")
run("test -f /root/modbot/requirements.txt && echo HAS_requirements || echo NO_requirements")
run("test -d /root/modbot/.venv && echo HAS_.venv || echo NO_.venv")
run("cat /root/modbot/ecosystem.config.js 2>/dev/null || cat /root/modbot/ecosystem.config.cjs 2>/dev/null || echo NO_mahito_ecosystem_in_repo")

# --- PM2 ---
print("\n########## PM2 ##########")
run("command -v pm2 && pm2 -v")
run("pm2 describe modbot 2>/dev/null | sed -n '1,50p' || echo NO_pm2_modbot")

ssh.close()
print("\nInspection complete.", flush=True)
