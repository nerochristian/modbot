import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional

from utils.embeds import ModEmbed, Colors
from utils.checks import is_mod, is_bot_owner_id

class WarningCommands:
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

    # Commands
    @commands.command(name="warn", description="⚠️ Warn a user")
    @is_mod()
    async def mod_warn(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        if is_bot_owner_id(user.id) and not is_bot_owner_id(ctx.author.id):
            return await self._respond(ctx, embed=ModEmbed.error("Permission Denied", "You cannot warn the bot owner."), ephemeral=True)
        await self._warn_logic(ctx, user, reason)

    # Slash command - registered dynamically in __init__.py
    async def warn_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        if is_bot_owner_id(user.id) and not is_bot_owner_id(interaction.user.id):
             return await self._respond(interaction, embed=ModEmbed.error("Permission Denied", "You cannot warn the bot owner."), ephemeral=True)
        await self._warn_logic(interaction, user, reason)

    @commands.command(name="warnings", description="⚠️ View warnings for a user")
    @is_mod()
    async def mod_warnings(self, ctx: commands.Context, user: discord.Member):
        await self._warnings_logic(ctx, user)

    # Slash command - registered dynamically in __init__.py
    async def warnings_slash(self, interaction: discord.Interaction, user: discord.Member):
        await self._warnings_logic(interaction, user)

    @commands.command(name="delwarn", description="🗑️ Delete a warning")
    @is_mod()
    async def mod_delwarn(self, ctx: commands.Context, warning_id: int):
        await self._delwarn_logic(ctx, warning_id)

    # Slash command - registered dynamically in __init__.py
    async def delwarn_slash(self, interaction: discord.Interaction, warning_id: int):
        await self._delwarn_logic(interaction, warning_id)

    @commands.command(name="clearwarnings", description="🧹 Clear all warnings for a user")
    @is_mod()
    async def mod_clearwarnings(self, ctx: commands.Context, user: discord.Member, *, reason: str = "Cleared by moderator"):
        await self._clearwarnings_logic(ctx, user, reason)

    # Slash command - registered dynamically in __init__.py
    async def clearwarnings_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Cleared by moderator"):
        await self._clearwarnings_logic(interaction, user, reason)
