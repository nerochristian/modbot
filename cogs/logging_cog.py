"""
Advanced Logging System
Comprehensive event logging for messages, members, voice, moderation actions, and more
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal, Any
import logging
import io

from utils.embeds import ModEmbed, Colors
from utils.checks import is_admin
from utils.cache import ChannelCache
from utils.transcript import generate_html_transcript, EphemeralTranscriptView
from utils.logging import normalize_log_embed

logger = logging.getLogger(__name__)


class Logging(commands.Cog):
    """Event logging system with configurable channels"""
    
    # Command group for logging configuration
    log_group = app_commands.Group(name="log", description="📝 Logging configuration")
    _LOG_CHANNEL_KEY_ALIASES: dict[str, tuple[str, ...]] = {
        "mod": ("mod_log_channel", "log_channel_mod"),
        "audit": ("audit_log_channel", "log_channel_audit"),
        "message": ("message_log_channel", "log_channel_message"),
        "voice": ("voice_log_channel", "log_channel_voice"),
        "automod": ("automod_log_channel", "log_channel_automod"),
        "report": ("report_log_channel", "log_channel_report"),
        "ticket": ("ticket_log_channel", "log_channel_ticket"),
    }

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._channel_cache = ChannelCache(ttl=300)  # 5 minute TTL
        self._audit_search_window_seconds = 15
        self._suppress_message_delete_until: dict[int, datetime] = {}
        self._suppress_bulk_delete_until: dict[int, datetime] = {}
        self._suppress_timeout_change_until: dict[tuple[int, int], datetime] = {}
        self._seen_webhook_create_entries: dict[int, datetime] = {}
        self._recent_message_snapshots: dict[int, dict[str, Any]] = {}
        self._recent_message_snapshot_ttl = timedelta(hours=3)
        self._recent_message_snapshot_max = 20000

    def _log_channel_setting_keys(self, log_type: str) -> tuple[str, ...]:
        aliases = self._LOG_CHANNEL_KEY_ALIASES.get(log_type)
        if aliases:
            return aliases
        return (f"log_channel_{log_type}", f"{log_type}_log_channel")

    @staticmethod
    def _coerce_channel_id(value: Any) -> Optional[int]:
        try:
            channel_id = int(value)
        except (TypeError, ValueError):
            return None
        return channel_id if channel_id > 0 else None

    def _resolve_log_channel_id(self, settings: dict[str, Any], log_type: str) -> Optional[int]:
        for key in self._log_channel_setting_keys(log_type):
            channel_id = self._coerce_channel_id(settings.get(key))
            if channel_id:
                return channel_id
        return None

    def suppress_message_delete_log(self, channel_id: int, seconds: int = 6) -> None:
        self._suppress_message_delete_until[channel_id] = datetime.now(timezone.utc) + timedelta(seconds=seconds)

    def suppress_bulk_delete_log(self, channel_id: int, seconds: int = 8) -> None:
        self._suppress_bulk_delete_until[channel_id] = datetime.now(timezone.utc) + timedelta(seconds=seconds)

    def _is_message_delete_suppressed(self, channel_id: int) -> bool:
        until = self._suppress_message_delete_until.get(channel_id)
        if not until:
            return False
        if datetime.now(timezone.utc) >= until:
            self._suppress_message_delete_until.pop(channel_id, None)
            return False
        return True

    def _is_bulk_delete_suppressed(self, channel_id: int) -> bool:
        until = self._suppress_bulk_delete_until.get(channel_id)
        if not until:
            return False
        if datetime.now(timezone.utc) >= until:
            self._suppress_bulk_delete_until.pop(channel_id, None)
            return False
        return True

    def suppress_timeout_change_log(self, guild_id: int, user_id: int, seconds: int = 8) -> None:
        key = (guild_id, user_id)
        self._suppress_timeout_change_until[key] = datetime.now(timezone.utc) + timedelta(seconds=seconds)

    def _is_timeout_change_suppressed(self, guild_id: int, user_id: int) -> bool:
        key = (guild_id, user_id)
        until = self._suppress_timeout_change_until.get(key)
        if not until:
            return False
        if datetime.now(timezone.utc) >= until:
            self._suppress_timeout_change_until.pop(key, None)
            return False
        return True

    def _remember_webhook_entry(self, entry_id: int) -> bool:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=5)
        stale_ids = [seen_id for seen_id, seen_at in self._seen_webhook_create_entries.items() if seen_at < cutoff]
        for seen_id in stale_ids:
            self._seen_webhook_create_entries.pop(seen_id, None)

        if entry_id in self._seen_webhook_create_entries:
            return False

        self._seen_webhook_create_entries[entry_id] = now
        return True

    def _prune_recent_message_snapshots(self) -> None:
        if not self._recent_message_snapshots:
            return
        now = datetime.now(timezone.utc)
        cutoff = now - self._recent_message_snapshot_ttl
        stale_ids = [
            message_id
            for message_id, data in self._recent_message_snapshots.items()
            if data.get("stored_at", now) < cutoff
        ]
        for message_id in stale_ids:
            self._recent_message_snapshots.pop(message_id, None)

        while len(self._recent_message_snapshots) > self._recent_message_snapshot_max:
            oldest_id = min(
                self._recent_message_snapshots,
                key=lambda mid: self._recent_message_snapshots[mid].get("stored_at", now),
            )
            self._recent_message_snapshots.pop(oldest_id, None)

    def _cache_message_snapshot(self, message: discord.Message) -> None:
        if not message.guild:
            return
        self._recent_message_snapshots[message.id] = {
            "stored_at": datetime.now(timezone.utc),
            "guild_id": message.guild.id,
            "channel_id": message.channel.id,
            "author_id": getattr(message.author, "id", None),
            "author_name": getattr(message.author, "name", ""),
            "author_display": getattr(message.author, "display_name", ""),
            "content": message.content or "",
            "created_ts": int(message.created_at.timestamp()) if getattr(message, "created_at", None) else None,
            "attachments": [a.filename for a in (message.attachments or [])[:10]],
            "attachment_count": len(message.attachments or []),
        }
        if len(self._recent_message_snapshots) % 250 == 0:
            self._prune_recent_message_snapshots()

    def _pop_message_snapshot(
        self,
        message_id: int,
        *,
        guild_id: Optional[int] = None,
        channel_id: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        data = self._recent_message_snapshots.pop(message_id, None)
        if not data:
            return None

        if guild_id is not None and data.get("guild_id") != guild_id:
            return None
        if channel_id is not None and data.get("channel_id") != channel_id:
            return None

        stored_at = data.get("stored_at")
        if isinstance(stored_at, datetime):
            if datetime.now(timezone.utc) - stored_at > self._recent_message_snapshot_ttl:
                return None
        return data

    async def get_log_channel(
        self, 
        guild: discord.Guild, 
        log_type: str,
        *,
        allow_audit_fallback: bool = False,
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
                channel_id = self._resolve_log_channel_id(settings, log_type)

                # Global audit fallback: if a type-specific channel is not configured,
                # route logs into the audit channel so events are never dropped.
                if allow_audit_fallback and not channel_id and log_type != "audit":
                    channel_id = self._resolve_log_channel_id(settings, "audit")

                # Keep mod logs strictly moderation-only.
                # If a non-mod log type resolves to the mod log channel, drop it.
                if log_type != "mod" and channel_id:
                    mod_channel_id = self._resolve_log_channel_id(settings, "mod")
                    if mod_channel_id and channel_id == mod_channel_id:
                        # For audit specifically, prefer any alternate audit key first.
                        if log_type == "audit":
                            for key in self._log_channel_setting_keys("audit"):
                                candidate_id = self._coerce_channel_id(settings.get(key))
                                if candidate_id and candidate_id != mod_channel_id:
                                    channel_id = candidate_id
                                    break
                        if channel_id == mod_channel_id:
                            channel_id = None
                 
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
            removed = False
            for key in self._log_channel_setting_keys(log_type):
                if key in settings:
                    del settings[key]
                    removed = True
            if removed:
                await self.bot.db.update_settings(guild_id, settings)
            
            logger.warning(f"Removed invalid {log_type} log channel for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error removing invalid channel: {e}")

    async def safe_send_log(
        self, 
        channel: Optional[discord.TextChannel], 
        embed: discord.Embed,
        *,
        use_v2: bool = False,
        view: Optional[discord.ui.View] = None,
        mirror_to_audit: bool = False,
    ) -> bool:
        """
        Safely send a log embed with enhanced error handling
        Returns: bool indicating success
        
        Args:
            channel: The channel to send to
            embed: The embed to send
            use_v2: Whether to use Components v2 (default False for classic v1 embeds)
            view: Optional view to Attach to the log message
            mirror_to_audit: Also send this log to the configured audit log channel
        """
        if not channel:
            return False

        # Hard routing guard: if an audit/message card is about to be posted in the
        # wrong channel, reroute before sending.
        routed_channel = channel
        try:
            destination_type = self._classify_misrouted_log_embed(embed)
            if destination_type:
                settings = await self.bot.db.get_settings(channel.guild.id)
                mod_channel_id = self._resolve_log_channel_id(settings, "mod")
                source_is_mod = bool(mod_channel_id and channel.id == mod_channel_id)
                destination_id = self._resolve_log_channel_id(settings, destination_type)
                if destination_id and destination_id != channel.id:
                    destination_channel = channel.guild.get_channel(destination_id)
                    if isinstance(destination_channel, discord.TextChannel):
                        routed_channel = destination_channel
                    elif source_is_mod:
                        logger.warning(
                            "Dropping %s log in %s: destination channel is invalid.",
                            destination_type,
                            channel.guild.name,
                        )
                        return False
                elif source_is_mod:
                    logger.warning(
                        "Dropping %s log in %s: destination channel is not configured.",
                        destination_type,
                        channel.guild.name,
                    )
                    return False
        except Exception:
            routed_channel = channel

        sent_primary = False
        try:
            normalized = normalize_log_embed(routed_channel, embed)
            await routed_channel.send(embed=normalized, use_v2=use_v2, view=view)
            sent_primary = True
        except discord.Forbidden:
            logger.warning(f"Missing permissions to log in {routed_channel.guild.name} #{routed_channel.name}")
            # Invalidate cache for this channel
            await self._channel_cache.invalidate(routed_channel.guild.id, "unknown")
        except discord.NotFound:
            logger.warning(f"Log channel not found: {routed_channel.guild.name} #{routed_channel.name}")
            # Channel was deleted
            await self._channel_cache.invalidate(routed_channel.guild.id, "unknown")
        except discord.HTTPException as e:
            logger.error(f"Failed to send log in {routed_channel.guild.name}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending log: {e}")
        sent_audit = False
        if mirror_to_audit:
            try:
                audit_channel = await self.get_log_channel(routed_channel.guild, "audit")
            except Exception:
                audit_channel = None

            if audit_channel and audit_channel.id != routed_channel.id:
                try:
                    # Do not reuse the same View object across multiple messages.
                    normalized_audit = normalize_log_embed(audit_channel, embed)
                    await audit_channel.send(embed=normalized_audit, use_v2=use_v2)
                    sent_audit = True
                except discord.Forbidden:
                    logger.warning(f"Missing permissions to log in {audit_channel.guild.name} #{audit_channel.name}")
                    await self._channel_cache.invalidate(audit_channel.guild.id, "audit")
                except discord.NotFound:
                    logger.warning(f"Audit log channel not found: {audit_channel.guild.name} #{audit_channel.name}")
                    await self._channel_cache.invalidate(audit_channel.guild.id, "audit")
                except discord.HTTPException as e:
                    logger.error(f"Failed to mirror log to audit in {audit_channel.guild.name}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error mirroring audit log: {e}")

        return sent_primary or sent_audit

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

    def _format_user_reference(self, user: Optional[discord.abc.User]) -> str:
        if user is None:
            return "*Unknown*"
        mention = getattr(user, "mention", None)
        primary = str(user)
        if mention:
            return f"{primary} ({mention})"
        return primary

    def _format_channel_reference(self, channel: Optional[object], *, fallback_id: Optional[int] = None) -> str:
        if channel is None:
            if fallback_id is not None:
                return f"<#{fallback_id}>"
            return "*Unknown*"
        channel_name = getattr(channel, "name", "unknown")
        mention = getattr(channel, "mention", None)
        if mention:
            return f"{channel_name} ({mention})"
        return channel_name

    @staticmethod
    def _classify_misrouted_log_embed(embed: discord.Embed) -> Optional[str]:
        """Return target log type for known misplaced cards, otherwise None."""
        title = (getattr(embed, "title", "") or "").strip().lower()
        if not title:
            return None

        # Message delete cards should live in message logs only.
        if (
            title == "message deleted"
            or title.endswith("messages deleted")
            or title == "bulk message delete"
        ):
            return "message"

        # Audit/system cards should not appear in mod logs.
        audit_markers = (
            "permissions updated",
            "channel created",
            "channel deleted",
            "role created",
            "role deleted",
            "role updated",
            "webhook created",
            "emoji created",
            "emoji deleted",
            "emoji updated",
            "emoji removed",
            "sticker created",
            "sticker deleted",
            "sticker updated",
            "invite created",
            "invite deleted",
        )
        if any(marker in title for marker in audit_markers):
            return "audit"

        return None

    async def _reroute_misplaced_log_message(self, message: discord.Message) -> None:
        """
        Move known misrouted log cards out of mod logs.

        This is a safety net for emitters that still post audit/message cards to
        the mod log channel.
        """
        if not message.guild or not message.embeds:
            return

        # Accept bot/webhook-authored cards, not only this exact user ID.
        # Some paths may post via alternate bot identity/webhook wrappers.
        if not getattr(message.author, "bot", False) and message.webhook_id is None:
            return

        settings = await self.bot.db.get_settings(message.guild.id)
        mod_channel_id = self._resolve_log_channel_id(settings, "mod")
        if not mod_channel_id or message.channel.id != mod_channel_id:
            return

        destination_type = self._classify_misrouted_log_embed(message.embeds[0])
        if not destination_type:
            return

        destination_id = self._resolve_log_channel_id(settings, destination_type)
        if not destination_id or destination_id == message.channel.id:
            return

        destination_channel = message.guild.get_channel(destination_id)
        if destination_channel is None:
            return

        try:
            normalized_embeds = [
                normalize_log_embed(destination_channel, embed)
                for embed in message.embeds[:10]
            ]
            send_kwargs: dict[str, Any] = {"embeds": normalized_embeds}
            if message.content:
                send_kwargs["content"] = message.content
            await destination_channel.send(**send_kwargs)
            await message.delete()
        except discord.Forbidden:
            logger.warning(
                "Missing permissions while rerouting misplaced log in %s",
                message.guild.name,
            )
        except discord.HTTPException as e:
            logger.error(
                "Failed to reroute misplaced log in %s: %s",
                message.guild.name,
                e,
            )
        except Exception as e:
            logger.error(
                "Unexpected error rerouting misplaced log in %s: %s",
                message.guild.name,
                e,
            )

    @staticmethod
    def _quote_lines(lines: list[str]) -> str:
        return "\n".join(f"> {line}" for line in lines if line)

    def _build_sapphire_log_embed(
        self,
        *,
        title: str,
        color: int,
        details_lines: list[str],
        message_text: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        footer_user: Optional[discord.abc.User] = None,
        footer_text: Optional[str] = None,
    ) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(timezone.utc),
        )

        if details_lines:
            embed.add_field(name="\u200b", value=self._quote_lines(details_lines), inline=False)

        if message_text is not None:
            value = (message_text or "").strip() or "*No content*"
            if len(value) > 1024:
                value = value[:1021].rstrip() + "..."
            embed.add_field(name="Message", value=value, inline=False)

        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        if footer_user is not None:
            footer_name = f"@{getattr(footer_user, 'name', str(footer_user))}"
            footer_icon = getattr(getattr(footer_user, "display_avatar", None), "url", None)
            embed.set_footer(text=footer_name, icon_url=footer_icon)
        elif footer_text:
            embed.set_footer(text=footer_text)

        return embed

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

    def _channel_detail_lines(self, channel: discord.abc.GuildChannel) -> list[str]:
        category = getattr(channel, "category", None)
        category_value = category.mention if category else "*None*"
        lines = [
            f"**Category:** {category_value}",
            f"**Position:** {getattr(channel, 'position', '*N/A*')}",
            f"**Overwrites:** {len(getattr(channel, 'overwrites', {}) or {})}",
        ]

        nsfw = getattr(channel, "nsfw", None)
        lines.append(f"**NSFW:** {self._yn(nsfw) if nsfw is not None else '*N/A*'}")

        slowmode_delay = getattr(channel, "slowmode_delay", None)
        lines.append(
            f"**Slowmode:** {f'{slowmode_delay}s' if slowmode_delay is not None else '*N/A*'}"
        )

        permissions_synced = getattr(channel, "permissions_synced", None)
        lines.append(
            f"**Synced:** {self._yn(permissions_synced) if permissions_synced is not None else '*N/A*'}"
        )

        topic = getattr(channel, "topic", None)
        if topic:
            lines.append(f"**Topic:** {self._shorten(topic, 180)}")

        bitrate = getattr(channel, "bitrate", None)
        user_limit = getattr(channel, "user_limit", None)
        if bitrate is not None or user_limit is not None:
            bitrate_text = f"{int(bitrate/1000)}kbps" if bitrate else "*N/A*"
            limit_text = str(user_limit) if user_limit else "∞"
            lines.append(f"**Voice:** Bitrate {bitrate_text}, Limit {limit_text}")

        return lines

    def _role_detail_lines(self, role: discord.Role, *, include_members: bool = True) -> list[str]:
        color_value = role.color.value
        color_text = f"#{color_value:06x}" if color_value else "Default"
        lines = [
            f"**Color:** {color_text}",
            f"**Position:** {role.position}",
            f"**Hoist:** {self._yn(role.hoist)}",
            f"**Mentionable:** {self._yn(role.mentionable)}",
            f"**Managed:** {self._yn(role.managed)}",
        ]
        if include_members:
            lines.insert(2, f"**Members:** {len(role.members)}")

        perms = role.permissions
        key_perms = [
            ("Administrator", perms.administrator),
            ("Manage Server", perms.manage_guild),
            ("Manage Roles", perms.manage_roles),
            ("Manage Channels", perms.manage_channels),
            ("Ban Members", perms.ban_members),
            ("Kick Members", perms.kick_members),
        ]
        enabled = [name for name, enabled in key_perms if enabled]
        lines.append(f"**Key perms:** {', '.join(enabled) if enabled else 'None'}")
        return lines

    # ==================== MESSAGE LOGGING ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Cache recent messages so raw delete fallback can still show author/content."""
        if not message.guild:
            return
        try:
            await self._reroute_misplaced_log_message(message)
        except Exception:
            pass
        try:
            self._cache_message_snapshot(message)
        except Exception:
            pass
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Log deleted messages"""
        # Ignore DMs
        if not message.guild:
            return

        self._pop_message_snapshot(
            message.id,
            guild_id=message.guild.id,
            channel_id=message.channel.id,
        )

        if self._is_message_delete_suppressed(message.channel.id):
            return

        channel = await self.get_log_channel(message.guild, 'message', allow_audit_fallback=False)
        if not channel:
            return

        message_link = (
            f"https://discord.com/channels/"
            f"{message.guild.id}/{message.channel.id}/{message.id}"
        )
        details_lines = [
            f"**Source channel:** {self._format_channel_reference(message.channel)}",
            f"**Message ID:** [{message.id}]({message_link})",
            f"**Message author:** {self._format_user_reference(message.author)}",
            f"**Message created:** <t:{int(message.created_at.timestamp())}:R>",
        ]

        content_value = (message.content or "").strip()
        if not content_value:
            content_value = "*No text content*" if (message.embeds or message.attachments) else "*No content*"

        embed = self._build_sapphire_log_embed(
            title="Message deleted",
            color=Colors.ERROR,
            details_lines=details_lines,
            message_text=content_value,
        )

        if message.attachments:
            attachment_names = [a.filename for a in message.attachments[:10]]
            attachments_text = ", ".join(attachment_names)
            if len(message.attachments) > 10:
                attachments_text += f", +{len(message.attachments) - 10} more"
            embed.add_field(
                name=f"Attachments ({len(message.attachments)})",
                value=attachments_text,
                inline=False,
            )

        # Single-message deletes should not include transcript downloads.
        # Transcript views are reserved for purge/bulk-delete events.
        await self.safe_send_log(channel, embed, use_v2=False, mirror_to_audit=False)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        """
        Fallback delete logger for uncached messages.

        `on_message_delete` only fires for cached messages. This raw event ensures
        we still emit logs when Discord does not have a cached Message object.
        """
        # Cached deletes are already handled by on_message_delete.
        if payload.cached_message is not None:
            return

        guild_id = payload.guild_id
        if guild_id is None:
            return

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return

        channel_id = payload.channel_id
        if self._is_message_delete_suppressed(channel_id):
            return

        log_channel = await self.get_log_channel(guild, "message", allow_audit_fallback=False)
        if not log_channel:
            return

        source_channel = guild.get_channel(channel_id) or guild.get_thread(channel_id)

        message_id = payload.message_id
        snapshot = self._pop_message_snapshot(
            message_id,
            guild_id=guild.id,
            channel_id=channel_id,
        )
        message_link = (
            f"https://discord.com/channels/"
            f"{guild.id}/{channel_id}/{message_id}"
        )

        if snapshot:
            author_id = snapshot.get("author_id")
            author_display = snapshot.get("author_display") or snapshot.get("author_name") or "unknown"
            author_ref = f"<@{author_id}> (`@{author_display}`)" if author_id else f"`@{author_display}`"
            created_ts = snapshot.get("created_ts")
            content_text = str(snapshot.get("content", "") or "").strip()
            attachment_count = int(snapshot.get("attachment_count", 0) or 0)
            if not content_text:
                content_text = "*No text content*" if attachment_count > 0 else "*No content*"

            details_lines = [
                f"**Source channel:** {self._format_channel_reference(source_channel, fallback_id=channel_id)}",
                f"**Message ID:** [{message_id}]({message_link})",
                f"**Message author:** {author_ref}",
                f"**Message created:** <t:{created_ts}:R>" if created_ts else "**Message created:** *Unknown*",
            ]
            embed = self._build_sapphire_log_embed(
                title="Message deleted",
                color=Colors.ERROR,
                details_lines=details_lines,
                message_text=content_text,
            )

            attachments = [str(name) for name in (snapshot.get("attachments") or []) if str(name).strip()]
            if attachments:
                attachments_text = ", ".join(attachments)
                if attachment_count > len(attachments):
                    attachments_text += f", +{attachment_count - len(attachments)} more"
                embed.add_field(
                    name=f"Attachments ({attachment_count})",
                    value=attachments_text,
                    inline=False,
                )
        else:
            details_lines = [
                f"**Source channel:** {self._format_channel_reference(source_channel, fallback_id=channel_id)}",
                f"**Message ID:** [{message_id}]({message_link})",
                "**Message author:** *Unknown (message not cached)*",
                "**Message created:** *Unknown*",
            ]
            embed = self._build_sapphire_log_embed(
                title="Message deleted",
                color=Colors.ERROR,
                details_lines=details_lines,
                message_text="*Content unavailable (message was not cached by the bot).*",
            )

        await self.safe_send_log(log_channel, embed, use_v2=False, mirror_to_audit=False)

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
            title="Message edited",
            color=Colors.WARNING,
            timestamp=datetime.now(timezone.utc),
        )

        channel_name = getattr(before.channel, "name", "unknown")
        created_ts = int(before.created_at.timestamp())
        details_lines = [
            f"**Channel:** {before.channel.mention} (`#{channel_name}`)",
            f"**Message ID:** `{before.id}`",
            f"**Message author:** {before.author.mention} (`@{before.author.name}`)",
            f"**Message created:** <t:{created_ts}:R>",
            f"**Jump:** [Open message]({after.jump_url})",
        ]
        embed.add_field(name="\u200b", value="> " + "\n> ".join(details_lines), inline=False)

        before_content = (before.content or "").strip() or "*Empty*"
        if len(before_content) > 1024:
            before_content = before_content[:1021].rstrip() + "..."

        after_content = (after.content or "").strip() or "*Empty*"
        if len(after_content) > 1024:
            after_content = after_content[:1021].rstrip() + "..."

        embed.add_field(name="Before", value=before_content, inline=True)
        embed.add_field(name="After", value=after_content, inline=True)

        footer_name = before.author.global_name or before.author.name
        embed.set_footer(text=f"@{footer_name}", icon_url=before.author.display_avatar.url)

        await self.safe_send_log(channel, embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        """Log bulk message deletions"""
        if not messages:
            return

        if self._is_bulk_delete_suppressed(messages[0].channel.id):
            return

        # Get guild from first message
        guild = messages[0].guild
        if not guild:
            return

        channel = await self.get_log_channel(guild, 'message', allow_audit_fallback=False)
        if not channel:
            return

        deleted_count = len(messages)
        source_channel = messages[0].channel
        details_lines = [
            f"**Source channel:** {self._format_channel_reference(source_channel)}",
        ]

        actor = None
        now = datetime.now(timezone.utc)
        try:
            async for entry in guild.audit_logs(limit=6, action=discord.AuditLogAction.message_bulk_delete):
                age = (now - entry.created_at).total_seconds()
                if age > self._audit_search_window_seconds:
                    continue
                entry_channel = getattr(getattr(entry, "extra", None), "channel", None)
                if entry_channel and getattr(entry_channel, "id", None) != source_channel.id:
                    continue
                actor = getattr(entry, "user", None)
                break
        except discord.Forbidden:
            actor = None
        except Exception as e:
            logger.error(f"Failed to query bulk delete audit logs in {guild.name}: {e}")

        embed = self._build_sapphire_log_embed(
            title=f"{deleted_count} messages deleted",
            color=Colors.ERROR,
            details_lines=details_lines,
            footer_user=actor,
        )

        transcript_file = generate_html_transcript(
            guild,
            messages[0].channel,
            [],
            purged_messages=messages,
        )
        transcript_name = f"purge-transcript-{guild.id}-{int(datetime.now(timezone.utc).timestamp())}.html"
        view = EphemeralTranscriptView(io.BytesIO(transcript_file.getvalue()), filename=transcript_name)

        await self.safe_send_log(channel, embed, view=view, mirror_to_audit=False)

    # ==================== MEMBER LOGGING ====================
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Log member joins"""
        channel = await self.get_log_channel(member.guild, 'audit')
        if not channel:
            return

        account_age = (datetime.now(timezone.utc) - member.created_at).days
        details_lines = [
            f"**User:** {self._format_user_reference(member)}",
            f"**Account age:** {account_age} day(s)",
            f"**Created:** <t:{int(member.created_at.timestamp())}:R>",
            f"**Member count:** #{member.guild.member_count}",
        ]

        color = Colors.SUCCESS
        suspicious_tokens = ("discord", "nitro", "mod", "admin", "support")
        if account_age < 7:
            details_lines.append("**Warning:** New account")
            color = Colors.WARNING
        if any(token in member.name.lower() for token in suspicious_tokens):
            details_lines.append("**Warning:** Username contains common scam keywords")
            color = Colors.WARNING

        embed = self._build_sapphire_log_embed(
            title="Member joined",
            color=color,
            details_lines=details_lines,
            thumbnail_url=member.display_avatar.url,
        )
        await self.safe_send_log(channel, embed)
        return

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Log member leaves/kicks"""
        channel = await self.get_log_channel(member.guild, 'audit')
        if not channel:
            return

        if member.joined_at:
            days_in_server = (datetime.now(timezone.utc) - member.joined_at).days
            tenure = f"{days_in_server} day(s)"
        else:
            tenure = "Unknown"

        details_lines = [
            f"**User:** {self._format_user_reference(member)}",
            f"**Time in server:** {tenure}",
            f"**Member count:** #{member.guild.member_count}",
        ]

        roles = [r.mention for r in member.roles[1:] if r.name != "@everyone"]
        if roles:
            roles_text = ", ".join(roles[:10])
            if len(roles) > 10:
                roles_text += f" +{len(roles) - 10} more"
            details_lines.append(f"**Roles:** {roles_text}")

        title = "Member left"
        footer_user = None
        try:
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                target_id = getattr(getattr(entry, "target", None), "id", None)
                if target_id != member.id:
                    continue
                if (datetime.now(timezone.utc) - entry.created_at).seconds < 5:
                    title = "Member kicked"
                    footer_user = getattr(entry, "user", None)
                    reason = getattr(entry, "reason", None)
                    if reason:
                        details_lines.append(f"**Reason:** {self._shorten(reason, 250)}")
                    break
        except discord.Forbidden:
            pass
        except Exception as e:
            logger.error(f"Failed to check audit log for kick: {e}")

        embed = self._build_sapphire_log_embed(
            title=title,
            color=Colors.ERROR,
            details_lines=details_lines,
            thumbnail_url=member.display_avatar.url,
            footer_user=footer_user,
        )
        await self.safe_send_log(channel, embed)
        return

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Log member updates (nickname, roles, etc.)"""
        channel = await self.get_log_channel(before.guild, 'audit')
        if not channel:
            return

        if before.nick != after.nick:
            entry = await self._find_recent_audit_entry(
                before.guild,
                action=discord.AuditLogAction.member_update,
                target_id=after.id,
            )
            moderator = getattr(entry, "user", None)
            reason = getattr(entry, "reason", None)
            details_lines = [
                f"**User:** {self._format_user_reference(after)}",
                f"**Before:** {before.nick or '*None*'}",
                f"**After:** {after.nick or '*None*'}",
            ]
            if reason:
                details_lines.append(f"**Reason:** {self._shorten(reason, 250)}")

            embed = self._build_sapphire_log_embed(
                title="Nickname changed",
                color=Colors.INFO,
                details_lines=details_lines,
                thumbnail_url=after.display_avatar.url,
                footer_user=moderator,
            )
            await self.safe_send_log(channel, embed)

        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]

            if added or removed:
                added_text = "*None*"
                if added:
                    added_text = ", ".join([r.mention for r in added[:10]])
                    if len(added) > 10:
                        added_text += f" +{len(added) - 10} more"

                removed_text = "*None*"
                if removed:
                    removed_text = ", ".join([r.mention for r in removed[:10]])
                    if len(removed) > 10:
                        removed_text += f" +{len(removed) - 10} more"

                entry = await self._find_recent_audit_entry(
                    before.guild,
                    action=discord.AuditLogAction.member_role_update,
                    target_id=after.id,
                )
                moderator = getattr(entry, "user", None)
                reason = getattr(entry, "reason", None)

                details_lines = [
                    f"**User:** {self._format_user_reference(after)}",
                    f"**Added:** {added_text}",
                    f"**Removed:** {removed_text}",
                ]
                if reason:
                    details_lines.append(f"**Reason:** {self._shorten(reason, 250)}")

                embed = self._build_sapphire_log_embed(
                    title="Roles updated",
                    color=Colors.INFO,
                    details_lines=details_lines,
                    thumbnail_url=after.display_avatar.url,
                    footer_user=moderator,
                )
                await self.safe_send_log(channel, embed)
        
        # ===== TIMEOUT CHANGES =====
        if before.timed_out_until != after.timed_out_until:
            if not self._is_timeout_change_suppressed(before.guild.id, after.id):
                if after.timed_out_until and after.timed_out_until > datetime.now(timezone.utc):
                    # User was timed out
                    entry = await self._find_recent_audit_entry(
                        before.guild,
                        action=discord.AuditLogAction.member_update,
                        target_id=after.id,
                    )
                    moderator = getattr(entry, "user", None)
                    reason = getattr(entry, "reason", None)

                    until_ts = int(after.timed_out_until.timestamp())
                    details_lines = [
                        f"**User:** {self._format_user_reference(after)}",
                        f"**Until:** <t:{until_ts}:F>",
                        f"**Duration:** <t:{until_ts}:R>",
                    ]
                    if reason:
                        details_lines.append(f"**Reason:** {self._shorten(reason, 250)}")

                    embed = self._build_sapphire_log_embed(
                        title="User timed out",
                        color=Colors.ERROR,
                        details_lines=details_lines,
                        thumbnail_url=after.display_avatar.url,
                        footer_user=moderator,
                    )
                    
                    await self.safe_send_log(channel, embed)
                elif before.timed_out_until and not after.timed_out_until:
                    # Timeout removed
                    entry = await self._find_recent_audit_entry(
                        before.guild,
                        action=discord.AuditLogAction.member_update,
                        target_id=after.id,
                    )
                    moderator = getattr(entry, "user", None)
                    reason = getattr(entry, "reason", None)

                    details_lines = [
                        f"**User:** {self._format_user_reference(after)}",
                    ]
                    if reason:
                        details_lines.append(f"**Reason:** {self._shorten(reason, 250)}")

                    embed = self._build_sapphire_log_embed(
                        title="User timeout removed",
                        color=Colors.SUCCESS,
                        details_lines=details_lines,
                        thumbnail_url=after.display_avatar.url,
                        footer_user=moderator,
                    )
                    
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

        moderator = None
        ban_reason = None
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                target_id = getattr(getattr(entry, "target", None), "id", None)
                if target_id == user.id:
                    moderator = getattr(entry, "user", None)
                    ban_reason = getattr(entry, "reason", None)
                    break
        except discord.Forbidden:
            logger.warning(f"Missing audit log permissions in {guild.name}")
        except Exception as e:
            logger.error(f"Failed to check audit log for ban: {e}")

        details_lines = [
            f"**User:** {self._format_user_reference(user)}",
            f"**Bot:** {self._yn(getattr(user, 'bot', False))}",
            f"**Reason:** {self._shorten(ban_reason, 250)}",
        ]
        if getattr(user, "created_at", None):
            details_lines.insert(1, f"**Account created:** <t:{int(user.created_at.timestamp())}:R>")

        embed = self._build_sapphire_log_embed(
            title="Member banned",
            color=Colors.DARK_RED,
            details_lines=details_lines,
            thumbnail_url=user.display_avatar.url,
            footer_user=moderator,
        )
        await self.safe_send_log(channel, embed)
        return

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Log unbans"""
        channel = await self.get_log_channel(guild, 'audit')
        if not channel:
            return

        moderator = None
        unban_reason = None
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
                target_id = getattr(getattr(entry, "target", None), "id", None)
                if target_id == user.id:
                    moderator = getattr(entry, "user", None)
                    unban_reason = getattr(entry, "reason", None)
                    break
        except discord.Forbidden:
            pass
        except Exception as e:
            logger.error(f"Failed to check audit log for unban: {e}")

        details_lines = [
            f"**User:** {self._format_user_reference(user)}",
            f"**Bot:** {self._yn(getattr(user, 'bot', False))}",
            f"**Reason:** {self._shorten(unban_reason, 250)}",
        ]
        if getattr(user, "created_at", None):
            details_lines.insert(1, f"**Account created:** <t:{int(user.created_at.timestamp())}:R>")

        embed = self._build_sapphire_log_embed(
            title="Member unbanned",
            color=Colors.SUCCESS,
            details_lines=details_lines,
            thumbnail_url=user.display_avatar.url,
            footer_user=moderator,
        )
        await self.safe_send_log(channel, embed)
        return

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        """Log webhook creation events."""
        log_channel = await self.get_log_channel(channel.guild, "audit")
        if not log_channel:
            return

        now = datetime.now(timezone.utc)
        entry = None
        try:
            async for candidate in channel.guild.audit_logs(limit=8, action=discord.AuditLogAction.webhook_create):
                age = (now - candidate.created_at).total_seconds()
                if age > self._audit_search_window_seconds:
                    continue

                webhook = getattr(candidate, "target", None)
                webhook_channel = getattr(webhook, "channel", None)
                webhook_channel_id = getattr(webhook_channel, "id", None) or getattr(webhook, "channel_id", None)
                if webhook_channel_id is not None and webhook_channel_id != channel.id:
                    continue

                entry = candidate
                break
        except discord.Forbidden:
            return
        except Exception as e:
            logger.error(f"Failed to query webhook audit logs in {channel.guild.name}: {e}")
            return

        if entry is None:
            return

        entry_id = getattr(entry, "id", None)
        if entry_id is None or not self._remember_webhook_entry(entry_id):
            return

        webhook = getattr(entry, "target", None)
        webhook_name = getattr(webhook, "name", "Unknown")
        webhook_id = getattr(webhook, "id", "Unknown")
        webhook_type = str(getattr(getattr(webhook, "type", None), "name", "incoming")).upper()

        details_lines = [
            f"**Webhook:** {webhook_name} (`{webhook_id}`)",
            f"**Channel:** {self._format_channel_reference(channel)}",
            f"**Type:** {webhook_type}",
            f"**Reason:** {self._shorten(getattr(entry, 'reason', None), 250)}",
        ]

        embed = self._build_sapphire_log_embed(
            title="Webhook created",
            color=Colors.SUCCESS,
            details_lines=details_lines,
            thumbnail_url=channel.guild.icon.url if channel.guild.icon else None,
            footer_user=getattr(entry, "user", None),
        )

        await self.safe_send_log(log_channel, embed)
    
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

        created_at = getattr(channel, "created_at", None)
        details_lines = [
            f"**Channel:** {self._format_channel_reference(channel)}",
            f"**Type:** {str(channel.type).title()}",
            f"**ID:** `{channel.id}`",
            f"**Created:** {f'<t:{int(created_at.timestamp())}:R>' if created_at else '*N/A*'}",
        ]
        details_lines.extend(self._channel_detail_lines(channel))
        if reason:
            details_lines.append(f"**Reason:** {self._shorten(reason, 250)}")

        embed = self._build_sapphire_log_embed(
            title="Channel created",
            color=Colors.SUCCESS,
            details_lines=details_lines,
            thumbnail_url=channel.guild.icon.url if channel.guild.icon else None,
            footer_user=actor,
        )
        await self.safe_send_log(log_channel, embed)
        return

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

        created_at = getattr(channel, "created_at", None)
        details_lines = [
            f"**Channel:** {self._format_channel_reference(channel)}",
            f"**Type:** {str(channel.type).title()}",
            f"**ID:** `{channel.id}`",
            f"**Created:** {f'<t:{int(created_at.timestamp())}:R>' if created_at else '*N/A*'}",
        ]
        details_lines.extend(self._channel_detail_lines(channel))
        if reason:
            details_lines.append(f"**Reason:** {self._shorten(reason, 250)}")

        embed = self._build_sapphire_log_embed(
            title="Channel deleted",
            color=Colors.ERROR,
            details_lines=details_lines,
            thumbnail_url=channel.guild.icon.url if channel.guild.icon else None,
            footer_user=actor,
        )
        await self.safe_send_log(log_channel, embed)
        return

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

        created_at = getattr(role, "created_at", None)
        details_lines = [
            f"**Role:** {role.mention}",
            f"**ID:** `{role.id}`",
            f"**Created:** {f'<t:{int(created_at.timestamp())}:R>' if created_at else '*N/A*'}",
        ]
        details_lines.extend(self._role_detail_lines(role, include_members=True))
        if reason:
            details_lines.append(f"**Reason:** {self._shorten(reason, 250)}")

        embed = self._build_sapphire_log_embed(
            title="Role created",
            color=role.color if role.color.value != 0 else Colors.SUCCESS,
            details_lines=details_lines,
            thumbnail_url=role.guild.icon.url if role.guild.icon else None,
            footer_user=actor,
        )
        await self.safe_send_log(channel, embed)
        return

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

        created_at = getattr(role, "created_at", None)
        details_lines = [
            f"**Role:** @{role.name}",
            f"**ID:** `{role.id}`",
            f"**Members at deletion:** {len(role.members)}",
            f"**Created:** {f'<t:{int(created_at.timestamp())}:R>' if created_at else '*N/A*'}",
        ]
        details_lines.extend(self._role_detail_lines(role, include_members=False))
        if reason:
            details_lines.append(f"**Reason:** {self._shorten(reason, 250)}")

        embed = self._build_sapphire_log_embed(
            title="Role deleted",
            color=Colors.ERROR,
            details_lines=details_lines,
            thumbnail_url=role.guild.icon.url if role.guild.icon else None,
            footer_user=actor,
        )
        await self.safe_send_log(channel, embed)
        return

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
                for key in self._log_channel_setting_keys(log_type):
                    settings[key] = channel.id
                await self.bot.db.update_settings(interaction.guild_id, settings)
                
                # Update cache
                await self._channel_cache.set(interaction.guild_id, log_type, channel.id)
                
                embed = ModEmbed.success(
                    "Logging Configured",
                    f"**{log_type.title()}** logs will now be sent to {channel.mention}"
                )
            else:
                # Disable logging for this type
                removed = False
                for key in self._log_channel_setting_keys(log_type):
                    if key in settings:
                        del settings[key]
                        removed = True
                if removed:
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
                channel_id = self._resolve_log_channel_id(settings, log_type)
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


