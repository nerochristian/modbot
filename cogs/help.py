"""
Advanced Help System with Role-Based Panels
Features:
- Interactive /help with categories, search, and detailed info
- /modpanel - Quick access to moderation tools
- /adminpanel - Server configuration & management
- /ownerpanel - Bot owner controls
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, List, Dict, Any
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import ModEmbed
from utils.checks import is_mod, is_admin, is_bot_owner_id
from config import Config


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _normalize_command_name(value: str) -> str:
    value = (value or "").strip()
    if value.startswith("/"):
        value = value[1:]
    return " ".join(value.lower().split())


def _walk_slash_commands(tree: app_commands.CommandTree) -> list[app_commands.Command | app_commands.Group]:
    cmds: list[app_commands.Command | app_commands.Group] = []
    for cmd in tree.walk_commands():
        if isinstance(cmd, app_commands.ContextMenu):
            continue
        if isinstance(cmd, (app_commands.Command, app_commands.Group)):
            cmds.append(cmd)
    return cmds


def _category_for_command(cmd: app_commands.Command | app_commands.Group | commands.Command) -> str:
    if isinstance(cmd, (app_commands.Command, app_commands.Group)):
        binding = getattr(cmd, "binding", None)
        cog_name = getattr(binding, "__cog_name__", None)
    else:
        cog_name = cmd.cog_name

    if cog_name:
        if cog_name.upper() == cog_name and len(cog_name) <= 4:
            return cog_name
        if cog_name == "AIModeration":
            return "AI Moderation"
        return cog_name
    return "Core"


def _format_invocation(cmd: app_commands.Command | app_commands.Group | commands.Command) -> str:
    if isinstance(cmd, (app_commands.Command, app_commands.Group)):
        return f"/{cmd.qualified_name}"
    return f",{cmd.qualified_name}"


def _chunked(items: list, *, size: int) -> Iterable[list]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _usage_line(cmd: app_commands.Command | commands.Command) -> str:
    parts = [_format_invocation(cmd)]
    
    if isinstance(cmd, (app_commands.Command, app_commands.Group)):
        for p in cmd.parameters:
            if p.required:
                parts.append(f"<{p.name}>")
            else:
                parts.append(f"[{p.name}]")
    else:
        # Prefix command
        for name, param in cmd.clean_params.items():
            if param.default is param.empty:
                parts.append(f"<{name}>")
            else:
                parts.append(f"[{name}]")
                
    return " ".join(parts)


def _parameter_lines(cmd: app_commands.Command | commands.Command) -> str:
    lines: list[str] = []
    
    if isinstance(cmd, (app_commands.Command, app_commands.Group)):
        if not cmd.parameters:
            return "No parameters."
        for p in cmd.parameters:
            desc = (p.description or "No description").strip()
            required = "required" if p.required else "optional"
            lines.append(f"• `{p.name}` ({required}) — {desc}")
    else:
        # Prefix command
        if not cmd.clean_params:
            return "No parameters."
        for name, param in cmd.clean_params.items():
            required = "required" if param.default is param.empty else "optional"
            lines.append(f"• `{name}` ({required})")
            
    return "\n".join(lines)


@dataclass(frozen=True)
class _HelpIndex:
    categories: dict[str, list[app_commands.Command | app_commands.Group | commands.Command]]
    by_name: dict[str, app_commands.Command | app_commands.Group | commands.Command]

    @staticmethod
    def build(
        bot: commands.Bot,
        *,
        include_slash: bool = True,
        include_prefix: bool = True,
    ) -> "_HelpIndex":
        categories: dict[str, list[app_commands.Command | app_commands.Group | commands.Command]] = {}
        by_name: dict[str, app_commands.Command | app_commands.Group | commands.Command] = {}

        if include_slash:
            for cmd in _walk_slash_commands(bot.tree):
                if getattr(cmd, "name", None) in ("help", "modpanel", "adminpanel", "ownerpanel"):
                    continue

                category = _category_for_command(cmd)
                categories.setdefault(category, []).append(cmd)
                by_name[_normalize_command_name(cmd.qualified_name)] = cmd

        if include_prefix:
            for cmd in bot.commands:
                if cmd.hidden:
                    continue

                category = _category_for_command(cmd)
                categories.setdefault(category, []).append(cmd)
                by_name[_normalize_command_name(cmd.qualified_name)] = cmd

                for alias in cmd.aliases:
                    by_name[_normalize_command_name(alias)] = cmd

        for cat in categories:
            categories[cat].sort(key=lambda c: c.qualified_name)

        return _HelpIndex(categories=categories, by_name=by_name)


# =============================================================================
# CATEGORY ICONS
# =============================================================================

CATEGORY_ICONS = {
    "Moderation": "🛡️",
    "Admin": "⚙️",
    "Roles": "🎭",
    "Voice": "🎤",
    "Tickets": "🎫",
    "Staff": "👮",
    "Court": "⚖️",
    "AutoMod": "🤖",
    "AI Moderation": "🧠",
    "Utility": "🔧",
    "Fun": "🎉",
    "Core": "💠",
}

def get_category_icon(category: str) -> str:
    return CATEGORY_ICONS.get(category, "📁")


# =============================================================================
# QUICK REFERENCE DATA
# =============================================================================

MOD_COMMANDS = {
    "Moderation": [
        ("`/warn`", "Warn a user"),
        ("`/kick`", "Kick a user"),
        ("`/ban`", "Ban a user (Senior Mod)"),
        ("`/tempban`", "Temporary ban (Senior Mod)"),
        ("`/timeout`", "Timeout/mute a user"),
        ("`/untimeout`", "Remove timeout"),
        ("`/unban`", "Unban by user ID"),
    ],
    "Channel (`/channel`)": [
        ("`/channel lock`", "Lock a channel"),
        ("`/channel unlock`", "Unlock a channel"),
        ("`/channel slowmode`", "Set slowmode"),
        ("`/channel nuke`", "Clone and delete (Senior Mod)"),
    ],
    "Voice (`/vc`)": [
        ("`/vc mute`", "Server mute user"),
        ("`/vc kick`", "Disconnect from VC"),
        ("`/vc move`", "Move user to channel"),
        ("`/vc moveall`", "Move all users"),
        ("`/vc check`", "Presence check"),
    ],
    "Info (`/info`)": [
        ("`/info user`", "User information"),
        ("`/info server`", "Server information"),
        ("`/info members`", "Member count stats"),
    ],
    "History": [
        ("`/history`", "View user history"),
        ("`/case`", "View specific case"),
        ("`/notes`", "View/add user notes"),
        ("`/purge`", "Bulk delete messages"),
    ],
}

ADMIN_COMMANDS = {
    "Server Setup": [
        ("`/setup`", "Configure bot settings"),
        ("`/setlog`", "Set logging channel"),
        ("`/setmod`", "Set mod role"),
    ],
    "AutoMod": [
        ("`/automod enable`", "Enable automod"),
        ("`/automod status`", "View settings"),
        ("`/automod punishment`", "Set punishment"),
    ],
    "Roles": [
        ("`/roles action:create`", "Create a role"),
        ("`/roles action:delete`", "Delete a role"),
        ("`/roles action:all`", "Give role to all"),
    ],
    "Rules & Guides": [
        ("`/rules action:add`", "Add a rule"),
        ("`/staffguide action:post`", "Post staff guide"),
    ],
}

OWNER_COMMANDS = {
    "Bot Management": [
        ("`!sync`", "Sync slash commands"),
        ("`!reload <cog>`", "Reload a cog"),
        ("`!shutdown`", "Shutdown the bot"),
    ],
    "Debug": [
        ("`!eval`", "Evaluate Python code"),
        ("`!sql`", "Run SQL query"),
        ("`!debug`", "Debug information"),
    ],
    "Global": [
        ("`!blacklist`", "Blacklist user/guild"),
        ("`!broadcast`", "Send to all guilds"),
    ],
}


# =============================================================================
# HELP VIEW
# =============================================================================

class HelpView(discord.ui.View):
    def __init__(
        self,
        *,
        bot: commands.Bot,
        author_id: int,
        index: _HelpIndex,
        mode: str = "slash",
        timeout: float = 300,
    ):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.author_id = author_id
        self.index = index
        self.mode = mode
        self.message: Optional[discord.Message] = None

        self.category: str = "Overview"
        self.pages: list[discord.Embed] = [self._build_overview_embed()]
        self.page_idx: int = 0

        self._select = discord.ui.Select(
            placeholder="📚 Choose a category...",
            options=self._build_category_options(),
            min_values=1,
            max_values=1,
            row=0,
        )
        self._select.callback = self._on_category_selected
        self.add_item(self._select)

        self._refresh_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This menu isn't yours.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass

    def _build_category_options(self) -> list[discord.SelectOption]:
        opts: list[discord.SelectOption] = [
            discord.SelectOption(label="Overview", value="Overview", emoji="🏠", description="Bot overview & quick start"),
            discord.SelectOption(label="All Commands", value="__all__", emoji="📋", description="Complete command list"),
            discord.SelectOption(label="Search Tips", value="__search__", emoji="🔍", description="How to find commands"),
        ]
        for category in sorted(self.index.categories.keys()):
            count = len(self.index.categories[category])
            emoji = get_category_icon(category)
            opts.append(discord.SelectOption(
                label=f"{category} ({count})", 
                value=category, 
                emoji=emoji,
                description=f"{count} commands in this category"
            ))
        return opts[:25]

    def _help_label(self) -> str:
        return ",help" if self.mode == "prefix" else "/help"

    def _details_hint(self) -> str:
        if self.mode == "prefix":
            return "Use ,help <name> for details"
        return "Use /help command:<name> for details"

    def _build_overview_embed(self) -> discord.Embed:
        total = sum(len(v) for v in self.index.categories.values())
        help_label = self._help_label()

        if self.mode == "prefix":
            quick_access = f"? `{help_label} <name>` ? Detailed command info\n"
        else:
            quick_access = (
                "? `/modpanel` ? Moderation quick actions\n"
                "? `/adminpanel` ? Server configuration\n"
                f"? `{help_label} command:<name>` ? Detailed command info\n"
            )

        embed = discord.Embed(
            title="?? Command Help",
            description=(
                f"Welcome! This bot has **{total}** commands across **{len(self.index.categories)}** categories.\n\n"
                "**Quick Access:**\n"
                f"{quick_access}"
            ),
            color=Config.COLOR_EMBED,
            timestamp=datetime.now(timezone.utc)
        )

        # Category summary
        cat_lines = []
        for category in sorted(self.index.categories.keys()):
            emoji = get_category_icon(category)
            count = len(self.index.categories[category])
            cat_lines.append(f"{emoji} **{category}** ? {count} commands")
        
        embed.add_field(
            name="?? Categories", 
            value="\n".join(cat_lines[:10]) if cat_lines else "No categories found.",
            inline=False
        )
        if self.mode == "prefix":
            tips = (
                "? Use the dropdown menu to browse categories\n"
                f"? Use `{help_label} ban` for detailed info\n"
                "? Prefix commands start with a comma"
            )
        else:
            tips = (
                "? Use the dropdown menu to browse categories\n"
                f"? Use `{help_label} command:ban` for detailed info\n"
                "? Commands with `action:` have multiple functions"
            )

        embed.add_field(
            name="?? Tips",
            value=tips,
            inline=False
        )

        embed.set_footer(text="Use the dropdown menu below to navigate")
        return embed

    def _build_command_list_pages(
        self, 
        *, 
        title: str, 
        commands_list: list[app_commands.Command | app_commands.Group | commands.Command]
    ) -> list[discord.Embed]:
        lines: list[str] = []
        for cmd in commands_list:
            desc = (getattr(cmd, "description", None) or "No description").strip()
            if len(desc) > 50:
                desc = desc[:47] + "..."
            lines.append(f"`{_format_invocation(cmd)}` ? {desc}")

        pages: list[discord.Embed] = []
        chunks = list(_chunked(lines, size=10)) or [[]]
        for idx, chunk in enumerate(chunks, start=1):
            embed = discord.Embed(
                title=title,
                description="\n".join(chunk) if chunk else "No commands found.",
                color=Config.COLOR_EMBED,
            )
            embed.set_footer(text=f"Page {idx}/{len(chunks)} ? {self._details_hint()}")
            pages.append(embed)
        return pages

    def _build_search_embed(self) -> discord.Embed:
        help_label = self._help_label()
        embed = discord.Embed(
            title="?? Finding Commands",
            description="Here's how to find what you need:",
            color=Config.COLOR_INFO,
        )
        if self.mode == "prefix":
            by_name = f"`{help_label} ban` ? Get detailed info about a specific command"
        else:
            by_name = f"`{help_label} command:ban` ? Get detailed info about a specific command"

        embed.add_field(
            name="By Name",
            value=by_name,
            inline=False
        )
        embed.add_field(
            name="By Category",
            value="Use the dropdown menu above to browse by category (Moderation, Admin, etc.)",
            inline=False
        )
        embed.add_field(
            name="All Commands",
            value="Select 'All Commands' from the dropdown for a complete list",
            inline=False
        )
        if self.mode != "prefix":
            embed.add_field(
                name="Action Commands",
                value=(
                    "Many commands use an `action` parameter:\n"
                    "? `/vc action:mute` ? Mute in voice\n"
                    "? `/roles action:add` ? Add a role\n"
                    "? `/ticket action:close` ? Close a ticket"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="Prefix Reminder",
                value="Use a comma before commands (example: `,ban`, `,kick`, `,mute`).",
                inline=False
            )
        return embed

    async def _on_category_selected(self, interaction: discord.Interaction) -> None:
        value = self._select.values[0]
        self.page_idx = 0

        if value == "Overview":
            self.category = "Overview"
            self.pages = [self._build_overview_embed()]
        elif value == "__all__":
            self.category = "All Commands"
            all_cmds: list[app_commands.Command | app_commands.Group] = []
            for cat in sorted(self.index.categories.keys()):
                all_cmds.extend(self.index.categories[cat])
            all_cmds.sort(key=lambda c: c.qualified_name)
            self.pages = self._build_command_list_pages(title="📋 All Commands", commands_list=all_cmds)
        elif value == "__search__":
            self.category = "Search"
            self.pages = [self._build_search_embed()]
        else:
            self.category = value
            emoji = get_category_icon(value)
            cmds = self.index.categories.get(value, [])
            self.pages = self._build_command_list_pages(title=f"{emoji} {value}", commands_list=cmds)

        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page_idx], view=self)

    def _refresh_buttons(self) -> None:
        last = len(self.pages) - 1
        self.first_button.disabled = self.page_idx <= 0
        self.prev_button.disabled = self.page_idx <= 0
        self.next_button.disabled = self.page_idx >= last
        self.last_button.disabled = self.page_idx >= last
        self.page_counter.label = f"{self.page_idx + 1}/{len(self.pages)}"

    @discord.ui.button(label="⏮", style=discord.ButtonStyle.secondary, row=1)
    async def first_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_idx = 0
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page_idx], view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.primary, row=1)
    async def prev_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_idx = max(0, self.page_idx - 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page_idx], view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True, row=1)
    async def page_counter(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.defer()

    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary, row=1)
    async def next_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_idx = min(len(self.pages) - 1, self.page_idx + 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page_idx], view=self)

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.secondary, row=1)
    async def last_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_idx = len(self.pages) - 1
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page_idx], view=self)


# =============================================================================
# ULTRA-IMPROVED MOD PANEL WITH INTERACTIVE ACTIONS
# =============================================================================

class QuickWarnModal(discord.ui.Modal, title="⚠️ Quick Warn"):
    user_input = discord.ui.TextInput(label="User ID", placeholder="e.g. 123456789", required=True)
    reason = discord.ui.TextInput(label="Reason", placeholder="Why are you warning them?", style=discord.TextStyle.paragraph, required=True, max_length=500)
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_input.value.strip().replace("<@", "").replace(">", "").replace("!", ""))
            member = interaction.guild.get_member(user_id)
            if not member:
                return await interaction.response.send_message("❌ User not found in this server.", ephemeral=True)
            
            # Get moderation cog and use its logic
            mod_cog = self.bot.get_cog("Moderation")
            if mod_cog:
                await mod_cog._warn_logic(interaction, member, self.reason.value)
            else:
                await interaction.response.send_message(f"⚠️ Warned {member.mention} for: {self.reason.value}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class QuickMuteModal(discord.ui.Modal, title="🔇 Quick Mute"):
    user_input = discord.ui.TextInput(label="User ID", placeholder="e.g. 123456789", required=True)
    duration = discord.ui.TextInput(label="Duration", placeholder="e.g. 1h, 30m, 1d", required=True, max_length=10)
    reason = discord.ui.TextInput(label="Reason", placeholder="Why are you muting them?", style=discord.TextStyle.paragraph, required=False, max_length=500)
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_input.value.strip().replace("<@", "").replace(">", "").replace("!", ""))
            member = interaction.guild.get_member(user_id)
            if not member:
                return await interaction.response.send_message("❌ User not found in this server.", ephemeral=True)
            
            # Get moderation cog and use its logic
            mod_cog = self.bot.get_cog("Moderation")
            if mod_cog:
                await mod_cog._mute_logic(interaction, member, self.duration.value, self.reason.value or "No reason provided")
            else:
                await interaction.response.send_message(f"🔇 Muted {member.mention} for {self.duration.value}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class QuickBanModal(discord.ui.Modal, title="🔨 Quick Ban"):
    user_input = discord.ui.TextInput(label="User ID", placeholder="e.g. 123456789", required=True)
    reason = discord.ui.TextInput(label="Reason", placeholder="Ban reason", style=discord.TextStyle.paragraph, required=True, max_length=500)
    delete_days = discord.ui.TextInput(label="Delete Messages (days)", placeholder="0-7", required=False, max_length=1, default="1")
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_input.value.strip().replace("<@", "").replace(">", "").replace("!", ""))
            member = interaction.guild.get_member(user_id)
            if not member:
                return await interaction.response.send_message("❌ User not found in this server.", ephemeral=True)
            
            days = int(self.delete_days.value or "1")
            days = max(0, min(7, days))
            
            # Get moderation cog and use its logic
            mod_cog = self.bot.get_cog("Moderation")
            if mod_cog:
                await mod_cog._ban_logic(interaction, member, self.reason.value, days)
            else:
                await interaction.guild.ban(member, delete_message_seconds=days * 86400, reason=self.reason.value)
                await interaction.response.send_message(f"🔨 Banned {member.mention}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class QuickPurgeModal(discord.ui.Modal, title="🗑️ Quick Purge"):
    amount = discord.ui.TextInput(label="Number of Messages", placeholder="1-100", required=True, max_length=3)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            num = min(100, max(1, int(self.amount.value)))
            await interaction.response.defer(ephemeral=True)
            deleted = await interaction.channel.purge(limit=num)
            await interaction.followup.send(f"🗑️ Deleted **{len(deleted)}** messages!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


class QuickKickModal(discord.ui.Modal, title="👢 Quick Kick"):
    user_input = discord.ui.TextInput(label="User ID", placeholder="e.g. 123456789", required=True)
    reason = discord.ui.TextInput(label="Reason", placeholder="Why are you kicking them?", style=discord.TextStyle.paragraph, required=True, max_length=500)
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_input.value.strip().replace("<@", "").replace(">", "").replace("!", ""))
            member = interaction.guild.get_member(user_id)
            if not member:
                return await interaction.response.send_message("❌ User not found in this server.", ephemeral=True)
            
            # Get moderation cog and use its logic
            mod_cog = self.bot.get_cog("Moderation")
            if mod_cog:
                await mod_cog._kick_logic(interaction, member, self.reason.value)
            else:
                await interaction.guild.kick(member, reason=self.reason.value)
                await interaction.response.send_message(f"👢 Kicked {member.mention}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


class QuickUnmuteModal(discord.ui.Modal, title="🔊 Quick Unmute"):
    user_input = discord.ui.TextInput(label="User ID", placeholder="e.g. 123456789", required=True)
    reason = discord.ui.TextInput(label="Reason (optional)", placeholder="Why are you unmuting them?", required=False, max_length=500)
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_input.value.strip().replace("<@", "").replace(">", "").replace("!", ""))
            member = interaction.guild.get_member(user_id)
            if not member:
                return await interaction.response.send_message("❌ User not found in this server.", ephemeral=True)
            
            # Get moderation cog and use its logic
            mod_cog = self.bot.get_cog("Moderation")
            if mod_cog:
                await mod_cog._unmute_logic(interaction, member, self.reason.value or "No reason provided")
            else:
                await member.timeout(None, reason=self.reason.value or "Unmuted via panel")
                await interaction.response.send_message(f"🔊 Unmuted {member.mention}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class ModPanelView(discord.ui.View):
    """Ultra-improved moderation panel with interactive quick actions"""
    
    def __init__(self, author_id: int, bot=None):
        super().__init__(timeout=600)
        self.author_id = author_id
        self.bot = bot
        self.current_page = "main"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This panel isn't yours.", ephemeral=True)
            return False
        return True

    def _build_main_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🛡️ Moderation Control Panel",
            description=(
                "**Welcome, Moderator!**\n"
                "Use the buttons below for quick actions or info.\n\n"
                "💡 **Quick Actions** - Open forms to execute commands\n"
                "📖 **Info Buttons** - Learn about commands"
            ),
            color=Config.COLOR_MOD,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="⚡ Quick Actions (Row 1)",
            value="• **Warn** - Issue warning\n• **Mute** - Timeout user\n• **Kick** - Remove user\n• **Ban** - Permanent ban",
            inline=True
        )
        embed.add_field(
            name="🔧 Tools (Row 2)",
            value="• **Purge** - Delete messages\n• **Lock** - Lock channel\n• **Slowmode** - Set delay\n• **History** - View cases",
            inline=True
        )
        embed.add_field(
            name="📊 Stats (Row 3)",
            value="• **Server Stats** - Member info\n• **Mod Stats** - Your actions\n• **Recent Cases** - Latest mod actions",
            inline=False
        )
        
        embed.set_footer(text="🔴 Red buttons = Destructive • 🟢 Green = Safe • 🔵 Blue = Info")
        return embed

    # ═══════════ ROW 0: QUICK MOD ACTIONS ═══════════
    @discord.ui.button(label="Warn", style=discord.ButtonStyle.secondary, emoji="⚠️", row=0)
    async def quick_warn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuickWarnModal(self.bot))

    @discord.ui.button(label="Mute", style=discord.ButtonStyle.secondary, emoji="🔇", row=0)
    async def quick_mute(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuickMuteModal(self.bot))

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.danger, emoji="👢", row=0)
    async def quick_kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuickKickModal(self.bot))

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, emoji="🔨", row=0)
    async def quick_ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuickBanModal(self.bot))

    # ═══════════ ROW 1: CHANNEL TOOLS ═══════════
    @discord.ui.button(label="Purge", style=discord.ButtonStyle.primary, emoji="🗑️", row=1)
    async def quick_purge(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuickPurgeModal())

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.secondary, emoji="🔒", row=1)
    async def quick_lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        overwrites = interaction.channel.overwrites_for(interaction.guild.default_role)
        is_locked = overwrites.send_messages is False
        
        try:
            if is_locked:
                # Unlock
                await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
                await interaction.response.send_message("🔓 Channel unlocked!", ephemeral=True)
                await interaction.channel.send(embed=discord.Embed(title="🔓 Channel Unlocked", description=f"Unlocked by {interaction.user.mention}", color=0x00FF00))
            else:
                # Lock
                await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
                await interaction.response.send_message("🔒 Channel locked!", ephemeral=True)
                await interaction.channel.send(embed=discord.Embed(title="🔒 Channel Locked", description=f"Locked by {interaction.user.mention}", color=0xFF6B6B))
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

    @discord.ui.button(label="Slowmode", style=discord.ButtonStyle.secondary, emoji="🐌", row=1)
    async def slowmode_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🐌 Slowmode Options", description="Select a slowmode duration:", color=Config.COLOR_INFO)
        view = SlowmodeSelectView(self.author_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Unmute", style=discord.ButtonStyle.success, emoji="🔊", row=1)
    async def quick_unmute(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuickUnmuteModal(self.bot))

    # ═══════════ ROW 2: INFO & STATS ═══════════
    @discord.ui.button(label="Server Stats", style=discord.ButtonStyle.primary, emoji="📊", row=2)
    async def server_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        g = interaction.guild
        embed = discord.Embed(title=f"📊 {g.name} Stats", color=Config.COLOR_INFO)
        embed.add_field(name="👥 Members", value=f"**{g.member_count}**", inline=True)
        embed.add_field(name="💬 Channels", value=f"**{len(g.channels)}**", inline=True)
        embed.add_field(name="🎭 Roles", value=f"**{len(g.roles)}**", inline=True)
        online = len([m for m in g.members if m.status != discord.Status.offline])
        embed.add_field(name="🟢 Online", value=f"**{online}**", inline=True)
        bots = len([m for m in g.members if m.bot])
        embed.add_field(name="🤖 Bots", value=f"**{bots}**", inline=True)
        embed.add_field(name="📅 Created", value=f"<t:{int(g.created_at.timestamp())}:R>", inline=True)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="My Stats", style=discord.ButtonStyle.secondary, emoji="📈", row=2)
    async def my_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title=f"📈 Your Mod Stats", color=Config.COLOR_INFO)
        
        # Try to fetch real stats from database
        if self.bot and hasattr(self.bot, 'db'):
            try:
                cases = await self.bot.db.get_cases_by_mod(interaction.guild_id, interaction.user.id)
                total = len(cases)
                warns = len([c for c in cases if c.get('type') == 'warn'])
                mutes = len([c for c in cases if c.get('type') in ('mute', 'timeout')])
                kicks = len([c for c in cases if c.get('type') == 'kick'])
                bans = len([c for c in cases if c.get('type') == 'ban'])
                
                embed.add_field(name="📋 Total Actions", value=f"**{total}**", inline=True)
                embed.add_field(name="⚠️ Warns", value=f"**{warns}**", inline=True)
                embed.add_field(name="🔇 Mutes", value=f"**{mutes}**", inline=True)
                embed.add_field(name="👢 Kicks", value=f"**{kicks}**", inline=True)
                embed.add_field(name="🔨 Bans", value=f"**{bans}**", inline=True)
            except:
                embed.description = "Could not fetch stats from database."
        else:
            embed.description = "Database not available."
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Commands", style=discord.ButtonStyle.secondary, emoji="📖", row=2)
    async def all_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="📖 All Mod Commands", color=Config.COLOR_INFO)
        for section, cmds in MOD_COMMANDS.items():
            value = "\n".join([f"{cmd} — {desc}" for cmd, desc in cmds])
            embed.add_field(name=f"📌 {section}", value=value, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="✖️", row=2)
    async def close_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        await interaction.response.send_message("Panel closed!", ephemeral=True)


class SlowmodeSelectView(discord.ui.View):
    """Slowmode duration selector"""
    def __init__(self, author_id: int):
        super().__init__(timeout=60)
        self.author_id = author_id

    @discord.ui.select(
        placeholder="Select slowmode duration...",
        options=[
            discord.SelectOption(label="Off", value="0", emoji="🚫"),
            discord.SelectOption(label="5 seconds", value="5", emoji="⚡"),
            discord.SelectOption(label="10 seconds", value="10", emoji="🏃"),
            discord.SelectOption(label="30 seconds", value="30", emoji="🚶"),
            discord.SelectOption(label="1 minute", value="60", emoji="⏱️"),
            discord.SelectOption(label="5 minutes", value="300", emoji="🐢"),
            discord.SelectOption(label="10 minutes", value="600", emoji="🦥"),
            discord.SelectOption(label="1 hour", value="3600", emoji="🛑"),
        ]
    )
    async def select_slowmode(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            seconds = int(select.values[0])
            await interaction.channel.edit(slowmode_delay=seconds)
            await interaction.response.send_message(f"🐌 Slowmode set to **{seconds}s**!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


# =============================================================================
# ULTRA-IMPROVED ADMIN PANEL
# =============================================================================

class AdminPanelView(discord.ui.View):
    """Admin panel with smart toggle buttons that execute actions directly"""
    
    def __init__(self, author_id: int, bot=None):
        super().__init__(timeout=600)
        self.author_id = author_id
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This panel isn't yours.", ephemeral=True)
            return False
        return True

    async def _get_settings(self, guild_id: int) -> dict:
        """Get guild settings from database"""
        if self.bot and hasattr(self.bot, 'db'):
            return await self.bot.db.get_settings(guild_id)
        return {}

    async def _update_setting(self, guild_id: int, key: str, value) -> None:
        """Update a guild setting"""
        if self.bot and hasattr(self.bot, 'db'):
            settings = await self.bot.db.get_settings(guild_id)
            settings[key] = value
            await self.bot.db.update_settings(guild_id, settings)

    def _build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ Admin Control Panel",
            description=(
                "**Welcome, Administrator!**\n"
                "Click buttons to **toggle settings** or **execute actions**.\n\n"
                "🟢 Green = Enable/On • 🔴 Red = Disable/Destructive"
            ),
            color=Config.COLOR_ADMIN,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="🛠️ Row 1: Configuration",
            value="• **AutoMod** - Toggle auto-moderation\n• **AI Mod** - Toggle AI moderation\n• **Logging** - Toggle message logging",
            inline=True
        )
        embed.add_field(
            name="🎛️ Row 2: Server Actions",
            value="• **Lockdown** - Lock/unlock all channels\n• **Tickets** - Toggle ticket system",
            inline=True
        )
        
        embed.set_footer(text="⚙️ Admin Panel • Click to toggle settings")
        return embed

    # ═══════════ ROW 0: TOGGLES ═══════════
    @discord.ui.button(label="AutoMod", style=discord.ButtonStyle.secondary, emoji="🤖", row=0)
    async def toggle_automod(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await self._get_settings(interaction.guild_id)
        current = settings.get("automod_enabled", False)
        new_value = not current
        await self._update_setting(interaction.guild_id, "automod_enabled", new_value)
        
        status = "🟢 **Enabled**" if new_value else "🔴 **Disabled**"
        await interaction.response.send_message(f"🤖 AutoMod is now {status}", ephemeral=True)

    @discord.ui.button(label="AI Mod", style=discord.ButtonStyle.secondary, emoji="🧠", row=0)
    async def toggle_aimod(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await self._get_settings(interaction.guild_id)
        current = settings.get("aimod_enabled", True)
        new_value = not current
        await self._update_setting(interaction.guild_id, "aimod_enabled", new_value)
        
        status = "🟢 **Enabled**" if new_value else "🔴 **Disabled**"
        await interaction.response.send_message(f"🧠 AI Moderation is now {status}", ephemeral=True)

    @discord.ui.button(label="Logging", style=discord.ButtonStyle.secondary, emoji="📋", row=0)
    async def toggle_logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await self._get_settings(interaction.guild_id)
        current = settings.get("logging_enabled", True)
        new_value = not current
        await self._update_setting(interaction.guild_id, "logging_enabled", new_value)
        
        status = "🟢 **Enabled**" if new_value else "🔴 **Disabled**"
        await interaction.response.send_message(f"📋 Logging is now {status}", ephemeral=True)

    @discord.ui.button(label="Tickets", style=discord.ButtonStyle.secondary, emoji="🎫", row=0)
    async def toggle_tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await self._get_settings(interaction.guild_id)
        current = settings.get("tickets_enabled", False)
        new_value = not current
        await self._update_setting(interaction.guild_id, "tickets_enabled", new_value)
        
        status = "🟢 **Enabled**" if new_value else "🔴 **Disabled**"
        await interaction.response.send_message(f"🎫 Ticket System is now {status}", ephemeral=True)

    # ═══════════ ROW 1: SERVER ACTIONS ═══════════
    @discord.ui.button(label="Server Lockdown", style=discord.ButtonStyle.danger, emoji="🔐", row=1)
    async def server_lockdown(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        # Check if server is locked by looking at @everyone perms
        guild = interaction.guild
        default_role = guild.default_role
        
        # Count locked channels to determine state
        locked_count = 0
        total_text = 0
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).manage_channels:
                total_text += 1
                overwrites = channel.overwrites_for(default_role)
                if overwrites.send_messages is False:
                    locked_count += 1
        
        # If more than half are locked, we unlock. Otherwise, lock.
        if locked_count > total_text // 2:
            # UNLOCK
            unlocked = 0
            for channel in guild.text_channels:
                try:
                    await channel.set_permissions(default_role, send_messages=None, reason=f"Server unlocked by {interaction.user}")
                    unlocked += 1
                except:
                    pass
            await interaction.followup.send(f"🔓 **Server Unlocked!** Restored {unlocked} channels.", ephemeral=True)
        else:
            # LOCK
            locked = 0
            for channel in guild.text_channels:
                try:
                    await channel.set_permissions(default_role, send_messages=False, reason=f"Server lockdown by {interaction.user}")
                    locked += 1
                except:
                    pass
            await interaction.followup.send(f"🔐 **Server Locked!** Locked {locked} channels.", ephemeral=True)

    @discord.ui.button(label="Anti-Raid", style=discord.ButtonStyle.secondary, emoji="🛡️", row=1)
    async def toggle_antiraid(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await self._get_settings(interaction.guild_id)
        current = settings.get("antiraid_enabled", False)
        new_value = not current
        await self._update_setting(interaction.guild_id, "antiraid_enabled", new_value)
        
        status = "🟢 **Enabled**" if new_value else "🔴 **Disabled**"
        await interaction.response.send_message(f"🛡️ Anti-Raid is now {status}", ephemeral=True)

    @discord.ui.button(label="Welcome", style=discord.ButtonStyle.secondary, emoji="👋", row=1)
    async def toggle_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await self._get_settings(interaction.guild_id)
        current = settings.get("welcome_enabled", False)
        new_value = not current
        await self._update_setting(interaction.guild_id, "welcome_enabled", new_value)
        
        status = "🟢 **Enabled**" if new_value else "🔴 **Disabled**"
        await interaction.response.send_message(f"👋 Welcome Messages are now {status}", ephemeral=True)

    @discord.ui.button(label="View Status", style=discord.ButtonStyle.primary, emoji="📊", row=1)
    async def view_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await self._get_settings(interaction.guild_id)
        
        def status(key, default=False):
            return "🟢 On" if settings.get(key, default) else "🔴 Off"
        
        embed = discord.Embed(title="📊 Current Settings", color=Config.COLOR_INFO)
        embed.add_field(name="🤖 AutoMod", value=status("automod_enabled"), inline=True)
        embed.add_field(name="🧠 AI Mod", value=status("aimod_enabled", True), inline=True)
        embed.add_field(name="📋 Logging", value=status("logging_enabled", True), inline=True)
        embed.add_field(name="🎫 Tickets", value=status("tickets_enabled"), inline=True)
        embed.add_field(name="🛡️ Anti-Raid", value=status("antiraid_enabled"), inline=True)
        embed.add_field(name="👋 Welcome", value=status("welcome_enabled"), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ═══════════ ROW 2: CLOSE ═══════════
    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="✖️", row=2)
    async def close_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        await interaction.response.send_message("Panel closed!", ephemeral=True)


class OwnerPanelView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=300)
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This panel isn't yours.", ephemeral=True)
            return False
        return True

    def _build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="👑 Bot Owner Panel",
            description="Bot management and debug commands.\n⚠️ **These commands are powerful - use with caution!**",
            color=0xFFD700,  # Gold color
            timestamp=datetime.now(timezone.utc)
        )
        
        for section, commands in OWNER_COMMANDS.items():
            value = "\n".join([f"{cmd} — {desc}" for cmd, desc in commands])
            embed.add_field(name=f"🔧 {section}", value=value, inline=False)
        
        embed.set_footer(text="Owner-only commands")
        return embed

    @discord.ui.button(label="Sync Commands", style=discord.ButtonStyle.primary, emoji="🔄", row=0)
    async def sync_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔄 Command Sync",
            description="Synchronize slash commands with Discord.",
            color=Config.COLOR_INFO,
        )
        embed.add_field(
            name="Commands",
            value=(
                "`!sync` — Sync to current guild\n"
                "`!sync global` — Sync globally (takes ~1hr)\n"
                "`!sync clear` — Clear guild commands"
            ),
            inline=False
        )
        embed.add_field(
            name="When to Use",
            value="After adding/modifying slash commands, or if commands aren't showing up.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Reload Cogs", style=discord.ButtonStyle.secondary, emoji="🔃", row=0)
    async def reload_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔃 Cog Management",
            description="Hot-reload bot modules without restarting.",
            color=Config.COLOR_INFO,
        )
        embed.add_field(
            name="Commands",
            value=(
                "`!reload <cog>` — Reload a specific cog\n"
                "`!reload all` — Reload all cogs\n"
                "`!load <cog>` — Load a cog\n"
                "`!unload <cog>` — Unload a cog"
            ),
            inline=False
        )
        embed.add_field(
            name="Cog Names",
            value="`moderation`, `admin`, `automod`, `help`, `tickets`, etc.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Debug Info", style=discord.ButtonStyle.secondary, emoji="🐛", row=0)
    async def debug_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🐛 Debug Commands",
            description="Debugging and diagnostics.",
            color=Config.COLOR_INFO,
        )
        embed.add_field(
            name="Commands",
            value=(
                "`!debug` — Bot debug information\n"
                "`!eval <code>` — Execute Python code\n"
                "`!sql <query>` — Run SQL query\n"
                "`!ping` — Check latency"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# =============================================================================
# HELP COG
# =============================================================================

class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _build_details_embed(self, cmd: app_commands.Command | app_commands.Group) -> discord.Embed:
        category = _category_for_command(cmd)
        emoji = get_category_icon(category)
        title = f"{emoji} {_format_invocation(cmd)}"
        desc = (getattr(cmd, "description", None) or "No description").strip()

        embed = discord.Embed(
            title=title, 
            description=desc,
            color=Config.COLOR_EMBED,
        )
        embed.add_field(name="Category", value=category, inline=True)

        if isinstance(cmd, app_commands.Command):
            embed.add_field(name="Usage", value=f"`{_usage_line(cmd)}`", inline=False)
            embed.add_field(name="Parameters", value=_parameter_lines(cmd), inline=False)
        else:
            embed.add_field(
                name="Usage",
                value=f"`{_format_invocation(cmd)}` (command group with subcommands)",
                inline=False,
            )

        if isinstance(cmd, app_commands.Command):
            footer = "Use /help to browse all commands"
        else:
            footer = "Use ,help to browse all commands"
        embed.set_footer(text=footer)
        return embed

    @commands.command(name="help", help="Browse commands and get detailed help")
    async def help_prefix(self, ctx: commands.Context, *, command: Optional[str] = None):
        """Text-based help command"""
        index = _HelpIndex.build(self.bot, include_slash=False, include_prefix=True)

        if command:
            key = _normalize_command_name(command)
            cmd = index.by_name.get(key)
            if not cmd:
                # Try partial match
                matches = [n for n in index.by_name.keys() if key in n]
                if matches:
                    suggestions = ", ".join([f"`{m}`" for m in matches[:5]])
                    await ctx.send(f"Command `{command}` not found. Did you mean: {suggestions}?", delete_after=15)
                else:
                    await ctx.send(f"Command `{command}` not found. Try `,help` to browse categories.", delete_after=15)
                return
            await ctx.send(embed=self._build_details_embed(cmd))
            return

        view = HelpView(bot=self.bot, author_id=ctx.author.id, index=index, mode="prefix")
        view.message = await ctx.send(embed=view.pages[0], view=view)

    @app_commands.command(name="help", description="📚 Browse commands and get detailed help")
    @app_commands.describe(command="Specific command to view (example: ban, warn, vc)")
    async def help_slash(self, interaction: discord.Interaction, command: Optional[str] = None) -> None:
        index = _HelpIndex.build(self.bot, include_slash=True, include_prefix=False)

        if command:
            key = _normalize_command_name(command)
            cmd = index.by_name.get(key)
            if not cmd:
                # Try partial match
                matches = [n for n in index.by_name.keys() if key in n]
                if matches:
                    suggestions = ", ".join([f"`/{m}`" for m in matches[:5]])
                    await interaction.response.send_message(
                        f"Command `{command}` not found. Did you mean: {suggestions}?",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        f"Command `{command}` not found. Try `/help` to browse categories.",
                        ephemeral=True,
                    )
                return
            await interaction.response.send_message(embed=self._build_details_embed(cmd), ephemeral=True)
            return

        view = HelpView(bot=self.bot, author_id=interaction.user.id, index=index, mode="slash")
        await interaction.response.send_message(embed=view.pages[0], view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @help_slash.autocomplete("command")
    async def help_autocomplete(self, interaction: discord.Interaction, current: str):
        index = _HelpIndex.build(self.bot, include_slash=True, include_prefix=False)
        q = _normalize_command_name(current)

        results: list[app_commands.Choice[str]] = []
        for name, cmd in sorted(index.by_name.items(), key=lambda kv: kv[0]):
            if q and q not in name:
                continue
            label = _format_invocation(cmd)
            results.append(app_commands.Choice(name=label, value=cmd.qualified_name))
            if len(results) >= 25:
                break
        return results

    @app_commands.command(name="modpanel", description="🛡️ Quick access moderation panel")
    @is_mod()
    async def modpanel(self, interaction: discord.Interaction) -> None:
        view = ModPanelView(author_id=interaction.user.id)
        embed = view._build_main_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="adminpanel", description="⚙️ Server administration panel")
    @is_admin()
    async def adminpanel(self, interaction: discord.Interaction) -> None:
        view = AdminPanelView(author_id=interaction.user.id)
        embed = view._build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="ownerpanel", description="👑 Bot owner control panel")
    async def ownerpanel(self, interaction: discord.Interaction) -> None:
        if not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Access Denied", "This panel is for the bot owner only."),
                ephemeral=True
            )
        
        view = OwnerPanelView(author_id=interaction.user.id)
        embed = view._build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # Prefix versions for compatibility
    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context, *, command: Optional[str] = None) -> None:
        """Prefix version of /help"""
        index = _HelpIndex.build(self.bot, include_slash=False, include_prefix=True)

        if command:
            key = _normalize_command_name(command)
            cmd = index.by_name.get(key)
            if not cmd:
                await ctx.send(f"Command `{command}` not found. Try `,help`.")
                return
            await ctx.send(embed=self._build_details_embed(cmd))
            return

        view = HelpView(bot=self.bot, author_id=ctx.author.id, index=index, mode="prefix")
        msg = await ctx.send(embed=view.pages[0], view=view)
        view.message = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
