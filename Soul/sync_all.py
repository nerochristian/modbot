import paramiko
import os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print("Connecting...")
    client.connect('162.243.9.88', username='root', password='Pokem0n2020nero', timeout=10)
    sftp = client.open_sftp()
    
    local_dir = 'c:\\Users\\Dell\\Soul\\guild'
    remote_dir = '/root/modbot'
    
    def upload_dir(local_path, remote_path):
        try:
            sftp.stat(remote_path)
        except IOError:
            sftp.mkdir(remote_path)
            
        for item in os.listdir(local_path):
            if item in ['.git', '__pycache__', '.ruff_cache', 'venv', 'tests']:
                continue
            l_path = os.path.join(local_path, item)
            r_path = f"{remote_path}/{item}"
            if os.path.isdir(l_path):
                upload_dir(l_path, r_path)
            else:
                print(f"Uploading {l_path} to {r_path}")
                sftp.put(l_path, r_path)

    print("Uploading files...")
    upload_dir(local_dir, remote_dir)
    sftp.close()
    
    print("Restarting modbot...")
    stdin, stdout, stderr = client.exec_command('pm2 restart modbot')
    print("STDOUT:", stdout.read().decode('utf-8'))
    print("STDERR:", stderr.read().decode('utf-8'))
    print("Done!")
except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
