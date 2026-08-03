"""Case-bound punishment appeals and server-side setup commands."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import discord
from discord.ext import commands

from utils.embeds import Colors, moderation_list_embed, stamp_actor_footer
from utils.status_emojis import get_app_emoji

logger = logging.getLogger("ModBot.Appeals")

APPEALABLE_ACTIONS = {"automod", "warn", "mute", "timeout", "kick", "ban", "tempban", "softban", "quarantine"}
DEFAULT_QUESTIONS = [
    {"id": "why", "label": "Why should this punishment be reviewed?", "placeholder": "Explain what happened and why staff should reconsider the case.", "style": "paragraph", "required": True},
    {"id": "context", "label": "Anything else staff should know?", "placeholder": "Add evidence, message links, or relevant context.", "style": "paragraph", "required": False},
]


def _as_bool(value: object, fallback: bool = False) -> bool:
    if value is None:
        return fallback
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _questions(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return [dict(question) for question in DEFAULT_QUESTIONS]
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value[:5]:
        if not isinstance(raw, dict):
            continue
        question_id = str(raw.get("id") or "").strip().lower()
        label = str(raw.get("label") or "").strip()
        if not question_id or question_id in seen or len(label) < 2:
            continue
        seen.add(question_id)
        normalized.append({
            "id": question_id[:40],
            "label": label[:80],
            "placeholder": str(raw.get("placeholder") or "").strip()[:160],
            "style": "short" if raw.get("style") == "short" else "paragraph",
            "required": raw.get("required") is not False,
        })
    return normalized or [dict(question) for question in DEFAULT_QUESTIONS]


def _database_timestamp(value: datetime) -> datetime:
    """Store UTC in the runtime's timezone-less PostgreSQL timestamp columns."""
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _action_copy(action: str) -> tuple[str, str]:
    normalized = action.strip().lower()
    labels = {
        "automod": ("warn", "Your message was **removed**"),
        "warn": ("warn", "You received a **warning**"),
        "mute": ("mute", "You have been **muted**"),
        "timeout": ("mute", "You have been **timed out**"),
        "kick": ("kick", "You have been **kicked**"),
        "ban": ("ban", "You have been **banned**"),
        "tempban": ("ban", "You have been **temporarily banned**"),
        "softban": ("ban", "You have been **softbanned**"),
        "quarantine": ("lock", "You have been **quarantined**"),
    }
    return labels.get(normalized, ("warning", "Moderation action"))


def build_punishment_notice(
    *,
    guild: discord.Guild,
    user: Optional[discord.abc.User] = None,
    action: str,
    reason: str,
    case_number: int,
    duration: Optional[str] = None,
    punishment_expires_at: Optional[datetime] = None,
    appeal_url: Optional[str] = None,
) -> discord.ui.LayoutView:
    emoji_kind, action_text = _action_copy(action)
    emoji = get_app_emoji(emoji_kind)
    action_line = f"{emoji} {action_text}" if emoji else action_text
    if duration:
        action_line += f" for **{duration}**"

    member_name = discord.utils.escape_markdown(
        str(getattr(user, "display_name", None) or getattr(user, "name", None) or "Member")
    )[:80]
    expiry_line = (
        f"\nuntil <t:{int(punishment_expires_at.timestamp())}:R>"
        if punishment_expires_at is not None
        else ""
    )
    header = f"## {member_name}\n{action_line}{expiry_line}"
    reason_text = str(reason or "No reason provided")[:700]
    id_emoji = get_app_emoji("id")
    identity = f"user:{user.id} " if user is not None else ""
    available_again = (
        f"\n-# Available again <t:{int(punishment_expires_at.timestamp())}:R>"
        if punishment_expires_at is not None
        else ""
    )
    details = (
        f"**Reason :**\n> {reason_text}\n"
        f"-# {id_emoji + ' ' if id_emoji else ''}`{identity}date:{datetime.now(timezone.utc):%Y-%m-%d}`"
    )
    guild_icon = getattr(getattr(guild, "icon", None), "url", None)
    children: list[discord.ui.Item[Any]] = []
    if guild_icon:
        children.append(
            discord.ui.Section(
                discord.ui.TextDisplay(header),
                accessory=discord.ui.Thumbnail(guild_icon),
            )
        )
    else:
        children.append(discord.ui.TextDisplay(header))
    children.extend(
        [
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(details),
        ]
    )

    view = discord.ui.LayoutView(timeout=None)
    accent_color = 0xED4245 if action.strip().lower() in {"ban", "tempban", "softban"} else 0xF0B232
    view.add_item(discord.ui.Container(*children, accent_color=accent_color))
    if punishment_expires_at is not None:
        view.add_item(discord.ui.TextDisplay(available_again.removeprefix("\n-# ")))
    if appeal_url:
        view.add_item(
            discord.ui.ActionRow(
                discord.ui.Button(
                    label="Appeal here",
                    url=appeal_url,
                    emoji=get_app_emoji("info") or None,
                )
            )
        )
    return view


class Appeals(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="appeals", invoke_without_command=True)
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def appeals_command(self, ctx: commands.Context) -> None:
        """Configure punishment appeals (dashboard setup is recommended)."""
        await ctx.send("Use `.appeals setup #staff-channel [open|closed]` or `.appeals status`. Full questions are configured in Dashboard → Modules → Appeals.")

    @appeals_command.command(name="setup")
    @commands.has_guild_permissions(manage_guild=True)
    async def setup_appeals(self, ctx: commands.Context, channel: discord.TextChannel, accepting: str = "open") -> None:
        settings = await self.bot.db.get_settings(ctx.guild.id)
        is_open = accepting.strip().lower() not in {"closed", "close", "off", "false", "no"}
        changes = dict(settings)
        changes.update({
            "appeals_enabled": True,
            "appeals_open": is_open,
            "appeal_staff_channel": str(channel.id),
            "appeal_expiry_days": max(1, min(30, int(settings.get("appeal_expiry_days") or 7))),
            "appeal_questions": _questions(settings.get("appeal_questions")),
        })
        await self.bot.db.update_settings(ctx.guild.id, changes)
        await ctx.send(
            f"Appeals are **enabled** and {'open' if is_open else 'closed'} for submissions. New appeals will be sent to {channel.mention}. Configure questions and link lifetime in the dashboard's **Appeals** module.",
        )

    @appeals_command.command(name="status")
    @commands.has_guild_permissions(manage_guild=True)
    async def appeals_status(self, ctx: commands.Context) -> None:
        settings = await self.bot.db.get_settings(ctx.guild.id)
        channel_id = str(settings.get("appeal_staff_channel") or "")
        questions = _questions(settings.get("appeal_questions"))
        embed = moderation_list_embed(
            title="Appeals workflow",
            color=Colors.INFO,
            summary_rows=(
                ("Module", "Enabled" if _as_bool(settings.get("appeals_enabled")) else "Disabled"),
                ("Submissions", "Open" if _as_bool(settings.get("appeals_open"), True) else "Closed"),
                ("Link lifetime", f"{max(1, min(30, int(settings.get('appeal_expiry_days') or 7)))} days"),
                ("Staff channel", f"<#{channel_id}>" if channel_id.isdigit() else "Not configured"),
            ),
            entries=(
                "**Appeal questions**\n"
                + "\n".join(f"> {index}. {question['label']}" for index, question in enumerate(questions, 1)),
            ),
            thumbnail_url=getattr(getattr(ctx.guild, "icon", None), "url", None),
        )
        stamp_actor_footer(embed, ctx.author)
        await ctx.send(embed=embed)

    async def notify_punishment(
        self,
        *,
        guild: discord.Guild,
        user: discord.abc.User,
        action: str,
        reason: str,
        case_number: int,
        duration: Optional[str] = None,
        punishment_expires_at: Optional[datetime] = None,
        settings: Optional[dict[str, Any]] = None,
        delivery_channel: Optional[discord.abc.Messageable] = None,
    ) -> bool:
        settings = settings or await self.bot.db.get_settings(guild.id)
        normalized_action = action.strip().lower()
        base_url = (os.getenv("DASHBOARD_PUBLIC_URL") or os.getenv("FRONTEND_PUBLIC_URL") or "").rstrip("/")
        enabled = _as_bool(settings.get("appeals_enabled"))
        accepting = _as_bool(settings.get("appeals_open"), True)
        eligible = enabled and accepting and normalized_action in APPEALABLE_ACTIONS and base_url.startswith(("https://", "http://"))

        appeal_url: Optional[str] = None
        expires_at: Optional[datetime] = None
        token_row_id: Optional[int] = None
        if eligible:
            moderation_case = await self.bot.db.get_case(guild.id, case_number)
            if moderation_case:
                token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
                expiry_days = max(1, min(30, int(settings.get("appeal_expiry_days") or 7)))
                expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)
                async with self.bot.db.transaction() as db:
                    cursor = await db.execute(
                        """
                        INSERT INTO dashboard_appeal_tokens
                        (token_hash, guild_id, case_id, user_id, expires_at, used_at, appeal_id,
                         delivery_status, delivery_error, questions_json)
                        VALUES (?, ?, ?, ?, ?, NULL, NULL, 'pending', NULL, ?)
                        ON CONFLICT (guild_id, case_id) DO UPDATE SET
                          token_hash = excluded.token_hash, user_id = excluded.user_id,
                          expires_at = excluded.expires_at, used_at = NULL, appeal_id = NULL,
                          delivery_status = 'pending', delivery_error = NULL,
                          questions_json = excluded.questions_json, created_at = CURRENT_TIMESTAMP
                        RETURNING id
                        """,
                        (
                            token_hash,
                            guild.id,
                            moderation_case["id"],
                            user.id,
                            _database_timestamp(expires_at),
                            json.dumps(_questions(settings.get("appeal_questions"))),
                        ),
                    )
                    row = await cursor.fetchone()
                    token_row_id = int(row[0]) if row else None
                appeal_url = f"{base_url}/appeal/{token}"

        view = build_punishment_notice(
            guild=guild,
            user=user,
            action=action,
            reason=reason,
            case_number=case_number,
            duration=duration,
            punishment_expires_at=punishment_expires_at,
            appeal_url=appeal_url,
        )
        delivery_status = "sent"
        delivery_error: Optional[str] = None
        try:
            await (delivery_channel or user).send(view=view)
        except (discord.Forbidden, discord.HTTPException) as exc:
            delivery_status = "failed"
            delivery_error = str(exc)[:500]
        if token_row_id is not None:
            async with self.bot.db.transaction() as db:
                await db.execute(
                    "UPDATE dashboard_appeal_tokens SET delivery_status = ?, delivery_error = ? WHERE id = ?",
                    (delivery_status, delivery_error, token_row_id),
                )
        return delivery_status == "sent"


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Appeals(bot))
