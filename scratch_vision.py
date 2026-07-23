import aiohttp
import asyncio

AIMODEL_API_KEY = "sk-YSOaE1QIsyyUmwkn9EavAsRjZ0D6A63dNIe0SBZVV8R"
AIMODEL_BASE_URL = "https://aimodel.lol/v1"

async def test_vision():
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {AIMODEL_API_KEY}"}
        
        models_to_test = ['accounts/aimodel/models/claude-sonnet-5', 'accounts/aimodel/models/glm-5.1', 'accounts/aimodel/models/claude-opus-4.8']
        
        for model in models_to_test:
            payload = {
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/React-icon.svg/1200px-React-icon.svg.png"
                            }
                        }
                    ]
                }],
                "max_tokens": 10
            }
            try:
                async with session.post(f"{AIMODEL_BASE_URL}/chat/completions", headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"{model} vision test: SUCCESS. Response: {data['choices'][0]['message']['content']}")
                    else:
                        text = await resp.text()
                        print(f"{model} vision test: FAILED ({resp.status}) - {text}")
            except Exception as e:
                print(f"{model} vision test: Exception {e}")

asyncio.run(test_vision())
