import paramiko
import sys
import os

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('162.243.9.88', username='root', password='Pokem0n2020nero', timeout=10)
    
    # SFTP
    sftp = client.open_sftp()
    local_path = r"c:\Users\Dell\Soul\guild\economy\crime.py"
    remote_path = "/root/modbot/guild/economy/crime.py"
    
    print(f"Uploading {local_path} to {remote_path}...")
    sftp.put(local_path, remote_path)
    sftp.close()
    
    # Restart
    print("Restarting modbot...")
    stdin, stdout, stderr = client.exec_command('pm2 restart modbot')
    print(stdout.read().decode('utf-8'))
    
    err = stderr.read().decode('utf-8')
    if err:
        print("STDERR:", err)
except Exception as e:
    print(f"Connection failed: {e}")
finally:
    client.close()
