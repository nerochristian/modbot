import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from cogs.aimoderation import ToolRegistry, ToolType
from cogs.aimoderation.handlers.admin import _raw_api_safety_error
from cogs.aimoderation.handlers.channels import handle_unlock_channel
from cogs.aimoderation.handlers.messages import handle_purge
from cogs.aimoderation.handlers.query_handlers import (
    handle_find_inactive,
    handle_scan_channel,
)


class AIModerationPackageTests(unittest.IsolatedAsyncioTestCase):
    def test_every_declared_tool_has_a_registered_handler(self) -> None:
        self.assertEqual(set(ToolType), set(ToolRegistry.list_tools()))

    async def test_unlock_restores_inherited_send_permission(self) -> None:
        channel = SimpleNamespace(set_permissions=AsyncMock())
        default_role = object()
        ctx = SimpleNamespace(
            message=SimpleNamespace(channel=channel),
            guild=SimpleNamespace(default_role=default_role),
            actor="Moderator",
        )

        result = await handle_unlock_channel(ctx)

        self.assertTrue(result.success)
        channel.set_permissions.assert_awaited_once_with(
            default_role,
            send_messages=None,
            reason="Unlock by Moderator",
        )

    async def test_inactive_query_handles_aware_join_dates(self) -> None:
        now = datetime.now(timezone.utc)
        inactive = SimpleNamespace(
            id=1,
            bot=False,
            joined_at=now - timedelta(days=90),
            mention="<@1>",
        )
        recent = SimpleNamespace(
            id=2,
            bot=False,
            joined_at=now - timedelta(days=2),
            mention="<@2>",
        )
        guild = SimpleNamespace(me=None, text_channels=[], members=[inactive, recent])
        values = {"days": 30, "limit": 20}
        ctx = SimpleNamespace(
            args=values,
            guild=guild,
            int_arg=lambda key, default=0: int(values.get(key, default)),
        )

        result = await handle_find_inactive(ctx)

        self.assertTrue(result.success)
        self.assertIn("<@1>", result.message)
        self.assertNotIn("<@2>", result.message)

    async def test_scan_channel_uses_loaded_automod_engine_api(self) -> None:
        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 10
        channel.mention = "<#10>"
        first = SimpleNamespace(author=SimpleNamespace(bot=False))
        second = SimpleNamespace(author=SimpleNamespace(bot=False))

        async def history(*, limit):
            self.assertEqual(limit, 2)
            for message in (first, second):
                yield message

        channel.history = history
        engine = SimpleNamespace(
            evaluate=AsyncMock(
                side_effect=[SimpleNamespace(rule="spam"), None]
            )
        )
        db = SimpleNamespace(get_settings=AsyncMock(return_value={"automod_spam_enabled": True}))
        bot = SimpleNamespace(
            db=db,
            get_cog=lambda name: SimpleNamespace(engine=engine) if name == "AutoMod" else None,
        )
        values = {"amount": 2}
        ctx = SimpleNamespace(
            args=values,
            guild=SimpleNamespace(id=1),
            message=SimpleNamespace(channel=channel),
            actor=SimpleNamespace(id=2),
            cog=SimpleNamespace(bot=bot),
            arg=lambda key, default=None: values.get(key, default),
            int_arg=lambda key, default=0: int(values.get(key, default)),
        )

        result = await handle_scan_channel(ctx)

        self.assertTrue(result.success)
        self.assertIn("1 violations found", result.message)
        self.assertEqual(engine.evaluate.await_count, 2)
        for call in engine.evaluate.await_args_list:
            self.assertTrue(call.kwargs["dry_run"])

    async def test_targeted_purge_uses_bounded_history_scan(self) -> None:
        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 10
        channel.mention = "<#10>"
        channel.purge = AsyncMock(return_value=[])
        source_message = SimpleNamespace(id=999, channel=channel)
        values = {"amount": 10, "target_user_id": 123}
        bot = SimpleNamespace(get_cog=lambda name: None)
        ctx = SimpleNamespace(
            args=values,
            message=source_message,
            guild=SimpleNamespace(id=1, me=None, text_channels=[channel]),
            actor=SimpleNamespace(id=2),
            decision=SimpleNamespace(),
            cog=SimpleNamespace(bot=bot, log_action=AsyncMock()),
            arg=lambda key, default=None: values.get(key, default),
            bool_arg=lambda key, default=False: bool(values.get(key, default)),
            int_arg=lambda key, default=0: int(values.get(key, default)),
            str_arg=lambda key, default="No reason provided": str(values.get(key, default)),
        )

        result = await handle_purge(ctx)

        self.assertTrue(result.success)
        self.assertEqual(channel.purge.await_args.kwargs["limit"], 100)

    def test_raw_api_rejects_cross_server_and_webhook_routes(self) -> None:
        actor = SimpleNamespace(id=1)
        guild = SimpleNamespace(
            id=111111111111111111,
            get_channel_or_thread=lambda channel_id: object() if channel_id == 333333333333333333 else None,
            get_channel=lambda channel_id: None,
        )
        ctx = SimpleNamespace(
            actor=actor,
            guild=guild,
            cog=SimpleNamespace(bot=SimpleNamespace(user=SimpleNamespace(id=2))),
        )

        with patch(
            "cogs.aimoderation.handlers.admin.is_bot_owner_id",
            return_value=True,
        ):
            self.assertIsNone(
                _raw_api_safety_error(
                    ctx,
                    "GET",
                    "/guilds/111111111111111111/channels",
                    {},
                )
            )
            self.assertIsNotNone(
                _raw_api_safety_error(
                    ctx,
                    "GET",
                    "/guilds/222222222222222222/channels",
                    {},
                )
            )
            self.assertIsNotNone(
                _raw_api_safety_error(
                    ctx,
                    "DELETE",
                    "/webhooks/333333333333333333",
                    {},
                )
            )


if __name__ == "__main__":
    unittest.main()
