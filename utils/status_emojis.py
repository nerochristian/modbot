from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import discord

from config import Config

_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
_BRAILLE_BLANK = "\u2800"

_EMOJI_META = {
    "success": {
        "config_icon": "EMOJI_SUCCESS",
        "default_icon": "\u2705",
        "config_name": "STATUS_SUCCESS_EMOJI_NAME",
        "default_name": "mod_success",
        "asset": "emoji_success.png",
    },
    "error": {
        "config_icon": "EMOJI_ERROR",
        "default_icon": "\u274c",
        "config_name": "STATUS_ERROR_EMOJI_NAME",
        "default_name": "mod_error",
        "asset": "emoji_error.png",
    },
}

_emoji_cache: dict[tuple[int, str], str] = {}
_emoji_locks: dict[tuple[int, str], asyncio.Lock] = {}
_emoji_locks_guard = asyncio.Lock()


def _bool(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


async def _get_lock(key: tuple[int, str]) -> asyncio.Lock:
    lock = _emoji_locks.get(key)
    if lock is not None:
        return lock
    async with _emoji_locks_guard:
        lock = _emoji_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _emoji_locks[key] = lock
        return lock


def _looks_custom_emoji(value: str) -> bool:
    text = (value or "").strip()
    return text.startswith("<:") or text.startswith("<a:")


def _member_can_manage_emojis(member: Optional[discord.Member]) -> bool:
    if member is None:
        return False
    perms = getattr(member, "guild_permissions", None)
    if perms is None:
        return False
    return bool(
        getattr(perms, "manage_emojis_and_stickers", False)
        or getattr(perms, "manage_emojis", False)
    )


async def _ensure_custom_status_emoji(guild: discord.Guild, kind: str) -> Optional[str]:
    meta = _EMOJI_META.get(kind)
    if meta is None:
        return None

    key = (guild.id, kind)
    cached = _emoji_cache.get(key)
    if cached:
        return cached

    emoji_name = str(
        getattr(Config, meta["config_name"], meta["default_name"]) or meta["default_name"]
    ).strip() or meta["default_name"]

    existing = discord.utils.get(guild.emojis, name=emoji_name)
    if existing is not None:
        mention = str(existing)
        _emoji_cache[key] = mention
        return mention

    if not _bool(getattr(Config, "AUTO_CREATE_STATUS_EMOJIS", True), default=True):
        return None

    bot_member = guild.me
    if not _member_can_manage_emojis(bot_member):
        return None

    lock = await _get_lock(key)
    async with lock:
        cached = _emoji_cache.get(key)
        if cached:
            return cached

        existing = discord.utils.get(guild.emojis, name=emoji_name)
        if existing is not None:
            mention = str(existing)
            _emoji_cache[key] = mention
            return mention

        asset_path = _ASSETS_DIR / meta["asset"]
        if not asset_path.exists():
            return None

        emoji_bytes = await asyncio.to_thread(asset_path.read_bytes)
        if len(emoji_bytes) > 256 * 1024:
            return None

        try:
            created = await guild.create_custom_emoji(
                name=emoji_name,
                image=emoji_bytes,
                reason=str(
                    getattr(
                        Config,
                        "STATUS_EMOJI_CREATE_REASON",
                        "Auto-create status emojis for moderation responses.",
                    )
                ),
            )
        except (discord.Forbidden, discord.HTTPException):
            return None

        mention = str(created)
        _emoji_cache[key] = mention
        return mention


async def apply_status_emoji_overrides(
    embed: discord.Embed,
    guild: Optional[discord.Guild],
) -> discord.Embed:
    """
    Replace unicode status icons with server custom emojis when available.
    """
    if guild is None:
        return embed

    description = getattr(embed, "description", None)
    if not description:
        return embed

    updated = str(description)
    for kind, meta in _EMOJI_META.items():
        configured_icon = str(getattr(Config, meta["config_icon"], meta["default_icon"]) or "").strip()
        if not configured_icon:
            continue
        if _looks_custom_emoji(configured_icon):
            continue

        prefix = f"{configured_icon} "
        if not updated.startswith(prefix):
            continue

        mention = await _ensure_custom_status_emoji(guild, kind)
        if not mention:
            continue

        updated = updated.replace(prefix, f"{mention} ", 1)
        break

    if updated != description:
        embed.description = updated

    return embed


def status_embed_pad_line(pad_chars: int) -> str:
    if pad_chars <= 0:
        return ""
    # Keep horizontal padding invisible without adding a new quoted line.
    return _BRAILLE_BLANK * pad_chars
