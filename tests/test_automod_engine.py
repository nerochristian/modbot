from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord

from cogs.automod import (
    PANEL_PAGES,
    AutoMod,
    AutoModPanel,
    _compact_duration,
    _parse_duration,
    _parse_threshold_pair,
)
from cogs.automod import AutoModEngine, Category, domain_matches, normalize_domain
from cogs.automod.logging import AutoModLogger
from cogs.automod.models import Action, RuleMatch, Severity
from cogs.automod.storage import AutoModStorage
from cogs.appeals import Appeals, _database_timestamp, build_punishment_notice


class FakePermissions:
    administrator = False
    manage_guild = False
    manage_messages = False


class FakeMessage:
    def __init__(
        self,
        content: str,
        *,
        user_id: int = 10,
        guild_id: int = 1,
        channel_id: int = 20,
    ) -> None:
        self.content = content
        self.guild = SimpleNamespace(id=guild_id)
        self.author = SimpleNamespace(
            id=user_id,
            created_at=datetime.now(timezone.utc) - timedelta(days=100),
            roles=[],
            guild_permissions=FakePermissions(),
        )
        self.channel = SimpleNamespace(id=channel_id, parent_id=None)
        self.mentions = []
        self.role_mentions = []
        self.created_at = datetime.now(timezone.utc)


def base_settings() -> dict[str, object]:
    return {
        "automod_scam_protection": True,
        "automod_badwords_enabled": True,
        "automod_spam_enabled": True,
        "automod_mentions_enabled": True,
        "automod_invites_enabled": True,
        "automod_links_enabled": True,
        "automod_caps_enabled": True,
        "automod_ai_enabled": False,
        "automod_newaccount_enabled": True,
        "automod_badwords": ["bad phrase"],
        "automod_links_mode": "dangerous",
        "automod_links_whitelist": [],
        "automod_whitelisted_domains": [],
        "automod_allowed_invites": [],
        "automod_spam_threshold": 3,
        "automod_spam_window": 5,
        "automod_duplicate_threshold": 3,
        "automod_duplicate_window": 30,
        "automod_caps_percentage": 80,
        "automod_caps_min_length": 10,
        "automod_max_mentions": 5,
        "automod_newaccount_days": 7,
        "automod_violation_cooldown": 1,
        "automod_punishment": "warn",
        "automod_security_punishment": "timeout",
    }


class AutoModEngineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = AutoModEngine()

    async def asyncTearDown(self) -> None:
        await self.engine.close()

    async def test_obfuscated_blocked_phrase_is_detected(self) -> None:
        match = await self.engine.evaluate(
            FakeMessage("b.a.d p h r a s e"),
            base_settings(),
            dry_run=True,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.rule, "badwords")

    async def test_disabled_rule_does_not_run(self) -> None:
        settings = base_settings()
        settings["automod_badwords_enabled"] = False
        match = await self.engine.evaluate(
            FakeMessage("b.a.d p h r a s e"),
            settings,
            dry_run=True,
        )
        self.assertIsNone(match)

    async def test_dangerous_mode_allows_ordinary_domain(self) -> None:
        match = await self.engine.evaluate(
            FakeMessage("Read https://example.com/docs"),
            base_settings(),
            dry_run=True,
        )
        self.assertIsNone(match)

    async def test_allowlist_mode_blocks_unlisted_domain(self) -> None:
        settings = base_settings()
        settings["automod_links_mode"] = "allowlist"
        settings["automod_whitelisted_domains"] = ["example.org"]
        match = await self.engine.evaluate(
            FakeMessage("Read https://example.com/docs"),
            settings,
            dry_run=True,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.rule, "links")

    async def test_allowlist_accepts_real_subdomain_only(self) -> None:
        settings = base_settings()
        settings["automod_links_mode"] = "allowlist"
        settings["automod_whitelisted_domains"] = ["example.com"]
        allowed = await self.engine.evaluate(
            FakeMessage("Read https://sub.example.com/docs"),
            settings,
            dry_run=True,
        )
        blocked = await self.engine.evaluate(
            FakeMessage("Read https://evilexample.com/docs"),
            settings,
            dry_run=True,
        )
        self.assertIsNone(allowed)
        self.assertIsNotNone(blocked)
        self.assertEqual(blocked.rule, "links")

    async def test_scam_uses_security_policy(self) -> None:
        settings = base_settings()
        match = await self.engine.evaluate(
            FakeMessage("Free nitro, claim https://notdiscord.example"),
            settings,
            dry_run=True,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.rule, "scams")
        self.assertIs(match.category, Category.SECURITY)
        self.assertEqual(self.engine.resolve_action(match, settings).value, "timeout")

    async def test_spam_uses_configured_window_and_threshold(self) -> None:
        settings = base_settings()
        match = None
        for index in range(3):
            match = await self.engine.evaluate(
                FakeMessage(f"unique message {index}", user_id=99),
                settings,
            )
        self.assertIsNotNone(match)
        self.assertEqual(match.rule, "spam")

    async def test_violation_cooldown_never_suppresses_detection(self) -> None:
        settings = base_settings()
        settings["automod_violation_cooldown"] = 300
        first_message = FakeMessage("bad phrase", user_id=55)
        second_message = FakeMessage("bad phrase", user_id=55)

        first = await self.engine.evaluate(first_message, settings)
        second = await self.engine.evaluate(second_message, settings)

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertTrue(self.engine.claim_action(first_message, first, settings))
        self.assertFalse(self.engine.claim_action(second_message, second, settings))


class AutoModMessageHandlingTests(unittest.IsolatedAsyncioTestCase):
    async def test_cooldown_suppresses_repeated_action_but_still_deletes(self) -> None:
        message = SimpleNamespace(
            guild=SimpleNamespace(id=1),
            author=SimpleNamespace(id=55),
            channel=SimpleNamespace(id=20),
            delete=AsyncMock(),
        )
        match = RuleMatch(
            rule="badwords",
            reason="Blocked word or phrase",
            severity=Severity.HIGH,
            category=Category.CONTENT,
        )
        engine = SimpleNamespace(
            should_delete_message=lambda detected, settings: True,
            resolve_action=lambda detected, settings: Action.WARN,
            record_action=Mock(),
        )
        database = SimpleNamespace(record_automod_event=AsyncMock())
        cog = AutoMod.__new__(AutoMod)
        cog.bot = SimpleNamespace(db=database)
        cog.engine = engine
        cog.punishments = SimpleNamespace(apply=AsyncMock())
        cog.logger = SimpleNamespace(log_message_action=AsyncMock())
        cog._notify_user = AsyncMock()

        await cog._handle_message_match(message, match, base_settings(), apply_action=False)

        message.delete.assert_awaited_once_with()
        cog.punishments.apply.assert_not_awaited()
        cog.logger.log_message_action.assert_not_awaited()
        cog._notify_user.assert_not_awaited()
        database.record_automod_event.assert_awaited_once()
        self.assertEqual(database.record_automod_event.await_args.args[6], Action.LOG.value)


class AutoModUtilityTests(unittest.TestCase):
    def test_domain_matching_does_not_allow_suffix_confusion(self) -> None:
        self.assertEqual(normalize_domain("https://WWW.Example.COM/path"), "www.example.com")
        self.assertTrue(domain_matches("sub.example.com", "example.com"))
        self.assertFalse(domain_matches("evilexample.com", "example.com"))

    def test_duration_parser_requires_complete_bounded_input(self) -> None:
        self.assertEqual(_parse_duration("1d12h"), 129600)
        self.assertIsNone(_parse_duration("abc1h"))
        self.assertIsNone(_parse_duration("29d"))

    def test_compact_duration_round_trips(self) -> None:
        for seconds in (60, 65, 3600, 3661, 9000, 129600, 2419200):
            self.assertEqual(_parse_duration(_compact_duration(seconds)), seconds)

    def test_threshold_pair_parser_enforces_both_ranges(self) -> None:
        self.assertEqual(
            _parse_threshold_pair("5/30", count_range=(2, 20), window_range=(5, 300)),
            (5, 30),
        )
        self.assertIsNone(_parse_threshold_pair("1/30", count_range=(2, 20), window_range=(5, 300)))
        self.assertIsNone(_parse_threshold_pair("5/301", count_range=(2, 20), window_range=(5, 300)))


class AutoModStorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_settings_reads_are_cached_and_return_isolated_copies(self) -> None:
        class CountingDatabase:
            def __init__(self) -> None:
                self.reads = 0

            async def get_settings(self, guild_id: int) -> dict[str, object]:
                self.reads += 1
                return {"automod_enabled": True, "automod_badwords": ["blocked phrase"]}

        database = CountingDatabase()
        storage = AutoModStorage(SimpleNamespace(db=database), cache_ttl_seconds=60)

        first = await storage.get_settings(123)
        first["automod_enabled"] = False
        second = await storage.get_settings(123)

        self.assertEqual(database.reads, 1)
        self.assertTrue(second["automod_enabled"])

    async def test_stale_settings_are_used_when_refresh_fails(self) -> None:
        class FlakyDatabase:
            def __init__(self) -> None:
                self.fail = False

            async def get_settings(self, guild_id: int) -> dict[str, object]:
                if self.fail:
                    raise RuntimeError("database unavailable")
                return {"automod_enabled": True}

        database = FlakyDatabase()
        storage = AutoModStorage(SimpleNamespace(db=database), cache_ttl_seconds=1)
        expected = await storage.get_settings(123)
        cached_at, cached = storage._cache[123]
        storage._cache[123] = (cached_at - 2, cached)
        database.fail = True

        self.assertEqual(await storage.get_settings(123), expected)

    async def test_database_save_is_read_back_before_success(self) -> None:
        class FakeDatabase:
            def __init__(self) -> None:
                self.settings: dict[int, dict[str, object]] = {}

            async def get_settings(self, guild_id: int) -> dict[str, object]:
                return dict(self.settings.get(guild_id, {}))

            async def update_settings(self, guild_id: int, settings: dict[str, object]) -> None:
                self.settings[guild_id] = dict(settings)

        database = FakeDatabase()
        storage = AutoModStorage(SimpleNamespace(db=database))

        saved = await storage.update_settings(
            123,
            {
                "automod_enabled": True,
                "automod_spam_enabled": False,
                "automod_badwords": ["blocked phrase"],
            },
        )
        restarted_storage = AutoModStorage(SimpleNamespace(db=database))
        reloaded = await restarted_storage.get_settings(123)

        self.assertFalse(saved["automod_spam_enabled"])
        self.assertFalse(reloaded["automod_spam_enabled"])
        self.assertEqual(reloaded["automod_badwords"], ["blocked phrase"])

    async def test_database_save_fails_if_written_value_is_missing(self) -> None:
        class DroppingDatabase:
            async def get_settings(self, guild_id: int) -> dict[str, object]:
                return {}

            async def update_settings(self, guild_id: int, settings: dict[str, object]) -> None:
                return None

        storage = AutoModStorage(SimpleNamespace(db=DroppingDatabase()))

        with self.assertRaisesRegex(RuntimeError, "automod_enabled"):
            await storage.update_settings(123, {"automod_enabled": False})


class AutoModPresentationTests(unittest.IsolatedAsyncioTestCase):
    def _message(self):
        guild = SimpleNamespace(id=1, name="The Supreme People", icon=SimpleNamespace(url="https://example.com/guild.png"))
        author = SimpleNamespace(
            id=1051999048644698193,
            mention="<@1051999048644698193>",
            display_avatar=SimpleNamespace(url="https://example.com/member.png"),
        )
        channel = SimpleNamespace(id=20, mention="<#20>")
        return SimpleNamespace(guild=guild, author=author, channel=channel, content="@everyone")

    async def test_staff_log_uses_compact_moderation_layout(self) -> None:
        logging_cog = SimpleNamespace(
            get_log_channel=AsyncMock(return_value=object()),
            safe_send_log=AsyncMock(return_value=True),
        )
        bot = SimpleNamespace(get_cog=lambda name: logging_cog if name == "Logging" else None)
        logger = AutoModLogger(bot)
        message = self._message()
        match = RuleMatch(
            rule="badwords",
            reason="Blocked word or phrase",
            severity=Severity.HIGH,
            category=Category.CONTENT,
            evidence=("@everyone",),
        )

        await logger.log_message_action(
            message,
            match,
            Action.TIMEOUT,
            deleted=True,
            case_number=63,
            offense_count=1,
        )

        embed = logging_cog.safe_send_log.await_args.args[1]
        self.assertEqual(embed.title, "AutoMod removed a message")
        self.assertIn("**Member:** <@1051999048644698193> (`1051999048644698193`)", embed.description)
        self.assertIn("**Rule:** Blocked words", embed.description)
        self.assertIn("**Action:** Timed out", embed.description)
        self.assertIn("**Case:** #63", embed.description)
        self.assertEqual([field.name for field in embed.fields], ["Message"])
        self.assertEqual(embed.fields[0].value, "> @everyone")
        self.assertEqual(embed.thumbnail.url, "https://example.com/member.png")

    async def test_user_notice_is_a_clean_server_branded_embed(self) -> None:
        logger = AutoModLogger(SimpleNamespace())
        message = self._message()
        match = RuleMatch(
            rule="badwords",
            reason="Blocked word or phrase",
            severity=Severity.HIGH,
            category=Category.CONTENT,
        )

        embed = logger.build_user_notice(
            message,
            match,
            Action.TIMEOUT,
            deleted=True,
            case_number=63,
            appeal_instructions="Open a ticket if you think this was a mistake.",
        )

        self.assertEqual(embed.title, "Message flagged")
        self.assertEqual(embed.author.name, "The Supreme People")
        self.assertIn("> **Server:** The Supreme People", embed.description)
        self.assertIn("> **Rule:** Blocked words", embed.description)
        self.assertIn("> **Outcome:** Removed", embed.description)
        self.assertIn("**Why it was flagged**\n> Blocked word or phrase", embed.description)
        self.assertIn("**Message**\n> @everyone", embed.description)
        self.assertIn("**What you can do**\n> Open a ticket if you think this was a mistake.", embed.description)
        self.assertEqual(list(embed.fields), [])
        self.assertEqual(embed.footer.text, "CASE-0063 | AutoMod")

    async def test_case_notice_is_compact_and_keeps_the_case_visible(self) -> None:
        guild = SimpleNamespace(
            name="The Supreme People",
            icon=SimpleNamespace(url="https://example.com/guild.png"),
        )
        punishment_expires_at = datetime.now(timezone.utc) + timedelta(minutes=53)
        user = SimpleNamespace(id=55, display_name="Kayrozaa")

        view = build_punishment_notice(
            guild=guild,
            user=user,
            action="Ban",
            reason="Repeated scam links",
            case_number=12,
            duration="7 days",
            punishment_expires_at=punishment_expires_at,
            appeal_url="https://docketbot.xyz/appeal/token",
        )

        self.assertIsInstance(view, discord.ui.LayoutView)
        container = view.children[0]
        self.assertIsInstance(container, discord.ui.Container)
        section = container.children[0]
        self.assertIsInstance(section, discord.ui.Section)
        header = next(item.content for item in section.children if isinstance(item, discord.ui.TextDisplay))
        details = next(item.content for item in container.children if isinstance(item, discord.ui.TextDisplay))
        self.assertIn("## Kayrozaa", header)
        self.assertNotIn("!!” 🥢", header)
        self.assertIn("You have been **banned** for **7 days**", header)
        self.assertIn(f"until <t:{int(punishment_expires_at.timestamp())}:R>", header)
        self.assertIn("**Reason :**\n> Repeated scam links", details)
        self.assertIn("`user:55 date:", details)
        self.assertIsInstance(container.children[1], discord.ui.Separator)
        self.assertIsInstance(view.children[1], discord.ui.TextDisplay)
        self.assertIn(f"Available again <t:{int(punishment_expires_at.timestamp())}:R>", view.children[1].content)
        self.assertIsInstance(view.children[2], discord.ui.ActionRow)

    async def test_appeal_expiry_is_stored_as_naive_utc_for_postgres(self) -> None:
        source = datetime(2026, 7, 18, 16, 30, tzinfo=timezone(timedelta(hours=-5)))

        stored = _database_timestamp(source)

        self.assertIsNone(stored.tzinfo)
        self.assertEqual(stored, datetime(2026, 7, 18, 21, 30))

    async def test_punishment_notice_uses_preopened_dm_channel(self) -> None:
        user = SimpleNamespace(id=55, send=AsyncMock())
        dm_channel = SimpleNamespace(send=AsyncMock())
        guild = SimpleNamespace(id=1, name="Guild", icon=None)
        appeals = Appeals(SimpleNamespace())

        delivered = await appeals.notify_punishment(
            guild=guild,
            user=user,
            action="Ban",
            reason="Test",
            case_number=4,
            settings={"appeals_enabled": False},
            delivery_channel=dm_channel,
        )

        self.assertTrue(delivered)
        dm_channel.send.assert_awaited_once()
        user.send.assert_not_awaited()


class AutoModPanelTests(unittest.IsolatedAsyncioTestCase):
    async def test_every_panel_page_fits_discord_component_limits(self) -> None:
        guild = SimpleNamespace(
            id=1,
            get_channel=lambda channel_id: None,
            get_role=lambda role_id: None,
        )
        settings = base_settings()
        settings.update(
            {
                "automod_enabled": True,
                "automod_notify_users": True,
                "automod_public_feedback": False,
                "automod_bypass_staff": True,
                "automod_bypass_roles": [111],
                "automod_bypass_channels": [222],
                "automod_mute_duration": 3600,
            }
        )
        panel = AutoModPanel(SimpleNamespace(), guild, 10, settings)
        try:
            for page, _, _ in PANEL_PAGES:
                panel.page = page
                panel.rebuild()
                self.assertLessEqual(len(panel.children), 25)
                widths_by_row: dict[int, int] = {}
                for item in panel.children:
                    self.assertIsNotNone(item.row)
                    widths_by_row[item.row] = widths_by_row.get(item.row, 0) + item.width
                self.assertTrue(all(width <= 5 for width in widths_by_row.values()))
                embed = panel.build_embed()
                self.assertLessEqual(len(embed), 6000)
                self.assertTrue(all(len(field.value) <= 1024 for field in embed.fields))
                expected_controls = len(panel.children)
                layout = await panel.build_layout()

                def walk(item):
                    yield item
                    for child in getattr(item, "children", []):
                        yield from walk(child)

                rendered_controls = [
                    item
                    for root in layout.children
                    for item in walk(root)
                    if int(item.to_component_dict().get("type", 0)) in {2, 3, 5, 6, 7, 8}
                ]
                self.assertEqual(len(rendered_controls), expected_controls)
        finally:
            panel.stop()


if __name__ == "__main__":
    unittest.main()
