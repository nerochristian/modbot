from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import discord

from config import Config
from utils.embeds import force_log_embed_size


def clone_embed(embed: discord.Embed) -> discord.Embed:
    return discord.Embed.from_dict(embed.to_dict())


def _get_url(obj: object, attr: str) -> Optional[str]:
    try:
        inner = getattr(obj, attr, None)
        return getattr(inner, "url", None) or None
    except Exception:
        return None


def normalize_log_embed(
    channel: Optional[discord.abc.Messageable],
    embed: discord.Embed,
    *,
    include_banner: bool = True,
) -> discord.Embed:
    """Apply the same visual normalization used by audit logs."""
    normalized = clone_embed(embed)

    if normalized.timestamp is None:
        normalized.timestamp = datetime.now(timezone.utc)

    guild = getattr(channel, "guild", None) if channel else None

    try:
        if not _get_url(normalized, "thumbnail"):
            author_icon = getattr(getattr(normalized, "author", None), "icon_url", None)
            if author_icon:
                normalized.set_thumbnail(url=author_icon)
            elif guild and getattr(guild, "icon", None):
                normalized.set_thumbnail(url=guild.icon.url)
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

    try:
        force_log_embed_size(normalized)
    except Exception:
        pass

    return normalized


async def send_log_embed(
    channel: Optional[discord.abc.Messageable],
    embed: discord.Embed,
    *,
    include_banner: bool = True,
    **kwargs: Any,
) -> None:
    """
    Send a normalized log embed with the same style used by audit logs.
    """
    if channel is None:
        return

    normalized = normalize_log_embed(channel, embed, include_banner=include_banner)

    await channel.send(embed=normalized, **kwargs)

