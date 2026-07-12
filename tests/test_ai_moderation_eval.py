"""AI-moderation security & correctness eval harness (live cogs/aimoderation).

Replaces the scenario coverage removed with the dead cogs/ai_moderation package,
targeting the LIVE cog instead. These are pure-logic checks (no Discord network):

1. validate_tool_access enforces the permission gauntlet for EVERY registered
   tool — a plain member is denied every permissioned tool; owner-only tools are
   denied to non-owners and allowed to owners.
2. _parse_duration_seconds parses compound durations correctly (regression lock
   for the "1h30m" bug where only the trailing unit counted).
"""

import types

import pytest

import cogs.aimoderation.aimoderation as aimod
from cogs.aimoderation.aimoderation import AIModeration
from cogs.aimoderation.types import ToolType
from cogs.aimoderation.registry import ToolRegistry


# --------------------------------------------------------------------------- #
# Mocks
# --------------------------------------------------------------------------- #
class _Perms:
    """Stand-in for discord.Permissions — everything False unless granted."""

    def __init__(self, **granted):
        self._granted = granted

    def __getattr__(self, name):
        return self._granted.get(name, False)


def _member(user_id, **perms):
    m = types.SimpleNamespace(id=user_id)
    m.guild_permissions = _Perms(**perms)
    # isinstance(actor, discord.Member) is checked in validate_tool_access;
    # patch that below so these lightweight stubs pass.
    return m


def _guild(bot_member):
    return types.SimpleNamespace(me=bot_member)


@pytest.fixture(autouse=True)
def _treat_stubs_as_members(monkeypatch):
    import discord
    monkeypatch.setattr(discord, "Member", types.SimpleNamespace, raising=False)
    # No one is a bot owner unless a test opts in.
    monkeypatch.setattr(aimod, "is_bot_owner_id", lambda uid: uid == 999, raising=True)


def _cog():
    return AIModeration.__new__(AIModeration)


_PERMISSIONED_TOOLS = [
    t for t in ToolType
    if getattr(ToolRegistry.get_metadata(t), "required_permission", None)
]
_OWNER_ONLY_TOOLS = [
    t for t in ToolType
    if getattr(ToolRegistry.get_metadata(t), "required_permission", None) == "bot_owner"
]


# --------------------------------------------------------------------------- #
# Permission gauntlet
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tool", _PERMISSIONED_TOOLS, ids=lambda t: t.value)
def test_plain_member_denied_every_permissioned_tool(tool):
    cog = _cog()
    actor = _member(1)  # no permissions, not owner
    bot = _member(2, administrator=True)
    err = cog.validate_tool_access(actor, _guild(bot), tool)
    assert err is not None, f"{tool.value} allowed a permissionless member"


@pytest.mark.parametrize("tool", _OWNER_ONLY_TOOLS, ids=lambda t: t.value)
def test_owner_only_tools_block_non_owner_allow_owner(tool):
    cog = _cog()
    admin_non_owner = _member(1, administrator=True)
    assert cog.validate_tool_access(admin_non_owner, _guild(_member(2)), tool) is not None
    owner = _member(999)  # matches patched is_bot_owner_id
    assert cog.validate_tool_access(owner, _guild(_member(2)), tool) is None


def test_member_with_required_permission_is_allowed():
    cog = _cog()
    ban_tool = ToolType.BAN
    actor = _member(1, ban_members=True)
    bot = _member(2, ban_members=True)
    assert cog.validate_tool_access(actor, _guild(bot), ban_tool) is None


def test_actor_has_permission_but_bot_missing_is_denied():
    cog = _cog()
    actor = _member(1, ban_members=True)
    bot = _member(2)  # bot lacks ban_members
    assert cog.validate_tool_access(actor, _guild(bot), ToolType.BAN) is not None


# --------------------------------------------------------------------------- #
# Duration parsing (regression lock for the compound-duration bug)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "text,expected",
    [
        ("1h30m", 5400),
        ("2h30m", 9000),
        ("1d12h", 129600),
        ("90m", 5400),
        ("2d", 172800),
        ("30s", 30),
        ("1w", 604800),
        ("2 hours 15 mins", 8100),
        ("for 5", 300),   # bare "for N" -> N minutes
        ("1hello", None), # not a valid unit, must not match "1h"
        ("", None),
        ("nothing", None),
    ],
)
def test_parse_duration_seconds(text, expected):
    cog = _cog()
    assert cog._parse_duration_seconds(text) == expected
