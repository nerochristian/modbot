import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from cogs.aimoderation.aimoderation import AIModeration, GeminiClient
from cogs.aimoderation.types import ConversationMode


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

    def test_research_embed_removes_redundant_blank_lines(self) -> None:
        embed = AIModeration._build_research_embed(
            None,
            "# Animal Hospital Roblox Release Date\n\n"
            "Released in early 2026.\n\n"
            "## Key Context\n\n"
            "• First detail.\n\n"
            "• Second detail.\n\n"
            "## Game Overview\n\n"
            "The core loop involves:\n\n"
            "• Checking patients.",
            "research animal hospital",
        )

        self.assertEqual(
            embed.description,
            "Released in early 2026.\n"
            "## Key Context\n"
            "• First detail.\n"
            "• Second detail.\n"
            "## Game Overview\n"
            "The core loop involves:\n"
            "• Checking patients.",
        )

    def test_research_spacing_preserves_fenced_code(self) -> None:
        response = "Intro.\n\n```py\nfirst = 1\n\nsecond = 2\n```\n\nDone."

        result = AIModeration._compact_research_spacing(response)

        self.assertEqual(
            result,
            "Intro.\n```py\nfirst = 1\n\nsecond = 2\n```\nDone.",
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

    def test_different_user_can_continue_active_channel_topic(self) -> None:
        client = object.__new__(GeminiClient)
        client.bot = SimpleNamespace(user=SimpleNamespace(id=99))
        first_user = SimpleNamespace(id=1, bot=False)
        second_user = SimpleNamespace(id=2, bot=False)
        bot_user = SimpleNamespace(id=99, bot=True)
        messages = [
            SimpleNamespace(author=first_user, content="roleplay as my friend", reference=None),
            SimpleNamespace(author=bot_user, content="I can chat like a friend", reference=None),
            SimpleNamespace(author=second_user, content="so can you be my gf", reference=None),
        ]

        self.assertTrue(
            client._is_conversation_continuation(second_user, messages)
        )

    def test_active_chat_window_expires(self) -> None:
        cog = object.__new__(AIModeration)
        cog._active_chat_channels = {}
        cog._mark_chat_active(123)
        self.assertTrue(cog._is_chat_active(123))

        cog._active_chat_channels[123] = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.assertFalse(cog._is_chat_active(123))
        self.assertNotIn(123, cog._active_chat_channels)

    def test_deepseek_session_is_named_for_server_and_channel(self) -> None:
        guild = SimpleNamespace(id=10, name="Soul")
        message = SimpleNamespace(
            channel=SimpleNamespace(id=20, name="general-chat")
        )

        key, name = GeminiClient._deepseek_session_identity(guild, message)

        self.assertEqual(key, "10:20")
        self.assertEqual(name, "Soul -> General Chat")

        research_key, research_name = GeminiClient._deepseek_session_identity(
            guild,
            message,
            research=True,
        )

        self.assertEqual(research_key, "10:20:research")
        self.assertEqual(research_name, "Soul -> General Chat [Research]")

        vision_key, vision_name = GeminiClient._deepseek_session_identity(
            guild,
            message,
            vision=True,
        )

        self.assertEqual(vision_key, "10:20:vision")
        self.assertEqual(vision_name, "Soul -> General Chat [Vision]")


class DeepSeekModerationSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_research_request_builds_a_complete_plan(self) -> None:
        cog = object.__new__(AIModeration)
        cog.ai = SimpleNamespace(has_web_search=True)

        signals = await cog._build_conversation_signals(
            "research all the conversion rates from different currencies to JMD"
        )

        self.assertEqual(signals.mode, ConversationMode.RESEARCH)
        self.assertTrue(signals.show_research_indicator)
        self.assertTrue(signals.asks_for_long_answer)
        self.assertEqual(signals.focus_entities, ())

        client = object.__new__(GeminiClient)
        client.config = SimpleNamespace(max_tokens_chat=1200)
        client.bot = SimpleNamespace(user=None)
        plan = client._build_conversation_plan(
            signals=signals,
            user_content="research conversion rates to JMD",
            guild=SimpleNamespace(name="Soul", member_count=10),
            author=SimpleNamespace(name="Surreny"),
            past_memory="",
        )

        self.assertTrue(plan.show_indicator)
        self.assertIn("research conversion rates to JMD", plan.user_prompt)

    async def test_call_passes_moderation_session_name_to_deepseek_web(self) -> None:
        class FakeDeepSeek:
            enabled = True

            def __init__(self) -> None:
                self.kwargs = {}

            async def chat(self, prompt: str, **kwargs):
                self.kwargs = kwargs
                return "{}"

        fake = FakeDeepSeek()
        client = object.__new__(GeminiClient)
        client.provider = "deepseek-web"
        client._deepseek_web = fake

        result = await client._call(
            [{"role": "user", "content": "warn <@20>"}],
            temperature=0.2,
            max_tokens=100,
            json_mode=True,
            session_key="10:moderation",
            session_name="Soul -> moderation",
            long_answer=True,
        )

        self.assertEqual(result, "{}")
        self.assertEqual(fake.kwargs["session_key"], "10:moderation")
        self.assertEqual(fake.kwargs["session_name"], "Soul -> moderation")
        self.assertTrue(fake.kwargs["long_answer"])


if __name__ == "__main__":
    unittest.main()
