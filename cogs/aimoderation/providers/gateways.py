"""Protected-gateway, DigitalOcean, and DeepSeek HTTP lanes.

``_call_relayrouter`` is the "protected task" lane used for moderation, action
routing, and memory curation. Its important property: when the legacy
RelayRouter-named gateway is pointed at OpenRouter, every request is force-pinned
to Nemotron and any other requested model is rejected with a warning, so a
config change cannot quietly route protected work to an arbitrary model.

DigitalOcean and the DeepSeek HTTP API are plain OpenAI-compatible fallbacks.
``_conversation_via_http`` is the ordered failover chain across them.

Configuration is read through :mod:`cogs.aimoderation.settings` at call time,
never ``from``-imported -- the suite patches these names on ``ai_client``, and a
snapshot would silently keep using the real environment.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from .. import settings
from ..transport import _exception_summary

logger = logging.getLogger("ModBot.AIModeration.Client")


class GatewayLaneMixin:
    """Protected gateway plus HTTP fallback lanes.

    Mixed into ``AIClient`` because the suite patches these as attributes of the
    client and via ``patch("...AIClient._call_relayrouter")``.

    Requires from the composing class: ``self._post_chat_completion``,
    ``self.config``, ``self.prefers_aimodel``, ``self.prefers_relayrouter``,
    ``self._call_aimodel_conversation``, and the ``_block_until`` /
    ``_block_reason`` attributes.
    """

    async def _call_relayrouter(
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
        """Call the protected-task gateway with bounded model failover."""
        if not settings.call("_relayrouter_api_enabled"):
            required_key = (
                "OPENROUTER_API_KEY"
                if settings.call("_relayrouter_routes_to_openrouter")
                else "RELAYROUTER_API_KEY"
            )
            raise RuntimeError(f"Protected AI gateway is missing {required_key}.")

        selected_model = (model or "").strip()
        if selected_model.lower() in {
            "",
            "deepseek-web",
            "digitalocean",
            "relay",
            "relayrouter",
            "relayrouter.org",
        }:
            selected_model = (
                settings.setting("_RELAYROUTER_VISION_MODEL")
                if allow_multimodal
                else settings.setting("_RELAYROUTER_MODERATION_MODEL")
            )

        configured_fallbacks = fallback_models
        if configured_fallbacks is None:
            configured_fallbacks = (
                settings.setting("_RELAYROUTER_VISION_FALLBACK_MODELS")
                if allow_multimodal
                else settings.setting("_RELAYROUTER_FALLBACK_MODELS")
            )

        candidates: List[str] = []
        for candidate in (selected_model, *configured_fallbacks):
            normalized = str(candidate or "").strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        routes_to_openrouter = settings.call("_relayrouter_routes_to_openrouter")
        if routes_to_openrouter:
            nemotron_model = settings.setting("_OPENROUTER_NEMOTRON_MODEL")
            rejected = [
                candidate
                for candidate in candidates
                if candidate != nemotron_model
            ]
            if rejected:
                logger.warning(
                    "Ignored non-Nemotron model(s) on the protected OpenRouter lane: %s",
                    ", ".join(rejected),
                )
            candidates = [nemotron_model]

        gateway_api_key = (
            settings.setting("_OPENROUTER_API_KEY")
            if routes_to_openrouter
            else settings.setting("_RELAYROUTER_API_KEY")
        )
        gateway_label = "OpenRouter protected" if routes_to_openrouter else "RelayRouter"

        last_error: Optional[Exception] = None
        for index, candidate in enumerate(candidates):
            try:
                result = await self._post_chat_completion(
                    messages,
                    base_url=settings.setting("_RELAYROUTER_BASE_URL"),
                    api_key=gateway_api_key,
                    model=candidate,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                    allow_multimodal=allow_multimodal,
                    provider_label=f"{gateway_label} ({candidate})",
                    # Each candidate is itself a retry route. Retrying a dead
                    # route first made multi-model failover take over a minute.
                    max_retries=0 if max_retries is None else max(0, max_retries),
                    request_timeout=(
                        request_timeout
                        if request_timeout is not None
                        else settings.call(
                            "_relayrouter_request_timeout",
                            multimodal=allow_multimodal,
                        )
                    ),
                )
                if result:
                    if index:
                        logger.info(
                            "%s fallback model %s succeeded after %d failed route(s)",
                            gateway_label,
                            candidate,
                            index,
                        )
                    self._block_until = None
                    self._block_reason = None
                    return result
                last_error = RuntimeError(
                    f"{gateway_label} ({candidate}) returned no assistant content."
                )
            except Exception as exc:
                last_error = exc
                if len(candidates) > 1:
                    logger.warning(
                        "%s model %s failed (%d/%d): %s",
                        gateway_label,
                        candidate,
                        index + 1,
                        len(candidates),
                        _exception_summary(exc),
                    )

        if last_error is not None:
            raise last_error
        return None

    async def _call_digitalocean(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
        model: Optional[str] = None,
        json_mode: bool = False,
        allow_multimodal: bool = False,
        max_retries: Optional[int] = None,
        request_timeout: Optional[int] = None,
    ) -> Optional[str]:
        do_api_key = settings.setting("_DO_API_KEY")
        if not do_api_key:
            raise RuntimeError("DigitalOcean inference is missing DO_API_KEY.")

        selected_model = (model or self.config.model or "").strip()
        if selected_model.lower() in {"", "deepseek-web", "digitalocean"}:
            selected_model = os.getenv("DO_PROFILE_MODEL", "deepseek-4-flash").strip()

        post_kwargs: Dict[str, Any] = {"provider_label": "DigitalOcean inference"}
        if max_retries is not None:
            post_kwargs["max_retries"] = max_retries
        if request_timeout is not None:
            post_kwargs["request_timeout"] = request_timeout
        return await self._post_chat_completion(
            messages,
            base_url=settings.setting("_DO_BASE_URL"),
            api_key=do_api_key,
            model=selected_model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            allow_multimodal=allow_multimodal,
            **post_kwargs,
        )

    async def _call_deepseek_api(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
        model: Optional[str] = None,
        json_mode: bool = False,
        allow_multimodal: bool = False,
        max_retries: Optional[int] = None,
        request_timeout: Optional[int] = None,
    ) -> Optional[str]:
        """Call the real DeepSeek HTTP API (OpenAI-compatible)."""
        deepseek_api_key = settings.setting("_DEEPSEEK_API_KEY")
        if not deepseek_api_key:
            raise RuntimeError("DeepSeek API is missing DEEPSEEK_API_KEY.")

        # DeepSeek's API has its own model namespace (deepseek-chat / deepseek-reasoner);
        # ignore DigitalOcean-style model hints that don't apply here.
        selected_model = (model or "").strip()
        if selected_model.lower() in {"", "deepseek-web", "digitalocean"} or selected_model.startswith("deepseek-4"):
            selected_model = settings.setting("_DEEPSEEK_API_MODEL")

        request_chat_path = (
            "/chat/completions/cline"
            if allow_multimodal
            else settings.setting("_DEEPSEEK_CHAT_PATH")
        )

        post_kwargs: Dict[str, Any] = {
            "provider_label": "DeepSeek API",
            "chat_path": request_chat_path,
        }
        if max_retries is not None:
            post_kwargs["max_retries"] = max_retries
        if request_timeout is not None:
            post_kwargs["request_timeout"] = request_timeout
        return await self._post_chat_completion(
            messages,
            base_url=settings.setting("_DEEPSEEK_BASE_URL"),
            api_key=deepseek_api_key,
            model=selected_model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            allow_multimodal=allow_multimodal,
            **post_kwargs,
        )

    async def _call_digitalocean_conversation(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        long_answer: bool = False,
    ) -> Optional[str]:
        max_tokens = max(self.config.max_tokens_chat, 2400) if long_answer else self.config.max_tokens_chat
        return await self._call_digitalocean(
            [{"role": "user", "content": prompt}],
            temperature=self.config.temperature_chat,
            max_tokens=max_tokens,
            model=model,
        )

    async def _conversation_via_http(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        long_answer: bool = False,
    ) -> Optional[str]:
        """Text conversation over the configured HTTP provider, then fallbacks.

        Used when the browser scraper is disabled/unavailable. Vision and native
        web-search remain browser-only; this covers plain text turns.
        """
        max_tokens = max(self.config.max_tokens_chat, 2400) if long_answer else self.config.max_tokens_chat
        if self.prefers_aimodel and settings.call("_aimodel_conversation_enabled"):
            return await self._call_aimodel_conversation(
                [{"role": "user", "content": prompt}],
                temperature=self.config.temperature_chat,
                max_tokens=max_tokens,
            )
        if self.prefers_relayrouter and settings.call("_relayrouter_api_enabled"):
            try:
                result = await self._call_relayrouter(
                    [{"role": "user", "content": prompt}],
                    temperature=self.config.temperature_chat,
                    max_tokens=max_tokens,
                    model=model or settings.setting("_RELAYROUTER_CHAT_MODEL"),
                )
                if result is not None:
                    return result
            except Exception:
                logger.warning(
                    "RelayRouter conversation failed; trying DigitalOcean.",
                    exc_info=True,
                )
        if settings.call("_deepseek_api_enabled"):
            try:
                result = await self._call_deepseek_api(
                    [{"role": "user", "content": prompt}],
                    temperature=self.config.temperature_chat,
                    max_tokens=max_tokens,
                    model=model,
                )
                if result is not None:
                    return result
            except Exception:
                logger.warning("DeepSeek API conversation failed; trying DigitalOcean.", exc_info=True)
        return await self._call_digitalocean_conversation(prompt, model=model, long_answer=long_answer)
