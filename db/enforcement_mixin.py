"""Enforcement database methods (mixin for Database).

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

logger = logging.getLogger("ModBot.Database.enforcement")


class EnforcementMixin:
    async def record_automod_event(
        self,
        guild_id: int,
        user_id: int,
        channel_id: Optional[int],
        rule: str,
        category: str,
        severity: str,
        action: str,
        reason: str,
        message_deleted: bool,
    ) -> None:
        """Persist an AutoMod decision for guild-scoped dashboard telemetry."""
        self._validate_guild_id(guild_id)
        async with self.get_connection() as db:
            await db.execute(
                """
                INSERT INTO automod_events
                    (guild_id, user_id, channel_id, rule, category, severity, action, reason, message_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    int(user_id),
                    int(channel_id) if channel_id else None,
                    str(rule)[:64],
                    str(category)[:64],
                    str(severity)[:32],
                    str(action)[:32],
                    str(reason)[:1000],
                    bool(message_deleted),
                ),
            )
            await db.commit()

    async def record_member_event(self, guild_id: int, user_id: int, event_type: str) -> None:
        """Record joins and leaves so dashboard growth charts use real events."""
        self._validate_guild_id(guild_id)
        normalized = str(event_type).strip().lower()
        if normalized not in {"join", "leave"}:
            raise ValueError(f"Invalid member event type: {event_type}")
        async with self.get_connection() as db:
            await db.execute(
                "INSERT INTO guild_member_events (guild_id, user_id, event_type) VALUES (?, ?, ?)",
                (guild_id, int(user_id), normalized),
            )
            await db.commit()

    async def add_quarantine(self, guild_id: int, user_id: int, moderator_id: int, reason: str, expires_at=None, role_ids: list = None) -> None:
        """Add a quarantine record"""
        self._validate_guild_id(guild_id)
        import json as _json
        roles_backup = _json.dumps(role_ids or [])
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute("""
                    INSERT INTO quarantines (guild_id, user_id, moderator_id, reason, roles_backup, expires_at, active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (guild_id, user_id, moderator_id, reason, roles_backup, expires_at))
                await db.commit()

    async def remove_quarantine(self, guild_id: int, user_id: int) -> None:
        """Remove (deactivate) a quarantine record"""
        self._validate_guild_id(guild_id)
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute("""
                    UPDATE quarantines SET active = 0 WHERE guild_id = ? AND user_id = ? AND active = 1
                """, (guild_id, user_id))
                await db.commit()

    async def create_report(
        self,
        guild_id: int,
        reporter_id: int,
        reported_id: int,
        reason: str,
    ) -> int:
        """Create a report"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    INSERT INTO reports (guild_id, reporter_id, reported_id, reason)
                    VALUES (?, ?, ?, ?)
                    """,
                    (guild_id, reporter_id, reported_id, reason),
                )
                await db.commit()
                return cursor.lastrowid

    async def get_reports(
        self,
        guild_id: int,
        user_id: Optional[int] = None,
        resolved: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Get reports"""
        async with self.get_connection() as db:
            query = "SELECT * FROM reports WHERE guild_id = ?"
            params: list = [guild_id]
            
            if user_id:
                query += " AND reported_id = ?"
                params.append(user_id)
            if resolved is not None:
                query += " AND resolved = ?"
                params.append(int(resolved))
            
            query += " ORDER BY created_at DESC"
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "reporter_id": r[2],
                    "reported_id": r[3],
                    "reason": r[4],
                    "resolved": r[5],
                    "resolved_by": r[6],
                    "created_at": r[7],
                }
                for r in rows
            ]

    async def resolve_report(
        self, guild_id: int, report_id: int, moderator_id: int
    ) -> bool:
        """Resolve a report"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    UPDATE reports
                    SET resolved = 1, resolved_by = ?
                    WHERE guild_id = ? AND id = ?
                    """,
                    (moderator_id, guild_id, report_id),
                )
                await db.commit()
                return cursor.rowcount > 0

    async def add_tempban(
        self,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        reason: str,
        expires_at: datetime,
    ) -> None:
        """Add a tempban"""
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute(
                    """
                    INSERT INTO tempbans
                    (guild_id, user_id, moderator_id, reason, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (guild_id, user_id, moderator_id, reason, expires_at.isoformat()),
                )
                await db.commit()

    async def get_expired_tempbans(self) -> List[Dict[str, Any]]:
        """Get expired tempbans"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM tempbans WHERE expires_at <= CURRENT_TIMESTAMP"
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "user_id": r[2],
                    "moderator_id": r[3],
                    "reason": r[4],
                    "expires_at": r[5],
                    "created_at": r[6],
                }
                for r in rows
            ]

    async def remove_tempban(self, guild_id: int, user_id: int) -> None:
        """Remove a tempban"""
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute(
                    "DELETE FROM tempbans WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id),
                )
                await db.commit()

    async def save_deleted_message_attachments(
        self,
        *,
        guild_id: int,
        channel_id: int,
        message_id: int,
        attachments: List[Dict[str, Any]],
    ) -> None:
        """Persist deleted-message attachment bytes for durable log retrieval."""
        rows = [
            (
                guild_id,
                channel_id,
                message_id,
                str(item.get("filename") or "attachment"),
                str(item.get("content_type") or ""),
                str(item.get("url") or ""),
                item.get("data"),
            )
            for item in attachments
            if item.get("data")
        ]
        if not rows:
            return

        async with self.get_connection() as db:
            await db.execute(
                """
                DELETE FROM deleted_message_attachments
                WHERE guild_id = ? AND message_id = ?
                """,
                (guild_id, message_id),
            )
            for row in rows:
                await db.execute(
                    """
                    INSERT INTO deleted_message_attachments
                    (guild_id, channel_id, message_id, filename, content_type, original_url, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
            await db.commit()

    async def get_deleted_message_attachments(
        self,
        guild_id: int,
        message_id: int,
    ) -> List[Dict[str, Any]]:
        """Return persisted deleted-message attachment bytes."""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT filename, content_type, original_url, data
                FROM deleted_message_attachments
                WHERE guild_id = ? AND message_id = ?
                ORDER BY id ASC
                """,
                (guild_id, message_id),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "filename": r[0],
                    "content_type": r[1],
                    "url": r[2],
                    "data": r[3],
                }
                for r in rows
            ]

