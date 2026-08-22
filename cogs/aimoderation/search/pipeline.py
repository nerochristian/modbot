"""The two harness lanes: a light search and an ULTRA research run.

Both lanes end in the same place -- an answer whose every factual claim is
backed by a URL the bot actually opened -- but they are deliberately different
shapes:

**search** is one query, four pages, one synthesis call, no planner and no
progress UI. It has to feel like a chat reply, so its whole budget is about
four to six seconds.

**research** finds wide and reads narrow, which is the shape a good research
agent converges on: plan several angles, gather forty-odd candidate URLs,
rank them by authority, then actually read the best twelve to fifteen and
write from their text. Budget is 25-35 seconds behind a live progress embed,
because a silent thirty seconds reads as a broken bot.

The models never touch the network here. Sources come from
:mod:`.backends` and :mod:`.fetch`; the model's only job is to synthesize what
was gathered and cite it. That separation is what makes the citation gate in
``research.py`` meaningful: a URL in the source list is a page that returned
bytes, not a string a model produced.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from .fetch import PageFetcher, trim_pages
from .models import (
    ExtractedPage,
    HarnessResult,
    ProgressUpdate,
    ResearchPlan,
    SearchHit,
    Source,
)
from .rank import rank_hits

logger = logging.getLogger("ModBot.AIModeration.Search")

ProgressCallback = Callable[[ProgressUpdate], Awaitable[None]]


def _env_int(name: str, default: int, *, low: int, high: int) -> int:
    try:
        return max(low, min(high, int((os.getenv(name) or "").strip() or default)))
    except (TypeError, ValueError):
        return default


# --- prompts ---------------------------------------------------------------

_PLANNER_SYSTEM = """You plan a web research run. You do not answer the question.

Break the user's question into the angles that must be checked, then write the \
web search queries that would surface them.

Rules:
- 3 to 5 queries. Prefer FEWER, BROADER queries over many narrow ones: each \
query returns about ten results, so breadth comes from good phrasing, not \
query count.
- Write queries the way a person types them into Google. No boolean operators, \
no quotes unless the exact phrase matters, no site: filters.
- If the question is about a product, game, company, law, or event that has an \
official source, name that source's domain in authoritative_domains (e.g. \
"hoyoverse.com", "apple.com", "federalreserve.gov"). Bare domains only.
- If the question involves anything recent, put the current year in at least \
one query.
- sub_questions are for the writer's benefit: the specific things the final \
report must answer."""

_RESEARCH_SYSTEM = """You are writing a research report for a Discord reply, \
from sources that were just fetched and read for you.

Absolute rules:
- Use ONLY the SOURCES below. If they do not answer part of the question, say \
so plainly. Never fill a gap from memory.
- Cite every factual claim with [n], matching the numbered sources.
- Where sources CONTRADICT each other, say so explicitly and give both \
numbers. Do not silently pick one.
- Ignore sources that turned out to be irrelevant. You do not have to use all \
of them, and padding with a source that does not bear on the question makes \
the report worse.
- Prefer official and primary sources over aggregators when they disagree on \
a fact.
- Do not write a URL in the body. The bot attaches the source links itself.

Style: lead with the answer, then the detail that supports it. Use short \
headings and tight paragraphs. Be specific -- dates, numbers, names, versions. \
No filler preamble, no "in conclusion". Write like a well-informed person \
explaining it, not like a search engine."""

_SEARCH_SYSTEM = """You are answering a Discord question using pages that were \
just fetched for you.

Rules:
- Use ONLY the SOURCES below. If they do not answer it, say so.
- Cite facts with [n].
- Do not write URLs in the body; the bot attaches links itself.
- Be brief and direct -- a couple of short paragraphs at most. This is a chat \
reply, not a report. Lead with the answer.
- Note the date of the information if it matters for whether it is current."""

_PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "sub_questions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 6,
        },
        "queries": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 5,
        },
        "authoritative_domains": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 6,
        },
    },
    "required": ["sub_questions", "queries", "authoritative_domains"],
    "additionalProperties": False,
}


# --- helpers ---------------------------------------------------------------


async def _emit(progress: Optional[ProgressCallback], update: ProgressUpdate) -> None:
    """Report a stage, never letting a UI failure break the run."""
    if progress is None:
        return
    try:
        await progress(update)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Progress callback failed: %s", exc)


def build_source_block(pages: Sequence[ExtractedPage]) -> tuple[str, List[Source]]:
    """Render fetched pages as a numbered source block for the writer.

    The numbering here IS the citation contract: ``[3]`` in the answer means
    the third entry of this block, so the order must match the returned
    :class:`Source` list exactly.
    """
    chunks: List[str] = []
    sources: List[Source] = []
    for index, page in enumerate(pages, start=1):
        sources.append(
            Source(
                index=index,
                url=page.url,
                title=page.title or page.url,
                read=page.via in {"direct", "reader"},
            )
        )
        label = page.title or page.url
        chunks.append(
            f"[{index}] {label}\nURL: {page.url}\n"
            f"{'(search snippet only -- page could not be opened)' if page.via == 'snippet' else ''}"
            f"\n{page.text}".replace("\n\n\n", "\n\n")
        )
    return "\n\n---\n\n".join(chunks), sources


def parse_plan(payload: Optional[Dict[str, Any]], *, question: str) -> ResearchPlan:
    """Turn the planner's JSON into a plan, falling back to the raw question.

    A failed plan must not cost the turn: searching the user's own words is a
    worse plan than a good decomposition but a much better outcome than an
    error message.
    """
    if not isinstance(payload, dict):
        return ResearchPlan(sub_questions=[question], queries=[question])

    def _strings(key: str, cap: int) -> List[str]:
        raw = payload.get(key)
        if not isinstance(raw, list):
            return []
        out: List[str] = []
        for item in raw:
            text = str(item or "").strip()
            if text and text not in out:
                out.append(text)
            if len(out) >= cap:
                break
        return out

    queries = _strings("queries", 5)
    return ResearchPlan(
        sub_questions=_strings("sub_questions", 6) or [question],
        queries=queries or [question],
        authoritative_domains=[
            d.lower().lstrip("*.") for d in _strings("authoritative_domains", 6)
        ],
    )


# --- lanes -----------------------------------------------------------------


@dataclass(slots=True)
class Gathered:
    """Retrieval output: the numbered source block, ready to be written from.

    Retrieval and writing are split so ``converse()`` can do the writing
    itself, in the bot's own voice and system prompt, without paying for a
    second synthesis pass. :func:`run_search` and :func:`run_research` are the
    standalone wrappers that add a writer on top.
    """

    block: str = ""
    sources: List[Source] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.block and self.sources)


async def gather_search(
    *,
    question: str,
    chain: Any,
    fetcher: Optional[PageFetcher] = None,
) -> Gathered:
    """Retrieve for the light lane: one query, a handful of pages."""
    started = time.monotonic()
    pages_wanted = _env_int("SEARCH_PAGES", 4, low=1, high=8)
    results = await chain.search([question], count=_env_int("SEARCH_RESULTS", 6, low=3, high=20))
    found = sum(len(v) for v in results.values())
    hits = rank_hits(results, limit=pages_wanted, per_domain_cap=1)
    if not hits:
        return Gathered(stats={"lane": "search", "reason": "no search results"})

    fetcher = fetcher or PageFetcher()
    pages = await fetcher.fetch_many(hits, limit=pages_wanted)
    trimmed = trim_pages(
        pages,
        per_page_chars=_env_int("SEARCH_PAGE_CHARS", 3_000, low=500, high=20_000),
        total_chars=_env_int("SEARCH_TOTAL_CHARS", 12_000, low=2_000, high=60_000),
    )
    if not trimmed:
        return Gathered(stats={"lane": "search", "reason": "nothing extractable"})

    block, sources = build_source_block(trimmed)
    return Gathered(
        block=block,
        sources=sources,
        stats={
            "lane": "search",
            "found": found,
            "read": sum(1 for p in trimmed if p.via in {"direct", "reader"}),
            "sources": len(sources),
            "seconds": round(time.monotonic() - started, 1),
        },
    )


async def run_search(
    client: Any,
    *,
    question: str,
    chain: Any,
    fetcher: Optional[PageFetcher] = None,
) -> HarnessResult:
    """The light lane end to end, including synthesis."""
    from .. import settings

    gathered = await gather_search(question=question, chain=chain, fetcher=fetcher)
    if not gathered.ok:
        return HarnessResult(answer="", stats=gathered.stats)
    block, sources = gathered.block, gathered.sources
    answer = await client._call_legion_writer(
        [
            {"role": "system", "content": _SEARCH_SYSTEM},
            {"role": "user", "content": f"SOURCES:\n\n{block}\n\nQUESTION: {question}"},
        ],
        model=settings.setting("_LEGION_SEARCH_MODEL"),
        max_tokens=min(2_000, client.config.max_tokens_chat),
        label="search",
    )
    return HarnessResult(answer=answer or "", sources=sources, stats=gathered.stats)


async def gather_research(
    client: Any,
    *,
    question: str,
    chain: Any,
    fetcher: Optional[PageFetcher] = None,
    progress: Optional[ProgressCallback] = None,
) -> Gathered:
    """Retrieve for the ULTRA lane: plan, find wide, rank, read narrow."""
    from .. import settings

    started = time.monotonic()
    max_pages = _env_int("RESEARCH_MAX_PAGES", 14, low=4, high=30)
    min_read = _env_int("RESEARCH_MIN_PAGES", 6, low=1, high=20)

    # 1 - plan
    await _emit(progress, ProgressUpdate(stage="planning", detail="Working out what to check"))
    payload = await client._call_legion_structured(
        [
            {"role": "system", "content": _PLANNER_SYSTEM},
            {"role": "user", "content": question},
        ],
        model=settings.setting("_LEGION_RESEARCH_PLANNER_MODEL"),
        schema_name="research_plan",
        schema=_PLAN_SCHEMA,
        max_tokens=2_000,
        request_timeout=_env_int("RESEARCH_PLAN_TIMEOUT", 20, low=5, high=60),
        label="research planner",
    )
    plan = parse_plan(payload, question=question)
    logger.info("Research plan: %d queries %s", len(plan.queries), plan.queries)

    # 2 - fan out. Batch-native backends take the whole list in one call.
    await _emit(
        progress,
        ProgressUpdate(
            stage="searching",
            detail=f"Searching ({len(plan.queries)} quer{'y' if len(plan.queries) == 1 else 'ies'})",
        ),
    )
    results = await chain.search(
        plan.queries, count=_env_int("RESEARCH_RESULTS_PER_QUERY", 10, low=5, high=25)
    )
    found = sum(len(v) for v in results.values())
    if not found:
        return Gathered(stats={"lane": "research", "reason": "no search results"})

    # 3 - rank, then read the best
    hits = rank_hits(
        results,
        limit=max_pages,
        preferred_domains=plan.authoritative_domains,
        per_domain_cap=_env_int("RESEARCH_PER_DOMAIN", 2, low=1, high=5),
    )
    await _emit(
        progress,
        ProgressUpdate(stage="found", detail=f"Found {found} web pages", found=found),
    )
    await _emit(
        progress,
        ProgressUpdate(
            stage="reading", detail=f"Reading {len(hits)} pages", found=found, reading=len(hits)
        ),
    )

    fetcher = fetcher or PageFetcher()
    pages = await fetcher.fetch_many(hits, limit=max_pages)
    read_ok = [p for p in pages if p.via in {"direct", "reader"} and p.ok]

    # Too few real reads means the answer would rest on snippets. Say so in the
    # stats and let the caller degrade rather than dressing it up as research.
    degraded = len(read_ok) < min_read

    trimmed = trim_pages(
        pages,
        per_page_chars=_env_int("RESEARCH_PAGE_CHARS", 4_000, low=500, high=20_000),
        total_chars=_env_int("RESEARCH_TOTAL_CHARS", 50_000, low=5_000, high=120_000),
    )
    if not trimmed:
        return Gathered(stats={"lane": "research", "reason": "nothing extractable"})

    await _emit(progress, ProgressUpdate(stage="writing", detail="Writing it up"))
    block, sources = build_source_block(trimmed)
    return Gathered(
        block=block,
        sources=sources,
        stats={
            "lane": "research",
            "queries": len(plan.queries),
            "sub_questions": list(plan.sub_questions),
            "found": found,
            "shortlisted": len(hits),
            "read": len(read_ok),
            "snippet_only": sum(1 for p in trimmed if p.via == "snippet"),
            "sources": len(sources),
            "degraded": degraded,
            "seconds": round(time.monotonic() - started, 1),
        },
    )


async def run_research(
    client: Any,
    *,
    question: str,
    chain: Any,
    fetcher: Optional[PageFetcher] = None,
    progress: Optional[ProgressCallback] = None,
) -> HarnessResult:
    """The ULTRA lane end to end, including synthesis."""
    from .. import settings

    gathered = await gather_research(
        client, question=question, chain=chain, fetcher=fetcher, progress=progress
    )
    if not gathered.ok:
        return HarnessResult(answer="", stats=gathered.stats)

    outline = "\n".join(
        f"- {q}" for q in (gathered.stats.get("sub_questions") or [question])
    )
    answer = await client._call_legion_writer(
        [
            {"role": "system", "content": _RESEARCH_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"SOURCES:\n\n{gathered.block}\n\n"
                    f"QUESTION: {question}\n\n"
                    f"The report must answer:\n{outline}"
                ),
            },
        ],
        model=settings.setting("_LEGION_RESEARCH_WRITER_MODEL"),
        fallback_models=settings.setting("_LEGION_RESEARCH_WRITER_FALLBACK_MODELS", ()),
        max_tokens=max(4_000, client.config.max_tokens_chat),
        request_timeout=_env_int("RESEARCH_WRITE_TIMEOUT", 90, low=20, high=180),
        label="research writer",
    )
    return HarnessResult(
        answer=answer or "", sources=gathered.sources, stats=gathered.stats
    )
