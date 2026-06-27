"""AutoMod Discord integration and slash-command configuration surface."""

from __future__ import annotations

import asyncio
import copy
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Literal, Mapping, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from cogs.automod_config import AUTOMOD_SETTINGS
from cogs.automod_engine import (
    Action,
    AutoModEngine,
    RULE_SETTING_KEYS,
    RuleMatch,
    normalize_domain,
)
from config import Config
from utils.checks import get_owner_ids, is_admin, is_mod
from utils.embeds import ModEmbed
from utils.logging import send_log_embed


logger = logging.getLogger("AutoMod")

RuleName = Literal[
    "words",
    "spam",
    "mentions",
    "caps",
    "links",
    "invites",
    "scams",
    "new_accounts",
    "ai",
]
ListOperation = Literal["add", "remove", "list", "clear"]
BypassOperation = Literal["add", "remove", "list"]
PolicyAction = Literal["log", "warn", "timeout", "kick", "ban", "quarantine"]


PRESETS: dict[str, dict[str, Any]] = {
    "relaxed": {
        "automod_enabled": True,
        "automod_badwords_enabled": True,
        "automod_spam_enabled": True,
        "automod_mentions_enabled": True,
        "automod_caps_enabled": False,
        "automod_links_enabled": True,
        "automod_invites_enabled": False,
        "automod_scam_protection": True,
        "automod_newaccount_enabled": False,
        "automod_ai_enabled": False,
        "automod_links_mode": "dangerous",
        "automod_spam_threshold": 7,
        "automod_spam_window": 5,
        "automod_duplicate_threshold": 4,
        "automod_duplicate_window": 30,
        "automod_caps_percentage": 90,
        "automod_caps_min_length": 20,
        "automod_max_mentions": 8,
        "automod_newaccount_days": 0,
        "automod_punishment": "warn",
        "automod_security_punishment": "timeout",
        "automod_mute_duration": 1800,
    },
    "standard": {
        "automod_enabled": True,
        "automod_badwords_enabled": True,
        "automod_spam_enabled": True,
        "automod_mentions_enabled": True,
        "automod_caps_enabled": True,
        "automod_links_enabled": True,
        "automod_invites_enabled": True,
        "automod_scam_protection": True,
        "automod_newaccount_enabled": True,
        "automod_ai_enabled": False,
        "automod_links_mode": "dangerous",
        "automod_spam_threshold": 5,
        "automod_spam_window": 5,
        "automod_duplicate_threshold": 3,
        "automod_duplicate_window": 30,
        "automod_caps_percentage": 80,
        "automod_caps_min_length": 12,
        "automod_max_mentions": 6,
        "automod_newaccount_days": 3,
        "automod_punishment": "warn",
        "automod_security_punishment": "timeout",
        "automod_mute_duration": 3600,
    },
    "strict": {
        "automod_enabled": True,
        "automod_badwords_enabled": True,
        "automod_spam_enabled": True,
        "automod_mentions_enabled": True,
        "automod_caps_enabled": True,
        "automod_links_enabled": True,
        "automod_invites_enabled": True,
        "automod_scam_protection": True,
        "automod_newaccount_enabled": True,
        "automod_ai_enabled": False,
        "automod_links_mode": "allowlist",
        "automod_spam_threshold": 4,
        "automod_spam_window": 5,
        "automod_duplicate_threshold": 3,
        "automod_duplicate_window": 20,
        "automod_caps_percentage": 70,
        "automod_caps_min_length": 10,
        "automod_max_mentions": 5,
        "automod_newaccount_days": 7,
        "automod_punishment": "timeout",
        "automod_security_punishment": "timeout",
        "automod_mute_duration": 3600,
    },
}


@dataclass
class EnforcementOutcome:
    action: Action
    success: bool
    details: str
    message_deleted: bool = False
    case_number: Optional[int] = None
    error: Optional[str] = None


def _format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts: list[str] = []
    for value, label in ((days, "day"), (hours, "hour"), (minutes, "minute"), (secs, "second")):
        if value:
            parts.append(f"{value} {label}{'' if value == 1 else 's'}")
    return ", ".join(parts[:2]) or "0 seconds"


def _parse_duration(value: str) -> Optional[int]:
    raw = re.sub(r"\s+", "", (value or "").casefold())
    if not raw:
        return None
    matches = list(re.finditer(r"(\d+)(s|m|h|d|w)", raw))
    if not matches or "".join(match.group(0) for match in matches) != raw:
        return None
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    total = sum(int(match.group(1)) * multipliers[match.group(2)] for match in matches)
    return total if 60 <= total <= 28 * 86400 else None


def _truncate(value: str, limit: int) -> str:
    value = str(value or "")
    return value if len(value) <= limit else f"{value[: limit - 3]}..."


class AutoMod(commands.Cog):
    """Configurable message moderation with deterministic local rules."""

    automod = app_commands.Group(name="automod", description="Configure and inspect AutoMod")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.engine = AutoModEngine()
        self._settings_cache: dict[int, tuple[float, dict[str, Any]]] = {}
        self._settings_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.cleanup_runtime_state.start()

    async def cog_unload(self) -> None:
        self.cleanup_runtime_state.cancel()
        await self.engine.close()

    @tasks.loop(minutes=15)
    async def cleanup_runtime_state(self) -> None:
        self.engine.prune()
        now = time.monotonic()
        for guild_id, (expires_at, _) in list(self._settings_cache.items()):
            if expires_at <= now:
                self._settings_cache.pop(guild_id, None)
        active_guild_ids = {guild.id for guild in self.bot.guilds}
        for guild_id in list(self._settings_locks):
            if guild_id not in active_guild_ids and guild_id not in self._settings_cache:
                self._settings_locks.pop(guild_id, None)

    @cleanup_runtime_state.before_loop
    async def before_cleanup_runtime_state(self) -> None:
        await self.bot.wait_until_ready()

    @staticmethod
    def _sync_master_module(settings: dict[str, Any]) -> None:
        modules = settings.setdefault("modules", {})
        if not isinstance(modules, dict):
            modules = {}
            settings["modules"] = modules
        module = modules.setdefault("automod", {})
        if not isinstance(module, dict):
            module = {}
            modules["automod"] = module
        module["enabled"] = bool(settings.get("automod_enabled", True))

    async def _get_settings(self, guild_id: int, *, fresh: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        cached = self._settings_cache.get(guild_id)
        if not fresh and cached and cached[0] > now:
            return copy.deepcopy(cached[1])
        async with self._settings_locks[guild_id]:
            cached = self._settings_cache.get(guild_id)
            now = time.monotonic()
            if not fresh and cached and cached[0] > now:
                return copy.deepcopy(cached[1])
            settings = await self.bot.db.get_settings(guild_id)
            self._settings_cache[guild_id] = (now + 30, copy.deepcopy(settings))
            return settings

    async def _edit_settings(
        self,
        guild_id: int,
        editor: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        async with self._settings_locks[guild_id]:
            settings = await self.bot.db.get_settings(guild_id)
            editor(settings)
            self._sync_master_module(settings)
            await self.bot.db.update_settings(guild_id, settings)
            self._settings_cache[guild_id] = (time.monotonic() + 30, copy.deepcopy(settings))
            return settings

    @staticmethod
    def _ensure_guild(interaction: discord.Interaction) -> Optional[int]:
        return interaction.guild_id

    @staticmethod
    def _status_embed(settings: Mapping[str, Any], guild: discord.Guild) -> discord.Embed:
        enabled = bool(settings.get("automod_enabled", True))
        embed = discord.Embed(
            title="AutoMod status",
            description=f"System: **{'Enabled' if enabled else 'Disabled'}**",
            color=Config.COLOR_SUCCESS if enabled else Config.COLOR_WARNING,
            timestamp=datetime.now(timezone.utc),
        )
        rules = []
        for rule, key in RULE_SETTING_KEYS.items():
            marker = "ON" if settings.get(key, False) else "OFF"
            rules.append(f"`{marker:<3}` {rule.replace('_', ' ').title()}")
        embed.add_field(name="Rules", value="\n".join(rules), inline=True)
        regular = str(settings.get("automod_punishment", "warn")).replace("mute", "timeout").title()
        security = str(settings.get("automod_security_punishment", "timeout")).replace("mute", "timeout").title()
        duration = _format_duration(int(settings.get("automod_mute_duration", 3600)))
        embed.add_field(
            name="Actions",
            value=f"Regular: **{regular}**\nSecurity: **{security}**\nTimeout: **{duration}**",
            inline=True,
        )
        log_channel = guild.get_channel(settings.get("automod_log_channel")) if settings.get("automod_log_channel") else None
        bypass_roles = settings.get("automod_bypass_roles", []) or []
        if settings.get("automod_bypass_role_id"):
            bypass_roles = list(bypass_roles) + [settings["automod_bypass_role_id"]]
        embed.add_field(
            name="Routing",
            value=(
                f"Logs: {log_channel.mention if log_channel else '`Not set`'}\n"
                f"Bypass roles: **{len(set(bypass_roles))}**\n"
                f"Bypass channels: **{len(set(settings.get('automod_bypass_channels', []) or []))}**"
            ),
            inline=False,
        )
        embed.set_footer(text="Use /automod help for the command map")
        return embed

    @staticmethod
    def _can_act_on(member: discord.Member, guild: discord.Guild) -> Optional[str]:
        bot_member = guild.me
        if member.id == guild.owner_id:
            return "The server owner cannot be moderated."
        if bot_member is None:
            return "The bot member could not be resolved."
        if member.top_role >= bot_member.top_role:
            return "Move the bot role above the target member's highest role."
        return None

    async def _create_case(
        self,
        guild: discord.Guild,
        member: discord.Member,
        action: Action,
        reason: str,
        duration: Optional[str] = None,
    ) -> Optional[int]:
        try:
            return await self.bot.db.create_case(
                guild.id,
                member.id,
                self.bot.user.id,
                f"AutoMod {action.value.title()}",
                reason,
                duration,
            )
        except Exception:
            logger.exception("Failed to create AutoMod case in guild %s", guild.id)
            return None

    async def _apply_warning_threshold(
        self,
        member: discord.Member,
        settings: Mapping[str, Any],
        warning_count: int,
        reason: str,
    ) -> Optional[str]:
        if not settings.get("warn_thresholds_enabled", True):
            return None
        guild = member.guild
        if warning_count >= int(settings.get("warn_threshold_ban", 7) or 10**9):
            await guild.ban(member, reason=f"[AutoMod] Warning threshold: {reason}")
            return "Ban threshold reached"
        if warning_count >= int(settings.get("warn_threshold_kick", 5) or 10**9):
            await member.kick(reason=f"[AutoMod] Warning threshold: {reason}")
            return "Kick threshold reached"
        if warning_count >= int(settings.get("warn_threshold_mute", 3) or 10**9):
            duration = min(28 * 86400, max(60, int(settings.get("warn_mute_duration", 3600))))
            await member.timeout(timedelta(seconds=duration), reason=f"[AutoMod] Warning threshold: {reason}")
            return f"Timeout threshold reached ({_format_duration(duration)})"
        return None

    async def _enforce(
        self,
        message: discord.Message,
        match: RuleMatch,
        settings: Mapping[str, Any],
    ) -> EnforcementOutcome:
        action = self.engine.resolve_action(match, settings)
        deleted = False
        deletion_error: Optional[str] = None
        if action is not Action.LOG and match.delete_message and settings.get("automod_delete_violations", True):
            try:
                await message.delete()
                deleted = True
            except discord.NotFound:
                deleted = True
            except discord.Forbidden:
                deletion_error = "Missing Manage Messages permission"
            except discord.HTTPException as exc:
                deletion_error = f"Discord rejected message deletion: {exc.code}"

        if action is Action.LOG:
            details = "Message deleted and logged" if deleted else "Logged only"
            success = deleted or not match.delete_message
            if deletion_error:
                details = deletion_error
            outcome = EnforcementOutcome(action, success, details, deleted, error=deletion_error)
            self.engine.mark_action(outcome.success)
            return outcome

        member = message.author
        hierarchy_error = self._can_act_on(member, message.guild)
        if hierarchy_error:
            outcome = EnforcementOutcome(action, False, hierarchy_error, deleted, error=hierarchy_error)
            self.engine.mark_action(False)
            return outcome

        duration_seconds = min(28 * 86400, max(60, int(settings.get("automod_mute_duration", 3600))))
        reason = _truncate(f"[AutoMod/{match.rule}] {match.reason}", 500)
        details = ""
        case_number: Optional[int] = None
        try:
            if action is Action.WARN:
                _, warning_count = await self.bot.db.add_warning(
                    message.guild.id,
                    member.id,
                    self.bot.user.id,
                    match.reason,
                )
                details = f"Warning issued (total: {warning_count})"
                threshold_result = await self._apply_warning_threshold(member, settings, warning_count, match.reason)
                if threshold_result:
                    details = f"{details}; {threshold_result}"
            elif action is Action.TIMEOUT:
                await member.timeout(timedelta(seconds=duration_seconds), reason=reason)
                details = f"Timed out for {_format_duration(duration_seconds)}"
            elif action is Action.KICK:
                await member.kick(reason=reason)
                details = "Kicked"
            elif action is Action.BAN:
                delete_seconds = min(7, max(0, int(settings.get("automod_ban_delete_days", 1)))) * 86400
                await message.guild.ban(member, reason=reason, delete_message_seconds=delete_seconds)
                details = "Banned"
            elif action is Action.QUARANTINE:
                role_id = settings.get("automod_quarantine_role_id")
                role = message.guild.get_role(int(role_id)) if role_id else None
                if role is None or role >= message.guild.me.top_role:
                    await member.timeout(timedelta(seconds=duration_seconds), reason=f"{reason} (quarantine fallback)")
                    details = f"Timed out for {_format_duration(duration_seconds)} (quarantine role unavailable)"
                else:
                    await member.add_roles(role, reason=reason)
                    details = f"Quarantined with {role.name}"
            duration = _format_duration(duration_seconds) if action is Action.TIMEOUT else None
            case_number = await self._create_case(message.guild, member, action, match.reason, duration)
            outcome = EnforcementOutcome(action, True, details, deleted, case_number)
        except discord.Forbidden:
            outcome = EnforcementOutcome(
                action,
                False,
                "Discord denied the action; check bot permissions and role order.",
                deleted,
                error="Forbidden",
            )
        except discord.HTTPException as exc:
            outcome = EnforcementOutcome(
                action,
                False,
                f"Discord rejected the action (HTTP {exc.status}, code {exc.code}).",
                deleted,
                error=str(exc),
            )
        except Exception as exc:
            logger.exception("AutoMod enforcement failed in guild %s", message.guild.id)
            outcome = EnforcementOutcome(action, False, "Internal enforcement error", deleted, error=str(exc))
        self.engine.mark_action(outcome.success)
        return outcome

    async def _send_log(
        self,
        message: discord.Message,
        match: RuleMatch,
        outcome: EnforcementOutcome,
        settings: Mapping[str, Any],
    ) -> None:
        channel_id = settings.get("automod_log_channel") or settings.get("log_channel_automod")
        channel = message.guild.get_channel(int(channel_id)) if channel_id else None
        if not isinstance(channel, discord.abc.Messageable):
            return
        colors = {
            "INFO": 0x3B82F6,
            "LOW": 0xF59E0B,
            "MEDIUM": 0xF97316,
            "HIGH": 0xEF4444,
            "CRITICAL": 0x991B1B,
        }
        embed = discord.Embed(
            title=f"AutoMod: {match.rule.replace('_', ' ').title()}",
            color=colors[match.severity.name],
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Member", value=f"{message.author.mention}\n`{message.author.id}`", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Severity", value=match.severity.name.title(), inline=True)
        embed.add_field(name="Reason", value=_truncate(match.reason, 1024), inline=False)
        action_text = outcome.details
        if outcome.case_number is not None:
            action_text += f"\nCase: `#{outcome.case_number}`"
        if not outcome.success:
            action_text = f"FAILED: {action_text}"
        embed.add_field(name="Action", value=_truncate(action_text, 1024), inline=False)
        if match.evidence:
            evidence = ", ".join(f"||{_truncate(item, 80)}||" for item in match.evidence)
            embed.add_field(name="Matched", value=_truncate(evidence, 1024), inline=False)
        content = (message.content or "").replace("```", "'''" )
        if content:
            embed.add_field(name="Message", value=f"```\n{_truncate(content, 900)}\n```", inline=False)
        try:
            await send_log_embed(channel, embed)
        except (discord.Forbidden, discord.HTTPException):
            logger.warning("Could not send AutoMod log in guild %s", message.guild.id)

    async def _notify_member(
        self,
        message: discord.Message,
        match: RuleMatch,
        outcome: EnforcementOutcome,
    ) -> None:
        if not outcome.success or outcome.action is Action.LOG:
            return
        embed = discord.Embed(
            title=f"Moderation action in {message.guild.name}",
            description="An automated rule was triggered by your message.",
            color=Config.COLOR_WARNING,
        )
        embed.add_field(name="Reason", value=_truncate(match.reason, 1024), inline=False)
        embed.add_field(name="Action", value=_truncate(outcome.details, 1024), inline=False)
        embed.set_footer(text="Contact the server's moderators if you believe this was a mistake.")
        try:
            await message.author.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            return

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot or message.webhook_id is not None:
            return
        try:
            settings = await self._get_settings(message.guild.id)
            if not settings.get("automod_enabled", True):
                return
            if self.engine.bypass_reason(message, settings, get_owner_ids()) is not None:
                return
            match = await self.engine.evaluate(message, settings)
            if match is None:
                return
            outcome = await self._enforce(message, match, settings)
            await self._send_log(message, match, outcome, settings)
            if settings.get("automod_notify_users", True):
                await self._notify_member(message, match, outcome)
            if settings.get("automod_public_feedback", False):
                text = f"AutoMod: {match.reason} — {outcome.details}"
                try:
                    await message.channel.send(
                        _truncate(text, 300),
                        delete_after=10,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                except (discord.Forbidden, discord.HTTPException):
                    pass
        except Exception:
            logger.exception("Unhandled AutoMod error in guild %s", message.guild.id)

    @automod.command(name="help", description="Show the AutoMod command map")
    @is_mod()
    async def automod_help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="AutoMod commands",
            description="All configuration responses are private to the moderator.",
            color=Config.COLOR_INFO,
        )
        embed.add_field(
            name="Start and inspect",
            value=(
                "`/automod setup` — apply a complete preset\n"
                "`/automod status` — inspect the live configuration\n"
                "`/automod enable` / `disable` — master switch\n"
                "`/automod test` — safely test sample text"
            ),
            inline=False,
        )
        embed.add_field(
            name="Tune behavior",
            value=(
                "`/automod rule` — enable one rule\n"
                "`/automod thresholds` — spam, duplicate, caps and mention limits\n"
                "`/automod actions` — regular/security actions and timeout duration\n"
                "`/automod link-mode` — dangerous-only or allowlist mode"
            ),
            inline=False,
        )
        embed.add_field(
            name="Lists and routing",
            value=(
                "`/automod words`, `/automod domains`, `/automod invites`\n"
                "`/automod bypass-role`, `/automod bypass-channel`\n"
                "`/automod logs`, `/automod recent`, `/automod stats`"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @automod.command(name="status", description="Show the active rules, actions and routing")
    @is_mod()
    async def automod_status(self, interaction: discord.Interaction) -> None:
        settings = await self._get_settings(interaction.guild_id)
        await interaction.response.send_message(
            embed=self._status_embed(settings, interaction.guild),
            ephemeral=True,
        )

    @automod.command(name="setup", description="Apply a complete, usable AutoMod preset")
    @app_commands.describe(preset="Protection level", log_channel="Where AutoMod actions should be logged")
    @is_admin()
    async def automod_setup(
        self,
        interaction: discord.Interaction,
        preset: Literal["relaxed", "standard", "strict"] = "standard",
        log_channel: Optional[discord.TextChannel] = None,
    ) -> None:
        def edit(settings: dict[str, Any]) -> None:
            settings.update(copy.deepcopy(PRESETS[preset]))
            if log_channel is not None:
                settings["automod_log_channel"] = log_channel.id

        settings = await self._edit_settings(interaction.guild_id, edit)
        embed = self._status_embed(settings, interaction.guild)
        embed.title = f"AutoMod setup: {preset.title()}"
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @automod.command(name="enable", description="Enable AutoMod without changing any rules")
    @is_admin()
    async def automod_enable(self, interaction: discord.Interaction) -> None:
        await self._edit_settings(interaction.guild_id, lambda settings: settings.__setitem__("automod_enabled", True))
        await interaction.response.send_message(embed=ModEmbed.success("AutoMod enabled", "Existing rule settings were preserved."), ephemeral=True)

    @automod.command(name="disable", description="Disable AutoMod without deleting its configuration")
    @is_admin()
    async def automod_disable(self, interaction: discord.Interaction) -> None:
        await self._edit_settings(interaction.guild_id, lambda settings: settings.__setitem__("automod_enabled", False))
        await interaction.response.send_message(embed=ModEmbed.success("AutoMod disabled", "Your configuration was preserved."), ephemeral=True)

    @automod.command(name="rule", description="Enable or disable one AutoMod rule")
    @app_commands.describe(rule="Rule to change", enabled="Whether the rule should run")
    @is_admin()
    async def automod_rule(self, interaction: discord.Interaction, rule: RuleName, enabled: bool) -> None:
        key = RULE_SETTING_KEYS[rule]
        await self._edit_settings(interaction.guild_id, lambda settings: settings.__setitem__(key, enabled))
        await interaction.response.send_message(
            embed=ModEmbed.success("Rule updated", f"**{rule.replace('_', ' ').title()}** is now **{'enabled' if enabled else 'disabled'}**."),
            ephemeral=True,
        )

    @automod.command(name="thresholds", description="Set spam, duplicate, caps, mention and account-age limits")
    @app_commands.describe(
        spam_messages="Messages allowed inside the spam window (2-50)",
        spam_seconds="Spam window in seconds (2-60)",
        duplicate_messages="Matching messages allowed (2-20)",
        duplicate_seconds="Duplicate window in seconds (5-300)",
        mentions="Unique user and role mentions allowed (1-50)",
        caps_percent="Uppercase percentage (50-100)",
        caps_characters="Minimum letters before caps checking (5-500)",
        new_account_days="Account age to log (0-365 days)",
    )
    @is_admin()
    async def automod_thresholds(
        self,
        interaction: discord.Interaction,
        spam_messages: Optional[app_commands.Range[int, 2, 50]] = None,
        spam_seconds: Optional[app_commands.Range[int, 2, 60]] = None,
        duplicate_messages: Optional[app_commands.Range[int, 2, 20]] = None,
        duplicate_seconds: Optional[app_commands.Range[int, 5, 300]] = None,
        mentions: Optional[app_commands.Range[int, 1, 50]] = None,
        caps_percent: Optional[app_commands.Range[int, 50, 100]] = None,
        caps_characters: Optional[app_commands.Range[int, 5, 500]] = None,
        new_account_days: Optional[app_commands.Range[int, 0, 365]] = None,
    ) -> None:
        changes = {
            "automod_spam_threshold": spam_messages,
            "automod_spam_window": spam_seconds,
            "automod_duplicate_threshold": duplicate_messages,
            "automod_duplicate_window": duplicate_seconds,
            "automod_max_mentions": mentions,
            "automod_caps_percentage": caps_percent,
            "automod_caps_min_length": caps_characters,
            "automod_newaccount_days": new_account_days,
        }
        supplied = {key: value for key, value in changes.items() if value is not None}
        if not supplied:
            settings = await self._get_settings(interaction.guild_id)
            text = (
                f"Spam: **{settings['automod_spam_threshold']}** / **{settings['automod_spam_window']}s**\n"
                f"Duplicates: **{settings['automod_duplicate_threshold']}** / **{settings['automod_duplicate_window']}s**\n"
                f"Mentions: **{settings['automod_max_mentions']}**\n"
                f"Caps: **{settings['automod_caps_percentage']}%** after **{settings['automod_caps_min_length']}** letters\n"
                f"New account: **{settings['automod_newaccount_days']} days**"
            )
            await interaction.response.send_message(embed=ModEmbed.info("Current thresholds", text), ephemeral=True)
            return
        await self._edit_settings(interaction.guild_id, lambda settings: settings.update(supplied))
        labels = [key.removeprefix("automod_").replace("_", " ").title() for key in supplied]
        await interaction.response.send_message(embed=ModEmbed.success("Thresholds updated", "\n".join(f"• {label}" for label in labels)), ephemeral=True)

    @automod.command(name="actions", description="Set actions for normal and security violations")
    @app_commands.describe(
        regular="Action for words, spam, mentions, invites and caps",
        security="Action for scams and dangerous links",
        timeout_duration="Timeout duration such as 30m, 2h or 1d",
        notify_users="DM users after a successful action",
        public_feedback="Post a short temporary notice in the channel",
    )
    @is_admin()
    async def automod_actions(
        self,
        interaction: discord.Interaction,
        regular: Optional[PolicyAction] = None,
        security: Optional[PolicyAction] = None,
        timeout_duration: Optional[str] = None,
        notify_users: Optional[bool] = None,
        public_feedback: Optional[bool] = None,
    ) -> None:
        duration = _parse_duration(timeout_duration) if timeout_duration is not None else None
        if timeout_duration is not None and duration is None:
            await interaction.response.send_message(
                embed=ModEmbed.error("Invalid duration", "Use values from 1 minute to 28 days, for example `30m`, `2h`, or `1d12h`."),
                ephemeral=True,
            )
            return
        changes: dict[str, Any] = {}
        if regular is not None:
            changes["automod_punishment"] = regular
        if security is not None:
            changes["automod_security_punishment"] = security
        if duration is not None:
            changes["automod_mute_duration"] = duration
        if notify_users is not None:
            changes["automod_notify_users"] = notify_users
        if public_feedback is not None:
            changes["automod_public_feedback"] = public_feedback
        if not changes:
            settings = await self._get_settings(interaction.guild_id)
            text = (
                f"Regular: **{settings.get('automod_punishment', 'warn')}**\n"
                f"Security: **{settings.get('automod_security_punishment', 'timeout')}**\n"
                f"Timeout: **{_format_duration(settings.get('automod_mute_duration', 3600))}**\n"
                f"DM users: **{settings.get('automod_notify_users', True)}**\n"
                f"Public feedback: **{settings.get('automod_public_feedback', False)}**"
            )
            await interaction.response.send_message(embed=ModEmbed.info("Current actions", text), ephemeral=True)
            return
        await self._edit_settings(interaction.guild_id, lambda settings: settings.update(changes))
        await interaction.response.send_message(embed=ModEmbed.success("Actions updated", "The new policy is active."), ephemeral=True)

    @automod.command(name="link-mode", description="Choose dangerous-link detection or a strict domain allowlist")
    @app_commands.describe(mode="Dangerous blocks known risky links; allowlist blocks every unlisted domain")
    @is_admin()
    async def automod_link_mode(
        self,
        interaction: discord.Interaction,
        mode: Literal["dangerous", "allowlist"],
    ) -> None:
        await self._edit_settings(interaction.guild_id, lambda settings: settings.__setitem__("automod_links_mode", mode))
        await interaction.response.send_message(
            embed=ModEmbed.success("Link mode updated", f"Link filtering now uses **{mode}** mode."),
            ephemeral=True,
        )

    async def _edit_string_list(
        self,
        interaction: discord.Interaction,
        *,
        key: str,
        operation: ListOperation,
        value: Optional[str],
        label: str,
        normalizer: Callable[[str], str],
        maximum: int,
        clear_confirmed: bool,
    ) -> None:
        if operation in {"add", "remove"} and not value:
            await interaction.response.send_message(embed=ModEmbed.error("Missing value", f"Provide the {label.lower()} to {operation}."), ephemeral=True)
            return
        if operation == "clear" and not clear_confirmed:
            await interaction.response.send_message(embed=ModEmbed.warning("Confirmation required", "Run the command again with `confirm:True`."), ephemeral=True)
            return
        normalized = normalizer(value or "")
        if value and not normalized:
            await interaction.response.send_message(embed=ModEmbed.error("Invalid value", f"That {label.lower()} is not valid."), ephemeral=True)
            return
        settings = await self._get_settings(interaction.guild_id, fresh=True)
        current = list(dict.fromkeys(str(item).casefold() for item in settings.get(key, []) if str(item).strip()))
        if operation == "list":
            shown = current[:40]
            body = "\n".join(f"• `{_truncate(item, 80)}`" for item in shown) or "`None configured`"
            if len(current) > len(shown):
                body += f"\n…and {len(current) - len(shown)} more."
            await interaction.response.send_message(embed=ModEmbed.info(f"{label} list", body), ephemeral=True)
            return
        if operation == "add":
            if normalized in current:
                await interaction.response.send_message(embed=ModEmbed.warning("No change", f"That {label.lower()} is already listed."), ephemeral=True)
                return
            if len(current) >= maximum:
                await interaction.response.send_message(embed=ModEmbed.error("List full", f"The limit is {maximum} entries."), ephemeral=True)
                return
            current.append(normalized)
        elif operation == "remove":
            if normalized not in current:
                await interaction.response.send_message(embed=ModEmbed.warning("No change", f"That {label.lower()} is not listed."), ephemeral=True)
                return
            current.remove(normalized)
        else:
            current.clear()
        await self._edit_settings(interaction.guild_id, lambda editable: editable.__setitem__(key, current))
        await interaction.response.send_message(embed=ModEmbed.success(f"{label} list updated", f"Entries: **{len(current)}**"), ephemeral=True)

    @automod.command(name="words", description="Add, remove, list or clear blocked words and phrases")
    @is_admin()
    async def automod_words(
        self,
        interaction: discord.Interaction,
        operation: ListOperation,
        phrase: Optional[app_commands.Range[str, 2, 80]] = None,
        confirm: bool = False,
    ) -> None:
        await self._edit_string_list(
            interaction,
            key="automod_badwords",
            operation=operation,
            value=phrase,
            label="Blocked phrase",
            normalizer=lambda value: re.sub(r"\s+", " ", value.strip().casefold()),
            maximum=500,
            clear_confirmed=confirm,
        )

    @automod.command(name="domains", description="Manage domains allowed by strict link mode")
    @is_admin()
    async def automod_domains(
        self,
        interaction: discord.Interaction,
        operation: ListOperation,
        domain: Optional[app_commands.Range[str, 3, 253]] = None,
        confirm: bool = False,
    ) -> None:
        await self._edit_string_list(
            interaction,
            key="automod_whitelisted_domains",
            operation=operation,
            value=domain,
            label="Allowed domain",
            normalizer=normalize_domain,
            maximum=500,
            clear_confirmed=confirm,
        )

    @automod.command(name="invites", description="Manage Discord invite codes that AutoMod allows")
    @is_admin()
    async def automod_invites(
        self,
        interaction: discord.Interaction,
        operation: ListOperation,
        invite: Optional[app_commands.Range[str, 2, 100]] = None,
        confirm: bool = False,
    ) -> None:
        def invite_code(value: str) -> str:
            return value.strip().rstrip("/").rsplit("/", 1)[-1].casefold()

        await self._edit_string_list(
            interaction,
            key="automod_allowed_invites",
            operation=operation,
            value=invite,
            label="Allowed invite",
            normalizer=invite_code,
            maximum=250,
            clear_confirmed=confirm,
        )

    async def _edit_bypass(
        self,
        interaction: discord.Interaction,
        operation: BypassOperation,
        target: Optional[discord.abc.Snowflake],
        *,
        key: str,
        label: str,
    ) -> None:
        settings = await self._get_settings(interaction.guild_id, fresh=True)
        current = []
        for value in settings.get(key, []) or []:
            try:
                current.append(int(value))
            except (TypeError, ValueError):
                continue
        current = list(dict.fromkeys(current))
        if operation == "list":
            mention = "<@&{}>" if key.endswith("roles") else "<#{}>"
            body = "\n".join(f"• {mention.format(item)}" for item in current) or "`None configured`"
            await interaction.response.send_message(embed=ModEmbed.info(f"Bypass {label}s", body), ephemeral=True)
            return
        if target is None:
            await interaction.response.send_message(embed=ModEmbed.error("Missing target", f"Choose a {label} to {operation}."), ephemeral=True)
            return
        if operation == "add" and target.id not in current:
            current.append(target.id)
        elif operation == "remove" and target.id in current:
            current.remove(target.id)
        else:
            await interaction.response.send_message(embed=ModEmbed.warning("No change", f"That {label} is {'already bypassed' if operation == 'add' else 'not bypassed'}."), ephemeral=True)
            return
        await self._edit_settings(interaction.guild_id, lambda editable: editable.__setitem__(key, current))
        await interaction.response.send_message(embed=ModEmbed.success("Bypass updated", f"{target.mention} was {operation}ed."), ephemeral=True)

    @automod.command(name="bypass-role", description="Add, remove or list roles ignored by AutoMod")
    @is_admin()
    async def automod_bypass_role(
        self,
        interaction: discord.Interaction,
        operation: BypassOperation,
        role: Optional[discord.Role] = None,
    ) -> None:
        await self._edit_bypass(interaction, operation, role, key="automod_bypass_roles", label="role")

    @automod.command(name="bypass-channel", description="Add, remove or list channels ignored by AutoMod")
    @is_admin()
    async def automod_bypass_channel(
        self,
        interaction: discord.Interaction,
        operation: BypassOperation,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        await self._edit_bypass(interaction, operation, channel, key="automod_bypass_channels", label="channel")

    @automod.command(name="logs", description="Set, disable or inspect the AutoMod log channel")
    @is_admin()
    async def automod_logs(
        self,
        interaction: discord.Interaction,
        operation: Literal["set", "disable", "status"],
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        if operation == "set" and channel is None:
            await interaction.response.send_message(embed=ModEmbed.error("Missing channel", "Choose a channel when using `set`."), ephemeral=True)
            return
        if operation == "status":
            settings = await self._get_settings(interaction.guild_id)
            existing = interaction.guild.get_channel(settings.get("automod_log_channel")) if settings.get("automod_log_channel") else None
            await interaction.response.send_message(embed=ModEmbed.info("AutoMod logs", existing.mention if existing else "`Disabled`"), ephemeral=True)
            return
        value = channel.id if operation == "set" else None
        await self._edit_settings(interaction.guild_id, lambda settings: settings.__setitem__("automod_log_channel", value))
        text = channel.mention if channel else "Logging disabled"
        await interaction.response.send_message(embed=ModEmbed.success("Log routing updated", text), ephemeral=True)

    @automod.command(name="test", description="Test sample text without deleting it or punishing anyone")
    @is_admin()
    async def automod_test(self, interaction: discord.Interaction, content: app_commands.Range[str, 1, 1500]) -> None:
        await interaction.response.defer(ephemeral=True)

        class TestMessage:
            def __init__(self) -> None:
                self.content = content
                self.author = interaction.user
                self.guild = interaction.guild
                self.channel = interaction.channel
                self.created_at = datetime.now(timezone.utc)
                self.mentions = list({match.group(1) for match in re.finditer(r"<@(\d+)>", content)})
                self.role_mentions = list({match.group(1) for match in re.finditer(r"<@&(\d+)>", content)})

        settings = await self._get_settings(interaction.guild_id)
        test_settings = dict(settings)
        test_settings["automod_newaccount_enabled"] = False
        match = await self.engine.evaluate(TestMessage(), test_settings, dry_run=True)
        if match is None:
            embed = ModEmbed.success("No violation", "The sample passed every enabled content rule.")
        else:
            action = self.engine.resolve_action(match, settings)
            embed = discord.Embed(title="Violation detected", color=Config.COLOR_WARNING)
            embed.add_field(name="Rule", value=match.rule.replace("_", " ").title(), inline=True)
            embed.add_field(name="Severity", value=match.severity.name.title(), inline=True)
            embed.add_field(name="Action", value=action.value.title(), inline=True)
            embed.add_field(name="Reason", value=match.reason, inline=False)
            if match.evidence:
                embed.add_field(name="Matched", value=", ".join(f"||{item}||" for item in match.evidence), inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @automod.command(name="stats", description="Show runtime AutoMod totals since the last bot restart")
    @is_mod()
    async def automod_stats(self, interaction: discord.Interaction) -> None:
        stats = self.engine.stats
        hits = self.engine.rule_hits
        hit_text = "\n".join(f"{name.replace('_', ' ').title()}: **{count:,}**" for name, count in hits.most_common()) or "`No violations yet`"
        embed = discord.Embed(title="AutoMod runtime stats", color=Config.COLOR_INFO)
        embed.add_field(
            name="Totals",
            value=(
                f"Messages checked: **{stats['messages_checked']:,}**\n"
                f"Violations: **{stats['violations_detected']:,}**\n"
                f"Actions succeeded: **{stats['actions_succeeded']:,}**\n"
                f"Actions failed: **{stats['actions_failed']:,}**"
            ),
            inline=True,
        )
        embed.add_field(name="Rule hits", value=_truncate(hit_text, 1024), inline=True)
        embed.set_footer(text="Runtime counters reset when the bot restarts")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @automod.command(name="recent", description="Show recent AutoMod violations from this bot session")
    @is_mod()
    async def automod_recent(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
    ) -> None:
        recent = self.engine.recent_for(interaction.guild_id, user.id if user else None)[:10]
        if not recent:
            await interaction.response.send_message(embed=ModEmbed.info("No recent violations", "No matching runtime records were found."), ephemeral=True)
            return
        lines = []
        for item in recent:
            timestamp = int(item.occurred_at)
            lines.append(
                f"<t:{timestamp}:R> <@{item.user_id}> in <#{item.channel_id}> — "
                f"**{item.rule.replace('_', ' ').title()}**: {_truncate(item.reason, 100)}"
            )
        embed = discord.Embed(title="Recent AutoMod violations", description="\n".join(lines), color=Config.COLOR_INFO)
        embed.set_footer(text="Runtime history is bounded and resets when the bot restarts")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @automod.command(name="reset", description="Restore all AutoMod settings to safe defaults")
    @is_admin()
    async def automod_reset(self, interaction: discord.Interaction, confirm: bool = False) -> None:
        if not confirm:
            await interaction.response.send_message(
                embed=ModEmbed.warning("Confirmation required", "Run `/automod reset confirm:True` to restore AutoMod defaults."),
                ephemeral=True,
            )
            return

        def reset(settings: dict[str, Any]) -> None:
            for key in list(settings):
                if key.startswith("automod_"):
                    settings.pop(key, None)
            settings.update(copy.deepcopy(AUTOMOD_SETTINGS))

        settings = await self._edit_settings(interaction.guild_id, reset)
        await interaction.response.send_message(embed=self._status_embed(settings, interaction.guild), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoMod(bot))
