# db/database.py
import aiosqlite
import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import sqlite3
from utils.constants import Paths, EconomyConfig

class DatabaseManager:
    def __init__(self):
        self.db_path = Paths.DB_NAME
        self.logger = logging.getLogger("bot.database")
        self._connection = None

    async def get_connection(self):
        """Returns the active connection or creates a new one."""
        if not self._connection:
            self._connection = await aiosqlite.connect(self.db_path)
            # Enable Foreign Keys enforcement
            await self._connection.execute("PRAGMA foreign_keys = ON")
            # Enable Write-Ahead Logging for concurrency performance
            await self._connection.execute("PRAGMA journal_mode = WAL")
        return self._connection

    async def close(self):
        """Closes the cached connection (if one was created via `get_connection`)."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def initialize(self):
        """
        The Master Schema Builder.
        Runs on startup to ensure all tables exist.
        """
        self.logger.info("Initializing Database Schema...")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute("PRAGMA journal_mode = WAL")

            async def _table_columns(table_name: str) -> set[str]:
                try:
                    async with db.execute(f'PRAGMA table_info("{table_name}")') as cursor:
                        rows = await cursor.fetchall()
                    return {row[1] for row in rows}
                except Exception:
                    return set()

            async def _rename_if_incompatible(table_name: str, required: set[str]):
                cols = await _table_columns(table_name)
                if not cols or required.issubset(cols):
                    return

                ts = int(datetime.utcnow().timestamp())
                legacy_name = f"{table_name}_legacy_{ts}"
                try:
                    await db.execute(f'ALTER TABLE "{table_name}" RENAME TO "{legacy_name}"')
                except Exception:
                    return

            # Migrate tables whose schemas changed.
            await _rename_if_incompatible("relationships", {"user_id", "target_id"})
            await _rename_if_incompatible("guilds", {"guild_id", "owner_id", "bank"})
            await _rename_if_incompatible("guild_members", {"user_id", "guild_id", "guild_role"})
            
            # ---------------------------------------------------------
            # 1. CORE USER & ECONOMY
            # ---------------------------------------------------------
            await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                discord_id INTEGER,
                username TEXT,
                balance INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                bank_limit INTEGER DEFAULT 5000,
                net_worth INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                prestige INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_daily TIMESTAMP,
                daily_streak INTEGER DEFAULT 0,
                bio TEXT DEFAULT 'Just another citizen.',
                favorite_color TEXT DEFAULT '#3498db',
                reputation INTEGER DEFAULT 50 -- 0 (Evil) to 100 (Saint)
            )
            """)

            for stmt in (
                "ALTER TABLE users ADD COLUMN discord_id INTEGER",
                "ALTER TABLE users ADD COLUMN username TEXT",
                "ALTER TABLE users ADD COLUMN net_worth INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN favorite_color TEXT DEFAULT '#3498db'",
            ):
                try:
                    await db.execute(stmt)
                except Exception:
                    pass

            await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)")

            await db.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER PRIMARY KEY,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                health INTEGER DEFAULT 100,
                energy INTEGER DEFAULT 100,
                hunger INTEGER DEFAULT 100,
                happiness INTEGER DEFAULT 100,
                fame INTEGER DEFAULT 0,
                total_work_count INTEGER DEFAULT 0,
                crimes_committed INTEGER DEFAULT 0,
                times_jailed INTEGER DEFAULT 0,
                casino_total_bet INTEGER DEFAULT 0,
                casino_total_won INTEGER DEFAULT 0,
                last_work TEXT,
                last_sleep TEXT,
                last_rob TEXT,
                last_crime TEXT,
                hospital_until TEXT,
                jail_until TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS user_meta (
                user_id INTEGER,
                key TEXT,
                value TEXT,
                PRIMARY KEY (user_id, key),
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS user_skills (
                user_id INTEGER,
                skill_name TEXT,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, skill_name),
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS user_command_stats (
                user_id INTEGER,
                command_name TEXT,
                times_used INTEGER DEFAULT 0,
                last_used TEXT,
                PRIMARY KEY (user_id, command_name),
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                achievement_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT,
                rarity TEXT DEFAULT 'common',
                category TEXT,
                points INTEGER DEFAULT 0
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                user_id INTEGER,
                achievement_id TEXT,
                unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, achievement_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (achievement_id) REFERENCES achievements (achievement_id) ON DELETE CASCADE
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                item_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT,
                rarity INTEGER DEFAULT 0,
                category TEXT,
                price INTEGER DEFAULT 0
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS user_inventory (
                user_id INTEGER,
                item_id TEXT,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, item_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES items (item_id) ON DELETE CASCADE
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS user_investments (
                investment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                investment_type TEXT,
                amount INTEGER,
                invested_at TEXT,
                active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS user_loans (
                loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                interest_rate REAL,
                total_debt INTEGER,
                borrowed_at TEXT,
                active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                property_id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                property_type TEXT,
                name TEXT,
                level INTEGER DEFAULT 1,
                rent_per_hour INTEGER DEFAULT 0,
                last_collected TEXT,
                FOREIGN KEY (owner_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            """)

            # ---------------------------------------------------------
            # 2. INVENTORY & ITEMS
            # ---------------------------------------------------------
            await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_id TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                durability INTEGER DEFAULT 100, -- For tools
                obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            """)
            
            # Index for faster inventory lookups
            await db.execute("CREATE INDEX IF NOT EXISTS idx_inventory_user ON inventory(user_id)")

            # ---------------------------------------------------------
            # 3. JOBS & CAREERS
            # ---------------------------------------------------------
            await db.execute("""
            CREATE TABLE IF NOT EXISTS user_jobs (
                user_id INTEGER PRIMARY KEY,
                job_id TEXT,
                current_position TEXT,
                shifts_worked INTEGER DEFAULT 0,
                promotions INTEGER DEFAULT 0,
                last_worked TIMESTAMP,
                salary_bonus_percent INTEGER DEFAULT 0,
                salary INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            """)

            try:
                await db.execute("ALTER TABLE user_jobs ADD COLUMN salary INTEGER DEFAULT 0")
            except Exception:
                pass

            # ---------------------------------------------------------
            # 4. CRIME & JUSTICE
            # ---------------------------------------------------------
            await db.execute("""
            CREATE TABLE IF NOT EXISTS criminal_records (
                user_id INTEGER PRIMARY KEY,
                crimes_committed INTEGER DEFAULT 0,
                successful_heists INTEGER DEFAULT 0,
                times_jailed INTEGER DEFAULT 0,
                total_bounty INTEGER DEFAULT 0,
                jail_release_time TIMESTAMP,
                heat_level INTEGER DEFAULT 0, -- Higher heat = higher police chance
                last_crime_time TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            """)

            # ---------------------------------------------------------
            # 5. BUSINESSES (TYCOON)
            # ---------------------------------------------------------
            await db.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                business_id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                name TEXT,
                type TEXT, -- e.g., 'lemonade', 'tech_startup', 'oil_rig'
                level INTEGER DEFAULT 1,
                balance INTEGER DEFAULT 0, -- Money stored in business
                revenue_rate INTEGER DEFAULT 0, -- Coins per hour
                last_collection TIMESTAMP,
                employees INTEGER DEFAULT 0,
                FOREIGN KEY (owner_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            """)

            # ---------------------------------------------------------
            # 6. STOCKS & CRYPTO
            # ---------------------------------------------------------
            # Holds the user's portfolio
            await db.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                asset_symbol TEXT, -- e.g., 'BTC', 'TSLA'
                amount REAL DEFAULT 0.0,
                avg_buy_price REAL DEFAULT 0.0,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            """)

            # Holds the current market state (Global)
            await db.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                symbol TEXT PRIMARY KEY,
                current_price REAL,
                history TEXT, -- JSON string of past prices
                volatility REAL, -- How much it moves
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # ---------------------------------------------------------
            # 7. FAMILY & MARRIAGE
            # ---------------------------------------------------------
            await db.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                user_id TEXT,
                target_id TEXT,
                affection INTEGER DEFAULT 0,
                status TEXT DEFAULT 'stranger',
                relationship_type TEXT DEFAULT 'friend',
                relationship_level INTEGER DEFAULT 0,
                last_interaction TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, target_id)
            )
            """)

            await db.execute("CREATE INDEX IF NOT EXISTS idx_relationships_user ON relationships(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id)")
            
            await db.execute("""
            CREATE TABLE IF NOT EXISTS children (
                child_id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                name TEXT,
                age INTEGER DEFAULT 0,
                happiness INTEGER DEFAULT 100,
                smartness INTEGER DEFAULT 50,
                last_interaction TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES users (user_id)
            )
            """)

            # ---------------------------------------------------------
            # 8. PETS
            # ---------------------------------------------------------
            await db.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                pet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                name TEXT,
                type TEXT, -- 'dog', 'cat', 'dragon'
                skin TEXT DEFAULT 'default',
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                hunger INTEGER DEFAULT 100, -- 100 is full
                energy INTEGER DEFAULT 100,
                happiness INTEGER DEFAULT 100,
                last_fed TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users (user_id)
            )
            """)

            # ---------------------------------------------------------
            # 9. GUILDS
            # ---------------------------------------------------------
            await db.execute("""
            CREATE TABLE IF NOT EXISTS guilds (
                guild_id TEXT PRIMARY KEY,
                name TEXT UNIQUE,
                owner_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                member_count INTEGER DEFAULT 1,
                perks TEXT DEFAULT '[]',
                description TEXT DEFAULT '',
                icon TEXT
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_members (
                user_id TEXT PRIMARY KEY,
                guild_id TEXT,
                guild_role TEXT DEFAULT 'member',
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                contribution INTEGER DEFAULT 0,
                FOREIGN KEY (guild_id) REFERENCES guilds (guild_id) ON DELETE CASCADE
            )
            """)

            # ---------------------------------------------------------
            # 10. TRANSACTION LOGS (AUDIT)
            # ---------------------------------------------------------
            await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                type TEXT, -- 'transfer', 'shop_buy', 'fine'
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Seed achievements/items (best-effort)
            try:
                from data.achievements import ACHIEVEMENTS as ACHIEVEMENTS_SEED

                for ach_id, ach in ACHIEVEMENTS_SEED.items():
                    await db.execute(
                        """
                        INSERT OR IGNORE INTO achievements
                            (achievement_id, name, description, icon, rarity, category, points)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            ach_id,
                            ach.get("name", ach_id),
                            ach.get("description", ""),
                            ach.get("emoji", ""),
                            ach.get("tier", "common"),
                            ach.get("category"),
                            int(ach.get("reward", {}).get("xp", 0)),
                        ),
                    )
            except Exception as e:
                self.logger.warning(f"Failed to seed achievements: {e}")

            try:
                items_seed: dict[str, dict] = {}

                try:
                    from data import items as items_module

                    for name, value in vars(items_module).items():
                        if not name.isupper() or not isinstance(value, dict):
                            continue
                        for item_id, item in value.items():
                            if isinstance(item_id, str) and isinstance(item, dict):
                                items_seed.setdefault(item_id, item)
                except Exception:
                    pass

                try:
                    from views.shop_views import SHOP_ITEMS as SHOP_ITEMS_SEED

                    for item_id, item in SHOP_ITEMS_SEED.items():
                        if isinstance(item_id, str) and isinstance(item, dict):
                            items_seed.setdefault(item_id, item)
                except Exception:
                    pass

                rarity_map = {
                    "collectibles": 3,
                    "vehicles": 2,
                    "tools": 2,
                    "housing": 2,
                    "pets": 2,
                    "consumables": 1,
                    "food": 1,
                    "ingredients": 0,
                    "other": 0,
                }

                for item_id, item in items_seed.items():
                    category = item.get("category", "other")
                    rarity = rarity_map.get(category, 0)
                    await db.execute(
                        """
                        INSERT OR IGNORE INTO items
                            (item_id, name, description, icon, rarity, category, price)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item_id,
                            item.get("name", item_id),
                            item.get("description", ""),
                            item.get("emoji") or item.get("icon") or "",
                            rarity,
                            category,
                            int(item.get("price", 0) or 0),
                        ),
                    )
            except Exception as e:
                self.logger.warning(f"Failed to seed items: {e}")

            await db.commit()
            self.logger.info("Database Schema Initialized Successfully.")

    # ------------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------------

    async def fetch_one(self, query: str, *args):
        """
        Executes a SELECT query and returns a single row as a dictionary.
        Safe against SQL injection by using parameterized queries (*args).
        """
        params = args[0] if len(args) == 1 and isinstance(args[0], (tuple, list)) else args

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def fetch_all(self, query: str, *args):
        """
        Executes a SELECT query and returns all rows as a list of dictionaries.
        """
        params = args[0] if len(args) == 1 and isinstance(args[0], (tuple, list)) else args

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def execute(self, query: str, *args):
        """
        Executes an INSERT, UPDATE, or DELETE query.
        Returns the ID of the last inserted row (if applicable).
        """
        params = args[0] if len(args) == 1 and isinstance(args[0], (tuple, list)) else args

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.lastrowid
            
    async def execute_script(self, script: str):
        """Executes a raw SQL script (multiple statements)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(script)
            await db.commit()

    # ------------------------------------------------------------------
    # LEGACY / SYNC COMPATIBILITY API (used by many cogs/views)
    # ------------------------------------------------------------------

    def _connect_sync(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _coerce_int_id(value) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def ensure_user(self, user_id) -> bool:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return False

        with self._connect_sync() as conn:
            exists = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (uid,)).fetchone()
            if not exists:
                balance = int(getattr(EconomyConfig, "STARTING_BALANCE", 0))
                bank = int(getattr(EconomyConfig, "STARTING_BANK", 0))
                bank_limit = int(getattr(EconomyConfig, "STARTING_BANK_LIMIT", 5000))
                conn.execute(
                    """
                    INSERT INTO users (user_id, discord_id, balance, bank, bank_limit, net_worth)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (uid, uid, balance, bank, bank_limit, balance + bank),
                )

            stats_exists = conn.execute("SELECT 1 FROM user_stats WHERE user_id = ?", (uid,)).fetchone()
            if not stats_exists:
                conn.execute("INSERT INTO user_stats (user_id) VALUES (?)", (uid,))

        return True

    def getuser(self, user_id: str) -> dict:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return {}

        self.ensure_user(uid)

        with self._connect_sync() as conn:
            user_row = conn.execute("SELECT * FROM users WHERE user_id = ?", (uid,)).fetchone()
            stats_row = conn.execute("SELECT * FROM user_stats WHERE user_id = ?", (uid,)).fetchone()

            data: dict = {}
            if user_row:
                data.update(dict(user_row))
            if stats_row:
                data.update(dict(stats_row))

            # Meta key/values
            meta_rows = conn.execute(
                "SELECT key, value FROM user_meta WHERE user_id = ?",
                (uid,),
            ).fetchall()
            for row in meta_rows:
                data[row["key"]] = row["value"]

            # Inventory (dict)
            inv_rows = conn.execute(
                "SELECT item_id, quantity FROM user_inventory WHERE user_id = ?",
                (uid,),
            ).fetchall()
            data["inventory"] = {r["item_id"]: int(r["quantity"]) for r in inv_rows if int(r["quantity"] or 0) > 0}

            # Achievements (JSON list string)
            ach_rows = conn.execute(
                "SELECT achievement_id FROM user_achievements WHERE user_id = ?",
                (uid,),
            ).fetchall()
            data["achievements"] = json.dumps([r["achievement_id"] for r in ach_rows])

            # Skill XP keys (skill_strength, etc) + derived levels (strength, etc)
            skill_rows = conn.execute(
                "SELECT skill_name, xp, level FROM user_skills WHERE user_id = ?",
                (uid,),
            ).fetchall()
            for row in skill_rows:
                data[f"skill_{row['skill_name']}"] = int(row["xp"])

            try:
                from services.skills_service import calculate_skill_level

                for base in ("strength", "intelligence", "charisma", "luck"):
                    xp = int(data.get(f"skill_{base}", 0) or 0)
                    level, _, _ = calculate_skill_level(xp)
                    data[base] = level
            except Exception:
                pass

            # Guild membership
            guild_row = conn.execute(
                "SELECT guild_id, guild_role FROM guild_members WHERE user_id = ?",
                (str(uid),),
            ).fetchone()
            if guild_row:
                data["guild_id"] = guild_row["guild_id"]
                data["guild_role"] = guild_row["guild_role"]

            return data

    def getallusers(self) -> list[str]:
        with self._connect_sync() as conn:
            rows = conn.execute("SELECT user_id FROM users").fetchall()
        return [str(r["user_id"]) for r in rows]

    def _upsert_meta(self, conn: sqlite3.Connection, user_id: int, key: str, value) -> None:
        if value is None:
            value_str = None
        elif isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        else:
            value_str = str(value)

        conn.execute(
            """
            INSERT INTO user_meta (user_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value
            """,
            (user_id, key, value_str),
        )

    def updatestat(self, user_id: str, key: str, value) -> None:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return

        self.ensure_user(uid)

        user_cols = {
            "balance",
            "bank",
            "bank_limit",
            "net_worth",
            "last_daily",
            "daily_streak",
            "bio",
            "reputation",
            "username",
            "favorite_color",
            "discord_id",
        }

        stats_cols = {
            "level",
            "xp",
            "health",
            "energy",
            "hunger",
            "happiness",
            "fame",
            "total_work_count",
            "crimes_committed",
            "times_jailed",
            "casino_total_bet",
            "casino_total_won",
            "last_work",
            "last_sleep",
            "last_rob",
            "last_crime",
            "hospital_until",
            "jail_until",
            "job_level",
            "job_xp",
            "current_job",
        }

        with self._connect_sync() as conn:
            if key == "inventory":
                inventory = value
                if isinstance(inventory, str):
                    try:
                        inventory = json.loads(inventory)
                    except Exception:
                        inventory = {}
                if not isinstance(inventory, dict):
                    inventory = {}

                conn.execute("DELETE FROM user_inventory WHERE user_id = ?", (uid,))
                for item_id, qty in inventory.items():
                    try:
                        qty_int = int(qty)
                    except (TypeError, ValueError):
                        continue
                    if qty_int <= 0:
                        continue
                    conn.execute(
                        "INSERT OR IGNORE INTO items (item_id, name) VALUES (?, ?)",
                        (str(item_id), str(item_id)),
                    )
                    conn.execute(
                        "INSERT INTO user_inventory (user_id, item_id, quantity) VALUES (?, ?, ?)",
                        (uid, str(item_id), qty_int),
                    )
                return

            if key == "achievements":
                achievement_ids = value
                if isinstance(achievement_ids, str):
                    try:
                        achievement_ids = json.loads(achievement_ids)
                    except Exception:
                        achievement_ids = []
                if not isinstance(achievement_ids, list):
                    achievement_ids = []

                conn.execute("DELETE FROM user_achievements WHERE user_id = ?", (uid,))
                for ach_id in achievement_ids:
                    if not isinstance(ach_id, str):
                        continue
                    conn.execute(
                        "INSERT OR IGNORE INTO achievements (achievement_id, name) VALUES (?, ?)",
                        (ach_id, ach_id),
                    )
                    conn.execute(
                        "INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?, ?)",
                        (uid, ach_id),
                    )
                return

            if key.startswith("skill_"):
                skill_name = key.removeprefix("skill_")
                try:
                    xp_val = int(value)
                except (TypeError, ValueError):
                    xp_val = 0

                level = 1
                try:
                    from services.skills_service import calculate_skill_level

                    level, _, _ = calculate_skill_level(xp_val)
                except Exception:
                    pass

                conn.execute(
                    """
                    INSERT INTO user_skills (user_id, skill_name, xp, level)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, skill_name) DO UPDATE SET xp = excluded.xp, level = excluded.level
                    """,
                    (uid, skill_name, xp_val, level),
                )
                return

            if key in ("guild_id", "guild_role"):
                if key == "guild_id":
                    if value is None or value == "":
                        conn.execute("DELETE FROM guild_members WHERE user_id = ?", (str(uid),))
                    else:
                        existing = conn.execute(
                            "SELECT 1 FROM guild_members WHERE user_id = ?",
                            (str(uid),),
                        ).fetchone()
                        if existing:
                            conn.execute(
                                "UPDATE guild_members SET guild_id = ? WHERE user_id = ?",
                                (str(value), str(uid)),
                            )
                        else:
                            conn.execute(
                                "INSERT INTO guild_members (user_id, guild_id) VALUES (?, ?)",
                                (str(uid), str(value)),
                            )
                    return

                if key == "guild_role":
                    conn.execute(
                        "UPDATE guild_members SET guild_role = ? WHERE user_id = ?",
                        (str(value), str(uid)),
                    )
                    return

            if key in user_cols:
                conn.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, uid))
                if key in {"balance", "bank", "bank_limit"}:
                    conn.execute("UPDATE users SET net_worth = balance + bank WHERE user_id = ?", (uid,))
                return

            if key in stats_cols:
                if key in {"job_level", "job_xp", "current_job"}:
                    self._upsert_meta(conn, uid, key, value)
                    return

                conn.execute(f"UPDATE user_stats SET {key} = ? WHERE user_id = ?", (value, uid))
                return

            self._upsert_meta(conn, uid, key, value)

    def updatestats(self, user_id: str, **kwargs) -> None:
        for key, value in kwargs.items():
            self.updatestat(user_id, key, value)

    def addbalance(self, user_id: str, amount: int, *, use_buffs: bool = True) -> None:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return

        self.ensure_user(uid)
        with self._connect_sync() as conn:
            conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (int(amount), uid))
            conn.execute("UPDATE users SET net_worth = balance + bank WHERE user_id = ?", (uid,))

    def removebalance(self, user_id: str, amount: int) -> None:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return

        self.ensure_user(uid)
        with self._connect_sync() as conn:
            conn.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (int(amount), uid))
            conn.execute("UPDATE users SET net_worth = balance + bank WHERE user_id = ?", (uid,))

    def addxp(self, user_id: str, amount: int, *, use_buffs: bool = True) -> None:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return

        self.ensure_user(uid)
        with self._connect_sync() as conn:
            row = conn.execute("SELECT level, xp FROM user_stats WHERE user_id = ?", (uid,)).fetchone()
            level = int(row["level"] if row else 1)
            xp = int(row["xp"] if row else 0)

            xp += int(amount)
            while xp >= level * 100 and level < 10_000:
                xp -= level * 100
                level += 1

            conn.execute("UPDATE user_stats SET level = ?, xp = ? WHERE user_id = ?", (level, xp, uid))

    def add_skill_xp(self, user_id: str, skill_name: str, amount: int) -> None:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return

        self.ensure_user(uid)
        skill = str(skill_name)
        with self._connect_sync() as conn:
            row = conn.execute(
                "SELECT xp FROM user_skills WHERE user_id = ? AND skill_name = ?",
                (uid, skill),
            ).fetchone()
            total = int(row["xp"] if row else 0) + int(amount)
            self.updatestat(str(uid), f"skill_{skill}", total)

    def increment_work_count(self, user_id: str) -> None:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return

        self.ensure_user(uid)
        with self._connect_sync() as conn:
            conn.execute(
                "UPDATE user_stats SET total_work_count = total_work_count + 1 WHERE user_id = ?",
                (uid,),
            )

    def increment_stat(self, user_id: str, stat: str, amount: int = 1) -> None:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return

        self.ensure_user(uid)
        stat_name = str(stat)

        stats_cols = {
            "total_work_count",
            "crimes_committed",
            "times_jailed",
            "casino_total_bet",
            "casino_total_won",
            "fame",
        }

        with self._connect_sync() as conn:
            if stat_name in stats_cols:
                conn.execute(
                    f"UPDATE user_stats SET {stat_name} = {stat_name} + ? WHERE user_id = ?",
                    (int(amount), uid),
                )
                return

            current = conn.execute(
                "SELECT value FROM user_meta WHERE user_id = ? AND key = ?",
                (uid, stat_name),
            ).fetchone()
            try:
                curr_val = int(current["value"]) if current and current["value"] is not None else 0
            except (TypeError, ValueError):
                curr_val = 0
            self._upsert_meta(conn, uid, stat_name, curr_val + int(amount))

    def updatelastwork(self, user_id: str, iso_time: str) -> None:
        self.updatestat(user_id, "last_work", iso_time)

    def updatelastsleep(self, user_id: str, iso_time: str) -> None:
        self.updatestat(user_id, "last_sleep", iso_time)

    def updatejob(self, user_id: str, job_name: str) -> None:
        self.updatestat(user_id, "current_job", job_name)

    def getleaderboard(self, field: str, limit: int = 10) -> list[tuple[str, int]]:
        field_name = str(field)
        limit_val = max(1, int(limit))

        user_fields = {"balance", "bank", "net_worth", "reputation", "daily_streak"}
        stat_fields = {
            "level",
            "xp",
            "health",
            "energy",
            "hunger",
            "happiness",
            "fame",
            "total_work_count",
            "crimes_committed",
            "casino_total_bet",
            "casino_total_won",
        }

        with self._connect_sync() as conn:
            if field_name in user_fields:
                rows = conn.execute(
                    f"SELECT user_id, {field_name} as value FROM users ORDER BY value DESC LIMIT ?",
                    (limit_val,),
                ).fetchall()
                return [(str(r["user_id"]), int(r["value"] or 0)) for r in rows]

            if field_name in stat_fields:
                rows = conn.execute(
                    f"SELECT user_id, {field_name} as value FROM user_stats ORDER BY value DESC LIMIT ?",
                    (limit_val,),
                ).fetchall()
                return [(str(r["user_id"]), int(r["value"] or 0)) for r in rows]

        return []

    def additem(self, user_id: str, item_id: str, quantity: int = 1) -> None:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return

        self.ensure_user(uid)
        item = str(item_id)
        qty = max(1, int(quantity))

        with self._connect_sync() as conn:
            conn.execute("INSERT OR IGNORE INTO items (item_id, name) VALUES (?, ?)", (item, item))
            conn.execute(
                """
                INSERT INTO user_inventory (user_id, item_id, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity
                """,
                (uid, item, qty),
            )

    def removeitem(self, user_id: str, item_id: str, quantity: int = 1) -> None:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return

        self.ensure_user(uid)
        item = str(item_id)
        qty = max(1, int(quantity))

        with self._connect_sync() as conn:
            conn.execute(
                "UPDATE user_inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                (qty, uid, item),
            )
            conn.execute(
                "DELETE FROM user_inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0",
                (uid, item),
            )

    def get_user_businesses(self, user_id: str) -> list[dict]:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return []

        with self._connect_sync() as conn:
            rows = conn.execute(
                "SELECT * FROM businesses WHERE owner_id = ? ORDER BY business_id ASC",
                (uid,),
            ).fetchall()

        businesses: list[dict] = []
        for row in rows:
            r = dict(row)
            businesses.append(
                {
                    "business_id": str(r.get("business_id")),
                    "owner_id": str(r.get("owner_id")),
                    "business_type": r.get("type"),
                    "name": r.get("name"),
                    "level": r.get("level", 1),
                    "revenue_per_hour": r.get("revenue_rate", 0),
                    "last_collected": r.get("last_collection"),
                }
            )
        return businesses

    def create_business(self, user_id: str, business_type: str, name: str, revenue_per_hour: int) -> str:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return ""

        with self._connect_sync() as conn:
            cur = conn.execute(
                """
                INSERT INTO businesses (owner_id, name, type, level, revenue_rate, last_collection)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (uid, name, business_type, int(revenue_per_hour), datetime.utcnow().isoformat()),
            )
            return str(cur.lastrowid)

    def updatebusiness(self, business_id: str, field: str, value) -> None:
        field_map = {
            "business_type": "type",
            "revenue_per_hour": "revenue_rate",
            "last_collected": "last_collection",
        }
        col = field_map.get(field, field)

        bid = self._coerce_int_id(business_id)
        if bid is None:
            return

        with self._connect_sync() as conn:
            conn.execute(f"UPDATE businesses SET {col} = ? WHERE business_id = ?", (value, bid))

    def get_user_properties(self, user_id: str) -> list[dict]:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return []

        with self._connect_sync() as conn:
            rows = conn.execute(
                "SELECT * FROM properties WHERE owner_id = ? ORDER BY property_id ASC",
                (uid,),
            ).fetchall()

        props: list[dict] = []
        for row in rows:
            r = dict(row)
            props.append(
                {
                    "property_id": str(r.get("property_id")),
                    "owner_id": str(r.get("owner_id")),
                    "property_type": r.get("property_type"),
                    "name": r.get("name"),
                    "level": r.get("level", 1),
                    "rent_per_hour": r.get("rent_per_hour", 0),
                    "last_collected": r.get("last_collected"),
                }
            )
        return props

    def create_property(self, user_id: str, property_type: str, name: str, rent_per_hour: int) -> str:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return ""

        with self._connect_sync() as conn:
            cur = conn.execute(
                """
                INSERT INTO properties (owner_id, property_type, name, level, rent_per_hour, last_collected)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (uid, property_type, name, int(rent_per_hour), datetime.utcnow().isoformat()),
            )
            return str(cur.lastrowid)

    def updateproperty(self, property_id: str, field: str, value) -> None:
        pid = self._coerce_int_id(property_id)
        if pid is None:
            return

        with self._connect_sync() as conn:
            conn.execute(f"UPDATE properties SET {field} = ? WHERE property_id = ?", (value, pid))

    def get_user_pets(self, user_id: str) -> list[dict]:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return []

        with self._connect_sync() as conn:
            rows = conn.execute(
                "SELECT * FROM pets WHERE owner_id = ? ORDER BY pet_id ASC",
                (uid,),
            ).fetchall()

        pets: list[dict] = []
        for row in rows:
            r = dict(row)
            pets.append(
                {
                    "pet_id": str(r.get("pet_id")),
                    "owner_id": str(r.get("owner_id")),
                    "pet_type": r.get("type"),
                    "name": r.get("name"),
                    "level": r.get("level", 1),
                    "xp": r.get("xp", 0),
                    "happiness": r.get("happiness", 100),
                    "hunger": r.get("hunger", 100),
                    "energy": r.get("energy", 100),
                    "last_fed": r.get("last_fed"),
                }
            )
        return pets

    def create_pet(self, user_id: str, pet_type: str, name: str) -> str:
        uid = self._coerce_int_id(user_id)
        if uid is None:
            return ""

        with self._connect_sync() as conn:
            cur = conn.execute(
                """
                INSERT INTO pets (owner_id, name, type, level, xp, hunger, energy, happiness, last_fed)
                VALUES (?, ?, ?, 1, 0, 100, 100, 100, ?)
                """,
                (uid, name, pet_type, datetime.utcnow().isoformat()),
            )
            return str(cur.lastrowid)

    def updatepet(self, pet_id: str, field: str, value) -> None:
        pid = self._coerce_int_id(pet_id)
        if pid is None:
            return

        with self._connect_sync() as conn:
            conn.execute(f"UPDATE pets SET {field} = ? WHERE pet_id = ?", (value, pid))

    def create_guild(self, guild_id: str, name: str, owner_id: str) -> None:
        with self._connect_sync() as conn:
            conn.execute(
                """
                INSERT INTO guilds (guild_id, name, owner_id, created_at, member_count)
                VALUES (?, ?, ?, ?, 1)
                """,
                (str(guild_id), str(name), str(owner_id), datetime.utcnow().isoformat()),
            )
            conn.execute(
                "INSERT OR REPLACE INTO guild_members (user_id, guild_id, guild_role) VALUES (?, ?, 'leader')",
                (str(owner_id), str(guild_id)),
            )

    def getguild(self, guild_id: str) -> dict | None:
        with self._connect_sync() as conn:
            row = conn.execute("SELECT * FROM guilds WHERE guild_id = ?", (str(guild_id),)).fetchone()
        return dict(row) if row else None

    def updateguild(self, guild_id: str, field: str, value) -> None:
        with self._connect_sync() as conn:
            conn.execute(f"UPDATE guilds SET {field} = ? WHERE guild_id = ?", (value, str(guild_id)))

    def add_to_guild_bank(self, guild_id: str, amount: int) -> None:
        with self._connect_sync() as conn:
            conn.execute("UPDATE guilds SET bank = bank + ? WHERE guild_id = ?", (int(amount), str(guild_id)))

    def remove_from_guild_bank(self, guild_id: str, amount: int) -> None:
        with self._connect_sync() as conn:
            conn.execute("UPDATE guilds SET bank = bank - ? WHERE guild_id = ?", (int(amount), str(guild_id)))

    def get_guild_members(self, guild_id: str) -> list[dict]:
        with self._connect_sync() as conn:
            rows = conn.execute("SELECT * FROM guild_members WHERE guild_id = ?", (str(guild_id),)).fetchall()
        return [dict(r) for r in rows]

    def add_to_family_bank(self, user_id: str, amount: int) -> None:
        uid = str(user_id)
        u = self.getuser(uid)
        spouse = u.get("spouse")

        try:
            current = int(u.get("family_bank", 0) or 0)
        except (TypeError, ValueError):
            current = 0

        new_val = current + int(amount)
        self.updatestat(uid, "family_bank", new_val)
        if spouse:
            self.updatestat(str(spouse), "family_bank", new_val)

    def remove_from_family_bank(self, user_id: str, amount: int) -> None:
        uid = str(user_id)
        u = self.getuser(uid)
        spouse = u.get("spouse")

        try:
            current = int(u.get("family_bank", 0) or 0)
        except (TypeError, ValueError):
            current = 0

        new_val = current - int(amount)
        self.updatestat(uid, "family_bank", new_val)
        if spouse:
            self.updatestat(str(spouse), "family_bank", new_val)

    def get_relationship(self, user_id: str, target_id: str) -> dict | None:
        with self._connect_sync() as conn:
            row = conn.execute(
                "SELECT * FROM relationships WHERE user_id = ? AND target_id = ?",
                (str(user_id), str(target_id)),
            ).fetchone()
        return dict(row) if row else None

    def get_relationships_for_user(self, user_id: str) -> list[dict]:
        with self._connect_sync() as conn:
            rows = conn.execute(
                "SELECT * FROM relationships WHERE user_id = ? OR target_id = ?",
                (str(user_id), str(user_id)),
            ).fetchall()
        return [dict(r) for r in rows]

    def upsert_relationship(
        self,
        user_id: str,
        target_id: str,
        affection_delta: int = 0,
        status: str = "stranger",
        touch_interaction: bool = False,
    ) -> dict:
        with self._connect_sync() as conn:
            existing = conn.execute(
                "SELECT * FROM relationships WHERE user_id = ? AND target_id = ?",
                (str(user_id), str(target_id)),
            ).fetchone()

            if not existing:
                conn.execute(
                    """
                    INSERT INTO relationships (user_id, target_id, affection, status, last_interaction)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(user_id),
                        str(target_id),
                        int(affection_delta),
                        str(status),
                        datetime.utcnow().isoformat() if touch_interaction else None,
                    ),
                )
            else:
                new_aff = int(existing["affection"] or 0) + int(affection_delta)
                conn.execute(
                    """
                    UPDATE relationships
                    SET affection = ?, status = ?, last_interaction = COALESCE(?, last_interaction)
                    WHERE user_id = ? AND target_id = ?
                    """,
                    (
                        new_aff,
                        str(status),
                        datetime.utcnow().isoformat() if touch_interaction else None,
                        str(user_id),
                        str(target_id),
                    ),
                )

            row = conn.execute(
                "SELECT * FROM relationships WHERE user_id = ? AND target_id = ?",
                (str(user_id), str(target_id)),
            ).fetchone()

        return dict(row) if row else {"user_id": user_id, "target_id": target_id, "affection": 0, "status": status}

    @staticmethod
    def _backup_sync(src_path: str, dst_path: str):
        with sqlite3.connect(src_path) as src, sqlite3.connect(dst_path) as dst:
            src.backup(dst)

    async def backup(self, backup_dir: str | Path = "backups", keep: int | None = 10) -> str | None:
        """
        Creates a consistent SQLite backup copy of the database file.
        Returns the backup file path (or None if the DB doesn't exist yet).
        """
        src = Path(self.db_path)
        if not src.exists():
            return None

        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dst = backup_dir / f"{src.stem}_{ts}{src.suffix}"

        await asyncio.to_thread(self._backup_sync, str(src), str(dst))

        if keep is not None:
            backups = sorted(
                backup_dir.glob(f"{src.stem}_*{src.suffix}"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for old in backups[keep:]:
                old.unlink(missing_ok=True)

        return str(dst)

# Global Database Instance
db = DatabaseManager()
