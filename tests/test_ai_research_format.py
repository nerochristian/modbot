import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from cogs.aimoderation.aimoderation import AIClient, AIModeration
from cogs.aimoderation.prompts import DEEP_RESEARCH_SYSTEM_PROMPT
from cogs.aimoderation.types import ConversationMode
from utils.deepseek_web import DeepSeekWebError


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
            "Released in early 2026.\n\n"
            "## Key Context\n\n"
            "• First detail.\n\n"
            "• Second detail.\n\n"
            "## Game Overview\n\n"
            "The core loop involves:\n\n"
            "• Checking patients.",
        )

    def test_bold_wrapped_discord_heading_becomes_embed_title(self) -> None:
        embed = AIModeration._build_research_embed(
            None,
            "**# 📢 Community Announcement: Moving Forward**\n\n"
            "Hey @everyone,\n\n"
            "• **Bot Usage Rules**\n"
            "  Use bots only in designated <#123456789012345678> channels.",
            "community update",
        )

        self.assertEqual(embed.title, "📢 Community Announcement: Moving Forward")
        self.assertIn("Hey @everyone,\n\n• **Bot Usage Rules**", embed.description)
        self.assertIn("<#123456789012345678>", embed.description)

    def test_research_prompt_requires_discord_announcement_shape(self) -> None:
        self.assertIn("# 📢 Community Announcement:", DEEP_RESEARCH_SYSTEM_PROMPT)
        self.assertIn("Hey @everyone,", DEEP_RESEARCH_SYSTEM_PROMPT)
        self.assertIn("• **[Topic Title]**", DEEP_RESEARCH_SYSTEM_PROMPT)
        self.assertIn("<#channel_id>", DEEP_RESEARCH_SYSTEM_PROMPT)

    def test_long_research_uses_multiple_embeds_without_truncation(self) -> None:
        response = "# Global Brief\n\n" + "\n\n".join(
            f"## Section {index}\nmarker-{index} " + (chr(96 + index) * 1_500)
            for index in range(1, 5)
        )

        embeds = AIModeration._build_research_embeds(response, "world news")
        combined = "\n".join(embed.description or "" for embed in embeds)

        self.assertGreater(len(embeds), 1)
        self.assertTrue(all(len(embed.description or "") <= 3_900 for embed in embeds))
        for index in range(1, 5):
            self.assertIn(f"marker-{index}", combined)
        self.assertIn("(1/", embeds[0].title)

    def test_research_spacing_preserves_fenced_code(self) -> None:
        response = "Intro.\n\n```py\nfirst = 1\n\nsecond = 2\n```\n\nDone."

        result = AIModeration._compact_research_spacing(response)

        self.assertEqual(
            result,
            "Intro.\n\n```py\nfirst = 1\n\nsecond = 2\n```\n\nDone.",
        )

    def test_topic_words_match_related_inflections(self) -> None:
        first = AIClient._conversation_topic_words("is zzz a gooner game")
        second = AIClient._conversation_topic_words("is gooning valid")

        self.assertIn("goon", first & second)

    def test_topic_words_ignore_bot_mentions_and_generic_words(self) -> None:
        topics = AIClient._conversation_topic_words(
            "<@123456789012345678> should I do that?"
        )

        self.assertEqual(topics, set())

    def test_different_user_can_continue_active_channel_topic(self) -> None:
        client = object.__new__(AIClient)
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

        key, name = AIClient._deepseek_session_identity(guild, message)

        self.assertEqual(key, "10:20")
        self.assertEqual(name, "Soul -> General Chat")

        research_key, research_name = AIClient._deepseek_session_identity(
            guild,
            message,
            research=True,
        )

        self.assertEqual(research_key, "10:20:research")
        self.assertEqual(research_name, "Soul -> General Chat [Research]")

        vision_key, vision_name = AIClient._deepseek_session_identity(
            guild,
            message,
            vision=True,
        )

        self.assertEqual(vision_key, "10:20:vision")
        self.assertEqual(vision_name, "Soul -> General Chat [Vision]")


class DeepSeekModerationSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_latest_game_update_routes_to_search_without_deepthink(self) -> None:
        classifier = AsyncMock(
            return_value={
                "route": "search",
                "confidence": 0.98,
                "current_info": True,
            }
        )
        cog = object.__new__(AIModeration)
        cog.ai = SimpleNamespace(
            has_web_search=True,
            classify_research_route=classifier,
        )

        signals = await cog._build_conversation_signals(
            "latest genshin update?"
        )

        self.assertEqual(signals.mode, ConversationMode.RESEARCH)
        self.assertTrue(signals.asks_for_current_info)
        self.assertFalse(signals.use_deepthink)
        self.assertFalse(signals.asks_for_long_answer)
        classifier.assert_awaited_once_with("latest genshin update?")

    async def test_timeless_question_stays_normal_when_galaxy_says_chat(self) -> None:
        cog = object.__new__(AIModeration)
        cog.ai = SimpleNamespace(
            has_web_search=True,
            classify_research_route=AsyncMock(
                return_value={
                    "route": "normal_chat",
                    "confidence": 0.94,
                    "current_info": False,
                }
            ),
        )

        signals = await cog._build_conversation_signals(
            "what is a Python list?"
        )

        self.assertEqual(signals.mode, ConversationMode.STANDARD)
        self.assertFalse(signals.use_deepthink)

    async def test_current_role_question_falls_back_to_fast_search_when_classifier_fails(self) -> None:
        cog = object.__new__(AIModeration)
        cog.ai = SimpleNamespace(
            has_web_search=True,
            classify_research_route=AsyncMock(return_value=None),
        )

        signals = await cog._build_conversation_signals(
            "who is the current CEO of Discord?"
        )

        self.assertEqual(signals.mode, ConversationMode.RESEARCH)
        self.assertTrue(signals.asks_for_current_info)
        self.assertFalse(signals.use_deepthink)

    async def test_explicit_research_request_builds_a_complete_plan(self) -> None:
        cog = object.__new__(AIModeration)
        classifier = AsyncMock(
            return_value={
                "route": "search_deepthink",
                "confidence": 0.97,
                "current_info": True,
            }
        )
        cog.ai = SimpleNamespace(
            has_web_search=True,
            classify_research_route=classifier,
        )

        signals = await cog._build_conversation_signals(
            "research all the conversion rates from different currencies to JMD"
        )

        self.assertEqual(signals.mode, ConversationMode.RESEARCH)
        self.assertTrue(signals.show_research_indicator)
        self.assertTrue(signals.asks_for_long_answer)
        self.assertTrue(signals.use_deepthink)
        self.assertEqual(signals.focus_entities, ())
        classifier.assert_awaited_once()

        client = object.__new__(AIClient)
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
        client = object.__new__(AIClient)
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

    async def test_call_falls_back_to_digitalocean_when_deepseek_web_fails(self) -> None:
        class BrokenDeepSeek:
            enabled = True

            async def chat(self, prompt: str, **kwargs):
                raise DeepSeekWebError("browser crashed")

        client = object.__new__(AIClient)
        client.config = SimpleNamespace(model="deepseek-web")
        client._deepseek_web = BrokenDeepSeek()
        client._call_digitalocean = AsyncMock(return_value='{"type": "chat"}')

        result = await client._call(
            [{"role": "user", "content": "hello"}],
            temperature=0.2,
            max_tokens=100,
            json_mode=True,
            session_key="10:moderation",
            session_name="Soul -> moderation",
        )

        self.assertEqual(result, '{"type": "chat"}')
        client._call_digitalocean.assert_awaited_once()

    async def test_call_falls_back_to_digitalocean_when_deepseek_web_stalls(self) -> None:
        class StalledDeepSeek:
            enabled = True

            async def chat(self, prompt: str, **kwargs):
                await asyncio.sleep(1)
                return "{}"

        client = object.__new__(AIClient)
        client.config = SimpleNamespace(model="deepseek-web")
        client._deepseek_web = StalledDeepSeek()
        client._call_digitalocean = AsyncMock(return_value='{"type": "chat"}')

        with patch.dict("os.environ", {"DEEPSEEK_WEB_PRIMARY_TIMEOUT": "0.1"}):
            result = await client._call(
                [{"role": "user", "content": "hello"}],
                temperature=0.2,
                max_tokens=100,
                json_mode=True,
                session_key="10:moderation",
                session_name="Soul -> moderation",
            )

        self.assertEqual(result, '{"type": "chat"}')
        client._call_digitalocean.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
