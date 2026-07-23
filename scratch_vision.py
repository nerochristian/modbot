import aiohttp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv('.env')
API_KEY = os.getenv('RELAYROUTER_API_KEY')
BASE_URL = os.getenv('RELAYROUTER_BASE_URL')

async def test_vision():
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        models_to_test = ['claude-test-opus-4-8', 'gpt-5.5']
        
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
                async with session.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"{model} vision test: SUCCESS. Response: {data['choices'][0]['message']['content']}")
                    else:
                        text = await resp.text()
                        print(f"{model} vision test: FAILED ({resp.status}) - {text}")
            except Exception as e:
                print(f"{model} vision test: Exception {e}")

asyncio.run(test_vision())
