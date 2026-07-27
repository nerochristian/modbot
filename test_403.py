import urllib.request

url = "https://aimodel.lol/v1/models"
api_key = "sk-YSOaE1QIsyyUmwkn9EavAsRjZ0D6A63dNIe0SBZVV8R"
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {api_key}', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode('utf-8')[:200])
except Exception as e:
    if hasattr(e, 'read'):
        print(f"HTTP {e.code}")
        print(e.read().decode('utf-8')[:500])
    else:
        print(str(e))
