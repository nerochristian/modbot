"""
LifeSimBot - A comprehensive Discord life simulation bot
Uses Discord Components V2 for modern UI interactions
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite

# Import environment variables
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Prefer project-level .env, then local override if present.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BASE_DIR / ".env")


def _resolve_runtime_path(raw_path: Optional[str], default_path: Path) -> Path:
    path = Path(raw_path).expanduser() if raw_path else default_path
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def _get_env_int(var_name: str, default: int) -> int:
    raw = os.getenv(var_name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default

DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
LOG_FILE_PATH = _resolve_runtime_path(
    os.getenv("LIFESIM_LOG_FILE") or os.getenv("LOG_FILE"),
    BASE_DIR / "bot.log",
)
LOG_FILE = str(LOG_FILE_PATH)


def _enable_windows_ansi() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE = -11
        if handle == 0 or handle == -1:
            return
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        return


@dataclass(frozen=True)
class _Ansi:
    reset: str = "\x1b[0m"
    bold: str = "\x1b[1m"
    dim: str = "\x1b[2m"

    red: str = "\x1b[31m"
    green: str = "\x1b[32m"
    yellow: str = "\x1b[33m"
    cyan: str = "\x1b[36m"
    gray: str = "\x1b[90m"


ANSI = _Ansi()
USE_COLOR = False
OK_TAG = "[OK]"
WARN_TAG = "[WARN]"
ERR_TAG = "[ERR]"


def _supports_color() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    stream = sys.stdout
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    return True


class _ColorFormatter(logging.Formatter):
    def __init__(self, *, use_color: bool):
        super().__init__("%(asctime)s | %(levelname)s | %(name)s | %(message)s", "%H:%M:%S")
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        if not self.use_color:
            return msg

        if record.levelno >= logging.ERROR:
            color = ANSI.red
        elif record.levelno >= logging.WARNING:
            color = ANSI.yellow
        elif record.levelno >= logging.INFO:
            color = ANSI.cyan
        else:
            color = ANSI.gray

        return f"{color}{msg}{ANSI.reset}"


def _setup_logging() -> logging.Logger:
    _enable_windows_ansi()
    global USE_COLOR
    use_color = _supports_color()
    USE_COLOR = use_color

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    root.handlers.clear()

    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    console_handler.setFormatter(_ColorFormatter(use_color=use_color))

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    return logging.getLogger("LifeSimBot")


logger = _setup_logging()

# Import database/utils (supports direct script and package import modes)
try:
    from db.database import DatabaseManager, db as database
    from utils.constants import *
    from utils.format import format_currency, format_time, format_percentage
    from utils.checks import is_registered, has_permissions, safe_reply
    from views.v2_embed import patch_layoutview_declarative_items
except ImportError:
    from .db.database import DatabaseManager, db as database
    from .utils.constants import *
    from .utils.format import format_currency, format_time, format_percentage
    from .utils.checks import is_registered, has_permissions, safe_reply
    from .views.v2_embed import patch_layoutview_declarative_items


# Work around discord.py alpha LayoutView bug where @discord.ui.button controls
# are not auto-registered on many views.
patch_layoutview_declarative_items()

# Bot configuration
TOKEN = os.getenv("LIFESIM_DISCORD_TOKEN") or os.getenv("DISCORD_TOKEN")
DATABASE_PATH = str(
    _resolve_runtime_path(
        os.getenv("LIFESIM_DATABASE_PATH") or os.getenv("DATABASE_PATH"),
        BASE_DIR / "life_sim.db",
    )
)
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '/')
SYNC_COMMANDS = os.getenv("LIFESIM_SYNC_COMMANDS", "true").lower() == "true"
SYNC_TIMEOUT_SECONDS = _get_env_int("LIFESIM_SYNC_TIMEOUT_SECONDS", 45)
SYNC_GUILD_ID = os.getenv("LIFESIM_SYNC_GUILD_ID")

# Intents configuration
intents = discord.Intents.default()
intents.message_content = os.getenv('INTENTS_MESSAGE_CONTENT', 'true').lower() == 'true'
intents.members = os.getenv('INTENTS_MEMBERS', 'true').lower() == 'true'
intents.presences = os.getenv('INTENTS_PRESENCES', 'false').lower() == 'true'

class LifeSimBot(commands.Bot):
    """
    Main bot class for LifeSimBot
    Implements Discord Components V2 for modern UI
    """
    
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(COMMAND_PREFIX),
            intents=intents,
            help_command=None,  # Custom help command
            case_insensitive=True,
            description="A comprehensive life simulation bot with economy, businesses, and more!",
            owner_ids=self._get_owner_ids()
        )
        
        self.db: Optional[DatabaseManager] = None
        self.start_time = datetime.now(timezone.utc)
        self.command_usage = {}
        self.user_cache = {}
        self.cooldowns = {}
        self.active_sessions = {}  # For tracking active minigames, duels, etc.
        self.startup_report: dict[str, object] = {}
        self.cog_package = f"{__package__}.cogs" if __package__ else "cogs"
        
        # Feature flags
        self.features = {
            'economy': os.getenv('ENABLE_ECONOMY', 'true').lower() == 'true',
            'casino': os.getenv('ENABLE_CASINO', 'true').lower() == 'true',
            'crypto': os.getenv('ENABLE_CRYPTO', 'true').lower() == 'true',
            'businesses': os.getenv('ENABLE_BUSINESSES', 'true').lower() == 'true',
            'properties': os.getenv('ENABLE_PROPERTIES', 'true').lower() == 'true',
            'jobs': os.getenv('ENABLE_JOBS', 'true').lower() == 'true',
            'skills': os.getenv('ENABLE_SKILLS', 'true').lower() == 'true',
            'pets': os.getenv('ENABLE_PETS', 'true').lower() == 'true',
            'cooking': os.getenv('ENABLE_COOKING', 'true').lower() == 'true',
            'crime': os.getenv('ENABLE_CRIME', 'true').lower() == 'true',
            'duels': os.getenv('ENABLE_DUELS', 'true').lower() == 'true',
            'guilds': os.getenv('ENABLE_GUILDS', 'true').lower() == 'true',
            'families': os.getenv('ENABLE_FAMILIES', 'true').lower() == 'true',
            'achievements': os.getenv('ENABLE_ACHIEVEMENTS', 'true').lower() == 'true',
            'quests': os.getenv('ENABLE_QUESTS', 'true').lower() == 'true',
            'events': os.getenv('ENABLE_EVENTS', 'true').lower() == 'true',
        }
        
        self._log_startup_banner()
    
    def _get_owner_ids(self) -> List[int]:
        """Parse owner IDs from environment"""
        admin_ids = os.getenv('ADMIN_IDS', '')
        if admin_ids:
            try:
                return [int(id.strip()) for id in admin_ids.split(',') if id.strip()]
            except ValueError:
                logger.warning("Invalid ADMIN_IDS format in .env")
        return []

    def _log_startup_banner(self) -> None:
        enabled = [k for k, v in self.features.items() if v]
        bold = ANSI.bold if USE_COLOR else ""
        dim = ANSI.dim if USE_COLOR else ""
        reset = ANSI.reset if USE_COLOR else ""
        logger.info(f"{bold}LifeSimBot{reset} starting up")
        logger.info(
            f"{dim}Python{reset} {platform.python_version()} | "
            f"{dim}discord.py{reset} {discord.__version__} | "
            f"{dim}OS{reset} {platform.system()} {platform.release()}"
        )
        logger.info(f"{dim}DB{reset} {DATABASE_PATH} | {dim}Log{reset} {LOG_FILE}")
        logger.info(f"{dim}Debug{reset} {DEBUG_MODE} | {dim}Features{reset} {len(enabled)} enabled")
    
    async def setup_hook(self):
        """
        Called when the bot is starting up
        Load cogs and sync commands
        """
        started = datetime.now(timezone.utc)
        self.startup_report = {"started_at": started.isoformat()}
        logger.info("Initializing...")

        # Initialize database
        try:
            self.db = database
            self.db.db_path = DATABASE_PATH
            await self.db.initialize()
            self.startup_report["db_ok"] = True
            logger.info(f"{OK_TAG} Database initialized")
        except Exception:
            self.startup_report["db_ok"] = False
            logger.error(f"{ERR_TAG} Database initialization failed")
            logger.error(traceback.format_exc())
            raise

        # Load all cogs
        loaded, failed = await self.load_cogs()
        self.startup_report["cogs_loaded"] = loaded
        self.startup_report["cogs_failed"] = failed

        # Sync commands with Discord (bounded timeout to avoid startup stalls)
        if SYNC_COMMANDS:
            try:
                if SYNC_GUILD_ID:
                    guild_obj = discord.Object(id=int(SYNC_GUILD_ID))
                    synced = await asyncio.wait_for(
                        self.tree.sync(guild=guild_obj),
                        timeout=SYNC_TIMEOUT_SECONDS,
                    )
                    logger.info(
                        f"{OK_TAG} Synced {len(synced)} application commands "
                        f"to guild {SYNC_GUILD_ID}"
                    )
                else:
                    synced = await asyncio.wait_for(
                        self.tree.sync(),
                        timeout=SYNC_TIMEOUT_SECONDS,
                    )
                    logger.info(f"{OK_TAG} Synced {len(synced)} application commands")

                self.startup_report["sync_ok"] = True
                self.startup_report["commands_synced"] = len(synced)
            except asyncio.TimeoutError:
                self.startup_report["sync_ok"] = False
                self.startup_report["commands_synced"] = 0
                logger.warning(
                    f"{WARN_TAG} Command sync timed out after "
                    f"{SYNC_TIMEOUT_SECONDS}s; continuing startup"
                )
            except Exception:
                self.startup_report["sync_ok"] = False
                self.startup_report["commands_synced"] = 0
                logger.error(f"{ERR_TAG} Failed to sync application commands")
                logger.error(traceback.format_exc())
        else:
            self.startup_report["sync_ok"] = None
            self.startup_report["commands_synced"] = 0
            logger.info("Command sync disabled (LIFESIM_SYNC_COMMANDS=false)")

        # Start background tasks
        self.start_background_tasks()

        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        if failed:
            logger.warning(f"{WARN_TAG} Startup completed with {len(failed)} cog error(s) in {elapsed:.2f}s")
            for entry in failed[:8]:
                logger.warning(f" - {entry['name']}: {entry['error']}")
            if len(failed) > 8:
                logger.warning(f" - ... and {len(failed) - 8} more")
        else:
            logger.info(f"{OK_TAG} Ready (startup {elapsed:.2f}s)")
    
    async def load_cogs(self) -> tuple[list[str], list[dict[str, str]]]:
        """Load all cog extensions"""
        cogs_dir = BASE_DIR / "cogs"
        cogs_to_load = []
        
        # Define cog loading order (some cogs depend on others)
        priority_cogs = [
            'core_cog',
            'economy_cog',
            'help_cog',
            'hub_cog'
        ]
        
        # Load priority cogs first
        for cog_name in priority_cogs:
            if (cogs_dir / f"{cog_name}.py").exists():
                cogs_to_load.append(cog_name)
        
        # Load remaining cogs
        for cog_file in cogs_dir.glob('*.py'):
            if cog_file.stem != '__init__' and cog_file.stem not in priority_cogs:
                # Skip empty placeholder files
                try:
                    if cog_file.read_text(encoding='utf-8').strip() == "":
                        logger.info(f"Skipping {cog_file.stem} (empty placeholder)")
                        continue
                except Exception:
                    pass

                # Avoid duplicate commands (core_cog already provides /leaderboard)
                if cog_file.stem == "leaderboard_cog":
                    logger.info("Skipping leaderboard_cog (handled by core_cog)")
                    continue

                # Check if feature is enabled
                feature_name = cog_file.stem.replace('_cog', '')
                if feature_name in self.features and not self.features[feature_name]:
                    logger.info(f"Skipping {cog_file.stem} (feature disabled)")
                    continue
                cogs_to_load.append(cog_file.stem)
        
        # Load cogs
        loaded: list[str] = []
        failed: list[dict[str, str]] = []
        for cog_name in cogs_to_load:
            try:
                await self.load_extension(f"{self.cog_package}.{cog_name}")
                loaded.append(cog_name)
                logger.info(f"{OK_TAG} Loaded cog: {cog_name}")
            except Exception as e:
                failed.append({"name": cog_name, "error": str(e)})
                logger.error(f"{ERR_TAG} Failed to load cog {cog_name}: {e}")
                logger.error(traceback.format_exc())

        logger.info(f"Cogs: {len(loaded)} loaded, {len(failed)} failed")
        return loaded, failed
    
    def start_background_tasks(self):
        """Start all background tasks"""
        if not self.update_stats.is_running():
            self.update_stats.start()
        if not self.check_cooldowns.is_running():
            self.check_cooldowns.start()
        if not self.auto_save.is_running():
            self.auto_save.start()
        
        logger.info("Background tasks started")
    
    @tasks.loop(minutes=5)
    async def update_stats(self):
        """Update bot statistics periodically"""
        try:
            # Update server count, user count, etc.
            guild_count = len(self.guilds)
            user_count = sum(g.member_count for g in self.guilds)
            
            # Update presence
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{guild_count} servers | /help"
                )
            )
            
            logger.debug(f"Stats updated - Guilds: {guild_count}, Users: {user_count}")
        except Exception as e:
            logger.error(f"Error updating stats: {e}")
    
    @update_stats.before_loop
    async def before_update_stats(self):
        """Wait until bot is ready before starting stats updates"""
        await self.wait_until_ready()
    
    @tasks.loop(seconds=30)
    async def check_cooldowns(self):
        """Clean up expired cooldowns"""
        try:
            current_time = datetime.now(timezone.utc)
            expired_keys = [
                key for key, expiry in self.cooldowns.items()
                if expiry < current_time
            ]
            for key in expired_keys:
                del self.cooldowns[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cooldowns")
        except Exception as e:
            logger.error(f"Error checking cooldowns: {e}")
    
    @tasks.loop(hours=1)
    async def auto_save(self):
        """Perform auto-save operations"""
        try:
            if self.db:
                await self.db.backup()
                logger.info("Database auto-backup completed")
        except Exception as e:
            logger.error(f"Error during auto-save: {e}")
    
    @auto_save.before_loop
    async def before_auto_save(self):
        """Wait until bot is ready before starting auto-save"""
        await self.wait_until_ready()
    
    async def on_ready(self):
        """Called when bot is fully ready"""
        guild_count = len(self.guilds)
        user_count = sum(g.member_count for g in self.guilds)
        latency_ms = int(self.latency * 1000) if self.latency is not None else 0
        sep = "=" * 52
        logger.info(sep)
        logger.info(f"{OK_TAG} Logged in as {self.user} ({self.user.id})")
        logger.info(f"Guilds: {guild_count} | Users: {user_count} | Latency: {latency_ms}ms")
        logger.info(sep)
        
        # Set initial presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | /help"
            ),
            status=discord.Status.online
        )

    async def on_error(self, event_method: str, *args, **kwargs):
        """Global event error handler (prevents silent failures)."""
        logger.error(f"{ERR_TAG} Event error in {event_method}")
        logger.error(traceback.format_exc())
    
    async def on_guild_join(self, guild: discord.Guild):
        """Called when bot joins a guild"""
        logger.info(f"Joined guild: {guild.name} ({guild.id}) - {guild.member_count} members")
        
        # Send welcome message to first available text channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                embed = discord.Embed(
                    title="👋 Thanks for adding LifeSimBot!",
                    description=(
                        "I'm a comprehensive life simulation bot with economy, "
                        "businesses, jobs, skills, and much more!\n\n"
                        "**Getting Started:**\n"
                        "• Use `/register` to create your account\n"
                        "• Use `/help` to see all available commands\n"
                        "• Use `/hub` to access the main menu\n\n"
                        "**Need Help?**\n"
                        "Join our support server: [Coming Soon]\n"
                        "Check out the documentation: [Coming Soon]"
                    ),
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=self.user.display_avatar.url if self.user else None)
                embed.set_footer(text=f"Serving {len(self.guilds)} servers")
                
                try:
                    await channel.send(embed=embed)
                    break
                except discord.Forbidden:
                    continue
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Called when bot leaves a guild"""
        logger.info(f"Left guild: {guild.name} ({guild.id})")
    
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Global error handler for traditional commands"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏰ Command on cooldown. Try again in {format_time(int(error.retry_after))}"
            )
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have the required permissions to execute this command.")
        else:
            logger.error(f"Command error: {error}")
            logger.error(traceback.format_exc())
            await ctx.send("❌ An error occurred while processing the command.")
    
    async def on_app_command_error(
        self, 
        interaction: discord.Interaction, 
        error: app_commands.AppCommandError
    ):
        """Global error handler for slash commands"""
        try:
            if isinstance(error, app_commands.CommandOnCooldown):
                return await safe_reply(
                    interaction,
                    content=f"⏱️ Command on cooldown. Try again in {format_time(int(error.retry_after))}.",
                    ephemeral=True,
                )

            if isinstance(error, app_commands.MissingPermissions):
                return await safe_reply(
                    interaction,
                    content="❌ You don't have permission to use this command.",
                    ephemeral=True,
                )

            if isinstance(error, app_commands.BotMissingPermissions):
                return await safe_reply(
                    interaction,
                    content="❌ I don't have the required permissions to execute this command.",
                    ephemeral=True,
                )

            logger.error(f"App command error: {error}")
            logger.error(traceback.format_exc())
            return await safe_reply(
                interaction,
                content="❌ An error occurred while processing the command.",
                ephemeral=True,
            )
        except (discord.NotFound, discord.HTTPException):
            return

    async def close(self):
        """Cleanup when bot is shutting down"""
        logger.info("Bot shutting down...")
        
        # Cancel background tasks
        if self.update_stats.is_running():
            self.update_stats.cancel()
        if self.check_cooldowns.is_running():
            self.check_cooldowns.cancel()
        if self.auto_save.is_running():
            self.auto_save.cancel()
        
        # Close database
        if self.db:
            await self.db.close()
        
        await super().close()
        logger.info("Bot shutdown complete")

# Bot instance
bot = LifeSimBot()

# Main entry point
def _asyncio_exception_handler(loop: asyncio.AbstractEventLoop, context: dict):
    exc = context.get("exception")
    msg = context.get("message")
    if exc is not None:
        logger.error(f"{ERR_TAG} Asyncio exception: {exc}")
        logger.error("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        return
    if msg:
        logger.error(f"{ERR_TAG} Asyncio error: {msg}")
        return


def _excepthook(exc_type, exc, tb):
    if issubclass(exc_type, KeyboardInterrupt):
        return
    logger.critical(f"{ERR_TAG} Unhandled exception: {exc}")
    logger.critical("".join(traceback.format_exception(exc_type, exc, tb)))


async def main():
    """Main function to run the bot"""
    try:
        try:
            loop = asyncio.get_running_loop()
            loop.set_exception_handler(_asyncio_exception_handler)
        except Exception:
            pass

        async with bot:
            logger.info("Connecting to Discord...")
            await bot.start(TOKEN)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"{ERR_TAG} Fatal error: {e}")
        logger.error(traceback.format_exc())
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    sys.excepthook = _excepthook
    if not TOKEN:
        logger.error(f"{ERR_TAG} DISCORD_TOKEN is missing (check your `.env`)")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"{ERR_TAG} Failed to run bot: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
