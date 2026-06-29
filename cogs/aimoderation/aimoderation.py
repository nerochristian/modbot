"""
AI Moderation Cog — thin wrapper around modular components.

Imports from: types.py, prompts.py, context.py, registry.py, ai_client.py, handlers/
"""
from __future__ import annotations

import asyncio
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
)
from .prompts import (
    ROUTING_SYSTEM_PROMPT, CONVERSATION_SYSTEM_PROMPT,
    DEEP_RESEARCH_SYSTEM_PROMPT, MOD_GUIDANCE_SYSTEM_PROMPT,
)
from .context import ToolResult, ToolContext, action_embed, parse_hex_color
from .registry import ToolRegistry
from .ai_client import GeminiClient

logger = logging.getLogger("ModBot.AIModeration")

_MENTION_RE = re.compile(r"<@!?(\d+)>")
_ROLE_MENTION_RE = re.compile(r"<@&(\d+)>")
_CHANNEL_MENTION_RE = re.compile(r"<#(\d+)>")
_SNOWFLAKE_RE = re.compile(r"\b(\d{15,22})\b")

_EOL = None  # placeholder — the class body follows
