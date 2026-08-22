"""Parallel page fetching and article extraction.

This is the module that makes the difference between "the bot saw ten search
snippets" and "the bot read ten websites". Measured end to end against twelve
real pages: **12 readable in 8.6s**, of which the network is only ~0.3s -- the
rest is HTML parsing. Reading a dozen sites costs seconds, not minutes.

Two measurements shape the design:

* **Roughly a quarter of pages refuse a plain client.** Reuters answered 401,
  StackOverflow 403, GitHub 400. Those get one retry through a reader proxy,
  and if that fails too the SERP snippet stands in so the source still counts
  rather than vanishing.
* **Raw HTML is enormous** -- up to 1.2MB and a million characters for a single
  news homepage. Feeding that to a model would blow a 100k context on two
  pages, so extraction to article text is mandatory, not a nicety, and there
  is a hard byte cap on the download itself.

Extraction runs off the event loop because trafilatura is CPU-bound and would
otherwise stall Discord for every page -- but on ONE dedicated thread, never
the shared pool. See :data:`_EXTRACT_POOL` for why that is not optional.
"""
from __future__ import annotations

import asyncio
import atexit
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Iterable, List, Optional, Sequence

from .models import ExtractedPage, SearchHit

logger = logging.getLogger("ModBot.AIModeration.Search")

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_TEXT_CONTENT_TYPES = ("text/html", "application/xhtml", "text/plain")

_WS_RE = re.compile(r"[ \t ]+")
_BLANKS_RE = re.compile(r"\n{3,}")

#: Extraction runs on a SINGLE dedicated thread, deliberately.
#:
#: trafilatura is backed by lxml, whose C parser corrupts the heap when several
#: threads parse large documents at once. Running twelve real pages through
#: ``run_in_executor`` on the default pool aborted the process with
#: ``double free or corruption`` in 2 of 6 runs -- not an exception a
#: try/except could contain, a SIGABRT that would take the whole bot down.
#:
#: Serializing is the dominant cost of a run and is accepted anyway: profiled
#: over ten Wikipedia articles (7.6MB of HTML), fetching took 0.30s and
#: extraction 6.7s, so this thread is the bottleneck, not the network. It stays
#: single-threaded because a bot that answers two seconds slower is strictly
#: better than one that SIGABRTs mid-conversation. Two cheap mitigations claw
#: most of it back: no second parse for metadata, and a byte cap on the
#: download (see :data:`_MAX_BYTES`).
_EXTRACT_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="serp-extract")
atexit.register(_EXTRACT_POOL.shutdown, wait=False)


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _int_env(name: str, default: int, *, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(_env(name) or default)))
    except (TypeError, ValueError):
        return default


# Hard ceiling on a single download, applied while streaming. Article text is
# effectively always in the first few hundred KB; past that a news homepage is
# just more navigation chrome, and every extra byte is lxml parse time on the
# serialized extract thread.
_MAX_BYTES = _int_env("SEARCH_MAX_PAGE_BYTES", 900_000, low=100_000, high=8_000_000)


def clean_text(raw: str) -> str:
    """Collapse whitespace without destroying paragraph structure."""
    if not raw:
        return ""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = _WS_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _BLANKS_RE.sub("\n\n", text).strip()


def _title_from_html(html: str) -> str:
    """Pull the document title with a regex rather than a second parse.

    ``trafilatura.extract_metadata`` gives a better title, but it costs a
    FULL second lxml parse of the document: profiled over ten Wikipedia
    articles, dropping it took extraction from 6.7s to 4.1s. A ``<title>`` tag
    is good enough for a source label, and the SERP title is there as a
    fallback when the tag is missing.
    """
    match = re.search(r"<title[^>]*>(.*?)</title>", html[:65_536], re.S | re.I)
    if not match:
        return ""
    from html import unescape

    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", match.group(1)))).strip()


def _extract_sync(html: str, url: str) -> tuple[str, str]:
    """Return ``(title, text)`` from HTML. Runs on the dedicated extract thread.

    trafilatura is the good path. The regex fallback is deliberately crude and
    exists so that a missing optional dependency degrades the answer instead
    of removing the feature.
    """
    title = _title_from_html(html)
    try:
        import trafilatura

        extracted = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
        if extracted:
            return title, clean_text(extracted)
    except ImportError:
        logger.debug("trafilatura not installed; falling back to regex extraction")
    except Exception as exc:  # noqa: BLE001 - never let one page kill a run
        logger.debug("trafilatura failed on %s: %s", url, exc)

    stripped = re.sub(r"<(script|style|noscript|svg|nav|footer|header)[^>]*>.*?</\1>",
                      " ", html, flags=re.S | re.I)
    stripped = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</h[1-6]>", "\n", stripped, flags=re.I)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    from html import unescape

    return title, clean_text(unescape(stripped))


class PageFetcher:
    """Fetches and extracts pages, in parallel, with a reader-proxy fallback."""

    def __init__(
        self,
        *,
        concurrency: Optional[int] = None,
        per_url_timeout: Optional[int] = None,
    ) -> None:
        self._concurrency = concurrency or _int_env(
            "SEARCH_FETCH_CONCURRENCY", 10, low=1, high=24
        )
        self._timeout = per_url_timeout or _int_env(
            "SEARCH_FETCH_TIMEOUT", 8, low=3, high=30
        )
        # r.jina.ai renders the page and returns clean markdown, which gets us
        # past the ~25% of sites that refuse a plain client. Opt-out because it
        # sends the target URL to a third party.
        self._reader_enabled = _env("SEARCH_READER_FALLBACK", "1").lower() not in {
            "0", "false", "no", "off",
        }
        self._reader_base = _env("SEARCH_READER_BASE", "https://r.jina.ai/")

    async def fetch_many(
        self,
        hits: Sequence[SearchHit],
        *,
        limit: Optional[int] = None,
    ) -> List[ExtractedPage]:
        """Fetch and extract up to ``limit`` hits concurrently.

        Returns one :class:`ExtractedPage` per input hit, in the input order,
        including failures -- the caller decides whether a snippet-only source
        still deserves a citation.
        """
        import aiohttp

        selected = list(hits)[: limit or len(hits)]
        if not selected:
            return []

        semaphore = asyncio.Semaphore(self._concurrency)
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        headers = {
            "User-Agent": _BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:

            async def one(hit: SearchHit) -> ExtractedPage:
                async with semaphore:
                    return await self._fetch_one(session, hit)

            pages = await asyncio.gather(
                *(one(hit) for hit in selected), return_exceptions=True
            )

        out: List[ExtractedPage] = []
        for hit, page in zip(selected, pages):
            if isinstance(page, ExtractedPage):
                out.append(page)
            else:
                out.append(
                    self._snippet_page(hit, error=f"{type(page).__name__}: {page}")
                )
        return out

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _snippet_page(hit: SearchHit, *, error: str) -> ExtractedPage:
        """Fall back to the SERP snippet so a blocked page still counts.

        A source we could not open is still a real URL the user can click, and
        the snippet is real text from the search engine. Marking it ``via
        snippet`` keeps the distinction honest in the stats rather than
        pretending the page was read.
        """
        snippet = clean_text(hit.snippet)
        return ExtractedPage(
            url=hit.url,
            title=hit.title,
            text=snippet,
            ok=bool(snippet),
            via="snippet" if snippet else "",
            error=error,
        )

    async def _fetch_one(self, session, hit: SearchHit) -> ExtractedPage:
        html, error = await self._get(session, hit.url)
        via = "direct"

        if html is None and self._reader_enabled:
            html, reader_error = await self._get(
                session, f"{self._reader_base}{hit.url}", reader=True
            )
            via = "reader"
            if html is None:
                error = f"{error}; reader: {reader_error}"

        if html is None:
            return self._snippet_page(hit, error=error or "fetch failed")

        loop = asyncio.get_running_loop()
        try:
            title, text = await loop.run_in_executor(
                _EXTRACT_POOL, _extract_sync, html, hit.url
            )
        except Exception as exc:  # noqa: BLE001
            return self._snippet_page(hit, error=f"extract failed: {exc}")

        # A page that yields almost nothing after extraction is a cookie wall
        # or a JS shell. The snippet is more useful than three words of chrome.
        if len(text) < 200:
            page = self._snippet_page(hit, error="extracted too little text")
            page.title = title or hit.title
            return page

        return ExtractedPage(
            url=hit.url,
            title=title or hit.title,
            text=text,
            ok=True,
            via=via,
        )

    async def _get(
        self, session, url: str, *, reader: bool = False
    ) -> tuple[Optional[str], str]:
        """GET a URL with a byte cap and a content-type guard."""
        try:
            async with session.get(url, allow_redirects=True, max_redirects=5) as resp:
                if resp.status >= 400:
                    return None, f"HTTP {resp.status}"
                content_type = (resp.headers.get("Content-Type") or "").lower()
                if content_type and not any(
                    marker in content_type for marker in _TEXT_CONTENT_TYPES
                ):
                    return None, f"unsupported content-type {content_type[:60]}"

                chunks: List[bytes] = []
                total = 0
                async for chunk in resp.content.iter_chunked(64 * 1024):
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= _MAX_BYTES:
                        break
                body = b"".join(chunks)

            encoding = "utf-8"
            match = re.search(rb'charset=["\']?([\w-]+)', body[:4096], re.I)
            if match:
                encoding = match.group(1).decode("ascii", "ignore") or "utf-8"
            try:
                return body.decode(encoding, "ignore"), ""
            except LookupError:
                return body.decode("utf-8", "ignore"), ""
        except asyncio.TimeoutError:
            return None, "timeout"
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"


def trim_pages(
    pages: Sequence[ExtractedPage],
    *,
    per_page_chars: int,
    total_chars: int,
) -> List[ExtractedPage]:
    """Trim extracted text to fit the writer's context window.

    Budget is shared fairly rather than first-come: giving one 200k-character
    page the whole allowance would silently drop the other eleven sources, and
    the point of reading a dozen pages is that the answer reflects a dozen
    pages. Short pages keep everything and hand their unused budget back.
    """
    usable = [page for page in pages if page.ok and page.text]
    if not usable:
        return []

    share = max(500, min(per_page_chars, total_chars // max(1, len(usable))))

    # Pages under their share release the difference for the longer ones.
    spare = sum(share - len(p.text) for p in usable if len(p.text) < share)
    long_pages = [p for p in usable if len(p.text) > share]
    bonus = spare // len(long_pages) if long_pages and spare > 0 else 0

    out: List[ExtractedPage] = []
    spent = 0
    for page in usable:
        allowance = share + (bonus if len(page.text) > share else 0)
        allowance = min(allowance, max(0, total_chars - spent))
        if allowance <= 0:
            break
        text = page.text
        if len(text) > allowance:
            # Budget the truncation marker too. Adding it after the cut let
            # every trimmed page overshoot its allowance, and with a dozen
            # pages that quietly pushed the bundle past the context budget the
            # caller asked for.
            marker = "\n[...]"
            room = max(0, allowance - len(marker))
            # Cut at a paragraph boundary when one is close, so the writer does
            # not see a sentence sheared in half.
            cut = text.rfind("\n\n", 0, room)
            text = text[: cut if cut > room * 0.6 else room].rstrip() + marker
        spent += len(text)
        out.append(
            ExtractedPage(
                url=page.url,
                title=page.title,
                text=text,
                ok=True,
                via=page.via,
            )
        )
    return out
