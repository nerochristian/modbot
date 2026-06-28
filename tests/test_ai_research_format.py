import unittest

from cogs.aimoderation import AIModeration


class ResearchFormattingTests(unittest.TestCase):
    def test_heading_becomes_embed_title(self) -> None:
        embed = AIModeration._build_research_embed(
            None,
            "# 📢 Community Update\n\n• **Launch**\n  It ships Friday.",
            "community update",
        )

        self.assertEqual(embed.title, "📢 Community Update")
        self.assertEqual(
            embed.description,
            "• **Launch**\n  It ships Friday.",
        )

    def test_sources_are_removed_from_answer_for_button(self) -> None:
        answer, sources = AIModeration._split_research_sources(
            "# 🔎 Result\n\nUseful answer.\n\n__BOT_SOURCES__\n"
            "- <https://example.com/source>"
        )

        self.assertEqual(answer, "# 🔎 Result\n\nUseful answer.")
        self.assertEqual(
            sources,
            "**Sources:**\n- <https://example.com/source>",
        )


if __name__ == "__main__":
    unittest.main()
