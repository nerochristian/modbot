"""
Advanced Moderation System
Comprehensive moderation toolkit with hierarchy checks, logging, and database integration
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
from typing import Optional
import asyncio
import aiohttp
import re
import io
import json
import logging
from urllib.parse import urlparse
from pathlib import Path

from utils.embeds import ModEmbed, Colors
from utils.checks import is_mod, is_admin, is_senior_mod, is_bot_owner_id, get_owner_ids
from utils.logging import send_log_embed
from utils.time_parser import parse_time
from utils.welcome_card import WelcomeCardOptions, build_welcome_card_file
from config import Config

logger = logging.getLogger(__name__)

TUTORIAL_VIDEO_URL = "https://cdn.discordapp.com/attachments/1430639019582034013/1454243445207208170/2025-12-26_17-43-35.mp4?ex=6950613f&is=694f0fbf&hm=326c7fa1fc65f79d8585b2084febb11771e531d778f682347a622abe95b22df6"
ADD_EMOJI_TUTORIAL_GIF_URL = "https://s7.ezgif.com/tmp/ezgif-78fb32957f0983d1.gif"
ADD_EMOJI_TUTORIAL_GIF_FILENAME = "addemoji_tutorial.gif"
ADD_EMOJI_TUTORIAL_GIF_PATH = Path(__file__).resolve().parents[1] / "assets" / ADD_EMOJI_TUTORIAL_GIF_FILENAME
# Legacy single-server fallback. Prefer per-guild `emoji_command_channel` in DB settings.
EMOJI_COMMAND_CHANNEL_ID = 0

_TUTORIAL_VIDEO_BYTES: Optional[bytes] = None
_TUTORIAL_VIDEO_LOCK = asyncio.Lock()
_ADD_EMOJI_TUTORIAL_GIF_BYTES: Optional[bytes] = None
_ADD_EMOJI_TUTORIAL_GIF_LOCK = asyncio.Lock()


class EmojiApprovalView(discord.ui.LayoutView):
    def __init__(
        self,
        cog: "Moderation",
        *,
        requester_id: int,
        emoji_name: str,
        emoji_url: str,
    ) -> None:
        super().__init__(timeout=60 * 60 * 24)  # 24h
        self._cog = cog
        self._requester_id = requester_id
        self._emoji_name = emoji_name
        self._emoji_url = emoji_url
        self._handled = False
        self.message: Optional[discord.Message] = None
        self._text = discord.ui.TextDisplay(self._render(status="Pending", note="Awaiting admin decision"))

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("**Emoji Approval Request**"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                self._text,
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.MediaGallery(discord.MediaGalleryItem(self._emoji_url)),
                accent_color=discord.Color.blurple().value,
            )
        )

        approve_button = discord.ui.Button(label="Approve", style=discord.ButtonStyle.success)
        reject_button = discord.ui.Button(label="Reject", style=discord.ButtonStyle.danger)

        async def _approve(interaction: discord.Interaction):
            return await self.approve(interaction, approve_button)

        async def _reject(interaction: discord.Interaction):
            return await self.reject(interaction, reject_button)

        approve_button.callback = _approve
        reject_button.callback = _reject

        self.add_item(approve_button)
        self.add_item(reject_button)

    def _render(self, *, status: str, note: str) -> str:
        return (
            f"**Requested By:** <@{self._requester_id}>\n"
            f"**Emoji Name:** `:{self._emoji_name}:`\n"
            f"**URL:** {self._emoji_url}\n"
            f"**Status:** {status}\n"
            f"**Note:** {note}"
        )

    def _can_act(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        member = interaction.user
        return bool(
            getattr(member, "guild_permissions", None)
            and member.guild_permissions.administrator
        ) or bool(
            member.id == interaction.guild.owner_id or is_bot_owner_id(member.id)
        )

    async def _disable_all(self) -> None:
        for child in self.children:
            try:
                child.disabled = True  # type: ignore[attr-defined]
            except Exception:
                continue

    async def _update_status(
        self,
        interaction: discord.Interaction,
        *,
        status: str,
        note: str,
    ) -> None:
        self._text.content = self._render(status=status, note=note)
        await self._disable_all()
        msg = interaction.message or self.message
        if msg:
            try:
                await msg.edit(view=self)
            except Exception:
                pass

    async def on_timeout(self) -> None:
        await self._disable_all()
        if not self.message:
            return
        try:
            self._text.content = self._render(
                status="Expired",
                note="No decision within 24 hours",
            )
            await self.message.edit(view=self)
        except Exception:
            pass

    async def approve(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not self._can_act(interaction):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "Administrator required."),
                ephemeral=True,
            )
        if self._handled:
            return await interaction.response.send_message(
                "Already handled.", ephemeral=True
            )
        self._handled = True

        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return

        try:
            emoji = await self._cog._create_emoji_from_url(
                guild=guild,
                name=self._emoji_name,
                url=self._emoji_url,
                reason=f"Approved by {interaction.user} (requested by {self._requester_id})",
            )
        except Exception as e:
            await self._update_status(
                interaction,
                status="Failed",
                note=f"Create failed: `{type(e).__name__}`",
            )
            return await interaction.followup.send(
                embed=ModEmbed.error(
                    "Failed", f"Could not add emoji: `{type(e).__name__}`"
                ),
                ephemeral=True,
            )

        await self._update_status(
            interaction,
            status="Approved",
            note=f"Added {emoji} as `:{emoji.name}:`",
        )
        return await interaction.followup.send(
            embed=ModEmbed.success(
                "Approved", f"Emoji added: {emoji} as `:{emoji.name}:`"
            ),
            ephemeral=True,
        )

    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not self._can_act(interaction):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "Administrator required."),
                ephemeral=True,
            )
        if self._handled:
            return await interaction.response.send_message(
                "Already handled.", ephemeral=True
            )
        self._handled = True
        await interaction.response.defer(ephemeral=True)

        await self._update_status(
            interaction,
            status="Rejected",
            note=f"Rejected by {interaction.user.mention}",
        )
        return await interaction.followup.send("Rejected.", ephemeral=True)


async def _fetch_tutorial_video_file() -> discord.File:
    global _TUTORIAL_VIDEO_BYTES

    if _TUTORIAL_VIDEO_BYTES is None:
        async with _TUTORIAL_VIDEO_LOCK:
            if _TUTORIAL_VIDEO_BYTES is None:
                max_bytes = 24 * 1024 * 1024
                timeout = aiohttp.ClientTimeout(total=30)
                data = bytearray()

                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(TUTORIAL_VIDEO_URL) as response:
                        if response.status != 200:
                            raise ValueError("fetch_failed")
                        async for chunk in response.content.iter_chunked(64 * 1024):
                            data.extend(chunk)
                            if len(data) > max_bytes:
                                raise ValueError("file_too_large")

                _TUTORIAL_VIDEO_BYTES = bytes(data)

    return discord.File(io.BytesIO(_TUTORIAL_VIDEO_BYTES), filename="tutorial.mp4")


async def _fetch_addemoji_tutorial_gif_file() -> Optional[discord.File]:
    global _ADD_EMOJI_TUTORIAL_GIF_BYTES

    if not ADD_EMOJI_TUTORIAL_GIF_PATH.exists():
        return None

    if _ADD_EMOJI_TUTORIAL_GIF_BYTES is None:
        async with _ADD_EMOJI_TUTORIAL_GIF_LOCK:
            if _ADD_EMOJI_TUTORIAL_GIF_BYTES is None:
                _ADD_EMOJI_TUTORIAL_GIF_BYTES = await asyncio.to_thread(ADD_EMOJI_TUTORIAL_GIF_PATH.read_bytes)

    return discord.File(io.BytesIO(_ADD_EMOJI_TUTORIAL_GIF_BYTES), filename=ADD_EMOJI_TUTORIAL_GIF_FILENAME)


class AddEmojiTutorialView(discord.ui.View):
    def __init__(self, *, requester_id: int):
        super().__init__(timeout=15 * 60)
        self._requester_id = requester_id

    @discord.ui.button(label="Tutorial", style=discord.ButtonStyle.secondary)
    async def tutorial(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self._requester_id:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not For You", "Only the person who ran `/emoji` can use this button."),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            video = await _fetch_tutorial_video_file()
            return await interaction.followup.send(file=video, ephemeral=True)
        except ValueError as e:
            if str(e) == "file_too_large":
                return await interaction.followup.send(
                    content=f"Tutorial video is too large to upload. Here is the link:\n{TUTORIAL_VIDEO_URL}",
                    ephemeral=True,
                )
            return await interaction.followup.send(
                content=f"Couldn't fetch the tutorial video. Here is the link:\n{TUTORIAL_VIDEO_URL}",
                ephemeral=True,
            )
        except Exception:
            return await interaction.followup.send(
                content=f"Couldn't fetch the tutorial video. Here is the link:\n{TUTORIAL_VIDEO_URL}",
                ephemeral=True,
            )


class ModerationError(Exception):
    """Custom exception for moderation-related errors"""
    pass


class Moderation(commands.Cog):
    """Moderation command suite with role hierarchy and permission checks"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._hierarchy_cache = {}

    async def cog_load(self):
        """Initialize database table for quarantines"""
        try:
            # Create quarantines table if it doesn't exist
            async with self.bot.db.get_connection() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS quarantines (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        moderator_id INTEGER NOT NULL,
                        roles_backup TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        expires_at TEXT,
                        reason TEXT,
                        active INTEGER DEFAULT 1
                    )
                """)
                await conn.commit()
            
            # Start background task
            if not self.check_quarantine_expiry.is_running():
                self.check_quarantine_expiry.start()
            
            logger.info("Quarantine system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize quarantine system: {e}")

    async def cog_unload(self):
        """Cleanup when cog is unloaded"""
        if self.check_quarantine_expiry.is_running():
            self.check_quarantine_expiry.cancel()

    @tasks.loop(minutes=1)
    async def check_quarantine_expiry(self):
        """Background task to check for expired quarantines"""
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            async with self.bot.db.get_connection() as conn:
                # Get all expired quarantines
                async with conn.execute("""
                    SELECT id, guild_id, user_id, roles_backup, moderator_id
                    FROM quarantines
                    WHERE active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
                """, (now,)) as cursor:
                    expired = await cursor.fetchall()
            
                for quarantine in expired:
                    q_id, guild_id, user_id, roles_json, mod_id = quarantine
                    
                    try:
                        # Get guild and member
                        guild = self.bot.get_guild(guild_id)
                        if not guild:
                            continue
                        
                        member = guild.get_member(user_id)
                        if not member:
                            # User left - just mark as inactive
                            await conn.execute(
                                "UPDATE quarantines SET active = 0 WHERE id = ?", (q_id,)
                            )
                            await conn.commit()
                            continue
                        
                        # Restore roles
                        role_ids = json.loads(roles_json)
                        await self._restore_roles(member, role_ids)
                        
                        # Remove quarantine role
                        settings = await self.bot.db.get_settings(guild_id)
                        quar_role_id = settings.get('quarantine_role')
                        if quar_role_id:
                            quar_role = guild.get_role(quar_role_id)
                            if quar_role and quar_role in member.roles:
                                try:
                                    await member.remove_roles(quar_role, reason="Quarantine expired")
                                except:
                                    pass
                        
                        # Mark as inactive
                        await conn.execute(
                            "UPDATE quarantines SET active = 0 WHERE id = ?", (q_id,)
                        )
                        await conn.commit()
                        
                        # Log action
                        embed = discord.Embed(
                            title="🔓 Quarantine Expired",
                            description=f"{member.mention}'s quarantine has automatically expired.",
                            color=Colors.SUCCESS,
                            timestamp=datetime.now(timezone.utc)
                        )
                        embed.add_field(name="User", value=f"{member.mention} (`{user_id}`)", inline=True)
                        await self.log_action(guild, embed)
                        
                        # DM user
                        dm_embed = discord.Embed(
                            title=f"🔓 Quarantine Lifted in {guild.name}",
                            description="Your temporary quarantine has expired and your roles have been restored.",
                            color=Colors.SUCCESS
                        )
                        await self.dm_user(member, dm_embed)
                        
                    except Exception as e:
                        logger.error(f"Error processing expired quarantine {q_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in quarantine expiry check: {e}")

    @check_quarantine_expiry.before_loop
    async def before_quarantine_check(self):
        """Wait until bot is ready before starting the task"""
        await self.bot.wait_until_ready()

    # ==================== QUARANTINE HELPER METHODS ====================

    async def _backup_roles(self, user: discord.Member) -> list[int]:
        """Backup user roles (excluding @everyone and quarantine role)"""
        settings = await self.bot.db.get_settings(user.guild.id)
        quarantine_role_id = settings.get('quarantine_role')
        
        role_ids = []
        for role in user.roles:
            # Skip @everyone and quarantine role
            if role.id == user.guild.id or role.id == quarantine_role_id:
                continue
            role_ids.append(role.id)
        
        return role_ids

    async def _restore_roles(self, user: discord.Member, role_ids: list[int]) -> tuple[int, int]:
        """Restore roles to user, returns (restored_count, failed_count)"""
        restored = 0
        failed = 0
        roles_to_add = []
        
        # Get bot member for hierarchy check
        bot_member = user.guild.me
        if not bot_member:
            try:
                bot_member = user.guild.get_member(self.bot.user.id)
            except:
                pass
        
        for role_id in role_ids:
            role = user.guild.get_role(role_id)
            if not role:
                failed += 1
                continue
                
            # Skip if user already has role
            if role in user.roles:
                continue

            # Check hierarchy
            if bot_member and bot_member.top_role <= role:
                logger.warning(f"Cannot restore role {role.name} to {user}: role higher than bot.")
                failed += 1
                continue
                
            roles_to_add.append(role)
        
        if roles_to_add:
            try:
                # Batch add for efficiency (1 API call)
                await user.add_roles(*roles_to_add, reason="Quarantine lifted")
                restored = len(roles_to_add)
            except Exception as e:
                logger.error(f"Failed to batch restore roles for {user}: {e}")
                # Fallback to one-by-one on error
                for role in roles_to_add:
                    try:
                        await user.add_roles(role, reason="Quarantine lifted (fallback)")
                        restored += 1
                    except Exception as inner_e:
                        logger.error(f"Failed to restore specific role {role.id}: {inner_e}")
                        failed += 1
                        
        return restored, failed

    async def _get_active_quarantine(self, guild_id: int, user_id: int) -> Optional[dict]:
        """Get active quarantine record from database"""
        try:
            async with self.bot.db.get_connection() as conn:
                async with conn.execute("""
                    SELECT id, guild_id, user_id, moderator_id, roles_backup, started_at, expires_at, reason
                    FROM quarantines
                    WHERE guild_id = ? AND user_id = ? AND active = 1
                """, (guild_id, user_id)) as cursor:
                    row = await cursor.fetchone()
                
            if not row:
                return None
            
            return {
                'id': row[0],
                'guild_id': row[1],
                'user_id': row[2],
                'moderator_id': row[3],
                'roles_backup': row[4],
                'started_at': row[5],
                'expires_at': row[6],
                'reason': row[7]
            }
        except Exception as e:
            logger.error(f"Error getting quarantine: {e}")
            return None


    # ==================== UTILITY METHODS ====================

    async def get_user_level(self, guild_id: int, member: discord.Member) -> int:
        """
        Get the hierarchy level of a user based on roles
        Returns: int (0-999, higher = more power)
        """
        cache_key = f"{guild_id}:{member.id}"
        
        # Check cache first
        if cache_key in self._hierarchy_cache:
            cached_time, level = self._hierarchy_cache[cache_key]
            if (datetime.now() - cached_time).seconds < 300:  # 5min cache
                return level
        
        # Dot role = HIGHEST level (above all)
        dot_role = discord.utils.get(member.roles, name=".")
        if dot_role:
            self._hierarchy_cache[cache_key] = (datetime.now(), 999)
            return 999
        
        # Bot owner = max level
        if await self._is_bot_owner(member):
            self._hierarchy_cache[cache_key] = (datetime.now(), 100)
            return 100
        
        # Server owner = max level
        if member.id == member.guild.owner_id:
            return 100
        
        # Check role hierarchy from settings
        settings = await self.bot.db.get_settings(guild_id)
        user_role_ids = {r.id for r in member.roles}
        
        role_hierarchy = {
            'manager_role': 8,
            'admin_role': 7,
            'supervisor_role': 6,
            'senior_mod_role': 5,
            'mod_role': 4,
            'trial_mod_role': 3,
            'staff_role': 2
        }
        
        for role_key, level in role_hierarchy.items():
            if settings.get(role_key) in user_role_ids:
                self._hierarchy_cache[cache_key] = (datetime.now(), level)
                return level
        
        return 0

    async def can_moderate(
        self,
        guild_id: int,
        moderator: discord.Member,
        target: discord.Member
    ) -> tuple[bool, str]:
        """
        Check if moderator can take action on target
        Returns: (bool, error_message)
        """
        moderator_is_owner = await self._is_bot_owner(moderator)

        # Self-check (bot owners only)
        if moderator.id == target.id:
            if moderator_is_owner:
                return True, ""
            return False, "You cannot moderate yourself."

        target_is_owner = await self._is_bot_owner(target)

        # Protect bot owner(s)
        if target_is_owner and not moderator_is_owner:
            return False, "You cannot moderate the bot owner."

        # Bot owner override (still subject to Discord's own limitations)
        if moderator_is_owner:
            return True, ""

        # Server owner override
        if moderator.id == moderator.guild.owner_id:
            return True, ""
        
        # Owner check
        if target.id == target.guild.owner_id:
            return False, "You cannot moderate the server owner."
        
        # Bot check - only block if bot has higher role AND moderator isn't high-level staff
        if target.bot:
            mod_level = await self.get_user_level(guild_id, moderator)
            if mod_level < 6 and target.top_role >= moderator.top_role:  # Supervisor+ can mod bots
                return False, "You cannot moderate this bot (role hierarchy)."
        
        # Hierarchy level check - THIS IS THE MAIN CHECK
        mod_level = await self.get_user_level(guild_id, moderator)
        target_level = await self.get_user_level(guild_id, target)
        
        # Higher level staff can moderate lower level staff
        if mod_level > target_level:
            return True, ""
        
        if mod_level <= target_level and target_level > 0:
            return False, "You cannot moderate this user. They have equal or higher permissions."
        
        # For non-staff targets, allow if moderator has any staff level
        if mod_level > 0:
            return True, ""
        
        return False, "You don't have moderation permissions."

    async def can_bot_moderate(
        self,
        target: discord.Member,
        *,
        moderator: Optional[discord.Member] = None,
    ) -> tuple[bool, str]:
        """Check if the bot has permission to moderate target (role hierarchy)."""
        guild = target.guild
        bot_member = guild.me
        if bot_member is None and getattr(self.bot, "user", None) is not None:
            bot_member = guild.get_member(self.bot.user.id)

        # Hard Discord limitation
        if target.id == guild.owner_id:
            return False, "I cannot moderate the server owner."

        # If we can't reliably determine hierarchy, allow the attempt and handle Forbidden later.
        if bot_member is None:
            return True, ""

        # Let the bot owner attempt actions even if the pre-check thinks hierarchy blocks it.
        # This helps avoid false negatives when member/role cache is stale.
        if moderator is not None and await self._is_bot_owner(moderator):
            return True, ""

        if target.top_role >= bot_member.top_role:
            return (
                False,
                "I cannot moderate this user. Their highest role "
                f"({target.top_role.mention}) is higher than or equal to mine "
                f"({bot_member.top_role.mention}).",
            )

        return True, ""

    async def log_action(self, guild: discord.Guild, embed: discord.Embed, log_type: str = "mod") -> None:
        """
        Log moderation action to configured channel
        log_type: "mod", "voice", or "audit"
        """
        try:
            settings = await self.bot.db.get_settings(guild.id)
            
            # Determine which log channel to use
            if log_type == "voice":
                log_channel_id = settings.get('voice_log_channel')
            elif log_type == "audit":
                log_channel_id = settings.get('audit_log_channel')
            else:
                log_channel_id = settings.get('mod_log_channel')
            
            if not log_channel_id:
                return
            
            channel = guild.get_channel(log_channel_id)
            if not channel:
                logger.warning(f"{log_type.capitalize()} log channel {log_channel_id} not found in {guild.name}")
                return
            
            await send_log_embed(channel, embed)
            
        except discord.Forbidden:
            logger.error(f"Missing permissions to log in {guild.name}")
        except Exception as e:
            logger.error(f"Failed to log action in {guild.name}: {e}")

    async def dm_user(self, user: discord.User, embed: discord.Embed) -> bool:
        """
        Attempt to DM a user
        Returns: bool indicating success
        """
        try:
            await user.send(embed=embed)
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False

    async def create_mod_embed(
        self,
        title: str,
        user: discord.User | discord.Member,
        moderator: discord.User | discord.Member,
        reason: str,
        color: int,
        case_num: Optional[int] = None,
        extra_fields: Optional[dict[str, str]] = None
    ) -> discord.Embed:
        """Create standardized moderation embed"""
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="User", value=f"{user.mention} (`{user.id}`)", inline=True)
        embed.add_field(name="Moderator", value=moderator.mention, inline=True)
        
        if extra_fields:
            for field_name, field_value in extra_fields.items():
                embed.add_field(name=field_name, value=field_value, inline=True)
        
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)
        
        if case_num:
            embed.set_footer(text=f"Case #{case_num}")
        
        return embed

    async def _respond(
        self,
        source: discord.Interaction | commands.Context,
        *,
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
        ephemeral: bool = False,
    ):
        """Send a response or followup depending on whether the interaction/context is already acknowledged."""
        try:
            if isinstance(source, discord.Interaction):
                if source.response.is_done():
                    return await source.followup.send(
                        content=content, embed=embed, ephemeral=ephemeral
                    )
                return await source.response.send_message(
                    content=content, embed=embed, ephemeral=ephemeral
                )
            else:
                # Context
                return await source.reply(content=content, embed=embed)
        except discord.HTTPException:
            # Fallback when the interaction state changed mid-execution.
            if isinstance(source, discord.Interaction):
                try:
                    return await source.followup.send(
                        content=content, embed=embed, ephemeral=ephemeral
                    )
                except Exception:
                    pass

    async def _kick_logic(self, source, user: discord.Member, reason: str):
        guild = source.guild
        moderator = source.user if isinstance(source, discord.Interaction) else source.author
        
        can_mod, error = await self.can_moderate(guild.id, moderator, user)
        if not can_mod:
            return await self._respond(source, embed=ModEmbed.error("Cannot Kick", error), ephemeral=True)
            
        can_bot, bot_error = await self.can_bot_moderate(user, moderator=moderator)
        if not can_bot:
            return await self._respond(source, embed=ModEmbed.error("Bot Permission Error", bot_error), ephemeral=True)
            
        case_num = await self.bot.db.create_case(guild.id, user.id, moderator.id, "Kick", reason)
        
        dm_embed = discord.Embed(title=f"👢 Kicked from {guild.name}", description=f"**Reason:** {reason}", color=Colors.ERROR)
        await self.dm_user(user, dm_embed)
        
        try:
            await user.kick(reason=f"{moderator}: {reason}")
        except Exception as e:
            return await self._respond(source, embed=ModEmbed.error("Failed", f"Could not kick: {e}"), ephemeral=True)
            
        embed = await self.create_mod_embed(title="👢 User Kicked", user=user, moderator=moderator, reason=reason, color=Colors.ERROR, case_num=case_num)
        await self._respond(source, embed=embed)
        await self.log_action(guild, embed)

    async def _ban_logic(self, source, user: discord.Member, reason: str, delete_days: int = 1):
        guild = source.guild
        moderator = source.user if isinstance(source, discord.Interaction) else source.author
        
        can_mod, error = await self.can_moderate(guild.id, moderator, user)
        if not can_mod:
            return await self._respond(source, embed=ModEmbed.error("Cannot Ban", error), ephemeral=True)
            
        can_bot, bot_error = await self.can_bot_moderate(user, moderator=moderator)
        if not can_bot:
            return await self._respond(source, embed=ModEmbed.error("Bot Permission Error", bot_error), ephemeral=True)
            
        case_num = await self.bot.db.create_case(guild.id, user.id, moderator.id, "Ban", reason)
        
        dm_embed = discord.Embed(title=f"🔨 Banned from {guild.name}", description=f"**Reason:** {reason}\n\nYou have been permanently banned.", color=Colors.DARK_RED)
        await self.dm_user(user, dm_embed)
        
        try:
            await user.ban(reason=f"{moderator}: {reason}", delete_message_days=delete_days)
        except Exception as e:
            return await self._respond(source, embed=ModEmbed.error("Failed", f"Could not ban: {e}"), ephemeral=True)
            
        embed = await self.create_mod_embed(title="🔨 User Banned", user=user, moderator=moderator, reason=reason, color=Colors.DARK_RED, case_num=case_num, extra_fields={"Messages Deleted": f"{delete_days} day(s)"})
        await self._respond(source, embed=embed)
        await self.log_action(guild, embed)
        
    async def _mute_logic(self, source, user: discord.Member, duration: str, reason: str):
        guild = source.guild
        moderator = source.user if isinstance(source, discord.Interaction) else source.author
        
        can_mod, error = await self.can_moderate(guild.id, moderator, user)
        if not can_mod:
            return await self._respond(source, embed=ModEmbed.error("Cannot Mute", error), ephemeral=True)
            
        can_bot, bot_error = await self.can_bot_moderate(user, moderator=moderator)
        if not can_bot:
            return await self._respond(source, embed=ModEmbed.error("Bot Permission Error", bot_error), ephemeral=True)

        bot_member = guild.me
        if not bot_member.guild_permissions.moderate_members:
            return await self._respond(source, embed=ModEmbed.error("Bot Missing Permissions", "I need **Timeout Members** permission."), ephemeral=True)
        
        parsed = parse_time(duration)
        if not parsed:
            return await self._respond(source, embed=ModEmbed.error("Invalid Duration", "Use format like `10m`, `1h`, `1d`"), ephemeral=True)
        
        delta, human_duration = parsed
        if delta.total_seconds() > 28 * 24 * 60 * 60:
            return await self._respond(source, embed=ModEmbed.error("Duration Too Long", "Max 28 days."), ephemeral=True)
        
        try:
            await user.timeout(delta, reason=f"{moderator}: {reason}")
        except Exception as e:
            return await self._respond(source, embed=ModEmbed.error("Failed", "You do not have permission to use this bot on that user."), ephemeral=True)

        case_num = await self.bot.db.create_case(guild.id, user.id, moderator.id, "Mute", reason, human_duration)
        
        embed = await self.create_mod_embed(title="🔇 User Muted", user=user, moderator=moderator, reason=reason, color=Colors.WARNING, case_num=case_num, extra_fields={"Duration": human_duration})
        await self._respond(source, embed=embed)
        await self.log_action(guild, embed)
        
        dm_embed = discord.Embed(title=f"🔇 Muted in {guild.name}", description=f"**Reason:** {reason}\n**Duration:** {human_duration}", color=Colors.WARNING)
        await self.dm_user(user, dm_embed)

    async def _unmute_logic(self, source, user: discord.Member, reason: str):
        guild = source.guild
        moderator = source.user if isinstance(source, discord.Interaction) else source.author
        
        if not user.is_timed_out():
            return await self._respond(source, embed=ModEmbed.error("Not Muted", "User is not muted."), ephemeral=True)
            
        bot_member = guild.me
        if not bot_member.guild_permissions.moderate_members:
            return await self._respond(source, embed=ModEmbed.error("Bot Missing Permissions", "I need **Timeout Members** permission."), ephemeral=True)

        try:
            await user.timeout(None, reason=f"{moderator}: {reason}")
        except Exception as e:
            return await self._respond(source, embed=ModEmbed.error("Failed", f"Could not unmute: {e}"), ephemeral=True)
            
        case_num = await self.bot.db.create_case(guild.id, user.id, moderator.id, "Unmute", reason)
        
        embed = await self.create_mod_embed(title="🔊 User Unmuted", user=user, moderator=moderator, reason=reason, color=Colors.SUCCESS, case_num=case_num)
        await self._respond(source, embed=embed)
        await self.log_action(guild, embed)

    async def _unban_logic(self, source, user_id: int, reason: str):
        guild = source.guild
        moderator = source.user if isinstance(source, discord.Interaction) else source.author
        
        try:
            user = await self.bot.fetch_user(user_id)
        except:
             return await self._respond(source, embed=ModEmbed.error("Invalid User", "User not found."), ephemeral=True)

        try:
            await guild.unban(user, reason=f"{moderator}: {reason}")
        except discord.NotFound:
             return await self._respond(source, embed=ModEmbed.error("Not Banned", "User is not banned."), ephemeral=True)
        except Exception as e:
             return await self._respond(source, embed=ModEmbed.error("Failed", f"Could not unban: {e}"), ephemeral=True)
             
        await self.bot.db.remove_tempban(guild.id, user.id)
        case_num = await self.bot.db.create_case(guild.id, user.id, moderator.id, "Unban", reason)
        
        embed = await self.create_mod_embed(title="🔓 User Unbanned", user=user, moderator=moderator, reason=reason, color=Colors.SUCCESS, case_num=case_num)
        await self._respond(source, embed=embed)
        await self.log_action(guild, embed)
        
    async def _softban_logic(self, source, user: discord.Member, reason: str):
        guild = source.guild
        moderator = source.user if isinstance(source, discord.Interaction) else source.author
        
        can_mod, error = await self.can_moderate(guild.id, moderator, user)
        if not can_mod:
            return await self._respond(source, embed=ModEmbed.error("Cannot Softban", error), ephemeral=True)
            
        can_bot, bot_error = await self.can_bot_moderate(user)
        if not can_bot:
            return await self._respond(source, embed=ModEmbed.error("Bot Permission Error", bot_error), ephemeral=True)
            
        case_num = await self.bot.db.create_case(guild.id, user.id, moderator.id, "Softban", reason)
        
        dm_embed = discord.Embed(title=f"🧹 Softbanned from {guild.name}", description=f"**Reason:** {reason}\n\nYou can rejoin the server.", color=Colors.ERROR)
        await self.dm_user(user, dm_embed)
        
        try:
            await user.ban(reason=f"[SOFTBAN] {reason}", delete_message_days=7)
            await guild.unban(user, reason="Softban - immediate unban")
        except Exception as e:
            return await self._respond(source, embed=ModEmbed.error("Failed", f"Could not softban: {e}"), ephemeral=True)
            
        embed = await self.create_mod_embed(title="🧹 User Softbanned", user=user, moderator=moderator, reason=reason, color=Colors.ERROR, case_num=case_num)
        embed.set_footer(text=f"Case #{case_num} | 7 days of messages deleted")
        await self._respond(source, embed=embed)
        await self.log_action(guild, embed)
        
    async def _tempban_logic(self, source, user: discord.Member, duration: str, reason: str):
        guild = source.guild
        moderator = source.user if isinstance(source, discord.Interaction) else source.author
        
        can_mod, error = await self.can_moderate(guild.id, moderator, user)
        if not can_mod:
            return await self._respond(source, embed=ModEmbed.error("Cannot Tempban", error), ephemeral=True)
            
        can_bot, bot_error = await self.can_bot_moderate(user, moderator=moderator)
        if not can_bot:
            return await self._respond(source, embed=ModEmbed.error("Bot Permission Error", bot_error), ephemeral=True)
        
        parsed = parse_time(duration)
        if not parsed:
            return await self._respond(source, embed=ModEmbed.error("Invalid Duration", "Use format like `1d`, `7d`, `30d`"), ephemeral=True)
        
        delta, human_duration = parsed
        expires_at = datetime.now(timezone.utc) + delta
        
        case_num = await self.bot.db.create_case(guild.id, user.id, moderator.id, "Tempban", reason, human_duration)
        await self.bot.db.add_tempban(guild.id, user.id, moderator.id, reason, expires_at)
        
        dm_embed = discord.Embed(title=f"⏰ Temporarily Banned from {guild.name}", description=f"**Reason:** {reason}\n**Duration:** {human_duration}\n**Expires:** <t:{int(expires_at.timestamp())}:F>", color=Colors.DARK_RED)
        await self.dm_user(user, dm_embed)
        
        try:
            await user.ban(reason=f"[TEMPBAN] {moderator}: {reason} ({human_duration})", delete_message_days=1)
        except Exception as e:
            return await self._respond(source, embed=ModEmbed.error("Failed", f"Could not tempban: {e}"), ephemeral=True)
            
        embed = await self.create_mod_embed(title="⏰ User Temporarily Banned", user=user, moderator=moderator, reason=reason, color=Colors.DARK_RED, case_num=case_num, extra_fields={"Duration": human_duration, "Expires": f"<t:{int(expires_at.timestamp())}:R>"})
        await self._respond(source, embed=embed)
        await self.log_action(guild, embed)

    async def _warn_logic(self, source, user: discord.Member, reason: str):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        can_mod, error = await self.can_moderate(source.guild.id, author, user)
        if not can_mod:
            return await self._respond(source, embed=ModEmbed.error("Cannot Warn", error), ephemeral=True)
        
        # Add to database
        await self.bot.db.add_warning(source.guild.id, user.id, author.id, reason)
        warnings = await self.bot.db.get_warnings(source.guild.id, user.id)
        case_num = await self.bot.db.create_case(
            source.guild.id, user.id, author.id, "Warn", reason
        )
        
        # Create embed
        embed = await self.create_mod_embed(
            title="⚠️ User Warned",
            user=user,
            moderator=author,
            reason=reason,
            color=Colors.WARNING,
            case_num=case_num,
            extra_fields={"Total Warnings": str(len(warnings))}
        )
        
        await self._respond(source, embed=embed)
        await self.log_action(source.guild, embed)
        
        # DM user
        dm_embed = discord.Embed(
            title=f"⚠️ Warning in {source.guild.name}",
            description=f"**Reason:** {reason}\n**Total Warnings:** {len(warnings)}",
            color=Colors.WARNING
        )
        await self.dm_user(user, dm_embed)

    async def _warnings_logic(self, source, user: discord.Member):
        warnings = await self.bot.db.get_warnings(source.guild.id, user.id)
        
        if not warnings:
            return await self._respond(source, embed=ModEmbed.info("No Warnings", f"{user.mention} has no warnings."), ephemeral=True)
        
        embed = discord.Embed(
            title=f"⚠️ Warnings for {user.display_name}",
            description=f"Total: **{len(warnings)}** warning(s)",
            color=Colors.WARNING,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        for warn in warnings[:10]:  # Limit to 10 most recent
            moderator = source.guild.get_member(warn['moderator_id'])
            mod_display = moderator.display_name if moderator else f"ID: {warn['moderator_id']}"
            timestamp = warn.get('created_at', 'Unknown time')
            
            embed.add_field(
                name=f"Warning #{warn['id']}",
                value=f"**Reason:** {warn['reason'][:100]}\n**By:** {mod_display}\n**When:** {timestamp}",
                inline=False
            )
        
        if len(warnings) > 10:
            embed.set_footer(text=f"Showing 10 of {len(warnings)} warnings")
        
        await self._respond(source, embed=embed)

    async def _delwarn_logic(self, source, warning_id: int):
        success = await self.bot.db.delete_warning(source.guild.id, warning_id)
        
        if success:
            embed = ModEmbed.success("Warning Deleted", f"Warning `#{warning_id}` has been removed.")
        else:
            embed = ModEmbed.error("Not Found", f"Warning `#{warning_id}` does not exist.")
        
        await self._respond(source, embed=embed, ephemeral=True)

    async def _clearwarnings_logic(self, source, user: discord.Member, reason: str):
        count = await self.bot.db.clear_warnings(source.guild.id, user.id)
        
        embed = ModEmbed.success(
            "Warnings Cleared",
            f"Cleared **{count}** warning(s) from {user.mention}.\n**Reason:** {reason}"
        )
        
        await self._respond(source, embed=embed)
        await self.log_action(source.guild, embed)

    async def _lock_logic(self, source, channel: discord.TextChannel = None, reason: str = "No reason provided", role: discord.Role = None):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        channel = channel or (source.channel if isinstance(source, discord.Interaction) else source.channel)
        bot_member = source.guild.me
        
        try:
            # Lock for everyone
            await channel.set_permissions(
                source.guild.default_role,
                send_messages=False,
                reason=f"{author}: {reason}"
            )
            
            # Also revoke send_messages for ALL existing role overrides (except allowed role and bot)
            # This prevents roles with explicit send_messages=True from bypassing the lock
            for target, overwrite in channel.overwrites.items():
                # Skip @everyone (already handled), the allowed role, and the bot itself
                if target == source.guild.default_role:
                    continue
                if role and target == role:
                    continue
                if isinstance(target, discord.Role) and target == bot_member.top_role:
                    continue
                if isinstance(target, discord.Member) and target.id == bot_member.id:
                    continue
                    
                # If this role/member has send_messages permission, revoke it
                if isinstance(target, discord.Role) and overwrite.send_messages is True:
                    await channel.set_permissions(
                        target,
                        overwrite=discord.PermissionOverwrite.from_pair(
                            overwrite.pair()[0],  # Keep allow permissions
                            overwrite.pair()[1] | discord.Permissions(send_messages=True)  # Add send_messages to deny
                        ),
                        reason=f"{author} (Lock): {reason}"
                    )
            
            # Allow specific role if provided
            role_msg = ""
            if role:
                await channel.set_permissions(
                    role,
                    send_messages=True,
                    reason=f"{author} (Lock Bypass): {reason}"
                )
                role_msg = f"\n✅ Allowed: {role.mention}"
                
        except discord.Forbidden:
            return await self._respond(source, embed=ModEmbed.error("Failed", "I don't have permission to edit channel permissions."), ephemeral=True)
        
        embed = discord.Embed(
            title="🔒 Channel Locked",
            description=f"{channel.mention} has been locked.{role_msg}",
            color=Colors.ERROR
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=author.mention, inline=False)

        if author.guild_permissions.administrator:
            embed.set_footer(text="Note: You are an Administrator, so you can bypass this lock.")
        
        await self._respond(source, embed=embed)
        
        if channel != (source.channel if isinstance(source, discord.Interaction) else source.channel):
             lock_notice = discord.Embed(
                title="🔒 Channel Locked",
                description=f"Locked by {author.mention}\n**Reason:** {reason}",
                color=Colors.ERROR
            )
             await channel.send(embed=lock_notice)

    async def _unlock_logic(self, source, channel: discord.TextChannel = None, reason: str = "No reason provided"):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        channel = channel or (source.channel if isinstance(source, discord.Interaction) else source.channel)
        
        try:
            # Unlock for everyone
            await channel.set_permissions(
                source.guild.default_role,
                send_messages=None,
                reason=f"{author}: {reason}"
            )

            # Iterate through overrides to remove the deny we added
            bot_member = source.guild.me
            for target, overwrite in channel.overwrites.items():
                if target == source.guild.default_role:
                    continue
                if isinstance(target, discord.Role) and target == bot_member.top_role:
                    continue
                if isinstance(target, discord.Member) and target.id == bot_member.id:
                    continue

                if overwrite.send_messages is False:
                    allow, deny = overwrite.pair()
                    deny.send_messages = False
                    await channel.set_permissions(
                        target,
                        overwrite=discord.PermissionOverwrite.from_pair(allow, deny),
                        reason=f"{author} (Unlock): {reason}"
                    )
        except discord.Forbidden:
             return await self._respond(source, embed=ModEmbed.error("Failed", "I don't have permission to edit channel permissions."), ephemeral=True)
        
        embed = discord.Embed(
            title="🔓 Channel Unlocked",
            description=f"{channel.mention} has been unlocked.",
            color=Colors.SUCCESS
        )
        embed.add_field(name="Moderator", value=author.mention, inline=False)
        
        await self._respond(source, embed=embed)

    async def _slowmode_logic(self, source, seconds: int, channel: discord.TextChannel = None):
        channel = channel or (source.channel if isinstance(source, discord.Interaction) else source.channel)
        try:
            await channel.edit(slowmode_delay=seconds)
        except discord.Forbidden:
             return await self._respond(source, embed=ModEmbed.error("Failed", "I don't have permission to edit this channel."), ephemeral=True)
        
        if seconds == 0:
            embed = ModEmbed.success("Slowmode Disabled", f"Slowmode has been disabled in {channel.mention}.")
        else:
            embed = ModEmbed.success("Slowmode Enabled", f"Slowmode set to **{seconds}s** in {channel.mention}.")
        
        await self._respond(source, embed=embed)

    async def _lockdown_logic(self, source, reason: str = "Server lockdown"):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        if isinstance(source, discord.Interaction):
            await source.response.defer()
        
        locked = []
        failed = []
        
        for channel in source.guild.text_channels:
            try:
                await channel.set_permissions(
                    source.guild.default_role,
                    send_messages=False,
                    reason=f"[LOCKDOWN] {reason}"
                )
                locked.append(channel.mention)
            except (discord.Forbidden, discord.HTTPException):
                failed.append(channel.mention)
        
        embed = discord.Embed(
            title="🚨 Server Lockdown Initiated",
            description=f"Locked **{len(locked)}** channels.",
            color=Colors.DARK_RED,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=author.mention, inline=False)
        
        if failed:
            embed.add_field(
                name=f"❌ Failed ({len(failed)})",
                value=", ".join(failed[:10]) + (f" ...and {len(failed) - 10} more" if len(failed) > 10 else ""),
                inline=False
            )
        
        await self._respond(source, embed=embed)
        await self.log_action(source.guild, embed)

    async def _unlockdown_logic(self, source, reason: str = "Lockdown lifted"):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        if isinstance(source, discord.Interaction):
            await source.response.defer()
            
        unlocked = []
        failed = []
        
        for channel in source.guild.text_channels:
            try:
                await channel.set_permissions(
                    source.guild.default_role,
                    send_messages=None,
                    reason=f"[UNLOCKDOWN] {reason}"
                )
                unlocked.append(channel.mention)
            except (discord.Forbidden, discord.HTTPException):
                failed.append(channel.mention)
        
        embed = discord.Embed(
            title="✅ Lockdown Lifted",
            description=f"Unlocked **{len(unlocked)}** channels.",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Moderator", value=author.mention, inline=False)
        
        if failed:
            embed.add_field(
                name=f"❌ Failed ({len(failed)})",
                value=", ".join(failed[:10]) + (f" ...and {len(failed) - 10} more" if len(failed) > 10 else ""),
                inline=False
            )
        
        await self._respond(source, embed=embed)
        await self.log_action(source.guild, embed)

    async def _nuke_logic(self, source, channel: discord.TextChannel = None):
        channel = channel or (source.channel if isinstance(source, discord.Interaction) else source.channel)
        user = source.user if isinstance(source, discord.Interaction) else source.author

        try:
            position = channel.position
            new_channel = await channel.clone(reason=f"Nuked by {user}")
            await new_channel.edit(position=position)
            await channel.delete(reason=f"Nuked by {user}")
        except discord.Forbidden:
             return await self._respond(source, embed=ModEmbed.error("Failed", "I don't have permission to clone/delete channels."), ephemeral=True)
        
        embed = discord.Embed(
            title="💥 Channel Nuked",
            description=f"This channel has been nuked by {user.mention}.",
            color=Colors.ERROR
        )
        embed.set_image(url="https://media1.tenor.com/m/OMQvHj3-AsMAAAAd/kaboom-boom.gif")
        
        await new_channel.send(embed=embed)

    async def _purge_logic(self, source, amount: int, user: discord.Member = None, check=None):
        if isinstance(source, discord.Interaction):
            await source.response.defer(ephemeral=True)
            channel = source.channel
            interaction = source
            author = source.user
        else:
            try:
                await source.message.delete()
            except:
                pass
            channel = source.channel
            interaction = None
            author = source.author

        # Fetch settings for hierarchy check
        settings = await self.bot.db.get_settings(source.guild.id)
        
        # Hierarchy Definition (Sync Version)
        role_hierarchy = {
            'manager_role': 7,
            'admin_role': 6,
            'supervisor_role': 5,
            'senior_mod_role': 4,
            'mod_role': 3,
            'trial_mod_role': 2,
            'staff_role': 1
        }

        def get_sync_level(member: discord.Member) -> int:
            if is_bot_owner_id(member.id) or member.id == member.guild.owner_id:
                return 100
            if member.guild_permissions.administrator:
                return 7
            
            user_role_ids = {r.id for r in member.roles}
            current_level = 0
            for key, val in role_hierarchy.items():
                rid = settings.get(key)
                if rid and rid in user_role_ids:
                    if val > current_level:
                        current_level = val
            return current_level

        # Calculate Moderator Level
        mod_level = get_sync_level(author)
        
        # Combined Check
        def combined_check(m: discord.Message):
            # 1. Existing checks (user filter / content filter)
            if user and m.author.id != user.id:
                return False
            if check and not check(m):
                return False
            
            # 2. Hierarchy Check
            if not isinstance(m.author, discord.Member):
                return True # Allow deleting messages from departed users
            
            # BYPASS: Server Owner and Bot Owner can delete ANYTHING
            if is_bot_owner_id(author.id) or author.id == author.guild.owner_id:
                return True

            # Allow deleting own messages
            if m.author.id == author.id:
                return True
                
            # Allow deleting bot messages (unless it's the bot owner?? No, bots are fair game usually, 
            # but let's check if the specific bot has a high role? 
            # Existing code for `can_moderate` checks bot hierarchy.
            # Simplified: If target is bot, allow unless it has higher role.
            if m.author.bot:
                if m.author.top_role >= author.top_role:
                    return False
                return True

            target_level = get_sync_level(m.author)
            
            # Strict inequality: mod_level Must be > target_level
            if mod_level <= target_level:
                return False
            
            return True

        try:
            deleted = await channel.purge(limit=amount, check=combined_check)
        except discord.Forbidden:
             return await self._respond(source, embed=ModEmbed.error("Failed", "I don't have permission to delete messages."), ephemeral=True)
        except discord.HTTPException as e:
             return await self._respond(source, embed=ModEmbed.error("Failed", f"An error occurred: {str(e)}"), ephemeral=True)
        
        msg = f"Deleted **{len(deleted)}** message(s)."
        if user:
            msg += f" from {user.mention}"
        
        embed = ModEmbed.success("Messages Purged", msg)
        await self._respond(source, embed=embed, ephemeral=True)

    async def _quarantine_logic(self, source, user: discord.Member, duration_str: str = None, reason: str = "No reason provided"):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        
        can_mod, error = await self.can_moderate(source.guild.id, author, user)
        if not can_mod:
             return await self._respond(source, embed=ModEmbed.error("Cannot Quarantine", error), ephemeral=True)
             
        can_bot, bot_error = await self.can_bot_moderate(user, moderator=author)
        if not can_bot:
             return await self._respond(source, embed=ModEmbed.error("Bot Permission Error", bot_error), ephemeral=True)

        settings = await self.bot.db.get_settings(source.guild.id)
        quarantine_role_id = settings.get("quarantine_role_id")
        
        if not quarantine_role_id:
             return await self._respond(source, embed=ModEmbed.error("Not Configured", "Quarantine role is not set."), ephemeral=True)
             
        quarantine_role = source.guild.get_role(int(quarantine_role_id))
        if not quarantine_role:
             return await self._respond(source, embed=ModEmbed.error("Configuration Error", "Quarantine role not found."), ephemeral=True)

        # Calculate duration
        expires_at = None
        human_duration = "Indefinite"
        if duration_str:
            parsed = parse_time(duration_str)
            if parsed:
                delta, human_duration = parsed
                expires_at = datetime.now(timezone.utc) + delta

        # Backup roles
        restored, failed = await self._backup_roles(user)
        
        # Apply quarantine
        try:
            await user.edit(roles=[quarantine_role], reason=f"[QUARANTINE] {author}: {reason}")
        except discord.Forbidden:
             return await self._respond(source, embed=ModEmbed.error("Failed", "I don't have permission to edit roles."), ephemeral=True)

        # DB
        await self.bot.db.add_quarantine(
            source.guild.id,
            user.id,
            author.id,
            reason,
            expires_at
        )
        
        embed = discord.Embed(
            title="☣️ User Quarantined",
            description=f"{user.mention} has been quarantined.",
            color=Colors.DARK_RED
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Duration", value=human_duration, inline=True)
        if expires_at:
             embed.add_field(name="Expires", value=f"<t:{int(expires_at.timestamp())}:R>", inline=True)
        
        embed.add_field(name="Roles Removed", value=str(restored), inline=True)
        
        await self._respond(source, embed=embed)
        await self.log_action(source.guild, embed)
        
        # DM
        dm_embed = discord.Embed(
            title=f"☣️ Quarantined in {source.guild.name}",
            description=f"**Reason:** {reason}\n**Duration:** {human_duration}",
            color=Colors.DARK_RED
        )
        await self.dm_user(user, dm_embed)

    async def _unquarantine_logic(self, source, user: discord.Member, reason: str = "Quarantine lifted"):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        
        active = await self._get_active_quarantine(source.guild.id, user.id)
        if not active:
             return await self._respond(source, embed=ModEmbed.error("Not Quarantined", "This user is not quarantined."), ephemeral=True)

        # Restore roles
        restored, failed = await self._restore_roles(user, active['roles'])
        
        # Remove quarantine role
        settings = await self.bot.db.get_settings(source.guild.id)
        quarantine_role_id = settings.get("quarantine_role_id")
        if quarantine_role_id:
            role = source.guild.get_role(int(quarantine_role_id))
            if role and role in user.roles:
                try:
                    await user.remove_roles(role, reason=f"[UNQUARANTINE] {author}: {reason}")
                except:
                    pass

        # DB update
        await self.bot.db.remove_quarantine(source.guild.id, user.id)
        
        embed = discord.Embed(
            title="✅ User Unquarantined",
            description=f"{user.mention} has been released from quarantine.",
            color=Colors.SUCCESS
        )
        embed.add_field(name="Restored Roles", value=f"{restored} (Failed: {failed})", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await self._respond(source, embed=embed)
        await self.log_action(source.guild, embed)

    async def _is_bot_owner(self, user: discord.abc.User) -> bool:
        """Return True when a user should be treated as the bot owner."""
        if is_bot_owner_id(user.id):
            return True

        owner_ids = getattr(self.bot, "owner_ids", None)
        if owner_ids and user.id in owner_ids:
            return True

        is_owner = getattr(self.bot, "is_owner", None)
        if is_owner is None:
            return False

        try:
            return bool(await is_owner(user))
        except Exception:
            return False

    # ==================== DIAGNOSTICS ====================

    @app_commands.command(
        name="ownerinfo",
        description="Show your ID, owner status, and bot permissions (ephemeral)",
    )
    async def ownerinfo(self, interaction: discord.Interaction):
        """Diagnostic command to help troubleshoot owner overrides and bot permissions."""
        guild = interaction.guild
        user = interaction.user

        user_top_role = getattr(user, "top_role", None)
        user_top_role_text = (
            f"{user_top_role.mention} (pos {user_top_role.position})"
            if user_top_role is not None
            else "N/A"
        )

        env_owner_ids = sorted(get_owner_ids())
        is_env_owner = is_bot_owner_id(user.id)

        is_owner_callable = getattr(interaction.client, "is_owner", None)
        is_app_owner = False
        if is_owner_callable is not None:
            try:
                is_app_owner = bool(await is_owner_callable(user))
            except Exception:
                is_app_owner = False

        is_owner = await self._is_bot_owner(user)

        bot_member = guild.me if guild else None
        bot_top_role_text = "N/A"
        bot_perms_text = "N/A"
        if bot_member is not None:
            bot_top = bot_member.top_role
            bot_top_role_text = f"{bot_top.mention} (pos {bot_top.position})"
            perms = bot_member.guild_permissions
            bot_perms_text = (
                f"administrator={perms.administrator}, "
                f"moderate_members={perms.moderate_members}, "
                f"ban_members={perms.ban_members}, "
                f"kick_members={perms.kick_members}"
            )

        guild_owner_text = "N/A"
        if guild and guild.owner_id:
            guild_owner_text = f"<@{guild.owner_id}> (`{guild.owner_id}`)"

        embed = discord.Embed(
            title="Owner / Permission Info",
            color=Colors.INFO,
        )
        embed.add_field(
            name="You",
            value=(
                f"{user.mention} (`{user.id}`)\n"
                f"Top role: {user_top_role_text}\n"
                f"Guild owner: {guild_owner_text}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Owner Checks",
            value=(
                f"Env match: {is_env_owner}\n"
                f"Client is_owner: {is_app_owner}\n"
                f"Resolved owner: {is_owner}\n"
                f"OWNER_IDS: {', '.join(str(i) for i in env_owner_ids)}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Bot",
            value=f"Top role: {bot_top_role_text}\nPerms: {bot_perms_text}",
            inline=False,
        )

        return await self._respond(interaction, embed=embed, ephemeral=True)

    # ==================== MOD COMMANDS ====================

    @commands.group(name="mod", invoke_without_command=True)
    @is_mod()
    async def mod_group(self, ctx: commands.Context):
        """Moderation commands group. Use ,mod help for a list of commands."""
        await ctx.invoke(self.mod_help)

    @mod_group.command(name="help")
    @is_mod()
    async def mod_help(self, ctx: commands.Context):
        """Show all moderation prefix commands"""
        embed = discord.Embed(
            title="📋 Moderation Commands",
            description="All moderation prefix commands. Use `,<command>` to run them.",
            color=Colors.INFO,
            timestamp=datetime.now(timezone.utc)
        )

        # User Moderation
        embed.add_field(
            name="👤 User Moderation",
            value=(
                "`,warn <user> [reason]` - Warn a user\n"
                "`,warnings <user>` - View warnings\n"
                "`,delwarn <id>` - Delete a warning\n"
                "`,clearwarnings <user> [reason]` - Clear all warnings\n"
                "`,kick <user> [reason]` - Kick a user\n"
                "`,ban <user> [reason]` - Ban a user\n"
                "`,tempban <user> <duration> [reason]` - Temp ban\n"
                "`,unban <user_id> [reason]` - Unban a user\n"
                "`,softban <user> [reason]` - Softban (ban+unban)\n"
                "`,timeout <user> <duration> [reason]` - Timeout/mute\n"
                "`,untimeout <user> [reason]` - Remove timeout\n"
                "`,rename <user> [nickname]` - Change nickname"
            ),
            inline=False
        )

        # Channel Management
        embed.add_field(
            name="📺 Channel Management",
            value=(
                "`,lock [channel] [reason]` - Lock a channel\n"
                "`,unlock [channel] [reason]` - Unlock a channel\n"
                "`,slowmode <duration> [channel]` - Set slowmode\n"
                "`,glock [channel] [role] [reason]` - Restrict to Glock role\n"
                "`,gunlock [channel] [role]` - Remove glock restriction\n"
                "`,lockdown [reason]` - Lock all channels\n"
                "`,unlockdown [reason]` - Unlock all channels\n"
                "`,nuke [channel]` - Clone and delete channel"
            ),
            inline=False
        )

        # Purge Commands
        embed.add_field(
            name="🗑️ Purge Commands",
            value=(
                "`,purge <amount> [user]` - Delete messages\n"
                "`,purgebots <amount>` - Delete bot messages\n"
                "`,purgecontains <text> <amount>` - Delete by content\n"
                "`,purgeembeds <amount>` - Delete embeds\n"
                "`,purgeimages <amount>` - Delete attachments\n"
                "`,purgelinks <amount>` - Delete links"
            ),
            inline=False
        )

        # Role & Mass Actions
        embed.add_field(
            name="🏷️ Roles & Mass Actions",
            value=(
                "`,massban <id1> <id2>... [reason]` - Ban multiple users\n"
                "`,banlist` - View banned users\n"
                "`,roleall <role>` - Give role to all members\n"
                "`,removeall <role>` - Remove role from all\n"
                "`,inrole <role>` - List members with role"
            ),
            inline=False
        )

        # Quarantine & Utility
        embed.add_field(
            name="☣️ Quarantine & Utility",
            value=(
                "`,quarantine <user> [duration] [reason]` - Quarantine user\n"
                "`,unquarantine <user> [reason]` - Remove quarantine\n"
                "`,setnick <user> [nickname]` - Set nickname\n"
                "`,nicknameall <template>` - Bulk set nicknames\n"
                "`,resetnicks` - Reset all nicknames"
            ),
            inline=False
        )

        # Case Management
        embed.add_field(
            name="📁 Cases & Logs",
            value=(
                "`,case <number>` - View a case\n"
                "`,editcase <number> <reason>` - Edit case reason\n"
                "`,history <user>` - View moderation history\n"
                "`,modlogs <user>` - Alias for history\n"
                "`,note <user> <note>` - Add a note\n"
                "`,notes <user>` - View notes\n"
                "`,modstats [user]` - View mod statistics"
            ),
            inline=False
        )

        # Emoji
        embed.add_field(
            name="😀 Emoji",
            value=(
                "`,emoji add <name> <url>` - Add an emoji\n"
                "`,emoji steal <emoji>` - Steal an emoji\n"
                "`,emoji tutorial` - Show emoji tutorial"
            ),
            inline=False
        )

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed)

    @commands.command(name="warn", description="⚠️ Warn a user")
    @is_mod()
    async def mod_warn(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        if is_bot_owner_id(user.id) and not is_bot_owner_id(ctx.author.id):
            return await self._respond(ctx, embed=ModEmbed.error("Permission Denied", "You cannot warn the bot owner."), ephemeral=True)
        await self._warn_logic(ctx, user, reason)

    @commands.command(name="warnings", description="⚠️ View warnings for a user")
    @is_mod()
    async def mod_warnings(self, ctx: commands.Context, user: discord.Member):
        """View warnings for a user"""
        await self._warnings_logic(ctx, user)

    @commands.command(name="delwarn", description="🗑️ Delete a warning")
    @is_mod()
    async def mod_delwarn(self, ctx: commands.Context, warning_id: int):
        """Delete a specific warning by ID"""
        await self._delwarn_logic(ctx, warning_id)

    @commands.command(name="clearwarnings", description="🧹 Clear all warnings for a user")
    @is_mod()
    async def mod_clearwarnings(self, ctx: commands.Context, user: discord.Member, *, reason: str = "Cleared by moderator"):
        """Clear all warnings for a user"""
        await self._clearwarnings_logic(ctx, user, reason)

    @commands.command(name="kick", description="👢 Kick a user from the server")
    @is_mod()
    async def mod_kick(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        if is_bot_owner_id(user.id) and not is_bot_owner_id(ctx.author.id):
            return await self._respond(ctx, embed=ModEmbed.error("Permission Denied", "You cannot kick the bot owner."), ephemeral=True)
        await self._kick_logic(ctx, user, reason)

    @commands.command(name="ban", description="🔨 Permanently ban a user")
    @is_mod()
    async def mod_ban(self, ctx: commands.Context, user: discord.Member, delete_days: Optional[int] = 1, *, reason: str = "No reason provided"):
        if is_bot_owner_id(user.id) and not is_bot_owner_id(ctx.author.id):
            return await self._respond(ctx, embed=ModEmbed.error("Permission Denied", "You cannot ban the bot owner."), ephemeral=True)
        # Note: delete_days logic might need ensuring int, or being passed correctly if user types reason without days.
        # However, purely optional int argument in midway is tricky in discord.py prefix commands.
        # A common pattern is `ban <user> [days] [reason]`.
        # If user types `,ban @user spamming`, `delete_days` might try to consume "spamming".
        # Better approach for prefix: `,ban @user [reason]` defaults to 1 day. 
        # Or explicit flag. For now, let's keep it simple: `,ban @user reason` (1 day default) or `,ban @user 7 reason`.
        
        # Checking if delete_days is actually part of reason if it's not an int?
        # discord.py handles Optional[int] by trying to convert. If fail, it effectively skips it (if using Greedy) or errors?
        # Let's simplify and make delete_days strict or use a converter. 
        # Actually proper way: `async def mod_ban(self, ctx, user: discord.Member, delete_days: Optional[int] = 1, *, reason: str = "No reason provided")`
        # If I type `,ban @user spam`, it fails conversion for delete_days.
        # Let's stick to standard `,ban @user <reason>` and hardcode delete_days=1 effectively or handle parsing manually?
        # Alternatively, use a flag converter? No, too complex.
        # Let's just make delete_days default to 1 and if the second arg isn't an int, assume it's start of reason.
        # But discord.py parser is rigid.
        # I'll change signature to `async def mod_ban(self, ctx, user, *, reason="...")` and hardcode 1 day for now to match common expectation, 
        # OR put delete_days at the end? No, `*` consumes rest.
        
        # Let's try `async def mod_ban(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):` and ignore delete_days param for prefix for now to keep it usable.
        # Most users just want to ban.
        await self._ban_logic(ctx, user, reason, delete_days=1)

    @commands.command(name="tempban", description="⏱️ Temporarily ban a user")
    @is_mod()
    async def mod_tempban(self, ctx: commands.Context, user: discord.Member, duration: str = "1d", *, reason: str = "No reason provided"):
        if is_bot_owner_id(user.id) and not is_bot_owner_id(ctx.author.id):
            return await self._respond(ctx, embed=ModEmbed.error("Permission Denied", "You cannot ban the bot owner."), ephemeral=True)
        await self._tempban_logic(ctx, user, duration, reason)

    @commands.command(name="unban", description="🔓 Unban a user")
    @is_mod()
    async def mod_unban(self, ctx: commands.Context, user_id: str, *, reason: str = "No reason provided"):
        try:
            uid = int(user_id)
        except ValueError:
            return await self._respond(ctx, embed=ModEmbed.error("Invalid ID", "User ID must be a number."), ephemeral=True)
        await self._unban_logic(ctx, uid, reason)

    @commands.command(name="softban", description="🧹 Ban and immediately unban to delete messages")
    @is_mod()
    async def mod_softban(self, ctx: commands.Context, user: discord.Member, delete_days: Optional[int] = 1, *, reason: str = "No reason provided"):
        if is_bot_owner_id(user.id) and not is_bot_owner_id(ctx.author.id):
            return await self._respond(ctx, embed=ModEmbed.error("Permission Denied", "You cannot softban the bot owner."), ephemeral=True)
        if not await self._check_senior_mod(ctx):
            return await self._respond(ctx, embed=ModEmbed.error("Permission Denied", "Softban requires Senior Moderator permissions."), ephemeral=True)
        await self._softban_logic(ctx, user, reason, delete_days)

    @commands.command(name="timeout", aliases=["mute"], description="🔇 Timeout/mute a user")
    @is_mod()
    async def mod_timeout(self, ctx: commands.Context, user: discord.Member, duration: str = "1h", *, reason: str = "No reason provided"):
        if is_bot_owner_id(user.id) and not is_bot_owner_id(ctx.author.id):
            return await self._respond(ctx, embed=ModEmbed.error("Permission Denied", "You cannot timeout the bot owner."), ephemeral=True)
        await self._mute_logic(ctx, user, duration, reason)

    @commands.command(name="untimeout", aliases=["unmute"], description="🔊 Remove timeout from a user")
    @is_mod()
    async def mod_untimeout(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        await self._unmute_logic(ctx, user, reason)

    @commands.command(name="rename", description="📝 Change a user's nickname")
    @is_mod()
    async def mod_rename(self, ctx: commands.Context, user: discord.Member, *, nickname: Optional[str] = None):
        await self._rename_logic(ctx, user, nickname)

    async def _check_senior_mod(self, source: discord.Interaction | commands.Context) -> bool:
        """Check if user has senior mod permissions."""
        user = source.user if isinstance(source, discord.Interaction) else source.author
        if is_bot_owner_id(user.id):
            return True
        if user.guild_permissions.administrator:
            return True
        if user.guild_permissions.ban_members:
            return True
        settings = await self.bot.db.get_settings(source.guild.id)
        senior_mod_role = settings.get("senior_mod_role")
        admin_roles = settings.get("admin_roles", [])
        user_role_ids = [r.id for r in user.roles]
        if senior_mod_role and senior_mod_role in user_role_ids:
            return True
        if any(role_id in user_role_ids for role_id in admin_roles):
            return True
        return False

    @commands.command(name="massban", description="🔨 Ban multiple users at once")
    @is_admin()
    async def massban(self, ctx: commands.Context, *, args: str):
        """
        Ban multiple users by ID
        Usage: ,massban <id1> <id2> ... [reason]
        """
        await ctx.typing()
        
        parts = args.split()
        user_ids = []
        reason_parts = []
        
        # Simple parsing: grab all leading integers as IDs, rest is reason
        # Or just try to parse every word as int. If valid int, treat as ID?
        # Standard massban usually puts IDs then reason.
        
        for part in parts:
            if part.isdigit() and len(part) > 15: # rudimentary ID check
                user_ids.append(part)
            else:
                reason_parts.append(part)
        
        reason = " ".join(reason_parts) if reason_parts else "Mass ban"
        
        banned = []
        failed = []
        
        for uid in user_ids:
            try:
                user_id = int(uid)
                # fetch_user might not find it if not cached? No, fetch_user makes API call.
                # But we can just ban by Object to save API calls if we trust ID.
                # But standard behavior is fetch to get name.
                try:
                    user = await self.bot.fetch_user(user_id)
                    user_str = f"{user} (`{user.id}`)"
                    ban_target = user
                except discord.NotFound:
                    # User not found, try banning by ID blindly
                    user_str = f"User {user_id}"
                    ban_target = discord.Object(id=user_id)

                await ctx.guild.ban(
                    ban_target,
                    reason=f"[MASSBAN] {ctx.author}: {reason}"
                )
                banned.append(user_str)
            except ValueError:
                failed.append(f"`{uid}` (invalid ID)")
            except discord.Forbidden:
                failed.append(f"`{uid}` (permission denied)")
            except discord.HTTPException as e:
                failed.append(f"`{uid}` ({str(e)})")
        
        embed = discord.Embed(
            title="🔨 Mass Ban Complete",
            color=Colors.DARK_RED,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="✅ Banned", value=f"**{len(banned)}** users", inline=True)
        embed.add_field(name="❌ Failed", value=f"**{len(failed)}** users", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        if banned:
            embed.add_field(
                name="Banned Users",
                value="\n".join(banned[:10]) + (f"\n*...and {len(banned) - 10} more*" if len(banned) > 10 else ""),
                inline=False
            )
        
        if failed:
            embed.add_field(
                name="Failed Users",
                value="\n".join(failed[:10]) + (f"\n*...and {len(failed) - 10} more*" if len(failed) > 10 else ""),
                inline=False
            )
        
        await ctx.reply(embed=embed)
        await self.log_action(ctx.guild, embed)

    @commands.command(name="banlist", description="📋 View all banned users")
    @is_mod()
    async def banlist(self, ctx: commands.Context):
        """Display list of banned users"""
        try:
            # ctx.guild.bans() is an async iterator in discord.py 2.0+
            bans = [entry async for entry in ctx.guild.bans(limit=50)]
        except discord.Forbidden:
            return await ctx.reply(
                embed=ModEmbed.error("Permission Denied", "I don't have permission to view bans.")
            )
        
        if not bans:
            return await ctx.reply(
                embed=ModEmbed.info("No Bans", "No users are currently banned.")
            )
        
        embed = discord.Embed(
            title=f"🔨 Ban List ({len(bans)} total)",
            color=Colors.ERROR,
            timestamp=datetime.now(timezone.utc)
        )
        
        ban_list = []
        for ban in bans[:20]:
            reason = ban.reason or "*No reason provided*"
            ban_list.append(f"**{ban.user}** (`{ban.user.id}`)\n└ {reason[:80]}")
        
        embed.description = "\n\n".join(ban_list)
        
        if len(bans) > 20:
            embed.set_footer(text=f"Showing 20 of {len(bans)} bans")
        
        await ctx.reply(embed=embed)

    # ==================== TIMEOUT/MUTE COMMANDS ====================



    # ==================== CHANNEL COMMAND GROUP ====================

    @commands.command(name="lock", description="🔒 Lock a channel")
    @is_mod()
    async def lock(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None, *, reason: str = "No reason provided"):
        """
        Lock a channel
        Usage: ,lock [channel] [reason]
        """
        target = channel or ctx.channel
        await self._lock_logic(ctx, target, reason)

    @commands.command(name="unlock", description="🔓 Unlock a channel")
    @is_mod()
    async def unlock(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None, *, reason: str = "No reason provided"):
        """
        Unlock a channel
        Usage: ,unlock [channel] [reason]
        """
        target = channel or ctx.channel
        await self._unlock_logic(ctx, target, reason)

    @commands.command(name="slowmode", description="🐌 Set channel slowmode")
    @is_mod()
    async def slowmode(self, ctx: commands.Context, duration: str = "0", channel: Optional[discord.TextChannel] = None):
        """
        Set slowmode
        Usage: ,slowmode <duration> [channel]
        Example: ,slowmode 5m #general
        """
        target = channel or ctx.channel
        seconds = 0
        parsed = parse_time(duration)
        if parsed:
            seconds = int(parsed[0].total_seconds())
        elif duration.isdigit():
             seconds = int(duration)
        
        await self._slowmode_logic(ctx, seconds, target)

    # ==================== CHANNEL MANAGEMENT ====================
    # NOTE: /lock, /unlock, /glock, /gunlock, /slowmode, /nuke removed - use /channel instead


    @commands.command(name="glock", description="🔒 Only the Glock role can talk in the channel")
    @is_mod()
    async def glock(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None, role: Optional[discord.Role] = None, *, reason: str = "No reason provided"):
        """
        Restrict chatting so only members with the Glock role can send messages.
        Usage: ,glock [channel] [role] [reason]
        """
        interaction = ctx # Shim for logic reuse ease, though we should really use ctx
        
        settings = await self.bot.db.get_settings(ctx.guild.id)
        configured_role_id = settings.get("glock_role_id") or settings.get("glock_role")
        glock_role = (
            role
            or (ctx.guild.get_role(int(configured_role_id)) if configured_role_id else None)
            or discord.utils.get(ctx.guild.roles, name="Glock")
        )
        if glock_role is None:
            return await ctx.reply(
                embed=ModEmbed.error(
                    "Missing Role",
                    "No glock role is configured for this server. Create a role named `Glock`, or pass `role:`.",
                )
            )

        if role is None and (not configured_role_id) and glock_role is not None:
            settings["glock_role_id"] = glock_role.id
            try:
                await self.bot.db.update_settings(ctx.guild.id, settings)
            except Exception:
                pass

        async def _apply(ch: discord.TextChannel) -> bool:
            try:
                await ch.set_permissions(
                    ctx.guild.default_role,
                    send_messages=False,
                    send_messages_in_threads=False,
                    reason=f"[GLOCK] {ctx.author}: {reason}",
                )
                await ch.set_permissions(
                    glock_role,
                    send_messages=True,
                    send_messages_in_threads=True,
                    reason=f"[GLOCK] {ctx.author}: {reason}",
                )
                return True
            except (discord.Forbidden, discord.HTTPException):
                return False

        target = channel or ctx.channel
        
        if not await _apply(target):
            return await ctx.reply(
                embed=ModEmbed.error("Failed", "I couldn't edit permissions for that channel.")
            )

        return await ctx.reply(
            embed=ModEmbed.success(
                "Glocked",
                f"{target.mention} is now restricted to {glock_role.mention}.",
            )
        )

    @commands.command(name="gunlock", description="🔓 Remove Glock-role-only channel restriction")
    @is_mod()
    async def gunlock(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None, role: Optional[discord.Role] = None, *, reason: str = "No reason provided"):
        """
        Remove glock restrictions.
        Usage: ,gunlock [channel] [role] [reason]
        """
        settings = await self.bot.db.get_settings(ctx.guild.id)
        configured_role_id = settings.get("glock_role_id") or settings.get("glock_role")
        glock_role = (
            role
            or (ctx.guild.get_role(int(configured_role_id)) if configured_role_id else None)
            or discord.utils.get(ctx.guild.roles, name="Glock")
        )
        if glock_role is None:
             return await ctx.reply(
                embed=ModEmbed.error(
                    "Missing Role",
                    "No glock role is configured for this server.",
                )
            )

        async def _revert(ch: discord.TextChannel) -> bool:
            try:
                everyone_overwrite = ch.overwrites_for(ctx.guild.default_role)
                glock_overwrite = ch.overwrites_for(glock_role)

                looks_like_glocked = (
                    everyone_overwrite.send_messages is False
                    and glock_overwrite.send_messages is True
                )
                # If not explicitly glocked, we can still try to reset if needed?
                # But logic says return False if not.
                if not looks_like_glocked:
                    return False

                await ch.set_permissions(
                    ctx.guild.default_role,
                    send_messages=None,
                    send_messages_in_threads=None,
                    reason=f"[GUNLOCK] {ctx.author}: {reason}",
                )
                await ch.set_permissions(
                    glock_role,
                    send_messages=None,
                    send_messages_in_threads=None,
                    reason=f"[GUNLOCK] {ctx.author}: {reason}",
                )
                return True
            except (discord.Forbidden, discord.HTTPException):
                return False

        target = channel or ctx.channel
        
        reverted = await _revert(target)
        if not reverted:
            return await ctx.reply(
                embed=ModEmbed.info("Not Glocked", f"{target.mention} doesn't look glocked.")
            )

        return await ctx.reply(
            embed=ModEmbed.success("Gunlocked", f"{target.mention} is unlocked.")
        )



    @commands.command(name="lockdown")
    @is_admin()
    async def lockdown(self, ctx: commands.Context, *, reason: str = "Server lockdown"):
        """Lock all text channels"""
        await self._lockdown_logic(ctx, reason)

    @commands.command(name="unlockdown")
    @is_admin()
    async def unlockdown(self, ctx: commands.Context, *, reason: str = "Lockdown lifted"):
        """Unlock all text channels"""
        await self._unlockdown_logic(ctx, reason)

    @commands.command(name="nuke")
    @is_admin()
    async def nuke(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Clone and delete a channel"""
        await self._nuke_logic(ctx, channel)

    # ==================== MESSAGE PURGE COMMANDS ====================

    @commands.command(name="purge", aliases=["clear"])
    @is_mod()
    async def purge(self, ctx: commands.Context, amount: int, user: Optional[discord.Member] = None):
        """Bulk delete messages"""
        if amount < 1 or amount > 100:
             return await ctx.send("Amount must be between 1 and 100.")
        await self._purge_logic(ctx, amount, user)

    @commands.command(name="purgebots")
    @is_mod()
    async def purgebots(self, ctx: commands.Context, amount: int = 100):
        """Delete messages from bots"""
        await self._purge_logic(ctx, amount, check=lambda m: m.author.bot)

    @commands.command(name="purgecontains")
    @is_mod()
    async def purgecontains(self, ctx: commands.Context, text: str, amount: int = 100):
        """Delete messages containing text"""
        await self._purge_logic(ctx, amount, check=lambda m: text.lower() in m.content.lower())

    @commands.command(name="purgeembeds")
    @is_mod()
    async def purgeembeds(self, ctx: commands.Context, amount: int = 100):
        """Delete messages with embeds"""
        await self._purge_logic(ctx, amount, check=lambda m: len(m.embeds) > 0)

    @commands.command(name="purgeimages")
    @is_mod()
    async def purgeimages(self, ctx: commands.Context, amount: int = 100):
        """Delete messages with attachments"""
        await self._purge_logic(ctx, amount, check=lambda m: len(m.attachments) > 0)

    @commands.command(name="purgelinks")
    @is_mod()
    async def purgelinks(self, ctx: commands.Context, amount: int = 100):
        """Delete messages with links"""
        url_pattern = re.compile(r'https?://')
        await self._purge_logic(ctx, amount, check=lambda m: url_pattern.search(m.content))

    # ==================== ROLE MANAGEMENT ====================

    @staticmethod
    def _parse_role_id_input(role_input: str) -> Optional[int]:
        role_input = (role_input or "").strip()
        if not role_input:
            return None

        mention_match = re.fullmatch(r"<@&(\d+)>", role_input)
        if mention_match:
            try:
                return int(mention_match.group(1))
            except Exception:
                return None

        if role_input.isdigit():
            try:
                return int(role_input)
            except Exception:
                return None

        return None

    @staticmethod
    def _matches_role_query(role: discord.Role, query: str) -> bool:
        query = (query or "").strip().lower()
        if not query:
            return True
        if query.isdigit() and query in str(role.id):
            return True
        return query in role.name.lower()

    async def _role_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        if not interaction.guild:
            return []

        member = getattr(interaction.namespace, "user", None)
        if not isinstance(member, discord.Member):
            member_id = getattr(member, "id", None)
            if isinstance(member_id, int):
                member = interaction.guild.get_member(member_id)
        if not isinstance(member, discord.Member):
            return []

        action = getattr(interaction.namespace, "action", None)
        guild = interaction.guild

        bot_member = guild.me
        bot_top_role = bot_member.top_role if bot_member else None

        def is_manageable_by_moderator(r: discord.Role) -> bool:
            if is_bot_owner_id(interaction.user.id) or interaction.user.id == guild.owner_id:
                return True
            return r < interaction.user.top_role

        if action == "add":
            roles = [
                r
                for r in guild.roles
                if r != guild.default_role
                and not r.managed
                and r not in member.roles
                and (bot_top_role is None or r < bot_top_role)
                and is_manageable_by_moderator(r)
                and self._matches_role_query(r, current)
            ]
        else:
            roles = [
                r
                for r in member.roles
                if r != guild.default_role
                and not r.managed
                and (bot_top_role is None or r < bot_top_role)
                and is_manageable_by_moderator(r)
                and self._matches_role_query(r, current)
            ]

        roles.sort(key=lambda r: r.position, reverse=True)
        return [app_commands.Choice(name=r.name, value=str(r.id)) for r in roles[:25]]


    @commands.command(name="roleall", description="🏷️ Give a role to all members")
    @is_admin()
    async def roleall(self, ctx: commands.Context, *, role: discord.Role):
        """
        Give a role to all server members
        Usage: ,roleall <role>
        """
        # Security checks
        if role >= ctx.guild.me.top_role:
            return await ctx.reply(embed=ModEmbed.error("Bot Error", "I cannot manage this role as it's higher than or equal to my highest role."))
        
        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id and not is_bot_owner_id(ctx.author.id):
            return await ctx.reply(embed=ModEmbed.error("Permission Denied", "You cannot assign a role higher than or equal to your highest role."))
        
        if role.managed:
            return await ctx.reply(embed=ModEmbed.error("Managed Role", "This role is managed by an integration and cannot be manually assigned."))
        
        if role.permissions.administrator or role.permissions.manage_guild or role.permissions.manage_roles or role.permissions.ban_members or role.permissions.kick_members:
            return await ctx.reply(embed=ModEmbed.error("Dangerous Role", "You cannot mass-assign dangerous permissions."))
        
        await ctx.typing()
        
        success = []
        failed = []
        
        for member in ctx.guild.members:
            if is_bot_owner_id(member.id) and not is_bot_owner_id(ctx.author.id):
                continue
            if role in member.roles:
                continue
            
            try:
                await member.add_roles(role, reason=f"Mass role assignment by {ctx.author}")
                success.append(member.mention)
            except (discord.Forbidden, discord.HTTPException):
                failed.append(member.mention)
        
        embed = discord.Embed(
            title="🏷️ Bulk Role Assignment",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="✅ Added", value=f"**{len(success)}** members", inline=True)
        embed.add_field(name="❌ Failed", value=f"**{len(failed)}** members", inline=True)
        embed.add_field(name="Role", value=role.mention, inline=False)
        
        await ctx.reply(embed=embed)

    @commands.command(name="removeall", description="🗑️ Remove a role from all members")
    @is_admin()
    async def removeall(self, ctx: commands.Context, *, role: discord.Role):
        """
        Remove a role from all members who have it
        Usage: ,removeall <role>
        """
        await ctx.typing()
        
        success = []
        failed = []
        
        for member in ctx.guild.members:
            if is_bot_owner_id(member.id) and not is_bot_owner_id(ctx.author.id):
                continue
            if role not in member.roles:
                continue
            
            try:
                await member.remove_roles(role)
                success.append(member.mention)
            except (discord.Forbidden, discord.HTTPException):
                failed.append(member.mention)
        
        embed = discord.Embed(
            title="🗑️ Bulk Role Removal",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="✅ Removed", value=f"**{len(success)}** members", inline=True)
        embed.add_field(name="❌ Failed", value=f"**{len(failed)}** members", inline=True)
        embed.add_field(name="Role", value=role.mention, inline=False)
        
        await ctx.reply(embed=embed)

    # ==================== UTILITY COMMANDS ====================

    @commands.command(name="setnick", description="✏️ Change a user's nickname")
    @is_mod()
    async def setnick(self, ctx: commands.Context, user: discord.Member, *, nickname: Optional[str] = None):
        """
        Change or reset a user's nickname
        Usage: ,setnick <user> [nickname]
        """
        can_mod, error = await self.can_moderate(ctx.guild.id, ctx.author, user)
        if not can_mod:
            return await ctx.reply(embed=ModEmbed.error("Cannot Change", error))
        
        old_nick = user.display_name
        
        try:
            await user.edit(nick=nickname)
        except discord.Forbidden:
            return await ctx.reply(embed=ModEmbed.error("Failed", "I don't have permission to change nicknames."))
        
        new_nick = nickname or user.name
        embed = ModEmbed.success(
            "Nickname Changed",
            f"**{old_nick}** → **{new_nick}**"
        )
        await ctx.reply(embed=embed)

    @commands.command(name="nicknameall", description="✏️ Change all members' nicknames")
    @is_admin()
    async def nicknameall(self, ctx: commands.Context, *, nickname: str):
        """
        Bulk change nicknames for all members
        Usage: ,nicknameall <nickname_template>
        """
        await ctx.typing()
        
        changed = []
        failed = []
        
        for member in ctx.guild.members:
            if member.bot:
                continue
            
            try:
                new_nick = nickname.replace('{user}', member.name)
                await member.edit(nick=new_nick)
                changed.append(member.mention)
            except (discord.Forbidden, discord.HTTPException):
                failed.append(member.mention)
        
        embed = discord.Embed(
            title="✏️ Bulk Nickname Change",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="✅ Changed", value=f"**{len(changed)}** members", inline=True)
        embed.add_field(name="❌ Failed", value=f"**{len(failed)}** members", inline=True)
        
        await ctx.reply(embed=embed)

    @commands.command(name="resetnicks", description="🔄 Reset all nicknames")
    @is_admin()
    async def resetnicks(self, ctx: commands.Context):
        """
        Reset all nicknames to default
        Usage: ,resetnicks
        """
        await ctx.typing()
        
        reset = []
        failed = []
        
        for member in ctx.guild.members:
            if not member.nick:
                continue
            
            try:
                await member.edit(nick=None)
                reset.append(member.mention)
            except (discord.Forbidden, discord.HTTPException):
                failed.append(member.mention)
        
        embed = discord.Embed(
            title="🔄 Nicknames Reset",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="✅ Reset", value=f"**{len(reset)}** members", inline=True)
        embed.add_field(name="❌ Failed", value=f"**{len(failed)}** members", inline=True)
        
        await ctx.reply(embed=embed)

    @commands.command(name="quarantine")
    @is_senior_mod()
    async def quarantine(self, ctx: commands.Context, user: discord.Member, duration: Optional[str] = None, *, reason: str = "No reason provided"):
        """
        Quarantine a user (remove all roles)
        Usage: ,quarantine <user> [duration] [reason]
        """
        await self._quarantine_logic(ctx, user, duration, reason)

    @commands.command(name="unquarantine")
    @is_mod()
    async def unquarantine(self, ctx: commands.Context, user: discord.Member, *, reason: str = "Quarantine lifted"):
        """
        Unquarantine a user
        Usage: ,unquarantine <user> [reason]
        """
        await self._unquarantine_logic(ctx, user, reason)


    @commands.command(name="inrole", description="👥 List members with a specific role")
    @is_mod()
    async def inrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Display all members with a specific role
        Usage: ,inrole <role>
        """
        members = role.members
        
        if not members:
            return await ctx.reply(
                embed=ModEmbed.info("No Members", f"No one has the {role.mention} role.")
            )
        
        embed = discord.Embed(
            title=f"Members with {role.name}",
            color=role.color,
            timestamp=datetime.now(timezone.utc)
        )
        
        member_list = [m.mention for m in members[:30]]
        embed.description = ", ".join(member_list)
        
        if len(members) > 30:
            embed.set_footer(text=f"Showing 30 of {len(members)} members")
        else:
            embed.set_footer(text=f"{len(members)} total members")
        
        await ctx.reply(embed=embed)

    # ==================== EMOJI/STICKER MANAGEMENT ====================

    @staticmethod
    def _sanitize_emoji_name(raw: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", (raw or "").strip())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        return cleaned[:32]

    @staticmethod
    def _normalize_asset_url(raw: str) -> str:
        cleaned = (raw or "").strip()
        if cleaned.startswith("<") and cleaned.endswith(">"):
            cleaned = cleaned[1:-1].strip()
        if cleaned.startswith("`") and cleaned.endswith("`"):
            cleaned = cleaned[1:-1].strip()
        return cleaned

    @staticmethod
    def _validate_asset_url(url: str) -> Optional[str]:
        """Return an error string if invalid; otherwise None."""
        if not url:
            return "URL is required."
        if any(ch.isspace() for ch in url):
            return "URL must not contain spaces."
        if len(url) > 2048:
            return "URL is too long."

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return "URL must start with http:// or https:// and be a valid link."

        if len(url) > 1024:
            return "URL is too long for the log embed. Use a shorter direct image link."

        return None

    async def _create_emoji_from_url(
        self,
        *,
        guild: discord.Guild,
        name: str,
        url: str,
        reason: str,
    ) -> discord.Emoji:
        url = self._normalize_asset_url(url)
        if not (url.startswith('http://') or url.startswith('https://')):
            raise ValueError('invalid_url')

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError('fetch_failed')
                emoji_bytes = await response.read()

        if len(emoji_bytes) > 256 * 1024:
            raise ValueError('file_too_large')

        return await guild.create_custom_emoji(
            name=name,
            image=emoji_bytes,
            reason=reason,
        )

    async def _get_emoji_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        try:
            settings = await self.bot.db.get_settings(guild.id)
        except Exception:
            settings = {}
        channel_id = settings.get('emoji_log_channel') or settings.get('automod_log_channel')
        if channel_id:
            ch = guild.get_channel(int(channel_id))
            if isinstance(ch, discord.TextChannel):
                return ch
        return None

    @commands.group(name="emoji", invoke_without_command=True)
    async def emoji_group(self, ctx: commands.Context):
        """
        Emoji tools (add, steal, tutorial)
        Usage: 
          ,emoji add <name> <url>
          ,emoji steal <emojis>
          ,emoji tutorial
        """
        await self.emoji_tutorial(ctx)

    @emoji_group.command(name="tutorial")
    async def emoji_tutorial(self, ctx: commands.Context):
        """Show emoji submission tutorial"""
        steps = (
            "This server uses **admin approval** for new emojis.\n\n"
            "**Step 1: Get a direct image URL**\n"
            "• Use a direct link to a `.png`, `.jpg`, or `.gif`.\n"
            "• If you're using a Discord attachment, copy the attachment URL.\n\n"
            "**Step 2: Pick a name**\n"
            "• Only letters, numbers, and underscores.\n"
            "• Example: `cool_cat`, `pepe_laugh`.\n\n"
            "**Step 3: Submit the request**\n"
            "• Run: `,emoji add <name> <url>`\n\n"
            "**Step 4: Wait for approval**\n"
            "• An admin will approve/reject in `#emoji-logs`.\n\n"
        )
        embed = discord.Embed(
            title="Emoji Tutorial",
            description=steps,
            color=Colors.EMBED,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Tip: The bot will reject files over ~256KB.")
        
        try:
             gif = await _fetch_addemoji_tutorial_gif_file()
        except:
             gif = None

        if gif:
             embed.set_image(url=f"attachment://{ADD_EMOJI_TUTORIAL_GIF_FILENAME}")
             await ctx.reply(embed=embed, file=gif)
        else:
             embed.set_image(url=ADD_EMOJI_TUTORIAL_GIF_URL)
             await ctx.reply(embed=embed)

    @emoji_group.command(name="add")
    async def emoji_add(self, ctx: commands.Context, name: str, url: str):
        """Request to add a new emoji"""
        settings = await self.bot.db.get_settings(ctx.guild.id)
        restricted = settings.get("emoji_command_channel") or settings.get("emoji_command_channel_id") or EMOJI_COMMAND_CHANNEL_ID
        if restricted and ctx.channel.id != int(restricted):
             return await ctx.reply(embed=ModEmbed.error("Wrong Channel", f"Use emoji commands in <#{int(restricted)}>."));
        
        url = self._normalize_asset_url(url)
        url_error = self._validate_asset_url(url)
        if url_error:
            return await ctx.reply(embed=ModEmbed.error("Invalid URL", f"{url_error}\n\nExample: `https://.../image.png`"))
            
        emoji_name = self._sanitize_emoji_name(name)
        if len(emoji_name) < 2:
            return await ctx.reply(embed=ModEmbed.error('Invalid Name', 'Names must be 2+ chars.'))
            
        if any(e.name == emoji_name for e in ctx.guild.emojis):
            return await ctx.reply(embed=ModEmbed.error('Exists', f'`:{emoji_name}:` exists.'))
            
        log_channel = await self._get_emoji_log_channel(ctx.guild)
        if not log_channel:
             return await ctx.reply(embed=ModEmbed.error("Not Configured", "Ask admin to setup `#emoji-logs`."))
             
        view = EmojiApprovalView(self, requester_id=ctx.author.id, emoji_name=emoji_name, emoji_url=url)
        try:
            msg = await log_channel.send(view=view)
            view.message = msg
            await ctx.reply(embed=ModEmbed.success('Submitted', f'Sent to {log_channel.mention}.'))
        except Exception as e:
            await ctx.reply(embed=ModEmbed.error("Failed", f"Error: {e}"))

    @emoji_group.command(name="steal")
    async def emoji_steal(self, ctx: commands.Context, *, emojis: str):
        """Steal emojis"""
        matches = list(re.finditer(r"<(a?):([A-Za-z0-9_]+):(\d+)>", emojis))
        if not matches:
             return await ctx.reply(embed=ModEmbed.error("No Emojis", "Paste custom emojis."))
             
        log_channel = await self._get_emoji_log_channel(ctx.guild)
        if not log_channel:
             return await ctx.reply(embed=ModEmbed.error("Not Configured", "Ask admin to setup `#emoji-logs`."))

        submitted = []
        skipped = []
        failed = []
        existing_names = {e.name for e in ctx.guild.emojis}
        seen_names = set()
        
        for m in matches[:25]:
            try:
                animated = bool(m.group(1))
                ename = m.group(2)
                eid = m.group(3)
                dname = self._sanitize_emoji_name(ename)
                eurl = f"https://cdn.discordapp.com/emojis/{eid}.{'gif' if animated else 'png'}"
                
                if dname in existing_names or dname in seen_names:
                    skipped.append(ename)
                    continue
                seen_names.add(dname)
                
                view = EmojiApprovalView(self, requester_id=ctx.author.id, emoji_name=dname, emoji_url=eurl)
                msg = await log_channel.send(view=view)
                view.message = msg
                submitted.append(f"`:{dname}:`")
            except Exception as e:
                failed.append(f"{ename} ({type(e).__name__})")
                
        msg = ""
        if submitted: msg += f"Submitted {len(submitted)} to {log_channel.mention}."
        if skipped: msg += f"\nSkipped: {', '.join(skipped[:10])}"
        if failed: msg += f"\nFailed: {', '.join(failed[:10])}"
        
        await ctx.reply(embed=ModEmbed.success("Steal Report", msg or "Nothing processed."))

    # ==================== MODERATION HISTORY ====================

    @commands.command(name="case", description="📋 View a specific moderation case")
    @is_mod()
    async def case(self, ctx: commands.Context, case_number: int):
        """Display information about a specific case"""
        case = await self.bot.db.get_case(ctx.guild.id, case_number)
        
        if not case:
            return await ctx.reply(embed=ModEmbed.error("Not Found", f"Case #{case_number} does not exist."))
        
        try:
            user = await self.bot.fetch_user(case['user_id'])
            moderator = await self.bot.fetch_user(case['moderator_id'])
        except discord.NotFound:
            user = f"Unknown User ({case['user_id']})"
            moderator = f"Unknown Moderator ({case['moderator_id']})"
        
        embed = discord.Embed(
            title=f"Case #{case['case_number']} - {case['action']}",
            color=Colors.MOD,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="User", value=f"{user.mention if hasattr(user, 'mention') else user}", inline=True)
        embed.add_field(name="Moderator", value=f"{moderator.mention if hasattr(moderator, 'mention') else moderator}", inline=True)
        embed.add_field(name="Reason", value=case['reason'], inline=False)
        
        if hasattr(user, 'display_avatar'):
            embed.set_thumbnail(url=user.display_avatar.url)
        
        await ctx.reply(embed=embed)

    @commands.command(name="editcase", description="✏️ Edit a case's reason")
    @is_mod()
    async def editcase(self, ctx: commands.Context, case_number: int, *, reason: str):
        """Update the reason for a moderation case"""
        case = await self.bot.db.get_case(ctx.guild.id, case_number)
        
        if not case:
            return await ctx.reply(embed=ModEmbed.error("Not Found", f"Case #{case_number} does not exist."))
        
        await self.bot.db.update_case(ctx.guild.id, case_number, reason)
        
        embed = ModEmbed.success(
            "Case Updated",
            f"Case #{case_number} reason has been updated to:\n``````"
        )
        
        await ctx.reply(embed=embed)

    @commands.command(name="history", description="📜 View a user's moderation history")
    @is_mod()
    async def history(self, ctx: commands.Context, user: discord.Member):
        """Display all moderation cases for a user"""
        cases = await self.bot.db.get_user_cases(ctx.guild.id, user.id)
        
        if not cases:
            return await ctx.reply(embed=ModEmbed.info("No History", f"{user.mention} has no moderation history."))
        
        embed = discord.Embed(
            title=f"📜 Moderation History: {user.display_name}",
            description=f"Total cases: **{len(cases)}**",
            color=Colors.MOD,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        for case in cases[:10]:
            moderator = ctx.guild.get_member(case['moderator_id'])
            mod_display = moderator.display_name if moderator else f"ID: {case['moderator_id']}"
            
            embed.add_field(
                name=f"Case #{case['case_number']} - {case['action']}",
                value=f"**Reason:** {case['reason'][:100]}\n**By:** {mod_display}",
                inline=False
            )
        
        if len(cases) > 10:
            embed.set_footer(text=f"Showing 10 of {len(cases)} cases")
        
        await ctx.reply(embed=embed)

    @commands.command(name="modlogs", description="📋 View comprehensive moderation logs")
    @is_mod()
    async def modlogs(self, ctx: commands.Context, user: discord.Member):
        """View full moderation logs including warnings and notes"""
        await ctx.typing()
        
        guild_id = ctx.guild.id
        
        # Fetch all data concurrently
        cases = await self.bot.db.get_user_cases(guild_id, user.id)
        warnings = await self.bot.db.get_warnings(guild_id, user.id)
        notes = await self.bot.db.get_notes(guild_id, user.id)
        
        all_logs = []
        
        # Process Cases
        for c in cases:
            all_logs.append({
                'type': 'case',
                'action': c['action'],
                'reason': c['reason'],
                'mod_id': c['moderator_id'],
                'timestamp': str(c['created_at']), # Ensure string for parsing
                'id': c['case_number']
            })
            
        # Process Warnings
        for w in warnings:
             all_logs.append({
                'type': 'warn',
                'action': 'Warning',
                'reason': w['reason'],
                'mod_id': w['moderator_id'],
                'timestamp': str(w['created_at']),
                'id': w['id']
            })
             
        # Process Notes
        for n in notes:
             all_logs.append({
                'type': 'note',
                'action': 'Note',
                'reason': n['note'],
                'mod_id': n['moderator_id'],
                'timestamp': str(n['created_at']),
                'id': n['id']
            })
        
        if not all_logs:
            return await ctx.reply(embed=ModEmbed.info("No Logs", f"{user.mention} has no moderation logs."))
            
        # Sort by timestamp (newest first)
        def parse_ts(x):
            try:
                # Try standard replace first
                return datetime.fromisoformat(str(x['timestamp']).replace(' ', 'T'))
            except:
                return datetime.min

        all_logs.sort(key=parse_ts, reverse=True)
        
        # Pagination Logic (Basic: Display first 15)
        embed = discord.Embed(
            title=f"📋 Mod Logs: {user.display_name}",
            color=Colors.MOD,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        description_lines = []
        
        for log in all_logs[:15]:
            # Emoji mapping
            emoji = "📝"
            if log['type'] == 'case':
                if 'ban' in log['action'].lower(): emoji = "🔨"
                elif 'kick' in log['action'].lower(): emoji = "👢"
                elif 'mute' in log['action'].lower(): emoji = "🔇"
                else: emoji = "🛡️"
            elif log['type'] == 'warn':
                emoji = "⚠️"
            
            # Timestamp formatting
            ts_obj = parse_ts(log)
            time_str = f"<t:{int(ts_obj.timestamp())}:R>" if ts_obj != datetime.min else "Unknown"
            
            mod_user = ctx.guild.get_member(log['mod_id'])
            mod_name = mod_user.name if mod_user else f"ID:{log['mod_id']}"
            
            # Format line
            # e.g. 🔨 **Ban** (#12) • 5m ago • _Spamming_ • by ModName
            line = f"{emoji} **{log['action'].title()}**"
            if log['type'] == 'case':
                line += f" (#{log['id']})"
            
            reason_short = (log['reason'] or "No reason")[:50]
            if len(log['reason'] or "") > 50: reason_short += "..."
                
            line += f" • {time_str} • *{reason_short}* • by **{mod_name}**"
            description_lines.append(line)
            
        embed.description = "\n".join(description_lines)
        
        if len(all_logs) > 15:
            embed.set_footer(text=f"Showing recent 15 of {len(all_logs)} entries")
        
        await ctx.reply(embed=embed)

    @commands.command(name="note", description="📝 Add a note to a user")
    @is_mod()
    async def note(self, ctx: commands.Context, user: discord.Member, *, note: str):
        """Add a moderator note to a user"""
        await self.bot.db.add_note(ctx.guild.id, user.id, ctx.author.id, note)
        
        embed = ModEmbed.success(
            "Note Added",
            f"Added note to {user.mention}:\n``````"
        )
        
        await ctx.reply(embed=embed)

    @commands.command(name="notes", description="📋 View notes for a user")
    @is_mod()
    async def notes(self, ctx: commands.Context, user: discord.Member):
        """Display all notes for a user"""
        notes = await self.bot.db.get_notes(ctx.guild.id, user.id)
        
        if not notes:
            return await ctx.reply(embed=ModEmbed.info("No Notes", f"{user.mention} has no notes."))
        
        embed = discord.Embed(
            title=f"📋 Notes: {user.display_name}",
            color=Colors.INFO,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        for n in notes[:10]:
            moderator = ctx.guild.get_member(n['moderator_id'])
            mod_display = moderator.display_name if moderator else f"ID: {n['moderator_id']}"
            
            embed.add_field(
                name=f"Note #{n['id']}",
                value=f"**Content:** {n['content'][:100]}\n**By:** {mod_display}",
                inline=False
            )
        
        if len(notes) > 10:
            embed.set_footer(text=f"Showing 10 of {len(notes)} notes")
        
        await ctx.reply(embed=embed)

    # ==================== MODERATION STATS ====================

    @commands.command(name="modstats", description="📊 View moderation statistics")
    @is_mod()
    async def modstats(self, ctx: commands.Context, moderator: Optional[discord.Member] = None):
        """Display moderation statistics"""
        if moderator:
            stats = await self.bot.db.get_moderator_stats(ctx.guild.id, moderator.id)
            
            embed = discord.Embed(
                title=f"📊 Mod Stats: {moderator.display_name}",
                color=Colors.MOD,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_thumbnail(url=moderator.display_avatar.url)
        else:
            stats = await self.bot.db.get_guild_mod_stats(ctx.guild.id)
            
            embed = discord.Embed(
                title=f"📊 Server Moderation Stats",
                color=Colors.MOD,
                timestamp=datetime.now(timezone.utc)
            )
        
        # Action counts
        action_fields = {
            "⚠️ Warnings": stats.get('warns', 0),
            "👢 Kicks": stats.get('kicks', 0),
            "🔨 Bans": stats.get('bans', 0),
            "⏰ Tempbans": stats.get('tempbans', 0),
            "🔇 Mutes": stats.get('mutes', 0),
            "🔒 Quarantines": stats.get('quarantines', 0)
        }
        
        for action, count in action_fields.items():
            embed.add_field(name=action, value=str(count), inline=True)
        
        total_actions = sum(action_fields.values())
        embed.add_field(name="📈 Total Actions", value=str(total_actions), inline=False)
        
        await ctx.reply(embed=embed)

    # ==================== WELCOME SYSTEM ====================

    async def _send_welcome_message(
        self,
        *,
        member: discord.Member,
        channel: discord.abc.Messageable,
    ) -> None:
        settings = await self.bot.db.get_settings(member.guild.id)
        server_name = (settings.get("welcome_server_name") or getattr(Config, "WELCOME_SERVER_NAME", "") or "").strip()
        if not server_name:
            server_name = member.guild.name

        system_name = (settings.get("welcome_system_name") or getattr(Config, "WELCOME_SYSTEM_NAME", "Welcome System") or "").strip()
        if not system_name:
            system_name = "Welcome System"
        accent = getattr(Config, "EMBED_ACCENT_COLOR", getattr(Config, "COLOR_EMBED", 0x5865F2))
        card_accent = getattr(Config, "WELCOME_CARD_ACCENT_COLOR", accent)

        joined_at = member.joined_at or datetime.now(timezone.utc)
        try:
            ts = int(joined_at.timestamp())
        except Exception:
            ts = int(datetime.now(timezone.utc).timestamp())

        options = WelcomeCardOptions(
            accent_color=card_accent,
            server_name=f"{system_name} - Moderation",
        )

        card_file = await build_welcome_card_file(
            self.bot,
            member,
            filename=f"welcome_{member.id}.png",
            options=options,
        )

        view = discord.ui.LayoutView(timeout=60)
        view.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"# {system_name} - {server_name}"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(f"# \N{INVERTED EXCLAMATION MARK}Welcome to {server_name}!"),
                discord.ui.TextDisplay(
                    f"| User: {member.mention}\n"
                    f"| Joined On: <t:{ts}:D> at <t:{ts}:t>"
                ),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.MediaGallery(
                    discord.MediaGalleryItem(f"attachment://{card_file.filename}")
                ),
                accent_color=accent,
            )
        )

        await channel.send(view=view, file=card_file)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Send a branded welcome card to the configured welcome channel."""
        settings = await self.bot.db.get_settings(member.guild.id)
        channel_id = settings.get("welcome_channel")
        if not channel_id:
            return

        if member.bot:
            return

        channel = member.guild.get_channel(int(channel_id)) or self.bot.get_channel(int(channel_id))
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
            except Exception:
                return
        if getattr(channel, "guild", None) and channel.guild.id != member.guild.id:
            return

        try:
            await self._send_welcome_message(member=member, channel=channel)
        except Exception:
            return

    @app_commands.command(name="testwelcome", description="Send a preview of the welcome system card")
    @app_commands.describe(
        member="Member to preview (defaults to you)",
        channel="Channel to send the preview in (defaults to here)",
    )
    @is_mod()
    async def testwelcome(
        self,
        interaction: discord.Interaction,
        member: Optional[discord.Member] = None,
        channel: Optional[discord.TextChannel] = None,
    ):
        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Available", "This command can only be used in a server."),
                ephemeral=True,
            )

        target = member or interaction.user
        if not isinstance(target, discord.Member):
            target = interaction.guild.get_member(interaction.user.id)  # type: ignore[assignment]
        if not isinstance(target, discord.Member):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Found", "Could not resolve the target member."),
                ephemeral=True,
            )

        dest = channel or interaction.channel
        if dest is None:
            return await interaction.response.send_message(
                embed=ModEmbed.error("No Channel", "Could not determine where to send the preview."),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self._send_welcome_message(member=target, channel=dest)
        except Exception as e:
            return await interaction.followup.send(
                embed=ModEmbed.error("Failed", f"Could not send preview: `{type(e).__name__}`"),
                ephemeral=True,
            )

        return await interaction.followup.send(
            embed=ModEmbed.success("Sent", f"Welcome preview sent in {getattr(dest, 'mention', 'the channel')}."),
            ephemeral=True,
        )

    @app_commands.command(name="welcomeall", description="Send the welcome card for everyone in the server")
    @app_commands.describe(
        channel="Channel to send the welcome messages in (defaults to the configured welcome channel)",
        include_bots="Include bot accounts",
        confirm="Set to true to actually send (this can spam)",
        limit="Optional max members to welcome",
    )
    @is_mod()
    async def welcomeall(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        include_bots: bool = False,
        confirm: bool = False,
        limit: Optional[app_commands.Range[int, 1, 500]] = None,
    ):
        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Available", "This command can only be used in a server."),
                ephemeral=True,
            )

        dest = channel
        if dest is None:
            settings = await self.bot.db.get_settings(interaction.guild.id)
            channel_id = settings.get("welcome_channel")
            if channel_id:
                resolved = interaction.guild.get_channel(int(channel_id))
                if isinstance(resolved, discord.TextChannel):
                    dest = resolved

        if dest is None:
            if isinstance(interaction.channel, discord.TextChannel):
                dest = interaction.channel
            else:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("No Channel", "Could not determine where to send the welcome messages."),
                    ephemeral=True,
                )

        members: list[discord.Member] = list(getattr(interaction.guild, "members", []) or [])
        try:
            if not members or (
                interaction.guild.member_count
                and len(members) < int(interaction.guild.member_count * 0.75)
            ):
                members = [m async for m in interaction.guild.fetch_members(limit=None)]
        except Exception:
            pass

        if not include_bots:
            members = [m for m in members if not getattr(m, "bot", False)]

        if limit is not None:
            members = members[: int(limit)]

        if not members:
            return await interaction.response.send_message(
                embed=ModEmbed.info("Nothing To Do", "No members found to welcome."),
                ephemeral=True,
            )

        if not confirm:
            return await interaction.response.send_message(
                embed=ModEmbed.warning(
                    "Confirmation Required",
                    f"This will send **{len(members)}** welcome message(s) in {dest.mention}.\n"
                    "Re-run with `confirm: True` to proceed.",
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True, thinking=True)

        sent = 0
        failed = 0
        for m in members:
            try:
                await self._send_welcome_message(member=m, channel=dest)
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.35)

        return await interaction.followup.send(
            embed=ModEmbed.success(
                "Done",
                f"Sent **{sent}** welcome message(s) in {dest.mention}."
                + (f" Failed: **{failed}**." if failed else ""),
            ),
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
