"""
Unified Settings Dashboard
Centralized configuration system for all bot features
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List, Literal, Any
import datetime
from datetime import timezone

from utils.embeds import ModEmbed, Colors
from utils.checks import is_admin
from config import Config

# ==============================================================================
# UI COMPONENTS
# ==============================================================================

class SettingsCategorySelect(discord.ui.Select):
    """Dropdown to select the settings category"""
    
    def __init__(self, current_category: str = None):
        options = [
            discord.SelectOption(
                label="General", 
                description="Core settings, Roles, Permissions", 
                emoji="⚙️",
                value="general",
                default=current_category == "general"
            ),
            discord.SelectOption(
                label="AutoMod", 
                description="Filters, Punishments, AI Detection", 
                emoji="🛡️",
                value="automod",
                default=current_category == "automod"
            ),
            discord.SelectOption(
                label="Logging", 
                description="Log Channels and Events", 
                emoji="📝",
                value="logging",
                default=current_category == "logging"
            ),
            discord.SelectOption(
                label="Voice & AFK", 
                description="Voice Tracking, AFK Detection", 
                emoji="🔊",
                value="voice",
                default=current_category == "voice"
            ),
        ]
        super().__init__(placeholder="Select a category to configure...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await self.view.switch_category(interaction, self.values[0])


class BaseSettingsView(discord.ui.View):
    """Base view for all settings dashboards"""
    
    def __init__(self, cog, guild: discord.Guild, category: str):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild = guild
        self.category = category
        
        # Add the category selector to the top of every view
        self.add_item(SettingsCategorySelect(current_category=category))

    async def switch_category(self, interaction: discord.Interaction, new_category: str):
        """Switch to a different settings category"""
        if new_category == self.category:
            return await interaction.response.defer()
            
        settings = await self.cog.bot.db.get_settings(self.guild.id)
        
        if new_category == "general":
            view = GeneralSettingsView(self.cog, self.guild, settings)
            embed = view.get_embed()
        elif new_category == "automod":
            view = AutoModSettingsView(self.cog, self.guild, settings)
            embed = view.get_embed()
        elif new_category == "logging":
            view = LoggingSettingsView(self.cog, self.guild, settings)
            embed = view.get_embed()
        elif new_category == "voice":
            view = VoiceSettingsView(self.cog, self.guild, settings)
            embed = view.get_embed()
        else:
            return
            
        await interaction.response.edit_message(embed=embed, view=view)


# ==============================================================================
# GENERAL SETTINGS
# ==============================================================================

class GeneralSettingsView(BaseSettingsView):
    def __init__(self, cog, guild, settings):
        super().__init__(cog, guild, "general")
        self.settings = settings

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(title="⚙️ General Settings", color=Colors.info, timestamp=datetime.datetime.now(timezone.utc))
        
        # Mute Role
        mute_role_id = self.settings.get("mute_role")
        mute_role = self.guild.get_role(mute_role_id).mention if mute_role_id and self.guild.get_role(mute_role_id) else "`Not Set`"
        
        # Mod Log (Main)
        mod_log_id = self.settings.get("mod_log_channel")
        mod_log = self.guild.get_channel(mod_log_id).mention if mod_log_id else "`Not Set`"
        
        # Forum Alerts
        forum_alerts_id = self.settings.get("forum_alerts_channel")
        forum_alerts = self.guild.get_channel(forum_alerts_id).mention if forum_alerts_id else "`Using Mod Log`"
        
        embed.add_field(name="🔇 Mute Role", value=mute_role, inline=True)
        embed.add_field(name="📜 Mod Log Channel", value=mod_log, inline=True)
        embed.add_field(name="🚨 Forum Alerts", value=forum_alerts, inline=True)
        embed.set_footer(text="Use the commands /setup or specialized commands to change these IDs for now.")
        return embed


# ==============================================================================
# AUTOMOD SETTINGS
# ==============================================================================

class AutoModSettingsView(BaseSettingsView):
    def __init__(self, cog, guild, settings):
        super().__init__(cog, guild, "automod")
        self.settings = settings
        self._update_buttons()

    def _update_buttons(self):
        # Enable/Disable Toggle
        is_enabled = self.settings.get("automod_enabled", False)
        self.toggle_btn.style = discord.ButtonStyle.success if is_enabled else discord.ButtonStyle.danger
        self.toggle_btn.label = "AutoMod: ON" if is_enabled else "AutoMod: OFF"
        
        # AI Toggle
        ai_enabled = self.settings.get("automod_ai_enabled", False)
        self.ai_btn.style = discord.ButtonStyle.success if ai_enabled else discord.ButtonStyle.secondary
        self.ai_btn.label = "AI Detection: ON" if ai_enabled else "AI Detection: OFF"

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🛡️ AutoMod Configuration", color=Colors.warning, timestamp=datetime.datetime.now(timezone.utc))
        
        status = "✅ Enabled" if self.settings.get("automod_enabled") else "❌ Disabled"
        punishment = self.settings.get("automod_punishment", "warn").title()
        
        filters = []
        if self.settings.get("automod_badwords"): filters.append(f"📝 Bad Words ({len(self.settings['automod_badwords'])})")
        if self.settings.get("automod_links_enabled"): filters.append("🔗 Links")
        if self.settings.get("automod_invites_enabled"): filters.append("📨 Invites")
        if self.settings.get("automod_spam_threshold", 0) > 0: filters.append("📢 Spam")
        if self.settings.get("automod_caps_percentage", 0) > 0: filters.append("🔠 Caps")
        if self.settings.get("automod_ai_enabled"): filters.append("🤖 AI Analysis")
        
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Punishment", value=punishment, inline=True)
        embed.add_field(name="Active Filters", value=", ".join(filters) if filters else "None", inline=False)
        return embed

    @discord.ui.button(label="Toggle AutoMod", custom_id="toggle_automod")
    async def toggle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_state = not self.settings.get("automod_enabled", False)
        self.settings["automod_enabled"] = new_state
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Toggle AI", custom_id="toggle_ai", row=1)
    async def ai_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_state = not self.settings.get("automod_ai_enabled", False)
        self.settings["automod_ai_enabled"] = new_state
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.select(
        placeholder="Select Punishment Type",
        options=[
            discord.SelectOption(label="Warn", value="warn", emoji="⚠️"),
            discord.SelectOption(label="Mute", value="mute", emoji="🔇"),
            discord.SelectOption(label="Kick", value="kick", emoji="👢"),
            discord.SelectOption(label="Ban", value="ban", emoji="🔨"),
        ],
        row=2
    )
    async def punishment_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.settings["automod_punishment"] = select.values[0]
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


# ==============================================================================
# LOGGING SETTINGS
# ==============================================================================

class LoggingSettingsView(BaseSettingsView):
    def __init__(self, cog, guild, settings):
        super().__init__(cog, guild, "logging")
        self.settings = settings

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(title="📝 Logging Configuration", color=Colors.info, timestamp=datetime.datetime.now(timezone.utc))
        
        def get_ch(key):
            cid = self.settings.get(key)
            return f"<#{cid}>" if cid else "`Disabled`"

        embed.add_field(name="🛡️ Mod Actions", value=get_ch("mod_log_channel"), inline=True)
        embed.add_field(name="⚙️ Audits", value=get_ch("audit_log_channel"), inline=True)
        embed.add_field(name="💬 Messages", value=get_ch("message_log_channel"), inline=True)
        embed.add_field(name="🔊 Voice", value=get_ch("voice_log_channel"), inline=True)
        
        embed.description = "Use the dropdown below to set a log channel to the **current channel** you are in."
        return embed

    @discord.ui.select(
        placeholder="Set Current Channel As...",
        options=[
            discord.SelectOption(label="Mod Logs", value="mod_log_channel", emoji="🛡️"),
            discord.SelectOption(label="Audit Logs", value="audit_log_channel", emoji="⚙️"),
            discord.SelectOption(label="Message Logs", value="message_log_channel", emoji="💬"),
            discord.SelectOption(label="Voice Logs", value="voice_log_channel", emoji="🔊"),
            discord.SelectOption(label="DISABLE Logging Feature", value="disable", emoji="❌"),
        ]
    )
    async def log_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        log_type = select.values[0]
        
        if log_type == "disable":
            # Ask which one to disable? Or simple disable menu?
            # For simplicity, we won't implement complex disable logic here to keep it concise.
            return await interaction.response.send_message("Use `/logging` command to disable specific logs.", ephemeral=True)
        
        self.settings[log_type] = interaction.channel_id
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        
        # Update cache in Logging cog if it exists
        logging_cog = self.cog.bot.get_cog("Logging")
        if logging_cog:
            # Map setting key to cache key (e.g. 'mod_log_channel' -> 'mod')
            cache_key = log_type.replace("_log_channel", "")
            await logging_cog._channel_cache.set(self.guild.id, cache_key, interaction.channel_id)

        await interaction.response.edit_message(embed=self.get_embed(), view=self)


# ==============================================================================
# VOICE SETTINGS
# ==============================================================================

class VoiceSettingsView(BaseSettingsView):
    def __init__(self, cog, guild, settings):
        super().__init__(cog, guild, "voice")
        self.settings = settings
        self._update_buttons()

    def _update_buttons(self):
        enabled = self.settings.get("afk_detection_enabled", False)
        self.afk_btn.style = discord.ButtonStyle.success if enabled else discord.ButtonStyle.danger
        self.afk_btn.label = "AFK Detection: ON" if enabled else "AFK Detection: OFF"

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🔊 Voice & AFK Settings", color=Colors.info, timestamp=datetime.datetime.now(timezone.utc))
        
        status = "✅ Enabled" if self.settings.get("afk_detection_enabled") else "❌ Disabled"
        timeout = f"{self.settings.get('afk_timeout_minutes', 15)} mins"
        response = f"{self.settings.get('afk_response_timeout', 30)} sec"
        
        ignored = len(self.settings.get("afk_ignored_channels", []))
        
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Inactive Timeout", value=timeout, inline=True)
        embed.add_field(name="Response Time", value=response, inline=True)
        embed.add_field(name="Ignored Channels", value=f"{ignored} channels", inline=False)
        return embed

    @discord.ui.button(label="Toggle AFK Detection", custom_id="toggle_afk")
    async def afk_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_state = not self.settings.get("afk_detection_enabled", False)
        self.settings["afk_detection_enabled"] = new_state
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @discord.ui.button(label="Set Timeouts (Modal)", style=discord.ButtonStyle.secondary)
    async def timeout_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VoiceTimeoutModal(self))


class VoiceTimeoutModal(discord.ui.Modal, title="Configure AFK Timeouts"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        
        self.afk_time = discord.ui.TextInput(
            label="Inactive Timeout (minutes)",
            placeholder="15",
            default=str(view.settings.get("afk_timeout_minutes", 15)),
            min_length=1, max_length=3
        )
        self.response_time = discord.ui.TextInput(
            label="Response Time (seconds)",
            placeholder="30",
            default=str(view.settings.get("afk_response_timeout", 30)),
            min_length=1, max_length=3
        )
        self.add_item(self.afk_time)
        self.add_item(self.response_time)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mins = int(self.afk_time.value)
            secs = int(self.response_time.value)
            
            if not (1 <= mins <= 120):
                raise ValueError("Minutes must be 1-120")
            if not (10 <= secs <= 300):
                raise ValueError("Seconds must be 10-300")
                
            self.view.settings["afk_timeout_minutes"] = mins
            self.view.settings["afk_response_timeout"] = secs
            
            await self.view.cog.bot.db.update_settings(interaction.guild_id, self.view.settings)
            
            await interaction.response.edit_message(embed=self.view.get_embed(), view=self.view)
        except ValueError as e:
            await interaction.response.send_message(f"Invalid input: {str(e)}", ephemeral=True)


# ==============================================================================
# SETTINGS COG
# ==============================================================================

class Settings(commands.Cog):
    """Unified Settings Command"""
    
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="settings", description="⚙️ Configure all bot settings in one place")
    @is_admin()
    async def settings(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        settings = await self.bot.db.get_settings(interaction.guild_id)
        
        # Start with General view
        view = GeneralSettingsView(self, interaction.guild, settings)
        await interaction.followup.send(embed=view.get_embed(), view=view)


async def setup(bot):
    await bot.add_cog(Settings(bot))
