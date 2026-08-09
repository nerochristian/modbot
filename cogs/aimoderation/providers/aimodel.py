"""AiModel lane: the Responses API, not chat-completions.

AiModel is the one gateway here that speaks OpenAI's *Responses* API, so it
needs its own request builder (``_responses_input``), its own content extractor,
and its own model-namespacing rule (``accounts/aimodel/models/...``). Keeping it
separate from the chat-completions transport is what stops those quirks leaking
into every other lane.

Configuration is read through :mod:`cogs.aimoderation.settings` at call time,
never ``from``-imported -- the suite patches these names on ``ai_client``, and a
snapshot would silently keep using the real environment.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from .. import settings

logger = logging.getLogger("ModBot.AIModeration.Client")


class AiModelLaneMixin:
    """AiModel Responses-API lanes.

    Mixed into ``AIClient`` because the suite patches these as attributes of the
    client (``client._post_responses_api = AsyncMock()``,
    ``patch("...AIClient._call_aimodel")``).

    Requires from the composing class: ``self._post_chat_completion``,
    ``self._normalize_text_messages``, ``self._get_http_session``,
    ``self._set_block``, ``self.config``, and the ``_block_until`` /
    ``_block_reason`` attributes.
    """

    @staticmethod
    def _canonical_aimodel_model(model: str) -> str:
        """Normalize AiModel aliases to the resource IDs required by its API."""
        selected = str(model or "").strip()
        if not selected:
            return selected
        if selected.startswith("accounts/aimodel/"):
            return selected
        return f"accounts/aimodel/models/{selected}"

    @classmethod
    def _responses_input(
        cls,
        messages: List[Dict[str, Any]],
        *,
        allow_multimodal: bool,
    ) -> List[Dict[str, Any]]:
        """Convert chat-completions messages into Responses API input items."""
        if not allow_multimodal:
            return [dict(message) for message in cls._normalize_text_messages(messages)]

        converted: List[Dict[str, Any]] = []
        for message in messages:
            role = str(message.get("role") or "user")
            raw_content = message.get("content")
            if isinstance(raw_content, str):
                text = raw_content.strip()
                if text:
                    converted.append({"role": role, "content": text})
                continue

            parts: List[Dict[str, Any]] = []
            if isinstance(raw_content, list):
                for raw_part in raw_content:
                    if not isinstance(raw_part, dict):
                        text = str(raw_part or "").strip()
                        if text:
                            parts.append({"type": "input_text", "text": text})
                        continue
                    part_type = str(raw_part.get("type") or "").strip().lower()
                    if part_type in {"text", "input_text"}:
                        text = str(raw_part.get("text") or "").strip()
                        if text:
                            parts.append({"type": "input_text", "text": text})
                    elif part_type in {"image_url", "input_image"}:
                        image_value = raw_part.get("image_url")
                        detail = raw_part.get("detail")
                        if isinstance(image_value, dict):
                            detail = image_value.get("detail", detail)
                            image_value = image_value.get("url")
                        image_url = str(image_value or "").strip()
                        if image_url:
                            image_part: Dict[str, Any] = {
                                "type": "input_image",
                                "image_url": image_url,
                            }
                            if detail in {"auto", "low", "high"}:
                                image_part["detail"] = detail
                            parts.append(image_part)
            if parts:
                converted.append({"role": role, "content": parts})
        return converted

    @staticmethod
    def _extract_responses_content(data: Any) -> Optional[str]:
        """Extract all output_text parts from a Responses API payload."""
        if not isinstance(data, dict):
            return None
        direct = data.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        pieces: List[str] = []
        for item in data.get("output") or []:
            if not isinstance(item, dict):
                continue
            for part in item.get("content") or []:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str) and text:
                        pieces.append(text)
        return "".join(pieces).strip() or None

    async def _post_responses_api(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
        allow_multimodal: bool,
        provider_label: str,
        max_retries: int = 1,
        request_timeout: int = 90,
        search: bool = False,
    ) -> Optional[str]:
        """POST to AiModel's Responses API with bounded transient retries."""
        request_input = self._responses_input(
            messages,
            allow_multimodal=allow_multimodal,
        )
        if not request_input:
            raise RuntimeError(f"{provider_label} request has no message content.")

        payload: Dict[str, Any] = {
            "model": self._canonical_aimodel_model(model),
            "input": request_input,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if search:
            payload["research"] = True
        if json_mode:
            payload["text"] = {"format": {"type": "json_object"}}

        last_error: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            session, owned_session = self._get_http_session(timeout=request_timeout)
            try:
                async with session.post(
                    f"{settings.setting('_AIMODEL_BASE_URL')}/responses",
                    headers={
                        "Authorization": f"Bearer {settings.setting('_AIMODEL_API_KEY')}",
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
                            self._set_block(
                                seconds=900,
                                reason=f"{provider_label} authentication or access failed.",
                            )
                            raise RuntimeError(
                                f"{provider_label} HTTP {resp.status}: {str(detail)[:500]}"
                            )
                        if resp.status == 402:
                            self._set_block(
                                seconds=300,
                                reason=f"{provider_label} balance or plan is exhausted.",
                            )
                            raise RuntimeError(
                                f"{provider_label} HTTP 402: {str(detail)[:500]}"
                            )
                        if resp.status == 429:
                            self._set_block(
                                seconds=60,
                                reason=f"{provider_label} rate limit reached.",
                            )
                        if resp.status < 500 and resp.status != 429:
                            raise RuntimeError(
                                f"{provider_label} HTTP {resp.status}: {str(detail)[:500]}"
                            )
                        last_error = RuntimeError(
                            f"{provider_label} HTTP {resp.status}: {str(detail)[:500]}"
                        )
                    else:
                        content = self._extract_responses_content(data)
                        if content:
                            self._block_until = None
                            self._block_reason = None
                        return content
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = exc
                logger.warning(
                    "%s network error (attempt %d/%d): %s",
                    provider_label,
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )
            finally:
                if owned_session:
                    await session.close()

            if attempt < max_retries:
                await asyncio.sleep(0.75 * (2 ** attempt))

        if last_error is not None:
            raise last_error
        return None

    async def _call_aimodel(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
        model: Optional[str] = None,
        json_mode: bool = False,
        allow_multimodal: bool = False,
        fallback_models: Optional[Tuple[str, ...]] = None,
        max_retries: Optional[int] = None,
        request_timeout: Optional[int] = None,
        search: bool = False,
    ) -> Optional[str]:
        """Call AiModel's Responses API with ordered provider-local failover.

        ``max_retries`` overrides the per-model retry count inside
        ``_post_responses_api`` (default ``1``). Callers that need a
        deterministic upper time bound — e.g. the behavior profile command,
        which wraps this in its own ``asyncio.wait_for`` — pass ``0`` so a
        single failed attempt cannot blow past the outer budget.
        """
        if not settings.call("_aimodel_api_enabled"):
            raise RuntimeError("AiModel is missing AIMODEL_API_KEY.")

        selected_model = str(model or "").strip()
        if selected_model.lower() in {
            "",
            "aimodel",
            "aimodel.lol",
            "deepseek-web",
            "digitalocean",
            "relay",
            "relayrouter",
            "relayrouter.org",
        }:
            selected_model = (
                settings.setting("_AIMODEL_VISION_MODEL")
                if allow_multimodal
                else settings.setting("_AIMODEL_MODERATION_MODEL")
            )

        configured_fallbacks = fallback_models
        if configured_fallbacks is None:
            configured_fallbacks = (
                settings.setting("_AIMODEL_VISION_FALLBACK_MODELS")
                if allow_multimodal
                else settings.setting("_AIMODEL_FALLBACK_MODELS")
            )

        candidates: List[str] = []
        for candidate in (selected_model, *configured_fallbacks):
            normalized = self._canonical_aimodel_model(candidate)
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        last_error: Optional[Exception] = None
        for index, candidate in enumerate(candidates):
            try:
                result = await self._post_responses_api(
                    messages,
                    model=candidate,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                    allow_multimodal=allow_multimodal,
                    provider_label=f"AiModel ({candidate.rsplit('/', 1)[-1]})",
                    request_timeout=(
                        request_timeout
                        if request_timeout is not None
                        else settings.call(
                            "_aimodel_request_timeout",
                            multimodal=allow_multimodal,
                        )
                    ),
                    max_retries=1 if max_retries is None else max(0, max_retries),
                    search=search,
                )
                if result:
                    if index:
                        logger.info(
                            "AiModel fallback %s succeeded after %d failed route(s)",
                            candidate,
                            index,
                        )
                    return result
                last_error = RuntimeError(
                    f"AiModel ({candidate}) returned no assistant content."
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "AiModel model %s failed (%d/%d): %s",
                    candidate,
                    index + 1,
                    len(candidates),
                    exc,
                )
                error_text = str(exc)
                if any(
                    marker in error_text
                    for marker in ("HTTP 401", "HTTP 402", "HTTP 403")
                ):
                    break

        if last_error is not None:
            raise last_error
        return None

    async def _call_aimodel_conversation(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        """Call Grok through AiModel's working text-only chat endpoint.

        This method is deliberately limited to ordinary text conversation.
        Search, research, vision, moderation, routing, and memory use their
        dedicated provider lanes instead.
        """
        if not settings.call("_aimodel_conversation_enabled"):
            raise RuntimeError("AiModel conversation is missing AIMODEL_API_KEY.")

        conversation_model = settings.setting("_AIMODEL_CONVERSATION_MODEL")
        return await self._post_chat_completion(
            messages,
            base_url=settings.setting("_AIMODEL_BASE_URL"),
            api_key=(
                settings.setting("_AIMODEL_CONVERSATION_API_KEY")
                or settings.setting("_AIMODEL_API_KEY")
            ),
            model=conversation_model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=False,
            allow_multimodal=False,
            provider_label=f"AiModel conversation ({conversation_model})",
            max_retries=0,
            request_timeout=min(
                45,
                settings.call("_aimodel_request_timeout", multimodal=False),
            ),
        )
