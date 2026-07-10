import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect('162.243.9.88', username='root', password='Pokem0n2020nero', timeout=10)
    stdin, stdout, stderr = client.exec_command('ps aux | grep bot.py')
    print('STDOUT:', stdout.read().decode('utf-8'))
except Exception as e:
    print(f'Error: {e}')
finally:
    client.close()
