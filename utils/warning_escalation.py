"""Normalize and execute warning-based moderation escalations.

Both manual warnings and AutoMod warnings pass through this module so a member
is punished only when their warning total crosses a configured threshold.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional

from utils.moderation_settings import moderation_bool, moderation_id_set


MAX_RULES = 20
MAX_WARNING_COUNT = 100
MIN_TIMEOUT_SECONDS = 60
MAX_TIMEOUT_SECONDS = 28 * 24 * 60 * 60

_ACTION_SEVERITY = {"timeout": 1, "kick": 2, "ban": 3}


@dataclass(frozen=True, slots=True)
class WarningEscalationRule:
    warning_count: int
    action: str
    duration_seconds: Optional[int] = None


@dataclass(frozen=True, slots=True)
class WarningEscalationResult:
    rule: WarningEscalationRule
    reason: str


CaseCallback = Callable[[str, str, Optional[int]], Awaitable[Any]]


def _integer(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    return parsed


def _legacy_rules(settings: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not settings.get("warn_thresholds_enabled", True):
        return []
    duration = _integer(settings.get("warn_mute_duration", 3600)) or 3600
    return [
        {
            "warning_count": settings.get("warn_threshold_mute", 3),
            "action": "timeout",
            "duration_seconds": duration,
        },
        {
            "warning_count": settings.get("warn_threshold_kick", 5),
            "action": "kick",
        },
        {
            "warning_count": settings.get("warn_threshold_ban", 7),
            "action": "ban",
        },
    ]


def normalize_warning_rules(settings: Mapping[str, Any]) -> tuple[WarningEscalationRule, ...]:
    """Return safe, ordered warning escalation rules.

    ``moderation_autopunish_rules`` is authoritative, including when it is an
    empty list. ``warn_threshold_rules`` and the historic flat settings remain
    accepted for existing guilds while they migrate through the dashboard.
    Malformed rules, duplicate thresholds, and severity regressions are
    discarded defensively.
    """

    if not settings.get("warn_thresholds_enabled", True):
        return ()

    if "moderation_autopunish_rules" in settings:
        raw_rules = settings.get("moderation_autopunish_rules")
    elif "warn_threshold_rules" in settings:
        raw_rules = settings.get("warn_threshold_rules")
    else:
        raw_rules = _legacy_rules(settings)

    if not isinstance(raw_rules, Sequence) or isinstance(raw_rules, (str, bytes, bytearray)):
        return ()

    fallback_duration = _integer(settings.get("warn_mute_duration", 3600)) or 3600
    candidates: list[WarningEscalationRule] = []
    thresholds: set[int] = set()

    for raw in raw_rules:
        if len(candidates) >= MAX_RULES:
            break
        if not isinstance(raw, Mapping):
            continue

        warning_count = _integer(raw.get("warnings", raw.get("warning_count")))
        action_value = str(raw.get("action", "")).strip().lower()
        action = "timeout" if action_value == "mute" else action_value
        if (
            warning_count is None
            or not 1 <= warning_count <= MAX_WARNING_COUNT
            or warning_count in thresholds
            or action not in _ACTION_SEVERITY
        ):
            continue

        duration_seconds: Optional[int] = None
        if action == "timeout":
            if "durationMinutes" in raw:
                duration_minutes = _integer(raw.get("durationMinutes"))
                duration_seconds = duration_minutes * 60 if duration_minutes is not None else None
            else:
                duration_seconds = _integer(raw.get("duration_seconds", fallback_duration))
            if duration_seconds is None or not MIN_TIMEOUT_SECONDS <= duration_seconds <= MAX_TIMEOUT_SECONDS:
                continue

        thresholds.add(warning_count)
        candidates.append(WarningEscalationRule(warning_count, action, duration_seconds))

    candidates.sort(key=lambda rule: rule.warning_count)
    normalized: list[WarningEscalationRule] = []
    highest_severity = 0
    for rule in candidates:
        severity = _ACTION_SEVERITY[rule.action]
        if severity < highest_severity:
            continue
        normalized.append(rule)
        highest_severity = severity
    return tuple(normalized)


def crossed_warning_rule(
    settings: Mapping[str, Any],
    total_warnings: int,
    previous_count: Optional[int] = None,
) -> Optional[WarningEscalationRule]:
    """Select the highest rule crossed by this warning-count transition."""

    total = max(0, int(total_warnings))
    previous = max(0, total - 1 if previous_count is None else int(previous_count))
    if previous >= total:
        return None
    crossed = [
        rule
        for rule in normalize_warning_rules(settings)
        if previous < rule.warning_count <= total
    ]
    return crossed[-1] if crossed else None


async def apply_warning_escalation(
    guild: Any,
    member: Any,
    settings: Mapping[str, Any],
    total_warnings: int,
    *,
    previous_count: Optional[int] = None,
    reason_prefix: str = "Automatic warning escalation",
    ban_delete_days: int = 1,
    create_case: Optional[CaseCallback] = None,
) -> Optional[WarningEscalationResult]:
    """Apply the highest newly crossed rule and optionally persist its case."""

    rule = crossed_warning_rule(settings, total_warnings, previous_count)
    if rule is None:
        return None
    protected_roles = moderation_id_set(settings, "protected_roles")
    member_roles = getattr(member, "roles", ())
    if protected_roles.intersection(
        int(getattr(role, "id", 0) or 0) for role in member_roles
    ):
        return None

    reason = f"{reason_prefix}: {rule.warning_count} warnings reached"
    case_action: str
    case_duration: Optional[int] = None
    if rule.action == "timeout":
        case_action = "Mute"
        case_duration = rule.duration_seconds
    elif rule.action == "kick":
        case_action = "Kick"
    else:
        case_action = "Ban"

    if moderation_bool(settings, "moderation_dm_users", True):
        sender = getattr(member, "send", None)
        if callable(sender):
            action_label = {
                "timeout": "timed out",
                "kick": "kicked",
                "ban": "banned",
            }[rule.action]
            duration_line = (
                f"\nDuration: {rule.duration_seconds // 60} minute(s)"
                if rule.duration_seconds
                else ""
            )
            guild_name = str(getattr(guild, "name", "this server"))
            try:
                await sender(
                    f"You were {action_label} in {guild_name}.\nReason: {reason}{duration_line}"
                )
            except Exception:
                # Closed DMs must never prevent the configured punishment.
                pass

    if rule.action == "timeout":
        await member.timeout(timedelta(seconds=rule.duration_seconds or MIN_TIMEOUT_SECONDS), reason=reason)
    elif rule.action == "kick":
        await guild.kick(member, reason=reason)
    else:
        delete_days = 0 if settings.get("moderation_preserve_ban_messages", True) else max(0, min(7, int(ban_delete_days)))
        await guild.ban(member, reason=reason, delete_message_days=delete_days)

    if create_case is not None:
        await create_case(case_action, reason, case_duration)
    return WarningEscalationResult(rule=rule, reason=reason)
