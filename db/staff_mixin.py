"""Staff database methods (mixin for Database).

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

logger = logging.getLogger("ModBot.Database.staff")


class StaffMixin:
    async def add_staff_sanction(
        self,
        guild_id: int,
        staff_id: int,
        issuer_id: int,
        reason: str,
        sanction_type: str,
    ) -> int:
        """Add a staff sanction"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    INSERT INTO staff_sanctions
                    (guild_id, staff_id, issuer_id, reason, sanction_type)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (guild_id, staff_id, issuer_id, reason, sanction_type),
                )
                await db.commit()
                return cursor.lastrowid

    async def get_staff_sanctions(
        self, guild_id: int, staff_id: int
    ) -> List[Dict[str, Any]]:
        """Get staff sanctions"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM staff_sanctions
                WHERE guild_id = ? AND staff_id = ?
                ORDER BY created_at DESC
                """,
                (guild_id, staff_id),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "staff_id": r[2],
                    "issuer_id": r[3],
                    "reason": r[4],
                    "sanction_type": r[5] or "warn",
                    "created_at": r[6],
                }
                for r in rows
            ]

    async def get_all_staff_sanctions(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all staff sanctions for a guild"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM staff_sanctions
                WHERE guild_id = ?
                ORDER BY created_at DESC
                """,
                (guild_id,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "staff_id": r[2],
                    "issuer_id": r[3],
                    "reason": r[4],
                    "sanction_type": r[5] or "warn",
                    "created_at": r[6],
                }
                for r in rows
            ]

    async def remove_staff_sanction(self, guild_id: int, sanction_id: int) -> bool:
        """Remove a staff sanction"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM staff_sanctions WHERE guild_id = ? AND id = ?",
                    (guild_id, sanction_id),
                )
                await db.commit()
                return cursor.rowcount > 0

    async def clear_staff_sanctions(self, guild_id: int, staff_id: int) -> int:
        """Clear all sanctions for a staff member"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM staff_sanctions WHERE guild_id = ? AND staff_id = ?",
                    (guild_id, staff_id),
                )
                await db.commit()
                return cursor.rowcount

    async def clear_staff_warns(self, guild_id: int, staff_id: int) -> int:
        """Clear staff warnings only"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM staff_sanctions WHERE guild_id = ? AND staff_id = ? AND sanction_type = 'warn'",
                    (guild_id, staff_id),
                )
                await db.commit()
                return cursor.rowcount

    async def clear_staff_strikes(self, guild_id: int, staff_id: int) -> int:
        """Clear staff strikes only"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM staff_sanctions WHERE guild_id = ? AND staff_id = ? AND sanction_type = 'strike'",
                    (guild_id, staff_id),
                )
                await db.commit()
                return cursor.rowcount

