"""
AutoMod - Automatic moderation features with Groq AI

Features:
- Rule-based filters (badwords, links, invites, spam, caps, mentions, new accounts)
- Groq AI content analysis for context-aware moderation
- Configurable punishments & durations
- Per-guild AI toggles and sensitivity
"""

import os
import re
import json
import asyncio
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal, Dict, Any, List

import discord
from discord import app_commands
from discord.ext import commands

from groq import Groq  # pip install groq

from utils.embeds import ModEmbed
from utils.logging import send_log_embed
from utils.checks import is_admin, is_mod, is_bot_owner_id
from utils.time_parser import parse_time
from config import Config


# =========================
# AI Moderation Helper
# =========================

class AIModerationHelper:
    """
    Thin wrapper around Groq for:
    - message content classification (toxicity, spam, etc.)
    - caching and basic rate limiting
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.client: Optional[Groq] = None
        if self.api_key:
            self.client = Groq(api_key=self.api_key)

        self.analysis_cache: Dict[str, tuple[dict, datetime]] = {}
        self.rate_limit_tracker: Dict[str, List[datetime]] = defaultdict(list)

        # config
        self.cache_ttl_seconds = 300
        self.max_requests_per_minute = 25
        self.model = "llama-3.3-70b-versatile"

    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _within_rate_limit(self) -> bool:
        now = datetime.now(timezone.utc)
        window = timedelta(seconds=60)
        events = [
            t for t in self.rate_limit_tracker["requests"]
            if now - t < window
        ]
        self.rate_limit_tracker["requests"] = events
        return len(events) < self.max_requests_per_minute

    def _record_request(self) -> None:
        self.rate_limit_tracker["requests"].append(datetime.now(timezone.utc))

    def _get_cached(self, content: str) -> Optional[dict]:
        h = self._hash_content(content)
        if h not in self.analysis_cache:
            return None
        data, ts = self.analysis_cache[h]
        if (datetime.now(timezone.utc) - ts).total_seconds() > self.cache_ttl_seconds:
            del self.analysis_cache[h]
            return None
        return data

    def _set_cache(self, content: str, result: dict) -> None:
        h = self._hash_content(content)
        self.analysis_cache[h] = (result, datetime.now(timezone.utc))

    async def analyze_message(
        self,
        content: str,
        context: Dict[str, Any],
    ) -> dict:
        """
        Returns a dict like:
        {
            "is_violation": bool,
            "category": "toxicity|spam|nsfw|threat|other",
            "severity": 1-10,
            "reason": str
        }
        """
        # no api key / client -> no ai
        if not self.client:
            return {"is_violation": False, "reason": "no_groq_client"}

        # try cache first
        cached = self._get_cached(content)
        if cached is not None:
            return cached

        # rudimentary rate limit
        if not self._within_rate_limit():
            return {"is_violation": False, "reason": "rate_limited"}

        prompt = f"""
You are a strict Discord moderation classifier.

Message:
\"\"\"{content}\"\"\"

Context (JSON):
{json.dumps(context, ensure_ascii=False)}

Decide if the message violates server rules.

Categories:
- toxicity: insults, harassment, slurs
- spam: repetitive, scam, or promotion
- nsfw: sexual content, porn, sexualized minors (ALWAYS max severity)
- threat: self-harm, threats of violence, doxxing
- other: anything else clearly against ToS

Respond ONLY with a JSON object like:
{{
  "is_violation": bool,
  "category": "toxicity|spam|nsfw|threat|other|none",
  "severity": 1-10,
  "reason": "short human explanation"
}}
"""

        def _call():
            return self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )

        try:
            completion = await asyncio.to_thread(_call)
            self._record_request()
            raw = completion.choices[0].message.content.strip()

            # try parse JSON (be forgiving)
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1:
                return {"is_violation": False, "reason": "parse_error"}

            data = json.loads(raw[start : end + 1])

            # minimal sane defaults
            result = {
                "is_violation": bool(data.get("is_violation")),
                "category": str(data.get("category", "none")),
                "severity": int(data.get("severity", 1)),
                "reason": str(data.get("reason", "no reason provided"))[:300],
            }

            self._set_cache(content, result)
            return result

        except Exception as e:
            print(f"[Groq AutoMod] error: {e}")
            return {"is_violation": False, "reason": "exception"}


# =========================
# AutoMod Cog
# =========================

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_tracker: Dict[tuple, List[datetime]] = defaultdict(list)
        self.spam_cooldown: set[tuple] = set()
        self.ai_helper = AIModerationHelper()

    # ---------- helper: logging ----------

    async def log_automod(self, guild: discord.Guild, embed: discord.Embed):
        settings = await self.bot.db.get_settings(guild.id)
        log_id = settings.get("automod_log_channel")
        if not log_id:
            return
        channel = guild.get_channel(log_id)
        if not channel:
            return
        try:
            await send_log_embed(channel, embed)
        except Exception:
            pass

    # ---------- helper: punishment ----------

    async def apply_punishment(
        self,
        user: discord.Member,
        guild: discord.Guild,
        punishment: str,
        reason: str,
        settings: dict,
    ) -> str:
        mute_duration = settings.get("automod_mute_duration", 3600)
        ban_duration = settings.get("automod_ban_duration", 0)
        spam_timeout = settings.get("automod_spam_timeout", 60)

        if punishment == "warn":
            await self.bot.db.add_warning(
                guild.id,
                user.id,
                self.bot.user.id,
                f"[AutoMod] {reason}",
            )
            return "Warning issued"

        if punishment == "mute":
            try:
                duration = timedelta(seconds=mute_duration)
                await user.timeout(duration, reason=f"[AutoMod] {reason}")
                return f"Muted for {self.format_duration(mute_duration)}"
            except Exception:
                return "Mute failed"

        if punishment == "kick":
            try:
                await user.kick(reason=f"[AutoMod] {reason}")
                return "Kicked"
            except Exception:
                return "Kick failed"

        if punishment == "ban":
            try:
                if ban_duration > 0:
                    await user.ban(
                        reason=f"[AutoMod] {reason}",
                        delete_message_days=1,
                    )
                    expires_at = datetime.now(timezone.utc) + timedelta(
                        seconds=ban_duration
                    )
                    await self.bot.db.add_tempban(
                        guild.id,
                        user.id,
                        self.bot.user.id,
                        reason,
                        expires_at,
                    )
                    return f"Banned for {self.format_duration(ban_duration)}"
                else:
                    await user.ban(
                        reason=f"[AutoMod] {reason}",
                        delete_message_days=1,
                    )
                    return "Permanently banned"
            except Exception:
                return "Ban failed"

        return "No action"

    def format_duration(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds} seconds"
        if seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        if seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''}"
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''}"

    async def take_action(
        self,
        message: discord.Message,
        reason: str,
        settings: dict,
        override_punishment: Optional[str] = None,
    ):
        punishment = override_punishment or settings.get("automod_punishment", "warn")
        user = message.author
        guild = message.guild

        try:
            await message.delete()
        except Exception:
            pass

        result = await self.apply_punishment(user, guild, punishment, reason, settings)

        embed = discord.Embed(
            title="🤖 AutoMod Action",
            color=Config.COLOR_WARNING,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(
            name="User", value=f"{user.mention} ({user.id})", inline=True
        )
        embed.add_field(name="Action", value=result, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(
            name="Channel", value=message.channel.mention, inline=True
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        await self.log_automod(guild, embed)

        try:
            notify_embed = discord.Embed(
                title=f"⚠️ AutoMod Alert in {guild.name}",
                description=(
                    "Your message was flagged and removed.\n"
                    f"**Reason:** {reason}\n"
                    f"**Action:** {result}"
                ),
                color=Config.COLOR_WARNING,
            )
            await user.send(embed=notify_embed)
        except Exception:
            pass

    # =========================
    # MESSAGE LISTENER
    # =========================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        if is_bot_owner_id(message.author.id):
            return

        if message.author.guild_permissions.manage_messages:
            return

        settings = await self.bot.db.get_settings(message.guild.id)
        if not settings.get("automod_enabled", False):
            return

        if message.channel.id in settings.get("ignored_channels", []):
            return

        user_role_ids = [r.id for r in message.author.roles]
        if any(r in settings.get("ignored_roles", []) for r in user_role_ids):
            return

        content = message.content or ""
        lowered = content.lower()

        # ---------- AI pre-pass (optional) ----------

        if settings.get("automod_ai_enabled", False) and content.strip():
            # build some lightweight context
            account_age_days = (
                datetime.now(timezone.utc) - message.author.created_at
            ).days
            join_age_days = (
                (datetime.now(timezone.utc) - message.author.joined_at).days
                if message.author.joined_at
                else 0
            )

            context = {
                "account_age_days": account_age_days,
                "join_age_days": join_age_days,
                "channel": message.channel.name,
                "guild_size": message.guild.member_count,
            }

            ai_result = await self.ai_helper.analyze_message(content, context)

            if ai_result.get("is_violation"):
                # respect per-guild severity floor / category filter
                min_sev = settings.get("automod_ai_min_severity", 4)
                allowed_categories = settings.get(
                    "automod_ai_categories",
                    ["toxicity", "spam", "nsfw", "threat", "other"],
                )

                if (
                    ai_result.get("severity", 1) >= min_sev
                    and ai_result.get("category") in allowed_categories
                ):
                    category = ai_result.get("category", "other")
                    severity = ai_result.get("severity", 1)
                    ai_reason = ai_result.get("reason", "AI violation")

                    # dynamic punishment scaling
                    punishment = settings.get("automod_punishment", "warn")

                    if category == "nsfw" or severity >= 9:
                        punishment = "ban"
                    elif severity >= 7 and punishment in ("warn", "mute"):
                        punishment = "mute"
                    elif severity <= 3:
                        punishment = "warn"

                    await self.take_action(
                        message,
                        f"[AI-{category.upper()} S{severity}] {ai_reason}",
                        settings,
                        override_punishment=punishment,
                    )
                    return

        # ---------- BAD WORDS FILTER ----------

        badwords = settings.get("automod_badwords", [])
        if badwords:
            for word in badwords:
                w = word.lower()
                if not w:
                    continue
                if w in lowered:
                    await self.take_action(
                        message,
                        "Blacklisted word detected",
                        settings,
                    )
                    return

        # ---------- LINK FILTER ----------

        if settings.get("automod_links_enabled", False):
            url_pattern = re.compile(r"https?://\S+")
            urls = url_pattern.findall(content)
            if urls:
                whitelist = settings.get("automod_links_whitelist", [])
                allowed = True
                for url in urls:
                    if not any(domain in url for domain in whitelist):
                        allowed = False
                        break
                if not allowed:
                    await self.take_action(
                        message,
                        "Unauthorized link posted",
                        settings,
                    )
                    return

        # ---------- DISCORD INVITE FILTER ----------

        if settings.get("automod_invites_enabled", False):
            invite_pattern = re.compile(
                r"(discord\.gg|discord\.com/invite|discordapp\.com/invite)/\S+"
            )
            if invite_pattern.search(content):
                await self.take_action(
                    message,
                    "Discord invite link",
                    settings,
                )
                return

        # ---------- SPAM FILTER ----------

        spam_threshold = settings.get("automod_spam_threshold", 5)
        if spam_threshold > 0:
            now = datetime.now(timezone.utc)
            key = (message.guild.id, message.author.id, message.channel.id)

            if key in self.spam_cooldown:
                try:
                    await message.delete()
                except Exception:
                    pass
                return

            self.spam_tracker[key] = [
                t for t in self.spam_tracker[key] if (now - t).total_seconds() < 5
            ]
            self.spam_tracker[key].append(now)

            if len(self.spam_tracker[key]) >= spam_threshold:
                self.spam_cooldown.add(key)
                user = message.author
                guild = message.guild
                channel = message.channel
                punishment = settings.get("automod_punishment", "warn")
                spam_timeout = settings.get("automod_spam_timeout", 60)

                self.spam_tracker[key] = []
                deleted_count = 0

                try:
                    messages_to_delete = []
                    async for msg in channel.history(limit=100):
                        if msg.author.id == user.id:
                            msg_age = (
                                now
                                - msg.created_at.replace(tzinfo=timezone.utc)
                            ).total_seconds()
                            if msg_age < 60:
                                messages_to_delete.append(msg)
                        if len(messages_to_delete) >= 50:
                            break

                    if messages_to_delete:
                        if len(messages_to_delete) == 1:
                            await messages_to_delete[0].delete()
                            deleted_count = 1
                        else:
                            await channel.delete_messages(messages_to_delete)
                            deleted_count = len(messages_to_delete)
                except discord.Forbidden:
                    print(f"[AutoMod] No permission to delete messages in {channel}")
                except discord.HTTPException as e:
                    print(f"[AutoMod] HTTP error deleting messages: {e}")
                except Exception as e:
                    print(f"[AutoMod] Error deleting messages: {e}")

                timeout_result = ""
                if spam_timeout > 0:
                    try:
                        await user.timeout(
                            timedelta(seconds=spam_timeout),
                            reason="[AutoMod] Spam detected",
                        )
                        timeout_result = f" + {self.format_duration(spam_timeout)} timeout"
                    except Exception as e:
                        print(f"[AutoMod] Could not timeout user: {e}")

                punishment_result = await self.apply_punishment(
                    user,
                    guild,
                    punishment,
                    "Spam detected",
                    settings,
                )

                embed = discord.Embed(
                    title="🤖 AutoMod Action - Spam Detected",
                    color=Config.COLOR_WARNING,
                    timestamp=datetime.now(timezone.utc),
                )
                embed.add_field(
                    name="User",
                    value=f"{user.mention} ({user.id})",
                    inline=True,
                )
                embed.add_field(
                    name="Action",
                    value=f"{punishment_result}{timeout_result}",
                    inline=True,
                )
                embed.add_field(
                    name="Reason",
                    value="Spam detected",
                    inline=False,
                )
                embed.add_field(
                    name="Channel",
                    value=channel.mention,
                    inline=True,
                )
                embed.add_field(
                    name="Messages Deleted",
                    value=str(deleted_count),
                    inline=True,
                )
                embed.set_thumbnail(url=user.display_avatar.url)
                await self.log_automod(guild, embed)

                try:
                    notify_embed = discord.Embed(
                        title=f"⚠️ AutoMod Alert in {guild.name}",
                        description=(
                            "You were detected spamming.\n"
                            f"**Messages Deleted:** {deleted_count}\n"
                            f"**Action:** {punishment_result}{timeout_result}"
                        ),
                        color=Config.COLOR_WARNING,
                    )
                    await user.send(embed=notify_embed)
                except Exception:
                    pass

                async def _cooldown_clear():
                    await asyncio.sleep(10)
                    self.spam_cooldown.discard(key)

                asyncio.create_task(_cooldown_clear())
                return

        # ---------- CAPS FILTER ----------

        caps_percentage = settings.get("automod_caps_percentage", 70)
        if caps_percentage > 0 and len(content) > 10:
            alpha_chars = [c for c in content if c.isalpha()]
            if alpha_chars:
                caps_ratio = (
                    sum(1 for c in alpha_chars if c.isupper())
                    / len(alpha_chars)
                    * 100
                )
                if caps_ratio >= caps_percentage:
                    await self.take_action(
                        message,
                        "Excessive caps",
                        settings,
                    )
                    return

        # ---------- MASS MENTIONS FILTER ----------

        max_mentions = settings.get("automod_max_mentions", 5)
        if max_mentions > 0:
            total_mentions = len(message.mentions) + len(message.role_mentions)
            if total_mentions >= max_mentions:
                await self.take_action(
                    message,
                    f"Mass mentions ({total_mentions})",
                    settings,
                )
                return

        # ---------- NEW ACCOUNT ALERT ----------

        account_age_days = settings.get("automod_newaccount_days", 0)
        if account_age_days > 0:
            age = (datetime.now(timezone.utc) - message.author.created_at).days
            if age < account_age_days:
                embed = discord.Embed(
                    title="⚠️ New Account Alert",
                    description=(
                        f"{message.author.mention} has a new account "
                        f"({age} days old)"
                    ),
                    color=Config.COLOR_WARNING,
                )
                embed.add_field(
                    name="Message",
                    value=content[:500] or "*no content*",
                    inline=False,
                )
                await self.log_automod(message.guild, embed)

    # =========================
    # SLASH COMMANDS
    # =========================

    automod_group = app_commands.Group(
        name="automod",
        description="AutoMod configuration commands",
    )

    # --- basic enable/disable/status ---

    @automod_group.command(name="enable", description="Enable AutoMod")
    @is_admin()
    async def automod_enable(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["automod_enabled"] = True
        await self.bot.db.update_settings(interaction.guild_id, settings)
        embed = ModEmbed.success(
            "AutoMod Enabled",
            "AutoMod is now active on this server.",
        )
        await interaction.response.send_message(embed=embed)

    @automod_group.command(name="disable", description="Disable AutoMod")
    @is_admin()
    async def automod_disable(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["automod_enabled"] = False
        await self.bot.db.update_settings(interaction.guild_id, settings)
        embed = ModEmbed.success(
            "AutoMod Disabled",
            "AutoMod is now disabled.",
        )
        await interaction.response.send_message(embed=embed)

    @automod_group.command(name="status", description="View AutoMod status and settings")
    @is_mod()
    async def automod_status(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        embed = discord.Embed(
            title="🤖 AutoMod Status",
            color=Config.COLOR_INFO,
        )
        status = "🟢 Enabled" if settings.get("automod_enabled") else "🔴 Disabled"
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(
            name="Punishment",
            value=settings.get("automod_punishment", "warn").title(),
            inline=True,
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        mute_dur = settings.get("automod_mute_duration", 3600)
        ban_dur = settings.get("automod_ban_duration", 0)
        spam_timeout = settings.get("automod_spam_timeout", 60)
        embed.add_field(
            name="⏱️ Durations",
            value=(
                f"**Mute Duration:** {self.format_duration(mute_dur)}\n"
                f"**Ban Duration:** {'Permanent' if ban_dur == 0 else self.format_duration(ban_dur)}\n"
                f"**Spam Timeout:** {self.format_duration(spam_timeout)}"
            ),
            inline=False,
        )

        filters = []
        if settings.get("automod_badwords"):
            filters.append(f"📝 Bad Words ({len(settings['automod_badwords'])} words)")
        if settings.get("automod_links_enabled"):
            filters.append("🔗 Link Filter")
        if settings.get("automod_invites_enabled"):
            filters.append("📨 Invite Filter")
        if settings.get("automod_spam_threshold", 0) > 0:
            filters.append(
                f"📢 Spam Filter ({settings['automod_spam_threshold']} msgs/5s)"
            )
        if settings.get("automod_caps_percentage", 0) > 0:
            filters.append(
                f"🔠 Caps Filter ({settings['automod_caps_percentage']}%)"
            )
        if settings.get("automod_max_mentions", 0) > 0:
            filters.append(
                f"📣 Mention Filter ({settings['automod_max_mentions']} max)"
            )
        if settings.get("automod_newaccount_days", 0) > 0:
            filters.append(
                f"🆕 New Account Alert ({settings['automod_newaccount_days']} days)"
            )
        if settings.get("automod_ai_enabled", False):
            filters.append("🤖 Groq AI Detection")

        embed.add_field(
            name="🛡️ Active Filters",
            value="\n".join(filters) if filters else "No filters active",
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    # --- base config (punishments/durations etc) ---

    @automod_group.command(name="punishment", description="Set AutoMod punishment type")
    @app_commands.describe(action="The punishment to apply")
    @is_admin()
    async def automod_punishment(
        self,
        interaction: discord.Interaction,
        action: Literal["warn", "mute", "kick", "ban"],
    ):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["automod_punishment"] = action
        await self.bot.db.update_settings(interaction.guild_id, settings)
        embed = ModEmbed.success(
            "Punishment Updated",
            f"AutoMod punishment set to **{action}**",
        )
        await interaction.response.send_message(embed=embed)

    @automod_group.command(name="muteduration", description="Set how long mutes last")
    @app_commands.describe(
        duration="Duration (e.g., 30m, 1h, 6h, 1d, 7d)",
    )
    @is_admin()
    async def automod_muteduration(
        self, interaction: discord.Interaction, duration: str
    ):
        parsed = parse_time(duration)
        if not parsed:
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Invalid Duration",
                    "Use format like `30m`, `1h`, `6h`, `1d`, `7d`",
                ),
                ephemeral=True,
            )
        delta, human_duration = parsed
        seconds = int(delta.total_seconds())

        if seconds > 28 * 24 * 60 * 60:
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Duration Too Long",
                    "Maximum mute duration is 28 days.",
                ),
                ephemeral=True,
            )

        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["automod_mute_duration"] = seconds
        await self.bot.db.update_settings(interaction.guild_id, settings)
        embed = ModEmbed.success(
            "Mute Duration Updated",
            f"AutoMod mutes will now last **{human_duration}**",
        )
        await interaction.response.send_message(embed=embed)

    @automod_group.command(name="banduration", description="Set ban duration (0=perma)")
    @app_commands.describe(
        duration="Duration (e.g., 1d, 7d, 30d) or '0'/'permanent' for permanent",
    )
    @is_admin()
    async def automod_banduration(
        self, interaction: discord.Interaction, duration: str
    ):
        settings = await self.bot.db.get_settings(interaction.guild_id)

        if duration == "0" or duration.lower() == "permanent":
            settings["automod_ban_duration"] = 0
            await self.bot.db.update_settings(interaction.guild_id, settings)
            embed = ModEmbed.success(
                "Ban Duration Updated",
                "AutoMod bans are now **permanent**",
            )
            return await interaction.response.send_message(embed=embed)

        parsed = parse_time(duration)
        if not parsed:
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Invalid Duration",
                    "Use format like `1d`, `7d`, `30d` or `0`/`permanent`.",
                ),
                ephemeral=True,
            )
        delta, human_duration = parsed
        seconds = int(delta.total_seconds())
        settings["automod_ban_duration"] = seconds
        await self.bot.db.update_settings(interaction.guild_id, settings)
        embed = ModEmbed.success(
            "Ban Duration Updated",
            f"AutoMod bans will now last **{human_duration}**",
        )
        await interaction.response.send_message(embed=embed)

    @automod_group.command(
        name="spamtimeout", description="Set timeout duration for spammers"
    )
    @app_commands.describe(
        duration="Duration (e.g., 30s, 1m, 5m, 10m) or '0' to disable",
    )
    @is_admin()
    async def automod_spamtimeout(
        self, interaction: discord.Interaction, duration: str
    ):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        if duration == "0":
            settings["automod_spam_timeout"] = 0
            await self.bot.db.update_settings(interaction.guild_id, settings)
            embed = ModEmbed.success(
                "Spam Timeout Disabled",
                "Spammers will no longer be automatically timed out.",
            )
            return await interaction.response.send_message(embed=embed)

        parsed = parse_time(duration)
        if not parsed:
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Invalid Duration",
                    "Use format like `30s`, `1m`, `5m`, `10m`",
                ),
                ephemeral=True,
            )
        delta, human_duration = parsed
        seconds = int(delta.total_seconds())
        if seconds > 28 * 24 * 60 * 60:
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Duration Too Long",
                    "Maximum timeout is 28 days.",
                ),
                ephemeral=True,
            )

        settings["automod_spam_timeout"] = seconds
        await self.bot.db.update_settings(interaction.guild_id, settings)
        embed = ModEmbed.success(
            "Spam Timeout Updated",
            f"Spammers will be timed out for **{human_duration}**",
        )
        await interaction.response.send_message(embed=embed)

    # --- filter configs ---

    @automod_group.command(name="spam", description="Configure spam filter")
    @app_commands.describe(
        threshold="Messages per 5 seconds to trigger (0 to disable)",
    )
    @is_admin()
    async def automod_spam(
        self, interaction: discord.Interaction, threshold: int
    ):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["automod_spam_threshold"] = max(0, threshold)
        await self.bot.db.update_settings(interaction.guild_id, settings)
        if threshold == 0:
            embed = ModEmbed.success(
                "Spam Filter Disabled",
                "Spam filter has been disabled.",
            )
        else:
            embed = ModEmbed.success(
                "Spam Filter Updated",
                f"Spam filter set to **{threshold}** messages per 5 seconds.",
            )
        await interaction.response.send_message(embed=embed)

    @automod_group.command(name="caps", description="Configure caps filter")
    @app_commands.describe(
        percentage="Percentage of caps to trigger (0 to disable)",
    )
    @is_admin()
    async def automod_caps(
        self, interaction: discord.Interaction, percentage: int
    ):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["automod_caps_percentage"] = max(0, min(100, percentage))
        await self.bot.db.update_settings(interaction.guild_id, settings)
        if percentage == 0:
            embed = ModEmbed.success(
                "Caps Filter Disabled",
                "Caps filter has been disabled.",
            )
        else:
            embed = ModEmbed.success(
                "Caps Filter Updated",
                f"Caps filter set to **{percentage}%**",
            )
        await interaction.response.send_message(embed=embed)

    @automod_group.command(name="mentions", description="Configure mass mention filter")
    @app_commands.describe(
        max_mentions="Maximum mentions allowed (0 to disable)",
    )
    @is_admin()
    async def automod_mentions(
        self, interaction: discord.Interaction, max_mentions: int
    ):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["automod_max_mentions"] = max(0, max_mentions)
        await self.bot.db.update_settings(interaction.guild_id, settings)
        if max_mentions == 0:
            embed = ModEmbed.success(
                "Mention Filter Disabled",
                "Mass mention filter has been disabled.",
            )
        else:
            embed = ModEmbed.success(
                "Mention Filter Updated",
                f"Max mentions set to **{max_mentions}**",
            )
        await interaction.response.send_message(embed=embed)

    @automod_group.command(name="invites", description="Toggle Discord invite filter")
    @app_commands.describe(enabled="Enable or disable")
    @is_admin()
    async def automod_invites(
        self, interaction: discord.Interaction, enabled: bool
    ):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["automod_invites_enabled"] = enabled
        await self.bot.db.update_settings(interaction.guild_id, settings)
        status = "enabled" if enabled else "disabled"
        embed = ModEmbed.success(
            "Invite Filter Updated",
            f"Discord invite filter has been **{status}**",
        )
        await interaction.response.send_message(embed=embed)

    @automod_group.command(name="links", description="Toggle link filter")
    @app_commands.describe(enabled="Enable or disable")
    @is_admin()
    async def automod_links(
        self, interaction: discord.Interaction, enabled: bool
    ):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["automod_links_enabled"] = enabled
        await self.bot.db.update_settings(interaction.guild_id, settings)
        status = "enabled" if enabled else "disabled"
        embed = ModEmbed.success(
            "Link Filter Updated",
            f"Link filter has been **{status}**",
        )
        await interaction.response.send_message(embed=embed)

    @automod_group.command(
        name="newaccount",
        description="Set new account alert threshold",
    )
    @app_commands.describe(
        days="Account age in days to flag (0 to disable)",
    )
    @is_admin()
    async def automod_newaccount(
        self, interaction: discord.Interaction, days: int
    ):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["automod_newaccount_days"] = max(0, days)
        await self.bot.db.update_settings(interaction.guild_id, settings)
        if days == 0:
            embed = ModEmbed.success(
                "New Account Alert Disabled",
                "New account alerts have been disabled.",
            )
        else:
            embed = ModEmbed.success(
                "New Account Alert Updated",
                f"Accounts younger than **{days}** days will be flagged.",
            )
        await interaction.response.send_message(embed=embed)

    # --- badwords subgroup ---

    badwords_group = app_commands.Group(
        name="badwords",
        description="Manage bad words filter",
        parent=automod_group,
    )

    @badwords_group.command(name="add", description="Add words to the blacklist")
    @app_commands.describe(
        words="Words to add (comma separated)",
    )
    @is_admin()
    async def badwords_add(self, interaction: discord.Interaction, words: str):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        badwords = settings.get("automod_badwords", [])
        new_words = [w.strip().lower() for w in words.split(",") if w.strip()]
        added = []
        for word in new_words:
            if word not in badwords:
                badwords.append(word)
                added.append(word)
        settings["automod_badwords"] = badwords
        await self.bot.db.update_settings(interaction.guild_id, settings)
        if added:
            embed = ModEmbed.success(
                "Words Added", f"Added **{len(added)}** words to the blacklist."
            )
        else:
            embed = ModEmbed.warning(
                "No Changes",
                "All provided words were already in the blacklist.",
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @badwords_group.command(
        name="remove", description="Remove words from the blacklist"
    )
    @app_commands.describe(
        words="Words to remove (comma separated)",
    )
    @is_admin()
    async def badwords_remove(
        self, interaction: discord.Interaction, words: str
    ):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        badwords = settings.get("automod_badwords", [])
        words_to_remove = [w.strip().lower() for w in words.split(",") if w.strip()]
        removed = []
        for word in words_to_remove:
            if word in badwords:
                badwords.remove(word)
                removed.append(word)
        settings["automod_badwords"] = badwords
        await self.bot.db.update_settings(interaction.guild_id, settings)
        if removed:
            embed = ModEmbed.success(
                "Words Removed",
                f"Removed **{len(removed)}** words from the blacklist.",
            )
        else:
            embed = ModEmbed.warning(
                "No Changes",
                "None of those words were in the blacklist.",
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @badwords_group.command(name="list", description="View all blacklisted words")
    @is_mod()
    async def badwords_list(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        badwords = settings.get("automod_badwords", [])
        if not badwords:
            embed = ModEmbed.info(
                "No Bad Words",
                "The bad words list is currently empty.",
            )
        else:
            censored = [f"||{w}||" for w in badwords]
            description = ", ".join(censored[:50])
            embed = discord.Embed(
                title="📝 Blacklisted Words",
                description=description or "No words",
                color=Config.COLOR_INFO,
            )
            if len(badwords) > 50:
                embed.set_footer(
                    text=f"Showing 50 of {len(badwords)} words",
                )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @badwords_group.command(name="clear", description="Clear all blacklisted words")
    @is_admin()
    async def badwords_clear(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        count = len(settings.get("automod_badwords", []))
        settings["automod_badwords"] = []
        await self.bot.db.update_settings(interaction.guild_id, settings)
        embed = ModEmbed.success(
            "Blacklist Cleared",
            f"Removed **{count}** words from the blacklist.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- AI specific config ---

    @automod_group.command(
        name="ai",
        description="Toggle Groq AI detection and configure sensitivity",
    )
    @app_commands.describe(
        enabled="Enable or disable Groq AI analysis",
        min_severity="Minimum severity (1-10) for AI to trigger",
        categories="Comma-separated categories (toxicity, spam, nsfw, threat, other)",
    )
    @is_admin()
    async def automod_ai(
        self,
        interaction: discord.Interaction,
        enabled: Optional[bool] = None,
        min_severity: Optional[int] = None,
        categories: Optional[str] = None,
    ):
        settings = await self.bot.db.get_settings(interaction.guild_id)

        if enabled is not None:
            settings["automod_ai_enabled"] = enabled

        if min_severity is not None:
            settings["automod_ai_min_severity"] = max(1, min(10, min_severity))

        if categories is not None:
            raw = [c.strip().lower() for c in categories.split(",") if c.strip()]
            valid = {"toxicity", "spam", "nsfw", "threat", "other"}
            chosen = [c for c in raw if c in valid]
            if chosen:
                settings["automod_ai_categories"] = chosen

        await self.bot.db.update_settings(interaction.guild_id, settings)

        status = (
            "enabled" if settings.get("automod_ai_enabled", False) else "disabled"
        )
        sev = settings.get("automod_ai_min_severity", 4)
        cats = settings.get(
            "automod_ai_categories",
            ["toxicity", "spam", "nsfw", "threat", "other"],
        )
        embed = ModEmbed.success(
            "AI Settings Updated",
            (
                f"Groq AI is **{status}**.\n"
                f"Min severity: **{sev}**\n"
                f"Categories: `{', '.join(cats)}`"
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
