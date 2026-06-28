import unittest

from cogs.aimoderation import AIModeration, GeminiClient


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

    def test_topic_words_match_related_inflections(self) -> None:
        first = GeminiClient._conversation_topic_words("is zzz a gooner game")
        second = GeminiClient._conversation_topic_words("is gooning valid")

        self.assertIn("goon", first & second)

    def test_topic_words_ignore_bot_mentions_and_generic_words(self) -> None:
        topics = GeminiClient._conversation_topic_words(
            "<@123456789012345678> should I do that?"
        )

        self.assertEqual(topics, set())


if __name__ == "__main__":
    unittest.main()
