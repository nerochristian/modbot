"""Role management through one parameterized ``/role`` command."""

from __future__ import annotations

import asyncio
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_bot_owner_id
from utils.embeds import ModEmbed
from utils.server_setup import module_enabled
from utils.status_emojis import apply_status_emoji_overrides


RoleAction = Literal[
    "info",
    "create",
    "delete",
    "add",
    "remove",
    "addall",
    "removeall",
    "auto",
    "allowlist-add",
    "allowlist-remove",
    "allowlist-list",
]


class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def _is_admin(member: discord.Member) -> bool:
        return bool(
            is_bot_owner_id(member.id)
            or member.id == member.guild.owner_id
            or member.guild_permissions.administrator
        )

    @staticmethod
    def _can_use_role_commands(member: discord.Member) -> bool:
        return bool(
            Roles._is_admin(member)
            or member.guild_permissions.manage_roles
        )

    async def _send(
        self,
        interaction: discord.Interaction,
        embed: discord.Embed,
        *,
        ephemeral: bool = False,
    ) -> None:
        if interaction.guild is not None:
            try:
                embed = await apply_status_emoji_overrides(embed, interaction.guild)
            except Exception:
                pass
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    def _can_manage_role(
        self,
        moderator: discord.Member,
        role: discord.Role,
    ) -> tuple[bool, str]:
        guild = moderator.guild
        bot_member = guild.me
        if role.is_default():
            return False, "The everyone role cannot be managed."
        if role.managed:
            return False, "Integration-managed roles cannot be changed manually."
        if bot_member is None or not bot_member.guild_permissions.manage_roles:
            return False, "I need Manage Roles to do that."
        if role >= bot_member.top_role:
            return False, "That role is higher than or equal to my highest role."
        if not self._is_admin(moderator) and role >= moderator.top_role:
            return False, "That role is higher than or equal to your highest role."
        if role.permissions.administrator and not moderator.guild_permissions.administrator:
            return False, "Only administrators can manage an Administrator role."
        return True, ""

    async def _require_role(
        self,
        interaction: discord.Interaction,
        role: Optional[discord.Role],
    ) -> Optional[discord.Role]:
        if role is not None:
            return role
        await self._send(
            interaction,
            ModEmbed.error("Missing Parameter", "Select the `role` parameter for this action."),
            ephemeral=True,
        )
        return None

    async def _mass_update(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        *,
        remove: bool,
        reason: Optional[str],
    ) -> None:
        allowed, error = self._can_manage_role(interaction.user, role)
        if not allowed:
            return await self._send(interaction, ModEmbed.error("Permission Denied", error), ephemeral=True)
        if not remove and any(
            (
                role.permissions.administrator,
                role.permissions.manage_guild,
                role.permissions.manage_roles,
                role.permissions.ban_members,
                role.permissions.kick_members,
            )
        ) and not is_bot_owner_id(interaction.user.id):
            return await self._send(
                interaction,
                ModEmbed.error("Dangerous Role", "Only a bot owner can mass-assign that role."),
                ephemeral=True,
            )

        await interaction.response.defer()
        members = [
            member
            for member in interaction.guild.members
            if not member.bot and ((role in member.roles) if remove else (role not in member.roles))
        ]
        succeeded = 0
        failed = 0
        audit_reason = reason or f"/role {'removeall' if remove else 'addall'} by {interaction.user}"
        for member in members:
            try:
                if remove:
                    await member.remove_roles(role, reason=audit_reason)
                else:
                    await member.add_roles(role, reason=audit_reason)
                succeeded += 1
                await asyncio.sleep(0.25)
            except discord.HTTPException:
                failed += 1

        verb = "Removed from" if remove else "Added to"
        embed = ModEmbed.success("Role Update Complete", f"{verb} **{succeeded}** members: {role.mention}")
        if failed:
            embed.add_field(name="Failed", value=str(failed))
        await self._send(interaction, embed)

    @app_commands.command(name="role", description="Manage roles with one command")
    @app_commands.describe(
        action="What to do; this is the only required parameter",
        role="Existing role used by the selected action",
        user="Member used by add or remove",
        name="New role name used by create",
        color="Hex color for create, such as #FF0000",
        hoist="Show a created role separately",
        mentionable="Allow everyone to mention a created role",
        position="Position for a newly created role",
        reason="Audit-log reason",
    )
    @app_commands.guild_only()
    async def role_command(
        self,
        interaction: discord.Interaction,
        action: RoleAction,
        role: Optional[discord.Role] = None,
        user: Optional[discord.Member] = None,
        name: Optional[str] = None,
        color: Optional[str] = None,
        hoist: Optional[bool] = None,
        mentionable: Optional[bool] = None,
        position: Optional[app_commands.Range[int, 1, 250]] = None,
        reason: Optional[str] = None,
    ) -> None:
        guild = interaction.guild
        actor = interaction.user
        if guild is None or not isinstance(actor, discord.Member):
            return await self._send(interaction, ModEmbed.error("Server Only", "Use this in a server."), ephemeral=True)

        if action == "info":
            target_role = await self._require_role(interaction, role)
            if target_role is None:
                return
            embed = discord.Embed(title=f"Role: {target_role.name}", color=target_role.color)
            embed.add_field(name="ID", value=str(target_role.id))
            embed.add_field(name="Members", value=str(len(target_role.members)))
            embed.add_field(name="Position", value=str(target_role.position))
            embed.add_field(name="Created", value=f"<t:{int(target_role.created_at.timestamp())}:R>")
            permissions = [label.replace("_", " ").title() for label, enabled in target_role.permissions if enabled]
            embed.add_field(name="Permissions", value=", ".join(permissions[:15]) or "None", inline=False)
            return await self._send(interaction, embed)

        if not self._can_use_role_commands(actor):
            return await self._send(
                interaction,
                ModEmbed.error("Permission Denied", "You need Manage Roles to use this action."),
                ephemeral=True,
            )

        admin_actions = {
            "create", "delete", "addall", "removeall", "auto",
            "allowlist-add", "allowlist-remove", "allowlist-list",
        }
        if action in admin_actions and not self._is_admin(actor):
            return await self._send(
                interaction,
                ModEmbed.error("Permission Denied", "This action requires Administrator."),
                ephemeral=True,
            )

        if action == "create":
            if not name or not name.strip():
                return await self._send(
                    interaction,
                    ModEmbed.error("Missing Parameter", "Provide `name` when action is `create`."),
                    ephemeral=True,
                )
            role_color = discord.Color.default()
            if color:
                try:
                    role_color = discord.Color(int(color.strip().removeprefix("#"), 16))
                except ValueError:
                    return await self._send(
                        interaction,
                        ModEmbed.error("Invalid Color", "Use a six-digit hex color such as `#FF0000`."),
                        ephemeral=True,
                    )
            await interaction.response.defer()
            try:
                created = await guild.create_role(
                    name=name.strip(),
                    color=role_color,
                    hoist=bool(hoist),
                    mentionable=bool(mentionable),
                    reason=reason or f"Created with /role by {actor}",
                )
                if position is not None:
                    try:
                        await created.edit(position=position, reason=reason)
                    except discord.HTTPException:
                        pass
            except discord.HTTPException as exc:
                return await self._send(interaction, ModEmbed.error("Role Creation Failed", str(exc)), ephemeral=True)
            return await self._send(interaction, ModEmbed.success("Role Created", created.mention))

        if action == "allowlist-list":
            settings = await self.bot.db.get_settings(guild.id)
            role_ids = settings.get("owner_role_allowlist", [])
            roles = [guild.get_role(int(role_id)) for role_id in role_ids if str(role_id).isdigit()]
            mentions = [item.mention for item in roles if item is not None]
            return await self._send(
                interaction,
                ModEmbed.info("Allowlisted Roles", ", ".join(mentions) or "No roles are allowlisted."),
                ephemeral=True,
            )

        target_role = await self._require_role(interaction, role)
        if target_role is None:
            return

        if action in {"allowlist-add", "allowlist-remove"}:
            if target_role.permissions.administrator and action == "allowlist-add":
                return await self._send(
                    interaction,
                    ModEmbed.error("Not Allowed", "Administrator roles cannot be allowlisted."),
                    ephemeral=True,
                )
            settings = await self.bot.db.get_settings(guild.id)
            allowlist = settings.get("owner_role_allowlist", [])
            allowlist = list(allowlist) if isinstance(allowlist, list) else []
            if action == "allowlist-add" and target_role.id not in allowlist:
                allowlist.append(target_role.id)
            if action == "allowlist-remove" and target_role.id in allowlist:
                allowlist.remove(target_role.id)
            settings["owner_role_allowlist"] = allowlist
            await self.bot.db.update_settings(guild.id, settings)
            verb = "added to" if action == "allowlist-add" else "removed from"
            return await self._send(
                interaction,
                ModEmbed.success("Allowlist Updated", f"{target_role.mention} was {verb} the allowlist."),
                ephemeral=True,
            )

        if action == "auto":
            allowed, error = self._can_manage_role(actor, target_role)
            if not allowed:
                return await self._send(interaction, ModEmbed.error("Permission Denied", error), ephemeral=True)
            settings = await self.bot.db.get_settings(guild.id)
            settings["auto_role"] = target_role.id
            await self.bot.db.update_settings(guild.id, settings)
            note = ""
            if module_enabled(settings, "verification", False):
                note = " Verification is enabled, so new members receive the unverified role first."
            return await self._send(
                interaction,
                ModEmbed.success("Auto Role Updated", f"New members will receive {target_role.mention}.{note}"),
                ephemeral=True,
            )

        if action == "delete":
            allowed, error = self._can_manage_role(actor, target_role)
            if not allowed:
                return await self._send(interaction, ModEmbed.error("Permission Denied", error), ephemeral=True)
            role_name = target_role.name
            try:
                await target_role.delete(reason=reason or f"Deleted with /role by {actor}")
            except discord.HTTPException as exc:
                return await self._send(interaction, ModEmbed.error("Role Deletion Failed", str(exc)), ephemeral=True)
            return await self._send(interaction, ModEmbed.success("Role Deleted", f"Deleted **{role_name}**."))

        if action in {"addall", "removeall"}:
            return await self._mass_update(
                interaction,
                target_role,
                remove=action == "removeall",
                reason=reason,
            )

        if user is None:
            return await self._send(
                interaction,
                ModEmbed.error("Missing Parameter", f"Select `user` when action is `{action}`."),
                ephemeral=True,
            )
        allowed, error = self._can_manage_role(actor, target_role)
        if not allowed:
            return await self._send(interaction, ModEmbed.error("Permission Denied", error), ephemeral=True)
        try:
            if action == "add":
                if target_role in user.roles:
                    return await self._send(interaction, ModEmbed.info("No Change", "That member already has the role."), ephemeral=True)
                await user.add_roles(target_role, reason=reason or f"Added with /role by {actor}")
                message = f"Added {target_role.mention} to {user.mention}."
            elif action == "remove":
                if target_role not in user.roles:
                    return await self._send(interaction, ModEmbed.info("No Change", "That member does not have the role."), ephemeral=True)
                await user.remove_roles(target_role, reason=reason or f"Removed with /role by {actor}")
                message = f"Removed {target_role.mention} from {user.mention}."
            else:
                return await self._send(interaction, ModEmbed.error("Invalid Action", "Select a valid action."), ephemeral=True)
        except discord.HTTPException as exc:
            return await self._send(interaction, ModEmbed.error("Role Update Failed", str(exc)), ephemeral=True)
        await self._send(interaction, ModEmbed.success("Role Updated", message))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return
        try:
            settings = await self.bot.db.get_settings(member.guild.id)
            if module_enabled(settings, "verification", False):
                return
            role = member.guild.get_role(int(settings.get("auto_role", 0) or 0))
            bot_member = member.guild.me
            if role and bot_member and bot_member.guild_permissions.manage_roles and role < bot_member.top_role:
                await member.add_roles(role, reason="Automatic join role")
        except (TypeError, ValueError, discord.HTTPException):
            return

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if after.bot or before.roles == after.roles:
            return
        try:
            settings = await self.bot.db.get_settings(after.guild.id)
            staff_role = after.guild.get_role(int(settings.get("staff_role", 0) or 0))
            configured = {
                int(settings[key])
                for key in (
                    "owner_role", "manager_role", "admin_role", "supervisor_role",
                    "senior_mod_role", "mod_role", "trial_mod_role",
                )
                if str(settings.get(key, "")).isdigit()
            }
            added = {role.id for role in after.roles if role not in before.roles}
            bot_member = after.guild.me
            if (
                staff_role
                and staff_role not in after.roles
                and added & configured
                and bot_member
                and bot_member.guild_permissions.manage_roles
                and staff_role < bot_member.top_role
            ):
                await after.add_roles(staff_role, reason="Staff role linked to moderation role")
        except (TypeError, ValueError, discord.HTTPException):
            return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Roles(bot))
