"""Beginner-friendly AutoMod status panel with interactive controls."""

from __future__ import annotations

from typing import Any, Optional

import discord

from config import Config
from .config import AUTOMOD_PRESETS, MODULE_SETTING_KEYS, MODULES
from .utils import compact_duration, id_list, parse_duration, parse_threshold_pair


PANEL_PAGES: tuple[tuple[int, str, str], ...] = (
    (0, "Overview", "Core AutoMod state and enabled modules."),
    (1, "Thresholds", "Spam, duplicate, caps, mention, and raid limits."),
    (2, "Punishments", "Default punishments and escalation settings."),
    (3, "Whitelist", "Roles, users, and channels ignored by AutoMod."),
)


def _parse_duration(value: str) -> int | None:
    return parse_duration(value, minimum=60, maximum=2419200)


def _compact_duration(seconds: int) -> str:
    return compact_duration(seconds)


def _parse_threshold_pair(value: str, *, count_range: tuple[int, int], window_range: tuple[int, int]) -> tuple[int, int] | None:
    return parse_threshold_pair(value, count_range=count_range, window_range=window_range)


class AutoModPanel(discord.ui.View):
    def __init__(self, bot: Any, guild: Any, user_id: int, settings: dict[str, Any]) -> None:
        super().__init__(timeout=180)
        self.bot = bot
        self.guild = guild
        self.user_id = int(user_id)
        self.settings = settings
        self.page = 0
        self.rebuild()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    def rebuild(self) -> None:
        self.clear_items()
        previous_button = discord.ui.Button(label="Prev", style=discord.ButtonStyle.secondary, row=0, disabled=self.page <= 0)
        next_button = discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary, row=0, disabled=self.page >= len(PANEL_PAGES) - 1)
        refresh_button = discord.ui.Button(label="Refresh", style=discord.ButtonStyle.primary, row=0)
        close_button = discord.ui.Button(label="Close", style=discord.ButtonStyle.danger, row=0)

        async def previous(interaction: discord.Interaction) -> None:
            self.page = max(0, self.page - 1)
            self.rebuild()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

        async def next_page(interaction: discord.Interaction) -> None:
            self.page = min(len(PANEL_PAGES) - 1, self.page + 1)
            self.rebuild()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

        async def refresh(interaction: discord.Interaction) -> None:
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

        async def close(interaction: discord.Interaction) -> None:
            self.stop()
            await interaction.response.edit_message(view=None)

        previous_button.callback = previous
        next_button.callback = next_page
        refresh_button.callback = refresh
        close_button.callback = close
        self.add_item(previous_button)
        self.add_item(refresh_button)
        self.add_item(next_button)
        self.add_item(close_button)

    def build_embed(self) -> discord.Embed:
        _, title, description = PANEL_PAGES[self.page]
        embed = discord.Embed(
            title=f"AutoMod {title}",
            description=description,
            color=getattr(Config, "COLOR_MOD", 0x5865F2),
        )
        embed.set_footer(text=f"Page {self.page + 1}/{len(PANEL_PAGES)}")
        if self.page == 0:
            enabled = [name for name, key in MODULE_SETTING_KEYS.items() if self.settings.get(key, False)]
            disabled = [name for name, key in MODULE_SETTING_KEYS.items() if not self.settings.get(key, False)]
            embed.add_field(name="System", value=f"Enabled: `{bool(self.settings.get('automod_enabled', True))}`\nLog channel: {self._channel_label(self.settings.get('automod_log_channel'))}", inline=False)
            embed.add_field(name="Enabled Modules", value=", ".join(f"`{item}`" for item in enabled) or "None", inline=False)
            embed.add_field(name="Disabled Modules", value=", ".join(f"`{item}`" for item in disabled) or "None", inline=False)
        elif self.page == 1:
            rows = (
                f"Spam: `{self.settings.get('automod_spam_threshold', 5)}/{self.settings.get('automod_spam_window', 5)}s`",
                f"Duplicates: `{self.settings.get('automod_duplicate_threshold', 3)}/{self.settings.get('automod_duplicate_window', 30)}s`",
                f"Fast messages: `{self.settings.get('automod_fast_message_threshold', 4)}/{self.settings.get('automod_fast_message_window', 3)}s`",
                f"Caps: `{self.settings.get('automod_caps_percentage', 70)}% after {self.settings.get('automod_caps_min_length', 12)} letters`",
                f"Mentions: `{self.settings.get('automod_max_mentions', 5)}`",
                f"Raid: `{self.settings.get('automod_raid_join_threshold', 8)}/{self.settings.get('automod_raid_join_window', 20)}s`",
            )
            embed.add_field(name="Thresholds", value="\n".join(rows), inline=False)
        elif self.page == 2:
            embed.add_field(
                name="Punishments",
                value=(
                    f"Default: `{self.settings.get('automod_punishment', 'warn')}`\n"
                    f"Security: `{self.settings.get('automod_security_punishment', 'timeout')}`\n"
                    f"Raid: `{self.settings.get('automod_raid_punishment', 'timeout')}`\n"
                    f"Mute duration: `{compact_duration(int(self.settings.get('automod_mute_duration', 3600)))}`\n"
                    f"Escalation: `{bool(self.settings.get('automod_escalation_enabled', True))}`"
                ),
                inline=False,
            )
        else:
            embed.add_field(name="Roles", value=self._ids("automod_bypass_roles", role=True), inline=False)
            embed.add_field(name="Users", value=self._ids("automod_bypass_users"), inline=False)
            embed.add_field(name="Channels", value=self._ids("automod_bypass_channels", channel=True), inline=False)
        return embed

    async def build_layout(self) -> discord.ui.LayoutView:
        layout = discord.ui.LayoutView(timeout=self.timeout)
        embed = self.build_embed()
        lines = [f"## {embed.title}", embed.description or ""]
        for field in embed.fields:
            lines.append(f"**{field.name}**\n{field.value}")
        controls = [
            discord.ui.Button(label=str(item.label), style=item.style, disabled=item.disabled, row=item.row)
            for item in self.children
            if isinstance(item, discord.ui.Button)
        ]
        layout.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("\n\n".join(lines)[:3500]),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.ActionRow(*controls),
                accent_color=getattr(Config, "COLOR_MOD", 0x5865F2),
            )
        )
        return layout

    def _ids(self, key: str, *, role: bool = False, channel: bool = False) -> str:
        values = self.settings.get(key, []) or []
        if not values:
            return "None"
        rendered: list[str] = []
        for value in values[:12]:
            try:
                item_id = int(value)
            except (TypeError, ValueError):
                continue
            if role:
                rendered.append(f"<@&{item_id}>")
            elif channel:
                rendered.append(f"<#{item_id}>")
            else:
                rendered.append(f"<@{item_id}>")
        extra = len(values) - len(rendered)
        if extra > 0:
            rendered.append(f"+{extra} more")
        return ", ".join(rendered) or "None"

    def _channel_label(self, value: Any) -> str:
        try:
            channel_id = int(value)
        except (TypeError, ValueError):
            return "None"
        return f"<#{channel_id}>"
