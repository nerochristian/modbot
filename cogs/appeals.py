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
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger("ModBot.Appeals")

APPEALABLE_ACTIONS = {"warn", "mute", "timeout", "kick", "ban", "tempban", "softban"}
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


class Appeals(commands.Cog):
    appeals = app_commands.Group(name="appeals", description="Configure and inspect punishment appeals")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @appeals.command(name="setup", description="Configure the private staff channel used for appeal reviews")
    @app_commands.describe(channel="Private staff channel for new appeals", accepting="Whether unused appeal links may be submitted")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_appeals(self, interaction: discord.Interaction, channel: discord.TextChannel, accepting: bool = True) -> None:
        settings = await self.bot.db.get_settings(interaction.guild_id)
        changes = dict(settings)
        changes.update({
            "appeals_enabled": True,
            "appeals_open": accepting,
            "appeal_staff_channel": str(channel.id),
            "appeal_expiry_days": max(1, min(30, int(settings.get("appeal_expiry_days") or 7))),
            "appeal_questions": _questions(settings.get("appeal_questions")),
        })
        await self.bot.db.update_settings(interaction.guild_id, changes)
        await interaction.response.send_message(
            f"Appeals are **enabled** and {'open' if accepting else 'closed'} for submissions. New appeals will be sent to {channel.mention}. Configure questions and link lifetime in the dashboard's **Appeals** module.",
            ephemeral=True,
        )

    @appeals.command(name="status", description="Show the current appeal workflow configuration")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def appeals_status(self, interaction: discord.Interaction) -> None:
        settings = await self.bot.db.get_settings(interaction.guild_id)
        channel_id = str(settings.get("appeal_staff_channel") or "")
        questions = _questions(settings.get("appeal_questions"))
        embed = discord.Embed(title="Appeals workflow", color=0x5865F2)
        embed.add_field(name="Module", value="Enabled" if _as_bool(settings.get("appeals_enabled")) else "Disabled", inline=True)
        embed.add_field(name="Submissions", value="Open" if _as_bool(settings.get("appeals_open"), True) else "Closed", inline=True)
        embed.add_field(name="Link lifetime", value=f"{max(1, min(30, int(settings.get('appeal_expiry_days') or 7)))} days", inline=True)
        embed.add_field(name="Staff channel", value=f"<#{channel_id}>" if channel_id.isdigit() else "Not configured", inline=False)
        embed.add_field(name="Questions", value="\n".join(f"{index}. {question['label']}" for index, question in enumerate(questions, 1)), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def notify_punishment(
        self,
        *,
        guild: discord.Guild,
        user: discord.abc.User,
        action: str,
        reason: str,
        case_number: int,
        duration: Optional[str] = None,
        settings: Optional[dict[str, Any]] = None,
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
                        (token_hash, guild.id, moderation_case["id"], user.id, expires_at, json.dumps(_questions(settings.get("appeal_questions")))),
                    )
                    row = await cursor.fetchone()
                    token_row_id = int(row[0]) if row else None
                appeal_url = f"{base_url}/appeal/{token}"

        embed = discord.Embed(
            title="Moderation action recorded",
            description=(
                f"You can ask **{guild.name}** staff to review this case until <t:{int(expires_at.timestamp())}:F>."
                if appeal_url and expires_at else f"A moderation action was recorded in **{guild.name}**."
            ),
            color=0x5865F2,
        )
        embed.add_field(name="Action", value=action.upper(), inline=True)
        embed.add_field(name="Case", value=f"CASE-{case_number:04d}", inline=True)
        if duration:
            embed.add_field(name="Duration", value=duration, inline=True)
        embed.add_field(name="Reason", value=reason[:1024], inline=False)
        embed.set_footer(text="Docket · Moderation records desk")
        view = discord.ui.View(timeout=None)
        if appeal_url:
            view.add_item(discord.ui.Button(label="Appeal here", url=appeal_url))
        delivery_status = "sent"
        delivery_error: Optional[str] = None
        try:
            await user.send(embed=embed, view=view if appeal_url else None)
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
