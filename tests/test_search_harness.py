"""The search harness's pure logic, with no network.

Everything here runs offline against fakes, because the decisions that matter
are not "did the HTTP call work" but "which twelve URLs out of seventy did we
choose to read, and does every [n] in the answer point at a real page".

Three properties are load-bearing enough to pin down:

* **Ranking picks the right pages.** Fetching is the slow, metered part of a
  run, so which URLs get a slot is the highest-leverage decision in the
  pipeline. Position alone is not good enough.
* **Citations resolve.** ``[3]`` must mean the third source, always. If the
  numbering can drift from the source list, every citation in every research
  reply is quietly untrustworthy.
* **Failures degrade rather than vanish.** A blocked page still counts as a
  source via its snippet; a dead backend hands off to the next one.
"""
from __future__ import annotations

import asyncio
import re

import pytest

from cogs.aimoderation.search.backends import BackendChain, SearchBackend, _parse_ddg_html
from cogs.aimoderation.search.budget import (
    BackendHealth,
    ResultCache,
    TokenBucket,
    cache_key,
)
from cogs.aimoderation.search.fetch import clean_text, trim_pages
from cogs.aimoderation.search.models import (
    ExtractedPage,
    SearchHit,
    normalize_url,
    registrable_domain,
)
from cogs.aimoderation.search.pipeline import build_source_block, parse_plan
from cogs.aimoderation.search.rank import (
    authority_tier,
    is_fetchable,
    merge_hits,
    rank_hits,
)


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def hit(url, *, position=1, queries=("q",), snippet="", title=""):
    return SearchHit(
        url=url, position=position, queries=queries, snippet=snippet, title=title
    )


# --- URL identity ----------------------------------------------------------


@pytest.mark.parametrize(
    "a,b",
    [
        ("http://example.com/a", "https://www.example.com/a/"),
        ("https://example.com/a?utm_source=x", "https://example.com/a"),
        ("https://example.com/a#frag", "https://example.com/a"),
        ("https://example.com/a?b=1&c=2", "https://example.com/a?c=2&b=1"),
    ],
)
def test_the_same_page_is_recognised_as_one_source(a, b):
    """Engines return the same page in different clothes.

    Counting those separately wastes a fetch slot that could have gone to a
    genuinely different source, and inflates "found N pages" with duplicates.
    """
    assert normalize_url(a) == normalize_url(b)


def test_different_pages_stay_different():
    assert normalize_url("https://example.com/a") != normalize_url("https://example.com/b")


def test_subdomains_group_under_one_site():
    assert registrable_domain("https://en.wikipedia.org/wiki/X") == "wikipedia.org"
    assert registrable_domain("https://foo.bar.co.uk/x") == "bar.co.uk"


# --- ranking ---------------------------------------------------------------


def test_authority_beats_position():
    """A rank-1 content farm must lose to a rank-5 primary source.

    This is the whole reason ranking is not just "trust the engine": asked
    about a game patch, the official notes at rank 5 are worth more than five
    aggregator blogs above them.
    """
    ranked = rank_hits(
        {
            "q": [
                hit("https://quora.com/a", position=1),
                hit("https://www.federalreserve.gov/news", position=5),
            ]
        },
        limit=2,
    )
    assert "federalreserve.gov" in ranked[0].url


def test_the_planner_can_name_the_authority_for_this_topic():
    """Topic-specific authority beats any static list.

    For "what's in the new update", the vendor's own site is the primary
    source even though no general-purpose tier list has heard of it.
    """
    assert authority_tier("https://www.hoyoverse.com/news") == 4
    assert authority_tier(
        "https://www.hoyoverse.com/news", preferred_domains=["hoyoverse.com"]
    ) == 1


def test_a_page_several_questions_found_outranks_one_they_did_not():
    """Query coverage is evidence of centrality to the topic."""
    ranked = rank_hits(
        {
            "q1": [hit("https://a.example/x", position=3, queries=("q1",))],
            "q2": [hit("https://a.example/x", position=4, queries=("q2",))],
            "q3": [hit("https://b.example/y", position=1, queries=("q3",))],
        },
        limit=2,
    )
    assert ranked[0].url == "https://a.example/x"
    assert len(ranked[0].queries) == 2


def test_one_site_cannot_take_every_slot():
    """Twelve pages from one domain is one source wearing twelve hats.

    Reading widely is the point; disagreement between sources is what the
    writer is asked to surface, and a single site never disagrees with itself.
    """
    results = {
        "q": [hit(f"https://same.example/{i}", position=i) for i in range(1, 9)]
        + [hit("https://other.example/x", position=20)]
    }
    ranked = rank_hits(results, limit=4, per_domain_cap=2)
    assert sum(1 for h in ranked if "other.example" in h.url) == 1
    # The cap relaxes rather than returning a short list.
    assert len(ranked) == 4


def test_unreadable_urls_never_take_a_fetch_slot():
    """A PDF or a tag index burns a slot and yields no article text."""
    assert not is_fetchable("https://a.example/report.pdf")
    assert not is_fetchable("https://a.example/tag/python")
    assert not is_fetchable("https://a.example/image.jpg")
    assert is_fetchable("https://a.example/news/story")


def test_merging_keeps_the_best_position_and_all_queries():
    merged = merge_hits(
        {
            "q1": [hit("https://a.example/x", position=7, queries=("q1",), snippet="s")],
            "q2": [
                hit(
                    "https://www.a.example/x/",
                    position=2,
                    queries=("q2",),
                    snippet="a longer snippet",
                    title="T",
                )
            ],
        }
    )
    assert len(merged) == 1
    assert merged[0].position == 2
    assert set(merged[0].queries) == {"q1", "q2"}
    # The richer snippet and the title both survive the merge.
    assert merged[0].snippet == "a longer snippet"
    assert merged[0].title == "T"


# --- citation contract -----------------------------------------------------


def test_every_citation_number_resolves_to_its_source():
    """``[3]`` must be the third source. Always.

    The writer is told to cite by number against this block, so if the
    numbering could drift from the returned source list, every citation in
    every research reply would be silently wrong.
    """
    pages = [
        ExtractedPage(url=f"https://s{i}.example/a", title=f"T{i}", text=f"body {i}",
                      ok=True, via="direct")
        for i in range(1, 6)
    ]
    block, sources = build_source_block(pages)

    numbers = [int(n) for n in re.findall(r"^\[(\d+)\]", block, re.MULTILINE)]
    assert numbers == [1, 2, 3, 4, 5]
    assert [s.index for s in sources] == [1, 2, 3, 4, 5]
    for source in sources:
        assert f"[{source.index}]" in block
        assert source.url in block


def test_a_snippet_only_source_is_labelled_as_unread():
    """The bot must not imply it read a page it could not open.

    Roughly a quarter of sites refuse a plain client. Their snippet is still a
    real citation, but the writer is told which ones they are, and ``read``
    records it honestly for the stats.
    """
    pages = [
        ExtractedPage(url="https://a.example/x", text="full text", ok=True, via="direct"),
        ExtractedPage(url="https://b.example/y", text="snippet", ok=True, via="snippet"),
    ]
    block, sources = build_source_block(pages)
    assert sources[0].read is True
    assert sources[1].read is False
    assert "could not be opened" in block


# --- context budget --------------------------------------------------------


def test_the_source_budget_is_shared_not_taken_first_come():
    """One enormous page must not crowd out eleven others.

    Reading a dozen sites is pointless if the first one eats the whole context
    window and the writer never sees the rest.
    """
    pages = [
        ExtractedPage(url="https://big.example/a", text="x" * 200_000, ok=True, via="direct"),
        *[
            ExtractedPage(url=f"https://s{i}.example/a", text="y" * 3_000, ok=True,
                          via="direct")
            for i in range(2, 8)
        ],
    ]
    trimmed = trim_pages(pages, per_page_chars=4_000, total_chars=20_000)

    assert len(trimmed) == 7, "every source should survive"
    assert sum(len(p.text) for p in trimmed) <= 20_000
    assert len(trimmed[0].text) < 20_000


def test_short_pages_keep_all_their_text():
    pages = [
        ExtractedPage(url=f"https://s{i}.example/a", text="z" * 500, ok=True, via="direct")
        for i in range(3)
    ]
    trimmed = trim_pages(pages, per_page_chars=4_000, total_chars=50_000)
    assert [len(p.text) for p in trimmed] == [500, 500, 500]


def test_failed_pages_are_dropped_from_the_writer_bundle():
    pages = [
        ExtractedPage(url="https://a.example/x", text="", ok=False, error="HTTP 403"),
        ExtractedPage(url="https://b.example/y", text="real", ok=True, via="direct"),
    ]
    assert [p.url for p in trim_pages(pages, per_page_chars=100, total_chars=1_000)] == [
        "https://b.example/y"
    ]


def test_clean_text_keeps_paragraphs_but_collapses_noise():
    assert clean_text("a  \t b\n\n\n\nc   \n") == "a b\n\nc"


# --- planner ---------------------------------------------------------------


def test_a_failed_plan_still_searches_the_question():
    """Losing the planner must cost quality, never the turn."""
    plan = parse_plan(None, question="how tall is the eiffel tower")
    assert plan.queries == ["how tall is the eiffel tower"]
    assert plan.usable


def test_a_plan_is_capped_and_deduplicated():
    plan = parse_plan(
        {
            "queries": ["a", "a", "b", "c", "d", "e", "f", "g"],
            "sub_questions": ["one"],
            "authoritative_domains": ["*.Example.COM"],
        },
        question="q",
    )
    assert plan.queries == ["a", "b", "c", "d", "e"]
    assert plan.authoritative_domains == ["example.com"]


# --- backend chain ---------------------------------------------------------


class FakeBackend(SearchBackend):
    def __init__(self, name, results, *, cache, health, configured=True):
        super().__init__(cache=cache, health=health)
        self.name = name
        self._results = results
        self._configured = configured
        self.calls = 0

    def configured(self):
        return self._configured

    async def _search_batch(self, queries, *, count):
        self.calls += 1
        if isinstance(self._results, Exception):
            raise self._results
        return {q: self._results.get(q, []) for q in queries}


def _fresh():
    return ResultCache(ttl_seconds=60), BackendHealth(name="x")


def test_a_dead_backend_hands_off_to_the_next_one():
    """The entire point of a chain is that there is somewhere else to go."""
    cache, _ = _fresh()
    dead = FakeBackend("dead", RuntimeError("boom"), cache=cache,
                       health=BackendHealth(name="dead"))
    alive = FakeBackend("alive", {"q": [hit("https://a.example/x")]}, cache=cache,
                        health=BackendHealth(name="alive"))

    got = run(BackendChain([dead, alive]).search(["q"]))

    assert [h.url for h in got["q"]] == ["https://a.example/x"]
    assert alive.calls == 1


def test_a_partial_answer_is_topped_up_rather_than_discarded():
    """One backend answering half the queries should not waste that half."""
    cache, _ = _fresh()
    partial = FakeBackend("partial", {"q1": [hit("https://a.example/1")]}, cache=cache,
                          health=BackendHealth(name="partial"))
    rest = FakeBackend("rest", {"q2": [hit("https://b.example/2")]}, cache=cache,
                       health=BackendHealth(name="rest"))

    got = run(BackendChain([partial, rest]).search(["q1", "q2"]))

    assert got["q1"] and got["q2"]


def test_an_unconfigured_backend_is_skipped_silently():
    cache, _ = _fresh()
    unset = FakeBackend("unset", {}, cache=cache, health=BackendHealth(name="unset"),
                        configured=False)
    alive = FakeBackend("alive", {"q": [hit("https://a.example/x")]}, cache=cache,
                        health=BackendHealth(name="alive"))

    run(BackendChain([unset, alive]).search(["q"]))

    assert unset.calls == 0 and alive.calls == 1


def test_the_cache_stops_a_repeat_query_costing_a_second_call():
    """Research fires several queries and users repeat questions.

    The cache is the single biggest protection on a metered free tier, because
    it works across lanes, users and guilds.
    """
    cache, health = _fresh()
    backend = FakeBackend("b", {"q": [hit("https://a.example/x")]}, cache=cache,
                          health=health)

    run(backend.search(["q"]))
    run(backend.search(["q"]))

    assert backend.calls == 1
    assert cache.hits == 1


# --- credit protection -----------------------------------------------------


def test_a_backend_stops_being_used_before_its_quota_runs_out():
    """Fail over BEFORE the credits are gone, not after.

    Discovering exhaustion by getting an error mid-answer means the user sees
    the failure; failing over early means they just see a slightly worse
    source list.
    """
    health = BackendHealth(name="metered", quota=2)
    assert health.available()
    health.record_success()
    health.record_success()
    assert not health.available()
    assert "quota" in health.unavailable_reason()


def test_repeated_failures_open_the_circuit():
    """A dead backend must not be re-probed on every query of a run."""
    health = BackendHealth(name="flaky", trip_after=2)
    health.record_failure("boom")
    assert health.available()
    health.record_failure("boom")
    assert not health.available()
    assert "circuit open" in health.unavailable_reason()


def test_a_success_clears_the_failure_streak():
    health = BackendHealth(name="flaky", trip_after=2)
    health.record_failure("blip")
    health.record_success()
    health.record_failure("blip")
    assert health.available(), "one old failure must not compound with a new one"


def test_the_token_bucket_paces_requests():
    """DuckDuckGo answered with a 202 challenge after ~3 rapid requests.

    Spacing them is the difference between a usable free fallback and one that
    is challenged the moment it is needed.
    """
    bucket = TokenBucket(rate_per_second=50.0, burst=2)

    async def drain():
        loop = asyncio.get_running_loop()
        start = loop.time()
        for _ in range(5):
            await bucket.acquire()
        return loop.time() - start

    # 2 free from the burst, 3 more at 50/s => at least ~60ms of waiting.
    assert run(drain()) >= 0.05


def test_cache_keys_ignore_trivial_spelling_differences():
    assert cache_key("  Fed  RATE decision ", 10) == cache_key("fed rate decision", 10)
    assert cache_key("a", 10) != cache_key("a", 5)


# --- DDG parsing -----------------------------------------------------------


def test_ddg_results_are_unwrapped_from_the_redirect():
    """DDG hides targets behind /l/?uddg=. The redirect is not the source."""
    html = (
        '<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com'
        '%2Fstory&rut=abc">Story title</a>'
        '<a class="result__snippet">A snippet</a>'
    )
    hits = _parse_ddg_html(html, query="q", count=5)
    assert len(hits) == 1
    assert hits[0].url == "https://example.com/story"
    assert hits[0].title == "Story title"
    assert hits[0].snippet == "A snippet"
