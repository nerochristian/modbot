"""Lane enablement and protected-lane pinning on OpenRouter.

This file exists because of a real outage. Back when four vendors were wired
up, three had dead credentials (two 401s and an unreachable host) while every
enablement predicate still reported True, because those predicates only ask "is
a key present", never "is this key good". The moderation lane therefore failed
100% of the time, spending ~65s per request walking dead fallbacks before
erroring. Collapsing to OpenRouter removes the dead-vendor half of that, but
not the rest: one key can still be bad, and one model can still be rate-limited.

Unit tests cannot dial a vendor, so they cannot catch an expired key. What they
CAN pin down is everything around it: that placeholders are rejected, that a
lane with no key reports itself disabled, that protected work runs only the
models it was configured with, and that failover moves on instead of retrying a
dead route. Those are the invariants that turned one bad key into a total
outage.

Nothing here performs network I/O: the HTTP layer is replaced with a recorder.
"""
from __future__ import annotations

import asyncio
import types as _types

import pytest

import cogs.aimoderation.ai_client as ai_client
from cogs.aimoderation.types import ImageContext
from cogs.aimoderation.ai_client import AIClient
from cogs.aimoderation.types import AIConfig


def run(coro):
    """Drive a coroutine without pytest-asyncio (not installed here)."""
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture
def client():
    bot = _types.SimpleNamespace(user=None, loop=None)
    return AIClient(bot, AIConfig())


# --- Credential hygiene -----------------------------------------------------

@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "YOUR_API_KEY",
        "YOUR_LEGION_API_KEY_HERE",
        "replace_me",
        "CHANGEME",
        "placeholder",
    ],
)
def test_placeholder_credentials_are_rejected(value):
    """A documented placeholder must never count as configured.

    Otherwise a half-filled .env presents as a working lane and the failure
    only appears at runtime, as an opaque auth error.
    """
    assert not ai_client._credential_is_configured(value)


@pytest.mark.parametrize("value", ["sk-or-v1-abc123", "rr_live_xyz", "a" * 40])
def test_real_looking_credentials_are_accepted(value):
    assert ai_client._credential_is_configured(value)


def test_placeholder_check_is_case_insensitive():
    assert not ai_client._credential_is_configured("Your_Api_Key")


# --- Lane enablement --------------------------------------------------------

def test_lane_without_a_key_reports_disabled(monkeypatch):
    monkeypatch.setattr(ai_client, "_LEGION_API_KEY", "")
    assert not ai_client._legion_enabled()
    assert not ai_client._legion_conversation_enabled()
    assert not ai_client._legion_protected_enabled()


def test_lane_with_a_key_reports_enabled(monkeypatch):
    monkeypatch.setattr(ai_client, "_LEGION_API_KEY", "sk-or-v1-real-looking")
    assert ai_client._legion_enabled()
    assert ai_client._legion_conversation_enabled()
    assert ai_client._legion_protected_enabled()


def test_protected_lane_needs_a_moderation_model(monkeypatch):
    """A key alone is not enough: the lane must know what to run.

    Reporting ready without a model sends the whole moderation path into a
    request that can only fail, instead of degrading to deterministic routing.
    """
    monkeypatch.setattr(ai_client, "_LEGION_API_KEY", "sk-or-v1-real-looking")
    monkeypatch.setattr(ai_client, "_LEGION_MODERATION_MODEL", "")
    assert not ai_client._legion_protected_enabled()


def test_every_lane_reads_the_same_key(monkeypatch):
    """OpenRouter is the only provider, so one key gates the whole bot.

    Asserted rather than assumed: a second key sneaking back in is how a lane
    ends up reporting available while the request it makes is unauthenticated.
    """
    monkeypatch.setattr(ai_client, "_LEGION_API_KEY", "")
    client = AIClient(_types.SimpleNamespace(user=None, loop=None), AIConfig())
    assert not client.is_available
    assert not client.has_web_search


# --- Protected-lane model pinning ------------------------------------------

def attempted_models(client, monkeypatch, requested=None, fallbacks=None, results=None):
    """Record the models the protected lane actually tries, in order."""
    seen = []
    outcomes = list(results or [])

    async def fake_post(messages, **kwargs):
        seen.append(kwargs["model"])
        if outcomes:
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return "ok"

    monkeypatch.setattr(client, "_post_chat_completion", fake_post)
    try:
        run(
            client._call_legion_protected(
                [{"role": "user", "content": "hi"}],
                temperature=0.0,
                max_tokens=16,
                model=requested,
                fallback_models=fallbacks,
            )
        )
    except Exception:
        pass
    return seen


@pytest.fixture
def openrouter_lane(monkeypatch):
    """The protected lane with a known model configuration."""
    monkeypatch.setattr(ai_client, "_LEGION_API_KEY", "sk-or-v1-real")
    monkeypatch.setattr(ai_client, "_LEGION_MODERATION_MODEL", "vendor/primary")
    monkeypatch.setattr(
        ai_client, "_LEGION_MODERATION_FALLBACK_MODELS", ("vendor/backup",)
    )
    # Defaulted from the moderation model in real config; pinned here so the
    # background-lane tests below can move them independently.
    monkeypatch.setattr(ai_client, "_LEGION_MEMORY_MODEL", "vendor/primary")
    monkeypatch.setattr(ai_client, "_LEGION_ACTION_ROUTER_MODEL", "vendor/primary")
    return monkeypatch


def test_protected_lane_runs_the_configured_model(client, openrouter_lane):
    """The configured moderation model must actually be the one called.

    This lane used to hard-pin the Nemotron family, which silently discarded
    whatever the deployment had configured and substituted its own model.
    """
    seen = attempted_models(client, openrouter_lane)
    assert seen and seen[0] == "vendor/primary", seen


def test_protected_lane_refuses_a_model_it_was_not_configured_with(client, openrouter_lane):
    """Still an allow-list: a caller cannot smuggle in its own model.

    A Decision is model-authored, so letting a requested model through would
    let the model choose where protected moderation work runs.
    """
    seen = attempted_models(client, openrouter_lane, requested="anthropic/claude-sonnet-5")
    assert "anthropic/claude-sonnet-5" not in seen, seen
    assert all(m in {"vendor/primary", "vendor/backup"} for m in seen), seen


def test_protected_lane_has_a_second_route(client, openrouter_lane):
    """One rate-limited model must not mean the whole lane is dead.

    Pinning to a single id is what made a transient 429 fall through to the
    dead vendor fallbacks instead of simply retrying on OpenRouter.
    """
    seen = attempted_models(
        client, openrouter_lane, results=[RuntimeError("429 rate limited"), "recovered"]
    )
    assert len(seen) >= 2, f"no fallback route attempted: {seen}"
    assert len(set(seen)) == len(seen), f"retried the same dead route: {seen}"


def test_protected_lane_tries_the_primary_before_the_fallback(client, openrouter_lane):
    seen = attempted_models(
        client, openrouter_lane, results=[RuntimeError("429"), "recovered"]
    )
    assert seen[0] == "vendor/primary", f"fallback tried first: {seen}"
    assert seen[1] == "vendor/backup", seen


def test_background_lane_keeps_its_own_cheaper_model(client, openrouter_lane):
    """Memory curation runs on its configured model, not the moderation one.

    The allow-list originally REPLACED the candidate list instead of filtering
    it. Since the moderation model sits first in that list, a background lane
    asking for its own cheap model silently got the expensive one -- the
    setting looked applied and did nothing.
    """
    openrouter_lane.setattr(ai_client, "_LEGION_MEMORY_MODEL", "vendor/cheap-background")
    seen = attempted_models(client, openrouter_lane, requested="vendor/cheap-background")
    assert seen[0] == "vendor/cheap-background", seen


def test_background_lane_still_falls_back(client, openrouter_lane):
    """Asking for the cheap model must not remove the safety net under it."""
    openrouter_lane.setattr(ai_client, "_LEGION_MEMORY_MODEL", "vendor/cheap-background")
    seen = attempted_models(
        client,
        openrouter_lane,
        requested="vendor/cheap-background",
        results=[RuntimeError("429"), "recovered"],
    )
    assert len(seen) >= 2, f"no fallback behind the background model: {seen}"
    assert seen[0] == "vendor/cheap-background", seen


def test_image_screening_goes_to_google_not_the_text_provider(client, monkeypatch):
    """Anything that must LOOK at a picture runs on Gemini, never on Legion.

    Every Legion Edge model is text-only, so sending an image-screening
    request there would ask a text model to judge a picture it cannot see.
    An earlier revision of this migration did exactly that -- it posted a
    Gemini model id to the Legion endpoint -- and screening silently stopped
    working. This pins the lane to the provider that can actually see.
    """
    monkeypatch.setattr(ai_client, "_GEMINI_API_KEY", "gk-real")
    monkeypatch.setattr(ai_client, "_GEMINI_IMAGE_SCREEN_MODEL", "gemini-screen")

    calls = []

    async def fake_vision(messages, **kwargs):
        calls.append(kwargs.get("model"))
        return '{"safe": false, "category": "nsfw", "confidence": 0.9}'

    async def fail_post(*a, **k):  # the text provider must not be touched
        raise AssertionError("image screening reached the text provider")

    monkeypatch.setattr(client, "_call_gemini_vision", fake_vision)
    monkeypatch.setattr(client, "_post_chat_completion", fail_post)

    image = ImageContext(
        label="a", filename="a.png", mime_type="image/png", data=b"\x89PNG"
    )
    verdict = run(client.screen_images_for_age_rating([image]))

    assert calls == ["gemini-screen"], calls
    assert verdict == {"safe": False, "category": "nsfw", "confidence": 0.9}


def test_image_screening_without_a_google_key_returns_unknown(client, monkeypatch):
    """No vision provider means "unknown", never a guess.

    Callers treat None as "do nothing". Returning safe/unsafe from a text
    model that never saw the image would either punish a member over nothing
    or wave real content through.
    """
    monkeypatch.setattr(ai_client, "_GEMINI_API_KEY", "")

    async def fail_post(*a, **k):
        raise AssertionError("screening ran without a vision provider")

    monkeypatch.setattr(client, "_post_chat_completion", fail_post)
    image = ImageContext(
        label="a", filename="a.png", mime_type="image/png", data=b"\x89PNG"
    )
    assert run(client.screen_images_for_age_rating([image])) is None


def test_protected_lane_refuses_to_run_without_a_key(client, monkeypatch):
    monkeypatch.setattr(ai_client, "_LEGION_API_KEY", "")
    with pytest.raises(RuntimeError):
        run(
            client._call_legion_protected(
                [{"role": "user", "content": "hi"}], temperature=0.0, max_tokens=16
            )
        )


# --- Late-bound settings contract ------------------------------------------
# settings.py exists so the lane modules read config at call time. A
# from-import would snapshot the value and silently ignore the patches above,
# leaving tests that pass while exercising live credentials.

def test_settings_reads_are_late_bound(monkeypatch):
    from cogs.aimoderation import settings

    monkeypatch.setattr(ai_client, "_LEGION_API_KEY", "PATCHED-AFTER-IMPORT")
    assert settings.setting("_LEGION_API_KEY") == "PATCHED-AFTER-IMPORT"


def test_settings_call_is_late_bound(monkeypatch):
    from cogs.aimoderation import settings

    monkeypatch.setattr(ai_client, "_legion_protected_enabled", lambda: False)
    assert settings.call("_legion_protected_enabled") is False


def test_settings_missing_name_can_default():
    from cogs.aimoderation import settings

    assert settings.setting("_DEFINITELY_NOT_A_SETTING", "fallback") == "fallback"
