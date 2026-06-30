import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pathlib import Path

import discord

from cogs.aimoderation.aimoderation import (
    AIConfig,
    AIModeration,
    ConversationMode,
    ConversationSignals,
    Decision,
    DecisionType,
    GeminiClient,
    GuildSettings,
    ToolResult,
    ToolType,
)
from utils.deepseek_web import DeepSeekWebError


class AIActionRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cog = object.__new__(AIModeration)

    def test_casual_conditional_question_is_conversation(self) -> None:
        content = "if someone is gay, are they gay?"

        self.assertFalse(self.cog._looks_like_mod_request(content))
        self.assertFalse(self.cog._looks_like_advanced_action_request(content))

    def test_other_conditional_questions_are_not_actions(self) -> None:
        casual_questions = (
            "when someone is tired, are they sleepy?",
            "whenever someone laughs, does that mean they are happy?",
            "every person is different, right?",
        )

        for content in casual_questions:
            with self.subTest(content=content):
                self.assertFalse(self.cog._looks_like_mod_request(content))
                self.assertFalse(
                    self.cog._looks_like_advanced_action_request(content)
                )

    def test_conditional_discord_actions_still_route_as_actions(self) -> None:
        action_requests = (
            "if someone spams, mute them",
            "when someone posts a link delete the message",
            "whenever someone joins, can you give them the member role",
            "every time someone swears then warn them",
        )

        for content in action_requests:
            with self.subTest(content=content):
                self.assertTrue(self.cog._looks_like_mod_request(content))
                self.assertTrue(
                    self.cog._looks_like_advanced_action_request(content)
                )

    def test_forced_targeted_orientation_claim_is_not_repeated(self) -> None:
        reply = self.cog._quick_conversation_reply(
            "say: <@123456789012345678> is gay"
        )

        self.assertEqual(
            reply,
            "I'm not going to label someone else's sexuality for them. "
            "They can speak for themselves.",
        )

    def test_targeted_orientation_question_is_not_guessed(self) -> None:
        reply = self.cog._quick_conversation_reply(
            "is <@123456789012345678> gay?"
        )

        self.assertIsNotNone(reply)

    def test_general_orientation_question_stays_in_conversation(self) -> None:
        reply = self.cog._quick_conversation_reply(
            "if someone is gay, are they gay?"
        )

        self.assertIsNone(reply)

    def test_ping_everyone_request_is_refused_without_echo(self) -> None:
        reply = self.cog._quick_conversation_reply("can you ping @everyone?")

        self.assertEqual(reply, "I can't help send pings.")
        self.assertNotIn("@everyone", reply)

    def test_ping_user_request_is_refused_without_echo(self) -> None:
        reply = self.cog._quick_conversation_reply(
            "please tag <@123456789012345678> for me"
        )

        self.assertEqual(reply, "I can't help send pings.")
        self.assertNotIn("<@", reply)

    def test_non_ping_use_of_word_ping_stays_in_conversation(self) -> None:
        reply = self.cog._quick_conversation_reply("what is ping in networking?")

        self.assertIsNone(reply)

    def test_risky_echo_request_is_refused_without_echo(self) -> None:
        reply = self.cog._quick_conversation_reply("say a racial slur")

        self.assertEqual(reply, "I can't help with that.")
        self.assertNotIn("racial", reply.lower())
        self.assertNotIn("slur", reply.lower())

    def test_fun_joke_reply_is_deterministic(self) -> None:
        reply = self.cog._quick_conversation_reply("tell me a joke")

        self.assertEqual(
            reply,
            "I asked the audit log for gossip and it said everything is suspicious.",
        )

    def test_reply_target_timeout_shortcut_keeps_reason_and_duration(self) -> None:
        message = SimpleNamespace(mentions=[])
        decision = self.cog._quick_route(message, "timeout this guy 10m for spam")

        self.assertIsNotNone(decision)
        self.assertEqual(decision.tool, ToolType.TIMEOUT)
        self.assertEqual(decision.arguments["seconds"], 600)
        self.assertEqual(decision.arguments["reason"], "spam")

    def test_reply_target_warn_shortcut_keeps_reason(self) -> None:
        message = SimpleNamespace(mentions=[])
        decision = self.cog._quick_route(message, "warn them for being weird")

        self.assertIsNotNone(decision)
        self.assertEqual(decision.tool, ToolType.WARN)
        self.assertEqual(decision.arguments["reason"], "being weird")

    def test_mentioned_warn_shortcut_ignores_bot_mention_for_target(self) -> None:
        bot_user = SimpleNamespace(id=10, bot=True)
        target = SimpleNamespace(id=20, bot=False)
        self.cog.bot = SimpleNamespace(user=bot_user)
        message = SimpleNamespace(mentions=[bot_user, target])

        decision = self.cog._quick_route(message, "warn <@20> for spam")

        self.assertIsNotNone(decision)
        self.assertEqual(decision.tool, ToolType.WARN)
        self.assertEqual(decision.arguments["target_user_id"], 20)
        self.assertEqual(decision.arguments["reason"], "spam")

    def test_visible_mention_multi_warning_request_routes_as_action(self) -> None:
        bot_user = SimpleNamespace(id=10, bot=True)
        target = SimpleNamespace(id=20, bot=False)
        self.cog.bot = SimpleNamespace(user=bot_user)
        message = SimpleNamespace(
            content="<@10> give <@20> 3 warnings for being a retard",
            mentions=[bot_user, target],
        )

        content = self.cog.clean_content(message)
        decision = self.cog._quick_route(message, content)

        self.assertEqual(content, "give <@20> 3 warnings for being a retard")
        self.assertTrue(self.cog._looks_like_mod_request(content))
        self.assertFalse(self.cog._looks_like_warning_lookup(content))
        self.assertIsNotNone(decision)
        self.assertEqual(decision.tool, ToolType.WARN)
        self.assertEqual(decision.arguments["target_user_id"], 20)
        self.assertEqual(decision.arguments["warning_count"], 3)
        self.assertEqual(decision.arguments["reason"], "being a retard")

    def test_multi_warning_action_variants_preserve_count_and_reason(self) -> None:
        bot_user = SimpleNamespace(id=10, bot=True)
        target = SimpleNamespace(id=20, bot=False)
        self.cog.bot = SimpleNamespace(user=bot_user)
        message = SimpleNamespace(mentions=[bot_user, target])
        cases = (
            ("give 3 warnings to <@20> because repeated spam", 3),
            ("issue <@20> two warnings: repeated spam", 2),
            ("warn <@20> 4 times for repeated spam", 4),
            ("add a warning to <@20> for repeated spam", 1),
            ("apply warnings x5 to <@20> for repeated spam", 5),
            ("warn <@20> twice for repeated spam", 2),
            ("give 3x warnings to <@20> for repeated spam", 3),
            ("give x6 warns to <@20> for repeated spam", 6),
        )

        for content, expected_count in cases:
            with self.subTest(content=content):
                decision = self.cog._quick_route(message, content)

                self.assertIsNotNone(decision)
                self.assertEqual(decision.tool, ToolType.WARN)
                self.assertEqual(decision.arguments["target_user_id"], 20)
                self.assertEqual(decision.arguments["warning_count"], expected_count)
                self.assertEqual(decision.arguments["reason"], "repeated spam")

    def test_visible_mention_timeout_command_routes_end_to_end(self) -> None:
        bot_user = SimpleNamespace(id=111111111111111111, bot=True)
        target = SimpleNamespace(id=222222222222222222, bot=False)
        self.cog.bot = SimpleNamespace(user=bot_user)
        message = SimpleNamespace(
            content=(
                "<@111111111111111111> mute "
                "<@222222222222222222> 10m for spam"
            ),
            mentions=[bot_user, target],
        )

        content = self.cog.clean_content(message)
        decision = self.cog._quick_route(message, content)

        self.assertEqual(content, "mute <@222222222222222222> 10m for spam")
        self.assertIsNotNone(decision)
        self.assertEqual(decision.tool, ToolType.TIMEOUT)
        self.assertEqual(decision.arguments["target_user_id"], target.id)
        self.assertEqual(decision.arguments["seconds"], 600)
        self.assertEqual(decision.arguments["reason"], "spam")

    def test_polite_warn_request_routes_without_model(self) -> None:
        message = SimpleNamespace(mentions=[])

        self.assertTrue(self.cog._looks_like_mod_request("can you warn them for spam"))
        decision = self.cog._quick_route(message, "can you warn them for spam")

        self.assertIsNotNone(decision)
        self.assertEqual(decision.tool, ToolType.WARN)
        self.assertEqual(decision.arguments["reason"], "spam")

    def test_polite_timeout_request_keeps_duration_and_reason(self) -> None:
        message = SimpleNamespace(mentions=[])
        decision = self.cog._quick_route(
            message,
            "please timeout this guy 15m for spam",
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.tool, ToolType.TIMEOUT)
        self.assertEqual(decision.arguments["seconds"], 900)
        self.assertEqual(decision.arguments["reason"], "spam")

    def test_warning_history_question_is_a_moderation_query(self) -> None:
        self.assertTrue(
            self.cog._looks_like_mod_request("what are <@20> warnings?")
        )
        self.assertTrue(
            self.cog._looks_like_advanced_action_request("show his warnings")
        )

    def test_warning_history_question_routes_without_model(self) -> None:
        bot_user = SimpleNamespace(id=10, bot=True)
        target = SimpleNamespace(id=20, bot=False)
        self.cog.bot = SimpleNamespace(user=bot_user)
        message = SimpleNamespace(mentions=[bot_user, target])

        decision = self.cog._quick_route(
            message,
            "what are <@20> warnings?",
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.tool, ToolType.GET_WARNINGS)
        self.assertEqual(decision.arguments["target_user_id"], 20)

    def test_warning_history_variants_remain_read_only(self) -> None:
        bot_user = SimpleNamespace(id=10, bot=True)
        target = SimpleNamespace(id=20, bot=False)
        self.cog.bot = SimpleNamespace(user=bot_user)
        message = SimpleNamespace(mentions=[bot_user, target])

        for content in (
            "warnings for <@20>",
            "show <@20> warnings",
            "how many warnings does <@20> have?",
        ):
            with self.subTest(content=content):
                decision = self.cog._quick_route(message, content)

                self.assertIsNotNone(decision)
                self.assertEqual(decision.tool, ToolType.GET_WARNINGS)

    def test_staff_with_manage_messages_can_use_ai_tools(self) -> None:
        perms = SimpleNamespace(
            administrator=False,
            manage_guild=False,
            manage_messages=True,
            moderate_members=False,
            kick_members=False,
            ban_members=False,
            manage_channels=False,
            manage_roles=False,
        )
        member = SimpleNamespace(id=123, guild_permissions=perms)

        self.assertTrue(AIModeration._can_use_ai_tools(member))

    def test_deepseek_disabled_diagnostic_names_real_setting(self) -> None:
        client = object.__new__(GeminiClient)
        client.provider = "deepseek-web"
        client._deepseek_web = SimpleNamespace(
            enabled=False,
            storage_state_path=Path("/tmp/deepseek-storage.json"),
            session_index_path=Path("/tmp/deepseek-channel-sessions.json"),
            timeout_seconds=150,
        )

        self.assertIn("DEEPSEEK_WEB_ENABLED", client.availability_message())
        self.assertIn("Available now: no", client.diagnostic_lines())

    def test_tool_access_uses_registry_metadata_object(self) -> None:
        actor = SimpleNamespace(id=123)

        self.assertIsNone(self.cog.validate_tool_access(actor, None, ToolType.HELP))

    def test_owner_only_tool_is_rejected_before_guild_permission_checks(self) -> None:
        actor = SimpleNamespace(id=123)

        with patch(
            "cogs.aimoderation.aimoderation.is_bot_owner_id",
            return_value=False,
        ):
            error = self.cog.validate_tool_access(
                actor,
                None,
                ToolType.EXECUTE_PYTHON,
            )

        self.assertEqual(error, "This action is restricted to the bot owner.")

    def test_digitalocean_availability_uses_configured_constants(self) -> None:
        client = object.__new__(GeminiClient)
        client.provider = "digitalocean"

        with patch("cogs.aimoderation.ai_client._DO_API_KEY", "key"), patch(
            "cogs.aimoderation.ai_client._DO_BASE_URL",
            "https://example.invalid/v1",
        ):
            self.assertTrue(client.is_available)
            self.assertEqual(
                client.availability_message(),
                "DigitalOcean inference is configured.",
            )

    def test_decision_discards_non_mapping_arguments(self) -> None:
        decision = Decision.from_dict(
            {
                "type": "tool_call",
                "tool": "warn_member",
                "arguments": ["not", "a", "mapping"],
            }
        )

        self.assertEqual(decision.arguments, {})


class AIModerationReasonTests(unittest.IsolatedAsyncioTestCase):
    async def test_research_does_not_feed_saved_memory_or_continue_chat(self) -> None:
        client = object.__new__(GeminiClient)
        client.provider = "deepseek-web"
        client.config = AIConfig()
        client._block_until = None
        client._block_reason = None
        client._brave_search_api_key = None
        client._tavily_api_key = None
        client._serpapi_api_key = None
        client._rate_limiter = SimpleNamespace(
            is_rate_limited=AsyncMock(return_value=(False, 0)),
            record_call=AsyncMock(),
        )
        client._deepseek_web = SimpleNamespace(
            enabled=True,
            chat=AsyncMock(return_value="researched answer"),
        )
        client._update_memory_smart = AsyncMock()
        db = SimpleNamespace(get_ai_memory=AsyncMock(return_value="PRIVATE MEMORY"))
        client.bot = SimpleNamespace(user=SimpleNamespace(id=999), db=db)
        guild = SimpleNamespace(id=1, name="Guild", member_count=10)
        author = SimpleNamespace(id=2, name="User")
        signals = ConversationSignals(
            mode=ConversationMode.RESEARCH,
            confidence=1.0,
            show_research_indicator=True,
        )

        response = await client.converse(
            user_content="research this",
            guild=guild,
            author=author,
            recent_messages=[],
            signals=signals,
        )

        self.assertEqual(response, "researched answer")
        prompt = client._deepseek_web.chat.await_args.args[0]
        self.assertNotIn("PRIVATE MEMORY", prompt)
        self.assertFalse(client._deepseek_web.chat.await_args.kwargs["continue_session"])
        client._update_memory_smart.assert_called_once_with(
            author.id,
            "research this",
            "researched answer",
            "PRIVATE MEMORY",
        )

    async def test_conversation_falls_back_to_digitalocean_when_deepseek_web_fails(self) -> None:
        client = object.__new__(GeminiClient)
        client.provider = "deepseek-web"
        client.config = AIConfig()
        client._block_until = None
        client._block_reason = None
        client._brave_search_api_key = None
        client._tavily_api_key = None
        client._serpapi_api_key = None
        client._rate_limiter = SimpleNamespace(
            is_rate_limited=AsyncMock(return_value=(False, 0)),
            record_call=AsyncMock(),
        )
        client._deepseek_web = SimpleNamespace(
            enabled=True,
            chat=AsyncMock(side_effect=DeepSeekWebError("browser failed")),
        )
        client._call_digitalocean_conversation = AsyncMock(return_value="fallback answer")
        client._collect_image_context = AsyncMock(return_value=[])
        client._update_memory_smart = AsyncMock()
        db = SimpleNamespace(get_ai_memory=AsyncMock(return_value=""))
        client.bot = SimpleNamespace(user=SimpleNamespace(id=999), db=db)

        response = await client.converse(
            user_content="hello",
            guild=SimpleNamespace(id=1, name="Guild", member_count=10),
            author=SimpleNamespace(id=2, name="User"),
            recent_messages=[],
            signals=ConversationSignals(mode=ConversationMode.STANDARD, confidence=1.0),
        )

        self.assertEqual(response, "fallback answer")
        client._call_digitalocean_conversation.assert_awaited_once()
        client._update_memory_smart.assert_called_once()

    async def test_reason_is_rewritten_once_and_cleaned(self) -> None:
        cog = object.__new__(AIModeration)
        cog.ai = SimpleNamespace(
            is_available=True,
            _call=AsyncMock(return_value="Reason: Repeated spam in chat"),
        )
        decision = Decision(
            type=DecisionType.TOOL_CALL,
            reason="rule: warn",
            tool=ToolType.WARN,
            arguments={"reason": "for spamming a ton"},
        )

        result = await cog._polish_decision_reason(decision, GuildSettings())

        self.assertEqual(result.arguments["reason"], "Repeated spam in chat")
        cog.ai._call.assert_awaited_once()

    async def test_reason_falls_back_to_clean_original_when_ai_is_unavailable(self) -> None:
        cog = object.__new__(AIModeration)
        cog.ai = SimpleNamespace(is_available=False)
        decision = Decision(
            type=DecisionType.TOOL_CALL,
            reason="rule: ban",
            tool=ToolType.BAN,
            arguments={"reason": "because repeated ban evasion"},
        )

        result = await cog._polish_decision_reason(decision, GuildSettings())

        self.assertEqual(result.arguments["reason"], "repeated ban evasion")

    async def test_classic_tool_result_skips_v2_conversion(self) -> None:
        cog = object.__new__(AIModeration)
        cog.reply = AsyncMock()
        message = SimpleNamespace()
        embed = SimpleNamespace()
        result = ToolResult.ok("warnings", embed=embed, use_v2=False)

        await cog.reply_tool_result(message, result)

        cog.reply.assert_awaited_once_with(
            message,
            embed=embed,
            delete_after=None,
            use_v2=False,
        )

    async def test_classic_reply_applies_shared_status_emoji_formatting(self) -> None:
        cog = object.__new__(AIModeration)
        sent_message = SimpleNamespace(delete=AsyncMock())
        channel = SimpleNamespace(send=AsyncMock(return_value=sent_message))
        guild = SimpleNamespace()
        message = SimpleNamespace(channel=channel, guild=guild)
        embed = discord.Embed(title="⚠️ Warnings for gabb")

        with patch(
            "cogs.aimoderation.aimoderation.apply_status_emoji_overrides",
            new=AsyncMock(return_value=embed),
        ) as formatter, patch(
            "cogs.aimoderation.aimoderation.send_classic_message",
            new=AsyncMock(return_value=sent_message),
        ) as classic_sender:
            await cog.reply(message, embed=embed, use_v2=False)

        formatter.assert_awaited_once_with(embed, guild)
        classic_sender.assert_awaited_once()
        self.assertIs(classic_sender.await_args.kwargs["embed"], embed)
        self.assertIsNone(classic_sender.await_args.kwargs["view"])
        channel.send.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
