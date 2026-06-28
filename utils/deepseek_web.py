"""Authenticated DeepSeek web client for chat, research, and vision."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final


logger = logging.getLogger("ModBot.DeepSeekWeb")

_DEEPSEEK_URL: Final = "https://chat.deepseek.com/"
_ANSWER_SELECTOR: Final = ".ds-assistant-message-main-content"
_CHALLENGE_MARKERS: Final = (
    "verify you are human",
    "checking your browser",
    "security verification",
    "turnstile",
    "captcha",
    "cf-chl",
)


class DeepSeekWebError(RuntimeError):
    """Base error raised by the DeepSeek browser provider."""


class DeepSeekWebAuthError(DeepSeekWebError):
    """The saved login expired or an interactive human check appeared."""


class DeepSeekWebClient:
    """Run isolated DeepSeek UI lanes while sharing one authenticated browser."""

    def __init__(self) -> None:
        self.enabled = os.getenv("DEEPSEEK_WEB_ENABLED", "false").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.storage_state_path = Path(
            os.getenv(
                "DEEPSEEK_WEB_STORAGE_STATE",
                "/root/.config/modbot/deepseek-storage.json",
            )
        )
        self.timeout_seconds = min(
            300,
            max(30, int(os.getenv("DEEPSEEK_WEB_TIMEOUT", "150"))),
        )
        self._start_lock = asyncio.Lock()
        self._lane_locks = {
            "chat": asyncio.Lock(),
            "research": asyncio.Lock(),
            "vision": asyncio.Lock(),
        }
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._pages: dict[str, Any] = {}

    @staticmethod
    def _limit_prompt(prompt: str, limit: int = 12_000) -> str:
        clean = (prompt or "").strip()
        if len(clean) <= limit:
            return clean
        marker = "\n\n[older context trimmed]\n\n"
        available = max(0, limit - len(marker))
        first = available // 2
        last = available - first
        return f"{clean[:first]}{marker}{clean[-last:]}"

    @staticmethod
    def _looks_like_challenge(text: str) -> bool:
        lowered = (text or "").lower()
        return any(marker in lowered for marker in _CHALLENGE_MARKERS)

    @staticmethod
    def _clean_answer(text: str) -> str:
        clean = (text or "").strip()
        clean = re.sub(
            r"^(?:markdown\s*)?(?:Copy\s*)?(?:Download\s*)?",
            "",
            clean,
            flags=re.IGNORECASE,
        ).strip()
        clean = re.sub(r"^```(?:markdown)?\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean)
        clean = re.sub(r"(?m)^\s*(?:[-–—]\s*)?\d{1,3}\s*$", "", clean)
        clean = re.sub(r"(?m)^\s*[-–—]\s*$", "", clean)
        clean = re.sub(r"[-–—](?=[.,;:!?](?:\s|$))", "", clean)
        clean = re.sub(r"\n{3,}", "\n\n", clean)
        return clean.strip()

    async def _start(self) -> None:
        async with self._start_lock:
            if self._browser is not None and self._browser.is_connected():
                return
            if not self.storage_state_path.is_file():
                raise DeepSeekWebAuthError(
                    "DeepSeek browser session is not configured."
                )
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

    async def _get_page(self, lane: str) -> Any:
        await self._start()
        page = self._pages.get(lane)
        if page is None or page.is_closed():
            page = await self._context.new_page()
            self._pages[lane] = page
        await page.goto(
            _DEEPSEEK_URL,
            wait_until="domcontentloaded",
            timeout=60_000,
        )
        return page

    @staticmethod
    async def _visible_locator(locator: Any) -> Any | None:
        for index in range(await locator.count()):
            candidate = locator.nth(index)
            if await candidate.is_visible():
                return candidate
        return None

    async def _wait_for_textbox(self, page: Any) -> Any:
        textbox = page.get_by_role("textbox", name="Message DeepSeek")
        try:
            await textbox.wait_for(state="visible", timeout=30_000)
            return textbox
        except Exception as exc:
            body_text = ""
            try:
                body_text = await page.locator("body").inner_text(timeout=2_000)
            except Exception:
                pass
            reason = (
                "DeepSeek showed an interactive human verification challenge. "
                "The saved browser session must be renewed manually."
                if self._looks_like_challenge(body_text)
                else "DeepSeek login expired or the saved browser session is invalid."
            )
            raise DeepSeekWebAuthError(reason) from exc

    async def _set_mode(self, page: Any, label: str) -> None:
        option = await self._visible_locator(page.get_by_text(label, exact=True))
        if option is None:
            if label == "Instant":
                return
            raise DeepSeekWebError(f"DeepSeek {label} mode was not found.")
        selected = (
            await option.get_attribute("aria-selected") == "true"
            or await option.get_attribute("aria-pressed") == "true"
        )
        classes = (await option.get_attribute("class") or "").lower()
        if not selected and "selected" not in classes and "active" not in classes:
            await option.click()

    async def _set_toggle(self, page: Any, label: str, enabled: bool) -> None:
        candidates = page.locator("div.ds-toggle-button").filter(has_text=label)
        toggle = await self._visible_locator(candidates)
        if toggle is None:
            raise DeepSeekWebError(f"DeepSeek {label} control was not found.")
        current = await toggle.get_attribute("aria-pressed") == "true"
        if current != enabled:
            await toggle.click()
            updated = await toggle.get_attribute("aria-pressed") == "true"
            if updated != enabled:
                state = "enabled" if enabled else "disabled"
                raise DeepSeekWebError(
                    f"DeepSeek {label} could not be {state}."
                )

    async def _attach_images(
        self,
        page: Any,
        images: Sequence[tuple[str, str, bytes]],
    ) -> None:
        file_input = page.locator('input[type="file"]')
        if await file_input.count() == 0:
            attachment_button = page.get_by_role(
                "button",
                name=re.compile(r"attach|upload|image", re.IGNORECASE),
            )
            button = await self._visible_locator(attachment_button)
            if button is not None:
                await button.click()
                file_input = page.locator('input[type="file"]')
        if await file_input.count() == 0:
            raise DeepSeekWebError("DeepSeek Vision upload control was not found.")

        payloads = [
            {"name": name, "mimeType": mime_type, "buffer": data}
            for name, mime_type, data in images
            if data
        ]
        if not payloads:
            raise DeepSeekWebError("No valid image data was supplied.")
        await file_input.first.set_input_files(payloads)

        # DeepSeek initially treats image uploads as documents for OCR. Once
        # that pass finishes, the UI exposes a "Try Vision" handoff that must
        # be selected before the message can be submitted as an image request.
        vision_link = page.get_by_text("Vision", exact=True)
        try:
            await vision_link.first.wait_for(state="visible", timeout=30_000)
            visible_link = await self._visible_locator(vision_link)
            if visible_link is None:
                raise DeepSeekWebError("DeepSeek Vision handoff was not visible.")
            await visible_link.click()
            await page.get_by_text(
                re.compile(r"Start Chatting with Vision", re.IGNORECASE)
            ).first.wait_for(state="visible", timeout=15_000)
            await asyncio.sleep(3)
        except DeepSeekWebError:
            raise
        except Exception as exc:
            raise DeepSeekWebError(
                "DeepSeek did not make the image available to Vision."
            ) from exc

    async def _extract_answer(self, answer: Any) -> tuple[str, list[str]]:
        text = await answer.evaluate(
            """element => {
                const clone = element.cloneNode(true);
                clone.querySelectorAll('a').forEach(anchor => {
                    const text = (anchor.innerText || '').trim();
                    if (/^[\\s\\-–—\\d]+$/.test(text)) anchor.remove();
                });

                const render = node => {
                    if (node.nodeType === Node.TEXT_NODE) {
                        return node.textContent || '';
                    }
                    if (node.nodeType !== Node.ELEMENT_NODE) return '';

                    const tag = node.tagName.toLowerCase();
                    const children = [...node.childNodes].map(render).join('');
                    const trimmed = children.trim();
                    if (!trimmed && tag !== 'br') return '';

                    if (/^h[1-6]$/.test(tag)) {
                        const level = Number(tag.slice(1));
                        return `${'#'.repeat(level)} ${trimmed}\n\n`;
                    }
                    if (tag === 'p') return `${trimmed}\n\n`;
                    if (tag === 'br') return '\n';
                    if (tag === 'strong' || tag === 'b') return `**${trimmed}**`;
                    if (tag === 'em' || tag === 'i') return `*${trimmed}*`;
                    if (tag === 'code' && node.parentElement?.tagName.toLowerCase() !== 'pre') {
                        return `\`${trimmed}\``;
                    }
                    if (tag === 'pre') return `\`\`\`\n${node.innerText.trim()}\n\`\`\`\n\n`;
                    if (tag === 'blockquote') {
                        return `${trimmed.split('\n').map(line => `> ${line}`).join('\n')}\n\n`;
                    }
                    if (tag === 'li') {
                        const parent = node.parentElement;
                        let marker = '•';
                        if (parent?.tagName.toLowerCase() === 'ol') {
                            marker = `${[...parent.children].indexOf(node) + 1}.`;
                        }
                        return `${marker} ${trimmed}\n\n`;
                    }
                    if (tag === 'ul' || tag === 'ol') return `${children.trim()}\n\n`;
                    if (tag === 'a') return trimmed;
                    if (tag === 'hr') return '\n---\n\n';
                    return children;
                };

                return render(clone)
                    .replace(/[ \\t]+\n/g, '\n')
                    .replace(/\n{3,}/g, '\n\n')
                    .trim();
            }"""
        )
        links = await answer.evaluate(
            """element => [...new Set(
                [...element.querySelectorAll('a[href]')]
                    .map(anchor => {
                        const url = new URL(anchor.href);
                        url.search = '';
                        url.hash = '';
                        return url.toString();
                    })
                    .filter(url => url.startsWith('http') && !url.includes('deepseek.com'))
            )]"""
        )
        return self._clean_answer(str(text)), [str(link) for link in links]

    async def _wait_for_answer(
        self,
        page: Any,
        before_count: int,
        *,
        stable_reads_required: int,
    ) -> tuple[str, list[str]]:
        answers = page.locator(_ANSWER_SELECTOR)
        deadline = time.monotonic() + self.timeout_seconds
        last_text = ""
        last_links: list[str] = []
        stable_reads = 0
        while time.monotonic() < deadline:
            await asyncio.sleep(0.75)
            count = await answers.count()
            if count <= before_count:
                continue
            text, links = await self._extract_answer(answers.nth(count - 1))
            if not text:
                continue
            if text == last_text:
                stable_reads += 1
            else:
                last_text = text
                last_links = links
                stable_reads = 0
            if stable_reads >= stable_reads_required:
                return text, last_links
        raise DeepSeekWebError(
            "DeepSeek timed out before a final answer was returned."
        )

    async def _run(
        self,
        prompt: str,
        *,
        lane: str,
        ui_mode: str,
        deepthink: bool,
        search: bool,
        images: Sequence[tuple[str, str, bytes]] = (),
    ) -> str:
        if not self.enabled:
            raise DeepSeekWebError("DeepSeek web provider is disabled.")
        clean_prompt = self._limit_prompt(prompt)
        if not clean_prompt:
            raise DeepSeekWebError("DeepSeek prompt is empty.")

        async with self._lane_locks[lane]:
            try:
                page = await self._get_page(lane)
                textbox = await self._wait_for_textbox(page)
                await self._set_mode(page, ui_mode)
                await self._set_toggle(page, "DeepThink", deepthink)
                await self._set_toggle(page, "Search", search)
                if images:
                    await self._attach_images(page, images)

                answers = page.locator(_ANSWER_SELECTOR)
                before_count = await answers.count()
                await textbox.fill(clean_prompt)
                await textbox.press("Enter")
                answer, source_links = await self._wait_for_answer(
                    page,
                    before_count,
                    stable_reads_required=5 if lane == "research" else 3,
                )
                if search and source_links and not any(
                    link in answer for link in source_links
                ):
                    sources = "\n".join(
                        f"- <{link}>" for link in source_links[:8]
                    )
                    answer = f"{answer}\n\n__BOT_SOURCES__\n{sources}"
                return answer[:24_000]
            except (DeepSeekWebAuthError, DeepSeekWebError):
                await self._discard_page(lane)
                raise
            except Exception as exc:
                await self._discard_page(lane)
                logger.exception("DeepSeek %s lane failed", lane)
                raise DeepSeekWebError(
                    f"DeepSeek browser failure: {type(exc).__name__}"
                ) from exc

    async def chat(self, prompt: str) -> str:
        request = (
            "Reply in the same language as the user's latest message; default to "
            "English when unclear. Return only the final Discord-ready answer. "
            "Do not expose reasoning, add citations, or claim live verification.\n\n"
            f"{prompt}"
        )
        return await self._run(
            request,
            lane="chat",
            ui_mode="Instant",
            deepthink=False,
            search=False,
        )

    async def research(self, prompt: str) -> str:
        request = (
            "Research the request using live web search. Reply in the same language "
            "as the user's latest message; default to English when unclear. Return "
            "only the polished Discord-ready final answer. Use this exact visual "
            "structure: begin with one '# <relevant emoji> <specific title>' heading; "
            "then a short direct answer; then organize useful details into clearly "
            "named sections. Format each key section as '• **Section name**' followed "
            "by its explanation on the next indented line. Put a blank line between "
            "every paragraph and section so the response never becomes a wall of text. "
            "Use natural prose, correct punctuation spacing, and bold only the details "
            "that deserve emphasis. Do not add a generic introduction, conclusion, "
            "Sources section, raw URLs, or numeric citation markers; source links are "
            "attached separately by the bot. Do not expose reasoning.\n\n"
            f"{prompt}"
        )
        return await self._run(
            request,
            lane="research",
            ui_mode="Instant",
            deepthink=True,
            search=True,
        )

    async def vision(
        self,
        prompt: str,
        images: Sequence[tuple[str, str, bytes]],
        *,
        search: bool = False,
    ) -> str:
        request = (
            "Analyze the attached image(s) and answer the user's request. Reply in "
            "the same language as the user's latest message; default to English. "
            "Return only the final Discord-ready answer and do not expose reasoning.\n\n"
            f"{prompt}"
        )
        return await self._run(
            request,
            lane="vision",
            ui_mode="Instant",
            deepthink=False,
            search=search,
            images=images,
        )

    async def _discard_page(self, lane: str) -> None:
        page = self._pages.pop(lane, None)
        if page is not None and not page.is_closed():
            try:
                await page.close()
            except Exception:
                pass

    async def close(self) -> None:
        for lane in list(self._pages):
            await self._discard_page(lane)
        context, browser, playwright = (
            self._context,
            self._browser,
            self._playwright,
        )
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
