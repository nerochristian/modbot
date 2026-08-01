import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import discord

from cogs.logging_cog import Logging
from utils.logging import normalize_log_embed


class AuditChangeFormattingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logging = object.__new__(Logging)

    def test_diff_proxies_show_role_changes(self) -> None:
        before_permissions = discord.Permissions.none()
        after_permissions = discord.Permissions.none()
        after_permissions.update(view_channel=True, manage_roles=True)
        entry = SimpleNamespace(
            changes=SimpleNamespace(
                before=SimpleNamespace(
                    name="VIP",
                    colour=discord.Colour.red(),
                    hoist=False,
                    mentionable=False,
                    permissions=before_permissions,
                ),
                after=SimpleNamespace(
                    name="Premium VIP",
                    colour=discord.Colour.blue(),
                    hoist=True,
                    mentionable=True,
                    permissions=after_permissions,
                ),
            )
        )

        lines = self.logging._audit_change_lines(entry)

        self.assertIn("**Name:** VIP → Premium VIP", lines)
        self.assertIn("**Color:** #e74c3c → #3498db", lines)
        self.assertIn("**Displayed separately:** No → Yes", lines)
        self.assertIn("**Mentionable:** No → Yes", lines)
        permission_line = next(line for line in lines if line.startswith("**Permissions changed:**"))
        self.assertIn("View Channels", permission_line)
        self.assertIn("Manage Roles", permission_line)

    def test_duplicate_colour_alias_is_only_reported_once(self) -> None:
        before = discord.Colour.red()
        after = discord.Colour.green()
        entry = SimpleNamespace(
            changes=SimpleNamespace(
                before=SimpleNamespace(colour=before, color=before),
                after=SimpleNamespace(colour=after, color=after),
            )
        )

        lines = self.logging._audit_change_lines(entry)

        self.assertEqual(lines, ["**Color:** #e74c3c → #2ecc71"])


class LoggingNativeFooterTests(unittest.IsolatedAsyncioTestCase):
    async def test_safe_send_log_preserves_native_embed_footer(self) -> None:
        logging_cog = object.__new__(Logging)
        channel = SimpleNamespace(
            guild=SimpleNamespace(name="Test Guild"),
            name="mod-logs",
            send=AsyncMock(),
        )
        embed = discord.Embed(title="Test Log", description="Details")

        with patch(
            "cogs.logging_cog.prepare_log_embed",
            new=AsyncMock(return_value=embed),
        ):
            sent = await logging_cog.safe_send_log(channel, embed)

        self.assertTrue(sent)
        kwargs = channel.send.await_args.kwargs
        self.assertIs(kwargs["embed"], embed)
        self.assertIsNone(kwargs["view"])
        self.assertFalse(kwargs["use_v2"])

    def test_normalizer_keeps_timestamp_in_native_footer_area(self) -> None:
        logged_at = datetime(2026, 8, 1, 1, 30, tzinfo=timezone.utc)
        guild = SimpleNamespace(name="Test Guild", icon=None)
        channel = SimpleNamespace(guild=guild)
        embed = discord.Embed(title="Member banned", timestamp=logged_at)
        embed.set_footer(text="@moderator", icon_url="https://cdn.example/mod.png")

        normalized = normalize_log_embed(channel, embed)

        self.assertEqual(normalized.timestamp, logged_at)
        self.assertEqual(normalized.footer.text, "@moderator")
        self.assertEqual(normalized.footer.icon_url, "https://cdn.example/mod.png")
        self.assertNotIn("Time", [field.name for field in normalized.fields])


if __name__ == "__main__":
    unittest.main()
