"""One-shot: tar live Mahito code (no secrets/runtime) on VPS and download it. Deleted after use. UTF-8 safe."""
from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import paramiko

HOST = "docketbot.xyz"
USER = "root"
PASSWORD = os.environ["MODBOT_VPS_PASS"]
REMOTE_TGZ = "/root/mahito-live-code.tgz"
LOCAL_TGZ = r"C:\Users\Smart Room 1\Downloads\mahito-compare\live.tgz"

# Secrets excluded by BASENAME at any depth (.env, credentials.json, *.db...).
# Big/regenerable/runtime dirs excluded by anchored path.
EXCLUDES = " ".join([
    "--exclude=.env", "--exclude=.env.*", "--exclude=credentials.json",
    "--exclude=*.db", "--exclude=*.db-shm", "--exclude=*.db-wal",
    "--exclude=__pycache__", "--exclude=*.pyc",
    "--exclude=modbot/data", "--exclude=modbot/db", "--exclude=modbot/backups",
    "--exclude=modbot/gc/data",
    "--exclude=modbot/python-embed", "--exclude=modbot/python-embed.zip",
    "--exclude=modbot/node_modules", "--exclude=modbot/.modbot.lock",
    "--exclude=modbot/LifeSimBot", "--exclude=modbot/scratch",
])

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"Connecting to {USER}@{HOST} ...", flush=True)
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)
print("Connected.", flush=True)

cmd = f"rm -f {REMOTE_TGZ} && tar czf {REMOTE_TGZ} {EXCLUDES} -C /root modbot && ls -lh {REMOTE_TGZ}"
print(f"\n===== $ {cmd}", flush=True)
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=180, get_pty=False)
print(stdout.read().decode("utf-8", "replace"), end="", flush=True)
err = stderr.read().decode("utf-8", "replace")
if err:
    print(f"(stderr) {err}", end="", file=sys.stderr, flush=True)

# Safety: confirm no .env / credentials / .db made it into the archive.
print("\n===== verify archive has no secrets/db =====", flush=True)
chk = f"tar tzf {REMOTE_TGZ} | grep -iE '(^|/)\\.env|credentials\\.json|\\.db($|-shm|-wal)|modbot\\.db' || echo CLEAN_no_secrets_or_db"
stdin, stdout, stderr = ssh.exec_command(chk, timeout=120, get_pty=False)
print(stdout.read().decode("utf-8", "replace"), end="", flush=True)

os.makedirs(os.path.dirname(LOCAL_TGZ), exist_ok=True)
print(f"\n===== SFTP download {REMOTE_TGZ} -> {LOCAL_TGZ} =====", flush=True)
sftp = ssh.open_sftp()
sftp.get(REMOTE_TGZ, LOCAL_TGZ)
size = os.path.getsize(LOCAL_TGZ)
print(f"downloaded {size} bytes.", flush=True)

sftp.close()
ssh.close()
print("\nFetch complete.", flush=True)
