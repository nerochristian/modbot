import asyncio
from types import SimpleNamespace

import pytest

from cogs.moderation.extensions.helpers import HelperCommands
from cogs.moderation.extensions.chat import ChatCommands
from utils.moderation_settings import (
    DEFAULT_RESPONSE_TEMPLATES,
    MAX_RESPONSE_LENGTH,
    moderation_bool,
    moderation_id_set,
    render_moderation_response,
)


class _User:
    def __init__(self, user_id: int, mention: str):
        self.id = user_id
        self.mention = mention


def test_moderation_boolean_parser_is_strict_and_defaults_safely():
    assert moderation_bool({"enabled": "yes"}, "enabled", False) is True
    assert moderation_bool({"enabled": "OFF"}, "enabled", True) is False
    assert moderation_bool({"enabled": "unexpected"}, "enabled", True) is True
    assert moderation_bool({"enabled": object()}, "enabled", False) is False


def test_id_sets_accept_dashboard_and_legacy_storage_shapes():
    assert moderation_id_set(
        {"roles": ["123", 456, "bad", 0, True]},
        "roles",
    ) == {123, 456}
    assert moderation_id_set({"roles": "123, 456\n789"}, "roles") == {
        123,
        456,
        789,
    }


@pytest.mark.parametrize("action,template", DEFAULT_RESPONSE_TEMPLATES.items())
def test_default_custom_responses_match_dashboard_contract(action, template):
    user = _User(10, "<@10>")
    moderator = _User(20, "<@20>")
    result = render_moderation_response(
        {"moderation_respond_with_reason": False},
        action,
        user=user,
        reason="Spam",
        moderator=moderator,
    )
    assert result == template.replace("{user}", user.mention)


def test_response_renderer_supports_known_placeholders_without_format_traversal():
    settings = {
        "moderation_ban_response": (
            "{user} / {moderator} / {duration} / {reason} / {unknown} / "
            "{user.__class__}"
        ),
        "moderation_respond_with_reason": True,
    }
    result = render_moderation_response(
        settings,
        "ban",
        user=_User(10, "<@10>"),
        reason="Raid links",
        moderator=_User(20, "<@20>"),
        duration="1 day",
    )
    assert result == (
        "<@10> / <@20> / 1 day / Raid links / {unknown} / {user.__class__}"
    )


def test_reason_toggle_suppresses_explicit_reason_placeholders():
    result = render_moderation_response(
        {
            "moderation_mute_response": "{user} muted. Reason: {reason}",
            "moderation_respond_with_reason": False,
        },
        "mute",
        user=_User(10, "<@10>"),
        reason="Sensitive internal note",
        moderator=_User(20, "<@20>"),
    )
    assert result == "<@10> muted. Reason: "


def test_response_renderer_appends_reason_once_and_bounds_output():
    result = render_moderation_response(
        {
            "moderation_kick_response": "x" * 1_500,
            "moderation_respond_with_reason": True,
        },
        "kick",
        user=_User(10, "<@10>"),
        reason="r" * 1_000,
        moderator=_User(20, "<@20>"),
    )
    assert len(result) <= MAX_RESPONSE_LENGTH
    assert result.endswith("...")


def test_response_renderer_rejects_unregistered_actions():
    with pytest.raises(ValueError):
        render_moderation_response(
            {},
            "massban",
            user=_User(10, "<@10>"),
            reason="Spam",
            moderator=_User(20, "<@20>"),
        )


def test_lockdown_channel_filter_defaults_to_all_and_honors_selection():
    channels = [SimpleNamespace(id=100), SimpleNamespace(id=200)]
    guild = SimpleNamespace(text_channels=channels)
    assert ChatCommands._configured_lockdown_channels(guild, {}) == channels
    assert ChatCommands._configured_lockdown_channels(
        guild,
        {"lockdown_channels": ["200", "999"]},
    ) == [channels[1]]


def test_lockdown_restore_state_round_trips_only_valid_entries():
    settings = {
        ChatCommands._LOCKDOWN_RESTORE_KEY: [
            {"channel_id": "200", "send_messages": None},
            {"channel_id": "100", "send_messages": True},
            {"channel_id": "bad", "send_messages": False},
            {"channel_id": "300", "send_messages": "invalid"},
        ]
    }
    state = ChatCommands._lockdown_restore_state(settings)
    assert state == {100: True, 200: None}
    assert ChatCommands._serialize_lockdown_restore_state(state) == [
        {"channel_id": "100", "send_messages": True},
        {"channel_id": "200", "send_messages": None},
    ]


class _SettingsDB:
    def __init__(self, settings):
        self.settings = settings

    async def get_settings(self, _guild_id):
        return self.settings


class _Bot:
    def __init__(self, settings, owner_ids=()):
        self.db = _SettingsDB(settings)
        self.owner_ids = set(owner_ids)


def _member(user_id, guild, *, role_ids=()):
    return SimpleNamespace(
        id=user_id,
        guild=guild,
        roles=[SimpleNamespace(id=role_id, name=f"role-{role_id}") for role_id in role_ids],
        guild_permissions=SimpleNamespace(administrator=False),
        bot=False,
    )


def test_protected_roles_block_moderators_but_not_owner_overrides():
    guild = SimpleNamespace(owner_id=1)
    moderator = _member(2, guild)
    target = _member(3, guild, role_ids=(999,))

    helper = HelperCommands()
    helper.bot = _Bot({"protected_roles": ["999"]})
    allowed, message = asyncio.run(helper.can_moderate(100, moderator, target))
    assert allowed is False
    assert "protected role" in message

    moderator.guild_permissions.administrator = True
    allowed, message = asyncio.run(
        helper.can_moderate(
            100,
            moderator,
            target,
            allow_protected_target=True,
        )
    )
    assert allowed is True
    assert message == ""

    bot_owner_helper = HelperCommands()
    bot_owner_helper.bot = _Bot({"protected_roles": ["999"]}, owner_ids=(2,))
    allowed, message = asyncio.run(
        bot_owner_helper.can_moderate(100, moderator, target)
    )
    assert allowed is True
    assert message == ""

    server_owner = _member(1, guild)
    allowed, message = asyncio.run(helper.can_moderate(100, server_owner, target))
    assert allowed is True
    assert message == ""
