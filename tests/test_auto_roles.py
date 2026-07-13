from types import SimpleNamespace

import pytest

from cogs.roles import Roles, autoroles_enabled


class _SettingsDB:
    def __init__(self, settings: dict):
        self.settings = settings

    async def get_settings(self, _guild_id: int) -> dict:
        return self.settings


class _Role:
    def __init__(self, role_id: int, position: int):
        self.id = role_id
        self.position = position

    def __lt__(self, other: "_Role") -> bool:
        return self.position < other.position


class _Guild:
    def __init__(self, role: _Role):
        self.id = 123
        self._role = role
        self.me = SimpleNamespace(
            guild_permissions=SimpleNamespace(manage_roles=True),
            top_role=_Role(999, 100),
        )

    def get_role(self, role_id: int):
        return self._role if role_id == self._role.id else None


class _Member:
    def __init__(self, guild: _Guild):
        self.bot = False
        self.guild = guild
        self.added_roles: list[tuple[_Role, str]] = []

    async def add_roles(self, role: _Role, *, reason: str) -> None:
        self.added_roles.append((role, reason))


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        ({}, False),
        ({"auto_role": 456}, True),
        ({"auto_role": "456"}, True),
        ({"auto_role": 456, "autoroles_enabled": False}, False),
        ({"autoroles_enabled": True}, True),
        ({"auto_role": 456, "modules": {"autoroles": {"enabled": False}}}, False),
        ({"auto_role": "invalid"}, False),
        ({"auto_role": True}, False),
    ],
)
def test_autoroles_enabled_honors_explicit_state_and_legacy_role(settings, expected):
    assert autoroles_enabled(settings) is expected


async def _run_join(settings: dict) -> _Member:
    role = _Role(456, 10)
    guild = _Guild(role)
    member = _Member(guild)
    cog = Roles(SimpleNamespace(db=_SettingsDB(settings)))
    await cog.on_member_join(member)
    return member


@pytest.mark.asyncio
async def test_explicit_false_blocks_legacy_auto_role_assignment():
    member = await _run_join({"auto_role": 456, "autoroles_enabled": False})
    assert member.added_roles == []


@pytest.mark.asyncio
async def test_missing_flag_preserves_legacy_configured_role_assignment():
    member = await _run_join({"auto_role": 456})
    assert [(role.id, reason) for role, reason in member.added_roles] == [
        (456, "Automatic join role"),
    ]


@pytest.mark.asyncio
async def test_explicit_true_assigns_the_configured_role():
    member = await _run_join({"auto_role": 456, "autoroles_enabled": True})
    assert [role.id for role, _reason in member.added_roles] == [456]


@pytest.mark.asyncio
async def test_verification_keeps_precedence_over_enabled_auto_roles():
    member = await _run_join(
        {
            "auto_role": 456,
            "autoroles_enabled": True,
            "verification_enabled": True,
        }
    )
    assert member.added_roles == []
