"""Pull recent modbot + dashboard logs from the VPS and surface errors."""
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


run("systemctl is-active modbot modbot-dashboard 2>&1 || true")
run("command -v pm2 >/dev/null 2>&1 && pm2 list 2>/dev/null || echo NO_PM2")

run("journalctl -u modbot --since '2 days ago' --no-pager 2>/dev/null "
    "| grep -iE 'error|exception|traceback|critical|failed|warning' | tail -80 || echo NO_MODBOT_JOURNAL")

run("journalctl -u modbot-dashboard --since '2 days ago' --no-pager 2>/dev/null "
    "| grep -iE 'error|exception|traceback|critical|failed' | tail -60 || echo NO_DASH_JOURNAL")

ssh.close()
print("\nDone.", flush=True)
