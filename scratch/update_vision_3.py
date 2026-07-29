import paramiko
import time
import os

host = "docketbot.xyz"
user = "root"
password = "Pokem0n2020nero"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print("Connecting to VPS...")
    ssh.connect(host, username=user, password=password, timeout=10)
    
    print("Reading /opt/modbot/.env")
    stdin, stdout, stderr = ssh.exec_command("cat /opt/modbot/.env")
    env_content = stdout.read().decode('utf-8')
    
    if not env_content.strip():
        print("Failed to read .env or it is empty!")
        exit(1)
        
    new_lines = []
    found = False
    for line in env_content.splitlines():
        if line.startswith("RELAYROUTER_VISION_MODEL="):
            new_lines.append("RELAYROUTER_VISION_MODEL=google/gemini-3.5-flash")
            found = True
        else:
            new_lines.append(line)
            
    if not found:
        new_lines.append("RELAYROUTER_VISION_MODEL=google/gemini-3.5-flash")
        
    new_env = "\n".join(new_lines) + "\n"
    
    print("Writing new .env to /opt/modbot/.env")
    sftp = ssh.open_sftp()
    with sftp.file('/opt/modbot/.env', 'w') as f:
        f.write(new_env)
    sftp.close()
    
    print("Restarting modbot service...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart modbot")
    time.sleep(3)
    
    stdin, stdout, stderr = ssh.exec_command("systemctl is-active modbot")
    status = stdout.read().decode('utf-8').strip()
    print(f"Bot status: {status}")

finally:
    ssh.close()
