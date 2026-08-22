"""Print the VPS .env with secret values masked.

Credentials come from the environment. They used to be literals here -- the
deploy host and the production root password -- which put the root password in
every clone of this repo.

Usage::

    VPS_HOST=example.com VPS_SSH_KEY=~/.ssh/id_ed25519 \
    python scripts/read_vps_env.py

Values are masked by default so the output is safe to paste. Pass --reveal
when you genuinely need a value.
"""
from __future__ import annotations

import os
import sys

import paramiko

REMOTE_ENV = os.getenv("VPS_ENV_PATH", "/opt/modbot/.env")
# Substring match, so LEGION_API_KEY, APIFY_TOKEN, VPS_PASSWORD all mask.
_SECRET_HINTS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "DSN", "URL")


def _mask(value: str) -> str:
    value = value.strip()
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]} ({len(value)} chars)"


def main() -> int:
    reveal = "--reveal" in sys.argv
    host = (os.getenv("VPS_HOST") or "").strip()
    if not host:
        sys.exit("VPS_HOST is not set. See the module docstring for usage.")
    user = os.getenv("VPS_USER", "root").strip()
    key_path = (os.getenv("VPS_SSH_KEY") or "").strip()
    password = (os.getenv("VPS_PASSWORD") or "").strip()
    if not key_path and not password:
        sys.exit("Set VPS_SSH_KEY (preferred) or VPS_PASSWORD.")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if key_path:
            ssh.connect(host, username=user, key_filename=key_path, timeout=10)
        else:
            ssh.connect(host, username=user, password=password, timeout=10)
        _, stdout, _ = ssh.exec_command(f"cat {REMOTE_ENV}")
        for line in stdout.read().decode("utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                print(line)
                continue
            name, _, value = line.partition("=")
            secret = any(hint in name.upper() for hint in _SECRET_HINTS)
            print(f"{name}={value if reveal or not secret else _mask(value)}")
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
