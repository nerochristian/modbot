import os
import re
import json
import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union, Literal, Set
from dataclasses import dataclass, field

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
        """Remove markdown code fences and extract JSON object."""
        text = raw.strip()
        
        # Remove markdown code fences
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
        
        # Improved: Extract JSON object using regex to handle LLM preamble/postamble
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            return match.group(1)
        
        return text

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
        
        # Database safety check
        if not hasattr(bot, "db"):
            logger.warning("Bot.db is missing! AI Moderation database features will be unavailable.")

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

        is_mentioned = self.bot.user in message.mentions
        is_proactive = False

        if not is_mentioned:
            # Check for proactive chance
            chance = settings.get("aimod_proactive_chance", 0.0)
            if chance <= 0:
                return
            
            # Simple cooldown check: don't proactive reply if one happened recently in this channel
            # We can use the ratelimiter or a simple cache
            # For now, let's just roll the dice.
            if random.random() > chance:
                return
            
            # Additional check: don't interrupt active conversations too much?
            # Or just go for it.
            is_proactive = True

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
                await self._reply(
                    message,
                    content="uhh my brain lagged for a sec, try again?",
                )
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


# ========= INTEGRATION WITH EXISTING COGS =========
# NOTE: AutoMod functionality is in automod.py (AIModerationHelper, AutoMod cog)
# NOTE: Raid detection is in antiraid.py (AIRaidAnalyzer, AntiRaid cog)
# These wrappers provide a unified interface for the AI moderation system

class AutoModIntegration:
    """Thin wrapper to interact with the existing AutoMod cog."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @property
    def cog(self):
        """Get the AutoMod cog if loaded."""
        return self.bot.get_cog("AutoMod")
    
    async def is_enabled(self, guild_id: int) -> bool:
        """Check if AutoMod is enabled for a guild."""
        if not self.cog:
            return False
        try:
            settings = await self.bot.db.get_settings(guild_id)
            return settings.get("automod_enabled", False)
        except Exception:
            return False
    
    async def get_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get AutoMod settings for a guild."""
        try:
            return await self.bot.db.get_settings(guild_id)
        except Exception:
            return {}


class AntiRaidIntegration:
    """Thin wrapper to interact with the existing AntiRaid cog."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @property
    def cog(self):
        """Get the AntiRaid cog if loaded."""
        return self.bot.get_cog("AntiRaid")
    
    async def is_raid_mode_active(self, guild_id: int) -> bool:
        """Check if raid mode is currently active."""
        if not self.cog:
            return False
        return guild_id in getattr(self.cog, '_raid_mode_active', set())
    
    async def trigger_lockdown(self, guild: discord.Guild, reason: str) -> bool:
        """Trigger lockdown via the AntiRaid cog."""
        if not self.cog:
            return False
        try:
            # Delegate to existing cog
            settings = await self.bot.db.get_settings(guild.id)
            await self.cog.trigger_raid_response(guild, settings, action="lockdown")
            return True
        except Exception as e:
            logger.error(f"Lockdown delegation failed: {e}")
            return False


# ========= AI CONTENT ANALYSIS =========

class ContentAnalyzer:
    """AI-powered content analysis for toxicity, sentiment, and intent."""
    
    ANALYSIS_PROMPT = """Analyze this Discord message for moderation purposes.

Message: "{content}"
Author: {author}
Context: {context}

Respond with JSON only:
{{
  "toxicity_score": 0.0-1.0,
  "sentiment": "positive" | "neutral" | "negative",
  "intent": "friendly" | "spam" | "harassment" | "threat" | "scam" | "unknown",
  "contains_pii": true/false,
  "language": "en" | "es" | ...,
  "summary": "brief description"
}}"""

    def __init__(self, client: Optional[Groq]):
        self.client = client
    
    async def analyze(
        self,
        content: str,
        author: str,
        context: str = "",
        model: str = GROQ_MODEL,
    ) -> Dict[str, Any]:
        """Analyze content using AI."""
        if not self.client:
            return {"error": "No AI client"}
        
        prompt = self.ANALYSIS_PROMPT.format(
            content=content[:500],
            author=author,
            context=context[:300],
        )
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300,
            )
            
            raw = response.choices[0].message.content
            # Strip markdown if present
            if raw.startswith("```"):
                raw = re.sub(r"^```\w*\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
            
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            return {"error": str(e)}


# ========= USER RISK SCORING =========

@dataclass
class UserRiskProfile:
    """Risk profile for a user."""
    user_id: int
    guild_id: int
    base_score: float = 0.0
    warning_count: int = 0
    timeout_count: int = 0
    kick_count: int = 0
    ban_count: int = 0
    automod_flags: int = 0
    last_violation: Optional[datetime] = None
    notes: List[str] = field(default_factory=list)
    
    @property
    def risk_score(self) -> float:
        """Calculate current risk score (0-100)."""
        score = self.base_score
        score += self.warning_count * 5
        score += self.timeout_count * 10
        score += self.kick_count * 20
        score += self.ban_count * 40
        score += self.automod_flags * 3
        
        # Decay over time
        if self.last_violation:
            days_since = (datetime.now(timezone.utc) - self.last_violation).days
            decay = min(0.5, days_since * 0.02)
            score *= (1 - decay)
        
        return min(100.0, max(0.0, score))
    
    @property
    def risk_level(self) -> str:
        """Get human-readable risk level."""
        score = self.risk_score
        if score < 10:
            return "Low"
        elif score < 30:
            return "Moderate"
        elif score < 60:
            return "High"
        else:
            return "Critical"


class RiskScorer:
    """Manages user risk scoring."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._profiles: Dict[Tuple[int, int], UserRiskProfile] = {}
    
    async def get_profile(self, user_id: int, guild_id: int) -> UserRiskProfile:
        """Get or create risk profile for user."""
        key = (user_id, guild_id)
        if key not in self._profiles:
            # Try to load from DB
            profile = UserRiskProfile(user_id=user_id, guild_id=guild_id)
            
            try:
                warnings = await self.bot.db.get_warnings(guild_id, user_id)
                profile.warning_count = len(warnings)
                
                cases = await self.bot.db.get_user_cases(guild_id, user_id)
                for case in cases:
                    action = case.get("action", "").lower()
                    if "timeout" in action or "mute" in action:
                        profile.timeout_count += 1
                    elif "kick" in action:
                        profile.kick_count += 1
                    elif "ban" in action:
                        profile.ban_count += 1
            except Exception:
                pass
            
            self._profiles[key] = profile
        
        return self._profiles[key]
    
    async def record_violation(
        self,
        user_id: int,
        guild_id: int,
        violation_type: str,
        severity: float = 1.0,
    ) -> UserRiskProfile:
        """Record a violation and update risk score."""
        profile = await self.get_profile(user_id, guild_id)
        profile.base_score += severity * 5
        profile.last_violation = datetime.now(timezone.utc)
        profile.notes.append(f"{violation_type} at {profile.last_violation.isoformat()}")
        
        if violation_type == "automod":
            profile.automod_flags += 1
        
        return profile
    
    async def get_recommendations(self, profile: UserRiskProfile) -> List[str]:
        """Get moderation recommendations based on risk profile."""
        recommendations = []
        score = profile.risk_score
        
        if score >= 80:
            recommendations.append("Consider permanent ban - user is extremely high risk")
        elif score >= 60:
            recommendations.append("Extended timeout (24h+) recommended")
            recommendations.append("Review recent activity carefully")
        elif score >= 40:
            recommendations.append("Issue formal warning")
            recommendations.append("Monitor user activity")
        elif score >= 20:
            recommendations.append("Note for future reference")
        
        if profile.automod_flags >= 3:
            recommendations.append("Multiple AutoMod flags - review message history")
        
        return recommendations


# ========= SCHEDULED ACTIONS =========

@dataclass
class ScheduledAction:
    """A scheduled moderation action."""
    id: str
    guild_id: int
    user_id: int
    action_type: str
    scheduled_for: datetime
    created_by: int
    reason: str
    executed: bool = False
    cancelled: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "action_type": self.action_type,
            "scheduled_for": self.scheduled_for.isoformat(),
            "created_by": self.created_by,
            "reason": self.reason,
            "executed": self.executed,
            "cancelled": self.cancelled,
        }


class ActionScheduler:
    """Manages scheduled/delayed moderation actions."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._actions: Dict[str, ScheduledAction] = {}
        self._task: Optional[asyncio.Task] = None
    
    def start(self):
        """Start the scheduler background task."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._scheduler_loop())
    
    def stop(self):
        """Stop the scheduler."""
        if self._task and not self._task.done():
            self._task.cancel()
    
    async def _scheduler_loop(self):
        """Background loop to execute scheduled actions."""
        while True:
            try:
                await asyncio.sleep(30)
                now = datetime.now(timezone.utc)
                
                for action_id, action in list(self._actions.items()):
                    if action.executed or action.cancelled:
                        continue
                    
                    if action.scheduled_for <= now:
                        await self._execute_action(action)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
    
    async def _execute_action(self, action: ScheduledAction):
        """Execute a scheduled action."""
        try:
            guild = self.bot.get_guild(action.guild_id)
            if not guild:
                action.cancelled = True
                return
            
            member = guild.get_member(action.user_id)
            
            if action.action_type == "unban":
                user = discord.Object(id=action.user_id)
                await guild.unban(user, reason=f"[Scheduled] {action.reason}")
            elif action.action_type == "untimeout" and member:
                await member.timeout(None, reason=f"[Scheduled] {action.reason}")
            elif action.action_type == "timeout" and member:
                until = datetime.now(timezone.utc) + timedelta(hours=1)
                await member.timeout(until, reason=f"[Scheduled] {action.reason}")
            elif action.action_type == "kick" and member:
                await member.kick(reason=f"[Scheduled] {action.reason}")
            elif action.action_type == "ban" and member:
                await guild.ban(member, reason=f"[Scheduled] {action.reason}")
            
            action.executed = True
            logger.info(f"Executed scheduled action {action.id}")
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled action {action.id}: {e}")
    
    async def schedule(
        self,
        guild_id: int,
        user_id: int,
        action_type: str,
        delay_seconds: int,
        created_by: int,
        reason: str,
    ) -> ScheduledAction:
        """Schedule a new action."""
        import uuid
        action = ScheduledAction(
            id=str(uuid.uuid4())[:8],
            guild_id=guild_id,
            user_id=user_id,
            action_type=action_type,
            scheduled_for=datetime.now(timezone.utc) + timedelta(seconds=delay_seconds),
            created_by=created_by,
            reason=reason,
        )
        self._actions[action.id] = action
        return action
    
    async def cancel(self, action_id: str) -> bool:
        """Cancel a scheduled action."""
        if action_id in self._actions:
            self._actions[action_id].cancelled = True
            return True
        return False
    
    def list_pending(self, guild_id: int) -> List[ScheduledAction]:
        """List pending actions for a guild."""
        return [
            a for a in self._actions.values()
            if a.guild_id == guild_id and not a.executed and not a.cancelled
        ]


# ========= APPEAL SYSTEM =========

@dataclass
class Appeal:
    """A moderation appeal."""
    id: str
    guild_id: int
    user_id: int
    case_id: int
    reason: str
    submitted_at: datetime
    status: Literal["pending", "approved", "denied", "reviewing"] = "pending"
    reviewer_id: Optional[int] = None
    reviewer_notes: Optional[str] = None
    ai_recommendation: Optional[str] = None


class AppealSystem:
    """Manages moderation appeals with AI review assistance."""
    
    def __init__(self, bot: commands.Bot, ai_client: Optional[Groq]):
        self.bot = bot
        self.ai_client = ai_client
        self._appeals: Dict[str, Appeal] = {}
    
    async def submit_appeal(
        self,
        guild_id: int,
        user_id: int,
        case_id: int,
        reason: str,
    ) -> Appeal:
        """Submit a new appeal."""
        import uuid
        appeal = Appeal(
            id=str(uuid.uuid4())[:8],
            guild_id=guild_id,
            user_id=user_id,
            case_id=case_id,
            reason=reason,
            submitted_at=datetime.now(timezone.utc),
        )
        
        # Get AI recommendation
        if self.ai_client:
            try:
                case = await self.bot.db.get_case(guild_id, case_id)
                case_info = json.dumps(case) if case else "Unknown case"
                
                prompt = f"""Review this moderation appeal:
Case: {case_info}
Appeal reason: {reason}

Should this appeal be approved? Respond with JSON:
{{"recommendation": "approve" | "deny" | "review", "confidence": 0.0-1.0, "reasoning": "..."}}"""

                response = await asyncio.to_thread(
                    self.ai_client.chat.completions.create,
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=200,
                )
                
                appeal.ai_recommendation = response.choices[0].message.content
            except Exception as e:
                logger.error(f"AI appeal review failed: {e}")
        
        self._appeals[appeal.id] = appeal
        return appeal
    
    async def review_appeal(
        self,
        appeal_id: str,
        reviewer_id: int,
        decision: Literal["approved", "denied"],
        notes: str = "",
    ) -> Optional[Appeal]:
        """Review and decide on an appeal."""
        if appeal_id not in self._appeals:
            return None
        
        appeal = self._appeals[appeal_id]
        appeal.status = decision
        appeal.reviewer_id = reviewer_id
        appeal.reviewer_notes = notes
        
        # If approved, potentially reverse the action
        if decision == "approved":
            try:
                case = await self.bot.db.get_case(appeal.guild_id, appeal.case_id)
                if case:
                    action = case.get("action", "").lower()
                    guild = self.bot.get_guild(appeal.guild_id)
                    
                    if guild and "ban" in action:
                        user = discord.Object(id=appeal.user_id)
                        await guild.unban(user, reason=f"[Appeal Approved] {notes}")
                    elif guild and ("timeout" in action or "mute" in action):
                        member = guild.get_member(appeal.user_id)
                        if member:
                            await member.timeout(None, reason=f"[Appeal Approved] {notes}")
            except Exception as e:
                logger.error(f"Failed to reverse action for appeal {appeal_id}: {e}")
        
        return appeal
    
    def get_pending(self, guild_id: int) -> List[Appeal]:
        """Get pending appeals for a guild."""
        return [
            a for a in self._appeals.values()
            if a.guild_id == guild_id and a.status == "pending"
        ]


# ========= ANALYTICS & REPORTING =========

@dataclass
class ModerationStats:
    """Statistics for moderation activity."""
    period_start: datetime
    period_end: datetime
    total_actions: int = 0
    warnings: int = 0
    timeouts: int = 0
    kicks: int = 0
    bans: int = 0
    unbans: int = 0
    purges: int = 0
    automod_actions: int = 0
    ai_actions: int = 0
    appeals_submitted: int = 0
    appeals_approved: int = 0
    most_active_moderators: Dict[int, int] = field(default_factory=dict)
    most_actioned_users: Dict[int, int] = field(default_factory=dict)


class AnalyticsEngine:
    """Generates moderation analytics and reports."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._action_log: List[Dict[str, Any]] = []
    
    def log_action(
        self,
        guild_id: int,
        action_type: str,
        moderator_id: int,
        target_id: Optional[int] = None,
        source: str = "manual",
    ):
        """Log a moderation action for analytics."""
        self._action_log.append({
            "timestamp": datetime.now(timezone.utc),
            "guild_id": guild_id,
            "action_type": action_type,
            "moderator_id": moderator_id,
            "target_id": target_id,
            "source": source,
        })
        
        # Keep only last 10000 entries
        if len(self._action_log) > 10000:
            self._action_log = self._action_log[-10000:]
    
    def get_stats(
        self,
        guild_id: int,
        period_hours: int = 24,
    ) -> ModerationStats:
        """Get moderation statistics for a period."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=period_hours)
        
        stats = ModerationStats(period_start=start, period_end=now)
        
        for entry in self._action_log:
            if entry["guild_id"] != guild_id:
                continue
            if entry["timestamp"] < start:
                continue
            
            stats.total_actions += 1
            action = entry["action_type"].lower()
            
            if "warn" in action:
                stats.warnings += 1
            elif "timeout" in action or "mute" in action:
                stats.timeouts += 1
            elif "kick" in action:
                stats.kicks += 1
            elif "ban" in action and "unban" not in action:
                stats.bans += 1
            elif "unban" in action:
                stats.unbans += 1
            elif "purge" in action:
                stats.purges += 1
            
            if entry["source"] == "automod":
                stats.automod_actions += 1
            elif entry["source"] == "ai":
                stats.ai_actions += 1
            
            # Track moderator activity
            mod_id = entry["moderator_id"]
            stats.most_active_moderators[mod_id] = stats.most_active_moderators.get(mod_id, 0) + 1
            
            # Track user actions
            target_id = entry.get("target_id")
            if target_id:
                stats.most_actioned_users[target_id] = stats.most_actioned_users.get(target_id, 0) + 1
        
        return stats
    
    def generate_report_embed(self, stats: ModerationStats) -> discord.Embed:
        """Generate a report embed from stats."""
        embed = discord.Embed(
            title="📊 Moderation Report",
            description=f"Period: {stats.period_start.strftime('%Y-%m-%d %H:%M')} to {stats.period_end.strftime('%Y-%m-%d %H:%M')} UTC",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc),
        )
        
        embed.add_field(
            name="Total Actions",
            value=str(stats.total_actions),
            inline=True,
        )
        
        actions_breakdown = (
            f"⚠️ Warnings: {stats.warnings}\n"
            f"🔇 Timeouts: {stats.timeouts}\n"
            f"👢 Kicks: {stats.kicks}\n"
            f"🔨 Bans: {stats.bans}\n"
            f"✅ Unbans: {stats.unbans}\n"
            f"🗑️ Purges: {stats.purges}"
        )
        embed.add_field(
            name="Breakdown",
            value=actions_breakdown,
            inline=True,
        )
        
        source_info = (
            f"🤖 AI Actions: {stats.ai_actions}\n"
            f"⚡ AutoMod: {stats.automod_actions}\n"
            f"👤 Manual: {stats.total_actions - stats.ai_actions - stats.automod_actions}"
        )
        embed.add_field(
            name="Sources",
            value=source_info,
            inline=True,
        )
        
        # Top moderators
        if stats.most_active_moderators:
            top_mods = sorted(
                stats.most_active_moderators.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5]
            mods_text = "\n".join([f"<@{uid}>: {count}" for uid, count in top_mods])
            embed.add_field(
                name="Top Moderators",
                value=mods_text or "None",
                inline=False,
            )
        
        return embed


# ========= SUBSYSTEM INITIALIZATION =========
# All subsystems are initialized in the extended __init__ below


# Extend the AIModeration class with new commands
_orig_init = AIModeration.__init__

def _new_init(self, bot: commands.Bot):
    _orig_init(self, bot)
    # Add subsystems - use integration wrappers for AutoMod and AntiRaid
    self.automod_integration = AutoModIntegration(bot)
    self.antiraid_integration = AntiRaidIntegration(bot)
    self.content_analyzer = ContentAnalyzer(self.ai.client if hasattr(self, 'ai') else None)
    self.risk_scorer = RiskScorer(bot)
    self.scheduler = ActionScheduler(bot)
    self.appeal_system = AppealSystem(bot, self.ai.client if hasattr(self, 'ai') else None)
    self.analytics = AnalyticsEngine(bot)
    self.localization = LocalizationManager(bot)
    self.macro_engine = MacroEngine(bot)
    self.audit_logger = EnhancedAuditLogger(bot)
    self.scheduler.start()

AIModeration.__init__ = _new_init


# ========= NEW SLASH COMMANDS =========

@app_commands.command(name="riskcheck", description="Check a user's risk score")
@app_commands.describe(user="The user to check")
async def riskcheck(interaction: discord.Interaction, user: discord.Member):
    """Check a user's risk profile."""
    if not interaction.guild:
        return await interaction.response.send_message("Use this in a server.", ephemeral=True)
    
    cog: AIModeration = interaction.client.get_cog("AIModeration")
    if not cog:
        return await interaction.response.send_message("AI Moderation not loaded.", ephemeral=True)
    
    profile = await cog.risk_scorer.get_profile(user.id, interaction.guild.id)
    recommendations = await cog.risk_scorer.get_recommendations(profile)
    
    embed = discord.Embed(
        title=f"🔍 Risk Profile: {user}",
        color=discord.Color.orange() if profile.risk_score > 30 else discord.Color.green(),
    )
    embed.add_field(name="Risk Score", value=f"{profile.risk_score:.1f}/100", inline=True)
    embed.add_field(name="Risk Level", value=profile.risk_level, inline=True)
    embed.add_field(name="Warnings", value=str(profile.warning_count), inline=True)
    embed.add_field(name="Timeouts", value=str(profile.timeout_count), inline=True)
    embed.add_field(name="Kicks", value=str(profile.kick_count), inline=True)
    embed.add_field(name="AutoMod Flags", value=str(profile.automod_flags), inline=True)
    
    if recommendations:
        embed.add_field(
            name="Recommendations",
            value="\n".join(f"• {r}" for r in recommendations),
            inline=False,
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(name="modstats", description="View moderation statistics")
@app_commands.describe(hours="Time period in hours (default: 24)")
async def modstats(interaction: discord.Interaction, hours: int = 24):
    """View moderation statistics."""
    if not interaction.guild:
        return await interaction.response.send_message("Use this in a server.", ephemeral=True)
    
    cog: AIModeration = interaction.client.get_cog("AIModeration")
    if not cog:
        return await interaction.response.send_message("AI Moderation not loaded.", ephemeral=True)
    
    stats = cog.analytics.get_stats(interaction.guild.id, hours)
    embed = cog.analytics.generate_report_embed(stats)
    
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="lockdown", description="Enable/disable server lockdown")
@app_commands.describe(enable="Enable or disable lockdown")
async def lockdown(interaction: discord.Interaction, enable: bool):
    """Toggle server lockdown mode."""
    if not interaction.guild:
        return await interaction.response.send_message("Use this in a server.", ephemeral=True)
    
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Admin only.", ephemeral=True)
    
    cog: AIModeration = interaction.client.get_cog("AIModeration")
    if not cog:
        return await interaction.response.send_message("AI Moderation not loaded.", ephemeral=True)
    
    if enable:
        success = await cog.antiraid_integration.trigger_lockdown(interaction.guild, "Manual lockdown")
        msg = "🔒 Server is now in lockdown mode." if success else "Lockdown failed - AntiRaid cog may not be loaded."
    else:
        # Disabling lockdown - this would need to be added to the AntiRaid integration
        # For now, just inform the user to use the AntiRaid cog directly
        msg = "🔓 To disable lockdown, use the AntiRaid cog commands directly."
    
    await interaction.response.send_message(msg)


@app_commands.command(name="schedule", description="Schedule a delayed moderation action")
@app_commands.describe(
    action="Action to schedule",
    user="Target user",
    delay="Delay in minutes",
    reason="Reason for the action",
)
async def schedule_action(
    interaction: discord.Interaction,
    action: Literal["timeout", "untimeout", "kick", "ban", "unban"],
    user: discord.Member,
    delay: int,
    reason: str = "No reason provided",
):
    """Schedule a delayed moderation action."""
    if not interaction.guild:
        return await interaction.response.send_message("Use this in a server.", ephemeral=True)
    
    cog: AIModeration = interaction.client.get_cog("AIModeration")
    if not cog:
        return await interaction.response.send_message("AI Moderation not loaded.", ephemeral=True)
    
    scheduled = await cog.scheduler.schedule(
        guild_id=interaction.guild.id,
        user_id=user.id,
        action_type=action,
        delay_seconds=delay * 60,
        created_by=interaction.user.id,
        reason=reason,
    )
    
    embed = discord.Embed(
        title="⏰ Action Scheduled",
        description=f"**Action:** {action}\n**Target:** {user.mention}\n**In:** {delay} minutes\n**ID:** `{scheduled.id}`",
        color=discord.Color.blue(),
    )
    
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="analyze", description="AI analysis of a message or user")
@app_commands.describe(content="Message content or user mention to analyze")
async def analyze_content(interaction: discord.Interaction, content: str):
    """Analyze content using AI."""
    if not interaction.guild:
        return await interaction.response.send_message("Use this in a server.", ephemeral=True)
    
    cog: AIModeration = interaction.client.get_cog("AIModeration")
    if not cog:
        return await interaction.response.send_message("AI Moderation not loaded.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    
    result = await cog.content_analyzer.analyze(
        content=content,
        author=str(interaction.user),
    )
    
    if "error" in result:
        return await interaction.followup.send(f"Analysis failed: {result['error']}")
    
    embed = discord.Embed(
        title="🔬 Content Analysis",
        color=discord.Color.red() if result.get("toxicity_score", 0) > 0.5 else discord.Color.green(),
    )
    embed.add_field(name="Toxicity", value=f"{result.get('toxicity_score', 0):.0%}", inline=True)
    embed.add_field(name="Sentiment", value=result.get("sentiment", "unknown"), inline=True)
    embed.add_field(name="Intent", value=result.get("intent", "unknown"), inline=True)
    embed.add_field(name="Language", value=result.get("language", "unknown"), inline=True)
    embed.add_field(name="Contains PII", value="Yes" if result.get("contains_pii") else "No", inline=True)
    embed.add_field(name="Summary", value=result.get("summary", "N/A"), inline=False)
    
    await interaction.followup.send(embed=embed)


# Register new commands
async def setup(bot: commands.Bot):
    cog = AIModeration(bot)
    await bot.add_cog(cog)
    
    # Add new commands
    bot.tree.add_command(riskcheck)
    bot.tree.add_command(modstats)
    bot.tree.add_command(lockdown)
    bot.tree.add_command(schedule_action)
    bot.tree.add_command(analyze_content)


# ========= MULTI-LANGUAGE SUPPORT =========

class LanguageStrings:
    """Multi-language string definitions."""
    
    STRINGS = {
        "en": {
            "warn_dm": "You have been warned in **{guild}**.\nReason: {reason}",
            "timeout_dm": "You have been timed out in **{guild}** for {duration}.\nReason: {reason}",
            "kick_dm": "You have been kicked from **{guild}**.\nReason: {reason}",
            "ban_dm": "You have been banned from **{guild}**.\nReason: {reason}",
            "appeal_info": "To appeal, contact a moderator.",
            "action_success": "Action completed successfully.",
            "action_failed": "Action failed: {error}",
            "no_permission": "You don't have permission to do that.",
            "target_not_found": "Target user not found.",
            "hierarchy_error": "You cannot moderate this user due to role hierarchy.",
            "rate_limited": "You're doing that too fast. Wait {seconds} seconds.",
            "ai_thinking": "Let me think about that...",
            "ai_error": "I had trouble processing that request.",
        },
        "es": {
            "warn_dm": "Has recibido una advertencia en **{guild}**.\nRazón: {reason}",
            "timeout_dm": "Has sido silenciado en **{guild}** por {duration}.\nRazón: {reason}",
            "kick_dm": "Has sido expulsado de **{guild}**.\nRazón: {reason}",
            "ban_dm": "Has sido baneado de **{guild}**.\nRazón: {reason}",
            "appeal_info": "Para apelar, contacta a un moderador.",
            "action_success": "Acción completada exitosamente.",
            "action_failed": "Acción fallida: {error}",
            "no_permission": "No tienes permiso para hacer eso.",
            "target_not_found": "Usuario objetivo no encontrado.",
            "hierarchy_error": "No puedes moderar a este usuario por jerarquía de roles.",
            "rate_limited": "Estás haciendo eso muy rápido. Espera {seconds} segundos.",
            "ai_thinking": "Déjame pensar en eso...",
            "ai_error": "Tuve problemas procesando esa solicitud.",
        },
        "pt": {
            "warn_dm": "Você recebeu um aviso em **{guild}**.\nMotivo: {reason}",
            "timeout_dm": "Você foi silenciado em **{guild}** por {duration}.\nMotivo: {reason}",
            "kick_dm": "Você foi expulso de **{guild}**.\nMotivo: {reason}",
            "ban_dm": "Você foi banido de **{guild}**.\nMotivo: {reason}",
            "appeal_info": "Para apelar, contate um moderador.",
            "action_success": "Ação concluída com sucesso.",
            "action_failed": "Ação falhou: {error}",
            "no_permission": "Você não tem permissão para isso.",
            "target_not_found": "Usuário alvo não encontrado.",
            "hierarchy_error": "Você não pode moderar este usuário devido à hierarquia de cargos.",
            "rate_limited": "Você está fazendo isso muito rápido. Aguarde {seconds} segundos.",
            "ai_thinking": "Deixe-me pensar nisso...",
            "ai_error": "Tive problemas ao processar essa solicitação.",
        },
        "de": {
            "warn_dm": "Du wurdest in **{guild}** verwarnt.\nGrund: {reason}",
            "timeout_dm": "Du wurdest in **{guild}** für {duration} stummgeschaltet.\nGrund: {reason}",
            "kick_dm": "Du wurdest aus **{guild}** gekickt.\nGrund: {reason}",
            "ban_dm": "Du wurdest aus **{guild}** gebannt.\nGrund: {reason}",
            "appeal_info": "Um Einspruch einzulegen, kontaktiere einen Moderator.",
            "action_success": "Aktion erfolgreich abgeschlossen.",
            "action_failed": "Aktion fehlgeschlagen: {error}",
            "no_permission": "Du hast keine Berechtigung dafür.",
            "target_not_found": "Zielbenutzer nicht gefunden.",
            "hierarchy_error": "Du kannst diesen Benutzer aufgrund der Rollenhierarchie nicht moderieren.",
            "rate_limited": "Du machst das zu schnell. Warte {seconds} Sekunden.",
            "ai_thinking": "Lass mich darüber nachdenken...",
            "ai_error": "Ich hatte Probleme bei der Verarbeitung dieser Anfrage.",
        },
        "fr": {
            "warn_dm": "Vous avez reçu un avertissement dans **{guild}**.\nRaison: {reason}",
            "timeout_dm": "Vous avez été mis en sourdine dans **{guild}** pour {duration}.\nRaison: {reason}",
            "kick_dm": "Vous avez été expulsé de **{guild}**.\nRaison: {reason}",
            "ban_dm": "Vous avez été banni de **{guild}**.\nRaison: {reason}",
            "appeal_info": "Pour faire appel, contactez un modérateur.",
            "action_success": "Action terminée avec succès.",
            "action_failed": "Action échouée: {error}",
            "no_permission": "Vous n'avez pas la permission de faire cela.",
            "target_not_found": "Utilisateur cible non trouvé.",
            "hierarchy_error": "Vous ne pouvez pas modérer cet utilisateur en raison de la hiérarchie des rôles.",
            "rate_limited": "Vous faites cela trop vite. Attendez {seconds} secondes.",
            "ai_thinking": "Laisse-moi réfléchir à ça...",
            "ai_error": "J'ai eu du mal à traiter cette demande.",
        },
    }
    
    @classmethod
    def get(cls, lang: str, key: str, **kwargs) -> str:
        """Get a localized string."""
        strings = cls.STRINGS.get(lang, cls.STRINGS["en"])
        template = strings.get(key, cls.STRINGS["en"].get(key, key))
        try:
            return template.format(**kwargs)
        except KeyError:
            return template


class LocalizationManager:
    """Manages per-guild language settings."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._guild_langs: Dict[int, str] = {}
    
    async def get_lang(self, guild_id: int) -> str:
        """Get the language for a guild."""
        if guild_id not in self._guild_langs:
            try:
                settings = await self.bot.db.get_settings(guild_id)
                self._guild_langs[guild_id] = settings.get("aimod_language", "en")
            except Exception:
                self._guild_langs[guild_id] = "en"
        return self._guild_langs[guild_id]
    
    async def set_lang(self, guild_id: int, lang: str) -> bool:
        """Set the language for a guild."""
        if lang not in LanguageStrings.STRINGS:
            return False
        
        self._guild_langs[guild_id] = lang
        try:
            await self.bot.db.set_setting(guild_id, "aimod_language", lang)
        except Exception:
            pass
        return True
    
    async def localize(self, guild_id: int, key: str, **kwargs) -> str:
        """Get a localized string for a guild."""
        lang = await self.get_lang(guild_id)
        return LanguageStrings.get(lang, key, **kwargs)


# ========= CUSTOM ACTION MACROS =========

@dataclass
class ActionMacro:
    """A custom action macro that combines multiple actions."""
    id: str
    guild_id: int
    name: str
    description: str
    created_by: int
    actions: List[Dict[str, Any]]  # List of action definitions
    trigger_words: List[str] = field(default_factory=list)
    cooldown_seconds: int = 0
    last_used: Optional[datetime] = None
    use_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "actions": self.actions,
            "trigger_words": self.trigger_words,
            "cooldown_seconds": self.cooldown_seconds,
            "use_count": self.use_count,
        }


class MacroEngine:
    """Manages and executes custom action macros."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._macros: Dict[str, ActionMacro] = {}
        self._guild_macros: Dict[int, List[str]] = {}
    
    async def create_macro(
        self,
        guild_id: int,
        name: str,
        description: str,
        actions: List[Dict[str, Any]],
        created_by: int,
        trigger_words: List[str] = None,
    ) -> ActionMacro:
        """Create a new action macro."""
        import uuid
        macro = ActionMacro(
            id=str(uuid.uuid4())[:8],
            guild_id=guild_id,
            name=name,
            description=description,
            created_by=created_by,
            actions=actions,
            trigger_words=trigger_words or [],
        )
        
        self._macros[macro.id] = macro
        
        if guild_id not in self._guild_macros:
            self._guild_macros[guild_id] = []
        self._guild_macros[guild_id].append(macro.id)
        
        return macro
    
    async def delete_macro(self, macro_id: str) -> bool:
        """Delete a macro."""
        if macro_id not in self._macros:
            return False
        
        macro = self._macros[macro_id]
        if macro.guild_id in self._guild_macros:
            self._guild_macros[macro.guild_id].remove(macro_id)
        del self._macros[macro_id]
        return True
    
    def get_macro(self, macro_id: str) -> Optional[ActionMacro]:
        """Get a macro by ID."""
        return self._macros.get(macro_id)
    
    def list_macros(self, guild_id: int) -> List[ActionMacro]:
        """List all macros for a guild."""
        macro_ids = self._guild_macros.get(guild_id, [])
        return [self._macros[mid] for mid in macro_ids if mid in self._macros]
    
    async def execute_macro(
        self,
        macro_id: str,
        message: discord.Message,
        target: discord.Member,
        reason: str = "Macro execution",
    ) -> Dict[str, Any]:
        """Execute a macro's actions."""
        macro = self.get_macro(macro_id)
        if not macro:
            return {"success": False, "error": "Macro not found"}
        
        # Check cooldown
        if macro.cooldown_seconds > 0 and macro.last_used:
            elapsed = (datetime.now(timezone.utc) - macro.last_used).total_seconds()
            if elapsed < macro.cooldown_seconds:
                return {"success": False, "error": f"Cooldown: {int(macro.cooldown_seconds - elapsed)}s remaining"}
        
        results = {"success": True, "actions_executed": 0, "actions_failed": 0}
        
        for action_def in macro.actions:
            try:
                action_type = action_def.get("type")
                
                if action_type == "warn":
                    await self.bot.db.add_warning(
                        message.guild.id,
                        target.id,
                        message.author.id,
                        action_def.get("reason", reason),
                    )
                elif action_type == "timeout":
                    duration = action_def.get("duration", 3600)
                    until = datetime.now(timezone.utc) + timedelta(seconds=duration)
                    await target.timeout(until, reason=f"[Macro] {reason}")
                elif action_type == "kick":
                    await target.kick(reason=f"[Macro] {reason}")
                elif action_type == "ban":
                    await message.guild.ban(target, reason=f"[Macro] {reason}")
                elif action_type == "dm":
                    try:
                        await target.send(action_def.get("message", reason))
                    except discord.Forbidden:
                        pass
                elif action_type == "reply":
                    await message.reply(action_def.get("message", "Action executed."))
                
                results["actions_executed"] += 1
                
            except Exception as e:
                logger.error(f"Macro action failed: {e}")
                results["actions_failed"] += 1
        
        macro.last_used = datetime.now(timezone.utc)
        macro.use_count += 1
        
        return results


# ========= ENHANCED AUDIT LOGGING =========

@dataclass
class AuditLogEntry:
    """An enhanced audit log entry."""
    id: str
    guild_id: int
    action_type: str
    actor_id: int
    target_id: Optional[int]
    reason: str
    timestamp: datetime
    source: str  # "manual", "ai", "automod", "scheduled", "macro"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_embed(self) -> discord.Embed:
        """Convert to a Discord embed."""
        color_map = {
            "warn": discord.Color.yellow(),
            "timeout": discord.Color.orange(),
            "kick": discord.Color.red(),
            "ban": discord.Color.dark_red(),
            "unban": discord.Color.green(),
            "purge": discord.Color.blue(),
        }
        
        embed = discord.Embed(
            title=f"📋 {self.action_type.upper()}",
            description=self.reason,
            color=color_map.get(self.action_type.lower(), discord.Color.greyple()),
            timestamp=self.timestamp,
        )
        
        embed.add_field(name="Actor", value=f"<@{self.actor_id}>", inline=True)
        if self.target_id:
            embed.add_field(name="Target", value=f"<@{self.target_id}>", inline=True)
        embed.add_field(name="Source", value=self.source.title(), inline=True)
        
        if self.metadata:
            meta_str = "\n".join([f"**{k}:** {v}" for k, v in self.metadata.items()])
            embed.add_field(name="Details", value=meta_str[:1024], inline=False)
        
        embed.set_footer(text=f"ID: {self.id}")
        
        return embed


class EnhancedAuditLogger:
    """Enhanced audit logging with search and export capabilities."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._entries: Dict[str, AuditLogEntry] = {}
        self._guild_entries: Dict[int, List[str]] = {}
    
    async def log(
        self,
        guild_id: int,
        action_type: str,
        actor_id: int,
        target_id: Optional[int] = None,
        reason: str = "No reason",
        source: str = "manual",
        metadata: Dict[str, Any] = None,
    ) -> AuditLogEntry:
        """Create a new audit log entry."""
        import uuid
        entry = AuditLogEntry(
            id=str(uuid.uuid4())[:12],
            guild_id=guild_id,
            action_type=action_type,
            actor_id=actor_id,
            target_id=target_id,
            reason=reason,
            timestamp=datetime.now(timezone.utc),
            source=source,
            metadata=metadata or {},
        )
        
        self._entries[entry.id] = entry
        
        if guild_id not in self._guild_entries:
            self._guild_entries[guild_id] = []
        self._guild_entries[guild_id].append(entry.id)
        
        # Keep only last 1000 entries per guild
        if len(self._guild_entries[guild_id]) > 1000:
            old_id = self._guild_entries[guild_id].pop(0)
            if old_id in self._entries:
                del self._entries[old_id]
        
        # Try to send to log channel
        await self._send_to_log_channel(entry)
        
        return entry
    
    async def _send_to_log_channel(self, entry: AuditLogEntry):
        """Send an entry to the guild's log channel."""
        try:
            logging_cog = self.bot.get_cog("Logging")
            if not logging_cog:
                return
            
            guild = self.bot.get_guild(entry.guild_id)
            if not guild:
                return
            
            channel = await logging_cog.get_log_channel(guild, "automod")
            if channel:
                await logging_cog.safe_send_log(channel, entry.to_embed())
        except Exception as e:
            logger.error(f"Failed to send audit log: {e}")
    
    def search(
        self,
        guild_id: int,
        action_type: Optional[str] = None,
        actor_id: Optional[int] = None,
        target_id: Optional[int] = None,
        source: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuditLogEntry]:
        """Search audit log entries."""
        entry_ids = self._guild_entries.get(guild_id, [])
        results = []
        
        for eid in reversed(entry_ids):  # Most recent first
            if len(results) >= limit:
                break
            
            entry = self._entries.get(eid)
            if not entry:
                continue
            
            if action_type and entry.action_type.lower() != action_type.lower():
                continue
            if actor_id and entry.actor_id != actor_id:
                continue
            if target_id and entry.target_id != target_id:
                continue
            if source and entry.source.lower() != source.lower():
                continue
            
            results.append(entry)
        
        return results
    
    def export_csv(self, guild_id: int, limit: int = 100) -> str:
        """Export audit log to CSV format."""
        entries = self.search(guild_id, limit=limit)
        
        lines = ["id,timestamp,action,actor_id,target_id,reason,source"]
        for entry in entries:
            reason_escaped = entry.reason.replace('"', '""')
            lines.append(
                f'{entry.id},{entry.timestamp.isoformat()},{entry.action_type},'
                f'{entry.actor_id},{entry.target_id or ""},"{reason_escaped}",{entry.source}'
            )
        
        return "\n".join(lines)


# ========= ADDITIONAL SLASH COMMANDS (Standalone for tree registration) =========

@app_commands.command(name="setlang", description="Set the bot's language for this server")
@app_commands.describe(language="Language code (en, es, pt, de, fr)")
@app_commands.checks.has_permissions(administrator=True)
async def set_language(interaction: discord.Interaction, language: str):
    """Set the server's language."""
    cog: AIModeration = interaction.client.get_cog("AIModeration")
    if not cog or not hasattr(cog, "localization"):
        return await interaction.response.send_message("Feature not available.", ephemeral=True)
    
    if language not in LanguageStrings.STRINGS:
        langs = ", ".join(LanguageStrings.STRINGS.keys())
        return await interaction.response.send_message(f"Available languages: {langs}", ephemeral=True)
    
    await cog.localization.set_lang(interaction.guild_id, language)
    await interaction.response.send_message(f"Language set to: {language}")


@app_commands.command(name="macro", description="Manage action macros")
@app_commands.describe(action="Action to perform", name="Macro name")
async def macro_command(
    interaction: discord.Interaction,
    action: Literal["list", "create", "delete", "run"],
    name: Optional[str] = None,
):
    """Manage action macros."""
    cog: AIModeration = interaction.client.get_cog("AIModeration")
    if not cog or not hasattr(cog, "macro_engine"):
        return await interaction.response.send_message("Feature not available.", ephemeral=True)
    
    if action == "list":
        macros = cog.macro_engine.list_macros(interaction.guild_id)
        if not macros:
            return await interaction.response.send_message("No macros configured.", ephemeral=True)
        
        embed = discord.Embed(title="📜 Action Macros", color=discord.Color.blue())
        for m in macros[:10]:
            embed.add_field(
                name=f"{m.name} (`{m.id}`)",
                value=f"{m.description}\nUsed: {m.use_count} times",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    elif action == "delete" and name:
        success = await cog.macro_engine.delete_macro(name)
        msg = "Macro deleted." if success else "Macro not found."
        await interaction.response.send_message(msg, ephemeral=True)
    
    else:
        await interaction.response.send_message("Use /macro list, /macro delete <id>", ephemeral=True)


@app_commands.command(name="auditlog", description="Search the moderation audit log")
@app_commands.describe(
    action_type="Filter by action type",
    user="Filter by actor or target",
    limit="Maximum results (default 10)",
)
async def audit_log_search(
    interaction: discord.Interaction,
    action_type: Optional[str] = None,
    user: Optional[discord.Member] = None,
    limit: int = 10,
):
    """Search the audit log."""
    cog: AIModeration = interaction.client.get_cog("AIModeration")
    if not cog or not hasattr(cog, "audit_logger"):
        return await interaction.response.send_message("Feature not available.", ephemeral=True)
    
    entries = cog.audit_logger.search(
        guild_id=interaction.guild_id,
        action_type=action_type,
        target_id=user.id if user else None,
        limit=min(limit, 25),
    )
    
    if not entries:
        return await interaction.response.send_message("No entries found.", ephemeral=True)
    
    embed = discord.Embed(
        title="📋 Audit Log Results",
        description=f"Found {len(entries)} entries",
        color=discord.Color.blue(),
    )
    
    for entry in entries[:10]:
        embed.add_field(
            name=f"{entry.action_type.upper()} - {entry.timestamp.strftime('%m/%d %H:%M')}",
            value=f"Actor: <@{entry.actor_id}> | Target: <@{entry.target_id}>\n{entry.reason[:100]}",
            inline=False,
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ========= PROPER SETUP FUNCTION =========

async def setup(bot: commands.Bot):
    """Load the AIModeration cog and register additional commands."""
    # Add the main cog
    await bot.add_cog(AIModeration(bot))
    
    # Register standalone slash commands
    bot.tree.add_command(set_language)
    bot.tree.add_command(macro_command)
    bot.tree.add_command(audit_log_search)
    
    logger.info("AIModeration cog loaded successfully")

