"""Read-only: find GitHub push credentials on the VPS. Secrets masked. UTF-8 safe."""
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

# Existence checks only (no secret values printed).
run("command -v gh && gh --version 2>&1 | head -1 || echo NO_gh")
run("gh auth status 2>&1 | sed -E 's/(oauth_token:|token:).*/\\1 <redacted>/I' || echo NO_gh_auth")
run("test -s /root/.git-credentials && echo HAS_git-credentials || echo NO_git-credentials")
run("git config --global --get credential.helper || echo NO_cred_helper")
run("git config --global user.name; git config --global user.email; echo '(git identity above)'")
run("ls -la /root/.ssh/ 2>/dev/null || echo NO_ssh_dir")
run("ssh -T git@github.com -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 2>&1 | head -3 || echo SSH_test_done")
run("env | grep -iE 'github|gh_token|git_token' | sed -E 's/=.*/=<redacted>/' || echo NO_github_env")

ssh.close()
print("\nCredential scan complete.", flush=True)
