import paramiko
import sys

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect('162.243.9.88', username='root', password='Pokem0n2020nero', timeout=10)
    stdin, stdout, stderr = client.exec_command('tail -n 200 /root/.pm2/logs/modbot-error.log')
    print(stdout.read().decode('utf-8'))
    
    err = stderr.read().decode('utf-8')
    if err:
        print("STDERR:", err)
except Exception as e:
    print(f"Connection failed: {e}")
finally:
    client.close()
