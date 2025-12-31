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
    def build(bot: commands.Bot) -> "_HelpIndex":
        categories: dict[str, list[app_commands.Command | app_commands.Group | commands.Command]] = {}
        by_name: dict[str, app_commands.Command | app_commands.Group | commands.Command] = {}

        for cmd in _walk_slash_commands(bot.tree):
            if getattr(cmd, "name", None) in ("help", "modpanel", "adminpanel", "ownerpanel"):
                continue

            category = _category_for_command(cmd)
            categories.setdefault(category, []).append(cmd)
            by_name[_normalize_command_name(cmd.qualified_name)] = cmd

        # Index prefix commands
        for cmd in bot.commands:
            if cmd.hidden:
                continue
            
            # If a slash command with same name exists, we might want to skip or merge?
            # For now, let's index them all. If names collide, last write wins in by_name 
            # but categories list appends.
            # To avoid duplicates in list, we could check.
            
            # Simple deduplication by qualified name within category? 
            # But they are different objects.
            
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
            lines.append(f"`{_format_invocation(cmd)}` — {desc}")

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
# ULTRA-IMPROVED MOD PANEL WITH INTERACTIVE ACTIONS
# =============================================================================

class QuickWarnModal(discord.ui.Modal, title="⚠️ Quick Warn"):
    user_input = discord.ui.TextInput(label="User ID or @mention", placeholder="e.g. 123456789 or username", required=True)
    reason = discord.ui.TextInput(label="Reason", placeholder="Why are you warning them?", style=discord.TextStyle.paragraph, required=True, max_length=500)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"⚠️ Use `/warn` with:\n**User:** `{self.user_input.value}`\n**Reason:** {self.reason.value}", ephemeral=True)

class QuickMuteModal(discord.ui.Modal, title="🔇 Quick Mute"):
    user_input = discord.ui.TextInput(label="User ID or @mention", placeholder="e.g. 123456789", required=True)
    duration = discord.ui.TextInput(label="Duration", placeholder="e.g. 1h, 30m, 1d, 7d", required=True, max_length=10)
    reason = discord.ui.TextInput(label="Reason", placeholder="Why are you muting them?", style=discord.TextStyle.paragraph, required=False, max_length=500)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🔇 Use `/mute` with:\n**User:** `{self.user_input.value}`\n**Duration:** `{self.duration.value}`\n**Reason:** {self.reason.value or 'N/A'}", ephemeral=True)

class QuickBanModal(discord.ui.Modal, title="🔨 Quick Ban"):
    user_input = discord.ui.TextInput(label="User ID or @mention", placeholder="e.g. 123456789", required=True)
    reason = discord.ui.TextInput(label="Reason", placeholder="Ban reason", style=discord.TextStyle.paragraph, required=True, max_length=500)
    delete_days = discord.ui.TextInput(label="Delete Messages (days)", placeholder="0-7", required=False, max_length=1, default="1")
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🔨 Use `/ban` with:\n**User:** `{self.user_input.value}`\n**Reason:** {self.reason.value}\n**Delete Days:** {self.delete_days.value or '1'}", ephemeral=True)

class QuickPurgeModal(discord.ui.Modal, title="🗑️ Quick Purge"):
    amount = discord.ui.TextInput(label="Number of Messages", placeholder="1-100", required=True, max_length=3)
    user_filter = discord.ui.TextInput(label="Filter by User (optional)", placeholder="User ID to filter (leave blank for all)", required=False)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            num = min(100, max(1, int(self.amount.value)))
            await interaction.channel.purge(limit=num)
            await interaction.response.send_message(f"🗑️ Deleted up to **{num}** messages!", ephemeral=True)
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
        await interaction.response.send_modal(QuickWarnModal())

    @discord.ui.button(label="Mute", style=discord.ButtonStyle.secondary, emoji="🔇", row=0)
    async def quick_mute(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuickMuteModal())

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.danger, emoji="👢", row=0)
    async def quick_kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="👢 Kick User", description="Use `/kick @user [reason]` to kick a member.", color=0xFF6B6B)
        embed.add_field(name="Example", value="`/kick @troublemaker Breaking rules`")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, emoji="🔨", row=0)
    async def quick_ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuickBanModal())

    # ═══════════ ROW 1: CHANNEL TOOLS ═══════════
    @discord.ui.button(label="Purge", style=discord.ButtonStyle.primary, emoji="🗑️", row=1)
    async def quick_purge(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuickPurgeModal())

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.secondary, emoji="🔒", row=1)
    async def quick_lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
            await interaction.response.send_message("🔒 Channel locked!", ephemeral=True)
            await interaction.channel.send(embed=discord.Embed(title="🔒 Channel Locked", description=f"Locked by {interaction.user.mention}", color=0xFF6B6B))
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

    @discord.ui.button(label="Unlock", style=discord.ButtonStyle.success, emoji="🔓", row=1)
    async def quick_unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
            await interaction.response.send_message("🔓 Channel unlocked!", ephemeral=True)
            await interaction.channel.send(embed=discord.Embed(title="🔓 Channel Unlocked", description=f"Unlocked by {interaction.user.mention}", color=0x00FF00))
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

    @discord.ui.button(label="Slowmode", style=discord.ButtonStyle.secondary, emoji="🐌", row=1)
    async def slowmode_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🐌 Slowmode Options", description="Select a slowmode duration:", color=Config.COLOR_INFO)
        view = SlowmodeSelectView(self.author_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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
        embed.description = "Use `/modstats` to see detailed statistics of your moderation actions."
        embed.add_field(name="Commands", value="`/history @user`\n`/cases @user`\n`/modlog`", inline=False)
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
    """Ultra-improved admin panel with quick configuration actions"""
    
    def __init__(self, author_id: int, bot=None):
        super().__init__(timeout=600)
        self.author_id = author_id
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This panel isn't yours.", ephemeral=True)
            return False
        return True

    def _build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ Admin Control Panel",
            description=(
                "**Welcome, Administrator!**\n"
                "Configure your server with the buttons below.\n\n"
                "🔧 **Quick Config** - Instant settings changes\n"
                "📖 **Info Buttons** - Learn about features"
            ),
            color=Config.COLOR_ADMIN,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="🛠️ Configuration (Row 1)",
            value="• **Setup** - Setup wizard\n• **AutoMod** - Auto moderation\n• **Logs** - Logging config\n• **Roles** - Role setup",
            inline=True
        )
        embed.add_field(
            name="🎛️ Quick Actions (Row 2)",
            value="• **Lockdown** - Lock server\n• **AI Mod** - Toggle AI\n• **Tickets** - Ticket system\n• **Welcome** - Welcome msgs",
            inline=True
        )
        embed.add_field(
            name="📊 Server Info (Row 3)",
            value="• **Settings** - View config\n• **Audit** - Recent activity\n• **Commands** - All admin cmds",
            inline=False
        )
        
        embed.set_footer(text="⚙️ Admin-level actions • Be careful with server-wide changes")
        return embed

    # ═══════════ ROW 0: CONFIGURATION ═══════════
    @discord.ui.button(label="Setup", style=discord.ButtonStyle.primary, emoji="⚙️", row=0)
    async def setup_wizard(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="⚙️ Quick Setup Guide", color=Config.COLOR_INFO)
        embed.description = "Run `/setup` for the interactive wizard, or set individually:"
        embed.add_field(name="Essential Commands", value=(
            "`/setlog` - Set mod log channel\n"
            "`/setmod` - Set moderator role\n"
            "`/setadmin` - Set admin role\n"
            "`/setwelcome` - Set welcome channel"
        ), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="AutoMod", style=discord.ButtonStyle.secondary, emoji="🤖", row=0)
    async def automod_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🤖 AutoMod Configuration", color=Config.COLOR_INFO)
        embed.add_field(name="Toggle Features", value=(
            "`/automod enable` / `disable`\n"
            "`/automod spam` - Anti-spam (threshold)\n"
            "`/automod caps` - Caps filter (%)\n"
            "`/automod links` - Block links\n"
            "`/automod invites` - Block invites"
        ), inline=False)
        embed.add_field(name="Punishments", value=(
            "`/automod punishment` - Set action (warn/mute/kick/ban)"
        ), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Logging", style=discord.ButtonStyle.secondary, emoji="📋", row=0)
    async def logging_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="📋 Logging Configuration", color=Config.COLOR_INFO)
        embed.add_field(name="Log Channels", value=(
            "`/setlog mod` - Moderation logs\n"
            "`/setlog voice` - Voice activity\n"
            "`/setlog joins` - Member joins/leaves\n"
            "`/setlog messages` - Message edits/deletes"
        ), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Roles", style=discord.ButtonStyle.secondary, emoji="🎭", row=0)
    async def roles_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎭 Role Management", color=Config.COLOR_INFO)
        embed.add_field(name="Staff Roles", value=(
            "`/setmod` - Moderator role\n"
            "`/setadmin` - Admin role\n"
            "`/setseniormod` - Senior mod role"
        ), inline=True)
        embed.add_field(name="Auto Roles", value=(
            "`/autorole set` - Join role\n"
            "`/autorole verify` - Verify role\n"
            "`/voicerole` - VC roles"
        ), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ═══════════ ROW 1: QUICK ACTIONS ═══════════
    @discord.ui.button(label="Server Lockdown", style=discord.ButtonStyle.danger, emoji="🔐", row=1)
    async def server_lockdown(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔐 Server Lockdown",
            description="**Warning:** This will lock ALL text channels!\n\nUse `/lockdown` to activate or `/unlockdown` to deactivate.",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="AI Moderation", style=discord.ButtonStyle.success, emoji="🧠", row=1)
    async def ai_mod_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🧠 AI Moderation", color=Config.COLOR_INFO)
        embed.description = "AI-powered natural language moderation.\n\nMention the bot + command (e.g. `@bot mute user for spam`)"
        embed.add_field(name="Commands", value=(
            "`/aimod enable` - Turn on\n"
            "`/aimod disable` - Turn off\n"
            "`/aimod channel` - Set command channel\n"
            "`/aimod confirm` - Require confirmations"
        ), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Tickets", style=discord.ButtonStyle.secondary, emoji="🎫", row=1)
    async def tickets_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎫 Ticket System", color=Config.COLOR_INFO)
        embed.add_field(name="Setup", value=(
            "`/ticketpanel` - Create ticket panel\n"
            "`/ticket category` - Set ticket category\n"
            "`/ticket staff` - Set support role"
        ), inline=False)
        embed.add_field(name="Management", value=(
            "`/ticket close` - Close ticket\n"
            "`/ticket add` - Add user\n"
            "`/ticket transcript` - Generate log"
        ), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Welcome", style=discord.ButtonStyle.secondary, emoji="👋", row=1)
    async def welcome_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="👋 Welcome System", color=Config.COLOR_INFO)
        embed.add_field(name="Setup", value=(
            "`/setwelcome` - Set welcome channel\n"
            "`/welcome message` - Custom message\n"
            "`/welcome card` - Enable/disable cards\n"
            "`/autorole` - Auto-assign role on join"
        ), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ═══════════ ROW 2: INFO & STATS ═══════════
    @discord.ui.button(label="View Settings", style=discord.ButtonStyle.primary, emoji="📊", row=2)
    async def view_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="📊 Current Server Settings", color=Config.COLOR_INFO)
        embed.description = "Use `/settings` to view all bot settings for this server."
        embed.add_field(name="Quick Info", value=(
            f"**Server:** {interaction.guild.name}\n"
            f"**Members:** {interaction.guild.member_count}\n"
            f"**Channels:** {len(interaction.guild.channels)}"
        ), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="All Commands", style=discord.ButtonStyle.secondary, emoji="📖", row=2)
    async def all_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="📖 All Admin Commands", color=Config.COLOR_INFO)
        for section, cmds in ADMIN_COMMANDS.items():
            value = "\n".join([f"{cmd} — {desc}" for cmd, desc in cmds])
            embed.add_field(name=f"📌 {section}", value=value, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

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

        embed.set_footer(text="Use /help to browse all commands")
        return embed

    @commands.command(name="help", help="Browse commands and get detailed help")
    async def help_prefix(self, ctx: commands.Context, *, command: Optional[str] = None):
        """Text-based help command"""
        index = _HelpIndex.build(self.bot)

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

        view = HelpView(bot=self.bot, author_id=ctx.author.id, index=index)
        view.message = await ctx.send(embed=view.pages[0], view=view)

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
