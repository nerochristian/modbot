"""
Role Management Commands (WITH SECURITY FIXES)
Refactored to use Subcommands (/role create, /role delete, etc.)
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
        self.role_group.add_command(self.allowlist_group)

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
            for key in ["owner_role", "manager_role", "admin_role", "supervisor_role", "senior_mod_role", "mod_role", "trial_mod_role"]:
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

    # Helper methods
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

    async def _owner_override_for_role(self, interaction: discord.Interaction, role: discord.Role) -> tuple[bool, str]:
        if not is_bot_owner_id(interaction.user.id):
            return False, ""
        return True, ""

    def can_manage_role(self, moderator: discord.Member, target_role: discord.Role) -> tuple[bool, str]:
        if is_bot_owner_id(moderator.id) or moderator.id == moderator.guild.owner_id:
            return True, ""
        if target_role >= moderator.top_role:
            return False, "You cannot manage this role as it's higher than or equal to your highest role."
        if target_role.permissions.administrator and not moderator.guild_permissions.administrator:
            return False, "You cannot manage roles with Administrator permission."
        dangerous_perms = ['ban_members', 'kick_members', 'manage_guild', 'manage_roles', 'manage_channels']
        for perm in dangerous_perms:
            if getattr(target_role.permissions, perm) and not getattr(moderator.guild_permissions, perm):
                return False, f"You cannot manage roles with `{perm.replace('_', ' ').title()}` permission."
        return True, ""

    # ==================== /role GROUP ====================
    role_group = app_commands.Group(name="role", description="🎭 Manage server roles")

    @role_group.command(name="create", description="✨ Create a new role with detailed options")
    @app_commands.describe(
        name="Name of the new role",
        color="Hex color (e.g. #FF0000) or name (e.g. Red)",
        hoist="Display role separately in online list?",
        mentionable="Can anyone mention this role?",
        position="Position (1 is lowest, higher is higher up)", 
        reason="Audit log reason"
    )
    @is_admin()
    async def create(
        self,
        interaction: discord.Interaction,
        name: str,
        color: Optional[str] = None,
        hoist: bool = False,
        mentionable: bool = False,
        position: Optional[int] = None,
        reason: Optional[str] = None
    ):
        if not interaction.guild:
            return await interaction.response.send_message(embed=ModEmbed.error("Error", "Guild only."), ephemeral=True)
        
        await interaction.response.defer()

        # Parse color
        role_color = discord.Color.default()
        if color:
            try:
                color = color.strip().replace("#", "")
                role_color = discord.Color(int(color, 16))
            except:
                pass # Default

        try:
            role = await interaction.guild.create_role(
                name=name,
                color=role_color,
                hoist=hoist,
                mentionable=mentionable,
                reason=f"{reason if reason else 'Created via /role create'} by {interaction.user}"
            )

            # Attempt position move (best effort)
            if position is not None and position > 0:
                try:
                    await role.edit(position=position)
                except:
                    pass # Often fails due to hierarchy

            embed = ModEmbed.success("Role Created", f"Successfully created {role.mention}")
            embed.add_field(name="Properties", value=f"Color: {role.color}\nHoist: {role.hoist}\nMentionable: {role.mentionable}")
            await interaction.followup.send(embed=embed)

        except discord.Forbidden:
             await interaction.followup.send(embed=ModEmbed.error("Permission Denied", "I do not have permission to create roles."))
        except Exception as e:
             await interaction.followup.send(embed=ModEmbed.error("Error", str(e)))

    @role_group.command(name="delete", description="🗑️ Delete an existing role")
    @app_commands.describe(role="The role to delete", reason="Audit log reason")
    @is_admin()
    async def delete(self, interaction: discord.Interaction, role: discord.Role, reason: Optional[str] = None):
        if not interaction.guild: return
        
        can_manage, error = self.can_manage_role(interaction.user, role)
        if not can_manage:
             return await interaction.response.send_message(embed=ModEmbed.error("Permission Denied", error), ephemeral=True)

        # Safety checks
        if role.managed:
             return await interaction.response.send_message(embed=ModEmbed.error("Error", "Cannot delete managed roles."), ephemeral=True)
        if role >= interaction.guild.me.top_role:
             return await interaction.response.send_message(embed=ModEmbed.error("Error", "Role is higher than me."), ephemeral=True)

        await interaction.response.defer()
        try:
            name = role.name
            await role.delete(reason=f"{reason if reason else 'Deleted via /role delete'} by {interaction.user}")
            await interaction.followup.send(embed=ModEmbed.success("Role Deleted", f"Deleted role **{name}**"))
        except Exception as e:
            await interaction.followup.send(embed=ModEmbed.error("Error", str(e)))

    @role_group.command(name="add", description="➕ Add a role to a user")
    @is_mod()
    async def add(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        can_manage, error = self.can_manage_role(interaction.user, role)
        if not can_manage:
             return await interaction.response.send_message(embed=ModEmbed.error("Permission Denied", error), ephemeral=True)
        
        if role in user.roles:
            return await interaction.response.send_message(embed=ModEmbed.error("Error", "User already has this role."), ephemeral=True)

        try:
            await user.add_roles(role, reason=f"Added by {interaction.user}")
            await interaction.response.send_message(embed=ModEmbed.success("Role Added", f"Added {role.mention} to {user.mention}"))
        except Exception as e:
            await interaction.response.send_message(embed=ModEmbed.error("Error", str(e)), ephemeral=True)

    @role_group.command(name="remove", description="➖ Remove a role from a user")
    @is_mod()
    async def remove(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        can_manage, error = self.can_manage_role(interaction.user, role)
        if not can_manage:
             return await interaction.response.send_message(embed=ModEmbed.error("Permission Denied", error), ephemeral=True)

        if role not in user.roles:
            return await interaction.response.send_message(embed=ModEmbed.error("Error", "User does not have this role."), ephemeral=True)

        try:
            await user.remove_roles(role, reason=f"Removed by {interaction.user}")
            await interaction.response.send_message(embed=ModEmbed.success("Role Removed", f"Removed {role.mention} from {user.mention}"))
        except Exception as e:
            await interaction.response.send_message(embed=ModEmbed.error("Error", str(e)), ephemeral=True)

    @role_group.command(name="info", description="ℹ️ Get detailed role info")
    async def info(self, interaction: discord.Interaction, role: discord.Role):
        embed = discord.Embed(title=f"Role: {role.name}", color=role.color)
        embed.add_field(name="ID", value=role.id)
        embed.add_field(name="Members", value=str(len(role.members)))
        embed.add_field(name="Created", value=f"<t:{int(role.created_at.timestamp())}:R>")
        embed.add_field(name="Position", value=str(role.position))
        embed.add_field(name="Hoisted", value=str(role.hoist))
        embed.add_field(name="Mentionable", value=str(role.mentionable))
        embed.add_field(name="Managed", value=str(role.managed))
        
        perms = [p[0].replace('_', ' ').title() for p in role.permissions if p[1]]
        if "Administrator" in perms: perms = ["Administrator"]
        embed.add_field(name="Key Permissions", value=", ".join(perms[:10]) or "None", inline=False)
        
        await interaction.response.send_message(embed=embed)

    # ==================== ALLOWLIST SUBGROUP ====================
    allowlist_group = app_commands.Group(name="allowlist", description="🔐 Configure roles bot owners may assign")

    @allowlist_group.command(name="add", description="Allow a role to be assigned by owners")
    @app_commands.describe(role="Role to allowlist")
    async def allowlist_add(self, interaction: discord.Interaction, role: discord.Role):
        # Check server admin permission
        if not _is_server_admin_check(interaction):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need to be a server admin to use this command."),
                ephemeral=True
            )
        
        if role.permissions.administrator:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Allowed", "Administrator roles cannot be allowlisted."),
                ephemeral=True,
            )
        settings = await self.bot.db.get_settings(interaction.guild_id)
        allowlist = settings.get("owner_role_allowlist", [])
        if not isinstance(allowlist, list): allowlist = []
        if role.id not in allowlist:
            allowlist.append(role.id)
            settings["owner_role_allowlist"] = allowlist
            await self.bot.db.update_settings(interaction.guild_id, settings)
        await interaction.response.send_message(
            embed=ModEmbed.success("Allowlisted", f"Bot owners can now assign {role.mention}."),
            ephemeral=True,
        )

    @allowlist_group.command(name="remove", description="Remove a role from the allowlist")
    @app_commands.describe(role="Role to remove")
    async def allowlist_remove(self, interaction: discord.Interaction, role: discord.Role):
        # Check server admin permission
        if not _is_server_admin_check(interaction):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need to be a server admin to use this command."),
                ephemeral=True
            )
            
        settings = await self.bot.db.get_settings(interaction.guild_id)
        allowlist = settings.get("owner_role_allowlist", [])
        if role.id in allowlist:
            allowlist.remove(role.id)
            settings["owner_role_allowlist"] = allowlist
            await self.bot.db.update_settings(interaction.guild_id, settings)
        await interaction.response.send_message(
            embed=ModEmbed.success("Removed", f"{role.mention} removed from allowlist."),
            ephemeral=True,
        )

    @allowlist_group.command(name="list", description="List allowlisted roles")
    async def allowlist_list(self, interaction: discord.Interaction):
        # Check server admin permission (optional for list? keeping it consistent)
        if not _is_server_admin_check(interaction):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need to be a server admin to use this command."),
                ephemeral=True
            )

        settings = await self.bot.db.get_settings(interaction.guild_id)
        allowlist = settings.get("owner_role_allowlist", [])
        if not allowlist:
            return await interaction.response.send_message(embed=ModEmbed.info("Allowlist", "No roles allowlisted."), ephemeral=True)
        roles = [interaction.guild.get_role(rid) for rid in allowlist]
        roles_str = ", ".join([r.mention for r in roles if r])
        await interaction.response.send_message(embed=ModEmbed.info("Allowlisted Roles", roles_str), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Roles(bot))
