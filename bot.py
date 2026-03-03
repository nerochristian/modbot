"""
ModBot - Advanced Discord Moderation Bot
Production-ready for Render deployment.
Version 3.4.0
"""

import discord
from discord.ext import commands
from discord.ext.commands.converter import run_converters
import logging
import os
import re
import sys
import asyncio
import shlex
import signal
import inspect
from difflib import SequenceMatcher
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

# ==================== ENVIRONMENT HELPERS ====================
IS_RENDER = os.getenv("RENDER", "").lower() in ("true", "1", "yes")
IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") is not None


def _env_enabled(var_name: str, default: bool = False) -> bool:
    raw = os.getenv(var_name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_modbot_token() -> Optional[str]:
    """Resolve ModBot token with explicit override support."""
    return os.getenv("MODBOT_DISCORD_TOKEN") or os.getenv("DISCORD_TOKEN")


def validate_environment() -> None:
    """Validate required environment variables."""
    optional_warnings = ["GROQ_API_KEY", "OWNER_IDS"]
    log = logging.getLogger("ModBot")

    if not _get_modbot_token():
        log.critical("[FATAL] Missing required bot token: set MODBOT_DISCORD_TOKEN or DISCORD_TOKEN.")
        sys.exit(1)

    for var in optional_warnings:
        if not os.getenv(var):
            log.warning(f"[WARN] Optional environment variable not set: {var}")


# ==================== SINGLE-INSTANCE LOCK ====================
_LOCK_HANDLE = None


def _acquire_single_instance_lock() -> None:
    """Prevent multiple bot instances on the same machine.
    Skipped on Render and Railway (container isolation handles this).
    """
    if IS_RENDER or IS_RAILWAY:
        return

    global _LOCK_HANDLE
    import atexit

    lock_path = Path(".modbot.lock")

    if sys.platform == "win32":
        try:
            import msvcrt
        except ImportError:
            return
        _LOCK_HANDLE = lock_path.open("a+")
        try:
            msvcrt.locking(_LOCK_HANDLE.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError("Another ModBot instance is already running.")

        def _release():
            try:
                msvcrt.locking(_LOCK_HANDLE.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception:
                pass
            try:
                _LOCK_HANDLE.close()
            except Exception:
                pass

        atexit.register(_release)
    else:
        try:
            import fcntl
        except ImportError:
            return
        _LOCK_HANDLE = lock_path.open("a+")
        try:
            fcntl.flock(_LOCK_HANDLE.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError("Another ModBot instance is already running.")

        def _release():
            try:
                fcntl.flock(_LOCK_HANDLE.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                _LOCK_HANDLE.close()
            except Exception:
                pass

        atexit.register(_release)

    try:
        _LOCK_HANDLE.seek(0)
        _LOCK_HANDLE.truncate()
        _LOCK_HANDLE.write(str(os.getpid()))
        _LOCK_HANDLE.flush()
    except OSError:
        pass


# ==================== STATIC FFMPEG ====================
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except ImportError:
    pass

# ==================== GLOBAL EMBED DEFAULT COLOR ====================
_ORIGINAL_EMBED_INIT = discord.Embed.__init__


def _embed_init_force_accent(self, *args, **kwargs):
    explicit_colour = kwargs.pop("colour", None)
    if "color" not in kwargs and explicit_colour is not None:
        kwargs["color"] = explicit_colour
    if "color" not in kwargs or kwargs["color"] is None:
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
    """Clean formatter with optional ANSI colors for TTY output."""

    COLORS = {
        "DEBUG": "\x1b[36m",
        "INFO": "\x1b[32m",
        "WARNING": "\x1b[33m",
        "ERROR": "\x1b[31m",
        "CRITICAL": "\x1b[35m",
        "RESET": "\x1b[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
            msg = f"{color}{msg}{self.COLORS['RESET']}"
        return msg


def setup_logging() -> logging.Logger:
    """Configure logging with clean formatter."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    log = logging.getLogger("ModBot")
    log.setLevel(logging.INFO)

    # Reduce discord.py verbosity
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.INFO)
    logging.getLogger("discord.client").setLevel(logging.WARNING)

    return log


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
    logger.critical(f"[FATAL] Failed to import required modules: {e}")
    sys.exit(1)

# Web dashboard (optional)
try:
    from web.app import start_dashboard

    _DASHBOARD_AVAILABLE = True
except ImportError:
    _DASHBOARD_AVAILABLE = False

# Install Components v2 patching, keep classic v1 embeds as default.
patch_components_v2()
ComponentsV2Config.disable()


# ==================== TARGET RESOLVE PROMPT ====================
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
                return discord.PartialEmoji.from_str(text)
            except Exception:
                return fallback
        return text

    async def _verify_interaction(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self._ctx.author.id:
            try:
                await interaction.response.send_message(
                    "Only the command author can use these buttons.", ephemeral=True
                )
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
    - Web dashboard integration
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
        self.version: str = "3.4.0"

        # Caching with TTL
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
        """Load bot owner IDs from environment."""
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
            logger.warning("[WARN] Invalid OWNER_IDS in .env, using default")
            return {1269772767516033025}

    async def get_prefix(self, message: discord.Message):
        """Dynamic prefix handler with database-backed caching."""
        if not message.guild:
            return commands.when_mentioned_or("!")(self, message)

        # Check cache first
        prefix = await self.prefix_cache.get(message.guild.id)

        if prefix is None:
            # Load from database
            try:
                settings = await self.db.get_settings(message.guild.id)
                prefix = settings.get("prefix") if settings else None
                if not prefix:
                    prefix = getattr(Config, "PREFIX", ",")
                await self.prefix_cache.set(message.guild.id, prefix)
            except Exception as e:
                logger.error(f"Failed to get prefix for {message.guild.name}: {e}")
                prefix = getattr(Config, "PREFIX", ",")

        return commands.when_mentioned_or(prefix)(self, message)

    # ─── Loading Reaction Helpers ─────────────────────────────────────────

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
                if getattr(partial, "id", None) is None:
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
            eid = getattr(value, "id", None)
            if isinstance(eid, int):
                return eid
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

    # ─── Member Resolution Helpers ────────────────────────────────────────

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
            content = content[len(prefix) :].lstrip()

        if not content:
            return "", ""

        command_name, _, arg_text = content.partition(" ")
        if not command_name or not arg_text:
            return "", ""
        first_arg, _, tail = arg_text.strip().partition(" ")
        return first_arg.strip(), tail.strip()

    @staticmethod
    def _normalize_member_query(raw: str) -> str:
        value = (raw or "").strip()
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
            return await run_converters(ctx, param.annotation, raw_value, param)

        for name, param in params[1:]:
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

    # ─── Setup & Lifecycle ────────────────────────────────────────────────

    async def setup_hook(self):
        """Load cogs, sync slash commands, initialize systems."""
        logger.info("[>>] Initializing bot systems...")

        # Initialize database
        try:
            await self.db.init_pool()
        except Exception as e:
            logger.error(f"[ERR] Failed to initialize database pool: {e}")
            raise

        # Start cache cleanup task
        self._cache_cleanup_task = self.loop.create_task(self._cache_cleanup_loop())

        # Ensure cogs directory exists
        cogs_path = Path("./cogs")
        if not cogs_path.exists():
            logger.warning("[WARN] Cogs directory not found, creating...")
            cogs_path.mkdir(exist_ok=True)

        # Cog list
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
            "cogs.aimoderation",
            "cogs.automod",
            "cogs.antiraid",
            "cogs.voice",
            "cogs.settings",
            "cogs.polls",
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

        for cog in cogs:
            try:
                await self.load_extension(cog)
                loaded.append(cog)
                logger.info(f"  [OK] Loaded: {cog}")
            except commands.ExtensionNotFound:
                skipped.append(cog)
                logger.debug(f"  [--] Skipped: {cog} (not found)")
            except commands.ExtensionAlreadyLoaded:
                logger.debug(f"  [--] Skipped: {cog} (already loaded)")
            except Exception as e:
                failed.append((cog, str(e)))
                logger.error(f"  [ERR] Failed: {cog} - {e}")

        # Summary
        logger.info("=" * 60)
        logger.info("[COG] Cog Loading Summary:")
        logger.info(f"  Loaded:  {len(loaded)}")
        logger.info(f"  Skipped: {len(skipped)}")
        logger.info(f"  Failed:  {len(failed)}")
        if failed:
            for cog, error in failed:
                logger.warning(f"    > {cog}: {error}")
        total_prefix = len(list(self.walk_commands()))
        total_slash = len(self.tree.get_commands())
        logger.info(f"  Commands: {total_prefix} prefix, {total_slash} slash")
        logger.info("=" * 60)

        # Set global interaction check
        self.tree.interaction_check = self._check_global_blacklist

        # Sync slash commands
        sync_guild_id = os.getenv("SYNC_GUILD_ID")
        try:
            if sync_guild_id:
                guild_object = discord.Object(id=int(sync_guild_id))
                logger.info(f"[CMD] Syncing slash commands to guild {sync_guild_id}...")
                self.tree.copy_global_to(guild=guild_object)
                synced = await self.tree.sync(guild=guild_object)
                logger.info(f"[CMD] Synced {len(synced)} slash commands to guild")
            else:
                logger.info("[CMD] Syncing slash commands globally...")
                synced = await self.tree.sync()
                logger.info(f"[CMD] Synced {len(synced)} slash commands globally")
        except discord.HTTPException as e:
            logger.error(f"[ERR] Failed to sync commands: {e}")
            self.errors_caught += 1
        except Exception as e:
            logger.error(f"[ERR] Unexpected error syncing commands: {e}")
            self.errors_caught += 1

        # Bind global error handler
        self.tree.on_error = self.on_tree_error

    async def on_tree_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Global error handler for application commands."""
        self.errors_caught += 1

        if isinstance(error, discord.app_commands.MissingPermissions):
            missing = [p.replace("_", " ").replace("guild", "server").title() for p in error.missing_permissions]
            fmt = ", ".join(missing[:-1]) + f", and {missing[-1]}" if len(missing) > 2 else " and ".join(missing)
            embed = ModEmbed.error(
                "Permission Denied",
                f"You are missing the following permission(s):\n**{fmt}**",
            )
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception:
                pass
            return

        if isinstance(error, discord.app_commands.BotMissingPermissions):
            missing = [p.replace("_", " ").replace("guild", "server").title() for p in error.missing_permissions]
            embed = ModEmbed.error(
                "I Need Permissions",
                f"I am missing the following permission(s):\n**{', '.join(missing)}**",
            )
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception:
                pass
            return

        cmd_name = interaction.command.name if interaction.command else "Unknown"
        logger.error(f"Slash command error '{cmd_name}': {error}", exc_info=error)

    async def _check_global_blacklist(self, interaction: discord.Interaction) -> bool:
        """Block blacklisted users from application commands."""
        if interaction.user.id in self.owner_ids:
            return True

        if interaction.user.id in self.blacklist_cache:
            try:
                await interaction.response.send_message(
                    f"{interaction.user.mention} **Blacklisted** — You are blacklisted from using this bot.",
                    ephemeral=True,
                )
            except (discord.errors.InteractionResponded, discord.errors.NotFound):
                pass
            return False

        return True

    async def on_ready(self):
        """Called when bot is ready and connected."""
        if self._ready_once:
            logger.info("[NET] Reconnected to Discord")
            return

        self._ready_once = True

        logger.info("=" * 60)
        logger.info(f"[BOT] Online: {self.user} (ID: {self.user.id})")
        logger.info(f"[BOT] Guilds: {len(self.guilds)}")
        logger.info(f"[BOT] Users:  {sum((g.member_count or 0) for g in self.guilds):,}")
        logger.info(f"[BOT] Version: {self.version}")
        logger.info(f"[BOT] discord.py: {discord.__version__}")
        if IS_RENDER:
            logger.info(f"[BOT] Render URL: {os.getenv('RENDER_EXTERNAL_URL', 'not set')}")
        logger.info("=" * 60)

        # Initialize guilds in database
        logger.info("[DB] Initializing guild databases...")
        success = 0
        fail_count = 0

        for guild in self.guilds:
            try:
                await self.db.init_guild(guild.id)
                success += 1
            except Exception as e:
                logger.error(f"[ERR] Failed to init {guild.name}: {e}")
                fail_count += 1

        logger.info(f"[DB] Initialized {success}/{len(self.guilds)} guilds")
        if fail_count:
            logger.warning(f"[WARN] {fail_count} guilds failed initialization")

        # Set presence
        await self.update_presence()

        # Sync status emojis to application
        try:
            synced_emojis = await sync_status_emojis_to_application(self)
            if synced_emojis:
                logger.info(f"[OK] Synced {len(synced_emojis)} status emoji assets to application")
            else:
                logger.warning("[WARN] Application emoji sync skipped; falling back to guild emoji provisioning")
        except Exception as e:
            logger.warning(f"[WARN] Failed to sync application emojis: {e}")

        # Load blacklist cache
        await self._load_blacklist_cache()

        logger.info("[START] Bot is fully operational!")

    async def _load_blacklist_cache(self):
        """Load blacklist from database into cache."""
        try:
            blacklist = await self.db.get_blacklist()
            self.blacklist_cache = {entry["user_id"] for entry in blacklist}
            logger.info(f"[OK] Loaded {len(self.blacklist_cache)} blacklisted users")
        except Exception as e:
            logger.error(f"Failed to load blacklist cache: {e}")
            self.blacklist_cache = set()

    async def update_presence(self):
        """Update bot rich presence."""
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

    # ─── Guild Events ─────────────────────────────────────────────────────

    async def on_guild_join(self, guild: discord.Guild):
        """Handle joining a new guild."""
        try:
            await self.db.init_guild(guild.id)
            logger.info(f"[OK] Joined guild: {guild.name} (ID: {guild.id}, Members: {guild.member_count})")
            await self.update_presence()
        except Exception as e:
            logger.error(f"Error handling guild join for {guild.name}: {e}")

    async def on_guild_remove(self, guild: discord.Guild):
        """Handle leaving a guild."""
        logger.info(f"[BYE] Left guild: {guild.name} (ID: {guild.id})")
        await self.prefix_cache.invalidate(guild.id)
        await self.update_presence()

    # ─── Message Events ───────────────────────────────────────────────────

    async def on_message(self, message: discord.Message):
        """Handle incoming messages."""
        if message.author.bot:
            return

        # Check blacklist for prefix commands
        if message.author.id in self.blacklist_cache and message.author.id not in self.owner_ids:
            if message.guild:
                prefix = await self.prefix_cache.get(message.guild.id)
                if prefix is None:
                    prefix = getattr(Config, "PREFIX", ",")
            else:
                prefix = "!"

            if (
                message.content.startswith(prefix)
                or message.content.startswith(f"<@{self.user.id}>")
                or message.content.startswith(f"<@!{self.user.id}>")
            ):
                await message.channel.send(
                    f"{message.author.mention} \u274c **Blacklisted** — You are blacklisted from using this bot."
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

    async def on_command(self, ctx: commands.Context):
        """Track command usage."""
        self.commands_used += 1
        location = ctx.guild.name if ctx.guild else "DMs"
        logger.info(f"[CMD] {ctx.author} used '{ctx.command.name}' in {location}")
        await self._send_prefix_loading(ctx)

    async def on_command_completion(self, ctx: commands.Context):
        """Clear loading marker once a command completes."""
        await self._clear_prefix_loading_for_ctx(ctx)

    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Global command error handler."""
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
                f"Missing required argument: `{error.param.name}`\n\n"
                f"Use `{ctx.prefix}help {ctx.command}` for more info.",
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
                                ctx.guild, kind="success", configured_emoji=str(confirm_icon)
                            )
                        except Exception:
                            pass
                        try:
                            cancel_icon = await get_status_emoji_for_guild(
                                ctx.guild, kind="error", configured_emoji=str(cancel_icon)
                            )
                        except Exception:
                            pass

                        warning_icon = getattr(Config, "EMOJI_WARNING", "\u26a0\ufe0f")
                        try:
                            warning_icon = await get_status_emoji_for_guild(
                                ctx.guild, kind="warning", configured_emoji=str(warning_icon)
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

    # ─── Snipe Events ─────────────────────────────────────────────────────

    async def on_message_delete(self, message: discord.Message):
        """Cache deleted messages for snipe command."""
        if message.author.bot or not message.guild:
            return
        if not message.content and not message.attachments:
            return

        await self.snipe_cache.add(
            message.channel.id,
            {
                "content": message.content,
                "author": message.author,
                "created_at": message.created_at,
                "attachments": [a.url for a in message.attachments if not a.is_spoiler()],
            },
        )

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Cache edited messages for editsnipe command."""
        if before.author.bot or not before.guild or before.content == after.content:
            return
        if not before.content and not after.content:
            return

        await self.edit_snipe_cache.add(
            before.channel.id,
            {
                "before": before.content,
                "after": after.content,
                "author": before.author,
                "edited_at": after.edited_at or datetime.now(timezone.utc),
                "jump_url": after.jump_url,
            },
        )

    # ─── Global Error & Cleanup ───────────────────────────────────────────

    async def on_error(self, event: str, *args, **kwargs):
        """Global event error handler."""
        self.errors_caught += 1
        logger.error(f"Error in event '{event}'", exc_info=sys.exc_info())

    async def _cache_cleanup_loop(self):
        """Background task to periodically log cache stats."""
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                await asyncio.sleep(300)
                logger.debug("[CACHE] Cleanup cycle completed")
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")

    async def close(self):
        """Graceful shutdown."""
        # Shutdown dashboard
        if self._dashboard_runner:
            try:
                await self._dashboard_runner.cleanup()
                logger.info("[OK] Dashboard server stopped")
            except Exception:
                pass

        logger.info("[BYE] Shutting down ModBot...")

        # Cancel cache cleanup task
        if self._cache_cleanup_task:
            self._cache_cleanup_task.cancel()
            try:
                await self._cache_cleanup_task
            except asyncio.CancelledError:
                pass

        # Log session statistics
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        logger.info("Session Stats:")
        logger.info(f"  Uptime:        {uptime:.0f}s ({uptime / 3600:.1f}h)")
        logger.info(f"  Commands Used: {self.commands_used}")
        logger.info(f"  Messages Seen: {self.messages_seen}")
        logger.info(f"  Errors Caught: {self.errors_caught}")

        # Clear caches
        try:
            await self.snipe_cache.clear()
            await self.edit_snipe_cache.clear()
            await self.prefix_cache.clear()
            logger.info("[OK] Caches cleared")
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")

        # Close database
        try:
            if hasattr(self.db, "close"):
                await self.db.close()
            logger.info("[OK] Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")

        await super().close()
        logger.info("[OK] Bot shutdown complete")


# ==================== MAIN ENTRY POINT ====================
async def main() -> int:
    """Main entry point with Render-optimized startup."""
    validate_environment()

    # Single-instance lock (skipped on Render)
    try:
        _acquire_single_instance_lock()
    except RuntimeError as e:
        logger.critical(str(e))
        return 1

    token = _get_modbot_token()
    if not token:
        logger.critical("=" * 60)
        logger.critical("[FATAL] ModBot token not found.")
        logger.critical("  Set MODBOT_DISCORD_TOKEN (or DISCORD_TOKEN fallback).")
        logger.critical("=" * 60)
        return 1

    bot = ModBot()

    try:
        async with bot:
            # Start web dashboard FIRST so Render detects the open port
            # before the bot connects to Discord (which can take time).
            if _DASHBOARD_AVAILABLE:
                try:
                    bot._dashboard_runner = await start_dashboard(bot)
                    logger.info("[OK] Dashboard started (pre-connect)")
                except Exception as e:
                    logger.warning(f"[WARN] Dashboard failed to start: {e}")

            # On Render, wait a few seconds before connecting to Discord.
            # This gives the previous deployment's process time to fully
            # die, avoiding IDENTIFY rate limits from overlapping sessions.
            if IS_RENDER:
                logger.info("[NET] Waiting 5s for previous session to expire...")
                await asyncio.sleep(5)

            logger.info("[NET] Connecting to Discord...")
            await bot.start(token)
    except KeyboardInterrupt:
        logger.info("[BYE] Received shutdown signal (Ctrl+C)")
    except discord.LoginFailure:
        logger.critical("=" * 60)
        logger.critical("[FATAL] Invalid Discord token!")
        logger.critical("  Check your .env or Render env vars.")
        logger.critical("  Get your token: https://discord.com/developers/applications")
        logger.critical("=" * 60)
        return 1
    except discord.PrivilegedIntentsRequired:
        logger.critical("=" * 60)
        logger.critical("[FATAL] Missing Privileged Intents!")
        logger.critical("  Enable in the Discord Developer Portal:")
        logger.critical("    - Server Members Intent")
        logger.critical("    - Message Content Intent")
        logger.critical("    - Presence Intent")
        logger.critical("=" * 60)
        return 1
    except Exception as e:
        logger.critical(f"[FATAL] Fatal error during bot execution: {e}", exc_info=True)
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
        logger.info("Shutdown complete")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Critical startup error: {e}", exc_info=True)
        sys.exit(1)
