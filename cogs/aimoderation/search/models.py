"""Value types passed between the search harness stages.

Deliberately plain dataclasses with no I/O: every ranking, dedupe, trimming,
and citation decision in this package operates on these and is therefore
unit-testable without a network.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

# Query parameters that identify a campaign rather than a document. Two URLs
# differing only by these are the same page, and counting them separately
# wastes a fetch slot that could have gone to a distinct source.
_TRACKING_PARAMS = frozenset(
    {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "utm_id", "gclid", "fbclid", "msclkid", "mc_cid", "mc_eid", "ref",
        "ref_src", "source", "spm", "igshid", "_ga",
    }
)


def normalize_url(url: str) -> str:
    """Return a comparison key for deduplicating results across engines.

    Strips the fragment, tracking parameters, a trailing slash, and a leading
    ``www.``, and lowercases the host. The scheme is normalized to https so the
    same page served over both does not occupy two slots.
    """
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
    except ValueError:
        return raw
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if parts.port and parts.port not in (80, 443):
        host = f"{host}:{parts.port}"
    kept = [
        pair
        for pair in parts.query.split("&")
        if pair and pair.split("=", 1)[0].lower() not in _TRACKING_PARAMS
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", host, path, "&".join(sorted(kept)), ""))


def registrable_domain(url: str) -> str:
    """Return a coarse domain for authority scoring and per-site capping.

    Coarse on purpose: this is not a public-suffix implementation, it only
    needs to group ``en.wikipedia.org`` and ``wikipedia.org`` together well
    enough to stop one site occupying every fetch slot.
    """
    try:
        host = (urlsplit(url if "//" in url else f"https://{url}").hostname or "").lower()
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    bits = host.split(".")
    if len(bits) <= 2:
        return host
    # Handle the common two-part public suffixes without a full PSL.
    if bits[-2] in {"co", "com", "org", "net", "ac", "gov", "edu"} and len(bits[-1]) == 2:
        return ".".join(bits[-3:])
    return ".".join(bits[-2:])


@dataclass(slots=True)
class SearchHit:
    """One SERP result, before any page has been fetched."""

    url: str
    title: str = ""
    snippet: str = ""
    engine: str = ""
    # 1-based position within the result list this hit came from.
    position: int = 0
    # Which planned queries surfaced this URL. A page found by several
    # different sub-questions is more likely to be central to the topic, so
    # this drives part of the ranking score.
    queries: Tuple[str, ...] = ()

    @property
    def key(self) -> str:
        return normalize_url(self.url)

    @property
    def domain(self) -> str:
        return registrable_domain(self.url)


@dataclass(slots=True)
class ExtractedPage:
    """A fetched and text-extracted page, or a record of why it failed.

    A failed fetch is still returned rather than dropped: its SERP snippet can
    carry the citation, and the pipeline reports honestly how many sources it
    actually read versus merely saw.
    """

    url: str
    title: str = ""
    text: str = ""
    ok: bool = False
    # "direct", "reader", or "snippet" -- how the text was obtained. Surfaced
    # in stats so a run degrading to snippets is visible rather than silent.
    via: str = ""
    error: str = ""

    @property
    def domain(self) -> str:
        return registrable_domain(self.url)


@dataclass(slots=True)
class Source:
    """A numbered source as presented to the writer and cited in the answer."""

    index: int
    url: str
    title: str
    read: bool


@dataclass(slots=True)
class HarnessResult:
    """What a lane hands back to ``converse()``."""

    answer: str
    sources: List[Source] = field(default_factory=list)
    stats: Dict[str, object] = field(default_factory=dict)

    @property
    def source_urls(self) -> List[str]:
        return [source.url for source in self.sources]

    @property
    def ok(self) -> bool:
        return bool(self.answer.strip())


@dataclass(slots=True)
class ResearchPlan:
    """The planner's decomposition of a research question."""

    sub_questions: List[str] = field(default_factory=list)
    queries: List[str] = field(default_factory=list)
    # Domains the planner considers authoritative for THIS topic (e.g. the
    # vendor's own site for a product question). Boosted during ranking.
    authoritative_domains: List[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return bool(self.queries)


@dataclass(slots=True)
class ProgressUpdate:
    """One step of the research funnel, for the live Discord embed."""

    stage: str
    detail: str = ""
    found: Optional[int] = None
    reading: Optional[int] = None
