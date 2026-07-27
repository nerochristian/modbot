import urllib.request
import json

api_key = "sk-YSOaE1QIsyyUmwkn9EavAsRjZ0D6A63dNIe0SBZVV8R"
url = "https://aimodel.lol/v1/responses"

models_to_test = [
    "claude-fable-5",
    "accounts/aimodel/models/claude-fable-5",
    "claude-5-fable",
    "accounts/aimodel/models/claude-5-fable",
    "fable-5.0",
    "fable-5",
]

for model in models_to_test:
    payload = {
        "model": model,
        "input": [{"role": "user", "content": "hi"}],
        "temperature": 0.5,
        "max_output_tokens": 10
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            print(f"{model}: OK")
    except Exception as e:
        if hasattr(e, 'read'):
            print(f"{model}: HTTP {e.code} - {e.read().decode('utf-8')}")
        else:
            print(f"{model}: {e}")
