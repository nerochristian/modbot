"""AutoMod logging helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import discord

from utils.embeds import Colors, compact_kv_lines, moderation_list_embed
from .models import Action, RuleMatch, Severity


def _trim(value: object, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text or "None"
    return text[: max(0, limit - 3)].rstrip() + "..."


def _friendly_rule(rule: str) -> str:
    labels = {
        "badwords": "Blocked words",
        "caps": "Excessive caps",
        "duplicates": "Duplicate messages",
        "emoji_spam": "Emoji spam",
        "fast_messages": "Fast messages",
        "invites": "Discord invites",
        "links": "Suspicious links",
        "mentions": "Mention spam",
        "new_accounts": "New account",
        "scams": "Scam protection",
        "spam": "Message spam",
        "unicode_spam": "Unicode spam",
        "wall_spam": "Message wall",
    }
    clean = str(rule or "").strip().lower()
    return labels.get(clean, clean.replace("_", " ").replace("-", " ").title() or "Unknown rule")


def _friendly_action(action: Action) -> str:
    return {
        Action.NONE: "No additional action",
        Action.LOG: "Logged",
        Action.WARN: "Warned",
        Action.MUTE: "Timed out",
        Action.TIMEOUT: "Timed out",
        Action.KICK: "Kicked",
        Action.BAN: "Banned",
    }[action]


def _severity_color(severity: Severity, *, failed: bool = False) -> int:
    if failed:
        return Colors.ERROR
    if severity is Severity.CRITICAL:
        return Colors.DARK_RED
    if severity is Severity.HIGH:
        return Colors.ERROR
    if severity is Severity.MEDIUM:
        return Colors.WARNING
    return Colors.INFO


def _message_preview(content: object, limit: int = 1000) -> str:
    text = _trim(content, limit)
    return "\n".join(f"> {line}" for line in text.splitlines())


class AutoModLogger:
    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot

    async def log_message_action(
        self,
        message: discord.Message,
        match: RuleMatch,
        action: Action,
        *,
        deleted: bool,
        case_number: Optional[int] = None,
        error: Optional[str] = None,
        offense_count: Optional[int] = None,
    ) -> None:
        if message.guild is None:
            return
        embed = discord.Embed(
            title="AutoMod action failed" if error else ("AutoMod removed a message" if deleted else "AutoMod rule triggered"),
            color=_severity_color(match.severity, failed=bool(error)),
            timestamp=datetime.now(timezone.utc),
        )
        rows: list[tuple[str, object]] = [
            ("Member", f"{message.author.mention} (`{message.author.id}`)"),
            ("Channel", getattr(message.channel, "mention", str(message.channel))),
            ("Rule", _friendly_rule(match.rule)),
            ("Action", _friendly_action(action)),
            ("Message removed", "Yes" if deleted else "No"),
        ]
        if offense_count is not None:
            rows.append(("Recent offenses", offense_count))
        if case_number:
            rows.append(("Case", f"#{case_number}"))
        rows.append(("Reason", _trim(match.reason, 500)))
        embed.description = compact_kv_lines(rows, max_value_length=500)
        if message.content:
            embed.add_field(name="Message", value=_message_preview(message.content), inline=False)
        evidence = _trim(", ".join(match.evidence), 900) if match.evidence else ""
        if evidence and evidence.casefold() != str(message.content or "").strip().casefold():
            embed.add_field(name="Matched content", value=_message_preview(evidence, 900), inline=False)
        if error:
            embed.add_field(name="Error", value=_trim(error, 900), inline=False)
        avatar_url = getattr(getattr(message.author, "display_avatar", None), "url", None)
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        await self._send(message.guild, embed)

    async def log_member_action(
        self,
        guild: discord.Guild,
        member: discord.Member,
        match: RuleMatch,
        action: Action,
        *,
        error: Optional[str] = None,
    ) -> None:
        embed = discord.Embed(
            title="AutoMod member alert failed" if error else "AutoMod member alert",
            color=_severity_color(match.severity, failed=bool(error)),
            timestamp=datetime.now(timezone.utc),
        )
        embed.description = compact_kv_lines(
            [
                ("Member", f"{member.mention} (`{member.id}`)"),
                ("Rule", _friendly_rule(match.rule)),
                ("Action", _friendly_action(action)),
                ("Reason", _trim(match.reason, 500)),
            ],
            max_value_length=500,
        )
        if error:
            embed.add_field(name="Error", value=_trim(error, 900), inline=False)
        avatar_url = getattr(getattr(member, "display_avatar", None), "url", None)
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        await self._send(guild, embed)

    def build_user_notice(
        self,
        message: discord.Message,
        match: RuleMatch,
        action: Action,
        *,
        deleted: bool,
        case_number: Optional[int] = None,
        appeal_instructions: str = "",
    ) -> discord.Embed:
        guild = message.guild
        server_name = guild.name if guild is not None else "this server"
        outcome = "Removed" if deleted else _friendly_action(action)
        entries = [
            f"**Why it was flagged**\n{_message_preview(match.reason, 500)}",
        ]
        if message.content:
            entries.append(f"**Message**\n{_message_preview(message.content)}")
        appeal = str(appeal_instructions or "").strip()
        if appeal:
            entries.append(f"**What you can do**\n> {_trim(appeal, 500)}")

        footer = f"CASE-{case_number:04d} | AutoMod" if case_number else "Docket AutoMod"
        embed = moderation_list_embed(
            title="Message flagged",
            color=_severity_color(match.severity),
            summary_rows=(
                ("Server", server_name),
                ("Rule", _friendly_rule(match.rule)),
                ("Outcome", outcome),
            ),
            entries=entries,
            footer_text=footer,
        )
        guild_icon = getattr(getattr(guild, "icon", None), "url", None)
        if guild_icon:
            embed.set_author(name=server_name, icon_url=guild_icon)
        else:
            embed.set_author(name=server_name)
        return embed

    async def _send(self, guild: discord.Guild, embed: discord.Embed) -> None:
        logging_cog = getattr(self.bot, "get_cog", lambda name: None)("Logging")
        if logging_cog and hasattr(logging_cog, "get_log_channel"):
            try:
                channel = await logging_cog.get_log_channel(guild, "automod", allow_audit_fallback=True)
            except TypeError:
                channel = await logging_cog.get_log_channel(guild, "automod")
            if channel is not None:
                if hasattr(logging_cog, "safe_send_log"):
                    await logging_cog.safe_send_log(channel, embed, mirror_to_audit=False)
                else:
                    await channel.send(embed=embed)
                return
        settings = await self.bot.db.get_settings(guild.id)
        channel_id = settings.get("automod_log_channel") or settings.get("log_channel_automod")
        try:
            channel = guild.get_channel(int(channel_id)) if channel_id else None
        except (TypeError, ValueError):
            channel = None
        if channel is not None:
            await channel.send(embed=embed)
