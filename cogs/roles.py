"""
Role Management Commands (WITH SECURITY FIXES)
Consolidated into single /roles command with action parameter
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional, Literal
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

    # ==================== CONSOLIDATED /roles COMMAND ====================
    
    @app_commands.command(name="roles", description="🎭 Role management commands")
    @app_commands.describe(
        action="The action to perform",
        user="Target user (for add/remove)",
        role="Target role",
        role2="Second role (optional)",
        role3="Third role (optional)",
        role4="Fourth role (optional)",
        name="Role name (for create)",
        color="Hex color e.g. #ff0000 (for create)",
        hoist="Show separately in member list (for create)",
    )
    @is_mod()
    async def roles(
        self,
        interaction: discord.Interaction,
        action: Literal["add", "remove", "create", "delete", "all", "bots", "humans", "info"],
        role: Optional[discord.Role] = None,
        role2: Optional[discord.Role] = None,
        role3: Optional[discord.Role] = None,
        role4: Optional[discord.Role] = None,
        user: Optional[discord.Member] = None,
        name: Optional[str] = None,
        color: Optional[str] = None,
        hoist: Optional[bool] = False,
    ):
        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Guild Only", "This command can only be used in a server."),
                ephemeral=True
            )

        # Collect all roles provided
        roles_list = [r for r in [role, role2, role3, role4] if r is not None]
        primary_role = roles_list[0] if roles_list else None

        # Route to appropriate handler
        if action == "add":
            await self._role_add(interaction, user, roles_list)
        elif action == "remove":
            await self._role_remove(interaction, user, roles_list)
        elif action == "create":
            await self._role_create(interaction, name, color, hoist)
        elif action == "delete":
            await self._role_delete(interaction, primary_role)
        elif action == "all":
            await self._role_all(interaction, primary_role)
        elif action == "bots":
            await self._role_bots(interaction, primary_role)
        elif action == "humans":
            await self._role_humans(interaction, primary_role)
        elif action == "info":
            await self._role_info(interaction, primary_role)

    async def _role_add(self, interaction: discord.Interaction, user: Optional[discord.Member], roles: list[discord.Role]):
        if not user or not roles:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Arguments", "Please specify `user` and at least one `role`."),
                ephemeral=True
            )

        added_roles = []
        failed_roles = []
        
        await interaction.response.defer()

        for role in roles:
            # Bot-owner override for safe role assignment
            owner_override, owner_error = await self._owner_override_for_role(interaction, role)
            
            can_proceed = False
            if owner_override:
                can_proceed = True
            else:
                can_manage, error = self.can_manage_role(interaction.user, role)
                can_manage_user, error2 = self.can_manage_target(interaction.user, user)
                if can_manage and can_manage_user:
                    can_proceed = True
            
            if not can_proceed:
                failed_roles.append(f"{role.mention} (No Permission)")
                continue

            if (
                interaction.guild
                and user.id == interaction.guild.owner_id
                and interaction.user.id != interaction.guild.owner_id
                and not is_bot_owner_id(interaction.user.id)
            ):
                failed_roles.append(f"{role.mention} (Server Owner Protected)")
                continue
            
            if role >= interaction.guild.me.top_role:
                failed_roles.append(f"{role.mention} (Bot Hierarchy)")
                continue
            
            if role in user.roles:
                failed_roles.append(f"{role.mention} (Already Has)")
                continue
            
            if role.managed:
                failed_roles.append(f"{role.mention} (Managed Role)")
                continue
            
            try:
                await user.add_roles(role, reason=f"Added by {interaction.user}")
                added_roles.append(role.mention)
            except Exception as e:
                failed_roles.append(f"{role.mention} (Error: {e})")

        if added_roles:
            embed = ModEmbed.success("Roles Added", f"Added {', '.join(added_roles)} to {user.mention}")
            if failed_roles:
                embed.add_field(name="Failed to Add", value="\n".join(failed_roles), inline=False)
            embed.set_footer(text=f"By {interaction.user}")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                embed=ModEmbed.error("Failed to Add Roles", "\n".join(failed_roles)),
                ephemeral=True
            )

    async def _role_remove(self, interaction: discord.Interaction, user: Optional[discord.Member], roles: list[discord.Role]):
        if not user or not roles:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Arguments", "Please specify `user` and at least one `role`."),
                ephemeral=True
            )

        removed_roles = []
        failed_roles = []
        
        await interaction.response.defer()

        for role in roles:
            owner_override, owner_error = await self._owner_override_for_role(interaction, role)
            
            can_proceed = False
            if owner_override:
                can_proceed = True
            else:
                can_manage, error = self.can_manage_role(interaction.user, role)
                can_manage_user, error2 = self.can_manage_target(interaction.user, user)
                if can_manage and can_manage_user:
                    can_proceed = True

            if not can_proceed:
                failed_roles.append(f"{role.mention} (No Permission)")
                continue

            if (
                interaction.guild
                and user.id == interaction.guild.owner_id
                and interaction.user.id != interaction.guild.owner_id
                and not is_bot_owner_id(interaction.user.id)
            ):
                failed_roles.append(f"{role.mention} (Server Owner Protected)")
                continue
            
            if role >= interaction.guild.me.top_role:
                failed_roles.append(f"{role.mention} (Bot Hierarchy)")
                continue
            
            if role not in user.roles:
                failed_roles.append(f"{role.mention} (User Doesn't Have)")
                continue
            
            if role.managed:
                failed_roles.append(f"{role.mention} (Managed Role)")
                continue
            
            try:
                await user.remove_roles(role, reason=f"Removed by {interaction.user}")
                removed_roles.append(role.mention)
            except Exception:
                failed_roles.append(f"{role.mention} (Error)")

        if removed_roles:
            embed = ModEmbed.success("Roles Removed", f"Removed {', '.join(removed_roles)} from {user.mention}")
            if failed_roles:
                embed.add_field(name="Failed to Remove", value="\n".join(failed_roles), inline=False)
            embed.set_footer(text=f"By {interaction.user}")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                embed=ModEmbed.error("Failed to Remove Roles", "\n".join(failed_roles)),
                ephemeral=True
            )

    async def _role_create(self, interaction: discord.Interaction, name: Optional[str], color: Optional[str], hoist: Optional[bool]):
        # Check admin permission
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need administrator permissions for this action."),
                ephemeral=True
            )

        if not name:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `name` for the role."),
                ephemeral=True
            )

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
            hoist=hoist or False,
            reason=f"Created by {interaction.user}"
        )
        
        embed = ModEmbed.success("Role Created", f"Created role {role.mention}")
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Hoisted", value="Yes" if hoist else "No", inline=True)
        await interaction.response.send_message(embed=embed)

    async def _role_delete(self, interaction: discord.Interaction, role: Optional[discord.Role]):
        # Check admin permission
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need administrator permissions for this action."),
                ephemeral=True
            )

        if not role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `role` to delete."),
                ephemeral=True
            )

        can_manage, error = self.can_manage_role(interaction.user, role)
        if not can_manage:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", error),
                ephemeral=True
            )
        
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Bot Permission Error", "I cannot delete this role as it's higher than or equal to my highest role."),
                ephemeral=True
            )
        
        if role.managed:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Managed Role", "This role is managed by an integration and cannot be deleted."),
                ephemeral=True
            )
        
        if role.is_default():
            return await interaction.response.send_message(
                embed=ModEmbed.error("Cannot Delete", "You cannot delete the @everyone role."),
                ephemeral=True
            )
        
        role_name = role.name
        await role.delete(reason=f"Deleted by {interaction.user}")
        embed = ModEmbed.success("Role Deleted", f"Deleted role **{role_name}**")
        await interaction.response.send_message(embed=embed)

    async def _role_all(self, interaction: discord.Interaction, role: Optional[discord.Role]):
        # Check admin permission
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need administrator permissions for this action."),
                ephemeral=True
            )

        if not role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `role` to give to everyone."),
                ephemeral=True
            )

        can_manage, error = self.can_manage_role(interaction.user, role)
        if not can_manage:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", error),
                ephemeral=True
            )
        
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

    async def _role_bots(self, interaction: discord.Interaction, role: Optional[discord.Role]):
        # Check admin permission
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need administrator permissions for this action."),
                ephemeral=True
            )

        if not role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `role` to give to all bots."),
                ephemeral=True
            )

        can_manage, error = self.can_manage_role(interaction.user, role)
        if not can_manage:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", error),
                ephemeral=True
            )
        
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

    async def _role_humans(self, interaction: discord.Interaction, role: Optional[discord.Role]):
        # Check admin permission
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need administrator permissions for this action."),
                ephemeral=True
            )

        if not role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `role` to give to all humans."),
                ephemeral=True
            )

        can_manage, error = self.can_manage_role(interaction.user, role)
        if not can_manage:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", error),
                ephemeral=True
            )
        
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

    async def _role_info(self, interaction: discord.Interaction, role: Optional[discord.Role]):
        if not role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `role` to view."),
                ephemeral=True
            )

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
        
        can_manage, _ = self.can_manage_role(interaction.user, role)
        embed.set_footer(text=f"You {'can' if can_manage else 'cannot'} manage this role")
        
        await interaction.response.send_message(embed=embed)

    # ==================== CONSOLIDATED /ownerallow COMMAND ====================
    
    @app_commands.command(name="ownerallow", description="🔐 Configure roles bot owners may assign")
    @app_commands.describe(
        action="The action to perform",
        role="Target role (for add/remove)",
        enabled="Enable or disable (for manage_others)",
    )
    async def ownerallow(
        self,
        interaction: discord.Interaction,
        action: Literal["add", "remove", "list", "manage_others"],
        role: Optional[discord.Role] = None,
        enabled: Optional[bool] = None,
    ):
        # Check server admin permission
        if not _is_server_admin_check(interaction):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need to be a server admin to use this command."),
                ephemeral=True
            )

        if action == "add":
            await self._ownerallow_add(interaction, role)
        elif action == "remove":
            await self._ownerallow_remove(interaction, role)
        elif action == "list":
            await self._ownerallow_list(interaction)
        elif action == "manage_others":
            await self._ownerallow_manage_others(interaction, enabled)

    async def _ownerallow_add(self, interaction: discord.Interaction, role: Optional[discord.Role]):
        if not role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `role` to allowlist."),
                ephemeral=True
            )

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

    async def _ownerallow_remove(self, interaction: discord.Interaction, role: Optional[discord.Role]):
        if not role:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `role` to remove from allowlist."),
                ephemeral=True
            )

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

    async def _ownerallow_list(self, interaction: discord.Interaction):
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
                role = interaction.guild.get_role(int(rid))
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

    async def _ownerallow_manage_others(self, interaction: discord.Interaction, enabled: Optional[bool]):
        if enabled is None:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify `enabled: True` or `enabled: False`."),
                ephemeral=True
            )

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


async def setup(bot):
    await bot.add_cog(Roles(bot))
