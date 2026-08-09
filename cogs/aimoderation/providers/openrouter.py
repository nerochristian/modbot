"""OpenRouter lanes: talking, search/vision conversation, and research pre-fetch.

Lane separation is the point of this module. ``_call_openrouter_chat`` is the
ordinary talking lane and deliberately sends no tools, no images, and no
citations, so changing the chat model cannot quietly take over search,
research, or vision. Those live on Luna (``_call_openrouter_conversation``,
``_call_openrouter_visual_candidates``) and Sonar
(``_call_research_prefetch``).

Configuration is read through :mod:`cogs.aimoderation.settings` at call time,
never ``from``-imported: the suite patches these names on the ``ai_client``
module, and a snapshot would silently keep using the real environment.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .. import settings


class OpenRouterLaneMixin:
    """OpenRouter request lanes.

    Mixed into ``AIClient`` rather than used standalone: the suite patches these
    as attributes of the client (``client._call_openrouter_chat = AsyncMock()``,
    ``patch("...ai_client.AIClient._call_openrouter_conversation")``), so they
    must remain bound methods.

    Requires from the composing class: ``self._post_chat_completion`` and
    ``self.config``.
    """

    async def _call_research_prefetch(
        self,
        user_content: str,
    ) -> Tuple[Optional[str], List[str]]:
        """Fetch live research material plus the URLs that actually back it.

        Perplexity Sonar is served by OpenRouter, not by the RelayRouter-named
        gateway, so this deliberately does not go through ``_call_relayrouter``:
        that lane force-pins every request to Nemotron when it points at
        OpenRouter, and relayrouter.org itself serves no ``perplexity/*`` model.

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
                        "max_results": 5,
                        "max_uses": 1,
                        "max_total_results": 10,
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
                    "Do not search and do not commit to one answer yet. List 2-4 plausible "
                    "candidates in confidence order and cite the visible colors, silhouette, "
                    "anatomy, markings, and distinctive parts that support or contradict each "
                    "candidate. Nearby captions may describe a previous item, so treat them as "
                    "context rather than proof. Keep this under 500 words."
                ),
            },
        ]
        luna_model = settings.setting("_OPENROUTER_LUNA_MODEL")
        return await self._post_chat_completion(
            candidate_messages,
            base_url=settings.setting("_OPENROUTER_BASE_URL"),
            api_key=settings.setting("_OPENROUTER_API_KEY"),
            model=luna_model,
            temperature=0.1,
            max_tokens=900,
            json_mode=False,
            allow_multimodal=True,
            provider_label=f"OpenRouter visual candidates ({luna_model})",
            max_retries=1,
            request_timeout=settings.call("_openrouter_request_timeout"),
        )
