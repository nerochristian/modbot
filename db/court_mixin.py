"""Court database methods (mixin for Database).

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

logger = logging.getLogger("ModBot.Database.court")


class CourtMixin:
    async def create_court_session(
        self,
        channel_id: int,
        guild_id: int,
        case_type: str,
        plaintiff_id: int,
        defendant_id: int,
        judge_id: int,
        reason: str,
    ) -> int:
        """Create a court session"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    INSERT INTO court_sessions
                    (channel_id, guild_id, case_type, plaintiff_id, defendant_id,
                     judge_id, reason, started_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')
                    """,
                    (
                        channel_id,
                        guild_id,
                        case_type,
                        plaintiff_id,
                        defendant_id,
                        judge_id,
                        reason,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                await db.commit()
                return cursor.lastrowid

    async def get_court_session(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get court session"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM court_sessions WHERE channel_id = ?",
                (channel_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "channel_id": row[1],
                "guild_id": row[2],
                "case_type": row[3],
                "plaintiff_id": row[4],
                "defendant_id": row[5],
                "judge_id": row[6],
                "reason": row[7],
                "verdict": row[8],
                "status": row[9],
                "jury_data": json.loads(row[10]) if row[10] else [],
                "started_at": row[11],
                "closed_at": row[12],
            }

    async def update_court_jury(self, channel_id: int, jury_list: List[int]) -> None:
        """Update court jury"""
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute(
                    "UPDATE court_sessions SET jury_data = ? WHERE channel_id = ?",
                    (json.dumps(jury_list), channel_id),
                )
                await db.commit()

    async def add_court_evidence(
        self,
        session_id: int,
        channel_id: int,
        title: str,
        description: str,
        link: str,
        submitted_by: int,
    ) -> int:
        """Add court evidence"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    INSERT INTO court_evidence
                    (session_id, channel_id, title, description, link,
                     submitted_by, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        channel_id,
                        title,
                        description,
                        link,
                        submitted_by,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                await db.commit()
                return cursor.lastrowid

    async def get_court_evidence(self, channel_id: int) -> List[Dict[str, Any]]:
        """Get court evidence"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM court_evidence
                WHERE channel_id = ?
                ORDER BY timestamp ASC
                """,
                (channel_id,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "session_id": r[1],
                    "channel_id": r[2],
                    "title": r[3],
                    "description": r[4],
                    "link": r[5],
                    "submitted_by": r[6],
                    "timestamp": r[7],
                }
                for r in rows
            ]

    async def add_court_vote(self, session_id: int, voter_id: int, vote: str) -> None:
        """Add court vote"""
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO court_votes
                    (session_id, voter_id, vote, timestamp)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, voter_id, vote, datetime.now(timezone.utc).isoformat()),
                )
                await db.commit()

    async def get_court_votes(self, session_id: int) -> List[Dict[str, Any]]:
        """Get court votes"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM court_votes WHERE session_id = ?",
                (session_id,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "session_id": r[1],
                    "voter_id": r[2],
                    "vote": r[3],
                    "timestamp": r[4],
                }
                for r in rows
            ]

    async def close_court_session(self, channel_id: int, verdict: str) -> None:
        """Close court session"""
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute(
                    """
                    UPDATE court_sessions
                    SET status = 'closed',
                        verdict = ?,
                        closed_at = ?
                    WHERE channel_id = ?
                    """,
                    (verdict, datetime.now(timezone.utc).isoformat(), channel_id),
                )
                await db.commit()

