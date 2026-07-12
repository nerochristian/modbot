"""Memory database methods (mixin for Database).

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

logger = logging.getLogger("ModBot.Database.memory")


class MemoryMixin:
    async def get_ai_memory(self, user_id: int) -> Optional[str]:
        """Get stored AI memory for a user."""
        self._validate_user_id(int(user_id))
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT memory_text FROM ai_memory WHERE user_id = ?",
                (int(user_id),),
            )
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

    async def get_ai_memory_record(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get stored AI memory plus metadata for admin inspection."""
        self._validate_user_id(int(user_id))
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT user_id, memory_text, last_updated FROM ai_memory WHERE user_id = ?",
                (int(user_id),),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {"user_id": row[0], "memory_text": row[1] or "", "last_updated": row[2]}

    async def update_ai_memory(self, user_id: int, memory_text: str) -> None:
        """Replace stored AI memory for a user."""
        self._validate_user_id(int(user_id))
        text = str(memory_text or "")
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO ai_memory (user_id, memory_text, last_updated)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                    (int(user_id), text),
                )
                await db.commit()

    async def clear_ai_memory(self, user_id: int) -> bool:
        """Delete stored AI memory for a user. Returns True if a row was removed."""
        self._validate_user_id(int(user_id))
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM ai_memory WHERE user_id = ?",
                    (int(user_id),),
                )
                await db.commit()
                return cursor.rowcount > 0

    async def get_guild_memory(self, guild_id: int) -> Optional[str]:
        """Get stored AI memory for a guild."""
        self._validate_guild_id(int(guild_id))
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT memory_text FROM guild_memory WHERE guild_id = ?",
                (int(guild_id),),
            )
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

    async def get_guild_memory_record(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get stored AI memory plus metadata for a guild."""
        self._validate_guild_id(int(guild_id))
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT guild_id, guild_name, memory_text, last_updated FROM guild_memory WHERE guild_id = ?",
                (int(guild_id),),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "guild_id": row[0],
                "guild_name": row[1] or "",
                "memory_text": row[2] or "",
                "last_updated": row[3],
            }

    async def update_guild_memory(self, guild_id: int, guild_name: str, memory_text: str) -> None:
        """Replace stored AI memory for a guild, keeping the name up to date."""
        self._validate_guild_id(int(guild_id))
        text = str(memory_text or "")
        name = str(guild_name or "")[:120]
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO guild_memory (guild_id, guild_name, memory_text, last_updated)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (int(guild_id), name, text),
                )
                await db.commit()

    async def clear_guild_memory(self, guild_id: int) -> bool:
        """Delete stored AI memory for a guild."""
        self._validate_guild_id(int(guild_id))
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM guild_memory WHERE guild_id = ?",
                    (int(guild_id),),
                )
                await db.commit()
                return cursor.rowcount > 0

    async def get_recent_channel_messages(
        self, channel_id: int, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve the most recent messages in a specific channel."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    SELECT message_id, channel_id, user_id, content, timestamp
                    FROM user_messages
                    WHERE channel_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (int(channel_id), int(limit)),
                )
                rows = await cursor.fetchall()
                return [
                    {
                        "message_id": row[0],
                        "channel_id": row[1],
                        "user_id": row[2],
                        "content": row[3] or "",
                        "timestamp": row[4],
                    }
                    for row in reversed(rows)
                ]
        except Exception as e:
            logger.error("Failed to get recent channel messages: %s", e)
            return []

    async def track_user_message(self, message: discord.Message) -> None:
        """Store a message for behavioral profiling."""
        if not message.guild or not message.author or message.author.bot:
            return
        content = message.content.strip()
        if not content:
            return
            
        try:
            async with self.get_connection() as db:
                await db.execute(
                    """
                    INSERT INTO user_messages (message_id, guild_id, channel_id, user_id, content)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (message.id, message.guild.id, message.channel.id, message.author.id, content)
                )
                await db.commit()
        except Exception as e:
            logger.error("Failed to track user message: %s", e)

    async def get_recent_user_messages(self, guild_id: int, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent messages for a specific user in a guild."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    SELECT message_id, channel_id, content, timestamp
                    FROM user_messages
                    WHERE guild_id = ? AND user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (guild_id, user_id, limit)
                )
                rows = await cursor.fetchall()
                # Return in chronological order
                return [
                    {
                        "message_id": row[0],
                        "channel_id": row[1],
                        "content": row[2] or "",
                        "timestamp": row[3],
                    }
                    for row in reversed(rows)
                ]
        except Exception as e:
            logger.error("Failed to get recent user messages: %s", e)
            return []

