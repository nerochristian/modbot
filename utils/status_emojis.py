from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional

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
    "warning": {
        "config_icon": "EMOJI_WARNING",
        "default_icon": "\u26a0\ufe0f",
        "config_name": "STATUS_WARNING_EMOJI_NAME",
        "default_name": "mod_warning",
        "asset": "emoji_warning.png",
    },
    "info": {
        "config_icon": "EMOJI_INFO",
        "default_icon": "\u2139\ufe0f",
        "config_name": "STATUS_INFO_EMOJI_NAME",
        "default_name": "mod_info",
        "asset": "emoji_info.png",
    },
    "lock": {
        "config_icon": "EMOJI_LOCK",
        "default_icon": "\U0001f512",
        "config_name": "STATUS_LOCK_EMOJI_NAME",
        "default_name": "mod_lock",
        "asset": "emoji_lock.png",
    },
    "unlock": {
        "config_icon": "EMOJI_UNLOCK",
        "default_icon": "\U0001f513",
        "config_name": "STATUS_UNLOCK_EMOJI_NAME",
        "default_name": "mod_unlock",
        "asset": "emoji_unlock.png",
    },
    "loading": {
        "config_icon": "EMOJI_LOADING",
        "default_icon": "\u23f3",
        "config_name": "STATUS_LOADING_EMOJI_NAME",
        "default_name": "mod_loading_v2",
        # Prefer animated loading emoji when a GIF asset is available.
        "assets": ("emoji_loading.gif", "emoji_loading.png"),
    },
}

_emoji_cache: dict[tuple[int, str, str], str] = {}
_emoji_locks: dict[tuple[int, str, str], asyncio.Lock] = {}
_emoji_locks_guard = asyncio.Lock()
_application_emoji_cache: dict[tuple[str, str], str] = {}
_application_kind_cache: dict[str, str] = {}
_application_sync_lock = asyncio.Lock()


def _bool(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


async def _get_lock(key: tuple[int, str, str]) -> asyncio.Lock:
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


def _emoji_name(meta: dict[str, Any]) -> str:
    return str(
        getattr(Config, meta["config_name"], meta["default_name"]) or meta["default_name"]
    ).strip() or meta["default_name"]


def _asset_candidates(meta: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    assets = meta.get("assets")
    if isinstance(assets, (list, tuple, set, frozenset)):
        for value in assets:
            name = str(value or "").strip()
            if name and name not in candidates:
                candidates.append(name)
    asset = str(meta.get("asset", "") or "").strip()
    if asset and asset not in candidates:
        candidates.append(asset)
    return candidates


def _pick_existing_emoji(
    emojis: list[discord.Emoji],
    *,
    name: str,
    prefer_animated: bool = False,
) -> Optional[discord.Emoji]:
    same_name = [emoji for emoji in emojis if emoji.name == name]
    if not same_name:
        return None
    if prefer_animated:
        animated = next((emoji for emoji in same_name if getattr(emoji, "animated", False)), None)
        if animated is not None:
            return animated
    return same_name[0]


def _cached_application_mention(kind: str, meta: dict[str, Any]) -> Optional[str]:
    key = (kind, _emoji_name(meta))
    return _application_emoji_cache.get(key) or _application_kind_cache.get(kind)


async def sync_status_emojis_to_application(bot: discord.Client) -> dict[str, str]:
    """
    Ensure all status emojis exist in the application's emoji inventory.

    This populates a process-local cache used by embed/reaction rendering so
    status icons come from the app emoji set (Developer Portal > Emojis).
    """
    synced: dict[str, str] = {}

    try:
        existing = await bot.fetch_application_emojis()
    except Exception:
        return synced

    auto_create = _bool(getattr(Config, "AUTO_CREATE_STATUS_EMOJIS", True), default=True)
    async with _application_sync_lock:
        for kind, meta in _EMOJI_META.items():
            configured_icon = str(getattr(Config, meta["config_icon"], meta["default_icon"]) or "").strip()
            emoji_name = _emoji_name(meta)
            cache_key = (kind, emoji_name)

            # If explicitly configured as a custom emoji mention, honor it directly.
            if _looks_custom_emoji(configured_icon):
                _application_emoji_cache[cache_key] = configured_icon
                _application_kind_cache[kind] = configured_icon
                synced[kind] = configured_icon
                continue

            cached = _application_emoji_cache.get(cache_key)
            if cached:
                _application_kind_cache[kind] = cached
                synced[kind] = cached
                continue

            selected = _pick_existing_emoji(
                existing,
                name=emoji_name,
                prefer_animated=(kind == "loading"),
            )

            if selected is None and auto_create:
                for asset_name in _asset_candidates(meta):
                    asset_path = _ASSETS_DIR / asset_name
                    if not asset_path.exists():
                        continue

                    emoji_bytes = await asyncio.to_thread(asset_path.read_bytes)
                    if len(emoji_bytes) > 256 * 1024:
                        continue

                    try:
                        selected = await bot.create_application_emoji(
                            name=emoji_name,
                            image=emoji_bytes,
                        )
                    except discord.Forbidden:
                        selected = None
                        break
                    except discord.HTTPException:
                        selected = None
                        continue

                    if selected is not None:
                        existing.append(selected)
                        break

            if selected is not None:
                mention = str(selected)
                _application_emoji_cache[cache_key] = mention
                _application_kind_cache[kind] = mention
                synced[kind] = mention

    return synced


def _member_can_manage_emojis(member: Optional[discord.Member]) -> bool:
    if member is None:
        return False
    perms = getattr(member, "guild_permissions", None)
    if perms is None:
        return False
    return bool(
        getattr(perms, "manage_emojis_and_stickers", False)
        or getattr(perms, "manage_emojis", False)
        or getattr(perms, "manage_expressions", False)
    )


async def _ensure_custom_status_emoji(guild: discord.Guild, kind: str) -> Optional[str]:
    meta = _EMOJI_META.get(kind)
    if meta is None:
        return None

    emoji_name = _emoji_name(meta)
    key = (guild.id, kind, emoji_name)

    cached = _emoji_cache.get(key)
    if cached:
        return cached

    existing = _pick_existing_emoji(
        list(guild.emojis),
        name=emoji_name,
        prefer_animated=(kind == "loading"),
    )
    if existing is not None:
        mention = str(existing)
        _emoji_cache[key] = mention
        return mention

    if not _bool(getattr(Config, "AUTO_CREATE_STATUS_EMOJIS", True), default=True):
        return None

    bot_member = guild.me
    if bot_member is None:
        bot_user = getattr(guild, "_state", None)
        bot_id = getattr(getattr(bot_user, "user", None), "id", None)
        if bot_id is not None:
            bot_member = guild.get_member(bot_id)
    if not _member_can_manage_emojis(bot_member):
        return None

    lock = await _get_lock(key)
    async with lock:
        cached = _emoji_cache.get(key)
        if cached:
            return cached

        existing = _pick_existing_emoji(
            list(guild.emojis),
            name=emoji_name,
            prefer_animated=(kind == "loading"),
        )
        if existing is not None:
            mention = str(existing)
            _emoji_cache[key] = mention
            return mention

        asset_candidates = _asset_candidates(meta)

        if not asset_candidates:
            return None

        reason = str(
            getattr(
                Config,
                "STATUS_EMOJI_CREATE_REASON",
                "Auto-create status emojis for moderation responses.",
            )
        )

        for asset_name in asset_candidates:
            asset_path = _ASSETS_DIR / asset_name
            if not asset_path.exists():
                continue

            emoji_bytes = await asyncio.to_thread(asset_path.read_bytes)
            if len(emoji_bytes) > 256 * 1024:
                continue

            try:
                created = await guild.create_custom_emoji(
                    name=emoji_name,
                    image=emoji_bytes,
                    reason=reason,
                )
            except discord.Forbidden:
                return None
            except discord.HTTPException:
                continue

            mention = str(created)
            _emoji_cache[key] = mention
            return mention

        return None


async def apply_status_emoji_overrides(
    embed: discord.Embed,
    guild: Optional[discord.Guild],
) -> discord.Embed:
    """
    Replace unicode status icons with app emojis when available.
    Falls back to guild custom emojis if app-level sync is unavailable.
    """
    if guild is None:
        return embed

    description = getattr(embed, "description", None)
    title = getattr(embed, "title", None)
    if not description and not title:
        return embed

    updated_description = str(description) if description else None
    updated_title = str(title) if title else None
    changed = False

    for kind, meta in _EMOJI_META.items():
        configured_icon = str(getattr(Config, meta["config_icon"], meta["default_icon"]) or "").strip()
        if not configured_icon:
            continue
        if _looks_custom_emoji(configured_icon):
            continue

        prefix = f"{configured_icon} "
        mention = _cached_application_mention(kind, meta)

        if updated_description and updated_description.startswith(prefix):
            if mention is None:
                mention = await _ensure_custom_status_emoji(guild, kind)
            if mention:
                updated_description = updated_description.replace(prefix, f"{mention} ", 1)
                changed = True

        if updated_title and updated_title.startswith(prefix):
            if mention is None:
                mention = await _ensure_custom_status_emoji(guild, kind)
            if mention:
                updated_title = updated_title.replace(prefix, f"{mention} ", 1)
                changed = True

    if changed:
        if updated_description is not None:
            embed.description = updated_description
        if updated_title is not None:
            embed.title = updated_title

    return embed


async def get_loading_emoji_for_guild(
    guild: Optional[discord.Guild],
    *,
    configured_emoji: Optional[str] = None,
) -> str:
    """
    Resolve loading emoji with app-emoji preference and guild fallback.

    Returns a unicode/custom emoji token suitable for message content or reactions.
    """
    configured = str(
        configured_emoji
        if configured_emoji is not None
        else getattr(Config, "EMOJI_LOADING", "\u23f3")
    ).strip()
    if not configured:
        configured = "\u23f3"

    if guild is None:
        return configured
    if _looks_custom_emoji(configured):
        return configured

    loading_meta = _EMOJI_META.get("loading")
    if loading_meta is not None:
        cached_loading = _cached_application_mention("loading", loading_meta)
        if cached_loading:
            return cached_loading

    mention = await _ensure_custom_status_emoji(guild, "loading")
    if mention:
        return mention
    return configured


async def get_status_emoji_for_guild(
    guild: Optional[discord.Guild],
    *,
    kind: str,
    configured_emoji: Optional[str] = None,
) -> str:
    """
    Resolve a status emoji token for a specific kind (success/error/warning/info/etc).

    Returns a unicode/custom emoji token suitable for button emoji/content usage.
    """
    meta = _EMOJI_META.get(kind)
    if meta is None:
        raw = str(configured_emoji or "").strip()
        return raw or "?"

    configured = str(
        configured_emoji
        if configured_emoji is not None
        else getattr(Config, meta["config_icon"], meta["default_icon"])
    ).strip()
    if not configured:
        configured = str(meta["default_icon"])

    if guild is None:
        return configured
    if _looks_custom_emoji(configured):
        return configured

    cached = _cached_application_mention(kind, meta)
    if cached:
        return cached

    mention = await _ensure_custom_status_emoji(guild, kind)
    if mention:
        return mention
    return configured


def status_embed_pad_line(pad_chars: int) -> str:
    if pad_chars <= 0:
        return ""
    return _BRAILLE_BLANK * pad_chars
