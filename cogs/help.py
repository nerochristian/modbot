"""
Interactive /help command (slash + prefix) with categories, pagination, and command details.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import discord
from discord import app_commands
from discord.ext import commands


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
        # Make AIModeration a little nicer.
        if cog_name.upper() == cog_name and len(cog_name) <= 4:
            return cog_name
        if cog_name == "AIModeration":
            return "AI Moderation"
        return cog_name
    return "Core"


def _format_slash_invocation(cmd: app_commands.Command | app_commands.Group) -> str:
    # qualified_name includes groups as "group sub".
    return f"/{cmd.qualified_name}"


def _chunked(items: list[str], *, size: int) -> Iterable[list[str]]:
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
        lines.append(f"- `{p.name}` ({required}) — {desc}")
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
            if getattr(cmd, "name", None) == "help":
                continue

            category = _category_for_command(cmd)
            categories.setdefault(category, []).append(cmd)
            by_name[_normalize_command_name(cmd.qualified_name)] = cmd

        for cat in categories:
            categories[cat].sort(key=lambda c: c.qualified_name)

        return _HelpIndex(categories=categories, by_name=by_name)


class HelpView(discord.ui.View):
    def __init__(
        self,
        *,
        bot: commands.Bot,
        author_id: int,
        index: _HelpIndex,
        timeout: float = 180,
    ):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.author_id = author_id
        self.index = index

        self.category: str = "Overview"
        self.pages: list[discord.Embed] = [self._build_overview_embed()]
        self.page_idx: int = 0

        # Important: our repo uses a Components v2 wrapper that converts classic Views
        # into v2 ActionRows. ActionRows can only contain 5 children, so we must put
        # the dropdown and 5 nav buttons into separate rows.
        try:
            self.first_button.row = 1
            self.prev_button.row = 1
            self.page_counter.row = 1
            self.next_button.row = 1
            self.last_button.row = 1
        except Exception:
            pass

        self._select = discord.ui.Select(
            placeholder="Choose a help category…",
            options=self._build_category_options(),
            min_values=1,
            max_values=1,
        )
        try:
            self._select.row = 0
        except Exception:
            pass
        self._select.callback = self._on_category_selected  # type: ignore[assignment]
        self.add_item(self._select)

        self._refresh_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This help menu isn't yours.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True  # type: ignore[assignment]

    def _build_category_options(self) -> list[discord.SelectOption]:
        opts: list[discord.SelectOption] = [
            discord.SelectOption(label="Overview", value="Overview", description="Quick start + categories"),
            discord.SelectOption(label="All Commands", value="__all__", description="Everything in one list"),
        ]
        for category in sorted(self.index.categories.keys()):
            count = len(self.index.categories[category])
            opts.append(discord.SelectOption(label=f"{category} ({count})", value=category))
        return opts[:25]

    def _build_overview_embed(self) -> discord.Embed:
        total = sum(len(v) for v in self.index.categories.values())

        embed = discord.Embed(
            title="Help",
            description=(
                f"Browse **{total}** slash commands using the menu below.\n"
                "For command details, use `/help command:<name>`.\n"
                "AI moderation help: `/aihelp`."
            ),
        )

        lines: list[str] = []
        for category in sorted(self.index.categories.keys()):
            lines.append(f"- **{category}**: {len(self.index.categories[category])}")
        embed.add_field(name="Categories", value="\n".join(lines) if lines else "No commands found.", inline=False)
        embed.set_footer(text="Tip: try /help command:ban")
        return embed

    def _build_command_list_pages(self, *, title: str, commands_list: list[app_commands.Command | app_commands.Group]) -> list[discord.Embed]:
        lines: list[str] = []
        for cmd in commands_list:
            desc = (getattr(cmd, "description", None) or "No description").strip()
            lines.append(f"- `{_format_slash_invocation(cmd)}` — {desc}")

        pages: list[discord.Embed] = []
        chunks = list(_chunked(lines, size=12)) or [[]]
        for idx, chunk in enumerate(chunks, start=1):
            embed = discord.Embed(
                title=title,
                description="\n".join(chunk) if chunk else "No commands found.",
            )
            embed.set_footer(text=f"Page {idx}/{len(chunks)} • Use /help command:<name> for details")
            pages.append(embed)
        return pages

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
            self.pages = self._build_command_list_pages(title="Help • All Commands", commands_list=all_cmds)
        else:
            self.category = value
            cmds = self.index.categories.get(value, [])
            self.pages = self._build_command_list_pages(title=f"Help • {value}", commands_list=cmds)

        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page_idx], view=self)

    def _refresh_buttons(self) -> None:
        last = len(self.pages) - 1
        self.first_button.disabled = self.page_idx <= 0
        self.prev_button.disabled = self.page_idx <= 0
        self.next_button.disabled = self.page_idx >= last
        self.last_button.disabled = self.page_idx >= last
        self.page_counter.label = f"{self.page_idx + 1}/{len(self.pages)}"

    @discord.ui.button(label="⏮", style=discord.ButtonStyle.secondary)
    async def first_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_idx = 0
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page_idx], view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_idx = max(0, self.page_idx - 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page_idx], view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def page_counter(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.defer()

    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_idx = min(len(self.pages) - 1, self.page_idx + 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page_idx], view=self)

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.secondary)
    async def last_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_idx = len(self.pages) - 1
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page_idx], view=self)


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _build_details_embed(self, cmd: app_commands.Command | app_commands.Group) -> discord.Embed:
        category = _category_for_command(cmd)
        title = f"Help • {_format_slash_invocation(cmd)}"
        desc = (getattr(cmd, "description", None) or "No description").strip()

        embed = discord.Embed(title=title, description=desc)
        embed.add_field(name="Category", value=category, inline=True)

        if isinstance(cmd, app_commands.Command):
            embed.add_field(name="Usage", value=f"`{_usage_line(cmd)}`", inline=False)
            embed.add_field(name="Parameters", value=_parameter_lines(cmd), inline=False)
        else:
            embed.add_field(
                name="Usage",
                value=f"`{_format_slash_invocation(cmd)}` (open this command in Discord to see subcommands)",
                inline=False,
            )

        embed.set_footer(text="Use /help to browse categories")
        return embed

    @app_commands.command(name="help", description="Show the full command list and command details.")
    @app_commands.describe(command="Specific command to view (example: ban, warn, ticketpanel)")
    async def help_slash(self, interaction: discord.Interaction, command: Optional[str] = None) -> None:
        index = _HelpIndex.build(self.bot)

        if command:
            key = _normalize_command_name(command)
            cmd = index.by_name.get(key)
            if not cmd:
                await interaction.response.send_message(
                    f"Couldn't find a command named `{command}`. Try `/help` and browse by category.",
                    ephemeral=True,
                )
                return
            await interaction.response.send_message(embed=self._build_details_embed(cmd), ephemeral=True)
            return

        view = HelpView(bot=self.bot, author_id=interaction.user.id, index=index)
        await interaction.response.send_message(embed=view.pages[0], view=view, ephemeral=True)

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

    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context, *, command: Optional[str] = None) -> None:
        """Prefix version of /help (also fixes error-handler hints)."""
        index = _HelpIndex.build(self.bot)

        if command:
            key = _normalize_command_name(command)
            cmd = index.by_name.get(key)
            if not cmd:
                await ctx.send(f"Couldn't find `{command}`. Try `/help`.")
                return
            await ctx.send(embed=self._build_details_embed(cmd))
            return

        view = HelpView(bot=self.bot, author_id=ctx.author.id, index=index)
        await ctx.send(embed=view.pages[0], view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
