"""Read-only: Mahito identity + DocketBot autoupdate health. UTF-8 safe."""
from __future__ import annotations

import os
import sys

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

print("########## Mahito identity (/root/modbot) ##########")
run("echo '--- agent.md ---' && sed -n '1,60p' /root/modbot/agent.md 2>&1")
run("echo '--- bot.py head ---' && sed -n '1,40p' /root/modbot/bot.py 2>&1")
run("echo '--- .env variable NAMES only (values redacted) ---' && sed -E 's/=.*/=<redacted>/' /root/modbot/.env 2>&1")
run("echo '--- any git/remote hints ---' && ls -la /root/modbot/.github 2>&1; cat /root/modbot/.github/workflows/* 2>/dev/null | head -40 || echo NO_workflows")

print("\n########## DocketBot health ##########")
run("systemctl is-active modbot 2>&1; systemctl is-enabled modbot 2>&1")
run("echo '--- modbot-autoupdate last runs ---' && journalctl -u modbot-autoupdate.service -n 6 --no-pager 2>&1 | grep -E 'Already up to date|Deploying|Deploy complete|Refusing|failed|error' | tail -6")
run("echo '--- modbot recent log ---' && journalctl -u modbot -n 8 --no-pager 2>&1 | tail -8")
run("echo '--- pm2 dashboard ---' && pm2 describe modbot-dashboard 2>&1 | grep -E 'status|script path|uptime' || echo NO_dash")

ssh.close()
print("\nDone.", flush=True)
