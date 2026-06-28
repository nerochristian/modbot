import asyncio
from utils.deepseek_web import DeepSeekWebClient

async def main():
    scraper = DeepSeekWebClient()
    await scraper._start()
    await scraper.prewarm()
    try:
        ans = await scraper.chat("When was anomaly hospital on roblox released?")
        print("ANSWER:", ans)
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
