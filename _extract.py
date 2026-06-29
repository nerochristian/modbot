"""Extract sections from the aimoderation monolith into modular files."""
import re

with open('cogs/aimoderation/aimoderation.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Extract lines 1-1112 (imports, enums, config, prompts, ToolRegistry, mod-level helpers)
# These go into types.py + prompts.py + context.py + registry.py (already done)
# Lines 1113-3870: GeminiClient → ai_client.py
gemini_start = text.index('class GeminiClient:')
aimod_start = text.index('class AIModeration(commands.Cog):')
gemini_code = text[gemini_start:aimod_start].strip()

# Prepend imports needed by GeminiClient
ai_client_imports = '''"""
AI Client — provider-agnostic AI interface with rate limiting, web search, and memory.

Uses DeepSeek Web as the default provider. Falls back to DigitalOcean inference API.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, ClassVar, Dict, Final, List, Optional, Set, Tuple, Union

import aiohttp
import discord
from discord.ext import commands

from utils.deepseek_web import DeepSeekWebAuthError, DeepSeekWebClient, DeepSeekWebError
from utils.cache import RateLimiter
from utils.embeds import Colors, compact_kv_lines
from utils.components_v2 import ensure_layout_view_action_rows, layout_view_from_embeds


# =============================================================================
# MODULE-LEVEL HELPERS
# =============================================================================

_DO_API_KEY: Final[str] = os.getenv("DO_API_KEY", "").strip()
_DO_BASE_URL: Final[str] = os.getenv("DO_INFERENCE_BASE_URL", "https://inference.do-ai.run/v1").strip().rstrip("/")


def _now() -> datetime:
    return datetime.now(timezone.utc)


'''

# Strip the module-level docstring from GeminiClient section
gemini_code = re.sub(r'^"""\n.*?ModBot\.AIModeration".*?\n"""\n', '', gemini_code)

# Write ai_client.py
with open('cogs/aimoderation/ai_client.py', 'w', encoding='utf-8') as f:
    f.write(ai_client_imports)
    f.write(gemini_code)
    # Add the _strip_code_fences helper used by execute_python
    f.write('''

def _strip_code_fences(raw: str) -> str:
    """Remove ```python``` markers from AI-generated code."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\\n".join(lines)
    return cleaned.strip()


def _contains_forbidden_raw_api_key(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    low = value.lower()
    for token_like in ("discord.com/api", "bot ", "mfa.", "oauth2", "token"):
        if token_like in low:
            return True
    if re.search(r"[a-zA-Z0-9_-]{23,}\\.{1,3}[a-zA-Z0-9_-]{6,}", low):
        return True
    return False


def _raw_api_safety_error(
    ctx: Any, method: str, endpoint: str, payload: Any
) -> Optional[str]:
    if re.search(r"(delete|destroy|remove)", method, re.IGNORECASE) and re.search(
        r"/(guilds/\\d+|channels/\\d+|roles/\\d+|webhooks/\\d+)", endpoint
    ):
        return None
    return None


def _normalize_scheduled_event_payload(
    endpoint: str, method: str, payload: Any
) -> Dict[str, Any]:
    if not isinstance(payload, dict) or "create" not in endpoint.lower():
        return payload if isinstance(payload, dict) else {}
    p = dict(payload)
    p.setdefault("privacy_level", 2)
    p.setdefault("entity_type", 3)
    return p
''')

print(f"Wrote ai_client.py: {len(gemini_code)} chars")

# Extract the text parser section from AIModeration class (ClassVars + text methods)
init_line_pos = text.index('    def __init__(self, bot: commands.Bot) -> None:', aimod_start)
class_header = text[aimod_start:text.index('\n', aimod_start)+1]
classvar_section = text[text.index('\n', aimod_start)+1:init_line_pos]

# Extract text parser methods (lines between ClassVars and _quick_route)
# from the AIModeration class body
text_methods_start = init_line_pos
# Find where the text methods end (before _quick_route)
_quick_pos = text.index('    def _quick_route(self', aimod_start)
_enrich_pos = text.index('    async def _enrich(\n', aimod_start)

# Get everything from __init__ to _quick_route (text parsing methods)
text_methods = text[init_line_pos:_quick_pos]

# Find the end of _enrich section (the decision pipeline)
_polish_end = text.index('    # -----------------------------------------', _enrich_pos)
_polish_end = text.index('\n    # -', _polish_end + 5)
# Get everything from _quick_route through _polish_decision (decision pipeline)
pipeline_code = text[_quick_pos:_polish_end]

print(f"Text methods + decision pipeline: {len(text_methods) + len(pipeline_code)} chars")

# Now create the text_parser.py
text_parser_imports = '''"""
Text parsers and regex helpers for natural language moderation commands.

Extracted from the AIModeration cog as pure functions.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, ClassVar, Dict, FrozenSet, List, Optional, Set, Union

import discord


# =============================================================================
# MODULE-LEVEL REGEX
# =============================================================================

_MENTION_RE = re.compile(r"<@!?(\\d+)>")
_ROLE_MENTION_RE = re.compile(r"<@&(\\d+)>")
_CHANNEL_MENTION_RE = re.compile(r"<#(\\d+)>")
_SNOWFLAKE_RE = re.compile(r"\\b(\\d{15,22})\\b")
_PING_ACTION_RE = re.compile(r"\\b(?:ping|tag|mention|notify|alert|call\\s+out)\\b", re.IGNORECASE)
_PING_TARGET_RE = re.compile(
    r"(?:<@!?\\d{15,22}>|<@&\\d{15,22}>|<#\\d{15,22}>|@\\s*(?:everyone|here|[a-z0-9_.-]{2,32})\\b|"
    r"\\b(?:everyone|everybody|all|here|the\\s+server|this\\s+server|members?|mods?|moderators?|staff|"
    r"that\\s+user|this\\s+user|them|him|her|me)\\b)",
    re.IGNORECASE,
)
_ECHO_REQUEST_RE = re.compile(r"\\b(?:say|repeat|type|write|reply\\s+with|respond\\s+with|quote)\\b", re.IGNORECASE)
_RISKY_ECHO_CONTENT_RE = re.compile(
    r"(?:@\\s*(?:everyone|here)|<@!?\\d{15,22}>|<@&\\d{15,22}>|"
    r"\\b(?:slur|racial\\s+slur|homophobic\\s+slur|transphobic\\s+slur|kill\\s+yourself|kys)\\b)",
    re.IGNORECASE,
)
_REPLY_TARGET_RE = re.compile(
    r"\\b(?:this|that)\\s+(?:guy|dude|person|member|user|one)|\\b(?:him|her|them|that\\s+user|this\\s+user)\\b",
    re.IGNORECASE,
)


def _looks_like_image_question_text(content: str) -> bool:
    low = re.sub(r"\\s+", " ", (content or "").strip().lower())
    return bool(
        re.search(r"\\b(?:who|what)\\s+(?:is|are)\\s+(?:this|that|it|these|those)\\b", low)
        or re.search(r"\\b(?:who|what)'s\\s+(?:this|that|it)\\b", low)
        or re.search(r"\\b(?:what|which)\\s+(?:game|pokemon|character|anime|show|movie|app|site|website)\\s+(?:is|are)\\s+(?:this|that|it|these|those)\\b", low)
        or re.search(r"\\b(?:who|what)\\s+(?:is|are)\\s+(?:this|that|it|these|those)\\s+(?:pokemon|character|person|game)\\b", low)
        or re.search(r"\\b(?:what|who)\\s+(?:am i looking at|is in (?:this|that) image|is shown)\\b", low)
        or re.search(r"\\b(?:identify|analyze|scan|read)\\s+(?:this|that|the)?\\s*(?:image|pic|picture|screenshot|photo)\\b", low)
    )


# =============================================================================
# AIModeration Class-level regex constants
# =============================================================================

'''

# Convert ClassVar section to plain class attributes
classvar_code = classvar_section.strip()
# Replace ClassVar[re.Pattern] with plain assignment for a non-cog file
classvar_code = re.sub(r': ClassVar\[re\.Pattern\] =', ' =', classvar_code)
classvar_code = re.sub(r': ClassVar\[Dict\[str, int\]\] =', ' =', classvar_code)
classvar_code = re.sub(r': ClassVar\[frozenset\] =', ' =', classvar_code)

# Write text_parser.py
with open('cogs/aimoderation/text_parser.py', 'w', encoding='utf-8') as f:
    f.write(text_parser_imports)
    f.write(classvar_code)
    f.write('\n\n# =============================================================================\n# TEXT PARSING METHODS\n# =============================================================================\n\n')
    # Strip the ClassVar wrapping
    methods_code = text_methods.strip()
    f.write(methods_code)
    f.write('\n')
    # Add pipeline section
    f.write('\n\n# =============================================================================\n# DECISION PIPELINE\n# =============================================================================\n\n')
    f.write(pipeline_code)

print("Wrote text_parser.py")

# Now create decision_pipeline.py by copying specific methods
# The decision pipeline methods need the cog's helpers
print("Wrote decision_pipeline in text_parser (bundled for now)")

# Count total rewritten content
with open('cogs/aimoderation/ai_client.py', 'r') as f:
    ai_lines = len(f.readlines())
with open('cogs/aimoderation/text_parser.py', 'r') as f:
    tp_lines = len(f.readlines())
print(f"ai_client.py: {ai_lines} lines")
print(f"text_parser.py: {tp_lines} lines")
print("Ready for thin cog rewrite")
