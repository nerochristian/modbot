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
from cogs.aimoderation.providers import GoogleImageEvidence
from cogs.aimoderation.types import (
    AIConfig, ConversationMode, ConversationSignals, ImageContext,
)


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


def _with_image(client, monkeypatch, *, api_key="vision-key"):
    """Give the turn one attached image and a usable Cloud Vision credential."""
    monkeypatch.setattr(ai_client, "_GOOGLE_CLOUD_VISION_API_KEY", api_key)
    monkeypatch.setattr(
        client,
        "_collect_image_context",
        AsyncMock(
            return_value=[
                ImageContext(
                    label="attachment",
                    filename="pic.png",
                    mime_type="image/png",
                    data=b"bytes",
                )
            ]
        ),
    )


def _vision_prompt_text(vision_lane) -> str:
    messages = vision_lane.await_args.args[0]
    return "\n".join(str(message.get("content")) for message in messages)


def test_every_image_turn_is_reverse_searched(client, guild, author, monkeypatch):
    """Reverse-image evidence is not reserved for "what is this?" turns.

    Cloud Vision's matching pages, web entities and OCR are the only ground
    truth about what an image actually *is*. A turn that asks something else
    about the image ("write a caption") needs that just as much as one asking
    for a name, so the lookup runs for every image and its evidence reaches the
    lane that answers.
    """
    _with_image(client, monkeypatch)
    lookup = AsyncMock(
        return_value=GoogleImageEvidence(
            context="Image 1:\nGoogle best-guess labels: hubble deep field",
            source_urls=("https://example.com/source",),
            exact_match=True,
        )
    )
    vision = AsyncMock(return_value="a caption")
    monkeypatch.setattr(client, "_call_google_web_detection", lookup)
    monkeypatch.setattr(client, "_call_openrouter_vision", vision)

    reply = converse(
        client, guild, author, signals=signals_for(), content="write a caption"
    )

    assert lookup.await_count == 1
    assert reply and "a caption" in reply
    assert "hubble deep field" in _vision_prompt_text(vision)


def test_reverse_search_evidence_does_not_hijack_an_ordinary_image_turn(
    client, guild, author, monkeypatch
):
    """Grounding an image turn must not convert it into an identity check.

    Identification turns run extra passes and refuse an unsourced answer. Were
    those applied to every image, "write a caption" would come back as a
    refusal to identify the subject.
    """
    _with_image(client, monkeypatch)
    monkeypatch.setattr(
        client,
        "_call_google_web_detection",
        AsyncMock(return_value=GoogleImageEvidence(context="Image 1:\nOCR text: hi")),
    )
    grounded = AsyncMock(return_value="it is a photo of X")
    monkeypatch.setattr(client, "_call_google_grounded_vision", grounded)
    monkeypatch.setattr(
        client, "_call_openrouter_vision", AsyncMock(return_value="a caption")
    )

    reply = converse(
        client, guild, author, signals=signals_for(), content="write a caption"
    )

    assert grounded.await_count == 0
    assert reply and "a caption" in reply


def test_a_slow_reverse_search_does_not_stall_an_ordinary_image_turn(
    client, guild, author, monkeypatch
):
    """Extra grounding is never worth making the user wait on a wedged lookup."""
    _with_image(client, monkeypatch)
    monkeypatch.setattr(ai_client, "_REVERSE_IMAGE_SOFT_BUDGET_SECONDS", 0.05)

    async def never_finishes(*_args, **_kwargs):
        await asyncio.sleep(30)
        raise AssertionError("the lookup should have been abandoned")

    monkeypatch.setattr(client, "_call_google_web_detection", never_finishes)
    vision = AsyncMock(return_value="a caption")
    monkeypatch.setattr(client, "_call_openrouter_vision", vision)

    reply = converse(
        client, guild, author, signals=signals_for(), content="write a caption"
    )

    assert reply and "a caption" in reply
    assert "Cloud Vision" not in _vision_prompt_text(vision)


def test_an_identification_turn_waits_for_the_reverse_search(
    client, guild, author, monkeypatch
):
    """The soft budget must not apply where the lookup *is* the answer."""
    _with_image(client, monkeypatch)
    monkeypatch.setattr(ai_client, "_REVERSE_IMAGE_SOFT_BUDGET_SECONDS", 0.05)

    async def slow_lookup(*_args, **_kwargs):
        await asyncio.sleep(0.2)
        return GoogleImageEvidence(
            context="Image 1:\nWeb entities: the subject (0.90)",
            source_urls=("https://example.com/source",),
            exact_match=True,
        )

    monkeypatch.setattr(client, "_call_google_web_detection", slow_lookup)
    monkeypatch.setattr(
        client, "_call_google_grounded_vision", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        client, "_call_openrouter_visual_candidates", AsyncMock(return_value=None)
    )
    searched = AsyncMock(return_value="that is the subject __BOT_SOURCES__\n- https://example.com/source")
    monkeypatch.setattr(client, "_call_openrouter_conversation", searched)

    reply = converse(
        client, guild, author, signals=signals_for(), content="who is this?"
    )

    assert reply and "the subject" in reply
    assert "Web entities: the subject" in _vision_prompt_text(searched)


def test_a_failed_reverse_search_still_answers_the_image_turn(
    client, guild, author, monkeypatch
):
    _with_image(client, monkeypatch)
    monkeypatch.setattr(
        client,
        "_call_google_web_detection",
        AsyncMock(side_effect=RuntimeError("vision 503")),
    )
    monkeypatch.setattr(
        client, "_call_openrouter_vision", AsyncMock(return_value="a caption")
    )

    reply = converse(
        client, guild, author, signals=signals_for(), content="write a caption"
    )

    assert reply and "a caption" in reply


def test_no_vision_credential_skips_the_reverse_search(
    client, guild, author, monkeypatch
):
    """Without a credential the lookup must not be started at all."""
    _with_image(client, monkeypatch, api_key="")
    lookup = AsyncMock(return_value=GoogleImageEvidence())
    monkeypatch.setattr(client, "_call_google_web_detection", lookup)
    monkeypatch.setattr(
        client, "_call_openrouter_vision", AsyncMock(return_value="a caption")
    )

    reply = converse(
        client, guild, author, signals=signals_for(), content="write a caption"
    )

    assert lookup.await_count == 0
    assert reply and "a caption" in reply


def test_no_key_reports_the_outage_rather_than_answering(guild, author, monkeypatch):
    monkeypatch.setattr(ai_client, "_OPENROUTER_API_KEY", "")
    client = AIClient(_types.SimpleNamespace(user=None, loop=None), AIConfig())

    reply = converse(client, guild, author, signals=signals_for())

    assert "OPENROUTER_API_KEY" in reply
