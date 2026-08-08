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
from cogs.aimoderation.types import AIConfig, ConversationMode, ConversationSignals


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


def test_openrouter_timeout_is_bounded(monkeypatch):
    monkeypatch.setenv("OPENROUTER_TIMEOUT", "1")
    assert ai_client_module._openrouter_request_timeout() == 5
    monkeypatch.setenv("OPENROUTER_TIMEOUT", "999")
    assert ai_client_module._openrouter_request_timeout() == 120


def test_openrouter_conversation_uses_only_configured_luna_model(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "aimodel"
    client.config = AIConfig(provider="aimodel")
    client._post_chat_completion = AsyncMock(return_value="natural reply")
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "")
    monkeypatch.setattr(ai_client_module, "_AIMODEL_CONVERSATION_API_KEY", "")
    monkeypatch.setattr(ai_client_module, "_OPENROUTER_API_KEY", "openrouter-test-key")
    monkeypatch.setattr(
        ai_client_module,
        "_OPENROUTER_BASE_URL",
        "https://openrouter.test/api/v1",
    )
    monkeypatch.setattr(
        ai_client_module,
        "_OPENROUTER_CHAT_MODEL",
        "openai/gpt-5.6-luna",
    )

    result = asyncio.run(
        client._call_openrouter_conversation(
            [{"role": "user", "content": "hello"}],
            temperature=0.8,
            max_tokens=500,
        )
    )

    assert result == "natural reply"
    kwargs = client._post_chat_completion.await_args.kwargs
    assert kwargs["base_url"] == "https://openrouter.test/api/v1"
    assert kwargs["model"] == "openai/gpt-5.6-luna"
    assert kwargs["json_mode"] is False
    assert kwargs["allow_multimodal"] is False
    assert client.conversation_model_name("stale-dashboard-model") == "openai/gpt-5.6-luna"


def test_aimodel_grok_is_only_the_ordinary_text_conversation_lane(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "aimodel"
    client.config = AIConfig(provider="aimodel")
    client._post_chat_completion = AsyncMock(return_value="natural grok reply")
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "stale-aimodel-key")
    monkeypatch.setattr(
        ai_client_module,
        "_AIMODEL_CONVERSATION_API_KEY",
        "aimodel-conversation-test-key",
    )
    monkeypatch.setattr(ai_client_module, "_AIMODEL_BASE_URL", "https://aimodel.test/v1")
    monkeypatch.setattr(ai_client_module, "_AIMODEL_CONVERSATION_MODEL", "grok-4.5")

    result = asyncio.run(
        client._call_aimodel_conversation(
            [{"role": "user", "content": "hello"}],
            temperature=0.8,
            max_tokens=500,
        )
    )

    assert result == "natural grok reply"
    kwargs = client._post_chat_completion.await_args.kwargs
    assert kwargs["base_url"] == "https://aimodel.test/v1"
    assert kwargs["api_key"] == "aimodel-conversation-test-key"
    assert kwargs["model"] == "grok-4.5"
    assert kwargs["json_mode"] is False
    assert kwargs["allow_multimodal"] is False
    assert kwargs["max_retries"] == 0
    assert "search" not in kwargs
    assert client.conversation_model_name("stale-dashboard-model") == "grok-4.5"


def test_grok_talks_and_luna_keeps_search_research_and_images(monkeypatch):
    """Grok owns ordinary talking; Luna owns search, research, and vision."""
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "stale-aimodel-key")
    monkeypatch.setattr(
        ai_client_module,
        "_AIMODEL_CONVERSATION_API_KEY",
        "aimodel-conversation-test-key",
    )
    monkeypatch.setattr(ai_client_module, "_AIMODEL_CONVERSATION_MODEL", "grok-4.5")
    monkeypatch.setattr(ai_client_module, "_OPENROUTER_API_KEY", "openrouter-test-key")
    standard = ConversationSignals(mode=ConversationMode.STANDARD, confidence=1.0)
    searched = ConversationSignals(
        mode=ConversationMode.STANDARD,
        confidence=1.0,
        requires_web_search=True,
    )
    research = ConversationSignals(mode=ConversationMode.RESEARCH, confidence=1.0)

    # OpenRouter now handles every conversation turn...
    assert AIClient._uses_openrouter_conversation_lane(standard, has_images=False) is True
    assert AIClient._uses_openrouter_conversation_lane(searched, has_images=False) is True
    assert AIClient._uses_openrouter_conversation_lane(research, has_images=False) is True
    assert AIClient._uses_openrouter_conversation_lane(standard, has_images=True) is True

    # ...but only search/research/vision turns escalate to Luna. Plain talking
    # stays on Grok, which is never given the web-search tool or images.
    assert AIClient._openrouter_lane_needs_luna(standard, has_images=False) is False
    assert AIClient._openrouter_lane_needs_luna(searched, has_images=False) is True
    assert AIClient._openrouter_lane_needs_luna(research, has_images=False) is True
    assert AIClient._openrouter_lane_needs_luna(standard, has_images=True) is True


def test_grok_chat_lane_sends_no_search_tool_and_no_images(monkeypatch):
    """The talking lane must not carry search tools, citations, or multimodal input."""
    client = AIClient.__new__(AIClient)
    client._post_chat_completion = AsyncMock(return_value="grok reply")
    monkeypatch.setattr(ai_client_module, "_OPENROUTER_API_KEY", "openrouter-test-key")
    monkeypatch.setattr(
        ai_client_module,
        "_OPENROUTER_GROK_CHAT_MODEL",
        "x-ai/grok-4.3",
    )

    result = asyncio.run(
        client._call_openrouter_grok_chat(
            [{"role": "user", "content": "how are you?"}],
            temperature=0.6,
            max_tokens=600,
        )
    )

    assert result == "grok reply"
    kwargs = client._post_chat_completion.await_args.kwargs
    assert kwargs["model"] == "x-ai/grok-4.3"
    assert kwargs["allow_multimodal"] is False
    assert kwargs["json_mode"] is False
    # No web-search tool and no citation harvesting on the talking lane.
    assert "extra_payload" not in kwargs
    assert kwargs.get("include_citations") in (None, False)


def test_openrouter_lets_luna_decide_when_search_is_needed(monkeypatch):
    client = AIClient.__new__(AIClient)
    client._post_chat_completion = AsyncMock(return_value="researched reply")
    monkeypatch.setattr(ai_client_module, "_OPENROUTER_API_KEY", "openrouter-test-key")
    monkeypatch.setattr(
        ai_client_module,
        "_OPENROUTER_CHAT_MODEL",
        "openai/gpt-5.6-luna",
    )

    result = asyncio.run(
        client._call_openrouter_conversation(
            [{"role": "user", "content": "what happened today?"}],
            temperature=0.4,
            max_tokens=800,
            allow_multimodal=True,
        )
    )

    assert result == "researched reply"
    kwargs = client._post_chat_completion.await_args.kwargs
    assert kwargs["allow_multimodal"] is True
    assert kwargs["include_citations"] is True
    assert kwargs["extra_payload"] == {
        "tools": [
            {
                "type": "openrouter:web_search",
                "parameters": {
                    "engine": "auto",
                    "max_results": 5,
                    "max_uses": 1,
                    "max_total_results": 10,
                },
            }
        ],
        "tool_choice": "auto",
        "max_tool_calls": 1,
    }


def test_openrouter_requires_search_for_explicit_search_or_research(monkeypatch):
    client = AIClient.__new__(AIClient)
    client._post_chat_completion = AsyncMock(return_value="researched reply")
    monkeypatch.setattr(ai_client_module, "_OPENROUTER_API_KEY", "openrouter-test-key")

    result = asyncio.run(
        client._call_openrouter_conversation(
            [{"role": "user", "content": "research the latest release"}],
            temperature=0.3,
            max_tokens=1200,
            require_search=True,
        )
    )

    assert result == "researched reply"
    assert (
        client._post_chat_completion.await_args.kwargs["extra_payload"]["tool_choice"]
        == "required"
    )


def test_conversation_forwards_explicit_search_requirement_to_luna(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "relayrouter"
    client.config = AIConfig(provider="relayrouter")
    client._block_until = None
    client._block_reason = None
    client._brave_search_api_key = None
    client._tavily_api_key = None
    client._serpapi_api_key = None
    client._rate_limiter = types.SimpleNamespace(
        is_rate_limited=AsyncMock(return_value=(False, 0)),
        record_call=AsyncMock(),
    )
    client._deepseek_web = types.SimpleNamespace(enabled=False)
    client._collect_image_context = AsyncMock(return_value=[])
    client._call_openrouter_conversation = AsyncMock(return_value="searched answer")
    client._update_memory_smart = AsyncMock()
    client.bot = types.SimpleNamespace(
        user=types.SimpleNamespace(id=999),
        db=types.SimpleNamespace(
            get_ai_memory=AsyncMock(return_value=""),
            get_guild_memory=AsyncMock(return_value=""),
        ),
    )
    monkeypatch.setattr(ai_client_module, "_OPENROUTER_API_KEY", "openrouter-test-key")

    result = asyncio.run(
        client.converse(
            user_content="search for the latest patch",
            guild=types.SimpleNamespace(id=1, name="Guild", member_count=10),
            author=types.SimpleNamespace(id=2, name="User"),
            recent_messages=[],
            signals=ConversationSignals(
                mode=ConversationMode.STANDARD,
                confidence=1.0,
                requires_web_search=True,
            ),
        )
    )

    assert result == "searched answer"
    assert client._call_openrouter_conversation.await_args.kwargs["require_search"] is True


def test_ordinary_conversation_uses_grok_without_openrouter(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "aimodel"
    client.config = AIConfig(provider="aimodel")
    client._block_until = None
    client._block_reason = None
    client._brave_search_api_key = None
    client._tavily_api_key = None
    client._serpapi_api_key = None
    client._rate_limiter = types.SimpleNamespace(
        is_rate_limited=AsyncMock(return_value=(False, 0)),
        record_call=AsyncMock(),
    )
    client._deepseek_web = types.SimpleNamespace(enabled=False)
    client._collect_image_context = AsyncMock(return_value=[])
    client._call_aimodel_conversation = AsyncMock(return_value="grok answer")
    client._call_openrouter_conversation = AsyncMock(return_value="wrong lane")
    client._update_memory_smart = AsyncMock()
    client.bot = types.SimpleNamespace(
        user=types.SimpleNamespace(id=999),
        db=types.SimpleNamespace(
            get_ai_memory=AsyncMock(return_value=""),
            get_guild_memory=AsyncMock(return_value=""),
        ),
    )
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "aimodel-test-key")
    monkeypatch.setattr(
        ai_client_module,
        "_AIMODEL_CONVERSATION_API_KEY",
        "aimodel-conversation-test-key",
    )
    monkeypatch.setattr(ai_client_module, "_AIMODEL_CONVERSATION_MODEL", "grok-4.5")
    monkeypatch.setattr(ai_client_module, "_OPENROUTER_API_KEY", "openrouter-test-key")

    result = asyncio.run(
        client.converse(
            user_content="how are you doing?",
            guild=types.SimpleNamespace(id=1, name="Guild", member_count=10),
            author=types.SimpleNamespace(id=2, name="User"),
            recent_messages=[],
            signals=ConversationSignals(
                mode=ConversationMode.STANDARD,
                confidence=1.0,
            ),
        )
    )

    assert result == "grok answer"
    client._call_aimodel_conversation.assert_awaited_once()
    client._call_openrouter_conversation.assert_not_awaited()


def test_ordinary_conversation_falls_back_to_luna_when_grok_is_down(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "aimodel"
    client.config = AIConfig(provider="aimodel")
    client._block_until = None
    client._block_reason = None
    client._brave_search_api_key = None
    client._tavily_api_key = None
    client._serpapi_api_key = None
    client._rate_limiter = types.SimpleNamespace(
        is_rate_limited=AsyncMock(return_value=(False, 0)),
        record_call=AsyncMock(),
    )
    client._deepseek_web = types.SimpleNamespace(enabled=False)
    client._collect_image_context = AsyncMock(return_value=[])
    client._call_aimodel_conversation = AsyncMock(
        side_effect=RuntimeError("AiModel HTTP 523")
    )
    client._call_openrouter_conversation = AsyncMock(return_value="luna fallback")
    client._update_memory_smart = AsyncMock()
    client.bot = types.SimpleNamespace(
        user=types.SimpleNamespace(id=999),
        db=types.SimpleNamespace(
            get_ai_memory=AsyncMock(return_value=""),
            get_guild_memory=AsyncMock(return_value=""),
        ),
    )
    monkeypatch.setattr(
        ai_client_module,
        "_AIMODEL_CONVERSATION_API_KEY",
        "aimodel-conversation-test-key",
    )
    monkeypatch.setattr(ai_client_module, "_AIMODEL_CONVERSATION_MODEL", "grok-4.5")
    monkeypatch.setattr(ai_client_module, "_OPENROUTER_API_KEY", "openrouter-test-key")

    result = asyncio.run(
        client.converse(
            user_content="how are you doing?",
            guild=types.SimpleNamespace(id=1, name="Guild", member_count=10),
            author=types.SimpleNamespace(id=2, name="User"),
            recent_messages=[],
            signals=ConversationSignals(
                mode=ConversationMode.STANDARD,
                confidence=1.0,
            ),
        )
    )

    assert result == "luna fallback"
    client._call_aimodel_conversation.assert_awaited_once()
    client._call_openrouter_conversation.assert_awaited_once()
    assert client._call_openrouter_conversation.await_args.kwargs.get("require_search") is None


def test_openrouter_citations_are_preserved_for_research_output():
    response = {
        "choices": [
            {
                "message": {
                    "content": "Current answer.",
                    "annotations": [
                        {
                            "type": "url_citation",
                            "url_citation": {
                                "url": "https://example.com/source",
                                "title": "Source",
                            },
                        }
                    ],
                }
            }
        ]
    }
    client, session, _ = _make_client([_FakeResp(200, response)])

    result = _post(
        client,
        include_citations=True,
        extra_payload={"tools": [{"type": "openrouter:web_search"}]},
    )

    assert result == "Current answer.\n\n__BOT_SOURCES__\n- https://example.com/source"
    assert session.requests[0][1]["json"]["tools"] == [
        {"type": "openrouter:web_search"}
    ]


def test_memory_curator_does_not_use_openrouter(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "aimodel"
    client.config = AIConfig(provider="aimodel")
    client._call_aimodel = AsyncMock(return_value="- Likes concise replies")
    client._call_openrouter_conversation = AsyncMock(return_value="wrong lane")
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "aimodel-test-key")
    monkeypatch.setattr(ai_client_module, "_OPENROUTER_API_KEY", "openrouter-test-key")

    result = asyncio.run(
        client._summarize_memory("", "keep it short", "Sure.")
    )

    assert result == "- Likes concise replies"
    client._call_aimodel.assert_awaited_once()
    client._call_openrouter_conversation.assert_not_awaited()


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
            model="accounts/aimodel/models/claude-fable-5",
            fallback_models=("accounts/aimodel/models/minimax-m2.7",),
        )
    )

    assert result == "fallback answer"
    models = [
        call.kwargs["model"]
        for call in client._post_responses_api.await_args_list
    ]
    assert models == [
        "accounts/aimodel/models/claude-fable-5",
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
                model="accounts/aimodel/models/claude-fable-5",
                fallback_models=("accounts/aimodel/models/minimax-m2.7",),
            )
        )

    assert client._post_responses_api.await_count == 1


def test_aimodel_conversation_ignores_stale_dashboard_model(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "aimodel"
    client.config = AIConfig(provider="aimodel", model="old-dashboard-model")
    client._call_aimodel_conversation = AsyncMock(return_value="chat")
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "aimodel-test-key")
    monkeypatch.setattr(
        ai_client_module,
        "_AIMODEL_CONVERSATION_API_KEY",
        "aimodel-conversation-test-key",
    )
    monkeypatch.setattr(ai_client_module, "_OPENROUTER_API_KEY", "")
    monkeypatch.setattr(
        ai_client_module,
        "_AIMODEL_CONVERSATION_MODEL",
        "grok-4.5",
    )

    result = asyncio.run(
        client._conversation_via_http(
            "hello",
            model="old-dashboard-model",
        )
    )

    assert result == "chat"
    assert client.conversation_model_name("old-dashboard-model") == "grok-4.5"
    client._call_aimodel_conversation.assert_awaited_once()


def test_aimodel_provider_routes_before_legacy_providers(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "aimodel"
    client.config = AIConfig(provider="aimodel", model="accounts/aimodel/models/claude-fable-5")
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
            provider_model_override="accounts/aimodel/models/claude-fable-5",
        )
    )

    assert result == "opus"
    assert client._call_aimodel.await_args.kwargs["model"].endswith("claude-fable-5")
    assert client._call_aimodel.await_args.kwargs["fallback_models"] == ()


def test_aimodel_provider_falls_back_to_deepseek_http_on_outage(monkeypatch):
    client = AIClient.__new__(AIClient)
    client.provider = "aimodel"
    client.config = AIConfig(provider="aimodel")
    client._call_aimodel = AsyncMock(side_effect=RuntimeError("HTTP 521"))
    client._call_deepseek_api = AsyncMock(return_value="deepseek-fallback")
    monkeypatch.setattr(ai_client_module, "_AIMODEL_API_KEY", "aimodel-test-key")
    monkeypatch.setattr(ai_client_module, "_DEEPSEEK_API_KEY", "deepseek-test-key")

    result = asyncio.run(
        client._call(
            [{"role": "user", "content": "plan an action"}],
            temperature=0.0,
            max_tokens=64,
        )
    )

    assert result == "deepseek-fallback"
    client._call_deepseek_api.assert_awaited_once()


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


def test_openrouter_protected_lane_allows_only_nemotron(monkeypatch):
    client = AIClient.__new__(AIClient)
    client._block_until = None
    client._block_reason = None
    client._post_chat_completion = AsyncMock(return_value="protected answer")
    monkeypatch.setattr(
        ai_client_module,
        "_RELAYROUTER_BASE_URL",
        "https://openrouter.ai/api/v1",
    )
    monkeypatch.setattr(ai_client_module, "_OPENROUTER_API_KEY", "openrouter-test-key")
    monkeypatch.setattr(ai_client_module, "_RELAYROUTER_API_KEY", "legacy-unused-key")

    result = asyncio.run(
        client._call_relayrouter(
            [{"role": "user", "content": "moderate this"}],
            temperature=0.0,
            max_tokens=64,
            model="deepseek-v4-flash",
            fallback_models=("perplexity/sonar", "openai/gpt-5.6-luna"),
        )
    )

    assert result == "protected answer"
    kwargs = client._post_chat_completion.await_args.kwargs
    assert kwargs["api_key"] == "openrouter-test-key"
    assert kwargs["model"] == ai_client_module._OPENROUTER_NEMOTRON_MODEL
    assert kwargs["provider_label"].startswith("OpenRouter protected")


def test_openrouter_conversation_ignores_stale_model_override(monkeypatch):
    client = AIClient.__new__(AIClient)
    client._post_chat_completion = AsyncMock(return_value="luna answer")
    monkeypatch.setattr(ai_client_module, "_OPENROUTER_API_KEY", "openrouter-test-key")
    monkeypatch.setattr(ai_client_module, "_OPENROUTER_CHAT_MODEL", "deepseek-v4-flash")

    result = asyncio.run(
        client._call_openrouter_conversation(
            [{"role": "user", "content": "hello"}],
            temperature=0.8,
            max_tokens=64,
        )
    )

    assert result == "luna answer"
    assert (
        client._post_chat_completion.await_args.kwargs["model"]
        == ai_client_module._OPENROUTER_LUNA_MODEL
    )


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


def test_provider_timeout_summary_is_not_blank():
    assert ai_client_module._exception_summary(asyncio.TimeoutError()) == "TimeoutError"


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
