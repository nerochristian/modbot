"""
AI Moderation subpackage (clean architecture).

Import from the new modular structure:
- types.py       — Enums, dataclasses, constants
- prompts.py     — System prompts
- context.py     — ToolContext, ToolResult, embed helpers
- registry.py    — ToolRegistry with @register decorator
- handlers/      — Tool handler functions (members, roles, channels, messages, guild, admin)

Backward compat: the full monolith lives in aimoderation.py and is re-exported here.
New code should import from individual modules.
"""

# --- Clean modules ---
from .types import (
    ToolType, DecisionType, ConversationMode,
    TARGETED_TOOLS, REASONED_MODERATION_TOOLS, MAX_MODERATION_REASON_LENGTH,
    AIConfig, GuildSettings, Decision, ConversationSignals, ConversationPlan,
    WebSearchResult, ImageContext, PermissionFlags, MentionInfo,
    _default_ai_provider, _default_ai_model,
)
from .prompts import (
    ROUTING_SYSTEM_PROMPT, CONVERSATION_SYSTEM_PROMPT,
    DEEP_RESEARCH_SYSTEM_PROMPT, MOD_GUIDANCE_SYSTEM_PROMPT,
)
from .context import (
    ToolResult, ToolContext, action_embed as _action_embed, parse_hex_color as _parse_hex_color,
)
from .registry import ToolRegistry

# --- Handler registration (side-effect: populates ToolRegistry) ---
from . import handlers  # noqa: F401
from . import bridge  # noqa: F401

# --- Legacy aliases for backward compat ---
# Embed helpers with underscore prefix (used internally by the monolith code)
action_embed = _action_embed
_parse_hex_color = _parse_hex_color

# Re-export everything from the monolith as well (for things not yet extracted)
from .aimoderation import (  # noqa: E402, F401
    # Module-level constants
    DO_API_KEY,
    DO_BASE_URL,
    logger,
    # Regex helpers  
    _MENTION_RE,
    _ROLE_MENTION_RE,
    _CHANNEL_MENTION_RE,
    _SNOWFLAKE_RE,
    _PING_ACTION_RE,
    _PING_TARGET_RE,
    _ECHO_REQUEST_RE,
    _RISKY_ECHO_CONTENT_RE,
    _REPLY_TARGET_RE,
    _looks_like_image_question_text,
    # Additional helpers
    _now,
    _contains_forbidden_raw_api_key,
    _raw_api_safety_error,
    _normalize_scheduled_event_payload,
    # Gemini client
    GeminiClient,
    # Cog
    AIModeration,
    # Setup
    setup,
)
