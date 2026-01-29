"""
Advanced Logging System
Comprehensive event logging for messages, members, voice, moderation actions, and more
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional, Literal
import logging

from utils.embeds import ModEmbed, Colors
from utils.checks import is_admin
from utils.cache import ChannelCache
from config import Config

logger = logging.getLogger(__name__)


class Logging(commands.Cog):
    """Event logging system with configurable channels"""
    
    # Command group for logging configuration
    log_group = app_commands.Group(name="log", description="📝 Logging configuration")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._channel_cache = ChannelCache(ttl=300)  # 5 minute TTL
        self._audit_search_window_seconds = 15

    async def get_log_channel(
        self, 
        guild: discord.Guild, 
        log_type: str
    ) -> Optional[discord.TextChannel]:
        """
        Get the appropriate log channel for a log type
        Uses advanced caching with TTL to reduce DB queries
        """
        # Check cache first
        channel_id = await self._channel_cache.get(guild.id, log_type)
        
        if channel_id is None:
            # Fetch from DB
            try:
                settings = await self.bot.db.get_settings(guild.id)
                channel_id = settings.get(f'{log_type}_log_channel')
                
                # Cache the result (even if None)
                await self._channel_cache.set(guild.id, log_type, channel_id)
            except Exception as e:
                logger.error(f"Failed to get log channel for {guild.name}: {e}")
                return None
        
        # Validate channel exists and is accessible
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel is None:
                # Channel was deleted, remove from cache and DB
                await self._remove_invalid_channel(guild.id, log_type)
                return None
            return channel
        
        return None
    
    async def _remove_invalid_channel(self, guild_id: int, log_type: str) -> None:
        """Remove invalid channel from cache and database"""
        try:
            # Invalidate cache
            await self._channel_cache.invalidate(guild_id, log_type)
            
            # Remove from database
            settings = await self.bot.db.get_settings(guild_id)
            if f'{log_type}_log_channel' in settings:
                del settings[f'{log_type}_log_channel']
                await self.bot.db.update_settings(guild_id, settings)
            
            logger.warning(f"Removed invalid {log_type} log channel for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error removing invalid channel: {e}")

    async def safe_send_log(
        self, 
        channel: Optional[discord.TextChannel], 
        embed: discord.Embed
    ) -> bool:
        """
        Safely send a log embed with enhanced error handling
        Returns: bool indicating success
        """
        if not channel:
            return False
        
        try:
            # 1. THUMBNAIL: Priority = Existing -> Author Icon -> Guild Icon
            try:
                if not getattr(getattr(embed, "thumbnail", None), "url", None):
                    author_icon = getattr(getattr(embed, "author", None), "icon_url", None)
                    if author_icon:
                        embed.set_thumbnail(url=author_icon)
                    elif channel.guild.icon:
                        embed.set_thumbnail(url=channel.guild.icon.url)
            except Exception:
                pass

            # 2. BANNER: Always set the main image to the Server Banner (Guild > Config)
            try:
                banner_url = None
                if channel.guild.banner:
                    banner_url = channel.guild.banner.url
                
                if not banner_url:
                    banner_url = (getattr(Config, "SERVER_BANNER_URL", "") or "").strip() or None
                
                if banner_url:
                    embed.set_image(url=banner_url)
            except Exception:
                pass

            await channel.send(embed=embed)
            return True
        except discord.Forbidden:
            logger.warning(f"Missing permissions to log in {channel.guild.name} #{channel.name}")
            # Invalidate cache for this channel
            await self._channel_cache.invalidate(channel.guild.id, "unknown")
            return False
        except discord.NotFound:
            logger.warning(f"Log channel not found: {channel.guild.name} #{channel.name}")
            # Channel was deleted
            await self._channel_cache.invalidate(channel.guild.id, "unknown")
            return False
        except discord.HTTPException as e:
            logger.error(f"Failed to send log in {channel.guild.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending log: {e}")
            return False

    def _shorten(self, text: Optional[str], limit: int) -> str:
        if not text:
            return "*None*"
        text = str(text).strip()
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 1)].rstrip() + "…"

    def _yn(self, value: Optional[bool]) -> str:
        if value is None:
            return "*N/A*"
        return "Yes" if value else "No"

    async def _find_recent_audit_entry(
        self,
        guild: discord.Guild,
        *,
        action: discord.AuditLogAction,
        target_id: int,
    ) -> Optional[discord.AuditLogEntry]:
        now = datetime.now(timezone.utc)
        try:
            async for entry in guild.audit_logs(limit=6, action=action):
                entry_target_id = getattr(getattr(entry, "target", None), "id", None)
                if entry_target_id != target_id:
                    continue
                age = (now - entry.created_at).total_seconds()
                if age <= self._audit_search_window_seconds:
                    return entry
        except discord.Forbidden:
            return None
        except Exception as e:
            logger.error(f"Failed to query audit logs in {guild.name}: {e}")
            return None
        return None

    def _add_channel_details_fields(self, embed: discord.Embed, channel: discord.abc.GuildChannel) -> None:
        category = getattr(channel, "category", None)
        category_value = category.mention if category else "*None*"
        embed.add_field(name="Category", value=category_value, inline=True)
        embed.add_field(name="Position", value=str(getattr(channel, "position", "*N/A*")), inline=True)
        embed.add_field(
            name="Overwrites",
            value=str(len(getattr(channel, "overwrites", {}) or {})),
            inline=True,
        )

        nsfw = getattr(channel, "nsfw", None)
        if nsfw is not None:
            embed.add_field(name="NSFW", value=self._yn(nsfw), inline=True)
        else:
            embed.add_field(name="NSFW", value="*N/A*", inline=True)

        slowmode_delay = getattr(channel, "slowmode_delay", None)
        if slowmode_delay is not None:
            embed.add_field(name="Slowmode", value=f"{slowmode_delay}s", inline=True)
        else:
            embed.add_field(name="Slowmode", value="*N/A*", inline=True)

        permissions_synced = getattr(channel, "permissions_synced", None)
        if permissions_synced is not None:
            embed.add_field(name="Synced", value=self._yn(permissions_synced), inline=True)
        else:
            embed.add_field(name="Synced", value="*N/A*", inline=True)

        topic = getattr(channel, "topic", None)
        if topic is not None:
            embed.add_field(name="Topic", value=self._shorten(topic, 200), inline=False)

        bitrate = getattr(channel, "bitrate", None)
        user_limit = getattr(channel, "user_limit", None)
        if bitrate is not None or user_limit is not None:
            bitrate_text = f"{int(bitrate/1000)}kbps" if bitrate else "*N/A*"
            limit_text = str(user_limit) if user_limit else "∞"
            embed.add_field(name="Voice", value=f"Bitrate: {bitrate_text} | Limit: {limit_text}", inline=False)

    def _add_role_details_fields(
        self,
        embed: discord.Embed,
        role: discord.Role,
        *,
        include_members: bool = True,
    ) -> None:
        color_value = role.color.value
        color_text = f"#{color_value:06x}" if color_value else "Default"
        embed.add_field(name="Color", value=color_text, inline=True)
        embed.add_field(name="Position", value=str(role.position), inline=True)
        if include_members:
            embed.add_field(name="Members", value=str(len(role.members)), inline=True)
        embed.add_field(name="Hoist", value=self._yn(role.hoist), inline=True)
        embed.add_field(name="Mentionable", value=self._yn(role.mentionable), inline=True)
        embed.add_field(name="Managed", value=self._yn(role.managed), inline=True)

        perms = role.permissions
        key_perms = [
            ("Administrator", perms.administrator),
            ("Manage Server", perms.manage_guild),
            ("Manage Roles", perms.manage_roles),
            ("Manage Channels", perms.manage_channels),
            ("Ban Members", perms.ban_members),
            ("Kick Members", perms.kick_members),
        ]
        perms_text = " | ".join([f"{name}: {self._yn(val)}" for name, val in key_perms])
        embed.add_field(name="Key Perms", value=perms_text, inline=False)

    # ==================== MESSAGE LOGGING ====================
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Log deleted messages"""
        # Ignore DMs and bot messages
        if not message.guild or message.author.bot:
            return
        
        # Ignore empty messages
        if not message.content and not message.attachments and not message.embeds:
            return
        
        channel = await self.get_log_channel(message.guild, 'message')
        if not channel:
            return
        
        embed = discord.Embed(
            title="Message Deleted",
            color=0xFF0000,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Set author to match the image style
        embed.set_author(name=f"{message.author.name}", icon_url=message.author.display_avatar.url)
        
        # Top 3 fields inline
        embed.add_field(
            name="Author",
            value=f"{message.author.mention} ({message.author.name})",
            inline=True
        )
        embed.add_field(
            name="Channel",
            value=message.channel.mention,
            inline=True
        )
        embed.add_field(
            name="Message ID",
            value=f"{message.id}",
            inline=True
        )
        
        # Content (truncated if too long)
        content_value = message.content
        if not content_value and not message.embeds and not message.attachments:
            content_value = "*No content*"
        elif not content_value:
            # If no text content but has attachments/embeds, describe them in content or leave empty if handled below
            content_value = ""

        if len(content_value) > 1024:
            content_value = content_value[:1021] + "..."
            
        if content_value:
            embed.add_field(name="Content", value=content_value, inline=False)
        
        # Attachments
        if message.attachments:
            attachments_list = [
                f"[{a.filename}]({a.url})" if not a.is_spoiler() 
                else f"||{a.filename}||" 
                for a in message.attachments[:10]
            ]
            attachments_text = "\n".join(attachments_list)
            if len(message.attachments) > 10:
                attachments_text += f"\n*...and {len(message.attachments) - 10} more*"
            embed.add_field(name="Attachments", value=attachments_text, inline=False)
        
        # Embeds
        if message.embeds:
            embed.add_field(
                name="Embeds",
                value=f"{len(message.embeds)} embed(s)",
                inline=False
            )
        
        # Footer
        embed.set_footer(text=f"Author ID: {message.author.id}")
        
        await self.safe_send_log(channel, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Log edited messages"""
        # Ignore DMs, bots, and non-content changes
        if not before.guild or before.author.bot:
            return
        if before.content == after.content:
            return
        
        # Ignore if both empty
        if not before.content and not after.content:
            return
        
        channel = await self.get_log_channel(before.guild, 'message')
        if not channel:
            return
        
        embed = discord.Embed(
            title="Message Edited",
            color=Colors.WARNING,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_author(name=f"{before.author.name}", icon_url=before.author.display_avatar.url)
        
        embed.add_field(
            name="Author",
            value=f"{before.author.mention} ({before.author.name})",
            inline=True
        )
        embed.add_field(
            name="Channel",
            value=before.channel.mention,
            inline=True
        )
        embed.add_field(
            name="Jump",
            value=f"[Go to Message]({after.jump_url})",
            inline=True
        )
        
        # Before content
        before_content = before.content[:500] if before.content else "*Empty*"
        if len(before.content) > 500:
            before_content += "..."
        embed.add_field(name="Before", value=before_content, inline=False)
        
        # After content
        after_content = after.content[:500] if after.content else "*Empty*"
        if len(after.content) > 500:
            after_content += "..."
        embed.add_field(name="After", value=after_content, inline=False)
        
        embed.set_footer(text=f"Message ID: {before.id}")
        
        await self.safe_send_log(channel, embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        """Log bulk message deletions"""
        if not messages:
            return
        
        # Get guild from first message
        guild = messages[0].guild
        if not guild:
            return
        
        channel = await self.get_log_channel(guild, 'message')
        if not channel:
            return
        
        embed = discord.Embed(
            title="Bulk Message Delete",
            description=f"**{len(messages)}** messages were deleted in {messages[0].channel.mention}",
            color=Colors.ERROR,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add some stats
        authors = set(m.author for m in messages if not m.author.bot)
        bot_count = sum(1 for m in messages if m.author.bot)
        
        embed.add_field(name="Human Messages", value=str(len(messages) - bot_count), inline=True)
        embed.add_field(name="Bot Messages", value=str(bot_count), inline=True)
        embed.add_field(name="Unique Authors", value=str(len(authors)), inline=True)
        
        await self.safe_send_log(channel, embed)

    # ==================== MEMBER LOGGING ====================
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Log member joins"""
        channel = await self.get_log_channel(member.guild, 'audit')
        if not channel:
            return
        
        # Calculate account age
        account_age = (datetime.now(timezone.utc) - member.created_at).days
        
        embed = discord.Embed(
            title="Member Joined",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
        
        embed.add_field(
            name="User",
            value=f"{member.mention} ({member.name})",
            inline=True
        )
        embed.add_field(
            name="Account Age",
            value=f"{account_age} days",
            inline=True
        )
        embed.add_field(
            name="Created",
            value=f"<t:{int(member.created_at.timestamp())}:R>",
            inline=True
        )
        
        embed.add_field(
            name="Member Count",
            value=f"#{member.guild.member_count}",
            inline=False
        )
        
        embed.set_footer(text=f"User ID: {member.id}")
        
        # Warning for new accounts
        if account_age < 7:
            embed.add_field(
                name="⚠️ Warning",
                value=f"Account created **{account_age}** day(s) ago",
                inline=False
            )
            embed.color = Colors.WARNING
        
        # Warning for suspicious usernames
        suspicious_chars = ['discord', 'nitro', 'mod', 'admin', 'support']
        username_lower = member.name.lower()
        if any(char in username_lower for char in suspicious_chars):
            embed.add_field(
                name="⚠️ Suspicious Username",
                value="Username contains common scam keywords",
                inline=False
            )
            embed.color = Colors.WARNING
        
        await self.safe_send_log(channel, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Log member leaves/kicks"""
        channel = await self.get_log_channel(member.guild, 'audit')
        if not channel:
            return
        
        embed = discord.Embed(
            title="Member Left",
            color=Colors.ERROR,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
        
        embed.add_field(
            name="User",
            value=f"{member.mention} ({member.name})",
            inline=True
        )
        
        # Join date
        if member.joined_at:
            days_in_server = (datetime.now(timezone.utc) - member.joined_at).days
            embed.add_field(
                name="Time in Server",
                value=f"{days_in_server} days",
                inline=True
            )
        else:
             embed.add_field(name="Time in Server", value="Unknown", inline=True)
             
        embed.add_field(
            name="Members",
            value=f"#{member.guild.member_count}",
            inline=True
        )
        
        # Roles
        roles = [r.mention for r in member.roles[1:] if r.name != "@everyone"]
        if roles:
            roles_text = ", ".join(roles[:10])
            if len(roles) > 10:
                roles_text += f" *+{len(roles) - 10} more*"
            embed.add_field(name="Roles", value=roles_text, inline=False)
        
        embed.set_footer(text=f"User ID: {member.id}")
        
        # Check audit log for kick
        try:
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id:
                    # Check if kick happened within last 5 seconds
                    if (datetime.now(timezone.utc) - entry.created_at).seconds < 5:
                        embed.title = "👢 Member Kicked"
                        embed.add_field(
                            name="Kicked By",
                            value=entry.user.mention,
                            inline=True
                        )
                        if entry.reason:
                            embed.add_field(
                                name="Reason",
                                value=entry.reason,
                                inline=False
                            )
                        break
        except discord.Forbidden:
            pass
        except Exception as e:
            logger.error(f"Failed to check audit log for kick: {e}")
        
        await self.safe_send_log(channel, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Log member updates (nickname, roles, etc.)"""
        channel = await self.get_log_channel(before.guild, 'audit')
        if not channel:
            return
        
        # ===== NICKNAME CHANGE =====
        if before.nick != after.nick:
            embed = discord.Embed(
                title="Nickname Changed",
                color=Colors.INFO,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.set_author(name=f"{after.name}", icon_url=after.display_avatar.url)
            
            embed.add_field(
                name="User",
                value=f"{after.mention} ({after.name})",
                inline=True
            )
            embed.add_field(
                name="Before",
                value=before.nick or "*None*",
                inline=True
            )
            embed.add_field(
                name="After",
                value=after.nick or "*None*",
                inline=True
            )
            
            entry = await self._find_recent_audit_entry(
                before.guild,
                action=discord.AuditLogAction.member_update,
                target_id=after.id,
            )
            moderator = getattr(entry, "user", None)
            reason = getattr(entry, "reason", None)
            embed.add_field(
                name="Moderator",
                value=moderator.mention if moderator else "*Unknown*",
                inline=True
            )
            embed.add_field(name="Reason", value=self._shorten(reason, 250), inline=False)

            embed.set_footer(text=f"User ID: {after.id}")
            
            await self.safe_send_log(channel, embed)
        
        # ===== ROLE CHANGES =====
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            
            if added or removed:
                embed = discord.Embed(
                    title="Roles Updated",
                    color=Colors.INFO,
                    timestamp=datetime.now(timezone.utc)
                )
                
                embed.set_author(name=f"{after.name}", icon_url=after.display_avatar.url)
                
                embed.add_field(
                    name="User",
                    value=f"{after.mention} ({after.name})",
                    inline=True
                )
                
                added_text = "*None*"
                if added:
                    added_text = ", ".join([r.mention for r in added[:10]])
                    if len(added) > 10:
                        added_text += f" *+{len(added) - 10} more*"
                embed.add_field(name="✅ Added", value=added_text, inline=False)

                removed_text = "*None*"
                if removed:
                    removed_text = ", ".join([r.mention for r in removed[:10]])
                    if len(removed) > 10:
                        removed_text += f" *+{len(removed) - 10} more*"
                embed.add_field(name="❌ Removed", value=removed_text, inline=False)

                entry = await self._find_recent_audit_entry(
                    before.guild,
                    action=discord.AuditLogAction.member_role_update,
                    target_id=after.id,
                )
                moderator = getattr(entry, "user", None)
                reason = getattr(entry, "reason", None)
                embed.add_field(
                    name="Moderator",
                    value=moderator.mention if moderator else "*Unknown*",
                    inline=True
                )
                embed.add_field(name="Reason", value=self._shorten(reason, 250), inline=False)

                embed.set_footer(text=f"User ID: {after.id}")
                
                await self.safe_send_log(channel, embed)
        
        # ===== TIMEOUT CHANGES =====
        if before.timed_out_until != after.timed_out_until:
            if after.timed_out_until and after.timed_out_until > datetime.now(timezone.utc):
                # User was timed out
                embed = discord.Embed(
                    title="Member Timed Out",
                    color=Colors.WARNING,
                    timestamp=datetime.now(timezone.utc)
                )
                
                embed.set_author(name=f"{after.name}", icon_url=after.display_avatar.url)
                
                embed.add_field(
                    name="User",
                    value=f"{after.mention} ({after.name})",
                    inline=True
                )
                embed.add_field(
                    name="Until",
                    value=f"<t:{int(after.timed_out_until.timestamp())}:F>",
                    inline=True
                )
                embed.add_field(
                    name="Duration",
                    value=f"<t:{int(after.timed_out_until.timestamp())}:R>",
                    inline=True
                )
                
                entry = await self._find_recent_audit_entry(
                    before.guild,
                    action=discord.AuditLogAction.member_update,
                    target_id=after.id,
                )
                moderator = getattr(entry, "user", None)
                reason = getattr(entry, "reason", None)

                embed.add_field(
                    name="Moderator",
                    value=moderator.mention if moderator else "*Unknown*",
                    inline=True
                )
                embed.add_field(name="Reason", value=self._shorten(reason, 250), inline=False)

                embed.set_footer(text=f"User ID: {after.id}")
                
                await self.safe_send_log(channel, embed)
            elif before.timed_out_until and not after.timed_out_until:
                # Timeout removed
                embed = discord.Embed(
                    title="Timeout Removed",
                    color=Colors.SUCCESS,
                    timestamp=datetime.now(timezone.utc)
                )
                
                embed.set_author(name=f"{after.name}", icon_url=after.display_avatar.url)
                
                embed.add_field(
                    name="User",
                    value=f"{after.mention} ({after.name})",
                    inline=True
                )
                
                entry = await self._find_recent_audit_entry(
                    before.guild,
                    action=discord.AuditLogAction.member_update,
                    target_id=after.id,
                )
                moderator = getattr(entry, "user", None)
                reason = getattr(entry, "reason", None)

                prev_ts = int(before.timed_out_until.timestamp())
                embed.add_field(name="Previous Until", value=f"<t:{prev_ts}:F>", inline=True)
                embed.add_field(
                    name="Moderator",
                    value=moderator.mention if moderator else "*Unknown*",
                    inline=True
                )
                embed.add_field(name="Reason", value=self._shorten(reason, 250), inline=False)

                embed.set_footer(text=f"User ID: {after.id}")
                
                await self.safe_send_log(channel, embed)

    # ==================== VOICE LOGGING ====================
    
    @commands.Cog.listener()
    async def on_voice_state_update(
        self, 
        member: discord.Member, 
        before: discord.VoiceState, 
        after: discord.VoiceState
    ):
        """Log voice channel activity"""
        channel = await self.get_log_channel(member.guild, 'voice')
        if not channel:
            return
        
        embed = None
        
        # ===== JOINED VOICE =====
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(
                title="Joined Voice Channel",
                color=Colors.SUCCESS,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
            
            embed.add_field(name="User", value=f"{member.mention} ({member.name})", inline=True)
            embed.add_field(name="Channel", value=after.channel.mention, inline=True)
            embed.add_field(
                name="Members",
                value=f"{len(after.channel.members)}",
                inline=True
            )
        
        # ===== LEFT VOICE =====
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(
                title="Left Voice Channel",
                color=Colors.ERROR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
            
            embed.add_field(name="User", value=f"{member.mention} ({member.name})", inline=True)
            embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        
        # ===== SWITCHED VOICE =====
        elif before.channel != after.channel and before.channel and after.channel:
            embed = discord.Embed(
                title="Switched Voice Channel",
                color=Colors.INFO,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
            
            embed.add_field(name="User", value=f"{member.mention} ({member.name})", inline=True)
            embed.add_field(name="From", value=before.channel.mention, inline=True)
            embed.add_field(name="To", value=after.channel.mention, inline=True)
        
        # ===== VOICE MUTE/UNMUTE =====
        elif before.self_mute != after.self_mute:
            action = "Muted" if after.self_mute else "Unmuted"
            embed = discord.Embed(
                title=f"Self {action}",
                color=Colors.INFO if after.self_mute else Colors.SUCCESS,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
            
            embed.add_field(name="User", value=f"{member.mention} ({member.name})", inline=True)
            if after.channel:
                embed.add_field(name="Channel", value=after.channel.mention, inline=True)
        
        # ===== VOICE DEAFEN/UNDEAFEN =====
        elif before.self_deaf != after.self_deaf:
            action = "Deafened" if after.self_deaf else "Undeafened"
            embed = discord.Embed(
                title=f"Self {action}",
                color=Colors.INFO if after.self_deaf else Colors.SUCCESS,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
            
            embed.add_field(name="User", value=f"{member.mention} ({member.name})", inline=True)
            if after.channel:
                embed.add_field(name="Channel", value=after.channel.mention, inline=True)

        # ===== STREAMING START/STOP =====
        elif before.self_stream != after.self_stream:
            action = "Started Streaming" if after.self_stream else "Stopped Streaming"
            embed = discord.Embed(
                title=f"{action}",
                color=Colors.INFO if after.self_stream else Colors.ERROR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
            
            embed.add_field(name="User", value=f"{member.mention} ({member.name})", inline=True)
            if after.channel:
                embed.add_field(name="Channel", value=after.channel.mention, inline=True)

        # ===== VIDEO START/STOP =====
        elif before.self_video != after.self_video:
            action = "Started Video" if after.self_video else "Stopped Video"
            embed = discord.Embed(
                title=f"{action}",
                color=Colors.INFO if after.self_video else Colors.ERROR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
            
            embed.add_field(name="User", value=f"{member.mention} ({member.name})", inline=True)
            if after.channel:
                embed.add_field(name="Channel", value=after.channel.mention, inline=True)

        if embed:
            embed.set_footer(text=f"User ID: {member.id}")
            await self.safe_send_log(channel, embed)

    # ==================== BAN/UNBAN LOGGING ====================
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Log bans"""
        channel = await self.get_log_channel(guild, 'audit')
        if not channel:
            return
        
        embed = discord.Embed(
            title="🔨 Member Banned",
            color=Colors.DARK_RED,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="User",
            value=f"{user.mention} (`{user.id}`)",
            inline=True
        )
        if getattr(user, "created_at", None):
            embed.add_field(
                name="Account Created",
                value=f"<t:{int(user.created_at.timestamp())}:R>",
                inline=True
            )
        embed.add_field(name="Bot", value=self._yn(getattr(user, "bot", False)), inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        
        # Try to get ban reason from audit log
        moderator_text = "*Unknown*"
        ban_reason = None
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    moderator_text = entry.user.mention
                    ban_reason = entry.reason
                    break
        except discord.Forbidden:
            logger.warning(f"Missing audit log permissions in {guild.name}")
        except Exception as e:
            logger.error(f"Failed to check audit log for ban: {e}")

        embed.add_field(name="Moderator", value=moderator_text, inline=True)
        embed.add_field(name="Reason", value=self._shorten(ban_reason, 250), inline=False)
        
        await self.safe_send_log(channel, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Log unbans"""
        channel = await self.get_log_channel(guild, 'audit')
        if not channel:
            return
        
        embed = discord.Embed(
            title="🔓 Member Unbanned",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="User",
            value=f"{user.mention} (`{user.id}`)",
            inline=True
        )
        if getattr(user, "created_at", None):
            embed.add_field(
                name="Account Created",
                value=f"<t:{int(user.created_at.timestamp())}:R>",
                inline=True
            )
        embed.add_field(name="Bot", value=self._yn(getattr(user, "bot", False)), inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        
        # Try to get unban info from audit log
        moderator_text = "*Unknown*"
        unban_reason = None
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
                if entry.target.id == user.id:
                    moderator_text = entry.user.mention
                    unban_reason = entry.reason
                    break
        except discord.Forbidden:
            pass
        except Exception as e:
            logger.error(f"Failed to check audit log for unban: {e}")

        embed.add_field(name="Moderator", value=moderator_text, inline=True)
        embed.add_field(name="Reason", value=self._shorten(unban_reason, 250), inline=False)
        
        await self.safe_send_log(channel, embed)

    # ==================== SERVER EVENTS ====================
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Log channel creation"""
        log_channel = await self.get_log_channel(channel.guild, 'audit')
        if not log_channel:
            return
        
        entry = await self._find_recent_audit_entry(
            channel.guild,
            action=discord.AuditLogAction.channel_create,
            target_id=channel.id,
        )
        actor = getattr(entry, "user", None)
        reason = getattr(entry, "reason", None)

        embed = discord.Embed(
            title="➕ Channel Created",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
        embed.add_field(name="ID", value=f"`{channel.id}`", inline=True)

        created_at = getattr(channel, "created_at", None)
        embed.add_field(
            name="Created",
            value=f"<t:{int(created_at.timestamp())}:R>" if created_at else "*N/A*",
            inline=True,
        )
        embed.add_field(name="By", value=actor.mention if actor else "*Unknown*", inline=True)
        embed.add_field(name="Reason", value=self._shorten(reason, 250), inline=False)
        self._add_channel_details_fields(embed, channel)

        if channel.guild.icon:
            embed.set_thumbnail(url=channel.guild.icon.url)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        
        await self.safe_send_log(log_channel, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Log channel deletion"""
        log_channel = await self.get_log_channel(channel.guild, 'audit')
        if not log_channel:
            return
        
        entry = await self._find_recent_audit_entry(
            channel.guild,
            action=discord.AuditLogAction.channel_delete,
            target_id=channel.id,
        )
        actor = getattr(entry, "user", None)
        reason = getattr(entry, "reason", None)

        embed = discord.Embed(
            title="➖ Channel Deleted",
            color=Colors.ERROR,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Channel", value=f"#{channel.name}", inline=True)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
        embed.add_field(name="ID", value=f"`{channel.id}`", inline=True)

        created_at = getattr(channel, "created_at", None)
        embed.add_field(
            name="Created",
            value=f"<t:{int(created_at.timestamp())}:R>" if created_at else "*N/A*",
            inline=True,
        )
        embed.add_field(name="By", value=actor.mention if actor else "*Unknown*", inline=True)
        embed.add_field(name="Reason", value=self._shorten(reason, 250), inline=False)
        self._add_channel_details_fields(embed, channel)

        if channel.guild.icon:
            embed.set_thumbnail(url=channel.guild.icon.url)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        
        await self.safe_send_log(log_channel, embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Log role creation"""
        channel = await self.get_log_channel(role.guild, 'audit')
        if not channel:
            return
        
        entry = await self._find_recent_audit_entry(
            role.guild,
            action=discord.AuditLogAction.role_create,
            target_id=role.id,
        )
        actor = getattr(entry, "user", None)
        reason = getattr(entry, "reason", None)

        embed = discord.Embed(
            title="➕ Role Created",
            color=role.color if role.color.value != 0 else Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Role", value=role.mention, inline=True)
        embed.add_field(name="ID", value=f"`{role.id}`", inline=True)

        created_at = getattr(role, "created_at", None)
        embed.add_field(
            name="Created",
            value=f"<t:{int(created_at.timestamp())}:R>" if created_at else "*N/A*",
            inline=True,
        )
        embed.add_field(name="By", value=actor.mention if actor else "*Unknown*", inline=True)
        embed.add_field(name="Reason", value=self._shorten(reason, 250), inline=False)
        self._add_role_details_fields(embed, role)

        if role.guild.icon:
            embed.set_thumbnail(url=role.guild.icon.url)
        embed.set_footer(text=f"Role ID: {role.id}")
        
        await self.safe_send_log(channel, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Log role deletion"""
        channel = await self.get_log_channel(role.guild, 'audit')
        if not channel:
            return
        
        entry = await self._find_recent_audit_entry(
            role.guild,
            action=discord.AuditLogAction.role_delete,
            target_id=role.id,
        )
        actor = getattr(entry, "user", None)
        reason = getattr(entry, "reason", None)

        embed = discord.Embed(
            title="➖ Role Deleted",
            color=Colors.ERROR,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Role", value=f"@{role.name}", inline=True)
        embed.add_field(name="ID", value=f"`{role.id}`", inline=True)
        embed.add_field(name="Members", value=str(len(role.members)), inline=True)

        created_at = getattr(role, "created_at", None)
        embed.add_field(
            name="Created",
            value=f"<t:{int(created_at.timestamp())}:R>" if created_at else "*N/A*",
            inline=True,
        )
        embed.add_field(name="By", value=actor.mention if actor else "*Unknown*", inline=True)
        embed.add_field(name="Reason", value=self._shorten(reason, 250), inline=False)
        self._add_role_details_fields(embed, role, include_members=False)

        if role.guild.icon:
            embed.set_thumbnail(url=role.guild.icon.url)
        embed.set_footer(text=f"Role ID: {role.id}")
        
        await self.safe_send_log(channel, embed)

    # ==================== CONFIGURATION COMMAND ====================
    
    @log_group.command(name="set", description="⚙️ Configure logging channels")
    @app_commands.describe(
        log_type="Type of log to configure",
        channel="Channel to send logs to (leave empty to disable)"
    )
    @is_admin()
    async def log_set(
        self,
        interaction: discord.Interaction,
        log_type: Literal['mod', 'audit', 'message', 'voice', 'automod', 'report', 'ticket'],
        channel: Optional[discord.TextChannel] = None
    ):
        """Configure logging channels for different event types"""
        try:
            settings = await self.bot.db.get_settings(interaction.guild_id)
            
            if channel:
                # Set channel
                settings[f'{log_type}_log_channel'] = channel.id
                await self.bot.db.update_settings(interaction.guild_id, settings)
                
                # Update cache
                await self._channel_cache.set(interaction.guild_id, log_type, channel.id)
                
                embed = ModEmbed.success(
                    "Logging Configured",
                    f"**{log_type.title()}** logs will now be sent to {channel.mention}"
                )
            else:
                # Disable logging for this type
                if f'{log_type}_log_channel' in settings:
                    del settings[f'{log_type}_log_channel']
                    await self.bot.db.update_settings(interaction.guild_id, settings)
                
                # Clear cache
                await self._channel_cache.invalidate(interaction.guild_id, log_type)
                
                embed = ModEmbed.success(
                    "Logging Disabled",
                    f"**{log_type.title()}** logging has been disabled"
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to configure logging: {e}")
            await interaction.response.send_message(
                embed=ModEmbed.error("Configuration Failed", f"An error occurred: {str(e)}"),
                ephemeral=True
            )

    @log_group.command(name="config", description="📋 View current logging configuration")
    @is_admin()
    async def log_config(self, interaction: discord.Interaction):
        """View all configured logging channels"""
        try:
            settings = await self.bot.db.get_settings(interaction.guild_id)
            
            embed = discord.Embed(
                title="📋 Logging Configuration",
                color=Colors.INFO,
                timestamp=datetime.now(timezone.utc)
            )
            
            log_types = ['mod', 'audit', 'message', 'voice', 'automod', 'report', 'ticket']
            
            for log_type in log_types:
                channel_id = settings.get(f'{log_type}_log_channel')
                if channel_id:
                    channel = interaction.guild.get_channel(channel_id)
                    value = channel.mention if channel else "❌ Channel not found"
                else:
                    value = "*Not configured*"
                
                embed.add_field(
                    name=f"{log_type.title()} Logs",
                    value=value,
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to get log config: {e}")
            await interaction.response.send_message(
                embed=ModEmbed.error("Failed", f"An error occurred: {str(e)}"),
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Load the Logging cog"""
    await bot.add_cog(Logging(bot))
