"""SERP backends, ordered into a failover chain.

Legion Edge has no search of its own, so this is where the bot actually finds
out what is on the web. Four backends, in the order the chain prefers them:

===============  ==========  ====================  ==========================
backend          index       cost                  why it sits here
===============  ==========  ====================  ==========================
``apify``        Google      $5 credit per cycle,  batch-native: one run takes
                             renewing (~3,300      the whole query list, so a
                             queries/mo)           research fan-out is ONE
                                                   billable call, not five
``serper``       Google      2,500 lifetime, free  fastest (~1-2s); reserved
                                                   for the interactive search
                                                   lane where latency shows
``ddg_http``     DDG         free                  no key required, so a fresh
                                                   clone still works
``ddg_browser``  DDG         free                  last resort: a real browser
                                                   gets past the challenge that
                                                   stops ``ddg_http``
===============  ==========  ====================  ==========================

Every backend returns :class:`SearchHit` lists keyed by the query that found
them, so the caller can score a URL by how many distinct sub-questions
surfaced it. Failures are never raised at the caller: a backend that errors is
recorded against its :class:`BackendHealth` and the chain moves on, because
having somewhere else to go is the entire reason the chain exists.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .budget import BackendHealth, ResultCache, TokenBucket, backoff_sleep, cache_key
from .models import SearchHit

logger = logging.getLogger("ModBot.AIModeration.Search")

_APIFY_BASE = "https://api.apify.com/v2"
_SERPER_URL = "https://google.serper.dev/search"
_DDG_HTML_URL = "https://html.duckduckgo.com/html/"

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _int_env(name: str, default: int, *, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(_env(name) or default)))
    except (TypeError, ValueError):
        return default


class SearchBackend:
    """Base class for a SERP source.

    Subclasses implement :meth:`_search_batch`. The base class owns caching,
    health accounting, and the "never raise at the caller" contract.
    """

    name = "base"
    #: Whether one upstream call can carry several queries. Batch backends are
    #: billed per call, so a research fan-out is dramatically cheaper on them.
    batch_native = False

    def __init__(self, *, cache: ResultCache, health: BackendHealth) -> None:
        self._cache = cache
        self.health = health

    # -- to implement -------------------------------------------------------

    def configured(self) -> bool:
        """Whether this backend has what it needs to run (key, binary, ...)."""
        raise NotImplementedError

    async def _search_batch(
        self, queries: Sequence[str], *, count: int
    ) -> Dict[str, List[SearchHit]]:
        raise NotImplementedError

    # -- public -------------------------------------------------------------

    async def search(
        self, queries: Sequence[str], *, count: int = 10
    ) -> Dict[str, List[SearchHit]]:
        """Return hits per query, serving what it can from cache.

        Never raises: on failure the backend is marked unhealthy and an empty
        mapping comes back so the chain can try the next one.
        """
        wanted = [q for q in (s.strip() for s in queries) if q]
        if not wanted:
            return {}

        results: Dict[str, List[SearchHit]] = {}
        misses: List[str] = []
        for query in wanted:
            cached = self._cache.get(cache_key(query, count))
            if cached is None:
                misses.append(query)
            else:
                results[query] = [hit for hit in cached if isinstance(hit, SearchHit)]

        if not misses:
            return results

        try:
            fetched = await self._search_batch(misses, count=count)
        except Exception as exc:  # noqa: BLE001 - the chain must survive anything
            self.health.record_failure(f"{type(exc).__name__}: {exc}")
            logger.warning("Search backend %s failed: %s", self.name, exc)
            return results

        got_anything = False
        for query in misses:
            hits = fetched.get(query) or []
            if hits:
                got_anything = True
                self._cache.put(cache_key(query, count), list(hits))
            results[query] = hits

        if got_anything:
            # Batch backends bill per call, not per query, so the spend
            # counter must advance once per call to match how credits burn.
            self.health.record_success()
        else:
            self.health.record_failure("returned no results")
        return results


class ApifyBackend(SearchBackend):
    """Google results via an Apify actor, run synchronously.

    Batch-native, which is why it carries research: the actor's input takes a
    ``queries`` array and returns one dataset row per query, so a five-query
    research fan-out costs a single actor run rather than five.

    The actor id is configurable because the default is a community-published
    actor, not an Apify-official one -- it can change price or be delisted.
    ``apify/google-search-scraper`` is the official drop-in on the same
    platform and the same free credits.
    """

    name = "apify"
    batch_native = True

    def __init__(self, *, cache: ResultCache, health: BackendHealth) -> None:
        super().__init__(cache=cache, health=health)
        self._token = _env("APIFY_TOKEN")
        self._actor = _env(
            "APIFY_SERP_ACTOR", "serp.cheap.ofc/cheapest-google-search"
        ).replace("/", "~")
        self._country = _env("SEARCH_COUNTRY", "us")
        self._timeout = _int_env("APIFY_TIMEOUT", 60, low=10, high=180)

    def configured(self) -> bool:
        return bool(self._token and self._actor)

    async def _search_batch(
        self, queries: Sequence[str], *, count: int
    ) -> Dict[str, List[SearchHit]]:
        import aiohttp

        url = (
            f"{_APIFY_BASE}/acts/{self._actor}/run-sync-get-dataset-items"
            f"?token={self._token}"
        )
        payload: Dict[str, Any] = {
            "queries": list(queries),
            "country": self._country,
            "page": 1,
        }
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise RuntimeError(f"Apify HTTP {resp.status}: {body[:300]}")
                import json as _json

                rows = _json.loads(body)

        out: Dict[str, List[SearchHit]] = {q: [] for q in queries}
        if not isinstance(rows, list):
            return out
        for row in rows:
            if not isinstance(row, dict):
                continue
            query = str(row.get("query") or "").strip()
            # Match the row back to the query we asked for; the actor echoes it
            # verbatim, but fall back to positional order if it ever does not.
            target = query if query in out else None
            if target is None:
                remaining = [q for q in queries if not out.get(q)]
                if not remaining:
                    continue
                target = remaining[0]
            hits: List[SearchHit] = []
            for item in row.get("organic") or []:
                if not isinstance(item, dict):
                    continue
                link = str(item.get("link") or "").strip()
                if not link.startswith(("http://", "https://")):
                    continue
                hits.append(
                    SearchHit(
                        url=link,
                        title=str(item.get("title") or "").strip(),
                        snippet=str(item.get("snippet") or "").strip(),
                        engine="google/apify",
                        position=int(item.get("position") or (len(hits) + 1)),
                        queries=(target,),
                    )
                )
                if len(hits) >= count:
                    break
            out[target] = hits
        return out


class SerperBackend(SearchBackend):
    """Google results via serper.dev.

    The fastest backend measured (~1-2s), which is why the interactive search
    lane prefers it: that lane's whole budget is 4-6 seconds. Not batch-native,
    so it is a poor fit for research fan-out and is not first in that chain.
    """

    name = "serper"

    def __init__(self, *, cache: ResultCache, health: BackendHealth) -> None:
        super().__init__(cache=cache, health=health)
        self._key = _env("SERPER_API_KEY")
        self._country = _env("SEARCH_COUNTRY", "us")
        self._timeout = _int_env("SERPER_TIMEOUT", 20, low=5, high=60)

    def configured(self) -> bool:
        return bool(self._key)

    async def _search_batch(
        self, queries: Sequence[str], *, count: int
    ) -> Dict[str, List[SearchHit]]:
        import aiohttp

        timeout = aiohttp.ClientTimeout(total=self._timeout)
        headers = {"X-API-KEY": self._key, "Content-Type": "application/json"}
        out: Dict[str, List[SearchHit]] = {}

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:

            async def one(query: str) -> None:
                payload = {"q": query, "num": count, "gl": self._country}
                async with session.post(_SERPER_URL, json=payload) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        raise RuntimeError(f"Serper HTTP {resp.status}: {text[:200]}")
                    data = await resp.json()
                hits: List[SearchHit] = []
                for item in data.get("organic") or []:
                    link = str(item.get("link") or "").strip()
                    if not link.startswith(("http://", "https://")):
                        continue
                    hits.append(
                        SearchHit(
                            url=link,
                            title=str(item.get("title") or "").strip(),
                            snippet=str(item.get("snippet") or "").strip(),
                            engine="google/serper",
                            position=int(item.get("position") or (len(hits) + 1)),
                            queries=(query,),
                        )
                    )
                out[query] = hits

            # Serper is a paid API with no burst penalty, so parallel is safe
            # and is what keeps the search lane inside its latency budget.
            await asyncio.gather(*(one(q) for q in queries))
        return out


class DdgHttpBackend(SearchBackend):
    """DuckDuckGo's HTML endpoint, scraped.

    The free fallback that needs no key, so the bot still works on a fresh
    clone. It is a fallback and not a primary for a measured reason: DDG
    returned HTTP 202 -- its bot challenge -- after roughly three back-to-back
    requests. Hence the shared token bucket and the sequential loop; bursting
    here is what breaks it.
    """

    name = "ddg_http"

    def __init__(
        self, *, cache: ResultCache, health: BackendHealth, bucket: TokenBucket
    ) -> None:
        super().__init__(cache=cache, health=health)
        self._bucket = bucket
        self._timeout = _int_env("DDG_TIMEOUT", 20, low=5, high=60)

    def configured(self) -> bool:
        return True

    async def _search_batch(
        self, queries: Sequence[str], *, count: int
    ) -> Dict[str, List[SearchHit]]:
        import aiohttp

        out: Dict[str, List[SearchHit]] = {}
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        headers = {"User-Agent": _BROWSER_UA, "Accept-Language": "en-US,en;q=0.9"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            for query in queries:
                html = ""
                for attempt in range(3):
                    await self._bucket.acquire()
                    async with session.post(
                        _DDG_HTML_URL, data={"q": query, "kl": "us-en"}
                    ) as resp:
                        # 202 is DDG's challenge, not a success. Treating it as
                        # one is how scrapers silently return zero results.
                        if resp.status == 202 or resp.status == 429:
                            await backoff_sleep(attempt)
                            continue
                        if resp.status >= 400:
                            raise RuntimeError(f"DDG HTTP {resp.status}")
                        html = await resp.text()
                        break
                if not html:
                    raise RuntimeError("DDG returned a challenge (202) on every attempt")
                out[query] = _parse_ddg_html(html, query=query, count=count)
        return out


def _parse_ddg_html(html: str, *, query: str, count: int) -> List[SearchHit]:
    """Extract organic results from DDG's HTML endpoint."""
    from html import unescape
    from urllib.parse import parse_qs, unquote, urlsplit

    hits: List[SearchHit] = []
    pattern = re.compile(
        r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    snippet_re = re.compile(
        r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    snippets = [re.sub(r"<[^>]+>", "", s) for s in snippet_re.findall(html)]

    for index, (href, title_html) in enumerate(pattern.findall(html)):
        # DDG wraps results in /l/?uddg=<encoded target>.
        target = href
        if "/l/?" in href or href.startswith("//duckduckgo.com/l/"):
            qs = parse_qs(urlsplit(href).query)
            target = unquote((qs.get("uddg") or [""])[0]) or href
        if not target.startswith(("http://", "https://")):
            continue
        title = unescape(re.sub(r"<[^>]+>", "", title_html)).strip()
        snippet = unescape(snippets[index]).strip() if index < len(snippets) else ""
        hits.append(
            SearchHit(
                url=target,
                title=title,
                snippet=snippet,
                engine="duckduckgo",
                position=index + 1,
                queries=(query,),
            )
        )
        if len(hits) >= count:
            break
    return hits


class DdgBrowserBackend(SearchBackend):
    """DuckDuckGo through a real headless browser.

    The last resort, for when ``ddg_http`` is being challenged: a real browser
    runs the page's JavaScript and carries cookies, which is what gets past the
    202. Playwright is already a project dependency, so this costs no new
    install.

    Expensive in memory (a Chromium context is ~300-500MB), so ONE context is
    created lazily and reused for the process lifetime -- never one per query.
    """

    name = "ddg_browser"

    def __init__(
        self, *, cache: ResultCache, health: BackendHealth, bucket: TokenBucket
    ) -> None:
        super().__init__(cache=cache, health=health)
        self._bucket = bucket
        self._playwright: Any = None
        self._browser: Any = None
        self._lock = asyncio.Lock()
        self._enabled = _env("SEARCH_ENABLE_BROWSER", "1").lower() not in {
            "0", "false", "no", "off",
        }
        self._timeout_ms = _int_env("DDG_BROWSER_TIMEOUT_MS", 25_000, low=5_000, high=90_000)

    def configured(self) -> bool:
        if not self._enabled:
            return False
        try:
            import playwright  # noqa: F401
        except ImportError:
            return False
        return True

    async def _ensure_browser(self) -> Any:
        async with self._lock:
            if self._browser is not None:
                return self._browser
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            launch: Dict[str, Any] = {
                "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
            }
            executable = _env("PLAYWRIGHT_CHROMIUM_PATH")
            if executable:
                launch["executable_path"] = executable
            self._browser = await self._playwright.chromium.launch(**launch)
            return self._browser

    async def close(self) -> None:
        async with self._lock:
            if self._browser is not None:
                try:
                    await self._browser.close()
                finally:
                    self._browser = None
            if self._playwright is not None:
                try:
                    await self._playwright.stop()
                finally:
                    self._playwright = None

    async def _search_batch(
        self, queries: Sequence[str], *, count: int
    ) -> Dict[str, List[SearchHit]]:
        from urllib.parse import quote_plus

        browser = await self._ensure_browser()
        out: Dict[str, List[SearchHit]] = {}
        context = await browser.new_context(
            user_agent=_BROWSER_UA, locale="en-US"
        )
        try:
            for query in queries:
                await self._bucket.acquire()
                page = await context.new_page()
                try:
                    await page.goto(
                        f"https://duckduckgo.com/?q={quote_plus(query)}&ia=web",
                        timeout=self._timeout_ms,
                        wait_until="domcontentloaded",
                    )
                    try:
                        await page.wait_for_selector(
                            "[data-testid='result-title-a'], a.result__a",
                            timeout=self._timeout_ms,
                        )
                    except Exception:
                        # No results rendered: a challenge page or an empty
                        # SERP. Either way this query yields nothing.
                        out[query] = []
                        continue
                    rows = await page.eval_on_selector_all(
                        "[data-testid='result-title-a'], a.result__a",
                        "els => els.map(e => ({url: e.href, title: e.innerText}))",
                    )
                    hits: List[SearchHit] = []
                    for index, row in enumerate(rows or []):
                        url = str((row or {}).get("url") or "").strip()
                        if not url.startswith(("http://", "https://")):
                            continue
                        hits.append(
                            SearchHit(
                                url=url,
                                title=str((row or {}).get("title") or "").strip(),
                                engine="duckduckgo/browser",
                                position=index + 1,
                                queries=(query,),
                            )
                        )
                        if len(hits) >= count:
                            break
                    out[query] = hits
                finally:
                    await page.close()
        finally:
            await context.close()
        return out


class BackendChain:
    """An ordered list of backends, tried until one produces results."""

    def __init__(self, backends: Sequence[SearchBackend]) -> None:
        self._backends = list(backends)

    def __bool__(self) -> bool:
        return any(b.configured() for b in self._backends)

    @property
    def backends(self) -> List[SearchBackend]:
        return list(self._backends)

    async def search(
        self, queries: Sequence[str], *, count: int = 10
    ) -> Dict[str, List[SearchHit]]:
        """Run ``queries`` against the first healthy backend that answers.

        A backend that returns results for only SOME queries still counts: the
        remainder fall through to the next backend, so a partial answer is
        topped up rather than discarded.
        """
        wanted = [q for q in (s.strip() for s in queries) if q]
        merged: Dict[str, List[SearchHit]] = {}
        for backend in self._backends:
            outstanding = [q for q in wanted if not merged.get(q)]
            if not outstanding:
                break
            if not backend.configured():
                continue
            if not backend.health.available():
                logger.debug(
                    "Skipping search backend %s: %s",
                    backend.name,
                    backend.health.unavailable_reason(),
                )
                continue
            got = await backend.search(outstanding, count=count)
            for query, hits in got.items():
                if hits:
                    merged[query] = hits
        return merged
