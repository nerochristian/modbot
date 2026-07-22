"""
Member-targeted moderation handlers — warn, timeout, kick, ban, unban, snickname.

These handlers register with the ToolRegistry and are called by the AI routing
pipeline when the LLM decides a member-focused action is needed.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Optional

import discord

from utils.checks import is_bot_owner_id
from utils.moderation_settings import (
    moderation_bool,
    moderation_id_set,
    render_moderation_response,
)
from utils.warning_escalation import apply_warning_escalation

from ..context import ToolContext, ToolResult, action_embed
from ..registry import ToolRegistry
from ..types import ToolType

logger = logging.getLogger("ModBot.AIModeration.Handlers.Members")

MAX_WARNING_BATCH = 10


def _format_duration(seconds: int) -> str:
    if seconds % 86_400 == 0:
        return f"{seconds // 86_400} day(s)"
    if seconds % 3_600 == 0:
        return f"{seconds // 3_600} hour(s)"
    if seconds % 60 == 0:
        return f"{seconds // 60} minute(s)"
    return f"{seconds} second(s)"


async def _guild_moderation_settings(ctx: ToolContext) -> dict:
    db = getattr(ctx.cog.bot, "db", None)
    get_settings = getattr(db, "get_settings", None)
    if not callable(get_settings):
        return {}
    try:
        settings = await get_settings(ctx.guild.id)
    except Exception:
        logger.exception("Failed to load moderation settings for guild %s", ctx.guild.id)
        return {}
    return settings if isinstance(settings, dict) else {}


def _has_protected_role(ctx: ToolContext, target: discord.Member, settings: dict) -> bool:
    if is_bot_owner_id(ctx.actor.id) or ctx.actor.id == ctx.guild.owner_id:
        return False
    protected = moderation_id_set(settings, "protected_roles")
    return bool(protected.intersection(role.id for role in target.roles))


def _suppress_duplicate_member_action_log(ctx: ToolContext, user_id: int, action: str) -> None:
    logging_cog = ctx.cog.bot.get_cog("Logging")
    suppress = getattr(logging_cog, "suppress_member_action_log", None)
    if callable(suppress):
        suppress(ctx.guild.id, user_id, action)


async def _dm_moderation_action(
    target: discord.Member,
    *,
    guild_name: str,
    action: str,
    reason: str,
    duration: str = "",
) -> None:
    details = [f"**Reason:** {reason}"]
    if duration:
        details.append(f"**Duration:** {duration}")
    embed = discord.Embed(
        title=f"{action} in {guild_name}",
        description="\n".join(details),
        color=discord.Color.orange(),
    )
    try:
        await target.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        return


@ToolRegistry.register(
    ToolType.WARN,
    display_name="Warn Member",
    color=discord.Color.gold(),
    emoji="Warning",
    required_permission="moderate_members",
    category="members",
)
async def handle_warn(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Could not resolve target member.")
    if not ctx.cog.can_moderate(ctx.actor, target):
        return ToolResult.fail(f"Cannot moderate {target.display_name} (role hierarchy).")

    reason = ctx.str_arg("reason")
    warning_count = ctx.int_arg("warning_count", 1)
    if not 1 <= warning_count <= MAX_WARNING_BATCH:
        return ToolResult.fail(
            f"Warning count must be between 1 and {MAX_WARNING_BATCH}."
        )
    db = getattr(ctx.cog.bot, "db", None)
    if not db:
        return ToolResult.fail("Database not available; warning was not recorded.")
    try:
        add_warnings = getattr(db, "add_warnings", None)
        if callable(add_warnings):
            _, total_count = await add_warnings(
                guild_id=ctx.guild.id,
                user_id=target.id,
                moderator_id=ctx.actor.id,
                reason=reason,
                count=warning_count,
            )
        else:
            total_count = 0
            for _ in range(warning_count):
                _, total_count = await db.add_warning(
                    guild_id=ctx.guild.id,
                    user_id=target.id,
                    moderator_id=ctx.actor.id,
                    reason=reason,
                )
    except Exception:
        logger.exception("Failed to record %d warning(s)", warning_count)
        return ToolResult.fail("Database error while recording warnings.")

    previous_count = max(0, total_count - warning_count)
    escalation_status: Optional[str] = None
    get_settings = getattr(db, "get_settings", None)
    if callable(get_settings):
        try:
            settings = await get_settings(ctx.guild.id)
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
                        ctx.guild.id,
                    )
                    return
                bot_user = getattr(ctx.cog.bot, "user", None)
                moderator_id = int(getattr(bot_user, "id", 0) or ctx.actor.id)
                duration = _format_duration(duration_seconds) if duration_seconds else None
                try:
                    await create_case(
                        ctx.guild.id,
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
                        ctx.guild.id,
                    )

            escalation = await apply_warning_escalation(
                ctx.guild,
                target,
                settings,
                total_count,
                previous_count=previous_count,
                reason_prefix="AI warning escalation",
                ban_delete_days=1,
                create_case=create_escalation_case,
            )
            if escalation is not None:
                action_labels = {
                    "timeout": "Timed out",
                    "kick": "Kicked",
                    "ban": "Banned",
                }
                duration = (
                    f" for {_format_duration(escalation.rule.duration_seconds)}"
                    if escalation.rule.duration_seconds
                    else ""
                )
                escalation_status = (
                    f"{action_labels[escalation.rule.action]} automatically{duration} "
                    f"after crossing {escalation.rule.warning_count} warnings."
                )
        except discord.Forbidden:
            logger.warning(
                "Discord denied automatic warning escalation for user %s in guild %s",
                target.id,
                ctx.guild.id,
            )
            escalation_status = "Automatic punishment failed because the bot lacks permission."
        except discord.HTTPException as exc:
            logger.warning(
                "Discord API rejected automatic warning escalation for user %s in guild %s: %s",
                target.id,
                ctx.guild.id,
                exc,
            )
            escalation_status = "Automatic punishment failed because Discord rejected the action."
        except Exception:
            logger.exception(
                "Could not evaluate automatic warning escalation for user %s in guild %s",
                target.id,
                ctx.guild.id,
            )
            escalation_status = "Automatic punishment could not be evaluated."

    embed_extra = {
        "Warnings Issued": str(warning_count),
        "Total Warnings": str(total_count),
    }
    log_extra: dict[str, object] = {
        "Warnings Issued": warning_count,
        "Total Warnings": total_count,
    }
    if escalation_status:
        embed_extra["Automatic Punishment"] = escalation_status
        log_extra["Automatic Punishment"] = escalation_status

    embed = action_embed(
        title="Warnings Issued" if warning_count > 1 else "Member Warned",
        color=discord.Color.gold(),
        actor=ctx.actor,
        target=target,
        reason=reason,
        extra=embed_extra,
    )
    await ctx.cog.log_action(
        message=ctx.message,
        action="warn_member",
        actor=ctx.actor,
        target=target,
        reason=reason,
        decision=ctx.decision,
        extra=log_extra,
    )
    label = "warning" if warning_count == 1 else "warnings"
    result_message = f"{warning_count} {label} issued. Total warnings: {total_count}."
    if escalation_status:
        result_message = f"{result_message} {escalation_status}"
    return ToolResult.ok(
        result_message,
        embed=embed,
    )


@ToolRegistry.register(
    ToolType.GET_WARNINGS,
    display_name="Get Warnings",
    color=discord.Color.blue(),
    emoji="Warnings",
    required_permission="moderate_members",
    category="members",
)
async def handle_get_warnings(ctx: ToolContext) -> ToolResult:
    from datetime import datetime, timezone

    from utils.embeds import Colors

    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Could not resolve target member.")

    db = getattr(ctx.cog.bot, "db", None)
    if not db:
        return ToolResult.fail("Database not available.")

    try:
        warnings = await db.get_warnings(ctx.guild.id, target.id)
    except Exception:
        logger.exception("Failed to fetch warnings")
        return ToolResult.fail("Database error while fetching warnings.")

    if not warnings:
        embed = discord.Embed(
            title=f"Warnings for {target.display_name}",
            description=f"{target.mention} has no warnings.",
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        return ToolResult.ok(f"{target.display_name} has no warnings.", embed=embed, use_v2=False)

    embed = discord.Embed(
        title=f"Warnings for {target.display_name}",
        description=f"Total: **{len(warnings)}** warning(s)",
        color=Colors.WARNING,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    for warning in warnings[:10]:
        moderator_id = warning.get("moderator_id")
        moderator = ctx.guild.get_member(moderator_id) if moderator_id else None
        moderator_name = moderator.display_name if moderator else f"ID: {moderator_id or 'Unknown'}"
        reason = str(warning.get("reason") or "No reason provided")[:100]
        created_at = str(warning.get("created_at") or "Unknown time")
        embed.add_field(
            name=f"Warning #{warning.get('id', '?')}",
            value=f"**Reason:** {reason}\n**By:** {moderator_name}\n**When:** {created_at}",
            inline=False,
        )
    if len(warnings) > 10:
        embed.set_footer(text=f"Showing 10 of {len(warnings)} warnings")
    return ToolResult.ok(f"Found {len(warnings)} warning(s).", embed=embed, use_v2=False)


@ToolRegistry.register(
    ToolType.GET_HISTORY,
    display_name="Get History",
    color=discord.Color.blue(),
    emoji="History",
    required_permission="moderate_members",
    category="members",
)
async def handle_get_history(ctx: ToolContext) -> ToolResult:
    """
    Full moderation record for a member — the @mention analogue of !modlogs.
    Merges cases, warnings, and notes into one newest-first timeline so a mod
    can `@bot show actions for @user` and see everything on record at once.
    """
    from datetime import datetime, timezone

    from utils.embeds import Colors

    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Could not resolve target member.")

    db = getattr(ctx.cog.bot, "db", None)
    if not db:
        return ToolResult.fail("Database not available.")

    try:
        cases = await db.get_user_cases(ctx.guild.id, target.id)
        warnings = await db.get_warnings(ctx.guild.id, target.id)
        notes = await db.get_notes(ctx.guild.id, target.id)
    except Exception:
        logger.exception("Failed to fetch moderation history")
        return ToolResult.fail("Database error while fetching history.")

    entries: list[dict] = []
    for case in cases or []:
        entries.append({
            "type": "case",
            "action": str(case.get("action") or "Action"),
            "reason": case.get("reason"),
            "mod_id": case.get("moderator_id"),
            "timestamp": str(case.get("created_at") or ""),
            "id": case.get("case_number"),
        })
    for warning in warnings or []:
        entries.append({
            "type": "warn",
            "action": "Warning",
            "reason": warning.get("reason"),
            "mod_id": warning.get("moderator_id"),
            "timestamp": str(warning.get("created_at") or ""),
            "id": warning.get("id"),
        })
    for note in notes or []:
        entries.append({
            "type": "note",
            "action": "Note",
            "reason": note.get("note"),
            "mod_id": note.get("moderator_id"),
            "timestamp": str(note.get("created_at") or ""),
            "id": note.get("id"),
        })

    if not entries:
        embed = discord.Embed(
            title=f"History for {target.display_name}",
            description=f"{target.mention} has a clean record — no actions on file.",
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        return ToolResult.ok(
            f"{target.display_name} has no moderation history.", embed=embed, use_v2=False
        )

    def parse_ts(entry: dict) -> datetime:
        try:
            return datetime.fromisoformat(str(entry["timestamp"]).replace(" ", "T"))
        except Exception:
            return datetime.min

    entries.sort(key=parse_ts, reverse=True)

    def emoji_for(entry: dict) -> str:
        if entry["type"] == "warn":
            return "⚠️"
        if entry["type"] == "note":
            return "📝"
        action = entry["action"].lower()
        if "ban" in action:
            return "🔨"
        if "kick" in action:
            return "👢"
        if "mute" in action or "timeout" in action:
            return "🔇"
        return "🛡️"

    lines: list[str] = []
    for entry in entries[:15]:
        ts = parse_ts(entry)
        when = f"<t:{int(ts.timestamp())}:R>" if ts != datetime.min else "unknown time"
        mod = ctx.guild.get_member(entry["mod_id"]) if entry["mod_id"] else None
        mod_name = mod.display_name if mod else (f"ID:{entry['mod_id']}" if entry["mod_id"] else "automod")
        reason = str(entry["reason"] or "No reason").strip()
        if len(reason) > 60:
            reason = reason[:57] + "..."
        label = entry["action"].title()
        ref = f" (#{entry['id']})" if entry["type"] == "case" and entry["id"] else ""
        lines.append(f"{emoji_for(entry)} **{label}**{ref} • {when} • *{reason}* • by **{mod_name}**")

    embed = discord.Embed(
        title=f"Moderation record for {target.display_name}",
        description="\n".join(lines),
        color=Colors.MOD,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    summary = (
        f"{len(cases or [])} case(s) · {len(warnings or [])} warning(s) · {len(notes or [])} note(s)"
    )
    if len(entries) > 15:
        embed.set_footer(text=f"Showing recent 15 of {len(entries)} entries · {summary}")
    else:
        embed.set_footer(text=summary)
    return ToolResult.ok(
        f"Found {len(entries)} record entr{'y' if len(entries) == 1 else 'ies'} for {target.display_name}.",
        embed=embed,
        use_v2=False,
    )


@ToolRegistry.register(
    ToolType.TIMEOUT,
    display_name="Timeout Member",
    color=discord.Color.orange(),
    emoji="Muted",
    required_permission="moderate_members",
    category="members",
)
async def handle_timeout(ctx: ToolContext) -> ToolResult:
    if ctx.bool_arg("all_members"):
        return await _handle_bulk_timeout(ctx)

    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Could not resolve target member.")
    if not ctx.cog.can_moderate(ctx.actor, target):
        return ToolResult.fail(f"Cannot moderate {target.display_name} (role hierarchy).")
    bot_member = ctx.guild.me
    if not bot_member or not ctx.cog.can_moderate(bot_member, target):
        return ToolResult.fail(f"Cannot moderate {target.display_name}; their role is above mine.")

    settings = await _guild_moderation_settings(ctx)
    if _has_protected_role(ctx, target, settings):
        return ToolResult.fail(f"Cannot mute {target.display_name}; they have a protected role.")

    raw_seconds = ctx.int_arg("seconds", ctx.cog.config.timeout_default_seconds)
    seconds = max(1, min(raw_seconds, ctx.cog.config.timeout_max_seconds))
    reason = ctx.str_arg("reason")

    await target.timeout(timedelta(seconds=seconds), reason=reason)

    duration = _format_duration(seconds)
    if moderation_bool(settings, "moderation_dm_users", True):
        await _dm_moderation_action(
            target,
            guild_name=ctx.guild.name,
            action="Muted",
            reason=reason,
            duration=duration,
        )
    embed = action_embed(
        title="Muted Member Timed Out", color=discord.Color.orange(),
        actor=ctx.actor, target=target, reason=reason,
        extra={"Duration": duration},
    )
    await ctx.cog.log_action(
        message=ctx.message, action="timeout_member",
        actor=ctx.actor, target=target, reason=reason, decision=ctx.decision,
        extra={"Duration": duration},
    )
    return ToolResult.ok(
        render_moderation_response(
            settings,
            "mute",
            user=target,
            reason=reason,
            moderator=ctx.actor,
            duration=duration,
        ),
        embed=embed,
    )


async def _handle_bulk_timeout(ctx: ToolContext) -> ToolResult:
    """Timeout an explicit member set without allowing one bad target to abort it."""
    settings = await _guild_moderation_settings(ctx)
    raw_seconds = ctx.int_arg("seconds", ctx.cog.config.timeout_default_seconds)
    seconds = max(1, min(raw_seconds, ctx.cog.config.timeout_max_seconds))
    duration = _format_duration(seconds)
    reason = ctx.str_arg("reason")

    excluded_role = None
    excluded_role_query = ctx.arg("exclude_role_id") or ctx.arg("exclude_role_name")
    if excluded_role_query:
        excluded_role = await ctx.cog.resolve_role(ctx.guild, excluded_role_query)
        if not excluded_role:
            return ToolResult.fail("The excluded role was not found, so nobody was muted.")

    excluded_user_ids: set[int] = set()
    for raw_user_id in ctx.arg("exclude_user_ids", []) or []:
        try:
            excluded_user_ids.add(int(raw_user_id))
        except (TypeError, ValueError):
            continue

    bot_member = ctx.guild.me
    if not bot_member:
        return ToolResult.fail("Could not verify my server role, so nobody was muted.")

    eligible: list[discord.Member] = []
    counts = {
        "excluded_role": 0,
        "excluded_users": 0,
        "bots": 0,
        "admins": 0,
        "protected": 0,
        "hierarchy": 0,
        "failed": 0,
    }
    for member in ctx.guild.members:
        if member.id in excluded_user_ids:
            counts["excluded_users"] += 1
            continue
        if member.id == ctx.actor.id:
            continue
        if member.bot:
            counts["bots"] += 1
            continue
        if excluded_role and any(role.id == excluded_role.id for role in member.roles):
            counts["excluded_role"] += 1
            continue
        if member.id == ctx.guild.owner_id or member.guild_permissions.administrator:
            counts["admins"] += 1
            continue
        if _has_protected_role(ctx, member, settings):
            counts["protected"] += 1
            continue
        if not ctx.cog.can_moderate(ctx.actor, member) or not ctx.cog.can_moderate(bot_member, member):
            counts["hierarchy"] += 1
            continue
        eligible.append(member)

    semaphore = asyncio.Semaphore(3)

    async def apply_timeout(member: discord.Member) -> bool:
        async with semaphore:
            try:
                await member.timeout(timedelta(seconds=seconds), reason=reason)
                if moderation_bool(settings, "moderation_dm_users", True):
                    await _dm_moderation_action(
                        member,
                        guild_name=ctx.guild.name,
                        action="Muted",
                        reason=reason,
                        duration=duration,
                    )
                return True
            except (discord.Forbidden, discord.HTTPException):
                logger.warning(
                    "Discord rejected bulk timeout for user %s in guild %s",
                    member.id,
                    ctx.guild.id,
                )
                return False

    outcomes = await asyncio.gather(*(apply_timeout(member) for member in eligible))
    muted_count = sum(outcomes)
    counts["failed"] = len(outcomes) - muted_count

    excluded_role_label = excluded_role.mention if excluded_role else "None"
    excluded_members = [
        member.mention
        for member in ctx.guild.members
        if member.id in excluded_user_ids
    ]
    excluded_members_label = ", ".join(excluded_members[:25]) or "None"
    summary_parts = [
        f"Muted **{muted_count}** member(s) for **{duration}**.",
    ]
    if excluded_role:
        summary_parts.append(
            f"Excluded by role: **{counts['excluded_role']}** ({excluded_role_label})."
        )
    if excluded_user_ids:
        summary_parts.append(
            f"Explicitly excluded: **{counts['excluded_users']}** member(s)."
        )
    skipped = counts["admins"] + counts["protected"] + counts["hierarchy"]
    if skipped:
        summary_parts.append(
            f"Safely skipped **{skipped}** admin, protected, or out-of-hierarchy member(s)."
        )
    if counts["failed"]:
        summary_parts.append(f"Discord rejected **{counts['failed']}** eligible timeout(s).")
    result_message = " ".join(summary_parts)

    embed = action_embed(
        title="Bulk Member Timeout",
        color=discord.Color.orange(),
        actor=ctx.actor,
        reason=reason,
        extra={
            "Duration": duration,
            "Muted": str(muted_count),
            "Excluded Role": excluded_role_label,
            "Excluded Role Members": str(counts["excluded_role"]),
            "Excluded Members": excluded_members_label,
            "Safety Skips": str(skipped),
            "Discord Failures": str(counts["failed"]),
        },
    )
    await ctx.cog.log_action(
        message=ctx.message,
        action="bulk_timeout_members",
        actor=ctx.actor,
        target=None,
        reason=reason,
        decision=ctx.decision,
        extra={
            "Duration": duration,
            "Muted": str(muted_count),
            "Excluded Role": excluded_role_label,
            "Excluded Role Members": str(counts["excluded_role"]),
            "Excluded Members": excluded_members_label,
            "Safety Skips": str(skipped),
            "Discord Failures": str(counts["failed"]),
        },
    )
    if counts["failed"] and muted_count == 0 and eligible:
        return ToolResult.fail(result_message)
    return ToolResult.ok(result_message, embed=embed)


@ToolRegistry.register(
    ToolType.UNTIMEOUT,
    display_name="Remove Timeout",
    color=discord.Color.green(),
    emoji="Unmuted",
    required_permission="moderate_members",
    category="members",
)
async def handle_untimeout(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Could not resolve target member.")
    if not ctx.cog.can_moderate(ctx.actor, target):
        return ToolResult.fail(f"Cannot moderate {target.display_name} (role hierarchy).")
    bot_member = ctx.guild.me
    if not bot_member or not ctx.cog.can_moderate(bot_member, target):
        return ToolResult.fail(f"Cannot moderate {target.display_name}; their role is above mine.")

    is_timed_out = getattr(target, "is_timed_out", None)
    if callable(is_timed_out) and not is_timed_out():
        return ToolResult.fail(f"{target.mention} is not currently timed out.")

    settings = await _guild_moderation_settings(ctx)
    reason = ctx.str_arg("reason", "Timeout removed.")
    await target.timeout(None, reason=reason)

    embed = action_embed(
        title="Unmuted Timeout Removed", color=discord.Color.green(),
        actor=ctx.actor, target=target, reason=reason,
    )
    await ctx.cog.log_action(
        message=ctx.message, action="untimeout_member",
        actor=ctx.actor, target=target, reason=reason, decision=ctx.decision,
    )
    return ToolResult.ok(
        render_moderation_response(
            settings,
            "unmute",
            user=target,
            reason=reason,
            moderator=ctx.actor,
        ),
        embed=embed,
    )


@ToolRegistry.register(
    ToolType.KICK,
    display_name="Kick Member",
    color=discord.Color.red(),
    emoji="Kick",
    required_permission="kick_members",
    category="members",
)
async def handle_kick(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Could not resolve target member.")
    if not ctx.cog.can_moderate(ctx.actor, target):
        return ToolResult.fail(f"Cannot kick {target.display_name} (role hierarchy).")
    bot_member = ctx.guild.me
    if not bot_member or not ctx.cog.can_moderate(bot_member, target):
        return ToolResult.fail(f"Cannot kick {target.display_name}; their role is above mine.")

    settings = await _guild_moderation_settings(ctx)
    if _has_protected_role(ctx, target, settings):
        return ToolResult.fail(f"Cannot kick {target.display_name}; they have a protected role.")
    reason = ctx.str_arg("reason")
    if moderation_bool(settings, "moderation_dm_users", True):
        await _dm_moderation_action(
            target,
            guild_name=ctx.guild.name,
            action="Kicked",
            reason=reason,
        )
    await target.kick(reason=f"AI Mod ({ctx.actor}): {reason}")

    embed = action_embed(
        title="Kick Member Kicked", color=discord.Color.red(),
        actor=ctx.actor, target=target, reason=reason,
    )
    await ctx.cog.log_action(
        message=ctx.message, action="kick_member",
        actor=ctx.actor, target=target, reason=reason, decision=ctx.decision,
    )
    return ToolResult.ok(
        render_moderation_response(
            settings,
            "kick",
            user=target,
            reason=reason,
            moderator=ctx.actor,
        ),
        embed=embed,
    )


@ToolRegistry.register(
    ToolType.BAN,
    display_name="Ban Member",
    color=discord.Color.dark_red(),
    emoji="Ban",
    required_permission="ban_members",
    category="members",
)
async def handle_ban(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Could not resolve target member.")
    if not ctx.cog.can_moderate(ctx.actor, target):
        return ToolResult.fail(f"Cannot ban {target.display_name} (role hierarchy).")
    bot_member = ctx.guild.me
    if not bot_member or not ctx.cog.can_moderate(bot_member, target):
        return ToolResult.fail(f"Cannot ban {target.display_name}; their role is above mine.")

    settings = await _guild_moderation_settings(ctx)
    if _has_protected_role(ctx, target, settings):
        return ToolResult.fail(f"Cannot ban {target.display_name}; they have a protected role.")
    reason = ctx.str_arg("reason")
    requested_delete_days = max(0, min(ctx.int_arg("delete_message_days", 0), 7))
    delete_days = 0 if moderation_bool(
        settings,
        "moderation_preserve_ban_messages",
        True,
    ) else requested_delete_days
    if moderation_bool(settings, "moderation_dm_users", True):
        await _dm_moderation_action(
            target,
            guild_name=ctx.guild.name,
            action="Banned",
            reason=reason,
        )
    _suppress_duplicate_member_action_log(ctx, target.id, "ban")
    await target.ban(reason=f"AI Mod ({ctx.actor}): {reason}", delete_message_days=delete_days)

    embed = action_embed(
        title="Ban Member Banned", color=discord.Color.dark_red(),
        actor=ctx.actor, target=target, reason=reason,
        extra={"Messages Deleted": f"{delete_days} day(s)"} if delete_days else None,
    )
    await ctx.cog.log_action(
        message=ctx.message, action="ban_member",
        actor=ctx.actor, target=target, reason=reason, decision=ctx.decision,
        extra={"Delete Messages": f"{delete_days} day(s)"},
    )
    return ToolResult.ok(
        render_moderation_response(
            settings,
            "ban",
            user=target,
            reason=reason,
            moderator=ctx.actor,
        ),
        embed=embed,
    )


@ToolRegistry.register(
    ToolType.UNBAN,
    display_name="Unban Member",
    color=discord.Color.green(),
    emoji="Done",
    required_permission="ban_members",
    category="members",
)
async def handle_unban(ctx: ToolContext) -> ToolResult:
    from datetime import datetime, timezone

    from utils.embeds import compact_kv_lines

    raw_id = ctx.args.get("target_user_id")
    try:
        target_id = int(raw_id)
    except (TypeError, ValueError):
        return ToolResult.fail("Invalid user ID for unban.")

    settings = await _guild_moderation_settings(ctx)
    reason = ctx.str_arg("reason", "Unbanned.")
    target = discord.Object(id=target_id)
    try:
        ban_entry = await ctx.guild.fetch_ban(target)
    except discord.NotFound:
        return ToolResult.fail(f"<@{target_id}> is not currently banned.")

    _suppress_duplicate_member_action_log(ctx, target_id, "unban")
    await ctx.guild.unban(target, reason=f"AI Mod ({ctx.actor}): {reason}")

    embed = discord.Embed(title="User Unbanned", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
    rows: list[tuple[str, object]] = [("Moderator", ctx.actor.mention), ("Reason", reason)]
    embed.set_footer(text=f"User ID: {target_id}")
    response_user: object = f"<@{target_id}>"
    user = getattr(ban_entry, "user", None)
    if user is not None:
        response_user = user
        embed.set_author(name=user.name, icon_url=user.display_avatar.url)
        rows.insert(0, ("User", f"{user.mention} (`{user.name}`)"))
        embed.set_thumbnail(url=user.display_avatar.url)
    else:
        rows.insert(0, ("User", f"<@{target_id}> (ID: `{target_id}`)"))
    embed.description = compact_kv_lines(rows)

    await ctx.cog.log_action(
        message=ctx.message, action="unban_member",
        actor=ctx.actor, target=None, reason=reason, decision=ctx.decision,
        extra={"User ID": str(target_id)},
    )
    return ToolResult.ok(
        render_moderation_response(
            settings,
            "unban",
            user=response_user,
            reason=reason,
            moderator=ctx.actor,
        ),
        embed=embed,
    )


@ToolRegistry.register(
    ToolType.SET_NICKNAME,
    display_name="Set Nickname",
    color=discord.Color.blue(),
    emoji="Nick",
    required_permission="manage_nicknames",
    category="members",
)
async def handle_set_nickname(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Target not found.")
    if not ctx.cog.can_moderate(ctx.actor, target):
        return ToolResult.fail("Target's role is above yours.")
    bot_member = ctx.guild.me
    if not bot_member or not ctx.cog.can_moderate(bot_member, target):
        return ToolResult.fail("Target's role is above mine.")

    new_nick: Optional[str] = ctx.arg("nickname")
    if new_nick and len(new_nick) > 32:
        return ToolResult.fail("Nickname too long (max 32 characters).")

    await target.edit(nick=new_nick, reason=f"AI Mod ({ctx.actor})")
    msg = f"Nickname set to `{new_nick}`." if new_nick else "Nickname reset."
    return ToolResult.ok(msg)


@ToolRegistry.register(
    ToolType.MOVE_MEMBER,
    display_name="Move Member",
    color=discord.Color.purple(),
    emoji="Move",
    required_permission="move_members",
    category="members",
)
async def handle_move_member(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Target not found.")
    if not ctx.cog.can_moderate(ctx.actor, target):
        return ToolResult.fail(f"Cannot move {target.display_name} (role hierarchy).")
    bot_member = ctx.guild.me
    if not bot_member or not ctx.cog.can_moderate(bot_member, target):
        return ToolResult.fail(f"Cannot move {target.display_name}; their role is above mine.")
    if not target.voice:
        return ToolResult.fail(f"{target.display_name} is not in a voice channel.")

    q = str(ctx.arg("channel_name", "")).strip()
    if not q:
        return ToolResult.fail("Voice channel name or ID is required.")

    vc: Optional[discord.VoiceChannel] = None
    if q.isdigit():
        ch = ctx.guild.get_channel(int(q))
        if isinstance(ch, discord.VoiceChannel):
            vc = ch
    if not vc:
        vc = discord.utils.find(
            lambda c: isinstance(c, discord.VoiceChannel) and c.name.lower() == q.lower(),
            ctx.guild.voice_channels,
        )
    if not vc:
        return ToolResult.fail(f"Voice channel `{q}` not found.")

    await target.move_to(vc, reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok(f"Moved {target.display_name} to **{vc.name}**.")


@ToolRegistry.register(
    ToolType.DISCONNECT_MEMBER,
    display_name="Disconnect Member",
    color=discord.Color.dark_grey(),
    emoji="Disconnect",
    required_permission="move_members",
    category="members",
)
async def handle_disconnect_member(ctx: ToolContext) -> ToolResult:
    target = await ctx.resolve_target()
    if not target:
        return ToolResult.fail("Target not found.")
    if not ctx.cog.can_moderate(ctx.actor, target):
        return ToolResult.fail(f"Cannot disconnect {target.display_name} (role hierarchy).")
    bot_member = ctx.guild.me
    if not bot_member or not ctx.cog.can_moderate(bot_member, target):
        return ToolResult.fail(f"Cannot disconnect {target.display_name}; their role is above mine.")
    if not target.voice:
        return ToolResult.fail(f"{target.display_name} is not in a voice channel.")

    await target.move_to(None, reason=f"AI Mod ({ctx.actor})")
    return ToolResult.ok(f"Disconnected **{target.display_name}** from voice.")
