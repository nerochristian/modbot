import unittest
from types import SimpleNamespace

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

    def test_detail_embed_has_usage_and_parameters(self) -> None:
        help_cog = Help(SimpleNamespace())
        embed = help_cog._build_details_embed(self.warn_command)

        self.assertEqual(embed.title, "Help: ,warn")
        self.assertTrue(any(field.name == "Run it" for field in embed.fields))
        self.assertTrue(any(field.name == "Inputs" for field in embed.fields))


if __name__ == "__main__":
    unittest.main()
