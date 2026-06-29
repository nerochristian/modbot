"""Guild-level handlers — edit guild, create/delete emoji, create invite, help."""
from __future__ import annotations

from typing import Dict

import aiohttp
import discord

from ..context import ToolContext, ToolResult, _now
from ..registry import ToolRegistry
from ..types import ToolType


@ToolRegistry.register(
    ToolType.EDIT_GUILD,
    display_name="Edit Server",
    color=discord.Color.gold(),
    emoji="Server",
    required_permission="manage_guild",
    category="guild",
)
async def handle_edit_guild(ctx: ToolContext) -> ToolResult:
    kwargs: Dict[str, str] = {}
    if "name" in ctx.args:
        kwargs["name"] = ctx.args["name"]
    if not kwargs:
        return ToolResult.fail("Nothing to edit.")
    await ctx.guild.edit(**kwargs, reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok("Server settings updated.")


@ToolRegistry.register(
    ToolType.CREATE_EMOJI,
    display_name="Create Emoji",
    color=discord.Color.green(),
    emoji="Emoji",
    required_permission="manage_emojis",
    category="guild",
)
async def handle_create_emoji(ctx: ToolContext) -> ToolResult:
    name = ctx.arg("name")
    url = ctx.arg("url")
    if not name or not url:
        return ToolResult.fail("Both emoji name and image URL are required.")

    session: aiohttp.ClientSession | None = getattr(ctx.cog.bot, "session", None)
    owned_session = False
    if not session or getattr(session, "closed", False):
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))
        owned_session = True

    try:
        async with session.get(str(url)) as resp:
            if resp.status != 200:
                return ToolResult.fail(f"Failed to download image (HTTP {resp.status}).")
            data = await resp.read()
        emoji = await ctx.guild.create_custom_emoji(name=str(name), image=data, reason=f"AI Mod ({ctx.actor})")
        embed = discord.Embed(description=f"Created emoji {emoji}", color=discord.Color.green())
        return ToolResult.ok("Emoji created.", embed=embed)
    finally:
        if owned_session:
            await session.close()


@ToolRegistry.register(
    ToolType.DELETE_EMOJI,
    display_name="Delete Emoji",
    color=discord.Color.red(),
    emoji="Delete",
    required_permission="manage_emojis",
    category="guild",
)
async def handle_delete_emoji(ctx: ToolContext) -> ToolResult:
    name = ctx.arg("name")
    if not name:
        return ToolResult.fail("Emoji name is required.")
    emoji = discord.utils.find(lambda e: e.name.lower() == str(name).lower(), ctx.guild.emojis)
    if not emoji:
        return ToolResult.fail(f"Emoji `{name}` not found.")
    await emoji.delete(reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok(f"Emoji `{name}` deleted.")


@ToolRegistry.register(
    ToolType.CREATE_INVITE,
    display_name="Create Invite",
    color=discord.Color.green(),
    emoji="Invite",
    required_permission="create_instant_invite",
    category="guild",
)
async def handle_create_invite(ctx: ToolContext) -> ToolResult:
    max_age = max(0, min(ctx.int_arg("max_age", 86400), 604800))
    create_invite = getattr(ctx.message.channel, "create_invite", None)
    if not callable(create_invite):
        return ToolResult.fail("I can't create an invite from this channel type.")
    invite = await create_invite(max_age=max_age, reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok(f"Invite created: {invite.url}")


@ToolRegistry.register(
    ToolType.HELP,
    display_name="Show Help",
    color=discord.Color.blurple(),
    emoji="?",
    category="guild",
)
async def handle_help(ctx: ToolContext) -> ToolResult:
    embed = ctx.cog.build_help_embed(ctx.guild)
    return ToolResult.ok("Help displayed.", embed=embed)
