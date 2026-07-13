"""Typed accessors for dashboard-managed moderation policy settings."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


DEFAULT_RESPONSE_TEMPLATES: dict[str, str] = {
    "ban": "***{user} was banned***",
    "unban": "***{user} was unbanned***",
    "softban": "***{user} was softbanned***",
    "kick": "***{user} was kicked***",
    "mute": "***{user} was muted***",
    "unmute": "***{user} was unmuted***",
}

_RESPONSE_SETTING_KEYS = {
    action: f"moderation_{action}_response"
    for action in DEFAULT_RESPONSE_TEMPLATES
}
_PLACEHOLDER_PATTERN = re.compile(r"\{([A-Za-z][A-Za-z0-9_]*)\}")
_MAX_TEMPLATE_LENGTH = 1_500
_MAX_SUBSTITUTION_LENGTH = 512
MAX_RESPONSE_LENGTH = 1_900


def moderation_bool(
    settings: Mapping[str, Any],
    key: str,
    default: bool,
) -> bool:
    """Read a dashboard boolean without treating arbitrary strings as truthy."""
    value = settings.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on", "enabled"}:
            return True
        if normalized in {"false", "0", "no", "off", "disabled"}:
            return False
    return default


def moderation_id_set(settings: Mapping[str, Any], key: str) -> set[int]:
    """Normalize a single ID, ID list, or legacy comma-separated ID string."""
    raw = settings.get(key)
    if raw is None:
        return set()

    if isinstance(raw, str):
        values: list[Any] = re.split(r"[\s,]+", raw.strip()) if raw.strip() else []
    elif isinstance(raw, (list, tuple, set, frozenset)):
        values = list(raw)
    else:
        values = [raw]

    result: set[int] = set()
    for value in values:
        if isinstance(value, bool):
            continue
        try:
            snowflake = int(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if snowflake > 0:
            result.add(snowflake)
    return result


def _bounded_text(value: Any, fallback: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        text = fallback
    return text[:_MAX_SUBSTITUTION_LENGTH]


def _user_reference(user: Any) -> str:
    mention = getattr(user, "mention", None)
    if mention:
        return _bounded_text(mention, "Unknown user")
    return _bounded_text(user, "Unknown user")


def render_moderation_response(
    settings: Mapping[str, Any],
    action: str,
    *,
    user: Any,
    reason: Any,
    moderator: Any,
    duration: Any = "",
) -> str:
    """Render a bounded action confirmation using only supported placeholders.

    Unknown placeholders are deliberately preserved as literal text. This avoids
    ``str.format`` exceptions and prevents attribute/index traversal in templates.
    """
    normalized_action = str(action).strip().lower()
    if normalized_action not in DEFAULT_RESPONSE_TEMPLATES:
        raise ValueError(f"Unsupported moderation response action: {action!r}")

    default_template = DEFAULT_RESPONSE_TEMPLATES[normalized_action]
    configured = settings.get(_RESPONSE_SETTING_KEYS[normalized_action])
    template = configured.strip() if isinstance(configured, str) else ""
    if not template:
        template = default_template
    template = template[:_MAX_TEMPLATE_LENGTH]

    include_reason = moderation_bool(
        settings,
        "moderation_respond_with_reason",
        True,
    )
    replacements = {
        "user": _user_reference(user),
        "reason": (
            _bounded_text(reason, "No reason provided") if include_reason else ""
        ),
        "moderator": _user_reference(moderator),
        "duration": _bounded_text(duration, "Not specified"),
    }

    rendered = _PLACEHOLDER_PATTERN.sub(
        lambda match: replacements.get(match.group(1), match.group(0)),
        template,
    )
    if (
        include_reason
        and "{reason}" not in template
    ):
        rendered = f"{rendered}\n**Reason:** {replacements['reason']}"

    if len(rendered) > MAX_RESPONSE_LENGTH:
        rendered = f"{rendered[: MAX_RESPONSE_LENGTH - 3].rstrip()}..."
    return rendered
