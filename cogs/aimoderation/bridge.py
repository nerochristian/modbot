"""
Bridge between AI moderation handlers and the traditional Moderation cog.

When the Moderation cog is loaded, AI tool handlers delegate ban/kick/mute/warn
actions through it for unified logging and audit trail. Otherwise they fall back
to direct Discord API calls.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from utils.moderation_settings import moderation_bool
from utils.warning_escalation import apply_warning_escalation

if TYPE_CHECKING:
    from cogs.moderation import Moderation

logger = logging.getLogger("ModBot.AIModeration.Bridge")


def get_moderation_cog(bot: Optional[commands.Bot]) -> Optional["Moderation"]:
    """Get the traditional Moderation cog if loaded."""
    if bot is None:
        return None
    cog = bot.get_cog("Moderation")
    return cog  # type: ignore[return-value]


# ---- Action delegation -------------------------------------------------------


async def ban_member(
    source: discord.Message,
    target: discord.Member,
    reason: str,
    *,
    delete_message_days: int = 0,
    actor: Optional[discord.Member] = None,
    bot: Optional[commands.Bot] = None,
) -> str:
    """Ban a member through the Moderation cog if available, else direct API."""
    mod_cog = get_moderation_cog(bot) if bot else None
    if mod_cog and hasattr(mod_cog, "_ban_logic"):
        await mod_cog._ban_logic(source, target, reason)
        return f"Banned {target.display_name}."
    # Fallback
    settings = {}
    db = getattr(bot, "db", None) if bot else None
    get_settings = getattr(db, "get_settings", None)
    if callable(get_settings) and source.guild:
        loaded = await get_settings(source.guild.id)
        if isinstance(loaded, dict):
            settings = loaded
    effective_delete_days = 0 if moderation_bool(
        settings,
        "moderation_preserve_ban_messages",
        True,
    ) else max(0, min(7, delete_message_days))
    await target.ban(
        reason=f"AI Mod: {reason}",
        delete_message_days=effective_delete_days,
    )
    return f"Banned {target.display_name}."


async def kick_member(
    source: discord.Message,
    target: discord.Member,
    reason: str,
    *,
    actor: Optional[discord.Member] = None,
    bot: Optional[commands.Bot] = None,
) -> str:
    """Kick a member through the Moderation cog if available."""
    mod_cog = get_moderation_cog(bot)
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
    *,
    bot: Optional[commands.Bot] = None,
) -> str:
    """Timeout a member through the Moderation cog if available."""
    duration_str = _format_duration(duration_seconds)
    mod_cog = get_moderation_cog(bot)
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
    *,
    actor: Optional[discord.Member] = None,
    bot: Optional[commands.Bot] = None,
) -> str:
    """Warn a member through the Moderation cog if available."""
    mod_cog = get_moderation_cog(bot)
    if mod_cog and hasattr(mod_cog, "_warn_logic"):
        await mod_cog._warn_logic(source, target, reason)
        return f"Warned {target.display_name}."
    db = getattr(bot, "db", None) if bot else None
    if db and source.guild and actor:
        _, total_count = await db.add_warning(
            guild_id=source.guild.id,
            user_id=target.id,
            moderator_id=actor.id,
            reason=reason,
        )
        get_settings = getattr(db, "get_settings", None)
        if not callable(get_settings):
            logger.error(
                "Warning for user %s in guild %s was recorded but guild settings are unavailable; "
                "automatic punishment was skipped",
                target.id,
                source.guild.id,
            )
            return f"Warned {target.display_name}. Automatic punishment could not be evaluated."

        try:
            settings = await get_settings(source.guild.id)
            if not isinstance(settings, dict):
                settings = {}

            async def create_escalation_case(
                action: str,
                action_reason: str,
                duration_seconds: Optional[int],
            ) -> None:
                create_case = getattr(db, "create_case", None)
                if not callable(create_case):
                    logger.error(
                        "Automatic warning escalation for guild %s could not create a case: "
                        "database create_case is unavailable",
                        source.guild.id,
                    )
                    return
                bot_user = getattr(bot, "user", None)
                moderator_id = int(getattr(bot_user, "id", 0) or actor.id)
                duration = _format_duration(duration_seconds) if duration_seconds else None
                try:
                    await create_case(
                        source.guild.id,
                        target.id,
                        moderator_id,
                        action,
                        action_reason,
                        duration,
                    )
                except Exception:
                    logger.exception(
                        "Automatic warning escalation was applied to user %s in guild %s "
                        "but its punishment case could not be created",
                        target.id,
                        source.guild.id,
                    )

            escalation = await apply_warning_escalation(
                source.guild,
                target,
                settings,
                total_count,
                previous_count=max(0, total_count - 1),
                reason_prefix="AI warning escalation",
                ban_delete_days=1,
                create_case=create_escalation_case,
            )
            if escalation is None:
                return f"Warned {target.display_name}."

            action_labels = {
                "timeout": "timed out",
                "kick": "kicked",
                "ban": "banned",
            }
            duration = (
                f" for {_format_duration(escalation.rule.duration_seconds)}"
                if escalation.rule.duration_seconds
                else ""
            )
            return (
                f"Warned {target.display_name}. Automatically "
                f"{action_labels[escalation.rule.action]}{duration} after crossing "
                f"{escalation.rule.warning_count} warnings."
            )
        except discord.Forbidden:
            logger.warning(
                "Discord denied automatic warning escalation for user %s in guild %s",
                target.id,
                source.guild.id,
            )
            return (
                f"Warned {target.display_name}. Automatic punishment failed because "
                "the bot lacks permission."
            )
        except discord.HTTPException as exc:
            logger.warning(
                "Discord API rejected automatic warning escalation for user %s in guild %s: %s",
                target.id,
                source.guild.id,
                exc,
            )
            return (
                f"Warned {target.display_name}. Automatic punishment failed because "
                "Discord rejected the action."
            )
        except Exception:
            logger.exception(
                "Warning for user %s in guild %s was recorded but automatic punishment failed",
                target.id,
                source.guild.id,
            )
            return f"Warned {target.display_name}. Automatic punishment could not be evaluated."
    raise RuntimeError("Moderation cog or database is required to record a warning.")


def _format_duration(seconds: int) -> str:
    if seconds >= 86400:
        return f"{seconds // 86400}d"
    if seconds >= 3600:
        return f"{seconds // 3600}h"
    if seconds >= 60:
        return f"{seconds // 60}m"
    return f"{seconds}s"
