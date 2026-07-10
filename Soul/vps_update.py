import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect('162.243.9.88', username='root', password='Pokem0n2020nero', timeout=10)
    
    # 1. Update the token in .env
    update_cmd = "sed -i 's/DISCORD_BOT_TOKEN=.*/DISCORD_BOT_TOKEN=MTUxMjkxNzk0MjM5NDk0OTc2Mg.G_x3cd.BVyO31BfZ2q3h5_hYA0PZrvd5t3FadQA87jHI8/' /root/modbot/.env"
    client.exec_command(update_cmd)
    
    # 2. Restart modbot
    client.exec_command("pm2 restart modbot")
    
    import time
    time.sleep(2) # Wait for it to restart and log something
    
    # 3. Fetch logs
    stdin, stdout, stderr = client.exec_command("pm2 logs modbot --lines 50 --nostream")
    print(stdout.read().decode('utf-8', errors='ignore'))
    print(stderr.read().decode('utf-8', errors='ignore'))
    
except Exception as e:
    print(f"Connection failed: {e}")
finally:
    client.close()
