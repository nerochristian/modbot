"""Roles database methods (mixin for Database).

Auto-split from database.py in Phase 6. Behavior unchanged; these methods
run on the composed Database instance (self is the full Database).
"""
import discord
import asyncio
import json
import logging
import os
import shutil
import tempfile
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import aiosqlite

logger = logging.getLogger("ModBot.Database.roles")


class RolesMixin:
    async def add_reaction_role(
        self, guild_id: int, message_id: int, emoji: str, role_id: int
    ) -> int:
        """Add reaction role"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    INSERT INTO reaction_roles (guild_id, message_id, emoji, role_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (guild_id, message_id, emoji, role_id),
                )
                await db.commit()
                return cursor.lastrowid

    async def get_reaction_roles(self, message_id: int) -> List[Dict[str, Any]]:
        """Get reaction roles for a message"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM reaction_roles WHERE message_id = ?",
                (message_id,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "message_id": r[2],
                    "emoji": r[3],
                    "role_id": r[4],
                    "created_at": r[5],
                }
                for r in rows
            ]

    async def remove_reaction_role(self, message_id: int, emoji: str) -> bool:
        """Remove reaction role"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM reaction_roles WHERE message_id = ? AND emoji = ?",
                    (message_id, emoji),
                )
                await db.commit()
                return cursor.rowcount > 0

    async def add_voice_role(
        self, guild_id: int, channel_id: int, role_id: int
    ) -> int:
        """Add voice role"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    INSERT INTO voice_roles (guild_id, channel_id, role_id)
                    VALUES (?, ?, ?)
                    """,
                    (guild_id, channel_id, role_id),
                )
                await db.commit()
                return cursor.lastrowid

    async def get_voice_roles(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all voice roles for a guild"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM voice_roles WHERE guild_id = ?",
                (guild_id,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "channel_id": r[2],
                    "role_id": r[3],
                    "created_at": r[4],
                }
                for r in rows
            ]

    async def remove_voice_role(self, guild_id: int, channel_id: int) -> bool:
        """Remove voice role"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM voice_roles WHERE guild_id = ? AND channel_id = ?",
                    (guild_id, channel_id),
                )
                await db.commit()
                return cursor.rowcount > 0

