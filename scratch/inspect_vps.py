"""Read-only VPS inspection probe #2 (deleted after use). UTF-8 safe."""
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

print("########## guild repo remote HEAD (from GitHub) ##########")
run("git ls-remote https://github.com/nerochristian/guild 2>&1 | head -20")

print("\n########## /opt/soul/guild (dead clone, git state) ##########")
run("cd /opt/soul/guild && git remote -v 2>&1 && echo '--- branch/head ---' && git rev-parse --abbrev-ref HEAD 2>&1 && git rev-parse --short HEAD 2>&1 && echo '--- dirty ---' && git status --porcelain --untracked-files=no 2>&1 && echo '(end dirty)'")
run("ls -la /opt/soul/guild/ 2>&1 | head -30")
run("echo '--- deploy.sh ---' && cat /opt/soul/guild/scripts/deploy.sh 2>&1 || echo NO_deploy_sh")
run("systemctl is-active soul-bot.service 2>&1; systemctl is-enabled soul-update.timer 2>&1; systemctl is-active soul-update.timer 2>&1")
run("id soul 2>&1 || echo NO_soul_user")

print("\n########## Compare /opt/soul/guild vs /root/modbot (code identity) ##########")
run("sha256sum /opt/soul/guild/bot.py /root/modbot/bot.py 2>&1")
run("echo '--- diff -rq (py only, excl runtime) ---' && diff -rq --exclude=.git --exclude=.env --exclude=data --exclude=db --exclude=__pycache__ --exclude=modbot.db --exclude=backups --exclude=node_modules --exclude='*.pyc' /opt/soul/guild /root/modbot 2>&1 | head -40 && echo '(end diff)'")

print("\n########## /root/modbot: is any file tracked in guild repo? full listing ##########")
run("ls -la /root/modbot/cogs 2>&1 | head -40")
run("cat /root/modbot/deploy.py 2>&1 | head -60 || echo NO_deploy_py")
run("cat /root/modbot/Procfile 2>&1 || echo NO_procfile")

print("\n########## PM2 ecosystem / startup ##########")
run("cat /root/.pm2/dump.pm2 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); [print(p.get('name'), p.get('pm_cwd'), p.get('pm_exec_path')) for p in d]\" 2>&1 || echo NO_dump")
run("systemctl cat pm2-root.service 2>&1 | head -20 || echo NO_pm2-root.service")

ssh.close()
print("\nInspection #2 complete.", flush=True)
