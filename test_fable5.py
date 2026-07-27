import urllib.request
import json
import datetime

api_key = "sk-YSOaE1QIsyyUmwkn9EavAsRjZ0D6A63dNIe0SBZVV8R"
url = "https://aimodel.lol/v1/responses"

def test_payload(model, prompt):
    payload = {
        "model": model,
        "input": [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_output_tokens": 300,
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        if hasattr(e, 'read'):
            return f"HTTP {e.code}: " + e.read().decode('utf-8')
        return str(e)

print("Test 1 (fable-5):")
print(test_payload("fable-5", "Search the internet for the top news headline globally for today, July 27, 2026."))

print("\nTest 2 (accounts/aimodel/models/fable-5):")
print(test_payload("accounts/aimodel/models/fable-5", "Search the internet for the top news headline globally for today, July 27, 2026."))

