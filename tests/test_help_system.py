import unittest
from unittest.mock import patch
from types import SimpleNamespace

import discord
from discord.ext import commands

from cogs.help import Help, HelpView, _HelpIndex, _normalize_command_name


async def _sample_warn(ctx, user: str, *, reason: str = "No reason provided"):
    return None


class HelpSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.warn_command = commands.Command(
            _sample_warn,
            name="warn",
            help="Warn a member and record the reason.",
            description="Warn a member and record the reason.",
            aliases=["w"],
        )
        self.index = _HelpIndex(
            categories={"Moderation": [self.warn_command]},
            by_name={"warn": self.warn_command, "w": self.warn_command},
        )

    def test_normalize_accepts_prefix_and_slash_names(self) -> None:
        self.assertEqual(_normalize_command_name("/automod setup"), "automod setup")
        self.assertEqual(_normalize_command_name(",help warn"), "help warn")

    def test_overview_mentions_both_help_entrypoints(self) -> None:
        view = HelpView(bot=SimpleNamespace(), author_id=123, index=self.index)
        embed = view.pages[0]

        self.assertIn("/help", embed.description)
        self.assertIn(",help", embed.description)
        self.assertTrue(any(field.name == "Fast Start" for field in embed.fields))
        self.assertNotIn("/modpanel", "\n".join(str(field.value) for field in embed.fields))
        self.assertNotIn("/adminpanel", "\n".join(str(field.value) for field in embed.fields))

    def test_detail_embed_has_usage_and_parameters(self) -> None:
        help_cog = Help(SimpleNamespace())
        embed = help_cog._build_details_embed(self.warn_command)

        self.assertEqual(embed.title, "Help: ,warn")
        self.assertTrue(any(field.name == "Run it" for field in embed.fields))
        self.assertTrue(any(field.name == "Inputs" for field in embed.fields))

    def test_panel_commands_are_not_registered_on_help_cog(self) -> None:
        self.assertFalse(hasattr(Help, "modpanel"))
        self.assertFalse(hasattr(Help, "adminpanel"))
        self.assertFalse(hasattr(Help, "ownerpanel"))

    def test_website_help_matches_three_row_action_card(self) -> None:
        help_cog = Help(SimpleNamespace())
        with patch.dict(
            "os.environ",
            {
                "DASHBOARD_PUBLIC_URL": "https://docket.example",
                "SUPPORT_SERVER_URL": "https://discord.gg/docket",
            },
        ):
            view = help_cog._website_help_view()

        self.assertIsInstance(view, discord.ui.LayoutView)
        self.assertEqual(len(view.children), 1)
        container = view.children[0]
        self.assertIsInstance(container, discord.ui.Container)

        sections = [
            child for child in container.children
            if isinstance(child, discord.ui.Section)
        ]
        separators = [
            child for child in container.children
            if isinstance(child, discord.ui.Separator)
        ]
        self.assertEqual(len(sections), 3)
        self.assertEqual(len(separators), 2)
        self.assertEqual(
            [section.accessory.label for section in sections],
            ["Commands", "Go to Dashboard", "Support Server"],
        )
        self.assertEqual(
            [section.accessory.url for section in sections],
            [
                "https://docket.example/commands",
                "https://docket.example/dashboard",
                "https://discord.gg/docket",
            ],
        )
        text = "\n".join(
            child.content
            for section in sections
            for child in section.children
            if isinstance(child, discord.ui.TextDisplay)
        )
        self.assertIn("## 📖 Commands\n-# Browse every slash and prefix command.", text)
        self.assertIn("## 🖥️ Dashboard\n-# Manage modules, staff, logs", text)
        self.assertIn("## ❓ Need Help?\n-# Open setup help", text)
        self.assertNotIn("ð", text)
        self.assertNotIn("â", text)

    def test_website_help_omits_support_without_a_real_server(self) -> None:
        help_cog = Help(SimpleNamespace())
        with patch.dict(
            "os.environ",
            {
                "DASHBOARD_PUBLIC_URL": "https://docket.example",
                "SUPPORT_SERVER_URL": "",
            },
        ):
            view = help_cog._website_help_view()

        container = view.children[0]
        sections = [
            child for child in container.children
            if isinstance(child, discord.ui.Section)
        ]
        self.assertEqual(
            [section.accessory.label for section in sections],
            ["Commands", "Go to Dashboard"],
        )


if __name__ == "__main__":
    unittest.main()
