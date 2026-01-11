"""
Voice Moderation Commands
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from typing import Optional, Literal, Union
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
        user_id="User ID for unban or check (if user left server)",
        channel="Target voice channel (for move/moveall/check_channel)",
        from_channel="Source channel (for moveall)",
        reason="Reason for the action",
        state="Verification state: on/off/settings/bypass_add/bypass_remove/timeout/check_channel/check_user",
        role="Role for bypass add/remove",
        minutes="Minutes for session timeout",
    )
    @is_mod()
    async def vc(
        self, 
        interaction: discord.Interaction, 
        action: Literal["mute", "unmute", "deafen", "undeafen", "kick", "move", "moveall", "ban", "unban", "verification"],
        user: Optional[discord.Member] = None,
        user_id: Optional[str] = None,
        channel: Optional[discord.VoiceChannel] = None,
        from_channel: Optional[discord.VoiceChannel] = None,
        reason: Optional[str] = "No reason provided",
        state: Optional[Literal["on", "off", "settings", "bypass_add", "bypass_remove", "timeout", "check_channel", "check_user"]] = None,
        role: Optional[discord.Role] = None,
        minutes: Optional[int] = None,
    ):
        # Handle verification separately (admin only)
        if action == "verification":
            # Check admin permission directly
            is_admin_user = False
            if is_bot_owner_id(interaction.user.id):
                is_admin_user = True
            elif interaction.user.guild_permissions.administrator:
                is_admin_user = True
            else:
                # Check for admin/manager roles from database
                settings = await self.bot.db.get_settings(interaction.guild_id)
                admin_roles = settings.get("admin_roles", [])
                manager_role = settings.get("manager_role")
                user_role_ids = [r.id for r in interaction.user.roles]
                if manager_role and manager_role in user_role_ids:
                    is_admin_user = True
                elif any(role_id in user_role_ids for role_id in admin_roles):
                    is_admin_user = True
            
            if not is_admin_user:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Permission Denied", "You need administrator permissions for this action."),
                    ephemeral=True
                )
            
            verification_cog = self.bot.get_cog("Verification")
            if not verification_cog:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Not Available", "Verification cog is not loaded."),
                    ephemeral=True
                )
            
            # Auto-detect state from provided parameters if state is None
            if state is None:
                if minutes is not None:
                    state = "timeout"
                elif role is not None:
                    state = "bypass_add"
                elif channel is not None:
                    state = "check_channel"
                elif user is not None or user_id is not None:
                    state = "check_user"
                else:
                    return await interaction.response.send_message(
                        embed=ModEmbed.error(
                            "Missing Argument", 
                            "**Usage:**\n"
                            "• `state:on` / `state:off` - Enable/disable verification\n"
                            "• `state:settings` - View current settings\n"
                            "• `state:timeout minutes:30` - Set session TTL\n"
                            "• `state:bypass_add role:@Role` - Add bypass role\n"
                            "• `state:bypass_remove role:@Role` - Remove bypass role\n"
                            "• `state:check_channel channel:#voice` - Force verify all users\n"
                            "• `state:check_user user:@User` - Force verify specific user"
                        ),
                        ephemeral=True
                    )
            
            # Handle verification sub-actions
            if state == "settings":
                await verification_cog.show_settings(interaction)
                return
            
            if state == "bypass_add":
                if role is None:
                    return await interaction.response.send_message(
                        embed=ModEmbed.error("Missing Argument", "Please specify a `role` to add as bypass."),
                        ephemeral=True
                    )
                await verification_cog.add_bypass_role(interaction, role)
                return
            
            if state == "bypass_remove":
                if role is None:
                    return await interaction.response.send_message(
                        embed=ModEmbed.error("Missing Argument", "Please specify a `role` to remove from bypass."),
                        ephemeral=True
                    )
                await verification_cog.remove_bypass_role(interaction, role)
                return
            
            if state == "timeout":
                if minutes is None:
                    return await interaction.response.send_message(
                        embed=ModEmbed.error("Missing Argument", "Please specify `minutes` for session timeout (1-1440)."),
                        ephemeral=True
                    )
                await verification_cog.set_session_timeout(interaction, minutes)
                return
            
            if state == "check_channel":
                if channel is None:
                    return await interaction.response.send_message(
                        embed=ModEmbed.error("Missing Argument", "Please specify a voice `channel` to check."),
                        ephemeral=True
                    )
                await self._manual_verify_channel(interaction, verification_cog, channel)
                return
            
            if state == "check_user":
                target_member = user
                if target_member is None and user_id:
                    try:
                        uid = int(user_id)
                        target_member = interaction.guild.get_member(uid)
                    except ValueError:
                        pass
                
                if target_member is None:
                    return await interaction.response.send_message(
                        embed=ModEmbed.error("Missing Argument", "Please specify a `user` or `user_id` to check."),
                        ephemeral=True
                    )
                await self._manual_verify_user(interaction, verification_cog, target_member)
                return
            
            # Handle on/off states
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
            # Unban can work with either user or user_id
            if user is None and user_id is None:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Missing Argument", "Please specify either `user` or `user_id` for unban."),
                    ephemeral=True
                )
            await self._unban(interaction, user, user_id)

    async def _respond(self, source, embed=None, content=None, ephemeral=False, view=None):
        if isinstance(source, discord.Interaction):
            if source.response.is_done():
                return await source.followup.send(content=content, embed=embed, ephemeral=ephemeral, view=view)
            else:
                return await source.response.send_message(content=content, embed=embed, ephemeral=ephemeral, view=view)
        else:
            return await source.send(content=content, embed=embed, view=view)

    async def _manual_verify_channel(self, interaction: discord.Interaction, verification_cog, channel: discord.VoiceChannel):
        """Manually trigger verification for all users in a voice channel."""
        await interaction.response.defer(ephemeral=True)
        
        if not channel.members:
            return await interaction.followup.send(
                embed=ModEmbed.info("Empty Channel", f"{channel.mention} has no members to verify."),
                ephemeral=True
            )
        
        # Get necessary resources
        waiting_channel = await verification_cog._get_waiting_voice_channel(interaction.guild)
        if not waiting_channel:
            return await interaction.followup.send(
                embed=ModEmbed.error("No Waiting Channel", "No waiting/verification channel is configured. Set one in `/setup`."),
                ephemeral=True
            )
        
        bypass_roles = await verification_cog._get_bypass_roles(interaction.guild.id)
        
        moved = 0
        bypassed = 0
        already_verified = 0
        failed = 0
        
        for member in channel.members:
            if member.bot:
                continue
            
            # Check if has bypass role
            if verification_cog._has_bypass_role(member, bypass_roles):
                bypassed += 1
                continue
            
            # Check if has valid session
            if verification_cog._has_valid_session(interaction.guild.id, member.id):
                already_verified += 1
                continue
            
            # Move to waiting channel and send DM
            try:
                key = (interaction.guild.id, member.id)
                verification_cog._voice_targets[key] = channel.id
                await member.move_to(waiting_channel, reason=f"Manual verification check by {interaction.user}")
                await verification_cog._send_voice_verify_dm(guild=interaction.guild, member=member)
                moved += 1
            except Exception:
                failed += 1
        
        embed = discord.Embed(
            title="🔍 Manual Verification Check",
            description=f"Checked all members in {channel.mention}",
            color=Config.COLOR_SUCCESS if moved > 0 else Config.COLOR_INFO
        )
        embed.add_field(name="📤 Moved to Verify", value=str(moved), inline=True)
        embed.add_field(name="⏭️ Bypassed", value=str(bypassed), inline=True)
        embed.add_field(name="✅ Already Verified", value=str(already_verified), inline=True)
        if failed > 0:
            embed.add_field(name="❌ Failed", value=str(failed), inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _manual_verify_user(self, interaction: discord.Interaction, verification_cog, member: discord.Member):
        """Manually trigger verification for a specific user."""
        if member.bot:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Invalid Target", "You cannot verify bots."),
                ephemeral=True
            )
        
        # Check if user is in voice
        if not member.voice or not member.voice.channel:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not In Voice", f"{member.mention} is not in a voice channel."),
                ephemeral=True
            )
        
        original_channel = member.voice.channel
        
        # Get waiting channel
        waiting_channel = await verification_cog._get_waiting_voice_channel(interaction.guild)
        if not waiting_channel:
            return await interaction.response.send_message(
                embed=ModEmbed.error("No Waiting Channel", "No waiting/verification channel is configured. Set one in `/setup`."),
                ephemeral=True
            )
        
        # Check bypass roles
        bypass_roles = await verification_cog._get_bypass_roles(interaction.guild.id)
        if verification_cog._has_bypass_role(member, bypass_roles):
            return await interaction.response.send_message(
                embed=ModEmbed.info("Has Bypass", f"{member.mention} has a bypass role and doesn't need verification."),
                ephemeral=True
            )
        
        # Check if already verified
        if verification_cog._has_valid_session(interaction.guild.id, member.id):
            return await interaction.response.send_message(
                embed=ModEmbed.info("Already Verified", f"{member.mention} has an active verification session."),
                ephemeral=True
            )
        
        # Invalidate any existing session and force re-verification
        key = (interaction.guild.id, member.id)
        verification_cog._voice_sessions.pop(key, None)
        verification_cog._voice_targets[key] = original_channel.id
        
        try:
            await member.move_to(waiting_channel, reason=f"Manual verification by {interaction.user}")
            await verification_cog._send_voice_verify_dm(guild=interaction.guild, member=member)
            
            embed = ModEmbed.success(
                "Verification Triggered",
                f"{member.mention} has been moved to {waiting_channel.mention} for verification.\n"
                f"They will return to {original_channel.mention} after completing the captcha."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=ModEmbed.error("Failed", "I don't have permission to move this user."),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=ModEmbed.error("Failed", f"Could not verify user: {e}"),
                ephemeral=True
            )


    async def _mute(self, source, user: discord.Member, reason: str):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        if not user.voice:
            return await self._respond(
                source,
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )
        
        try:
            await user.edit(mute=True, reason=f"{author}: {reason}")
        except discord.Forbidden:
             return await self._respond(source, embed=ModEmbed.error("Failed", "I don't have permission to mute members."), ephemeral=True)

        embed = ModEmbed.success("Voice Muted", f"{user.mention} has been server muted.\n**Reason:** {reason}")
        await self._respond(source, embed=embed)
    
    async def _unmute(self, source, user: discord.Member):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        if not user.voice:
            return await self._respond(
                source,
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )
        
        try:
            await user.edit(mute=False, reason=f"Unmuted by {author}")
        except discord.Forbidden:
             return await self._respond(source, embed=ModEmbed.error("Failed", "I don't have permission to mute members."), ephemeral=True)

        embed = ModEmbed.success("Voice Unmuted", f"{user.mention} has been server unmuted.")
        await self._respond(source, embed=embed)
    
    async def _deafen(self, source, user: discord.Member, reason: str):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        if not user.voice:
            return await self._respond(
                source,
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )
            
        try:
            await user.edit(deafen=True, reason=f"{author}: {reason}")
        except discord.Forbidden:
             return await self._respond(source, embed=ModEmbed.error("Failed", "I don't have permission to deafen members."), ephemeral=True)

        embed = ModEmbed.success("Voice Deafened", f"{user.mention} has been server deafened.\n**Reason:** {reason}")
        await self._respond(source, embed=embed)
    
    async def _undeafen(self, source, user: discord.Member):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        if not user.voice:
            return await self._respond(
                source,
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )
        
        try:
            await user.edit(deafen=False, reason=f"Undeafened by {author}")
        except discord.Forbidden:
             return await self._respond(source, embed=ModEmbed.error("Failed", "I don't have permission to deafen members."), ephemeral=True)

        embed = ModEmbed.success("Voice Undeafened", f"{user.mention} has been server undeafened.")
        await self._respond(source, embed=embed)
    
    async def _kick(self, source, user: discord.Member, reason: str):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        if not user.voice:
            return await self._respond(
                source,
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )
        
        channel_name = user.voice.channel.name
        try:
            await user.move_to(None, reason=f"{author}: {reason}")
        except discord.Forbidden:
             return await self._respond(source, embed=ModEmbed.error("Failed", "I don't have permission to disconnect members."), ephemeral=True)
        
        embed = ModEmbed.success("Disconnected from Voice", 
                                 f"{user.mention} has been disconnected from **{channel_name}**.\n**Reason:** {reason}")
        await self._respond(source, embed=embed)
    
    async def _move(self, source, user: discord.Member, channel: discord.VoiceChannel):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        if not user.voice:
            return await self._respond(
                source,
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )
        
        old_channel = user.voice.channel.name
        try:
            await user.move_to(channel, reason=f"Moved by {author}")
        except discord.Forbidden:
             return await self._respond(source, embed=ModEmbed.error("Failed", "I don't have permission to move members."), ephemeral=True)
        
        embed = ModEmbed.success("User Moved", 
                                 f"{user.mention} has been moved from **{old_channel}** to **{channel.name}**")
        await self._respond(source, embed=embed)
    
    async def _moveall(self, source, from_channel: discord.VoiceChannel,
                       to_channel: discord.VoiceChannel):
        if not from_channel.members:
            return await self._respond(
                source,
                embed=ModEmbed.error("Empty Channel", f"{from_channel.mention} has no members."),
                ephemeral=True
            )
        
        if isinstance(source, discord.Interaction):
            await source.response.defer()
        
        author = source.user if isinstance(source, discord.Interaction) else source.author

        count = 0
        for member in from_channel.members:
            if is_bot_owner_id(member.id) and not is_bot_owner_id(author.id):
                continue
            try:
                await member.move_to(to_channel, reason=f"Mass move by {author}")
                count += 1
            except:
                pass
        
        embed = ModEmbed.success("Users Moved", 
                                 f"Moved **{count}** users from {from_channel.mention} to {to_channel.mention}")
        await self._respond(source, embed=embed)

    async def _ban(self, source, user: discord.Member, reason: str):
        if not source.guild:
            return await self._respond(source, embed=ModEmbed.error("Guild Only", "This command can only be used in a server."), ephemeral=True)

        if isinstance(source, discord.Interaction):
            await source.response.defer()

        author = source.user if isinstance(source, discord.Interaction) else source.author

        # Disconnect user from voice if currently connected
        if user.voice:
            try:
                await user.move_to(None, reason=f"Voice banned by {author}: {reason}")
            except:
                pass

        # Apply voice ban to all voice channels in the server
        failed = 0
        success = 0
        for channel in source.guild.voice_channels:
            try:
                await channel.set_permissions(
                    user,
                    connect=False,
                    reason=f"Voice banned by {author}: {reason}"
                )
                success += 1
            except:
                failed += 1

        # Also apply to stage channels
        for channel in source.guild.stage_channels:
            try:
                await channel.set_permissions(
                    user,
                    connect=False,
                    reason=f"Voice banned by {author}: {reason}"
                )
                success += 1
            except:
                failed += 1

        # Log to moderation cases if available
        try:
            await self.bot.db.create_case(
                source.guild.id,
                user.id,
                author.id,
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
        await self._respond(source, embed=embed)

    async def _unban(self, source, user: Optional[discord.Member], user_id: Optional[str]):
        if not source.guild:
            return await self._respond(source, embed=ModEmbed.error("Guild Only", "This command can only be used in a server."), ephemeral=True)

        if isinstance(source, discord.Interaction):
            await source.response.defer()
            
        author = source.user if isinstance(source, discord.Interaction) else source.author

        # Determine target - either from user object or user_id
        target_user = None
        target_id = None
        
        if user:
            target_user = user
            target_id = user.id
        elif user_id:
            try:
                target_id = int(user_id)
                # Try to fetch the user object (works even if they left)
                try:
                    target_user = await self.bot.fetch_user(target_id)
                except:
                    # User doesn't exist, but we can still use ID to remove permissions
                    target_user = await self.bot.get_or_fetch_member(source.guild, target_id)
            except ValueError:
                return await self._respond(
                    source,
                    embed=ModEmbed.error("Invalid ID", "Please provide a valid user ID."),
                    ephemeral=True
                )

        if not target_id:
            return await self._respond(
                source,
                embed=ModEmbed.error("Error", "Could not determine target user."),
                ephemeral=True
            )

        # Remove voice ban overwrites from all voice channels
        removed = 0
        for channel in source.guild.voice_channels:
            try:
                # Get the permission overwrite for this user
                if target_user:
                    overwrites = channel.overwrites_for(target_user)
                else:
                    # Fallback: check if there's an overwrite by ID
                    overwrites = channel.overwrites.get(discord.Object(id=target_id))
                    if not overwrites:
                        continue
                
                # Only remove if connect is explicitly set to False
                if overwrites and overwrites.connect is False:
                    await channel.set_permissions(
                        target_user if target_user else discord.Object(id=target_id),
                        overwrite=None,
                        reason=f"Voice unbanned by {author}"
                    )
                    removed += 1
            except Exception as e:
                pass

        # Also check stage channels
        for channel in source.guild.stage_channels:
            try:
                if target_user:
                    overwrites = channel.overwrites_for(target_user)
                else:
                    overwrites = channel.overwrites.get(discord.Object(id=target_id))
                    if not overwrites:
                        continue
                
                if overwrites and overwrites.connect is False:
                    await channel.set_permissions(
                        target_user if target_user else discord.Object(id=target_id),
                        overwrite=None,
                        reason=f"Voice unbanned by {author}"
                    )
                    removed += 1
            except Exception as e:
                pass

        # Log to moderation cases if available
        try:
            await self.bot.db.create_case(
                source.guild.id,
                target_id,
                author.id,
                "vcunban",
                "Voice ban removed"
            )
        except:
            pass

        user_mention = target_user.mention if target_user else f"User ID: {target_id}"
        
        if removed > 0:
            embed = ModEmbed.success(
                "Voice Unbanned",
                f"{user_mention} has been voice unbanned. Removed restrictions from **{removed}** channels."
            )
        else:
            embed = ModEmbed.info(
                "No Ban Found",
                f"{user_mention} did not have any voice channel restrictions to remove."
            )
        await self._respond(source, embed=embed)

    async def _verification(self, source, state: Literal["on", "off"]):
        if not source.guild:
            return await self._respond(source, embed=ModEmbed.error("Guild Only", "Use this command in a server."), ephemeral=True)

        enable = state == "on"
        
        if enable:
            # Check if waiting room is configured
            settings = await self.bot.db.get_settings(source.guild.id)
            waiting_id = settings.get("waiting_verify_voice_channel")
            if not waiting_id:
                return await self._respond(
                    source,
                    embed=ModEmbed.error(
                        "Not Configured",
                        "Missing the `waiting-verify` voice channel. Run `/setup` first.",
                    ),
                    ephemeral=True,
                )
            
            waiting = source.guild.get_channel(int(waiting_id))
            if not isinstance(waiting, discord.VoiceChannel):
                return await self._respond(
                    source,
                    embed=ModEmbed.error(
                        "Not Configured",
                        "The waiting-verify channel is invalid. Run `/setup` again.",
                    ),
                    ephemeral=True,
                )

        settings = await self.bot.db.get_settings(source.guild.id)
        settings["voice_verification_enabled"] = enable
        await self.bot.db.update_settings(source.guild.id, settings)

        # If disabling, clear any voice verification state from the Verification cog
        if not enable:
            verification_cog = self.bot.get_cog("Verification")
            if verification_cog:
                gid = source.guild.id
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

        await self._respond(
            source,
            embed=ModEmbed.success(
                "Updated",
                f"Voice verification is now **{state}**.",
            ),
            ephemeral=True,
        )

    @commands.command(name="vcmute")
    @is_mod()
    async def vcmute(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        """Mute a user in voice"""
        await self._mute(ctx, user, reason)

    @commands.command(name="vcunmute")
    @is_mod()
    async def vcunmute(self, ctx: commands.Context, user: discord.Member):
        """Unmute a user in voice"""
        await self._unmute(ctx, user)

    @commands.command(name="vcdeafen")
    @is_mod()
    async def vcdeafen(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        """Deafen a user in voice"""
        await self._deafen(ctx, user, reason)

    @commands.command(name="vcundeafen")
    @is_mod()
    async def vcundeafen(self, ctx: commands.Context, user: discord.Member):
        """Undeafen a user in voice"""
        await self._undeafen(ctx, user)

    @commands.command(name="vckick")
    @is_mod()
    async def vckick(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        """Kick a user from voice channel"""
        await self._kick(ctx, user, reason)

    @commands.command(name="vcmove")
    @is_mod()
    async def vcmove(self, ctx: commands.Context, user: discord.Member, channel: discord.VoiceChannel):
        """Move a user to another voice channel"""
        await self._move(ctx, user, channel)

    @commands.command(name="vcmoveall")
    @is_mod()
    async def vcmoveall(self, ctx: commands.Context, from_channel: discord.VoiceChannel, to_channel: discord.VoiceChannel):
        """Move all users from one channel to another"""
        await self._moveall(ctx, from_channel, to_channel)

    @commands.command(name="vcban")
    @is_mod()
    async def vcban(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        """Ban a user from all voice channels"""
        await self._ban(ctx, user, reason)

    @commands.command(name="vcunban")
    @is_mod()
    async def vcunban(self, ctx: commands.Context, user: Union[discord.Member, discord.User, str]):
        """Unban a user from voice channels"""
        user_obj = None
        user_id = None
        if isinstance(user, (discord.Member, discord.User)):
            user_obj = user
        else:
            user_id = str(user)
        await self._unban(ctx, user_obj, user_id)

    @commands.command(name="vcverify")
    @is_admin()
    async def vcverify(self, ctx: commands.Context, state: Literal["on", "off"]):
        """Enable/disable voice verification requirement"""
        await self._verification(ctx, state)


async def setup(bot):
    await bot.add_cog(Voice(bot))
