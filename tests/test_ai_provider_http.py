"""Behavior tests for the AI moderation HTTP provider path.

Covers the DeepSeek-API-first routing added in the Phase 5 rebuild: the shared
OpenAI-compatible chat-completions POST must (1) return content on success,
(2) retry transient 5xx/429 failures, and (3) fail fast on auth errors while
tripping the provider block. These run without network or a real bot/config by
constructing AIClient via __new__ and injecting a fake aiohttp session.
"""

import asyncio
import types
from unittest.mock import AsyncMock

import pytest

import cogs.aimoderation.ai_client as ai_client_module
from cogs.aimoderation.ai_client import AIClient
from cogs.aimoderation.types import AIConfig


class _FakeResp:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def text(self):
        if isinstance(self._payload, str):
            return self._payload
        import json

        return json.dumps(self._payload)


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0
        self.closed = False
        self.requests = []

    def post(self, *args, **kwargs):
        self.requests.append((args, kwargs))
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
_RESPONSES_OK = {
    "output": [
        {
            "type": "message",
            "content": [{"type": "output_text", "text": "HELLO"}],
        }
    ]
}


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


def test_sse_success_path_returns_content():
    body = (
        'data: {"choices":[{"delta":{"content":"HE"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"LLO"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    client, session, _ = _make_client([_FakeResp(200, body)])
    assert _post(client, chat_path="/chat/completions/cline") == "HELLO"
    assert session.calls == 1


def test_custom_gateway_chat_path_is_used():
    client, session, _ = _make_client([_FakeResp(200, _OK)])
    assert _post(client, chat_path="/chat/completions/json") == "HELLO"
    assert session.calls == 1


def test_multimodal_deepseek_api_uses_cline_endpoint(monkeypatch):
    client = AIClient.__new__(AIClient)
    client._post_chat_completion = AsyncMock(return_value="vision")
    monkeypatch.setattr(ai_client_module, "_DEEPSEEK_API_KEY", "api-key")
    monkeypatch.setattr(ai_client_module, "_DEEPSEEK_API_MODEL", "gemini-3-5-flash")

    result = asyncio.run(
        client._call_deepseek_api(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "describe"},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
                    ],
                }
            ],
            temperature=0.0,
            max_tokens=32,
            allow_multimodal=True,
        )
    )

    assert result == "vision"
    assert client._post_chat_completion.await_args.kwargs["chat_path"] == "/chat/completions/cline"
    assert client._post_chat_completion.await_args.kwargs["allow_multimodal"] is True


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


def test_relayrouter_api_enabled_reflects_key(monkeypatch):
    monkeypatch.setattr(ai_client_module, "_RELAYROUTER_API_KEY", "relay-test-key")
    assert ai_client_module._relayrouter_api_enabled() is True
    monkeypatch.setattr(ai_client_module, "_RELAYROUTER_API_KEY", "")
    assert ai_client_module._relayrouter_api_enabled() is False


def test_aimodel_api_enabled_reflects_key(monkeypatch):
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "aimodel-test-key")
    assert ai_client_module._aimodel_api_enabled() is True
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "")
    assert ai_client_module._aimodel_api_enabled() is False


def test_aimodel_timeouts_are_bounded(monkeypatch):
    monkeypatch.setenv("AIMODEL_TIMEOUT", "1")
    monkeypatch.setenv("AIMODEL_VISION_TIMEOUT", "999")
    assert ai_client_module._aimodel_request_timeout(multimodal=False) == 5
    assert ai_client_module._aimodel_request_timeout(multimodal=True) == 180


def test_aimodel_responses_success_and_json_mode(monkeypatch):
    client, session, _ = _make_client([_FakeResp(200, _RESPONSES_OK)])
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "aimodel-test-key")
    monkeypatch.setattr(ai_client_module, "_AIMODEL_BASE_URL", "https://aimodel.test/v1")

    result = asyncio.run(
        client._post_responses_api(
            [
                {"role": "system", "content": "Return JSON."},
                {"role": "user", "content": "Hello"},
            ],
            model="glm-5.1",
            temperature=0.1,
            max_tokens=64,
            json_mode=True,
            allow_multimodal=False,
            provider_label="AiModel test",
        )
    )

    assert result == "HELLO"
    args, kwargs = session.requests[0]
    assert args[0] == "https://aimodel.test/v1/responses"
    assert kwargs["json"]["model"] == "accounts/aimodel/models/glm-5.1"
    assert kwargs["json"]["input"] == [
        {"role": "system", "content": "Return JSON."},
        {"role": "user", "content": "Hello"},
    ]
    assert kwargs["json"]["text"] == {"format": {"type": "json_object"}}
    assert kwargs["json"]["max_output_tokens"] == 64


def test_aimodel_multimodal_messages_use_responses_parts():
    converted = AIClient._responses_input(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "describe"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64,AA==",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        allow_multimodal=True,
    )

    assert converted == [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "describe"},
                {
                    "type": "input_image",
                    "image_url": "data:image/png;base64,AA==",
                    "detail": "high",
                },
            ],
        }
    ]


def test_aimodel_falls_back_in_configured_order(monkeypatch):
    client = AIClient.__new__(AIClient)
    client._block_until = None
    client._block_reason = None
    client._post_responses_api = AsyncMock(
        side_effect=[RuntimeError("primary down"), "fallback answer"]
    )
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "aimodel-test-key")

    result = asyncio.run(
        client._call_aimodel(
            [{"role": "user", "content": "hello"}],
            temperature=0.7,
            max_tokens=64,
            model="accounts/aimodel/models/glm-5.1",
            fallback_models=("accounts/aimodel/models/minimax-m2.7",),
        )
    )

    assert result == "fallback answer"
    models = [
        call.kwargs["model"]
        for call in client._post_responses_api.await_args_list
    ]
    assert models == [
        "accounts/aimodel/models/glm-5.1",
        "accounts/aimodel/models/minimax-m2.7",
    ]


def test_aimodel_does_not_retry_other_models_after_balance_error(monkeypatch):
    client = AIClient.__new__(AIClient)
    client._block_until = None
    client._block_reason = None
    client._post_responses_api = AsyncMock(
        side_effect=RuntimeError("AiModel HTTP 402: balance exhausted")
    )
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "aimodel-test-key")

    with pytest.raises(RuntimeError, match="HTTP 402"):
        asyncio.run(
            client._call_aimodel(
                [{"role": "user", "content": "hello"}],
                temperature=0.7,
                max_tokens=64,
                model="accounts/aimodel/models/glm-5.1",
                fallback_models=("accounts/aimodel/models/minimax-m2.7",),
            )
        )

    assert client._post_responses_api.await_count == 1


def test_aimodel_conversation_ignores_stale_dashboard_model(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "aimodel"
    client.config = AIConfig(provider="aimodel", model="old-dashboard-model")
    client._call_aimodel = AsyncMock(return_value="chat")
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "aimodel-test-key")
    monkeypatch.setattr(
        ai_client_module,
        "_AIMODEL_CHAT_MODEL",
        "accounts/aimodel/models/glm-5.1",
    )

    result = asyncio.run(
        client._conversation_via_http(
            "hello",
            model="old-dashboard-model",
        )
    )

    assert result == "chat"
    assert client.conversation_model_name("old-dashboard-model") == "accounts/aimodel/models/glm-5.1"
    assert client._call_aimodel.await_args.kwargs["model"] == "accounts/aimodel/models/glm-5.1"


def test_aimodel_provider_routes_before_legacy_providers(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "aimodel"
    client.config = AIConfig(provider="aimodel", model="accounts/aimodel/models/glm-5.1")
    client._call_aimodel = AsyncMock(return_value="aimodel")
    client._call_relayrouter = AsyncMock(return_value="relay")
    client._deepseek_web = types.SimpleNamespace(enabled=True, chat=AsyncMock())
    client._call_deepseek_api = AsyncMock(return_value="deepseek")
    client._call_digitalocean = AsyncMock(return_value="digitalocean")
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "aimodel-test-key")

    result = asyncio.run(
        client._call(
            [{"role": "user", "content": "route this"}],
            temperature=0.0,
            max_tokens=32,
            model="stale-guild-model",
        )
    )

    assert result == "aimodel"
    assert client._call_aimodel.await_args.kwargs["model"] == ai_client_module._AIMODEL_MODERATION_MODEL
    client._call_relayrouter.assert_not_awaited()
    client._deepseek_web.chat.assert_not_awaited()
    client._call_deepseek_api.assert_not_awaited()
    client._call_digitalocean.assert_not_awaited()


def test_aimodel_provider_accepts_internal_execution_model_override(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "aimodel"
    client.config = AIConfig(provider="aimodel")
    client._call_aimodel = AsyncMock(return_value="opus")
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "aimodel-test-key")

    result = asyncio.run(
        client._call(
            [{"role": "user", "content": "retry invalid generated code"}],
            temperature=0.0,
            max_tokens=64,
            provider_model_override="accounts/aimodel/models/claude-opus-4.8",
        )
    )

    assert result == "opus"
    assert client._call_aimodel.await_args.kwargs["model"].endswith("claude-opus-4.8")


def test_relayrouter_timeouts_are_bounded(monkeypatch):
    monkeypatch.setenv("RELAYROUTER_TIMEOUT", "1")
    monkeypatch.setenv("RELAYROUTER_VISION_TIMEOUT", "999")
    assert ai_client_module._relayrouter_request_timeout(multimodal=False) == 5
    assert ai_client_module._relayrouter_request_timeout(multimodal=True) == 90


def test_relayrouter_vision_uses_standard_chat_completions(monkeypatch):
    client = AIClient.__new__(AIClient)
    client._block_until = None
    client._block_reason = None
    client._post_chat_completion = AsyncMock(return_value="vision")
    monkeypatch.setattr(ai_client_module, "_RELAYROUTER_API_KEY", "relay-test-key")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "describe"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
            ],
        }
    ]
    result = asyncio.run(
        client._call_relayrouter(
            messages,
            temperature=0.0,
            max_tokens=32,
            model="gpt-5-6-terra",
            allow_multimodal=True,
            fallback_models=(),
        )
    )

    assert result == "vision"
    kwargs = client._post_chat_completion.await_args.kwargs
    assert kwargs["model"] == "gpt-5-6-terra"
    assert kwargs["allow_multimodal"] is True
    assert kwargs["request_timeout"] == 45
    assert kwargs["max_retries"] == 0
    assert "chat_path" not in kwargs


def test_relayrouter_falls_back_in_configured_order(monkeypatch):
    client = AIClient.__new__(AIClient)
    client._block_until = None
    client._block_reason = None
    client._post_chat_completion = AsyncMock(
        side_effect=[RuntimeError("primary down"), "fallback answer"]
    )
    monkeypatch.setattr(ai_client_module, "_RELAYROUTER_API_KEY", "relay-test-key")

    result = asyncio.run(
        client._call_relayrouter(
            [{"role": "user", "content": "hello"}],
            temperature=0.7,
            max_tokens=64,
            model="gpt-5-6-luna",
            fallback_models=("claude-sonnet-4-6", "deepseek-v4-flash"),
        )
    )

    assert result == "fallback answer"
    models = [
        call.kwargs["model"]
        for call in client._post_chat_completion.await_args_list
    ]
    assert models == ["gpt-5-6-luna", "claude-sonnet-4-6"]


def test_relayrouter_provider_routes_before_legacy_providers(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "relayrouter"
    client.config = AIConfig(provider="relayrouter", model="gpt-5-6-terra")
    client._call_relayrouter = AsyncMock(return_value="relay")
    client._deepseek_web = types.SimpleNamespace(enabled=True, chat=AsyncMock())
    client._call_deepseek_api = AsyncMock(return_value="deepseek")
    client._call_digitalocean = AsyncMock(return_value="digitalocean")
    monkeypatch.setattr(ai_client_module, "_RELAYROUTER_API_KEY", "relay-test-key")

    result = asyncio.run(
        client._call(
            [{"role": "user", "content": "route this"}],
            temperature=0.0,
            max_tokens=32,
        )
    )

    assert result == "relay"
    client._call_relayrouter.assert_awaited_once()
    client._deepseek_web.chat.assert_not_awaited()
    client._call_deepseek_api.assert_not_awaited()
    client._call_digitalocean.assert_not_awaited()


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


def test_deepseek_provider_routes_to_galaxy_before_browser(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "deepseek"
    client.config = AIConfig(provider="deepseek")
    client._deepseek_web = types.SimpleNamespace(
        enabled=True,
        chat=AsyncMock(return_value="browser"),
    )
    client._call_deepseek_api = AsyncMock(return_value="galaxy")
    client._call_digitalocean = AsyncMock(return_value="digitalocean")
    monkeypatch.setattr(ai_client_module, "_DEEPSEEK_API_KEY", "api-key")

    result = asyncio.run(
        client._call(
            [{"role": "user", "content": "route this"}],
            temperature=0.0,
            max_tokens=32,
        )
    )

    assert result == "galaxy"
    client._call_deepseek_api.assert_awaited_once()
    client._deepseek_web.chat.assert_not_awaited()
    client._call_digitalocean.assert_not_awaited()


def test_deepseek_provider_falls_back_to_browser_before_digitalocean(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "deepseek"
    client.config = AIConfig(provider="deepseek")
    client._deepseek_web = types.SimpleNamespace(
        enabled=True,
        chat=AsyncMock(return_value="browser"),
    )
    client._call_deepseek_api = AsyncMock(side_effect=RuntimeError("gateway down"))
    client._call_digitalocean = AsyncMock(return_value="digitalocean")
    monkeypatch.setattr(ai_client_module, "_DEEPSEEK_API_KEY", "api-key")

    result = asyncio.run(
        client._call(
            [{"role": "user", "content": "route this"}],
            temperature=0.0,
            max_tokens=32,
        )
    )

    assert result == "browser"
    client._call_deepseek_api.assert_awaited_once()
    client._deepseek_web.chat.assert_awaited_once()
    client._call_digitalocean.assert_not_awaited()
