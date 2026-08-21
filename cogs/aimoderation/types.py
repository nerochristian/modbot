"""
AI Moderation types — enums, dataclasses, and constants.

Extracted from cogs/aimoderation.py into cogs/moderation/ai/types.py
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Final, Optional, Set, Tuple

from utils.moderation_settings import moderation_id_set

if TYPE_CHECKING:
    import discord

logger = logging.getLogger("ModBot.AIModeration.Types")


# =============================================================================
# ENUMS
# =============================================================================


class ToolType(str, Enum):
    GET_WARNINGS = "get_warnings"
    GET_HISTORY = "get_history"
    WARN = "warn_member"
    TIMEOUT = "timeout_member"
    UNTIMEOUT = "untimeout_member"
    KICK = "kick_member"
    BAN = "ban_member"
    UNBAN = "unban_member"
    PURGE = "purge_messages"
    ADD_ROLE = "add_role"
    REMOVE_ROLE = "remove_role"
    CREATE_ROLE = "create_role"
    DELETE_ROLE = "delete_role"
    EDIT_ROLE = "edit_role"
    CREATE_CHANNEL = "create_channel"
    DELETE_CHANNEL = "delete_channel"
    EDIT_CHANNEL = "edit_channel"
    LOCK_CHANNEL = "lock_channel"
    UNLOCK_CHANNEL = "unlock_channel"
    SET_NICKNAME = "set_nickname"
    LOCK_THREAD = "lock_thread"
    MOVE_MEMBER = "move_member"
    DISCONNECT_MEMBER = "disconnect_member"
    DM_USER = "dm_user"
    EDIT_GUILD = "edit_guild"
    CREATE_EMOJI = "create_emoji"
    DELETE_EMOJI = "delete_emoji"
    CREATE_INVITE = "create_invite"
    PIN_MESSAGE = "pin_message"
    UNPIN_MESSAGE = "unpin_message"
    EXECUTE_RAW_API = "execute_raw_api"
    EXECUTE_PYTHON = "execute_python"
    HELP = "show_help"
    FIND_INACTIVE_MEMBERS = "find_inactive_members"
    SCAN_CHANNEL = "scan_channel"
    SUMMARIZE_ACTIONS = "summarize_actions"
    SAFETY_CHECK = "server_safety_check"


class DecisionType(str, Enum):
    TOOL_CALL = "tool_call"
    CHAT = "chat"
    ERROR = "error"


class ConversationMode(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    RESEARCH = "research"
    MOD_GUIDANCE = "mod_guidance"


# =============================================================================
# TOOL SETS
# =============================================================================


TARGETED_TOOLS: Final[Set[ToolType]] = {
    ToolType.WARN, ToolType.TIMEOUT, ToolType.UNTIMEOUT,
    ToolType.KICK, ToolType.BAN, ToolType.UNBAN,
    ToolType.ADD_ROLE, ToolType.REMOVE_ROLE,
    ToolType.SET_NICKNAME, ToolType.MOVE_MEMBER, ToolType.DISCONNECT_MEMBER,
    ToolType.DM_USER, ToolType.GET_WARNINGS, ToolType.GET_HISTORY, ToolType.PURGE,
}

REASONED_MODERATION_TOOLS: Final[Set[ToolType]] = {
    ToolType.WARN,
    ToolType.TIMEOUT,
    ToolType.UNTIMEOUT,
    ToolType.KICK,
    ToolType.BAN,
    ToolType.UNBAN,
    ToolType.PURGE,
}

MAX_MODERATION_REASON_LENGTH: Final[int] = 140


# =============================================================================
# CONFIGURATION DATACLASSES
# =============================================================================


def _default_max_tokens_chat() -> int:
    """Output-token ceiling for conversation replies.

    This is a headroom limit, not a target: the bot splits long replies into
    Discord-sized chunks, so a high ceiling costs nothing on normal short
    answers (billing is per token actually generated).

    It must stay well above the longest expected answer because reasoning
    models count their hidden reasoning tokens against ``max_tokens``. The old
    3,000 cap was low enough that a reasoning model could spend the entire
    budget thinking and return an EMPTY reply with finish_reason="length".
    Upstream providers here allow ~128k completion tokens.
    """
    raw = (os.getenv("AI_MAX_TOKENS_CHAT") or "").strip()
    if raw:
        try:
            parsed = int(raw)
        except ValueError:
            parsed = 0
        if parsed > 0:
            return max(1_000, min(64_000, parsed))
    return 16_000


def _default_ai_provider() -> str:
    """The provider name. OpenRouter is the only one, so this is a constant.

    Kept as a function (and as an ``AIConfig`` field) because ``/aimod status``
    and the dashboard both display it, and because ``AI_PROVIDER`` is still set
    in deployed .env files -- honouring a stale value there would point the bot
    at a vendor that no longer has any code behind it.
    """
    return "openrouter"


def _default_ai_model() -> str:
    """The model shown as this guild's default before any per-guild override.

    This is the moderation-lane model, because the routing/action decisions are
    what a guild-level model setting is actually able to influence. The
    conversation lanes name their own models in ``ai_client``.
    """
    return (
        os.getenv("AI_MODEL")
        or os.getenv("OPENROUTER_MODERATION_MODEL")
        or os.getenv("RELAYROUTER_MODERATION_MODEL")
        or "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    ).strip()


@dataclass(frozen=True)
class AIConfig:
    """Immutable configuration for AI moderation system."""
    provider: str = field(default_factory=_default_ai_provider)
    model: str = field(default_factory=_default_ai_model)
    temperature_routing: float = 0.2
    temperature_chat: float = 0.85
    max_tokens_routing: int = 1500
    max_tokens_chat: int = field(default_factory=_default_max_tokens_chat)
    memory_window: int = 200
    memory_max_chars: int = 96_000
    context_messages: int = 100
    context_char_budget: int = 96_000
    routing_context_messages: int = 80
    user_memory_context_chars: int = 16_000
    guild_memory_context_chars: int = 20_000
    rate_limit_calls: int = 30
    rate_limit_window: int = 60
    timeout_max_seconds: int = 259_200    # 3 days
    timeout_default_seconds: int = 3_600  # 1 hour
    confirm_timeout_seconds: int = 25
    proactive_chance: float = 0.02
    target_cache_ttl_minutes: int = 15


@dataclass
class GuildSettings:
    """Per-guild AI moderation settings."""
    enabled: bool = False
    chat_enabled: bool = False
    model: Optional[str] = None
    context_messages: int = 100
    # Every mutating tool requires an explicit button confirmation. That is not
    # configurable by design -- see AIModeration._requires_confirmation -- so
    # there is deliberately no confirm_enabled / confirm_actions setting here.
    # Only the approval window is tunable.
    confirm_timeout_seconds: int = 25
    proactive_chance: float = 0.02
    location_context: str = ""
    # Screen uploaded images for age-inappropriate content (NSFW / gore).
    # Off by default: it costs one model call per image posted.
    image_scan_enabled: bool = False
    # What to do when an image is flagged: "log" (report only), "delete"
    # (remove the message and log), or "punish" (delete and run the configured
    # automod escalation). Defaults to the least destructive option.
    image_scan_action: str = "log"
    mod_roles: Set[int] = field(default_factory=set)

    IMAGE_SCAN_ACTIONS: ClassVar[Tuple[str, ...]] = ("log", "delete", "punish")

    @staticmethod
    def _coerce_bool(raw: Any, default: bool) -> bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return bool(raw)
        if isinstance(raw, str):
            normalized = raw.strip().lower()
            if normalized in {"1", "true", "yes", "on", "enable", "enabled"}:
                return True
            if normalized in {"0", "false", "no", "off", "disable", "disabled"}:
                return False
            return default
        return default

    @staticmethod
    def _coerce_int(raw: Any, default: int, *, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = default
        if minimum is not None:
            value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return value

    @staticmethod
    def _coerce_float(raw: Any, default: float, *, minimum: Optional[float] = None, maximum: Optional[float] = None) -> float:
        try:
            value = float(raw)
        except (TypeError, ValueError):
            value = default
        if minimum is not None:
            value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return value

    @classmethod
    def _coerce_image_scan_action(cls, raw: Any) -> str:
        """Normalize the flagged-image action, rejecting unknown values.

        An unrecognized action must never escalate: fall back to "log" so a bad
        or stale setting cannot start deleting messages or punishing members.
        """
        value = str(raw or "").strip().lower()
        if value in cls.IMAGE_SCAN_ACTIONS:
            return value
        return "log"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GuildSettings":
        return cls(
            enabled=cls._coerce_bool(data.get("aimod_enabled", False), False),
            chat_enabled=cls._coerce_bool(data.get("aimod_chat_enabled", False), False),
            model=data.get("aimod_model"),
            context_messages=cls._coerce_int(
                data.get("aimod_context_messages", 100),
                100,
                minimum=1,
                maximum=200,
            ),
            confirm_timeout_seconds=cls._coerce_int(data.get("aimod_confirm_timeout_seconds", 25), 25, minimum=1, maximum=300),
            proactive_chance=cls._coerce_float(data.get("aimod_proactive_chance", 0.02), 0.02, minimum=0.0, maximum=1.0),
            location_context=str(data.get("aimod_location_context") or data.get("server_location") or "").strip(),
            image_scan_enabled=cls._coerce_bool(
                data.get("aimod_image_scan_enabled", False),
                False,
            ),
            image_scan_action=cls._coerce_image_scan_action(
                data.get("aimod_image_scan_action", "log"),
            ),
            mod_roles=moderation_id_set(data, "mod_roles"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aimod_enabled": self.enabled,
            "aimod_chat_enabled": self.chat_enabled,
            "aimod_model": self.model,
            "aimod_context_messages": self.context_messages,
            "aimod_confirm_timeout_seconds": self.confirm_timeout_seconds,
            "aimod_proactive_chance": self.proactive_chance,
            "aimod_location_context": self.location_context,
            "aimod_image_scan_enabled": self.image_scan_enabled,
            "aimod_image_scan_action": self.image_scan_action,
            "mod_roles": sorted(self.mod_roles),
        }


# =============================================================================
# DECISION DATACLASS
# =============================================================================


# Bare-verb synonyms for the schema tool names. Models emit "ban" instead of
# "ban_member" often enough that discarding the decision is the wrong default:
# the resolved tool still has to clear validate_tool_access before it runs, so
# accepting an unambiguous synonym costs nothing and recovers a dead command.
_TOOL_ALIASES: Dict[str, "ToolType"] = {
    "ban": ToolType.BAN,
    "unban": ToolType.UNBAN,
    "kick": ToolType.KICK,
    "warn": ToolType.WARN,
    "timeout": ToolType.TIMEOUT,
    "mute": ToolType.TIMEOUT,
    "untimeout": ToolType.UNTIMEOUT,
    "unmute": ToolType.UNTIMEOUT,
    "purge": ToolType.PURGE,
    "clear": ToolType.PURGE,
    "delete_messages": ToolType.PURGE,
    "warnings": ToolType.GET_WARNINGS,
    "history": ToolType.GET_HISTORY,
    "help": ToolType.HELP,
    "nickname": ToolType.SET_NICKNAME,
    "dm": ToolType.DM_USER,
}


@dataclass
class Decision:
    """AI router output."""
    type: DecisionType
    reason: str
    tool: Optional[ToolType] = None
    arguments: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Decision":
        raw_type = str(data.get("type") or "").strip().lower()
        dec_type = DecisionType.ERROR
        if raw_type == "tool_call":
            dec_type = DecisionType.TOOL_CALL
        elif raw_type == "chat":
            dec_type = DecisionType.CHAT

        raw_tool = str(data.get("tool") or "").strip().lower()
        tool = None
        if raw_tool:
            try:
                tool = ToolType(raw_tool)
            except ValueError:
                tool = _TOOL_ALIASES.get(raw_tool)
            if tool is None:
                # A TOOL_CALL carrying an unresolvable tool used to be returned
                # as-is with tool=None. The dispatcher gates on
                # `decision.type == TOOL_CALL and decision.tool`, so that object
                # fell through to the error branch reporting nothing useful --
                # the command just died silently. Degrade explicitly instead,
                # naming the value the model actually sent.
                logger.warning("Model returned unknown tool name: %r", raw_tool)
                return cls(
                    type=DecisionType.ERROR,
                    reason=f"Unknown tool requested by the model: {raw_tool!r}",
                )
        elif dec_type is DecisionType.TOOL_CALL:
            # tool_call with the field absent, empty, or null. Same silent
            # no-op as an unresolvable name: the dispatcher requires a truthy
            # tool, so this would reach the error branch with nothing to say.
            logger.warning("Model returned tool_call with no tool name")
            return cls(
                type=DecisionType.ERROR,
                reason="Model requested a tool call without naming a tool.",
            )

        raw_arguments = data.get("arguments")
        arguments = dict(raw_arguments) if isinstance(raw_arguments, dict) else {}

        return cls(
            type=dec_type,
            reason=str(data.get("reason") or ""),
            tool=tool,
            arguments=arguments,
        )

    @classmethod
    def error(cls, reason: str) -> "Decision":
        return cls(type=DecisionType.ERROR, reason=reason)

    @classmethod
    def chat(cls, reason: str = "") -> "Decision":
        return cls(type=DecisionType.CHAT, reason=reason)


# =============================================================================
# CONVERSATION DATACLASSES
# =============================================================================


@dataclass(frozen=True)
class ConversationSignals:
    """Conversation classifier output."""
    mode: ConversationMode
    confidence: float
    show_research_indicator: bool = False
    asks_for_current_info: bool = False
    asks_for_sources: bool = False
    asks_for_long_answer: bool = False
    mentions_moderation: bool = False
    focus_entities: Tuple[str, ...] = ()
    requires_web_search: bool = False

    @property
    def research(self) -> bool:
        """Backward-compatible research-mode flag."""
        return self.mode == ConversationMode.RESEARCH

    @property
    def sources(self) -> bool:
        """Backward-compatible source-request flag."""
        return self.asks_for_sources

    @property
    def long_answer(self) -> bool:
        """Backward-compatible long-answer flag."""
        return self.asks_for_long_answer


@dataclass(frozen=True)
class ConversationPlan:
    """Assembled prompt plan for a conversation turn."""
    system_prompt: str
    user_prompt: str
    temperature: float
    max_tokens: int
    show_research_indicator: bool
    context_prompt: str = ""

    @property
    def show_indicator(self) -> bool:
        """Backward-compatible research-indicator flag."""
        return self.show_research_indicator


@dataclass(frozen=True)
class WebSearchResult:
    """Search hit from a web search provider."""
    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class ImageContext:
    """Image data for multimodal model requests."""
    label: str
    filename: str
    mime_type: str
    data: bytes

    @property
    def data_url(self) -> str:
        return f"data:{self.mime_type};base64,{__import__('base64').b64encode(self.data).decode()}"


# =============================================================================
# PERMISSION & MENTION DATACLASSES
# =============================================================================


@dataclass
class PermissionFlags:
    """Guild permission flags derived from a member."""
    bot_owner: bool = False
    administrator: bool = False
    ban_members: bool = False
    kick_members: bool = False
    manage_guild: bool = False
    manage_channels: bool = False
    manage_roles: bool = False
    manage_messages: bool = False
    manage_threads: bool = False
    manage_nicknames: bool = False
    manage_emojis: bool = False
    create_instant_invite: bool = False
    move_members: bool = False
    moderate_members: bool = False
    mute_members: bool = False

    @classmethod
    def from_member(
        cls,
        member: "discord.Member",
        channel: Optional["discord.abc.GuildChannel"] = None,
        *,
        bot_owner: bool = False,
    ) -> "PermissionFlags":
        perms = member.guild_permissions
        channel_perms = None
        permissions_for = getattr(channel, "permissions_for", None)
        if callable(permissions_for):
            channel_perms = permissions_for(member)

        def effective(name: str) -> bool:
            if channel_perms is not None and name in {
                "manage_messages",
                "manage_threads",
                "create_instant_invite",
            }:
                return bool(getattr(channel_perms, name, False))
            return bool(getattr(perms, name, False))

        return cls(
            bot_owner=bot_owner,
            administrator=perms.administrator,
            ban_members=perms.ban_members,
            kick_members=perms.kick_members,
            manage_guild=perms.manage_guild,
            manage_channels=perms.manage_channels,
            manage_roles=perms.manage_roles,
            manage_messages=effective("manage_messages"),
            manage_threads=effective("manage_threads"),
            manage_nicknames=perms.manage_nicknames,
            manage_emojis=perms.manage_emojis_and_stickers,
            create_instant_invite=effective("create_instant_invite"),
            move_members=perms.move_members,
            moderate_members=perms.moderate_members,
            mute_members=perms.mute_members,
        )

    @classmethod
    def superuser(cls, *, bot_owner: bool = False) -> "PermissionFlags":
        return cls(
            bot_owner=bot_owner,
            administrator=True, ban_members=True, kick_members=True,
            manage_guild=True, manage_channels=True, manage_roles=True,
            manage_messages=True, manage_threads=True, manage_nicknames=True,
            manage_emojis=True, create_instant_invite=True, move_members=True,
            moderate_members=True, mute_members=True,
        )

    def to_dict(self) -> Dict[str, bool]:
        return {
            "bot_owner": self.bot_owner,
            "administrator": self.administrator,
            "ban_members": self.ban_members,
            "kick_members": self.kick_members,
            "manage_guild": self.manage_guild,
            "manage_channels": self.manage_channels,
            "manage_roles": self.manage_roles,
            "manage_messages": self.manage_messages,
            "manage_threads": self.manage_threads,
            "manage_nicknames": self.manage_nicknames,
            "manage_emojis": self.manage_emojis,
            "create_instant_invite": self.create_instant_invite,
            "move_members": self.move_members,
            "moderate_members": self.moderate_members,
            "mute_members": self.mute_members,
        }

    def allows(self, permission: str) -> bool:
        """Return whether this member may use a standard Discord permission gate."""
        if permission == "bot_owner":
            return self.bot_owner
        if self.administrator:
            return True
        return bool(getattr(self, str(permission or "").strip(), False))


@dataclass
class MentionInfo:
    """Metadata about a mention found in a message."""
    index: int
    user_id: int
    is_bot: bool = False
    display_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"index": self.index, "id": self.user_id, "is_bot": self.is_bot, "display": self.display_name}
