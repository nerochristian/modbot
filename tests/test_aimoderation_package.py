import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from cogs.ai_scheduler import AIScheduler
from cogs.aimoderation import ToolRegistry, ToolType
from cogs.aimoderation.handlers.admin import (
    _make_activity_fetcher,
    _raw_api_safety_error,
    handle_execute_python,
)
from cogs.aimoderation.handlers.channels import handle_unlock_channel
from cogs.aimoderation.handlers.messages import handle_purge
from cogs.aimoderation.handlers.members import handle_timeout, handle_unban, handle_warn
from cogs.aimoderation.bridge import warn_member
from cogs.aimoderation.handlers.query_handlers import (
    handle_find_inactive,
    handle_scan_channel,
)
from cogs.aimoderation.python_runtime import (
    PythonSafetyError,
    execution_digest,
    safe_builtins,
    validate_python_code,
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

    async def test_unban_reports_not_banned_without_calling_unban(self) -> None:
        response = SimpleNamespace(status=404, reason="Not Found")
        unknown_ban = discord.NotFound(
            response,
            {"code": 10026, "message": "Unknown Ban"},
        )
        guild = SimpleNamespace(
            id=1,
            fetch_ban=AsyncMock(side_effect=unknown_ban),
            unban=AsyncMock(),
        )
        ctx = SimpleNamespace(
            args={"target_user_id": 20},
            guild=guild,
            actor="Moderator",
            cog=SimpleNamespace(bot=SimpleNamespace()),
            str_arg=lambda key, default="No reason provided": default,
        )

        result = await handle_unban(ctx)

        self.assertFalse(result.success)
        self.assertIn("not currently banned", result.message)
        guild.unban.assert_not_awaited()

    async def test_warn_handler_records_requested_warning_count_atomically(self) -> None:
        target = SimpleNamespace(
            id=20,
            name="target",
            display_name="Target",
            mention="<@20>",
            display_avatar=SimpleNamespace(url="https://example.invalid/avatar.png"),
        )
        actor = SimpleNamespace(id=10, mention="<@10>")
        database = SimpleNamespace(
            add_warnings=AsyncMock(return_value=([101, 102, 103], 5))
        )
        cog = SimpleNamespace(
            bot=SimpleNamespace(db=database),
            can_moderate=lambda moderator, member: True,
            log_action=AsyncMock(),
        )
        values = {"reason": "repeated spam", "warning_count": 3}
        ctx = SimpleNamespace(
            resolve_target=AsyncMock(return_value=target),
            cog=cog,
            actor=actor,
            guild=SimpleNamespace(id=1),
            message=SimpleNamespace(),
            decision=SimpleNamespace(),
            str_arg=lambda key, default="No reason provided": str(
                values.get(key, default)
            ),
            int_arg=lambda key, default=0: int(values.get(key, default)),
        )

        result = await handle_warn(ctx)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "3 warnings issued. Total warnings: 5.")
        database.add_warnings.assert_awaited_once_with(
            guild_id=1,
            user_id=20,
            moderator_id=10,
            reason="repeated spam",
            count=3,
        )
        self.assertIn("Warnings Issued", result.embed.title)
        cog.log_action.assert_awaited_once()

    async def test_warn_handler_rejects_unsafe_batch_size(self) -> None:
        target = SimpleNamespace(id=20, display_name="Target")
        database = SimpleNamespace(add_warnings=AsyncMock())
        cog = SimpleNamespace(
            bot=SimpleNamespace(db=database),
            can_moderate=lambda moderator, member: True,
        )
        ctx = SimpleNamespace(
            resolve_target=AsyncMock(return_value=target),
            cog=cog,
            actor=SimpleNamespace(id=10),
            int_arg=lambda key, default=0: 11,
            str_arg=lambda key, default="No reason provided": "spam",
        )

        result = await handle_warn(ctx)

        self.assertFalse(result.success)
        self.assertIn("between 1 and 10", result.message)
        database.add_warnings.assert_not_awaited()

    async def test_warn_handler_applies_highest_rule_crossed_by_batch(self) -> None:
        target = SimpleNamespace(
            id=20,
            name="target",
            display_name="Target",
            mention="<@20>",
            display_avatar=SimpleNamespace(url="https://example.invalid/avatar.png"),
        )
        actor = SimpleNamespace(id=10, mention="<@10>")
        database = SimpleNamespace(
            add_warnings=AsyncMock(return_value=([101, 102, 103], 5)),
            get_settings=AsyncMock(return_value={
                "moderation_autopunish_rules": [
                    {"warnings": 3, "action": "timeout", "durationMinutes": 30},
                    {"warnings": 5, "action": "kick", "durationMinutes": 0},
                ],
            }),
            create_case=AsyncMock(return_value=8),
        )
        guild = SimpleNamespace(id=1, kick=AsyncMock())
        cog = SimpleNamespace(
            bot=SimpleNamespace(db=database, user=SimpleNamespace(id=99)),
            can_moderate=lambda moderator, member: True,
            log_action=AsyncMock(),
        )
        values = {"reason": "repeated spam", "warning_count": 3}
        ctx = SimpleNamespace(
            resolve_target=AsyncMock(return_value=target),
            cog=cog,
            actor=actor,
            guild=guild,
            message=SimpleNamespace(),
            decision=SimpleNamespace(),
            str_arg=lambda key, default="No reason provided": str(values.get(key, default)),
            int_arg=lambda key, default=0: int(values.get(key, default)),
        )

        result = await handle_warn(ctx)

        self.assertTrue(result.success)
        self.assertIn("Kicked automatically", result.message)
        guild.kick.assert_awaited_once_with(
            target,
            reason="AI warning escalation: 5 warnings reached",
        )
        database.create_case.assert_awaited_once_with(
            1,
            20,
            99,
            "Kick",
            "AI warning escalation: 5 warnings reached",
            None,
        )

    async def test_bridge_fallback_warn_applies_escalation_and_records_case(self) -> None:
        target = SimpleNamespace(id=20, display_name="Target")
        actor = SimpleNamespace(id=10)
        guild = SimpleNamespace(id=1, ban=AsyncMock())
        source = SimpleNamespace(guild=guild)
        database = SimpleNamespace(
            add_warning=AsyncMock(return_value=(101, 3)),
            get_settings=AsyncMock(return_value={
                "moderation_preserve_ban_messages": True,
                "moderation_autopunish_rules": [
                    {"warnings": 3, "action": "ban", "durationMinutes": 0},
                ],
            }),
            create_case=AsyncMock(return_value=4),
        )
        bot = SimpleNamespace(
            db=database,
            user=SimpleNamespace(id=99),
            get_cog=lambda name: None,
        )

        result = await warn_member(
            source,
            target,
            "repeated spam",
            actor=actor,
            bot=bot,
        )

        self.assertIn("Automatically banned", result)
        guild.ban.assert_awaited_once_with(
            target,
            reason="AI warning escalation: 3 warnings reached",
            delete_message_days=0,
        )
        database.create_case.assert_awaited_once_with(
            1,
            20,
            99,
            "Ban",
            "AI warning escalation: 3 warnings reached",
            None,
        )

    async def test_warn_handler_keeps_recorded_warning_when_escalation_is_denied(self) -> None:
        target = SimpleNamespace(
            id=20,
            name="target",
            display_name="Target",
            mention="<@20>",
            display_avatar=SimpleNamespace(url="https://example.invalid/avatar.png"),
        )
        actor = SimpleNamespace(id=10, mention="<@10>")
        database = SimpleNamespace(
            add_warnings=AsyncMock(return_value=([103], 3)),
            get_settings=AsyncMock(return_value={
                "moderation_autopunish_rules": [
                    {"warnings": 3, "action": "kick", "durationMinutes": 0},
                ],
            }),
            create_case=AsyncMock(),
        )
        response = MagicMock(status=403, reason="Forbidden")
        guild = SimpleNamespace(
            id=1,
            kick=AsyncMock(side_effect=discord.Forbidden(response, "denied")),
        )
        cog = SimpleNamespace(
            bot=SimpleNamespace(db=database, user=SimpleNamespace(id=99)),
            can_moderate=lambda moderator, member: True,
            log_action=AsyncMock(),
        )
        ctx = SimpleNamespace(
            resolve_target=AsyncMock(return_value=target),
            cog=cog,
            actor=actor,
            guild=guild,
            message=SimpleNamespace(),
            decision=SimpleNamespace(),
            str_arg=lambda key, default="No reason provided": "repeated spam",
            int_arg=lambda key, default=0: 1,
        )

        result = await handle_warn(ctx)

        self.assertTrue(result.success)
        self.assertIn("lacks permission", result.message)
        database.create_case.assert_not_awaited()

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
        self.assertEqual(channel.purge.await_args.kwargs["limit"], 500)

    def test_python_runtime_accepts_normal_discord_action_code(self) -> None:
        code = (
            "members = [member for member in guild.members if not member.bot]\n"
            "members.sort(key=lambda member: member.joined_at or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))\n"
            "return f'Found {len(members)} members.'"
        )

        compiled = validate_python_code(code)

        self.assertIsNotNone(compiled)
        self.assertIsNotNone(validate_python_code("import time\nreturn time.monotonic()"))

    def test_python_runtime_allows_only_permission_flag_setattr(self) -> None:
        code = (
            "permissions = discord.Permissions(administrator=True)\n"
            "setattr(permissions, 'administrator', False)\n"
            "return permissions.administrator"
        )
        permissions = discord.Permissions(administrator=True)
        restricted_setattr = safe_builtins()["setattr"]

        self.assertIsNotNone(validate_python_code(code))
        restricted_setattr(permissions, "administrator", False)
        self.assertFalse(permissions.administrator)
        with self.assertRaises(TypeError):
            restricted_setattr(SimpleNamespace(administrator=True), "administrator", False)
        with self.assertRaises(AttributeError):
            restricted_setattr(permissions, "__class__", False)
        with self.assertRaises(TypeError):
            restricted_setattr(permissions, "administrator", "false")

    def test_python_runtime_getattr_blocks_dynamic_sensitive_access(self) -> None:
        restricted_getattr = safe_builtins()["getattr"]
        permissions = discord.Permissions(administrator=True)

        self.assertTrue(restricted_getattr(permissions, "administrator"))
        self.assertEqual(restricted_getattr(SimpleNamespace(), "missing", "fallback"), "fallback")
        for blocked_name in ("__dict__", "token", "http", "close", "delete"):
            with self.subTest(blocked_name=blocked_name), self.assertRaises(AttributeError):
                restricted_getattr(SimpleNamespace(), blocked_name, None)

        self.assertTrue(safe_builtins()["hasattr"](permissions, "administrator"))

    def test_python_runtime_blocks_escape_and_lifecycle_operations(self) -> None:
        blocked = (
            "import os\nreturn os.environ",
            "return open('token.txt').read()",
            "return bot.http.token",
            "await bot.close()",
            "asyncio.create_task(channel.send('later'))",
            "while True:\n    await asyncio.sleep(1)",
            "return guild.__dict__",
            "await guild.delete()",
        )

        for code in blocked:
            with self.subTest(code=code), self.assertRaises(PythonSafetyError):
                validate_python_code(code)

    async def test_execute_python_runs_digest_bound_plan_and_returns_result(self) -> None:
        code = "return 'Created 3 channels.'"
        values = {
            "code": code,
            "code_sha256": execution_digest(code),
            "summary": "Create three project channels",
        }
        actor = SimpleNamespace(id=10, mention="<@10>")
        bot = SimpleNamespace(
            is_owner=AsyncMock(return_value=True),
            get_cog=lambda name: None,
        )
        cog = SimpleNamespace(bot=bot, log_action=AsyncMock())
        ctx = SimpleNamespace(
            actor=actor,
            guild=SimpleNamespace(text_channels=[]),
            message=SimpleNamespace(channel=SimpleNamespace()),
            decision=SimpleNamespace(reason="owner action"),
            cog=cog,
            arg=lambda key, default=None: values.get(key, default),
        )

        with patch(
            "cogs.aimoderation.handlers.admin.is_bot_owner_id",
            return_value=True,
        ):
            result = await handle_execute_python(ctx)

        self.assertTrue(result.success)
        self.assertIn("Created 3 channels", result.message)
        self.assertIn(execution_digest(code)[:12], result.message)
        cog.log_action.assert_awaited_once()

    async def test_execute_python_send_bounded_attaches_long_reports(self) -> None:
        actor = SimpleNamespace(id=123, mention="<@123>")
        destination = SimpleNamespace(send=AsyncMock())
        destination.send.return_value = SimpleNamespace(id=456)
        cog = SimpleNamespace(
            bot=SimpleNamespace(is_owner=AsyncMock(return_value=True)),
        )
        ctx = SimpleNamespace(
            actor=actor,
            cog=cog,
            guild=SimpleNamespace(id=1),
            message=SimpleNamespace(channel=destination),
            arg=lambda name, default="": {
                "code": "await send_bounded(channel, 'x' * 2500, filename='raid rollback.json')\nreturn 'sent'",
                "summary": "Send a bounded report",
            }.get(name, default),
        )

        with patch("cogs.aimoderation.handlers.admin.is_bot_owner_id", return_value=True), patch(
            "cogs.aimoderation.handlers.admin._log_execution", new=AsyncMock()
        ):
            result = await handle_execute_python(ctx)

        self.assertTrue(result.success)
        destination.send.assert_awaited_once()
        args, kwargs = destination.send.await_args
        self.assertEqual(args[0], "The full action report is attached.")
        self.assertEqual(kwargs["file"].filename, "raid-rollback.json")

    async def test_execute_python_can_persist_digest_bound_follow_up(self) -> None:
        actor = SimpleNamespace(id=123, mention="<@123>")
        connection = AsyncMock()
        connection_context = AsyncMock()
        connection_context.__aenter__.return_value = connection
        bot = SimpleNamespace(
            is_owner=AsyncMock(return_value=True),
            db=SimpleNamespace(get_connection=lambda: connection_context),
        )
        follow_up = "return 'follow-up complete'"
        code = (
            "run_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)\n"
            f"result = await schedule_durable_action(run_at, {follow_up!r}, summary='archive stale tickets')\n"
            "return result['code_sha256']"
        )
        ctx = SimpleNamespace(
            actor=actor,
            cog=SimpleNamespace(bot=bot),
            guild=SimpleNamespace(id=1),
            message=SimpleNamespace(channel=SimpleNamespace()),
            arg=lambda name, default="": {"code": code, "summary": "Schedule a durable follow-up"}.get(name, default),
        )

        with patch("cogs.aimoderation.handlers.admin.is_bot_owner_id", return_value=True), patch(
            "cogs.aimoderation.handlers.admin._log_execution", new=AsyncMock()
        ):
            result = await handle_execute_python(ctx)

        self.assertTrue(result.success)
        connection.execute.assert_awaited_once()
        query, params = connection.execute.await_args.args
        self.assertIn("INSERT INTO scheduled_tasks", query)
        self.assertEqual(params[0:2], (1, 123))
        payload = json.loads(params[2])
        self.assertEqual(payload["code"], follow_up)
        self.assertEqual(payload["code_sha256"], execution_digest(follow_up))
        connection.commit.assert_awaited_once()

    async def test_activity_fetcher_supports_detailed_message_records(self) -> None:
        now = datetime.now(timezone.utc)
        author = SimpleNamespace(id=42, bot=False, __str__=lambda self: "Member")
        record = SimpleNamespace(
            id=99,
            author=author,
            content="repeat me",
            created_at=now,
            jump_url="https://discord.com/channels/1/2/99",
        )

        class FakeTextChannel:
            id = 2
            name = "general"

            def history(self, **kwargs):
                async def iterator():
                    yield record

                return iterator()

        guild = SimpleNamespace(text_channels=[FakeTextChannel()])
        fetch_recent_activity = _make_activity_fetcher(guild)

        summary = await fetch_recent_activity(days=1)
        detailed = await fetch_recent_activity(
            lookback=timedelta(hours=1),
            kinds=["messages"],
        )

        self.assertEqual(summary, {42: now})
        self.assertEqual(detailed[0]["content"], "repeat me")
        self.assertEqual(detailed[0]["channel_id"], 2)

    async def test_bulk_timeout_excludes_named_role_and_skips_unsafe_targets(self) -> None:
        excluded_role = SimpleNamespace(id=5, name="Above all", mention="<@&5>")
        ordinary_role = SimpleNamespace(id=6, name="Member")

        def member(member_id, *, roles=(), bot=False, administrator=False):
            return SimpleNamespace(
                id=member_id,
                mention=f"<@{member_id}>",
                bot=bot,
                roles=list(roles),
                guild_permissions=SimpleNamespace(administrator=administrator),
                timeout=AsyncMock(),
                send=AsyncMock(),
            )

        actor = member(10)
        actor.mention = "<@10>"
        bot_member = member(99, bot=True)
        excluded = member(20, roles=(excluded_role,))
        eligible = member(30, roles=(ordinary_role,))
        administrator = member(40, roles=(ordinary_role,), administrator=True)
        above_bot = member(50, roles=(ordinary_role,))
        guild = SimpleNamespace(
            id=1,
            name="Guild",
            owner_id=1,
            me=bot_member,
            members=[actor, bot_member, excluded, eligible, administrator, above_bot],
        )
        database = SimpleNamespace(
            get_settings=AsyncMock(return_value={"moderation_dm_users": False})
        )
        cog = SimpleNamespace(
            bot=SimpleNamespace(db=database),
            config=SimpleNamespace(timeout_default_seconds=3600, timeout_max_seconds=259200),
            resolve_role=AsyncMock(return_value=excluded_role),
            can_moderate=lambda moderator, target: target.id != above_bot.id,
            log_action=AsyncMock(),
        )
        values = {
            "all_members": True,
            "exclude_role_id": excluded_role.id,
            "seconds": 600,
            "reason": "requested bulk moderation",
        }
        ctx = SimpleNamespace(
            args=values,
            arg=lambda key, default=None: values.get(key, default),
            bool_arg=lambda key, default=False: bool(values.get(key, default)),
            int_arg=lambda key, default=0: int(values.get(key, default)),
            str_arg=lambda key, default="No reason provided": str(values.get(key, default)),
            cog=cog,
            actor=actor,
            guild=guild,
            message=SimpleNamespace(),
            decision=SimpleNamespace(),
        )

        result = await handle_timeout(ctx)

        self.assertTrue(result.success)
        self.assertIn("Muted **1**", result.message)
        self.assertIn("Excluded by role: **1**", result.message)
        eligible.timeout.assert_awaited_once()
        excluded.timeout.assert_not_awaited()
        administrator.timeout.assert_not_awaited()
        above_bot.timeout.assert_not_awaited()
        cog.log_action.assert_awaited_once()

    async def test_bulk_timeout_honors_explicit_member_exclusions(self) -> None:
        def member(member_id):
            return SimpleNamespace(
                id=member_id,
                mention=f"<@{member_id}>",
                bot=False,
                roles=[],
                guild_permissions=SimpleNamespace(administrator=False),
                timeout=AsyncMock(),
                send=AsyncMock(),
            )

        actor = member(10)
        explicitly_excluded = member(20)
        eligible = member(30)
        bot_member = SimpleNamespace(id=99, mention="<@99>", bot=True, roles=[])
        guild = SimpleNamespace(
            id=1,
            name="Guild",
            owner_id=1,
            me=bot_member,
            members=[actor, explicitly_excluded, eligible, bot_member],
        )
        database = SimpleNamespace(
            get_settings=AsyncMock(return_value={"moderation_dm_users": False})
        )
        cog = SimpleNamespace(
            bot=SimpleNamespace(db=database),
            config=SimpleNamespace(timeout_default_seconds=3600, timeout_max_seconds=259200),
            resolve_role=AsyncMock(),
            can_moderate=lambda moderator, target: True,
            log_action=AsyncMock(),
        )
        values = {
            "all_members": True,
            "exclude_user_ids": [actor.id, explicitly_excluded.id],
            "seconds": 600,
        }
        ctx = SimpleNamespace(
            arg=lambda key, default=None: values.get(key, default),
            bool_arg=lambda key, default=False: bool(values.get(key, default)),
            int_arg=lambda key, default=0: int(values.get(key, default)),
            str_arg=lambda key, default="No reason provided": str(values.get(key, default)),
            cog=cog,
            actor=actor,
            guild=guild,
            message=SimpleNamespace(),
            decision=SimpleNamespace(),
        )

        result = await handle_timeout(ctx)

        self.assertTrue(result.success)
        self.assertIn("Explicitly excluded: **2**", result.message)
        explicitly_excluded.timeout.assert_not_awaited()
        eligible.timeout.assert_awaited_once()

    async def test_execute_python_rejects_code_changed_after_confirmation(self) -> None:
        code = "return 'safe'"
        values = {"code": code, "code_sha256": execution_digest("return 'different'")}
        bot = SimpleNamespace(is_owner=AsyncMock(return_value=True), get_cog=lambda name: None)
        ctx = SimpleNamespace(
            actor=SimpleNamespace(id=10),
            guild=SimpleNamespace(text_channels=[]),
            message=SimpleNamespace(channel=SimpleNamespace()),
            decision=SimpleNamespace(reason="owner action"),
            cog=SimpleNamespace(bot=bot, log_action=AsyncMock()),
            arg=lambda key, default=None: values.get(key, default),
        )

        with patch(
            "cogs.aimoderation.handlers.admin.is_bot_owner_id",
            return_value=True,
        ):
            result = await handle_execute_python(ctx)

        self.assertFalse(result.success)
        self.assertIn("changed after confirmation", result.message)

    async def test_scheduled_python_is_revalidated_before_execution(self) -> None:
        scheduler = object.__new__(AIScheduler)
        scheduler.bot = SimpleNamespace(get_guild=lambda guild_id: SimpleNamespace(id=guild_id))

        with patch("cogs.ai_scheduler.is_bot_owner_id", return_value=True), self.assertRaises(PythonSafetyError):
            await scheduler._execute_task(
                1,
                "execute_python",
                {"code": "import subprocess\nreturn subprocess.check_output(['whoami'])"},
                author_id=10,
            )

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
