"""Investigate dashboard restart churn: deploy cadence + what commits change."""
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "docketbot.xyz"
USER = "root"
PASSWORD = "Pokem0n2020nero"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30,
            allow_agent=False, look_for_keys=False)


def run(cmd, timeout=120):
    print(f"\n===== $ {cmd}", flush=True)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out, end="", flush=True)
    if err:
        print("[stderr]\n" + err, end="", flush=True)
    print(f"\n----- [exit {rc}]", flush=True)
    return rc, out, err


# How often does the deploy timer actually DEPLOY (vs "Already up to date")?
run("journalctl -u modbot-autoupdate.service --since '3 hours ago' --no-pager 2>/dev/null "
    "| grep -E 'Deploying|Deploy complete|Already up to date|Refusing|failed' | tail -40 || echo NONE")

# Count deploys vs up-to-date in last 6h
run("journalctl -u modbot-autoupdate.service --since '6 hours ago' --no-pager 2>/dev/null "
    "| grep -cE 'Deploying [0-9a-f]+ ->' ; echo '^ deploys(6h)' ; "
    "journalctl -u modbot-autoupdate.service --since '6 hours ago' --no-pager 2>/dev/null "
    "| grep -cE 'Already up to date' ; echo '^ up-to-date(6h)'")

# What do the recent commits change? Are dashboard/ files touched each time?
run("cd /opt/modbot && git log -12 --format='%h %ci %s' --stat -- . | head -120")

# Just the file paths changed in the last 8 commits (to see if dashboard/ is always in them)
run("cd /opt/modbot && for c in $(git log -8 --format=%h); do "
    "echo \"--- $c $(git log -1 --format=%s $c)\"; "
    "git show --stat --format= $c | grep -E '\\|' | awk '{print $1}' | sed 's#/[^/]*$##' | sort -u | head; done")

ssh.close()
print("\nDone.", flush=True)
