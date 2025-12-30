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
    
    @app_commands.command(name="vc", description="🎤 Voice channel moderation commands")
    @app_commands.describe(
        action="The action to perform",
        user="The user to target (required for most actions)",
        channel="Target voice channel (for move/moveall)",
        from_channel="Source channel (for moveall)",
        reason="Reason for the action",
        state="on/off (for verification)"
    )
    @is_mod()
    async def vc(
        self, 
        interaction: discord.Interaction, 
        action: Literal["mute", "unmute", "deafen", "undeafen", "kick", "move", "moveall", "ban", "unban", "verification"],
        user: Optional[discord.Member] = None,
        channel: Optional[discord.VoiceChannel] = None,
        from_channel: Optional[discord.VoiceChannel] = None,
        reason: Optional[str] = "No reason provided",
        state: Optional[Literal["on", "off"]] = None
    ):
        # Handle verification separately (admin only)
        if action == "verification":
            # Check admin permission
            admin_check = is_admin()
            try:
                await admin_check.interaction_check(interaction)
            except app_commands.CheckFailure:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Permission Denied", "You need administrator permissions for this action."),
                    ephemeral=True
                )
            
            if state is None:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Missing Argument", "Please specify `state: on` or `state: off` for verification."),
                    ephemeral=True
                )
            await self._verification(interaction, state)
            return
        
        # All other actions require a user
        if user is None:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `user` for this action."),
                ephemeral=True
            )
        
        # Check bot owner protection
        if is_bot_owner_id(user.id) and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", f"You cannot {action} the bot owner."),
                ephemeral=True
            )
        
        # Route to appropriate handler
        if action == "mute":
            await self._mute(interaction, user, reason)
        elif action == "unmute":
            await self._unmute(interaction, user)
        elif action == "deafen":
            await self._deafen(interaction, user, reason)
        elif action == "undeafen":
            await self._undeafen(interaction, user)
        elif action == "kick":
            await self._kick(interaction, user, reason)
        elif action == "move":
            if channel is None:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Missing Argument", "Please specify a `channel` to move the user to."),
                    ephemeral=True
                )
            await self._move(interaction, user, channel)
        elif action == "moveall":
            if from_channel is None or channel is None:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Missing Arguments", "Please specify both `from_channel` and `channel` for moveall."),
                    ephemeral=True
                )
            await self._moveall(interaction, from_channel, channel)
        elif action == "ban":
            await self._ban(interaction, user, reason)
        elif action == "unban":
            await self._unban(interaction, user)

    async def _mute(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        if not user.voice:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )
        
        await user.edit(mute=True, reason=f"{interaction.user}: {reason}")
        embed = ModEmbed.success("Voice Muted", f"{user.mention} has been server muted.\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)
    
    async def _unmute(self, interaction: discord.Interaction, user: discord.Member):
        if not user.voice:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )
        
        await user.edit(mute=False, reason=f"Unmuted by {interaction.user}")
        embed = ModEmbed.success("Voice Unmuted", f"{user.mention} has been server unmuted.")
        await interaction.response.send_message(embed=embed)
    
    async def _deafen(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        if not user.voice:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )
        
        await user.edit(deafen=True, reason=f"{interaction.user}: {reason}")
        embed = ModEmbed.success("Voice Deafened", f"{user.mention} has been server deafened.\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)
    
    async def _undeafen(self, interaction: discord.Interaction, user: discord.Member):
        if not user.voice:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )
        
        await user.edit(deafen=False, reason=f"Undeafened by {interaction.user}")
        embed = ModEmbed.success("Voice Undeafened", f"{user.mention} has been server undeafened.")
        await interaction.response.send_message(embed=embed)
    
    async def _kick(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        if not user.voice:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )
        
        channel_name = user.voice.channel.name
        await user.move_to(None, reason=f"{interaction.user}: {reason}")
        
        embed = ModEmbed.success("Disconnected from Voice", 
                                 f"{user.mention} has been disconnected from **{channel_name}**.\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)
    
    async def _move(self, interaction: discord.Interaction, user: discord.Member, channel: discord.VoiceChannel):
        if not user.voice:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )
        
        old_channel = user.voice.channel.name
        await user.move_to(channel, reason=f"Moved by {interaction.user}")
        
        embed = ModEmbed.success("User Moved", 
                                 f"{user.mention} has been moved from **{old_channel}** to **{channel.name}**")
        await interaction.response.send_message(embed=embed)
    
    async def _moveall(self, interaction: discord.Interaction, from_channel: discord.VoiceChannel,
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

    async def _ban(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Guild Only", "This command can only be used in a server."),
                ephemeral=True
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

    async def _unban(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Guild Only", "This command can only be used in a server."),
                ephemeral=True
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

    async def _verification(self, interaction: discord.Interaction, state: Literal["on", "off"]):
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
