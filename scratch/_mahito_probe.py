"""Investigate Mahito repo state + PM2 env + guild repo deploy scripts.
Read-only scratch — deleted after use."""
from __future__ import annotations

import os
import paramiko

HOST = "docketbot.xyz"
USER = "root"
PASSWORD = os.environ["MODBOT_VPS_PASS"]

CMD = (
    "echo === root-modbot-git? ===; "
    "ls -la /root/modbot/.git 2>/dev/null && echo HAS_GIT || echo NO_GIT; "
    "echo; echo === root-modbot-revparse ===; "
    "cd /root/modbot 2>/dev/null && git rev-parse --short HEAD 2>/dev/null && git remote -v 2>/dev/null || echo 'not a git repo'; "
    "echo; echo === root-modbot-git-status ===; "
    "cd /root/modbot 2>/dev/null && git status --porcelain --untracked-files=no 2>/dev/null | head -20 || echo 'no git'; "
    "echo; echo === soul-guild-git ===; "
    "cd /opt/soul/guild && git rev-parse --short HEAD && git remote -v && git status --porcelain --untracked-files=no | head; "
    "echo; echo === guild-deploy-scripts? ===; "
    "ls -la /opt/soul/guild/deploy 2>/dev/null; ls /opt/soul/guild/scripts 2>/dev/null; "
    "find /opt/soul/guild -maxdepth 2 -iname 'vps_deploy*' -o -iname '*deploy*.sh' 2>/dev/null | head; "
    "echo; echo === guild-agent.md ===; "
    "head -60 /opt/soul/guild/agent.md 2>/dev/null; "
    "echo; echo === pm2-modbot-full-desc ===; "
    "pm2 describe modbot 2>/dev/null | head -40; "
    "echo; echo === guild-requirements ===; "
    "ls /opt/soul/guild/requirements.txt /root/modbot/requirements.txt 2>/dev/null; "
    "echo; echo === guild-venv ===; "
    "ls -d /opt/soul/guild/.venv /root/modbot/.venv 2>/dev/null; "
    "echo; echo === root-modbot-procfile ===; "
    "cat /root/modbot/Procfile 2>/dev/null; "
    "echo; echo === guild-local-files-diff-vs-root-modbot ===; "
    "diff -rq /opt/soul/guild /root/modbot 2>/dev/null | grep -vE '\\.git|__pycache__|\\.venv|\\.env|image\\.png|bot\\.log|modbot\\.db|/data/|/backups/|/db/' | head -30; "
    "echo; echo === systemd-docket-autoupdate-timer ===; "
    "systemctl is-active modbot-autoupdate.timer 2>/dev/null; systemctl list-timers modbot-autoupdate.timer --no-pager 2>/dev/null | head; "
    "echo; echo === etc-autoupdate-env ===; "
    "cat /etc/modbot-autoupdate.env 2>/dev/null; "
    "echo; echo === pm2-dump-exists ===; "
    "ls -la /root/.pm2/dump.pm2 2>/dev/null"
)

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect(HOST, username=USER, password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)
_, o, e = s.exec_command(CMD, timeout=60)
out = o.read().decode("utf-8", "replace")
err = e.read().decode("utf-8", "replace")
s.close()
open("scratch/_mahito_probe_out.txt", "w", encoding="utf-8").write(out + ("\nSTDERR:" + err if err else ""))
print("done")
