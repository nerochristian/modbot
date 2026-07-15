"""Settings storage for AutoMod.

The bot normally uses the repo database. A JSON fallback is included so this
package can still be dropped into a simple discord.py project.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import default_settings, merged_settings


logger = logging.getLogger(__name__)


class AutoModStorage:
    def __init__(
        self,
        bot: object,
        path: str | Path = "data/automod_settings.json",
        *,
        cache_ttl_seconds: float = 15.0,
    ) -> None:
        self.bot = bot
        self.path = Path(path)
        self.cache_ttl_seconds = max(1.0, float(cache_ttl_seconds))
        self._cache: dict[int, tuple[float, dict[str, Any]]] = {}
        self._locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def get_settings(self, guild_id: int) -> dict[str, Any]:
        guild_id = int(guild_id)
        now = time.monotonic()
        cached = self._cache.get(guild_id)
        if cached is not None and now - cached[0] < self.cache_ttl_seconds:
            return dict(cached[1])

        async with self._locks[guild_id]:
            now = time.monotonic()
            cached = self._cache.get(guild_id)
            if cached is not None and now - cached[0] < self.cache_ttl_seconds:
                return dict(cached[1])

            try:
                settings = await self._load_settings(guild_id)
            except Exception:
                if cached is None:
                    raise
                logger.exception(
                    "Failed to refresh AutoMod settings for guild %s; using the last known configuration",
                    guild_id,
                )
                self._cache[guild_id] = (now, cached[1])
                return dict(cached[1])

            self._cache[guild_id] = (now, settings)
            return dict(settings)

    async def _load_settings(self, guild_id: int) -> dict[str, Any]:
        db = getattr(self.bot, "db", None)
        if db is not None and hasattr(db, "get_settings"):
            return merged_settings(await db.get_settings(guild_id))
        payload = self._read_file()
        return merged_settings(payload.get(str(guild_id), {}))

    async def update_settings(self, guild_id: int, changes: dict[str, Any]) -> dict[str, Any]:
        guild_id = int(guild_id)
        current = await self.get_settings(guild_id)
        current.update(changes)
        db = getattr(self.bot, "db", None)
        if db is not None and hasattr(db, "update_settings"):
            await db.update_settings(guild_id, current)
            self._cache.pop(guild_id, None)
            persisted = await self.get_settings(guild_id)
            mismatched = [
                key
                for key, expected in changes.items()
                if (key.startswith("automod_") or key in {"ignored_roles", "ignored_channels"})
                and persisted.get(key) != expected
            ]
            if mismatched:
                raise RuntimeError(
                    "AutoMod settings were not persisted: " + ", ".join(sorted(mismatched))
                )
            return persisted
        payload = self._read_file()
        payload[str(guild_id)] = current
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        self._cache[guild_id] = (time.monotonic(), dict(current))
        return current

    async def reset_settings(self, guild_id: int) -> dict[str, Any]:
        defaults = default_settings()
        db = getattr(self.bot, "db", None)
        if db is not None and hasattr(db, "update_settings"):
            await db.update_settings(int(guild_id), defaults)
            self._cache.pop(int(guild_id), None)
            return await self.get_settings(int(guild_id))
        payload = self._read_file()
        payload[str(int(guild_id))] = defaults
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        self._cache[int(guild_id)] = (time.monotonic(), dict(defaults))
        return defaults

    def _read_file(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}
