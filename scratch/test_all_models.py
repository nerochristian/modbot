import os
import requests
import time
from dotenv import load_dotenv

load_dotenv(".env")

api_key = os.getenv("AIMODEL_API_KEY")
base_url = "https://aimodel.lol/v1"

def query_model(model, prompt, temp=0.0):
    try:
        res = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temp,
                "max_tokens": 100
            }
        )
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content'].strip()
        return f"Error: {res.status_code}"
    except Exception as e:
        return f"Fail: {e}"

print("Fetching available models...")
try:
    response = requests.get(
        f"{base_url}/models",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    models_list = response.json().get("data", [])
    model_ids = [m.get('id') for m in models_list]
except Exception as e:
    print(f"Error fetching models: {e}")
    model_ids = []

print(f"Found {len(model_ids)} models. Testing identity and cutoff for each...\n")

for model in model_ids:
    print(f"--- {model} ---")
    cutoff = query_model(model, "What is your exact knowledge cutoff date? Answer in one sentence.")
    print(f"Cutoff: {cutoff}")
    # Random numbers
    nums = []
    for _ in range(3):
        ans = query_model(model, "Pick a random number between 1 and 100. Output strictly just the number, nothing else.", temp=0.7)
        nums.append(ans)
    print(f"Randoms: {', '.join(nums)}\n")
