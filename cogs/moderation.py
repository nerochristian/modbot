"""
Advanced Moderation System
Comprehensive moderation toolkit with hierarchy checks, logging, and database integration
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
import asyncio
import aiohttp
import re
import io
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
EMOJI_COMMAND_CHANNEL_ID = 1454265143792763054

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

    # ==================== UTILITY METHODS ====================

    async def get_user_level(self, guild_id: int, member: discord.Member) -> int:
        """
        Get the hierarchy level of a user based on roles
        Returns: int (0-100, higher = more power)
        """
        cache_key = f"{guild_id}:{member.id}"
        
        # Check cache first
        if cache_key in self._hierarchy_cache:
            cached_time, level = self._hierarchy_cache[cache_key]
            if (datetime.now() - cached_time).seconds < 300:  # 5min cache
                return level
        
        # Bot owner = max level
        if await self._is_bot_owner(member):
            self._hierarchy_cache[cache_key] = (datetime.now(), 100)
            return 100
        
        # Owner = max level
        if member.id == member.guild.owner_id:
            return 100
        
        # Admin perms = level 6
        if member.guild_permissions.administrator:
            return 6
        
        # Check role hierarchy from settings
        settings = await self.bot.db.get_settings(guild_id)
        user_role_ids = {r.id for r in member.roles}
        
        role_hierarchy = {
            'admin_role': 6,
            'supervisor_role': 5,
            'senior_mod_role': 4,
            'mod_role': 3,
            'trial_mod_role': 2,
            'staff_role': 1
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
        
        # Bot check
        if target.bot and target.top_role >= moderator.top_role:
            return False, "You cannot moderate this bot (role hierarchy)."
        
        # Hierarchy level check
        mod_level = await self.get_user_level(guild_id, moderator)
        target_level = await self.get_user_level(guild_id, target)
        
        if mod_level < target_level:
            return False, "You cannot moderate this user. They have equal or higher permissions."
        
        # Role position check
        if (
            target.top_role >= moderator.top_role
            and moderator.id != moderator.guild.owner_id
            and not moderator_is_owner
        ):
            return False, "You cannot moderate someone with a higher or equal role."
        
        return True, ""

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
        interaction: discord.Interaction,
        *,
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
        ephemeral: bool = False,
    ):
        """Send a response or followup depending on whether the interaction is already acknowledged."""
        try:
            if interaction.response.is_done():
                return await interaction.followup.send(
                    content=content, embed=embed, ephemeral=ephemeral
                )
            return await interaction.response.send_message(
                content=content, embed=embed, ephemeral=ephemeral
            )
        except discord.HTTPException:
            # Fallback when the interaction state changed mid-execution.
            try:
                return await interaction.followup.send(
                    content=content, embed=embed, ephemeral=ephemeral
                )
            except Exception:
                return None

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

    # ==================== WARNING COMMANDS ====================

    @app_commands.command(name="warn", description="⚠️ Issue a warning to a user")
    @app_commands.describe(
        user="The user to warn",
        reason="Reason for the warning"
    )
    @is_mod()
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided"
    ):
        """Warn a user and track in database"""
        can_mod, error = await self.can_moderate(interaction.guild_id, interaction.user, user)
        if not can_mod:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Cannot Warn", error),
                ephemeral=True
            )
        
        # Add to database
        await self.bot.db.add_warning(interaction.guild_id, user.id, interaction.user.id, reason)
        warnings = await self.bot.db.get_warnings(interaction.guild_id, user.id)
        case_num = await self.bot.db.create_case(
            interaction.guild_id, user.id, interaction.user.id, "Warn", reason
        )
        
        # Create embed
        embed = await self.create_mod_embed(
            title="⚠️ User Warned",
            user=user,
            moderator=interaction.user,
            reason=reason,
            color=Colors.WARNING,
            case_num=case_num,
            extra_fields={"Total Warnings": str(len(warnings))}
        )
        
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)
        
        # DM user
        dm_embed = discord.Embed(
            title=f"⚠️ Warning in {interaction.guild.name}",
            description=f"**Reason:** {reason}\n**Total Warnings:** {len(warnings)}",
            color=Colors.WARNING
        )
        await self.dm_user(user, dm_embed)

    @app_commands.command(name="warnings", description="📋 View all warnings for a user")
    @app_commands.describe(user="User to check")
    @is_mod()
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        """Display all warnings for a user"""
        warnings = await self.bot.db.get_warnings(interaction.guild_id, user.id)
        
        if not warnings:
            return await interaction.response.send_message(
                embed=ModEmbed.info("No Warnings", f"{user.mention} has no warnings."),
                ephemeral=True
            )
        
        embed = discord.Embed(
            title=f"⚠️ Warnings for {user.display_name}",
            description=f"Total: **{len(warnings)}** warning(s)",
            color=Colors.WARNING,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        for warn in warnings[:10]:  # Limit to 10 most recent
            moderator = interaction.guild.get_member(warn['moderator_id'])
            mod_display = moderator.display_name if moderator else f"ID: {warn['moderator_id']}"
            timestamp = warn.get('created_at', 'Unknown time')
            
            embed.add_field(
                name=f"Warning #{warn['id']}",
                value=f"**Reason:** {warn['reason'][:100]}\n**By:** {mod_display}\n**When:** {timestamp}",
                inline=False
            )
        
        if len(warnings) > 10:
            embed.set_footer(text=f"Showing 10 of {len(warnings)} warnings")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="delwarn", description="🗑️ Delete a specific warning")
    @app_commands.describe(warning_id="ID of the warning to delete")
    @is_mod()
    async def delwarn(self, interaction: discord.Interaction, warning_id: int):
        """Remove a warning from the database"""
        success = await self.bot.db.delete_warning(interaction.guild_id, warning_id)
        
        if success:
            embed = ModEmbed.success("Warning Deleted", f"Warning `#{warning_id}` has been removed.")
        else:
            embed = ModEmbed.error("Not Found", f"Warning `#{warning_id}` does not exist.")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clearwarnings", description="🧹 Clear all warnings for a user")
    @app_commands.describe(
        user="User whose warnings to clear",
        reason="Reason for clearing"
    )
    @is_senior_mod()
    async def clearwarnings(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided"
    ):
        """Clear all warnings for a user"""
        count = await self.bot.db.clear_warnings(interaction.guild_id, user.id)
        
        embed = ModEmbed.success(
            "Warnings Cleared",
            f"Cleared **{count}** warning(s) from {user.mention}.\n**Reason:** {reason}"
        )
        
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    # ==================== KICK & BAN COMMANDS ====================

    @app_commands.command(name="kick", description="👢 Kick a user from the server")
    @app_commands.describe(
        user="User to kick",
        reason="Reason for kick"
    )
    @is_mod()
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided"
    ):
        """Kick a user from the server"""
        can_mod, error = await self.can_moderate(interaction.guild_id, interaction.user, user)
        if not can_mod:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Cannot Kick", error),
                ephemeral=True
            )
        
        can_bot, bot_error = await self.can_bot_moderate(user, moderator=interaction.user)
        if not can_bot:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Bot Permission Error", bot_error),
                ephemeral=True
            )
        
        case_num = await self.bot.db.create_case(
            interaction.guild_id, user.id, interaction.user.id, "Kick", reason
        )
        
        # DM before kick
        dm_embed = discord.Embed(
            title=f"👢 Kicked from {interaction.guild.name}",
            description=f"**Reason:** {reason}",
            color=Colors.ERROR
        )
        await self.dm_user(user, dm_embed)
        
        # Perform kick
        try:
            await user.kick(reason=f"{interaction.user}: {reason}")
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I don't have permission to kick this user."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", f"An error occurred: {str(e)}"),
                ephemeral=True
            )
        
        embed = await self.create_mod_embed(
            title="👢 User Kicked",
            user=user,
            moderator=interaction.user,
            reason=reason,
            color=Colors.ERROR,
            case_num=case_num
        )
        
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="ban", description="🔨 Ban a user from the server")
    @app_commands.describe(
        user="User to ban",
        reason="Reason for ban",
        delete_days="Days of messages to delete (0-7)"
    )
    @is_senior_mod()
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided",
        delete_days: app_commands.Range[int, 0, 7] = 1
    ):
        """Permanently ban a user"""
        can_mod, error = await self.can_moderate(interaction.guild_id, interaction.user, user)
        if not can_mod:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Cannot Ban", error),
                ephemeral=True
            )
        
        can_bot, bot_error = await self.can_bot_moderate(user, moderator=interaction.user)
        if not can_bot:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Bot Permission Error", bot_error),
                ephemeral=True
            )
        
        case_num = await self.bot.db.create_case(
            interaction.guild_id, user.id, interaction.user.id, "Ban", reason
        )
        
        # DM before ban
        dm_embed = discord.Embed(
            title=f"🔨 Banned from {interaction.guild.name}",
            description=f"**Reason:** {reason}\n\nYou have been permanently banned.",
            color=Colors.DARK_RED
        )
        await self.dm_user(user, dm_embed)
        
        # Execute ban
        try:
            await user.ban(
                reason=f"{interaction.user}: {reason}",
                delete_message_days=delete_days
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I don't have permission to ban this user."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", f"An error occurred: {str(e)}"),
                ephemeral=True
            )
        
        embed = await self.create_mod_embed(
            title="🔨 User Banned",
            user=user,
            moderator=interaction.user,
            reason=reason,
            color=Colors.DARK_RED,
            case_num=case_num,
            extra_fields={"Messages Deleted": f"{delete_days} day(s)"}
        )
        
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="tempban", description="⏰ Temporarily ban a user")
    @app_commands.describe(
        user="User to temporarily ban",
        duration="Ban duration (e.g., 1d, 7d, 30d)",
        reason="Reason for ban"
    )
    @is_senior_mod()
    async def tempban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: str,
        reason: str = "No reason provided"
    ):
        """Temporarily ban a user with automatic unban"""
        can_mod, error = await self.can_moderate(interaction.guild_id, interaction.user, user)
        if not can_mod:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Cannot Tempban", error),
                ephemeral=True
            )
        
        can_bot, bot_error = await self.can_bot_moderate(user, moderator=interaction.user)
        if not can_bot:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Bot Permission Error", bot_error),
                ephemeral=True
            )
        
        # Parse duration
        parsed = parse_time(duration)
        if not parsed:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Invalid Duration", "Use format like `1d`, `7d`, `30d`"),
                ephemeral=True
            )
        
        delta, human_duration = parsed
        expires_at = datetime.now(timezone.utc) + delta
        
        case_num = await self.bot.db.create_case(
            interaction.guild_id, user.id, interaction.user.id,
            "Tempban", reason, human_duration
        )
        
        await self.bot.db.add_tempban(
            interaction.guild_id, user.id, interaction.user.id, reason, expires_at
        )
        
        # DM user
        dm_embed = discord.Embed(
            title=f"⏰ Temporarily Banned from {interaction.guild.name}",
            description=f"**Reason:** {reason}\n**Duration:** {human_duration}\n**Expires:** <t:{int(expires_at.timestamp())}:F>",
            color=Colors.DARK_RED
        )
        await self.dm_user(user, dm_embed)
        
        # Execute ban
        try:
            await user.ban(
                reason=f"[TEMPBAN] {interaction.user}: {reason} ({human_duration})",
                delete_message_days=1
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I don't have permission to ban this user."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", f"An error occurred: {str(e)}"),
                ephemeral=True
            )
        
        embed = await self.create_mod_embed(
            title="⏰ User Temporarily Banned",
            user=user,
            moderator=interaction.user,
            reason=reason,
            color=Colors.DARK_RED,
            case_num=case_num,
            extra_fields={
                "Duration": human_duration,
                "Expires": f"<t:{int(expires_at.timestamp())}:R>"
            }
        )
        
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="unban", description="🔓 Unban a user")
    @app_commands.describe(
        user_id="ID of the user to unban",
        reason="Reason for unban"
    )
    @is_senior_mod()
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: str = "No reason provided"
    ):
        """Unban a previously banned user"""
        try:
            user = await self.bot.fetch_user(int(user_id))
        except (ValueError, discord.NotFound):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Invalid User", "Could not find a user with that ID."),
                ephemeral=True
            )
        
        try:
            await interaction.guild.unban(user, reason=f"{interaction.user}: {reason}")
        except discord.NotFound:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Banned", "This user is not currently banned."),
                ephemeral=True
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I don't have permission to unban users."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", f"An error occurred: {str(e)}"),
                ephemeral=True
            )
        
        # Remove from tempban list if exists
        await self.bot.db.remove_tempban(interaction.guild_id, user.id)
        
        case_num = await self.bot.db.create_case(
            interaction.guild_id, user.id, interaction.user.id, "Unban", reason
        )
        
        embed = await self.create_mod_embed(
            title="🔓 User Unbanned",
            user=user,
            moderator=interaction.user,
            reason=reason,
            color=Colors.SUCCESS,
            case_num=case_num
        )
        
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="softban", description="🧹 Softban (ban + immediate unban to delete messages)")
    @app_commands.describe(
        user="User to softban",
        reason="Reason for softban"
    )
    @is_senior_mod()
    async def softban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided"
    ):
        """Ban and immediately unban to delete messages"""
        can_mod, error = await self.can_moderate(interaction.guild_id, interaction.user, user)
        if not can_mod:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Cannot Softban", error),
                ephemeral=True
            )
        
        can_bot, bot_error = await self.can_bot_moderate(user)
        if not can_bot:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Bot Permission Error", bot_error),
                ephemeral=True
            )
        
        case_num = await self.bot.db.create_case(
            interaction.guild_id, user.id, interaction.user.id, "Softban", reason
        )
        
        # DM user
        dm_embed = discord.Embed(
            title=f"🧹 Softbanned from {interaction.guild.name}",
            description=f"**Reason:** {reason}\n\nYou can rejoin the server.",
            color=Colors.ERROR
        )
        await self.dm_user(user, dm_embed)
        
        # Execute softban
        try:
            await user.ban(reason=f"[SOFTBAN] {reason}", delete_message_days=7)
            await interaction.guild.unban(user, reason="Softban - immediate unban")
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I don't have permission to ban this user."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", f"An error occurred: {str(e)}"),
                ephemeral=True
            )
        
        embed = await self.create_mod_embed(
            title="🧹 User Softbanned",
            user=user,
            moderator=interaction.user,
            reason=reason,
            color=Colors.ERROR,
            case_num=case_num
        )
        
        embed.set_footer(text=f"Case #{case_num} | 7 days of messages deleted")
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="massban", description="🔨 Ban multiple users at once")
    @app_commands.describe(
        user_ids="User IDs separated by spaces",
        reason="Reason for mass ban"
    )
    @is_admin()
    async def massban(
        self,
        interaction: discord.Interaction,
        user_ids: str,
        reason: str = "Mass ban"
    ):
        """Ban multiple users by ID"""
        await interaction.response.defer()
        
        ids = user_ids.split()
        banned = []
        failed = []
        
        for uid in ids:
            try:
                user_id = int(uid.strip())
                user = await self.bot.fetch_user(user_id)
                
                await interaction.guild.ban(
                    user,
                    reason=f"[MASSBAN] {interaction.user}: {reason}"
                )
                banned.append(f"{user} (`{user.id}`)")
            except ValueError:
                failed.append(f"`{uid}` (invalid ID)")
            except discord.NotFound:
                failed.append(f"`{uid}` (user not found)")
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
        
        await interaction.followup.send(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="banlist", description="📋 View all banned users")
    @is_mod()
    async def banlist(self, interaction: discord.Interaction):
        """Display list of banned users"""
        try:
            bans = [entry async for entry in interaction.guild.bans(limit=50)]
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "I don't have permission to view bans."),
                ephemeral=True
            )
        
        if not bans:
            return await interaction.response.send_message(
                embed=ModEmbed.info("No Bans", "No users are currently banned."),
                ephemeral=True
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
        
        await interaction.response.send_message(embed=embed)

    # ==================== TIMEOUT/MUTE COMMANDS ====================

    @app_commands.command(name="mute", description="🔇 Timeout a user")
    @app_commands.describe(
        user="User to timeout",
        duration="Duration (e.g., 10m, 1h, 1d)",
        reason="Reason for timeout"
    )
    @is_mod()
    async def mute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: str = "1h",
        reason: str = "No reason provided"
    ):
        """Timeout (mute) a user"""
        can_mod, error = await self.can_moderate(interaction.guild_id, interaction.user, user)
        if not can_mod:
            return await self._respond(
                interaction,
                embed=ModEmbed.error("Cannot Mute", error),
                ephemeral=True
            )
        
        can_bot, bot_error = await self.can_bot_moderate(user, moderator=interaction.user)
        if not can_bot:
            return await self._respond(
                interaction,
                embed=ModEmbed.error("Bot Permission Error", bot_error),
                ephemeral=True
            )

        bot_member = interaction.guild.me if interaction.guild else None
        if not bot_member or not bot_member.guild_permissions.moderate_members:
            return await self._respond(
                interaction,
                embed=ModEmbed.error(
                    "Bot Missing Permissions",
                    "I need the **Timeout Members** permission to mute (timeout) users.",
                ),
                ephemeral=True,
            )
        
        # Parse duration
        parsed = parse_time(duration)
        if not parsed:
            return await self._respond(
                interaction,
                embed=ModEmbed.error("Invalid Duration", "Use format like `10m`, `1h`, `1d`"),
                ephemeral=True
            )
        
        delta, human_duration = parsed
        
        # Discord timeout max = 28 days
        if delta.total_seconds() > 28 * 24 * 60 * 60:
            return await self._respond(
                interaction,
                embed=ModEmbed.error("Duration Too Long", "Maximum timeout is 28 days."),
                ephemeral=True
            )
        
        # Execute timeout
        try:
            await user.timeout(delta, reason=f"{interaction.user}: {reason}")
        except discord.Forbidden:
            return await self._respond(
                interaction,
                embed=ModEmbed.error(
                    "Failed",
                    "I couldn't timeout this user. Make sure I have **Timeout Members** permission and my role is above the target.",
                ),
                ephemeral=True,
            )
        except discord.HTTPException as e:
            return await self._respond(
                interaction,
                embed=ModEmbed.error("Failed", f"An error occurred: {str(e)}"),
                ephemeral=True
            )

        case_num = await self.bot.db.create_case(
            interaction.guild_id,
            user.id,
            interaction.user.id,
            "Mute",
            reason,
            human_duration,
        )
        
        embed = await self.create_mod_embed(
            title="🔇 User Muted",
            user=user,
            moderator=interaction.user,
            reason=reason,
            color=Colors.WARNING,
            case_num=case_num,
            extra_fields={"Duration": human_duration}
        )
        
        await self._respond(interaction, embed=embed)
        await self.log_action(interaction.guild, embed)
        
        # DM user
        dm_embed = discord.Embed(
            title=f"🔇 Muted in {interaction.guild.name}",
            description=f"**Reason:** {reason}\n**Duration:** {human_duration}",
            color=Colors.WARNING
        )
        await self.dm_user(user, dm_embed)

    @app_commands.command(name="unmute", description="🔊 Remove timeout from a user")
    @app_commands.describe(
        user="User to unmute",
        reason="Reason for unmute"
    )
    @is_mod()
    async def unmute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided"
    ):
        """Remove timeout from a user"""
        if not user.is_timed_out():
            return await self._respond(
                interaction,
                embed=ModEmbed.error("Not Muted", f"{user.mention} is not currently muted."),
                ephemeral=True
            )

        bot_member = interaction.guild.me if interaction.guild else None
        if not bot_member or not bot_member.guild_permissions.moderate_members:
            return await self._respond(
                interaction,
                embed=ModEmbed.error(
                    "Bot Missing Permissions",
                    "I need the **Timeout Members** permission to unmute (remove timeouts).",
                ),
                ephemeral=True,
            )
        
        try:
            await user.timeout(None, reason=f"{interaction.user}: {reason}")
        except discord.Forbidden:
            return await self._respond(
                interaction,
                embed=ModEmbed.error(
                    "Failed",
                    "I couldn't unmute this user. Make sure I have **Timeout Members** permission and my role is above the target.",
                ),
                ephemeral=True,
            )
        except discord.HTTPException as e:
            return await self._respond(
                interaction,
                embed=ModEmbed.error("Failed", f"An error occurred: {str(e)}"),
                ephemeral=True
            )

        case_num = await self.bot.db.create_case(
            interaction.guild_id, user.id, interaction.user.id, "Unmute", reason
        )
        
        embed = await self.create_mod_embed(
            title="🔊 User Unmuted",
            user=user,
            moderator=interaction.user,
            reason=reason,
            color=Colors.SUCCESS,
            case_num=case_num
        )
        
        await self._respond(interaction, embed=embed)
        await self.log_action(interaction.guild, embed)

    # ==================== CHANNEL MANAGEMENT ====================

    @app_commands.command(name="lock", description="🔒 Lock a channel")
    @app_commands.describe(
        channel="Channel to lock (current channel if not specified)",
        reason="Reason for lock"
    )
    @is_mod()
    async def lock(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        reason: str = "No reason provided"
    ):
        """Lock a channel (prevent @everyone from sending messages)"""
        channel = channel or interaction.channel
        
        try:
            await channel.set_permissions(
                interaction.guild.default_role,
                send_messages=False,
                reason=f"{interaction.user}: {reason}"
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I don't have permission to edit channel permissions."),
                ephemeral=True
            )
        
        embed = discord.Embed(
            title="🔒 Channel Locked",
            description=f"{channel.mention} has been locked.",
            color=Colors.ERROR
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        if channel != interaction.channel:
            lock_notice = discord.Embed(
                title="🔒 Channel Locked",
                description=f"Locked by {interaction.user.mention}\n**Reason:** {reason}",
                color=Colors.ERROR
            )
            await channel.send(embed=lock_notice)

    @app_commands.command(name="unlock", description="🔓 Unlock a channel")
    @app_commands.describe(
        channel="Channel to unlock (current channel if not specified)",
        reason="Reason for unlock"
    )
    @is_mod()
    async def unlock(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        reason: str = "No reason provided"
    ):
        """Unlock a channel"""
        channel = channel or interaction.channel
        
        try:
            await channel.set_permissions(
                interaction.guild.default_role,
                send_messages=None,
                reason=f"{interaction.user}: {reason}"
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I don't have permission to edit channel permissions."),
                ephemeral=True
            )
        
        embed = discord.Embed(
            title="🔓 Channel Unlocked",
            description=f"{channel.mention} has been unlocked.",
            color=Colors.SUCCESS
        )
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="glock", description="🔒 Only the Glock role can talk in the channel")
    @app_commands.describe(
        channel="Channel to glock (current channel if not specified)",
        all="Apply to all text channels in the server",
        reason="Reason for glock",
    )
    @is_mod()
    async def glock(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        all: bool = False,
        reason: str = "No reason provided",
    ):
        """Restrict chatting so only members with the Glock role can send messages."""
        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Available", "This command can only be used in a server."),
                ephemeral=True,
            )

        glock_role_id = 1448478745953435741
        glock_role = interaction.guild.get_role(glock_role_id)
        if glock_role is None:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Role", f"Role `{glock_role_id}` not found in this server."),
                ephemeral=True,
            )

        async def _apply(ch: discord.TextChannel) -> bool:
            try:
                await ch.set_permissions(
                    interaction.guild.default_role,
                    send_messages=False,
                    send_messages_in_threads=False,
                    reason=f"[GLOCK] {interaction.user}: {reason}",
                )
                await ch.set_permissions(
                    glock_role,
                    send_messages=True,
                    send_messages_in_threads=True,
                    reason=f"[GLOCK] {interaction.user}: {reason}",
                )
                return True
            except (discord.Forbidden, discord.HTTPException):
                return False

        if all:
            await interaction.response.defer(ephemeral=True, thinking=True)
            ok = 0
            failed = 0
            for ch in interaction.guild.text_channels:
                if await _apply(ch):
                    ok += 1
                else:
                    failed += 1

            return await interaction.followup.send(
                embed=ModEmbed.success(
                    "Glocked",
                    f"Applied to **{ok}** channel(s)."
                    + (f" Failed: **{failed}**." if failed else ""),
                ),
                ephemeral=True,
            )

        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Invalid Channel", "Please run this in a text channel or provide one."),
                ephemeral=True,
            )

        if not await _apply(target):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I couldn't edit permissions for that channel."),
                ephemeral=True,
            )

        return await interaction.response.send_message(
            embed=ModEmbed.success(
                "Glocked",
                f"{target.mention} is now restricted to {glock_role.mention}.",
            )
        )

    @app_commands.command(name="gunlock", description="🔓 Remove Glock-role-only channel restriction")
    @app_commands.describe(
        channel="Channel to gunlock (current channel if not specified)",
        all="Apply to all text channels in the server",
        reason="Reason for gunlock",
    )
    @is_mod()
    async def gunlock(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        all: bool = False,
        reason: str = "No reason provided",
    ):
        """Remove glock restrictions."""
        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Available", "This command can only be used in a server."),
                ephemeral=True,
            )

        glock_role_id = 1448478745953435741
        glock_role = interaction.guild.get_role(glock_role_id)
        if glock_role is None:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Role", f"Role `{glock_role_id}` not found in this server."),
                ephemeral=True,
            )

        async def _revert(ch: discord.TextChannel) -> bool:
            try:
                everyone_overwrite = ch.overwrites_for(interaction.guild.default_role)
                glock_overwrite = ch.overwrites_for(glock_role)

                looks_like_glocked = (
                    everyone_overwrite.send_messages is False
                    and glock_overwrite.send_messages is True
                )
                if not looks_like_glocked:
                    return False

                await ch.set_permissions(
                    interaction.guild.default_role,
                    send_messages=None,
                    send_messages_in_threads=None,
                    reason=f"[GUNLOCK] {interaction.user}: {reason}",
                )
                await ch.set_permissions(
                    glock_role,
                    send_messages=None,
                    send_messages_in_threads=None,
                    reason=f"[GUNLOCK] {interaction.user}: {reason}",
                )
                return True
            except (discord.Forbidden, discord.HTTPException):
                return False

        if all:
            await interaction.response.defer(ephemeral=True, thinking=True)
            ok = 0
            skipped = 0
            failed = 0
            for ch in interaction.guild.text_channels:
                try:
                    reverted = await _revert(ch)
                except Exception:
                    failed += 1
                    continue
                if reverted:
                    ok += 1
                else:
                    skipped += 1

            return await interaction.followup.send(
                embed=ModEmbed.success(
                    "Gunlocked",
                    f"Reverted **{ok}** channel(s). Skipped: **{skipped}**."
                    + (f" Failed: **{failed}**." if failed else ""),
                ),
                ephemeral=True,
            )

        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Invalid Channel", "Please run this in a text channel or provide one."),
                ephemeral=True,
            )

        reverted = await _revert(target)
        if not reverted:
            return await interaction.response.send_message(
                embed=ModEmbed.info("Not Glocked", f"{target.mention} doesn't look glocked."),
                ephemeral=True,
            )

        return await interaction.response.send_message(
            embed=ModEmbed.success("Gunlocked", f"{target.mention} is unlocked."),
        )

    @app_commands.command(name="slowmode", description="🐌 Set channel slowmode")
    @app_commands.describe(
        seconds="Slowmode delay in seconds (0 to disable, max 21600)",
        channel="Channel to modify (current if not specified)"
    )
    @is_mod()
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: app_commands.Range[int, 0, 21600],
        channel: Optional[discord.TextChannel] = None
    ):
        """Set slowmode delay for a channel"""
        channel = channel or interaction.channel
        
        try:
            await channel.edit(slowmode_delay=seconds)
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I don't have permission to edit this channel."),
                ephemeral=True
            )
        
        if seconds == 0:
            embed = ModEmbed.success(
                "Slowmode Disabled",
                f"Slowmode has been disabled in {channel.mention}."
            )
        else:
            embed = ModEmbed.success(
                "Slowmode Enabled",
                f"Slowmode set to **{seconds}s** in {channel.mention}."
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="lockdown", description="🚨 Lock all channels")
    @app_commands.describe(reason="Reason for server lockdown")
    @is_admin()
    async def lockdown(
        self,
        interaction: discord.Interaction,
        reason: str = "Server lockdown"
    ):
        """Lock all text channels in the server"""
        await interaction.response.defer()
        
        locked = []
        failed = []
        
        for channel in interaction.guild.text_channels:
            try:
                await channel.set_permissions(
                    interaction.guild.default_role,
                    send_messages=False,
                    reason=f"[LOCKDOWN] {reason}"
                )
                locked.append(channel.mention)
            except discord.Forbidden:
                failed.append(channel.mention)
            except discord.HTTPException:
                failed.append(channel.mention)
        
        embed = discord.Embed(
            title="🚨 Server Lockdown Initiated",
            description=f"Locked **{len(locked)}** channels.",
            color=Colors.DARK_RED,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
        
        if failed:
            embed.add_field(
                name=f"❌ Failed ({len(failed)})",
                value=", ".join(failed[:10]) + (f" ...and {len(failed) - 10} more" if len(failed) > 10 else ""),
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="unlockdown", description="✅ Unlock all channels")
    @app_commands.describe(reason="Reason for lifting lockdown")
    @is_admin()
    async def unlockdown(
        self,
        interaction: discord.Interaction,
        reason: str = "Lockdown lifted"
    ):
        """Unlock all text channels in the server"""
        await interaction.response.defer()
        
        unlocked = []
        failed = []
        
        for channel in interaction.guild.text_channels:
            try:
                await channel.set_permissions(
                    interaction.guild.default_role,
                    send_messages=None,
                    reason=f"[UNLOCKDOWN] {reason}"
                )
                unlocked.append(channel.mention)
            except discord.Forbidden:
                failed.append(channel.mention)
            except discord.HTTPException:
                failed.append(channel.mention)
        
        embed = discord.Embed(
            title="✅ Lockdown Lifted",
            description=f"Unlocked **{len(unlocked)}** channels.",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
        
        if failed:
            embed.add_field(
                name=f"❌ Failed ({len(failed)})",
                value=", ".join(failed[:10]) + (f" ...and {len(failed) - 10} more" if len(failed) > 10 else ""),
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="nuke", description="💥 Clone and delete a channel")
    @app_commands.describe(channel="Channel to nuke (current if not specified)")
    @is_admin()
    async def nuke(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None
    ):
        """Delete and recreate a channel (clears all messages)"""
        channel = channel or interaction.channel
        
        try:
            position = channel.position
            new_channel = await channel.clone(reason=f"Nuked by {interaction.user}")
            await new_channel.edit(position=position)
            await channel.delete(reason=f"Nuked by {interaction.user}")
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I don't have permission to clone/delete channels."),
                ephemeral=True
            )
        
        embed = discord.Embed(
            title="💥 Channel Nuked",
            description=f"This channel has been nuked by {interaction.user.mention}.",
            color=Colors.ERROR
        )
        embed.set_image(url="https://media.giphy.com/media/HhTXt43pk1I1W/giphy.gif")
        
        await new_channel.send(embed=embed)

    # ==================== MESSAGE PURGE COMMANDS ====================

    @app_commands.command(name="purge", description="🗑️ Delete multiple messages")
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Only delete messages from this user (optional)"
    )
    @is_mod()
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
        user: Optional[discord.Member] = None
    ):
        """Bulk delete messages"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            if user:
                deleted = await interaction.channel.purge(limit=amount, check=lambda m: m.author.id == user.id)
            else:
                deleted = await interaction.channel.purge(limit=amount)
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=ModEmbed.error("Failed", "I don't have permission to delete messages."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            return await interaction.followup.send(
                embed=ModEmbed.error("Failed", f"An error occurred: {str(e)}"),
                ephemeral=True
            )
        
        user_text = f" from {user.mention}" if user else ""
        embed = ModEmbed.success("Messages Purged", f"Deleted **{len(deleted)}** message(s){user_text}.")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="purgebots", description="🤖 Delete bot messages")
    @app_commands.describe(amount="Number of messages to check (1-100)")
    @is_mod()
    async def purgebots(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100] = 100
    ):
        """Delete messages from bots"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            deleted = await interaction.channel.purge(limit=amount, check=lambda m: m.author.bot)
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=ModEmbed.error("Failed", "I don't have permission to delete messages."),
                ephemeral=True
            )
        
        embed = ModEmbed.success("Bot Messages Purged", f"Deleted **{len(deleted)}** bot messages.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="purgecontains", description="🔍 Delete messages containing text")
    @app_commands.describe(
        text="Text to search for",
        amount="Number of messages to check (1-100)"
    )
    @is_mod()
    async def purgecontains(
        self,
        interaction: discord.Interaction,
        text: str,
        amount: app_commands.Range[int, 1, 100] = 100
    ):
        """Delete messages containing specific text"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            deleted = await interaction.channel.purge(limit=amount, check=lambda m: text.lower() in m.content.lower())
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=ModEmbed.error("Failed", "I don't have permission to delete messages."),
                ephemeral=True
            )
        
        embed = ModEmbed.success("Messages Purged", f"Deleted **{len(deleted)}** messages containing `{text}`.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="purgeembeds", description="📦 Delete messages with embeds")
    @app_commands.describe(amount="Number of messages to check (1-100)")
    @is_mod()
    async def purgeembeds(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100] = 100
    ):
        """Delete messages containing embeds"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            deleted = await interaction.channel.purge(limit=amount, check=lambda m: len(m.embeds) > 0)
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=ModEmbed.error("Failed", "I don't have permission to delete messages."),
                ephemeral=True
            )
        
        embed = ModEmbed.success("Embed Messages Purged", f"Deleted **{len(deleted)}** messages with embeds.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="purgeimages", description="🖼️ Delete messages with attachments")
    @app_commands.describe(amount="Number of messages to check (1-100)")
    @is_mod()
    async def purgeimages(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100] = 100
    ):
        """Delete messages with attachments"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            deleted = await interaction.channel.purge(limit=amount, check=lambda m: len(m.attachments) > 0)
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=ModEmbed.error("Failed", "I don't have permission to delete messages."),
                ephemeral=True
            )
        
        embed = ModEmbed.success("Image Messages Purged", f"Deleted **{len(deleted)}** messages with attachments.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="purgelinks", description="🔗 Delete messages with links")
    @app_commands.describe(amount="Number of messages to check (1-100)")
    @is_mod()
    async def purgelinks(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100] = 100
    ):
        """Delete messages containing URLs"""
        await interaction.response.defer(ephemeral=True)
        
        url_pattern = re.compile(r'https?://')
        
        try:
            deleted = await interaction.channel.purge(limit=amount, check=lambda m: url_pattern.search(m.content))
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=ModEmbed.error("Failed", "I don't have permission to delete messages."),
                ephemeral=True
            )
        
        embed = ModEmbed.success("Link Messages Purged", f"Deleted **{len(deleted)}** messages with links.")
        await interaction.followup.send(embed=embed, ephemeral=True)

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

    @app_commands.command(name="role", description="🏷️ Manage user roles")
    @app_commands.describe(
        action="Action to perform",
        user="User to modify",
        role="Role to add/remove"
    )
    @is_mod()
    async def role(
        self,
        interaction: discord.Interaction,
        action: Literal["add", "remove"],
        user: discord.Member,
        role: str
    ):
        """Add or remove a role from a user"""
        can_mod, error = await self.can_moderate(interaction.guild_id, interaction.user, user)
        if not can_mod:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Cannot Modify Roles", error),
                ephemeral=True
            )

        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Guild Only", "This command can only be used in a server."),
                ephemeral=True
            )

        role_obj: Optional[discord.Role] = None
        role_id = self._parse_role_id_input(role)
        if role_id is not None:
            role_obj = interaction.guild.get_role(role_id)
        else:
            role_name = (role or "").strip().lower()
            if role_name:
                role_obj = discord.utils.find(lambda r: r.name.lower() == role_name, interaction.guild.roles)

        if not role_obj or role_obj == interaction.guild.default_role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Role Not Found", "Pick a valid role from the suggestions."),
                ephemeral=True
            )

        role = role_obj

        # Check bot hierarchy
        bot_member = interaction.guild.me
        if role >= bot_member.top_role:
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Role Too High",
                    f"I can't manage {role.mention} because it's higher than or equal to my top role."
                ),
                ephemeral=True
            )
        
        # Check moderator hierarchy
        if (
            role >= interaction.user.top_role
            and interaction.user.id != interaction.guild.owner_id
            and not is_bot_owner_id(interaction.user.id)
        ):
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Role Too High",
                    f"You can't manage {role.mention} because it's higher than or equal to your top role."
                ),
                ephemeral=True
            )
        
        try:
            if action == "add":
                if role in user.roles:
                    return await interaction.response.send_message(
                        embed=ModEmbed.error("Already Has Role", f"{user.mention} already has {role.mention}."),
                        ephemeral=True
                    )
                
                await user.add_roles(role, reason=f"Added by {interaction.user}")
                embed = ModEmbed.success("Role Added", f"Gave {role.mention} to {user.mention}.")
            else:
                if role not in user.roles:
                    return await interaction.response.send_message(
                        embed=ModEmbed.error("Doesn't Have Role", f"{user.mention} doesn't have {role.mention}."),
                        ephemeral=True
                    )
                
                await user.remove_roles(role, reason=f"Removed by {interaction.user}")
                embed = ModEmbed.success("Role Removed", f"Removed {role.mention} from {user.mention}.")
            
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I don't have permission to manage roles."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                embed=ModEmbed.error("Failed", f"An error occurred: {str(e)}"),
                ephemeral=True
            )

    @role.autocomplete("role")
    async def role_role_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        return await self._role_autocomplete(interaction, current)

    @app_commands.command(name="roleall", description="🏷️ Give a role to all members")
    @app_commands.describe(role="Role to give to all members")
    @is_admin()
    async def roleall(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        """Give a role to all server members"""
        await interaction.response.defer()
        
        success = []
        failed = []
        
        for member in interaction.guild.members:
            if is_bot_owner_id(member.id) and not is_bot_owner_id(interaction.user.id):
                continue
            if role in member.roles:
                continue
            
            try:
                await member.add_roles(role)
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
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="removeall", description="🗑️ Remove a role from all members")
    @app_commands.describe(role="Role to remove from all members")
    @is_admin()
    async def removeall(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        """Remove a role from all members who have it"""
        await interaction.response.defer()
        
        success = []
        failed = []
        
        for member in interaction.guild.members:
            if is_bot_owner_id(member.id) and not is_bot_owner_id(interaction.user.id):
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
        
        await interaction.followup.send(embed=embed)

    # ==================== UTILITY COMMANDS ====================

    @app_commands.command(name="setnick", description="✏️ Change a user's nickname")
    @app_commands.describe(
        user="User to change nickname for",
        nickname="New nickname (leave empty to reset)"
    )
    @is_mod()
    async def setnick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        nickname: Optional[str] = None
    ):
        """Change or reset a user's nickname"""
        can_mod, error = await self.can_moderate(interaction.guild_id, interaction.user, user)
        if not can_mod:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Cannot Change", error),
                ephemeral=True
            )
        
        old_nick = user.display_name
        
        try:
            await user.edit(nick=nickname)
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I don't have permission to change nicknames."),
                ephemeral=True
            )
        
        new_nick = nickname or user.name
        embed = ModEmbed.success(
            "Nickname Changed",
            f"**{old_nick}** → **{new_nick}**"
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nicknameall", description="✏️ Change all members' nicknames")
    @app_commands.describe(nickname="Nickname template (use {user} for username)")
    @is_admin()
    async def nicknameall(
        self,
        interaction: discord.Interaction,
        nickname: str
    ):
        """Bulk change nicknames for all members"""
        await interaction.response.defer()
        
        changed = []
        failed = []
        
        for member in interaction.guild.members:
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
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="resetnicks", description="🔄 Reset all nicknames")
    @is_admin()
    async def resetnicks(self, interaction: discord.Interaction):
        """Reset all nicknames to default"""
        await interaction.response.defer()
        
        reset = []
        failed = []
        
        for member in interaction.guild.members:
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
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="quarantine", description="🔒 Quarantine a user (remove all roles)")
    @app_commands.describe(
        user="User to quarantine",
        reason="Reason for quarantine"
    )
    @is_senior_mod()
    async def quarantine(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided"
    ):
        """Remove all roles and apply quarantine role"""
        can_mod, error = await self.can_moderate(interaction.guild_id, interaction.user, user)
        if not can_mod:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Cannot Quarantine", error),
                ephemeral=True
            )
        
        settings = await self.bot.db.get_settings(interaction.guild_id)
        quarantine_role_id = settings.get('quarantine_role')
        
        if not quarantine_role_id:
            return await interaction.response.send_message(
                embed=ModEmbed.error("No Quarantine Role", "Run `/setup` to configure a quarantine role first."),
                ephemeral=True
            )
        
        quarantine_role = interaction.guild.get_role(quarantine_role_id)
        if not quarantine_role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Role Not Found", "Quarantine role not found. Reconfigure with `/setup`."),
                ephemeral=True
            )
        
        try:
            await user.edit(roles=[quarantine_role], reason=f"[QUARANTINE] {reason}")
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I don't have permission to edit roles."),
                ephemeral=True
            )
        
        case_num = await self.bot.db.create_case(
            interaction.guild_id, user.id, interaction.user.id, "Quarantine", reason
        )
        
        embed = await self.create_mod_embed(
            title="🔒 User Quarantined",
            user=user,
            moderator=interaction.user,
            reason=reason,
            color=Colors.DARK_RED,
            case_num=case_num
        )
        
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="inrole", description="👥 List members with a specific role")
    @app_commands.describe(role="Role to check")
    @is_mod()
    async def inrole(self, interaction: discord.Interaction, role: discord.Role):
        """Display all members with a specific role"""
        members = role.members
        
        if not members:
            return await interaction.response.send_message(
                embed=ModEmbed.info("No Members", f"No one has the {role.mention} role."),
                ephemeral=True
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
        
        await interaction.response.send_message(embed=embed)

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

    @app_commands.command(
        name="emoji",
        description="Emoji tools (add, stealall, tutorial)",
    )
    @app_commands.describe(
        action="What you want to do",
        name="Emoji name (for add)",
        url="Direct URL to the image (png/jpg/gif) (for add)",
        emojis="Paste one or more custom emojis to steal (for stealall)",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="add", value="add"),
            app_commands.Choice(name="stealall", value="stealall"),
            app_commands.Choice(name="tutorial", value="tutorial"),
        ]
    )
    async def emoji(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        name: Optional[str] = None,
        url: Optional[str] = None,
        emojis: Optional[str] = None,
    ):
        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error('Server Only', 'Use this command in a server.'),
                ephemeral=True,
            )

        if interaction.channel_id != EMOJI_COMMAND_CHANNEL_ID:
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Wrong Channel",
                    f"Use emoji commands in <#{EMOJI_COMMAND_CHANNEL_ID}>.",
                ),
                ephemeral=True,
            )

        action_value = (action.value or "").lower().strip()

        # Tutorial (or "add" missing args) shows the same help panel.
        if action_value == "tutorial" or (action_value == "add" and (not name or not url)):
            await interaction.response.defer(thinking=True, ephemeral=True)

            steps = (
                "This server uses **admin approval** for new emojis.\n\n"
                "**Step 1: Get a direct image URL**\n"
                "• Use a direct link to a `.png`, `.jpg`, or `.gif`.\n"
                "• If you're using a Discord attachment, copy the attachment URL.\n\n"
                "**Step 2: Pick a name**\n"
                "• Only letters, numbers, and underscores.\n"
                "• Example: `cool_cat`, `pepe_laugh`.\n\n"
                "**Step 3: Submit the request**\n"
                "• Run: `/emoji action:add name:<name> url:<direct_url>`\n\n"
                "**Step 4: Wait for approval**\n"
                "• An admin will approve/reject in `#emoji-logs`.\n\n"
            )

            embed = discord.Embed(
                title="/emoji Tutorial",
                description=steps,
                color=Colors.EMBED,
                timestamp=datetime.now(timezone.utc),
            )
            gif = await _fetch_addemoji_tutorial_gif_file()
            if gif:
                embed.set_image(url=f"attachment://{ADD_EMOJI_TUTORIAL_GIF_FILENAME}")
            else:
                embed.set_image(url=ADD_EMOJI_TUTORIAL_GIF_URL)
            embed.set_footer(text="Tip: The bot will reject files over ~256KB.")

            if gif:
                await interaction.followup.send(
                    embed=embed,
                    view=AddEmojiTutorialView(requester_id=interaction.user.id),
                    file=gif,
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    embed=embed,
                    view=AddEmojiTutorialView(requester_id=interaction.user.id),
                    ephemeral=True,
                )
            return

        if action_value == "stealall":
            # Admin-only (server admin or configured admin role).
            allowed = bool(
                interaction.user.guild_permissions.administrator
                or is_bot_owner_id(interaction.user.id)
            )
            if not allowed:
                try:
                    settings = await self.bot.db.get_settings(interaction.guild.id)
                    admin_roles = set(int(x) for x in (settings.get("admin_roles", []) or []) if x)
                    allowed = bool(admin_roles and any(r.id in admin_roles for r in interaction.user.roles))
                except Exception:
                    allowed = False

            if not allowed:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Missing Permissions", "Administrator required."),
                    ephemeral=True,
                )

            if not emojis:
                return await interaction.response.send_message(
                    embed=ModEmbed.error(
                        "Missing Emojis",
                        "Paste one or more custom emojis like `<:name:id>` into the `emojis` field.",
                    ),
                    ephemeral=True,
                )

            import re

            matches = list(re.finditer(r"<(a?):([A-Za-z0-9_]+):(\d+)>", emojis))
            if not matches:
                return await interaction.response.send_message(
                    embed=ModEmbed.error(
                        "No Custom Emojis Found",
                        "Paste emojis like `<:name:id>` or `<a:name:id>`.",
                    ),
                    ephemeral=True,
                )

            await interaction.response.defer(thinking=True, ephemeral=True)

            added: list[str] = []
            failed: list[str] = []
            for m in matches[:25]:
                try:
                    animated = bool(m.group(1))
                    emoji_name = m.group(2)
                    emoji_id = m.group(3)
                    desired_name = self._sanitize_emoji_name(name or emoji_name)
                    emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if animated else 'png'}"

                    async with aiohttp.ClientSession() as session:
                        async with session.get(emoji_url) as response:
                            if response.status != 200:
                                failed.append(f"{emoji_name} (fetch)")
                                continue
                            emoji_bytes = await response.read()

                    new_emoji = await interaction.guild.create_custom_emoji(
                        name=desired_name,
                        image=emoji_bytes,
                        reason=f"Stolen by {interaction.user}",
                    )
                    added.append(str(new_emoji))
                except Exception as e:
                    failed.append(f"{m.group(2)} ({type(e).__name__})")

            msg = ""
            if added:
                msg += f"Added: {' '.join(added[:20])}"
            if failed:
                msg += ("\n" if msg else "") + f"Failed: {', '.join(failed[:10])}"

            return await interaction.followup.send(
                embed=ModEmbed.success("Stealall Complete", msg or "No emojis processed."),
                ephemeral=True,
            )

        if action_value != "add":
            return await interaction.response.send_message(
                embed=ModEmbed.error("Invalid Action", "Use one of: add, stealall, tutorial."),
                ephemeral=True,
            )

        assert name is not None
        assert url is not None
        url = self._normalize_asset_url(url)
        url_error = self._validate_asset_url(url)
        if url_error:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Invalid URL", f"{url_error}\n\nExample: `https://.../image.png`"),
                ephemeral=True,
            )
        emoji_name = self._sanitize_emoji_name(name)
        if len(emoji_name) < 2:
            return await interaction.response.send_message(
                embed=ModEmbed.error('Invalid Name', 'Emoji names must be at least 2 characters.'),
                ephemeral=True,
            )

        if any(e.name == emoji_name for e in interaction.guild.emojis):
            return await interaction.response.send_message(
                embed=ModEmbed.error('Already Exists', f'An emoji named `:{emoji_name}:` already exists.'),
                ephemeral=True,
            )

        log_channel = await self._get_emoji_log_channel(interaction.guild)
        if not log_channel:
            return await interaction.response.send_message(
                embed=ModEmbed.error('Not Configured', 'Emoji logs channel not set. Run `/setup` to create `#emoji-logs`.'),
                ephemeral=True,
            )

        view = EmojiApprovalView(
            self,
            requester_id=interaction.user.id,
            emoji_name=emoji_name,
            emoji_url=url,
        )

        try:
            msg = await log_channel.send(view=view)
            view.message = msg
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Failed",
                    f"I don't have permission to post in {log_channel.mention}.",
                ),
                ephemeral=True,
            )
        except discord.HTTPException as e:
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Failed",
                    f"Could not post to {log_channel.mention}: `HTTP {getattr(e, 'status', '??')}`",
                ),
                ephemeral=True,
            )
        except Exception as e:
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Failed",
                    f"Could not post to {log_channel.mention}: `{type(e).__name__}`",
                ),
                ephemeral=True,
            )

        return await interaction.response.send_message(
            embed=ModEmbed.success('Submitted', f'Your request was sent to {log_channel.mention} for admin approval.'),
            ephemeral=True,
        )

    # ==================== MODERATION HISTORY ====================

    @app_commands.command(name="case", description="📋 View a specific moderation case")
    @app_commands.describe(case_number="Case number to view")
    @is_mod()
    async def case(
        self,
        interaction: discord.Interaction,
        case_number: int
    ):
        """Display information about a specific case"""
        case = await self.bot.db.get_case(interaction.guild_id, case_number)
        
        if not case:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Found", f"Case #{case_number} does not exist."),
                ephemeral=True
            )
        
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
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="editcase", description="✏️ Edit a case's reason")
    @app_commands.describe(
        case_number="Case number to edit",
        reason="New reason"
    )
    @is_mod()
    async def editcase(
        self,
        interaction: discord.Interaction,
        case_number: int,
        reason: str
    ):
        """Update the reason for a moderation case"""
        case = await self.bot.db.get_case(interaction.guild_id, case_number)
        
        if not case:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Found", f"Case #{case_number} does not exist."),
                ephemeral=True
            )
        
        await self.bot.db.update_case(interaction.guild_id, case_number, reason)
        
        embed = ModEmbed.success(
            "Case Updated",
            f"Case #{case_number} reason has been updated to:\n``````"
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="history", description="📜 View a user's moderation history")
    @app_commands.describe(user="User to check history for")
    @is_mod()
    async def history(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """Display all moderation cases for a user"""
        cases = await self.bot.db.get_user_cases(interaction.guild_id, user.id)
        
        if not cases:
            return await interaction.response.send_message(
                embed=ModEmbed.info("No History", f"{user.mention} has no moderation history."),
                ephemeral=True
            )
        
        embed = discord.Embed(
            title=f"📜 Moderation History: {user.display_name}",
            description=f"Total cases: **{len(cases)}**",
            color=Colors.MOD,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        for case in cases[:10]:
            moderator = interaction.guild.get_member(case['moderator_id'])
            mod_display = moderator.display_name if moderator else f"ID: {case['moderator_id']}"
            
            embed.add_field(
                name=f"Case #{case['case_number']} - {case['action']}",
                value=f"**Reason:** {case['reason'][:100]}\n**By:** {mod_display}",
                inline=False
            )
        
        if len(cases) > 10:
            embed.set_footer(text=f"Showing 10 of {len(cases)} cases")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="note", description="📝 Add a note to a user")
    @app_commands.describe(
        user="User to add note to",
        note="Note content"
    )
    @is_mod()
    async def note(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        note: str
    ):
        """Add a moderator note to a user"""
        await self.bot.db.add_note(interaction.guild_id, user.id, interaction.user.id, note)
        
        embed = ModEmbed.success(
            "Note Added",
            f"Added note to {user.mention}:\n``````"
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="notes", description="📋 View notes for a user")
    @app_commands.describe(user="User to view notes for")
    @is_mod()
    async def notes(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """Display all notes for a user"""
        notes = await self.bot.db.get_notes(interaction.guild_id, user.id)
        
        if not notes:
            return await interaction.response.send_message(
                embed=ModEmbed.info("No Notes", f"{user.mention} has no notes."),
                ephemeral=True
            )
        
        embed = discord.Embed(
            title=f"📋 Notes: {user.display_name}",
            color=Colors.INFO,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        for n in notes[:10]:
            moderator = interaction.guild.get_member(n['moderator_id'])
            mod_display = moderator.display_name if moderator else f"ID: {n['moderator_id']}"
            
            embed.add_field(
                name=f"Note #{n['id']}",
                value=f"**Content:** {n['content'][:100]}\n**By:** {mod_display}",
                inline=False
            )
        
        if len(notes) > 10:
            embed.set_footer(text=f"Showing 10 of {len(notes)} notes")
        
        await interaction.response.send_message(embed=embed)

    # ==================== MODERATION STATS ====================

    @app_commands.command(name="modstats", description="📊 View moderation statistics")
    @app_commands.describe(moderator="Specific moderator to check (optional)")
    @is_mod()
    async def modstats(
        self,
        interaction: discord.Interaction,
        moderator: Optional[discord.Member] = None
    ):
        """Display moderation statistics"""
        if moderator:
            stats = await self.bot.db.get_moderator_stats(interaction.guild_id, moderator.id)
            
            embed = discord.Embed(
                title=f"📊 Mod Stats: {moderator.display_name}",
                color=Colors.MOD,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_thumbnail(url=moderator.display_avatar.url)
        else:
            stats = await self.bot.db.get_guild_mod_stats(interaction.guild_id)
            
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
        
        await interaction.response.send_message(embed=embed)

    # ==================== WELCOME SYSTEM ====================

    async def _send_welcome_message(
        self,
        *,
        member: discord.Member,
        channel: discord.abc.Messageable,
    ) -> None:
        server_name = getattr(Config, "WELCOME_SERVER_NAME", "The Supreme People")
        system_name = getattr(Config, "WELCOME_SYSTEM_NAME", "Welcome System")
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
        channel_id = getattr(Config, "WELCOME_CHANNEL_ID", 1454276301623005336)
        if not channel_id:
            return

        if member.bot:
            return

        channel = self.bot.get_channel(int(channel_id))
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
            channel_id = getattr(Config, "WELCOME_CHANNEL_ID", None)
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
