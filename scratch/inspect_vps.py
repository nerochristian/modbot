"""Read-only divergence check: clone origin/guild, diff vs /root/modbot. UTF-8 safe."""
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

run("rm -rf /tmp/guild-ref && git clone --depth 1 --branch guild https://github.com/nerochristian/guild.git /tmp/guild-ref 2>&1 | tail -5 && cd /tmp/guild-ref && git rev-parse --short HEAD")
run("echo '--- guild repo top-level ---' && ls -la /tmp/guild-ref 2>&1 | head -40")
run("echo '--- guild repo .gitignore ---' && cat /tmp/guild-ref/.gitignore 2>&1")
run("echo '=== DIFF origin/guild (ref) vs /root/modbot (live), excluding runtime ==='")
run(
    "diff -rq "
    "--exclude=.git --exclude=.env --exclude=.venv --exclude=data --exclude=db "
    "--exclude=modbot.db --exclude=backups --exclude=__pycache__ --exclude=node_modules "
    "--exclude=python-embed --exclude=LifeSimBot --exclude=.modbot.lock --exclude=scratch "
    "--exclude=assets --exclude=image.png --exclude='*.pyc' "
    "/tmp/guild-ref /root/modbot 2>&1 | head -60; echo '(end diff)'"
)
run("echo '--- cleanup ref ---' && rm -rf /tmp/guild-ref && echo removed")

ssh.close()
print("\nDivergence check complete.", flush=True)
