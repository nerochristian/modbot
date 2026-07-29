import paramiko
import sys
import os

host = '162.243.9.88' # IP for docketbot.xyz
password = 'Pokem0n2020nero'

files_to_upload = [
    (r"c:\Users\Smart Room 1\Downloads\modbot\cogs\aimoderation\ai_client.py", "/opt/modbot/cogs/aimoderation/ai_client.py"),
    (r"c:\Users\Smart Room 1\Downloads\modbot\cogs\aimoderation\aimoderation.py", "/opt/modbot/cogs/aimoderation/aimoderation.py")
]

try:
    print("Connecting to VPS...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username='root', password=password, timeout=10)
    
    sftp = ssh.open_sftp()
    
    for local_path, remote_path in files_to_upload:
        print(f"Uploading {local_path} to {remote_path}...")
        sftp.put(local_path, remote_path)
        
    sftp.close()
    
    print("Restarting modbot service...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart modbot && sleep 2 && systemctl is-active modbot")
    print("Status:", stdout.read().decode().strip())
    
    ssh.close()
    print("Done!")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
