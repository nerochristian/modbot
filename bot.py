"""
ModBot - Advanced Discord Moderation Bot
Enterprise-grade moderation system with comprehensive logging
Version 3.3.0 - Complete Database Overhaul
"""

import discord
from discord.ext import commands
from discord.ext.commands.converter import run_converters
import logging
import os
import re
import sys
import asyncio
import atexit
import subprocess
import shlex
from difflib import SequenceMatcher
import inspect
from datetime import datetime, timezone
from typing import Optional, Dict, Any, get_args, get_origin
from pathlib import Path
from dotenv import load_dotenv

from config import Config
from utils.embeds import ModEmbed
from utils.status_emojis import (
    apply_status_emoji_overrides,
    get_loading_emoji_for_guild,
    get_status_emoji_for_guild,
    sync_status_emojis_to_application,
)

# Load environment variables
load_dotenv()

# ==================== SINGLE-INSTANCE LOCK ====================
_LOCK_HANDLE = None

def _acquire_single_instance_lock() -> None:
    """Prevent multiple bot instances on the same machine."""
    global _LOCK_HANDLE
    try:
        import msvcrt  # Windows-only
    except ImportError:
        return
    lock_path = Path(".modbot.lock")
    _LOCK_HANDLE = lock_path.open("a+")
    try:
        msvcrt.locking(_LOCK_HANDLE.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        raise RuntimeError("Another ModBot instance is already running.")
    # Lock ownership is enforced by msvcrt.locking; pid text is best-effort
    # metadata and should never crash startup if filesystem permissions are odd.
    try:
        _LOCK_HANDLE.seek(0)
        _LOCK_HANDLE.truncate()
        _LOCK_HANDLE.write(str(os.getpid()))
        _LOCK_HANDLE.flush()
    except OSError:
        pass

    def _release_lock():
        try:
            msvcrt.locking(_LOCK_HANDLE.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception:
            pass
        try:
            _LOCK_HANDLE.close()
        except Exception:
            pass

    atexit.register(_release_lock)

# Initialize static-ffmpeg if installed (ensures ffmpeg binary is in PATH)
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
    print("[Setup] Static FFmpeg initialized successfully")
except ImportError:
    pass

# ==================== GLOBAL EMBED DEFAULT COLOR ====================
# Applies Config.EMBED_ACCENT_COLOR only when no explicit embed color is set.
_ORIGINAL_EMBED_INIT = discord.Embed.__init__

def _embed_init_force_accent(self, *args, **kwargs):
    explicit_colour = kwargs.pop("colour", None)
    if "color" not in kwargs and explicit_colour is not None:
        kwargs["color"] = explicit_colour
    if "color" not in kwargs or kwargs["color"] is None:
        kwargs["color"] = getattr(Config, "EMBED_ACCENT_COLOR", 0x5865F2)
    return _ORIGINAL_EMBED_INIT(self, *args, **kwargs)

discord.Embed.__init__ = _embed_init_force_accent

# ==================== ENVIRONMENT VALIDATION ====================
def _get_modbot_token() -> Optional[str]:
    """Resolve ModBot token with explicit override support."""
    return os.getenv("MODBOT_DISCORD_TOKEN") or os.getenv("DISCORD_TOKEN")


def validate_environment() -> None:
    """Validate required environment variables"""
    optional_warnings = ["GROQ_API_KEY", "OWNER_IDS"]
    logger = logging.getLogger("ModBot")

    if not _get_modbot_token():
        logger.critical(
            "ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Missing required bot token: set MODBOT_DISCORD_TOKEN "
            "(or DISCORD_TOKEN fallback)."
        )
        sys.exit(1)

    for var in optional_warnings:
        if not os.getenv(var):
            logger.warning(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â Optional environment variable not set: {var}")

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
        "DEBUG": "\x1b[36m",
        "INFO": "\x1b[32m",
        "WARNING": "\x1b[33m",
        "ERROR": "\x1b[31m",
        "CRITICAL": "\x1b[35m",
        "RESET": "\x1b[0m",
    }

    EMOJI_FALLBACK = {
        "\u2705": "[OK]",
        "\u274c": "[ERR]",
        "\u26a1": "[>>]",
        "\U0001f916": "[BOT]",
        "\U0001f4e1": "[NET]",
        "\U0001f44b": "[BYE]",
        "\u26a0\ufe0f": "[!]",
        "\U0001f527": "[CFG]",
        "\U0001f4ac": "[CMD]",
        "\U0001f4e6": "[COG]",
        "\U0001f465": "[USR]",
        "\U0001f680": "[START]",
        "\U0001f5c4\ufe0f": "[DB]",
    }

    @staticmethod
    def _repair_mojibake(text: str) -> str:
        repaired = text
        for _ in range(3):
            if not any(ch in repaired for ch in ("\u00c3", "\u00c2", "\u00e2", "\u00f0")):
                break

            candidate = repaired
            for source_encoding in ("cp1252", "latin-1"):
                try:
                    candidate = repaired.encode(source_encoding).decode("utf-8")
                    break
                except UnicodeError:
                    continue

            if candidate == repaired:
                break

            repaired = candidate

        return repaired

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        msg = self._repair_mojibake(msg)
        for emoji, fallback in self.EMOJI_FALLBACK.items():
            msg = msg.replace(emoji, fallback)

        # Last-resort cleanup for any remaining mojibake fragments.
        if any(ch in msg for ch in ("\u00c3", "\u00c2", "\u00e2", "\u00f0")):
            msg = msg.encode("ascii", "ignore").decode("ascii")

        try:
            encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
            msg.encode(encoding)
        except (UnicodeEncodeError, LookupError, AttributeError):
            for emoji, fallback in self.EMOJI_FALLBACK.items():
                msg = msg.replace(emoji, fallback)

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
    from utils.components_v2 import (
        ComponentsV2Config,
        patch_components_v2,
        layout_view_from_embeds,
    )
except ImportError as e:
    logger.critical(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Failed to import required modules: {e}")
    sys.exit(1)

# Web dashboard (optional ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â runs if DISCORD_CLIENT_ID + DISCORD_CLIENT_SECRET are set)
try:
    from web.app import start_dashboard
    _DASHBOARD_AVAILABLE = True
except ImportError:
    _DASHBOARD_AVAILABLE = False

# Install Components v2 patching, but keep classic v1 embeds as default.
patch_components_v2()
ComponentsV2Config.disable()


def _env_enabled(var_name: str, default: bool = False) -> bool:
    raw = os.getenv(var_name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _start_lifesim_process() -> Optional[subprocess.Popen]:
    """
    Optionally start LifeSimBot as a managed child process.

    Requires LIFESIM_DISCORD_TOKEN to avoid running two clients on one token.
    """
    if not _env_enabled("RUN_LIFESIM_WITH_MODBOT", default=True):
        logger.info("LifeSimBot child process disabled via RUN_LIFESIM_WITH_MODBOT")
        return None

    project_root = Path(__file__).resolve().parent
    lifesim_script: Optional[Path] = None
    for folder_name in ("lifesimbot", "LifeSimBot"):
        candidate = project_root / folder_name / "bot.py"
        if candidate.exists():
            lifesim_script = candidate
            break
    if lifesim_script is None:
        for child in project_root.iterdir():
            if child.is_dir() and child.name.lower() == "lifesimbot":
                candidate = child / "bot.py"
                if candidate.exists():
                    lifesim_script = candidate
                    break
    if lifesim_script is None:
        logger.warning("LifeSimBot entrypoint not found in ./lifesimbot/bot.py")
        return None

    mod_token = _get_modbot_token()
    lifesim_token = os.getenv("LIFESIM_DISCORD_TOKEN")

    if not lifesim_token:
        logger.warning(
            "LIFESIM_DISCORD_TOKEN is not set; skipping LifeSimBot child process."
        )
        return None

    if mod_token and lifesim_token == mod_token:
        logger.warning(
            "LIFESIM_DISCORD_TOKEN matches the ModBot token "
            "(MODBOT_DISCORD_TOKEN / DISCORD_TOKEN); skipping LifeSimBot "
            "to prevent token session conflicts."
        )
        return None

    child_env = os.environ.copy()
    # LifeSimBot reads LIFESIM_DISCORD_TOKEN first, then DISCORD_TOKEN.
    child_env["DISCORD_TOKEN"] = lifesim_token

    try:
        proc = subprocess.Popen(
            [sys.executable, str(lifesim_script)],
            cwd=str(lifesim_script.parent),
            env=child_env,
        )
        logger.info(f"Started LifeSimBot (pid={proc.pid})")
        return proc
    except Exception as e:
        logger.error(f"Failed to start LifeSimBot child process: {e}", exc_info=True)
        return None


def _stop_lifesim_process(proc: Optional[subprocess.Popen]) -> None:
    """Stop managed LifeSimBot child process if it's still running."""
    if not proc:
        return

    try:
        if proc.poll() is not None:
            logger.info(f"LifeSimBot exited with code {proc.returncode}")
            return

        proc.terminate()
        try:
            proc.wait(timeout=10)
            logger.info("LifeSimBot child process stopped")
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
            logger.warning("LifeSimBot child process was force-killed after timeout")
    except Exception as e:
        logger.error(f"Error while stopping LifeSimBot child process: {e}")


class TargetResolvePromptView(discord.ui.View):
    """Confirm/cancel prompt when a member argument was close but not exact."""

    def __init__(
        self,
        *,
        bot: "ModBot",
        ctx: commands.Context,
        candidate: discord.Member,
        args_tail: str,
        confirm_emoji: object = None,
        cancel_emoji: object = None,
    ) -> None:
        super().__init__(timeout=45)
        self._bot = bot
        self._ctx = ctx
        self._candidate = candidate
        self._args_tail = args_tail
        self._finalized = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self.prompt_message: Optional[discord.Message] = None

        confirm_emoji = self._safe_button_emoji(
            confirm_emoji if confirm_emoji is not None else getattr(Config, "EMOJI_SUCCESS", "\u2705"),
            "\u2705",
        )
        cancel_emoji = self._safe_button_emoji(
            cancel_emoji if cancel_emoji is not None else getattr(Config, "EMOJI_ERROR", "\u274c"),
            "\u274c",
        )

        confirm_button = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="Confirm",
            emoji=confirm_emoji,
        )
        cancel_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Cancel",
            emoji=cancel_emoji,
        )

        async def _confirm(interaction: discord.Interaction):
            await self._on_confirm(interaction)

        async def _cancel(interaction: discord.Interaction):
            await self._on_cancel(interaction)

        confirm_button.callback = _confirm
        cancel_button.callback = _cancel
        self.add_item(confirm_button)
        self.add_item(cancel_button)

    def _safe_button_emoji(self, value: object, fallback: str) -> object:
        text = str(value or "").strip()
        if not text:
            return fallback
        if text.startswith("<:") or text.startswith("<a:"):
            try:
                parsed = discord.PartialEmoji.from_str(text)
                return parsed
            except Exception:
                return fallback
        return text

    async def _verify_interaction(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self._ctx.author.id:
            try:
                await interaction.response.send_message("Only the command author can use these buttons.", ephemeral=True)
            except Exception:
                pass
            return False
        if not self._finalized:
            return True
        try:
            await interaction.response.send_message("This prompt is already resolved.", ephemeral=True)
        except Exception:
            pass
        return False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await self._verify_interaction(interaction)

    async def _disable_and_update(self, interaction: discord.Interaction) -> None:
        self._finalized = True
        self.prompt_message = interaction.message or self.prompt_message
        for child in self.children:
            try:
                child.disabled = True
            except Exception:
                continue
        # When this prompt is sent as Components v2, editing with a classic View can
        # strip the card container. Skip visual disable there and rely on _finalized.
        if not list(getattr(interaction.message, "embeds", []) or []):
            return
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

    def _schedule_prompt_cleanup(self, delay_seconds: int = 10) -> None:
        if self._cleanup_task is not None and not self._cleanup_task.done():
            return

        async def _cleanup() -> None:
            await asyncio.sleep(max(1, delay_seconds))
            msg = self.prompt_message
            if msg is None:
                return
            try:
                await msg.delete()
            except Exception:
                pass

        self._cleanup_task = asyncio.create_task(_cleanup())

    async def _on_confirm(self, interaction: discord.Interaction) -> None:
        if not await self._verify_interaction(interaction):
            return
        await interaction.response.defer()
        await self._bot._clear_prefix_loading_for_ctx(self._ctx)
        await self._disable_and_update(interaction)
        self._schedule_prompt_cleanup(delay_seconds=10)

        try:
            ok, error_message = await self._bot._invoke_with_resolved_target(
                self._ctx,
                target=self._candidate,
                args_tail=self._args_tail,
            )
        except Exception as exc:
            ok = False
            error_message = str(exc)
        finally:
            await self._bot._clear_prefix_loading_for_ctx(self._ctx)
        if ok:
            return

        try:
            embed = ModEmbed.error(
                "Could not continue command",
                error_message or "I couldn't rebuild that command from the provided arguments.",
            )
            embed = await apply_status_emoji_overrides(embed, self._ctx.guild)
            await interaction.followup.send(embed=embed)
        except Exception:
            pass

    async def _on_cancel(self, interaction: discord.Interaction) -> None:
        if not await self._verify_interaction(interaction):
            return
        await interaction.response.defer()
        await self._bot._clear_prefix_loading_for_ctx(self._ctx)
        await self._disable_and_update(interaction)
        self._schedule_prompt_cleanup(delay_seconds=10)

    async def on_timeout(self) -> None:
        self._finalized = True
        for child in self.children:
            try:
                child.disabled = True
            except Exception:
                continue

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
        self.loading_emoji: str = getattr(Config, "EMOJI_LOADING", "\u23f3")
        self._prefix_loading_messages: dict[int, tuple[discord.Message, object]] = {}
        
        # Internal flags
        self._ready_once: bool = False
        self._cache_cleanup_task: Optional[asyncio.Task] = None
        self._dashboard_runner = None
        
        # Global blacklist cache (set of user IDs)
        self.blacklist_cache: set[int] = set()
    
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
            logger.warning("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â Invalid OWNER_IDS in .env, using default")
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
                if prefix is None:
                    prefix = "!" # Fallback if None but key exists
                
                # Check config override just in case
                if prefix == "!":
                    prefix = ","
                await self.prefix_cache.set(message.guild.id, prefix)
            except Exception as e:
                logger.error(f"Failed to get prefix for {message.guild.name}: {e}")
                prefix = ","
        
        return commands.when_mentioned_or(prefix)(self, message)

    async def _send_prefix_loading(self, ctx: commands.Context) -> None:
        """Add a temporary loading reaction for prefix commands."""
        message = getattr(ctx, "message", None)
        if not message:
            return
        if message.id in self._prefix_loading_messages:
            return

        reaction = await self._try_add_loading_reaction(message)
        if reaction is not None:
            self._prefix_loading_messages[message.id] = (message, reaction)

    def _resolve_loading_reaction(self, configured_emoji: Optional[str] = None) -> object:
        fallback = "\u23f3"
        raw = str(configured_emoji if configured_emoji is not None else self.loading_emoji or fallback).strip()
        if not raw:
            return fallback
        if raw.startswith("<:") or raw.startswith("<a:"):
            try:
                partial = discord.PartialEmoji.from_str(raw)
                emoji_id = getattr(partial, "id", None)
                if emoji_id is None:
                    return fallback
                return partial
            except Exception:
                return fallback
        return raw

    async def _try_add_loading_reaction(self, message: discord.Message) -> Optional[object]:
        configured = self.loading_emoji
        if message.guild is not None:
            try:
                configured = await get_loading_emoji_for_guild(
                    message.guild,
                    configured_emoji=self.loading_emoji,
                )
            except Exception:
                configured = self.loading_emoji

        reaction = self._resolve_loading_reaction(configured)
        try:
            await message.add_reaction(reaction)
            return reaction
        except Exception:
            fallback = "\u23f3"
            if reaction == fallback:
                return None
            try:
                await message.add_reaction(fallback)
                return fallback
            except Exception:
                return None

    async def _try_remove_loading_reaction(self, message: discord.Message, reaction: object) -> None:
        bot_user = self.user
        if bot_user is None:
            return
        try:
            await message.remove_reaction(reaction, bot_user)
            return
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

        def _emoji_id(value: object) -> Optional[int]:
            emoji_id = getattr(value, "id", None)
            if isinstance(emoji_id, int):
                return emoji_id
            text = str(value or "").strip()
            match = re.fullmatch(r"<a?:\w+:(\d+)>", text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    return None
            return None

        expected_id = _emoji_id(reaction)
        expected_text = str(reaction or "").strip()
        target_message = message

        try:
            target_message = await message.channel.fetch_message(message.id)
        except Exception:
            pass

        for reaction_obj in getattr(target_message, "reactions", []) or []:
            emoji_value = getattr(reaction_obj, "emoji", None)
            emoji_id = _emoji_id(emoji_value)
            matched = False
            if expected_id is not None and emoji_id is not None:
                matched = expected_id == emoji_id
            elif expected_text:
                matched = str(emoji_value or "").strip() == expected_text
            if not matched:
                continue
            try:
                await target_message.remove_reaction(emoji_value, bot_user)
                return
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                continue

    async def _clear_prefix_loading(self, message_id: Optional[int]) -> None:
        """Remove a previously added loading reaction."""
        if message_id is None:
            return
        loading_state = self._prefix_loading_messages.pop(message_id, None)
        if loading_state is None:
            return
        loading_message, reaction = loading_state
        await self._try_remove_loading_reaction(loading_message, reaction)

    async def _clear_prefix_loading_for_ctx(self, ctx: commands.Context) -> None:
        message = getattr(ctx, "message", None)
        await self._clear_prefix_loading(getattr(message, "id", None))

    @staticmethod
    def _is_member_like_annotation(annotation: object) -> bool:
        if annotation in (discord.Member, discord.User):
            return True
        origin = get_origin(annotation)
        if origin is None:
            return False
        return any(ModBot._is_member_like_annotation(arg) for arg in get_args(annotation))

    def _extract_first_argument_and_tail(self, ctx: commands.Context) -> tuple[str, str]:
        content = (getattr(ctx.message, "content", "") or "").strip()
        prefix = str(getattr(ctx, "prefix", "") or "")
        if prefix and content.startswith(prefix):
            content = content[len(prefix):].lstrip()

        if not content:
            return "", ""

        # Remove command token, then split into first arg + tail.
        command_name, _, arg_text = content.partition(" ")
        if not command_name or not arg_text:
            return "", ""
        first_arg, _, tail = arg_text.strip().partition(" ")
        return first_arg.strip(), tail.strip()

    @staticmethod
    def _normalize_member_query(raw: str) -> str:
        value = (raw or "").strip()
        # Mention style: <@123> / <@!123>
        mention = re.fullmatch(r"<@!?(\d{15,22})>", value)
        if mention:
            return mention.group(1)
        return value.strip("@").strip()

    def _find_best_member_match(self, guild: discord.Guild, raw_query: str) -> Optional[discord.Member]:
        query = self._normalize_member_query(raw_query)
        if not query:
            return None

        if query.isdigit():
            member = guild.get_member(int(query))
            if member is not None:
                return member

        q = query.casefold()
        best_member: Optional[discord.Member] = None
        best_score = 0.0

        for member in guild.members:
            names = [
                (member.display_name or "").strip(),
                (member.name or "").strip(),
                (getattr(member, "global_name", "") or "").strip(),
            ]
            local_best = 0.0
            for name in names:
                if not name:
                    continue
                n = name.casefold()
                if q == n:
                    return member
                if n.startswith(q):
                    local_best = max(local_best, 0.96)
                elif q in n:
                    local_best = max(local_best, 0.86)
                else:
                    local_best = max(local_best, SequenceMatcher(None, q, n).ratio())

            if local_best > best_score:
                best_score = local_best
                best_member = member

        if best_member is None:
            return None
        return best_member if best_score >= 0.55 else None

    @staticmethod
    def _split_tokens(arg_text: str) -> list[str]:
        text = (arg_text or "").strip()
        if not text:
            return []
        try:
            return shlex.split(text)
        except Exception:
            return text.split()

    async def _invoke_with_resolved_target(
        self,
        ctx: commands.Context,
        *,
        target: discord.Member,
        args_tail: str,
    ) -> tuple[bool, str]:
        command = ctx.command
        if command is None:
            return False, "Command context is missing."

        params = list(command.clean_params.items())
        if not params:
            return False, "Command has no usable parameters."

        first_name, _ = params[0]
        kwargs: dict[str, Any] = {first_name: target}
        tokens = self._split_tokens(args_tail)

        async def _convert_param(param: inspect.Parameter, raw_value: str) -> Any:
            if param.annotation is inspect.Parameter.empty:
                return raw_value
            return await run_converters(
                ctx,
                param.annotation,
                raw_value,
                param,
            )

        for name, param in params[1:]:
            # Unsupported shape for this generic resolver.
            if param.kind is inspect.Parameter.VAR_POSITIONAL:
                return False, "This command format is not supported by the quick resolver."

            if param.kind is inspect.Parameter.KEYWORD_ONLY:
                raw_value = " ".join(tokens).strip()
                tokens = []
                if not raw_value:
                    if param.default is inspect.Parameter.empty:
                        return False, f"Missing required argument `{name}`."
                    kwargs[name] = param.default
                else:
                    kwargs[name] = await _convert_param(param, raw_value)
                continue

            # Positional-or-keyword parameter.
            if tokens:
                raw_value = tokens.pop(0)
                kwargs[name] = await _convert_param(param, raw_value)
            elif param.default is not inspect.Parameter.empty:
                kwargs[name] = param.default
            else:
                return False, f"Missing required argument `{name}`."

        if tokens:
            extra = " ".join(tokens)
            return False, f"Too many arguments: `{extra}`."

        await ctx.invoke(command, **kwargs)
        return True, ""
    
    async def setup_hook(self):
        """Load cogs and sync slash commands"""
        logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ Initializing bot systems...")
        
        # Initialize database connection pool
        try:
            await self.db.init_pool()
        except Exception as e:
            logger.error(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Failed to initialize database pool: {e}")
            raise
        
        # Start cache cleanup task
        self._cache_cleanup_task = self.loop.create_task(self._cache_cleanup_loop())
        
        # Ensure cogs directory exists
        cogs_path = Path("./cogs")
        if not cogs_path.exists():
            logger.warning("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â Cogs directory not found, creating...")
            cogs_path.mkdir(exist_ok=True)
        
        # Cog list - CORE MODERATION BOT ONLY
        # AI cogs are in bot_ai.py
        # Support cogs are in bot_support.py
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
            "cogs.forum_moderation",
            "cogs.prefix_commands",
            # AI & Automation (Merged)
            "cogs.aimoderation",
            "cogs.automod",
            "cogs.antiraid",
            "cogs.voice",
            "cogs.settings",
            "cogs.polls",
            # Support & Tickets (Merged)
            "cogs.tickets",
            "cogs.modmail",
            "cogs.utility",
            "cogs.admin",
            "cogs.staff",
            "cogs.court",
            "cogs.whitelist",
        ]
        
        loaded: list[str] = []
        failed: list[tuple[str, str]] = []
        skipped: list[str] = []
        
        # Load each cog
        for cog in cogs:
            try:
                await self.load_extension(cog)
                loaded.append(cog)
                logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ Loaded: {cog}")
            except commands.ExtensionNotFound:
                skipped.append(cog)
                logger.debug(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â Skipped: {cog} (not found)")
            except commands.ExtensionAlreadyLoaded:
                logger.debug(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â Skipped: {cog} (already loaded)")
            except Exception as e:
                failed.append((cog, str(e)))
                logger.error(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Failed: {cog} - {e}")
        
        # Summary
        logger.info("=" * 60)
        logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¦ Cog Loading Summary:")
        logger.info(f"  ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ Loaded: {len(loaded)}")
        logger.info(f"  ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â Skipped: {len(skipped)}")
        logger.info(f"  ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Failed: {len(failed)}")
        if failed:
            logger.warning("  Failed cogs:")
            for cog, error in failed:
                logger.warning(f"    ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ {cog}: {error}")
        logger.info("=" * 60)
        
        # Display loaded commands
        logger.info("=" * 60)
        logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ Loaded {len(self.cogs)} cogs successfully")
        logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â  Total Commands: {len(list(self.walk_commands()))} prefix, {len(self.tree.get_commands())} slash")
        logger.info("=" * 60)
        
        # Set global interaction check for the tree
        self.tree.interaction_check = self._check_global_blacklist
        
        # Sync slash commands
        sync_guild_id = os.getenv("SYNC_GUILD_ID")
        try:
            if sync_guild_id:
                guild_object = discord.Object(id=int(sync_guild_id))
                logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ Syncing slash commands to specific guild: {sync_guild_id}...")
                self.tree.copy_global_to(guild=guild_object)
                synced = await self.tree.sync(guild=guild_object)
                logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ Successfully synced {len(synced)} slash commands to guild {sync_guild_id}")
            else:
                logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ Syncing slash commands globally (this may take up to 1 hour)...")
                synced = await self.tree.sync()
                logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ Successfully synced {len(synced)} slash commands globally")
        except discord.HTTPException as e:
            logger.error(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Failed to sync commands: {e}")
            self.errors_caught += 1
        except Exception as e:
            logger.error(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Unexpected error syncing commands: {e}")
            self.errors_caught += 1

        # Bind the global error handler
        self.tree.on_error = self.on_tree_error

        # Start web dashboard
        if _DASHBOARD_AVAILABLE:
            try:
                self._dashboard_runner = await start_dashboard(self)
            except Exception as e:
                logger.warning(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â Dashboard failed to start: {e}")
    
    async def on_tree_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Global error handler for application commands"""
        self.errors_caught += 1

        # Handle Missing Permissions
        if isinstance(error, discord.app_commands.MissingPermissions):
            missing = [p.replace('_', ' ').replace('guild', 'server').title() for p in error.missing_permissions]
            if len(missing) > 2:
                fmt = f"{', '.join(missing[:-1])}, and {missing[-1]}"
            else:
                fmt = " and ".join(missing)

            embed = ModEmbed.error(
                "Permission Denied",
                f"You are missing the following permission(s) to run this command:\n**{fmt}**",
            )
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception:
                pass
            return

        # Handle other errors (BotMissingPermissions, etc.)
        if isinstance(error, discord.app_commands.BotMissingPermissions):
            missing = [p.replace('_', ' ').replace('guild', 'server').title() for p in error.missing_permissions]
            embed = ModEmbed.error(
                "I Need Permissions",
                f"I am missing the following permission(s) to do that:\n**{', '.join(missing)}**",
            )
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception:
                pass
            return

        # Generic fallback
        logger.error(f"Ignoring exception in command '{interaction.command.name if interaction.command else 'Unknown'}': {error}", exc_info=error)

    async def _check_global_blacklist(self, interaction: discord.Interaction) -> bool:
        """Global check for application commands - blocks blacklisted users"""
        # Allow owners to bypass blacklist (just in case they tested it on themselves)
        if interaction.user.id in self.owner_ids:
            return True

        if interaction.user.id in self.blacklist_cache:
            try:
                await interaction.response.send_message(
                    f"{interaction.user.mention} ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â« **Blacklisted** - You are blacklisted from using this bot.",
                    ephemeral=True
                )
            except (discord.errors.InteractionResponded, discord.errors.NotFound):
                pass
            # Return False to halt command execution
            return False
        
        return True

    async def on_ready(self):
        """Called when bot is ready and connected"""
        if self._ready_once:
            logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚ÂÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¾ Reconnected to Discord")
            return
        
        self._ready_once = True
        
        # Banner
        logger.info("=" * 60)
        logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¤ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Bot Online: {self.user} (ID: {self.user.id})")
        logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â  Guilds: {len(self.guilds)}")
        logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¹Ã…â€œÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¥ Total Users: {sum((g.member_count or 0) for g in self.guilds):,}")
        logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ Version: {self.version}")
        logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â Discord.py: {discord.__version__}")
        logger.info("=" * 60)
        
        # Initialize database for all guilds
        logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¾ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â Initializing guild databases...")
        success = 0
        failed = 0
        
        for guild in self.guilds:
            try:
                await self.db.init_guild(guild.id)
                success += 1
            except Exception as e:
                logger.error(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Failed to init {guild.name}: {e}")
                failed += 1
        
        logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ Initialized {success}/{len(self.guilds)} guilds")
        if failed:
            logger.warning(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â {failed} guilds failed initialization")
        logger.info("=" * 60)
        
        # Set presence
        await self.update_presence()

        # Ensure status emojis are provisioned in Developer Portal > Application Emojis.
        try:
            synced_emojis = await sync_status_emojis_to_application(self)
            if synced_emojis:
                logger.info(f"Synced {len(synced_emojis)} status emoji assets to application emojis.")
            else:
                logger.warning("Application emoji sync skipped/unavailable; falling back to guild emoji provisioning.")
        except Exception as e:
            logger.warning(f"Failed to sync application emojis: {e}")
        
        # Load blacklist cache
        await self._load_blacklist_cache()
        
        logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ Bot is fully operational!")
    
    async def _load_blacklist_cache(self):
        """Load blacklist from database into cache"""
        try:
            blacklist = await self.db.get_blacklist()
            self.blacklist_cache = {entry["user_id"] for entry in blacklist}
            logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â« Loaded {len(self.blacklist_cache)} blacklisted users")
        except Exception as e:
            logger.error(f"Failed to load blacklist cache: {e}")
            self.blacklist_cache = set()
    
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
                f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ Joined guild: {guild.name} "
                f"(ID: {guild.id}, Members: {guild.member_count})"
            )
            await self.update_presence()
        except Exception as e:
            logger.error(f"Error handling guild join for {guild.name}: {e}")
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Handle leaving a guild"""
        logger.info(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¹Ã…â€œÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¹ Left guild: {guild.name} (ID: {guild.id})")
        # Clear cached prefix
        await self.prefix_cache.invalidate(guild.id)
        await self.update_presence()
    
    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        if message.author.bot:
            return

        # Check blacklist for prefix commands
        if message.author.id in self.blacklist_cache and message.author.id not in self.owner_ids:
            # Check if this looks like a command
            if message.guild:
                prefix = await self.prefix_cache.get(message.guild.id)
                if prefix is None:
                    prefix = ","
            else:
                prefix = "!"

            if message.content.startswith(prefix) or message.content.startswith(f"<@{self.user.id}>") or message.content.startswith(f"<@!{self.user.id}>"):
                await message.channel.send(
                    f"{message.author.mention} \u274c **Blacklisted** - You are blacklisted from using this bot."
                )
                return

        self.messages_seen += 1

        ctx = await self.get_context(message)
        if ctx.command is None:
            invoked = (ctx.invoked_with or "").strip()
            if invoked:
                loading_reaction = await self._try_add_loading_reaction(message)

                embed = ModEmbed.error(
                    "Command not found",
                    f"There's no command called `{invoked}`.",
                )
                try:
                    embed = await apply_status_emoji_overrides(embed, message.guild)
                except Exception:
                    pass
                try:
                    await message.reply(embed=embed, mention_author=False)
                except Exception:
                    await message.channel.send(embed=embed)
                finally:
                    if loading_reaction is not None:
                        await self._try_remove_loading_reaction(message, loading_reaction)
            return

        await self.invoke(ctx)

    async def on_interaction(self, interaction: discord.Interaction):
        """Handle interactions - check blacklist for slash commands"""
        # Only check application commands
        if interaction.type != discord.InteractionType.application_command:
            return

        pass

    async def on_command(self, ctx: commands.Context):
        """Track command usage"""
        self.commands_used += 1
        location = ctx.guild.name if ctx.guild else "DMs"
        logger.info(f"\U0001f4ac {ctx.author} used '{ctx.command.name}' in {location}")
        await self._send_prefix_loading(ctx)

    async def on_command_completion(self, ctx: commands.Context):
        """Clear loading marker once a command completes successfully."""
        await self._clear_prefix_loading_for_ctx(ctx)

    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Global command error handler"""
        await self._clear_prefix_loading_for_ctx(ctx)
        self.errors_caught += 1

        async def _send_error_response(
            embed: discord.Embed,
            *,
            view: Optional[discord.ui.View] = None,
            use_v2: bool = False,
        ):
            if ctx.guild is not None:
                try:
                    embed = await apply_status_emoji_overrides(embed, ctx.guild)
                except Exception:
                    pass
            if use_v2 and ctx.channel is not None:
                # Explicitly build a LayoutView via the shared v2 converter.
                send_kwargs: dict[str, Any] = {}
                msg = getattr(ctx, "message", None)
                if msg is not None:
                    try:
                        send_kwargs["reference"] = msg.to_reference(fail_if_not_exists=False)
                    except Exception:
                        send_kwargs["reference"] = msg
                    send_kwargs["mention_author"] = False
                try:
                    layout = await layout_view_from_embeds(
                        embed=embed,
                        existing_view=view,
                    )
                    send_kwargs["view"] = layout
                    return await ctx.channel.send(**send_kwargs)
                except Exception:
                    pass

            try:
                return await ctx.reply(embed=embed, view=view, mention_author=False)
            except Exception:
                return await ctx.send(embed=embed, view=view)

        if isinstance(error, commands.CommandNotFound):
            invoked = (ctx.invoked_with or "unknown").strip()
            embed = ModEmbed.error("Command not found", f"There's no command called `{invoked}`.")
            return await _send_error_response(embed)

        if isinstance(error, commands.MissingPermissions):
            embed = ModEmbed.error("Missing permissions", "You don't have permission to use this command.")
            return await _send_error_response(embed)

        if isinstance(error, commands.BotMissingPermissions):
            missing = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
            embed = ModEmbed.error("Bot missing permissions", f"I need these permissions: {missing}")
            return await _send_error_response(embed)

        if isinstance(error, commands.MissingRequiredArgument):
            embed = ModEmbed.error(
                "Missing argument",
                (
                    f"Missing required argument: `{error.param.name}`\n\n"
                    f"Use `{ctx.prefix}help {ctx.command}` for more info."
                ),
            )
            return await _send_error_response(embed)

        if isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
            if ctx.guild is not None and ctx.command is not None:
                params = list(ctx.command.clean_params.values())
                if params and self._is_member_like_annotation(params[0].annotation):
                    first_arg, tail = self._extract_first_argument_and_tail(ctx)
                    unresolved = str(getattr(error, "argument", "") or first_arg).strip()
                    candidate = self._find_best_member_match(ctx.guild, unresolved)
                    if candidate is not None:
                        confirm_icon = getattr(Config, "EMOJI_SUCCESS", "\u2705")
                        cancel_icon = getattr(Config, "EMOJI_ERROR", "\u274c")
                        try:
                            confirm_icon = await get_status_emoji_for_guild(
                                ctx.guild,
                                kind="success",
                                configured_emoji=str(confirm_icon),
                            )
                        except Exception:
                            pass
                        try:
                            cancel_icon = await get_status_emoji_for_guild(
                                ctx.guild,
                                kind="error",
                                configured_emoji=str(cancel_icon),
                            )
                        except Exception:
                            pass

                        warning_icon = getattr(Config, "EMOJI_WARNING", "\u26a0\ufe0f")
                        try:
                            warning_icon = await get_status_emoji_for_guild(
                                ctx.guild,
                                kind="warning",
                                configured_emoji=str(warning_icon),
                            )
                        except Exception:
                            pass
                        warning_icon_text = str(warning_icon or "").strip() or "\u26a0\ufe0f"
                        shortcode = re.fullmatch(r":([A-Za-z0-9_]{2,32}):", warning_icon_text)
                        if shortcode:
                            named = discord.utils.get(ctx.guild.emojis, name=shortcode.group(1))
                            if named is not None:
                                warning_icon_text = str(named)
                        if re.fullmatch(r":[A-Za-z0-9_]{2,32}:", warning_icon_text):
                            warning_icon_text = "\u26a0\ufe0f"

                        embed = ModEmbed.warning(
                            "No exact user could be found.",
                            f"Do you want to continue with {candidate.mention} (`@{candidate.display_name}`)?",
                        )
                        if embed.description:
                            embed.description = re.sub(
                                r"^:[A-Za-z0-9_]{2,32}:\s+",
                                f"{warning_icon_text} ",
                                str(embed.description),
                                count=1,
                            )
                        view = TargetResolvePromptView(
                            bot=self,
                            ctx=ctx,
                            candidate=candidate,
                            args_tail=tail,
                            confirm_emoji=confirm_icon,
                            cancel_emoji=cancel_icon,
                        )
                        await self._clear_prefix_loading_for_ctx(ctx)
                        return await _send_error_response(embed, view=view, use_v2=True)

        if isinstance(error, commands.BadArgument):
            embed = ModEmbed.error("Invalid argument", f"Invalid argument provided.\n\n{error}")
            return await _send_error_response(embed)

        if isinstance(error, commands.CommandOnCooldown):
            embed = ModEmbed.warning(
                "Cooldown",
                f"Please wait {error.retry_after:.1f}s before using this command again.",
            )
            return await _send_error_response(embed)

        if isinstance(error, commands.UserInputError):
            embed = ModEmbed.error(
                "Invalid input",
                f"{error}\n\nUse `{ctx.prefix}help {ctx.command}` for usage info.",
            )
            return await _send_error_response(embed)

        if isinstance(error, commands.CheckFailure):
            embed = ModEmbed.error("Check failed", "You cannot use this command here.")
            return await _send_error_response(embed)

        logger.error(
            f"Command error in '{ctx.command}': {type(error).__name__}: {error}",
            exc_info=error,
        )

        embed = ModEmbed.error(
            "Command error",
            "An unexpected error occurred while executing this command.\nThe error has been logged.",
        )
        embed.set_footer(text=f"Error: {type(error).__name__}")

        try:
            await _send_error_response(embed)
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
                logger.debug("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¹ Cache cleanup cycle completed")
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    async def close(self):
        # Shutdown dashboard
        if self._dashboard_runner:
            try:
                await self._dashboard_runner.cleanup()
                logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ Dashboard server stopped")
            except Exception:
                pass
        """Cleanup on shutdown"""
        logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¹Ã…â€œÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¹ Shutting down ModBot...")
        
        # Cancel cache cleanup task
        if self._cache_cleanup_task:
            self._cache_cleanup_task.cancel()
            try:
                await self._cache_cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Log session statistics
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â  Session Stats:")
        logger.info(f"  ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ Uptime: {uptime:.0f}s ({uptime/3600:.1f}h)")
        logger.info(f"  ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ Commands Used: {self.commands_used}")
        logger.info(f"  ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ Messages Seen: {self.messages_seen}")
        logger.info(f"  ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ Errors Caught: {self.errors_caught}")
        
        # Clear caches
        try:
            await self.snipe_cache.clear()
            await self.edit_snipe_cache.clear()
            await self.prefix_cache.clear()
            logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ Caches cleared")
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")
        
        # Close database connections
        try:
            if hasattr(self.db, "close"):
                await self.db.close()
            logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
        
        # Close bot
        await super().close()
        logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ Bot shutdown complete")


# ==================== MAIN ENTRY POINT ====================
async def main() -> int:
    """Main entry point with error handling"""
    # Validate environment
    validate_environment()

    # Prevent multiple running instances
    try:
        _acquire_single_instance_lock()
    except RuntimeError as e:
        logger.critical(str(e))
        return 1
    
    # Get token
    token = _get_modbot_token()
    if not token:
        logger.critical("=" * 60)
        logger.critical(
            "ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ ModBot token not found. Set MODBOT_DISCORD_TOKEN "
            "(or DISCORD_TOKEN fallback)."
        )
        logger.critical("=" * 60)
        logger.critical("Please create a .env file with:")
        logger.critical("MODBOT_DISCORD_TOKEN=your_modbot_token_here")
        logger.critical("LIFESIM_DISCORD_TOKEN=your_lifesimbot_token_here")
        logger.critical("=" * 60)
        return 1
    
    # Create bot instance
    bot = ModBot()
    lifesim_proc: Optional[subprocess.Popen] = _start_lifesim_process()

    try:
        async with bot:
            logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ Starting bot...")
            await bot.start(token)
    except KeyboardInterrupt:
        logger.info("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â°ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¹Ã…â€œÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¹ Received shutdown signal (Ctrl+C)")
    except discord.LoginFailure:
        logger.critical("=" * 60)
        logger.critical("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Invalid Discord token!")
        logger.critical("=" * 60)
        logger.critical(
            "Check your .env file and ensure MODBOT_DISCORD_TOKEN "
            "(or DISCORD_TOKEN fallback) is correct."
        )
        logger.critical(
            "Get your token from: https://discord.com/developers/applications"
        )
        logger.critical("=" * 60)
        return 1
    except discord.PrivilegedIntentsRequired:
        logger.critical("=" * 60)
        logger.critical("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Missing Privileged Intents!")
        logger.critical("=" * 60)
        logger.critical("Enable these in the Discord Developer Portal:")
        logger.critical("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ Server Members Intent")
        logger.critical("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ Message Content Intent")
        logger.critical("ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ Presence Intent")
        logger.critical("=" * 60)
        return 1
    except Exception as e:
        logger.critical(f"ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Fatal error during bot execution: {e}", exc_info=True)
        return 1
    finally:
        _stop_lifesim_process(lifesim_proc)
        if not bot.is_closed():
            await bot.close()
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Critical startup error: {e}", exc_info=True)
        sys.exit(1)

