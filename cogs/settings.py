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
# GENERAL SETTINGS (EDITABLE)
# ==============================================================================

class GeneralSettingsView(BaseSettingsView):
    def __init__(self, cog, guild, settings):
        super().__init__(cog, guild, "general")
        self.settings = settings

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(title="⚙️ General Settings", color=Colors.INFO, timestamp=datetime.datetime.now(timezone.utc))
        
        # Mute Role
        mute_role_id = self.settings.get("mute_role")
        mute_role = self.guild.get_role(mute_role_id).mention if mute_role_id and self.guild.get_role(mute_role_id) else "`Not Set`"
        
        # Manager Role
        manager_role_id = self.settings.get("manager_role")
        manager_role = self.guild.get_role(manager_role_id).mention if manager_role_id and self.guild.get_role(manager_role_id) else "`Not Set`"

        # Channels
        mod_log = self.guild.get_channel(self.settings.get("mod_log_channel")).mention if self.settings.get("mod_log_channel") else "`Not Set`"
        forum_alerts = self.guild.get_channel(self.settings.get("forum_alerts_channel")).mention if self.settings.get("forum_alerts_channel") else "`Using Mod Log`"
        
        embed.add_field(name="🔇 Mute Role", value=mute_role, inline=True)
        embed.add_field(name="👔 Manager Role", value=manager_role, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True) # Spacer
        embed.add_field(name="📜 Mod Log", value=mod_log, inline=True)
        embed.add_field(name="🚨 Forum Alerts", value=forum_alerts, inline=True)
        
        embed.set_footer(text="Select options below to change settings.")
        return embed

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Select Mute Role", min_values=1, max_values=1, row=1)
    async def mute_role_select(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.settings["mute_role"] = select.values[0].id
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Select Manager Role", min_values=1, max_values=1, row=2)
    async def manager_role_select(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.settings["manager_role"] = select.values[0].id
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Select Mod Log Channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text], row=3)
    async def mod_log_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.settings["mod_log_channel"] = select.values[0].id
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Select Forum Alerts Channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text], row=4)
    async def forum_alerts_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.settings["forum_alerts_channel"] = select.values[0].id
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


# ==============================================================================
# AUTOMOD SETTINGS (ENHANCED)
# ==============================================================================

class AutoModSettingsView(BaseSettingsView):
    def __init__(self, cog, guild, settings):
        super().__init__(cog, guild, "automod")
        self.settings = settings
        self._update_buttons()

    def _update_buttons(self):
        is_enabled = self.settings.get("automod_enabled", False)
        self.toggle_btn.style = discord.ButtonStyle.success if is_enabled else discord.ButtonStyle.danger
        self.toggle_btn.label = "AutoMod: ON" if is_enabled else "AutoMod: OFF"
        
        ai_enabled = self.settings.get("automod_ai_enabled", False)
        self.ai_btn.style = discord.ButtonStyle.success if ai_enabled else discord.ButtonStyle.secondary
        self.ai_btn.label = "AI: ON" if ai_enabled else "AI: OFF"

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🛡️ AutoMod Configuration", color=Colors.WARNING, timestamp=datetime.datetime.now(timezone.utc))
        
        status = "✅ Enabled" if self.settings.get("automod_enabled") else "❌ Disabled"
        punishment = self.settings.get("automod_punishment", "warn").title()
        bad_words_count = len(self.settings.get("automod_badwords", []))
        
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Punishment", value=punishment, inline=True)
        embed.add_field(name="Bad Words", value=f"{bad_words_count} words", inline=True)
        
        # Ignored
        ignored_ch = len(self.settings.get("ignored_channels", []))
        ignored_roles = len(self.settings.get("ignored_roles", []))
        embed.add_field(name="Ignored", value=f"{ignored_ch} chans, {ignored_roles} roles", inline=False)
        
        return embed

    @discord.ui.button(label="Toggle AutoMod", custom_id="toggle_automod", row=1)
    async def toggle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_state = not self.settings.get("automod_enabled", False)
        self.settings["automod_enabled"] = new_state
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        self._update_buttons()
        interaction.message.embeds[0].color = Colors.SUCCESS if new_state else Colors.ERROR
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Toggle AI", custom_id="toggle_ai", row=1)
    async def ai_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_state = not self.settings.get("automod_ai_enabled", False)
        self.settings["automod_ai_enabled"] = new_state
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Edit Bad Words", style=discord.ButtonStyle.secondary, row=1)
    async def badwords_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BadWordsModal(self))

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

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Ignored Channels (Multi)", min_values=0, max_values=25, row=3)
    async def ignored_channels_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.settings["ignored_channels"] = [c.id for c in select.values]
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Ignored Roles (Multi)", min_values=0, max_values=25, row=4)
    async def ignored_roles_select(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.settings["ignored_roles"] = [r.id for r in select.values]
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class BadWordsModal(discord.ui.Modal, title="Edit Bad Words"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        current_words = view.settings.get("automod_badwords", [])
        
        self.words = discord.ui.TextInput(
            label="Bad Words (comma separated)",
            style=discord.TextStyle.paragraph,
            placeholder="word1, word2, bad phrase",
            default=", ".join(current_words),
            required=False,
            max_length=4000
        )
        self.add_item(self.words)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.words.value
        if not raw.strip():
            new_list = []
        else:
            new_list = [w.strip() for w in raw.split(",") if w.strip()]
        
        self.view.settings["automod_badwords"] = new_list
        await self.view.cog.bot.db.update_settings(interaction.guild_id, self.view.settings)
        await interaction.response.edit_message(embed=self.view.get_embed(), view=self.view)


# ==============================================================================
# LOGGING SETTINGS
# ==============================================================================

class LoggingSettingsView(BaseSettingsView):
    def __init__(self, cog, guild, settings):
        super().__init__(cog, guild, "logging")
        self.settings = settings

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(title="📝 Logging Configuration", color=Colors.INFO, timestamp=datetime.datetime.now(timezone.utc))
        
        def get_ch(key):
            cid = self.settings.get(key)
            return f"<#{cid}>" if cid else "`Disabled`"

        embed.add_field(name="🛡️ Mod Actions", value=get_ch("mod_log_channel"), inline=True)
        embed.add_field(name="⚙️ Audits", value=get_ch("audit_log_channel"), inline=True)
        embed.add_field(name="💬 Messages", value=get_ch("message_log_channel"), inline=True)
        embed.add_field(name="🔊 Voice", value=get_ch("voice_log_channel"), inline=True)
        
        embed.description = "Use the dropdown below to set a log channel to the **current channel**."
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
            return await interaction.response.send_message("To disable, select a log type then run /settings again (feature pending full disable UI).", ephemeral=True)
        
        self.settings[log_type] = interaction.channel_id
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        
        logging_cog = self.cog.bot.get_cog("Logging")
        if logging_cog:
            cache_key = log_type.replace("_log_channel", "")
            await logging_cog._channel_cache.set(self.guild.id, cache_key, interaction.channel_id)

        await interaction.response.edit_message(embed=self.get_embed(), view=self)


# ==============================================================================
# VOICE SETTINGS (EDITABLE)
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
        embed = discord.Embed(title="🔊 Voice & AFK Settings", color=Colors.INFO, timestamp=datetime.datetime.now(timezone.utc))
        
        status = "✅ Enabled" if self.settings.get("afk_detection_enabled") else "❌ Disabled"
        timeout = f"{self.settings.get('afk_timeout_minutes', 15)} mins"
        response = f"{self.settings.get('afk_response_timeout', 30)} sec"
        ignored = len(self.settings.get("afk_ignored_channels", []))
        
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Inactive Timeout", value=timeout, inline=True)
        embed.add_field(name="Response Time", value=response, inline=True)
        embed.add_field(name="Ignored Channels", value=f"{ignored}", inline=True)
        return embed

    @discord.ui.button(label="Toggle AFK Detection", custom_id="toggle_afk", row=1)
    async def afk_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_state = not self.settings.get("afk_detection_enabled", False)
        self.settings["afk_detection_enabled"] = new_state
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @discord.ui.button(label="Set Timeouts", style=discord.ButtonStyle.secondary, row=1)
    async def timeout_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VoiceTimeoutModal(self))

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Select Ignored Voice Channels", min_values=0, max_values=25, channel_types=[discord.ChannelType.voice], row=2)
    async def ignored_vc_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.settings["afk_ignored_channels"] = [c.id for c in select.values]
        await self.cog.bot.db.update_settings(self.guild.id, self.settings)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class VoiceTimeoutModal(discord.ui.Modal, title="Configure AFK Timeouts"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.afk_time = discord.ui.TextInput(
            label="Inactive Timeout (minutes)", placeholder="15",
            default=str(view.settings.get("afk_timeout_minutes", 15)),
            min_length=1, max_length=3
        )
        self.response_time = discord.ui.TextInput(
            label="Response Time (seconds)", placeholder="30",
            default=str(view.settings.get("afk_response_timeout", 30)),
            min_length=1, max_length=3
        )
        self.add_item(self.afk_time)
        self.add_item(self.response_time)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mins = int(self.afk_time.value)
            secs = int(self.response_time.value)
            if not (1 <= mins <= 120): raise ValueError("Minutes must be 1-120")
            if not (10 <= secs <= 300): raise ValueError("Seconds must be 10-300")
                
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
        view = GeneralSettingsView(self, interaction.guild, settings)
        await interaction.followup.send(embed=view.get_embed(), view=view)

async def setup(bot):
    await bot.add_cog(Settings(bot))
