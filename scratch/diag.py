"""Read-only diagnostic: is the drift CRLF-only or real content? Deleted after use. UTF-8 safe."""
from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import paramiko

HOST = "docketbot.xyz"
USER = "root"
PASSWORD = os.environ["MODBOT_VPS_PASS"]


def run(cmd: str, *, timeout: int = 90) -> None:
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

run("cd /root/modbot && echo '--- autocrlf/eol on VPS ---' && git config --get core.autocrlf; git config --get core.eol; echo '(end)'")
run("cd /root/modbot && echo '=== diff --stat IGNORING CR-at-EOL (if empty => pure CRLF) ===' && git diff --ignore-cr-at-eol --stat | tail -15; echo '=== end ==='")
run("cd /root/modbot && echo '=== raw diff of bot.py (first 15 lines; look for ^M) ===' && git diff bot.py | head -15; echo '=== end ==='")
run("cd /root/modbot && echo '=== CR count: index blob vs disk (bot.py) ===' && printf 'index CRs: '; git show origin/guild:bot.py | tr -cd '\\r' | wc -c; printf 'disk  CRs: '; tr -cd '\\r' < bot.py | wc -c")

ssh.close()
print("\nDiagnostic complete.", flush=True)
