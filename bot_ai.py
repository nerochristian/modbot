"""
ModBot AI - AI & Automation Bot
Entry point for AI moderation, automod, and automation features
"""

import discord
from discord.ext import commands
import logging
import os
import re
import sys
import asyncio
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

from config import Config

# Load environment variables
load_dotenv()

# Initialize static-ffmpeg if installed
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except ImportError:
    pass

# ==================== GLOBAL EMBED COLOR ENFORCEMENT ====================
_ORIGINAL_EMBED_INIT = discord.Embed.__init__

def _embed_init_force_accent(self, *args, **kwargs):
    kwargs.pop("colour", None)
    kwargs.pop("timestamp", None)
    kwargs["color"] = getattr(Config, "EMBED_ACCENT_COLOR", 0x5865F2)
    return _ORIGINAL_EMBED_INIT(self, *args, **kwargs)

discord.Embed.__init__ = _embed_init_force_accent

# ==================== CONSOLE ENCODING FIX ====================
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ==================== LOGGING ====================
class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
        "RESET": "\033[0m",
    }
    
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
            msg = f"{color}{msg}{self.COLORS['RESET']}"
        return msg

def setup_logging() -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    logger = logging.getLogger("ModBotAI")
    logger.setLevel(logging.INFO)
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    return logger

logger = setup_logging()

# ==================== IMPORTS ====================
try:
    from database import Database
    from utils.cache import SnipeCache, PrefixCache
    from utils.components_v2 import patch_components_v2
except ImportError as e:
    logger.critical(f"❌ Failed to import required modules: {e}")
    sys.exit(1)

patch_components_v2()

# ==================== BOT CLASS ====================
class ModBotAI(commands.Bot):
    """
    AI Bot - handles AI moderation, automod, antiraid, and automation.
    Shares database with main ModBot.
    """
    
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
            owner_ids=self._load_owner_ids(),
        )
        
        # Core systems (shared database)
        self.db: Database = Database()
        self.start_time: datetime = datetime.now(timezone.utc)
        self.version: str = "3.3.0-AI"
        
        # Caching
        self.snipe_cache = SnipeCache(max_age_seconds=300, max_size=500)
        self.edit_snipe_cache = SnipeCache(max_age_seconds=300, max_size=500)
        self.prefix_cache = PrefixCache(ttl=600)
        
        # Statistics
        self.commands_used: int = 0
        self.messages_seen: int = 0
        self.errors_caught: int = 0
        
        # Internal flags
        self._ready_once: bool = False
        self.blacklist_cache: set[int] = set()
    
    @staticmethod
    def _load_owner_ids() -> set[int]:
        owner_ids_str = os.getenv("OWNER_IDS") or os.getenv("OWNER_ID") or ""
        try:
            owner_ids = {1269772767516033025}
            for part in re.split(r"[,\s]+", owner_ids_str.strip()):
                part = part.strip()
                if part:
                    owner_ids.add(int(part))
            return owner_ids
        except ValueError:
            return {1269772767516033025}
    
    async def get_prefix(self, message: discord.Message):
        if not message.guild:
            return commands.when_mentioned_or("!")(self, message)
        
        prefix = await self.prefix_cache.get(message.guild.id)
        if prefix is None:
            try:
                settings = await self.db.get_settings(message.guild.id)
                prefix = settings.get("prefix", ",")
                await self.prefix_cache.set(message.guild.id, prefix)
            except Exception:
                prefix = ","
        
        return commands.when_mentioned_or(prefix)(self, message)
    
    async def setup_hook(self):
        logger.info("🔧 Initializing ModBot AI...")
        
        # Initialize database
        try:
            await self.db.init_pool()
        except Exception as e:
            logger.error(f"❌ Failed to initialize database pool: {e}")
            raise
        
        # AI Bot cogs
        cogs = [
            "cogs.help",  # Each bot has its own /help
            "cogs.aimoderation",
            "cogs.automod",
            "cogs.antiraid",
            "cogs.voice",
            "cogs.settings",
            "cogs.polls",
            "cogs.logging_cog",  # Needed for AI logging
            "cogs.prefix_commands",  # Prefix commands work on all bots
        ]
        
        loaded = []
        failed = []
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                loaded.append(cog)
                logger.info(f"✅ Loaded: {cog}")
            except commands.ExtensionNotFound:
                logger.debug(f"⚠️ Skipped: {cog} (not found)")
            except Exception as e:
                failed.append((cog, str(e)))
                logger.error(f"❌ Failed: {cog} - {e}")
        
        logger.info("=" * 60)
        logger.info(f"📦 AI Bot Cog Summary: ✅ {len(loaded)} | ❌ {len(failed)}")
        logger.info(f"📊 Commands: {len(self.tree.get_commands())} slash")
        logger.info("=" * 60)
        
        # Global blacklist check
        self.tree.interaction_check = self._check_global_blacklist
        
        # Sync slash commands
        try:
            logger.info("⚡ Syncing slash commands...")
            synced = await self.tree.sync()
            logger.info(f"⚡ Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"❌ Failed to sync commands: {e}")
        
        self.tree.on_error = self.on_tree_error
    
    async def on_tree_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        self.errors_caught += 1
        if isinstance(error, discord.app_commands.MissingPermissions):
            embed = discord.Embed(title="🚫 Permission Denied", color=0xFF0000)
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass
            return
        logger.error(f"Command error: {error}", exc_info=error)
    
    async def _check_global_blacklist(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in self.owner_ids:
            return True
        if interaction.user.id in self.blacklist_cache:
            try:
                await interaction.response.send_message("🚫 You are blacklisted.", ephemeral=True)
            except:
                pass
            return False
        return True
    
    async def on_ready(self):
        if self._ready_once:
            logger.info("🔄 Reconnected to Discord")
            return
        
        self._ready_once = True
        
        logger.info("=" * 60)
        logger.info(f"🤖 ModBot AI Online: {self.user}")
        logger.info(f"📊 Guilds: {len(self.guilds)}")
        logger.info(f"🔧 Version: {self.version}")
        logger.info("=" * 60)
        
        # Init guilds
        for guild in self.guilds:
            try:
                await self.db.init_guild(guild.id)
            except Exception:
                pass
        
        # Load blacklist
        try:
            blacklist = await self.db.get_blacklist()
            self.blacklist_cache = {entry["user_id"] for entry in blacklist}
        except Exception:
            self.blacklist_cache = set()
        
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for rule breakers | /aihelp",
            ),
            status=discord.Status.online,
        )
        
        logger.info("🚀 ModBot AI is operational!")
    
    async def on_guild_join(self, guild: discord.Guild):
        try:
            await self.db.init_guild(guild.id)
            logger.info(f"✅ Joined: {guild.name}")
        except Exception:
            pass
    
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        self.messages_seen += 1
        await self.process_commands(message)
    
    async def close(self):
        logger.info("👋 Shutting down ModBot AI...")
        try:
            if hasattr(self.db, "close"):
                await self.db.close()
        except Exception:
            pass
        await super().close()


# ==================== MAIN ====================
async def main() -> int:
    token = os.getenv("DISCORD_TOKEN_AI")
    if not token:
        logger.critical("❌ DISCORD_TOKEN_AI not found!")
        logger.critical("Add DISCORD_TOKEN_AI=your_token to .env")
        return 1
    
    bot = ModBotAI()
    
    try:
        async with bot:
            logger.info("🚀 Starting ModBot AI...")
            await bot.start(token)
    except KeyboardInterrupt:
        logger.info("👋 Shutdown signal received")
    except discord.LoginFailure:
        logger.critical("❌ Invalid DISCORD_TOKEN_AI!")
        return 1
    except Exception as e:
        logger.critical(f"❌ Fatal error: {e}", exc_info=True)
        return 1
    finally:
        if not bot.is_closed():
            await bot.close()
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        logger.critical(f"❌ Critical error: {e}", exc_info=True)
        sys.exit(1)
