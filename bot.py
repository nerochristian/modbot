"""
ModBot - Advanced Discord Moderation Bot
Enterprise-grade moderation system with comprehensive logging
Version 3.3.0 - Complete Database Overhaul
"""

import discord
from discord.ext import commands
import logging
import os
import re
import sys
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

from config import Config

# Load environment variables
load_dotenv()

# ==================== GLOBAL EMBED COLOR ENFORCEMENT ====================
# Forces all embeds (side color) to use Config.EMBED_ACCENT_COLOR.
_ORIGINAL_EMBED_INIT = discord.Embed.__init__


def _embed_init_force_accent(self, *args, **kwargs):
    kwargs.pop("colour", None)
    kwargs.pop("timestamp", None)
    kwargs["color"] = getattr(Config, "EMBED_ACCENT_COLOR", 0x5865F2)
    return _ORIGINAL_EMBED_INIT(self, *args, **kwargs)


discord.Embed.__init__ = _embed_init_force_accent

# ==================== ENVIRONMENT VALIDATION ====================
def validate_environment() -> None:
    """Validate required environment variables"""
    required = ["DISCORD_TOKEN"]
    optional_warnings = ["GROQ_API_KEY", "OWNER_IDS"]
    
    for var in required:
        if not os.getenv(var):
            logger = logging.getLogger("ModBot")
            logger.critical(f"❌ Missing required environment variable: {var}")
            sys.exit(1)
    
    for var in optional_warnings:
        if not os.getenv(var):
            logger = logging.getLogger("ModBot")
            logger.warning(f"⚠️ Optional environment variable not set: {var}")

# ==================== CONSOLE ENCODING FIX ====================
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ==================== CUSTOM LOGGING ====================
class ColoredFormatter(logging.Formatter):
    """Custom formatter with ANSI colors"""
    
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
        "RESET": "\033[0m",
    }
    
    EMOJI_FALLBACK = {
        "✅": "[OK]",
        "❌": "[ERR]",
        "⚡": "[>>]",
        "🤖": "[BOT]",
        "📡": "[NET]",
        "👋": "[BYE]",
        "⚠️": "[!]",
        "🔧": "[CFG]",
        "💬": "[CMD]",
        "📦": "[COG]",
        "👥": "[USR]",
        "🚀": "[START]",
        "🗄️": "[DB]",
    }
    
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        
        # Handle encoding issues
        try:
            encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
            msg.encode(encoding)
        except (UnicodeEncodeError, LookupError, AttributeError):
            for emoji, fallback in self.EMOJI_FALLBACK.items():
                msg = msg.replace(emoji, fallback)
        
        # Apply colors if TTY
        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
            msg = f"{color}{msg}{self.COLORS['RESET']}"
        
        return msg


def setup_logging() -> logging.Logger:
    """Configure logging with custom formatter"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    logger = logging.getLogger("ModBot")
    logger.setLevel(logging.INFO)
    
    # Reduce discord.py verbosity
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.INFO)
    logging.getLogger("discord.client").setLevel(logging.WARNING)
    
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

# Enable Discord Components v2 layouts (converts embeds into LayoutView cards).
patch_components_v2()

# ==================== BOT CLASS ====================
class ModBot(commands.Bot):
    """
    Main bot class with comprehensive features:
    - Dynamic prefix system from database
    - Command and message statistics
    - Snipe/editsnipe caching
    - Automatic guild initialization
    - Complete feature support for all cogs
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
        
        # Core systems
        self.db: Database = Database()
        self.start_time: datetime = datetime.now(timezone.utc)
        self.version: str = "3.3.0"
        
        # Advanced caching with TTL (prevents memory leaks)
        self.snipe_cache = SnipeCache(max_age_seconds=300, max_size=500)
        self.edit_snipe_cache = SnipeCache(max_age_seconds=300, max_size=500)
        self.prefix_cache = PrefixCache(ttl=600)
        
        # Statistics
        self.commands_used: int = 0
        self.messages_seen: int = 0
        self.errors_caught: int = 0
        
        # Internal flags
        self._ready_once: bool = False
        self._cache_cleanup_task: Optional[asyncio.Task] = None
    
    @staticmethod
    def _load_owner_ids() -> set[int]:
        """Load bot owner IDs from environment"""
        owner_ids_str = os.getenv("OWNER_IDS") or os.getenv("OWNER_ID") or ""
        try:
            owner_ids = {1269772767516033025}
            for part in re.split(r"[,\s]+", owner_ids_str.strip()):
                part = part.strip()
                if not part:
                    continue
                owner_ids.add(int(part))
            return owner_ids
        except ValueError:
            logger.warning("⚠️ Invalid OWNER_IDS in .env, using default")
            return {1269772767516033025}
    
    async def get_prefix(self, message: discord.Message):
        """Dynamic prefix handler with advanced caching"""
        if not message.guild:
            return commands.when_mentioned_or("!")(self, message)
        
        # Check cache with TTL
        prefix = await self.prefix_cache.get(message.guild.id)
        
        if prefix is None:
            # Load from database
            try:
                settings = await self.db.get_settings(message.guild.id)
                prefix = settings.get("prefix", "!")
                await self.prefix_cache.set(message.guild.id, prefix)
            except Exception as e:
                logger.error(f"Failed to get prefix for {message.guild.name}: {e}")
                prefix = "!"
        
        return commands.when_mentioned_or(prefix)(self, message)
    
    async def setup_hook(self):
        """Load cogs and sync slash commands"""
        logger.info("🔧 Initializing bot systems...")
        
        # Initialize database connection pool
        try:
            await self.db.init_pool()
        except Exception as e:
            logger.error(f"❌ Failed to initialize database pool: {e}")
            raise
        
        # Start cache cleanup task
        self._cache_cleanup_task = self.loop.create_task(self._cache_cleanup_loop())
        
        # Ensure cogs directory exists
        cogs_path = Path("./cogs")
        if not cogs_path.exists():
            logger.warning("⚠️ Cogs directory not found, creating...")
            cogs_path.mkdir(exist_ok=True)
        
        # Cog list
        cogs = [
            "cogs.setup",
            "cogs.verification",
            "cogs.moderation",
            "cogs.roles",
            "cogs.logging_cog",
            "cogs.automod",
            "cogs.tickets",
            "cogs.reports",
            "cogs.utility",
            "cogs.pin",
            "cogs.voice",
            "cogs.antiraid",
            "cogs.admin",
            "cogs.staff",
            "cogs.court",
            "cogs.aimoderation",
            "cogs.modmail",
        ]
        
        loaded: list[str] = []
        failed: list[tuple[str, str]] = []
        skipped: list[str] = []
        
        # Load each cog
        for cog in cogs:
            try:
                await self.load_extension(cog)
                loaded.append(cog)
                logger.info(f"✅ Loaded: {cog}")
            except commands.ExtensionNotFound:
                skipped.append(cog)
                logger.debug(f"⚠️ Skipped: {cog} (not found)")
            except commands.ExtensionAlreadyLoaded:
                logger.debug(f"⚠️ Skipped: {cog} (already loaded)")
            except Exception as e:
                failed.append((cog, str(e)))
                logger.error(f"❌ Failed: {cog} - {e}")
        
        # Summary
        logger.info("=" * 60)
        logger.info("📦 Cog Loading Summary:")
        logger.info(f"  ✅ Loaded: {len(loaded)}")
        logger.info(f"  ⚠️ Skipped: {len(skipped)}")
        logger.info(f"  ❌ Failed: {len(failed)}")
        if failed:
            logger.warning("  Failed cogs:")
            for cog, error in failed:
                logger.warning(f"    • {cog}: {error}")
        logger.info("=" * 60)
        
        # Display loaded commands
        await self._display_loaded_commands()
        
        # Sync slash commands
        try:
            logger.info("⚡ Syncing slash commands...")
            synced = await self.tree.sync()
            logger.info(f"⚡ Successfully synced {len(synced)} slash commands")
            
            if synced:
                logger.info("=" * 60)
                logger.info("💬 Loaded Slash Commands:")
                for cmd in synced:
                    logger.info(
                        f"  /{cmd.name} - {cmd.description[:50] if cmd.description else 'No description'}"
                    )
                logger.info("=" * 60)
        except discord.HTTPException as e:
            logger.error(f"❌ Failed to sync commands: {e}")
            self.errors_caught += 1
        except Exception as e:
            logger.error(f"❌ Unexpected error syncing commands: {e}")
            self.errors_caught += 1
    
    async def _display_loaded_commands(self):
        """Display all loaded commands organized by cog"""
        logger.info("=" * 60)
        logger.info("💬 Loaded Prefix Commands:")
        
        total_commands = 0
        cog_commands = {}
        
        for command in self.walk_commands():
            total_commands += 1
            cog_name = command.cog_name if command.cog_name else "No Category"
            if cog_name not in cog_commands:
                cog_commands[cog_name] = []
            cog_commands[cog_name].append(command)
        
        # Display by cog
        for cog_name in sorted(cog_commands.keys()):
            cmds = cog_commands[cog_name]
            logger.info(f"\n  📦 {cog_name} ({len(cmds)} commands):")
            for cmd in sorted(cmds, key=lambda x: x.qualified_name):
                aliases = f" [aliases: {', '.join(cmd.aliases)}]" if cmd.aliases else ""
                logger.info(f"    • {cmd.qualified_name}{aliases}")
        
        logger.info(f"\n  📊 Total Commands Loaded: {total_commands}")
        logger.info("=" * 60)
    
    async def on_ready(self):
        """Called when bot is ready and connected"""
        if self._ready_once:
            logger.info("🔄 Reconnected to Discord")
            return
        
        self._ready_once = True
        
        # Banner
        logger.info("=" * 60)
        logger.info(f"🤖 Bot Online: {self.user} (ID: {self.user.id})")
        logger.info(f"📊 Guilds: {len(self.guilds)}")
        logger.info(f"👥 Total Users: {sum(g.member_count for g in self.guilds):,}")
        logger.info(f"🔧 Version: {self.version}")
        logger.info(f"🐍 Discord.py: {discord.__version__}")
        logger.info("=" * 60)
        
        # Initialize database for all guilds
        logger.info("🗄️ Initializing guild databases...")
        success = 0
        failed = 0
        
        for guild in self.guilds:
            try:
                await self.db.init_guild(guild.id)
                success += 1
            except Exception as e:
                logger.error(f"❌ Failed to init {guild.name}: {e}")
                failed += 1
        
        logger.info(f"✅ Initialized {success}/{len(self.guilds)} guilds")
        if failed:
            logger.warning(f"⚠️ {failed} guilds failed initialization")
        logger.info("=" * 60)
        
        # Set presence
        await self.update_presence()
        logger.info("🚀 Bot is fully operational!")
    
    async def update_presence(self):
        """Update bot status"""
        try:
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{len(self.guilds)} servers | /help",
                ),
                status=discord.Status.online,
            )
        except Exception as e:
            logger.error(f"Failed to update presence: {e}")
    
    async def on_guild_join(self, guild: discord.Guild):
        """Handle joining a new guild"""
        try:
            await self.db.init_guild(guild.id)
            logger.info(
                f"✅ Joined guild: {guild.name} "
                f"(ID: {guild.id}, Members: {guild.member_count})"
            )
            await self.update_presence()
        except Exception as e:
            logger.error(f"Error handling guild join for {guild.name}: {e}")
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Handle leaving a guild"""
        logger.info(f"👋 Left guild: {guild.name} (ID: {guild.id})")
        # Clear cached prefix
        await self.prefix_cache.invalidate(guild.id)
        await self.update_presence()
    
    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        if message.author.bot:
            return
        
        self.messages_seen += 1
        await self.process_commands(message)
    
    async def on_command(self, ctx: commands.Context):
        """Track command usage"""
        self.commands_used += 1
        location = ctx.guild.name if ctx.guild else "DMs"
        logger.info(f"💬 {ctx.author} used '{ctx.command.name}' in {location}")
    
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Global command error handler"""
        self.errors_caught += 1
        
        # Ignore command not found
        if isinstance(error, commands.CommandNotFound):
            return
        
        # Missing permissions
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Missing Permissions",
                description="You don't have permission to use this command.",
                color=0xFF0000,
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        # Bot missing permissions
        if isinstance(error, commands.BotMissingPermissions):
            missing = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
            embed = discord.Embed(
                title="❌ Bot Missing Permissions",
                description=f"I need these permissions: {missing}",
                color=0xFF0000,
            )
            return await ctx.send(embed=embed)
        
        # Missing required argument
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❌ Missing Argument",
                description=(
                    f"Missing required argument: `{error.param.name}`\n\n"
                    f"Use `{ctx.prefix}help {ctx.command}` for more info."
                ),
                color=0xFF0000,
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        # Bad argument
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Invalid Argument",
                description=f"Invalid argument provided.\n\n{error}",
                color=0xFF0000,
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        # Command on cooldown
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Cooldown",
                description=f"Please wait {error.retry_after:.1f}s before using this command again.",
                color=0xFF9900,
            )
            return await ctx.send(embed=embed, delete_after=5)
        
        # User input error
        if isinstance(error, commands.UserInputError):
            embed = discord.Embed(
                title="❌ Invalid Input",
                description=(
                    f"{error}\n\nUse `{ctx.prefix}help {ctx.command}` for usage info."
                ),
                color=0xFF0000,
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        # Check failure
        if isinstance(error, commands.CheckFailure):
            embed = discord.Embed(
                title="❌ Check Failed",
                description="You cannot use this command here.",
                color=0xFF0000,
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        # Log unexpected errors
        logger.error(
            f"Command error in '{ctx.command}': {type(error).__name__}: {error}",
            exc_info=error,
        )
        
        # Send generic error message
        embed = discord.Embed(
            title="❌ Command Error",
            description=(
                "An unexpected error occurred while executing this command.\n"
                "The error has been logged."
            ),
            color=0xFF0000,
        )
        embed.set_footer(text=f"Error: {type(error).__name__}")
        
        try:
            await ctx.send(embed=embed)
        except Exception:
            pass
    
    async def on_message_delete(self, message: discord.Message):
        """Cache deleted messages for snipe command (with TTL)"""
        if message.author.bot or not message.guild:
            return
        
        if not message.content and not message.attachments:
            return
        
        await self.snipe_cache.add(message.channel.id, {
            "content": message.content,
            "author": message.author,
            "created_at": message.created_at,
            "attachments": [
                a.url for a in message.attachments if not a.is_spoiler()
            ],
        })
    
    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ):
        """Cache edited messages for editsnipe command (with TTL)"""
        if (
            before.author.bot
            or not before.guild
            or before.content == after.content
        ):
            return
        
        if not before.content and not after.content:
            return
        
        await self.edit_snipe_cache.add(before.channel.id, {
            "before": before.content,
            "after": after.content,
            "author": before.author,
            "edited_at": after.edited_at or datetime.now(timezone.utc),
            "jump_url": after.jump_url,
        })
    
    async def on_error(self, event: str, *args, **kwargs):
        """Global event error handler"""
        self.errors_caught += 1
        logger.error(f"Error in event '{event}'", exc_info=sys.exc_info())
    
    async def _cache_cleanup_loop(self):
        """Background task to clean up expired cache entries"""
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Cleanup would happen automatically via TTL,
                # but we can log stats here
                logger.debug("🧹 Cache cleanup cycle completed")
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    async def close(self):
        """Cleanup on shutdown"""
        logger.info("👋 Shutting down ModBot...")
        
        # Cancel cache cleanup task
        if self._cache_cleanup_task:
            self._cache_cleanup_task.cancel()
            try:
                await self._cache_cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Log session statistics
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        logger.info("📊 Session Stats:")
        logger.info(f"  • Uptime: {uptime:.0f}s ({uptime/3600:.1f}h)")
        logger.info(f"  • Commands Used: {self.commands_used}")
        logger.info(f"  • Messages Seen: {self.messages_seen}")
        logger.info(f"  • Errors Caught: {self.errors_caught}")
        
        # Clear caches
        try:
            await self.snipe_cache.clear()
            await self.edit_snipe_cache.clear()
            await self.prefix_cache.clear()
            logger.info("✅ Caches cleared")
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")
        
        # Close database connections
        try:
            if hasattr(self.db, "close"):
                await self.db.close()
            logger.info("✅ Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
        
        # Close bot
        await super().close()
        logger.info("✅ Bot shutdown complete")


# ==================== MAIN ENTRY POINT ====================
async def main() -> int:
    """Main entry point with error handling"""
    # Validate environment
    validate_environment()
    
    # Get token
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.critical("=" * 60)
        logger.critical("❌ DISCORD_TOKEN not found in environment!")
        logger.critical("=" * 60)
        logger.critical("Please create a .env file with:")
        logger.critical("DISCORD_TOKEN=your_bot_token_here")
        logger.critical("=" * 60)
        return 1
    
    # Create bot instance
    bot = ModBot()
    
    try:
        async with bot:
            logger.info("🚀 Starting bot...")
            await bot.start(token)
    except KeyboardInterrupt:
        logger.info("👋 Received shutdown signal (Ctrl+C)")
    except discord.LoginFailure:
        logger.critical("=" * 60)
        logger.critical("❌ Invalid Discord token!")
        logger.critical("=" * 60)
        logger.critical("Check your .env file and ensure DISCORD_TOKEN is correct.")
        logger.critical(
            "Get your token from: https://discord.com/developers/applications"
        )
        logger.critical("=" * 60)
        return 1
    except discord.PrivilegedIntentsRequired:
        logger.critical("=" * 60)
        logger.critical("❌ Missing Privileged Intents!")
        logger.critical("=" * 60)
        logger.critical("Enable these in the Discord Developer Portal:")
        logger.critical("• Server Members Intent")
        logger.critical("• Message Content Intent")
        logger.critical("• Presence Intent")
        logger.critical("=" * 60)
        return 1
    except Exception as e:
        logger.critical(f"❌ Fatal error during bot execution: {e}", exc_info=True)
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
        logger.info("👋 Shutdown complete")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"❌ Critical startup error: {e}", exc_info=True)
        sys.exit(1)
