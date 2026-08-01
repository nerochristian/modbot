"""Structural security regression tests for the moderation command suite.

These do not spin up Discord; they statically assert an invariant that is easy
to break by accident: every destructive action helper in ``management.py`` must
run the actor-authorization check (``can_moderate``) before acting.

Background: ``_unmute_logic`` and ``_unquarantine_logic`` (the "undo" pair) once
lacked this check, so any member could invoke the ``/unmute`` and ``/untimeout``
/ ``/unquarantine`` slash commands to reverse a moderator's action. The slash
commands are registered dynamically without decorators, so the ONLY actor gate
lives inside these ``_logic`` methods — if the call is missing, the command is
open to everyone. This test fails if that ever regresses.
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord

from cogs.moderation.extensions.management import ManagementCommands
from cogs.moderation.extensions.misc import MiscCommands
from cogs.moderation.extensions.warnings import WarningCommands

MANAGEMENT = (
    pathlib.Path(__file__).resolve().parent.parent
    / "cogs" / "moderation" / "extensions" / "management.py"
)

# Every helper here performs (or reverses) a moderation action on a member and
# is reachable from an undecorated slash command, so each MUST call
# ``can_moderate`` to authorize the invoking user.
DESTRUCTIVE_LOGIC_METHODS = {
    "_kick_logic",
    "_ban_logic",
    "_tempban_logic",
    "_softban_logic",
    "_mute_logic",
    "_unmute_logic",
    "_quarantine_logic",
    "_unquarantine_logic",
}


def _method_nodes():
    tree = ast.parse(MANAGEMENT.read_text(encoding="utf-8"))
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
    }


def _calls_can_moderate(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute) and sub.attr == "can_moderate":
            return True
    return False


def test_all_destructive_logic_methods_authorize_actor():
    methods = _method_nodes()
    missing_defs = DESTRUCTIVE_LOGIC_METHODS - methods.keys()
    assert not missing_defs, f"expected methods not found (renamed?): {missing_defs}"

    unguarded = {
        name
        for name in DESTRUCTIVE_LOGIC_METHODS
        if not _calls_can_moderate(methods[name])
    }
    assert not unguarded, (
        "these moderation helpers do not call can_moderate() and are reachable "
        f"from undecorated slash commands (permission hole): {sorted(unguarded)}"
    )


def test_prefix_moderation_commands_have_real_command_checks():
    for command in (
        WarningCommands.mod_warn,
        WarningCommands.mod_warnings,
        WarningCommands.mod_delwarn,
        WarningCommands.mod_clearwarnings,
        ManagementCommands.kick_prefix,
        ManagementCommands.ban_prefix,
        ManagementCommands.mute_prefix,
    ):
        assert command.checks, f"{command.qualified_name} has no prefix authorization check"


def test_dynamic_slash_registration_attaches_permission_checks():
    moderation_init = MANAGEMENT.parent.parent / "__init__.py"
    source = moderation_init.read_text(encoding="utf-8")
    assert "command.add_check(checks[access])" in source
    assert "cleanup_command.add_check(moderator_predicate)" in source


class BanFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_forbidden_ban_does_not_create_case_or_send_punishment_dm(self):
        cog = object.__new__(ManagementCommands)
        cog.bot = SimpleNamespace(
            db=SimpleNamespace(
                get_settings=AsyncMock(return_value={"moderation_dm_users": True}),
                create_case=AsyncMock(),
            )
        )
        cog.can_moderate = AsyncMock(return_value=(True, ""))
        cog.can_bot_moderate = AsyncMock(return_value=(True, ""))
        cog.prepare_dm_channel = AsyncMock(return_value=SimpleNamespace())
        cog.send_punishment_notice = AsyncMock()
        cog._respond = AsyncMock()
        cog._suppress_duplicate_member_action_log = Mock()

        bot_role = SimpleNamespace(mention="<@&10>")
        guild = SimpleNamespace(
            id=1,
            name="Guild",
            me=SimpleNamespace(
                top_role=bot_role,
                guild_permissions=SimpleNamespace(ban_members=True),
            ),
        )
        moderator = SimpleNamespace(id=2)
        source = SimpleNamespace(guild=guild, author=moderator)
        response = SimpleNamespace(status=403, reason="Forbidden")
        target = SimpleNamespace(
            id=3,
            mention="<@3>",
            top_role=SimpleNamespace(mention="<@&30>"),
            ban=AsyncMock(
                side_effect=discord.Forbidden(
                    response,
                    {"code": 50013, "message": "Missing Permissions"},
                )
            ),
        )

        await cog._ban_logic(source, target, "No reason")

        cog.bot.db.create_case.assert_not_awaited()
        cog.send_punishment_notice.assert_not_awaited()
        error_embed = cog._respond.await_args.kwargs["embed"]
        self.assertIn("I don't have permission to ban", error_embed.description)
        self.assertIn("move it above", error_embed.description)


class WelcomeCommandPermissionTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _ordinary_member_interaction():
        return SimpleNamespace(
            guild=SimpleNamespace(id=123456789012345678),
            user=SimpleNamespace(
                id=234567890123456789,
                guild_permissions=SimpleNamespace(manage_guild=False),
            ),
            channel=SimpleNamespace(),
            response=SimpleNamespace(send_message=AsyncMock()),
        )

    def _commands(self):
        commands = object.__new__(MiscCommands)
        commands._send_welcome_message = AsyncMock()
        commands.bot = SimpleNamespace(
            db=SimpleNamespace(get_settings=AsyncMock()),
        )
        return commands

    def assert_manage_server_rejection(self, interaction):
        interaction.response.send_message.assert_awaited_once()
        kwargs = interaction.response.send_message.await_args.kwargs
        self.assertTrue(kwargs["ephemeral"])
        self.assertIn("Missing Permissions", kwargs["embed"].description)
        self.assertIn("Manage Server", kwargs["embed"].description)

    async def test_ordinary_member_cannot_preview_welcome_card(self):
        commands = self._commands()
        interaction = self._ordinary_member_interaction()

        await commands.testwelcome(interaction)

        self.assert_manage_server_rejection(interaction)
        commands._send_welcome_message.assert_not_awaited()
        commands.bot.db.get_settings.assert_not_awaited()

    async def test_ordinary_member_cannot_welcome_all_members(self):
        commands = self._commands()
        interaction = self._ordinary_member_interaction()

        await commands.welcomeall(interaction, confirm=True)

        self.assert_manage_server_rejection(interaction)
        commands._send_welcome_message.assert_not_awaited()
        commands.bot.db.get_settings.assert_not_awaited()
