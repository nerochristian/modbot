import asyncio
from utils.deepseek_web import DeepSeekWebClient

async def main():
    client = DeepSeekWebClient()
    await client.prewarm()
    
    # After prewarm, the page is loaded
    page = client._pages.get("prewarm") or list(client._pages.values())[0]
    
    html = await page.content()
    with open("c:/Users/Dell/mod/scratch/ds_page.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    await page.screenshot(path="c:/Users/Dell/mod/scratch/ds_screenshot.png")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
