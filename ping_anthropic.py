import urllib.request
import json

url = "https://aimodel.lol/v1/messages"
headers = {
    "x-api-key": "sk-KdGb0sOpgENfT95QRhDerqwGQLBZAHyA4nlJ1vGmg44",
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
    "User-Agent": "Mozilla/5.0"
}
data = {
    "model": "claude-fable-5",
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": "hello"}
    ]
}

req = urllib.request.Request(url, json.dumps(data).encode("utf-8"), headers)
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        print(response.read().decode())
except Exception as e:
    if hasattr(e, 'read'):
        print(e.read().decode())
    else:
        print(e)
