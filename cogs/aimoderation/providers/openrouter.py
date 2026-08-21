"""Every OpenRouter lane: talking, search, vision, research, and protected work.

OpenRouter is the only provider, so lane separation here is by MODEL rather
than by vendor, and it is the point of this module. ``_call_openrouter_chat``
is the ordinary talking lane and deliberately sends no tools, no images, and no
citations, so changing the chat model cannot quietly take over search,
research, or vision. Those live on Luna (``_call_openrouter_conversation``,
``_call_openrouter_visual_candidates``) and Sonar
(``_call_research_prefetch``).

``_call_openrouter_protected`` is the separate lane for work that can mute,
delete, or ban: moderation, action routing, image screening, and memory
curation. It accepts only the models this deployment configured for those
tasks, so a caller -- including one steered by a hostile Discord message --
cannot smuggle in a model of its own choosing.

Configuration is read through :mod:`cogs.aimoderation.settings` at call time,
never ``from``-imported: the suite patches these names on the ``ai_client``
module, and a snapshot would silently keep using the real environment.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from .. import settings
from ..transport import _exception_summary

def _int_env(name: str, default: int, *, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(os.getenv(name, "").strip() or default)))
    except (TypeError, ValueError):
        return default


_SEARCH_MAX_RESULTS: int = _int_env("OPENROUTER_SEARCH_MAX_RESULTS", 3, low=1, high=10)
_SEARCH_MAX_TOTAL_RESULTS: int = _int_env(
    "OPENROUTER_SEARCH_MAX_TOTAL_RESULTS", 5, low=1, high=20
)


logger = logging.getLogger("ModBot.AIModeration.Client")


class OpenRouterLaneMixin:
    """OpenRouter request lanes.

    Mixed into ``AIClient`` rather than used standalone: the suite patches these
    as attributes of the client (``client._call_openrouter_chat = AsyncMock()``,
    ``patch("...ai_client.AIClient._call_openrouter_conversation")``), so they
    must remain bound methods.

    Requires from the composing class: ``self._post_chat_completion``,
    ``self.config``, and the ``_block_until`` / ``_block_reason`` attributes.
    """

    async def _call_openrouter_protected(
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
    ) -> Optional[str]:
        """Run a protected task with bounded model failover.

        Protected means moderation, action routing, image screening, and memory
        curation -- the calls whose output can punish a member. The lane runs
        the models this deployment configured for that work and nothing else:
        a requested model outside the allow-list is dropped with a warning
        rather than dialled, so a decision cannot bring its own model along.
        """
        if not settings.call("_openrouter_protected_enabled"):
            raise RuntimeError("The protected AI lane is missing OPENROUTER_API_KEY.")

        selected_model = (model or "").strip()
        if not selected_model:
            selected_model = (
                settings.setting("_OPENROUTER_MODERATION_VISION_MODEL")
                if allow_multimodal
                else settings.setting("_OPENROUTER_MODERATION_MODEL")
            )

        configured_fallbacks = fallback_models
        if configured_fallbacks is None:
            configured_fallbacks = (
                settings.setting("_OPENROUTER_MODERATION_VISION_FALLBACK_MODELS")
                if allow_multimodal
                else settings.setting("_OPENROUTER_MODERATION_FALLBACK_MODELS")
            )

        candidates: List[str] = []
        for candidate in (selected_model, *configured_fallbacks):
            normalized = str(candidate or "").strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        # Background lanes (memory curation, routing) may deliberately run a
        # different, cheaper model than the interactive moderation lane -- no
        # user is waiting on them, so a rate-limited free model is an acceptable
        # trade there. They are configured explicitly, so they belong in the
        # allow-list; anything NOT configured is still refused.
        background = tuple(
            settings.setting(name, "")
            for name in ("_OPENROUTER_MEMORY_MODEL", "_OPENROUTER_ROUTER_MODEL")
        )
        allowed = [
            model_id
            for model_id in (
                settings.setting("_OPENROUTER_MODERATION_VISION_MODEL")
                if allow_multimodal
                else settings.setting("_OPENROUTER_MODERATION_MODEL"),
                *(
                    settings.setting("_OPENROUTER_MODERATION_VISION_FALLBACK_MODELS")
                    if allow_multimodal
                    else settings.setting("_OPENROUTER_MODERATION_FALLBACK_MODELS")
                ),
                *background,
            )
            if model_id
        ]
        # De-duplicate while preserving the configured order, so the primary is
        # tried first and a fallback is only reached on failure.
        seen: set = set()
        allowed = [m for m in allowed if not (m in seen or seen.add(m))]

        rejected = [c for c in candidates if c not in allowed]
        if rejected:
            logger.warning(
                "Ignored model(s) not configured for the protected lane: %s",
                ", ".join(rejected),
            )

        # FILTER the requested candidates rather than replacing them: the
        # caller's order carries the lane's intent. Replacing it wholesale meant
        # a background lane asking for its own cheap model still got the
        # moderation model, because that sits first in the allow-list.
        permitted = [c for c in candidates if c in allowed]
        # Append the lane defaults as fallbacks behind whatever was asked for,
        # so a single rate-limited model still has somewhere to go.
        candidates = permitted + [m for m in allowed if m not in permitted]

        last_error: Optional[Exception] = None
        for index, candidate in enumerate(candidates):
            try:
                result = await self._post_chat_completion(
                    messages,
                    base_url=settings.setting("_OPENROUTER_BASE_URL"),
                    api_key=settings.setting("_OPENROUTER_API_KEY"),
                    model=candidate,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                    allow_multimodal=allow_multimodal,
                    provider_label=f"OpenRouter protected ({candidate})",
                    # Moderation, routing, and memory each pin their own model
                    # on this lane. One of them being rate-limited says nothing
                    # about the talking lane, so it must not trip the
                    # client-wide block that gates every conversation. This
                    # lane's own failover already handles a dead candidate.
                    allow_service_block=False,
                    # Each candidate is itself a retry route. Retrying a dead
                    # route first made multi-model failover take over a minute.
                    max_retries=0 if max_retries is None else max(0, max_retries),
                    request_timeout=(
                        request_timeout
                        if request_timeout is not None
                        else settings.call(
                            "_openrouter_protected_timeout",
                            multimodal=allow_multimodal,
                        )
                    ),
                )
                if result:
                    if index:
                        logger.info(
                            "Protected fallback model %s succeeded after %d failed route(s)",
                            candidate,
                            index,
                        )
                    self._block_until = None
                    self._block_reason = None
                    return result
                last_error = RuntimeError(
                    f"OpenRouter protected ({candidate}) returned no assistant content."
                )
            except Exception as exc:
                last_error = exc
                if len(candidates) > 1:
                    logger.warning(
                        "Protected model %s failed (%d/%d): %s",
                        candidate,
                        index + 1,
                        len(candidates),
                        _exception_summary(exc),
                    )

        if last_error is not None:
            raise last_error
        return None

    async def _call_research_prefetch(
        self,
        user_content: str,
    ) -> Tuple[Optional[str], List[str]]:
        """Fetch live research material plus the URLs that actually back it.

        Deliberately not the protected lane: that one only dials the configured
        moderation models, and Sonar is not one of them.

        Returns (content, source_urls). The URLs come from the provider's real
        citations, so an answer with no citations yields no sources and correctly
        fails the verifiable-source gate instead of being dressed up as sourced.
        """
        if not settings.call("_openrouter_conversation_enabled"):
            return None, []

        research_model = settings.setting("_OPENROUTER_RESEARCH_MODEL")
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a live internet research assistant. Provide a highly "
                    "detailed, factual, and up-to-date answer to the user's query. "
                    "Cite the sources you used."
                ),
            },
            {"role": "user", "content": user_content},
        ]
        content = await self._post_chat_completion(
            messages,
            base_url=settings.setting("_OPENROUTER_BASE_URL"),
            api_key=settings.setting("_OPENROUTER_API_KEY"),
            model=research_model,
            temperature=0.3,
            max_tokens=self.config.max_tokens_chat,
            json_mode=False,
            allow_multimodal=False,
            provider_label=f"OpenRouter research ({research_model})",
            max_retries=0,
            request_timeout=settings.call("_openrouter_request_timeout"),
            include_citations=True,
        )
        if not content:
            return None, []

        # ``include_citations`` appends a __BOT_SOURCES__ block. Split it back off
        # so the research material stays clean and the URLs travel separately.
        body, _, sources_block = content.partition("__BOT_SOURCES__")
        urls = [
            url.strip().lstrip("-").strip()
            for url in re.findall(r"https?://[^\s<>]+", sources_block)
        ]
        return body.strip(), [url for url in urls if url]

    async def _call_openrouter_chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        """Call the talking model on OpenRouter for ordinary text conversation.

        This lane is deliberately narrow: no web-search tool, no images, no
        citations. Search, research, vision, moderation, routing, and memory all
        keep their own dedicated lanes, so changing the default chat model cannot
        silently take over those behaviors.

        Reasoning is turned off here by default. The current talking model (GLM)
        enables it implicitly, which tripled reply latency and spent billable
        output tokens on hidden reasoning that a casual chat reply never needs.
        """
        if not settings.call("_openrouter_conversation_enabled"):
            raise RuntimeError("OpenRouter conversation is missing OPENROUTER_API_KEY.")

        extra_payload: Optional[Dict[str, Any]] = None
        if settings.setting("_OPENROUTER_CHAT_DISABLE_REASONING"):
            extra_payload = {"reasoning": {"enabled": False}}

        talk_model = settings.setting("_OPENROUTER_TALK_CHAT_MODEL")
        return await self._post_chat_completion(
            messages,
            base_url=settings.setting("_OPENROUTER_BASE_URL"),
            api_key=settings.setting("_OPENROUTER_API_KEY"),
            model=talk_model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=False,
            allow_multimodal=False,
            provider_label=f"OpenRouter chat ({talk_model})",
            max_retries=1,
            request_timeout=settings.call("_openrouter_request_timeout"),
            extra_payload=extra_payload,
        )

    async def _call_openrouter_conversation(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
        allow_multimodal: bool = False,
        require_search: bool = False,
    ) -> Optional[str]:
        """Call Luna with bounded web search that the model normally invokes as needed.

        Callers enforce the lane boundary: moderation, action routing, and
        memory curation never use this method. Explicit search/research requests
        can require the tool without changing ordinary conversation behavior.
        """
        if not settings.call("_openrouter_conversation_enabled"):
            raise RuntimeError("OpenRouter conversation is missing OPENROUTER_API_KEY.")

        extra_payload: Dict[str, Any] = {
            "tools": [
                {
                    "type": "openrouter:web_search",
                    "parameters": {
                        "engine": "auto",
                        # Results are billed per result and dominate the cost of
                        # a searched turn -- far more than the model does. Three
                        # is enough to answer and cite a Discord question; raise
                        # OPENROUTER_SEARCH_MAX_RESULTS if answers get thin.
                        "max_results": _SEARCH_MAX_RESULTS,
                        "max_uses": 1,
                        "max_total_results": _SEARCH_MAX_TOTAL_RESULTS,
                    },
                }
            ],
            "tool_choice": "required" if require_search else "auto",
            "max_tool_calls": 1,
        }

        # Pinned to the Luna constant on purpose: this lane must ignore a stale
        # _OPENROUTER_CHAT_MODEL override (e.g. left over from a dashboard
        # setting) so search/research/vision cannot be silently repointed at the
        # talking model. Asserted by
        # test_openrouter_conversation_ignores_stale_model_override.
        luna_model = settings.setting("_OPENROUTER_LUNA_MODEL")
        return await self._post_chat_completion(
            messages,
            base_url=settings.setting("_OPENROUTER_BASE_URL"),
            api_key=settings.setting("_OPENROUTER_API_KEY"),
            model=luna_model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=False,
            allow_multimodal=allow_multimodal,
            provider_label=f"OpenRouter conversation ({luna_model})",
            max_retries=1,
            request_timeout=settings.call("_openrouter_request_timeout"),
            extra_payload=extra_payload,
            include_citations=True,
        )

    async def _call_openrouter_research_writer(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        """Write the research report from evidence Sonar already gathered.

        Sonar is a search product: it finds and cites sources well, but it is not
        the strongest long-form writer. When the pre-fetch has already supplied
        the evidence and the real source URLs, the synthesis step is pure writing
        over text that is already in the prompt -- no search tool and no images
        needed -- so it goes to the writer model instead of the search lane.
        """
        if not settings.call("_openrouter_conversation_enabled"):
            raise RuntimeError("OpenRouter conversation is missing OPENROUTER_API_KEY.")

        extra_payload: Optional[Dict[str, Any]] = None
        if settings.setting("_OPENROUTER_CHAT_DISABLE_REASONING"):
            extra_payload = {"reasoning": {"enabled": False}}

        writer_model = settings.setting("_OPENROUTER_RESEARCH_WRITER_MODEL")
        return await self._post_chat_completion(
            messages,
            base_url=settings.setting("_OPENROUTER_BASE_URL"),
            api_key=settings.setting("_OPENROUTER_API_KEY"),
            model=writer_model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=False,
            allow_multimodal=False,
            provider_label=f"OpenRouter research writer ({writer_model})",
            max_retries=1,
            request_timeout=settings.call("_openrouter_request_timeout"),
            extra_payload=extra_payload,
        )

    async def _call_openrouter_vision(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        """Call the dedicated vision model for image understanding.

        Luna accepts images but is a search model, and it reads a photo's actual
        visible subject poorly. The vision lane is natively multimodal, so image
        turns come here instead. No web-search tool is attached: describing what
        is in a picture does not need one, and the caller adds a separate
        searched verification pass when an identity claim has to be checked.
        """
        if not settings.call("_openrouter_conversation_enabled"):
            raise RuntimeError("OpenRouter conversation is missing OPENROUTER_API_KEY.")

        vision_model = settings.setting("_OPENROUTER_VISION_MODEL")
        return await self._post_chat_completion(
            messages,
            base_url=settings.setting("_OPENROUTER_BASE_URL"),
            api_key=settings.setting("_OPENROUTER_API_KEY"),
            model=vision_model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=False,
            allow_multimodal=True,
            provider_label=f"OpenRouter vision ({vision_model})",
            max_retries=1,
            request_timeout=settings.call("_openrouter_request_timeout"),
        )

    async def _call_openrouter_visual_candidates(
        self,
        messages: List[Dict[str, Any]],
    ) -> Optional[str]:
        """Generate visual-only candidates before the searched verification pass."""
        candidate_messages = [
            *messages,
            {
                "role": "user",
                "content": (
                    "Perform an independent visual-identification pass on the attached image. "
                    "Do not search and do not commit to one answer yet. First inspect every edge "
                    "and corner and transcribe all visible watermark text, artist signatures, "
                    "@usernames, logos, captions, and tiny lettering exactly, including uncertain "
                    "characters. Then list 2-4 plausible candidates in confidence order and cite "
                    "the visible colors, silhouette, anatomy, markings, clothing, and distinctive "
                    "parts that support or contradict each candidate. Explicitly consider whether "
                    "the subject is an original character rather than a franchise character. "
                    "Nearby captions may describe a previous item, so treat them as context rather "
                    "than proof. Keep this under 700 words."
                ),
            },
        ]
        # This pass is pure looking-at-the-image, so it belongs on the vision
        # model rather than the search model.
        vision_model = settings.setting("_OPENROUTER_VISION_MODEL")
        return await self._post_chat_completion(
            candidate_messages,
            base_url=settings.setting("_OPENROUTER_BASE_URL"),
            api_key=settings.setting("_OPENROUTER_API_KEY"),
            model=vision_model,
            temperature=0.1,
            max_tokens=1_200,
            json_mode=False,
            allow_multimodal=True,
            provider_label=f"OpenRouter visual candidates ({vision_model})",
            max_retries=1,
            request_timeout=settings.call("_openrouter_request_timeout"),
        )
