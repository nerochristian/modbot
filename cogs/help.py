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


def _category_for_command(cmd: app_commands.Command | app_commands.Group) -> str:
    binding = getattr(cmd, "binding", None)
    cog_name = getattr(binding, "__cog_name__", None)
    if cog_name:
        if cog_name.upper() == cog_name and len(cog_name) <= 4:
            return cog_name
        if cog_name == "AIModeration":
            return "AI Moderation"
        return cog_name
    return "Core"


def _format_slash_invocation(cmd: app_commands.Command | app_commands.Group) -> str:
    return f"/{cmd.qualified_name}"


def _chunked(items: list, *, size: int) -> Iterable[list]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _usage_line(cmd: app_commands.Command) -> str:
    parts = [_format_slash_invocation(cmd)]
    for p in cmd.parameters:
        if p.required:
            parts.append(f"<{p.name}>")
        else:
            parts.append(f"[{p.name}]")
    return " ".join(parts)


def _parameter_lines(cmd: app_commands.Command) -> str:
    if not cmd.parameters:
        return "No parameters."
    lines: list[str] = []
    for p in cmd.parameters:
        desc = (p.description or "No description").strip()
        required = "required" if p.required else "optional"
        lines.append(f"• `{p.name}` ({required}) — {desc}")
    return "\n".join(lines)


@dataclass(frozen=True)
class _HelpIndex:
    categories: dict[str, list[app_commands.Command | app_commands.Group]]
    by_name: dict[str, app_commands.Command | app_commands.Group]

    @staticmethod
    def build(bot: commands.Bot) -> "_HelpIndex":
        categories: dict[str, list[app_commands.Command | app_commands.Group]] = {}
        by_name: dict[str, app_commands.Command | app_commands.Group] = {}

        for cmd in _walk_slash_commands(bot.tree):
            if getattr(cmd, "name", None) in ("help", "modpanel", "adminpanel", "ownerpanel"):
                continue

            category = _category_for_command(cmd)
            categories.setdefault(category, []).append(cmd)
            by_name[_normalize_command_name(cmd.qualified_name)] = cmd

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
    "User Actions": [
        ("`/warn`", "Issue a warning"),
        ("`/kick`", "Kick a user"),
        ("`/ban`", "Ban a user"),
        ("`/tempban`", "Temporary ban"),
        ("`/mute`", "Timeout a user"),
        ("`/unmute`", "Remove timeout"),
    ],
    "Channel Actions": [
        ("`/purge`", "Bulk delete messages"),
        ("`/lock`", "Lock a channel"),
        ("`/unlock`", "Unlock a channel"),
        ("`/slowmode`", "Set slowmode"),
    ],
    "Voice Actions": [
        ("`/vc action:mute`", "Server mute user"),
        ("`/vc action:kick`", "Kick from VC"),
        ("`/vc action:move`", "Move user to VC"),
    ],
    "Info & History": [
        ("`/history`", "View user history"),
        ("`/case`", "View specific case"),
        ("`/notes`", "View/add user notes"),
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
        timeout: float = 300,
    ):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.author_id = author_id
        self.index = index
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

    def _build_overview_embed(self) -> discord.Embed:
        total = sum(len(v) for v in self.index.categories.values())
        
        embed = discord.Embed(
            title="📚 Command Help",
            description=(
                f"Welcome! This bot has **{total}** commands across **{len(self.index.categories)}** categories.\n\n"
                "**Quick Access:**\n"
                "• `/modpanel` — Moderation quick actions\n"
                "• `/adminpanel` — Server configuration\n"
                "• `/help command:<name>` — Detailed command info\n"
            ),
            color=Config.COLOR_EMBED,
            timestamp=datetime.now(timezone.utc)
        )

        # Category summary
        cat_lines = []
        for category in sorted(self.index.categories.keys()):
            emoji = get_category_icon(category)
            count = len(self.index.categories[category])
            cat_lines.append(f"{emoji} **{category}** — {count} commands")
        
        embed.add_field(
            name="📁 Categories", 
            value="\n".join(cat_lines[:10]) if cat_lines else "No categories found.",
            inline=False
        )

        embed.add_field(
            name="💡 Tips",
            value=(
                "• Use the dropdown menu to browse categories\n"
                "• Use `/help command:ban` for detailed info\n"
                "• Commands with `action:` have multiple functions"
            ),
            inline=False
        )

        embed.set_footer(text="Use the dropdown menu below to navigate")
        return embed

    def _build_command_list_pages(
        self, 
        *, 
        title: str, 
        commands_list: list[app_commands.Command | app_commands.Group]
    ) -> list[discord.Embed]:
        lines: list[str] = []
        for cmd in commands_list:
            desc = (getattr(cmd, "description", None) or "No description").strip()
            if len(desc) > 50:
                desc = desc[:47] + "..."
            lines.append(f"`{_format_slash_invocation(cmd)}` — {desc}")

        pages: list[discord.Embed] = []
        chunks = list(_chunked(lines, size=10)) or [[]]
        for idx, chunk in enumerate(chunks, start=1):
            embed = discord.Embed(
                title=title,
                description="\n".join(chunk) if chunk else "No commands found.",
                color=Config.COLOR_EMBED,
            )
            embed.set_footer(text=f"Page {idx}/{len(chunks)} • /help command:<name> for details")
            pages.append(embed)
        return pages

    def _build_search_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🔍 Finding Commands",
            description="Here's how to find what you need:",
            color=Config.COLOR_INFO,
        )
        embed.add_field(
            name="By Name",
            value="`/help command:ban` — Get detailed info about a specific command",
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
        embed.add_field(
            name="Action Commands",
            value=(
                "Many commands use an `action` parameter:\n"
                "• `/vc action:mute` — Mute in voice\n"
                "• `/roles action:add` — Add a role\n"
                "• `/ticket action:close` — Close a ticket"
            ),
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
# PANEL VIEWS
# =============================================================================

class ModPanelView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.current_page = "main"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This panel isn't yours.", ephemeral=True)
            return False
        return True

    def _build_main_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🛡️ Moderator Panel",
            description="Quick access to moderation commands. Select a category below.",
            color=Config.COLOR_MOD,
            timestamp=datetime.now(timezone.utc)
        )
        
        for section, commands in MOD_COMMANDS.items():
            value = "\n".join([f"{cmd} — {desc}" for cmd, desc in commands])
            embed.add_field(name=f"📌 {section}", value=value, inline=False)
        
        embed.set_footer(text="Use the buttons below for quick actions")
        return embed

    @discord.ui.button(label="Warn", style=discord.ButtonStyle.secondary, emoji="⚠️", row=0)
    async def warn_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚠️ Warn Command",
            description="Issue a warning to a user.",
            color=Config.COLOR_WARNING,
        )
        embed.add_field(name="Usage", value="`/warn <user> <reason>`", inline=False)
        embed.add_field(name="Example", value="`/warn @user Spamming in chat`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Mute", style=discord.ButtonStyle.secondary, emoji="🔇", row=0)
    async def mute_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔇 Mute Command",
            description="Timeout a user for a specified duration.",
            color=Config.COLOR_WARNING,
        )
        embed.add_field(name="Usage", value="`/mute <user> <duration> [reason]`", inline=False)
        embed.add_field(name="Durations", value="`5m`, `1h`, `6h`, `1d`, `7d`", inline=False)
        embed.add_field(name="Example", value="`/mute @user 1h Being disruptive`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.secondary, emoji="👢", row=0)
    async def kick_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👢 Kick Command",
            description="Remove a user from the server (they can rejoin).",
            color=Config.COLOR_WARNING,
        )
        embed.add_field(name="Usage", value="`/kick <user> [reason]`", inline=False)
        embed.add_field(name="Example", value="`/kick @user Breaking rules`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, emoji="🔨", row=0)
    async def ban_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔨 Ban Command",
            description="Permanently ban a user from the server.",
            color=Config.COLOR_ERROR,
        )
        embed.add_field(name="Usage", value="`/ban <user> [reason] [delete_days]`", inline=False)
        embed.add_field(name="Options", value="`delete_days`: Delete their messages (0-7 days)", inline=False)
        embed.add_field(name="Example", value="`/ban @user Repeated violations`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Purge", style=discord.ButtonStyle.secondary, emoji="🗑️", row=1)
    async def purge_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🗑️ Purge Command",
            description="Bulk delete messages from a channel.",
            color=Config.COLOR_INFO,
        )
        embed.add_field(name="Usage", value="`/purge <amount> [user]`", inline=False)
        embed.add_field(name="Options", value="`user`: Only delete messages from this user", inline=False)
        embed.add_field(name="Example", value="`/purge 50` or `/purge 20 @spammer`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="History", style=discord.ButtonStyle.secondary, emoji="📜", row=1)
    async def history_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📜 History Command",
            description="View a user's moderation history.",
            color=Config.COLOR_INFO,
        )
        embed.add_field(name="Usage", value="`/history <user>`", inline=False)
        embed.add_field(name="Shows", value="Warnings, mutes, kicks, bans, and notes", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AdminPanelView(discord.ui.View):
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
            title="⚙️ Admin Panel",
            description="Server configuration and management commands.",
            color=Config.COLOR_ADMIN,
            timestamp=datetime.now(timezone.utc)
        )
        
        for section, commands in ADMIN_COMMANDS.items():
            value = "\n".join([f"{cmd} — {desc}" for cmd, desc in commands])
            embed.add_field(name=f"📌 {section}", value=value, inline=False)
        
        embed.set_footer(text="Use the buttons below for quick info")
        return embed

    @discord.ui.button(label="Setup", style=discord.ButtonStyle.primary, emoji="⚙️", row=0)
    async def setup_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚙️ Bot Setup",
            description="Configure the bot for your server.",
            color=Config.COLOR_INFO,
        )
        embed.add_field(
            name="Essential Setup",
            value=(
                "`/setup` — Interactive setup wizard\n"
                "`/setlog` — Set logging channel\n"
                "`/setmod` — Set moderator role\n"
                "`/setadmin` — Set admin role"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="AutoMod", style=discord.ButtonStyle.secondary, emoji="🤖", row=0)
    async def automod_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🤖 AutoMod Configuration",
            description="Automatic moderation settings.",
            color=Config.COLOR_INFO,
        )
        embed.add_field(
            name="Basic Commands",
            value=(
                "`/automod enable` — Enable automod\n"
                "`/automod disable` — Disable automod\n"
                "`/automod status` — View current settings\n"
                "`/automod punishment` — Set punishment type"
            ),
            inline=False
        )
        embed.add_field(
            name="Filters",
            value=(
                "`/automod spam` — Spam filter threshold\n"
                "`/automod caps` — Caps filter percentage\n"
                "`/automod links` — Link filter toggle\n"
                "`/automod invites` — Invite filter toggle\n"
                "`/automod badwords add` — Add blacklisted words"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Roles", style=discord.ButtonStyle.secondary, emoji="🎭", row=0)
    async def roles_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎭 Role Management",
            description="Advanced role commands.",
            color=Config.COLOR_INFO,
        )
        embed.add_field(
            name="Commands",
            value=(
                "`/roles action:add` — Add role to user\n"
                "`/roles action:remove` — Remove role from user\n"
                "`/roles action:create` — Create a new role\n"
                "`/roles action:delete` — Delete a role\n"
                "`/roles action:all` — Give role to all members\n"
                "`/roles action:info` — View role info"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Tickets", style=discord.ButtonStyle.secondary, emoji="🎫", row=1)
    async def tickets_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎫 Ticket System",
            description="Support ticket commands.",
            color=Config.COLOR_INFO,
        )
        embed.add_field(
            name="Commands",
            value=(
                "`/ticketpanel` — Create a ticket panel\n"
                "`/ticket action:create` — Create a ticket\n"
                "`/ticket action:close` — Close a ticket\n"
                "`/ticket action:add` — Add user to ticket\n"
                "`/ticket action:transcript` — Generate transcript"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


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
        title = f"{emoji} {_format_slash_invocation(cmd)}"
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
                value=f"`{_format_slash_invocation(cmd)}` (command group with subcommands)",
                inline=False,
            )

        embed.set_footer(text="Use /help to browse all commands")
        return embed

    @app_commands.command(name="help", description="📚 Browse commands and get detailed help")
    @app_commands.describe(command="Specific command to view (example: ban, warn, vc)")
    async def help_slash(self, interaction: discord.Interaction, command: Optional[str] = None) -> None:
        index = _HelpIndex.build(self.bot)

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

        view = HelpView(bot=self.bot, author_id=interaction.user.id, index=index)
        await interaction.response.send_message(embed=view.pages[0], view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @help_slash.autocomplete("command")
    async def help_autocomplete(self, interaction: discord.Interaction, current: str):
        index = _HelpIndex.build(self.bot)
        q = _normalize_command_name(current)

        results: list[app_commands.Choice[str]] = []
        for name, cmd in sorted(index.by_name.items(), key=lambda kv: kv[0]):
            if q and q not in name:
                continue
            label = _format_slash_invocation(cmd)
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
        index = _HelpIndex.build(self.bot)

        if command:
            key = _normalize_command_name(command)
            cmd = index.by_name.get(key)
            if not cmd:
                await ctx.send(f"Command `{command}` not found. Try `/help`.")
                return
            await ctx.send(embed=self._build_details_embed(cmd))
            return

        view = HelpView(bot=self.bot, author_id=ctx.author.id, index=index)
        msg = await ctx.send(embed=view.pages[0], view=view)
        view.message = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
