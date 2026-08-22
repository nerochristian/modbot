"""Dedupe and rank SERP hits into the shortlist that actually gets fetched.

Fetching is the expensive, slow, rate-limited part of the harness, so which
twelve URLs out of seventy get read is the single highest-leverage decision in
the pipeline. Position in one engine's result list is not enough on its own.

Three signals, in rough order of value:

1. **Authority tier.** Asked "what's in the latest Genshin update", the
   official HoYoverse post beats ten aggregator blogs that paraphrase it.
   Tiering is what stops the shortlist filling up with SEO chaff.
2. **Query coverage.** A URL surfaced by three different sub-questions is
   probably central to the topic; one surfaced by a single narrow query
   probably answers only that corner of it.
3. **Result position.** Useful, but the weakest of the three -- it is the
   engine's guess at relevance for one phrasing.

Plus a per-domain cap, because eight pages from one site is one source wearing
eight hats, and the whole point of reading widely is disagreement between
sources.

Pure functions over dataclasses: no network, no models, fully unit-testable.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Sequence, Set

from .models import SearchHit, registrable_domain

# Tier 1: primary and institutional sources. Government, standards bodies,
# academic, and the canonical developer references.
_TIER_ONE_SUFFIXES = (".gov", ".mil", ".edu", ".ac.uk", ".gov.uk", ".int")
_TIER_ONE_DOMAINS = frozenset(
    {
        "who.int", "europa.eu", "un.org", "nasa.gov", "nih.gov",
        "iso.org", "ietf.org", "rfc-editor.org", "w3.org", "unicode.org",
        "python.org", "docs.python.org", "developer.mozilla.org",
        "kernel.org", "postgresql.org", "sqlite.org",
    }
)

# Tier 2: established outlets and reference works with editorial standards.
_TIER_TWO_DOMAINS = frozenset(
    {
        "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "npr.org",
        "nytimes.com", "washingtonpost.com", "wsj.com", "ft.com",
        "theguardian.com", "economist.com", "bloomberg.com", "cnbc.com",
        "arstechnica.com", "theverge.com", "wired.com", "techcrunch.com",
        "nature.com", "science.org", "scientificamerican.com",
        "espn.com", "apnews.org", "aljazeera.com", "dw.com",
    }
)

# Tier 3: useful but derivative -- crowd-edited, aggregated, or Q&A.
_TIER_THREE_DOMAINS = frozenset(
    {
        "wikipedia.org", "wikimedia.org", "fandom.com", "wikia.com",
        "stackoverflow.com", "stackexchange.com", "superuser.com",
        "serverfault.com", "github.com", "gitlab.com",
        "investopedia.com", "britannica.com", "imdb.com",
    }
)

# Tier 5: content farms and engagement bait. Not banned -- sometimes they are
# genuinely the only coverage -- but they lose every tie.
_TIER_FIVE_DOMAINS = frozenset(
    {
        "pinterest.com", "quora.com", "answers.com", "ehow.com",
        "wikihow.com", "medium.com", "substack.com", "blogspot.com",
        "wordpress.com", "tumblr.com", "facebook.com", "x.com",
        "twitter.com", "tiktok.com", "instagram.com",
    }
)

#: Score contribution per tier. Tier 4 (1.0) is the unclassified default: an
#: ordinary site that is neither vouched for nor suspect.
_TIER_WEIGHTS = {1: 3.0, 2: 2.2, 3: 1.5, 4: 1.0, 5: 0.4}

# Paths that are navigation rather than content. A search engine will happily
# return a site's tag index; there is nothing to read there.
_LOW_VALUE_PATH_RE = re.compile(
    r"/(tag|tags|category|categories|author|search|page)/|/(login|signin|signup|register)\b",
    re.IGNORECASE,
)

# File types the fetcher cannot extract article text from.
_BINARY_EXT_RE = re.compile(
    r"\.(pdf|zip|gz|tar|rar|7z|mp4|mp3|wav|avi|mov|webm|png|jpe?g|gif|svg|webp|ico|exe|dmg|apk)(\?|$)",
    re.IGNORECASE,
)


def authority_tier(url: str, *, preferred_domains: Sequence[str] = ()) -> int:
    """Classify a URL into an authority tier from 1 (best) to 5 (worst).

    ``preferred_domains`` comes from the research planner, which names the
    domains that are authoritative for THIS question -- a vendor's own site for
    a product query, a league's site for a sports one. Those are promoted to
    tier 1, because topic-specific authority beats any static list.
    """
    domain = registrable_domain(url)
    if not domain:
        return 4

    for preferred in preferred_domains:
        candidate = registrable_domain(preferred) or (preferred or "").strip().lower()
        if candidate and (domain == candidate or domain.endswith(f".{candidate}")):
            return 1

    if domain in _TIER_ONE_DOMAINS or domain.endswith(_TIER_ONE_SUFFIXES):
        return 1
    if domain in _TIER_TWO_DOMAINS:
        return 2
    if domain in _TIER_THREE_DOMAINS or domain.endswith(".wikipedia.org"):
        return 3
    if domain in _TIER_FIVE_DOMAINS:
        return 5
    return 4


def is_fetchable(url: str) -> bool:
    """Whether this URL is worth spending a fetch slot on."""
    if not url.startswith(("http://", "https://")):
        return False
    if _BINARY_EXT_RE.search(url):
        return False
    if _LOW_VALUE_PATH_RE.search(url):
        return False
    return True


def merge_hits(results: Dict[str, List[SearchHit]]) -> List[SearchHit]:
    """Collapse per-query result lists into one deduplicated list.

    A URL found by several queries keeps its BEST position and accumulates the
    queries that found it, which is what makes coverage scoring possible.
    """
    merged: Dict[str, SearchHit] = {}
    for query, hits in results.items():
        for hit in hits:
            key = hit.key
            if not key:
                continue
            existing = merged.get(key)
            if existing is None:
                merged[key] = SearchHit(
                    url=hit.url,
                    title=hit.title,
                    snippet=hit.snippet,
                    engine=hit.engine,
                    position=hit.position,
                    queries=tuple(hit.queries or (query,)),
                )
                continue
            queries = set(existing.queries) | set(hit.queries or (query,))
            existing.queries = tuple(sorted(queries))
            if hit.position and (not existing.position or hit.position < existing.position):
                existing.position = hit.position
            if len(hit.snippet) > len(existing.snippet):
                existing.snippet = hit.snippet
            if not existing.title and hit.title:
                existing.title = hit.title
            if hit.engine and hit.engine not in existing.engine:
                existing.engine = f"{existing.engine}+{hit.engine}"
    return list(merged.values())


def score_hit(
    hit: SearchHit,
    *,
    total_queries: int,
    preferred_domains: Sequence[str] = (),
) -> float:
    """Score one hit. Higher is better."""
    tier = authority_tier(hit.url, preferred_domains=preferred_domains)
    tier_weight = _TIER_WEIGHTS.get(tier, 1.0)

    # Coverage: 1.0 for a URL every query found, scaling down to ~0.3 for one.
    coverage = len(hit.queries) / max(1, total_queries)
    coverage_weight = 0.3 + 0.7 * min(1.0, coverage)

    # Position: 1.0 at rank 1, decaying gently. Never zero -- a rank-9 result
    # from an official source should still beat a rank-1 content farm.
    position = hit.position or 10
    position_weight = 1.0 / (1.0 + 0.12 * max(0, position - 1))

    return tier_weight * coverage_weight * position_weight


def rank_hits(
    results: Dict[str, List[SearchHit]],
    *,
    limit: int,
    preferred_domains: Sequence[str] = (),
    per_domain_cap: int = 2,
) -> List[SearchHit]:
    """Return the best ``limit`` hits to fetch, at most ``per_domain_cap`` per site.

    The domain cap is applied as a first pass and then relaxed: if capping
    leaves fewer than ``limit`` hits, the best of the overflow is added back,
    because twelve pages from six domains beats eight pages from six domains.
    """
    merged = [hit for hit in merge_hits(results) if is_fetchable(hit.url)]
    if not merged:
        return []

    total_queries = max(1, len({q for hit in merged for q in hit.queries}))
    ordered = sorted(
        merged,
        key=lambda hit: score_hit(
            hit, total_queries=total_queries, preferred_domains=preferred_domains
        ),
        reverse=True,
    )

    chosen: List[SearchHit] = []
    overflow: List[SearchHit] = []
    per_domain: Dict[str, int] = {}
    for hit in ordered:
        domain = hit.domain or hit.key
        if per_domain.get(domain, 0) >= per_domain_cap:
            overflow.append(hit)
            continue
        per_domain[domain] = per_domain.get(domain, 0) + 1
        chosen.append(hit)
        if len(chosen) >= limit:
            return chosen

    for hit in overflow:
        if len(chosen) >= limit:
            break
        chosen.append(hit)
    return chosen[:limit]
