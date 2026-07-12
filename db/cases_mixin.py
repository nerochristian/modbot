"""Cases database methods (mixin for Database).

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

logger = logging.getLogger("ModBot.Database.cases")


class CasesMixin:
    async def create_case(
        self,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        action: str,
        reason: str,
        duration: Optional[str] = None,
    ) -> int:
        """Create a new moderation case"""
        self._validate_guild_id(guild_id)
        self._validate_user_id(user_id)
        self._validate_user_id(moderator_id)
        
        async with self.transaction() as db:
            cursor = await db.execute(
                "SELECT MAX(case_number) FROM cases WHERE guild_id = ?",
                (guild_id,),
            )
            row = await cursor.fetchone()
            case_number = (row[0] or 0) + 1
            
            await db.execute(
                """
                INSERT INTO cases
                (guild_id, case_number, user_id, moderator_id, action, reason, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (guild_id, case_number, user_id, moderator_id, action, reason, duration),
            )
            
            await db.execute(
                "INSERT INTO mod_stats (guild_id, moderator_id, action) VALUES (?, ?, ?)",
                (guild_id, moderator_id, action),
            )
            
            return case_number

    async def get_case(self, guild_id: int, case_number: int) -> Optional[Dict[str, Any]]:
        """Get a specific case"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM cases WHERE guild_id = ? AND case_number = ?",
                (guild_id, case_number),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "guild_id": row[1],
                "case_number": row[2],
                "user_id": row[3],
                "moderator_id": row[4],
                "action": row[5],
                "reason": row[6],
                "duration": row[7],
                "created_at": row[8],
                "active": row[9],
            }

    async def update_case(self, guild_id: int, case_number: int, reason: str) -> None:
        """Update case reason"""
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute(
                    "UPDATE cases SET reason = ? WHERE guild_id = ? AND case_number = ?",
                    (reason, guild_id, case_number),
                )
                await db.commit()

    async def get_user_cases(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Get all cases for a user"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM cases
                WHERE guild_id = ? AND user_id = ?
                ORDER BY created_at DESC
                """,
                (guild_id, user_id),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "case_number": r[2],
                    "user_id": r[3],
                    "moderator_id": r[4],
                    "action": r[5],
                    "reason": r[6],
                    "duration": r[7],
                    "created_at": r[8],
                    "active": r[9],
                }
                for r in rows
            ]

    async def get_cases_by_moderator(
        self, guild_id: int, moderator_id: int
    ) -> List[Dict[str, Any]]:
        """Get all cases created by a specific moderator."""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM cases
                WHERE guild_id = ? AND moderator_id = ?
                ORDER BY created_at DESC
                """,
                (guild_id, moderator_id),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "case_number": r[2],
                    "user_id": r[3],
                    "moderator_id": r[4],
                    "action": r[5],
                    "reason": r[6],
                    "duration": r[7],
                    "created_at": r[8],
                    "active": r[9],
                }
                for r in rows
            ]

    async def add_warning(
        self, guild_id: int, user_id: int, moderator_id: int, reason: str
    ):
        """Add a warning. Returns (warning_id, total_warning_count)."""
        warning_ids, total_count = await self.add_warnings(
            guild_id=guild_id,
            user_id=user_id,
            moderator_id=moderator_id,
            reason=reason,
            count=1,
        )
        return warning_ids[0], total_count

    async def add_warnings(
        self,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        reason: str,
        count: int,
    ) -> tuple[List[int], int]:
        """Atomically add multiple warnings and return their IDs and the new total."""
        if isinstance(count, bool) or not 1 <= count <= 10:
            raise ValueError("Warning count must be between 1 and 10.")

        async with self._lock:
            async with self.get_connection() as db:
                try:
                    warning_ids: List[int] = []
                    for _ in range(count):
                        cursor = await db.execute(
                            """
                            INSERT INTO warnings (guild_id, user_id, moderator_id, reason)
                            VALUES (?, ?, ?, ?)
                            """,
                            (guild_id, user_id, moderator_id, reason),
                        )
                        warning_ids.append(cursor.lastrowid)
                    cursor2 = await db.execute(
                        "SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?",
                        (guild_id, user_id),
                    )
                    row = await cursor2.fetchone()
                    total_count = row[0] if row else count
                    await db.commit()
                    return warning_ids, total_count
                except Exception:
                    await db.rollback()
                    raise

    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Get all warnings for a user"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM warnings
                WHERE guild_id = ? AND user_id = ?
                ORDER BY created_at DESC
                """,
                (guild_id, user_id),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "user_id": r[2],
                    "moderator_id": r[3],
                    "reason": r[4],
                    "created_at": r[5],
                }
                for r in rows
            ]

    async def delete_warning(self, guild_id: int, warning_id: int) -> bool:
        """Delete a warning"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM warnings WHERE guild_id = ? AND id = ?",
                    (guild_id, warning_id),
                )
                await db.commit()
                return cursor.rowcount > 0

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        """Clear all warnings for a user"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id),
                )
                await db.commit()
                return cursor.rowcount

    async def add_note(
        self, guild_id: int, user_id: int, moderator_id: int, note: str
    ) -> int:
        """Add a mod note"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    INSERT INTO mod_notes (guild_id, user_id, moderator_id, note)
                    VALUES (?, ?, ?, ?)
                    """,
                    (guild_id, user_id, moderator_id, note),
                )
                await db.commit()
                return cursor.lastrowid

    async def get_notes(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Get all notes for a user"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM mod_notes
                WHERE guild_id = ? AND user_id = ?
                ORDER BY created_at DESC
                """,
                (guild_id, user_id),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "user_id": r[2],
                    "moderator_id": r[3],
                    "note": r[4],
                    "created_at": r[5],
                }
                for r in rows
            ]

    async def get_mod_stats(
        self, guild_id: int, moderator_id: Optional[int] = None
    ) -> Dict[str, int]:
        """Get moderation statistics"""
        async with self.get_connection() as db:
            if moderator_id:
                cursor = await db.execute(
                    """
                    SELECT action, COUNT(*)
                    FROM mod_stats
                    WHERE guild_id = ? AND moderator_id = ?
                    GROUP BY action
                    """,
                    (guild_id, moderator_id),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT action, COUNT(*)
                    FROM mod_stats
                    WHERE guild_id = ?
                    GROUP BY action
                    """,
                    (guild_id,),
                )
            
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

