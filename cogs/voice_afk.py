"""
Voice AFK Detection System with TTS Verification
Automatically detects inactive users in voice channels and verifies they are not AFK/bots
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
import asyncio
import os
import tempfile

from utils.embeds import ModEmbed
from utils.checks import is_admin

# Try to import TTS library
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
    TTS_ENGINE = "gtts"
except ImportError:
    try:
        import edge_tts
        TTS_AVAILABLE = True
        TTS_ENGINE = "edge_tts"
    except ImportError:
        TTS_AVAILABLE = False
        TTS_ENGINE = None


class AFKConfirmButton(discord.ui.View):
    """Button view for AFK confirmation"""
    
    def __init__(self, cog: "VoiceAFK", member: discord.Member, timeout: float = 30.0):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.member = member
        self.confirmed = False
        self.spoke = False  # Track if user spoke
    
    def mark_spoke(self):
        """Mark that the user spoke"""
        self.spoke = True
        self.confirmed = True
        self.stop()
    
    @discord.ui.button(label="I'm Here!", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.member.id:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not For You", "This button is not for you."),
                ephemeral=True
            )
        
        self.confirmed = True
        self.stop()
        
        await interaction.response.send_message(
            embed=ModEmbed.success("Confirmed!", "Great! You've confirmed you're still here. Enjoy your time in voice chat!"),
            ephemeral=True
        )
    
    async def on_timeout(self):
        if not self.spoke:
            self.confirmed = False



class VoiceAFK(commands.Cog):
    """Voice AFK detection and verification system"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Track user activity: (guild_id, user_id) -> last_active_time
        self.user_activity: dict[tuple[int, int], datetime] = {}
        
        # Pending AFK checks: (guild_id, user_id) -> True (to prevent duplicate checks)
        self.pending_checks: set[tuple[int, int]] = set()
        
        # Ignored channels per guild: guild_id -> set of channel_ids
        self.ignored_channels: dict[int, set[int]] = {}
        
        # Temp directory for TTS files
        self.temp_dir = tempfile.gettempdir()
        
        # Start the background task
        self.check_inactive_users.start()
    
    def cog_unload(self):
        self.check_inactive_users.cancel()
    
    async def _get_afk_settings(self, guild_id: int) -> dict:
        """Get AFK settings for a guild"""
        settings = await self.bot.db.get_settings(guild_id)
        return {
            "enabled": settings.get("afk_detection_enabled", False),
            "timeout_minutes": settings.get("afk_timeout_minutes", 15),
            "response_timeout": settings.get("afk_response_timeout", 30),
            "ignored_channels": settings.get("afk_ignored_channels", [])
        }
    
    async def _update_afk_settings(self, guild_id: int, **kwargs):
        """Update AFK settings for a guild"""
        settings = await self.bot.db.get_settings(guild_id)
        for key, value in kwargs.items():
            settings[f"afk_{key}"] = value
        await self.bot.db.update_settings(guild_id, settings)
    
    def _update_activity(self, guild_id: int, user_id: int):
        """Update the last activity time for a user"""
        self.user_activity[(guild_id, user_id)] = datetime.now(timezone.utc)
    
    def _remove_activity(self, guild_id: int, user_id: int):
        """Remove activity tracking for a user"""
        self.user_activity.pop((guild_id, user_id), None)
        self.pending_checks.discard((guild_id, user_id))
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Track voice activity"""
        if member.bot:
            return
        
        guild_id = member.guild.id
        user_id = member.id
        
        # User left voice entirely
        if after.channel is None:
            self._remove_activity(guild_id, user_id)
            return
        
        # User joined voice or changed state (any activity counts)
        if before.channel != after.channel or \
           before.self_mute != after.self_mute or \
           before.self_deaf != after.self_deaf or \
           before.self_stream != after.self_stream or \
           before.self_video != after.self_video:
            self._update_activity(guild_id, user_id)
    
    @tasks.loop(seconds=60)
    async def check_inactive_users(self):
        """Background task to check for inactive users"""
        now = datetime.now(timezone.utc)
        
        for guild in self.bot.guilds:
            try:
                afk_settings = await self._get_afk_settings(guild.id)
                
                if not afk_settings["enabled"]:
                    continue
                
                timeout_minutes = afk_settings["timeout_minutes"]
                ignored = set(afk_settings["ignored_channels"])
                
                # Check all voice channels
                for vc in guild.voice_channels:
                    if vc.id in ignored:
                        continue
                    
                    for member in vc.members:
                        if member.bot:
                            continue
                        
                        key = (guild.id, member.id)
                        
                        # Skip if already being checked
                        if key in self.pending_checks:
                            continue
                        
                        # Get last activity time (or set if not tracked)
                        last_active = self.user_activity.get(key)
                        if last_active is None:
                            self._update_activity(guild.id, member.id)
                            continue
                        
                        # Check if user is alone in the VC (special 5-minute timeout)
                        non_bot_members = [m for m in vc.members if not m.bot]
                        is_alone = len(non_bot_members) == 1
                        
                        # Use 5 minutes for solo users, normal timeout for others
                        check_timeout = 5 if is_alone else timeout_minutes
                        
                        # Check if inactive for too long
                        inactive_time = (now - last_active).total_seconds() / 60
                        if inactive_time >= check_timeout:
                            # Start AFK check
                            self.pending_checks.add(key)
                            asyncio.create_task(self._perform_afk_check(member, vc, afk_settings))
            
            except Exception as e:
                print(f"[VoiceAFK] Error checking guild {guild.id}: {e}")
    
    @check_inactive_users.before_loop
    async def before_check_inactive(self):
        await self.bot.wait_until_ready()
    
    async def _generate_tts(self, text: str, filename: str) -> Optional[str]:
        """Generate TTS audio file"""
        filepath = os.path.join(self.temp_dir, filename)
        
        try:
            if TTS_ENGINE == "gtts":
                tts = gTTS(text=text, lang='en')
                tts.save(filepath)
                return filepath
            elif TTS_ENGINE == "edge_tts":
                import edge_tts
                communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
                await communicate.save(filepath)
                return filepath
            else:
                return None
        except Exception as e:
            print(f"[VoiceAFK] TTS generation failed: {e}")
            return None
    
    async def _perform_afk_check(self, member: discord.Member, channel: discord.VoiceChannel, settings: dict):
        """Perform an AFK check on a user"""
        key = (member.guild.id, member.id)
        
        try:
            # Check if member is still in VC
            if not member.voice or member.voice.channel != channel:
                return
            
            # Generate TTS - updated message to mention speaking
            tts_text = f"Hello {member.display_name}! Are you still there? Say something, toggle your mic, or click the button to confirm you're here. You have {settings['response_timeout']} seconds."
            tts_file = await self._generate_tts(tts_text, f"afk_check_{member.id}.mp3")
            
            voice_client = None
            view = None
            msg = None
            voice_activity_detected = False
            
            # Create an event to signal voice activity
            voice_event = asyncio.Event()
            
            async def on_voice_change(m, before, after):
                """Callback for voice state changes during check"""
                nonlocal voice_activity_detected
                if m.id == member.id:
                    # Check if user made any voice activity
                    if before.self_mute != after.self_mute or \
                       before.self_deaf != after.self_deaf or \
                       before.mute != after.mute or \
                       before.deaf != after.deaf:
                        voice_activity_detected = True
                        voice_event.set()
                        if view:
                            view.mark_spoke()
            
            # Temporarily add a voice state listener
            original_listeners = self.bot.extra_events.get('on_voice_state_update', []).copy()
            
            @self.bot.event
            async def on_voice_state_update(m, before, after):
                # Call our check
                await on_voice_change(m, before, after)
                # Also call any existing handlers
                for listener in original_listeners:
                    try:
                        await listener(m, before, after)
                    except:
                        pass
                # Also update our activity tracking
                if not m.bot:
                    if after.channel is None:
                        self._remove_activity(m.guild.id, m.id)
                    elif before.channel != after.channel or \
                         before.self_mute != after.self_mute or \
                         before.self_deaf != after.self_deaf or \
                         before.self_stream != after.self_stream or \
                         before.self_video != after.self_video:
                        self._update_activity(m.guild.id, m.id)
            
            try:
                # Join the voice channel
                voice_client = await channel.connect()
                
                # Play TTS if available
                if tts_file and os.path.exists(tts_file):
                    audio_source = discord.FFmpegPCMAudio(tts_file)
                    voice_client.play(audio_source)
                    
                    # Wait for audio to finish
                    while voice_client.is_playing():
                        await asyncio.sleep(0.5)
                
                # Find a text channel to send the confirmation button - prioritize DM, then fallback channel
                # Try to DM the user first
                text_channel = None
                dm_mode = False
                
                try:
                    dm_channel = await member.create_dm()
                    # Test if we can send
                    view = AFKConfirmButton(self, member, timeout=settings["response_timeout"])
                    
                    embed = discord.Embed(
                        title="🎤 AFK Check",
                        description=f"You have been inactive in **{channel.name}** ({member.guild.name}) for a while.\n\n"
                                    f"**Respond in one of these ways within {settings['response_timeout']} seconds:**\n"
                                    f"• 🎙️ Say something in voice chat\n"
                                    f"• 🔇 Toggle your mute/unmute\n"
                                    f"• ✅ Click the button below\n\n"
                                    f"If you don't respond, you will be disconnected.",
                        color=0xFFAA00,
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    msg = await dm_channel.send(embed=embed, view=view)
                    dm_mode = True
                except:
                    # DM failed, try fallback channel (1388268039773884591) or any text channel
                    fallback_channel_id = 1388268039773884591
                    text_channel = member.guild.get_channel(fallback_channel_id)
                    
                    if not text_channel:
                        # Find any text channel the member can read
                        for tc in member.guild.text_channels:
                            if tc.permissions_for(member).read_messages:
                                text_channel = tc
                                break
                    
                    if text_channel:
                        view = AFKConfirmButton(self, member, timeout=settings["response_timeout"])
                        
                        embed = discord.Embed(
                            title="🎤 AFK Check",
                            description=f"{member.mention}, you have been inactive in **{channel.name}** for a while.\n\n"
                                        f"**Respond in one of these ways within {settings['response_timeout']} seconds:**\n"
                                        f"• 🎙️ Say something in voice chat\n"
                                        f"• 🔇 Toggle your mute/unmute\n"
                                        f"• ✅ Click the button below\n\n"
                                        f"If you don't respond, you will be disconnected.",
                            color=0xFFAA00,
                            timestamp=datetime.now(timezone.utc)
                        )
                        
                        msg = await text_channel.send(
                            content=member.mention,
                            embed=embed,
                            view=view
                        )
                    
                    # Wait for either button click, voice activity, or timeout
                    try:
                        # Wait for whichever happens first
                        done, pending = await asyncio.wait(
                            [
                                asyncio.create_task(view.wait()),
                                asyncio.create_task(voice_event.wait())
                            ],
                            timeout=settings["response_timeout"],
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        
                        # Cancel pending tasks
                        for task in pending:
                            task.cancel()
                        
                    except asyncio.TimeoutError:
                        pass
                    
                    # Delete the message
                    try:
                        await msg.delete()
                    except:
                        pass
                    
                    # Check result - confirmed via button OR voice activity
                    if view.confirmed or voice_activity_detected:
                        # User confirmed, update their activity
                        self._update_activity(member.guild.id, member.id)
                        method = "voice activity" if voice_activity_detected else "button"
                        print(f"[VoiceAFK] {member} confirmed presence in {channel.name} via {method}")
                        
                        # Play TTS confirmation "Ok, just checking!"
                        try:
                            confirm_tts_file = await self._generate_tts(
                                f"Okay, just checking! Thanks for confirming, {member.display_name}.",
                                f"afk_confirm_{member.id}.mp3"
                            )
                            if confirm_tts_file and os.path.exists(confirm_tts_file) and voice_client and voice_client.is_connected():
                                audio_source = discord.FFmpegPCMAudio(confirm_tts_file)
                                voice_client.play(audio_source)
                                
                                # Wait for audio to finish
                                while voice_client.is_playing():
                                    await asyncio.sleep(0.5)
                                
                                # Clean up confirm TTS file
                                try:
                                    os.remove(confirm_tts_file)
                                except:
                                    pass
                        except Exception as e:
                            print(f"[VoiceAFK] Failed to play confirmation TTS: {e}")
                        
                        # Send confirmation to the text channel briefly
                        try:
                            confirm_msg = await text_channel.send(
                                embed=discord.Embed(
                                    title="✅ Presence Confirmed",
                                    description=f"{member.mention} confirmed they're still here!",
                                    color=0x00FF00
                                )
                            )
                            await asyncio.sleep(5)
                            await confirm_msg.delete()
                        except:
                            pass
                    else:
                        # User didn't respond, kick them
                        if member.voice and member.voice.channel:
                            try:
                                await member.move_to(None, reason="AFK detection - No response to activity check")
                                
                                # Try to DM them
                                try:
                                    dm_embed = discord.Embed(
                                        title="🔇 Disconnected for Inactivity",
                                        description=f"You were disconnected from **{channel.name}** in **{member.guild.name}** for being AFK.\n\n"
                                                    f"You didn't respond to the activity check in time. Feel free to rejoin when you're back!",
                                        color=0xFF6600,
                                        timestamp=datetime.now(timezone.utc)
                                    )
                                    await member.send(embed=dm_embed)
                                except:
                                    pass
                                
                                print(f"[VoiceAFK] Kicked {member} from {channel.name} for inactivity")
                            except discord.Forbidden:
                                print(f"[VoiceAFK] Failed to kick {member} - no permissions")
                else:
                    # No text channel found - just listen for voice activity only
                    try:
                        await asyncio.wait_for(voice_event.wait(), timeout=settings["response_timeout"])
                        self._update_activity(member.guild.id, member.id)
                        print(f"[VoiceAFK] {member} confirmed presence in {channel.name} via voice activity")
                    except asyncio.TimeoutError:
                        if member.voice and member.voice.channel:
                            try:
                                await member.move_to(None, reason="AFK detection - No response to activity check")
                            except:
                                pass
            
            finally:
                # Disconnect from voice
                if voice_client and voice_client.is_connected():
                    await voice_client.disconnect()
                
                # Clean up TTS file
                if tts_file and os.path.exists(tts_file):
                    try:
                        os.remove(tts_file)
                    except:
                        pass
        
        except Exception as e:
            print(f"[VoiceAFK] Error during AFK check for {member}: {e}")
        
        finally:
            # Remove from pending checks
            self.pending_checks.discard(key)
    
    # ========== User AFK Status System ==========
    # NOTE: The /afk command is defined in utility.py - this is just the on_message handler
    
    # @app_commands.command(name="afk", description="💤 Set yourself as AFK with a reason")
    # @app_commands.describe(
    #     reason="Why are you AFK? (optional)"
    # )
    # async def afk_status(
    #     self,
    #     interaction: discord.Interaction,
    #     reason: Optional[str] = "AFK"
    # ):
    #     """Set yourself as AFK - when someone pings you, they'll see your AFK status"""
    #     guild_id = interaction.guild.id
    #     user_id = interaction.user.id
    #     
    #     # Store AFK status in database
    #     settings = await self.bot.db.get_settings(guild_id)
    #     afk_users = settings.get("afk_users", {})
    #     
    #     # Convert to dict if it's a string (JSON issue)
    #     if isinstance(afk_users, str):
    #         import json
    #         try:
    #             afk_users = json.loads(afk_users)
    #         except:
    #             afk_users = {}
    #     
    #     afk_users[str(user_id)] = {
    #         "reason": reason[:200] if reason else "AFK",  # Limit reason length
    #         "since": datetime.now(timezone.utc).isoformat()
    #     }
    #     
    #     settings["afk_users"] = afk_users
    #     await self.bot.db.update_settings(guild_id, settings)
    #     
    #     embed = discord.Embed(
    #         title="💤 AFK Set",
    #         description=f"You are now AFK: **{reason}**\n\nI'll let people know when they ping you!",
    #         color=0x9966FF,
    #         timestamp=datetime.now(timezone.utc)
    #     )
    #     embed.set_footer(text="Send a message to remove your AFK status")
    #     
    #     await interaction.response.send_message(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle AFK status - notify when AFK user is pinged, remove AFK when they speak"""
        if message.author.bot or not message.guild:
            return
        
        guild_id = message.guild.id
        user_id = message.author.id
        
        try:
            settings = await self.bot.db.get_settings(guild_id)
            afk_users = settings.get("afk_users", {})
            
            # Convert to dict if needed
            if isinstance(afk_users, str):
                import json
                try:
                    afk_users = json.loads(afk_users)
                except:
                    afk_users = {}
            
            # Check if the message author was AFK - remove their AFK status
            if str(user_id) in afk_users:
                del afk_users[str(user_id)]
                settings["afk_users"] = afk_users
                await self.bot.db.update_settings(guild_id, settings)
                
                try:
                    await message.reply(
                        embed=discord.Embed(
                            title="👋 Welcome Back!",
                            description=f"{message.author.mention}, your AFK status has been removed.",
                            color=0x00FF00
                        ),
                        delete_after=5
                    )
                except:
                    pass
                return
            
            # Check if any mentioned users are AFK
            afk_mentions = []
            for mentioned_user in message.mentions:
                if str(mentioned_user.id) in afk_users:
                    afk_data = afk_users[str(mentioned_user.id)]
                    reason = afk_data.get("reason", "AFK")
                    since_str = afk_data.get("since", "")
                    
                    # Calculate how long they've been AFK
                    try:
                        since = datetime.fromisoformat(since_str)
                        delta = datetime.now(timezone.utc) - since
                        
                        if delta.total_seconds() < 60:
                            time_ago = "just now"
                        elif delta.total_seconds() < 3600:
                            mins = int(delta.total_seconds() / 60)
                            time_ago = f"{mins} minute{'s' if mins != 1 else ''} ago"
                        elif delta.total_seconds() < 86400:
                            hours = int(delta.total_seconds() / 3600)
                            time_ago = f"{hours} hour{'s' if hours != 1 else ''} ago"
                        else:
                            days = int(delta.total_seconds() / 86400)
                            time_ago = f"{days} day{'s' if days != 1 else ''} ago"
                    except:
                        time_ago = "some time ago"
                    
                    afk_mentions.append(f"💤 **{mentioned_user.display_name}** is AFK: {reason} (set {time_ago})")
            
            if afk_mentions:
                embed = discord.Embed(
                    description="\n".join(afk_mentions),
                    color=0x9966FF
                )
                await message.reply(embed=embed, delete_after=10)
        
        except Exception as e:
            print(f"[VoiceAFK] Error in AFK message handler: {e}")
    
    # ========== Admin AFK Detection Methods (called from /vc) ==========
    # These methods are public so they can be called from the Voice cog
    
    async def afk_settings(self, interaction: discord.Interaction):
        """View AFK detection settings"""
        settings = await self._get_afk_settings(interaction.guild.id)
        
        status = "✅ Enabled" if settings["enabled"] else "❌ Disabled"
        
        ignored_list = []
        for ch_id in settings["ignored_channels"]:
            ch = interaction.guild.get_channel(ch_id)
            if ch:
                ignored_list.append(ch.mention)
        
        embed = discord.Embed(
            title="🎤 Voice AFK Detection Settings",
            color=0x00AAFF,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Timeout", value=f"{settings['timeout_minutes']} minutes", inline=True)
        embed.add_field(name="Response Time", value=f"{settings['response_timeout']} seconds", inline=True)
        embed.add_field(
            name="Ignored Channels",
            value=", ".join(ignored_list) if ignored_list else "None",
            inline=False
        )
        embed.add_field(
            name="TTS Engine",
            value=f"✅ {TTS_ENGINE}" if TTS_AVAILABLE else "❌ Not available (install gTTS or edge-tts)",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def afk_enable(self, interaction: discord.Interaction):
        """Enable AFK detection"""
        if not TTS_AVAILABLE:
            return await interaction.response.send_message(
                embed=ModEmbed.warning(
                    "TTS Not Available",
                    "AFK detection requires a TTS library. Install with:\n`pip install gTTS` or `pip install edge-tts`\n\n"
                    "The feature will still work but without voice announcements."
                ),
                ephemeral=True
            )
        
        await self._update_afk_settings(interaction.guild.id, detection_enabled=True)
        
        await interaction.response.send_message(
            embed=ModEmbed.success("AFK Detection Enabled", "Voice AFK detection is now **enabled** for this server."),
            ephemeral=True
        )
    
    async def afk_disable(self, interaction: discord.Interaction):
        """Disable AFK detection"""
        await self._update_afk_settings(interaction.guild.id, detection_enabled=False)
        
        # Clear any pending checks for this guild
        to_remove = [k for k in self.pending_checks if k[0] == interaction.guild.id]
        for k in to_remove:
            self.pending_checks.discard(k)
        
        # Clear activity tracking for this guild
        to_remove = [k for k in self.user_activity.keys() if k[0] == interaction.guild.id]
        for k in to_remove:
            self.user_activity.pop(k, None)
        
        await interaction.response.send_message(
            embed=ModEmbed.success("AFK Detection Disabled", "Voice AFK detection is now **disabled** for this server."),
            ephemeral=True
        )
    
    async def afk_timeout(self, interaction: discord.Interaction, minutes: int):
        """Set the AFK timeout"""
        if minutes < 1 or minutes > 120:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Invalid Value", "Timeout must be between 1 and 120 minutes."),
                ephemeral=True
            )
        
        await self._update_afk_settings(interaction.guild.id, timeout_minutes=minutes)
        
        await interaction.response.send_message(
            embed=ModEmbed.success("Timeout Updated", f"AFK timeout set to **{minutes} minutes**."),
            ephemeral=True
        )
    
    async def afk_ignore(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        """Add a channel to the ignore list"""
        settings = await self._get_afk_settings(interaction.guild.id)
        ignored = settings["ignored_channels"]
        
        if channel.id in ignored:
            return await interaction.response.send_message(
                embed=ModEmbed.warning("Already Ignored", f"{channel.mention} is already ignored."),
                ephemeral=True
            )
        
        ignored.append(channel.id)
        await self._update_afk_settings(interaction.guild.id, ignored_channels=ignored)
        
        await interaction.response.send_message(
            embed=ModEmbed.success("Channel Ignored", f"{channel.mention} will be ignored for AFK detection."),
            ephemeral=True
        )
    
    async def afk_unignore(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        """Remove a channel from the ignore list"""
        settings = await self._get_afk_settings(interaction.guild.id)
        ignored = settings["ignored_channels"]
        
        if channel.id not in ignored:
            return await interaction.response.send_message(
                embed=ModEmbed.warning("Not Ignored", f"{channel.mention} is not in the ignore list."),
                ephemeral=True
            )
        
        ignored.remove(channel.id)
        await self._update_afk_settings(interaction.guild.id, ignored_channels=ignored)
        
        await interaction.response.send_message(
            embed=ModEmbed.success("Channel Unignored", f"{channel.mention} will now be monitored for AFK detection."),
            ephemeral=True
        )
    
    async def afk_check_user(self, interaction: discord.Interaction, user: discord.Member):
        """Manually trigger an AFK check on a user"""
        if not user.voice or not user.voice.channel:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not in Voice", f"{user.mention} is not in a voice channel."),
                ephemeral=True
            )
        
        if user.bot:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Invalid Target", "Cannot check bots for AFK."),
                ephemeral=True
            )
        
        key = (interaction.guild.id, user.id)
        if key in self.pending_checks:
            return await interaction.response.send_message(
                embed=ModEmbed.warning("Already Checking", f"{user.mention} is already being checked for AFK."),
                ephemeral=True
            )
        
        await interaction.response.send_message(
            embed=ModEmbed.success("AFK Check Started", f"Starting AFK check for {user.mention} in {user.voice.channel.mention}."),
            ephemeral=True
        )
        
        settings = await self._get_afk_settings(interaction.guild.id)
        self.pending_checks.add(key)
        asyncio.create_task(self._perform_afk_check(user, user.voice.channel, settings))


async def setup(bot):
    await bot.add_cog(VoiceAFK(bot))

