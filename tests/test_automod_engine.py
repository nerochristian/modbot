from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from cogs.automod import (
    PANEL_PAGES,
    AutoModPanel,
    _compact_duration,
    _parse_duration,
    _parse_threshold_pair,
)
from cogs.automod import AutoModEngine, Category, domain_matches, normalize_domain
from cogs.automod.logging import AutoModLogger
from cogs.automod.models import Action, RuleMatch, Severity


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

        self.assertEqual(embed.title, "AutoMod notice")
        self.assertEqual(embed.author.name, "The Supreme People")
        self.assertIn("**The Supreme People**", embed.description)
        self.assertEqual([field.name for field in embed.fields], ["What happened", "Your message", "Appeal or questions"])
        self.assertIn("**Action:** Timed out", embed.fields[0].value)
        self.assertEqual(embed.fields[1].value, "> @everyone")
        self.assertEqual(embed.fields[2].value, "Open a ticket if you think this was a mistake.")
        self.assertEqual(embed.footer.text, "This notice was sent automatically by Docket AutoMod.")


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
