import discord
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional, Union, Tuple
import logging
import json

from utils.embeds import ModEmbed, Colors
from utils.checks import is_bot_owner_id, get_owner_ids
from utils.logging import send_log_embed

logger = logging.getLogger(__name__)

class HelperCommands:
    async def _respond(
        self,
        source: Union[discord.Interaction, commands.Context],
        *,
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
        ephemeral: bool = False,
        **kwargs,
    ):
        """Send a response or followup depending on whether the interaction/context is already acknowledged."""
        try:
            if isinstance(source, discord.Interaction):
                if source.response.is_done():
                    return await source.followup.send(
                        content=content, embed=embed, ephemeral=ephemeral, **kwargs
                    )
                return await source.response.send_message(
                    content=content, embed=embed, ephemeral=ephemeral, **kwargs
                )
            else:
                # Context
                return await source.reply(content=content, embed=embed, **kwargs)
        except discord.HTTPException:
            # Fallback when the interaction state changed mid-execution.
            if isinstance(source, discord.Interaction):
                try:
                    return await source.followup.send(
                        content=content, embed=embed, ephemeral=ephemeral, **kwargs
                    )
                except Exception:
                    pass

    async def log_action(self, guild: discord.Guild, embed: discord.Embed, log_type: str = "mod", view: Optional[discord.ui.View] = None) -> None:
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
                # Silent fail/warn if channel missing
                return
            
            await send_log_embed(channel, embed, view=view)
            
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
        user: Union[discord.User, discord.Member],
        moderator: Union[discord.User, discord.Member],
        reason: str,
        color: int,
        case_num: Optional[int] = None,
        extra_fields: Optional[dict[str, str]] = None
    ) -> discord.Embed:
        """Create standardized moderation embed (audit-log style)"""
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )

        # Author line: target user's name + avatar (like audit logs)
        embed.set_author(
            name=f"{user.name}",
            icon_url=user.display_avatar.url
        )

        embed.add_field(name="User", value=f"{user.mention} ({user.name})", inline=True)
        embed.add_field(name="Moderator", value=f"{moderator.mention}", inline=True)

        if extra_fields:
            for field_name, field_value in extra_fields.items():
                embed.add_field(name=field_name, value=field_value, inline=True)

        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)

        # Footer: Case # + User ID (like audit logs show IDs)
        footer_parts = []
        if case_num:
            footer_parts.append(f"Case #{case_num}")
        footer_parts.append(f"User ID: {user.id}")
        embed.set_footer(text=" • ".join(footer_parts))

        return embed

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

    async def get_user_level(self, guild_id: int, member: discord.Member) -> int:
        """
        Get the hierarchy level of a user based on roles
        Returns: int (0-999, higher = more power)
        """
        if not hasattr(self, "_hierarchy_cache"):
             self._hierarchy_cache = {}

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
    ) -> Tuple[bool, str]:
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
    ) -> Tuple[bool, str]:
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

    async def _backup_roles(self, user: discord.Member) -> list[int]:
        """Backup user roles (excluding @everyone and quarantine role)"""
        settings = await self.bot.db.get_settings(user.guild.id)
        quarantine_role_id = settings.get('automod_quarantine_role_id')
        
        role_ids = []
        for role in user.roles:
            # Skip @everyone and quarantine role
            if role.id == user.guild.id or role.id == quarantine_role_id:
                continue
            role_ids.append(role.id)
        
        return role_ids

    async def _restore_roles(self, user: discord.Member, role_ids: list[int]) -> Tuple[int, int]:
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
                # logger.warning(f"Cannot restore role {role.name} to {user}: role higher than bot.")
                failed += 1
                continue
                
            roles_to_add.append(role)
        
        if roles_to_add:
            try:
                # Batch add for efficiency (1 API call)
                await user.add_roles(*roles_to_add, reason="Quarantine lifted")
                restored = len(roles_to_add)
            except Exception as e:
                # logger.error(f"Failed to batch restore roles for {user}: {e}")
                # Fallback to one-by-one on error
                for role in roles_to_add:
                    try:
                        await user.add_roles(role, reason="Quarantine lifted (fallback)")
                        restored += 1
                    except Exception as inner_e:
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
        except Exception:
            return None
