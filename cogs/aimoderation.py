import os
import re
import json
import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Literal

import discord
from discord import app_commands
from discord.ext import commands
from groq import Groq

from utils.checks import is_admin, is_bot_owner_id, is_mod
from utils.cache import RateLimiter
from utils.messages import Messages
import logging

logger = logging.getLogger("ModBot")

# ========= CONFIG =========

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

USER_MEMORY_WINDOW = 50  # Increased from 20 for "ultra memory"
USER_MEMORY_MAX_CHARS = 32000  # Increased from 8000

DEFAULT_AIMOD_SETTINGS: Dict[str, Any] = {
    "aimod_enabled": True,
    "aimod_model": GROQ_MODEL,
    "aimod_context_messages": 15,
    "aimod_confirm_enabled": False,
    "aimod_confirm_timeout_seconds": 25,
    "aimod_confirm_actions": ["ban_member", "kick_member", "purge_messages"],
    "aimod_proactive_chance": 0.02,  # 2% chance to reply proactively
    "aimod_proactive_cooldown": 30,  # Seconds between proactive responses per channel
    "aimod_ignore_spam": True,  # Ignore obvious spam messages
}

# ========= SYSTEM PROMPT FOR ROUTING =========

SYSTEM_PROMPT = """
You are an AI moderation router for a Discord bot.

Goal:
- When the bot is mentioned, you receive the cleaned message content plus metadata.
- Decide ONE best moderation action (tool) to perform OR decide to chat conversationally.
- Understand creative verbs like "terminate", "execute", "banish", "mute", "gag", etc.,
  and map them to normal moderation actions (warn, timeout, kick, ban, purge).
- If the user instead wants to have a conversation or ask for advice (non-moderation),
  respond with type="chat" so the bot replies conversationally instead of doing a mod action.

JSON response format (NO markdown, NO code fences, NO extra text):

{
  "type": "tool_call" | "chat" | "error",
  "reason": "short explanation",
    "tool": "warn_member" | "timeout_member" | "untimeout_member" | "kick_member" | "ban_member" |
                     "unban_member" | "purge_messages" | "show_help" | null,
  "arguments": { ...tool specific arguments... }
}

Available tools:

1) warn_member
   - target_user_id: int
   - reason: str

2) timeout_member
   - target_user_id: int
   - seconds: int (timeout duration in seconds, max 259200 = 3 days)
   - reason: str

3) kick_member
   - target_user_id: int
   - reason: str

4) ban_member
   - target_user_id: int
   - delete_message_days: int (0-7)
   - reason: str

5) unban_member
   - target_user_id: int
   - reason: str

6) purge_messages
   - amount: int (1-500)
   - reason: str or null

7) untimeout_member
    - target_user_id: int
    - reason: str or null

8) show_help
    - no arguments

Mapping language:
- "mute", "timeout", "silence", "gag"         => timeout_member
- "unmute", "untimeout", "unsilence", "ungag" => untimeout_member
- "kick", "boot", "yeet out"                  => kick_member
- "ban", "permaban", "banish", "exile"        => ban_member
- "warn", "note", "slap on the wrist"         => warn_member
- "purge", "clear", "wipe", "nuke" + count    => purge_messages
- "help", "what can you do"                   => show_help

User / role permissions:
- You are given booleans like "can_timeout_members", "can_kick_members" etc.
- NEVER choose a tool that the user is not allowed to perform (if flag is false,
  treat it as forbidden and either select a weaker tool or return type="error").
- Example: "banish" but can_ban_members = false:
  - downgrade to timeout if allowed OR
  - return type="error" explaining lack of permissions.

Duration parsing:
- Understand "for an hr", "for 1h", "for 30 minutes", "for 2 days", etc.
- Convert duration to seconds; cap at 259200 seconds (3 days).
- If no duration is clearly given for timeout, default to 3600 seconds (1 hour).

Target resolution:
- You are given a list of mentions metadata.
- The FIRST mention is always the bot itself.
- Any later mentions are possible targets.
- Prefer a single clear target; if multiple, pick the one that best fits the request
  (usually the first non-bot mentioned after the bot).
- Set "target_user_id" to the chosen user's ID.

If the request is not about moderation, or too ambiguous, or user just wants to talk:
- Return type="chat" so the bot replies conversationally.

If impossible to fulfill due to missing info or permissions:
- Return type="error" with a helpful reason and tool=null, arguments={}.

CRITICAL:
- Respond with exactly one JSON object, no surrounding quotes, no markdown, no backticks.
""".strip()


# ========= GROQ CLIENT WRAPPER =========


class GroqClientWrapper:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        api_key = os.getenv("GROQ_API_KEY")
        self.client: Optional[Groq] = Groq(api_key=api_key) if api_key else None

        # Memory is now persistent via DB, but we keep a small in-memory LRU cache if needed
        # For now, we'll just fetch from DB to ensure persistence.
        
        # Rate limiting: 30 calls per minute per user
        self._rate_limiter = RateLimiter(max_calls=30, window_seconds=60)

    @staticmethod
    def _strip_code_fences(raw: str) -> str:
        """Remove markdown code fences if present."""
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    # ========= ROUTER: decides tool_call / chat / error =========

    async def choose_tool(
        self,
        *,
        user_content: str,
        guild: discord.Guild,
        author: Union[discord.Member, discord.User],
        mentions_meta: List[Dict[str, Any]],
        recent_messages: List[discord.Message],
        permission_flags: Dict[str, bool],
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ask model to decide what action to take (tool or chat or error)."""
        if not self.client:
            return {
                "type": "error",
                "reason": Messages.AI_NO_API_KEY,
                "tool": None,
                "arguments": {},
            }

        is_limited, retry_after = await self._rate_limiter.is_rate_limited(author.id)
        if is_limited:
            return {
                "type": "error",
                "reason": Messages.format(
                    Messages.AI_RATE_LIMIT, seconds=int(max(1, retry_after))
                ),
                "tool": None,
                "arguments": {},
            }

        history_lines: List[str] = []
        for msg in recent_messages[-10:]:
            who = "bot" if msg.author.bot else "user"
            history_lines.append(
                f"[{who}] {msg.author} ({msg.author.id}): {msg.content[:200]}"
            )
        history = "\n".join(history_lines) or "None"

        mention_lines: List[str] = []
        for m in mentions_meta:
            mention_lines.append(
                f"- index={m['index']} is_bot={m['is_bot']} "
                f"name={m['display']} id={m['id']}"
            )
        mentions_block = "\n".join(mention_lines) or "None"

        perm_lines = [
            f"- {key}: {value}" for key, value in sorted(permission_flags.items())
        ]
        perms_block = "\n".join(perm_lines) or "None"

        user_prompt = f"""
Server:
- Guild name: {guild.name}
- Guild ID: {guild.id}
- Member count: {getattr(guild, "member_count", "unknown")}

Request author:
- Name: {author}
- ID: {author.id}

Author permission flags:
{perms_block}

Mentions metadata (FIRST is the bot itself):
{mentions_block}

User message content (bot mention removed and trimmed):
\"\"\"{user_content}\"\"\"

Recent channel messages:
{history}

Decide what to do and respond ONLY with JSON using the schema from the system message.
""".strip()

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        loop = asyncio.get_running_loop()

        def _call():
            return self.client.chat.completions.create(
                model=model or GROQ_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=512,
            )

        try:
            await self._rate_limiter.record_call(author.id)
            completion = await loop.run_in_executor(None, _call)

            if not completion or not hasattr(completion, "choices") or not completion.choices:
                return {
                    "type": "error",
                    "reason": "No choices returned by model",
                    "tool": None,
                    "arguments": {},
                }

            choice = completion.choices[0]
            if hasattr(choice, "message"):
                content = choice.message.content or ""
            elif hasattr(choice, "text"):
                content = choice.text or ""
            else:
                return {
                    "type": "error",
                    "reason": "Malformed model response (no message/text)",
                    "tool": None,
                    "arguments": {},
                }

            content = self._strip_code_fences(content)
            try:
                data = json.loads(content)
            except Exception:
                return {
                    "type": "error",
                    "reason": "Model returned invalid JSON",
                    "tool": None,
                    "arguments": {},
                }

            if not isinstance(data, dict):
                return {
                    "type": "error",
                    "reason": "Model returned non-object JSON",
                    "tool": None,
                    "arguments": {},
                }

            data.setdefault("type", "error")
            data.setdefault("reason", "No reason provided")
            data.setdefault("tool", None)
            data.setdefault("arguments", {})

            valid_tools = {
                "warn_member",
                "timeout_member",
                "untimeout_member",
                "kick_member",
                "ban_member",
                "unban_member",
                "purge_messages",
                "show_help",
            }
            if data["type"] == "tool_call" and data["tool"] not in valid_tools:
                data["type"] = "error"
                data["reason"] = f"Unknown tool {data['tool']} chosen by model"

            return data
        except Exception as e:
            return {
                "type": "error",
                "reason": f"Exception during model call: {type(e).__name__}",
                "tool": None,
                "arguments": {},
            }

    # ========= CONVERSATION: remembers past exchanges per user =========

    # ========= CONVERSATION: remembers past exchanges per user =========

    async def converse(
        self,
        *,
        user_content: str,
        guild: discord.Guild,
        author: Union[discord.Member, discord.User],
        recent_messages: List[discord.Message],
        mentions_meta: List[Dict[str, Any]],
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a conversational reply, remembering past exchanges with this user."""
        if not self.client:
            return Messages.AI_NO_API_KEY

        is_limited, retry_after = await self._rate_limiter.is_rate_limited(author.id)
        if is_limited:
            return Messages.format(
                Messages.AI_RATE_LIMIT, seconds=int(max(1, retry_after))
            )

        loop = asyncio.get_running_loop()
        
        # Load memory from database
        try:
            past_memory = await self.bot.db.get_ai_memory(author.id)
        except Exception:
            past_memory = ""
        past_memory = past_memory.strip()

        history_lines: List[str] = []
        for msg in recent_messages[-USER_MEMORY_WINDOW:]:
            who = "bot" if msg.author.bot else "user"
            history_lines.append(f"[{who}] {msg.author}: {msg.content[:200]}")
        channel_snippet = "\n".join(history_lines) or "None"

        convo_system = (
            "You are an ultra-smart, witty, and fun AI assistant for this Discord server. "
            "Your personality is lively, observant, and engaging. You are NOT a boring robot. "
            "You have excellent memory of past conversations with this user. "
            "You can banter, make jokes, discuss complex topics, or give serious advice when needed. "
            "Always be helpful, but do it with style and personality. "
            "Use the provided context (memory and recent messages) to give highly relevant, coherent answers. "
            "Keep responses concise (1-3 sentences) unless a detailed explanation is requested. "
            "If the user is joking, joke back. If they are serious, be supportive."
        )

        user_prompt = (
            f"Server: {guild.name} (ID: {guild.id})\n"
            f"User: {author} (ID: {author.id})\n"
            f"User message: {user_content}\n\n"
            f"Past memory with this user (PERSISTENT):\n"
            f"{past_memory or 'None'}\n\n"
            f"Recent channel messages:\n"
            f"{channel_snippet}\n\n"
            "Reply as a fun, smart, and natural message."
        )

        messages = [
            {"role": "system", "content": convo_system},
            {"role": "user", "content": user_prompt},
        ]

        def _call():
            return self.client.chat.completions.create(
                model=model or GROQ_MODEL,
                messages=messages,
                temperature=0.8, # Increased for more fun/creativity
                max_tokens=512,
            )

        try:
            await self._rate_limiter.record_call(author.id)
            completion = await loop.run_in_executor(None, _call)
            if not completion or not hasattr(completion, "choices") or not completion.choices:
                return None

            choice = completion.choices[0]
            if hasattr(choice, "message"):
                content = choice.message.content or ""
            elif hasattr(choice, "text"):
                content = choice.text or ""
            else:
                return None

            content = self._strip_code_fences(content)
            
            # Update memory in background
            mem_piece = f"\n[user] {author}: {user_content[:200]}\n[bot] {content[:200]}"
            new_mem = (past_memory + mem_piece).strip()
            if len(new_mem) > USER_MEMORY_MAX_CHARS:
                # Keep the oldest part (summary) if possible? For now, sliding window
                # To be smarter: we could ask AI to summarize the memory if it gets too full.
                # For now, simplistic sliding window from end.
                new_mem = new_mem[-USER_MEMORY_MAX_CHARS:]
            
            # Save to DB asynchronously
            asyncio.create_task(self.bot.db.update_ai_memory(author.id, new_mem))
            
            return content
        except Exception:
            return None


# ========= COG =========


class ConfirmAIModActionView(discord.ui.View):
    """Confirmation view for AI moderation actions."""
    
    def __init__(
        self,
        cog: "AIModeration",
        *,
        actor_id: int,
        origin: discord.Message,
        tool: str,
        args: Dict[str, Any],
        decision: Dict[str, Any],
        timeout_seconds: int,
    ) -> None:
        super().__init__(timeout=max(5, min(int(timeout_seconds), 120)))
        self._cog = cog
        self._actor_id = actor_id
        self._origin = origin
        self._tool = tool
        self._args = args
        self._decision = decision
        self._done = False
        self.prompt_message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self._actor_id or is_bot_owner_id(interaction.user.id):
            return True
        try:
            await interaction.response.send_message(
                "This confirmation isn't for you.", ephemeral=True
            )
        except Exception:
            pass
        return False

    async def _disable_all(self) -> None:
        for child in self.children:
            if hasattr(child, 'disabled'):
                child.disabled = True

    async def on_timeout(self) -> None:
        if self._done:
            return
        self._done = True
        await self._disable_all()
        if self.prompt_message:
            try:
                embed = discord.Embed(
                    title="⏰ Confirmation Expired",
                    description="The action was not confirmed in time.",
                    color=discord.Color.greyple(),
                )
                await self.prompt_message.edit(embed=embed, view=self)
            except Exception:
                pass

    @discord.ui.button(label="✓ Confirm", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self._done:
            return
        self._done = True
        await self._disable_all()
        
        try:
            await interaction.response.defer()
        except Exception:
            pass

        if self.prompt_message:
            try:
                embed = discord.Embed(
                    title="✅ Action Confirmed",
                    description="Executing the moderation action...",
                    color=discord.Color.green(),
                )
                await self.prompt_message.edit(embed=embed, view=self)
            except Exception:
                pass

        await self._cog._dispatch_tool(
            self._origin,
            self._tool,
            self._args,
            self._decision,
            purge_before=self.prompt_message,
        )

    @discord.ui.button(label="✗ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self._done:
            return
        self._done = True
        await self._disable_all()
        
        try:
            embed = discord.Embed(
                title="❌ Action Cancelled",
                description="The moderation action was cancelled.",
                color=discord.Color.red(),
            )
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception:
            try:
                await interaction.response.send_message("Cancelled.", ephemeral=True)
            except Exception:
                pass



class AIModeration(commands.Cog):
    """
    AI moderation cog:
    - Mention the bot and talk normally: "terminate / execute / banish @user", etc.
    - Groq decides which moderation action to trigger OR replies conversationally.
    - All actions are still permission-checked against the calling member.
    - Every AI moderation action is logged to the automod log channel.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ai = GroqClientWrapper(bot)
        self.proactive_cooldowns: Dict[int, datetime] = {}  # channel_id -> last_response_time

    # ========= UTILITY HELPERS =========

    async def _get_aimod_settings(self, guild_id: int) -> Dict[str, Any]:
        merged = dict(DEFAULT_AIMOD_SETTINGS)
        db = getattr(self.bot, "db", None)
        if not db:
            return merged
        try:
            settings = await db.get_settings(guild_id)
        except Exception:
            return merged
        for key in DEFAULT_AIMOD_SETTINGS.keys():
            if key in settings:
                merged[key] = settings[key]
        return merged

    async def _set_aimod_setting(self, guild_id: int, key: str, value: Any) -> None:
        db = getattr(self.bot, "db", None)
        if not db:
            return
        settings = await db.get_settings(guild_id)
        settings[key] = value
        await db.update_settings(guild_id, settings)

    async def _recent_messages(
        self,
        channel: discord.abc.Messageable,
        limit: int = 15,
    ) -> List[discord.Message]:
        """Fetch recent messages from the channel."""
        try:
            msgs: List[discord.Message] = []
            async for msg in channel.history(limit=limit):
                msgs.append(msg)
            return msgs
        except Exception:
            return []

    def _clean_content(self, message: discord.Message) -> str:
        """Remove bot mention from message content."""
        content = message.content or ""
        if not self.bot.user:
            return content.strip()
        for fmt in (f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"):
            content = content.replace(fmt, "")
        return content.strip()

    def _mentions_meta(self, message: discord.Message) -> List[Dict[str, Any]]:
        """Build metadata for all mentions in the message."""
        out: List[Dict[str, Any]] = []
        for idx, m in enumerate(message.mentions):
            out.append(
                {
                    "index": idx,
                    "id": m.id,
                    "is_bot": bool(getattr(m, "bot", False)),
                    "display": str(m),
                }
            )
        return out

    async def _resolve_member_from_id(
        self, guild: discord.Guild, raw_id: Any
    ) -> Optional[discord.Member]:
        """Try to resolve a member from a raw ID value."""
        try:
            uid = int(raw_id)
        except (TypeError, ValueError):
            return None
        return guild.get_member(uid)

    async def _reply(
        self,
        origin: discord.Message,
        *,
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
        delete_after: Optional[float] = None,
    ):
        """Reply to a message, optionally auto-delete."""
        try:
            msg = await origin.channel.send(
                content=content,
                embed=embed,
                reference=origin,
                mention_author=False,
            )
            if delete_after:
                await msg.delete(delay=delete_after)
        except Exception:
            pass

    def _permission_flags(self, member: discord.Member) -> Dict[str, bool]:
        """Extract permission flags for a member."""
        if is_bot_owner_id(member.id):
            return {
                "can_manage_messages": True,
                "can_moderate_members": True,
                "can_kick_members": True,
                "can_ban_members": True,
                "can_manage_guild": True,
            }
        perms = member.guild_permissions
        return {
            "can_manage_messages": perms.manage_messages,
            "can_moderate_members": perms.moderate_members,
            "can_kick_members": perms.kick_members,
            "can_ban_members": perms.ban_members,
            "can_manage_guild": perms.manage_guild,
        }

    def _can_do_action_on(
        self,
        actor: discord.Member,
        target: discord.Member,
    ) -> bool:
        """Check if actor can perform actions on target (hierarchy)."""
        if actor == target:
            return is_bot_owner_id(actor.id)
        if is_bot_owner_id(target.id) and not is_bot_owner_id(actor.id):
            return False
        if target.id == target.guild.owner_id:
            return False
        if is_bot_owner_id(actor.id):
            return True
        if actor.top_role <= target.top_role and actor.id != actor.guild.owner_id:
            return False
        return True

    def _is_obvious_spam(self, content: str) -> bool:
        """
        Check if message is obvious spam that shouldn't trigger AI.
        
        Detects:
        - Empty or whitespace-only messages
        - Single character repeated (e.g., "s", "ss")
        - Very short messages (3-5 chars) with only 1 unique character (e.g., "sss", "!!!!")
        
        Does NOT flag:
        - Valid short words with different characters (e.g., "hi", "ok", "no")
        - Longer messages with variety
        
        Args:
            content: The message content to check
            
        Returns:
            True if the message is obvious spam, False otherwise
        """
        if not content:
            return True
        
        content = content.strip()
        
        # Empty or whitespace only
        if len(content) == 0:
            return True
        
        # Single character repeated
        if len(content) <= 2 and len(set(content)) == 1:
            return True
        
        # Very short message with only 1 unique character (3-5 chars)
        if 3 <= len(content) <= 5 and len(set(content.lower())) == 1:
            return True
        
        return False

    async def _log_ai_action(
        self,
        *,
        message: discord.Message,
        action: str,
        actor: discord.Member,
        target: Optional[Union[discord.Member, discord.User]] = None,
        reason: str = "No reason provided.",
        extra: Optional[Dict[str, str]] = None,
        decision: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an AI moderation action into the automod log channel
        using the existing logging cog's accurate channels.
        """
        guild = message.guild
        if guild is None:
            return

        # Try to get Logging cog
        logging_cog = self.bot.get_cog("Logging")
        if logging_cog is None:
            return

        # Get automod log channel via Logging.get_log_channel
        try:
            channel = await logging_cog.get_log_channel(guild, "automod")
        except Exception:
            channel = None

        if channel is None:
            return

        embed = discord.Embed(
            title=f"🤖 AI Moderation Action – {action}",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )

        embed.add_field(
            name="Actor",
            value=f"{actor.mention} (`{actor.id}`)",
            inline=True,
        )

        if target is not None:
            embed.add_field(
                name="Target",
                value=f"{target.mention} (`{target.id}`)",
                inline=True,
            )
        else:
            embed.add_field(
                name="Target",
                value="*None / unresolved*",
                inline=True,
            )

        embed.add_field(
            name="Channel",
            value=message.channel.mention,
            inline=True,
        )

        embed.add_field(
            name="Reason",
            value=reason or "No reason provided.",
            inline=False,
        )

        if extra:
            for k, v in extra.items():
                embed.add_field(name=k, value=v, inline=True)

        raw_content = message.content or ""
        if raw_content:
            trimmed = raw_content[:400]
            if len(raw_content) > 400:
                trimmed += "\n\n*…truncated*"
            embed.add_field(
                name="Original Message",
                value=trimmed,
                inline=False,
            )

        if decision:
            try:
                compact = json.dumps(
                    {
                        "type": decision.get("type"),
                        "tool": decision.get("tool"),
                    },
                    separators=(",", ":"),
                )
                embed.add_field(
                    name="AI Decision",
                    value=f"`{compact}`",
                    inline=False,
                )
            except Exception:
                pass

        embed.set_footer(text="AI Moderation -  logged to automod logs")

        try:
            await logging_cog.safe_send_log(channel, embed)
        except Exception:
            pass

    def _requires_confirmation(self, tool: str, settings: Dict[str, Any]) -> bool:
        if not settings.get("aimod_confirm_enabled", False):
            return False
        actions = settings.get("aimod_confirm_actions") or []
        return tool in set(actions)

    def _build_help_embed(self, guild: Optional[discord.Guild]) -> discord.Embed:
        bot_mention = (
            guild.me.mention if guild and guild.me else f"<@{self.bot.user.id}>"
        )
        lines = [
            "Talk to me like a human and I'll try to do the right moderation action, "
            "as long as **you** have permission for it.",
            "",
            "You can also have a conversation with me: ask for advice, explain context, "
            "or discuss a situation.",
            "",
            "**Examples:**",
            f"- `{bot_mention} terminate @User for spamming`",
            f"- `{bot_mention} banish @User for alt account, delete 1 day`",
            f"- `{bot_mention} execute @User for 2 hours for slurs`",
            f"- `{bot_mention} purge 50 messages they are all spam`",
            f"- `{bot_mention} yo what's good`",
            "",
            "Cool words I understand (mapped to real actions):",
            "- terminate / execute / gag / mute / silence → timeout",
              "- banish / exile / obliterate → ban",
              "- yeet / boot / eject → kick",
              "",
              "**Controls:**",
              "- `/aimod status` to view settings",
              "- `/aimod preview` to dry-run a request (no action)",
              "- `/aimod confirm` to require button confirmation",
              "",
              "Use `/aihelp` to see this again.",
          ]
        embed = discord.Embed(
            title="AI Moderation",
            description="\n".join(lines),
            color=0x5865F2,
        )
        embed.set_footer(text="Powered by Groq AI (respects your permissions)")
        return embed

    async def _dispatch_tool(
        self,
        message: discord.Message,
        tool: str,
        args: Dict[str, Any],
        decision: Optional[Dict[str, Any]] = None,
        *,
        purge_before: Optional[discord.Message] = None,
    ) -> None:
        if tool == "warn_member":
            await self._tool_warn(message, args, decision)
        elif tool == "timeout_member":
            await self._tool_timeout(message, args, decision)
        elif tool == "untimeout_member":
            await self._tool_untimeout(message, args, decision)
        elif tool == "kick_member":
            await self._tool_kick(message, args, decision)
        elif tool == "ban_member":
            await self._tool_ban(message, args, decision)
        elif tool == "unban_member":
            await self._tool_unban(message, args, decision)
        elif tool == "purge_messages":
            await self._tool_purge(message, args, decision, purge_before=purge_before)
        elif tool == "show_help":
            await self._send_help_embed(message)
        else:
            embed = discord.Embed(
                title="AI Tool Error",
                description=f"Unknown tool `{tool}`.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)

    async def _request_confirmation(
        self,
        message: discord.Message,
        *,
        tool: str,
        args: Dict[str, Any],
        decision: Dict[str, Any],
        settings: Dict[str, Any],
    ) -> None:
        guild = message.guild
        assert guild is not None
        actor: discord.Member = message.author  # type: ignore

        # Resolve target info
        target_text = "*None*"
        target_member = None
        raw_target = args.get("target_user_id")
        if raw_target is not None:
            target_member = await self._resolve_member_from_id(guild, raw_target)
            if target_member:
                target_text = f"{target_member.mention} ({target_member})"
            else:
                try:
                    target_text = f"<@{int(raw_target)}> (ID: `{int(raw_target)}`)"
                except Exception:
                    target_text = "*Could not resolve target*"

        # Action-specific formatting
        tool_info = {
            "warn_member": ("⚠️ Warn Member", discord.Color.gold()),
            "timeout_member": ("🔇 Timeout Member", discord.Color.orange()),
            "untimeout_member": ("🔊 Remove Timeout", discord.Color.green()),
            "kick_member": ("👢 Kick Member", discord.Color.red()),
            "ban_member": ("🔨 Ban Member", discord.Color.dark_red()),
            "unban_member": ("✅ Unban Member", discord.Color.green()),
            "purge_messages": ("🗑️ Purge Messages", discord.Color.blue()),
        }
        tool_display, tool_color = tool_info.get(tool, (f"🤖 {tool}", discord.Color.orange()))

        # Build reason string
        reason = args.get('reason') or decision.get('reason') or 'No reason provided'

        # Build extra info for specific tools
        extra_info = ""
        if tool == "timeout_member":
            seconds = args.get("seconds", 3600)
            try:
                mins = int(seconds) // 60
                extra_info = f"\n**Duration:** {mins} minute(s)"
            except Exception:
                pass
        elif tool == "purge_messages":
            amount = args.get("amount", 10)
            extra_info = f"\n**Amount:** {amount} message(s)"
        elif tool == "ban_member":
            delete_days = args.get("delete_message_days", 0)
            extra_info = f"\n**Delete Messages:** {delete_days} day(s)"

        timeout_secs = settings.get("aimod_confirm_timeout_seconds", 25)
        embed = discord.Embed(
            title=f"🤖 Confirm: {tool_display}",
            description=(
                f"**Target:** {target_text}\n"
                f"**Reason:** {reason}{extra_info}\n\n"
                f"⏱️ This will expire in **{timeout_secs} seconds**.\n"
                "Click a button below to confirm or cancel."
            ),
            color=tool_color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Requested by {actor} • AI Moderation")
        if target_member and target_member.avatar:
            embed.set_thumbnail(url=target_member.display_avatar.url)

        view = ConfirmAIModActionView(
            self,
            actor_id=actor.id,
            origin=message,
            tool=tool,
            args=args,
            decision=decision,
            timeout_seconds=timeout_secs,
        )
        try:
            prompt = await message.channel.send(
                embed=embed,
                view=view,
                reference=message,
                mention_author=False,
            )
            view.prompt_message = prompt
        except Exception:
            pass

    # ========= EVENT: natural language via mention =========

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Main event handler for bot mentions or proactive responses."""
        if message.author.bot or not message.guild:
            return
        if not self.bot.user:
            return

        settings = await self._get_aimod_settings(message.guild.id)
        if not settings.get("aimod_enabled", True):
            return

        # Check if message is obvious spam (unless explicitly mentioned)
        is_mentioned = self.bot.user in message.mentions
        if not is_mentioned and settings.get("aimod_ignore_spam", True):
            if self._is_obvious_spam(message.content):
                return

        is_proactive = False

        if not is_mentioned:
            # Check for proactive chance
            chance = settings.get("aimod_proactive_chance", 0.0)
            if chance <= 0:
                return
            
            # Check cooldown
            cooldown_seconds = settings.get("aimod_proactive_cooldown", 30)
            now = datetime.now(timezone.utc)
            if message.channel.id in self.proactive_cooldowns:
                last_time = self.proactive_cooldowns[message.channel.id]
                elapsed = (now - last_time).total_seconds()
                if elapsed < cooldown_seconds:
                    logger.debug(
                        f"Proactive response skipped due to cooldown in channel {message.channel.id} "
                        f"(elapsed: {elapsed:.1f}s < {cooldown_seconds}s)"
                    )
                    return
            
            if random.random() > chance:
                return
            
            is_proactive = True
            # Update cooldown
            self.proactive_cooldowns[message.channel.id] = now

        cleaned = self._clean_content(message)
        if not cleaned:
            if is_mentioned:
                await self._send_help_embed(message)
            return

        if isinstance(message.author, discord.Member):
            perm_flags = self._permission_flags(message.author)
        else:
            perm_flags = {
                "can_manage_messages": False,
                "can_moderate_members": False,
                "can_kick_members": False,
                "can_ban_members": False,
                "can_manage_guild": False,
            }

        mentions_meta = self._mentions_meta(message)
        recent_messages = await self._recent_messages(
            message.channel,
            limit=int(settings.get("aimod_context_messages", 15)),
        )

        # Show typing indicator while AI is processing
        async with message.channel.typing():
            try:
                decision = await self.ai.choose_tool(
                    user_content=cleaned,
                    guild=message.guild,
                    author=message.author,
                    mentions_meta=mentions_meta,
                    recent_messages=recent_messages,
                    permission_flags=perm_flags,
                    model=settings.get("aimod_model") or GROQ_MODEL,
                )
            except Exception as e:
                embed = discord.Embed(
                    title="❌ AI Moderation Error",
                    description=f"Failed to process request: `{type(e).__name__}`\n\nPlease try again.",
                    color=0xFF0000,
                )
                await self._reply(message, embed=embed, delete_after=15)
                if hasattr(self.bot, "errors_caught"):
                    self.bot.errors_caught += 1
                return

        dtype = decision.get("type")

        if dtype == "tool_call":
            tool = decision.get("tool")
            args = decision.get("arguments") or {}

            if isinstance(tool, str) and self._requires_confirmation(tool, settings):
                await self._request_confirmation(
                    message,
                    tool=tool,
                    args=args,
                    decision=decision,
                    settings=settings,
                )
                return

            if isinstance(tool, str):
                await self._dispatch_tool(message, tool, args, decision)
            return

        if dtype == "chat":
            reply = await self.ai.converse(
                user_content=cleaned,
                guild=message.guild,
                author=message.author,
                recent_messages=recent_messages,
                mentions_meta=mentions_meta,
                model=settings.get("aimod_model") or GROQ_MODEL,
            )
            if reply:
                if len(reply) > 1900:
                    embed = discord.Embed(
                        title="AI",
                        description=reply,
                        color=0x00AAFF,
                    )
                    await self._reply(message, embed=embed)
                else:
                    await self._reply(message, content=reply)
            else:
                # Silent failure for proactive mode
                if not is_proactive:
                    # Only show error if explicitly mentioned
                    logger.warning(f"AI failed to generate response for message {message.id}")
                    await self._reply(
                        message,
                        content="I couldn't process that request. Please try again.",
                        delete_after=10,
                    )
                # Otherwise fail silently
            return

        reason = decision.get("reason", "Request could not be processed.")
        embed = discord.Embed(
            title="AI Could Not Comply",
            description=reason,
            color=0xFF9900,
        )
        await self._reply(message, embed=embed, delete_after=15)

    # ========= TOOL HANDLERS =========

    async def _tool_untimeout(
        self,
        message: discord.Message,
        args: Dict[str, Any],
        decision: Optional[Dict[str, Any]] = None,
    ):
        guild = message.guild
        assert guild is not None
        actor: discord.Member = message.author  # type: ignore

        member = await self._resolve_member_from_id(guild, args.get("target_user_id"))
        reason = str(args.get("reason") or "No reason provided.")

        if not member:
            embed = discord.Embed(
                title="Unmute Failed",
                description="AI could not determine which member to unmute.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        if not actor.guild_permissions.moderate_members and not is_bot_owner_id(actor.id):
            embed = discord.Embed(
                title="Unmute Not Allowed",
                description="You lack the Timeout Members permission.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        if not self._can_do_action_on(actor, member):
            embed = discord.Embed(
                title="Unmute Not Allowed",
                description="You cannot unmute that member due to role hierarchy.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        try:
            await member.timeout(None, reason=f"[AI] {reason}")
        except discord.Forbidden:
            embed = discord.Embed(
                title="Unmute Failed",
                description="I don't have permission to unmute that user.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return
        except Exception as e:
            embed = discord.Embed(
                title="Unmute Error",
                description=f"Failed to unmute member: `{type(e).__name__}`.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        embed = discord.Embed(
            title="Member Unmuted (AI)",
            description=f"{member.mention} has been unmuted.\nReason: {reason}",
            color=0x00FF99,
        )
        embed.set_footer(text=f"Requested by {actor}")
        await message.channel.send(embed=embed)

        await self._log_ai_action(
            message=message,
            action="Unmute",
            actor=actor,
            target=member,
            reason=reason,
            decision=decision,
        )

    async def _tool_warn(
        self,
        message: discord.Message,
        args: Dict[str, Any],
        decision: Optional[Dict[str, Any]] = None,
    ):
        guild = message.guild
        assert guild is not None
        actor: discord.Member = message.author  # type: ignore

        member = await self._resolve_member_from_id(guild, args.get("target_user_id"))
        reason = str(args.get("reason") or "No reason provided.")

        if not member:
            embed = discord.Embed(
                title="Warn Failed",
                description="AI could not determine which member to warn.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        if not self._can_do_action_on(actor, member):
            embed = discord.Embed(
                title="Warn Not Allowed",
                description="You cannot warn that member due to role hierarchy.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        # DM user
        try:
            dm = await member.create_dm()
            await dm.send(
                f"You have been warned in **{guild.name}**.\nReason: {reason}"
            )
        except Exception:
            pass

        embed = discord.Embed(
            title="Member Warned (AI)",
            description=f"{member.mention} has been warned.\nReason: {reason}",
            color=0xFFA500,
        )
        embed.set_footer(text=f"Requested by {actor}")

        await message.channel.send(embed=embed)
        await self._log_ai_action(
            message=message,
            action="Warn",
            actor=actor,
            target=member,
            reason=reason,
            decision=decision,
        )

    async def _tool_timeout(
        self,
        message: discord.Message,
        args: Dict[str, Any],
        decision: Optional[Dict[str, Any]] = None,
    ):
        guild = message.guild
        assert guild is not None
        actor: discord.Member = message.author  # type: ignore

        member = await self._resolve_member_from_id(guild, args.get("target_user_id"))
        reason = str(args.get("reason") or "No reason provided.")
        raw_seconds = args.get("seconds", 3600)

        try:
            seconds = int(raw_seconds)
        except (TypeError, ValueError):
            seconds = 3600

        seconds = max(60, min(seconds, 259200))

        if not member:
            embed = discord.Embed(
                title="Timeout Failed",
                description="AI could not determine which member to timeout.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        if not actor.guild_permissions.moderate_members and not is_bot_owner_id(actor.id):
            embed = discord.Embed(
                title="Timeout Not Allowed",
                description="You lack the Timeout Members permission.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        if not self._can_do_action_on(actor, member):
            embed = discord.Embed(
                title="Timeout Not Allowed",
                description="You cannot timeout that member due to role hierarchy.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        until = datetime.now(timezone.utc) + timedelta(seconds=seconds)

        try:
            await member.timeout(until, reason=f"[AI] {reason}")
        except discord.Forbidden:
            embed = discord.Embed(
                title="Timeout Failed",
                description="I don't have permission to timeout that user.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return
        except Exception as e:
            embed = discord.Embed(
                title="Timeout Error",
                description=f"Failed to timeout member: `{type(e).__name__}`.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        mins = seconds // 60
        embed = discord.Embed(
            title="Member Timed Out (AI)",
            description=(
                f"{member.mention} has been timed out for **{mins} minutes**.\n"
                f"Reason: {reason}"
            ),
            color=0xFF4500,
        )
        embed.set_footer(text=f"Requested by {actor}")
        await message.channel.send(embed=embed)

        await self._log_ai_action(
            message=message,
            action="Timeout",
            actor=actor,
            target=member,
            reason=reason,
            extra={"Duration": f"{seconds} seconds"},
            decision=decision,
        )

    async def _tool_kick(
        self,
        message: discord.Message,
        args: Dict[str, Any],
        decision: Optional[Dict[str, Any]] = None,
    ):
        guild = message.guild
        assert guild is not None
        actor: discord.Member = message.author  # type: ignore

        member = await self._resolve_member_from_id(guild, args.get("target_user_id"))
        reason = str(args.get("reason") or "No reason provided.")

        if not member:
            embed = discord.Embed(
                title="Kick Failed",
                description="AI could not determine which member to kick.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        if not actor.guild_permissions.kick_members and not is_bot_owner_id(actor.id):
            embed = discord.Embed(
                title="Kick Not Allowed",
                description="You lack the Kick Members permission.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        if not self._can_do_action_on(actor, member):
            embed = discord.Embed(
                title="Kick Not Allowed",
                description="You cannot kick that member due to role hierarchy.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        try:
            await member.kick(reason=f"[AI] {reason}")
        except discord.Forbidden:
            embed = discord.Embed(
                title="Kick Failed",
                description="I don't have permission to kick that user.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return
        except Exception as e:
            embed = discord.Embed(
                title="Kick Error",
                description=f"Failed to kick member: `{type(e).__name__}`.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        embed = discord.Embed(
            title="Member Kicked (AI)",
            description=f"{member.mention} has been kicked.\nReason: {reason}",
            color=0xFF0000,
        )
        embed.set_footer(text=f"Requested by {actor}")
        await message.channel.send(embed=embed)

        await self._log_ai_action(
            message=message,
            action="Kick",
            actor=actor,
            target=member,
            reason=reason,
            decision=decision,
        )

    async def _tool_ban(
        self,
        message: discord.Message,
        args: Dict[str, Any],
        decision: Optional[Dict[str, Any]] = None,
    ):
        guild = message.guild
        assert guild is not None
        actor: discord.Member = message.author  # type: ignore

        member = await self._resolve_member_from_id(guild, args.get("target_user_id"))
        reason = str(args.get("reason") or "No reason provided.")
        raw_days = args.get("delete_message_days", 0)

        try:
            delete_days = int(raw_days)
        except (TypeError, ValueError):
            delete_days = 0

        delete_days = max(0, min(delete_days, 7))

        if not member:
            embed = discord.Embed(
                title="Ban Failed",
                description="AI could not determine which member to ban.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        if not actor.guild_permissions.ban_members and not is_bot_owner_id(actor.id):
            embed = discord.Embed(
                title="Ban Not Allowed",
                description="You lack the Ban Members permission.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        if not self._can_do_action_on(actor, member):
            embed = discord.Embed(
                title="Ban Not Allowed",
                description="You cannot ban that member due to role hierarchy.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        try:
            # Fix for discord.py 2.0+ compatibility
            await guild.ban(
                member,
                delete_message_seconds=delete_days * 86400,  # Convert days to seconds
                reason=f"[AI] {reason}",
            )
        except discord.Forbidden:
            embed = discord.Embed(
                title="Ban Failed",
                description="I don't have permission to ban that user.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return
        except Exception as e:
            embed = discord.Embed(
                title="Ban Error",
                description=f"Failed to ban member: `{type(e).__name__}`.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        embed = discord.Embed(
            title="Member Banned (AI)",
            description=(
                f"{member.mention} has been banned.\n"
                f"Reason: {reason}\n"
                f"Deleted last **{delete_days}** day(s) of messages."
            ),
            color=0x8B0000,
        )
        embed.set_footer(text=f"Requested by {actor}")
        await message.channel.send(embed=embed)

        await self._log_ai_action(
            message=message,
            action="Ban",
            actor=actor,
            target=member,
            reason=reason,
            extra={"Messages Deleted": f"{delete_days} day(s)"},
            decision=decision,
        )

    async def _tool_unban(
        self,
        message: discord.Message,
        args: Dict[str, Any],
        decision: Optional[Dict[str, Any]] = None,
    ):
        guild = message.guild
        assert guild is not None
        actor: discord.Member = message.author  # type: ignore

        raw_id = args.get("target_user_id")
        try:
            uid = int(raw_id)
        except (TypeError, ValueError):
            uid = None

        reason = str(args.get("reason") or "No reason provided.")

        if not uid:
            embed = discord.Embed(
                title="Unban Failed",
                description="AI did not provide a valid user ID to unban.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        if not actor.guild_permissions.ban_members and not is_bot_owner_id(actor.id):
            embed = discord.Embed(
                title="Unban Not Allowed",
                description="You lack the Ban Members permission.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        try:
            try:
                user = await self.bot.fetch_user(uid)
            except Exception:
                user = discord.Object(id=uid)  # type: ignore
            await guild.unban(user, reason=f"[AI] {reason}")
        except discord.NotFound:
            embed = discord.Embed(
                title="Unban Failed",
                description="That user is not banned.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return
        except discord.Forbidden:
            embed = discord.Embed(
                title="Unban Failed",
                description="I don't have permission to unban users.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return
        except Exception as e:
            embed = discord.Embed(
                title="Unban Error",
                description=f"Failed to unban member: `{type(e).__name__}`.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        display_user: Union[discord.User, discord.Object]
        if isinstance(user, discord.Object):
            display_user = user
            user_str = f"<@{uid}>"
        else:
            display_user = user
            user_str = f"{user.mention}"

        embed = discord.Embed(
            title="Member Unbanned (AI)",
            description=f"{user_str} has been unbanned.\nReason: {reason}",
            color=0x00FF00,
        )
        embed.set_footer(text=f"Requested by {actor}")
        await message.channel.send(embed=embed)

        await self._log_ai_action(
            message=message,
            action="Unban",
            actor=actor,
            target=display_user if isinstance(display_user, discord.User) else None,
            reason=reason,
            decision=decision,
        )

    async def _tool_purge(
        self,
        message: discord.Message,
        args: Dict[str, Any],
        decision: Optional[Dict[str, Any]] = None,
        *,
        purge_before: Optional[discord.Message] = None,
    ):
        channel = message.channel
        guild = message.guild
        assert guild is not None
        actor: discord.Member = message.author  # type: ignore

        raw_amount = args.get("amount", 10)
        try:
            amount = int(raw_amount)
        except (TypeError, ValueError):
            amount = 10

        amount = max(1, min(amount, 500))
        reason = str(args.get("reason") or "Channel cleanup (AI).")

        if not actor.guild_permissions.manage_messages and not is_bot_owner_id(actor.id):
            embed = discord.Embed(
                title="Purge Not Allowed",
                description="You lack the Manage Messages permission.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        try:
            deleted = await channel.purge(
                limit=amount + 1,
                before=purge_before,
                reason=f"[AI] {reason}",
            )
        except discord.Forbidden:
            embed = discord.Embed(
                title="Purge Failed",
                description="I don't have permission to manage messages here.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return
        except Exception as e:
            embed = discord.Embed(
                title="Purge Error",
                description=f"Failed to delete messages: `{type(e).__name__}`.",
                color=0xFF0000,
            )
            await self._reply(message, embed=embed, delete_after=15)
            return

        embed = discord.Embed(
            title="Messages Purged (AI)",
            description=f"Deleted **{len(deleted)}** messages.\nReason: {reason}",
            color=0x00CED1,
        )
        await channel.send(embed=embed, delete_after=10)

        await self._log_ai_action(
            message=message,
            action="Purge",
            actor=actor,
            target=None,
            reason=reason,
            extra={"Deleted Messages": str(len(deleted))},
            decision=decision,
        )

    # ========= HELP (embed + slash) =========

    async def _send_help_embed(self, message: discord.Message):
        """Send help embed explaining how the bot works."""
        embed = self._build_help_embed(message.guild)
        await message.channel.send(embed=embed)

    @commands.hybrid_command(name="aihelp", description="Show AI moderation help.")
    async def aihelp(self, ctx: commands.Context):
        """Slash command for help."""
        if not ctx.guild:
            await ctx.send("Use this in a server.")
            return

        embed = self._build_help_embed(ctx.guild)
        if getattr(ctx, "interaction", None):
            try:
                await ctx.interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception:
                await ctx.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    # ========= SLASH COMMANDS =========
    
    @app_commands.command(name="aimod", description="🤖 AI moderation settings and tools")
    @app_commands.describe(
        action="Action to perform (status, enable, disable, etc.)",
        model="Model name (for 'model' action)",
        count="Number of messages (for 'context' action)",
        enabled="Enable/disable confirmations (for 'confirm' action)",
        actions="Comma-separated tools (for 'confirm' action)",
        timeout_seconds="Timeout in seconds (for 'confirm' action)",
        text="Text to preview (for 'preview' action)",
        target="Target member (for 'preview' action)",
    )
    async def aimod(
        self,
        interaction: discord.Interaction,
        action: Literal["status", "enable", "disable", "model", "context", "confirm", "preview", "help"],
        model: Optional[str] = None,
        count: Optional[int] = None,
        enabled: Optional[bool] = None,
        actions: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        text: Optional[str] = None,
        target: Optional[discord.Member] = None,
    ):
        if action == "help":
            await self.aihelp(interaction) # type: ignore
            return

        if action == "status":
            if not is_mod().predicate(interaction):
                return await interaction.response.send_message("❌ You must be a moderator to use this.", ephemeral=True)
            await self.aimod_status(interaction)
        
        elif action == "enable":
            if not is_admin().predicate(interaction):
                return await interaction.response.send_message("❌ You must be an admin to use this.", ephemeral=True)
            await self._set_aimod_setting(interaction.guild_id, "aimod_enabled", True)
            await interaction.response.send_message("✅ AI moderation is now enabled.", ephemeral=True)
            
        elif action == "disable":
            if not is_admin().predicate(interaction):
                return await interaction.response.send_message("❌ You must be an admin to use this.", ephemeral=True)
            await self._set_aimod_setting(interaction.guild_id, "aimod_enabled", False)
            await interaction.response.send_message("✅ AI moderation is now disabled.", ephemeral=True)

        elif action == "model":
            if not is_admin().predicate(interaction):
                return await interaction.response.send_message("❌ You must be an admin to use this.", ephemeral=True)
            if not model:
                return await interaction.response.send_message("❌ Please specify a `model`.", ephemeral=True)
            
            clean_model = model.strip()
            if clean_model.lower() == "default":
                clean_model = GROQ_MODEL
            await self._set_aimod_setting(interaction.guild_id, "aimod_model", clean_model)
            await interaction.response.send_message(f"✅ AI moderation model set to `{clean_model}`.", ephemeral=True)

        elif action == "context":
            if not is_admin().predicate(interaction):
                return await interaction.response.send_message("❌ You must be an admin to use this.", ephemeral=True)
            if count is None:
                return await interaction.response.send_message("❌ Please specify a `count` (0-30).", ephemeral=True)
                
            val = max(0, min(int(count), 30))
            await self._set_aimod_setting(interaction.guild_id, "aimod_context_messages", val)
            await interaction.response.send_message(f"✅ Context messages set to **{val}**.", ephemeral=True)

        elif action == "confirm":
            if not is_admin().predicate(interaction):
                return await interaction.response.send_message("❌ You must be an admin to use this.", ephemeral=True)
            if enabled is None:
                return await interaction.response.send_message("❌ Please specify `enabled: True/False`.", ephemeral=True)
            
            await self.aimod_confirm(interaction, enabled, actions, timeout_seconds)

        elif action == "preview":
            if not is_mod().predicate(interaction):
                return await interaction.response.send_message("❌ You must be a moderator to use this.", ephemeral=True)
            if not text:
                return await interaction.response.send_message("❌ Please specify `text` to preview.", ephemeral=True)
            
            await self.aimod_preview(interaction, text, target)

    # Internal helper for status logic reuse
    async def aimod_status(self, interaction: discord.Interaction):
        settings = await self._get_aimod_settings(interaction.guild_id)
        embed = discord.Embed(title="🤖 AI Moderation Settings", color=discord.Color.blurple())
        
        embed.add_field(name="Enabled", value="🟢 Yes" if settings.get("aimod_enabled", True) else "🔴 No", inline=True)
        embed.add_field(name="Model", value=f"`{settings.get('aimod_model', GROQ_MODEL)}`", inline=True)
        embed.add_field(name="Context Messages", value=str(settings.get("aimod_context_messages", 15)), inline=True)
        
        confirm_enabled = bool(settings.get("aimod_confirm_enabled", False))
        embed.add_field(name="Confirm Actions", value="🟢 On" if confirm_enabled else "🔴 Off", inline=True)
        
        actions = settings.get("aimod_confirm_actions") or []
        embed.add_field(name="Confirm List", value=f"`{', '.join(actions)}`" if actions else "*None*", inline=False)
        embed.add_field(name="Confirm Timeout", value=f"{settings.get('aimod_confirm_timeout_seconds', 25)}s", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Internal helper for confirm logic reuse
    async def aimod_confirm(self, interaction: discord.Interaction, enabled: bool, actions: Optional[str], timeout_seconds: Optional[int]):
        settings = await self._get_aimod_settings(interaction.guild_id)
        settings["aimod_confirm_enabled"] = bool(enabled)
        
        if timeout_seconds is not None:
            settings["aimod_confirm_timeout_seconds"] = max(5, min(int(timeout_seconds), 120))
            
        if actions is not None:
            chosen = [a.strip() for a in actions.split(",") if a.strip()]
            valid = {
                "warn_member", "timeout_member", "untimeout_member", "kick_member",
                "ban_member", "unban_member", "purge_messages", "show_help"
            }
            chosen = [a for a in chosen if a in valid]
            if chosen:
                settings["aimod_confirm_actions"] = chosen

        # Persist
        db = getattr(self.bot, "db", None)
        if db:
            raw = await db.get_settings(interaction.guild_id)
            raw["aimod_confirm_enabled"] = settings["aimod_confirm_enabled"]
            raw["aimod_confirm_timeout_seconds"] = settings.get("aimod_confirm_timeout_seconds", 25)
            raw["aimod_confirm_actions"] = settings.get("aimod_confirm_actions", DEFAULT_AIMOD_SETTINGS["aimod_confirm_actions"])
            await db.update_settings(interaction.guild_id, raw)

        await interaction.response.send_message(
            f"✅ Confirmations are now **{'enabled' if enabled else 'disabled'}**.",
            ephemeral=True,
        )

    # Internal helper for preview logic reuse
    async def aimod_preview(self, interaction: discord.Interaction, text: str, target: Optional[discord.Member]):
        if not interaction.guild or not interaction.channel:
            await interaction.response.send_message("Use this in a server.", ephemeral=True)
            return

        if not self.bot.user:
            await interaction.response.send_message("Bot is not ready yet.", ephemeral=True)
            return

        settings = await self._get_aimod_settings(interaction.guild_id)
        perm_flags = self._permission_flags(interaction.user)  # type: ignore

        mentions_meta: List[Dict[str, Any]] = [
            {"index": 0, "id": self.bot.user.id, "is_bot": True, "display": str(self.bot.user)}
        ]
        if target is not None:
            mentions_meta.append(
                {"index": 1, "id": target.id, "is_bot": bool(getattr(target, "bot", False)), "display": str(target)}
            )

        recent_messages = await self._recent_messages(
            interaction.channel, limit=int(settings.get("aimod_context_messages", 15))
        )
        
        # Defer since AI can take a moment
        await interaction.response.defer(ephemeral=True)
        
        try:
            decision = await self.ai.choose_tool(
                user_content=text,
                guild=interaction.guild,
                author=interaction.user,
                mentions_meta=mentions_meta,
                recent_messages=recent_messages,
                permission_flags=perm_flags,
                model=settings.get("aimod_model") or GROQ_MODEL,
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Error during preview: {e}", ephemeral=True)
            return

        embed = discord.Embed(title="AI Moderation Preview", color=discord.Color.blurple())
        embed.add_field(name="Type", value=f"`{decision.get('type')}`", inline=True)
        embed.add_field(name="Tool", value=f"`{decision.get('tool')}`", inline=True)
        embed.add_field(name="Reason", value=str(decision.get("reason") or "No reason"), inline=False)
        try:
            args_json = json.dumps(decision.get("arguments") or {}, ensure_ascii=False)
        except Exception:
            args_json = "{}"
        embed.add_field(name="Arguments", value=f"`{args_json}`", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AIModeration(bot))
