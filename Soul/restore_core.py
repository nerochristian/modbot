import paramiko
import sys

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect('162.243.9.88', username='root', password='Pokem0n2020nero', timeout=10)
    sftp = client.open_sftp()
    
    # 1. Download original core.py to overwrite our broken local copy
    sftp.get('/root/modbot/economy/core.py', 'c:\\Users\\Dell\\Soul\\guild\\economy\\core.py')
    
    sftp.close()
    print("Successfully downloaded core.py")
except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
