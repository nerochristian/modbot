"""Punishment execution for AutoMod."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import discord

from .models import Action, RuleMatch
from .utils import bot_can_act_on, compact_duration, timeout_delta
from utils.warning_escalation import apply_warning_escalation


class PunishmentResult:
    def __init__(
        self,
        action: Action,
        *,
        case_number: Optional[int] = None,
        error: Optional[str] = None,
        notification_sent: bool = False,
    ) -> None:
        self.action = action
        self.case_number = case_number
        self.error = error
        self.notification_sent = notification_sent

    @property
    def ok(self) -> bool:
        return self.error is None


class PunishmentManager:
    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot

    async def apply(
        self,
        guild: discord.Guild,
        member: discord.Member,
        action: Action,
        match: RuleMatch,
        settings: dict[str, Any],
        *,
        duration_override: Optional[int] = None,
    ) -> PunishmentResult:
        if action in {Action.NONE, Action.LOG}:
            return PunishmentResult(action)
        action = Action.TIMEOUT if action is Action.MUTE else action
        allowed, reason = bot_can_act_on(member, action.value)
        if not allowed:
            return PunishmentResult(action, error=reason)

        reason_text = f"AutoMod {match.rule}: {match.reason}"
        duration = int(duration_override or settings.get("automod_mute_duration", 3600))
        delivery_channel: Optional[discord.DMChannel] = None
        if action in {Action.KICK, Action.BAN} and settings.get("automod_notify_users", True) is not False:
            try:
                delivery_channel = await member.create_dm()
            except (discord.Forbidden, discord.HTTPException):
                delivery_channel = None
        try:
            if action is Action.WARN:
                case_number = await self._create_case(guild.id, member.id, "Warn", reason_text)
                notification_sent = await self._notify_appeal(guild, member, "Warn", reason_text, case_number, settings)
                warning_id, total = await self._add_warning(guild.id, member.id, reason_text)
                threshold_result, escalation_case = await self._apply_warning_thresholds(
                    guild, member, total, settings
                )
                # When the warn escalates, report the ESCALATION's case number.
                # This used to return the Warn's case_number alongside the
                # escalated action, so the AutoMod log embed said e.g. "Ban -
                # Case #101" while #101 was the warning row.
                if threshold_result is not None:
                    return PunishmentResult(
                        threshold_result,
                        case_number=escalation_case or case_number or warning_id,
                        notification_sent=notification_sent,
                    )
                return PunishmentResult(action, case_number=case_number or warning_id, notification_sent=notification_sent)
            if action is Action.TIMEOUT:
                await member.timeout(timeout_delta(duration), reason=reason_text)
                case_number = await self._create_case(guild.id, member.id, "Mute", reason_text, compact_duration(duration))
                notification_sent = await self._notify_appeal(
                    guild,
                    member,
                    "Mute",
                    reason_text,
                    case_number,
                    settings,
                    compact_duration(duration),
                    punishment_expires_at=datetime.now(timezone.utc) + timedelta(seconds=duration),
                )
                return PunishmentResult(action, case_number=case_number, notification_sent=notification_sent)
            if action is Action.KICK:
                await member.kick(reason=reason_text)
                case_number = await self._create_case(guild.id, member.id, "Kick", reason_text)
                notification_sent = await self._notify_appeal(
                    guild,
                    member,
                    "Kick",
                    reason_text,
                    case_number,
                    settings,
                    delivery_channel=delivery_channel,
                )
                return PunishmentResult(action, case_number=case_number, notification_sent=notification_sent)
            if action is Action.BAN:
                delete_days = 0 if settings.get(
                    "moderation_preserve_ban_messages",
                    True,
                ) else max(0, min(7, int(settings.get("automod_ban_delete_days", 1))))
                await guild.ban(member, reason=reason_text, delete_message_days=delete_days)
                case_number = await self._create_case(guild.id, member.id, "Ban", reason_text)
                notification_sent = await self._notify_appeal(
                    guild,
                    member,
                    "Ban",
                    reason_text,
                    case_number,
                    settings,
                    delivery_channel=delivery_channel,
                )
                return PunishmentResult(action, case_number=case_number, notification_sent=notification_sent)
        except discord.Forbidden:
            return PunishmentResult(action, error="Discord denied the action. Check bot role position and permissions.")
        except discord.HTTPException as exc:
            return PunishmentResult(action, error=f"Discord API error: {exc}")
        return PunishmentResult(action, error=f"Unsupported action: {action.value}")

    async def _notify_appeal(
        self,
        guild: discord.Guild,
        member: discord.Member,
        action: str,
        reason: str,
        case_number: Optional[int],
        settings: dict[str, Any],
        duration: Optional[str] = None,
        punishment_expires_at: Optional[datetime] = None,
        delivery_channel: Optional[discord.abc.Messageable] = None,
    ) -> bool:
        if not case_number or settings.get("automod_notify_users", True) is False:
            return False
        appeals = self.bot.get_cog("Appeals")
        if appeals is None or not hasattr(appeals, "notify_punishment"):
            return False
        try:
            return await appeals.notify_punishment(
                guild=guild,
                user=member,
                action=action,
                reason=reason,
                case_number=case_number,
                duration=duration,
                punishment_expires_at=punishment_expires_at,
                settings=settings,
                delivery_channel=delivery_channel,
                moderator=getattr(guild, "me", None) or getattr(self.bot, "user", None),
            )
        except Exception:
            return False

    async def create_automod_case(
        self,
        guild: discord.Guild,
        member: discord.Member,
        match: RuleMatch,
        settings: dict[str, Any],
    ) -> tuple[Optional[int], bool]:
        reason = f"AutoMod {match.rule}: {match.reason}"
        case_number = await self._create_case(guild.id, member.id, "AutoMod", reason)
        notification_sent = await self._notify_appeal(
            guild,
            member,
            "AutoMod",
            reason,
            case_number,
            settings,
        )
        return case_number, notification_sent

    async def _add_warning(self, guild_id: int, user_id: int, reason: str) -> tuple[int, int]:
        db = getattr(self.bot, "db", None)
        bot_user = getattr(self.bot, "user", None)
        moderator_id = int(getattr(bot_user, "id", 0) or user_id)
        if db is not None and hasattr(db, "add_warning"):
            return await db.add_warning(guild_id, user_id, moderator_id, reason)
        return 0, 1

    async def _create_case(self, guild_id: int, user_id: int, action: str, reason: str, duration: Optional[str] = None) -> Optional[int]:
        db = getattr(self.bot, "db", None)
        bot_user = getattr(self.bot, "user", None)
        moderator_id = int(getattr(bot_user, "id", 0) or user_id)
        if db is not None and hasattr(db, "create_case"):
            return await db.create_case(guild_id, user_id, moderator_id, action, reason, duration)
        return None

    async def _apply_warning_thresholds(
        self,
        guild: discord.Guild,
        member: discord.Member,
        total_warnings: int,
        settings: dict[str, Any],
    ) -> tuple[Optional[Action], Optional[int]]:
        """Apply any crossed warning threshold.

        Returns (escalated_action, escalation_case_number). Both are None when
        no threshold was crossed.
        """
        escalation_case: Optional[int] = None

        async def create_escalation_case(action: str, reason: str, duration_seconds: Optional[int]) -> None:
            nonlocal escalation_case
            duration = compact_duration(duration_seconds) if duration_seconds else None
            escalation_case = await self._create_case(guild.id, member.id, action, reason, duration)

        try:
            result = await apply_warning_escalation(
                guild,
                member,
                settings,
                total_warnings,
                previous_count=max(0, total_warnings - 1),
                reason_prefix="AutoMod escalation",
                ban_delete_days=max(0, min(7, int(settings.get("automod_ban_delete_days", 1)))),
                create_case=create_escalation_case,
                # The caller already DM'd the member about the warning itself
                # (_notify_appeal, just above). Letting this send its own
                # escalation DM meant one violation produced two DMs.
                skip_dm=True,
            )
            if result is not None:
                return (
                    {
                        "timeout": Action.TIMEOUT,
                        "kick": Action.KICK,
                        "ban": Action.BAN,
                    }[result.rule.action],
                    escalation_case,
                )
        except (discord.Forbidden, discord.HTTPException, TypeError, ValueError):
            return None, None
        return None, None
