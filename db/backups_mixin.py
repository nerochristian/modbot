"""Backups database methods (mixin for Database).

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

logger = logging.getLogger("ModBot.Database.backups")


class BackupsMixin:
    async def backup_guild_data(self, guild_id: int) -> str:
        """
        Export guild data as JSON backup
        
        Args:
            guild_id: Guild to backup
            
        Returns:
            JSON string with all guild data
        """
        self._validate_guild_id(guild_id)
        
        backup = {
            "guild_id": guild_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "3.3.0",
            "data": {}
        }
        
        async with self.get_connection() as db:
            # Export settings
            settings = await self.get_settings(guild_id)
            backup["data"]["settings"] = settings
            
            # Export cases
            cursor = await db.execute(
                "SELECT * FROM cases WHERE guild_id = ? ORDER BY created_at DESC LIMIT 1000",
                (guild_id,)
            )
            rows = await cursor.fetchall()
            backup["data"]["cases"] = [
                {
                    "case_number": r[2],
                    "user_id": r[3],
                    "moderator_id": r[4],
                    "action": r[5],
                    "reason": r[6],
                    "duration": r[7],
                    "created_at": r[8],
                    "active": r[9]
                }
                for r in rows
            ]
            
            # Export warnings
            cursor = await db.execute(
                "SELECT * FROM warnings WHERE guild_id = ? ORDER BY created_at DESC LIMIT 1000",
                (guild_id,)
            )
            rows = await cursor.fetchall()
            backup["data"]["warnings"] = [
                {
                    "user_id": r[2],
                    "moderator_id": r[3],
                    "reason": r[4],
                    "created_at": r[5]
                }
                for r in rows
            ]
        
        return json.dumps(backup, indent=2)

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}
        
        async with self.get_connection() as db:
            tables = [
                "guild_settings", "cases", "warnings", "mod_notes",
                "reports", "tickets", "staff_sanctions", "court_sessions",
                "modmail_threads", "giveaways", "reaction_roles", "voice_roles"
            ]
            
            for table in tables:
                cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                row = await cursor.fetchone()
                stats[f"{table}_count"] = row[0] if row else 0

            if self._is_postgres:
                cursor = await db.execute(
                    """
                    SELECT ROUND(pg_database_size(current_database())::numeric / (1024 * 1024), 2)
                    """
                )
                row = await cursor.fetchone()
                stats["database_size_mb"] = float(row[0]) if row and row[0] is not None else 0.0
            else:
                cursor = await db.execute("PRAGMA page_count")
                page_count = (await cursor.fetchone())[0]
                cursor = await db.execute("PRAGMA page_size")
                page_size = (await cursor.fetchone())[0]
                stats["database_size_mb"] = round((page_count * page_size) / (1024 * 1024), 2)
        
        return stats

    async def create_server_backup(
        self,
        guild_id: int,
        created_by: int,
        backup_data: Dict[str, Any],
        triggered_by: str = "manual",
        summary: Optional[str] = None,
    ) -> int:
        """Store a server backup snapshot. Returns the backup id."""
        self._validate_guild_id(guild_id)
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    INSERT INTO server_backups
                    (guild_id, created_by, triggered_by, backup_data, summary)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        guild_id,
                        created_by,
                        triggered_by,
                        json.dumps(backup_data, ensure_ascii=False),
                        summary or "",
                    ),
                )
                await db.commit()
                return cursor.lastrowid

    async def get_server_backup(self, backup_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a single server backup by id."""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM server_backups WHERE id = ?",
                (backup_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "guild_id": row[1],
                "created_by": row[2],
                "triggered_by": row[3],
                "backup_data": json.loads(row[4]) if row[4] else {},
                "summary": row[5],
                "created_at": row[6],
            }

    async def list_server_backups(
        self, guild_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List recent server backups for a guild."""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT id, guild_id, created_by, triggered_by, summary, created_at
                FROM server_backups
                WHERE guild_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (guild_id, limit),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "created_by": r[2],
                    "triggered_by": r[3],
                    "summary": r[4],
                    "created_at": r[5],
                }
                for r in rows
            ]

    async def prune_old_backups(self, guild_id: int, keep: int = 10) -> int:
        """Keep only the most recent N backups for a guild. Returns count removed."""
        async with self._lock:
            async with self.get_connection() as db:
                # `LIMIT -1 OFFSET ?` is a SQLite-ism: on Postgres it raises
                # "LIMIT must not be negative", which auto_backup() swallowed --
                # so pruning silently never happened and backups grew forever.
                # A large literal limit is valid on both dialects.
                cursor = await db.execute(
                    """
                    SELECT id FROM server_backups
                    WHERE guild_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1000000 OFFSET ?
                    """,
                    (guild_id, keep),
                )
                old_ids = [r[0] for r in await cursor.fetchall()]
                if old_ids:
                    placeholders = ",".join("?" for _ in old_ids)
                    await db.execute(
                        f"DELETE FROM server_backups WHERE id IN ({placeholders})",
                        old_ids,
                    )
                await db.commit()
                return len(old_ids)

