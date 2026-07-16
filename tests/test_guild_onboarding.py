import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import discord

from bot import GUILD_ONBOARDING_BANNER, ModBot, OnboardingPrefixSelect


class GuildOnboardingTests(unittest.TestCase):
    def test_onboarding_uses_banner_and_nebula_style_action_rows(self) -> None:
        bot = SimpleNamespace()
        guild = SimpleNamespace(id=123, name="The Supreme People")

        with patch.dict(
            "os.environ",
            {
                "DASHBOARD_PUBLIC_URL": "https://docket.example",
                "SUPPORT_SERVER_URL": "https://discord.gg/docket",
            },
        ):
            view = ModBot._guild_onboarding_view(bot, guild)

        self.assertIsInstance(view, discord.ui.LayoutView)
        self.assertEqual(len(view.children), 1)
        container = view.children[0]
        self.assertIsInstance(container, discord.ui.Container)
        self.assertIsInstance(container.children[0], discord.ui.MediaGallery)

        sections = [
            child for child in container.children
            if isinstance(child, discord.ui.Section)
        ]
        self.assertEqual(len(sections), 2)
        self.assertEqual(
            [section.accessory.label for section in sections],
            ["Dashboard", "View commands"],
        )
        self.assertEqual(
            [section.accessory.url for section in sections],
            [
                "https://docket.example/servers",
                "https://docket.example/commands",
            ],
        )

        action_rows = [
            child for child in container.children
            if isinstance(child, discord.ui.ActionRow)
        ]
        self.assertEqual(len(action_rows), 2)
        self.assertEqual(
            [row.children[0].placeholder for row in action_rows],
            ["Available languages", "Select a prefix…"],
        )

        text = "\n".join(
            child.content
            for child in container.children
            if isinstance(child, discord.ui.TextDisplay)
        )
        text += "\n" + "\n".join(
            child.content
            for section in sections
            for child in section.children
            if isinstance(child, discord.ui.TextDisplay)
        )
        self.assertIn("### Thanks for adding Docket", text)
        self.assertIn("The Supreme People", text)
        self.assertIn("## ⚡ Quick Setup\n-# Manage all settings", text)
        self.assertIn("## 📖 Commands List\n-# Explore everything Docket can do.", text)
        self.assertIn("## 🌐 Language & Prefix\n-# Customize how Docket responds", text)
        self.assertIn("[Support Server](https://discord.gg/docket)", text)
        self.assertNotIn("Ã", text)

    def test_onboarding_omits_support_when_no_server_is_configured(self) -> None:
        bot = SimpleNamespace()
        guild = SimpleNamespace(id=123, name="Test Server")

        with patch.dict("os.environ", {"SUPPORT_SERVER_URL": ""}):
            view = ModBot._guild_onboarding_view(bot, guild, include_banner=False)

        container = view.children[0]
        text = "\n".join(
            child.content
            for child in container.children
            if isinstance(child, discord.ui.TextDisplay)
        )
        self.assertNotIn("Support Server", text)

    def test_onboarding_banner_asset_exists(self) -> None:
        self.assertTrue(GUILD_ONBOARDING_BANNER.is_file())
        self.assertGreater(GUILD_ONBOARDING_BANNER.stat().st_size, 100_000)


class OnboardingPrefixSelectTests(unittest.IsolatedAsyncioTestCase):
    async def test_prefix_selection_persists_and_invalidates_cache(self) -> None:
        bot = SimpleNamespace(
            db=SimpleNamespace(update_settings=AsyncMock()),
            prefix_cache=SimpleNamespace(invalidate=AsyncMock()),
        )
        select = OnboardingPrefixSelect(bot, 123)
        select._values = ["!"]
        interaction = SimpleNamespace(
            guild_id=123,
            user=SimpleNamespace(guild_permissions=SimpleNamespace(manage_guild=True)),
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )

        await select.callback(interaction)

        bot.db.update_settings.assert_awaited_once_with(123, {"prefix": "!"})
        bot.prefix_cache.invalidate.assert_awaited_once_with(123)
        interaction.followup.send.assert_awaited_once_with(
            "Prefix updated to `!`. Try `!help`.",
            ephemeral=True,
        )


if __name__ == "__main__":
    unittest.main()
