"""Access database methods (mixin for Database).

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

try:
    from utils.query_builder import QueryBuilder
except Exception:
    QueryBuilder = None

logger = logging.getLogger("ModBot.Database.access")


class AccessMixin:
    async def add_to_blacklist(self, user_id: int, reason: str, added_by: int) -> bool:
        """Add a user to the global blacklist"""
        self._validate_user_id(user_id)
        self._validate_user_id(added_by)
        await self._ensure_blacklist_table()
        
        async with self._lock:
            async with self.get_connection() as db:
                try:
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO blacklist (user_id, reason, added_by)
                        VALUES (?, ?, ?)
                        """,
                        (user_id, reason, added_by),
                    )
                    await db.commit()
                    return True
                except Exception:
                    return False

    async def remove_from_blacklist(self, user_id: int) -> bool:
        """Remove a user from the global blacklist"""
        self._validate_user_id(user_id)
        await self._ensure_blacklist_table()
        
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM blacklist WHERE user_id = ?",
                    (user_id,),
                )
                await db.commit()
                return cursor.rowcount > 0

    async def get_blacklist(self) -> List[Dict[str, Any]]:
        """Get all blacklisted users"""
        await self._ensure_blacklist_table()
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT user_id, reason, added_by, created_at FROM blacklist ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
            return [
                {
                    "user_id": r[0],
                    "reason": r[1],
                    "added_by": r[2],
                    "created_at": r[3],
                }
                for r in rows
            ]

    async def is_blacklisted(self, user_id: int) -> bool:
        """Check if a user is blacklisted"""
        await self._ensure_blacklist_table()
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT 1 FROM blacklist WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            return row is not None

    async def add_whitelist(self, guild_id: int, user_id: int, added_by: int) -> bool:
        """Add user to whitelist. Returns True if added, False if already exists."""
        self._validate_guild_id(guild_id)
        self._validate_user_id(user_id)
        
        async with self._lock:
            async with self.get_connection() as db:
                try:
                    await db.execute(
                        """
                        INSERT INTO whitelist (guild_id, user_id, added_by)
                        VALUES (?, ?, ?)
                        """,
                        (guild_id, user_id, added_by),
                    )
                    await db.commit()
                    return True
                except aiosqlite.IntegrityError:
                    return False

    async def remove_whitelist(self, guild_id: int, user_id: int) -> bool:
        """Remove user from whitelist. Returns True if removed, False if not found."""
        self._validate_guild_id(guild_id)
        self._validate_user_id(user_id)
        
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM whitelist WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id),
                )
                await db.commit()
                return cursor.rowcount > 0

    async def get_whitelist(self, guild_id: int) -> List[int]:
        """Get list of whitelisted user IDs for a guild."""
        self._validate_guild_id(guild_id)
        
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT user_id FROM whitelist WHERE guild_id = ?",
                (guild_id,),
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def is_whitelisted(self, guild_id: int, user_id: int) -> bool:
        """Check if a user is whitelisted."""
        self._validate_guild_id(guild_id)
        self._validate_user_id(user_id)
        
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT 1 FROM whitelist WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
            return await cursor.fetchone() is not None

    async def clear_whitelist(self, guild_id: int) -> int:
        """Clear all whitelist entries for a guild. Returns count of removed entries."""
        self._validate_guild_id(guild_id)
        
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM whitelist WHERE guild_id = ?",
                    (guild_id,),
                )
                await db.commit()
                return cursor.rowcount

    async def upsert_risk_score(
        self, guild_id: int, user_id: int, score: int, factors: Dict[str, int]
    ) -> None:
        """Insert or update a user's risk score in a guild."""
        self._validate_guild_id(guild_id)
        self._validate_user_id(user_id)
        now = datetime.now(timezone.utc).isoformat()
        factors_json = json.dumps(factors, ensure_ascii=False)
        builder = getattr(self, "qb", None)
        async with self._lock:
            async with self.get_connection() as db:
                if builder is not None:
                    sql, params = builder.upsert(
                        "user_risk_scores",
                        conflict_columns=("guild_id", "user_id"),
                        mode="replace",
                        guild_id=guild_id,
                        user_id=user_id,
                        score=score,
                        factors=factors_json,
                        last_calculated=now,
                    )
                    await db.execute(sql, params)
                else:
                    await db.execute(
                        """
                        INSERT INTO user_risk_scores (guild_id, user_id, score, factors, last_calculated)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(guild_id, user_id) DO UPDATE SET
                            score = excluded.score,
                            factors = excluded.factors,
                            last_calculated = excluded.last_calculated
                        """,
                        (guild_id, user_id, score, factors_json, now),
                    )
                await db.commit()

    async def get_risk_score(
        self, guild_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get risk score and factor breakdown for a user."""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT score, factors, last_calculated
                FROM user_risk_scores
                WHERE guild_id = ? AND user_id = ?
                """,
                (guild_id, user_id),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "score": row[0],
                "factors": json.loads(row[1]) if row[1] else {},
                "last_calculated": row[2],
            }

    async def get_top_risky_users(
        self, guild_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get the highest-risk users in a guild."""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT user_id, score, factors, last_calculated
                FROM user_risk_scores
                WHERE guild_id = ?
                ORDER BY score DESC
                LIMIT ?
                """,
                (guild_id, limit),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "user_id": r[0],
                    "score": r[1],
                    "factors": json.loads(r[2]) if r[2] else {},
                    "last_calculated": r[3],
                }
                for r in rows
            ]

    async def store_banned_profile(
        self, user_id: int, username: str, avatar_hash: Optional[str], guild_id: int
    ) -> None:
        """Store or update a banned user's profile for alt detection."""
        self._validate_user_id(user_id)
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "SELECT banned_from_guilds FROM banned_user_profiles WHERE user_id = ?",
                    (user_id,),
                )
                existing = await cursor.fetchone()
                guilds = []
                if existing:
                    guilds = json.loads(existing[0]) if existing[0] else []
                if guild_id not in guilds:
                    guilds.append(guild_id)

                if existing:
                    await db.execute(
                        """
                        UPDATE banned_user_profiles
                        SET username = ?, avatar_hash = ?,
                            banned_at = ?, banned_from_guilds = ?
                        WHERE user_id = ?
                        """,
                        (
                            username,
                            avatar_hash,
                            datetime.now(timezone.utc).isoformat(),
                            json.dumps(guilds, ensure_ascii=False),
                            user_id,
                        ),
                    )
                else:
                    await db.execute(
                        """
                        INSERT INTO banned_user_profiles
                        (user_id, username, avatar_hash, banned_at, banned_from_guilds)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            username,
                            avatar_hash,
                            datetime.now(timezone.utc).isoformat(),
                            json.dumps(guilds, ensure_ascii=False),
                        ),
                    )
                await db.commit()

    async def get_banned_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a banned user's stored profile."""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM banned_user_profiles WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "user_id": row[0],
                "username": row[1],
                "avatar_hash": row[2],
                "banned_at": row[3],
                "banned_from_guilds": json.loads(row[4]) if row[4] else [],
            }

    async def get_all_banned_profiles(self) -> List[Dict[str, Any]]:
        """Get all stored banned user profiles."""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM banned_user_profiles ORDER BY banned_at DESC"
            )
            rows = await cursor.fetchall()
            return [
                {
                    "user_id": r[0],
                    "username": r[1],
                    "avatar_hash": r[2],
                    "banned_at": r[3],
                    "banned_from_guilds": json.loads(r[4]) if r[4] else [],
                }
                for r in rows
            ]

