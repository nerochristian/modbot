"""
Guardian - Anti-nuke protection (pairs with anti-raid as the Guardian module).

Watches audit-log-attributed destructive actions (mass channel/role deletes,
mass bans/kicks, webhook spam, and dangerous permission grants) and stops a
rogue or compromised staff account before the server burns down.

Everything is configurable from the dashboard Guardian module or /guardian:
- guardian_nuke_enabled            master switch (default False)
- guardian_nuke_action             strip | ban | kick | quarantine (default strip)
- guardian_nuke_quarantine_role    role id, required for quarantine
- guardian_nuke_log_channel        alert channel (falls back to antiraid/mod log)
- guardian_nuke_cooldown_seconds   10-3600 (default 60)
- guardian_watch_<event>           per-event toggle (default True)
- guardian_<event>_threshold       actions needed to trip (per event)
- guardian_<event>_window          seconds the threshold must fill within
- guardian_ignored_users / _roles  trusted bypass lists (owner/bots always exempt)
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import Config
from utils.checks import is_admin, is_bot_owner_id
from utils.logging import send_log_embed
from utils.moderation_settings import moderation_bool, moderation_id_set

DANGEROUS_PERMISSIONS = (
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "ban_members",
    "kick_members",
    "manage_webhooks",
)

# event key -> (audit log action or None, default threshold, default window seconds, label)
NUKE_EVENTS: dict[str, tuple[Optional[discord.AuditLogAction], int, int, str]] = {
    "channel_delete": (discord.AuditLogAction.channel_delete, 3, 30, "Channel deletions"),
    "channel_create": (discord.AuditLogAction.channel_create, 5, 30, "Channel creations"),
    "role_delete": (discord.AuditLogAction.role_delete, 3, 30, "Role deletions"),
    "ban": (discord.AuditLogAction.ban, 5, 30, "Bans"),
    "kick": (discord.AuditLogAction.kick, 5, 30, "Kicks"),
    "webhook_create": (discord.AuditLogAction.webhook_create, 2, 30, "Webhook creations"),
    "dangerous_grant": (None, 1, 60, "Dangerous permission grants"),
}

NUKE_ACTIONS = ("strip", "ban", "kick", "quarantine")


def _clamped_int(settings: dict, key: str, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(settings.get(key, default))))
    except (TypeError, ValueError, OverflowError):
        return default


def _watch_enabled(settings: dict, event: str) -> bool:
    return moderation_bool(settings, f"guardian_watch_{event}", True)


def _threshold(settings: dict, event: str) -> int:
    default = NUKE_EVENTS[event][1]
    return _clamped_int(settings, f"guardian_{event}_threshold", default, 1, 100)


def _window(settings: dict, event: str) -> int:
    default = NUKE_EVENTS[event][2]
    return _clamped_int(settings, f"guardian_{event}_window", default, 5, 600)


def _role_is_dangerous(role: discord.Role) -> bool:
    if role.is_default():
        return False
    return any(getattr(role.permissions, perm) for perm in DANGEROUS_PERMISSIONS)


class Guardian(commands.Cog):
    """Anti-nuke engine: audit-log attribution + configurable tripwires."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # guild_id -> event -> actor_id -> [timestamps]
        self.event_tracker: Dict[int, Dict[str, Dict[int, List[datetime]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        self.nuke_cooldown: set[int] = set()

    # ---------- helpers ----------

    async def _recent_actor(
        self,
        guild: discord.Guild,
        action: discord.AuditLogAction,
        target_id: Optional[int] = None,
        seconds: int = 10,
    ) -> Optional[discord.abc.User]:
        """Find who performed a destructive action via the audit log."""
        try:
            async for entry in guild.audit_logs(limit=6, action=action):
                age = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
                if age > seconds:
                    break
                if target_id is not None and getattr(entry.target, "id", None) != target_id:
                    continue
                if entry.user:
                    return entry.user
        except (discord.Forbidden, discord.HTTPException):
            return None
        return None

    def _is_exempt(
        self,
        guild: discord.Guild,
        user: discord.abc.User,
        settings: dict,
    ) -> bool:
        if user.id == guild.owner_id:
            return True
        if user.bot or is_bot_owner_id(user.id):
            return True
        if user.id in moderation_id_set(settings, "guardian_ignored_users"):
            return True
        ignored_roles = moderation_id_set(settings, "guardian_ignored_roles")
        if ignored_roles:
            member = guild.get_member(user.id)
            if member and any(role.id in ignored_roles for role in member.roles):
                return True
        return False

    async def _record(
        self,
        guild: discord.Guild,
        event: str,
        actor: Optional[discord.abc.User],
    ) -> None:
        if actor is None or guild.me is None:
            return
        if actor.id == guild.me.id:
            return  # our own enforcement never trips the alarm

        settings = await self.bot.db.get_settings(guild.id)
        if not moderation_bool(settings, "guardian_nuke_enabled", False):
            return
        if not _watch_enabled(settings, event):
            return
        if self._is_exempt(guild, actor, settings):
            return

        now = datetime.now(timezone.utc)
        window = _window(settings, event)
        bucket = self.event_tracker[guild.id][event][actor.id]
        cutoff = now - timedelta(seconds=window)
        self.event_tracker[guild.id][event][actor.id] = bucket = [t for t in bucket if t >= cutoff]
        bucket.append(now)

        if len(bucket) < _threshold(settings, event):
            return
        bucket.clear()
        await self._trigger(guild, actor, event, settings)

    async def _trigger(
        self,
        guild: discord.Guild,
        actor: discord.abc.User,
        event: str,
        settings: dict,
    ) -> None:
        if guild.id in self.nuke_cooldown:
            return
        self.nuke_cooldown.add(guild.id)

        action = str(settings.get("guardian_nuke_action", "strip")).strip().lower()
        if action not in NUKE_ACTIONS:
            action = "strip"
        label = NUKE_EVENTS[event][3]
        member = guild.get_member(actor.id)

        outcome = "No action possible (actor left the server)"
        try:
            if action == "strip":
                if member:
                    bot_top = guild.me.top_role if guild.me else None
                    removable = [
                        role for role in member.roles
                        if not role.is_default()
                        and not role.managed
                        and bot_top is not None
                        and role < bot_top
                    ]
                    if removable:
                        await member.remove_roles(
                            *removable,
                            reason="[GUARDIAN] Anti-nuke: permissions stripped",
                        )
                    outcome = f"Stripped {len(removable)} role(s)"
                else:
                    await guild.ban(actor, reason="[GUARDIAN] Anti-nuke (actor already left)", delete_message_days=0)
                    outcome = "Banned (actor had left the server)"
            elif action == "ban":
                await guild.ban(actor, reason="[GUARDIAN] Anti-nuke", delete_message_days=0)
                outcome = "Banned"
            elif action == "kick":
                if member:
                    await member.kick(reason="[GUARDIAN] Anti-nuke")
                    outcome = "Kicked"
                else:
                    outcome = "Actor already gone"
            elif action == "quarantine":
                role = None
                raw_role = settings.get("guardian_nuke_quarantine_role")
                try:
                    role = guild.get_role(int(raw_role)) if raw_role else None
                except (TypeError, ValueError, OverflowError):
                    role = None
                if member and role:
                    await member.add_roles(role, reason="[GUARDIAN] Anti-nuke quarantine")
                    outcome = f"Quarantined with {role.name}"
                else:
                    outcome = "Quarantine failed (member or role missing)"
        except (discord.Forbidden, discord.HTTPException) as exc:
            outcome = f"Response failed: {exc.text or exc.status}"

        embed = discord.Embed(
            title="🛡️ Guardian: nuke attempt stopped",
            description=(
                f"**{actor}** (`{actor.id}`) tripped the **{label.lower()}** tripwire.\n"
                f"**Response:** {outcome}"
            ),
            color=Config.COLOR_ERROR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Tripwire", value=f"{label}: {_threshold(settings, event)} in {_window(settings, event)}s", inline=True)
        embed.add_field(name="Configured action", value=action.title(), inline=True)

        log_channel_id = (
            settings.get("guardian_nuke_log_channel")
            or settings.get("antiraid_log_channel")
            or settings.get("mod_log_channel")
        )
        if log_channel_id:
            try:
                channel = guild.get_channel(int(log_channel_id))
            except (TypeError, ValueError, OverflowError):
                channel = None
            if channel:
                try:
                    await send_log_embed(channel, embed, bot=self.bot)
                except Exception:
                    pass

        async def _clear_cooldown() -> None:
            cooldown = _clamped_int(settings, "guardian_nuke_cooldown_seconds", 60, 10, 3600)
            await asyncio.sleep(cooldown)
            self.nuke_cooldown.discard(guild.id)

        asyncio.create_task(_clear_cooldown())

    # ---------- listeners ----------

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        actor = await self._recent_actor(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        await self._record(channel.guild, "channel_delete", actor)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        actor = await self._recent_actor(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        await self._record(channel.guild, "channel_create", actor)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        actor = await self._recent_actor(role.guild, discord.AuditLogAction.role_delete, role.id)
        await self._record(role.guild, "role_delete", actor)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        actor = await self._recent_actor(guild, discord.AuditLogAction.ban, user.id)
        await self._record(guild, "ban", actor)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Only kicks count; plain leaves have no audit-log entry.
        actor = await self._recent_actor(member.guild, discord.AuditLogAction.kick, member.id, seconds=6)
        if actor:
            await self._record(member.guild, "kick", actor)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        actor = await self._recent_actor(channel.guild, discord.AuditLogAction.webhook_create)
        if actor:
            await self._record(channel.guild, "webhook_create", actor)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        gained = [role for role in after.roles if role not in before.roles and _role_is_dangerous(role)]
        if not gained:
            return
        actor = await self._recent_actor(after.guild, discord.AuditLogAction.member_role_update, after.id)
        await self._record(after.guild, "dangerous_grant", actor)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if _role_is_dangerous(before) or not _role_is_dangerous(after):
            return
        actor = await self._recent_actor(after.guild, discord.AuditLogAction.role_update, after.id)
        await self._record(after.guild, "dangerous_grant", actor)

    # ---------- slash commands ----------

    guardian_group = app_commands.Group(
        name="guardian",
        description="Guardian anti-nuke protection configuration",
    )

    async def _save(self, interaction: discord.Interaction, settings: dict) -> None:
        await self.bot.db.update_settings(interaction.guild_id, settings)

    @guardian_group.command(name="enable", description="Enable Guardian anti-nuke protection")
    @is_admin()
    async def guardian_enable(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["guardian_nuke_enabled"] = True
        await self._save(interaction, settings)
        await interaction.response.send_message("🛡️ Guardian anti-nuke protection **enabled**.", ephemeral=True)

    @guardian_group.command(name="disable", description="Disable Guardian anti-nuke protection")
    @is_admin()
    async def guardian_disable(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["guardian_nuke_enabled"] = False
        await self._save(interaction, settings)
        await interaction.response.send_message("🛡️ Guardian anti-nuke protection **disabled**.", ephemeral=True)

    @guardian_group.command(name="action", description="Set the anti-nuke response action")
    @app_commands.describe(action="What happens to someone who trips a tripwire")
    @app_commands.choices(action=[app_commands.Choice(name=a.title(), value=a) for a in NUKE_ACTIONS])
    @is_admin()
    async def guardian_action(self, interaction: discord.Interaction, action: app_commands.Choice[str]):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["guardian_nuke_action"] = action.value
        await self._save(interaction, settings)
        await interaction.response.send_message(f"🛡️ Anti-nuke response set to **{action.name}**.", ephemeral=True)

    @guardian_group.command(name="quarantine", description="Set the role used by the quarantine response")
    @app_commands.describe(role="Role to apply (omit to clear)")
    @is_admin()
    async def guardian_quarantine(self, interaction: discord.Interaction, role: Optional[discord.Role] = None):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["guardian_nuke_quarantine_role"] = role.id if role else None
        await self._save(interaction, settings)
        await interaction.response.send_message(
            f"🛡️ Quarantine role {'set to ' + role.mention if role else 'cleared'}.", ephemeral=True
        )

    @guardian_group.command(name="tripwire", description="Tune a tripwire threshold and window")
    @app_commands.describe(
        event="Which destructive action to tune",
        threshold="Actions needed to trigger (1-100)",
        window="Seconds the threshold must fill within (5-600)",
    )
    @app_commands.choices(event=[app_commands.Choice(name=v[3], value=k) for k, v in NUKE_EVENTS.items()])
    @is_admin()
    async def guardian_tripwire(
        self,
        interaction: discord.Interaction,
        event: app_commands.Choice[str],
        threshold: Optional[int] = None,
        window: Optional[int] = None,
    ):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        if threshold is not None:
            settings[f"guardian_{event.value}_threshold"] = max(1, min(100, threshold))
        if window is not None:
            settings[f"guardian_{event.value}_window"] = max(5, min(600, window))
        await self._save(interaction, settings)
        await interaction.response.send_message(
            f"🛡️ **{event.name}** tripwire: {_threshold(settings, event.value)} in {_window(settings, event.value)}s.",
            ephemeral=True,
        )

    @guardian_group.command(name="settings", description="View Guardian anti-nuke configuration")
    @is_admin()
    async def guardian_settings(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        enabled = moderation_bool(settings, "guardian_nuke_enabled", False)
        embed = discord.Embed(
            title="🛡️ Guardian: anti-nuke",
            color=Config.COLOR_SUCCESS if enabled else Config.COLOR_ERROR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Status", value="✅ Enabled" if enabled else "❌ Disabled", inline=True)
        embed.add_field(name="Response", value=str(settings.get("guardian_nuke_action", "strip")).title(), inline=True)
        embed.add_field(name="Cooldown", value=f"{_clamped_int(settings, 'guardian_nuke_cooldown_seconds', 60, 10, 3600)}s", inline=True)
        lines = []
        for key, (_, _, _, label) in NUKE_EVENTS.items():
            if not _watch_enabled(settings, key):
                lines.append(f"**{label}:** off")
            else:
                lines.append(f"**{label}:** {_threshold(settings, key)} in {_window(settings, key)}s")
        embed.add_field(name="Tripwires", value="\n".join(lines), inline=False)
        ignored_users = moderation_id_set(settings, "guardian_ignored_users")
        ignored_roles = moderation_id_set(settings, "guardian_ignored_roles")
        embed.add_field(
            name="Trusted bypass",
            value=f"{len(ignored_users)} users · {len(ignored_roles)} roles",
            inline=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Guardian(bot))
