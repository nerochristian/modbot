import asyncio
import os
import sys

from dotenv import load_dotenv

# load environment variables before importing bot modules
load_dotenv(".env")

sys.path.insert(0, os.path.abspath("."))

from cogs.aimoderation.ai_client import AiClient

async def main():
    client = AiClient(None)
    # mock config since we don't have a real bot
    class DummyConfig:
        model = "accounts/aimodel/models/glm-5.1"
    client.config = DummyConfig()
    client.provider = "aimodel"

    print("Provider:", client.provider)
    print("Is available:", client.is_available)
    print("Availability message:", client.availability_message())

    print("\nTesting _call_aimodel directly...")
    try:
        response = await client._call_aimodel(
            [{"role": "user", "content": "Hello!"}],
            temperature=0.1,
            max_tokens=50,
            model="accounts/aimodel/models/glm-5.1"
        )
        print("Response:", response)
    except Exception as e:
        print("Error calling aimodel:", e)

if __name__ == "__main__":
    asyncio.run(main())
