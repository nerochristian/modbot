"""
Voice Moderation Commands
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from typing import Optional
from utils.embeds import ModEmbed
from utils.checks import is_mod, is_bot_owner_id
from config import Config

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="vcmute", description="🔇 Server mute a user in voice")
    @app_commands.describe(user="The user to mute", reason="Reason for mute")
    @is_mod()
    async def vcmute(self, interaction: discord.Interaction, user: discord.Member, 
                     reason: Optional[str] = "No reason provided"):
        if not user.voice:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )

        if is_bot_owner_id(user.id) and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You cannot voice-mute the bot owner."),
                ephemeral=True,
            )
        
        await user.edit(mute=True, reason=f"{interaction.user}:  {reason}")
        
        embed = ModEmbed.success("Voice Muted", f"{user. mention} has been server muted.\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="vcunmute", description="🔊 Server unmute a user in voice")
    @app_commands.describe(user="The user to unmute")
    @is_mod()
    async def vcunmute(self, interaction: discord.Interaction, user: discord.Member):
        if not user.voice:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )

        if is_bot_owner_id(user.id) and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You cannot voice-unmute the bot owner."),
                ephemeral=True,
            )
        
        await user. edit(mute=False, reason=f"Unmuted by {interaction.user}")
        
        embed = ModEmbed.success("Voice Unmuted", f"{user.mention} has been server unmuted.")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="vcdeafen", description="🔇 Server deafen a user in voice")
    @app_commands.describe(user="The user to deafen", reason="Reason for deafen")
    @is_mod()
    async def vcdeafen(self, interaction: discord. Interaction, user: discord.Member,
                       reason: Optional[str] = "No reason provided"):
        if not user.voice:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )

        if is_bot_owner_id(user.id) and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You cannot deafen the bot owner."),
                ephemeral=True,
            )
        
        await user. edit(deafen=True, reason=f"{interaction.user}:  {reason}")
        
        embed = ModEmbed.success("Voice Deafened", f"{user.mention} has been server deafened.\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="vcundeafen", description="🔊 Server undeafen a user in voice")
    @app_commands.describe(user="The user to undeafen")
    @is_mod()
    async def vcundeafen(self, interaction: discord.Interaction, user: discord.Member):
        if not user.voice:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )

        if is_bot_owner_id(user.id) and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You cannot undeafen the bot owner."),
                ephemeral=True,
            )
        
        await user. edit(deafen=False, reason=f"Undeafened by {interaction.user}")
        
        embed = ModEmbed.success("Voice Undeafened", f"{user. mention} has been server undeafened.")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="vckick", description="👢 Disconnect a user from voice")
    @app_commands.describe(user="The user to disconnect", reason="Reason for disconnect")
    @is_mod()
    async def vckick(self, interaction: discord.Interaction, user: discord. Member,
                     reason: Optional[str] = "No reason provided"):
        if not user.voice:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel. "),
                ephemeral=True
            )

        if is_bot_owner_id(user.id) and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You cannot disconnect the bot owner from voice."),
                ephemeral=True,
            )
        
        channel_name = user.voice.channel. name
        await user.move_to(None, reason=f"{interaction.user}:  {reason}")
        
        embed = ModEmbed.success("Disconnected from Voice", 
                                 f"{user.mention} has been disconnected from **{channel_name}**.\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="vcmove", description="🔀 Move a user to another voice channel")
    @app_commands.describe(user="The user to move", channel="The channel to move them to")
    @is_mod()
    async def vcmove(self, interaction: discord.Interaction, user: discord. Member, 
                     channel: discord.VoiceChannel):
        if not user.voice:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )

        if is_bot_owner_id(user.id) and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You cannot move the bot owner."),
                ephemeral=True,
            )
        
        old_channel = user.voice.channel. name
        await user.move_to(channel, reason=f"Moved by {interaction.user}")
        
        embed = ModEmbed.success("User Moved", 
                                 f"{user. mention} has been moved from **{old_channel}** to **{channel.name}**")
        await interaction.response.send_message(embed=embed)
    
    @app_commands. command(name="vcmoveall", description="🔀 Move all users from one voice channel to another")
    @app_commands.describe(from_channel="The channel to move from", to_channel="The channel to move to")
    @is_mod()
    async def vcmoveall(self, interaction: discord.Interaction, from_channel: discord.VoiceChannel,
                        to_channel: discord. VoiceChannel):
        if not from_channel.members:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Empty Channel", f"{from_channel.mention} has no members."),
                ephemeral=True
            )
        
        await interaction.response.defer()
        
        count = 0
        for member in from_channel.members:
            if is_bot_owner_id(member.id) and not is_bot_owner_id(interaction.user.id):
                continue
            try:
                await member.move_to(to_channel, reason=f"Mass move by {interaction.user}")
                count += 1
            except:
                pass
        
        embed = ModEmbed.success("Users Moved", 
                                 f"Moved **{count}** users from {from_channel.mention} to {to_channel.mention}")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Voice(bot))
