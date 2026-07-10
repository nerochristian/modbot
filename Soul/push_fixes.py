import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print("Connecting...")
    client.connect('162.243.9.88', username='root', password='Pokem0n2020nero', timeout=10)
    sftp = client.open_sftp()
    
    print("Uploading .env...")
    sftp.put('c:\\Users\\Dell\\Soul\\guild\\.env', '/root/modbot/.env')
    
    print("Uploading core.py...")
    sftp.put('c:\\Users\\Dell\\Soul\\guild\\economy\\core.py', '/root/modbot/economy/core.py')
    
    sftp.close()
    
    print("Restarting modbot...")
    stdin, stdout, stderr = client.exec_command('pm2 restart modbot')
    
    import time
    time.sleep(3)
    
    stdin, stdout, stderr = client.exec_command('pm2 logs modbot --lines 30 --nostream')
    print("STDOUT:", stdout.read().decode('utf-8', errors='ignore'))
    print("STDERR:", stderr.read().decode('utf-8', errors='ignore'))
    
except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
