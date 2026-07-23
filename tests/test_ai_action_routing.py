import asyncio
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pathlib import Path

import discord

from database import Database
from cogs.aimoderation.aimoderation import (
    AIConfig,
    AIClient,
    AIModeration,
    ConversationMode,
    ConversationSignals,
    Decision,
    DecisionType,
    GuildSettings,
    ToolResult,
    ToolType,
)
from cogs.aimoderation.types import ImageContext, PermissionFlags
from cogs.aimoderation.registry import ToolRegistry
from utils.deepseek_web import DeepSeekWebError


class AIActionRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cog = object.__new__(AIModeration)

    def test_client_initializes_provider_from_config(self) -> None:
        client = AIClient(
            SimpleNamespace(),
            AIConfig(provider="digitalocean", model="deepseek-4-flash"),
        )

        self.assertEqual(client.provider, "digitalocean")

    def test_default_galaxy_model_uses_configured_deepseek_model(self) -> None:
        from cogs.aimoderation.types import _default_ai_model

        with patch.dict(
            "os.environ",
            {
                "AI_PROVIDER": "deepseek",
                "AI_MODEL": "",
                "DEEPSEEK_MODEL": "gemini-3-5-flash",
            },
        ):
            self.assertEqual(_default_ai_model(), "gemini-3-5-flash")

    def test_default_relayrouter_model_uses_moderation_model(self) -> None:
        from cogs.aimoderation.types import _default_ai_model

        with patch.dict(
            "os.environ",
            {
                "AI_PROVIDER": "relayrouter",
                "AI_MODEL": "",
                "RELAYROUTER_MODERATION_MODEL": "gpt-5-6-terra",
            },
        ):
            self.assertEqual(_default_ai_model(), "gpt-5-6-terra")

    def test_purge_is_a_targeted_tool(self) -> None:
        from cogs.aimoderation.types import TARGETED_TOOLS

        self.assertIn(ToolType.PURGE, TARGETED_TOOLS)

    def test_risky_actions_require_confirmation_by_default(self) -> None:
        settings = GuildSettings()

        for tool in (
            ToolType.BAN,
            ToolType.KICK,
            ToolType.PURGE,
            ToolType.DELETE_CHANNEL,
            ToolType.DELETE_ROLE,
            ToolType.DELETE_EMOJI,
            ToolType.EDIT_GUILD,
            ToolType.EXECUTE_RAW_API,
            ToolType.EXECUTE_PYTHON,
        ):
            with self.subTest(tool=tool):
                decision = Decision(
                    type=DecisionType.TOOL_CALL,
                    reason="test",
                    tool=tool,
                    arguments={},
                )
                self.assertTrue(
                    self.cog._requires_confirmation(settings, decision)
                )

        timeout = Decision(
            type=DecisionType.TOOL_CALL,
            reason="test",
            tool=ToolType.TIMEOUT,
            arguments={},
        )
        self.assertTrue(self.cog._requires_confirmation(settings, timeout))

        for tool in (
            ToolType.HELP,
            ToolType.GET_WARNINGS,
            ToolType.GET_HISTORY,
            ToolType.FIND_INACTIVE_MEMBERS,
            ToolType.SCAN_CHANNEL,
            ToolType.SUMMARIZE_ACTIONS,
            ToolType.SAFETY_CHECK,
        ):
            with self.subTest(read_only_tool=tool):
                read_only = Decision(
                    type=DecisionType.TOOL_CALL,
                    reason="read only",
                    tool=tool,
                    arguments={},
                )
                self.assertFalse(
                    self.cog._requires_confirmation(settings, read_only)
                )

        long_timeout = Decision(
            type=DecisionType.TOOL_CALL,
            reason="test",
            tool=ToolType.TIMEOUT,
            arguments={"seconds": 86_400},
        )
        self.assertTrue(
            self.cog._requires_confirmation(
                GuildSettings(confirm_enabled=False), long_timeout
            )
        )

        ban = Decision(
            type=DecisionType.TOOL_CALL,
            reason="test",
            tool=ToolType.BAN,
            arguments={},
        )
        self.assertTrue(
            self.cog._requires_confirmation(
                GuildSettings(confirm_enabled=False, confirm_actions=set()), ban
            )
        )

    def test_confirmation_settings_round_trip(self) -> None:
        settings = GuildSettings.from_dict(
            {
                "aimod_confirm_enabled": "true",
                "aimod_confirm_timeout_seconds": 45,
                "aimod_confirm_actions": ["ban_member", "purge_messages"],
            }
        )

        self.assertTrue(settings.confirm_enabled)
        self.assertEqual(settings.confirm_timeout_seconds, 45)
        self.assertEqual(
            settings.confirm_actions,
            {"ban_member", "purge_messages"},
        )
        serialized = settings.to_dict()
        self.assertTrue(serialized["aimod_confirm_enabled"])
        self.assertEqual(
            serialized["aimod_confirm_actions"],
            ["ban_member", "purge_messages"],
        )

    def test_context_window_uses_api_sized_defaults_and_clamp(self) -> None:
        self.assertEqual(GuildSettings.from_dict({}).context_messages, 100)
        self.assertEqual(
            GuildSettings.from_dict({"aimod_context_messages": 999}).context_messages,
            200,
        )

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

    def test_direct_single_target_actions_stay_on_deterministic_router(self) -> None:
        direct_actions = (
            "warn @Target for spam",
            "timeout @Target for 10 minutes",
            "kick @Target for harassment",
            "ban @Target for malicious links",
            "purge 25 messages",
        )

        for content in direct_actions:
            with self.subTest(content=content):
                self.assertFalse(self.cog._requires_model_routing(content))

    def test_complex_actions_require_model_routing(self) -> None:
        complex_actions = (
            "warn every member without the Verified role",
            "timeout all accounts created less than one hour ago",
            "copy matching messages to mod-log and then delete them",
            "allow viewing but deny sending messages for Muted members",
            "schedule a cleanup of expired roles every day",
            "archive all threads inactive for seven days",
            "quarantine new arrivals when more than ten members join",
            "restore yesterday's backup after exporting the current state",
        )

        for content in complex_actions:
            with self.subTest(content=content):
                self.assertTrue(self.cog._requires_model_routing(content))

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

    def test_how_are_you_followup_is_warm_and_reciprocal(self) -> None:
        reply = self.cog._quick_conversation_reply(
            "That's true, anyway, how are you?"
        )

        self.assertEqual(
            reply,
            "I'm doing good, thanks for asking. How are you?",
        )
        self.assertNotIn("what you need", reply.lower())

    def test_whats_up_reply_does_not_turn_into_a_capability_advertisement(self) -> None:
        reply = self.cog._quick_conversation_reply("What's up?")

        self.assertEqual(reply, "Not much on my end. What's up with you?")
        self.assertNotIn("i can help", reply.lower())

    def test_model_identity_reports_requested_model_without_guessing(self) -> None:
        self.cog.ai = SimpleNamespace(
            conversation_model_name=lambda override=None: override or "gpt-5-6-luna"
        )

        reply = self.cog._quick_conversation_reply("What llm are you?")

        self.assertIn("`gpt-5-6-luna`", reply)
        self.assertIn("fallback", reply.lower())
        self.assertNotIn("gpt-4o", reply.lower())

    def test_world_news_routes_to_research_when_classifier_returns_nothing(self) -> None:
        self.cog.ai = SimpleNamespace(
            classify_research_route=AsyncMock(return_value=None),
            has_web_search=True,
        )

        signals = asyncio.run(
            self.cog._build_conversation_signals("What's going on in the world?")
        )

        self.assertEqual(signals.mode, ConversationMode.RESEARCH)
        self.assertTrue(signals.asks_for_current_info)
        self.assertTrue(signals.show_research_indicator)

    def test_reply_target_timeout_shortcut_keeps_reason_and_duration(self) -> None:
        message = SimpleNamespace(mentions=[])
        decision = self.cog._quick_route(message, "timeout this guy 10m for spam")

        self.assertIsNotNone(decision)
        self.assertEqual(decision.tool, ToolType.TIMEOUT)
        self.assertEqual(decision.arguments["seconds"], 600)
        self.assertEqual(decision.arguments["reason"], "spam")

    def test_bulk_timeout_shortcut_grounds_excluded_role_without_target(self) -> None:
        role = SimpleNamespace(id=55, name="Above all")
        message = SimpleNamespace(mentions=[], role_mentions=[role])

        decision = self.cog._quick_route(
            message,
            "mute everyone who doesn't have the role <@&55>",
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.tool, ToolType.TIMEOUT)
        self.assertTrue(decision.arguments["all_members"])
        self.assertEqual(decision.arguments["exclude_role_id"], 55)
        self.assertEqual(decision.arguments["exclude_role_name"], "Above all")
        self.assertNotIn("target_user_id", decision.arguments)

    def test_bulk_timeout_shortcut_grounds_excluded_members_without_fake_role(self) -> None:
        bot_user = SimpleNamespace(id=999, bot=True)
        aries = SimpleNamespace(id=20, bot=False)
        cherry = SimpleNamespace(id=30, bot=False)
        author = SimpleNamespace(id=10)
        self.cog.bot = SimpleNamespace(user=bot_user)
        message = SimpleNamespace(
            author=author,
            mentions=[bot_user, aries, cherry],
            role_mentions=[],
        )

        decision = self.cog._quick_route(
            message,
            "mute everyone, except me, <@20> and <@30>",
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.tool, ToolType.TIMEOUT)
        self.assertEqual(decision.arguments["exclude_user_ids"], [10, 20, 30])
        self.assertNotIn("exclude_role_name", decision.arguments)
        self.assertNotIn("target_user_id", decision.arguments)

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

    def test_history_lookup_is_a_moderation_query(self) -> None:
        for content in (
            "show actions for <@20>",
            "pull up <@20> record",
            "modlogs <@20>",
            "check his history",
        ):
            with self.subTest(content=content):
                self.assertTrue(self.cog._looks_like_mod_request(content))
                self.assertTrue(
                    self.cog._looks_like_advanced_action_request(content)
                )

    def test_history_lookup_routes_to_get_history(self) -> None:
        bot_user = SimpleNamespace(id=10, bot=True)
        target = SimpleNamespace(id=20, bot=False)
        self.cog.bot = SimpleNamespace(user=bot_user)
        message = SimpleNamespace(mentions=[bot_user, target])

        for content in (
            "show actions for <@20>",
            "pull up <@20> record",
            "modlogs <@20>",
            "whats <@20> rap sheet",
        ):
            with self.subTest(content=content):
                decision = self.cog._quick_route(message, content)

                self.assertIsNotNone(decision)
                self.assertEqual(decision.tool, ToolType.GET_HISTORY)
                self.assertEqual(decision.arguments["target_user_id"], 20)

    def test_warn_history_still_routes_to_get_warnings(self) -> None:
        # "warning history" is specifically about warnings, not the full record.
        bot_user = SimpleNamespace(id=10, bot=True)
        target = SimpleNamespace(id=20, bot=False)
        self.cog.bot = SimpleNamespace(user=bot_user)
        message = SimpleNamespace(mentions=[bot_user, target])

        decision = self.cog._quick_route(message, "show <@20> warning history")

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

    def test_canonical_mod_role_can_route_moderation_tools(self) -> None:
        perms = SimpleNamespace(
            administrator=False,
            manage_guild=False,
            manage_messages=False,
            moderate_members=False,
            kick_members=False,
            ban_members=False,
            manage_channels=False,
            manage_roles=False,
        )
        member = SimpleNamespace(
            id=123,
            guild_permissions=perms,
            roles=[SimpleNamespace(id=987654321)],
        )
        settings = GuildSettings.from_dict({"mod_roles": ["987654321"]})

        self.assertTrue(AIModeration._can_use_ai_tools(member, settings))
        self.assertEqual(settings.mod_roles, {987654321})
        self.assertEqual(settings.to_dict()["mod_roles"], [987654321])

    def test_configured_mod_role_never_replaces_native_action_permission(self) -> None:
        actor_permissions = SimpleNamespace(
            administrator=False,
            ban_members=False,
            manage_channels=False,
        )
        bot_permissions = SimpleNamespace(
            ban_members=True,
            manage_channels=True,
        )
        actor = SimpleNamespace(id=123, guild_permissions=actor_permissions)
        guild = SimpleNamespace(me=SimpleNamespace(guild_permissions=bot_permissions))

        with patch("cogs.aimoderation.aimoderation.discord.Member", SimpleNamespace), patch(
            "cogs.aimoderation.aimoderation.is_bot_owner_id",
            return_value=False,
        ):
            self.assertIn(
                "Ban Members",
                self.cog.validate_tool_access(
                    actor, guild, ToolType.BAN, configured_mod_role=True
                ),
            )
            self.assertIn(
                "Manage Channels",
                self.cog.validate_tool_access(
                    actor,
                    guild,
                    ToolType.CREATE_CHANNEL,
                    configured_mod_role=True,
                ),
            )

    def test_mod_role_does_not_bypass_bot_discord_permissions(self) -> None:
        actor = SimpleNamespace(
            id=123,
            guild_permissions=SimpleNamespace(administrator=False, ban_members=True),
        )
        guild = SimpleNamespace(
            me=SimpleNamespace(guild_permissions=SimpleNamespace(ban_members=False)),
        )

        with patch("cogs.aimoderation.aimoderation.discord.Member", SimpleNamespace), patch(
            "cogs.aimoderation.aimoderation.is_bot_owner_id",
            return_value=False,
        ):
            error = self.cog.validate_tool_access(
                actor,
                guild,
                ToolType.BAN,
                configured_mod_role=True,
            )

        self.assertEqual(error, "I need the `Ban Members` permission.")

    def test_channel_manage_messages_override_authorizes_purge(self) -> None:
        actor = SimpleNamespace(
            id=123,
            guild_permissions=SimpleNamespace(administrator=False, manage_messages=False),
        )
        bot_member = SimpleNamespace(
            id=999,
            guild_permissions=SimpleNamespace(administrator=False, manage_messages=False),
        )
        guild = SimpleNamespace(me=bot_member)
        channel = SimpleNamespace(
            permissions_for=lambda member: SimpleNamespace(
                administrator=False,
                manage_messages=member.id in {123, 999},
            )
        )

        with patch("cogs.aimoderation.aimoderation.discord.Member", SimpleNamespace), patch(
            "cogs.aimoderation.aimoderation.is_bot_owner_id",
            return_value=False,
        ):
            error = self.cog.validate_tool_access(
                actor,
                guild,
                ToolType.PURGE,
                channel=channel,
            )

        self.assertIsNone(error)

    def test_permission_snapshot_includes_effective_channel_override(self) -> None:
        guild_permissions = SimpleNamespace(
            administrator=False,
            ban_members=False,
            kick_members=False,
            manage_guild=False,
            manage_channels=False,
            manage_roles=False,
            manage_messages=False,
            manage_threads=False,
            manage_nicknames=False,
            manage_emojis_and_stickers=False,
            create_instant_invite=False,
            move_members=False,
            moderate_members=False,
            mute_members=False,
        )
        member = SimpleNamespace(guild_permissions=guild_permissions)
        channel = SimpleNamespace(
            permissions_for=lambda _: SimpleNamespace(
                manage_messages=True,
                manage_threads=True,
                create_instant_invite=True,
            )
        )

        permissions = PermissionFlags.from_member(member, channel)

        self.assertTrue(permissions.manage_messages)
        self.assertTrue(permissions.manage_threads)
        self.assertTrue(permissions.create_instant_invite)
        self.assertFalse(permissions.ban_members)

    def test_bot_owner_permission_is_explicit_and_never_implied_by_admin(self) -> None:
        admin = PermissionFlags.superuser()
        owner = PermissionFlags.superuser(bot_owner=True)

        self.assertFalse(admin.bot_owner)
        self.assertFalse(admin.allows("bot_owner"))
        self.assertTrue(owner.bot_owner)
        self.assertTrue(owner.allows("bot_owner"))

    def test_complex_server_requests_are_not_misclassified_as_chat(self) -> None:
        requests = (
            "list all members whose usernames contain invite links",
            "summarize timeouts issued during the last seven days",
            "mark as age-restricted #memes",
            "route harassment reports to the senior moderation team",
            "rank the most active public channels",
            "post an announcement for the server rules update",
            "rename the existing emoji for approved reports",
            "show who most recently changed server roles and their permissions",
        )

        for request in requests:
            with self.subTest(request=request):
                self.assertTrue(
                    self.cog._looks_like_advanced_action_request(request)
                    or self.cog._requires_model_routing(request)
                )

    def test_owner_fallback_preserves_clarifications_and_impossibility_errors(self) -> None:
        blocked_reasons = (
            "Creating the emoji requires an image URL which was not provided.",
            "Creating the emoji is impossible because no image URL was provided.",
            "No new name was specified; need clarification.",
            "Cannot programmatically detect disruptive audio; this is fundamentally impossible.",
            "This is not a concrete action with identifiable targets.",
            "Multiple possible targets are ambiguous.",
        )
        for reason in blocked_reasons:
            with self.subTest(reason=reason):
                self.assertFalse(
                    self.cog._owner_fallback_can_proceed(Decision.error(reason))
                )

        feasible = Decision.error(
            "This workflow is beyond standard tool capabilities and requires generated automation."
        )
        self.assertTrue(self.cog._owner_fallback_can_proceed(feasible))

    def test_administrator_still_requires_bot_action_permission(self) -> None:
        actor = SimpleNamespace(
            id=123,
            guild_permissions=SimpleNamespace(administrator=True, ban_members=False),
        )
        guild = SimpleNamespace(
            me=SimpleNamespace(
                id=999,
                guild_permissions=SimpleNamespace(administrator=False, ban_members=False),
            )
        )

        with patch("cogs.aimoderation.aimoderation.discord.Member", SimpleNamespace), patch(
            "cogs.aimoderation.aimoderation.is_bot_owner_id",
            return_value=False,
        ):
            error = self.cog.validate_tool_access(actor, guild, ToolType.BAN)

        self.assertEqual(error, "I need the `Ban Members` permission.")

    def test_routing_prompt_exposes_permission_derived_tool_allowlist(self) -> None:
        client = object.__new__(AIClient)
        client.config = AIConfig()
        client.bot = SimpleNamespace(user=SimpleNamespace(id=999))
        permissions = PermissionFlags(manage_messages=True)
        author = SimpleNamespace(
            id=123,
            roles=[SimpleNamespace(name="Moderator", is_default=lambda: False)],
            __str__=lambda self: "Staff",
        )

        prompt = client._build_routing_prompt(
            user_content="purge 10 messages",
            guild=SimpleNamespace(id=1, name="Guild", member_count=5),
            author=author,
            mentions=[],
            recent_messages=[],
            permissions=permissions,
        )

        authorized = prompt.split("Authorized standard tools: ", 1)[1].splitlines()[0]
        blocked = prompt.split("Blocked standard tools: ", 1)[1].splitlines()[0]
        self.assertIn("purge_messages", authorized)
        self.assertNotIn("ban_member", authorized)
        self.assertIn("ban_member", blocked)
        self.assertIn("execute_python", blocked)
        self.assertIn("Role names (untrusted labels", prompt)

        owner_prompt = client._build_routing_prompt(
            user_content="archive every inactive thread",
            guild=SimpleNamespace(id=1, name="Guild", member_count=5),
            author=author,
            mentions=[],
            recent_messages=[],
            permissions=PermissionFlags.superuser(bot_owner=True),
        )
        owner_authorized = owner_prompt.split("Authorized standard tools: ", 1)[1].splitlines()[0]
        self.assertIn("execute_python", owner_authorized)

    def test_deepseek_disabled_diagnostic_names_real_setting(self) -> None:
        client = object.__new__(AIClient)
        client.provider = "deepseek-web"
        client._deepseek_web = SimpleNamespace(
            enabled=False,
            storage_state_path=Path("/tmp/deepseek-storage.json"),
            session_index_path=Path("/tmp/deepseek-channel-sessions.json"),
            timeout_seconds=150,
        )

        with patch("cogs.aimoderation.ai_client._deepseek_api_enabled", return_value=False), patch(
            "cogs.aimoderation.ai_client._DO_API_KEY",
            "do-key",
        ):
            self.assertIn("DEEPSEEK_WEB_ENABLED", client.availability_message())
            self.assertIn("Available now: yes", client.diagnostic_lines())
            self.assertIn("DigitalOcean inference fallback", client.availability_message())

    def test_deepseek_http_is_a_real_availability_path(self) -> None:
        client = object.__new__(AIClient)
        client.provider = "deepseek"
        client._deepseek_web = SimpleNamespace(
            enabled=False,
            storage_state_path=None,
            session_index_path=None,
            timeout_seconds=150,
        )

        with patch("cogs.aimoderation.ai_client._deepseek_api_enabled", return_value=True), patch(
            "cogs.aimoderation.ai_client._DO_API_KEY",
            "",
        ):
            self.assertTrue(client.is_available)
            self.assertEqual(
                client.availability_message(),
                "DeepSeek HTTP is configured as the primary provider.",
            )
            self.assertIn("DeepSeek HTTP configured: yes", client.diagnostic_lines())

    def test_recent_target_cache_is_scoped_to_the_guild(self) -> None:
        self.cog.config = AIConfig(target_cache_ttl_minutes=5)
        self.cog._target_cache = {}

        self.cog._remember_target(100, 10, 20)

        self.assertEqual(self.cog._get_recent_target(100, 10), 20)
        self.assertIsNone(self.cog._get_recent_target(200, 10))

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
        client = object.__new__(AIClient)
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
    async def test_galaxy_classifies_search_depth_with_strict_route(self) -> None:
        client = object.__new__(AIClient)
        client.provider = "deepseek"
        client.config = AIConfig(provider="deepseek")
        client._call_deepseek_api = AsyncMock(
            return_value=(
                '{"route":"search","confidence":0.96,'
                '"current_info":true,"reason":"current game patch"}'
            )
        )

        with patch(
            "cogs.aimoderation.ai_client._deepseek_api_enabled",
            return_value=True,
        ):
            decision = await client.classify_research_route(
                "latest genshin update?"
            )

        self.assertEqual(decision["route"], "search")
        self.assertTrue(decision["current_info"])
        messages = client._call_deepseek_api.await_args.args[0]
        self.assertIn("search_deepthink", messages[0]["content"])
        self.assertIn("latest genshin update", messages[1]["content"])
        self.assertEqual(
            client._call_deepseek_api.await_args.kwargs["model"],
            "gemini-3-5-flash",
        )

    async def test_galaxy_loose_json_classifier_is_recovered(self) -> None:
        client = object.__new__(AIClient)
        client.provider = "deepseek"
        client.config = AIConfig(provider="deepseek")
        client._call_deepseek_api = AsyncMock(
            return_value="{ route: search, confidence: 0.9, current_info: true }"
        )

        with patch(
            "cogs.aimoderation.ai_client._deepseek_api_enabled",
            return_value=True,
        ):
            decision = await client.classify_research_route(
                "latest genshin update?"
            )

        self.assertEqual(decision["route"], "search")
        self.assertTrue(decision["current_info"])

    async def test_galaxy_invalid_json_classifier_falls_back_quietly(self) -> None:
        client = object.__new__(AIClient)
        client.provider = "deepseek"
        client.config = AIConfig(provider="deepseek")
        client._call_deepseek_api = AsyncMock(
            return_value="{ confidence: 0.9, current_info: maybe }"
        )

        with patch(
            "cogs.aimoderation.ai_client._deepseek_api_enabled",
            return_value=True,
        ):
            decision = await client.classify_research_route(
                "latest genshin update?"
            )

        self.assertIsNone(decision)

    async def test_galaxy_string_current_info_counts_as_current_for_search_route(self) -> None:
        client = object.__new__(AIClient)
        client.provider = "deepseek"
        client.config = AIConfig(provider="deepseek")
        client._call_deepseek_api = AsyncMock(
            return_value=(
                '```json\n{"route":"search","confidence":0.91,'
                '"current_info":"latest patch lookup","reason":"fresh info"}\n```'
            )
        )

        with patch(
            "cogs.aimoderation.ai_client._deepseek_api_enabled",
            return_value=True,
        ):
            decision = await client.classify_research_route(
                "latest genshin update?"
            )

        self.assertEqual(decision["route"], "search")
        self.assertTrue(decision["current_info"])

    async def test_disabled_ai_mod_hard_gates_explicit_owner_request(self) -> None:
        cog = object.__new__(AIModeration)
        bot_user = SimpleNamespace(id=999)
        cog.bot = SimpleNamespace(
            user=bot_user,
            get_context=AsyncMock(return_value=SimpleNamespace(valid=False)),
        )
        cog.get_guild_settings = AsyncMock(
            return_value=GuildSettings(enabled=False, chat_enabled=False),
        )
        cog._message_replies_to_bot = AsyncMock(return_value=False)
        cog.clean_content = lambda message: "ban <@20> for spam"
        cog._looks_like_mod_request = lambda content: True
        cog._looks_like_advanced_action_request = lambda content: False
        cog.reply = AsyncMock()
        cog.fetch_recent_messages = AsyncMock()
        message = SimpleNamespace(
            author=SimpleNamespace(bot=False, id=10),
            guild=SimpleNamespace(id=1),
            mentions=[bot_user],
            reference=None,
            content="<@999> ban <@20> for spam",
            channel=SimpleNamespace(id=30),
        )

        with patch(
            "cogs.aimoderation.aimoderation.is_bot_owner_id",
            return_value=True,
        ):
            await cog.on_message(message)

        cog.reply.assert_awaited_once()
        self.assertIn("AI moderation is disabled", cog.reply.await_args.kwargs["content"])
        cog.fetch_recent_messages.assert_not_awaited()

    async def test_execute_decision_rechecks_enabled_state_after_confirmation(self) -> None:
        cog = object.__new__(AIModeration)
        cog.get_guild_settings = AsyncMock(return_value=GuildSettings(enabled=False))
        cog.reply_tool_result = AsyncMock()
        message = SimpleNamespace(guild=SimpleNamespace(id=1))
        decision = Decision(
            type=DecisionType.TOOL_CALL,
            reason="spam",
            tool=ToolType.BAN,
            arguments={"target_user_id": 20},
        )

        with patch.object(ToolRegistry, "execute", new_callable=AsyncMock) as execute:
            result = await cog._execute_decision(message, decision, send_result=True)

        self.assertFalse(result.success)
        self.assertIn("AI moderation is disabled", result.message)
        execute.assert_not_awaited()
        cog.reply_tool_result.assert_awaited_once_with(message, result)

    async def test_routing_history_is_capped_by_guild_context_setting(self) -> None:
        cog = object.__new__(AIModeration)
        bot_user = SimpleNamespace(id=999)
        cog.bot = SimpleNamespace(
            user=bot_user,
            get_context=AsyncMock(return_value=SimpleNamespace(valid=False)),
        )
        cog.config = AIConfig(memory_window=50)
        cog.get_guild_settings = AsyncMock(
            return_value=GuildSettings(enabled=True, context_messages=3),
        )
        cog._message_replies_to_bot = AsyncMock(return_value=False)
        cog.clean_content = lambda message: "show warnings for <@20>"
        cog._looks_like_mod_request = lambda content: True
        cog._looks_like_advanced_action_request = lambda content: False
        cog.extract_mentions = lambda message: SimpleNamespace()
        decision = Decision(type=DecisionType.ERROR, reason="stop")
        cog._quick_route = lambda message, content: decision
        cog._enrich = AsyncMock(return_value=decision)
        cog.fetch_recent_messages = AsyncMock(return_value=[])
        cog.reply = AsyncMock()
        cog._friendly_error_reply = lambda content, reason: reason
        message = SimpleNamespace(
            author=SimpleNamespace(bot=False, id=10),
            guild=SimpleNamespace(id=1),
            mentions=[bot_user],
            reference=None,
            content="<@999> show warnings for <@20>",
            channel=SimpleNamespace(id=30),
        )

        with patch(
            "cogs.aimoderation.aimoderation.is_bot_owner_id",
            return_value=False,
        ):
            await cog.on_message(message)

        cog.fetch_recent_messages.assert_awaited_once_with(message.channel, limit=3)

    async def test_member_prefix_resolution_refuses_ambiguous_targets(self) -> None:
        cog = object.__new__(AIModeration)
        guild = SimpleNamespace(
            members=[
                SimpleNamespace(id=1, name="alex", display_name="Alex"),
                SimpleNamespace(id=2, name="alexander", display_name="Alexander"),
            ],
            get_member=lambda _member_id: None,
        )

        self.assertIsNone(await cog.resolve_member(guild, "ale"))
        resolved = await cog.resolve_member(guild, "alexander")
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.id, 2)

    def test_confirmation_preview_never_exposes_generated_code(self) -> None:
        cog = object.__new__(AIModeration)
        message = SimpleNamespace(
            author=SimpleNamespace(mention="<@1>"),
            channel=SimpleNamespace(mention="<#2>"),
        )
        decision = Decision(
            type=DecisionType.TOOL_CALL,
            reason="advanced action",
            tool=ToolType.EXECUTE_PYTHON,
            arguments={"code": "await guild.delete()"},
        )

        preview = cog._confirmation_preview(message, decision)

        self.assertIn("Owner-only automation", preview)
        self.assertNotIn("guild.delete", preview)

    def test_confirmation_preview_renders_excluded_members_separately(self) -> None:
        cog = object.__new__(AIModeration)
        message = SimpleNamespace(
            author=SimpleNamespace(mention="<@10>"),
            channel=SimpleNamespace(mention="<#2>"),
        )
        decision = Decision(
            type=DecisionType.TOOL_CALL,
            reason="bulk timeout",
            tool=ToolType.TIMEOUT,
            arguments={
                "all_members": True,
                "exclude_user_ids": [10, 20, 30],
                "seconds": 3600,
            },
        )

        preview = cog._confirmation_preview(message, decision)

        self.assertIn("Excluded Members", preview)
        self.assertIn("<@10>, <@20>, <@30>", preview)
        self.assertNotIn("Excluded Role", preview)

    async def test_generated_python_plan_retries_preflight_and_locks_digest(self) -> None:
        cog = object.__new__(AIModeration)
        cog.bot = SimpleNamespace(user=SimpleNamespace(id=999))
        cog.ai = SimpleNamespace(
            prefers_relayrouter=True,
            prefers_aimodel=True,
            _call=AsyncMock(
                side_effect=[
                    (
                        '{"code":"import os\\nreturn os.getcwd()",'
                        '"summary":"Inspect files","scope":"host",'
                        '"expected_effects":["Read files"]}'
                    ),
                    (
                        '{"code":"return f\'Guild {guild.id} has {len(guild.members)} members.\'",'
                        '"summary":"Count server members","scope":"Current guild only",'
                        '"expected_effects":["Read the cached member count"]}'
                    ),
                ]
            )
        )
        guild = SimpleNamespace(
            id=1,
            name="Guild",
            member_count=5,
            members=[SimpleNamespace() for _ in range(5)],
            categories=[],
            channels=[],
            roles=[],
        )
        message = SimpleNamespace(
            guild=guild,
            author=SimpleNamespace(id=10, __str__=lambda self: "Owner"),
            channel=SimpleNamespace(id=20, name="general"),
            mentions=[],
        )

        plan = await cog._generate_execute_python_plan(
            content="count the members",
            message=message,
            settings=GuildSettings(model="claude-opus-4-8"),
        )

        planner_prompt = cog.ai._call.await_args_list[0].args[0][0]["content"]
        self.assertIn("PermissionOverwrite iteration yields", planner_prompt)
        self.assertIn("send_bounded", planner_prompt)
        self.assertIn("never reinterpret public as every channel", planner_prompt)
        self.assertIn("including text, forum, media", planner_prompt)
        self.assertIn("lookback=datetime.timedelta", planner_prompt)
        self.assertIn("guild owner, administrators", planner_prompt)
        self.assertIn("a prose summary alone is not an export", planner_prompt)

        self.assertIsNotNone(plan)
        self.assertEqual(plan["summary"], "Count server members")
        self.assertEqual(len(plan["code_sha256"]), 64)
        self.assertEqual(cog.ai._call.await_count, 2)
        self.assertTrue(
            cog.ai._call.await_args.kwargs["provider_model_override"].endswith("claude-opus-4.8")
        )
        self.assertIsNone(cog.ai._call.await_args.kwargs["model"])
        second_prompt = cog.ai._call.await_args_list[1].args[0][1]["content"]
        self.assertIn("failed preflight", second_prompt)
        self.assertTrue(cog.ai._call.await_args.kwargs["json_mode"])

    async def test_direct_mention_is_not_discarded_when_it_matches_legacy_command(self) -> None:
        cog = object.__new__(AIModeration)
        bot_user = SimpleNamespace(id=999, bot=True)
        cog.bot = SimpleNamespace(
            user=bot_user,
            get_context=AsyncMock(return_value=SimpleNamespace(valid=True)),
        )
        cog.get_guild_settings = AsyncMock(
            return_value=GuildSettings(enabled=False, chat_enabled=False),
        )
        cog._message_replies_to_bot = AsyncMock(return_value=False)
        cog.clean_content = lambda message: "purge the last 50 messages sent by cherry"
        cog._looks_like_mod_request = lambda content: True
        cog._looks_like_advanced_action_request = lambda content: False
        cog.reply = AsyncMock()
        message = SimpleNamespace(
            author=SimpleNamespace(bot=False, id=10),
            guild=SimpleNamespace(id=1),
            mentions=[bot_user],
            reference=None,
            content="<@999> purge the last 50 messages sent by cherry",
            channel=SimpleNamespace(id=30),
        )

        await cog.on_message(message)

        cog.reply.assert_awaited_once()
        self.assertIn("AI moderation is disabled", cog.reply.await_args.kwargs["content"])

    def test_duplicate_suggestion_thread_request_is_advanced_action(self) -> None:
        cog = object.__new__(AIModeration)

        self.assertTrue(
            cog._looks_like_advanced_action_request(
                "find duplicate suggestion threads, keep the oldest, and archive the duplicates"
            )
        )

    def test_purge_parser_preserves_last_message_count(self) -> None:
        cog = object.__new__(AIModeration)

        args = cog._extract_purge_args(
            "purge the last 50 messages sent by <@123456789012345678>"
        )

        self.assertEqual(args["amount"], 50)
        self.assertEqual(args["target_user_id"], 123456789012345678)

    async def test_enrichment_overrides_hallucinated_purge_count_and_target(self) -> None:
        cog = object.__new__(AIModeration)
        bot_user = SimpleNamespace(id=999, bot=True)
        target = SimpleNamespace(id=123456789012345678, bot=False)
        cog.bot = SimpleNamespace(user=bot_user)
        content = "purge the last 50 messages sent by <@123456789012345678>"
        cog.clean_content = lambda message: content
        message = SimpleNamespace(
            content=content,
            mentions=[bot_user, target],
            channel_mentions=[],
            reference=None,
            author=SimpleNamespace(id=10),
            guild=SimpleNamespace(id=1),
        )
        decision = Decision(
            type=DecisionType.TOOL_CALL,
            reason="model route",
            tool=ToolType.PURGE,
            arguments={"amount": "five hundred", "target_user_id": 777},
        )

        enriched = await cog._enrich(message, decision, [])

        self.assertEqual(enriched.arguments["amount"], 50)
        self.assertFalse(enriched.arguments["amount_is_limit"])
        self.assertEqual(enriched.arguments["target_user_id"], target.id)

    async def test_enrichment_preserves_every_explicit_member_target(self) -> None:
        cog = object.__new__(AIModeration)
        bot_user = SimpleNamespace(id=999, bot=True)
        first_target = SimpleNamespace(id=20, bot=False)
        second_target = SimpleNamespace(id=30, bot=False)
        cog.bot = SimpleNamespace(user=bot_user)
        content = "unmute <@20> and <@30>"
        cog.clean_content = lambda message: content
        message = SimpleNamespace(
            content=content,
            mentions=[bot_user, first_target, second_target],
            role_mentions=[],
            channel_mentions=[],
            reference=None,
            author=SimpleNamespace(id=10),
            guild=SimpleNamespace(id=1),
        )
        decision = Decision(
            type=DecisionType.TOOL_CALL,
            reason="model route",
            tool=ToolType.UNTIMEOUT,
            arguments={"target_user_id": 777},
        )

        enriched = await cog._enrich(message, decision, [])

        self.assertEqual(enriched.arguments["target_user_ids"], [20, 30])
        self.assertNotIn("target_user_id", enriched.arguments)

    def test_confirmation_preview_renders_multiple_targets(self) -> None:
        cog = object.__new__(AIModeration)
        message = SimpleNamespace(
            author=SimpleNamespace(mention="<@10>"),
            channel=SimpleNamespace(mention="<#2>"),
        )
        decision = Decision(
            type=DecisionType.TOOL_CALL,
            reason="remove both timeouts",
            tool=ToolType.UNTIMEOUT,
            arguments={"target_user_ids": [20, 30]},
        )

        preview = cog._confirmation_preview(message, decision)

        self.assertIn("Targets", preview)
        self.assertIn("<@20>, <@30>", preview)

    async def test_execute_decision_fans_out_and_reports_partial_failure(self) -> None:
        cog = object.__new__(AIModeration)
        cog.get_guild_settings = AsyncMock(return_value=GuildSettings(enabled=True))
        cog._has_configured_mod_role = lambda author, settings: False
        cog._remember_target = unittest.mock.Mock()
        cog.reply_tool_result = AsyncMock()
        message = SimpleNamespace(
            guild=SimpleNamespace(id=1),
            author=SimpleNamespace(id=10),
        )
        decision = Decision(
            type=DecisionType.TOOL_CALL,
            reason="remove both timeouts",
            tool=ToolType.UNTIMEOUT,
            arguments={"target_user_ids": [20, 30], "reason": "requested"},
        )

        with patch.object(
            ToolRegistry,
            "execute",
            new_callable=AsyncMock,
            side_effect=[ToolResult.ok("first done"), ToolResult.fail("second denied")],
        ) as execute:
            result = await cog._execute_decision(message, decision, send_result=True)

        self.assertTrue(result.success)
        self.assertIn("Completed **1** of **2**", result.message)
        self.assertIn("<@20>", result.message)
        self.assertIn("<@30>: second denied", result.message)
        self.assertEqual(execute.await_count, 2)
        self.assertEqual(execute.await_args_list[0].args[3]["target_user_id"], 20)
        self.assertEqual(execute.await_args_list[1].args[3]["target_user_id"], 30)
        cog._remember_target.assert_called_once_with(1, 10, 20)
        cog.reply_tool_result.assert_awaited_once_with(message, result)

    async def test_bulk_timeout_enrichment_discards_stale_or_hallucinated_target(self) -> None:
        cog = object.__new__(AIModeration)
        bot_user = SimpleNamespace(id=999, bot=True)
        excluded_role = SimpleNamespace(id=55, name="Above all")
        cog.bot = SimpleNamespace(user=bot_user)
        cog.config = AIConfig(timeout_default_seconds=3600)
        content = "mute everyone who doesn't have the role <@&55>"
        cog.clean_content = lambda message: content
        cog._infer_target = AsyncMock(return_value=20)
        message = SimpleNamespace(
            content=content,
            mentions=[bot_user],
            role_mentions=[excluded_role],
            channel_mentions=[],
            reference=None,
            author=SimpleNamespace(id=10),
            guild=SimpleNamespace(id=1),
        )
        decision = Decision(
            type=DecisionType.TOOL_CALL,
            reason="model route",
            tool=ToolType.TIMEOUT,
            arguments={"target_user_id": 20},
        )

        enriched = await cog._enrich(message, decision, [])

        self.assertTrue(enriched.arguments["all_members"])
        self.assertEqual(enriched.arguments["exclude_role_id"], excluded_role.id)
        self.assertNotIn("target_user_id", enriched.arguments)
        cog._infer_target.assert_not_awaited()

    def test_bulk_timeout_always_requires_confirmation(self) -> None:
        cog = object.__new__(AIModeration)
        decision = Decision(
            type=DecisionType.TOOL_CALL,
            reason="bulk timeout",
            tool=ToolType.TIMEOUT,
            arguments={"all_members": True, "seconds": 60},
        )

        self.assertTrue(
            cog._requires_confirmation(
                GuildSettings(confirm_enabled=False, confirm_actions=set()),
                decision,
            )
        )

    async def test_bot_ingress_reserves_direct_mentions_for_ai(self) -> None:
        from bot import ModBot

        fake_bot = SimpleNamespace(
            blacklist_cache=set(),
            owner_ids=set(),
            messages_seen=0,
            _starts_with_bot_mention=lambda message: True,
            get_cog=lambda name: object() if name == "AIModeration" else None,
            get_context=AsyncMock(),
        )
        message = SimpleNamespace(
            author=SimpleNamespace(bot=False, id=10),
            guild=SimpleNamespace(id=1),
            content="<@999> purge the last 50 messages sent by cherry",
        )

        await ModBot.on_message(fake_bot, message)

        self.assertEqual(fake_bot.messages_seen, 1)
        fake_bot.get_context.assert_not_awaited()

    async def test_memory_summarization_uses_digitalocean_flash(self) -> None:
        client = AIClient(
            SimpleNamespace(),
            AIConfig(provider="deepseek-web", model="deepseek-web"),
        )
        client._call_digitalocean = AsyncMock(return_value="- Likes concise replies")

        with patch.dict(
            "os.environ",
            {"DO_MEMORY_MODEL": "deepseek-4-flash"},
        ):
            result = await client._summarize_memory(
                "", "Keep it short", "Understood."
            )

        self.assertEqual(result, "- Likes concise replies")
        client._call_digitalocean.assert_awaited_once()
        self.assertEqual(
            client._call_digitalocean.await_args.kwargs["model"],
            "deepseek-4-flash",
        )

    async def test_conversation_includes_guild_memory_for_standard_chat(self) -> None:
        client = object.__new__(AIClient)
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
            chat=AsyncMock(return_value="server-aware answer"),
        )
        client._collect_image_context = AsyncMock(return_value=[])
        client._update_memory_smart = AsyncMock()
        db = SimpleNamespace(
            get_ai_memory=AsyncMock(return_value="- Likes concise replies"),
            get_guild_memory=AsyncMock(return_value="(Guild) -> Memory\n- Server likes Python help"),
        )
        client.bot = SimpleNamespace(user=SimpleNamespace(id=999), db=db)

        response = await client.converse(
            user_content="what should we work on?",
            guild=SimpleNamespace(id=1, name="Guild", member_count=10),
            author=SimpleNamespace(id=2, name="User"),
            recent_messages=[],
            signals=ConversationSignals(mode=ConversationMode.STANDARD, confidence=1.0),
        )

        self.assertEqual(response, "server-aware answer")
        prompt = client._deepseek_web.chat.await_args.args[0]
        self.assertIn("### MEMORY OF THIS USER ###", prompt)
        self.assertIn("### MEMORY OF THIS SERVER ###", prompt)
        self.assertIn("Server likes Python help", prompt)
        db.get_guild_memory.assert_awaited_once_with(1)

    async def test_conversation_uses_galaxy_before_browser_when_configured(self) -> None:
        client = object.__new__(AIClient)
        client.provider = "deepseek"
        client.config = AIConfig(provider="deepseek")
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
            chat=AsyncMock(return_value="browser answer"),
        )
        client._call_deepseek_api = AsyncMock(return_value="galaxy answer")
        client._collect_image_context = AsyncMock(return_value=[])
        client._update_memory_smart = AsyncMock()
        client.bot = SimpleNamespace(
            user=SimpleNamespace(id=999),
            db=SimpleNamespace(
                get_ai_memory=AsyncMock(return_value=""),
                get_guild_memory=AsyncMock(return_value=""),
            ),
        )

        with patch(
            "cogs.aimoderation.ai_client._deepseek_api_enabled",
            return_value=True,
        ):
            response = await client.converse(
                user_content="hello there",
                guild=SimpleNamespace(id=1, name="Guild", member_count=10),
                author=SimpleNamespace(id=2, name="User"),
                recent_messages=[],
                signals=ConversationSignals(
                    mode=ConversationMode.STANDARD,
                    confidence=1.0,
                ),
            )

        self.assertEqual(response, "galaxy answer")
        client._call_deepseek_api.assert_awaited_once()
        client._deepseek_web.chat.assert_not_awaited()
        messages = client._call_deepseek_api.await_args.args[0]
        self.assertEqual(messages[0]["role"], "system")
        self.assertGreater(len(messages[0]["content"]), 1_024)
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("### CURRENT USER MESSAGE ###", messages[1]["content"])
        self.assertIn("hello there", messages[1]["content"])

    def test_conversation_history_budget_keeps_the_newest_messages(self) -> None:
        client = object.__new__(AIClient)
        client.config = AIConfig(memory_window=200, context_char_budget=4_000)
        client.bot = SimpleNamespace(user=SimpleNamespace(id=999))

        messages = []
        for index in range(10):
            author = SimpleNamespace(
                id=index + 1,
                bot=False,
                display_name=f"User {index}",
            )
            messages.append(
                SimpleNamespace(
                    author=author,
                    content=f"marker-{index} " + ("x" * 900),
                    attachments=[],
                    embeds=[],
                    stickers=[],
                    message_snapshots=[],
                    reference=None,
                )
            )

        history = client._format_conversation_history(messages)

        self.assertIn("marker-9", history)
        self.assertNotIn("marker-0", history)
        self.assertIn("earlier message(s) omitted", history)

    async def test_research_does_not_feed_saved_memory_or_continue_chat(self) -> None:
        client = object.__new__(AIClient)
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
            chat=AsyncMock(
                side_effect=[
                    (
                        "searched material\n\n__BOT_SOURCES__\n"
                        "- <https://example.com/source>"
                    ),
                    "deepthink researched answer",
                ]
            ),
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
            use_deepthink=True,
        )

        response = await client.converse(
            user_content="research this",
            guild=guild,
            author=author,
            recent_messages=[],
            signals=signals,
        )

        self.assertIn("researched answer", response)
        self.assertIn("https://example.com/source", response)
        self.assertEqual(client._deepseek_web.chat.await_count, 2)
        search_call, deepthink_call = client._deepseek_web.chat.await_args_list
        prompt = search_call.args[0]
        self.assertNotIn("PRIVATE MEMORY", prompt)
        self.assertNotIn("### MEMORY OF THIS SERVER ###", prompt)
        self.assertFalse(search_call.kwargs["continue_session"])
        self.assertTrue(search_call.kwargs["search"])
        self.assertFalse(search_call.kwargs["deepthink"])
        self.assertTrue(deepthink_call.kwargs["continue_session"])
        self.assertFalse(deepthink_call.kwargs["search"])
        self.assertTrue(deepthink_call.kwargs["deepthink"])
        self.assertIn("VERIFIED SEARCH MATERIAL", deepthink_call.args[0])
        self.assertIn("current UTC time", deepthink_call.args[0])
        client._update_memory_smart.assert_called_once_with(
            author.id,
            "research this",
            response,
            "PRIVATE MEMORY",
        )

    async def test_galaxy_research_uses_sourced_browser_search_not_plain_http(self) -> None:
        client = object.__new__(AIClient)
        client.provider = "deepseek"
        client.config = AIConfig(provider="deepseek")
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
            chat=AsyncMock(
                side_effect=[
                    (
                        "verified news\n\n__BOT_SOURCES__\n"
                        "- <https://example.com/news>"
                    ),
                    "deepthink final news",
                ]
            ),
        )
        client._call_deepseek_api = AsyncMock(return_value="unsourced API answer")
        client._collect_image_context = AsyncMock(return_value=[])
        client._update_memory_smart = AsyncMock()
        client.bot = SimpleNamespace(
            user=SimpleNamespace(id=999),
            db=SimpleNamespace(
                get_ai_memory=AsyncMock(return_value=""),
                get_guild_memory=AsyncMock(return_value=""),
            ),
        )

        with patch(
            "cogs.aimoderation.ai_client._deepseek_api_enabled",
            return_value=True,
        ):
            response = await client.converse(
                user_content="research world news",
                guild=SimpleNamespace(id=1, name="Guild", member_count=10),
                author=SimpleNamespace(id=2, name="User"),
                recent_messages=[],
                signals=ConversationSignals(
                    mode=ConversationMode.RESEARCH,
                    confidence=1.0,
                    show_research_indicator=True,
                    use_deepthink=True,
                ),
            )

        self.assertIn("https://example.com/news", response)
        self.assertIn("deepthink final news", response)
        client._call_deepseek_api.assert_not_awaited()
        self.assertEqual(client._deepseek_web.chat.await_count, 2)
        search_call, deepthink_call = client._deepseek_web.chat.await_args_list
        self.assertTrue(search_call.kwargs["search"])
        self.assertFalse(search_call.kwargs["deepthink"])
        self.assertFalse(deepthink_call.kwargs["search"])
        self.assertTrue(deepthink_call.kwargs["deepthink"])

    async def test_search_only_research_skips_deepthink_pass(self) -> None:
        client = object.__new__(AIClient)
        client.provider = "deepseek"
        client.config = AIConfig(provider="deepseek")
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
            chat=AsyncMock(
                return_value=(
                    "Version 6.7 is current.\n\n__BOT_SOURCES__\n"
                    "- <https://example.com/genshin>"
                )
            ),
        )
        client._collect_image_context = AsyncMock(return_value=[])
        client._update_memory_smart = AsyncMock()
        client.bot = SimpleNamespace(
            user=SimpleNamespace(id=999),
            db=SimpleNamespace(
                get_ai_memory=AsyncMock(return_value=""),
                get_guild_memory=AsyncMock(return_value=""),
            ),
        )

        response = await client.converse(
            user_content="latest genshin update?",
            guild=SimpleNamespace(id=1, name="Guild", member_count=10),
            author=SimpleNamespace(id=2, name="User"),
            recent_messages=[],
            signals=ConversationSignals(
                mode=ConversationMode.RESEARCH,
                confidence=1.0,
                show_research_indicator=True,
                asks_for_current_info=True,
                use_deepthink=False,
            ),
        )

        self.assertIn("Version 6.7", response)
        client._deepseek_web.chat.assert_awaited_once()
        call = client._deepseek_web.chat.await_args
        self.assertTrue(call.kwargs["search"])
        self.assertFalse(call.kwargs["deepthink"])

    async def test_unsourced_research_is_rejected(self) -> None:
        client = object.__new__(AIClient)
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
            chat=AsyncMock(return_value="plausible but unsourced news"),
        )
        client._collect_image_context = AsyncMock(return_value=[])
        client._update_memory_smart = AsyncMock()
        client.bot = SimpleNamespace(
            user=SimpleNamespace(id=999),
            db=SimpleNamespace(
                get_ai_memory=AsyncMock(return_value=""),
                get_guild_memory=AsyncMock(return_value=""),
            ),
        )

        response = await client.converse(
            user_content="research world news",
            guild=SimpleNamespace(id=1, name="Guild", member_count=10),
            author=SimpleNamespace(id=2, name="User"),
            recent_messages=[],
            signals=ConversationSignals(
                mode=ConversationMode.RESEARCH,
                confidence=1.0,
                show_research_indicator=True,
            ),
        )

        self.assertIn("no verifiable source links", response)
        client._update_memory_smart.assert_not_called()

    async def test_conversation_falls_back_to_digitalocean_when_deepseek_web_fails(self) -> None:
        client = object.__new__(AIClient)
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
        client._conversation_via_http = AsyncMock(return_value="fallback answer")
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
        client._conversation_via_http.assert_awaited_once()
        client._update_memory_smart.assert_called_once()

    async def test_database_guild_memory_crud_and_channel_batch_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"DB_MODE": "sqlite", "DATABASE_URL": ""}):
                db = Database()
                db.db_path = str(Path(tmpdir) / "modbot-test.db")
                db._supabase_mirror.enabled = False

                try:
                    await db.init_guild(123)
                    await db.update_guild_memory(123, "Guild Name", "(Guild Name) -> Memory\n- Likes tests")

                    self.assertEqual(
                        await db.get_guild_memory(123),
                        "(Guild Name) -> Memory\n- Likes tests",
                    )
                    record = await db.get_guild_memory_record(123)
                    self.assertIsNotNone(record)
                    self.assertEqual(record["guild_id"], 123)
                    self.assertEqual(record["guild_name"], "Guild Name")

                    async with db.get_connection() as conn:
                        await conn.execute(
                            """
                            INSERT INTO user_messages (message_id, guild_id, channel_id, user_id, content, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (1, 123, 999, 11, "old", "2026-07-07T00:00:01+00:00"),
                        )
                        await conn.execute(
                            """
                            INSERT INTO user_messages (message_id, guild_id, channel_id, user_id, content, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (2, 123, 999, 11, "middle", "2026-07-07T00:00:02+00:00"),
                        )
                        await conn.execute(
                            """
                            INSERT INTO user_messages (message_id, guild_id, channel_id, user_id, content, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (3, 123, 999, 12, "new", "2026-07-07T00:00:03+00:00"),
                        )
                        await conn.execute(
                            """
                            INSERT INTO user_messages (message_id, guild_id, channel_id, user_id, content, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (4, 123, 1000, 13, "other channel", "2026-07-07T00:00:04+00:00"),
                        )
                        await conn.commit()

                    rows = await db.get_recent_channel_messages(999, limit=2)
                    self.assertEqual([row["message_id"] for row in rows], [2, 3])
                    self.assertEqual([row["content"] for row in rows], ["middle", "new"])

                    user_rows = await db.get_recent_user_messages(123, 11, limit=2)
                    self.assertEqual(
                        [row["message_id"] for row in user_rows], [1, 2]
                    )
                    self.assertEqual(
                        [row["content"] for row in user_rows], ["old", "middle"]
                    )

                    self.assertTrue(await db.clear_guild_memory(123))
                    self.assertIsNone(await db.get_guild_memory(123))
                finally:
                    await db.close()

    async def test_notification_migration_enables_existing_servers_without_resetting_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"DB_MODE": "sqlite", "DATABASE_URL": ""}):
                db = Database()
                db.db_path = str(Path(tmpdir) / "notification-migration.db")
                db._supabase_mirror.enabled = False

                try:
                    await db.init_guild(456)
                    async with db.get_connection() as conn:
                        await conn.execute(
                            "UPDATE guild_settings SET settings = ? WHERE guild_id = ?",
                            ('{"prefix":"!","moderation_dm_users":false,"automod_notify_users":false}', 456),
                        )
                        await conn.execute(
                            "DELETE FROM dashboard_schema_migrations WHERE key = ?",
                            ("20260718_punishment_notifications_on",),
                        )
                        await conn.commit()
                        await db._migrate_schema(conn)
                        await conn.commit()

                    settings = await db.get_settings(456)
                    self.assertEqual(settings["prefix"], "!")
                    self.assertIs(settings["moderation_dm_users"], True)
                    self.assertIs(settings["automod_notify_users"], True)
                    self.assertIs(settings["appeals_enabled"], True)
                    self.assertIs(settings["appeals_open"], True)
                finally:
                    await db.close()

    async def test_conversation_falls_back_to_digitalocean_when_deepseek_web_stalls(self) -> None:
        async def stalled_chat(*args, **kwargs):
            await asyncio.sleep(1)
            return "late answer"

        client = object.__new__(AIClient)
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
            chat=AsyncMock(side_effect=stalled_chat),
        )
        client._conversation_via_http = AsyncMock(return_value="fallback answer")
        client._collect_image_context = AsyncMock(return_value=[])
        client._update_memory_smart = AsyncMock()
        db = SimpleNamespace(get_ai_memory=AsyncMock(return_value=""))
        client.bot = SimpleNamespace(user=SimpleNamespace(id=999), db=db)

        with patch.dict("os.environ", {"DEEPSEEK_WEB_PRIMARY_TIMEOUT": "0.1"}):
            response = await client.converse(
                user_content="hello",
                guild=SimpleNamespace(id=1, name="Guild", member_count=10),
                author=SimpleNamespace(id=2, name="User"),
                recent_messages=[],
                signals=ConversationSignals(mode=ConversationMode.STANDARD, confidence=1.0),
            )

        self.assertEqual(response, "fallback answer")
        client._conversation_via_http.assert_awaited_once()
        client._update_memory_smart.assert_called_once()

    async def test_relayrouter_inspects_images_without_deepseek_vision(self) -> None:
        client = object.__new__(AIClient)
        client.provider = "relayrouter"
        client.config = AIConfig(provider="relayrouter", model="gpt-5-6-terra")
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
            chat=AsyncMock(return_value="browser chat"),
            vision=AsyncMock(return_value="browser vision"),
        )
        client._call_relayrouter = AsyncMock(return_value="The image is red.")
        client._collect_image_context = AsyncMock(
            return_value=[
                ImageContext(
                    label="attached image",
                    filename="pixel.png",
                    mime_type="image/png",
                    data=b"pixel",
                )
            ]
        )
        client._update_memory_smart = AsyncMock()
        client.bot = SimpleNamespace(
            user=SimpleNamespace(id=999),
            db=SimpleNamespace(get_ai_memory=AsyncMock(return_value="")),
        )

        with patch(
            "cogs.aimoderation.ai_client._RELAYROUTER_API_KEY",
            "relay-test-key",
        ), patch(
            "cogs.aimoderation.ai_client._RELAYROUTER_VISION_MODEL",
            "vision-model",
        ):
            response = await client.converse(
                user_content="what is in this image?",
                guild=SimpleNamespace(id=1, name="Guild", member_count=10),
                author=SimpleNamespace(id=2, name="User"),
                recent_messages=[],
                signals=ConversationSignals(
                    mode=ConversationMode.STANDARD,
                    confidence=1.0,
                ),
            )

        self.assertEqual(response, "The image is red.")
        kwargs = client._call_relayrouter.await_args.kwargs
        self.assertEqual(kwargs["model"], "vision-model")
        self.assertTrue(kwargs["allow_multimodal"])
        client._deepseek_web.vision.assert_not_awaited()

    async def test_relayrouter_vision_failure_falls_back_to_deepseek_vision(self) -> None:
        client = object.__new__(AIClient)
        client.provider = "relayrouter"
        client.config = AIConfig(provider="relayrouter", model="gpt-5-6-terra")
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
            chat=AsyncMock(return_value="browser chat"),
            vision=AsyncMock(return_value="Tynamo"),
        )
        client._call_relayrouter = AsyncMock(side_effect=RuntimeError("vision routes down"))
        client._collect_image_context = AsyncMock(
            return_value=[
                ImageContext(
                    label="forwarded image",
                    filename="pokemon.png",
                    mime_type="image/png",
                    data=b"pixel",
                )
            ]
        )
        client._update_memory_smart = AsyncMock()
        client.bot = SimpleNamespace(
            user=SimpleNamespace(id=999),
            db=SimpleNamespace(get_ai_memory=AsyncMock(return_value="")),
        )

        with patch(
            "cogs.aimoderation.ai_client._RELAYROUTER_API_KEY",
            "relay-test-key",
        ):
            response = await client.converse(
                user_content="who is this?",
                guild=SimpleNamespace(id=1, name="Guild", member_count=10),
                author=SimpleNamespace(id=2, name="User"),
                recent_messages=[],
                signals=ConversationSignals(
                    mode=ConversationMode.STANDARD,
                    confidence=1.0,
                ),
            )

        self.assertEqual(response, "Tynamo")
        client._deepseek_web.vision.assert_awaited_once()
        uploads = client._deepseek_web.vision.await_args.args[1]
        self.assertEqual(uploads, [("pokemon.png", "image/png", b"pixel")])

    async def test_relayrouter_vision_missing_image_reply_uses_deepseek_fallback(self) -> None:
        client = object.__new__(AIClient)
        client.provider = "relayrouter"
        client.config = AIConfig(provider="relayrouter", model="gpt-5-6-terra")
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
            chat=AsyncMock(return_value="browser chat"),
            vision=AsyncMock(return_value="Tynamo"),
        )
        client._call_relayrouter = AsyncMock(return_value="Please upload the screenshot.")
        client._collect_image_context = AsyncMock(
            return_value=[
                ImageContext(
                    label="forwarded image",
                    filename="pokemon.png",
                    mime_type="image/png",
                    data=b"pixel",
                )
            ]
        )
        client._update_memory_smart = AsyncMock()
        client.bot = SimpleNamespace(
            user=SimpleNamespace(id=999),
            db=SimpleNamespace(get_ai_memory=AsyncMock(return_value="")),
        )

        with patch(
            "cogs.aimoderation.ai_client._RELAYROUTER_API_KEY",
            "relay-test-key",
        ):
            response = await client.converse(
                user_content="who is this?",
                guild=SimpleNamespace(id=1, name="Guild", member_count=10),
                author=SimpleNamespace(id=2, name="User"),
                recent_messages=[],
                signals=ConversationSignals(
                    mode=ConversationMode.STANDARD,
                    confidence=1.0,
                ),
            )

        self.assertEqual(response, "Tynamo")
        client._deepseek_web.vision.assert_awaited_once()

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

    async def test_reason_rejects_model_meta_commentary(self) -> None:
        cog = object.__new__(AIModeration)
        cog.ai = SimpleNamespace(
            is_available=True,
            _call=AsyncMock(
                return_value=(
                    "The user wants me to rewrite a Discord moderation reason as a "
                    "concise sentence fragment. Let me analyze the original reason."
                )
            ),
        )
        decision = Decision(
            type=DecisionType.TOOL_CALL,
            reason="rule: timeout",
            tool=ToolType.TIMEOUT,
            arguments={"target_user_id": 123, "reason": "repeated spam"},
        )

        result = await cog._polish_decision_reason(decision, GuildSettings())

        self.assertEqual(result.arguments["reason"], "repeated spam")

    def test_anyone_who_isnt_a_bot_is_bulk_timeout(self) -> None:
        cog = object.__new__(AIModeration)
        bot_user = SimpleNamespace(id=999, bot=True)
        cog.bot = SimpleNamespace(user=bot_user)
        message = SimpleNamespace(
            author=SimpleNamespace(id=10, mention="<@10>"),
            mentions=[bot_user],
            role_mentions=[],
            channel=SimpleNamespace(mention="<#20>"),
        )

        decision = cog._quick_route(message, "mute anyone who isnt a bot for 1m")

        self.assertIsNotNone(decision)
        self.assertEqual(decision.tool, ToolType.TIMEOUT)
        self.assertEqual(decision.arguments["seconds"], 60)
        self.assertIs(decision.arguments["all_members"], True)
        self.assertNotIn("target_user_id", decision.arguments)
        self.assertNotIn("reason", decision.arguments)
        self.assertIsNone(cog._decision_scope_error(decision))
        preview = cog._confirmation_preview(message, decision)
        self.assertIn("All eligible non-bot server members", preview)

    def test_targeted_action_without_target_is_rejected_before_confirmation(self) -> None:
        decision = Decision(
            type=DecisionType.TOOL_CALL,
            reason="rule: timeout",
            tool=ToolType.TIMEOUT,
            arguments={"seconds": 60},
        )

        error = AIModeration._decision_scope_error(decision)

        self.assertIsNotNone(error)
        self.assertIn("couldn't determine which member", error)

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
