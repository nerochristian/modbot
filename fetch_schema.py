import urllib.request
import json

url = "https://opencode.ai/config.json"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        schema = json.loads(response.read().decode('utf-8'))
        print(json.dumps(schema.get('', {}).get('Config', {}), indent=2)[:2000])
except Exception as e:
    print(f"Error: {e}")
