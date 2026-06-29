import unittest
from types import SimpleNamespace

import discord

from config import Config
from utils import status_emojis
from utils.status_emojis import apply_status_emoji_overrides


class StatusEmojiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        status_emojis._application_emoji_cache.clear()
        status_emojis._application_kind_cache.clear()
        status_emojis._application_name_cache.clear()

    async def test_shortcode_title_falls_back_to_unicode_when_unresolved(self) -> None:
        original = Config.EMOJI_WARN
        Config.EMOJI_WARN = ":mod_warn:"
        try:
            embed = discord.Embed(title=":mod_warn: User Warned")
            guild = SimpleNamespace(_state=SimpleNamespace(_get_client=lambda: None))

            updated = await apply_status_emoji_overrides(embed, guild)

            self.assertEqual(updated.title, "\u26a0\ufe0f User Warned")
        finally:
            Config.EMOJI_WARN = original

    async def test_shortcode_title_uses_application_emoji_when_available(self) -> None:
        class FakeEmoji:
            name = "mod_warn"

            def __str__(self) -> str:
                return "<:mod_warn:1521191582424895739>"

        class FakeClient:
            async def fetch_application_emojis(self):
                return [FakeEmoji()]

        original = Config.EMOJI_WARN
        Config.EMOJI_WARN = ":mod_warn:"
        try:
            embed = discord.Embed(title=":mod_warn: User Warned")
            guild = SimpleNamespace(client=FakeClient())

            updated = await apply_status_emoji_overrides(embed, guild)

            self.assertEqual(
                updated.title,
                "<:mod_warn:1521191582424895739> User Warned",
            )
        finally:
            Config.EMOJI_WARN = original


if __name__ == "__main__":
    unittest.main()
