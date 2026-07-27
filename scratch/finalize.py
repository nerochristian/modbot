"""One-shot: finalize link (reset --hard to LF), verify clean + deploy no-op + pm2 online. Deleted after use. UTF-8 safe."""
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

run("cd /root/modbot && git reset --hard origin/guild 2>&1 | tail -3 && echo '--- HEAD ---' && git rev-parse --short HEAD && echo '--- upstream ---' && git rev-parse --abbrev-ref --symbolic-full-name @{u}")
run("cd /root/modbot && echo '=== git status --porcelain (should be clean / only ignored) ===' && git status --porcelain | head -30; echo '=== end status ==='")
run("cd /root/modbot && echo '=== tracked-drift recheck ignoring CR (should be only .gitignore or empty) ===' && git diff --ignore-cr-at-eol --stat | tail -5; echo '=== end ==='")
run("echo '=== deploy script dry run (should say Already up to date, NO restart) ===' && bash /usr/local/sbin/mahito-autodeploy.sh 2>&1")
run("echo '=== pm2 mahito still online (untouched) ===' && pm2 describe modbot 2>&1 | grep -E 'status|uptime' || echo NO_pm2")
run("rm -f /root/mahito-live-code.tgz && echo 'cleaned temp tgz'")

ssh.close()
print("\nFinalize complete.", flush=True)
