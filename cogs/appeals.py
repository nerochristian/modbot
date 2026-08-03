"""Case-bound punishment appeals and server-side setup commands."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

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


def _safe_rejoin_url(value: object) -> Optional[str]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = urlparse(raw)
    except ValueError:
        return None
    host = (parsed.hostname or "").casefold()
    if parsed.scheme != "https" or host not in {
        "discord.gg",
        "www.discord.gg",
        "discord.com",
        "www.discord.com",
    }:
        return None
    if host.endswith("discord.com") and not parsed.path.startswith("/invite/"):
        return None
    return raw


def _release_status_label(action: str, duration: Optional[str]) -> Optional[str]:
    normalized = str(action or "").strip().casefold()
    release_verbs = {
        "mute": "Unmuted",
        "timeout": "Unmuted",
        "ban": "Unbanned",
        "tempban": "Unbanned",
        "quarantine": "Released",
    }
    verb = release_verbs.get(normalized)
    if verb is None:
        return None
    clean_duration = " ".join(str(duration or "soon").split())
    label = f"{verb} in {clean_duration}"
    return label if len(label) <= 80 else f"{verb} when timer ends"


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
    rejoin_url: Optional[str] = None,
    moderator: Optional[discord.abc.User] = None,
    issued_at: Optional[datetime] = None,
) -> tuple[discord.Embed, Optional[discord.ui.View]]:
    normalized_action = action.strip().lower()
    emoji_kind, action_text = _action_copy(action)
    emoji = get_app_emoji(emoji_kind)
    action_line = f"{emoji} {action_text}" if emoji else action_text
    if punishment_expires_at is not None:
        action_line += f" until <t:{int(punishment_expires_at.timestamp())}:R>"

    member_name = discord.utils.escape_markdown(
        str(getattr(user, "display_name", None) or getattr(user, "name", None) or "Member")
    )[:80]
    reason_text = str(reason or "No reason provided")[:700]
    id_emoji = get_app_emoji("id")
    identity = f"user:{user.id} " if user is not None else ""
    details = (
        f"> {reason_text}\n"
        f"-# {id_emoji + ' ' if id_emoji else ''}`{identity}date:{datetime.now(timezone.utc):%Y-%m-%d}`"
    )
    accent_color = 0xED4245 if normalized_action in {"ban", "tempban", "softban"} else 0xF0B232
    action_time = issued_at or datetime.now(timezone.utc)
    embed = discord.Embed(
        title=member_name,
        description=action_line,
        color=accent_color,
        timestamp=action_time,
    )
    embed.add_field(name="Reason :", value=details, inline=False)

    guild_icon = getattr(getattr(guild, "icon", None), "url", None)
    if guild_icon:
        embed.set_thumbnail(url=str(guild_icon))

    safe_rejoin_url = _safe_rejoin_url(rejoin_url)
    status_label = (
        _release_status_label(normalized_action, duration)
        if punishment_expires_at is not None
        else None
    )
    if status_label:
        embed.add_field(name="\u200b", value=f"**{status_label}**", inline=False)
    elif normalized_action in {"kick", "softban"} and safe_rejoin_url:
        embed.add_field(
            name="\u200b",
            value=f"[Rejoin server]({safe_rejoin_url})",
            inline=False,
        )

    if moderator is not None:
        stamp_actor_footer(embed, moderator, timestamp=action_time)
    else:
        embed.set_footer(text="Docket moderation")

    view: Optional[discord.ui.View] = None
    if appeal_url:
        view = discord.ui.View(timeout=None)
        view.add_item(
            discord.ui.Button(
                label="Appeal here",
                url=appeal_url,
                emoji=get_app_emoji("info") or None,
            )
        )
    return embed, view


def build_release_notice(
    *,
    guild: discord.Guild,
    user: Optional[discord.abc.User] = None,
    rejoin_url: Optional[str] = None,
) -> discord.ui.LayoutView:
    """Build the DM sent after a temporary ban is automatically released."""
    member_name = discord.utils.escape_markdown(
        str(getattr(user, "display_name", None) or getattr(user, "name", None) or "Member")
    )[:80]
    success = get_app_emoji("success")
    header = f"## {member_name}\n{success + ' ' if success else ''}You have been **unbanned**"
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
    children.extend([
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay("> Your temporary ban has ended. You can rejoin the server now."),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
    ])

    safe_rejoin_url = _safe_rejoin_url(rejoin_url)
    footer = discord.ui.TextDisplay(
        f"-# {guild.name} · <t:{int(datetime.now(timezone.utc).timestamp())}:f>"
    )
    if safe_rejoin_url:
        children.append(
            discord.ui.Section(
                footer,
                accessory=discord.ui.Button(label="Rejoin server", url=safe_rejoin_url),
            )
        )
    else:
        children.append(footer)

    view = discord.ui.LayoutView(timeout=None)
    view.add_item(discord.ui.Container(*children, accent_color=0x22C55E))
    return view


class Appeals(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._rejoin_invites: dict[int, str] = {}

    async def _resolve_rejoin_url(self, guild: discord.Guild, settings: dict[str, Any]) -> Optional[str]:
        """Return a safe public invite, creating one only when the bot can do so."""
        for key in (
            "moderation_rejoin_invite_url",
            "server_invite_url",
            "welcome_invite_url",
            "invite_url",
        ):
            configured = _safe_rejoin_url(settings.get(key))
            if configured:
                return configured

        vanity_code = str(getattr(guild, "vanity_url_code", None) or "").strip()
        if vanity_code:
            return f"https://discord.gg/{vanity_code}"

        guild_id = int(getattr(guild, "id", 0) or 0)
        cached = _safe_rejoin_url(self._rejoin_invites.get(guild_id))
        if cached:
            return cached

        bot_member = getattr(guild, "me", None)
        candidates = []
        seen_ids: set[int] = set()
        for channel in (
            getattr(guild, "system_channel", None),
            getattr(guild, "rules_channel", None),
            getattr(guild, "public_updates_channel", None),
            *(getattr(guild, "text_channels", None) or []),
        ):
            channel_id = int(getattr(channel, "id", 0) or 0)
            if channel is None or channel_id in seen_ids:
                continue
            seen_ids.add(channel_id)
            candidates.append(channel)

        for channel in candidates:
            create_invite = getattr(channel, "create_invite", None)
            if not callable(create_invite):
                continue
            permissions_for = getattr(channel, "permissions_for", None)
            if callable(permissions_for) and bot_member is not None:
                permissions = permissions_for(bot_member)
                if not (
                    bool(getattr(permissions, "administrator", False))
                    or (
                        bool(getattr(permissions, "view_channel", False))
                        and bool(getattr(permissions, "create_instant_invite", False))
                    )
                ):
                    continue
            try:
                invite = await create_invite(
                    max_age=0,
                    max_uses=0,
                    unique=False,
                    reason="Docket moderation rejoin link",
                )
            except (discord.Forbidden, discord.HTTPException, TypeError):
                continue
            invite_url = _safe_rejoin_url(getattr(invite, "url", None) or str(invite))
            if invite_url:
                if guild_id:
                    self._rejoin_invites[guild_id] = invite_url
                return invite_url
        return None

    async def _resolve_case_moderator(
        self,
        guild: discord.Guild,
        moderation_case: Optional[dict[str, Any]],
    ) -> Optional[discord.abc.User]:
        if not moderation_case:
            return None
        try:
            moderator_id = int(moderation_case["moderator_id"])
        except (KeyError, TypeError, ValueError, OverflowError):
            return None

        get_member = getattr(guild, "get_member", None)
        moderator = get_member(moderator_id) if callable(get_member) else None
        if moderator is None:
            get_user = getattr(self.bot, "get_user", None)
            moderator = get_user(moderator_id) if callable(get_user) else None
        if moderator is None:
            fetch_user = getattr(self.bot, "fetch_user", None)
            if callable(fetch_user):
                try:
                    moderator = await fetch_user(moderator_id)
                except (discord.NotFound, discord.HTTPException):
                    moderator = None
        return moderator

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

        moderation_case: Optional[dict[str, Any]] = None
        get_case = getattr(getattr(self.bot, "db", None), "get_case", None)
        if callable(get_case):
            try:
                moderation_case = await get_case(guild.id, case_number)
            except Exception:
                logger.debug("Could not resolve moderation case %s for DM metadata", case_number)
        moderator = await self._resolve_case_moderator(guild, moderation_case)

        rejoin_url: Optional[str] = None
        if normalized_action in {"kick", "softban"}:
            rejoin_url = await self._resolve_rejoin_url(guild, settings)

        appeal_url: Optional[str] = None
        expires_at: Optional[datetime] = None
        token_row_id: Optional[int] = None
        if eligible:
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

        embed, view = build_punishment_notice(
            guild=guild,
            user=user,
            action=action,
            reason=reason,
            case_number=case_number,
            duration=duration,
            punishment_expires_at=punishment_expires_at,
            appeal_url=appeal_url,
            rejoin_url=rejoin_url,
            moderator=moderator,
        )
        delivery_status = "sent"
        delivery_error: Optional[str] = None
        try:
            message_kwargs: dict[str, Any] = {"embed": embed}
            if view is not None:
                message_kwargs["view"] = view
            await (delivery_channel or user).send(**message_kwargs)
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

    async def notify_tempban_expired(
        self,
        *,
        guild: discord.Guild,
        user: discord.abc.User,
        settings: Optional[dict[str, Any]] = None,
    ) -> bool:
        settings = settings or await self.bot.db.get_settings(guild.id)
        rejoin_url = await self._resolve_rejoin_url(guild, settings)
        view = build_release_notice(guild=guild, user=user, rejoin_url=rejoin_url)
        try:
            await user.send(view=view)
        except (discord.Forbidden, discord.HTTPException):
            return False
        return True


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Appeals(bot))
