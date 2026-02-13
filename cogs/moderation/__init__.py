import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone
import logging
import json
import re
from config import Config
from utils.checks import is_bot_owner_id

# Mixins
from .extensions.helpers import HelperCommands
from .extensions.chat import ChatCommands
from .extensions.cases import CaseCommands
from .extensions.warnings import WarningCommands
from .extensions.management import ManagementCommands
from .extensions.misc import MiscCommands

logger = logging.getLogger("ModBot.Moderation")

class Moderation(
    commands.Cog,
    HelperCommands,
    ChatCommands,
    CaseCommands,
    WarningCommands,
    ManagementCommands,
    MiscCommands
):
    """Moderation command suite with role hierarchy and permission checks"""
    
    # Top-level moderation command group - class level for auto-registration
    # Named 'moderation' (not 'mod') to avoid collision with standalone commands from mixins
    mod_slash = app_commands.Group(name="moderation", description="🛡️ Moderation commands")
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._hierarchy_cache = {}
        
        # Set up subgroups with parent reference
        self._setup_subgroups()

    def _setup_subgroups(self):
        """Setup subgroups and add commands to them"""
        # Helper to create Command from method
        def cmd(name: str, desc: str, callback):
            command = app_commands.Command(name=name, description=desc, callback=callback)
            return command

        # Chat Subgroup - /moderation chat <command>
        chat_group = app_commands.Group(name="chat", description="?? Chat moderation", parent=self.mod_slash)
        chat_group.add_command(cmd("lock", "Lock a channel", self.lock_slash))
        chat_group.add_command(cmd("unlock", "Unlock a channel", self.unlock_slash))
        chat_group.add_command(cmd("slowmode", "Set channel slowmode", self.slowmode_slash))
        chat_group.add_command(cmd("glock", "Allow only specific role to talk", self.glock_slash))
        chat_group.add_command(cmd("gunlock", "Remove glock restriction", self.gunlock_slash))
        chat_group.add_command(cmd("lockdown", "Lock all channels", self.lockdown_slash))
        chat_group.add_command(cmd("unlockdown", "Unlock all channels", self.unlockdown_slash))
        chat_group.add_command(cmd("nuke", "Clone and delete channel", self.nuke_slash))
        chat_group.add_command(cmd("purge", "Bulk delete messages", self.purge_slash))
        chat_group.add_command(cmd("purgebots", "Delete bot messages", self.purgebots_slash))
        chat_group.add_command(cmd("purgecontains", "Delete messages containing text", self.purgecontains_slash))
        chat_group.add_command(cmd("purgeembeds", "Delete messages with embeds", self.purgeembeds_slash))
        chat_group.add_command(cmd("purgeimages", "Delete messages with images", self.purgeimages_slash))
        chat_group.add_command(cmd("purgelinks", "Delete messages with links", self.purgelinks_slash))

        # Whitelist Subgroup
        whitelist_group = WhitelistGroup(self)
        self.mod_slash.add_command(whitelist_group)

        # Member Management Subgroup - /moderation member <command>
        member_group = app_commands.Group(name="member", description="?? User management", parent=self.mod_slash)
        member_group.add_command(cmd("kick", "Kick a user", self.kick_slash))
        member_group.add_command(cmd("ban", "Ban a user", self.ban_slash))
        member_group.add_command(cmd("unban", "Unban a user", self.unban_slash))
        member_group.add_command(cmd("softban", "Softban a user", self.softban_slash))
        member_group.add_command(cmd("tempban", "Temporarily ban a user", self.tempban_slash))
        member_group.add_command(cmd("mute", "Mute/timeout a user", self.mute_slash))
        member_group.add_command(cmd("unmute", "Unmute a user", self.unmute_slash))
        member_group.add_command(cmd("timeout", "Timeout a user", self.timeout_slash))
        member_group.add_command(cmd("untimeout", "Remove timeout", self.untimeout_slash))
        member_group.add_command(cmd("rename", "Change nickname", self.rename_slash))
        member_group.add_command(cmd("setnick", "Set nickname", self.setnick_slash))
        member_group.add_command(cmd("quarantine", "Quarantine a user", self.quarantine_slash))
        member_group.add_command(cmd("unquarantine", "Unquarantine a user", self.unquarantine_slash))

        # Bulk Operations Subgroup - /moderation bulk <command>
        bulk_group = app_commands.Group(name="bulk", description="?? Bulk operations", parent=self.mod_slash)
        bulk_group.add_command(cmd("massban", "Ban multiple users", self.massban_slash))
        bulk_group.add_command(cmd("banlist", "View banned users", self.banlist_slash))
        bulk_group.add_command(cmd("roleall", "Give role to everyone", self.roleall_slash))
        bulk_group.add_command(cmd("removeall", "Remove role from everyone", self.removeall_slash))
        bulk_group.add_command(cmd("inrole", "List users with role", self.inrole_slash))
        bulk_group.add_command(cmd("nicknameall", "Set nickname for all", self.nicknameall_slash))
        bulk_group.add_command(cmd("resetnicks", "Reset all nicknames", self.resetnicks_slash))

        # Warnings Subgroup - /moderation warn <command>
        warn_group = app_commands.Group(name="warns", description="?? Warning system", parent=self.mod_slash)
        warn_group.add_command(cmd("add", "Warn a user", self.warn_slash))
        warn_group.add_command(cmd("list", "View warnings", self.warnings_slash))
        warn_group.add_command(cmd("delete", "Delete a warning", self.delwarn_slash))
        warn_group.add_command(cmd("clear", "Clear all warnings", self.clearwarnings_slash))

        # Cases Subgroup - /moderation case <command>
        case_group = app_commands.Group(name="cases", description="?? Case management", parent=self.mod_slash)
        case_group.add_command(cmd("view", "View a case", self.case_slash))
        case_group.add_command(cmd("edit", "Edit case reason", self.editcase_slash))
        case_group.add_command(cmd("history", "View user history", self.history_slash))
        case_group.add_command(cmd("modlogs", "View mod logs", self.modlogs_slash))
        case_group.add_command(cmd("note", "Add a note", self.note_slash))
        case_group.add_command(cmd("notes", "View notes", self.notes_slash))
        case_group.add_command(cmd("modstats", "View mod statistics", self.modstats_slash))

        # Top-level shortcuts under /moderation
        self.mod_slash.add_command(cmd("kick", "Kick a user", self.kick_slash))
        self.mod_slash.add_command(cmd("ban", "Ban a user", self.ban_slash))
        self.mod_slash.add_command(cmd("unban", "Unban a user", self.unban_slash))
        self.mod_slash.add_command(cmd("tempban", "Temporarily ban a user", self.tempban_slash))
        self.mod_slash.add_command(cmd("mute", "Mute/timeout a user", self.mute_slash))
        self.mod_slash.add_command(cmd("unmute", "Unmute a user", self.unmute_slash))
        self.mod_slash.add_command(cmd("timeout", "Timeout a user", self.timeout_slash))
        self.mod_slash.add_command(cmd("warn", "Warn a user", self.warn_slash))
        self.mod_slash.add_command(cmd("warnings", "View warnings", self.warnings_slash))
        self.mod_slash.add_command(cmd("delwarn", "Delete a warning", self.delwarn_slash))
        self.mod_slash.add_command(cmd("clearwarnings", "Clear all warnings", self.clearwarnings_slash))
        self.mod_slash.add_command(cmd("case", "View a case", self.case_slash))
        self.mod_slash.add_command(cmd("history", "View user history", self.history_slash))
        self.mod_slash.add_command(cmd("note", "Add a note", self.note_slash))
        self.mod_slash.add_command(cmd("notes", "View notes", self.notes_slash))

        # Misc commands directly on /moderation
        self.mod_slash.add_command(cmd("testwelcome", "Preview welcome card", self.testwelcome))
        self.mod_slash.add_command(cmd("welcomeall", "Welcome all members", self.welcomeall))
        self.mod_slash.add_command(cmd("ownerinfo", "View owner info", self.ownerinfo))
    def cog_check(self, ctx: commands.Context) -> bool:
        return True

    async def cog_load(self):
        """Initialize database table for quarantines and start tasks"""
        async with self.bot.db.get_connection() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS quarantines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    user_id INTEGER,
                    moderator_id INTEGER,
                    reason TEXT,
                    roles_backup TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    active INTEGER DEFAULT 1
                )
            """)
            await db.commit()
        
        if not self.check_quarantine_expiry.is_running():
            self.check_quarantine_expiry.start()

    async def cog_unload(self):
        if self.check_quarantine_expiry.is_running():
            self.check_quarantine_expiry.cancel()
        
        self.bot.tree.remove_command("mod")

    @tasks.loop(minutes=1)
    async def check_quarantine_expiry(self):
        """Check for expired quarantines and restore roles"""
        now = datetime.now(timezone.utc)
        try:
            async with self.bot.db.pool.acquire() as conn:
                async with conn.execute("SELECT id, guild_id, user_id, roles_backup, moderator_id FROM quarantines WHERE active = 1 AND expires_at IS NOT NULL AND expires_at <= ?", (now,)) as cursor:
                    expired = await cursor.fetchall()
            
            for q in expired:
                q_id, guild_id, user_id, roles_backup, mod_id = q
                guild = self.bot.get_guild(guild_id)
                if not guild: continue
                
                try:
                    user = await guild.fetch_member(user_id)
                except:
                    user = None
                
                async with self.bot.db.pool.acquire() as conn:
                    await conn.execute("UPDATE quarantines SET active = 0 WHERE id = ?", (q_id,))
                    await conn.commit()
                
                if user:
                    try:
                        role_ids = json.loads(roles_backup)
                        await self._restore_roles(user, role_ids)
                    except:
                        pass
                        
                    settings = await self.bot.db.get_settings(guild.id)
                    q_role_id = settings.get("automod_quarantine_role_id")
                    if q_role_id:
                        role = guild.get_role(int(q_role_id))
                        if role:
                            try:
                                await user.remove_roles(role, reason="Quarantine expired")
                            except:
                                pass
                    
                    try:
                        embed = discord.Embed(title="✅ Quarantine Expired", description=f"{user.mention} released.", color=0x00ff00)
                        await self.log_action(guild, embed)
                    except:
                        pass
        except Exception as e:
            logger.error(f"Error checking quarantine expiry: {e}")

    @check_quarantine_expiry.before_loop
    async def before_quarantine_check(self):
        await self.bot.wait_until_ready()

    # ==================== REPLY-BASED QUICK ACTIONS ====================

    # Maps embed title keywords to the original action type
    _TITLE_TO_ACTION = {
        # Moderation core titles
        "banned": "ban",
        "temporarily banned": "tempban",
        "softbanned": "softban",
        "kicked": "kick",
        "muted": "mute",
        "quarantined": "quarantine",
        "warned": "warn",
        "unmuted": "unmute",
        "unbanned": "unban",
        "unquarantined": "unquarantine",
        # AI moderation titles/phrases
        "member banned": "ban",
        "user banned": "ban",
        "member kicked": "kick",
        "user kicked": "kick",
        "member warned": "warn",
        "user warned": "warn",
        "member timed out": "mute",
        "timed out": "mute",
        "timeout removed": "unmute",
        "remove timeout": "unmute",
        "user unbanned": "unban",
        "member unbanned": "unban",
    }

    # Reply shortcuts → what action to perform
    _REPLY_COMMANDS = {
        # Undo / reverse
        "undo":         "undo",
        "reverse":      "undo",
        "revert":       "undo",
        # Direct actions
        "unban":        "unban",
        "unmute":       "unmute",
        "untimeout":    "unmute",
        "unquar":       "unquarantine",
        "unquarantine": "unquarantine",
        "unwarn":       "unwarn",
        "delwarn":      "unwarn",
        # Escalation — reply to any mod embed to escalate
        "ban":          "ban",
        "kick":         "kick",
        "mute":         "mute",
        "timeout":      "mute",
        "quarantine":   "quarantine",
        "quar":         "quarantine",
        "warn":         "warn",
    }

    # What "undo" means for each action type
    _UNDO_MAP = {
        "ban":          "unban",
        "tempban":      "unban",
        "mute":         "unmute",
        "quarantine":   "unquarantine",
        "warn":         "unwarn",
        # These can't really be undone
        "kick":         None,
        "softban":      None,
    }

    _REPLY_REASON_PLACEHOLDERS = frozenset({
        "him",
        "her",
        "them",
        "that",
        "this",
        "it",
        "user",
        "member",
        "person",
        "guy",
    })

    def _extract_user_id(self, embed: discord.Embed) -> int | None:
        """Extract target user ID from a mod embed."""
        # Check User-like fields first (standard mod embeds)
        for field in embed.fields:
            if field.name and field.value and field.name.lower() in {"user", "member", "target"}:
                match = re.search(r'(\d{17,20})', field.value)
                if match:
                    return int(match.group(1))

        # Some embeds store target in footer: "Case #5 • User ID: 123..."
        if embed.footer and embed.footer.text:
            match = re.search(r"user\s*id\s*[:#]?\s*(\d{17,20})", embed.footer.text, flags=re.IGNORECASE)
            if match:
                return int(match.group(1))

        # Fallback: scan every field value for a snowflake-like ID.
        for field in embed.fields:
            if not field.value:
                continue
            match = re.search(r'(\d{17,20})', field.value)
            if match:
                return int(match.group(1))

        # Check description (quarantine embeds use mention in description)
        if embed.description:
            match = re.search(r'<@!?(\d{17,20})>', embed.description)
            if match:
                return int(match.group(1))
        return None

    def _detect_action(self, embed: discord.Embed) -> str | None:
        """Detect what mod action an embed represents from its title."""
        if not embed.title:
            return None
        title = embed.title.lower()
        for keyword, action in self._TITLE_TO_ACTION.items():
            if keyword in title:
                return action
        return None

    def _normalize_reply_reason(self, raw_reason: str) -> str:
        """Sanitize quick-reply reason text and drop placeholder words like 'him'."""
        reason = (raw_reason or "").strip()
        if not reason:
            return "Reply action"

        # Strip wrapping punctuation/quotes.
        reason = reason.strip("`'\"“”‘’.,:;!?- ").strip()
        if not reason:
            return "Reply action"

        # Common pattern: "for spam" / "because spam".
        reason = re.sub(r"^(?:for|because)\s+", "", reason, flags=re.IGNORECASE).strip()
        if not reason:
            return "Reply action"

        # Pattern: "him for spam" => "spam"
        pronoun_lead = re.match(
            r"^(him|her|them|that|this|it|user|member|person|guy)\b(?:\s+(?:for|because)\b)?\s*(.*)$",
            reason,
            flags=re.IGNORECASE,
        )
        if pronoun_lead:
            tail = pronoun_lead.group(2).strip()
            if tail:
                reason = tail
            else:
                return "Reply action"

        compact = re.sub(r"[\W_]+", "", reason).lower()
        if not compact or compact in self._REPLY_REASON_PLACEHOLDERS:
            return "Reply action"
        return reason

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle reply-based quick actions on mod embeds."""
        # Ignore bots, DMs, or messages without a reply reference
        if message.author.bot or not message.guild or not message.reference:
            return

        # Only process short reply commands with optional reason text.
        raw_parts = message.content.strip().split()
        if not raw_parts or len(raw_parts) > 8:
            return
        content = [p.lower() for p in raw_parts]

        cmd = content[0]
        if cmd not in self._REPLY_COMMANDS:
            return

        # Resolve the replied-to message
        try:
            ref_msg = message.reference.resolved
            if ref_msg is None:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
        except (discord.NotFound, discord.HTTPException):
            return

        # Two modes:
        # 1. Reply to a bot mod embed → extract target from embed, support "undo"
        # 2. Reply to any user's message → target = that message's author
        target_id = None
        original_action = None

        if ref_msg.author.id == self.bot.user.id and ref_msg.embeds:
            # Replying to a bot embed — detect action for undo, always extract target
            embed = ref_msg.embeds[0]
            original_action = self._detect_action(embed)
            target_id = self._extract_user_id(embed)
        
        if target_id is None and ref_msg.author.id != self.bot.user.id:
            # Replying to a regular user's message — target is that user
            target_id = ref_msg.author.id
            original_action = None  # No "undo" context for direct replies

        if target_id is None:
            try:
                await message.reply(
                    embed=discord.Embed(
                        title="⚠️ Could Not Resolve Target",
                        description="I couldn't find a target user ID in the replied message. Reply to a moderation embed that includes the target user.",
                        color=discord.Color.orange(),
                    ),
                    delete_after=10,
                )
            except discord.HTTPException:
                pass
            return

        # Check staff permissions
        member = message.author
        mod_level = await self.get_user_level(message.guild.id, member)
        has_discord_staff_perm = (
            member.id == message.guild.owner_id
            or is_bot_owner_id(member.id)
            or member.guild_permissions.manage_messages
        )
        if mod_level < 4 and not has_discord_staff_perm:  # At least Mod level (or fallback Discord perm)
            try:
                await message.reply(
                    embed=discord.Embed(
                        title="❌ Permission Denied",
                        description="You need at least **Moderator** level to use reply actions.",
                        color=discord.Color.red()
                    ),
                    delete_after=10
                )
            except discord.HTTPException:
                pass
            return

        # Determine what action to take
        requested = self._REPLY_COMMANDS[cmd]
        if requested == "undo":
            if original_action is None:
                try:
                    await message.reply(
                        embed=discord.Embed(
                            title="⚠️ Cannot Undo",
                            description="Reply to a **bot moderation embed** to use undo.",
                            color=discord.Color.orange()
                        ),
                        delete_after=10
                    )
                except discord.HTTPException:
                    pass
                return
            action_to_take = self._UNDO_MAP.get(original_action)
            if action_to_take is None:
                try:
                    await message.reply(
                        embed=discord.Embed(
                            title="⚠️ Cannot Undo",
                            description=f"**{original_action.title()}** actions cannot be automatically undone.",
                            color=discord.Color.orange()
                        ),
                        delete_after=10
                    )
                except discord.HTTPException:
                    pass
                return
        else:
            action_to_take = requested

        # Parse optional reason from reply (e.g. "ban toxic behavior")
        reason = self._normalize_reply_reason(" ".join(raw_parts[1:]))

        # Execute the action
        try:
            await self._execute_reply_action(message, action_to_take, target_id, reason)
        except Exception as e:
            logger.error(f"Reply action error: {e}", exc_info=True)
            try:
                await message.reply(
                    embed=discord.Embed(
                        title="❌ Error",
                        description=f"Failed to execute: `{e}`",
                        color=discord.Color.red()
                    ),
                    delete_after=15
                )
            except discord.HTTPException:
                pass

    async def _execute_reply_action(self, message: discord.Message, action: str, target_id: int, reason: str):
        """Execute a mod action from a reply."""
        guild = message.guild

        if action in ("unban",):
            # Unban works with user ID directly
            await self._unban_logic(message, target_id, reason)
            return

        # For member-based actions, fetch the member
        try:
            target = await guild.fetch_member(target_id)
        except discord.NotFound:
            if action == "ban":
                # Can ban even if they left
                try:
                    user = await self.bot.fetch_user(target_id)
                    await guild.ban(user, reason=f"[Reply Action] {message.author}: {reason}")
                    await message.reply(
                        embed=discord.Embed(
                            title="🔨 User Banned",
                            description=f"<@{target_id}> has been banned.",
                            color=discord.Color.red()
                        )
                    )
                except Exception as e:
                    await message.reply(
                        embed=discord.Embed(
                            title="❌ Failed",
                            description=f"Could not ban: {e}",
                            color=discord.Color.red()
                        ),
                        delete_after=10
                    )
                return
            await message.reply(
                embed=discord.Embed(
                    title="⚠️ User Not Found",
                    description="That user is no longer in the server.",
                    color=discord.Color.orange()
                ),
                delete_after=10
            )
            return
        except discord.HTTPException:
            return

        # Dispatch to existing logic methods
        dispatch = {
            "unmute":        lambda: self._unmute_logic(message, target, reason),
            "unquarantine":  lambda: self._unquarantine_logic(message, target, reason),
            "unwarn":        lambda: self._delete_latest_warn(message, target),
            "ban":           lambda: self._ban_logic(message, target, reason),
            "kick":          lambda: self._kick_logic(message, target, reason),
            "mute":          lambda: self._mute_logic(message, target, "1h", reason),
            "quarantine":    lambda: self._quarantine_logic(message, target, None, reason),
            "warn":          lambda: self._warn_logic(message, target, reason),
        }

        handler = dispatch.get(action)
        if handler:
            await handler()
        else:
            await message.reply(
                embed=discord.Embed(
                    title="⚠️ Unknown Action",
                    description=f"Action `{action}` is not supported as a reply action.",
                    color=discord.Color.orange()
                ),
                delete_after=10
            )

    async def _delete_latest_warn(self, source, user: discord.Member):
        """Delete the most recent warning for a user (used by reply 'unwarn')."""
        try:
            warnings = await self.bot.db.get_warnings(source.guild.id, user.id)
            if not warnings:
                await source.reply(
                    embed=discord.Embed(
                        title="ℹ️ No Warnings",
                        description=f"{user.mention} has no warnings to remove.",
                        color=discord.Color.blue()
                    ),
                    delete_after=10
                )
                return
            latest = warnings[-1]
            warn_id = latest.get("id") or latest.get("warning_id")
            if warn_id:
                await self.bot.db.delete_warning(source.guild.id, warn_id)
            await source.reply(
                embed=discord.Embed(
                    title="✅ Warning Removed",
                    description=f"Removed the latest warning from {user.mention}.",
                    color=discord.Color.green()
                )
            )
        except Exception as e:
            await source.reply(
                embed=discord.Embed(
                    title="❌ Error",
                    description=f"Could not remove warning: {e}",
                    color=discord.Color.red()
                ),
                delete_after=10
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle new member joins (Whitelist & Welcome)"""
        if member.bot: 
            return # Optionally skip bots for welcome? Original skipped bot for whitelist.
        
        settings = await self.bot.db.get_settings(member.guild.id)
        
        # Whitelist Check
        if settings.get("whitelist_mode"):
            whitelisted_ids = settings.get("whitelisted_ids", [])
            if member.id not in whitelisted_ids and not member.bot:
                try:
                    await member.dm_channel.send(f"🔒 **{member.guild.name}** is currently in whitelist-only mode. You are not on the whitelist.")
                except:
                    pass
                
                try:
                    await member.kick(reason="Whitelist mode active - User not whitelisted")
                    # Log it
                    embed = discord.Embed(title="🔒 User Kicked (Whitelist)", color=0xff0000)
                    embed.add_field(name="User", value=f"{member} ({member.id})")
                    await self.log_action(member.guild, embed)
                    return # Stop processing
                except Exception as e:
                    logger.error(f"Failed to kick non-whitelisted user {member.id}: {e}")

            # Assign whitelist role if configured and user is allowed
            role_id = settings.get("whitelisted_role")
            if role_id:
                role = member.guild.get_role(int(role_id))
                if role:
                    try:
                        await member.add_roles(role, reason="Whitelist role auto-assign")
                    except:
                        pass
        
        # Welcome Message
        channel_id = settings.get("welcome_channel")
        if channel_id:
            channel = member.guild.get_channel(int(channel_id))
            if channel and isinstance(channel, discord.TextChannel):
                await self._send_welcome_message(member=member, channel=channel)


# Helper Class for whitelist group if not in management.py
class WhitelistGroup(app_commands.Group):
    def __init__(self, cog: Moderation):
        super().__init__(name="whitelist", description="Manage server whitelist")
        self.cog = cog

    @app_commands.command(name="enable", description="Enable whitelist mode (lock server)")
    async def enable(self, interaction: discord.Interaction):
        await self.cog._toggle_whitelist_mode(interaction, True)

    @app_commands.command(name="disable", description="Disable whitelist mode")
    async def disable(self, interaction: discord.Interaction):
        await self.cog._toggle_whitelist_mode(interaction, False)

    @app_commands.command(name="add", description="Add user to whitelist")
    async def add(self, interaction: discord.Interaction, user: discord.Member):
        await self.cog._whitelist_logic(interaction, user)

    @app_commands.command(name="remove", description="Remove user from whitelist")
    async def remove(self, interaction: discord.Interaction, user: discord.Member):
        await self.cog._unwhitelist_logic(interaction, user)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
