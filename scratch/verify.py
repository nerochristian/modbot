"""One-shot: poll for auto-deploy of test commit 39a067b + Mahito restart. Deleted after use. UTF-8 safe."""
from __future__ import annotations

import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import paramiko

HOST = "docketbot.xyz"
USER = "root"
PASSWORD = os.environ["MODBOT_VPS_PASS"]
TARGET = "39a067b"


def run(cmd: str, *, timeout: int = 60) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout, get_pty=False)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return out + err


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"Connecting to {USER}@{HOST} ...", flush=True)
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)
print("Connected.\n", flush=True)

deployed = False
for attempt in range(12):  # ~120s max
    journal = run("journalctl -u mahito-autodeploy.service -n 20 --no-pager 2>&1")
    if TARGET in journal and ("Deploy complete" in journal or "restarted and online" in journal):
        deployed = True
        print(f"[attempt {attempt}] AUTO-DEPLOY DETECTED for {TARGET}:\n")
        # print only the relevant lines
        for line in journal.splitlines():
            if any(k in line for k in ("Fetching", "Deploying", "Deploy complete", "restarted", "requirements", "Compile", "Already up to date")):
                print("  " + line)
        break
    print(f"[attempt {attempt}] not yet deployed; waiting 10s...", flush=True)
    time.sleep(10)

print("\n===== PM2 modbot status (uptime should be low if restarted) =====")
print(run("pm2 describe modbot 2>&1 | grep -E 'status|uptime|restarts'"))

print("\n===== current git HEAD on VPS =====")
print(run("cd /root/modbot && git rev-parse --short HEAD"))

print("\n===== recent autodeploy journal (tail) =====")
print(run("journalctl -u mahito-autodeploy.service -n 12 --no-pager 2>&1 | tail -12"))

ssh.close()
print(f"\nRESULT: {'SUCCESS - auto-deploy worked' if deployed else 'NOT DETECTED within timeout'}", flush=True)
