"""Tickets database methods (mixin for Database).

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

logger = logging.getLogger("ModBot.Database.tickets")


class TicketsMixin:
    async def create_ticket(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        ticket_number: int,
        category: str = "general",
        details: Optional[str] = None,
    ) -> int:
        """Create a ticket"""
        async with self._lock:
            async with self.get_connection() as db:
                details = (details or "").strip() or None
                try:
                    cursor = await db.execute(
                        """
                        INSERT INTO tickets
                        (guild_id, channel_id, user_id, ticket_number, category, details)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (guild_id, channel_id, user_id, ticket_number, category, details),
                    )
                except Exception:
                    cursor = await db.execute(
                        """
                        INSERT INTO tickets
                        (guild_id, channel_id, user_id, ticket_number, category)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (guild_id, channel_id, user_id, ticket_number, category),
                    )
                await db.commit()
                return cursor.lastrowid

    async def get_ticket(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get ticket by channel ID"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM tickets WHERE channel_id = ?", (channel_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            data = {
                "id": row[0],
                "guild_id": row[1],
                "channel_id": row[2],
                "user_id": row[3],
                "ticket_number": row[4],
                "category": row[5],
                "status": row[6],
                "created_at": row[7],
                "closed_at": row[8],
            }
            if len(row) > 9:
                data["details"] = row[9]
            if len(row) > 10:
                data["claimed_by"] = row[10]
            if len(row) > 11:
                data["claimed_at"] = row[11]
            if len(row) > 12:
                data["panel_message_id"] = row[12]
            return data

    async def claim_ticket(self, channel_id: int, staff_id: int) -> bool:
        """Claim a ticket"""
        async with self._lock:
            async with self.get_connection() as db:
                try:
                    cursor = await db.execute(
                        """
                        UPDATE tickets
                        SET claimed_by = ?, claimed_at = CURRENT_TIMESTAMP
                        WHERE channel_id = ? AND status = 'open' AND (claimed_by IS NULL OR claimed_by = 0)
                        """,
                        (staff_id, channel_id),
                    )
                    await db.commit()
                    return cursor.rowcount > 0
                except Exception:
                    return False

    async def close_ticket(self, channel_id: int) -> bool:
        """Close a ticket"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    UPDATE tickets
                    SET status = 'closed', closed_at = CURRENT_TIMESTAMP
                    WHERE channel_id = ?
                    """,
                    (channel_id,),
                )
                await db.commit()
                return cursor.rowcount > 0

    async def get_next_ticket_number(self, guild_id: int) -> int:
        """Get next ticket number"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT MAX(ticket_number) FROM tickets WHERE guild_id = ?",
                (guild_id,),
            )
            row = await cursor.fetchone()
            return (row[0] or 0) + 1

