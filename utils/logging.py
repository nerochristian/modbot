from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import discord

from config import Config

_ZWS = "\u200b"
_MAX_FIELD_VALUE = 1024
_MAX_DESCRIPTION = 4096


def _trim(text: object, limit: int) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def clone_embed(embed: discord.Embed) -> discord.Embed:
    try:
        return discord.Embed.from_dict(embed.to_dict())
    except Exception:
        # Fallback path for malformed embeds (e.g. corrupted private _fields).
        cloned = discord.Embed(
            title=getattr(embed, "title", None),
            description=getattr(embed, "description", None),
            color=getattr(embed, "color", None),
            url=getattr(embed, "url", None),
            timestamp=getattr(embed, "timestamp", None),
        )

        try:
            author = getattr(embed, "author", None)
            author_name = getattr(author, "name", None)
            author_url = getattr(author, "url", None)
            author_icon_url = getattr(author, "icon_url", None)
            if author_name:
                cloned.set_author(
                    name=author_name,
                    url=author_url,
                    icon_url=author_icon_url,
                )
        except Exception:
            pass

        try:
            footer = getattr(embed, "footer", None)
            footer_text = getattr(footer, "text", None)
            footer_icon_url = getattr(footer, "icon_url", None)
            if footer_text:
                cloned.set_footer(text=footer_text, icon_url=footer_icon_url)
        except Exception:
            pass

        try:
            thumb_url = _get_url(embed, "thumbnail")
            if thumb_url:
                cloned.set_thumbnail(url=thumb_url)
        except Exception:
            pass

        try:
            image_url = _get_url(embed, "image")
            if image_url:
                cloned.set_image(url=image_url)
        except Exception:
            pass

        raw_fields: list[object] = []
        try:
            raw_fields = list(getattr(embed, "fields", []) or [])
        except Exception:
            raw_fields = list(getattr(embed, "_fields", []) or [])

        for field in raw_fields:
            try:
                if isinstance(field, dict):
                    name = str(field.get("name", ""))
                    value = str(field.get("value", ""))
                    inline = bool(field.get("inline", False))
                else:
                    name = str(getattr(field, "name", ""))
                    value = str(getattr(field, "value", ""))
                    inline = bool(getattr(field, "inline", False))
                cloned.add_field(name=name, value=value, inline=inline)
            except Exception:
                continue

        return cloned


def _get_url(obj: object, attr: str) -> Optional[str]:
    try:
        inner = getattr(obj, attr, None)
        return getattr(inner, "url", None) or None
    except Exception:
        return None


def _log_icon(title: str) -> str:
    lowered = title.lower()
    if any(word in lowered for word in ("delete", "deleted", "left", "ban", "kick", "removed")):
        return "\U0001f6ab"
    if any(word in lowered for word in ("warn", "timeout", "lock", "slowmode", "quarantine")):
        return "\u26a0\ufe0f"
    if any(word in lowered for word in ("join", "created", "added", "unban", "unlock", "unmuted", "updated")):
        return "\u2705"
    if any(word in lowered for word in ("message", "purge", "edit")):
        return "\U0001f4dd"
    if any(word in lowered for word in ("voice", "stream", "video", "deafen", "mute")):
        return "\U0001f50a"
    return "\U0001f6e1\ufe0f"


def _looks_prefixed(title: str) -> bool:
    if not title:
        return False
    first = title.strip()[0]
    return not first.isascii() or first in {"[", "(", "{", "#"}


def _normalize_title(title: object) -> Optional[str]:
    clean = _trim(title, 240)
    if not clean:
        return None
    if _looks_prefixed(clean):
        return clean
    return f"{_log_icon(clean)} {clean}"


def _normalize_fields(embed: discord.Embed) -> None:
    fields = list(getattr(embed, "fields", []) or [])
    if not fields:
        return

    embed.clear_fields()
    for field in fields[:25]:
        name = str(getattr(field, "name", "") or "").strip()
        value = str(getattr(field, "value", "") or "").strip()
        inline = bool(getattr(field, "inline", False))

        if not value:
            continue
        if not name or name == _ZWS:
            name = "Details"

        name = _trim(name, 256)
        value = _trim(value, _MAX_FIELD_VALUE)
        if "\n" in value or len(value) > 80:
            inline = False
        embed.add_field(name=name, value=value, inline=inline)


def normalize_log_embed(
    channel: Optional[discord.abc.Messageable],
    embed: discord.Embed,
    *,
    include_banner: bool = False,
) -> discord.Embed:
    """Normalize log embeds into a compact, consistent card style."""
    normalized = clone_embed(embed)
    had_timestamp = normalized.timestamp is not None

    if normalized.timestamp is None:
        normalized.timestamp = datetime.now(timezone.utc)

    guild = getattr(channel, "guild", None) if channel else None

    try:
        normalized.title = _normalize_title(getattr(normalized, "title", None))
    except Exception:
        pass

    try:
        if normalized.description:
            normalized.description = _trim(normalized.description, _MAX_DESCRIPTION)
    except Exception:
        pass

    try:
        _normalize_fields(normalized)
    except Exception:
        pass

    try:
        # Keep thumbnails for audit-card parity; only strip large images by default.
        normalized.set_image(url=None)
    except Exception:
        pass

    try:
        # Keep log cards focused on content; thumbnails carry user identity better
        # than an extra author row on narrow Discord clients.
        normalized.remove_author()
    except Exception:
        pass

    try:
        # Footer fallback helps logs still look complete when no footer was set.
        footer = getattr(normalized, "footer", None)
        footer_text = (getattr(footer, "text", "") or "").strip()
        footer_icon = getattr(footer, "icon_url", None)
        if not footer_text and guild is not None:
            icon_url = getattr(getattr(guild, "icon", None), "url", None)
            normalized.set_footer(text=guild.name, icon_url=icon_url)
        elif footer_text:
            normalized.set_footer(text=_trim(footer_text, 2048), icon_url=footer_icon)
    except Exception:
        pass

    try:
        image_url = _get_url(normalized, "image")
        if include_banner and not image_url:
            thumb_url = _get_url(normalized, "thumbnail")
            banner_url = None
            if guild and getattr(guild, "banner", None):
                banner_url = guild.banner.url
            if not banner_url:
                banner_url = (getattr(Config, "SERVER_BANNER_URL", "") or "").strip() or None

            if banner_url:
                normalized.set_image(url=banner_url)
            elif thumb_url:
                normalized.set_image(url=thumb_url)
    except Exception:
        pass

    return normalized


async def send_log_embed(
    channel: Optional[discord.abc.Messageable],
    embed: discord.Embed,
    *,
    include_banner: bool = False,
    **kwargs: Any,
) -> None:
    """
    Send a normalized log embed with a compact, consistent style.
    """
    if channel is None:
        return

    normalized = normalize_log_embed(channel, embed, include_banner=include_banner)

    # Log channels stay on classic embeds/components v1 even if global v2
    # conversion is enabled elsewhere.
    kwargs["use_v2"] = False
    await channel.send(embed=normalized, **kwargs)

