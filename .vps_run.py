import os, sys, paramiko

host = "162.243.9.88"
user = os.environ.get("VPS_USER", "root")
pw = os.environ["VPS_PW"]
cmd = sys.argv[1]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pw, timeout=30, look_for_keys=False, allow_agent=False)
chan = c.get_transport().open_session()
chan.get_pty()
chan.exec_command(cmd)
out = b""
while True:
    data = chan.recv(4096)
    if not data:
        break
    out += data
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()
code = chan.recv_exit_status()
print(f"\n[exit_code={code}]")
c.close()
