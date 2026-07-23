import aiohttp
import asyncio
import time
import os

AIMODEL_API_KEY = "sk-YSOaE1QIsyyUmwkn9EavAsRjZ0D6A63dNIe0SBZVV8R"
AIMODEL_BASE_URL = "https://aimodel.lol/v1"

async def test_latency():
    async with aiohttp.ClientSession() as session:
        # 1. Get models
        headers = {"Authorization": f"Bearer {AIMODEL_API_KEY}"}
        async with session.get(f"{AIMODEL_BASE_URL}/models", headers=headers) as resp:
            data = await resp.json()
            models = [m['id'] for m in data.get('data', [])]
            print("Available models:", len(models))
        
        # Test a few relevant models
        target_models = []
        for m in models:
            if "claude" in m.lower() or "glm" in m.lower() or "sonnet" in m.lower() or "opus" in m.lower() or "minimax" in m.lower():
                target_models.append(m)
        
        print("Testing models:", target_models)
        
        results = {}
        for model in target_models:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            }
            start = time.time()
            try:
                async with session.post(f"{AIMODEL_BASE_URL}/chat/completions", headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        end = time.time()
                        latency = end - start
                        results[model] = latency
                        print(f"{model}: {latency:.2f}s")
                    else:
                        text = await resp.text()
                        print(f"{model}: Error {resp.status} - {text}")
            except Exception as e:
                print(f"{model}: Exception {e}")
                
        print("\n--- Latency Ranking ---")
        for model, lat in sorted(results.items(), key=lambda x: x[1]):
            print(f"{model}: {lat:.2f}s")

asyncio.run(test_latency())
