import unittest
from types import SimpleNamespace
from unittest.mock import patch

import discord

from bot import GUILD_ONBOARDING_BANNER, ModBot


class GuildOnboardingTests(unittest.TestCase):
    def test_onboarding_uses_banner_and_nebula_style_action_rows(self) -> None:
        bot = SimpleNamespace()
        guild = SimpleNamespace(name="The Supreme People")

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
        self.assertEqual(len(sections), 4)
        self.assertEqual(
            [section.accessory.label for section in sections],
            ["Dashboard", "View commands", "Configure AutoMod", "Support server"],
        )
        self.assertEqual(
            [section.accessory.url for section in sections],
            [
                "https://docket.example/servers",
                "https://docket.example/commands",
                "https://docket.example/dashboard/automod",
                "https://discord.gg/docket",
            ],
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
        self.assertIn("Docket is ready", text)
        self.assertIn("The Supreme People", text)
        self.assertIn("Quick setup", text)
        self.assertIn("Protection center", text)
        self.assertNotIn("Ã", text)

    def test_onboarding_banner_asset_exists(self) -> None:
        self.assertTrue(GUILD_ONBOARDING_BANNER.is_file())
        self.assertGreater(GUILD_ONBOARDING_BANNER.stat().st_size, 100_000)


if __name__ == "__main__":
    unittest.main()
