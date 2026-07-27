"""One-shot: link /root/modbot to origin/guild NON-destructively and report drift. Deleted after use. UTF-8 safe."""
from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import paramiko

HOST = "docketbot.xyz"
USER = "root"
PASSWORD = os.environ["MODBOT_VPS_PASS"]


def run(cmd: str, *, timeout: int = 120) -> None:
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

run("cd /root/modbot && git init -b guild 2>&1 && (git remote remove origin 2>/dev/null; git remote add origin https://github.com/nerochristian/guild.git) && git fetch origin guild 2>&1 | tail -3")
run("cd /root/modbot && git reset origin/guild 2>&1 | tail -5 && git branch --set-upstream-to=origin/guild guild 2>&1")
run("cd /root/modbot && echo '--- HEAD ---' && git rev-parse HEAD && echo '--- upstream ---' && git rev-parse --abbrev-ref --symbolic-full-name @{u}")
run("cd /root/modbot && echo '=== TRACKED drift (M/D/A) between working tree and origin/guild ===' && git status --porcelain | grep -vE '^\\?\\?' || echo '(no tracked drift)'; echo '=== end ==='")
run("cd /root/modbot && echo '=== full status (first 30 lines) ===' && git status --porcelain | head -30; echo '=== end ==='")
run("pm2 describe modbot 2>&1 | grep -E 'status|uptime' || echo NO_pm2")

ssh.close()
print("\nLinkage phase-1 (non-destructive) complete.", flush=True)
