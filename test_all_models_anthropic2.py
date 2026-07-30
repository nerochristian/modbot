import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://aimodel.lol/v1/messages"
headers = {
    "x-api-key": "sk-KdGb0sOpgENfT95QRhDerqwGQLBZAHyA4nlJ1vGmg44",
    "Content-Type": "application/json",
    "anthropic-version": "2023-06-01"
}
models = [
    "kimi-k3-fast", "kimi-k3", "claude-opus-5", "gpt-5.6", 
    "claude-sonnet-5", "claude-fable-5", "claude-opus-4.8", 
    "claude-opus-4.7", "glm-5.2", "deepseek-v4-pro",
    "claude-3-5-sonnet-20240620", "claude-3-opus-20240229"
]

for model in models:
    print(f"Testing model: {model}")
    data = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}]
    }
    req = urllib.request.Request(url, json.dumps(data).encode("utf-8"), headers)
    try:
        with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
            print("SUCCESS:", response.read().decode()[:100])
    except urllib.error.HTTPError as e:
        print("ERROR:", e.read().decode())
    except Exception as e:
        print("EXCEPTION:", str(e))
