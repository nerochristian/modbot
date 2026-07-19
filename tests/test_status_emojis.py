import unittest
from pathlib import Path
from types import SimpleNamespace

import discord

from config import Config
from utils import status_emojis
from utils.embeds import ModEmbed
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

    async def test_plain_moderation_log_title_gets_semantic_application_emoji(self) -> None:
        status_emojis._application_kind_cache["ban"] = "<a:mod_ban:1521191582424895740>"
        embed = discord.Embed(title="Member Banned")
        guild = SimpleNamespace()

        updated = await apply_status_emoji_overrides(embed, guild)

        self.assertEqual(updated.title, "<a:mod_ban:1521191582424895740> Member Banned")

    async def test_plain_generic_log_title_gets_info_application_emoji(self) -> None:
        status_emojis._application_kind_cache["info"] = "<a:mod_info:1521191582424895741>"
        embed = discord.Embed(title="Channel Permissions Changed")
        guild = SimpleNamespace()

        updated = await apply_status_emoji_overrides(embed, guild)

        self.assertEqual(updated.title, "<a:mod_info:1521191582424895741> Channel Permissions Changed")

    def test_additional_application_emoji_assets_are_complete(self) -> None:
        assets_dir = Path(status_emojis.__file__).resolve().parents[1] / "assets"

        self.assertEqual(len(status_emojis._ADDITIONAL_EMOJI_DEFAULTS), 28)
        for kind in status_emojis._ADDITIONAL_EMOJI_DEFAULTS:
            meta = status_emojis._EMOJI_META[kind]
            self.assertEqual(meta["default_name"], f"mod_{kind}")
            self.assertEqual(meta["asset"], f"emoji_{kind}.gif")
            self.assertTrue((assets_dir / f"emoji_{kind}.svg").is_file(), kind)

    async def test_verification_title_uses_verification_application_emoji(self) -> None:
        status_emojis._application_kind_cache["verification"] = (
            "<a:mod_verification:1521191582424895742>"
        )
        embed = discord.Embed(title="Member Verification Complete")

        updated = await apply_status_emoji_overrides(embed, SimpleNamespace())

        self.assertEqual(
            updated.title,
            "<a:mod_verification:1521191582424895742> Member Verification Complete",
        )

    def test_moderation_confirmation_is_an_embed(self) -> None:
        status_emojis._application_kind_cache["ban"] = "<a:mod_ban:1521191582424895740>"

        embed = ModEmbed.moderation_response("ban", "***<@123> was banned***\n**Reason:** spam")

        self.assertTrue(embed.description.startswith("<a:mod_ban:1521191582424895740> "))
        self.assertIn("<@123> was banned", embed.description)


if __name__ == "__main__":
    unittest.main()
