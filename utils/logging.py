from __future__ import annotations

from typing import Any, Optional

import discord


def clone_embed(embed: discord.Embed) -> discord.Embed:
    return discord.Embed.from_dict(embed.to_dict())


def _get_url(obj: object, attr: str) -> Optional[str]:
    try:
        inner = getattr(obj, attr, None)
        return getattr(inner, "url", None) or None
    except Exception:
        return None


async def send_log_embed(
    channel: Optional[discord.abc.Messageable],
    embed: discord.Embed,
    **kwargs: Any,
) -> None:
    """
    Send a log embed with a consistent "square" look:
    - Prefer a top-right thumbnail (guild icon if missing)
    - If no main image is set, reuse the thumbnail as the embed image

    Note: bot.py globally patches sends to Components v2 cards; we still send an
    embed so existing code stays compatible.
    """
    if channel is None:
        return

    normalized = clone_embed(embed)

    try:
        if not _get_url(normalized, "thumbnail"):
            guild = getattr(channel, "guild", None)
            if guild and getattr(guild, "icon", None):
                normalized.set_thumbnail(url=guild.icon.url)
    except Exception:
        pass

    try:
        thumb_url = _get_url(normalized, "thumbnail")
        image_url = _get_url(normalized, "image")
        if thumb_url and not image_url:
            normalized.set_image(url=thumb_url)
    except Exception:
        pass

    await channel.send(embed=normalized, **kwargs)

