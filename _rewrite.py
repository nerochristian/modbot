#!/usr/bin/env python3
"""Replace duplicate definitions in aimoderation.py with clean modular imports."""

MONOLITH = 'cogs/aimoderation/aimoderation.py'

with open(MONOLITH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find boundaries
aimod_start = None
setup_end = None
for i, line in enumerate(lines):
    if line.startswith('class AIModeration(commands.Cog):'):
        aimod_start = i
    if line.strip().startswith('async def setup(bot:') and 'await bot.add_cog' in line:
        setup_end = i + 1  # include the line

if aimod_start is None:
    raise SystemExit("Could not find AIModeration class")

print(f"AIModeration class at line {aimod_start+1}, setup at line {setup_end+1}")

# Build the new file
new_lines = []

# 1. Docstring
new_lines.append('"""\n')
new_lines.append('AI Moderation Cog — thin wrapper around modular components.\n')
new_lines.append('\n')
new_lines.append('Imports from: types, prompts, context, registry, ai_client, handlers\n')
new_lines.append('"""\n')
new_lines.append('from __future__ import annotations\n')
new_lines.append('\n')

# 2. Standard library imports (only what the class body needs)
new_lines.append('''import asyncio
import difflib
import json
import logging
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar, Dict, FrozenSet, List, Optional, Set, Tuple, Union

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.classic_send import send_classic_message
from utils.checks import is_bot_owner_id
from utils.embeds import Colors, compact_kv_lines
from utils.components_v2 import ensure_layout_view_action_rows, layout_view_from_embeds
from utils.messages import Messages
from utils.status_emojis import apply_status_emoji_overrides
from utils.transcript import EphemeralTranscriptView, generate_html_transcript

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
from .context import ToolResult, ToolContext, action_embed, parse_hex_color
from .registry import ToolRegistry
from .ai_client import GeminiClient

logger = logging.getLogger("ModBot.AIModeration")

''')

# 3. Module-level regex helpers (used by the class body)
new_lines.append('''_MENTION_RE = re.compile(r"<@!?(\d+)>")
_ROLE_MENTION_RE = re.compile(r"<@&(\d+)>")
_CHANNEL_MENTION_RE = re.compile(r"<#(\d+)>")
_SNOWFLAKE_RE = re.compile(r"\b(\d{15,22})\b")
_PING_ACTION_RE = re.compile(r"\b(?:ping|tag|mention|notify|alert|call\s+out)\b", re.IGNORECASE)
_PING_TARGET_RE = re.compile(
    r"(?:<@!?\d{15,22}>|<@&\d{15,22}>|<#\d{15,22}>|@\s*(?:everyone|here|[a-z0-9_.-]{2,32})\b|"
    r"\b(?:everyone|everybody|all|here|the\s+server|this\s+server|members?|mods?|moderators?|staff|"
    r"that\s+user|this\s+user|them|him|her|me)\b)",
    re.IGNORECASE,
)
_ECHO_REQUEST_RE = re.compile(r"\b(?:say|repeat|type|write|reply\s+with|respond\s+with|quote)\b", re.IGNORECASE)
_RISKY_ECHO_CONTENT_RE = re.compile(
    r"(?:@\s*(?:everyone|here)|<@!?\d{15,22}>|<@&\d{15,22}>|"
    r"\b(?:slur|racial\s+slur|homophobic\s+slur|transphobic\s+slur|kill\s+yourself|kys)\b)",
    re.IGNORECASE,
)
_REPLY_TARGET_RE = re.compile(
    r"\b(?:this|that)\s+(?:guy|dude|person|member|user|one)|\b(?:him|her|them|that\s+user|this\s+user)\b",
    re.IGNORECASE,
)


def _looks_like_image_question_text(content: str) -> bool:
    low = re.sub(r"\s+", " ", (content or "").strip().lower())
    return bool(
        re.search(r"\b(?:who|what)\s+(?:is|are)\s+(?:this|that|it|these|those)\b", low)
        or re.search(r"\b(?:who|what)'s\s+(?:this|that|it)\b", low)
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _strip_code_fences(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lns = cleaned.split("\n")
        lns = [l for l in lns if not l.strip().startswith("```")]
        cleaned = "\n".join(lns)
    return cleaned.strip()


def _contains_forbidden_raw_api_key(value: object) -> bool:
    if isinstance(value, dict):
        for key, inner in value.items():
            if str(key).lower() in {"token", "authorization", "client_secret", "bot_token"}:
                return True
            if _contains_forbidden_raw_api_key(inner):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_raw_api_key(inner) for inner in value)
    return False


def _raw_api_safety_error(ctx: ToolContext, method: str, endpoint: str, payload: object) -> Optional[str]:
    # Safety check for raw API calls - imported from context
    if not is_bot_owner_id(ctx.actor.id) and not ctx.actor.guild_permissions.administrator:
        return "Raw Discord API access requires the Administrator permission."
    if not endpoint.startswith("/"):
        return "Raw API endpoint must start with /."
    if "{" in endpoint or "}" in endpoint:
        return "Raw API endpoint contains unresolved placeholders."
    if method not in {"GET", "POST", "PATCH", "PUT", "DELETE"}:
        return "Unsupported HTTP method."
    if _contains_forbidden_raw_api_key(payload):
        return "Payload cannot contain token or authorization fields."
    return None


def _normalize_scheduled_event_payload(endpoint: str, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized_endpoint = endpoint.lower().split("?", 1)[0].rstrip("/")
    if method != "POST" or not re.fullmatch(r"/guilds/\d{15,22}/scheduled-events", normalized_endpoint):
        return payload
    fixed = dict(payload)
    fixed.setdefault("privacy_level", 2)
    fixed.setdefault("entity_type", 3)
    if "entity_metadata" not in fixed:
        fixed["entity_metadata"] = {"location": "Server"}
    return fixed


''')

# 4. The AIModeration class (everything from class AIModeration to end)
class_body = lines[aimod_start:]
new_lines.append('# =============================================================================\n')
new_lines.append('# AIMODERATION COG\n')
new_lines.append('# =============================================================================\n')
new_lines.append('\n')
new_lines.extend(class_body)

# Write the final file
with open(MONOLITH, 'w', encoding='utf-8') as f:
    f.write(''.join(new_lines))

# Quick syntax check
import ast
try:
    with open(MONOLITH, 'r', encoding='utf-8') as f:
        ast.parse(f.read())
    print(f"Syntax OK. Wrote {len(''.join(new_lines).splitlines())} lines.")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
