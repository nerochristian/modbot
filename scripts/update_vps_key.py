"""Push a rotated API key to the VPS .env and restart the bot.

Every credential is read from the environment. They used to be literals in
this file -- the deploy host, the root password, and a live API key -- which
meant rotating a key required editing a tracked file, and anyone with repo
access had the production root password.

Usage::

    VPS_HOST=example.com VPS_USER=root VPS_PASSWORD=... \\
    LEGION_API_KEY=lek_live_... python scripts/update_vps_key.py

Prefer key-based auth: set ``VPS_SSH_KEY`` to a private key path and leave
``VPS_PASSWORD`` unset.
"""
from __future__ import annotations

import os
import sys
import time

import paramiko

#: The .env variable to rewrite. Defaults to the current provider's key.
ENV_VAR = os.getenv("VPS_ENV_VAR", "LEGION_API_KEY").strip()
REMOTE_ENV = os.getenv("VPS_ENV_PATH", "/opt/modbot/.env")
SERVICE = os.getenv("VPS_SERVICE", "modbot")


def _require(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        sys.exit(f"{name} is not set. See the module docstring for usage.")
    return value


def main() -> int:
    host = _require("VPS_HOST")
    user = os.getenv("VPS_USER", "root").strip()
    key_path = (os.getenv("VPS_SSH_KEY") or "").strip()
    password = (os.getenv("VPS_PASSWORD") or "").strip()
    if not key_path and not password:
        sys.exit("Set VPS_SSH_KEY (preferred) or VPS_PASSWORD.")
    new_api_key = _require(ENV_VAR)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"Connecting to {user}@{host}...")
        if key_path:
            ssh.connect(host, username=user, key_filename=key_path, timeout=10)
        else:
            ssh.connect(host, username=user, password=password, timeout=10)

        print(f"Reading {REMOTE_ENV}")
        _, stdout, _ = ssh.exec_command(f"cat {REMOTE_ENV}")
        env_content = stdout.read().decode("utf-8")
        if not env_content.strip():
            sys.exit(f"Failed to read {REMOTE_ENV}, or it is empty.")

        prefix = f"{ENV_VAR}="
        lines = env_content.splitlines()
        new_lines = [prefix + new_api_key if l.startswith(prefix) else l for l in lines]
        if not any(l.startswith(prefix) for l in lines):
            new_lines.append(prefix + new_api_key)

        print(f"Writing {REMOTE_ENV}")
        sftp = ssh.open_sftp()
        try:
            with sftp.file(REMOTE_ENV, "w") as handle:
                handle.write("\n".join(new_lines) + "\n")
        finally:
            sftp.close()

        print(f"Restarting {SERVICE}...")
        ssh.exec_command(f"systemctl restart {SERVICE}")
        time.sleep(3)
        _, stdout, _ = ssh.exec_command(f"systemctl is-active {SERVICE}")
        status = stdout.read().decode("utf-8").strip()
        print(f"Bot status: {status}")
        return 0 if status == "active" else 1
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
