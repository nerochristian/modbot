"""Test script that simulates bot startup to catch command registration errors."""
import asyncio
import sys
import logging
import traceback
import os

sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("test")

from dotenv import load_dotenv
load_dotenv(override=True)

import discord
from discord.ext import commands

# Create a minimal bot instance
intents = discord.Intents.all()

class TestBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=",",
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
        )
        self.db = None
        self.start_time = None
        self.version = "3.4.0"
        self.snipe_cache = None
        self.edit_snipe_cache = None
        self.prefix_cache = None
        self.caches = {}
        self.commands_used = 0
        self.messages_seen = 0
        self.errors_caught = 0
        self.loading_emoji = "\u23f3"
        self._prefix_loading_messages = {}
        self._command_cooldowns = {}
        self._command_rate_windows = {}
        self._ready_once = False
        self._cache_cleanup_task = None
        self._dashboard_runner = None
        self.blacklist_cache = set()
        self._cache_backend = "memory"

    async def get_prefix(self, message):
        return commands.when_mentioned_or(",")(self, message)

bot = TestBot()

# Mock database
class MockDB:
    async def get_settings(self, guild_id):
        return {}
    async def init_guild(self, guild_id):
        pass
    async def init_pool(self):
        pass
    async def get_blacklist(self):
        return []
    async def close(self):
        pass
    def get_connection(self):
        class MockConn:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def execute(self, *args, **kwargs):
                pass
            async def commit(self):
                pass
            async def fetchall(self):
                return []
        return MockConn()

bot.db = MockDB()

# Mock cache
class MockCache:
    async def get(self, key):
        return None
    async def set(self, key, value):
        pass
    async def invalidate(self, key):
        pass
    async def clear(self):
        pass

bot.prefix_cache = MockCache()
bot.snipe_cache = MockCache()
bot.edit_snipe_cache = MockCache()

cogs = [
    "cogs.moderation",
    "cogs.setup",
    "cogs.verification",
    "cogs.help",
    "cogs.roles",
    "cogs.logging_cog",
    "cogs.pin",
    "cogs.reports",
    "cogs.blacklist",
    "cogs.prefix_commands",
    "cogs.aimoderation",
    "cogs.ai_scheduler",
    "cogs.automod",
    "cogs.antiraid",
    "cogs.voice",
    "cogs.settings",
    "cogs.polls",
    "cogs.tickets",
    "cogs.utility",
    "cogs.admin",
    "cogs.court",
    "cogs.whitelist",
    "cogs.server_backup",
    "cogs.risk_scoring",
    "cogs.alt_detection",
    "cogs.staff_reports",
    "cogs.behavior_profiling",
]

async def test_load():
    loaded = []
    failed = []
    
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            loaded.append(cog)
            print(f"  [OK] Loaded: {cog}")
        except Exception as e:
            failed.append((cog, str(e)))
            print(f"  [ERR] Failed: {cog} - {e}")
            traceback.print_exc()
    
    print(f"\nLoaded: {len(loaded)}, Failed: {len(failed)}")
    
    # Count commands
    total_prefix = len(list(bot.walk_commands()))
    total_slash = len(bot.tree.get_commands())
    print(f"Prefix commands: {total_prefix}")
    print(f"Slash commands (top-level): {total_slash}")
    
    # List all slash commands
    print("\n=== Top-level slash commands ===")
    for cmd in bot.tree.get_commands():
        if hasattr(cmd, 'commands'):
            subcommands = [c.name for c in cmd.commands]
            print(f"  /{cmd.name} (group with: {', '.join(subcommands)})")
        else:
            print(f"  /{cmd.name}")
    
    # List all prefix commands
    print("\n=== Prefix commands ===")
    for cmd in bot.walk_commands():
        print(f"  {cmd.qualified_name}")
    
    # Check for duplicate slash command names
    slash_names = [cmd.name for cmd in bot.tree.get_commands()]
    duplicates = [name for name in set(slash_names) if slash_names.count(name) > 1]
    if duplicates:
        print(f"\n[WARNING] Duplicate slash command names: {duplicates}")
    else:
        print(f"\n[OK] No duplicate slash command names")
    
    return failed

try:
    failed = asyncio.run(test_load())
    if failed:
        print(f"\n[FAIL] {len(failed)} cogs failed to load")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All cogs loaded successfully!")
except Exception as e:
    print(f"\n[FATAL] {e}")
    traceback.print_exc()
    sys.exit(1)