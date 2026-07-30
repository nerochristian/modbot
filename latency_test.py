import urllib.request
import json
import time
import os

api_key = "sk-KdGb0sOpgENfT95QRhDerqwGQLBZAHyA4nlJ1vGmg44"
base_url = "https://aimodel.lol/v1"

print("Fetching models...")
req = urllib.request.Request(f"{base_url}/models", headers={
    'Authorization': f'Bearer {api_key}',
    'User-Agent': 'Mozilla/5.0'
})

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        models = [m['id'] for m in data.get('data', [])]
except Exception as e:
    print(f"Failed to fetch models: {e}")
    exit(1)

results = []
print(f"Testing {len(models)} models for latency (TTFT)...")

for model in models:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True,
        "max_tokens": 10
    }).encode('utf-8')
    
    req = urllib.request.Request(f"{base_url}/chat/completions", data=payload, headers={
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    })
    
    start_time = time.time()
    ttft = None
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            for line in response:
                if line.strip():
                    ttft = (time.time() - start_time) * 1000
                    break
        
        if ttft:
            results.append((model, f"{ttft:.2f} ms"))
            print(f"{model}: {ttft:.2f} ms")
        else:
            results.append((model, "No data"))
            print(f"{model}: No data")
    except Exception as e:
        results.append((model, "Error or Timeout"))
        print(f"{model}: Error or Timeout")

# Write to markdown table
with open('latency_results.md', 'w') as f:
    f.write("| Model | Time to First Token (TTFT) |\n")
    f.write("|---|---|\n")
    for model, latency in results:
        f.write(f"| {model} | {latency} |\n")

print("\nDone! Results saved to latency_results.md")
