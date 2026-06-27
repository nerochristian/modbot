"""Experimental DeepSeek web client used when no supported research API exists."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from pathlib import Path


logger = logging.getLogger("ModBot.DeepSeekWeb")


class DeepSeekWebError(RuntimeError):
    pass


class DeepSeekWebAuthError(DeepSeekWebError):
    pass


class DeepSeekWebClient:
    """Serialize research requests through an authenticated headless browser."""

    def __init__(self) -> None:
        self.enabled = os.getenv("DEEPSEEK_WEB_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
        self.storage_state_path = Path(
            os.getenv("DEEPSEEK_WEB_STORAGE_STATE", "/root/.config/modbot/deepseek-storage.json")
        )
        self.timeout_seconds = min(300, max(30, int(os.getenv("DEEPSEEK_WEB_TIMEOUT", "150"))))
        self._lock = asyncio.Lock()
        self._playwright = None
        self._browser = None
        self._context = None

    async def _start(self) -> None:
        if self._browser is not None and self._browser.is_connected():
            return
        if not self.storage_state_path.is_file():
            raise DeepSeekWebAuthError("DeepSeek browser session is not configured.")
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise DeepSeekWebError("Playwright is not installed.") from exc

        self._playwright = await async_playwright().start()
        try:
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage", "--no-sandbox"],
            )
            self._context = await self._browser.new_context(
                storage_state=str(self.storage_state_path),
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/148.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1440, "height": 1000},
            )
        except Exception:
            await self.close()
            raise

    async def _set_toggle(self, page, label: str) -> None:
        toggle = page.locator("div.ds-toggle-button").filter(has_text=label)
        if await toggle.count() != 1:
            raise DeepSeekWebError(f"DeepSeek {label} control was not found.")
        if await toggle.get_attribute("aria-pressed") != "true":
            await toggle.click()
            if await toggle.get_attribute("aria-pressed") != "true":
                raise DeepSeekWebError(f"DeepSeek {label} could not be enabled.")

    async def research(self, prompt: str) -> str:
        if not self.enabled:
            raise DeepSeekWebError("DeepSeek web provider is disabled.")
        clean_prompt = (prompt or "").strip()
        if not clean_prompt:
            raise DeepSeekWebError("Research prompt is empty.")
        clean_prompt = clean_prompt[:12000]

        async with self._lock:
            await self._start()
            page = await self._context.new_page()
            try:
                await page.goto(
                    "https://chat.deepseek.com/",
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
                textbox = page.get_by_role("textbox", name="Message DeepSeek")
                try:
                    await textbox.wait_for(state="visible", timeout=30000)
                except Exception as exc:
                    raise DeepSeekWebAuthError(
                        "DeepSeek session expired or a login challenge was shown."
                    ) from exc

                await self._set_toggle(page, "DeepThink")
                await self._set_toggle(page, "Search")
                answers = page.locator(".ds-assistant-message-main-content")
                before_count = await answers.count()
                request = (
                    "Research the following request using web search. Answer in the same language as the request. "
                    "Return only the final answer, include source URLs, distinguish confirmed facts from uncertainty, "
                    "and do not expose hidden reasoning.\n\n"
                    f"REQUEST:\n{clean_prompt}"
                )
                await textbox.fill(request)
                await textbox.press("Enter")

                deadline = time.monotonic() + self.timeout_seconds
                last_text = ""
                stable_reads = 0
                final = ""
                while time.monotonic() < deadline:
                    await asyncio.sleep(1)
                    count = await answers.count()
                    if count <= before_count:
                        continue
                    raw_text = (await answers.nth(count - 1).inner_text()).strip()
                    if not raw_text:
                        continue
                    candidate = re.sub(r'-\s*\n(?:-\s*\n)*(?:\d+\s*\n(?:-\s*\n)*)*', lambda m: ''.join(f'[{n}]' for n in re.findall(r'\d+', m.group(0))), raw_text)
                    if candidate == last_text:
                        stable_reads += 1
                    else:
                        last_text = candidate
                        stable_reads = 0
                    if stable_reads >= 5:
                        final = candidate
                        break
                if not final:
                    raise DeepSeekWebError("DeepSeek research timed out before a final answer was returned.")

                final_locator = answers.nth((await answers.count()) - 1)
                links = await final_locator.locator("a[href]").evaluate_all(
                    "elements => [...new Set(elements.map(a => a.href).filter(Boolean))]"
                )
                source_links = [str(url) for url in links if str(url).startswith(("http://", "https://"))]
                if source_links and not any(url in final for url in source_links):
                    final += "\n\nSources:\n" + "\n".join(f"[{i+1}] {url}" for i, url in enumerate(source_links[:12]))
                return final[:24000]
            except DeepSeekWebError:
                raise
            except Exception as exc:
                logger.exception("DeepSeek web research failed")
                raise DeepSeekWebError(f"DeepSeek browser failure: {type(exc).__name__}") from exc
            finally:
                await page.close()

    async def close(self) -> None:
        context, browser, playwright = self._context, self._browser, self._playwright
        self._context = self._browser = self._playwright = None
        if context is not None:
            try:
                await context.close()
            except Exception:
                pass
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass
        if playwright is not None:
            try:
                await playwright.stop()
            except Exception:
                pass
