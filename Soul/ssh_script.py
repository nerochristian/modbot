import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('162.243.9.88', username='root', password='Pokem0n2020nero', timeout=10)
stdin, stdout, stderr = client.exec_command('systemctl list-units | grep -i bot')
with open('output.txt', 'w', encoding='utf-8') as f:
    f.write(stdout.read().decode('utf-8', errors='ignore'))
client.close()
