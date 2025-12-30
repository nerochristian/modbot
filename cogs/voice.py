"""
Voice Moderation Commands
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from typing import Optional, Literal
from utils.embeds import ModEmbed
from utils.checks import is_mod, is_admin, is_bot_owner_id
from config import Config


class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    vc = app_commands.Group(name="vc", description="🎤 Voice channel moderation commands")
    
    @vc.command(name="mute", description="🔇 Server mute a user in voice")
    @app_commands.describe(user="The user to mute", reason="Reason for mute")
    @is_mod()
    async def mute(self, interaction: discord.Interaction, user: discord.Member, 
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
        
        await user.edit(mute=True, reason=f"{interaction.user}: {reason}")
        
        embed = ModEmbed.success("Voice Muted", f"{user.mention} has been server muted.\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)
    
    @vc.command(name="unmute", description="🔊 Server unmute a user in voice")
    @app_commands.describe(user="The user to unmute")
    @is_mod()
    async def unmute(self, interaction: discord.Interaction, user: discord.Member):
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
        
        await user.edit(mute=False, reason=f"Unmuted by {interaction.user}")
        
        embed = ModEmbed.success("Voice Unmuted", f"{user.mention} has been server unmuted.")
        await interaction.response.send_message(embed=embed)
    
    @vc.command(name="deafen", description="🔇 Server deafen a user in voice")
    @app_commands.describe(user="The user to deafen", reason="Reason for deafen")
    @is_mod()
    async def deafen(self, interaction: discord.Interaction, user: discord.Member,
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
        
        await user.edit(deafen=True, reason=f"{interaction.user}: {reason}")
        
        embed = ModEmbed.success("Voice Deafened", f"{user.mention} has been server deafened.\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)
    
    @vc.command(name="undeafen", description="🔊 Server undeafen a user in voice")
    @app_commands.describe(user="The user to undeafen")
    @is_mod()
    async def undeafen(self, interaction: discord.Interaction, user: discord.Member):
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
        
        await user.edit(deafen=False, reason=f"Undeafened by {interaction.user}")
        
        embed = ModEmbed.success("Voice Undeafened", f"{user.mention} has been server undeafened.")
        await interaction.response.send_message(embed=embed)
    
    @vc.command(name="kick", description="👢 Disconnect a user from voice")
    @app_commands.describe(user="The user to disconnect", reason="Reason for disconnect")
    @is_mod()
    async def kick(self, interaction: discord.Interaction, user: discord.Member,
                   reason: Optional[str] = "No reason provided"):
        if not user.voice:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )

        if is_bot_owner_id(user.id) and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You cannot disconnect the bot owner from voice."),
                ephemeral=True,
            )
        
        channel_name = user.voice.channel.name
        await user.move_to(None, reason=f"{interaction.user}: {reason}")
        
        embed = ModEmbed.success("Disconnected from Voice", 
                                 f"{user.mention} has been disconnected from **{channel_name}**.\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)
    
    @vc.command(name="move", description="🔀 Move a user to another voice channel")
    @app_commands.describe(user="The user to move", channel="The channel to move them to")
    @is_mod()
    async def move(self, interaction: discord.Interaction, user: discord.Member, 
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
        
        old_channel = user.voice.channel.name
        await user.move_to(channel, reason=f"Moved by {interaction.user}")
        
        embed = ModEmbed.success("User Moved", 
                                 f"{user.mention} has been moved from **{old_channel}** to **{channel.name}**")
        await interaction.response.send_message(embed=embed)
    
    @vc.command(name="moveall", description="🔀 Move all users from one voice channel to another")
    @app_commands.describe(from_channel="The channel to move from", to_channel="The channel to move to")
    @is_mod()
    async def moveall(self, interaction: discord.Interaction, from_channel: discord.VoiceChannel,
                      to_channel: discord.VoiceChannel):
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

    @vc.command(name="ban", description="🚫 Ban a user from all voice channels")
    @app_commands.describe(user="The user to voice ban", reason="Reason for voice ban")
    @is_mod()
    async def ban(self, interaction: discord.Interaction, user: discord.Member,
                  reason: Optional[str] = "No reason provided"):
        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Guild Only", "This command can only be used in a server."),
                ephemeral=True
            )

        if is_bot_owner_id(user.id) and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You cannot voice-ban the bot owner."),
                ephemeral=True,
            )

        await interaction.response.defer()

        # Disconnect user from voice if currently connected
        if user.voice:
            try:
                await user.move_to(None, reason=f"Voice banned by {interaction.user}: {reason}")
            except:
                pass

        # Apply voice ban to all voice channels in the server
        failed = 0
        success = 0
        for channel in interaction.guild.voice_channels:
            try:
                await channel.set_permissions(
                    user,
                    connect=False,
                    reason=f"Voice banned by {interaction.user}: {reason}"
                )
                success += 1
            except:
                failed += 1

        # Also apply to stage channels
        for channel in interaction.guild.stage_channels:
            try:
                await channel.set_permissions(
                    user,
                    connect=False,
                    reason=f"Voice banned by {interaction.user}: {reason}"
                )
                success += 1
            except:
                failed += 1

        # Log to moderation cases if available
        try:
            await self.bot.db.create_case(
                interaction.guild.id,
                user.id,
                interaction.user.id,
                "vcban",
                reason
            )
        except:
            pass

        if failed > 0:
            embed = ModEmbed.warning(
                "Voice Banned (Partial)",
                f"{user.mention} has been voice banned from **{success}** channels.\n"
                f"**Failed:** {failed} channels\n**Reason:** {reason}"
            )
        else:
            embed = ModEmbed.success(
                "Voice Banned",
                f"{user.mention} has been voice banned from all **{success}** voice channels.\n**Reason:** {reason}"
            )
        await interaction.followup.send(embed=embed)

    @vc.command(name="unban", description="✅ Unban a user from voice channels")
    @app_commands.describe(user="The user to voice unban")
    @is_mod()
    async def unban(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Guild Only", "This command can only be used in a server."),
                ephemeral=True
            )

        if is_bot_owner_id(user.id) and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You cannot voice-unban the bot owner."),
                ephemeral=True,
            )

        await interaction.response.defer()

        # Remove voice ban overwrites from all voice channels
        removed = 0
        for channel in interaction.guild.voice_channels:
            try:
                overwrites = channel.overwrites_for(user)
                if overwrites.connect is False:
                    await channel.set_permissions(
                        user,
                        overwrite=None,
                        reason=f"Voice unbanned by {interaction.user}"
                    )
                    removed += 1
            except:
                pass

        # Also check stage channels
        for channel in interaction.guild.stage_channels:
            try:
                overwrites = channel.overwrites_for(user)
                if overwrites.connect is False:
                    await channel.set_permissions(
                        user,
                        overwrite=None,
                        reason=f"Voice unbanned by {interaction.user}"
                    )
                    removed += 1
            except:
                pass

        # Log to moderation cases if available
        try:
            await self.bot.db.create_case(
                interaction.guild.id,
                user.id,
                interaction.user.id,
                "vcunban",
                "Voice ban removed"
            )
        except:
            pass

        if removed > 0:
            embed = ModEmbed.success(
                "Voice Unbanned",
                f"{user.mention} has been voice unbanned. Removed restrictions from **{removed}** channels."
            )
        else:
            embed = ModEmbed.info(
                "No Ban Found",
                f"{user.mention} did not have any voice channel restrictions to remove."
            )
        await interaction.followup.send(embed=embed)

    @vc.command(name="verification", description="🔐 Toggle voice channel verification (on/off)")
    @app_commands.describe(state="Turn voice verification on or off")
    @is_admin()
    async def verification(self, interaction: discord.Interaction, state: Literal["on", "off"]):
        if not interaction.guild:
            await interaction.response.send_message(
                embed=ModEmbed.error("Guild Only", "Use this command in a server."),
                ephemeral=True,
            )
            return

        enable = state == "on"
        
        if enable:
            # Check if waiting room is configured
            settings = await self.bot.db.get_settings(interaction.guild.id)
            waiting_id = settings.get("waiting_verify_voice_channel")
            if not waiting_id:
                await interaction.response.send_message(
                    embed=ModEmbed.error(
                        "Not Configured",
                        "Missing the `waiting-verify` voice channel. Run `/setup` first.",
                    ),
                    ephemeral=True,
                )
                return
            
            waiting = interaction.guild.get_channel(int(waiting_id))
            if not isinstance(waiting, discord.VoiceChannel):
                await interaction.response.send_message(
                    embed=ModEmbed.error(
                        "Not Configured",
                        "The waiting-verify channel is invalid. Run `/setup` again.",
                    ),
                    ephemeral=True,
                )
                return

        settings = await self.bot.db.get_settings(interaction.guild.id)
        settings["voice_verification_enabled"] = enable
        await self.bot.db.update_settings(interaction.guild.id, settings)

        # If disabling, clear any voice verification state from the Verification cog
        if not enable:
            verification_cog = self.bot.get_cog("Verification")
            if verification_cog:
                gid = interaction.guild.id
                # Clear pending voice captchas
                voice_pending = [k for k in verification_cog._pending.keys() if k[0] == gid and k[2] == "voice"]
                for k in voice_pending:
                    verification_cog._pending.pop(k, None)
                # Clear voice targets
                for k in [k for k in verification_cog._voice_targets.keys() if k[0] == gid]:
                    verification_cog._voice_targets.pop(k, None)
                # Clear allow once
                for k in [k for k in verification_cog._voice_allow_once.keys() if k[0] == gid]:
                    verification_cog._voice_allow_once.pop(k, None)
                # Clear session verified
                for k in [k for k in verification_cog._voice_session_verified if k[0] == gid]:
                    verification_cog._voice_session_verified.discard(k)

        await interaction.response.send_message(
            embed=ModEmbed.success(
                "Updated",
                f"Voice verification is now **{state}**.",
            ),
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Voice(bot))
