import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pathlib import Path

from cogs.aimoderation import (
    AIModeration,
    Decision,
    DecisionType,
    GeminiClient,
    GuildSettings,
    ToolType,
)


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


class AIModerationReasonTests(unittest.IsolatedAsyncioTestCase):
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


if __name__ == "__main__":
    unittest.main()
