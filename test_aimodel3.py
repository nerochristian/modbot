import urllib.request
import json
import datetime

api_key = "sk-YSOaE1QIsyyUmwkn9EavAsRjZ0D6A63dNIe0SBZVV8R"
url = "https://aimodel.lol/v1/responses"

def test_payload(payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        if hasattr(e, 'read'):
            return e.read().decode('utf-8')
        return str(e)

payload = {
    "model": "accounts/aimodel/models/glm-5.2",
    "input": [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "What is the top news headline globally for today, July 27, 2026?"}],
    "temperature": 0.5,
    "max_output_tokens": 300,
    "research": True
}
print("Testing ultra recent query with research=True:")
print(test_payload(payload))
