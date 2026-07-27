import urllib.request
import json

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

payload1 = {
    "model": "accounts/aimodel/models/glm-5.2",
    "input": [{"role": "system", "content": "You are a bot"}, {"role": "user", "content": "who is the current president of the united states as of today?"}],
    "temperature": 0.5,
    "max_output_tokens": 100,
    "search": True
}
print("Test 1 (search):", test_payload(payload1)[:300])

payload2 = payload1.copy()
del payload2["search"]
payload2["web_search"] = True
print("Test 2 (web_search):", test_payload(payload2)[:300])

payload3 = payload1.copy()
del payload3["search"]
payload3["research"] = True
print("Test 3 (research):", test_payload(payload3)[:300])
