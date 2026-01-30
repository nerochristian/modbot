"""
Advanced Database Handler - Complete Schema Support
Supports ALL cogs with auto-migration and proper async patterns
Version: 3.3.0
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import aiosqlite

logger = logging.getLogger("ModBot.Database")
DATABASE_PATH = "modbot.db"


class Database:
    """
    Main database handler with:
    - Async context manager support
    - Auto-migration for schema changes
    - Connection pooling (single persistent connection)
    - Thread-safe operations
    - Transaction support
    - Input validation
    """
    
    def __init__(self) -> None:
        self.db_path = DATABASE_PATH
        self._lock = asyncio.Lock()
        self._initialized = False
        self._pool: Optional[aiosqlite.Connection] = None

    @property
    def pool(self) -> "Database":
        """Compatibility shim for legacy call sites expecting .pool.acquire()."""
        return self

    @asynccontextmanager
    async def acquire(self):
        """Compatibility shim for legacy pool acquire."""
        await self.init_pool()
        async with self.get_connection() as conn:
            yield conn
    
    async def init_pool(self) -> None:
        """Initialize database connection pool"""
        if self._pool is None:
            self._pool = await aiosqlite.connect(self.db_path)
            # Enable WAL mode for better concurrency
            await self._pool.execute("PRAGMA journal_mode=WAL")
            await self._pool.execute("PRAGMA synchronous=NORMAL")
            # Enable foreign keys
            await self._pool.execute("PRAGMA foreign_keys=ON")
            logger.info("✅ Database connection pool initialized")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection as async context manager"""
        # Use pooled connection if available
        if self._pool is not None:
            yield self._pool
        else:
            # Fallback to creating new connection
            conn = await aiosqlite.connect(self.db_path)
            try:
                yield conn
            finally:
                await conn.close()
    
    @asynccontextmanager
    async def transaction(self):
        """
        Transaction context manager for safe database operations
        Automatically commits on success, rolls back on error
        """
        async with self._lock:
            async with self.get_connection() as conn:
                try:
                    await conn.execute("BEGIN")
                    yield conn
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise
    
    @staticmethod
    def _validate_guild_id(guild_id: int) -> None:
        """Validate guild ID"""
        if not isinstance(guild_id, int) or guild_id <= 0:
            raise ValueError(f"Invalid guild_id: {guild_id}")
    
    @staticmethod
    def _validate_user_id(user_id: int) -> None:
        """Validate user ID"""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id}")
    
    # ==================== INITIALIZATION & MIGRATION ====================
    
    async def _migrate_schema(self, db: aiosqlite.Connection) -> None:
        """Auto-migrate schema by adding missing columns"""
        migrations = [
            # modmail_threads
            ("modmail_threads", "category", "TEXT DEFAULT 'general'"),
            ("modmail_threads", "priority", "TEXT DEFAULT 'normal'"),
            ("modmail_threads", "claimed_by", "INTEGER"),
            ("modmail_threads", "message_count", "INTEGER DEFAULT 0"),
            # modmail_messages
            ("modmail_messages", "is_staff", "BOOLEAN DEFAULT 0"),
            # court_sessions
            ("court_sessions", "jury_data", "TEXT DEFAULT '[]'"),
            # staff_sanctions
            ("staff_sanctions", "sanction_type", "TEXT DEFAULT 'warn'"),
            # tickets
            ("tickets", "details", "TEXT"),
            ("tickets", "claimed_by", "INTEGER"),
            ("tickets", "claimed_at", "TIMESTAMP"),
            ("tickets", "panel_message_id", "INTEGER"),
            # giveaways
            ("giveaways", "description", "TEXT"),
            ("giveaways", "bonus_role_id", "INTEGER"),
            ("giveaways", "bonus_amount", "INTEGER DEFAULT 0"),
            ("giveaways", "required_role_id", "INTEGER"),
            ("giveaways", "winners_role_id", "INTEGER"),
            ("giveaways", "image_url", "TEXT"),
            ("giveaways", "thumbnail_url", "TEXT"),
            ("giveaways", "banner_url", "TEXT"),
            ("giveaways", "dm_winners", "BOOLEAN DEFAULT 0"),
            ("giveaways", "reward", "TEXT"),
        ]
        
        for table, column, col_type in migrations:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                logger.debug(f"✅ Added column '{column}' to '{table}'")
            except Exception:
                pass  # Column already exists
    
    async def init_guild(self, guild_id: int) -> None:
        """Initialize all database tables and ensure guild exists"""
        self._validate_guild_id(guild_id)
        
        # Ensure pool is initialized
        await self.init_pool()
        
        async with self._lock:
            async with self.get_connection() as db:
                # ===== CORE GUILD SETTINGS =====
                # Create tables first; indexes are created after schema/migrations.
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS guild_settings (
                        guild_id INTEGER PRIMARY KEY,
                        settings TEXT DEFAULT '{}'
                    )
                """)
                
                # ===== MODERATION =====
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS cases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        case_number INTEGER,
                        user_id INTEGER,
                        moderator_id INTEGER,
                        action TEXT,
                        reason TEXT,
                        duration TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        active BOOLEAN DEFAULT 1
                    )
                """)
                
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS warnings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        user_id INTEGER,
                        moderator_id INTEGER,
                        reason TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS mod_notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        user_id INTEGER,
                        moderator_id INTEGER,
                        note TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS tempbans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        user_id INTEGER,
                        moderator_id INTEGER,
                        reason TEXT,
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS mod_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        moderator_id INTEGER,
                        action TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # ===== REPORTS & TICKETS =====
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        reporter_id INTEGER,
                        reported_id INTEGER,
                        reason TEXT,
                        resolved BOOLEAN DEFAULT 0,
                        resolved_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        channel_id INTEGER,
                        user_id INTEGER,
                        ticket_number INTEGER,
                        category TEXT,
                        status TEXT DEFAULT 'open',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        closed_at TIMESTAMP
                    )
                """)
                
                # ===== STAFF SANCTIONS =====
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS staff_sanctions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        staff_id INTEGER,
                        issuer_id INTEGER,
                        reason TEXT,
                        sanction_type TEXT DEFAULT 'warn',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # ===== COURT SYSTEM =====
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS court_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel_id INTEGER,
                        guild_id INTEGER,
                        case_type TEXT,
                        plaintiff_id INTEGER,
                        defendant_id INTEGER,
                        judge_id INTEGER,
                        reason TEXT,
                        verdict TEXT,
                        status TEXT DEFAULT 'open',
                        jury_data TEXT DEFAULT '[]',
                        started_at TEXT,
                        closed_at TEXT
                    )
                """)
                
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS court_evidence (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        channel_id INTEGER,
                        title TEXT,
                        description TEXT,
                        link TEXT,
                        submitted_by INTEGER,
                        timestamp TEXT,
                        FOREIGN KEY (session_id) REFERENCES court_sessions(id)
                    )
                """)
                
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS court_votes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        voter_id INTEGER,
                        vote TEXT,
                        timestamp TEXT,
                        UNIQUE(session_id, voter_id),
                        FOREIGN KEY (session_id) REFERENCES court_sessions(id)
                    )
                """)
                
                # ===== MODMAIL SYSTEM =====
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS modmail_threads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        user_id INTEGER,
                        channel_id INTEGER,
                        category TEXT DEFAULT 'general',
                        priority TEXT DEFAULT 'normal',
                        opened_at TEXT,
                        closed_at TEXT,
                        status TEXT DEFAULT 'open',
                        claimed_by INTEGER,
                        message_count INTEGER DEFAULT 0
                    )
                """)
                
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS modmail_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        thread_id INTEGER,
                        author_id INTEGER,
                        content TEXT,
                        timestamp TEXT,
                        is_staff BOOLEAN DEFAULT 0,
                        FOREIGN KEY (thread_id) REFERENCES modmail_threads(id)
                    )
                """)
                
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS modmail_blocks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        user_id INTEGER,
                        reason TEXT,
                        blocked_by INTEGER,
                        created_at TEXT
                    )
                """)
                
                # ===== UTILITY =====
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS giveaways (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        channel_id INTEGER,
                        message_id INTEGER,
                        prize TEXT,
                        reward TEXT,
                        description TEXT,
                        winners INTEGER DEFAULT 1,
                        ends_at TIMESTAMP,
                        ended BOOLEAN DEFAULT 0,
                        host_id INTEGER,
                        bonus_role_id INTEGER,
                        bonus_amount INTEGER DEFAULT 0,
                        required_role_id INTEGER,
                        winners_role_id INTEGER,
                        image_url TEXT,
                        thumbnail_url TEXT,
                        banner_url TEXT,
                        dm_winners BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                await db.execute("""
                    CREATE TABLE IF NOT EXISTS giveaway_entries (
                        giveaway_id INTEGER,
                        user_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (giveaway_id, user_id)
                    )
                """)
                
                # ===== REACTION ROLES =====
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS reaction_roles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        message_id INTEGER,
                        emoji TEXT,
                        role_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # ===== VOICE ROLES =====
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS voice_roles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        channel_id INTEGER,
                        role_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # ===== GLOBAL BLACKLIST =====
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS blacklist (
                        user_id INTEGER PRIMARY KEY,
                        reason TEXT,
                        added_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # ===== AI MEMORY =====
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS ai_memory (
                        user_id INTEGER PRIMARY KEY,
                        memory_text TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Auto-migrate missing columns
                await self._migrate_schema(db)

                # Add indexes for better performance (best-effort).
                index_statements = [
                    """
                    CREATE INDEX IF NOT EXISTS idx_cases_guild_user
                    ON cases(guild_id, user_id)
                    """,
                    """
                    CREATE INDEX IF NOT EXISTS idx_cases_guild_active
                    ON cases(guild_id, active)
                    """,
                    """
                    CREATE INDEX IF NOT EXISTS idx_warnings_guild_user
                    ON warnings(guild_id, user_id)
                    """,
                    """
                    CREATE INDEX IF NOT EXISTS idx_mod_notes_guild_user
                    ON mod_notes(guild_id, user_id)
                    """,
                    """
                    CREATE INDEX IF NOT EXISTS idx_reports_guild_resolved
                    ON reports(guild_id, resolved)
                    """,
                    """
                    CREATE INDEX IF NOT EXISTS idx_tickets_guild_status
                    ON tickets(guild_id, status)
                    """,
                    """
                    CREATE INDEX IF NOT EXISTS idx_modmail_threads_guild_user
                    ON modmail_threads(guild_id, user_id, status)
                    """,
                ]
                for sql in index_statements:
                    try:
                        await db.execute(sql)
                    except Exception:
                        pass
                
                # Ensure guild exists
                await db.execute(
                    "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)",
                    (guild_id,),
                )
                
                await db.commit()
                
                if not self._initialized:
                    logger.info(f"✅ Initialized database for guild {guild_id}")
                    self._initialized = True
    
    # ==================== SETTINGS ====================
    
    async def get_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get guild settings"""
        self._validate_guild_id(guild_id)
        
        async with self.get_connection() as db:
            try:
                cursor = await db.execute(
                    "SELECT settings FROM guild_settings WHERE guild_id = ?",
                    (guild_id,),
                )
                row = await cursor.fetchone()
                return json.loads(row[0]) if row and row[0] else {}
            except aiosqlite.OperationalError as e:
                if "no such table: guild_settings" not in str(e).lower():
                    raise

        # Schema missing: initialize and retry once.
        await self.init_guild(guild_id)
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT settings FROM guild_settings WHERE guild_id = ?",
                (guild_id,),
            )
            row = await cursor.fetchone()
            return json.loads(row[0]) if row and row[0] else {}
    
    async def update_settings(self, guild_id: int, settings: Dict[str, Any]) -> None:
        """Update guild settings"""
        self._validate_guild_id(guild_id)
        
        async with self._lock:
            async with self.get_connection() as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO guild_settings (guild_id, settings)
                    VALUES (?, ?)
                    """,
                    (guild_id, json.dumps(settings)),
                )
                await db.commit()
    
    async def set_setting(self, guild_id: int, key: str, value: Any) -> None:
        """Set a single setting"""
        settings = await self.get_settings(guild_id)
        settings[key] = value
        await self.update_settings(guild_id, settings)
    
    # ==================== MODERATION - CASES ====================
    
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
    
    # ==================== MODERATION - WARNINGS ====================
    
    async def add_warning(
        self, guild_id: int, user_id: int, moderator_id: int, reason: str
    ) -> int:
        """Add a warning"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    INSERT INTO warnings (guild_id, user_id, moderator_id, reason)
                    VALUES (?, ?, ?, ?)
                    """,
                    (guild_id, user_id, moderator_id, reason),
                )
                await db.commit()
                return cursor.lastrowid
    
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
    
    # ==================== MODERATION - NOTES ====================
    
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
    
    # ==================== REPORTS ====================
    
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
    
    # ==================== TICKETS ====================
    
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
    
    # ==================== TEMPBANS ====================
    
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
    
    # ==================== STAFF SANCTIONS ====================
    
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
    
    # ==================== COURT SYSTEM ====================
    
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
    
    # ==================== MODMAIL SYSTEM ====================
    
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
    
    # ==================== GIVEAWAYS ====================
    
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
    
    # ==================== REACTION ROLES ====================
    
    async def add_reaction_role(
        self, guild_id: int, message_id: int, emoji: str, role_id: int
    ) -> int:
        """Add reaction role"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    INSERT INTO reaction_roles (guild_id, message_id, emoji, role_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (guild_id, message_id, emoji, role_id),
                )
                await db.commit()
                return cursor.lastrowid
    
    async def get_reaction_roles(self, message_id: int) -> List[Dict[str, Any]]:
        """Get reaction roles for a message"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM reaction_roles WHERE message_id = ?",
                (message_id,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "message_id": r[2],
                    "emoji": r[3],
                    "role_id": r[4],
                    "created_at": r[5],
                }
                for r in rows
            ]
    
    async def remove_reaction_role(self, message_id: int, emoji: str) -> bool:
        """Remove reaction role"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM reaction_roles WHERE message_id = ? AND emoji = ?",
                    (message_id, emoji),
                )
                await db.commit()
                return cursor.rowcount > 0
    
    # ==================== VOICE ROLES ====================
    
    async def add_voice_role(
        self, guild_id: int, channel_id: int, role_id: int
    ) -> int:
        """Add voice role"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    """
                    INSERT INTO voice_roles (guild_id, channel_id, role_id)
                    VALUES (?, ?, ?)
                    """,
                    (guild_id, channel_id, role_id),
                )
                await db.commit()
                return cursor.lastrowid
    
    async def get_voice_roles(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all voice roles for a guild"""
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM voice_roles WHERE guild_id = ?",
                (guild_id,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "guild_id": r[1],
                    "channel_id": r[2],
                    "role_id": r[3],
                    "created_at": r[4],
                }
                for r in rows
            ]
    
    async def remove_voice_role(self, guild_id: int, channel_id: int) -> bool:
        """Remove voice role"""
        async with self._lock:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM voice_roles WHERE guild_id = ? AND channel_id = ?",
                    (guild_id, channel_id),
                )
                await db.commit()
                return cursor.rowcount > 0
    
    # ==================== MOD STATS ====================
    
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
    
    # ==================== CLEANUP ====================
    
    async def close(self):
        """Close database connections"""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
        logger.info("🗄️ Database cleanup complete")
    
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
            # Get table sizes
            tables = [
                "guild_settings", "cases", "warnings", "mod_notes",
                "reports", "tickets", "staff_sanctions", "court_sessions",
                "modmail_threads", "giveaways", "reaction_roles", "voice_roles"
            ]
            
            for table in tables:
                cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                row = await cursor.fetchone()
                stats[f"{table}_count"] = row[0] if row else 0
            
            # Get database size
            cursor = await db.execute("PRAGMA page_count")
            page_count = (await cursor.fetchone())[0]
            cursor = await db.execute("PRAGMA page_size")
            page_size = (await cursor.fetchone())[0]
            stats["database_size_mb"] = round((page_count * page_size) / (1024 * 1024), 2)
        
        return stats
    
    # ==================== GLOBAL BLACKLIST ====================
    
    async def add_to_blacklist(self, user_id: int, reason: str, added_by: int) -> bool:
        """Add a user to the global blacklist"""
        self._validate_user_id(user_id)
        self._validate_user_id(added_by)
        
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
        async with self.get_connection() as db:
            cursor = await db.execute(
                "SELECT 1 FROM blacklist WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            return row is not None
