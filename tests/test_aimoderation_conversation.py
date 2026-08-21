"""``converse`` lane selection and terminal behavior, with no network.

These exist because collapsing to a single provider removed every fallback
that used to sit under ``converse``. That is the point of the change, but it
also means the OpenRouter lane selection is now the whole conversation path:
if it picks the wrong lane, or returns ``None`` where it used to fall through,
there is nothing downstream to paper over it. A user just sees silence.

Every lane is stubbed, so a failure here is a routing regression, never a
vendor outage. ``tests/test_aimoderation_live.py`` covers the vendor.
"""
from __future__ import annotations

import asyncio
import types as _types
from unittest.mock import AsyncMock, MagicMock

import pytest

import cogs.aimoderation.ai_client as ai_client
from cogs.aimoderation.ai_client import AIClient
from cogs.aimoderation.types import AIConfig, ConversationMode, ConversationSignals


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(ai_client, "_OPENROUTER_API_KEY", "sk-or-v1-real")
    monkeypatch.setattr(ai_client, "_OPENROUTER_CHAT_MODEL", "vendor/talk")
    # No db attribute, so memory loads return "" instead of touching a database.
    bot = _types.SimpleNamespace(user=None, loop=None, session=None)
    instance = AIClient(bot, AIConfig())
    # A turn carrying no images: keep the attachment download out of the test.
    monkeypatch.setattr(instance, "_collect_image_context", AsyncMock(return_value=[]))
    # Memory persistence is fire-and-forget and needs a running loop + database.
    monkeypatch.setattr(instance, "_schedule_memory_update", MagicMock())
    return instance


@pytest.fixture
def guild():
    g = MagicMock()
    g.id, g.name, g.member_count = 111, "Test Guild", 50
    for attr in ("roles", "channels", "categories", "text_channels", "voice_channels", "emojis"):
        setattr(g, attr, [])
    return g


@pytest.fixture
def author():
    a = MagicMock()
    a.id, a.name, a.display_name, a.bot = 222, "tester", "tester", False
    a.mention, a.roles = "<@222>", []
    return a


def signals_for(mode=ConversationMode.STANDARD, *, requires_web_search=False):
    return ConversationSignals(
        mode=mode,
        confidence=1.0,
        show_research_indicator=False,
        asks_for_current_info=False,
        asks_for_sources=False,
        asks_for_long_answer=False,
        mentions_moderation=False,
        requires_web_search=requires_web_search,
    )


def converse(client, guild, author, *, signals, content="hello there"):
    return run(
        client.converse(
            user_content=content,
            guild=guild,
            author=author,
            recent_messages=[],
            signals=signals,
        )
    )


def test_ordinary_talking_uses_the_talking_lane(client, guild, author, monkeypatch):
    """Casual chat must not reach the searched lane.

    The talking lane sends no tools and no images; routing casual chat through
    the searched lane instead spends a web search on "hello" and answers in the
    wrong voice.
    """
    talk = AsyncMock(return_value="hey")
    search = AsyncMock(return_value="searched answer")
    monkeypatch.setattr(client, "_call_openrouter_chat", talk)
    monkeypatch.setattr(client, "_call_openrouter_conversation", search)

    reply = converse(client, guild, author, signals=signals_for())

    assert reply == "hey"
    assert talk.await_count == 1
    assert search.await_count == 0


def test_a_turn_needing_current_info_uses_the_searched_lane(client, guild, author, monkeypatch):
    talk = AsyncMock(return_value="stale answer")
    search = AsyncMock(return_value="searched answer")
    monkeypatch.setattr(client, "_call_openrouter_chat", talk)
    monkeypatch.setattr(client, "_call_openrouter_conversation", search)

    reply = converse(
        client, guild, author, signals=signals_for(requires_web_search=True)
    )

    assert reply == "searched answer"
    assert search.await_count == 1
    assert talk.await_count == 0


def test_a_failed_lane_says_so_instead_of_going_silent(client, guild, author, monkeypatch):
    """There is no provider left to fall through to, so say something.

    Returning ``None`` here is what the cog renders as no reply at all, which
    reads to a member as the bot ignoring them rather than as an outage.
    """
    monkeypatch.setattr(
        client,
        "_call_openrouter_chat",
        AsyncMock(side_effect=RuntimeError("upstream 500")),
    )

    reply = converse(client, guild, author, signals=signals_for())

    assert reply
    assert "failed" in reply.lower()


def test_research_without_sources_is_refused_not_answered(client, guild, author, monkeypatch):
    """An unsourced research answer must be refused, not dressed up as sourced.

    The pre-fetch is what supplies verifiable links; when both it and the
    searched lane come back empty there is nothing to cite.
    """
    monkeypatch.setattr(
        client, "_prefetch_research_context", AsyncMock(return_value=("", []))
    )
    monkeypatch.setattr(
        client, "_call_openrouter_conversation", AsyncMock(return_value=None)
    )

    reply = converse(
        client, guild, author, signals=signals_for(ConversationMode.RESEARCH)
    )

    assert reply == ai_client._RESEARCH_UNAVAILABLE


def test_research_with_prefetched_evidence_uses_the_writer(client, guild, author, monkeypatch):
    """Sonar gathers, the writer writes. Sonar is a search product, not a writer."""
    monkeypatch.setattr(
        client,
        "_prefetch_research_context",
        AsyncMock(return_value=("evidence body", ["https://example.com/a"])),
    )
    writer = AsyncMock(return_value="the report")
    search = AsyncMock(return_value="search lane answer")
    monkeypatch.setattr(client, "_call_openrouter_research_writer", writer)
    monkeypatch.setattr(client, "_call_openrouter_conversation", search)

    reply = converse(
        client, guild, author, signals=signals_for(ConversationMode.RESEARCH)
    )

    assert writer.await_count == 1
    assert search.await_count == 0
    assert reply and "the report" in reply
    # The gate must attach the pre-fetched links, or a good answer is refused.
    assert "https://example.com/a" in reply


def test_no_key_reports_the_outage_rather_than_answering(guild, author, monkeypatch):
    monkeypatch.setattr(ai_client, "_OPENROUTER_API_KEY", "")
    client = AIClient(_types.SimpleNamespace(user=None, loop=None), AIConfig())

    reply = converse(client, guild, author, signals=signals_for())

    assert "OPENROUTER_API_KEY" in reply
