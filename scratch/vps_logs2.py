"""Second pass: dashboard PM2 logs + modbot restart history."""
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


# Dashboard error log (PM2 owns it, id 4)
run("pm2 logs modbot-dashboard --err --nostream --lines 60 2>/dev/null || echo NO_PM2_LOGS")
# When did it last restart, and why (out log tail)
run("pm2 logs modbot-dashboard --out --nostream --lines 25 2>/dev/null || echo NO_OUT")
# modbot restart count / current run
run("systemctl show modbot -p NRestarts -p ActiveEnterTimestamp -p ExecMainStartTimestamp 2>&1 || true")
# Current git commit on the box
run("cd /opt/modbot && git rev-parse --short HEAD && git log -1 --format='%ci %s'")

ssh.close()
print("\nDone.", flush=True)
