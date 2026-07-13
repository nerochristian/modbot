import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from cogs.antiraid import AntiRaid


class FakeOverwrite:
    def __init__(self, send_messages=None):
        self.send_messages = send_messages

    def is_empty(self):
        return self.send_messages is None


class FakeChannel:
    def __init__(self, channel_id, send_messages=None):
        self.id = channel_id
        self._overwrite = FakeOverwrite(send_messages)
        self.set_permissions = AsyncMock(side_effect=self._save_overwrite)

    def overwrites_for(self, _role):
        return FakeOverwrite(self._overwrite.send_messages)

    async def _save_overwrite(self, _role, *, overwrite=None, reason=None):
        self._overwrite = overwrite or FakeOverwrite()
        self.last_reason = reason


class FakeGuild:
    def __init__(self, channels):
        self.id = 9001
        self.default_role = object()
        self.text_channels = channels
        self._channels = {channel.id: channel for channel in channels}

    def get_channel(self, channel_id):
        return self._channels.get(channel_id)


class AntiRaidLockdownTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SimpleNamespace(set_setting=AsyncMock())
        self.cog = object.__new__(AntiRaid)
        self.cog.bot = SimpleNamespace(db=self.db)

    async def test_lockdown_only_touches_configured_channels_and_snapshots_state(self):
        configured = FakeChannel(101, True)
        untouched = FakeChannel(202, None)
        guild = FakeGuild([configured, untouched])

        locked = await self.cog._lock_raid_channels(
            guild,
            {"lockdown_channels": ["101"]},
            reason="test lockdown",
        )

        self.assertEqual(locked, 1)
        self.assertIs(configured._overwrite.send_messages, False)
        untouched.set_permissions.assert_not_awaited()
        self.db.set_setting.assert_awaited_once_with(
            guild.id,
            "moderation_lockdown_restore",
            [{"channel_id": "101", "send_messages": True}],
        )

    async def test_unlockdown_restores_exact_allow_state(self):
        channel = FakeChannel(101, False)
        guild = FakeGuild([channel])

        unlocked = await self.cog._unlock_raid_channels(
            guild,
            {
                "moderation_lockdown_restore": [
                    {"channel_id": "101", "send_messages": True},
                ],
            },
            reason="test unlock",
        )

        self.assertEqual(unlocked, 1)
        self.assertIs(channel._overwrite.send_messages, True)
        self.db.set_setting.assert_awaited_once_with(
            guild.id,
            "moderation_lockdown_restore",
            [],
        )

    async def test_unlockdown_removes_empty_overwrite_when_original_was_inherited(self):
        channel = FakeChannel(101, False)
        guild = FakeGuild([channel])

        await self.cog._unlock_raid_channels(
            guild,
            {
                "moderation_lockdown_restore": [
                    {"channel_id": "101", "send_messages": None},
                ],
            },
            reason="test inherited restore",
        )

        _, kwargs = channel.set_permissions.await_args
        self.assertIsNone(kwargs["overwrite"])
        self.assertIsNone(channel._overwrite.send_messages)


if __name__ == "__main__":
    unittest.main()
