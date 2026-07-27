import urllib.request
import json

url = "https://opencode.ai/config.json"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        with open("schema.json", "w", encoding="utf-8") as f:
            f.write(response.read().decode("utf-8"))
except Exception as e:
    print(f"Error: {e}")
