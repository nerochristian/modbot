"""Credit protection, caching, pacing, and per-backend circuit breaking.

The search backends this bot uses are all finite in some way: Apify grants $5
of platform credit per billing cycle, Serper grants 2,500 lifetime queries, and
DuckDuckGo grants nothing but will answer until it decides you are a bot. None
of them fail gracefully on their own, so the protections live here:

* **Cache** -- research fires several queries per run and users repeat
  questions. A short TTL cache turns overlapping queries into zero-cost hits.
  This is the single biggest saver, because it works across lanes and users.
* **Spend counter** -- fails a backend over BEFORE its credits are exhausted
  rather than after, so the bot degrades to the next tier instead of erroring
  mid-answer.
* **Token bucket** -- only the DuckDuckGo paths need it. Bursting is what
  triggers DDG's HTTP 202 challenge; a paid API has no burst penalty and is
  deliberately allowed to run queries in parallel.
* **Circuit breaker** -- a backend that just failed is skipped for a cooldown
  instead of being retried on every query of the same run.

Everything here is pure in-process state. It resets on restart, which is
acceptable: the cache is an optimization and the counters are conservative
(a restart makes the bot *more* cautious, never less).
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("ModBot.AIModeration.Search")

_WHITESPACE_RE = re.compile(r"\s+")


def cache_key(query: str, count: int) -> str:
    """Normalize a query so trivially different spellings share a cache slot."""
    normalized = _WHITESPACE_RE.sub(" ", (query or "").strip().lower())
    return f"{normalized}::{count}"


@dataclass(slots=True)
class _CacheEntry:
    value: List[object]
    expires_at: float


class ResultCache:
    """TTL cache of SERP results keyed by normalized query."""

    def __init__(self, *, ttl_seconds: float = 900.0, max_entries: int = 512) -> None:
        self._ttl = max(0.0, ttl_seconds)
        self._max_entries = max(1, max_entries)
        self._entries: Dict[str, _CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[List[object]]:
        entry = self._entries.get(key)
        if entry is None:
            self.misses += 1
            return None
        if entry.expires_at <= time.monotonic():
            self._entries.pop(key, None)
            self.misses += 1
            return None
        self.hits += 1
        return list(entry.value)

    def put(self, key: str, value: List[object]) -> None:
        if self._ttl <= 0:
            return
        if len(self._entries) >= self._max_entries:
            # Evict the soonest-to-expire entry; cheap and good enough for a
            # cache this small, and avoids dragging in an LRU dependency.
            oldest = min(self._entries, key=lambda k: self._entries[k].expires_at)
            self._entries.pop(oldest, None)
        self._entries[key] = _CacheEntry(
            value=list(value), expires_at=time.monotonic() + self._ttl
        )

    def clear(self) -> None:
        self._entries.clear()


class TokenBucket:
    """Async rate limiter used only on the scraped DuckDuckGo paths.

    DDG returned HTTP 202 after roughly three back-to-back requests in
    testing. Spacing requests out is the difference between a fallback that
    works and one that is challenged the moment it is needed.
    """

    def __init__(self, *, rate_per_second: float = 1.0, burst: int = 2) -> None:
        self._rate = max(0.05, rate_per_second)
        self._burst = max(1, burst)
        self._tokens = float(self._burst)
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self._tokens = min(
                    float(self._burst), self._tokens + (now - self._updated) * self._rate
                )
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                await asyncio.sleep((1.0 - self._tokens) / self._rate)


@dataclass
class BackendHealth:
    """Circuit breaker and spend counter for one backend."""

    name: str
    # Queries this backend may serve per cycle before we stop using it. 0 means
    # unmetered (the DDG paths, which are limited by challenges rather than
    # credits).
    quota: int = 0
    used: int = 0
    consecutive_failures: int = 0
    open_until: float = 0.0
    last_error: str = ""

    #: Failures before the breaker opens. Low, because the whole point of a
    #: backend chain is that there is somewhere else to go.
    trip_after: int = 2
    #: How long the breaker stays open. Long enough to finish a research run on
    #: the next backend rather than re-probing a dead one every query.
    cooldown_seconds: float = 300.0

    def available(self) -> bool:
        if self.open_until > time.monotonic():
            return False
        if self.quota and self.used >= self.quota:
            return False
        return True

    def unavailable_reason(self) -> str:
        if self.open_until > time.monotonic():
            remaining = int(self.open_until - time.monotonic())
            return f"circuit open for {remaining}s ({self.last_error or 'repeated failures'})"
        if self.quota and self.used >= self.quota:
            return f"quota reached ({self.used}/{self.quota})"
        return ""

    def record_success(self) -> None:
        self.used += 1
        self.consecutive_failures = 0
        self.open_until = 0.0
        self.last_error = ""

    def record_failure(self, error: str) -> None:
        self.consecutive_failures += 1
        self.last_error = error[:200]
        if self.consecutive_failures >= self.trip_after:
            self.open_until = time.monotonic() + self.cooldown_seconds
            logger.warning(
                "Search backend %s tripped after %d failures (%s); "
                "skipping it for %ds",
                self.name,
                self.consecutive_failures,
                self.last_error,
                int(self.cooldown_seconds),
            )

    def budget_remaining(self) -> Optional[int]:
        return None if not self.quota else max(0, self.quota - self.used)


async def backoff_sleep(attempt: int, *, base: float = 0.5, cap: float = 8.0) -> None:
    """Exponential backoff with jitter, for 429/202 responses."""
    delay = min(cap, base * (2 ** max(0, attempt)))
    await asyncio.sleep(delay * (0.5 + random.random() * 0.5))
