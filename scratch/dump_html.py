import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://chat.deepseek.com/")
        await asyncio.sleep(5)
        
        await page.screenshot(path="c:/Users/Dell/mod/scratch/ds_screenshot.png")
        
        html = await page.content()
        with open("c:/Users/Dell/mod/scratch/ds_page.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
