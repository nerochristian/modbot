#!/usr/bin/env python3
"""Extract modular files from the aimoderation monolith."""
import re, os

MONOLITH = 'cogs/aimoderation/aimoderation.py'
OUT_DIR = 'cogs/aimoderation'

with open(MONOLITH, 'r', encoding='utf-8') as f:
    text = f.read()

# --- FIND BOUNDARIES ---
gc_start = text.index('class GeminiClient:')
gc_end = text.index('\n\n# =============================================================================\n# TOOL HANDLERS')
aimod_start = text.index('class AIModeration(commands.Cog):')
setup_pos = text.index('async def setup(bot: commands.Bot) -> None:')

# Find where AIModeration class body starts (after ClassVar block + __init__)
init_pos = text.index('    def __init__(self, bot: commands.Bot) -> None:', aimod_start)
# Find where text parsers end (before decision pipeline)
_quick_pos = text.index('    def _quick_route(self, message: discord.Message, content: str)', aimod_start)
# Find where decision pipeline ends and member resolution begins
_polish_end = text.index('    async def resolve_member(', aimod_start)

print(f"GeminiClient: {gc_start}-{gc_end}")
print(f"Text parsers: {init_pos}-{_quick_pos}")
print(f"Decision pipeline: {_quick_pos}-{_polish_end}")
print(f"AIModeration: {aimod_start}-{setup_pos}")
print(f"Setup: {setup_pos}")

# ==========================================================================
# 1. Write ai_client.py — GeminiClient class
# ==========================================================================
gc_code = text[gc_start:gc_end].lstrip()
ai_imports = '''"""
AI Client — provider-agnostic AI interface with rate limiting, web search, and memory.

Uses DeepSeek Web as the default provider (browser-based, no API key). 
Falls back to DigitalOcean inference API if configured.
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
from utils.messages import Messages

from .types import (
    ToolType, DecisionType, ConversationMode, AIConfig,
    TARGETED_TOOLS, REASONED_MODERATION_TOOLS, MAX_MODERATION_REASON_LENGTH,
    Decision, ConversationSignals, ConversationPlan,
    WebSearchResult, ImageContext, PermissionFlags, MentionInfo,
)
from .prompts import (
    ROUTING_SYSTEM_PROMPT, CONVERSATION_SYSTEM_PROMPT,
    DEEP_RESEARCH_SYSTEM_PROMPT, MOD_GUIDANCE_SYSTEM_PROMPT,
)

logger = logging.getLogger("ModBot.AIModeration.Client")

_DO_API_KEY: Final[str] = os.getenv("DO_API_KEY", "").strip()
_DO_BASE_URL: Final[str] = os.getenv("DO_INFERENCE_BASE_URL", "https://inference.do-ai.run/v1").strip().rstrip("/")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _looks_like_image_question_text(content: str) -> bool:
    low = re.sub(r"\\s+", " ", (content or "").strip().lower())
    return bool(
        re.search(r"\\b(?:who|what)\\s+(?:is|are)\\s+(?:this|that|it|these|those)\\b", low)
        or re.search(r"\\b(?:who|what)'s\\s+(?:this|that|it)\\b", low)
        or re.search(r"\\b(?:what|which)\\s+(?:game|pokemon|character|anime|show|movie|app|site|website)\\s+(?:is|are)\\s+(?:this|that|it|these|those)\\b", low)
        or re.search(r"\\b(?:who|what)\\s+(?:is|are)\\s+(?:this|that|it|these|those)\\s+(?:pokemon|character|person|game)\\b", low)
    )


'''

with open(f'{OUT_DIR}/ai_client.py', 'w', encoding='utf-8') as f:
    f.write(ai_imports)
    f.write(gc_code)
    f.write('\n')

print(f"  Wrote ai_client.py")

# ==========================================================================
# 2. Write text_parser.py — class-level regexes + text methods
# ==========================================================================
classvar_code = text[aimod_start:text.index('\n    def __init__(', aimod_start)]
text_methods = text[init_pos:_quick_pos]

tp_imports = '''"""
Text parsers and regex helpers for natural language moderation commands.

Pure functions extracted from the AIModeration cog.
"""
from __future__ import annotations

import re
from datetime import timedelta
from typing import Any, ClassVar, Dict, FrozenSet, List, Optional, Set, Union

import discord


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


class TextParsers:
    """Collection of regex constants and text-parsing methods.

    These were originally class attributes on the AIModeration cog.
    Extracted so the thin cog can inherit or compose them.
    """

'''

# Convert ClassVar assignments to plain class attrs
cvar = classvar_code.strip()
cvar = re.sub(r'    _MOD_REQUEST_RE: ClassVar\[re\.Pattern\] = ', '    _MOD_REQUEST_RE: ClassVar[re.Pattern] = ', cvar)
# Actually make them plain attrs by removing ClassVar annotation
cvar = re.sub(r': ClassVar\[\w+\[\w+(?:,\s*\w+)*\]\]\s*=', ' =', cvar)

with open(f'{OUT_DIR}/text_parser.py', 'w', encoding='utf-8') as f:
    f.write(tp_imports)
    f.write(cvar)
    f.write('\n\n')
    f.write(text_methods)
    f.write('\n')

print(f"  Wrote text_parser.py")

# ==========================================================================
# 3. Write decision_pipeline.py
# ==========================================================================
pipeline_code = text[_quick_pos:_polish_end]

dp_imports = '''"""
Decision routing pipeline — quick_route, recover, enrich, polish.

Handles deterministic rule-based routing and AI-assisted enrichment
before tool execution.
"""
from __future__ import annotations

import asyncio
import re
from typing import Any, ClassVar, Dict, FrozenSet, List, Optional, Set, Union, Tuple

import discord
from discord.ext import commands

from .types import (
    ToolType, DecisionType, Decision, AIConfig, GuildSettings,
    TARGETED_TOOLS, REASONED_MODERATION_TOOLS, MAX_MODERATION_REASON_LENGTH,
    PermissionFlags, MentionInfo,
)

from .text_parser import TextParsers

logger = logging.getLogger("ModBot.AIModeration.Pipeline")


def _now() -> datetime:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def _strip_code_fences(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\\n".join(lines)
    return cleaned.strip()


class DecisionPipeline(TextParsers):
    """Handles natural language → Decision routing and enrichment."""

    def __init__(self, bot: commands.Bot, config: AIConfig, ai_client):
        self.bot = bot
        self.config = config
        self.ai = ai_client
        self._target_cache: Dict[int, Tuple[int, object]] = {}
        self._active_chat_channels: Dict[int, object] = {}

    def clean_content(self, message: discord.Message) -> str:
        content = message.content or ""
        if self.bot.user:
            content = re.sub(
                rf"^\\s*<@!?{self.bot.user.id}>\\s*[:,]?\\s*",
                "",
                content,
                count=1,
            )
        return content.strip()

'''

with open(f'{OUT_DIR}/decision_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(dp_imports)
    # Replace `self.config` references in the pipeline code (they were cog attributes)
    # The pipeline code uses `self.config`, `self.bot.user`, `self.ai` — these will work 
    # since DecisionPipeline has those attributes
    f.write(pipeline_code)
    f.write('\n')

print(f"  Wrote decision_pipeline.py")

# ==========================================================================
# 4. Verify: can we import the new modules?
# ==========================================================================
print("\nVerifying imports...")
import subprocess, sys
for mod in ['ai_client', 'text_parser', 'decision_pipeline']:
    try:
        exec(f'from cogs.aimoderation.{mod} import *')
        print(f"  {mod}: OK")
    except Exception as e:
        print(f"  {mod}: FAILED - {e}")

print("\nDone! Next step: rewrite aimoderation.py as thin cog.")
