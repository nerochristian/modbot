"""
Role Management Commands (WITH SECURITY FIXES)
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional
import re
from utils.embeds import ModEmbed
from utils.checks import is_mod, is_admin, is_bot_owner_id
from config import Config


def _is_server_admin_check(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    return bool(
        interaction.user.id == interaction.guild.owner_id
        or interaction.user.guild_permissions.administrator
    )


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        # Auto-add Staff role when any mod role is granted.
        try:
            if before.roles == after.roles:
                return
            if after.bot or not after.guild:
                return

            settings = await self.bot.db.get_settings(after.guild.id)
            staff_role_id = settings.get("staff_role")
            if not staff_role_id:
                return
            staff_role = after.guild.get_role(int(staff_role_id))
            if not staff_role or staff_role in after.roles:
                return

            mod_role_ids: set[int] = set()
            for key in ["admin_role", "supervisor_role", "senior_mod_role", "mod_role", "trial_mod_role"]:
                rid = settings.get(key)
                if isinstance(rid, int) and rid > 0:
                    mod_role_ids.add(rid)

            if not mod_role_ids:
                return

            added_ids = {r.id for r in after.roles if r not in before.roles}
            if not (added_ids & mod_role_ids):
                return

            bot_member = after.guild.me
            if not bot_member or not bot_member.guild_permissions.manage_roles:
                return
            if staff_role >= bot_member.top_role:
                return

            await after.add_roles(staff_role, reason="Auto-add staff role when mod role assigned")
        except Exception:
            return

    @app_commands.command(
        name="promote",
        description="Promote a member to a moderation role (also adds Staff)",
    )
    @is_admin()
    @app_commands.describe(
        user="Member to promote",
        rank="Which role to assign",
        reason="Optional reason to include in the DM",
    )
    @app_commands.choices(
        rank=[
            app_commands.Choice(name="Trial Moderator", value="trial_mod_role"),
            app_commands.Choice(name="Moderator", value="mod_role"),
            app_commands.Choice(name="Senior Moderator", value="senior_mod_role"),
            app_commands.Choice(name="Supervisor", value="supervisor_role"),
            app_commands.Choice(name="Admin", value="admin_role"),
        ]
    )
    async def promote(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        rank: app_commands.Choice[str],
        reason: Optional[str] = None,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                embed=ModEmbed.error("Guild Only", "Use this command in a server."),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        settings = await self.bot.db.get_settings(interaction.guild.id)
        role_id = settings.get(rank.value)
        staff_role_id = settings.get("staff_role")

        if not isinstance(role_id, int):
            await interaction.followup.send(
                embed=ModEmbed.error("Not Configured", f"Role for `{rank.name}` is not set. Run `/setup`."),
                ephemeral=True,
            )
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.followup.send(
                embed=ModEmbed.error("Role Missing", f"Configured role for `{rank.name}` was not found. Run `/setup` again."),
                ephemeral=True,
            )
            return

        staff_role = (
            interaction.guild.get_role(int(staff_role_id))
            if isinstance(staff_role_id, int)
            else None
        )

        bot_member = interaction.guild.me
        if not bot_member or not bot_member.guild_permissions.manage_roles:
            await interaction.followup.send(
                embed=ModEmbed.error("Missing Permission", "Bot needs `Manage Roles`."),
                ephemeral=True,
            )
            return

        if role >= bot_member.top_role or (staff_role and staff_role >= bot_member.top_role):
            await interaction.followup.send(
                embed=ModEmbed.error(
                    "Role Hierarchy",
                    "Move the bot's role above the target roles, then try again.",
                ),
                ephemeral=True,
            )
            return

        if user.top_role >= bot_member.top_role:
            await interaction.followup.send(
                embed=ModEmbed.error("Cannot Promote", "That member has roles above/equal to the bot."),
                ephemeral=True,
            )
            return

        roles_to_add: list[discord.Role] = [role]
        if staff_role and staff_role not in user.roles:
            roles_to_add.append(staff_role)

        try:
            await user.add_roles(*roles_to_add, reason=f"Promoted by {interaction.user} ({interaction.user.id})")
        except Exception as e:
            await interaction.followup.send(
                embed=ModEmbed.error("Failed", f"Could not add roles: {e}"),
                ephemeral=True,
            )
            return

        dm_sent = True
        try:
            dm_embed = discord.Embed(
                title="You were promoted!",
                description=(
                    f"You have been given **{role.name}** in **{interaction.guild.name}**.\n"
                    f"{'Staff role was also added automatically.' if staff_role else ''}"
                ),
                color=Config.COLOR_SUCCESS,
            )
            if reason:
                dm_embed.add_field(name="Reason", value=reason, inline=False)
            dm_embed.add_field(name="Promoted By", value=f"{interaction.user.mention}", inline=False)
            await user.send(embed=dm_embed)
        except Exception:
            dm_sent = False

        await interaction.followup.send(
            embed=ModEmbed.success(
                "Promoted",
                f"{user.mention} received **{role.name}**"
                + (f" + **{staff_role.name}**" if staff_role and staff_role in roles_to_add else "")
                + ("" if dm_sent else "\n\n⚠️ Could not DM the user (DMs closed)."),
            ),
            ephemeral=True,
        )

    @staticmethod
    def _parse_role_id(role_input: str) -> Optional[int]:
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

    async def _remove_role_autocomplete(
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

        bot_member = interaction.guild.me or (
            interaction.guild.get_member(self.bot.user.id) if self.bot.user else None
        )
        bot_top_role = bot_member.top_role if bot_member else None

        roles = [
            r
            for r in member.roles
            if r != interaction.guild.default_role
            and not r.managed
            and (bot_top_role is None or r < bot_top_role)
            and self._matches_role_query(r, current)
        ]
        roles.sort(key=lambda r: r.position, reverse=True)
        return [app_commands.Choice(name=r.name, value=str(r.id)) for r in roles[:25]]

    # RENAMED GROUP TO AVOID CONFLICT WITH MODERATION.PY
    roles_group = app_commands.Group(
        name="roles",
        description="Advanced role management commands",
    )

    @staticmethod
    def _is_dangerous_role(role: discord.Role) -> bool:
        perms = role.permissions
        return bool(
            perms.administrator
            or perms.manage_guild
            or perms.manage_roles
            or perms.manage_channels
            or perms.kick_members
            or perms.ban_members
            or perms.moderate_members
        )

    async def _get_owner_role_allowlist(self, guild_id: int) -> set[int]:
        db = getattr(self.bot, "db", None)
        if not db:
            return set()
        try:
            settings = await db.get_settings(guild_id)
        except Exception:
            return set()

        raw = settings.get("owner_role_allowlist", [])
        if not isinstance(raw, list):
            return set()
        out: set[int] = set()
        for item in raw:
            try:
                out.add(int(item))
            except Exception:
                continue
        return out

    async def _owner_override_for_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
    ) -> tuple[bool, str]:
        """
        Bot owners (from OWNER_IDS/OWNER_ID) bypass role safety restrictions.
        """
        if not is_bot_owner_id(interaction.user.id):
            return False, ""
        return True, ""

    ownerallow_group = app_commands.Group(
        name="ownerallow",
        description="Configure roles bot owners may assign",
        parent=roles_group,
    )

    @ownerallow_group.command(name="add", description="Allowlist a role for bot owners")
    @app_commands.describe(role="Role that bot owners may assign")
    @app_commands.check(_is_server_admin_check)
    async def ownerallow_add(self, interaction: discord.Interaction, role: discord.Role):
        if role.permissions.administrator:
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Not Allowed",
                    "Administrator roles cannot be allowlisted.",
                ),
                ephemeral=True,
            )

        settings = await self.bot.db.get_settings(interaction.guild_id)
        allowlist = settings.get("owner_role_allowlist", [])
        if not isinstance(allowlist, list):
            allowlist = []

        if role.id not in allowlist:
            allowlist.append(role.id)
            settings["owner_role_allowlist"] = allowlist
            await self.bot.db.update_settings(interaction.guild_id, settings)

        await interaction.response.send_message(
            embed=ModEmbed.success("Allowlisted", f"Bot owners can now assign {role.mention}."),
            ephemeral=True,
        )

    @ownerallow_group.command(name="remove", description="Remove a role from the allowlist")
    @app_commands.describe(role="Role to remove from allowlist")
    @app_commands.check(_is_server_admin_check)
    async def ownerallow_remove(self, interaction: discord.Interaction, role: discord.Role):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        allowlist = settings.get("owner_role_allowlist", [])
        if not isinstance(allowlist, list):
            allowlist = []

        if role.id in allowlist:
            allowlist = [rid for rid in allowlist if int(rid) != role.id]
            settings["owner_role_allowlist"] = allowlist
            await self.bot.db.update_settings(interaction.guild_id, settings)

        await interaction.response.send_message(
            embed=ModEmbed.success("Removed", f"Removed {role.mention} from owner allowlist."),
            ephemeral=True,
        )

    @ownerallow_group.command(name="list", description="List roles allowlisted for bot owners")
    @app_commands.check(_is_server_admin_check)
    async def ownerallow_list(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        allowlist = settings.get("owner_role_allowlist", [])
        manage_others = bool(settings.get("owner_role_manage_others_enabled", False))

        if not isinstance(allowlist, list) or not allowlist:
            embed = ModEmbed.info("Owner Allowlist", "No roles are allowlisted.")
            embed.add_field(
                name="Manage Others",
                value="✅ Enabled" if manage_others else "❌ Disabled",
                inline=False,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        roles: list[str] = []
        for rid in allowlist[:25]:
            try:
                role = interaction.guild.get_role(int(rid))  # type: ignore[union-attr]
            except Exception:
                role = None
            roles.append(role.mention if role else f"`{rid}` (missing)")

        embed = ModEmbed.info("Owner Allowlist", "\n".join(roles))
        embed.add_field(
            name="Manage Others",
            value="✅ Enabled" if manage_others else "❌ Disabled",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ownerallow_group.command(
        name="manage_others",
        description="Allow bot owners to assign allowlisted roles to other users",
    )
    @app_commands.describe(enabled="Enable or disable")
    @app_commands.check(_is_server_admin_check)
    async def ownerallow_manage_others(self, interaction: discord.Interaction, enabled: bool):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["owner_role_manage_others_enabled"] = bool(enabled)
        await self.bot.db.update_settings(interaction.guild_id, settings)

        await interaction.response.send_message(
            embed=ModEmbed.success(
                "Updated",
                f"Owner role management for others is now **{'enabled' if enabled else 'disabled'}**.",
            ),
            ephemeral=True,
        )

    def can_manage_role(self, moderator: discord.Member, target_role: discord.Role) -> tuple[bool, str]:
        """
        Check if moderator can manage the target role
        Returns (can_manage, error_message)
        """
        # Server owner can do anything
        if moderator.id == moderator.guild.owner_id:
            return True, ""
        
        # Can't manage roles higher than or equal to your own
        if target_role >= moderator.top_role:
            return False, "You cannot manage this role as it's higher than or equal to your highest role."
        
        # Can't manage roles with admin permission unless you're admin
        if target_role.permissions.administrator and not moderator.guild_permissions.administrator:
            return False, "You cannot manage roles with Administrator permission."
        
        # Can't manage roles with dangerous permissions unless you have them too
        dangerous_perms = ['ban_members', 'kick_members', 'manage_guild', 'manage_roles', 'manage_channels']
        for perm in dangerous_perms:
            if getattr(target_role.permissions, perm) and not getattr(moderator.guild_permissions, perm):
                return False, f"You cannot manage roles with `{perm.replace('_', ' ').title()}` permission."
        
        return True, ""

    def can_manage_target(self, moderator: discord.Member, target: discord.Member) -> tuple[bool, str]:
        """
        Check if moderator can manage the target user
        Returns (can_manage, error_message)
        """
        # Can't manage yourself (for some actions)
        if moderator.id == target.id:
            return True, ""  # Allow managing own roles in some cases

        # Protect bot owner(s)
        if is_bot_owner_id(target.id) and not is_bot_owner_id(moderator.id):
            return False, "You cannot manage the bot owner."

        # Server owner can do anything
        if moderator.id == moderator.guild.owner_id:
            return True, ""
        
        # Can't manage the server owner
        if target.id == target.guild.owner_id:
            return False, "You cannot manage the server owner."
        
        # Can't manage someone with higher or equal role
        if target.top_role >= moderator.top_role:
            return False, "You cannot manage this user as their highest role is higher than or equal to yours."
        
        return True, ""

    @roles_group.command(name="add", description="➕ Add a role to a user")
    @app_commands.describe(user="The user to add role to", role="The role to add")
    @is_mod()
    async def add(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        # Bot-owner override for safe role assignment (dangerous roles require allowlist)
        owner_override, owner_error = await self._owner_override_for_role(interaction, role)
        if not owner_override:
            # Check if moderator can manage this role
            can_manage, error = self.can_manage_role(interaction.user, role)
            if not can_manage:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Permission Denied", error),
                    ephemeral=True,
                )

            # Check if moderator can manage target user
            can_manage_user, error = self.can_manage_target(interaction.user, user)
            if not can_manage_user:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Permission Denied", error),
                    ephemeral=True,
                )
        elif owner_error:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", owner_error),
                ephemeral=True,
            )

        # Never allow giving roles to the server owner unless you're the server owner
        if (
            interaction.guild
            and user.id == interaction.guild.owner_id
            and interaction.user.id != interaction.guild.owner_id
            and not is_bot_owner_id(interaction.user.id)
        ):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You cannot manage the server owner's roles."),
                ephemeral=True,
            )
        
        # Check if bot can manage this role
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Bot Permission Error", "I cannot manage this role as it's higher than or equal to my highest role."),
                ephemeral=True
            )
        
        # Check if user already has the role
        if role in user.roles:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Already Has Role", f"{user.mention} already has {role.mention}"),
                ephemeral=True
            )
        
        # Check if it's a managed/integration role
        if role.managed:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Managed Role", "This role is managed by an integration and cannot be manually assigned."),
                ephemeral=True
            )
        
        await user.add_roles(role, reason=f"Added by {interaction.user}")
        embed = ModEmbed.success("Role Added", f"Added {role.mention} to {user.mention}")
        embed.set_footer(text=f"By {interaction.user}")
        await interaction.response.send_message(embed=embed)

    @roles_group.command(name="remove", description="➖ Remove a role from a user")
    @app_commands.describe(user="The user to remove role from", role="The role to remove")
    @is_mod()
    async def remove(self, interaction: discord.Interaction, user: discord.Member, role: str):
        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Guild Only", "This command can only be used in a server."),
                ephemeral=True,
            )

        role_obj: Optional[discord.Role] = None
        role_id = self._parse_role_id(role)
        if role_id is not None:
            candidate = interaction.guild.get_role(role_id)
            if candidate and candidate in user.roles and candidate != interaction.guild.default_role:
                role_obj = candidate
        else:
            role_name = (role or "").strip().lower()
            if role_name:
                role_obj = discord.utils.find(
                    lambda r: r != interaction.guild.default_role and r.name.lower() == role_name,
                    user.roles,
                )

        if not role_obj:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Role Not Found", "Select a role the user currently has."),
                ephemeral=True,
            )

        role = role_obj
        owner_override, owner_error = await self._owner_override_for_role(interaction, role)
        if not owner_override:
            # Check if moderator can manage this role
            can_manage, error = self.can_manage_role(interaction.user, role)
            if not can_manage:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Permission Denied", error),
                    ephemeral=True,
                )

            # Check if moderator can manage target user
            can_manage_user, error = self.can_manage_target(interaction.user, user)
            if not can_manage_user:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Permission Denied", error),
                    ephemeral=True,
                )
        elif owner_error:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", owner_error),
                ephemeral=True,
            )

        if (
            interaction.guild
            and user.id == interaction.guild.owner_id
            and interaction.user.id != interaction.guild.owner_id
            and not is_bot_owner_id(interaction.user.id)
        ):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You cannot manage the server owner's roles."),
                ephemeral=True,
            )
        
        # Check if bot can manage this role
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Bot Permission Error", "I cannot manage this role as it's higher than or equal to my highest role."),
                ephemeral=True
            )
        
        # Check if user has the role
        if role not in user.roles:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Doesn't Have Role", f"{user.mention} doesn't have {role.mention}"),
                ephemeral=True
            )
        
        # Check if it's a managed/integration role
        if role.managed:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Managed Role", "This role is managed by an integration and cannot be manually removed."),
                ephemeral=True
            )
        
        await user.remove_roles(role, reason=f"Removed by {interaction.user}")
        embed = ModEmbed.success("Role Removed", f"Removed {role.mention} from {user.mention}")
        embed.set_footer(text=f"By {interaction.user}")
        await interaction.response.send_message(embed=embed)

    @remove.autocomplete("role")
    async def remove_role_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        return await self._remove_role_autocomplete(interaction, current)

    @roles_group.command(name="create", description="🆕 Create a new role")
    @app_commands.describe(name="Role name", color="Hex color (e.g., #ff0000)", hoist="Show separately in member list")
    @is_admin()
    async def create(self, interaction: discord.Interaction, name: str, 
                     color: Optional[str] = None, hoist: Optional[bool] = False):
        try:
            if color:
                color = color.replace('#', '')
                role_color = discord.Color(int(color, 16))
            else:
                role_color = discord.Color.default()
        except:
            role_color = discord.Color.default()
        
        role = await interaction.guild.create_role(
            name=name,
            color=role_color,
            hoist=hoist,
            reason=f"Created by {interaction.user}"
        )
        
        embed = ModEmbed.success("Role Created", f"Created role {role.mention}")
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Hoisted", value="Yes" if hoist else "No", inline=True)
        await interaction.response.send_message(embed=embed)

    @roles_group.command(name="delete", description="🗑️ Delete a role")
    @app_commands.describe(role="The role to delete")
    @is_admin()
    async def delete(self, interaction: discord.Interaction, role: discord.Role):
        # Check if admin can manage this role
        can_manage, error = self.can_manage_role(interaction.user, role)
        if not can_manage:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", error),
                ephemeral=True
            )
        
        # Check if bot can manage this role
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Bot Permission Error", "I cannot delete this role as it's higher than or equal to my highest role."),
                ephemeral=True
            )
        
        # Can't delete managed roles
        if role.managed:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Managed Role", "This role is managed by an integration and cannot be deleted."),
                ephemeral=True
            )
        
        # Can't delete @everyone
        if role.is_default():
            return await interaction.response.send_message(
                embed=ModEmbed.error("Cannot Delete", "You cannot delete the @everyone role."),
                ephemeral=True
            )
        
        role_name = role.name
        await role.delete(reason=f"Deleted by {interaction.user}")
        embed = ModEmbed.success("Role Deleted", f"Deleted role **{role_name}**")
        await interaction.response.send_message(embed=embed)

    @roles_group.command(name="all", description="👥 Give a role to all members")
    @app_commands.describe(role="The role to give to everyone")
    @is_admin()
    async def all(self, interaction: discord.Interaction, role: discord.Role):
        # Check if admin can manage this role
        can_manage, error = self.can_manage_role(interaction.user, role)
        if not can_manage:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", error),
                ephemeral=True
            )
        
        # Check if bot can manage this role
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Bot Permission Error", "I cannot manage this role as it's higher than or equal to my highest role."),
                ephemeral=True
            )
        
        # Can't mass assign managed roles
        if role.managed:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Managed Role", "This role is managed by an integration and cannot be manually assigned."),
                ephemeral=True
            )
        
        # Warn about dangerous roles
        if role.permissions.administrator or role.permissions.ban_members or role.permissions.kick_members:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Dangerous Role", "You cannot mass-assign roles with Administrator, Ban, or Kick permissions."),
                ephemeral=True
            )
        
        await interaction.response.defer()
        count = 0
        failed = 0
        for member in interaction.guild.members:
            if is_bot_owner_id(member.id) and not is_bot_owner_id(interaction.user.id):
                continue
            if role not in member.roles and not member.bot:
                try:
                    await member.add_roles(role, reason=f"Mass role add by {interaction.user}")
                    count += 1
                except:
                    failed += 1
        
        embed = ModEmbed.success("Role Added to All", f"Added {role.mention} to **{count}** members")
        if failed > 0:
            embed.add_field(name="Failed", value=str(failed), inline=True)
        await interaction.followup.send(embed=embed)

    @roles_group.command(name="bots", description="🤖 Give a role to all bots")
    @app_commands.describe(role="The role to give to all bots")
    @is_admin()
    async def bots(self, interaction: discord.Interaction, role: discord.Role):
        # Check if admin can manage this role
        can_manage, error = self.can_manage_role(interaction.user, role)
        if not can_manage:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", error),
                ephemeral=True
            )
        
        # Check if bot can manage this role
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Bot Permission Error", "I cannot manage this role as it's higher than or equal to my highest role."),
                ephemeral=True
            )
        
        if role.managed:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Managed Role", "This role is managed by an integration and cannot be manually assigned."),
                ephemeral=True
            )
        
        await interaction.response.defer()
        count = 0
        for member in interaction.guild.members:
            if is_bot_owner_id(member.id) and not is_bot_owner_id(interaction.user.id):
                continue
            if member.bot and role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Bot role add by {interaction.user}")
                    count += 1
                except:
                    pass
        
        embed = ModEmbed.success("Role Added to Bots", f"Added {role.mention} to **{count}** bots")
        await interaction.followup.send(embed=embed)

    @roles_group.command(name="humans", description="👤 Give a role to all humans")
    @app_commands.describe(role="The role to give to all humans")
    @is_admin()
    async def humans(self, interaction: discord.Interaction, role: discord.Role):
        # Check if admin can manage this role
        can_manage, error = self.can_manage_role(interaction.user, role)
        if not can_manage:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", error),
                ephemeral=True
            )
        
        # Check if bot can manage this role
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Bot Permission Error", "I cannot manage this role as it's higher than or equal to my highest role."),
                ephemeral=True
            )
        
        if role.managed:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Managed Role", "This role is managed by an integration and cannot be manually assigned."),
                ephemeral=True
            )
        
        # Warn about dangerous roles
        if role.permissions.administrator or role.permissions.ban_members or role.permissions.kick_members:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Dangerous Role", "You cannot mass-assign roles with Administrator, Ban, or Kick permissions."),
                ephemeral=True
            )
        
        await interaction.response.defer()
        count = 0
        for member in interaction.guild.members:
            if is_bot_owner_id(member.id) and not is_bot_owner_id(interaction.user.id):
                continue
            if not member.bot and role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Human role add by {interaction.user}")
                    count += 1
                except:
                    pass
        
        embed = ModEmbed.success("Role Added to Humans", f"Added {role.mention} to **{count}** humans")
        await interaction.followup.send(embed=embed)

    @roles_group.command(name="info", description="📋 View information about a role")
    @app_commands.describe(role="The role to view")
    async def info(self, interaction: discord.Interaction, role: discord.Role):
        embed = discord.Embed(
            title=f"Role Information - {role.name}",
            color=role.color if role.color != discord.Color.default() else Config.COLOR_INFO,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="ID", value=role.id, inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Position", value=role.position, inline=True)
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="Hoisted", value="Yes" if role.hoist else "No", inline=True)
        embed.add_field(name="Managed", value="Yes" if role.managed else "No", inline=True)
        embed.add_field(name="Members", value=len(role.members), inline=True)
        embed.add_field(
            name="Created",
            value=f"<t:{int(role.created_at.timestamp())}:R>",
            inline=True
        )
        
        # Key permissions
        perms = []
        if role.permissions.administrator:
            perms.append("⚠️ Administrator")
        if role.permissions.manage_guild:
            perms.append("Manage Server")
        if role.permissions.manage_roles:
            perms.append("Manage Roles")
        if role.permissions.manage_channels:
            perms.append("Manage Channels")
        if role.permissions.kick_members:
            perms.append("Kick Members")
        if role.permissions.ban_members:
            perms.append("Ban Members")
        if role.permissions.manage_messages:
            perms.append("Manage Messages")
        if role.permissions.mention_everyone:
            perms.append("Mention Everyone")
        
        if perms:
            embed.add_field(name="Key Permissions", value=", ".join(perms), inline=False)
        
        embed.add_field(name="Mention", value=role.mention, inline=False)
        
        # Can you manage this role?
        can_manage, _ = self.can_manage_role(interaction.user, role)
        embed.set_footer(text=f"You {'can' if can_manage else 'cannot'} manage this role")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Roles(bot))
