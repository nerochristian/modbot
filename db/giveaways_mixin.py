"""Giveaways database methods (mixin for Database).

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

logger = logging.getLogger("ModBot.Database.giveaways")


class GiveawaysMixin:
    async def create_giveaway(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        prize: str,
        reward: Optional[str],
        description: Optional[str],
        winners: int,
        ends_at: datetime,
        host_id: int,
        bonus_role_id: Optional[int] = None,
        bonus_amount: int = 0,
        required_role_id: Optional[int] = None,
        winners_role_id: Optional[int] = None,
        image_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        banner_url: Optional[str] = None,
        dm_winners: bool = False,
    ) -> int:
        """Create a giveaway"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    INSERT INTO giveaways
                    (guild_id, channel_id, message_id, prize, reward, description, winners, ends_at, host_id, bonus_role_id, bonus_amount, required_role_id, winners_role_id, image_url, thumbnail_url, banner_url, dm_winners)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        guild_id,
                        channel_id,
                        message_id,
                        prize,
                        reward,
                        description,
                        winners,
                        ends_at.isoformat(),
                        host_id,
                        bonus_role_id,
                        bonus_amount,
                        required_role_id,
                        winners_role_id,
                        image_url,
                        thumbnail_url,
                        banner_url,
                        1 if dm_winners else 0,
                    ),
                )
                await db.commit()
                return cursor.lastrowid

    async def get_active_giveaways(self) -> List[Dict[str, Any]]:
        """Get active giveaways"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT
                    id, guild_id, channel_id, message_id, prize, reward, description, winners, ends_at, ended, host_id,
                    bonus_role_id, bonus_amount, required_role_id, winners_role_id, image_url, thumbnail_url, banner_url, dm_winners, created_at
                FROM giveaways
                WHERE ended = 0
                """
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "channel_id": r[2],
                    "message_id": r[3],
                    "prize": r[4],
                    "reward": r[5],
                    "description": r[6],
                    "winners": r[7],
                    "ends_at": r[8],
                    "ended": r[9],
                    "host_id": r[10],
                    "bonus_role_id": r[11],
                    "bonus_amount": r[12],
                    "required_role_id": r[13],
                    "winners_role_id": r[14],
                    "image_url": r[15],
                    "thumbnail_url": r[16],
                    "banner_url": r[17],
                    "dm_winners": r[18],
                    "created_at": r[19],
                }
                for r in rows
            ]

    async def get_giveaway_by_message_id(
        self, guild_id: int, message_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a giveaway by guild + message ID"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT
                    id, guild_id, channel_id, message_id, prize, reward, description, winners, ends_at, ended, host_id,
                    bonus_role_id, bonus_amount, required_role_id, winners_role_id, image_url, thumbnail_url, banner_url, dm_winners, created_at
                FROM giveaways
                WHERE guild_id = ? AND message_id = ?
                """,
                (guild_id, message_id),
            )
            r = await cursor.fetchone()
            if not r:
                return None

            return {
                "id": r[0],
                "guild_id": r[1],
                "channel_id": r[2],
                "message_id": r[3],
                "prize": r[4],
                "reward": r[5],
                "description": r[6],
                "winners": r[7],
                "ends_at": r[8],
                "ended": r[9],
                "host_id": r[10],
                "bonus_role_id": r[11],
                "bonus_amount": r[12],
                "required_role_id": r[13],
                "winners_role_id": r[14],
                "image_url": r[15],
                "thumbnail_url": r[16],
                "banner_url": r[17],
                "dm_winners": r[18],
                "created_at": r[19],
            }

    async def get_giveaway_by_id(self, guild_id: int, giveaway_id: int) -> Optional[Dict[str, Any]]:
        """Get a giveaway by guild + giveaway ID"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT
                    id, guild_id, channel_id, message_id, prize, reward, description, winners, ends_at, ended, host_id,
                    bonus_role_id, bonus_amount, required_role_id, winners_role_id, image_url, thumbnail_url, banner_url, dm_winners, created_at
                FROM giveaways
                WHERE guild_id = ? AND id = ?
                """,
                (guild_id, giveaway_id),
            )
            r = await cursor.fetchone()
            if not r:
                return None

            return {
                "id": r[0],
                "guild_id": r[1],
                "channel_id": r[2],
                "message_id": r[3],
                "prize": r[4],
                "reward": r[5],
                "description": r[6],
                "winners": r[7],
                "ends_at": r[8],
                "ended": r[9],
                "host_id": r[10],
                "bonus_role_id": r[11],
                "bonus_amount": r[12],
                "required_role_id": r[13],
                "winners_role_id": r[14],
                "image_url": r[15],
                "thumbnail_url": r[16],
                "banner_url": r[17],
                "dm_winners": r[18],
                "created_at": r[19],
            }

    async def get_giveaway_entries(self, giveaway_id: int) -> List[int]:
        """Get user IDs entered into a giveaway"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?",
                (giveaway_id,),
            )
            rows = await cursor.fetchall()
            return [int(r[0]) for r in rows]

    async def toggle_giveaway_entry(self, giveaway_id: int, user_id: int) -> bool:
        """
        Toggle a giveaway entry.
        Returns True if the user is now entered, False if withdrawn.
        """
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "SELECT 1 FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?",
                    (giveaway_id, user_id),
                )
                exists = await cursor.fetchone() is not None

                if exists:
                    await db.execute(
                        "DELETE FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?",
                        (giveaway_id, user_id),
                    )
                    await db.commit()
                    return False

                await db.execute(
                    "INSERT OR IGNORE INTO giveaway_entries (giveaway_id, user_id) VALUES (?, ?)",
                    (giveaway_id, user_id),
                )
                await db.commit()
                return True

    async def end_giveaway(self, giveaway_id: int) -> None:
        """End a giveaway"""
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute(
                    "UPDATE giveaways SET ended = 1 WHERE id = ?",
                    (giveaway_id,),
                )
                await db.commit()

