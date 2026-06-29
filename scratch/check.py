import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://chat.deepseek.com/")
        await asyncio.sleep(3)
        
        # Dump HTML of everything containing "DeepThink"
        elements = await page.locator(':has-text("DeepThink")').all()
        for i, el in enumerate(elements):
            try:
                html = await el.evaluate("el => el.outerHTML")
                if len(html) < 2000:
                    print(f"--- Element {i} ---")
                    print(html)
            except:
                pass
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
