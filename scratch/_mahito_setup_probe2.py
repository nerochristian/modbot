"""Check guild repo tracked files + push credentials. Read-only scratch."""
from __future__ import annotations

import os
import paramiko

HOST = "docketbot.xyz"
USER = "root"
PASSWORD = os.environ["MODBOT_VPS_PASS"]

CMD = (
    "echo === guild-tracked-files-top ===; "
    "cd /opt/soul/guild && git ls-tree --name-only HEAD | head -80; "
    "echo; echo === guild-tracked-count ===; "
    "cd /opt/soul/guild && git ls-files | wc -l; "
    "echo; echo === guild-tracked-asset-samples ===; "
    "cd /opt/soul/guild && git ls-files 'assets/*' | head -20; "
    "echo; echo === guild-tracks-python-embed? ===; "
    "cd /opt/soul/guild && git ls-files | grep -iE 'python-embed|image.png|welcome_bg|LifeSimBot' | head; "
    "echo; echo === root-modbot-gitignore-content ===; "
    "cat /root/modbot/.gitignore 2>/dev/null; "
    "echo; echo === root-modbot-dot-github ===; "
    "ls -la /root/modbot/.github/workflows 2>/dev/null; "
    "echo; echo === gh-creds? ===; "
    "ls -la /root/.ssh/ 2>/dev/null | head; "
    "echo === gh-token-env? ===; "
    "env | grep -iE 'GH_TOKEN|GITHUB_TOKEN' | sed 's/=.*/=<set>/' 2>/dev/null || echo none; "
    "echo; echo === git-credential-helper ===; "
    "git config --global --list 2>/dev/null | grep -iE 'credential|user' ; "
    "echo; echo === soul-guild-push-test-dry ===; "
    "cd /opt/soul/guild && git ls-remote origin guild 2>&1 | head -3; "
    "echo; echo === root-modbot-pm2-start-time ===; "
    "pm2 describe modbot 2>/dev/null | grep -E 'uptime|created|status|restarts'; "
    "echo; echo === git-available ===; "
    "which git; git --version"
)

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect(HOST, username=USER, password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)
_, o, e = s.exec_command(CMD, timeout=60)
out = o.read().decode("utf-8", "replace")
err = e.read().decode("utf-8", "replace")
s.close()
open("scratch/_mahito_setup_probe2_out.txt", "w", encoding="utf-8").write(out + ("\nSTDERR:" + err if err else ""))
print("done")
