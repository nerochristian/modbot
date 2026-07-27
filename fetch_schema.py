import urllib.request
import json

url = "https://opencode.ai/config.json"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        schema = json.loads(response.read().decode('utf-8'))
        config_defs = schema.get('', {}).get('Config', {}).get('properties', {})
        print("Config Properties:")
        for k, v in config_defs.items():
            print(f"- {k}")
except Exception as e:
    print(f"Error: {e}")
