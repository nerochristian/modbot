"""Ling's two-label intent classifier, and how the signal layer trusts it.

Ling is an optimization sitting on the reply path with a 2s budget and a shared
upstream pool that 429s (see tests/test_aimoderation_service_block.py). So the
rules under test are as much about degradation as accuracy: a confused, slow, or
rate-limited classifier must leave the regex verdict standing, never erase it.

The live accuracy of the prompt itself is measured separately, against the real
model -- these are the wiring guarantees that hold regardless of what it says.
"""
from __future__ import annotations

import asyncio
import types as _types
from unittest.mock import AsyncMock, MagicMock

import pytest

import cogs.aimoderation.ai_client as ai_client
from cogs.aimoderation.ai_client import AIClient
from cogs.aimoderation.types import AIConfig, ConversationMode


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(ai_client, "_OPENROUTER_API_KEY", "sk-or-v1-real")
    bot = _types.SimpleNamespace(user=None, loop=None, session=None)
    return AIClient(bot, AIConfig())


# --- parsing -----------------------------------------------------------------

def test_both_labels_survive_a_clean_response(client):
    parsed = client._parse_intent_payload('{"route":"normal","moderation":"action"}')

    assert parsed["route"] == "normal"
    assert parsed["moderation"] == "action"
    assert parsed["is_moderation"] is True
    assert parsed["wants_mod_action"] is True


def test_guidance_is_moderation_but_not_an_action(client):
    """"how do i ban someone" needs the mod-guidance prompt, not the tool layer."""
    parsed = client._parse_intent_payload('{"route":"normal","moderation":"guidance"}')

    assert parsed["is_moderation"] is True
    assert parsed["wants_mod_action"] is False


def test_a_mod_action_is_never_sent_to_the_web(client):
    """Docket bans people with its own tools. Search on "ban @user" is a mistake."""
    parsed = client._parse_intent_payload('{"route":"search","moderation":"action"}')

    assert parsed["route"] == "normal"


def test_near_miss_vocabulary_is_mapped_not_discarded(client):
    """Small models reach for synonyms. Recover the label instead of failing."""
    parsed = client._parse_intent_payload('{"route":"chat","moderation":"mod"}')

    assert parsed["route"] == "normal"
    assert parsed["moderation"] == "action"


def test_labels_are_recovered_from_unfenced_output(client):
    """json_mode is requested, not guaranteed. Prose around the labels still parses."""
    parsed = client._parse_intent_payload(
        'route: normal, moderation: lookup -- they want warnings'
    )

    assert parsed["route"] == "normal"
    assert parsed["moderation"] == "lookup"


def test_one_missing_label_does_not_void_the_other(client):
    parsed = client._parse_intent_payload('{"moderation":"action"}')

    assert parsed["moderation"] == "action"
    assert parsed["route"] == "normal"


@pytest.mark.parametrize("raw", ["", "{}", "not json at all", '{"route":"banana"}'])
def test_unusable_output_returns_none(client, raw):
    """None means "I have no opinion", which lets the caller keep its own."""
    assert client._parse_intent_payload(raw) is None


# --- how the signal layer uses it --------------------------------------------

class _Parser:
    """The parsing mixin with a stubbed AI, so no network is involved."""

    def __init__(self, decision):
        from cogs.aimoderation.parsing import MessageParsingMixin

        self.__class__ = type("_P", (MessageParsingMixin,), {})
        self.ai = _types.SimpleNamespace(
            classify_intent=AsyncMock(return_value=decision),
            has_web_search=True,
        )


def signals_for(content, decision=None):
    return run(_Parser(decision)._build_conversation_signals(content))


def test_ling_catches_a_mod_request_the_regex_missed(monkeypatch):
    """The recall win: soft phrasing that no pattern in parsing.py matches."""
    signals = signals_for(
        "could you maybe chill aries out for a little while",
        {"route": "normal", "moderation": "action"},
    )

    assert signals.mentions_moderation is True


def test_ling_cannot_talk_the_regex_out_of_a_match():
    """An explicit command must not depend on a flaky upstream classifier.

    "timeout @user 5m" is matched locally, so Ling is never consulted and its
    hypothetical "none" can never reach the decision.
    """
    parser = _Parser({"route": "search", "moderation": "none"})
    signals = run(parser._build_conversation_signals("timeout @aries 5m for spam"))

    assert signals.mentions_moderation is True
    assert parser.ai.classify_intent.await_count == 0, "no network hop on the fast path"


def test_a_dead_classifier_leaves_the_regex_verdict_standing():
    """429 or timeout returns None. Ordinary chat stays ordinary chat."""
    signals = signals_for("who would win goku or saitama", None)

    assert signals.mentions_moderation is False
    assert signals.mode == ConversationMode.STANDARD


def test_guidance_activates_the_mod_guidance_prompt():
    """MOD_GUIDANCE existed with no way to reach it. Ling is that way."""
    signals = signals_for(
        "whats the syntax for banning someone",
        {"route": "normal", "moderation": "guidance"},
    )

    assert signals.mode == ConversationMode.MOD_GUIDANCE


def test_search_still_routes_to_search():
    signals = signals_for(
        "hows the new zzz character",
        {"route": "search", "moderation": "none"},
    )

    assert signals.requires_web_search is True
    assert signals.mentions_moderation is False
