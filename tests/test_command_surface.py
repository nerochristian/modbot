import ast
import asyncio
import collections
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from cogs.moderation import Moderation
from cogs.admin import Admin
from cogs.aimoderation.aimoderation import AIModeration
from cogs.court import Court
from cogs.roles import Roles
from cogs.tickets import Tickets
from cogs.setup import Setup
from cogs.utility import Utility


ROOT = Path(__file__).resolve().parent.parent
COGS = ROOT / "cogs"
REQUIRED_MODERATION_SLASH = {"ban", "kick", "mute", "timeout", "warn"}


def test_cog_classes_do_not_override_command_lifecycle_methods() -> None:
    duplicates: list[str] = []
    for path in COGS.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for class_node in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            names = collections.Counter(
                node.name
                for node in class_node.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
            for name, count in names.items():
                if count > 1:
                    duplicates.append(f"{path.relative_to(ROOT)}:{class_node.name}.{name}")

    assert not duplicates, f"duplicate class methods override command code: {duplicates}"


def test_moderation_registers_required_slash_commands() -> None:
    async def register() -> tuple[commands.Bot, Moderation]:
        bot = commands.Bot(command_prefix=",", intents=discord.Intents.none())
        cog = Moderation(bot)
        await cog._register_top_level_commands()
        return bot, cog

    bot, cog = asyncio.run(register())
    try:
        registered = {command.name for command in bot.tree.get_commands()}
        assert REQUIRED_MODERATION_SLASH <= registered
        assert "cleanup" in registered
        assert {command.name for command in bot.tree.get_command("cleanup").commands} == {
            "bots",
            "contains",
            "embeds",
            "images",
            "links",
        }
        assert {command.name for command in bot.tree.get_command("welcome").commands} == {
            "background", "preview", "everyone",
        }
        assert {command.name for command in bot.tree.get_command("emoji").commands} == {
            "tutorial", "add", "steal",
        }
        assert not {"setwelcomebg", "testwelcome", "welcomeall", "emojitutorial", "addemoji", "stealemoji"} & registered
        assert all(
            isinstance(command, app_commands.Group) or callable(command.callback)
            for command in cog._slash_commands
        )
    finally:
        asyncio.run(bot.close())


def test_low_frequency_features_use_groups_instead_of_root_command_slots() -> None:
    court_commands = {command.name: command for command in Court.__cog_app_commands__}
    assert set(court_commands) == {"court"}
    assert {command.name for command in court_commands["court"].commands} == {
        "setup-logs", "file", "evidence", "jury", "verdict", "view-evidence", "close",
    }

    ticket_commands = {command.name: command for command in Tickets.__cog_app_commands__}
    assert "ticket" in ticket_commands
    assert "ticketpanel" not in ticket_commands
    assert "panel" in {command.name for command in ticket_commands["ticket"].commands}


def test_removed_admin_and_spam_commands_are_not_slash_commands() -> None:
    removed = {"neutralize", "modrole", "adminrole", "ignore", "announce", "reset", "spam", "stopspam"}
    assert not removed & {command.name for command in Admin.__cog_app_commands__}


def test_guides_are_grouped_without_legacy_roots() -> None:
    ai_commands = {command.name: command for command in AIModeration.__cog_app_commands__}
    assert "aihelp" not in ai_commands
    assert "help" in {command.name for command in ai_commands["ai"].commands}

    setup_commands = {command.name: command for command in Setup.__cog_app_commands__}
    assert "staffupdates" not in setup_commands
    assert {command.name for command in setup_commands["guide"].commands} == {
        "moderation", "staff", "updates",
    }


def test_modmail_is_not_exposed_by_bot_or_cogs() -> None:
    exposed = []
    for path in [ROOT / "bot.py", *COGS.rglob("*.py")]:
        if "modmail" in path.read_text(encoding="utf-8-sig").lower():
            exposed.append(str(path.relative_to(ROOT)))
    assert not exposed, f"ModMail remains exposed in runtime code: {exposed}"


def test_role_actions_expose_only_their_relevant_parameters() -> None:
    commands_by_name = {command.name: command for command in Roles.__cog_app_commands__}
    assert {
        "info", "create", "delete", "add", "remove", "addall", "removeall",
        "auto",
    } == commands_by_name.keys()
    assert [parameter.name for parameter in commands_by_name["auto"].parameters] == ["role"]
    assert [parameter.name for parameter in commands_by_name["add"].parameters] == ["user", "role", "reason"]
    assert [parameter.name for parameter in commands_by_name["create"].parameters] == [
        "name", "color", "hoist", "mentionable", "position", "reason",
    ]
    assert [parameter.name for parameter in commands_by_name["removeall"].parameters] == ["role", "reason"]


def test_nuke_deletes_original_before_best_effort_reposition() -> None:
    source = (COGS / "moderation" / "extensions" / "chat.py").read_text(encoding="utf-8-sig")
    function = source[source.index("    async def _nuke_logic"):source.index("    async def _glock_logic")]
    assert function.index("await channel.delete") < function.index("await new_channel.edit")


def test_dashboard_is_a_top_level_slash_command() -> None:
    command = Utility.dashboard
    assert isinstance(command, app_commands.Command)
    assert command.name == "dashboard"
    assert command.parameters == []


def test_server_info_uses_compact_v1_embed() -> None:
    source = (COGS / "utility.py").read_text(encoding="utf-8-sig")
    function = source[source.index("    async def server("):source.index("    # ==================== RULE34 SEARCH")]

    assert "embed.set_author(" in function
    assert "name=guild.name" in function
    assert "use_v2=False" in function
    assert "possessive_name" not in function


def test_universal_v2_shim_consumes_explicit_v1_override() -> None:
    source = (ROOT / "gc" / "components_v2.py").read_text(encoding="utf-8-sig")
    function = source[source.index("def _normalize_v2_payload("):source.index("\ndef _patch_async_method(")]

    assert 'kwargs.pop("use_v2", None)' in function
    assert "use_v2 is False" in function
    assert "return args, kwargs" in function
    assert "await _apply_shared_status_emojis(self, kwargs)" in source


def test_server_is_a_top_level_slash_command() -> None:
    command = Utility.server
    assert isinstance(command, app_commands.Command)
    assert command.name == "server"
    assert command.parameters == []
    assert "server" not in {command.name for command in Utility.utility_group.commands}
