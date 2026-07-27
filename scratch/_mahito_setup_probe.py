"""Gather what's needed to init /root/modbot as a git repo + write gitignore/deploy.
Read-only scratch — deleted after use."""
from __future__ import annotations

import os
import paramiko

HOST = "docketbot.xyz"
USER = "root"
PASSWORD = os.environ["MODBOT_VPS_PASS"]

CMD = (
    "echo === root-modbot-full-tree ===; "
    "cd /root/modbot && ls -la; "
    "echo; echo === root-modbot-tree-depth2 ===; "
    "cd /root/modbot && find . -maxdepth 2 -not -path '*/.git/*' | sort | head -120; "
    "echo; echo === guild-gitignore ===; "
    "cat /opt/soul/guild/.gitignore 2>/dev/null; "
    "echo; echo === guild-deploy-sh ===; "
    "cat /opt/soul/guild/scripts/deploy.sh 2>/dev/null; "
    "echo; echo === guild-requirements ===; "
    "cat /opt/soul/guild/requirements.txt 2>/dev/null; "
    "echo; echo === root-modbot-requirements ===; "
    "cat /root/modbot/requirements.txt 2>/dev/null; "
    "echo; echo === root-modbot-has-modbot-lock ===; "
    "cat /root/modbot/.modbot.lock 2>/dev/null; "
    "echo; echo === guild-git-branch ===; "
    "cd /opt/soul/guild && git branch -a 2>/dev/null; "
    "echo; echo === guild-git-log-full ===; "
    "cd /opt/soul/guild && git log --oneline -8 2>/dev/null; "
    "echo; echo === root-modbot-db-files ===; "
    "cd /root/modbot && ls -la modbot.db data db 2>/dev/null; "
    "echo; echo === root-modbot-lfs-check ===; "
    "cd /root/modbot && du -sh assets image.png 2>/dev/null; "
    "echo; echo === git-config-user ===; "
    "git config --global user.name; git config --global user.email; "
    "echo; echo === guild-gh-push-access ===; "
    "cd /opt/soul/guild && git remote get-url origin"
)

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect(HOST, username=USER, password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)
_, o, e = s.exec_command(CMD, timeout=60)
out = o.read().decode("utf-8", "replace")
err = e.read().decode("utf-8", "replace")
s.close()
open("scratch/_mahito_setup_probe_out.txt", "w", encoding="utf-8").write(out + ("\nSTDERR:" + err if err else ""))
print("done")
