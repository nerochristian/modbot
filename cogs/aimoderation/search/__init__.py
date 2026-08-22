"""The bot's own search and research harness.

This package exists because Legion Edge -- the only text provider -- has no
search capability of any kind: no plugins, no native ``web_search`` tool, no
``/v1/responses``. The previous implementation leaned entirely on a provider
that ran search server-side, so when the provider changed, the bot's ability to
know anything current had to be rebuilt here.

What that means in practice: the models in ``providers/legion.py`` never reach
the internet. This package does, in three separable steps -- find candidate
URLs (:mod:`.backends`), rank them (:mod:`.rank`), open and read them
(:mod:`.fetch`) -- and the model only ever synthesizes text that came back.
That ordering is what makes the citation gate in ``research.py`` mean
something: a source URL is a page that returned bytes.

Two chains are assembled here rather than one, because the lanes want opposite
things from a backend. Research wants batch economy: Apify's actor takes the
whole query list in one billable run, so a five-query fan-out costs one call.
The interactive search lane wants latency: Serper answers in 1-2 seconds and
the whole lane budget is 4-6. Both fall back to DuckDuckGo, so a deployment
with no keys at all still works.

Everything is lazily constructed and cached at module level: the cache and the
per-backend health counters must be shared across every guild and lane, or the
protections they provide (spend limits, circuit breakers, DDG pacing) would
reset on every call.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from .backends import (
    ApifyBackend,
    BackendChain,
    DdgBrowserBackend,
    DdgHttpBackend,
    SearchBackend,
    SerperBackend,
)
from .budget import BackendHealth, ResultCache, TokenBucket
from .fetch import PageFetcher, trim_pages
from .models import (
    ExtractedPage,
    HarnessResult,
    ProgressUpdate,
    ResearchPlan,
    SearchHit,
    Source,
    normalize_url,
    registrable_domain,
)
from .pipeline import run_research, run_search
from .rank import authority_tier, rank_hits

logger = logging.getLogger("ModBot.AIModeration.Search")

__all__ = [
    "ExtractedPage",
    "HarnessResult",
    "PageFetcher",
    "ProgressUpdate",
    "ResearchPlan",
    "SearchHit",
    "Source",
    "any_backend_configured",
    "authority_tier",
    "backend_diagnostics",
    "close_harness",
    "normalize_url",
    "rank_hits",
    "registrable_domain",
    "research_chain",
    "reset_harness",
    "run_research",
    "run_search",
    "search_chain",
    "trim_pages",
]


def _env_int(name: str, default: int, *, low: int, high: int) -> int:
    try:
        return max(low, min(high, int((os.getenv(name) or "").strip() or default)))
    except (TypeError, ValueError):
        return default


# Shared process-wide state. See the module docstring: these MUST be shared, or
# the spend counters and circuit breakers reset on every request.
_cache: Optional[ResultCache] = None
_bucket: Optional[TokenBucket] = None
_health: Dict[str, BackendHealth] = {}
_backends: Dict[str, SearchBackend] = {}
_research_chain: Optional[BackendChain] = None
_search_chain: Optional[BackendChain] = None


def _get_cache() -> ResultCache:
    global _cache
    if _cache is None:
        _cache = ResultCache(
            ttl_seconds=_env_int("SEARCH_CACHE_TTL", 900, low=0, high=86_400),
            max_entries=_env_int("SEARCH_CACHE_ENTRIES", 512, low=16, high=8_192),
        )
    return _cache


def _get_bucket() -> TokenBucket:
    global _bucket
    if _bucket is None:
        # ~1 request/second. DDG returned its 202 challenge after roughly three
        # back-to-back requests, so this is the pacing that keeps the free
        # fallback usable rather than instantly challenged.
        _bucket = TokenBucket(rate_per_second=1.0, burst=2)
    return _bucket


def _get_health(name: str, *, quota: int = 0) -> BackendHealth:
    if name not in _health:
        _health[name] = BackendHealth(name=name, quota=quota)
    return _health[name]


def _get_backend(name: str) -> SearchBackend:
    """Build a backend once and reuse it (the browser one owns a Chromium)."""
    if name in _backends:
        return _backends[name]

    cache = _get_cache()
    if name == "apify":
        # Apify bills per actor RUN, and one run carries the whole query list,
        # so the quota is counted in calls rather than queries. $5/cycle at
        # ~$0.0015/query is thousands of queries; the cap is a safety net, not
        # the expected limit.
        backend: SearchBackend = ApifyBackend(
            cache=cache,
            health=_get_health("apify", quota=_env_int("APIFY_MAX_CALLS", 0, low=0, high=1_000_000)),
        )
    elif name == "serper":
        backend = SerperBackend(
            cache=cache,
            health=_get_health(
                "serper", quota=_env_int("SERPER_MAX_CALLS", 0, low=0, high=1_000_000)
            ),
        )
    elif name == "ddg_http":
        backend = DdgHttpBackend(
            cache=cache, health=_get_health("ddg_http"), bucket=_get_bucket()
        )
    elif name == "ddg_browser":
        backend = DdgBrowserBackend(
            cache=cache, health=_get_health("ddg_browser"), bucket=_get_bucket()
        )
    else:
        raise ValueError(f"Unknown search backend: {name}")

    _backends[name] = backend
    return backend


def _chain_from_env(var: str, default: str) -> BackendChain:
    order = [
        part.strip()
        for part in ((os.getenv(var) or "").strip() or default).split(",")
        if part.strip()
    ]
    resolved: List[SearchBackend] = []
    for name in order:
        try:
            resolved.append(_get_backend(name))
        except ValueError:
            logger.warning("Ignoring unknown search backend %r in %s", name, var)
    return BackendChain(resolved)


def research_chain() -> BackendChain:
    """Backends for research, batch-economy first."""
    global _research_chain
    if _research_chain is None:
        _research_chain = _chain_from_env(
            "RESEARCH_BACKEND_ORDER", "apify,serper,ddg_http,ddg_browser"
        )
    return _research_chain


def search_chain() -> BackendChain:
    """Backends for the interactive search lane, lowest latency first."""
    global _search_chain
    if _search_chain is None:
        _search_chain = _chain_from_env(
            "SEARCH_BACKEND_ORDER", "serper,apify,ddg_http,ddg_browser"
        )
    return _search_chain


def any_backend_configured() -> bool:
    """Whether any SERP backend could answer a query right now.

    ``AIClient.has_web_search`` defers to this, because with Legion Edge the
    ability to search is a property of the harness, not of the model provider.
    """
    return bool(research_chain()) or bool(search_chain())


def backend_diagnostics() -> List[str]:
    """Human-readable backend state for ``/aimod status``."""
    lines: List[str] = []
    order = ["apify", "serper", "ddg_http", "ddg_browser"]
    for name in order:
        try:
            backend = _get_backend(name)
        except ValueError:  # pragma: no cover - order is a literal
            continue
        if not backend.configured():
            lines.append(f"Search `{name}`: not configured")
            continue
        health = backend.health
        reason = health.unavailable_reason()
        state = f"unavailable ({reason})" if reason else "ready"
        remaining = health.budget_remaining()
        budget = f", {remaining} call(s) left" if remaining is not None else ""
        lines.append(f"Search `{name}`: {state} -- {health.used} call(s) used{budget}")

    cache = _get_cache()
    total = cache.hits + cache.misses
    if total:
        lines.append(
            f"Search cache: {cache.hits}/{total} hits "
            f"({round(100 * cache.hits / total)}% saved)"
        )
    return lines


async def close_harness() -> None:
    """Release harness resources (the browser backend holds a Chromium)."""
    for backend in list(_backends.values()):
        closer = getattr(backend, "close", None)
        if closer is None:
            continue
        try:
            await closer()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Closing search backend %s failed: %s", backend.name, exc)


def reset_harness() -> None:
    """Drop all cached harness state. For tests only."""
    global _cache, _bucket, _research_chain, _search_chain
    _cache = None
    _bucket = None
    _research_chain = None
    _search_chain = None
    _health.clear()
    _backends.clear()
