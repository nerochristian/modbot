"""HTTP transport for the AI moderation client.

This is the lane-agnostic wire layer: it owns the OpenAI-compatible
chat-completions POST (with retry/backoff and auth-failure blocking), the
response parsers for both JSON and SSE bodies, OpenRouter citation extraction,
and message normalization for text-only routes.

Extracted from ai_client.py to separate "how we talk HTTP" from "which lane
and model to use" (providers) and "what a conversation turn means" (converse).

Implemented as a mixin rather than a standalone client because these are called
as ``self._post_chat_completion(...)`` throughout the provider lanes and are
mocked as AIClient attributes in the test-suite; keeping the method surface
identical preserves both.

Requires from the composing class:
  - ``self.bot``           for the shared aiohttp session
  - ``self._set_block``    to trip the service block on auth failure
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger("ModBot.AIModeration.Client")


def _exception_summary(exc: BaseException) -> str:
    """Return a useful one-line label even for message-less timeout errors."""
    detail = str(exc).strip()
    return detail if detail else type(exc).__name__


class TransportMixin:
    """OpenAI-compatible HTTP transport shared by every lane."""

    async def _post_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool = False,
        allow_multimodal: bool = False,
        provider_label: str,
        chat_path: str = "/chat/completions",
        max_retries: int = 2,
        request_timeout: int = 60,
        extra_payload: Optional[Dict[str, Any]] = None,
        include_citations: bool = False,
        allow_service_block: bool = True,
    ) -> Optional[str]:
        """Shared OpenAI-compatible chat-completions POST with bounded retries.

        Used by every OpenRouter lane. Retries only
        transient failures (network errors, 5xx, 429); auth/4xx fail fast.

        ``allow_service_block`` controls whether a 401/403/429 here may trip the
        CLIENT-WIDE service block, which ``_preflight`` then returns instead of
        answering anyone. Only lanes that actually serve the user's reply may do
        that. Pass False from optional and background lanes: each pins its own
        model, so its quota says nothing about whether the talking lane works,
        and a rate-limited 2-second route classifier must not silence every
        conversation in every guild for a minute.
        """
        request_messages = messages if allow_multimodal else self._normalize_text_messages(messages)
        if not request_messages:
            raise RuntimeError(f"{provider_label} request has no message content.")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": request_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if extra_payload:
            payload.update(extra_payload)

        last_error: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            session, owned_session = self._get_http_session(timeout=request_timeout)
            try:
                async with session.post(
                    f"{base_url}{chat_path}",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as resp:
                    raw_body = await resp.text()
                    try:
                        data = json.loads(raw_body)
                    except json.JSONDecodeError:
                        data = None
                    if resp.status >= 400:
                        detail = data.get("error", data) if isinstance(data, dict) else raw_body[:500]
                        if resp.status in {401, 403}:
                            if allow_service_block:
                                self._set_block(seconds=900, reason=f"{provider_label} authentication or access failed.")
                            raise RuntimeError(f"{provider_label} HTTP {resp.status}: {str(detail)[:500]}")
                        if resp.status == 429 and allow_service_block:
                            self._set_block(seconds=60, reason=f"{provider_label} rate limit or quota reached.")
                        # 429 and 5xx are transient — fall through to retry.
                        if resp.status < 500 and resp.status != 429:
                            raise RuntimeError(f"{provider_label} HTTP {resp.status}: {str(detail)[:500]}")
                        last_error = RuntimeError(f"{provider_label} HTTP {resp.status}: {str(detail)[:500]}")
                    else:
                        if isinstance(data, dict):
                            content = self._extract_completion_content(data)
                            if not (content or "").strip():
                                # A reasoning model can spend the whole output
                                # budget on hidden reasoning and return empty
                                # content with finish_reason="length". Name that
                                # explicitly: the old generic "no assistant
                                # content" error made it look like an outage.
                                self._log_empty_completion(data, provider_label)
                            if content and include_citations:
                                urls = self._extract_openrouter_citation_urls(data)
                                if urls:
                                    sources = "\n".join(f"- {url}" for url in urls)
                                    content = f"{content}\n\n__BOT_SOURCES__\n{sources}"
                            return content
                        return self._extract_sse_completion_content(raw_body)
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = exc
                logger.warning(
                    "%s network error (attempt %d/%d): %s",
                    provider_label,
                    attempt + 1,
                    max_retries + 1,
                    _exception_summary(exc),
                )
            finally:
                if owned_session:
                    await session.close()

            if attempt < max_retries:
                await asyncio.sleep(0.5 * (2 ** attempt))

        if last_error:
            raise last_error
        return None

    @staticmethod
    def _extract_sse_completion_content(raw_body: str) -> Optional[str]:
        """Extract assistant text from OpenAI-compatible SSE chunks."""
        chunks: List[str] = []
        for line in (raw_body or "").splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            choices = data.get("choices") if isinstance(data, dict) else None
            if not choices:
                continue
            delta = (choices[0] or {}).get("delta") or {}
            content = delta.get("content")
            if isinstance(content, str):
                chunks.append(content)
        return "".join(chunks).strip() or None

    @staticmethod
    def _log_empty_completion(data: Any, provider_label: str) -> None:
        """Explain an empty assistant reply, which is usually budget exhaustion."""
        try:
            choice = ((data.get("choices") or [{}])[0]) or {}
            finish = choice.get("finish_reason") or choice.get("native_finish_reason")
            usage = data.get("usage") or {}
            reasoning_tokens = (
                (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
            )
            if finish == "length":
                logger.warning(
                    "%s returned an EMPTY reply truncated at the output limit "
                    "(completion_tokens=%s, reasoning_tokens=%s). The model spent "
                    "the whole max_tokens budget before emitting text; raise "
                    "AI_MAX_TOKENS_CHAT or disable reasoning for this model.",
                    provider_label,
                    usage.get("completion_tokens"),
                    reasoning_tokens,
                )
            else:
                logger.warning(
                    "%s returned an empty reply (finish_reason=%s, usage=%s).",
                    provider_label,
                    finish,
                    usage or "unknown",
                )
        except Exception:  # never let diagnostics break the request path
            logger.debug("Failed to diagnose empty completion", exc_info=True)

    @classmethod
    def _extract_completion_content(cls, data: Any) -> Optional[str]:
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
            # `_stringify_web_content` lives on this very mixin (see below), and
            # `_extract_sse_completion_content` already calls it as `cls.`.
            # Qualifying it as `AIClient.` raised NameError -- AIClient is not
            # imported here -- and the call site only catches ClientError /
            # TimeoutError, so any provider returning list-shaped content (the
            # normal shape for citation-annotated replies) killed the request.
            return cls._stringify_web_content(content)
        return None

    @staticmethod
    def _extract_openrouter_citation_urls(data: Any) -> List[str]:
        """Extract ordered URL citations from an OpenRouter assistant message."""
        if not isinstance(data, dict):
            return []
        choices = data.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            return []
        message = choices[0].get("message") or {}
        urls: List[str] = []

        def visit(node: Any) -> None:
            if isinstance(node, dict):
                if str(node.get("type") or "").lower() == "url_citation":
                    citation = node.get("url_citation")
                    if not isinstance(citation, dict):
                        citation = node
                    url = str(citation.get("url") or "").strip()
                    if url.startswith(("https://", "http://")) and url not in urls:
                        urls.append(url)
                for value in node.values():
                    visit(value)
            elif isinstance(node, list):
                for value in node:
                    visit(value)

        visit(message.get("annotations") or [])
        if isinstance(message.get("content"), list):
            visit(message["content"])
        return urls

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
