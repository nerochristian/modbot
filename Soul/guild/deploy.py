import paramiko
import sys

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print("Connecting...")
    client.connect('162.243.9.88', username='root', password='Pokem0n2020nero', timeout=10)
    
    print("Uploading bot.py...")
    sftp = client.open_sftp()
    sftp.put('c:\\Users\\Dell\\Soul\\guild\\bot.py', '/root/modbot/bot.py')
    sftp.close()
    
    print("Restarting modbot...")
    stdin, stdout, stderr = client.exec_command('pm2 restart modbot')
    print("STDOUT:", stdout.read().decode('utf-8'))
    
    err = stderr.read().decode('utf-8')
    if err:
        print("STDERR:", err)
    print("Done!")
except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
