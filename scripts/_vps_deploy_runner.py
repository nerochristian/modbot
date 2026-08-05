"""One-shot VPS deploy runner (paramiko). Not committed; deleted after use.

Connects to the modbot VPS, pulls the latest main, runs a compile check, and
restarts the bot via whichever process manager actually owns it (systemd
`modbot` service or PM2 `modbot` app). The deploy script on the box
(scripts/vps_deploy.sh) encodes the canonical git-pull + compile + restart
flow and refuses a dirty tree, so we drive it directly when present.
"""
from __future__ import annotations

import os
import sys

import paramiko

HOST = "docketbot.xyz"
USER = "root"
APP_DIR = "/opt/modbot"
PASSWORD = os.environ["MODBOT_VPS_PASS"]


def run(cmd: str, *, timeout: int = 300) -> tuple[int, str, str]:
    print(f"\n$ {cmd}", flush=True)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout, get_pty=False)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out, end="", flush=True)
    if err:
        print(err, end="", file=sys.stderr, flush=True)
    print(f"[exit {rc}]", flush=True)
    return rc, out, err


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"Connecting to {USER}@{HOST} ...", flush=True)
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)
print("Connected.", flush=True)

# 1. Confirm the app dir and current commit before touching anything.
run(f"test -d {APP_DIR}/.git && echo APP_DIR_OK || echo APP_DIR_MISSING")
run(f"cd {APP_DIR} && git rev-parse --short HEAD 2>/dev/null || echo NO_GIT")
run(f"cd {APP_DIR} && git status --porcelain --untracked-files=no || echo NO_GIT")

# 2. Fetch + fast-forward to origin/main. The deploy script refuses a dirty
#    tree, so a clean ff-only is the safe pre-step.
run(f"cd {APP_DIR} && git fetch --prune origin main")
run(f"cd {APP_DIR} && git merge --ff-only origin/main")

# 3. Compile check BEFORE restarting, so a syntax error can never take the
#    bot down. Mirrors vps_deploy.sh's compile_check.
rc_compile, _, _ = run(
    f"cd {APP_DIR} && python3 -m compileall -q bot.py cogs utils database.py config.py 2>&1"
)
if rc_compile != 0:
    print("COMPILE CHECK FAILED -- aborting restart.", file=sys.stderr)
    ssh.close()
    sys.exit(1)

# 4. Detect the process manager and restart the bot. Prefer the systemd
#    service the deploy script targets; fall back to PM2 if that's what's
#    actually running the bot. Never print `pm2 jlist`: it includes the full
#    process environment and can expose production credentials in deploy logs.
rc_systemctl, out_systemctl, _ = run("systemctl cat modbot >/dev/null 2>&1 && echo SYSTEMD_MODBOT || echo NO_SYSTEMD")
rc_pm2, out_pm2, _ = run(
    "command -v pm2 >/dev/null 2>&1 && "
    "test -n \"$(pm2 pid modbot 2>/dev/null | grep -E '^[0-9]+$' | grep -v '^0$' | head -1)\" "
    "&& echo PM2_MODBOT || echo NO_PM2_MODBOT"
)

if "SYSTEMD_MODBOT" in out_systemctl:
    run("systemctl restart modbot")
    run("sleep 3 && systemctl is-active --quiet modbot && echo MODBOT_ACTIVE || echo MODBOT_FAILED")
elif "PM2_MODBOT" in out_pm2:
    run("pm2 restart modbot --update-env")
    run("pm2 save")
    run("sleep 3 && pm2 describe modbot >/dev/null && echo MODBOT_PM2_OK || echo MODBOT_PM2_FAILED")
else:
    print("Could not determine process manager (no systemd modbot, no PM2 modbot app).", file=sys.stderr)
    print("Recent processes:", file=sys.stderr)
    run("ps -eo pid,comm,args --sort=-start_time | grep -E 'bot.py|python3' | grep -v grep | head -20")
    ssh.close()
    sys.exit(1)

# 5. Tail the recent bot log so we can see it came back healthy.
run(f"cd {APP_DIR} && (journalctl -u modbot -n 15 --no-pager 2>/dev/null || pm2 logs modbot --nostream --lines 15 2>/dev/null) || echo NO_LOG")

ssh.close()
print("\nDeploy complete.", flush=True)
