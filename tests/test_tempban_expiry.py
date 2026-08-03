from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from cogs.moderation import Moderation
from db.enforcement_mixin import EnforcementMixin


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    async def fetchall(self):
        return self._rows


class _Connection:
    def __init__(self, rows):
        self._rows = rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, query):
        assert query == "SELECT * FROM tempbans"
        return _Cursor(self._rows)


@pytest.mark.asyncio
async def test_expired_tempban_query_accepts_legacy_iso_timestamps():
    now = datetime.now(timezone.utc)
    rows = [
        (1, 10, 100, 200, "expired", (now - timedelta(minutes=1)).isoformat(), now.isoformat()),
        (2, 10, 101, 200, "future", (now + timedelta(hours=1)).isoformat(), now.isoformat()),
    ]
    database = SimpleNamespace(get_connection=lambda: _Connection(rows))

    expired = await EnforcementMixin.get_expired_tempbans(database)

    assert [entry["user_id"] for entry in expired] == [100]


@pytest.mark.asyncio
async def test_expired_tempban_is_unbanned_logged_and_sent_rejoin_dm():
    user = SimpleNamespace(id=100, name="member")
    bot_actor = SimpleNamespace(id=999, name="Docket", display_avatar=SimpleNamespace(url="https://example.com/bot.png"))
    guild = SimpleNamespace(id=10, name="Guild", me=bot_actor, unban=AsyncMock())
    appeals = SimpleNamespace(notify_tempban_expired=AsyncMock(return_value=True))
    database = SimpleNamespace(
        get_expired_tempbans=AsyncMock(return_value=[{
            "guild_id": 10,
            "user_id": 100,
            "moderator_id": 200,
            "reason": "temporary ban",
        }]),
        remove_tempban=AsyncMock(),
        get_settings=AsyncMock(return_value={"moderation_dm_users": True}),
        create_case=AsyncMock(return_value=77),
    )
    bot = SimpleNamespace(
        db=database,
        user=bot_actor,
        get_guild=Mock(return_value=guild),
        fetch_user=AsyncMock(return_value=user),
        get_cog=Mock(side_effect=lambda name: appeals if name == "Appeals" else None),
    )
    moderation = object.__new__(Moderation)
    moderation.bot = bot
    moderation._suppress_duplicate_member_action_log = Mock()
    moderation.create_mod_embed = AsyncMock(return_value=discord.Embed(title="Member automatically unbanned"))
    moderation.log_action = AsyncMock()

    await moderation._process_expired_tempbans()

    guild.unban.assert_awaited_once_with(user, reason="Temporary ban expired")
    database.remove_tempban.assert_awaited_once_with(10, 100)
    appeals.notify_tempban_expired.assert_awaited_once_with(
        guild=guild,
        user=user,
        settings={"moderation_dm_users": True},
    )
    database.create_case.assert_awaited_once_with(10, 100, 999, "Unban", "Temporary ban expired")
    moderation.log_action.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_expiry_unban_stays_queued_for_retry():
    response = SimpleNamespace(status=403, reason="Forbidden")
    guild = SimpleNamespace(
        id=10,
        unban=AsyncMock(
            side_effect=discord.Forbidden(response, {"code": 50013, "message": "Missing Permissions"})
        ),
    )
    database = SimpleNamespace(
        get_expired_tempbans=AsyncMock(return_value=[{
            "guild_id": 10,
            "user_id": 100,
            "moderator_id": 200,
            "reason": "temporary ban",
        }]),
        remove_tempban=AsyncMock(),
    )
    bot = SimpleNamespace(
        db=database,
        get_guild=Mock(return_value=guild),
        fetch_user=AsyncMock(return_value=SimpleNamespace(id=100)),
    )
    moderation = object.__new__(Moderation)
    moderation.bot = bot
    moderation._suppress_duplicate_member_action_log = Mock()

    await moderation._process_expired_tempbans()

    database.remove_tempban.assert_not_awaited()
