"""Check push capability + LifeSimBot tracking + .gitignore needs. Read-only scratch."""
from __future__ import annotations

import os
import paramiko

HOST = "docketbot.xyz"
USER = "root"
PASSWORD = os.environ["MODBOT_VPS_PASS"]

CMD = (
    "echo === soul-guild-remote-url-detail ===; "
    "cd /opt/soul/guild && git remote -v; "
    "echo; echo === soul-guild-can-push? dry-run ===; "
    "cd /opt/soul/guild && git push --dry-run origin guild 2>&1 | head -10; "
    "echo; echo === git-credential-store-file ===; "
    "ls -la /root/.git-credentials /root/.gitconfig 2>/dev/null; cat /root/.gitconfig 2>/dev/null; "
    "echo; echo === LifeSimBot-tracked-on-guild? ===; "
    "cd /opt/soul/guild && git ls-files 'LifeSimBot/*' | head; echo '--- root-modbot LifeSimBot:'; ls /root/modbot/LifeSimBot 2>/dev/null; "
    "echo; echo === backups-tracked? ===; "
    "cd /opt/soul/guild && git ls-files 'backups/*' | head; "
    "echo; echo === modbot-lock-tracked? ===; "
    "cd /opt/soul/guild && git ls-files | grep -iE 'modbot.lock|^.now$' ; "
    "echo; echo === now-file ===; "
    "cat /opt/soul/guild/now 2>/dev/null | head; echo '--- root:'; cat /root/modbot/now 2>/dev/null | head; "
    "echo; echo === root-modbot-gitignore-vs-guild ===; "
    "diff /root/modbot/.gitignore /opt/soul/guild/.gitignore 2>/dev/null && echo 'IDENTICAL' || echo 'DIFFER'; "
    "echo; echo === ssh-key-scan-gh ===; "
    "ssh-keygen -F github.com 2>/dev/null | head -3 || echo 'no known_hosts entry for github'; "
    "echo; echo === root-ssh-knownhosts ===; "
    "ls -la /root/.ssh/known_hosts 2>/dev/null; "
    "echo; echo === pm2-modbot-env-gh ===; "
    "pm2 env 6 2>/dev/null | grep -iE 'GH_|GITHUB|TOKEN' | sed 's/=.*/=<set>/' || echo 'no gh env in pm2'"
)

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect(HOST, username=USER, password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)
_, o, e = s.exec_command(CMD, timeout=60)
out = o.read().decode("utf-8", "replace")
err = e.read().decode("utf-8", "replace")
s.close()
open("scratch/_pushcred_probe_out.txt", "w", encoding="utf-8").write(out + ("\nSTDERR:" + err if err else ""))
print("done")
