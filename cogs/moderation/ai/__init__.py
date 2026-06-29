"""
AI Moderation subpackage.

Re-exports all public symbols from the aimoderation module.
Import this module with `from cogs.moderation.ai import ...` to get all
the same names that were previously available from `cogs.aimoderation`.
"""

from .aimoderation import (
    # Enums
    ToolType,
    DecisionType,
    ConversationMode,
    # Constants
    TARGETED_TOOLS,
    REASONED_MODERATION_TOOLS,
    MAX_MODERATION_REASON_LENGTH,
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
    # Config
    AIConfig,
    GuildSettings,
    _default_ai_provider,
    _default_ai_model,
    # System prompts
    ROUTING_SYSTEM_PROMPT,
    CONVERSATION_SYSTEM_PROMPT,
    DEEP_RESEARCH_SYSTEM_PROMPT,
    MOD_GUIDANCE_SYSTEM_PROMPT,
    # Data classes
    Decision,
    ConversationSignals,
    ConversationPlan,
    WebSearchResult,
    ImageContext,
    PermissionFlags,
    MentionInfo,
    # Tool context
    ToolResult,
    ToolContext,
    # Tool registry
    ToolRegistry,
    ToolHandler,
    # Embed helpers
    _now,
    action_embed,
    _parse_hex_color,
    _contains_forbidden_raw_api_key,
    _raw_api_safety_error,
    _normalize_scheduled_event_payload,
    # Gemini client
    GeminiClient,
    # Cog
    AIModeration,
    # Module-level constants
    DO_API_KEY,
    DO_BASE_URL,
    logger,
)
