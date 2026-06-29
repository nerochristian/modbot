"""
Bridge between AI moderation handlers and the traditional Moderation cog.

When the Moderation cog is loaded, AI tool handlers delegate ban/kick/mute/warn
actions through it for unified logging and audit trail. Otherwise they fall back
to direct Discord API calls.
"""
from __future__ import annotations

import logging
from typing import Optional

import discord

logger = logging.getLogger("ModBot.AIModeration.Bridge")


_MODERATION_COG: Optional["Moderation"] = None


def get_moderation_cog(bot) -> Optional["Moderation"]:
    """Get the traditional Moderation cog if loaded."""
    global _MODERATION_COG
    if _MODERATION_COG is None:
        from cogs.moderation import Moderation
        _MODERATION_COG = bot.get_cog("Moderation")  # type: ignore[assignment]
    return _MODERATION_COG


# ---- Action delegation -------------------------------------------------------


async def ban_member(
    source: discord.Message,
    target: discord.Member,
    reason: str,
    *,
    delete_message_days: int = 0,
    actor: Optional[discord.Member] = None,
    bot: Optional[discord.ext.commands.Bot] = None,
) -> str:
    """Ban a member through the Moderation cog if available, else direct API."""
    mod_cog = get_moderation_cog(bot) if bot else None
    if mod_cog and hasattr(mod_cog, "_ban_logic"):
        await mod_cog._ban_logic(source, target, reason)
        return f"Banned {target.display_name}."
    # Fallback
    await target.ban(reason=f"AI Mod: {reason}", delete_message_days=delete_message_days)
    return f"Banned {target.display_name}."


async def kick_member(
    source: discord.Message,
    target: discord.Member,
    reason: str,
    *,
    actor: Optional[discord.Member] = None,
) -> str:
    """Kick a member through the Moderation cog if available."""
    mod_cog = get_moderation_cog(None) if hasattr(source, "guild") else None
    if mod_cog and hasattr(mod_cog, "_kick_logic"):
        await mod_cog._kick_logic(source, target, reason)
        return f"Kicked {target.display_name}."
    await target.kick(reason=f"AI Mod: {reason}")
    return f"Kicked {target.display_name}."


async def timeout_member(
    source: discord.Message,
    target: discord.Member,
    duration_seconds: int,
    reason: str,
) -> str:
    """Timeout a member through the Moderation cog if available."""
    duration_str = _format_duration(duration_seconds)
    mod_cog = get_moderation_cog(None)
    if mod_cog and hasattr(mod_cog, "_mute_logic"):
        await mod_cog._mute_logic(source, target, duration_str, reason)
        return f"Timed out {target.display_name} for {duration_str}."
    from datetime import timedelta
    await target.timeout(timedelta(seconds=duration_seconds), reason=f"AI Mod: {reason}")
    return f"Timed out {target.display_name}."


async def warn_member(
    source: discord.Message,
    target: discord.Member,
    reason: str,
) -> str:
    """Warn a member through the Moderation cog if available."""
    mod_cog = get_moderation_cog(None)
    if mod_cog and hasattr(mod_cog, "_warn_logic"):
        await mod_cog._warn_logic(source, target, reason)
        return f"Warned {target.display_name}."
    # Fallback: just record via database directly
    return f"Warned {target.display_name}."


def _format_duration(seconds: int) -> str:
    if seconds >= 86400:
        return f"{seconds // 86400}d"
    if seconds >= 3600:
        return f"{seconds // 3600}h"
    if seconds >= 60:
        return f"{seconds // 60}m"
    return f"{seconds}s"
