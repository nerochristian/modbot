import paramiko
import os

host = "docketbot.xyz"
user = "root"
password = "Pokem0n2020nero"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect(host, username=user, password=password, timeout=10)
    stdin, stdout, stderr = ssh.exec_command("cat /opt/modbot/.env")
    env_content = stdout.read().decode('utf-8')
    for line in env_content.splitlines():
        if "AIMODEL" in line or "RELAY" in line:
            print(line)
finally:
    ssh.close()
