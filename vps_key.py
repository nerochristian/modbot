import paramiko
import os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('162.243.9.88', username='root', password='Pokem0n2020nero', timeout=10)

key_path = os.path.expanduser('~/.ssh/id_rsa.pub')
with open(key_path, 'r') as f:
    key = f.read().strip()

command = f'mkdir -p ~/.ssh && echo "{key}" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
stdin, stdout, stderr = client.exec_command(command)
print("OUT:", stdout.read().decode())
print("ERR:", stderr.read().decode())

# Check running apps
stdin, stdout, stderr = client.exec_command('ls -la /root')
print(stdout.read().decode())

client.close()
