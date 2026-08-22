"""``converse`` lane selection and terminal behavior, with no network.

These exist because collapsing to a single provider removed every fallback
that used to sit under ``converse``. That is the point of the change, but it
also means lane selection is now the whole conversation path: if it picks the
wrong lane, or returns ``None`` where it used to fall through, there is
nothing downstream to paper over it. A user just sees silence.

The lane split that matters most here is retrieval. The models cannot browse,
so ``_gather_web_context`` is the only thing that can produce a source URL --
which is what makes "research with no sources is refused" enforceable rather
than aspirational.

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
    monkeypatch.setattr(ai_client, "_LEGION_API_KEY", "sk-or-v1-real")
    monkeypatch.setattr(ai_client, "_LEGION_CHAT_MODEL", "vendor/talk")
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


def test_ordinary_talking_never_reaches_the_web(client, guild, author, monkeypatch):
    """Casual chat must not trigger retrieval.

    Search costs a SERP call against a metered free tier and several seconds of
    page fetching. Spending that on "hello" is both slow and, eventually,
    expensive.
    """
    talk = AsyncMock(return_value="hey")
    gather = AsyncMock(return_value=("", []))
    monkeypatch.setattr(client, "_call_legion_chat", talk)
    monkeypatch.setattr(client, "_gather_web_context", gather)

    reply = converse(client, guild, author, signals=signals_for())

    assert reply == "hey"
    assert talk.await_count == 1
    assert gather.await_count == 0


def test_a_search_turn_retrieves_then_answers_from_the_sources(
    client, guild, author, monkeypatch
):
    """The search lane gathers pages first, then writes from them.

    Retrieval and synthesis are separate on purpose: the model never browses,
    so the only way a source URL exists is that the harness fetched it.
    """
    talk = AsyncMock(return_value="answer citing [1]")
    gather = AsyncMock(return_value=("[1] a page\nURL: https://example.com/a", ["https://example.com/a"]))
    monkeypatch.setattr(client, "_call_legion_chat", talk)
    monkeypatch.setattr(client, "_gather_web_context", gather)

    reply = converse(
        client, guild, author, signals=signals_for(ConversationMode.SEARCH)
    )

    assert gather.await_count == 1
    # The light lane, not the deep one.
    assert gather.await_args.kwargs["deep"] is False
    assert talk.await_count == 1
    # The fetched page reached the prompt.
    prompt = talk.await_args.args[0][-1]["content"]
    assert "https://example.com/a" in prompt
    assert reply and "answer citing" in reply


def test_a_search_turn_still_answers_when_retrieval_comes_back_empty(
    client, guild, author, monkeypatch
):
    """A dead search backend degrades to chat rather than refusing.

    Unlike research, a search turn is usually a question the model can make a
    reasonable stab at. The prompt tells it to admit it could not check.
    """
    talk = AsyncMock(return_value="best guess, unverified")
    monkeypatch.setattr(client, "_call_legion_chat", talk)
    monkeypatch.setattr(client, "_gather_web_context", AsyncMock(return_value=("", [])))

    reply = converse(
        client, guild, author, signals=signals_for(ConversationMode.SEARCH)
    )

    assert reply == "best guess, unverified"


def test_a_failed_lane_says_so_instead_of_going_silent(client, guild, author, monkeypatch):
    """There is no provider left to fall through to, so say something.

    Returning ``None`` here is what the cog renders as no reply at all, which
    reads to a member as the bot ignoring them rather than as an outage.
    """
    monkeypatch.setattr(
        client,
        "_call_legion_chat",
        AsyncMock(side_effect=RuntimeError("upstream 500")),
    )

    reply = converse(client, guild, author, signals=signals_for())

    assert reply
    assert "failed" in reply.lower()


def test_research_without_sources_is_refused_not_answered(client, guild, author, monkeypatch):
    """An unsourced research answer must be refused, not dressed up as sourced.

    Retrieval is the ONLY thing that produces source links -- the model cannot
    browse. When it comes back empty there is nothing to cite, and answering
    from memory while calling it research is the exact failure this gate
    exists to prevent.
    """
    monkeypatch.setattr(client, "_gather_web_context", AsyncMock(return_value=("", [])))
    monkeypatch.setattr(client, "_call_legion_chat", AsyncMock(return_value=None))
    monkeypatch.setattr(client, "_call_legion_writer", AsyncMock(return_value=None))

    reply = converse(
        client, guild, author, signals=signals_for(ConversationMode.RESEARCH)
    )

    assert reply == ai_client._RESEARCH_UNAVAILABLE


def test_research_with_gathered_sources_uses_the_writer(client, guild, author, monkeypatch):
    """The harness gathers, the writer writes.

    Research goes to the writer model rather than the chat model because the
    writer measurably uses more of the sources it is handed -- 8/8 versus 6/8
    on the same bundle.
    """
    monkeypatch.setattr(
        client,
        "_gather_web_context",
        AsyncMock(return_value=("[1] evidence\nURL: https://example.com/a", ["https://example.com/a"])),
    )
    writer = AsyncMock(return_value="the report")
    talk = AsyncMock(return_value="chat lane answer")
    monkeypatch.setattr(client, "_call_legion_writer", writer)
    monkeypatch.setattr(client, "_call_legion_chat", talk)

    reply = converse(
        client, guild, author, signals=signals_for(ConversationMode.RESEARCH)
    )

    assert writer.await_count == 1
    assert talk.await_count == 0
    assert reply and "the report" in reply


def test_research_falls_back_to_chat_when_the_writer_stalls(
    client, guild, author, monkeypatch
):
    """A writer hiccup must not waste sources that were already fetched.

    Retrieval is the slow, metered part of the turn. Throwing it away because
    one model returned nothing would spend the budget and show the user an
    error anyway.
    """
    monkeypatch.setattr(
        client,
        "_gather_web_context",
        AsyncMock(return_value=("[1] evidence\nURL: https://example.com/a", ["https://example.com/a"])),
    )
    monkeypatch.setattr(client, "_call_legion_writer", AsyncMock(return_value=None))
    talk = AsyncMock(return_value="the report, written by the chat lane")
    monkeypatch.setattr(client, "_call_legion_chat", talk)

    reply = converse(
        client, guild, author, signals=signals_for(ConversationMode.RESEARCH)
    )

    assert talk.await_count == 1
    assert reply and "chat lane" in reply
    # The gate must attach the pre-fetched links, or a good answer is refused.
    assert "https://example.com/a" in reply


def test_no_key_reports_the_outage_rather_than_answering(guild, author, monkeypatch):
    monkeypatch.setattr(ai_client, "_LEGION_API_KEY", "")
    client = AIClient(_types.SimpleNamespace(user=None, loop=None), AIConfig())

    reply = converse(client, guild, author, signals=signals_for())

    assert "LEGION_API_KEY" in reply
