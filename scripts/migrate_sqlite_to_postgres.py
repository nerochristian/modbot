import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import Database


TABLES = [
    "guild_settings",
    "cases",
    "warnings",
    "mod_notes",
    "tempbans",
    "mod_stats",
    "reports",
    "tickets",
    "staff_sanctions",
    "court_sessions",
    "court_evidence",
    "court_votes",
    "modmail_threads",
    "modmail_messages",
    "modmail_blocks",
    "giveaways",
    "giveaway_entries",
    "reaction_roles",
    "voice_roles",
    "blacklist",
    "whitelist",
    "ai_memory",
    "quarantines",
    "dashboard_audit",
]


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def get_columns(conn: sqlite3.Connection, table: str) -> list[tuple[str, str]]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [(str(row[1]), str(row[2] or "")) for row in rows]


async def ensure_postgres_schema(db: Database, source: sqlite3.Connection) -> None:
    guild_ids: list[int] = []
    if table_exists(source, "guild_settings"):
        guild_ids = [
            int(row[0])
            for row in source.execute("SELECT guild_id FROM guild_settings").fetchall()
            if row[0] is not None
        ]

    if guild_ids:
        for guild_id in guild_ids:
            await db.init_guild(guild_id)
        return

    await db.init_guild(1)
    async with db.get_connection() as conn:
        await conn.execute("DELETE FROM guild_settings WHERE guild_id = ?", (1,))
        await conn.commit()


async def migrate_table(db: Database, source: sqlite3.Connection, table: str) -> int:
    if not table_exists(source, table):
        return 0

    columns = get_columns(source, table)
    if not columns:
        return 0

    column_names = [name for name, _ in columns]
    boolean_columns = {name for name, declared_type in columns if "BOOL" in declared_type.upper()}
    rows = source.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        return 0

    placeholders = ", ".join("?" for _ in column_names)
    insert_sql = (
        f"INSERT INTO {table} ({', '.join(column_names)}) "
        f"VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    )

    inserted = 0
    async with db.get_connection() as conn:
        for row in rows:
            values = []
            for index, column_name in enumerate(column_names):
                value = row[index]
                if column_name in boolean_columns and value is not None:
                    values.append(bool(value))
                else:
                    values.append(value)
            await conn.execute(insert_sql, tuple(values))
            inserted += 1
        await conn.commit()

        if "id" in column_names:
            await conn.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {table}), 1), true)"
            )
            await conn.commit()

    return inserted


async def main() -> int:
    parser = argparse.ArgumentParser(description="Copy the local SQLite database into PostgreSQL/Supabase.")
    parser.add_argument(
        "--source",
        default=str(ROOT / "modbot.db"),
        help="Path to the source SQLite database file.",
    )
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    if not source_path.exists():
        print(f"Source database not found: {source_path}")
        return 1

    target_db = Database()
    if target_db._db_mode != "postgres":
        print("DATABASE_URL is not configured for PostgreSQL. Set it to your Supabase/Postgres connection string first.")
        return 1

    source = sqlite3.connect(source_path)
    try:
        await ensure_postgres_schema(target_db, source)

        total_rows = 0
        for table in TABLES:
            inserted = await migrate_table(target_db, source, table)
            if inserted:
                print(f"{table}: {inserted}")
                total_rows += inserted

        print(f"Migration complete. Imported {total_rows} row(s) from {source_path}.")
        return 0
    finally:
        source.close()
        await target_db.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
