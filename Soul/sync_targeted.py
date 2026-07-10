import paramiko
import os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print("Connecting...")
    client.connect('162.243.9.88', username='root', password='Pokem0n2020nero', timeout=10)
    sftp = client.open_sftp()
    
    import os
    
    files_to_sync = ['economy/shop.py']
    
    base_local = 'c:\\Users\\Dell\\Soul\\guild'
    base_remote = '/opt/soul/guild'
    
    for f in files_to_sync:
        l_path = os.path.join(base_local, f.replace('/', '\\'))
        r_path = f"{base_remote}/{f}"
        print(f"Uploading {l_path} to {r_path}")
        sftp.put(l_path, r_path)

    sftp.close()
    
    print("Restarting soul bot...")
    stdin, stdout, stderr = client.exec_command('systemctl restart soul-bot.service')
    print("STDOUT:", stdout.read().decode('utf-8'))
    print("STDERR:", stderr.read().decode('utf-8'))
    print("Done!")
except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
