import paramiko
import os
import subprocess

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("docketbot.xyz", username="root", password="Pokem0n2020nero")

stdin, stdout, stderr = client.exec_command("sed -i 's/claude-opus-4.8/claude-fable-5/g' /opt/modbot/.env")
exit_status = stdout.channel.recv_exit_status()
print(f"Sed command exit status: {exit_status}")

client.close()
