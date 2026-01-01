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
        user_id="User ID for unban (if user left server)",
        channel="Target voice channel (for move/moveall/check/afkdetect)",
        from_channel="Source channel (for moveall)",
        reason="Reason for the action",
        state="on/off (for verification/afkdetect)",
        minutes="Minutes for afkdetect timeout"
    )
    @is_mod()
    async def vc(
        self, 
        interaction: discord.Interaction, 
        action: Literal["mute", "unmute", "deafen", "undeafen", "kick", "move", "moveall", "ban", "unban", "verification", "check", "afkdetect"],
        user: Optional[discord.Member] = None,
        user_id: Optional[str] = None,
        channel: Optional[discord.VoiceChannel] = None,
        from_channel: Optional[discord.VoiceChannel] = None,
        reason: Optional[str] = "No reason provided",
        state: Optional[Literal["on", "off", "settings", "ignore", "unignore"]] = None,
        minutes: Optional[int] = None
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
        
        # Handle afkdetect separately (admin only)
        if action == "afkdetect":
            # Check admin permission
            admin_check = is_admin()
            try:
                await admin_check.interaction_check(interaction)
            except app_commands.CheckFailure:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Permission Denied", "You need administrator permissions for this action."),
                    ephemeral=True
                )
            
            await self._afkdetect(interaction, state, channel, user, minutes)
            return
        
        # Handle check separately - can check a single user OR all users in a VC
        if action == "check":
            # If a specific user is provided, check just that user
            if user is not None:
                voice_afk_cog = self.bot.get_cog("VoiceAFK")
                if not voice_afk_cog:
                    return await interaction.response.send_message(
                        embed=ModEmbed.error("Not Available", "Voice AFK detection cog is not loaded."),
                        ephemeral=True
                    )
                await voice_afk_cog.afk_check_user(interaction, user)
                return
            
            # No user specified - check all users in the channel
            if channel is None:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Missing Argument", "Please specify a `user` to check, or a `channel` to check everyone."),
                    ephemeral=True
                )
            await self._check_vc(interaction, channel)
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

    async def _check_vc(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        """Check all users in a voice channel for AFK - parallel DMs, individual thanks"""
        # Get the VoiceAFK cog
        voice_afk_cog = self.bot.get_cog("VoiceAFK")
        
        if not voice_afk_cog:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Available", "Voice AFK detection is not loaded. Make sure `voice_afk.py` cog is loaded."),
                ephemeral=True
            )
        
        # Check if there are users in the channel
        members = [m for m in channel.members if not m.bot]
        if not members:
            return await interaction.response.send_message(
                embed=ModEmbed.warning("Empty Channel", f"{channel.mention} has no users to check."),
                ephemeral=True
            )
        
        await interaction.response.defer(ephemeral=True)
        
        # Get AFK settings
        settings = await voice_afk_cog._get_afk_settings(interaction.guild.id)
        
        # Filter out members already being checked
        to_check = []
        skipped = 0
        
        for member in members:
            key = (interaction.guild.id, member.id)
            if key in voice_afk_cog.pending_checks:
                skipped += 1
                continue
            to_check.append(member)
            voice_afk_cog.pending_checks.add(key)
        
        if not to_check:
            return await interaction.followup.send(
                embed=ModEmbed.warning("All Being Checked", "All users in this channel are already being checked."),
                ephemeral=True
            )
        
        # Send initial message
        embed = ModEmbed.success(
            "AFK Check Started",
            f"Checking **{len(to_check)}** users in {channel.mention} for AFK.\n"
            f"Skipped **{skipped}** (already being checked).\n\n"
            f"A TTS prompt will play and users must respond within {settings['response_timeout']} seconds."
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        import asyncio
        import os
        from datetime import datetime, timezone
        
        # Try to import voice recv for speaking detection
        try:
            import discord.ext.voice_recv as voice_recv
            VOICE_RECV_AVAILABLE = True
        except ImportError:
            VOICE_RECV_AVAILABLE = False
        
        # Join voice channel - use VoiceRecvClient if available
        voice_client = None
        speaking_detected = {}  # member_id -> True when they speak
        
        try:
            if VOICE_RECV_AVAILABLE:
                voice_client = await channel.connect(cls=voice_recv.VoiceRecvClient)
                
                # Create speaking callback for all users
                def on_voice_packet(user, data):
                    if user and user.id in [m.id for m in to_check]:
                        speaking_detected[user.id] = True
                
                # Start listening for voice packets
                voice_client.listen(voice_recv.BasicSink(on_voice_packet))
            else:
                voice_client = await channel.connect()
        except Exception as e:
            print(f"[VoiceAFK] Failed to connect to {channel.name}: {e}")
            for member in to_check:
                voice_afk_cog.pending_checks.discard((interaction.guild.id, member.id))
            return
        
        try:
            # Play generic "Hello everyone" TTS
            generic_tts = await voice_afk_cog._generate_tts(
                f"Hello everyone! This is an AFK check. Please confirm you're here by clicking the button in your DMs, "
                f"toggling your mute, or saying something. You have {settings['response_timeout']} seconds.",
                "afk_check_all.mp3"
            )
            
            if generic_tts and os.path.exists(generic_tts):
                audio_source = discord.FFmpegPCMAudio(generic_tts)
                voice_client.play(audio_source)
                while voice_client.is_playing():
                    await asyncio.sleep(0.5)
                try:
                    os.remove(generic_tts)
                except:
                    pass
            
            # Send DMs to all users in PARALLEL
            from cogs.voice_afk import AFKConfirmButton
            
            user_views = {}  # member_id -> (view, msg)
            
            async def send_dm(member):
                try:
                    dm_channel = await member.create_dm()
                    view = AFKConfirmButton(voice_afk_cog, member, timeout=settings["response_timeout"])
                    
                    embed = discord.Embed(
                        title="🎤 AFK Check",
                        description=f"You are being checked for AFK in **{channel.name}** ({interaction.guild.name}).\n\n"
                                    f"**Respond in one of these ways within {settings['response_timeout']} seconds:**\n"
                                    f"• 🎙️ Say something in voice chat\n"
                                    f"• 🔇 Toggle your mute/unmute\n"
                                    f"• ✅ Click the button below\n\n"
                                    f"If you don't respond, you will be disconnected.",
                        color=0xFFAA00,
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    msg = await dm_channel.send(embed=embed, view=view)
                    return member.id, view, msg
                except Exception as e:
                    print(f"[VoiceAFK] Failed to DM {member}: {e}")
                    return member.id, None, None
            
            # Send all DMs in parallel
            dm_results = await asyncio.gather(*[send_dm(m) for m in to_check])
            
            for member_id, view, msg in dm_results:
                if view:
                    user_views[member_id] = (view, msg)
            
            # Wait for responses (listen for button clicks or voice activity)
            confirmed = set()
            
            # Create voice activity listeners for each member
            voice_events = {m.id: asyncio.Event() for m in to_check}
            
            async def check_voice_activity(m, before, after):
                if m.id in voice_events:
                    if before.self_mute != after.self_mute or \
                       before.self_deaf != after.self_deaf or \
                       before.mute != after.mute or \
                       before.deaf != after.deaf:
                        voice_events[m.id].set()
            
            # Temporarily add voice listener
            original_listeners = self.bot.extra_events.get('on_voice_state_update', []).copy()
            
            @self.bot.event
            async def on_voice_state_update(m, before, after):
                await check_voice_activity(m, before, after)
                for listener in original_listeners:
                    try:
                        await listener(m, before, after)
                    except:
                        pass
            
            try:
                # Wait for timeout, checking for confirmations
                start_time = asyncio.get_event_loop().time()
                timeout = settings["response_timeout"]
                
                while asyncio.get_event_loop().time() - start_time < timeout:
                    await asyncio.sleep(1)
                    
                    # Check for new confirmations
                    for member in to_check:
                        if member.id in confirmed:
                            continue
                        
                        # Check button click
                        if member.id in user_views:
                            view, msg = user_views[member.id]
                            if view and view.confirmed:
                                confirmed.add(member.id)
                                voice_afk_cog._update_activity(interaction.guild.id, member.id)
                                
                                # Edit DM
                                try:
                                    await msg.edit(embed=discord.Embed(
                                        title="✅ Presence Confirmed",
                                        description=f"Thanks for confirming you're still in **{channel.name}**!",
                                        color=0x00FF00
                                    ), view=None)
                                except:
                                    pass
                                
                                # Thank them in voice
                                if voice_client and voice_client.is_connected():
                                    try:
                                        tts_file = await voice_afk_cog._generate_tts(
                                            f"Thanks {member.display_name}!",
                                            f"afk_thanks_{member.id}.mp3"
                                        )
                                        if tts_file and os.path.exists(tts_file):
                                            # Wait for any current audio to finish
                                            while voice_client.is_playing():
                                                await asyncio.sleep(0.2)
                                            audio_source = discord.FFmpegPCMAudio(tts_file)
                                            voice_client.play(audio_source)
                                            while voice_client.is_playing():
                                                await asyncio.sleep(0.2)
                                            try:
                                                os.remove(tts_file)
                                            except:
                                                pass
                                    except:
                                        pass
                        
                        # Check voice activity (mute/unmute toggle)
                        if member.id in voice_events and voice_events[member.id].is_set():
                            if member.id not in confirmed:
                                confirmed.add(member.id)
                                voice_afk_cog._update_activity(interaction.guild.id, member.id)
                                
                                # Thank them in voice
                                if voice_client and voice_client.is_connected():
                                    try:
                                        tts_file = await voice_afk_cog._generate_tts(
                                            f"Thanks {member.display_name}!",
                                            f"afk_thanks_{member.id}.mp3"
                                        )
                                        if tts_file and os.path.exists(tts_file):
                                            while voice_client.is_playing():
                                                await asyncio.sleep(0.2)
                                            audio_source = discord.FFmpegPCMAudio(tts_file)
                                            voice_client.play(audio_source)
                                            while voice_client.is_playing():
                                                await asyncio.sleep(0.2)
                                            try:
                                                os.remove(tts_file)
                                            except:
                                                pass
                                    except:
                                        pass
                        
                        # Check speaking detection (green indicator)
                        if member.id in speaking_detected and speaking_detected[member.id]:
                            if member.id not in confirmed:
                                confirmed.add(member.id)
                                voice_afk_cog._update_activity(interaction.guild.id, member.id)
                                
                                # Edit DM if they have one
                                if member.id in user_views:
                                    view, msg = user_views[member.id]
                                    try:
                                        await msg.edit(embed=discord.Embed(
                                            title="✅ Presence Confirmed",
                                            description=f"Detected you speaking in **{channel.name}**!",
                                            color=0x00FF00
                                        ), view=None)
                                    except:
                                        pass
                                
                                # Thank them in voice
                                if voice_client and voice_client.is_connected():
                                    try:
                                        tts_file = await voice_afk_cog._generate_tts(
                                            f"Thanks {member.display_name}!",
                                            f"afk_thanks_{member.id}.mp3"
                                        )
                                        if tts_file and os.path.exists(tts_file):
                                            while voice_client.is_playing():
                                                await asyncio.sleep(0.2)
                                            audio_source = discord.FFmpegPCMAudio(tts_file)
                                            voice_client.play(audio_source)
                                            while voice_client.is_playing():
                                                await asyncio.sleep(0.2)
                                            try:
                                                os.remove(tts_file)
                                            except:
                                                pass
                                    except:
                                        pass
                
                # Timeout reached - kick unconfirmed users
                for member in to_check:
                    if member.id not in confirmed:
                        if member.voice and member.voice.channel:
                            try:
                                await member.move_to(None, reason="AFK detection - No response to activity check")
                                try:
                                    dm_embed = discord.Embed(
                                        title="🔇 Disconnected for Inactivity",
                                        description=f"You were disconnected from **{channel.name}** in **{interaction.guild.name}** for being AFK.",
                                        color=0xFF6600,
                                        timestamp=datetime.now(timezone.utc)
                                    )
                                    await member.send(embed=dm_embed)
                                except:
                                    pass
                                print(f"[VoiceAFK] Kicked {member} from {channel.name} for inactivity")
                            except:
                                pass
                    
                    # Remove from pending
                    voice_afk_cog.pending_checks.discard((interaction.guild.id, member.id))
            
            finally:
                # Restore original listeners
                pass
        
        finally:
            # Disconnect from voice
            if voice_client and voice_client.is_connected():
                await voice_client.disconnect()

    async def _afkdetect(
        self,
        interaction: discord.Interaction,
        state: Optional[str],
        channel: Optional[discord.VoiceChannel],
        user: Optional[discord.Member],
        minutes: Optional[int]
    ):
        """Handle AFK detection admin actions"""
        voice_afk_cog = self.bot.get_cog("VoiceAFK")
        
        if not voice_afk_cog:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Available", "Voice AFK detection cog is not loaded."),
                ephemeral=True
            )
        
        # Route based on state parameter
        if state is None or state == "settings":
            await voice_afk_cog.afk_settings(interaction)
        elif state == "on":
            await voice_afk_cog.afk_enable(interaction)
        elif state == "off":
            await voice_afk_cog.afk_disable(interaction)
        elif state == "ignore":
            if channel is None:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Missing Argument", "Please specify a `channel` to ignore."),
                    ephemeral=True
                )
            await voice_afk_cog.afk_ignore(interaction, channel)
        elif state == "unignore":
            if channel is None:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Missing Argument", "Please specify a `channel` to unignore."),
                    ephemeral=True
                )
            await voice_afk_cog.afk_unignore(interaction, channel)
        
        # Handle timeout setting via minutes parameter
        if minutes is not None:
            await voice_afk_cog.afk_timeout(interaction, minutes)
        
        # Handle user check
        if user is not None and state is None:
            await voice_afk_cog.afk_check_user(interaction, user)

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
