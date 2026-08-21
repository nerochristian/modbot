"""Which lanes may trip the client-wide service block.

This file exists because of a real incident. A 429 on the route classifier --
a two-second, best-effort call whose entire failure mode is "return None and
let converse() pick a default" -- tripped the CLIENT-WIDE block. Every
conversation in every guild then got "rate limit or quota reached. Try again in
~1m." instead of a reply, from a model that was not going to answer them
anyway. The upstream message was even explicit that only that one shared-pool
model was limited.

The rule these tests pin: a lane may block the client only if it is a lane that
actually serves the user's reply. Optional and background lanes each pin their
own model, so their quota says nothing about whether the talking lane works.
"""
from __future__ import annotations

import asyncio
import types as _types

import pytest

import cogs.aimoderation.ai_client as ai_client
from cogs.aimoderation.ai_client import AIClient
from cogs.aimoderation.types import AIConfig


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    async def text(self):
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    """Answers every POST with one status, so a 429 is deterministic."""

    def __init__(self, status=429, body='{"error":{"message":"rate-limited"}}'):
        self.closed = False
        self._status = status
        self._body = body
        self.calls = 0

    def post(self, *args, **kwargs):
        self.calls += 1
        return FakeResponse(self._status, self._body)

    async def close(self):
        self.closed = True


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(ai_client, "_OPENROUTER_API_KEY", "sk-or-v1-real")
    monkeypatch.setattr(ai_client, "_OPENROUTER_CHAT_MODEL", "vendor/talk")
    session = FakeSession()
    instance = AIClient(_types.SimpleNamespace(user=None, loop=None, session=session), AIConfig())
    instance.fake_session = session
    return instance


def post(client, **kwargs):
    kwargs.setdefault("base_url", "https://openrouter.ai/api/v1")
    kwargs.setdefault("api_key", "sk-or-v1-real")
    kwargs.setdefault("model", "vendor/x")
    kwargs.setdefault("temperature", 0.0)
    kwargs.setdefault("max_tokens", 16)
    kwargs.setdefault("provider_label", "test lane")
    kwargs.setdefault("max_retries", 0)
    try:
        run(client._post_chat_completion([{"role": "user", "content": "hi"}], **kwargs))
    except Exception:
        pass


def test_a_reply_serving_lane_still_blocks_on_429(client):
    """The block is not being removed -- it still protects the talking lane.

    When the model that would have answered is out of quota, telling the user
    to try again in a minute beats hammering a dead upstream.
    """
    post(client)

    assert client._get_block_message() is not None


def test_an_optional_lane_does_not_block_on_429(client):
    post(client, allow_service_block=False)

    assert client._get_block_message() is None


def test_an_optional_lane_does_not_block_on_auth_failure(client, monkeypatch):
    """403 is the same story: one lane's access says nothing about another's."""
    client.fake_session._status = 403

    post(client, allow_service_block=False)

    assert client._get_block_message() is None


def test_a_rate_limited_route_classifier_leaves_conversation_answerable(client):
    """The exact incident: Ling 429s, and everyone stops getting replies.

    The classifier is allowed to fail -- converse() defaults the route. What it
    must not do is make _preflight refuse the turn it was classifying.
    """
    route = run(client.classify_research_route("stop what....?"))

    assert route is None, "a 429 classifier must degrade, not raise"
    assert client._get_block_message() is None
    assert run(client._preflight(user_id=1)) is None


def test_a_rate_limited_protected_lane_leaves_conversation_answerable(client, monkeypatch):
    """Moderation and conversation pin different models and fail independently."""
    monkeypatch.setattr(ai_client, "_OPENROUTER_MODERATION_MODEL", "vendor/moderation")
    monkeypatch.setattr(ai_client, "_OPENROUTER_MODERATION_FALLBACK_MODELS", ())

    try:
        run(
            client._call_openrouter_protected(
                [{"role": "user", "content": "hi"}],
                temperature=0.0,
                max_tokens=16,
            )
        )
    except Exception:
        pass

    assert client._get_block_message() is None
    assert run(client._preflight(user_id=1)) is None


def test_image_screening_outage_leaves_conversation_answerable(client):
    """Screening already returns None for "unknown"; it must not also block."""
    from cogs.aimoderation.types import ImageContext

    image = ImageContext(
        label="attachment", filename="a.png", mime_type="image/png", data=b"x"
    )
    verdict = run(client.screen_images_for_age_rating([image]))

    assert verdict is None
    assert client._get_block_message() is None
