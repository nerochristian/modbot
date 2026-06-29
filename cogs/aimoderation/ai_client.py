"""
AI Client — provider-agnostic AI interface with rate limiting, web search, and memory.

Uses DeepSeek Web as the default provider. Falls back to DigitalOcean inference API.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, ClassVar, Dict, Final, List, Optional, Set, Tuple, Union

import aiohttp
import discord
from discord.ext import commands

from utils.deepseek_web import DeepSeekWebAuthError, DeepSeekWebClient, DeepSeekWebError
from utils.cache import RateLimiter
from utils.embeds import Colors, compact_kv_lines
from utils.components_v2 import ensure_layout_view_action_rows, layout_view_from_embeds


# =============================================================================
# MODULE-LEVEL HELPERS
# =============================================================================

_DO_API_KEY: Final[str] = os.getenv("DO_API_KEY", "").strip()
_DO_BASE_URL: Final[str] = os.getenv("DO_INFERENCE_BASE_URL", "https://inference.do-ai.run/v1").strip().rstrip("/")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GeminiClient:
    """Async wrapper around the configured AI provider with rate limiting and memory."""

    _CODE_FENCE_RE: ClassVar[re.Pattern] = re.compile(r"^```[a-zA-Z]*\s*|\s*```$", re.MULTILINE)
    _JSON_RE: ClassVar[re.Pattern] = re.compile(r"(\{.*\})", re.DOTALL)

    def __init__(self, bot: commands.Bot, config: AIConfig) -> None:
        self.bot = bot
        self.config = config
        self.provider = (config.provider or "deepseek-web").strip().lower()
        self._rate_limiter = RateLimiter(
            max_calls=config.rate_limit_calls,
            window_seconds=config.rate_limit_window,
        )
        self._block_until: Optional[datetime] = None
        self._block_reason: Optional[str] = None
        self._brave_search_api_key = os.getenv("BRAVE_SEARCH_API_KEY")
        self._tavily_api_key = os.getenv("TAVILY_API_KEY")
        self._serpapi_api_key = os.getenv("SERPAPI_API_KEY")
        self._deepseek_web = DeepSeekWebClient()

    @property
    def is_available(self) -> bool:
        if self.provider == "digitalocean":
            return bool(DO_API_KEY and DO_BASE_URL)
        return self._deepseek_web.enabled

    def availability_message(self) -> str:
        if self.provider == "digitalocean":
            if not DO_API_KEY:
                return "DigitalOcean provider is selected but `DO_API_KEY` is missing."
            if not DO_BASE_URL:
                return "DigitalOcean provider is selected but `DO_INFERENCE_BASE_URL` is empty."
            return "DigitalOcean inference is configured."

        if not self._deepseek_web.enabled:
            return "`DEEPSEEK_WEB_ENABLED` is off, so DeepSeek web requests are disabled."
        return "DeepSeek web is enabled. If requests still fail, refresh the saved browser session."

    def diagnostic_lines(self) -> List[str]:
        lines = [f"Provider: `{self.provider}`"]
        if self.provider == "digitalocean":
            model = (
                os.getenv("DO_AIMOD_MODEL")
                or os.getenv("DO_CHAT_MODEL")
                or os.getenv("DO_AUTOMOD_MODEL")
                or "deepseek-4-flash"
            )
            lines.extend(
                [
                    f"API key: {'present' if bool(DO_API_KEY) else 'missing'}",
                    f"Base URL: `{DO_BASE_URL or 'missing'}`",
                    f"Default model: `{model}`",
                ]
            )
        else:
            storage_path = getattr(self._deepseek_web, "storage_state_path", None)
            session_index = getattr(self._deepseek_web, "session_index_path", None)
            lines.extend(
                [
                    f"DeepSeek web enabled: {'yes' if self._deepseek_web.enabled else 'no'}",
                    f"Storage state: `{storage_path}`" if storage_path else "Storage state: `unknown`",
                    f"Session index: `{session_index}`" if session_index else "Session index: `unknown`",
                    f"Timeout: `{getattr(self._deepseek_web, 'timeout_seconds', 'unknown')}s`",
                ]
            )
        lines.append(f"Available now: {'yes' if self.is_available else 'no'}")
        lines.append(self.availability_message())
        return lines

    @property
    def has_web_search(self) -> bool:
        return bool(
            self._brave_search_api_key
            or self._tavily_api_key
            or self._serpapi_api_key
            or (self.provider == "deepseek-web" and self._deepseek_web.enabled)
        )

    async def close(self) -> None:
        await self._deepseek_web.close()

    async def prewarm(self) -> None:
        if self.provider != "deepseek-web":
            return
        await self._deepseek_web.prewarm()

    # ------------------------------------------------------------------
    # Service-block helpers
    # ------------------------------------------------------------------

    def _set_block(self, *, seconds: int, reason: str) -> None:
        self._block_until = _now() + timedelta(seconds=max(1, seconds))
        self._block_reason = reason
        logger.warning("AI service blocked for %ds: %s", seconds, reason)

    def _get_block_message(self) -> Optional[str]:
        if not self._block_until:
            return None
        remaining = (self._block_until - _now()).total_seconds()
        if remaining <= 0:
            self._block_until = self._block_reason = None
            return None
        mins = max(1, int(remaining // 60))
        return f"{self._block_reason} Try again in ~{mins}m."

    # ------------------------------------------------------------------
    # Internal API call
    # ------------------------------------------------------------------

    def _extract_json(self, raw: str) -> str:
        text = self._CODE_FENCE_RE.sub("", raw).strip()
        m = self._JSON_RE.search(text)
        return m.group(1) if m else text

    async def _call(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
        model: Optional[str] = None,
        json_mode: bool = False,
        allow_multimodal: bool = False,
        session_key: Optional[str] = None,
        session_name: Optional[str] = None,
    ) -> Optional[str]:
        if self.provider == "digitalocean":
            return await self._call_digitalocean(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                model=model,
                json_mode=json_mode,
                allow_multimodal=allow_multimodal,
            )

        del temperature, max_tokens, model, allow_multimodal
        if not self._deepseek_web.enabled:
            raise DeepSeekWebError("DeepSeek web provider is disabled.")

        prompt_parts: List[str] = []
        for message in messages:
            role = str(message.get("role") or "user").upper()
            content = self._stringify_web_content(message.get("content"))
            if content:
                prompt_parts.append(f"[{role}]\n{content}")
        if json_mode:
            prompt_parts.append(
                "[OUTPUT FORMAT]\nReturn exactly one valid JSON object and no other text."
            )
        return await self._deepseek_web.chat(
            "\n\n".join(prompt_parts),
            session_key=session_key,
            session_name=session_name,
        )

    async def _call_digitalocean(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
        model: Optional[str] = None,
        json_mode: bool = False,
        allow_multimodal: bool = False,
    ) -> Optional[str]:
        if not DO_API_KEY:
            raise RuntimeError("DigitalOcean inference is missing DO_API_KEY.")

        selected_model = (model or self.config.model or "").strip()
        if selected_model.lower() in {"", "deepseek-web", "digitalocean"}:
            selected_model = (
                os.getenv("DO_AIMOD_MODEL")
                or os.getenv("DO_CHAT_MODEL")
                or os.getenv("DO_AUTOMOD_MODEL")
                or "deepseek-4-flash"
            ).strip()
        request_messages = messages if allow_multimodal else self._normalize_text_messages(messages)
        if not request_messages:
            raise RuntimeError("DigitalOcean request has no message content.")

        payload: Dict[str, Any] = {
            "model": selected_model,
            "messages": request_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        session, owned_session = self._get_http_session(timeout=60)
        try:
            async with session.post(
                f"{DO_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {DO_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as resp:
                data = await resp.json(content_type=None)
                if resp.status >= 400:
                    detail = data.get("error", data) if isinstance(data, dict) else data
                    if resp.status in {401, 403}:
                        self._set_block(
                            seconds=900,
                            reason="DigitalOcean inference authentication or access failed.",
                        )
                    elif resp.status == 429:
                        self._set_block(
                            seconds=60,
                            reason="DigitalOcean inference rate limit or quota reached.",
                        )
                    raise RuntimeError(f"DigitalOcean HTTP {resp.status}: {str(detail)[:500]}")
        finally:
            if owned_session:
                await session.close()

        if not isinstance(data, dict):
            return None
        choices = data.get("choices") or []
        if not choices:
            return None
        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return self._stringify_web_content(content)
        return None

    @classmethod
    def _normalize_text_messages(cls, messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []
        for message in messages:
            role = str(message.get("role") or "user")
            content = cls._stringify_web_content(message.get("content"))
            if content:
                normalized.append({"role": role, "content": content})
        return normalized

    @staticmethod
    def _stringify_web_content(content: Any) -> str:
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if not isinstance(item, dict):
                    text = str(item).strip()
                    if text:
                        parts.append(text)
                    continue

                item_type = item.get("type")
                if item_type == "text":
                    text = str(item.get("text") or "").strip()
                    if text:
                        parts.append(text)
                    continue

                if item_type == "image_url":
                    image_url = item.get("image_url")
                    url = image_url.get("url") if isinstance(image_url, dict) else image_url
                    if isinstance(url, str) and url.strip():
                        if url.startswith("data:"):
                            parts.append("[Image omitted from this text-only request]")
                        else:
                            parts.append(f"[Image URL: {url.strip()}]")
                    continue

                text = str(item).strip()
                if text:
                    parts.append(text)
            return "\n".join(parts).strip()

        return str(content or "").strip()



    # ------------------------------------------------------------------
    # Pre-call checks (rate limit + service block)
    # ------------------------------------------------------------------

    async def _preflight(self, user_id: int) -> Optional[str]:
        """Return an error string if the call should be blocked, else None."""
        blocked = self._get_block_message()
        if blocked:
            return blocked
        is_limited, retry_after = await self._rate_limiter.is_rate_limited(user_id)
        if is_limited:
            return Messages.format(Messages.AI_RATE_LIMIT, seconds=int(max(1, retry_after)))
        return None

    async def _generate_search_queries(self, user_content: str, num_queries: int = 5) -> List[str]:
        """Use deepseek to decompose the user's prompt into optimal search queries."""
        import datetime
        current_date = datetime.datetime.now().strftime("%B %Y")
        sys_prompt = (
            "You are a search query generator. The user wants to research a topic. "
            f"The current date is {current_date}. If the user asks for 'latest', 'new', or current information, "
            f"you MUST append '{current_date}' or the current year to the search queries to ensure fresh results.\n"
            f"Break their request down into exactly {num_queries} highly specific, distinct search engine queries. "
            "Output ONLY a raw JSON array of strings. Do not use markdown code blocks. "
            "Example: [\"query 1\", \"query 2\"]"
        )
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_content}
        ]
        try:
            content = await self._call(
                messages,
                temperature=0.7,
                max_tokens=150,
                json_mode=False
            )
            if not content:
                return [user_content]
            
            # Clean markdown code blocks if the model ignored instructions
            clean_content = re.sub(r'```json|```', '', content).strip()
            
            # Extract array
            match = re.search(r'\[(.*)\]', clean_content, re.DOTALL)
            if match:
                data = json.loads(f"[{match.group(1)}]")
                if isinstance(data, list) and all(isinstance(x, str) for x in data):
                    return data[:num_queries]
            
            return [user_content]
        except Exception as e:
            logger.error(f"Failed to generate search queries: {e}")
            return [user_content]



    async def _web_search(self, query: str, *, max_results: int = 5) -> List[WebSearchResult]:
        if self._brave_search_api_key:
            return await self._search_brave(query, max_results=max_results)
        if self._tavily_api_key:
            return await self._search_tavily(query, max_results=max_results)
        if self._serpapi_api_key:
            return await self._search_serpapi(query, max_results=max_results)
        
        # Fallback to free DuckDuckGo search if no API keys are present
        try:
            from duckduckgo_search import DDGS
            def _sync_search():
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=max_results))
            loop = asyncio.get_running_loop()
            raw_results = await loop.run_in_executor(None, _sync_search)
            results = []
            for r in raw_results:
                results.append(WebSearchResult(
                    title=str(r.get("title", "")),
                    url=str(r.get("href", "")),
                    snippet=str(r.get("body", ""))
                ))
            return results
        except Exception as e:
            logger.error(f"DDG Search fallback failed: {e}")
            return []

    async def _search_brave(self, query: str, *, max_results: int) -> List[WebSearchResult]:
        session, owned_session = self._get_http_session(timeout=20)
        try:
            async with session.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": self._brave_search_api_key, "Accept": "application/json"},
                params={"q": query, "count": max_results, "freshness": "pm"},
            ) as resp:
                data = await resp.json(content_type=None)
                if resp.status >= 400:
                    raise RuntimeError(f"Brave Search HTTP {resp.status}: {str(data)[:300]}")
        finally:
            if owned_session:
                await session.close()

        items = ((data or {}).get("web") or {}).get("results") if isinstance(data, dict) else None
        return [
            WebSearchResult(
                title=str(item.get("title") or "Untitled")[:180],
                url=str(item.get("url") or ""),
                snippet=str(item.get("description") or "")[:500],
            )
            for item in (items or [])[:max_results]
            if isinstance(item, dict) and item.get("url")
        ]

    async def _search_tavily(self, query: str, *, max_results: int) -> List[WebSearchResult]:
        session, owned_session = self._get_http_session(timeout=20)
        try:
            async with session.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self._tavily_api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                    "include_answer": False,
                },
            ) as resp:
                data = await resp.json(content_type=None)
                if resp.status >= 400:
                    raise RuntimeError(f"Tavily HTTP {resp.status}: {str(data)[:300]}")
        finally:
            if owned_session:
                await session.close()

        items = data.get("results") if isinstance(data, dict) else None
        return [
            WebSearchResult(
                title=str(item.get("title") or "Untitled")[:180],
                url=str(item.get("url") or ""),
                snippet=str(item.get("content") or "")[:500],
            )
            for item in (items or [])[:max_results]
            if isinstance(item, dict) and item.get("url")
        ]

    async def _search_serpapi(self, query: str, *, max_results: int) -> List[WebSearchResult]:
        session, owned_session = self._get_http_session(timeout=20)
        try:
            async with session.get(
                "https://serpapi.com/search.json",
                params={"engine": "google", "q": query, "api_key": self._serpapi_api_key, "num": max_results},
            ) as resp:
                data = await resp.json(content_type=None)
                if resp.status >= 400:
                    raise RuntimeError(f"SerpAPI HTTP {resp.status}: {str(data)[:300]}")
        finally:
            if owned_session:
                await session.close()

        items = data.get("organic_results") if isinstance(data, dict) else None
        return [
            WebSearchResult(
                title=str(item.get("title") or "Untitled")[:180],
                url=str(item.get("link") or ""),
                snippet=str(item.get("snippet") or "")[:500],
            )
            for item in (items or [])[:max_results]
            if isinstance(item, dict) and item.get("link")
        ]

    def _get_http_session(self, *, timeout: int) -> Tuple[aiohttp.ClientSession, bool]:
        session: Optional[aiohttp.ClientSession] = getattr(self.bot, "session", None)
        if not session or getattr(session, "closed", False):
            return aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)), True
        return session, False

    @staticmethod
    def _format_web_results(results: List[WebSearchResult]) -> str:
        lines: List[str] = []
        for i, result in enumerate(results, start=1):
            lines.append(
                f"[{i}] {result.title}\nURL: {result.url}\nSnippet: {result.snippet or 'No snippet provided.'}"
            )
        return "\n\n".join(lines)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def _build_routing_prompt(
        self,
        *,
        user_content: str,
        guild: discord.Guild,
        author: Union[discord.Member, discord.User],
        mentions: List[MentionInfo],
        recent_messages: List[discord.Message],
        permissions: PermissionFlags,
    ) -> str:
        bot_id = self.bot.user.id if self.bot.user else None

        def _format_line(m: discord.Message) -> str:
            if bot_id and m.author.id == bot_id:
                label = "assistant"
            elif m.author.bot:
                label = "other_bot"
            else:
                label = "user"
            content = self._message_preview(m, limit=200)
            reply_tag = self._get_reply_context(m, bot_id, recent_messages) if bot_id else None
            reply_suffix = f" {reply_tag}" if reply_tag else ""
            return f"[{label}] {m.author} ({m.author.id}): {content}{reply_suffix}"

        history = "\n".join(
            _format_line(m) for m in recent_messages[-10:]
        ) or "None"
        mention_lines = "\n".join(
            f"- index={m.index} is_bot={m.is_bot} name={m.display_name} id={m.user_id}"
            for m in mentions
        ) or "None"
        perm_lines = "\n".join(
            f"- {k}: {v}" for k, v in sorted(permissions.to_dict().items())
        )
        context_channel_id = getattr(getattr(recent_messages[-1], "channel", None), "id", "Unknown") if recent_messages else "Unknown"
        bot_id_str = str(bot_id) if bot_id else "Unknown"
        return (
            f"Server: {guild.name} (ID: {guild.id}, Members: {guild.member_count or '?'})\n"
            f"Author: {author} (ID: {author.id})\n\n"
            f"Context Variables for API Endpoints:\n"
            f"- {{guild_id}}: {guild.id}\n"
            f"- {{channel_id}}: {context_channel_id}\n"
            f"- {{bot_id}}: {bot_id_str}\n"
            f"- Current Time: {_now().astimezone().isoformat()}\n\n"
            f"Permissions:\n{perm_lines}\n\n"
            f"Mentions (first is bot):\n{mention_lines}\n\n"
            f'Message: """{user_content}"""\n\n'
            "Recent messages format: [assistant/user/other_bot] author (id): content [optional reply-chain annotation]. "
            "Reply annotations show what message a user was responding to.\n"
            f"Recent messages:\n{history}"
        )

    async def choose_action(
        self,
        *,
        user_content: str,
        guild: discord.Guild,
        author: Union[discord.Member, discord.User],
        mentions: List[MentionInfo],
        recent_messages: List[discord.Message],
        permissions: PermissionFlags,
        model: Optional[str] = None,
    ) -> Decision:
        if not self.is_available:
            return Decision.error(self.availability_message())

        error = await self._preflight(author.id)
        if error:
            return Decision.error(error)

        prompt = self._build_routing_prompt(
            user_content=user_content,
            guild=guild,
            author=author,
            mentions=mentions,
            recent_messages=recent_messages,
            permissions=permissions,
        )
        messages = [
            {"role": "system", "content": ROUTING_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        try:
            await self._rate_limiter.record_call(author.id)
            # FIX: pass json_mode=True so the model is constrained to JSON output
            content = await self._call(
                messages,
                temperature=self.config.temperature_routing,
                max_tokens=self.config.max_tokens_routing,
                model=model,
                json_mode=True,
                session_key=f"{guild.id}:moderation",
                session_name=f"{guild.name} -> moderation",
            )
            if not content:
                return Decision.error("No response from AI model.")
            data = json.loads(self._extract_json(content))
            if not isinstance(data, dict):
                return Decision.error("AI returned unexpected format.")
            return Decision.from_dict(data)
        except json.JSONDecodeError:
            return Decision.error("AI returned invalid JSON.")
        except Exception:
            block_msg = self._get_block_message()
            if block_msg:
                return Decision.error(block_msg)
            logger.exception("Unexpected error in choose_action")
            return Decision.error("AI encountered an unexpected error.")

    async def converse(
        self,
        *,
        user_content: str,
        guild: discord.Guild,
        author: Union[discord.Member, discord.User],
        recent_messages: List[discord.Message],
        source_message: Optional[discord.Message] = None,
        model: Optional[str] = None,
        signals: Optional[ConversationSignals] = None,
        location_context: str = "",
    ) -> Optional[str]:
        if not self.is_available:
            return self.availability_message()

        error = await self._preflight(author.id)
        if error:
            return error

        signals = signals or ConversationSignals(
            mode=ConversationMode.STANDARD,
            confidence=0.0,
            show_research_indicator=False,
            asks_for_current_info=False,
            asks_for_sources=False,
            asks_for_long_answer=False,
            mentions_moderation=False,
        )

        # Research is intentionally isolated from prior conversations. Only
        # the current request and explicitly attached/replied media are sent.
        past_memory = ""
        is_continuation = False
        thread_context = "No recent messages"
        try:
            db = getattr(self.bot, "db", None)
            if db:
                past_memory = await db.get_ai_memory(author.id) or ""
        except Exception:
            pass
        is_continuation = self._is_conversation_continuation(
            author,
            recent_messages,
        )
        if signals.mode != ConversationMode.RESEARCH:
            thread_context = self._format_conversation_history(recent_messages)

        web_context = ""
        uses_native_search = (
            signals.mode == ConversationMode.RESEARCH
            and self.provider == "deepseek-web"
            and self._deepseek_web.enabled
        )
        if (
            signals.mode == ConversationMode.RESEARCH
            and not uses_native_search
            and self.has_web_search
        ):
            try:
                queries = await self._generate_search_queries(user_content, num_queries=3)
                seen_urls: Set[str] = set()
                results: List[WebSearchResult] = []
                for query in queries[:3]:
                    for result in await self._web_search(query, max_results=4):
                        if result.url in seen_urls:
                            continue
                        seen_urls.add(result.url)
                        results.append(result)
                    if len(results) >= 8:
                        break
                if results:
                    web_context = self._format_web_results(results[:8])
            except Exception:
                logger.warning("External web search failed", exc_info=True)

        plan = self._build_conversation_plan(
            signals=signals,
            user_content=user_content,
            guild=guild,
            author=author,
            past_memory=past_memory,
            thread_context=thread_context,
            is_continuation=is_continuation,
            location_context=location_context,
            web_context=web_context,
            uses_native_search=uses_native_search,
        )

        # --- Build message chain with multi-turn context ---
        is_image_question = _looks_like_image_question_text(user_content)
        image_context: List[ImageContext] = []
        if self.provider == "deepseek-web" or is_image_question:
            image_context = await self._collect_image_context(
                recent_messages,
                source_message=source_message,
            )
        if is_image_question and not image_context:
            return "I don't see an image attachment or embed in the replied/recent messages."
        prompt = f"{plan.system_prompt}\n\n### USER MESSAGE ###\n{plan.user_prompt}"

        try:
            await self._rate_limiter.record_call(author.id)
            if self.provider == "digitalocean":
                if image_context:
                    return "Image analysis is not enabled on this DigitalOcean text model."
                content = await self._call(
                    [
                        {"role": "system", "content": plan.system_prompt},
                        {"role": "user", "content": plan.user_prompt},
                    ],
                    temperature=self.config.temperature_chat,
                    max_tokens=self.config.max_tokens_chat,
                    model=model,
                )
            else:
                if not self._deepseek_web.enabled:
                    return "DeepSeek is not configured on this deployment."
                session_key, session_name = self._deepseek_session_identity(
                    guild,
                    source_message,
                    research=signals.mode == ConversationMode.RESEARCH,
                    vision=bool(image_context),
                )
                if image_context:
                    uploads = [
                        (image.filename, image.mime_type, image.data)
                        for image in image_context
                    ]
                    content = await self._deepseek_web.vision(
                        prompt,
                        uploads,
                        search=signals.mode == ConversationMode.RESEARCH,
                        session_key=session_key,
                        session_name=session_name,
                    )
                else:
                    content = await self._deepseek_web.chat(
                        prompt,
                        session_key=session_key,
                        session_name=session_name,
                        continue_session=is_continuation,
                        search=True,
                        long_answer=signals.asks_for_long_answer,
                        deepthink=uses_native_search,
                    )
            if not content:
                return None
            content = self._postprocess_chat_response(content)

            # Fire-and-forget memory update with summarization
            asyncio.create_task(
                self._update_memory_smart(author.id, user_content, content, past_memory)
            )
            return content
        except DeepSeekWebAuthError as exc:
            logger.warning("DeepSeek browser session needs renewal: %s", exc)
            return (
                "DeepSeek needs a human session renewal before I can answer. "
                "The saved login expired or an interactive verification appeared."
            )
        except DeepSeekWebError as exc:
            logger.warning("DeepSeek browser request failed: %s", exc)
            return "DeepSeek is temporarily unavailable. Try again shortly."
        except Exception:
            block_msg = self._get_block_message()
            if block_msg:
                return block_msg
            logger.exception("Unexpected error in AI conversation")
            return "The AI request failed unexpectedly. Try again shortly."

    @staticmethod
    def _deepseek_session_identity(
        guild: discord.Guild,
        source_message: Optional[discord.Message],
        *,
        research: bool = False,
        vision: bool = False,
    ) -> tuple[Optional[str], Optional[str]]:
        channel = getattr(source_message, "channel", None)
        channel_id = getattr(channel, "id", None)
        if channel_id is None:
            return None, None
        channel_name = getattr(channel, "name", None)
        channel_title = re.sub(r"[-_]+", " ", str(channel_name or "")).title()
        session_key = f"{guild.id}:{channel_id}"
        session_name = f"{guild.name} -> {channel_title or f'Channel {channel_id}'}"
        if vision:
            session_key += ":vision"
            session_name += " [Vision]"
        elif research:
            session_key += ":research"
            session_name += " [Research]"
        return session_key, session_name

    def _format_conversation_history(
        self, recent_messages: List[discord.Message]
    ) -> str:
        """Format recent messages into a clean multi-turn conversation history."""
        if not recent_messages:
            return "No recent messages"

        lines: List[str] = []
        bot_id = self.bot.user.id if self.bot.user else None
        def record_field(record: Any, name: str, default: Any = None) -> Any:
            if isinstance(record, dict):
                return record.get(name, default)
            return getattr(record, name, default)

        for m in recent_messages[-self.config.memory_window:]:
            if bot_id and m.author.id == bot_id:
                author_label = "assistant"
            elif m.author.bot:
                author_label = "other_bot"
            else:
                author_label = "user"
            name = getattr(m.author, "display_name", None) or str(m.author)
            content = (m.content or "").strip()

            # Handle attachments and embeds
            extras: List[str] = []
            if m.attachments:
                image_names = [
                    str(record_field(a, "filename", "image") or "image")
                    for a in m.attachments
                    if self._is_supported_image_attachment(a)
                ]
                if image_names:
                    extras.append(f"[image attachment(s): {', '.join(image_names[:3])}]")
                else:
                    extras.append(f"[{len(m.attachments)} attachment(s)]")
            if m.embeds:
                extras.append(f"[{len(m.embeds)} embed(s)]")
            if m.stickers:
                extras.append(f"[sticker: {m.stickers[0].name}]")
            for snapshot in getattr(m, "message_snapshots", []) or []:
                snapshot_attachments = record_field(snapshot, "attachments", []) or []
                snapshot_images = [
                    str(record_field(a, "filename", "image") or "image")
                    for a in snapshot_attachments
                    if self._is_supported_image_attachment(a)
                ]
                if snapshot_images:
                    extras.append(f"[forwarded image attachment(s): {', '.join(snapshot_images[:3])}]")
                    continue
                snapshot_embeds = record_field(snapshot, "embeds", []) or []
                if any(record_field(embed, "image") or record_field(embed, "thumbnail") for embed in snapshot_embeds):
                    extras.append("[forwarded embed image]")

            display = content[:2000]
            if extras:
                display = f"{display} {' '.join(extras)}".strip()
            if not display:
                display = " ".join(extras) if extras else "[empty message]"

            reply_context = self._get_reply_context(m, bot_id, recent_messages) if bot_id else None
            reply_prefix = f"{reply_context} " if reply_context else ""
            lines.append(f"[{author_label}] {name}: {reply_prefix}{display}")

        return "\n".join(lines)

    def _is_conversation_continuation(
        self,
        author: Union[discord.Member, discord.User],
        recent_messages: List[discord.Message],
    ) -> bool:
        """Detect if the user is continuing an active conversation with the bot."""
        if not recent_messages or len(recent_messages) < 2:
            return False

        # Check if one of the last 3 messages is from the bot replying to this user
        bot_id = self.bot.user.id if self.bot.user else None
        if not bot_id:
            return False

        current = recent_messages[-1]
        if current.author.id == author.id and self._is_reply_to_bot(current, bot_id, recent_messages):
            return True

        if not any(msg.author.id == bot_id for msg in recent_messages[-4:]):
            return False

        current_text = re.sub(r"<@!?\d+>", "", current.content or "").strip()
        if re.match(
            r"^(?:and\b|also\b|but\b|so\b|why\??$|how so\??$|what about\b|"
            r"what else\b|then what\b|wdym\b|huh\??$|yes\b|yeah\b|no\b|"
            r"is that\b|is it\b|should i do (?:that|it)\b|tell me more\b)",
            current_text,
            re.IGNORECASE,
        ):
            return True

        previous_human = next(
            (
                msg
                for msg in reversed(recent_messages[:-1])
                if not msg.author.bot and (msg.content or "").strip()
            ),
            None,
        )
        if previous_human is None:
            return False
        current_topics = self._conversation_topic_words(current_text)
        previous_topics = self._conversation_topic_words(previous_human.content or "")
        return bool(current_topics & previous_topics)

    @staticmethod
    def _conversation_topic_words(text: str) -> Set[str]:
        stopwords = {
            "about", "after", "again", "also", "and", "are", "can", "could",
            "did", "does", "for", "from", "game", "have", "how", "into", "is",
            "it", "like", "me", "my", "not", "of", "on", "or", "should", "that",
            "the", "their", "them", "then", "this", "to", "valid", "was", "what",
            "when", "where", "which", "who", "why", "with", "would", "you", "your",
        }
        clean = re.sub(r"<[@#][!&]?\d+>", " ", text.lower())
        words: Set[str] = set()
        for raw in re.findall(r"[a-z][a-z0-9']{2,}", clean):
            word = raw.strip("'")
            if word in stopwords:
                continue
            for suffix in ("ing", "ers", "er", "ed", "es", "s"):
                if word.endswith(suffix) and len(word) - len(suffix) >= 4:
                    word = word[: -len(suffix)]
                    break
            if word and word not in stopwords:
                words.add(word)
        return words

    def _build_conversation_messages(
        self,
        plan: "ConversationPlan",
        recent_messages: List[discord.Message],
        author: Union[discord.Member, discord.User],
        *,
        image_context: Optional[List[ImageContext]] = None,
        image_summary: str = "",
    ) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": plan.system_prompt},
        ]

        bot_id = self.bot.user.id if self.bot.user else None
        if bot_id and recent_messages:
            # Take last few exchanges (up to 9 turns, excluding the very last one which is the current message)
            recent_slice = recent_messages[-10:-1]
            for msg in recent_slice:
                content = (msg.content or "").strip()
                if not content or len(content) < 2:
                    continue
                    
                name = getattr(msg.author, "display_name", None) or str(msg.author)
                if msg.author.id == bot_id:
                    messages.append({"role": "assistant", "content": content[:2000]})
                elif msg.author.id == author.id:
                    # Detect if this user message is a reply to the bot's message
                    reply_context = self._get_reply_context(msg, bot_id, recent_messages)
                    if reply_context:
                        messages.append({"role": "user", "content": f"{reply_context}: {content[:2000]}"})
                    else:
                        messages.append({"role": "user", "content": content[:2000]})
                else:
                    # Inject other users' context as a user turn prefixed with their name
                    speaker = f"[other bot {name}]" if msg.author.bot else f"[{name}]"
                    reply_context = self._get_reply_context(msg, bot_id, recent_messages)
                    if reply_context:
                        messages.append({"role": "user", "content": f"{reply_context} {speaker}: {content[:2000]}"})
                    else:
                        messages.append({"role": "user", "content": f"{speaker}: {content[:2000]}"})

        user_prompt = plan.user_prompt
        # For the current (last) message, also detect reply context
        if recent_messages and bot_id:
            current_msg = recent_messages[-1]
            reply_context = self._get_reply_context(current_msg, bot_id, recent_messages)
            if reply_context and current_msg.author.id == author.id:
                user_prompt = f"{reply_context}: {user_prompt}"

        images = image_context or []
        if images:
            parts: List[Dict[str, Any]] = [
                {
                    "type": "text",
                    "text": (
                        "Recent Discord image attachments are included below. "
                        "Use the actual visual contents when answering image questions. "
                        "Do not guess from nearby text if the image shows otherwise.\n\n"
                        + "\n".join(
                            f"Image {i}: {image.label} ({image.filename})"
                            for i, image in enumerate(images, start=1)
                        )
                    ),
                }
            ]
            for image in images:
                parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": image.data_url, "detail": "auto"},
                    }
                )
            messages.append({"role": "user", "content": parts})

        if image_summary.strip():
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Visual analysis pass. Use this as the source of truth "
                        "for the image contents when answering the user's image question:\n"
                        f"{image_summary.strip()}"
                    ),
                }
            )

        messages.append({"role": "user", "content": user_prompt})
        return messages



    async def _collect_image_context(
        self,
        recent_messages: List[discord.Message],
        *,
        source_message: Optional[discord.Message] = None,
        max_images: int = 4,
        max_bytes_each: int = 6_000_000,
    ) -> List[ImageContext]:
        """Download recent Discord image attachments for multimodal model calls."""
        images: List[ImageContext] = []

        async def add_image(
            *,
            msg: discord.Message,
            filename: str,
            mime_type: str,
            data: bytes,
            label: Optional[str] = None,
        ) -> bool:
            if not data or len(data) > max_bytes_each:
                return False
            author_name = getattr(msg.author, "display_name", None) or str(msg.author)
            timestamp = msg.created_at.astimezone().strftime("%Y-%m-%d %H:%M")
            images.append(
                ImageContext(
                    label=label or f"from {author_name} at {timestamp}",
                    filename=filename or "image",
                    mime_type=mime_type,
                    data=data,
                )
            )
            return len(images) >= max_images

        async def read_image_url(url: str) -> Optional[bytes]:
            if not url:
                return None
            session, owned_session = self._get_http_session(timeout=20)
            try:
                async with session.get(url) as resp:
                    if resp.status >= 400:
                        return None
                    content_length = resp.headers.get("Content-Length")
                    if content_length:
                        try:
                            if int(content_length) > max_bytes_each:
                                return None
                        except ValueError:
                            pass
                    data = await resp.read()
                    if not data or len(data) > max_bytes_each:
                        return None
                    return data
            except Exception:
                logger.debug("Could not download Discord embed image %s", url, exc_info=True)
                return None
            finally:
                if owned_session:
                    await session.close()

        def field(obj: Any, name: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        async def read_attachment(attachment: Any) -> Optional[bytes]:
            filename = str(field(attachment, "filename", "image") or "image")
            read_method = field(attachment, "read")
            try:
                if callable(read_method):
                    return await read_method(use_cached=True)
            except Exception:
                logger.debug("Could not read Discord image attachment %s directly", filename, exc_info=True)

            for attr_name in ("url", "proxy_url"):
                url = str(field(attachment, attr_name, "") or "")
                if not url:
                    continue
                data = await read_image_url(url)
                if data:
                    return data
            return None

        def media_urls(media: Any) -> List[str]:
            urls: List[str] = []
            for attr_name in ("url", "proxy_url"):
                url = str(field(media, attr_name, "") or "")
                if url and url not in urls:
                    urls.append(url)
            return urls

        async def collect_from_record(
            msg: discord.Message,
            record: Any,
            *,
            label: Optional[str] = None,
        ) -> bool:
            for attachment in field(record, "attachments", []) or []:
                if len(images) >= max_images:
                    return True
                if not self._is_supported_image_attachment(attachment):
                    continue
                size = field(attachment, "size", 0) or 0
                filename = str(field(attachment, "filename", "image") or "image")
                if size and size > max_bytes_each:
                    logger.debug(
                        "Skipping large image attachment %s (%d bytes)",
                        filename,
                        size,
                    )
                    continue
                raw = await read_attachment(attachment)
                if not raw:
                    continue
                if await add_image(
                    msg=msg,
                    filename=filename,
                    mime_type=self._attachment_mime_type(attachment),
                    data=raw,
                    label=label,
                ):
                    return True

            for embed in field(record, "embeds", []) or []:
                if len(images) >= max_images:
                    return True
                for attr_name in ("image", "thumbnail"):
                    media = field(embed, attr_name)
                    for url in media_urls(media):
                        data = await read_image_url(url)
                        if not data:
                            continue
                        filename = url.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1] or f"{attr_name}.png"
                        mime_type = self._mime_type_from_url(url)
                        if await add_image(msg=msg, filename=filename, mime_type=mime_type, data=data, label=label):
                            return True
                        break
            return False

        async def collect_message(msg: discord.Message) -> bool:
            if await collect_from_record(msg, msg):
                return True
            author_name = getattr(msg.author, "display_name", None) or str(msg.author)
            timestamp = msg.created_at.astimezone().strftime("%Y-%m-%d %H:%M")
            for snapshot in getattr(msg, "message_snapshots", []) or []:
                if await collect_from_record(
                    msg,
                    snapshot,
                    label=f"forwarded image in message from {author_name} at {timestamp}",
                ):
                    return True
            return False

        if source_message is not None:
            if await collect_message(source_message):
                return images

            reference = getattr(source_message, "reference", None)
            if reference and getattr(reference, "message_id", None):
                replied_message = getattr(reference, "resolved", None)
                if not isinstance(replied_message, discord.Message):
                    fetch_message = getattr(source_message.channel, "fetch_message", None)
                    if callable(fetch_message):
                        try:
                            replied_message = await fetch_message(reference.message_id)
                        except (discord.HTTPException, discord.NotFound, discord.Forbidden):
                            replied_message = None
                if isinstance(replied_message, discord.Message):
                    await collect_message(replied_message)
            return images

        for msg in reversed(recent_messages[-10:]):
            if await collect_message(msg):
                return list(reversed(images))
        return list(reversed(images))

    @staticmethod
    def _is_supported_image_attachment(attachment: Any) -> bool:
        content_type = (
            attachment.get("content_type")
            if isinstance(attachment, dict)
            else getattr(attachment, "content_type", None)
        )
        filename = (
            attachment.get("filename")
            if isinstance(attachment, dict)
            else getattr(attachment, "filename", None)
        )
        content_type = str(content_type or "").lower()
        filename = str(filename or "").lower()
        if content_type in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
            return True
        return filename.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))

    @staticmethod
    def _attachment_mime_type(attachment: Any) -> str:
        content_type = (
            attachment.get("content_type")
            if isinstance(attachment, dict)
            else getattr(attachment, "content_type", None)
        )
        filename = (
            attachment.get("filename")
            if isinstance(attachment, dict)
            else getattr(attachment, "filename", None)
        )
        content_type = str(content_type or "").lower()
        if content_type in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
            return content_type
        filename = str(filename or "").lower()
        if filename.endswith(".png"):
            return "image/png"
        if filename.endswith(".webp"):
            return "image/webp"
        if filename.endswith(".gif"):
            return "image/gif"
        return "image/jpeg"

    @staticmethod
    def _mime_type_from_url(url: str) -> str:
        path = url.split("?", 1)[0].lower()
        if path.endswith(".png"):
            return "image/png"
        if path.endswith(".webp"):
            return "image/webp"
        if path.endswith(".gif"):
            return "image/gif"
        return "image/jpeg"

    def _get_reply_context(
        self,
        msg: discord.Message,
        bot_id: int,
        all_messages: List[discord.Message],
    ) -> Optional[str]:
        """Return compact reply-chain context for a message."""
        if not msg.reference or not msg.reference.message_id:
            return None

        ref_id = msg.reference.message_id
        ref = msg.reference.resolved
        if isinstance(ref, discord.Message) and ref.author.id == bot_id:
            ref_content = self._message_preview(ref, limit=1000)
            return f"[replying to your message: \"{ref_content}\"]"
        for m in all_messages:
            if m.id == ref_id and m.author.id == bot_id:
                ref_content = self._message_preview(m, limit=1000)
                return f"[replying to your message: \"{ref_content}\"]"
        if isinstance(ref, discord.Message):
            ref_name = getattr(ref.author, "display_name", None) or str(ref.author)
            ref_content = self._message_preview(ref, limit=1000)
            return f"[replying to {ref_name}: \"{ref_content}\"]"
        for m in all_messages:
            if m.id == ref_id:
                ref_name = getattr(m.author, "display_name", None) or str(m.author)
                ref_content = self._message_preview(m, limit=1000)
                return f"[replying to {ref_name}: \"{ref_content}\"]"
        return None

    def _is_reply_to_bot(
        self,
        msg: discord.Message,
        bot_id: int,
        all_messages: List[discord.Message],
    ) -> bool:
        if not msg.reference or not msg.reference.message_id:
            return False
        ref = msg.reference.resolved
        if isinstance(ref, discord.Message):
            return ref.author.id == bot_id
        ref_id = msg.reference.message_id
        return any(m.id == ref_id and m.author.id == bot_id for m in all_messages)

    @staticmethod
    def _message_preview(msg: discord.Message, *, limit: int) -> str:
        def record_field(record: Any, name: str, default: Any = None) -> Any:
            if isinstance(record, dict):
                return record.get(name, default)
            return getattr(record, name, default)

        text = re.sub(r"\s+", " ", (msg.content or "").strip())
        if not text:
            extras: List[str] = []
            if msg.attachments:
                image_names = [
                    a.filename
                    for a in msg.attachments
                    if GeminiClient._is_supported_image_attachment(a)
                ]
                if image_names:
                    extras.append(f"image attachment(s): {', '.join(image_names[:3])}")
                else:
                    extras.append(f"{len(msg.attachments)} attachment(s)")
            if msg.embeds:
                extras.append(f"{len(msg.embeds)} embed(s)")
            if msg.stickers:
                extras.append(f"sticker: {msg.stickers[0].name}")
            for snapshot in getattr(msg, "message_snapshots", []) or []:
                snapshot_attachments = record_field(snapshot, "attachments", []) or []
                snapshot_images = [
                    str(record_field(a, "filename", "image") or "image")
                    for a in snapshot_attachments
                    if GeminiClient._is_supported_image_attachment(a)
                ]
                if snapshot_images:
                    extras.append(f"forwarded image attachment(s): {', '.join(snapshot_images[:3])}")
                    continue
                snapshot_embeds = record_field(snapshot, "embeds", []) or []
                if any(record_field(embed, "image") or record_field(embed, "thumbnail") for embed in snapshot_embeds):
                    extras.append("forwarded embed image")
            text = ", ".join(extras) if extras else "non-text message"
        return text[:limit]

    def _build_conversation_plan(
        self,
        *,
        signals: ConversationSignals,
        user_content: str,
        guild: discord.Guild,
        author: Union[discord.Member, discord.User],
        past_memory: str,
        thread_context: str = "",
        is_continuation: bool = False,
        location_context: str = "",
        web_context: str = "",
        uses_native_search: bool = False,
    ) -> ConversationPlan:
        display_name = author.display_name if isinstance(author, discord.Member) else str(author)
        role_snippet = ""
        if isinstance(author, discord.Member):
            top = [r.name for r in author.roles[1:4]]
            if top:
                role_snippet = f" | Roles: {', '.join(top)}"

        # Build context header
        context_parts = [
            f"Server: {guild.name} ({guild.member_count or '?'} members)",
            f"Speaker: {display_name} (@{author.name}){role_snippet}",
            f"Time: {_now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}",
        ]
        if is_continuation:
            context_parts.append("Context: This is a continuation of an active conversation.")
        if location_context.strip():
            context_parts.append(f"Server location context: {location_context.strip()}")
        
        full_context = "### CURRENT STATE & CONTEXT ###\n"
        full_context += "\n".join(context_parts) + "\n\n"
        
        # Keep creator identity available in every mode without forcing unnatural replies.
        full_context += (
            "### CREATOR CONTEXT ###\n"
            "Cherry (user ID 1512848256789647560) created and owns Apflo. "
            "Treat Cherry warmly and respectfully, while staying natural and truthful. "
            "Do not insult or demean Cherry, but do not grovel, worship, or start arguments on their behalf.\n\n"
        )

        if thread_context and thread_context != "No recent messages":
            full_context += (
                "### CURRENT THREAD ###\n"
                "This is the immediate Discord conversation and short-term local knowledge. "
                "Use it to resolve vague follow-ups, replies, and questions about things already mentioned here. "
                "For example, if the thread says a dinner, event, class, game, or meeting has a time/place/name, use that detail directly.\n"
                f"{thread_context}\n\n"
            )

        if web_context:
            full_context += f"### WEB SEARCH RESULTS ###\n{web_context}\n\n"
        elif uses_native_search:
            full_context += "### LIVE SEARCH ###\nDeepSeek web search is enabled for this request. Use current search results and include source URLs when available.\n\n"
        
        # Memory section
        if past_memory.strip():
            # Trim to last meaningful chunk
            trimmed = past_memory.strip()
            if len(trimmed) > 4000:
                trimmed = trimmed[-4000:]
                # Don't start mid-entry
                first_bracket = trimmed.find("\n[")
                if first_bracket > 0:
                    trimmed = trimmed[first_bracket:]
            full_context += f"What you remember about this user:\n{trimmed}\n\n"

        # --- RESEARCH MODE ---
        if signals.mode == ConversationMode.RESEARCH:
            sys_prompt = ""
            if not is_continuation:
                sys_prompt = f"{DEEP_RESEARCH_SYSTEM_PROMPT}\n\n"
            sys_prompt += f"{full_context}"
            if not is_continuation:
                sys_prompt += "Instructions:\n"
                if web_context:
                    sys_prompt += (
                        "- Answer using the WEB SEARCH RESULTS above.\n"
                        "- Cite result numbers like [1] next to factual claims from search.\n"
                        "- If the search results do not support a claim, say the search results do not confirm it.\n"
                    )
                elif uses_native_search:
                    sys_prompt += (
                        "- Use DeepSeek's live web search before answering.\n"
                        "- Include plain source URLs only when available. Do not output raw citation tokens.\n"
                        "- If native search does not verify a claim, say it was not confirmed.\n"
                    )
                sys_prompt += "- Provide a brief, direct answer.\n- If there are key points, use a short bulleted list. Do not use markdown tables.\n- Keep it extremely concise.\n"
                if signals.asks_for_current_info:
                    sys_prompt += (
                        "- The user is asking for current/latest information. Use only the web search results for current claims.\n"
                    )
                if signals.asks_for_sources:
                    sys_prompt += "- The user asked for sources. Include the result numbers and URLs where useful.\n"
                if signals.asks_for_long_answer:
                    sys_prompt += "- Provide a slightly more detailed answer, but STILL limit to 250-500 words.\n"
                if signals.focus_entities:
                    sys_prompt += f"- Focus on these entities: {', '.join(signals.focus_entities)}\n"

            return ConversationPlan(
                system_prompt=sys_prompt,
                user_prompt=user_content,
                temperature=0.35,
                max_tokens=max(self.config.max_tokens_chat, 2048),
                show_research_indicator=signals.show_research_indicator,
            )

        # --- MOD GUIDANCE MODE ---
        if signals.mode == ConversationMode.MOD_GUIDANCE:
            bot_mention = self.bot.user.mention if self.bot.user else "@bot"
            sys_prompt = ""
            if not is_continuation:
                sys_prompt = f"{MOD_GUIDANCE_SYSTEM_PROMPT}\n\n"
            sys_prompt += f"{full_context}"
            sys_prompt += "Provide practical moderation guidance.\n"
            sys_prompt += f"Use `{bot_mention}` in command examples so they can copy-paste.\n"
            sys_prompt += "If the user is missing info (target, reason, duration), ask ONE question.\n"
            
            return ConversationPlan(
                system_prompt=sys_prompt,
                user_prompt=user_content,
                temperature=0.5,
                max_tokens=self.config.max_tokens_chat,
                show_research_indicator=False,
            )

        # --- STANDARD CONVERSATION ---
        task_instruction = (
            "Reply naturally for this Discord conversation. Lead with the answer and keep it concise. "
            "Do not use canned acknowledgements or summarize what you are about to do."
        )
        if is_continuation:
            task_instruction += (
                " This continues an active conversation. "
                "Pick up naturally from where you left off - don't re-introduce yourself."
            )

        if self._is_local_context_question(user_content):
            task_instruction += (
                " The user is asking for a detail that may already be in the current thread. "
                "Check CURRENT THREAD first and answer from it. If it is not there, say you don't see that detail."
            )

        task_instruction += (
            " Do not use long dash characters to separate clauses. Use normal punctuation instead. "
            "Hyphens inside compound words are fine."
        )

        sys_prompt = ""
        if not is_continuation:
            sys_prompt = f"{CONVERSATION_SYSTEM_PROMPT}\n\n"
        sys_prompt += f"{full_context}### INSTRUCTIONS ###\n{task_instruction}"
        
        return ConversationPlan(
            system_prompt=sys_prompt,
            user_prompt=user_content,
            temperature=self.config.temperature_chat,
            max_tokens=self.config.max_tokens_chat,
            show_research_indicator=False,
        )

    @staticmethod
    def _postprocess_chat_response(content: str) -> str:
        """Normalize assistant chat output so Discord replies stay clean and readable."""
        text = (content or "").strip()
        if not text:
            return ""

        # Strip wrapping code fences the model sometimes adds
        text = re.sub(r"^```(?:\w+)?\s*", "", text).strip()
        text = re.sub(r"\s*```$", "", text).strip()

        # Collapse excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = GeminiClient._strip_citation_tokens(text)
        text = GeminiClient._convert_simple_markdown_table(text)
        text = GeminiClient._strip_consumer_app_footers(text)

        # The user requested to stop using long dash separators and use commas instead.
        text = text.replace(" \u2014 ", ", ").replace("\u2014", ", ")
        text = text.replace(" \u2013 ", ", ").replace("\u2013", ", ")
        text = text.replace(" -- ", ", ").replace("--", ", ")

        # Strip meta-commentary the model sometimes prepends
        meta_patterns = [
            r"^(?:Sure(?:,|!)?\s*)?(?:Here(?:'s| is)?\s*)?(?:my )?(?:response|answer|reply)\s*[:!]\s*\n*",
            r"^(?:Of course(?:,|!)?\s*)",
            r"^(?:Absolutely(?:,|!)?\s*)",
            r"^(?:What (?:a )?great question(?:!|\.|,)?\s*)",
            r"^(?:Great question(?:!|\.|,)?\s*)",
        ]
        for pattern in meta_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

        # Strip trailing "Let me know if..." type endings
        trailing_patterns = [
            r"\n+(?:Let me know|Feel free to ask|Hope (?:this|that) helps|Don't hesitate).*$",
        ]
        for pattern in trailing_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

        # If the model wrapped the entire response in quotes, unwrap
        if text.startswith('"') and text.endswith('"') and text.count('"') == 2:
            text = text[1:-1].strip()

        return text

    @staticmethod
    def _strip_consumer_app_footers(content: str) -> str:
        """Remove Gemini/Google consumer-app enablement footers from API replies."""
        text = content or ""
        patterns = (
            r"(?:^|\n)\s*(?:By the way,\s*)?to unlock the full functionality of all apps,?\s*enable\s+Gemini Apps Activity\.?\s*$",
            r"(?:^|\n)\s*(?:By the way,\s*)?(?:please\s+)?enable\s+Gemini Apps Activity\b.*$",
            r"(?:^|\n)\s*(?:By the way,\s*)?.*\bGemini Apps Activity\b.*$",
            r"(?:^|\n)\s*(?:By the way,\s*)?.*\bGoogle Apps Activity\b.*$",
            r"(?:^|\n)\s*(?:By the way,\s*)?.*\bGoogle app activity\b.*$",
        )
        for pattern in patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE).strip()
        return text

    @staticmethod
    def _is_local_context_question(content: str) -> bool:
        low = (content or "").strip().lower()
        if not low:
            return False
        if re.search(r"\b(what|when|where|who|which)\b", low) and re.search(
            r"\b(time|date|day|place|location|channel|room|event|dinner|meeting|class|game|party|plan|thing|it|that|this)\b",
            low,
        ):
            return True
        return bool(re.search(r"\b(what time|when is|where is|who is|what is (?:it|that|this|the))\b", low))

    @staticmethod
    def _strip_citation_tokens(text: str) -> str:
        text = re.sub(r"\s*\[citation:\d+\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*\[source:\d+\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+([,.;:])", r"\1", text)
        return text

    @staticmethod
    def _convert_simple_markdown_table(text: str) -> str:
        lines = text.splitlines()
        output: List[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if (
                line.strip().startswith("|")
                and i + 1 < len(lines)
                and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[i + 1])
            ):
                headers = [cell.strip() for cell in line.strip().strip("|").split("|")]
                i += 2
                bullets: List[str] = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    cells = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                    if len(cells) >= 2:
                        label = cells[0].strip("* ")
                        detail = " | ".join(cells[1:]).strip()
                        bullets.append(f"- **{label}:** {detail}")
                    i += 1
                if bullets:
                    if headers and headers[0]:
                        output.append(f"**{headers[0]}**")
                    output.extend(bullets)
                    continue
            output.append(line)
            i += 1
        return "\n".join(output)

    async def _update_memory_smart(
        self, user_id: int, user_msg: str, bot_response: str, past_memory: str
    ) -> None:
        """Update per-user conversation memory with smart truncation.

        Keeps the most recent exchanges and trims at entry boundaries
        to avoid cutting mid-thought.
        """
        try:
            db = getattr(self.bot, "db", None)
            if not db:
                return

            # Build new entry
            user_snippet = user_msg[:1000].strip()
            bot_snippet = bot_response[:1000].strip()
            entry = f"\n[user]: {user_snippet}\n[bot]: {bot_snippet}"

            new_memory = (past_memory + entry).strip()

            # Smart truncation: keep within limit but don't break mid-entry
            max_chars = self.config.memory_max_chars
            if len(new_memory) > max_chars:
                # Find the first complete entry boundary after the cutoff point
                cutoff = len(new_memory) - max_chars
                # Search for the next "\n[user]:" or "\n[bot]:" after cutoff
                next_entry = new_memory.find("\n[user]:", cutoff)
                if next_entry == -1:
                    next_entry = new_memory.find("\n[bot]:", cutoff)
                if next_entry > 0:
                    new_memory = new_memory[next_entry:].strip()
                else:
                    new_memory = new_memory[-max_chars:]

            await db.update_ai_memory(user_id, new_memory)
        except Exception:
            logger.debug("Failed to update AI memory for user %d", user_id, exc_info=True)

    # Keep old method name as alias for compatibility
    async def _update_memory(
        self, user_id: int, user_msg: str, bot_response: str, past_memory: str
    ) -> None:
        await self._update_memory_smart(user_id, user_msg, bot_response, past_memory)


# =============================================================================
# TOOL HANDLERS
# =============================================================================


@ToolRegistry.register(ToolType.WARN, display_name="Warn Member", color=discord.Color.gold(), emoji="Warning", required_permission="moderate_members")
async def handle_warn(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Could not resolve target member.")
    if not ctx.cog.can_moderate(ctx.actor, target):
        return ToolResult.fail(f"Cannot moderate {target.display_name} (role hierarchy).")

    reason = ctx.str_arg("reason")
    db = getattr(ctx.cog.bot, "db", None)
    if db:
        try:
            await db.add_warning(
                guild_id=ctx.guild.id, user_id=target.id,
                moderator_id=ctx.actor.id, reason=reason,
            )
        except Exception:
            logger.exception("Failed to record warning")
            return ToolResult.fail("Database error while recording warning.")

    embed = action_embed(
        title="Warning Member Warned", color=discord.Color.gold(),
        actor=ctx.actor, target=target, reason=reason,
    )
    await ctx.cog.log_action(
        message=ctx.message, action="warn_member",
        actor=ctx.actor, target=target, reason=reason, decision=ctx.decision,
    )
    return ToolResult.ok("Warning issued.", embed=embed)


@ToolRegistry.register(
    ToolType.GET_WARNINGS,
    display_name="Get Warnings",
    color=discord.Color.blue(),
    emoji="Warnings",
    required_permission="moderate_members",
)
async def handle_get_warnings(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Could not resolve target member.")
    
    db = getattr(ctx.cog.bot, "db", None)
    if not db:
        return ToolResult.fail("Database not available.")
        
    try:
        warnings = await db.get_warnings(ctx.guild.id, target.id)
    except Exception:
        logger.exception("Failed to fetch warnings")
        return ToolResult.fail("Database error while fetching warnings.")
        
    if not warnings:
        embed = discord.Embed(
            title=f"⚠️ Warnings for {target.display_name}",
            description=f"{target.mention} has no warnings.",
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        return ToolResult.ok(
            f"{target.display_name} has no warnings.",
            embed=embed,
            use_v2=False,
        )

    embed = discord.Embed(
        title=f"⚠️ Warnings for {target.display_name}",
        description=f"Total: **{len(warnings)}** warning(s)",
        color=Colors.WARNING,
        timestamp=_now(),
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    for warning in warnings[:10]:
        moderator_id = warning.get("moderator_id")
        moderator = ctx.guild.get_member(moderator_id) if moderator_id else None
        moderator_name = moderator.display_name if moderator else f"ID: {moderator_id or 'Unknown'}"
        reason = str(warning.get("reason") or "No reason provided")[:100]
        created_at = str(warning.get("created_at") or "Unknown time")
        embed.add_field(
            name=f"Warning #{warning.get('id', '?')}",
            value=f"**Reason:** {reason}\n**By:** {moderator_name}\n**When:** {created_at}",
            inline=False,
        )
    if len(warnings) > 10:
        embed.set_footer(text=f"Showing 10 of {len(warnings)} warnings")
    return ToolResult.ok(
        f"Found {len(warnings)} warning(s).",
        embed=embed,
        use_v2=False,
    )


@ToolRegistry.register(ToolType.TIMEOUT, display_name="Timeout Member", color=discord.Color.orange(), emoji="Muted", required_permission="moderate_members")
async def handle_timeout(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Could not resolve target member.")
    if not ctx.cog.can_moderate(ctx.actor, target):
        return ToolResult.fail(f"Cannot moderate {target.display_name} (role hierarchy).")

    raw_seconds = ctx.int_arg("seconds", ctx.cog.config.timeout_default_seconds)
    seconds = max(1, min(raw_seconds, ctx.cog.config.timeout_max_seconds))
    reason = ctx.str_arg("reason")

    await target.timeout(timedelta(seconds=seconds), reason=reason)

    minutes = seconds // 60
    embed = action_embed(
        title="Muted Member Timed Out", color=discord.Color.orange(),
        actor=ctx.actor, target=target, reason=reason,
        extra={"Duration": f"{minutes} minute(s)"},
    )
    await ctx.cog.log_action(
        message=ctx.message, action="timeout_member",
        actor=ctx.actor, target=target, reason=reason, decision=ctx.decision,
        extra={"Duration": f"{minutes} minute(s)"},
    )
    return ToolResult.ok("Timeout applied.", embed=embed)


@ToolRegistry.register(ToolType.UNTIMEOUT, display_name="Remove Timeout", color=discord.Color.green(), emoji="Unmuted", required_permission="moderate_members")
async def handle_untimeout(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Could not resolve target member.")

    reason = ctx.str_arg("reason", "Timeout removed.")
    await target.timeout(None, reason=reason)

    embed = action_embed(
        title="Unmuted Timeout Removed", color=discord.Color.green(),
        actor=ctx.actor, target=target, reason=reason,
    )
    await ctx.cog.log_action(
        message=ctx.message, action="untimeout_member",
        actor=ctx.actor, target=target, reason=reason, decision=ctx.decision,
    )
    return ToolResult.ok("Timeout removed.", embed=embed)


@ToolRegistry.register(ToolType.KICK, display_name="Kick Member", color=discord.Color.red(), emoji="Kick", required_permission="kick_members")
async def handle_kick(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Could not resolve target member.")
    if not ctx.cog.can_moderate(ctx.actor, target):
        return ToolResult.fail(f"Cannot kick {target.display_name} (role hierarchy).")

    reason = ctx.str_arg("reason")
    await target.kick(reason=f"AI Mod ({ctx.actor}): {reason}")

    embed = action_embed(
        title="Kick Member Kicked", color=discord.Color.red(),
        actor=ctx.actor, target=target, reason=reason,
    )
    await ctx.cog.log_action(
        message=ctx.message, action="kick_member",
        actor=ctx.actor, target=target, reason=reason, decision=ctx.decision,
    )
    return ToolResult.ok("Member kicked.", embed=embed)


@ToolRegistry.register(ToolType.BAN, display_name="Ban Member", color=discord.Color.dark_red(), emoji="Ban", required_permission="ban_members")
async def handle_ban(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Could not resolve target member.")
    if not ctx.cog.can_moderate(ctx.actor, target):
        return ToolResult.fail(f"Cannot ban {target.display_name} (role hierarchy).")

    reason = ctx.str_arg("reason")
    delete_days = max(0, min(ctx.int_arg("delete_message_days", 0), 7))
    await target.ban(reason=f"AI Mod ({ctx.actor}): {reason}", delete_message_days=delete_days)

    embed = action_embed(
        title="Ban Member Banned", color=discord.Color.dark_red(),
        actor=ctx.actor, target=target, reason=reason,
        extra={"Messages Deleted": f"{delete_days} day(s)"} if delete_days else None,
    )
    await ctx.cog.log_action(
        message=ctx.message, action="ban_member",
        actor=ctx.actor, target=target, reason=reason, decision=ctx.decision,
        extra={"Delete Messages": f"{delete_days} day(s)"},
    )
    return ToolResult.ok("Member banned.", embed=embed)


@ToolRegistry.register(ToolType.UNBAN, display_name="Unban Member", color=discord.Color.green(), emoji="Done", required_permission="ban_members")
async def handle_unban(ctx: ToolContext) -> ToolResult:
    raw_id = ctx.args.get("target_user_id")
    try:
        target_id = int(raw_id)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ToolResult.fail("Invalid user ID for unban.")

    reason = ctx.str_arg("reason", "Unbanned.")
    await ctx.guild.unban(discord.Object(id=target_id), reason=f"AI Mod ({ctx.actor}): {reason}")

    embed = discord.Embed(title="User Unbanned", color=discord.Color.green(), timestamp=_now())
    rows: list[tuple[str, object]] = [
        ("Moderator", ctx.actor.mention),
        ("Reason", reason),
    ]
    embed.set_footer(text=f"User ID: {target_id}")
    try:
        user = await ctx.cog.bot.fetch_user(target_id)
        embed.set_author(name=user.name, icon_url=user.display_avatar.url)
        rows.insert(0, ("User", f"{user.mention} (`{user.name}`)"))
        embed.set_thumbnail(url=user.display_avatar.url)
    except discord.HTTPException:
        rows.insert(0, ("User", f"<@{target_id}> (ID: `{target_id}`)"))
    embed.description = compact_kv_lines(rows)

    await ctx.cog.log_action(
        message=ctx.message, action="unban_member",
        actor=ctx.actor, target=None, reason=reason, decision=ctx.decision,
        extra={"User ID": str(target_id)},
    )
    return ToolResult.ok("User unbanned.", embed=embed)


# -- Role Management ----------------------------------------------------------


@ToolRegistry.register(ToolType.ADD_ROLE, display_name="Add Role", color=discord.Color.green(), emoji="+", required_permission="manage_roles")
async def handle_add_role(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Target user not found.")

    role = await ctx.resolve_role()
    if not role:
        return ToolResult.fail(f"Role `{ctx.arg('role_name')}` not found.")

    if not ctx.cog.can_manage_role(ctx.actor, role):
        return ToolResult.fail(f"Cannot assign `{role.name}` - it's above your top role.")
    bot_member = ctx.guild.me
    if not bot_member or not ctx.cog.can_manage_role(bot_member, role):
        return ToolResult.fail(f"Cannot assign `{role.name}` - it's above my top role.")

    reason = ctx.str_arg("reason")
    await target.add_roles(role, reason=f"AI Mod ({ctx.actor}): {reason}")

    embed = discord.Embed(description=f"Added {role.mention} to {target.mention}", color=discord.Color.green())
    return ToolResult.ok("Role added.", embed=embed)


@ToolRegistry.register(ToolType.REMOVE_ROLE, display_name="Remove Role", color=discord.Color.orange(), emoji="-", required_permission="manage_roles")
async def handle_remove_role(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Target user not found.")

    role = await ctx.resolve_role()
    if not role:
        return ToolResult.fail(f"Role `{ctx.arg('role_name')}` not found.")

    if not ctx.cog.can_manage_role(ctx.actor, role):
        return ToolResult.fail(f"Cannot remove `{role.name}` - it's above your top role.")
    bot_member = ctx.guild.me
    if not bot_member or not ctx.cog.can_manage_role(bot_member, role):
        return ToolResult.fail(f"Cannot remove `{role.name}` - it's above my top role.")

    reason = ctx.str_arg("reason")
    await target.remove_roles(role, reason=f"AI Mod ({ctx.actor}): {reason}")

    embed = discord.Embed(description=f"Removed {role.mention} from {target.mention}", color=discord.Color.orange())
    return ToolResult.ok("Role removed.", embed=embed)


@ToolRegistry.register(ToolType.CREATE_ROLE, display_name="Create Role", color=discord.Color.blue(), emoji="*", required_permission="manage_roles")
async def handle_create_role(ctx: ToolContext) -> ToolResult:
    name = ctx.arg("name")
    if not name:
        return ToolResult.fail("Role name is required.")

    color = _parse_hex_color(ctx.arg("color_hex"))
    hoist = ctx.bool_arg("hoist")
    reason = ctx.str_arg("reason")

    role = await ctx.guild.create_role(
        name=name, color=color, hoist=hoist,
        reason=f"AI Mod ({ctx.actor}): {reason}",
    )
    embed = discord.Embed(description=f"Created role {role.mention}", color=color)
    return ToolResult.ok("Role created.", embed=embed)


@ToolRegistry.register(ToolType.DELETE_ROLE, display_name="Delete Role", color=discord.Color.red(), emoji="Delete", required_permission="manage_roles")
async def handle_delete_role(ctx: ToolContext) -> ToolResult:
    role = await ctx.resolve_role()
    if not role:
        return ToolResult.fail(f"Role `{ctx.arg('role_name')}` not found.")
    if not ctx.cog.can_manage_role(ctx.actor, role):
        return ToolResult.fail("That role is above you in the hierarchy.")
    bot_member = ctx.guild.me
    if not bot_member or not ctx.cog.can_manage_role(bot_member, role):
        return ToolResult.fail("That role is above me in the hierarchy.")

    await role.delete(reason=f"AI Mod ({ctx.actor}): {ctx.str_arg('reason')}")
    embed = discord.Embed(description=f"Deleted role **{role.name}**", color=discord.Color.red())
    return ToolResult.ok("Role deleted.", embed=embed)


@ToolRegistry.register(ToolType.EDIT_ROLE, display_name="Edit Role", color=discord.Color.blue(), emoji="Edit", required_permission="manage_roles")
async def handle_edit_role(ctx: ToolContext) -> ToolResult:
    role = await ctx.resolve_role()
    if not role:
        return ToolResult.fail(f"Role `{ctx.arg('role_name')}` not found.")
    if not ctx.cog.can_manage_role(ctx.actor, role):
        return ToolResult.fail("That role is above you in the hierarchy.")
    bot_member = ctx.guild.me
    if not bot_member or not ctx.cog.can_manage_role(bot_member, role):
        return ToolResult.fail("That role is above me in the hierarchy.")

    kwargs: Dict[str, Any] = {}
    if "new_name" in ctx.args:
        kwargs["name"] = ctx.args["new_name"]
    if "new_color" in ctx.args:
        kwargs["color"] = _parse_hex_color(ctx.args["new_color"])

    if not kwargs:
        return ToolResult.fail("Nothing to edit - provide new_name and/or new_color.")

    await role.edit(**kwargs, reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok(f"Role **{role.name}** updated.")


# -- Channel Management -------------------------------------------------------


@ToolRegistry.register(ToolType.CREATE_CHANNEL, display_name="Create Channel", color=discord.Color.green(), emoji="Channel", required_permission="manage_channels")
async def handle_create_channel(ctx: ToolContext) -> ToolResult:
    name = ctx.arg("name")
    if not name:
        return ToolResult.fail("What should the channel be called? Example: `make a channel called staff-chat`.")

    c_type = str(ctx.arg("type", "text")).lower()
    category: Optional[discord.CategoryChannel] = None
    if cat_name := ctx.arg("category"):
        category = discord.utils.find(
            lambda c: c.name.lower() == str(cat_name).lower(),
            ctx.guild.categories,
        )

    reason = f"AI Mod ({ctx.actor}): {ctx.str_arg('reason')}"

    if "voice" in c_type:
        ch = await ctx.guild.create_voice_channel(name, category=category, reason=reason)
    elif "stage" in c_type:
        ch = await ctx.guild.create_stage_channel(name, category=category, reason=reason)
    elif "forum" in c_type:
        ch = await ctx.guild.create_forum_channel(name, category=category, reason=reason)
    else:
        ch = await ctx.guild.create_text_channel(name, category=category, reason=reason)

    embed = discord.Embed(description=f"Created {ch.mention}", color=discord.Color.green())
    return ToolResult.ok("Channel created.", embed=embed)


@ToolRegistry.register(ToolType.DELETE_CHANNEL, display_name="Delete Channel", color=discord.Color.red(), emoji="Delete", required_permission="manage_channels")
async def handle_delete_channel(ctx: ToolContext) -> ToolResult:
    query = str(ctx.arg("channel_name", "")).strip()
    if not query:
        return ToolResult.fail("Channel name or ID is required.")

    channel: Optional[discord.abc.GuildChannel] = None
    if query.isdigit():
        channel = ctx.guild.get_channel(int(query))
    if not channel:
        channel = discord.utils.find(lambda c: c.name.lower() == query.lower(), ctx.guild.channels)
    if not channel:
        return ToolResult.fail(f"Channel `{query}` not found.")

    name = channel.name
    await channel.delete(reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok(f"Channel `{name}` deleted.")


@ToolRegistry.register(ToolType.EDIT_CHANNEL, display_name="Edit Channel", color=discord.Color.blue(), emoji="Edit", required_permission="manage_channels")
async def handle_edit_channel(ctx: ToolContext) -> ToolResult:
    channel: discord.abc.GuildChannel = ctx.message.channel  # type: ignore[assignment]
    if channel_name := ctx.arg("channel_name"):
        q = str(channel_name).strip()
        found = (ctx.guild.get_channel(int(q)) if q.isdigit()
                 else discord.utils.find(lambda c: c.name.lower() == q.lower(), ctx.guild.channels))
        if found:
            channel = found

    if not isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.ForumChannel)):
        return ToolResult.fail("Cannot edit that type of channel.")

    kwargs: Dict[str, Any] = {}
    if "new_name" in ctx.args:
        kwargs["name"] = ctx.args["new_name"]
    if "topic" in ctx.args and isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
        kwargs["topic"] = ctx.args["topic"]
    if "nsfw" in ctx.args:
        kwargs["nsfw"] = ctx.bool_arg("nsfw")
    if "slowmode" in ctx.args:
        try:
            kwargs["slowmode_delay"] = max(0, min(int(ctx.args["slowmode"]), 21600))
        except (TypeError, ValueError):
            return ToolResult.fail("Invalid slowmode value - must be 0-21600 seconds.")
    if isinstance(channel, discord.VoiceChannel):
        if "bitrate" in ctx.args:
            try:
                kwargs["bitrate"] = int(ctx.args["bitrate"])
            except (TypeError, ValueError):
                return ToolResult.fail("Invalid bitrate.")
        if "user_limit" in ctx.args:
            try:
                kwargs["user_limit"] = max(0, min(int(ctx.args["user_limit"]), 99))
            except (TypeError, ValueError):
                return ToolResult.fail("Invalid user_limit.")

    if not kwargs:
        return ToolResult.fail("Nothing to edit.")

    await channel.edit(**kwargs, reason=f"AI Mod ({ctx.actor})")
    changes = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    return ToolResult.ok(f"Channel updated: `{changes}`.")


@ToolRegistry.register(ToolType.LOCK_CHANNEL, display_name="Lock Channel", color=discord.Color.orange(), emoji="Locked", required_permission="manage_channels")
async def handle_lock_channel(ctx: ToolContext) -> ToolResult:
    channel = ctx.message.channel
    if not hasattr(channel, "set_permissions"):
        return ToolResult.fail("Cannot lock this channel type.")
    await channel.set_permissions(  # type: ignore[union-attr]
        ctx.guild.default_role, send_messages=False,
        reason=f"Lock by {ctx.actor}",
    )
    return ToolResult.ok("Channel locked.")


@ToolRegistry.register(ToolType.UNLOCK_CHANNEL, display_name="Unlock Channel", color=discord.Color.green(), emoji="Unlocked", required_permission="manage_channels")
async def handle_unlock_channel(ctx: ToolContext) -> ToolResult:
    channel = ctx.message.channel
    if not hasattr(channel, "set_permissions"):
        return ToolResult.fail("Cannot unlock this channel type.")
    await channel.set_permissions(  # type: ignore[union-attr]
        ctx.guild.default_role, send_messages=True,
        reason=f"Unlock by {ctx.actor}",
    )
    return ToolResult.ok("Channel unlocked.")


# -- Member Admin -------------------------------------------------------------


@ToolRegistry.register(ToolType.SET_NICKNAME, display_name="Set Nickname", color=discord.Color.blue(), emoji="Nick", required_permission="manage_nicknames")
async def handle_set_nickname(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Target not found.")
    if not ctx.cog.can_moderate(ctx.actor, target):
        return ToolResult.fail("Target's role is above yours.")
    bot_member = ctx.guild.me
    if not bot_member or not ctx.cog.can_moderate(bot_member, target):
        return ToolResult.fail("Target's role is above mine.")

    new_nick: Optional[str] = ctx.arg("nickname")
    if new_nick and len(new_nick) > 32:
        return ToolResult.fail("Nickname too long (max 32 characters).")

    await target.edit(nick=new_nick, reason=f"AI Mod ({ctx.actor})")
    msg = f"Nickname set to `{new_nick}`." if new_nick else "Nickname reset."
    return ToolResult.ok(msg)


# -- Voice --------------------------------------------------------------------


@ToolRegistry.register(ToolType.MOVE_MEMBER, display_name="Move Member", color=discord.Color.purple(), emoji="Move", required_permission="move_members")
async def handle_move_member(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Target not found.")
    if not target.voice:
        return ToolResult.fail(f"{target.display_name} is not in a voice channel.")

    q = str(ctx.arg("channel_name", "")).strip()
    if not q:
        return ToolResult.fail("Voice channel name or ID is required.")

    vc: Optional[discord.VoiceChannel] = None
    if q.isdigit():
        ch = ctx.guild.get_channel(int(q))
        if isinstance(ch, discord.VoiceChannel):
            vc = ch
    if not vc:
        vc = discord.utils.find(
            lambda c: isinstance(c, discord.VoiceChannel) and c.name.lower() == q.lower(),
            ctx.guild.voice_channels,
        )
    if not vc:
        return ToolResult.fail(f"Voice channel `{q}` not found.")

    await target.move_to(vc, reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok(f"Moved {target.display_name} to **{vc.name}**.")


@ToolRegistry.register(ToolType.DISCONNECT_MEMBER, display_name="Disconnect Member", color=discord.Color.dark_grey(), emoji="Disconnect", required_permission="move_members")
async def handle_disconnect_member(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Target not found.")
    if not target.voice:
        return ToolResult.fail(f"{target.display_name} is not in a voice channel.")

    await target.move_to(None, reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok(f"Disconnected **{target.display_name}** from voice.")


@ToolRegistry.register(ToolType.DM_USER, display_name="DM User", color=discord.Color.green(), emoji="DM")
async def handle_dm_user(ctx: ToolContext) -> ToolResult:
    is_owner = await ctx.cog.bot.is_owner(ctx.actor)
    is_admin = isinstance(ctx.actor, discord.Member) and ctx.actor.guild_permissions.administrator
    can_manage = isinstance(ctx.actor, discord.Member) and ctx.actor.guild_permissions.manage_messages
    if not (is_owner or is_admin or can_manage):
        return ToolResult.fail("You need Manage Messages to DM users through the bot.")

    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Target user not found.")
    if target.bot:
        return ToolResult.fail("I won't DM another bot.")

    dm_text = str(ctx.arg("message", "")).strip()
    if not dm_text:
        return ToolResult.fail("What should I DM them?")
    if len(dm_text) > 1900:
        return ToolResult.fail("That DM is too long. Keep it under 1900 characters.")

    try:
        await target.send(dm_text)
    except discord.Forbidden:
        return ToolResult.fail(f"I couldn't DM {target.mention}; their DMs are closed or they blocked the bot.")
    except discord.HTTPException as exc:
        return ToolResult.fail(f"Discord rejected the DM ({exc.status}).")

    await ctx.cog.log_action(
        message=ctx.message,
        action="dm_user",
        actor=ctx.actor,
        target=target,
        reason="AI Moderation DM",
        decision=ctx.decision,
        extra={"Message": dm_text[:900]},
    )
    return ToolResult.ok(f"Done! Sent a DM to {target.mention}.")


# -- Server & Assets ----------------------------------------------------------


@ToolRegistry.register(ToolType.EDIT_GUILD, display_name="Edit Server", color=discord.Color.gold(), emoji="Server", required_permission="manage_guild")
async def handle_edit_guild(ctx: ToolContext) -> ToolResult:
    kwargs: Dict[str, Any] = {}
    if "name" in ctx.args:
        kwargs["name"] = ctx.args["name"]
    if not kwargs:
        return ToolResult.fail("Nothing to edit.")
    await ctx.guild.edit(**kwargs, reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok("Server settings updated.")


@ToolRegistry.register(ToolType.CREATE_EMOJI, display_name="Create Emoji", color=discord.Color.green(), emoji="Emoji", required_permission="manage_emojis")
async def handle_create_emoji(ctx: ToolContext) -> ToolResult:
    name = ctx.arg("name")
    url = ctx.arg("url")
    if not name or not url:
        return ToolResult.fail("Both emoji name and image URL are required.")

    session: Optional[aiohttp.ClientSession] = getattr(ctx.cog.bot, "session", None)
    owned_session = False
    if not session or getattr(session, "closed", False):
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))
        owned_session = True

    try:
        async with session.get(str(url)) as resp:
            if resp.status != 200:
                return ToolResult.fail(f"Failed to download image (HTTP {resp.status}).")
            data = await resp.read()
        emoji = await ctx.guild.create_custom_emoji(name=str(name), image=data, reason=f"AI Mod ({ctx.actor})")
        embed = discord.Embed(description=f"Created emoji {emoji}", color=discord.Color.green())
        return ToolResult.ok("Emoji created.", embed=embed)
    finally:
        if owned_session:
            await session.close()


@ToolRegistry.register(ToolType.DELETE_EMOJI, display_name="Delete Emoji", color=discord.Color.red(), emoji="Delete", required_permission="manage_emojis")
async def handle_delete_emoji(ctx: ToolContext) -> ToolResult:
    name = ctx.arg("name")
    if not name:
        return ToolResult.fail("Emoji name is required.")
    emoji = discord.utils.find(lambda e: e.name.lower() == str(name).lower(), ctx.guild.emojis)
    if not emoji:
        return ToolResult.fail(f"Emoji `{name}` not found.")
    await emoji.delete(reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok(f"Emoji `{name}` deleted.")


@ToolRegistry.register(ToolType.CREATE_INVITE, display_name="Create Invite", color=discord.Color.green(), emoji="Invite", required_permission="create_instant_invite")
async def handle_create_invite(ctx: ToolContext) -> ToolResult:
    max_age = max(0, min(ctx.int_arg("max_age", 86400), 604800))
    create_invite = getattr(ctx.message.channel, "create_invite", None)
    if not callable(create_invite):
        return ToolResult.fail("I can't create an invite from this channel type.")
    invite = await create_invite(max_age=max_age, reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok(f"Invite created: {invite.url}")


@ToolRegistry.register(ToolType.PIN_MESSAGE, display_name="Pin Message", color=discord.Color.red(), emoji="Pin", required_permission="manage_messages")
async def handle_pin_message(ctx: ToolContext) -> ToolResult:
    msg_id = ctx.arg("message_id")
    if not msg_id:
        return ToolResult.fail("Message ID is required.")
    fetch_message = getattr(ctx.message.channel, "fetch_message", None)
    if not callable(fetch_message):
        return ToolResult.fail("I can't fetch messages in this channel type.")
    msg = await fetch_message(int(msg_id))
    await msg.pin(reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok("Message pinned.")


@ToolRegistry.register(ToolType.UNPIN_MESSAGE, display_name="Unpin Message", color=discord.Color.orange(), emoji="Unpin", required_permission="manage_messages")
async def handle_unpin_message(ctx: ToolContext) -> ToolResult:
    msg_id = ctx.arg("message_id")
    if not msg_id:
        return ToolResult.fail("Message ID is required - reply to the message or provide its ID.")
    fetch_message = getattr(ctx.message.channel, "fetch_message", None)
    if not callable(fetch_message):
        return ToolResult.fail("I can't fetch messages in this channel type.")
    msg = await fetch_message(int(msg_id))
    await msg.unpin(reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok("Message unpinned.")


@ToolRegistry.register(ToolType.LOCK_THREAD, display_name="Lock Thread", color=discord.Color.orange(), emoji="Locked", required_permission="manage_threads")
async def handle_lock_thread(ctx: ToolContext) -> ToolResult:
    thread: Optional[discord.Thread] = None
    if isinstance(ctx.message.channel, discord.Thread):
        thread = ctx.message.channel
    elif (hint := ctx.arg("thread_id")):
        try:
            thread = ctx.guild.get_thread(int(hint))
        except (TypeError, ValueError):
            pass

    if not thread:
        return ToolResult.fail("No target thread found. Run this in a thread, or provide a thread ID.")

    await thread.edit(locked=True, archived=True, reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok(f"Thread **{thread.name}** locked.")


@ToolRegistry.register(ToolType.PURGE, display_name="Purge Messages", color=discord.Color.blue(), emoji="Delete", required_permission="manage_messages")
async def handle_purge(ctx: ToolContext) -> ToolResult:
    channel = ctx.message.channel
    raw_channel_id = ctx.arg("channel_id")
    if raw_channel_id:
        try:
            resolved_channel = ctx.guild.get_channel(int(raw_channel_id))
        except (TypeError, ValueError):
            resolved_channel = None
        if resolved_channel is None:
            return ToolResult.fail("I couldn't find that channel.")
        channel = resolved_channel

    if not isinstance(channel, discord.TextChannel):
        return ToolResult.fail("Purge only works in text channels.")

    if ctx.arg("needs_channel_scope"):
        return ToolResult.ok(
            f"Did you mean in {ctx.message.channel.mention}, or in all channels? "
            "Mention the channel to use, or say `in this channel`."
        )

    bot_member = ctx.guild.me
    all_channels_requested = ctx.bool_arg("all_channels_requested")
    if bot_member and not all_channels_requested:
        bot_perms = channel.permissions_for(bot_member)
        if not bot_perms.manage_messages or not bot_perms.read_message_history:
            return ToolResult.fail(f"I need Manage Messages and Read Message History in {channel.mention}.")

    amount = max(1, min(ctx.int_arg("amount", 10), 500))
    reason = ctx.str_arg("reason", "AI Moderation purge")
    target_user_id = ctx.arg("target_user_id")
    try:
        target_user_id = int(target_user_id) if target_user_id else None
    except (TypeError, ValueError):
        target_user_id = None

    lookback_seconds = ctx.arg("lookback_seconds")
    try:
        lookback_seconds = int(lookback_seconds) if lookback_seconds else None
    except (TypeError, ValueError):
        lookback_seconds = None
    if lookback_seconds is not None:
        lookback_seconds = max(1, min(lookback_seconds, 14 * 24 * 60 * 60))

    if all_channels_requested and target_user_id is None:
        return ToolResult.ok("Tell me whose messages to delete when using all channels.")

    logging_cog = ctx.cog.bot.get_cog("Logging")
    if logging_cog and not all_channels_requested:
        logging_cog.suppress_message_delete_log(channel.id)
        logging_cog.suppress_bulk_delete_log(channel.id)

    cutoff = _now() - timedelta(seconds=lookback_seconds) if lookback_seconds else None

    def message_matches(candidate: discord.Message) -> bool:
        if candidate.id == ctx.message.id:
            return False
        if target_user_id is not None and candidate.author.id != target_user_id:
            return False
        if cutoff and candidate.created_at < cutoff:
            return False
        return True

    deleted_messages: List[discord.Message] = []
    deleted_by_channel: Dict[int, int] = {}

    async def purge_one_channel(target_channel: discord.TextChannel, remaining: int) -> List[discord.Message]:
        matched_count = 0

        def should_delete(candidate: discord.Message) -> bool:
            nonlocal matched_count
            if not message_matches(candidate):
                return False
            if matched_count >= remaining:
                return False
            matched_count += 1
            return True

        if logging_cog:
            logging_cog.suppress_message_delete_log(target_channel.id)
            logging_cog.suppress_bulk_delete_log(target_channel.id)
        purge_limit = remaining + 1 if target_user_id is None and lookback_seconds is None else max(5000, remaining * 5)
        return await target_channel.purge(limit=purge_limit, check=should_delete)

    if all_channels_requested:
        for target_channel in ctx.guild.text_channels:
            if len(deleted_messages) >= amount:
                break
            if bot_member:
                bot_perms = target_channel.permissions_for(bot_member)
                if not bot_perms.manage_messages or not bot_perms.read_message_history:
                    continue
            remaining = amount - len(deleted_messages)
            try:
                deleted = await purge_one_channel(target_channel, remaining)
            except (discord.Forbidden, discord.HTTPException):
                logger.debug("Skipping channel during all-channel purge: %s", target_channel.id, exc_info=True)
                continue
            deleted_clean = [m for m in deleted if m.id != ctx.message.id]
            if deleted_clean:
                deleted_messages.extend(deleted_clean)
                deleted_by_channel[target_channel.id] = deleted_by_channel.get(target_channel.id, 0) + len(deleted_clean)
        deleted_count = len(deleted_messages)
    else:
        deleted = await purge_one_channel(channel, amount)
        deleted_messages = [m for m in deleted if m.id != ctx.message.id]
        deleted_count = len(deleted_messages)

    if all_channels_requested:
        channel_label = f"{len(deleted_by_channel)} channel{'s' if len(deleted_by_channel) != 1 else ''}"
    else:
        channel_label = channel.mention

    # Keep transcript logs channel-specific. A cross-channel transcript would be
    # misleading because the existing transcript template represents one channel.
    if all_channels_requested:
        await ctx.cog.log_action(
            message=ctx.message, action="purge_messages",
            actor=ctx.actor, target=None, reason=reason, decision=ctx.decision,
            extra={"Count": str(deleted_count), "Scope": "All channels"},
        )
        target_text = f" of <@{target_user_id}>" if target_user_id is not None else ""
        if deleted_count == 0:
            return ToolResult.ok(f"I didn't find any messages{target_text} in any channel.")
        plural = "message" if deleted_count == 1 else "messages"
        cap_note = " I stopped at the 500-message limit." if deleted_count >= amount and amount >= 500 else ""
        return ToolResult.ok(
            f"Done! All {deleted_count} {plural}{target_text} across {channel_label} have been deleted.{cap_note}"
        )

    if deleted_count > 0 and logging_cog:
        try:
            bot_count = sum(1 for m in deleted_messages if m.author.bot)
            unique_authors = {m.author for m in deleted_messages if not m.author.bot}
            preview_lines: List[str] = []
            for msg in reversed(deleted_messages):
                raw = (msg.content or "").strip()
                if not raw:
                    if msg.attachments:
                        raw = f"[{len(msg.attachments)} attachment(s)]"
                    elif msg.embeds:
                        raw = "[embed]"
                    else:
                        continue
                raw = " ".join(raw.split())
                if len(raw) > 80:
                    raw = raw[:77].rstrip() + "..."
                author_name = getattr(msg.author, "display_name", None) or getattr(msg.author, "name", "unknown")
                preview_lines.append(f"`{author_name}`: {raw}")
                if len(preview_lines) >= 8:
                    break
            preview_text = "\n".join(preview_lines) if preview_lines else "*No text content available*"

            # FIX: generate_html_transcript may return bytes or BytesIO - handle both
            transcript_raw = generate_html_transcript(
                ctx.guild, channel, [], purged_messages=deleted_messages
            )
            if isinstance(transcript_raw, (bytes, bytearray)):
                transcript_bytes: io.BytesIO = io.BytesIO(transcript_raw)
            elif isinstance(transcript_raw, io.BytesIO):
                transcript_bytes = transcript_raw
            else:
                transcript_bytes = io.BytesIO(str(transcript_raw).encode("utf-8"))

            transcript_name = f"purge-{ctx.guild.id}-{int(_now().timestamp())}.html"

            log_channel = await logging_cog.get_log_channel(ctx.guild, "message")
            if log_channel:
                log_embed = discord.Embed(
                    title="Bulk Message Delete",
                    description=f"**{deleted_count}** message(s) purged in {channel.mention}",
                    color=discord.Color.red(),
                    timestamp=_now(),
                )
                log_embed.description = "\n".join(
                    filter(
                        None,
                        [
                            log_embed.description or "",
                            compact_kv_lines(
                                [
                                    ("Moderator", f"{ctx.actor.mention} (`{ctx.actor.id}`)"),
                                    ("Human Messages", deleted_count - bot_count),
                                    ("Bot Messages", bot_count),
                                    ("Unique Authors", len(unique_authors)),
                                ]
                            ),
                        ],
                    )
                )
                log_embed.add_field(name="Purged Message Preview", value=preview_text[:1024], inline=False)

                transcript_bytes.seek(0)
                view = EphemeralTranscriptView(io.BytesIO(transcript_bytes.read()), filename=transcript_name)
                await logging_cog.safe_send_log(log_channel, log_embed, view=view)

            mod_log_channel = await logging_cog.get_log_channel(ctx.guild, "mod")
            if mod_log_channel:
                mod_embed = discord.Embed(
                    title="Moderator Purge",
                    description=f"{ctx.actor.mention} purged **{deleted_count}** message(s) in {channel.mention}.",
                    color=discord.Color.red(),
                    timestamp=_now(),
                )
                mod_embed.description = "\n".join(
                    filter(
                        None,
                        [
                            mod_embed.description or "",
                            compact_kv_lines(
                                [
                                    ("Moderator", f"{ctx.actor.mention} (`{ctx.actor.id}`)"),
                                    ("Reason", reason),
                                    ("Human Messages", deleted_count - bot_count),
                                    ("Bot Messages", bot_count),
                                    ("Unique Authors", len(unique_authors)),
                                ]
                            ),
                        ],
                    )
                )

                transcript_bytes.seek(0)
                mod_view = EphemeralTranscriptView(io.BytesIO(transcript_bytes.read()), filename=transcript_name)
                await logging_cog.safe_send_log(mod_log_channel, mod_embed, view=mod_view)
        except Exception:
            logger.debug("Failed to post purge transcript", exc_info=True)

    await ctx.cog.log_action(
        message=ctx.message, action="purge_messages",
        actor=ctx.actor, target=None, reason=reason, decision=ctx.decision,
        extra={"Count": str(deleted_count)},
    )
    target_text = f" of <@{target_user_id}>" if target_user_id is not None else ""
    window_text = ""
    if lookback_seconds is not None:
        if lookback_seconds % 86400 == 0:
            unit_amount = lookback_seconds // 86400
            window_text = f" from the last {unit_amount} day{'s' if unit_amount != 1 else ''}"
        elif lookback_seconds % 3600 == 0:
            unit_amount = lookback_seconds // 3600
            window_text = f" from the last {unit_amount} hour{'s' if unit_amount != 1 else ''}"
        elif lookback_seconds % 60 == 0:
            unit_amount = lookback_seconds // 60
            window_text = f" from the last {unit_amount} minute{'s' if unit_amount != 1 else ''}"
        else:
            window_text = f" from the last {lookback_seconds} seconds"

    if deleted_count == 0:
        return ToolResult.ok(f"I didn't find any messages{target_text}{window_text} in {channel.mention}.")

    plural = "message" if deleted_count == 1 else "messages"
    cap_note = " I stopped at the 500-message limit." if deleted_count >= amount and amount >= 500 else ""
    if target_user_id is not None and not cap_note:
        return ToolResult.ok(
            f"Done! All {deleted_count} {plural}{target_text}{window_text} in {channel.mention} "
            f"have been deleted.{cap_note}"
        )
    return ToolResult.ok(
        f"Done! Deleted {deleted_count} {plural}{target_text}{window_text} in {channel.mention}.{cap_note}"
    )


@ToolRegistry.register(ToolType.HELP, display_name="Show Help", color=discord.Color.blurple(), emoji="?")
async def handle_help(ctx: ToolContext) -> ToolResult:
    embed = ctx.cog.build_help_embed(ctx.guild)
    return ToolResult.ok("Help displayed.", embed=embed)


@ToolRegistry.register(ToolType.EXECUTE_RAW_API, display_name="Execute Raw API", color=discord.Color.blurple(), emoji="API")
async def handle_execute_raw_api(ctx: ToolContext) -> ToolResult:
    method = str(ctx.arg("method", "")).strip().upper()
    endpoint = str(ctx.arg("endpoint", "")).strip()
    raw_payload = ctx.arg("payload", {})
    payload: Dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}

    safety_error = _raw_api_safety_error(ctx, method, endpoint, payload)
    if safety_error:
        return ToolResult.fail(safety_error)
    payload = _normalize_scheduled_event_payload(endpoint, method, payload)

    route = discord.http.Route(method, endpoint)
    kwargs: Dict[str, Any] = {"reason": f"AI raw API ({ctx.actor})"}
    if method in {"POST", "PATCH", "PUT"}:
        kwargs["json"] = payload

    result = await ctx.cog.bot.http.request(route, **kwargs)

    preview = "No response body."
    if result is not None:
        try:
            preview = json.dumps(result, ensure_ascii=True)
        except TypeError:
            preview = str(result)
        if len(preview) > 900:
            preview = preview[:897] + "..."

    embed = discord.Embed(
        title="Raw Discord API Executed",
        color=discord.Color.blurple(),
        timestamp=_now(),
    )
    embed.add_field(name="Method", value=method, inline=True)
    embed.add_field(name="Endpoint", value=f"`{endpoint[:250]}`", inline=False)
    embed.add_field(name="Response", value=f"```json\n{preview}\n```", inline=False)
    return ToolResult.ok("Raw Discord API request executed.", embed=embed)



@ToolRegistry.register(ToolType.EXECUTE_PYTHON, display_name="Execute Python", color=discord.Color.red(), emoji="Python")
async def handle_execute_python(ctx: ToolContext) -> ToolResult:
    """Execute AI-generated Python code and log details to automod."""
    import csv
    import datetime
    import os as _os
    import traceback as _tb

    _TIMEOUT: int = 60
    _MAX_PREVIEW: int = 900
    _MAX_CODE_DISPLAY: int = 1000

    is_owner = await ctx.cog.bot.is_owner(ctx.actor)
    is_admin = isinstance(ctx.actor, discord.Member) and ctx.actor.guild_permissions.administrator
    if not is_owner and not is_admin:
        return ToolResult.fail("Execute Python is restricted to administrators.")

    code = _strip_code_fences(str(ctx.arg("code", "")))
    if not code:
        return ToolResult.fail("No Python code provided.")

    real_channel = ctx.message.channel if ctx.message else None
    env: Dict[str, Any] = {
        "bot": ctx.cog.bot,
        "guild": ctx.guild,
        "author": ctx.actor,
        "message": ctx.message,
        "channel": real_channel,
        "discord": __import__("discord"),
        "asyncio": __import__("asyncio"),
        "csv": csv,
        "datetime": datetime,
        "io": io,
        "json": json,
        "os": _os,
        "random": random,
        "re": re,
        "fetch_recent_activity": _make_activity_fetcher(ctx.guild),
    }

    wrapped = _wrap_async(code)
    try:
        compiled = compile(wrapped, "<ai_exec>", "exec")
    except SyntaxError as exc:
        return ToolResult.fail(f"Syntax error (line {exc.lineno}): {exc.msg}")

    try:
        exec(compiled, env)
        raw_result = await asyncio.wait_for(env["__ai_exec_func"](), timeout=_TIMEOUT)
    except asyncio.TimeoutError:
        return ToolResult.fail(
            f"Execution timed out after {_TIMEOUT}s. Try a smaller scope or break into steps."
        )
    except Exception as exc:
        tb_lines = _tb.format_exception(type(exc), exc, exc.__traceback__)
        short = "".join(tb_lines[-5:])
        if len(short) > _MAX_PREVIEW:
            short = short[:_MAX_PREVIEW - 3] + "..."
        return ToolResult.fail(f"Python execution failed:\n```\n{short}\n```")

    preview = str(raw_result) if raw_result is not None else "Execution completed successfully (no return value)."
    if len(preview) > _MAX_PREVIEW:
        preview = preview[:_MAX_PREVIEW - 3] + "..."

    log_embed = discord.Embed(
        title="Python Code Executed",
        color=discord.Color.green(),
        timestamp=_now(),
    )
    log_embed.add_field(name="Code", value=f"```py\n{code[:_MAX_CODE_DISPLAY]}\n```", inline=False)
    log_embed.add_field(name="Result", value=f"```\n{preview}\n```", inline=False)
    log_embed.add_field(name="Actor", value=f"{ctx.actor.mention} (`{ctx.actor.id}`)", inline=True)

    await _log_execution(ctx, preview, log_embed)
    return ToolResult.ok("Done! I put the execution details in automod logs.")


# execute_python helpers

def _strip_code_fences(raw: str) -> str:
    """Remove markdown code fences and surrounding whitespace."""
    code = raw.strip()
    for prefix in ("```python", "```py", "```"):
        if code.startswith(prefix):
            code = code[len(prefix):]
            break
    if code.endswith("```"):
        code = code[:-3]
    return code.strip()


def _wrap_async(code: str) -> str:
    """Wrap raw code inside an async function body."""
    lines = code.splitlines()
    indented = "\n".join(f"    {line}" for line in lines)
    return f"async def __ai_exec_func():\n{indented}\n"


def _make_activity_fetcher(guild: discord.Guild) -> Callable:
    """Build the fetch_recent_activity helper for generated code."""
    import datetime as _dt

    async def fetch_recent_activity(days: int = 7) -> Dict[int, Any]:
        now = _dt.datetime.now(_dt.timezone.utc)
        cutoff = now - _dt.timedelta(days=max(1, min(days, 30)))
        activity: Dict[int, Any] = {}

        # Run channel scans concurrently for speed on large servers
        async def _scan(ch: discord.TextChannel) -> None:
            try:
                async for msg in ch.history(limit=50, after=cutoff):
                    prev = activity.get(msg.author.id)
                    if prev is None or msg.created_at > prev:
                        activity[msg.author.id] = msg.created_at
            except (discord.Forbidden, discord.HTTPException):
                pass

        # Process in batches of 10 to avoid rate limits
        channels = guild.text_channels
        for i in range(0, len(channels), 10):
            batch = channels[i:i + 10]
            await asyncio.gather(*[_scan(ch) for ch in batch])

        return activity

    return fetch_recent_activity


async def _log_execution(
    ctx: ToolContext, preview: str, log_embed: discord.Embed
) -> None:
    """Send execution details to the automod audit log."""
    await ctx.cog.log_action(
        message=ctx.message,
        action="execute_python",
        actor=ctx.actor,
        target=None,
        reason=ctx.decision.reason or "AI Python execution",
        decision=ctx.decision,
        extra={"Result": preview[:900]},
        view=None,
    )
    logging_cog = ctx.cog.bot.get_cog("Logging")
    if not logging_cog:
        return
    try:
        log_channel = await logging_cog.get_log_channel(ctx.guild, "automod")
        if log_channel:
            await logging_cog.safe_send_log(log_channel, log_embed)
    except Exception:
        logger.debug("Failed to send Python execution details to automod log", exc_info=True)

# =============================================================================
# MAIN COG
# =============================================================================

def _strip_code_fences(raw: str) -> str:
    """Remove ```python``` markers from AI-generated code."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    return cleaned.strip()


def _contains_forbidden_raw_api_key(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    low = value.lower()
    for token_like in ("discord.com/api", "bot ", "mfa.", "oauth2", "token"):
        if token_like in low:
            return True
    if re.search(r"[a-zA-Z0-9_-]{23,}\.{1,3}[a-zA-Z0-9_-]{6,}", low):
        return True
    return False


def _raw_api_safety_error(
    ctx: Any, method: str, endpoint: str, payload: Any
) -> Optional[str]:
    if re.search(r"(delete|destroy|remove)", method, re.IGNORECASE) and re.search(
        r"/(guilds/\d+|channels/\d+|roles/\d+|webhooks/\d+)", endpoint
    ):
        return None
    return None


def _normalize_scheduled_event_payload(
    endpoint: str, method: str, payload: Any
) -> Dict[str, Any]:
    if not isinstance(payload, dict) or "create" not in endpoint.lower():
        return payload if isinstance(payload, dict) else {}
    p = dict(payload)
    p.setdefault("privacy_level", 2)
    p.setdefault("entity_type", 3)
    return p
