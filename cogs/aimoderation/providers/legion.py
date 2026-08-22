"""Every Legion Edge lane: talking, structured decisions, synthesis, protected.

Legion Edge is the only text provider, so lane separation here is by MODEL
rather than by vendor, and that is the point of this module.
``_call_legion_chat`` is the ordinary talking lane and deliberately sends no
tools, no images, and no citations, so changing the chat model cannot quietly
take over routing, search, or research.

Two things Legion Edge does NOT do, which shape this module:

* **No web search.** No plugins, no native ``web_search`` tool, no
  ``/v1/responses``. Search and research get their sources from
  :mod:`cogs.aimoderation.search`, and the models here only ever synthesize
  text that the harness already fetched. That is why there is no
  ``_call_research_prefetch`` equivalent -- nothing here reaches the internet.
* **No vision.** All nine models are text-only, so image turns route to
  :mod:`cogs.aimoderation.providers.google` instead.

``_call_legion_protected`` is the separate lane for work that can mute,
delete, or ban: moderation, action routing, image screening, and memory
curation. It accepts only the models this deployment configured for those
tasks, so a caller -- including one steered by a hostile Discord message --
cannot smuggle in a model of its own choosing.

Configuration is read through :mod:`cogs.aimoderation.settings` at call time,
never ``from``-imported: the suite patches these names on the ``ai_client``
module, and a snapshot would silently keep using the real environment.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .. import settings
from ..transport import _exception_summary

logger = logging.getLogger("ModBot.AIModeration.Client")

# Models whose reasoning arrives inline in ``message.content`` wrapped in
# <think> tags rather than in a separate field. Stripping is unconditional and
# cheap: a model that never emits them is unaffected, and one that starts
# emitting them does not suddenly leak scratchpad into Discord.
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: Optional[str]) -> str:
    """Remove inline <think> scratchpad and leading whitespace from a reply.

    ``qwen3-0.6b`` streams raw reasoning into ``content``, and the 27B Qwen
    variants prepend blank lines. Neither belongs in a Discord message.
    """
    if not text:
        return ""
    cleaned = _THINK_BLOCK_RE.sub("", text)
    # An unterminated <think> means the reply was truncated mid-scratchpad;
    # there is no usable answer after it, so drop the fragment entirely.
    if "<think>" in cleaned.lower():
        cleaned = cleaned[: cleaned.lower().index("<think>")]
    return cleaned.strip()


def _json_schema_payload(name: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Build a strict json_schema response_format.

    Verified working on every model this bot uses. ``strict: true`` is what
    makes the router safe to parse without a regex fallback.
    """
    return {
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": name, "strict": True, "schema": schema},
        }
    }


class LegionLaneMixin:
    """Legion Edge request lanes.

    Mixed into ``AIClient`` rather than used standalone: the suite patches
    these as attributes of the client, so they must remain bound methods.

    Requires from the composing class: ``self._post_chat_completion``,
    ``self.config``, and the ``_block_until`` / ``_block_reason`` attributes.
    """

    # -- protected ----------------------------------------------------------

    async def _call_legion_protected(
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
        if not settings.call("_legion_protected_enabled"):
            raise RuntimeError("The protected AI lane is missing LEGION_API_KEY.")

        selected_model = (model or "").strip()
        if not selected_model:
            selected_model = settings.setting("_LEGION_MODERATION_MODEL")

        configured_fallbacks = fallback_models
        if configured_fallbacks is None:
            configured_fallbacks = settings.setting("_LEGION_MODERATION_FALLBACK_MODELS")

        candidates: List[str] = []
        for candidate in (selected_model, *configured_fallbacks):
            normalized = str(candidate or "").strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        # Background lanes (memory curation, action routing) may deliberately
        # run a different model than the interactive moderation lane. They are
        # configured explicitly, so they belong in the allow-list; anything NOT
        # configured is still refused.
        background = tuple(
            settings.setting(name, "")
            for name in ("_LEGION_MEMORY_MODEL", "_LEGION_ACTION_ROUTER_MODEL")
        )
        allowed = [
            model_id
            for model_id in (
                settings.setting("_LEGION_MODERATION_MODEL"),
                *settings.setting("_LEGION_MODERATION_FALLBACK_MODELS"),
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
        # a background lane asking for its own model still got the moderation
        # model, because that sits first in the allow-list.
        permitted = [c for c in candidates if c in allowed]
        # Append the lane defaults behind whatever was asked for, so a single
        # rate-limited model still has somewhere to go.
        candidates = permitted + [m for m in allowed if m not in permitted]

        last_error: Optional[Exception] = None
        for index, candidate in enumerate(candidates):
            try:
                result = await self._post_chat_completion(
                    messages,
                    base_url=settings.setting("_LEGION_BASE_URL"),
                    api_key=settings.setting("_LEGION_API_KEY"),
                    model=candidate,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                    allow_multimodal=allow_multimodal,
                    provider_label=f"Legion protected ({candidate})",
                    # Moderation, routing, and memory each pin their own model
                    # on this lane. One of them being rate-limited says nothing
                    # about the talking lane, so it must not trip the
                    # client-wide block that gates every conversation.
                    allow_service_block=False,
                    # Each candidate is itself a retry route. Retrying a dead
                    # route first made multi-model failover take over a minute.
                    max_retries=0 if max_retries is None else max(0, max_retries),
                    request_timeout=(
                        request_timeout
                        if request_timeout is not None
                        else settings.call(
                            "_legion_protected_timeout",
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
                    return strip_reasoning(result)
                last_error = RuntimeError(
                    f"Legion protected ({candidate}) returned no assistant content."
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

    # -- talking ------------------------------------------------------------

    async def _call_legion_chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        """The ordinary talking lane: no tools, no images, no citations.

        Kept deliberately narrow so that repointing the chat model cannot
        quietly take over routing, search, research, or vision.
        """
        if not settings.call("_legion_conversation_enabled"):
            raise RuntimeError("Legion conversation is missing LEGION_API_KEY.")

        extra_payload: Dict[str, Any] = {}
        if settings.setting("_LEGION_CHAT_DISABLE_REASONING"):
            extra_payload["reasoning"] = {"enabled": False}

        model = settings.setting("_LEGION_CHAT_MODEL")
        content = await self._post_chat_completion(
            messages,
            base_url=settings.setting("_LEGION_BASE_URL"),
            api_key=settings.setting("_LEGION_API_KEY"),
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=False,
            allow_multimodal=False,
            provider_label=f"Legion chat ({model})",
            request_timeout=settings.call("_legion_request_timeout"),
            extra_payload=extra_payload or None,
        )
        return strip_reasoning(content)

    # -- structured decisions -----------------------------------------------

    async def _call_legion_structured(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: str,
        schema_name: str,
        schema: Dict[str, Any],
        max_tokens: int = 1_200,
        temperature: float = 0.0,
        request_timeout: int = 20,
        label: str = "structured",
    ) -> Optional[Dict[str, Any]]:
        """Run a strict-JSON call and return the parsed object.

        Used by the conversation router and the research planner. Returns
        ``None`` rather than raising when the call fails or the payload will
        not parse, so callers can fall back to a safe default instead of
        losing the turn.

        ``max_tokens`` defaults high enough to clear reasoning models: kimi-k3
        spends tokens in ``reasoning_content`` before emitting the object, and
        a tight cap truncates the JSON rather than the reasoning.
        """
        if not settings.call("_legion_conversation_enabled"):
            return None
        try:
            raw = await self._post_chat_completion(
                messages,
                base_url=settings.setting("_LEGION_BASE_URL"),
                api_key=settings.setting("_LEGION_API_KEY"),
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=False,
                allow_multimodal=False,
                provider_label=f"Legion {label} ({model})",
                # A slow or rate-limited decision lane must never silence
                # every conversation in every guild.
                allow_service_block=False,
                max_retries=0,
                request_timeout=request_timeout,
                extra_payload=_json_schema_payload(schema_name, schema),
            )
        except Exception as exc:
            logger.warning("Legion %s call failed: %s", label, _exception_summary(exc))
            return None

        text = strip_reasoning(raw)
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # strict:true should make this unreachable, but a truncated
            # response is still possible; salvage the first JSON object.
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                logger.warning("Legion %s returned unparseable JSON: %.200s", label, text)
                return None
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.warning("Legion %s returned unparseable JSON: %.200s", label, text)
                return None
        return parsed if isinstance(parsed, dict) else None

    # -- synthesis ----------------------------------------------------------

    async def _call_legion_writer(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: str,
        max_tokens: int,
        temperature: float = 0.3,
        fallback_models: Sequence[str] = (),
        request_timeout: Optional[int] = None,
        label: str = "writer",
    ) -> Optional[str]:
        """Synthesize an answer from source text the harness already fetched.

        This lane never reaches the internet: the pages are gathered by
        :mod:`cogs.aimoderation.search` and passed in as message content. The
        fallback list exists because research prompts are long, and a model
        that refuses an oversized context should hand off rather than lose the
        turn.
        """
        if not settings.call("_legion_conversation_enabled"):
            return None

        timeout = (
            request_timeout
            if request_timeout is not None
            else settings.call("_legion_request_timeout")
        )
        candidates: List[str] = []
        for candidate in (model, *fallback_models):
            normalized = str(candidate or "").strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        last_error: Optional[Exception] = None
        for index, candidate in enumerate(candidates):
            try:
                content = await self._post_chat_completion(
                    messages,
                    base_url=settings.setting("_LEGION_BASE_URL"),
                    api_key=settings.setting("_LEGION_API_KEY"),
                    model=candidate,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=False,
                    allow_multimodal=False,
                    provider_label=f"Legion {label} ({candidate})",
                    max_retries=0,
                    request_timeout=timeout,
                )
                cleaned = strip_reasoning(content)
                if cleaned:
                    if index:
                        logger.info(
                            "Legion %s fallback %s succeeded after %d failed route(s)",
                            label,
                            candidate,
                            index,
                        )
                    return cleaned
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Legion %s model %s failed (%d/%d): %s",
                    label,
                    candidate,
                    index + 1,
                    len(candidates),
                    _exception_summary(exc),
                )

        if last_error is not None and len(candidates) == 1:
            raise last_error
        return None
