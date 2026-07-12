import ast
import asyncio
import collections
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from cogs.moderation import Moderation


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
        assert all(
            isinstance(command, app_commands.Group) or callable(command.callback)
            for command in cog._slash_commands
        )
    finally:
        asyncio.run(bot.close())


def test_modmail_is_not_exposed_by_bot_or_cogs() -> None:
    exposed = []
    for path in [ROOT / "bot.py", *COGS.rglob("*.py")]:
        if "modmail" in path.read_text(encoding="utf-8-sig").lower():
            exposed.append(str(path.relative_to(ROOT)))
    assert not exposed, f"ModMail remains exposed in runtime code: {exposed}"
