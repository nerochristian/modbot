"""Modmail database methods (mixin for Database).

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

logger = logging.getLogger("ModBot.Database.modmail")


class ModmailMixin:
    async def upsert_modmail_thread(
        self,
        guild_id: int,
        user_id: int,
        channel_id: int,
        category: str = "general",
        priority: str = "normal",
    ) -> int:
        """Create or update modmail thread"""
        async with self._lock:
            async with self.get_connection() as db:
                # Close any existing open threads
                await db.execute(
                    """
                    UPDATE modmail_threads
                    SET status = 'closed', closed_at = ?
                    WHERE guild_id = ? AND user_id = ? AND status = 'open'
                    """,
                    (datetime.now(timezone.utc).isoformat(), guild_id, user_id),
                )
                
                # Create new thread
                cursor = await db.execute(
                    """
                    INSERT INTO modmail_threads
                    (guild_id, user_id, channel_id, category, priority, opened_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'open')
                    """,
                    (
                        guild_id,
                        user_id,
                        channel_id,
                        category,
                        priority,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                
                await db.commit()
                return cursor.lastrowid

    async def get_open_modmail_thread(
        self, guild_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get open modmail thread for a user"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM modmail_threads
                WHERE guild_id = ? AND user_id = ? AND status = 'open'
                """,
                (guild_id, user_id),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "guild_id": row[1],
                "user_id": row[2],
                "channel_id": row[3],
                "category": row[4],
                "priority": row[5],
                "opened_at": row[6],
                "closed_at": row[7],
                "status": row[8],
                "claimed_by": row[9],
                "message_count": row[10],
            }

    async def close_modmail_thread(self, guild_id: int, user_id: int) -> None:
        """Close modmail thread"""
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute(
                    """
                    UPDATE modmail_threads
                    SET status = 'closed', closed_at = ?
                    WHERE guild_id = ? AND user_id = ? AND status = 'open'
                    """,
                    (datetime.now(timezone.utc).isoformat(), guild_id, user_id),
                )
                await db.commit()

    async def add_modmail_message(
        self,
        thread_id: int,
        author_id: int,
        content: str,
        is_staff: bool = False,
    ) -> int:
        """Add modmail message"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    INSERT INTO modmail_messages
                    (thread_id, author_id, content, timestamp, is_staff)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        thread_id,
                        author_id,
                        content,
                        datetime.now(timezone.utc).isoformat(),
                        int(is_staff),
                    ),
                )
                
                # Increment message count
                await db.execute(
                    """
                    UPDATE modmail_threads
                    SET message_count = message_count + 1
                    WHERE id = ?
                    """,
                    (thread_id,),
                )
                
                await db.commit()
                return cursor.lastrowid

    async def get_modmail_messages(self, thread_id: int) -> List[Dict[str, Any]]:
        """Get modmail messages"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM modmail_messages
                WHERE thread_id = ?
                ORDER BY timestamp ASC
                """,
                (thread_id,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "thread_id": r[1],
                    "author_id": r[2],
                    "content": r[3],
                    "timestamp": r[4],
                    "is_staff": bool(r[5]),
                }
                for r in rows
            ]

    async def add_modmail_block(
        self, guild_id: int, user_id: int, reason: str, blocked_by: int
    ) -> None:
        """Block user from modmail"""
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute(
                    """
                    INSERT INTO modmail_blocks
                    (guild_id, user_id, reason, blocked_by, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (guild_id, user_id, reason, blocked_by, datetime.now(timezone.utc).isoformat()),
                )
                await db.commit()

    async def remove_modmail_block(self, guild_id: int, user_id: int) -> None:
        """Unblock user from modmail"""
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute(
                    "DELETE FROM modmail_blocks WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id),
                )
                await db.commit()

    async def is_modmail_blocked(self, guild_id: int, user_id: int) -> bool:
        """Check if user is blocked from modmail"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT 1 FROM modmail_blocks WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
            return await cursor.fetchone() is not None

