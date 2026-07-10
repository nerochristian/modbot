import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('162.243.9.88', username='root', password='Pokem0n2020nero')
stdin, stdout, stderr = client.exec_command('ls -la /root/modbot/cogs/')
print(stdout.read().decode('utf-8'))
client.close()
