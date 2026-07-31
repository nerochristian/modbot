import aiohttp
import asyncio
import time
import os

AIMODEL_API_KEY = "sk-4ESdaNCIHygyvR0ehaolNBDuPTAifxQxkcHqfePdxFN"
AIMODEL_BASE_URL = "https://aimodel.lol/v1"

async def test_latency():
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {AIMODEL_API_KEY}"}
        
        target_models = ['claude-3.5-sonnet', 'claude-3.5-sonnet-20240620', 'claude-3-opus', 'claude-3-sonnet', 'gpt-4o', 'gpt-4-turbo', 'glm-4', 'glm-4-flash', 'minimax']
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
