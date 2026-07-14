"""Behavior tests for the AI moderation HTTP provider path.

Covers the DeepSeek-API-first routing added in the Phase 5 rebuild: the shared
OpenAI-compatible chat-completions POST must (1) return content on success,
(2) retry transient 5xx/429 failures, and (3) fail fast on auth errors while
tripping the provider block. These run without network or a real bot/config by
constructing AIClient via __new__ and injecting a fake aiohttp session.
"""

import asyncio
import types

import pytest

import cogs.aimoderation.ai_client as ai_client_module
from cogs.aimoderation.ai_client import AIClient


class _FakeResp:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def json(self, content_type=None):
        return self._payload


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0
        self.closed = False

    def post(self, *args, **kwargs):
        resp = self._responses[self.calls]
        self.calls += 1
        return resp

    async def close(self):
        self.closed = True


def _make_client(responses):
    client = AIClient.__new__(AIClient)
    client.bot = types.SimpleNamespace(session=None)
    client._block_until = None
    client._block_reason = None
    session = _FakeSession(responses)
    client._get_http_session = lambda *, timeout: (session, False)
    blocks = {}
    client._set_block = lambda *, seconds, reason: blocks.update(seconds=seconds, reason=reason)
    return client, session, blocks


_OK = {"choices": [{"message": {"content": "HELLO"}}]}


def _post(client, **overrides):
    kwargs = dict(
        base_url="http://x",
        api_key="k",
        model="deepseek-chat",
        temperature=0.1,
        max_tokens=10,
        provider_label="Test",
    )
    kwargs.update(overrides)
    return asyncio.run(
        client._post_chat_completion([{"role": "user", "content": "x"}], **kwargs)
    )


def test_success_path_returns_content():
    client, session, _ = _make_client([_FakeResp(200, _OK)])
    assert _post(client) == "HELLO"
    assert session.calls == 1


def test_retries_transient_5xx_then_succeeds():
    client, session, _ = _make_client([_FakeResp(500, {"error": "boom"}), _FakeResp(200, _OK)])
    assert _post(client, max_retries=2) == "HELLO"
    assert session.calls == 2


def test_auth_error_fails_fast_and_blocks():
    client, session, blocks = _make_client([_FakeResp(401, {"error": "auth"})])
    with pytest.raises(RuntimeError):
        _post(client, max_retries=2)
    assert session.calls == 1  # no retry on auth failure
    assert blocks.get("seconds") == 900


def test_deepseek_api_enabled_reflects_key(monkeypatch):
    monkeypatch.setattr(ai_client_module, "_DEEPSEEK_API_KEY", "sk-test")
    assert ai_client_module._deepseek_api_enabled() is True
    monkeypatch.setattr(ai_client_module, "_DEEPSEEK_API_KEY", "")
    assert ai_client_module._deepseek_api_enabled() is False


@pytest.mark.parametrize(
    "placeholder",
    (
        "YOUR_DEEPSEEK_API_KEY_HERE",
        "your_api_key",
        "replace_me",
        "changeme",
        "placeholder",
    ),
)
def test_deepseek_api_placeholders_are_disabled(monkeypatch, placeholder):
    monkeypatch.setattr(ai_client_module, "_DEEPSEEK_API_KEY", placeholder)
    assert ai_client_module._deepseek_api_enabled() is False
