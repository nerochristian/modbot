"""AutoMod Discord integration and slash-command configuration surface."""

from __future__ import annotations

import asyncio
import copy
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Literal, Mapping, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from cogs.automod_config import AUTOMOD_SETTINGS
from cogs.automod_engine import (
    Action,
    AutoModEngine,
    RULE_SETTING_KEYS,
    RuleMatch,
    normalize_domain,
)
from config import Config
from utils.checks import get_owner_ids, is_admin, is_mod
from utils.embeds import ModEmbed
from utils.logging import send_log_embed


logger = logging.getLogger("AutoMod")

RuleName = Literal[
    "words",
    "spam",
    "mentions",
    "caps",
    "links",
    "invites",
    "scams",
    "new_accounts",
    "ai",
]
ListOperation = Literal["add", "remove", "list", "clear"]
BypassOperation = Literal["add", "remove", "list"]
PolicyAction = Literal["log", "warn", "timeout", "kick", "ban", "quarantine"]


PRESETS: dict[str, dict[str, Any]] = {
    "relaxed": {
        "automod_enabled": True,
        "automod_badwords_enabled": True,
        "automod_spam_enabled": True,
        "automod_mentions_enabled": True,
        "automod_caps_enabled": False,
        "automod_links_enabled": True,
        "automod_invites_enabled": False,
        "automod_scam_protection": True,
        "automod_newaccount_enabled": False,
        "automod_ai_enabled": False,
        "automod_links_mode": "dangerous",
        "automod_spam_threshold": 7,
        "automod_spam_window": 5,
        "automod_duplicate_threshold": 4,
        "automod_duplicate_window": 30,
        "automod_caps_percentage": 90,
        "automod_caps_min_length": 20,
        "automod_max_mentions": 8,
        "automod_newaccount_days": 0,
        "automod_punishment": "warn",
        "automod_security_punishment": "timeout",
        "automod_mute_duration": 1800,
    },
    "standard": {
        "automod_enabled": True,
        "automod_badwords_enabled": True,
        "automod_spam_enabled": True,
        "automod_mentions_enabled": True,
        "automod_caps_enabled": True,
        "automod_links_enabled": True,
        "automod_invites_enabled": True,
        "automod_scam_protection": True,
        "automod_newaccount_enabled": True,
        "automod_ai_enabled": False,
        "automod_links_mode": "dangerous",
        "automod_spam_threshold": 5,
        "automod_spam_window": 5,
        "automod_duplicate_threshold": 3,
        "automod_duplicate_window": 30,
        "automod_caps_percentage": 80,
        "automod_caps_min_length": 12,
        "automod_max_mentions": 6,
        "automod_newaccount_days": 3,
        "automod_punishment": "warn",
        "automod_security_punishment": "timeout",
        "automod_mute_duration": 3600,
    },
    "strict": {
        "automod_enabled": True,
        "automod_badwords_enabled": True,
        "automod_spam_enabled": True,
        "automod_mentions_enabled": True,
        "automod_caps_enabled": True,
        "automod_links_enabled": True,
        "automod_invites_enabled": True,
        "automod_scam_protection": True,
        "automod_newaccount_enabled": True,
        "automod_ai_enabled": False,
        "automod_links_mode": "allowlist",
        "automod_spam_threshold": 4,
        "automod_spam_window": 5,
        "automod_duplicate_threshold": 3,
        "automod_duplicate_window": 20,
        "automod_caps_percentage": 70,
        "automod_caps_min_length": 10,
        "automod_max_mentions": 5,
        "automod_newaccount_days": 7,
        "automod_punishment": "timeout",
        "automod_security_punishment": "timeout",
        "automod_mute_duration": 3600,
    },
}


@dataclass
class EnforcementOutcome:
    action: Action
    success: bool
    details: str
    message_deleted: bool = False
    case_number: Optional[int] = None
    error: Optional[str] = None


def _format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts: list[str] = []
    for value, label in ((days, "day"), (hours, "hour"), (minutes, "minute"), (secs, "second")):
        if value:
            parts.append(f"{value} {label}{'' if value == 1 else 's'}")
    return ", ".join(parts[:2]) or "0 seconds"


def _compact_duration(seconds: int) -> str:
    seconds = max(60, int(seconds))
    parts: list[str] = []
    for suffix, size in (("w", 604800), ("d", 86400), ("h", 3600), ("m", 60)):
        value, seconds = divmod(seconds, size)
        if value:
            parts.append(f"{value}{suffix}")
    return "".join(parts) or "1m"


def _parse_duration(value: str) -> Optional[int]:
    raw = re.sub(r"\s+", "", (value or "").casefold())
    if not raw:
        return None
    matches = list(re.finditer(r"(\d+)(s|m|h|d|w)", raw))
    if not matches or "".join(match.group(0) for match in matches) != raw:
        return None
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    total = sum(int(match.group(1)) * multipliers[match.group(2)] for match in matches)
    return total if 60 <= total <= 28 * 86400 else None


def _truncate(value: str, limit: int) -> str:
    value = str(value or "")
    return value if len(value) <= limit else f"{value[: limit - 3]}..."


PANEL_PAGES: tuple[tuple[str, str, str], ...] = (
    ("overview", "Overview", "System state and presets"),
    ("rules", "Rules", "Enable or disable detectors"),
    ("thresholds", "Thresholds", "Tune spam and content limits"),
    ("actions", "Actions", "Punishments and notifications"),
    ("lists", "Lists", "Words, domains and invite codes"),
    ("routing", "Routing", "Logs and quarantine role"),
    ("bypasses", "Bypasses", "Ignored roles and channels"),
)


def _parse_threshold_pair(
    raw: str,
    *,
    count_range: tuple[int, int],
    window_range: tuple[int, int],
) -> Optional[tuple[int, int]]:
    match = re.fullmatch(r"\s*(\d+)\s*[/,]\s*(\d+)\s*", raw or "")
    if match is None:
        return None
    count, window = int(match.group(1)), int(match.group(2))
    if not count_range[0] <= count <= count_range[1]:
        return None
    if not window_range[0] <= window <= window_range[1]:
        return None
    return count, window


class AutoModThresholdsModal(discord.ui.Modal, title="AutoMod thresholds"):
    def __init__(self, panel: "AutoModPanel") -> None:
        super().__init__(timeout=300)
        self.panel = panel
        settings = panel.settings
        self.flood = discord.ui.TextInput(
            label="Flood: messages / seconds",
            default=f"{settings.get('automod_spam_threshold', 5)}/{settings.get('automod_spam_window', 5)}",
            placeholder="5/5",
            max_length=7,
        )
        self.duplicates = discord.ui.TextInput(
            label="Duplicates: messages / seconds",
            default=f"{settings.get('automod_duplicate_threshold', 3)}/{settings.get('automod_duplicate_window', 30)}",
            placeholder="3/30",
            max_length=8,
        )
        self.mentions = discord.ui.TextInput(
            label="Maximum unique mentions",
            default=str(settings.get("automod_max_mentions", 5)),
            placeholder="5",
            max_length=2,
        )
        self.caps = discord.ui.TextInput(
            label="Caps: percent / minimum letters",
            default=f"{settings.get('automod_caps_percentage', 70)}/{settings.get('automod_caps_min_length', 10)}",
            placeholder="70/10",
            max_length=7,
        )
        self.account_age = discord.ui.TextInput(
            label="New-account age in days (0 disables)",
            default=str(settings.get("automod_newaccount_days", 7)),
            placeholder="7",
            max_length=3,
        )
        for item in (self.flood, self.duplicates, self.mentions, self.caps, self.account_age):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        flood = _parse_threshold_pair(str(self.flood), count_range=(2, 50), window_range=(2, 60))
        duplicates = _parse_threshold_pair(str(self.duplicates), count_range=(2, 20), window_range=(5, 300))
        caps = _parse_threshold_pair(str(self.caps), count_range=(50, 100), window_range=(5, 500))
        try:
            mentions = int(str(self.mentions).strip())
            account_age = int(str(self.account_age).strip())
        except ValueError:
            mentions = account_age = -1
        if flood is None or duplicates is None or caps is None or not 1 <= mentions <= 50 or not 0 <= account_age <= 365:
            await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Invalid thresholds",
                    "Flood `2-50/2-60`, duplicates `2-20/5-300`, mentions `1-50`, "
                    "caps `50-100/5-500`, and account age `0-365` are accepted.",
                ),
                ephemeral=True,
            )
            return

        def edit(settings: dict[str, Any]) -> None:
            settings.update(
                {
                    "automod_spam_threshold": flood[0],
                    "automod_spam_window": flood[1],
                    "automod_duplicate_threshold": duplicates[0],
                    "automod_duplicate_window": duplicates[1],
                    "automod_max_mentions": mentions,
                    "automod_caps_percentage": caps[0],
                    "automod_caps_min_length": caps[1],
                    "automod_newaccount_days": account_age,
                }
            )

        await self.panel.commit(interaction, edit, "Thresholds updated")


class AutoModDurationModal(discord.ui.Modal, title="AutoMod timeout duration"):
    def __init__(self, panel: "AutoModPanel") -> None:
        super().__init__(timeout=300)
        self.panel = panel
        current = _compact_duration(int(panel.settings.get("automod_mute_duration", 3600)))
        self.duration = discord.ui.TextInput(
            label="Duration (1 minute to 28 days)",
            default=current,
            placeholder="1h, 2h30m, or 1d",
            min_length=2,
            max_length=20,
        )
        self.add_item(self.duration)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        duration = _parse_duration(str(self.duration))
        if duration is None:
            await interaction.response.send_message(
                embed=ModEmbed.error("Invalid duration", "Use `30m`, `2h`, `1d12h`, or another value from 1 minute to 28 days."),
                ephemeral=True,
            )
            return
        await self.panel.commit(
            interaction,
            lambda settings: settings.__setitem__("automod_mute_duration", duration),
            "Timeout duration updated",
        )


class AutoModListModal(discord.ui.Modal):
    def __init__(
        self,
        panel: "AutoModPanel",
        *,
        title: str,
        key: str,
        normalizer: Callable[[str], str],
        maximum: int,
        split_lines_only: bool = False,
    ) -> None:
        super().__init__(title=title, timeout=300)
        self.panel = panel
        self.key = key
        self.normalizer = normalizer
        self.maximum = maximum
        self.split_lines_only = split_lines_only
        self.additions = discord.ui.TextInput(
            label="Add entries (one per line)",
            style=discord.TextStyle.paragraph,
            placeholder="Leave blank to add nothing",
            required=False,
            max_length=1500,
        )
        self.removals = discord.ui.TextInput(
            label="Remove entries (one per line)",
            style=discord.TextStyle.paragraph,
            placeholder="Leave blank to remove nothing",
            required=False,
            max_length=1500,
        )
        self.add_item(self.additions)
        self.add_item(self.removals)

    def _values(self, raw: str) -> list[str]:
        parts = raw.splitlines() if self.split_lines_only else re.split(r"[\n,]+", raw)
        values: list[str] = []
        for part in parts:
            normalized = self.normalizer(part)
            if normalized and normalized not in values:
                values.append(normalized)
        return values

    async def on_submit(self, interaction: discord.Interaction) -> None:
        additions = self._values(str(self.additions))
        removals = set(self._values(str(self.removals)))
        if not additions and not removals:
            await interaction.response.send_message(
                embed=ModEmbed.warning("No changes", "Add at least one entry or specify an entry to remove."),
                ephemeral=True,
            )
            return
        current = [
            self.normalizer(str(value))
            for value in self.panel.settings.get(self.key, [])
            if self.normalizer(str(value))
        ]
        updated = [value for value in dict.fromkeys(current) if value not in removals]
        for value in additions:
            if value not in updated:
                updated.append(value)
        if len(updated) > self.maximum:
            await interaction.response.send_message(
                embed=ModEmbed.error("List full", f"This list supports at most {self.maximum} entries."),
                ephemeral=True,
            )
            return
        await self.panel.commit(
            interaction,
            lambda settings: settings.__setitem__(self.key, updated),
            f"List updated ({len(updated)} entries)",
        )


class AutoModPanel(discord.ui.View):
    """Paged AutoMod configuration UI backed by the canonical guild settings."""

    def __init__(
        self,
        cog: "AutoMod",
        guild: discord.Guild,
        owner_id: int,
        settings: dict[str, Any],
    ) -> None:
        super().__init__(timeout=600)
        self.cog = cog
        self.guild = guild
        self.owner_id = owner_id
        self.settings = settings
        self.page = "overview"
        self.message: Optional[discord.InteractionMessage] = None
        self.notice = ""
        self.rebuild()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("This panel belongs to another administrator.", ephemeral=True)
        return False

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item[Any]) -> None:
        logger.exception("AutoMod panel interaction failed", exc_info=error)
        if interaction.response.is_done():
            await interaction.followup.send("The panel could not apply that change. Check the bot logs.", ephemeral=True)
        else:
            await interaction.response.send_message("The panel could not apply that change. Check the bot logs.", ephemeral=True)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass

    async def commit(
        self,
        interaction: discord.Interaction,
        editor: Callable[[dict[str, Any]], None],
        notice: str,
    ) -> None:
        await interaction.response.defer()
        self.settings = await self.cog._edit_settings(self.guild.id, editor)
        self.notice = notice
        self.rebuild()
        if self.message is not None:
            await self.message.edit(embed=self.build_embed(), view=self)

    async def refresh(self, interaction: discord.Interaction, notice: str = "Settings refreshed") -> None:
        await interaction.response.defer()
        self.settings = await self.cog._get_settings(self.guild.id, fresh=True)
        self.notice = notice
        self.rebuild()
        if self.message is not None:
            await self.message.edit(embed=self.build_embed(), view=self)

    def build_embed(self) -> discord.Embed:
        page_label = next(label for value, label, _ in PANEL_PAGES if value == self.page)
        enabled = bool(self.settings.get("automod_enabled", True))
        embed = discord.Embed(
            title=f"AutoMod Control Panel · {page_label}",
            description=(
                f"System status: **{'ONLINE' if enabled else 'OFFLINE'}**\n"
                "Use the page menu and controls below. Every change saves immediately."
            ),
            color=Config.COLOR_SUCCESS if enabled else Config.COLOR_WARNING,
            timestamp=datetime.now(timezone.utc),
        )
        if self.page == "overview":
            enabled_count = sum(bool(self.settings.get(key, False)) for key in RULE_SETTING_KEYS.values())
            log_channel = self.guild.get_channel(self.settings.get("automod_log_channel")) if self.settings.get("automod_log_channel") else None
            embed.add_field(name="Protection", value=f"**{enabled_count}/{len(RULE_SETTING_KEYS)}** rules enabled", inline=True)
            embed.add_field(
                name="Policy",
                value=(
                    f"Regular: **{str(self.settings.get('automod_punishment', 'warn')).title()}**\n"
                    f"Security: **{str(self.settings.get('automod_security_punishment', 'timeout')).title()}**"
                ),
                inline=True,
            )
            embed.add_field(name="Logs", value=log_channel.mention if log_channel else "`Not configured`", inline=True)
            embed.add_field(
                name="Recommended start",
                value="Apply **Standard**, choose a log channel on **Routing**, then use `/automod test` with sample messages.",
                inline=False,
            )
        elif self.page == "rules":
            lines = [
                f"{'●' if self.settings.get(key, False) else '○'} **{rule.replace('_', ' ').title()}**"
                for rule, key in RULE_SETTING_KEYS.items()
            ]
            embed.add_field(name="Detectors", value="\n".join(lines), inline=False)
        elif self.page == "thresholds":
            embed.add_field(
                name="Flood and duplicates",
                value=(
                    f"Flood: **{self.settings.get('automod_spam_threshold', 5)} messages / {self.settings.get('automod_spam_window', 5)}s**\n"
                    f"Duplicate: **{self.settings.get('automod_duplicate_threshold', 3)} messages / {self.settings.get('automod_duplicate_window', 30)}s**"
                ),
                inline=False,
            )
            embed.add_field(
                name="Content limits",
                value=(
                    f"Mentions: **{self.settings.get('automod_max_mentions', 5)}**\n"
                    f"Caps: **{self.settings.get('automod_caps_percentage', 70)}%** after **{self.settings.get('automod_caps_min_length', 10)}** letters\n"
                    f"New account: **{self.settings.get('automod_newaccount_days', 7)} days**"
                ),
                inline=False,
            )
        elif self.page == "actions":
            embed.add_field(
                name="Enforcement",
                value=(
                    f"Regular violations: **{str(self.settings.get('automod_punishment', 'warn')).title()}**\n"
                    f"Security violations: **{str(self.settings.get('automod_security_punishment', 'timeout')).title()}**\n"
                    f"Timeout duration: **{_format_duration(self.settings.get('automod_mute_duration', 3600))}**"
                ),
                inline=False,
            )
            embed.add_field(
                name="Feedback",
                value=(
                    f"DM users: **{'On' if self.settings.get('automod_notify_users', True) else 'Off'}**\n"
                    f"Channel notice: **{'On' if self.settings.get('automod_public_feedback', False) else 'Off'}**"
                ),
                inline=False,
            )
        elif self.page == "lists":
            for title, key in (
                ("Blocked words and phrases", "automod_badwords"),
                ("Allowed domains", "automod_whitelisted_domains"),
                ("Allowed invite codes", "automod_allowed_invites"),
            ):
                values = list(self.settings.get(key, []) or [])
                preview = ", ".join(f"`{_truncate(value, 30)}`" for value in values[:8]) or "`None`"
                if len(values) > 8:
                    preview += f" and {len(values) - 8} more"
                embed.add_field(name=f"{title} ({len(values)})", value=preview, inline=False)
        elif self.page == "routing":
            log_channel = self.guild.get_channel(self.settings.get("automod_log_channel")) if self.settings.get("automod_log_channel") else None
            quarantine = self.guild.get_role(self.settings.get("automod_quarantine_role_id")) if self.settings.get("automod_quarantine_role_id") else None
            embed.add_field(name="Log channel", value=log_channel.mention if log_channel else "`Not configured`", inline=False)
            embed.add_field(name="Quarantine role", value=quarantine.mention if quarantine else "`Not configured`", inline=False)
            embed.add_field(name="Clearing values", value="Open either selector and submit no selection to clear its value.", inline=False)
        elif self.page == "bypasses":
            role_ids = list(dict.fromkeys(int(value) for value in self.settings.get("automod_bypass_roles", []) or [] if str(value).isdigit()))
            channel_ids = list(dict.fromkeys(int(value) for value in self.settings.get("automod_bypass_channels", []) or [] if str(value).isdigit()))
            roles = ", ".join(f"<@&{value}>" for value in role_ids[:10]) or "`None`"
            channels = ", ".join(f"<#{value}>" for value in channel_ids[:10]) or "`None`"
            embed.add_field(name=f"Roles ({len(role_ids)})", value=roles, inline=False)
            embed.add_field(name=f"Channels ({len(channel_ids)})", value=channels, inline=False)
            embed.add_field(
                name="Staff bypass",
                value=f"**{'On' if self.settings.get('automod_bypass_staff', True) else 'Off'}** — administrators and moderators are ignored.",
                inline=False,
            )
        if self.notice:
            embed.set_footer(text=f"Saved · {self.notice}")
        else:
            embed.set_footer(text="Panel expires after 10 minutes of inactivity")
        return embed

    def rebuild(self) -> None:
        self.clear_items()
        navigation = discord.ui.Select(
            placeholder="Choose a settings page",
            options=[
                discord.SelectOption(label=label, value=value, description=description, default=value == self.page)
                for value, label, description in PANEL_PAGES
            ],
            row=0,
        )
        navigation.callback = self._change_page
        self.add_item(navigation)
        getattr(self, f"_build_{self.page}")()

    def _button(
        self,
        *,
        label: str,
        style: discord.ButtonStyle,
        row: int,
        callback: Callable[[discord.Interaction], Any],
        disabled: bool = False,
    ) -> None:
        button = discord.ui.Button(label=label, style=style, row=row, disabled=disabled)
        button.callback = callback
        self.add_item(button)

    def _build_overview(self) -> None:
        enabled = bool(self.settings.get("automod_enabled", True))
        self._button(
            label="Disable AutoMod" if enabled else "Enable AutoMod",
            style=discord.ButtonStyle.danger if enabled else discord.ButtonStyle.success,
            row=1,
            callback=self._toggle_master,
        )
        self._button(label="Refresh", style=discord.ButtonStyle.secondary, row=1, callback=self._refresh)
        self._button(label="Close", style=discord.ButtonStyle.secondary, row=1, callback=self._close)
        presets = discord.ui.Select(
            placeholder="Apply a complete protection preset",
            options=[
                discord.SelectOption(label="Relaxed", value="relaxed", description="Basic safety with fewer interruptions"),
                discord.SelectOption(label="Standard", value="standard", description="Recommended for most servers"),
                discord.SelectOption(label="Strict", value="strict", description="Allowlisted links and stronger limits"),
            ],
            row=2,
        )
        presets.callback = self._apply_preset
        self.add_item(presets)

    def _build_rules(self) -> None:
        options = [
            discord.SelectOption(
                label=rule.replace("_", " ").title(),
                value=rule,
                default=bool(self.settings.get(key, False)),
            )
            for rule, key in RULE_SETTING_KEYS.items()
        ]
        select = discord.ui.Select(
            placeholder="Select every rule that should be enabled",
            options=options,
            min_values=0,
            max_values=len(options),
            row=1,
        )
        select.callback = self._set_rules
        self.add_item(select)
        self._button(label="Enable recommended rules", style=discord.ButtonStyle.primary, row=2, callback=self._recommended_rules)
        self._button(label="Disable all rules", style=discord.ButtonStyle.danger, row=2, callback=self._disable_rules)

    def _build_thresholds(self) -> None:
        self._button(label="Edit thresholds", style=discord.ButtonStyle.primary, row=1, callback=self._open_thresholds)
        self._button(label="Use standard thresholds", style=discord.ButtonStyle.secondary, row=1, callback=self._standard_thresholds)

    def _build_actions(self) -> None:
        actions = [
            discord.SelectOption(label=label, value=value)
            for label, value in (
                ("Log only", "log"),
                ("Warn", "warn"),
                ("Timeout", "timeout"),
                ("Kick", "kick"),
                ("Ban", "ban"),
                ("Quarantine", "quarantine"),
            )
        ]
        regular = discord.ui.Select(placeholder="Set the regular violation action", options=actions, row=1)
        regular.callback = self._set_regular_action
        self.add_item(regular)
        security = discord.ui.Select(placeholder="Set the security violation action", options=actions, row=2)
        security.callback = self._set_security_action
        self.add_item(security)
        self._button(label="Set timeout duration", style=discord.ButtonStyle.primary, row=3, callback=self._open_duration)
        self._button(
            label=f"User DMs: {'On' if self.settings.get('automod_notify_users', True) else 'Off'}",
            style=discord.ButtonStyle.success if self.settings.get("automod_notify_users", True) else discord.ButtonStyle.secondary,
            row=3,
            callback=self._toggle_notify,
        )
        self._button(
            label=f"Channel notices: {'On' if self.settings.get('automod_public_feedback', False) else 'Off'}",
            style=discord.ButtonStyle.success if self.settings.get("automod_public_feedback", False) else discord.ButtonStyle.secondary,
            row=3,
            callback=self._toggle_public,
        )

    def _build_lists(self) -> None:
        self._button(label="Edit blocked words", style=discord.ButtonStyle.primary, row=1, callback=self._open_words)
        self._button(label="Edit allowed domains", style=discord.ButtonStyle.primary, row=2, callback=self._open_domains)
        self._button(label="Edit allowed invites", style=discord.ButtonStyle.primary, row=3, callback=self._open_invites)
        mode = str(self.settings.get("automod_links_mode", "dangerous"))
        self._button(
            label=f"Link mode: {mode.title()}",
            style=discord.ButtonStyle.secondary,
            row=4,
            callback=self._toggle_link_mode,
        )

    def _build_routing(self) -> None:
        logs = discord.ui.ChannelSelect(
            placeholder="Set log channel (empty selection clears)",
            min_values=0,
            max_values=1,
            channel_types=[discord.ChannelType.text],
            row=1,
        )
        logs.callback = self._set_log_channel
        self.add_item(logs)
        quarantine = discord.ui.RoleSelect(
            placeholder="Set quarantine role (empty selection clears)",
            min_values=0,
            max_values=1,
            row=2,
        )
        quarantine.callback = self._set_quarantine_role
        self.add_item(quarantine)

    def _build_bypasses(self) -> None:
        roles = discord.ui.RoleSelect(placeholder="Add a bypass role", min_values=1, max_values=1, row=1)
        roles.callback = self._add_bypass_role
        self.add_item(roles)
        channels = discord.ui.ChannelSelect(
            placeholder="Add a bypass channel",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text, discord.ChannelType.forum],
            row=2,
        )
        channels.callback = self._add_bypass_channel
        self.add_item(channels)
        options: list[discord.SelectOption] = []
        for value in self.settings.get("automod_bypass_roles", []) or []:
            if str(value).isdigit():
                role = self.guild.get_role(int(value))
                options.append(discord.SelectOption(label=f"Role: {role.name if role else value}", value=f"role:{value}"))
        for value in self.settings.get("automod_bypass_channels", []) or []:
            if str(value).isdigit():
                channel = self.guild.get_channel(int(value))
                options.append(discord.SelectOption(label=f"Channel: {channel.name if channel else value}", value=f"channel:{value}"))
        if options:
            remove = discord.ui.Select(
                placeholder="Remove bypass entries",
                options=options[:25],
                min_values=1,
                max_values=min(25, len(options)),
                row=3,
            )
            remove.callback = self._remove_bypasses
            self.add_item(remove)
        else:
            self._button(label="No bypass entries to remove", style=discord.ButtonStyle.secondary, row=3, callback=self._refresh, disabled=True)
        self._button(
            label=f"Staff bypass: {'On' if self.settings.get('automod_bypass_staff', True) else 'Off'}",
            style=discord.ButtonStyle.success if self.settings.get("automod_bypass_staff", True) else discord.ButtonStyle.secondary,
            row=4,
            callback=self._toggle_staff_bypass,
        )

    async def _change_page(self, interaction: discord.Interaction) -> None:
        self.page = str(interaction.data["values"][0])
        self.notice = ""
        self.rebuild()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def _toggle_master(self, interaction: discord.Interaction) -> None:
        enabled = not bool(self.settings.get("automod_enabled", True))
        await self.commit(interaction, lambda settings: settings.__setitem__("automod_enabled", enabled), f"AutoMod {'enabled' if enabled else 'disabled'}")

    async def _refresh(self, interaction: discord.Interaction) -> None:
        await self.refresh(interaction)

    async def _close(self, interaction: discord.Interaction) -> None:
        self.stop()
        embed = self.build_embed()
        embed.description = "This control panel was closed. Run `/automod panel` to open a new one."
        embed.set_footer(text="Panel closed")
        await interaction.response.edit_message(embed=embed, view=None)

    async def _apply_preset(self, interaction: discord.Interaction) -> None:
        preset = str(interaction.data["values"][0])
        await self.commit(interaction, lambda settings: settings.update(copy.deepcopy(PRESETS[preset])), f"{preset.title()} preset applied")

    async def _set_rules(self, interaction: discord.Interaction) -> None:
        selected = set(interaction.data.get("values", []))

        def edit(settings: dict[str, Any]) -> None:
            for rule, key in RULE_SETTING_KEYS.items():
                settings[key] = rule in selected

        await self.commit(interaction, edit, f"{len(selected)} rules enabled")

    async def _recommended_rules(self, interaction: discord.Interaction) -> None:
        recommended = {"words", "spam", "mentions", "caps", "links", "invites", "scams", "new_accounts"}

        def edit(settings: dict[str, Any]) -> None:
            for rule, key in RULE_SETTING_KEYS.items():
                settings[key] = rule in recommended

        await self.commit(interaction, edit, "Recommended rules enabled")

    async def _disable_rules(self, interaction: discord.Interaction) -> None:
        await self.commit(
            interaction,
            lambda settings: settings.update({key: False for key in RULE_SETTING_KEYS.values()}),
            "All rules disabled",
        )

    async def _open_thresholds(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(AutoModThresholdsModal(self))

    async def _standard_thresholds(self, interaction: discord.Interaction) -> None:
        keys = (
            "automod_spam_threshold",
            "automod_spam_window",
            "automod_duplicate_threshold",
            "automod_duplicate_window",
            "automod_max_mentions",
            "automod_caps_percentage",
            "automod_caps_min_length",
            "automod_newaccount_days",
        )
        await self.commit(
            interaction,
            lambda settings: settings.update({key: PRESETS["standard"][key] for key in keys}),
            "Standard thresholds applied",
        )

    async def _set_regular_action(self, interaction: discord.Interaction) -> None:
        value = str(interaction.data["values"][0])
        await self.commit(interaction, lambda settings: settings.__setitem__("automod_punishment", value), f"Regular action set to {value}")

    async def _set_security_action(self, interaction: discord.Interaction) -> None:
        value = str(interaction.data["values"][0])
        await self.commit(interaction, lambda settings: settings.__setitem__("automod_security_punishment", value), f"Security action set to {value}")

    async def _open_duration(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(AutoModDurationModal(self))

    async def _toggle_notify(self, interaction: discord.Interaction) -> None:
        value = not bool(self.settings.get("automod_notify_users", True))
        await self.commit(interaction, lambda settings: settings.__setitem__("automod_notify_users", value), f"User DMs {'enabled' if value else 'disabled'}")

    async def _toggle_public(self, interaction: discord.Interaction) -> None:
        value = not bool(self.settings.get("automod_public_feedback", False))
        await self.commit(interaction, lambda settings: settings.__setitem__("automod_public_feedback", value), f"Channel notices {'enabled' if value else 'disabled'}")

    async def _open_words(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(
            AutoModListModal(
                self,
                title="Blocked words and phrases",
                key="automod_badwords",
                normalizer=lambda value: re.sub(r"\s+", " ", value.strip().casefold()),
                maximum=500,
                split_lines_only=True,
            )
        )

    async def _open_domains(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(
            AutoModListModal(self, title="Allowed domains", key="automod_whitelisted_domains", normalizer=normalize_domain, maximum=500)
        )

    async def _open_invites(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(
            AutoModListModal(
                self,
                title="Allowed Discord invites",
                key="automod_allowed_invites",
                normalizer=lambda value: value.strip().rstrip("/").rsplit("/", 1)[-1].casefold(),
                maximum=250,
            )
        )

    async def _toggle_link_mode(self, interaction: discord.Interaction) -> None:
        value = "allowlist" if self.settings.get("automod_links_mode", "dangerous") == "dangerous" else "dangerous"
        await self.commit(interaction, lambda settings: settings.__setitem__("automod_links_mode", value), f"Link mode set to {value}")

    async def _set_log_channel(self, interaction: discord.Interaction) -> None:
        values = interaction.data.get("values", [])
        value = int(values[0]) if values else None
        await self.commit(interaction, lambda settings: settings.__setitem__("automod_log_channel", value), "Log channel updated")

    async def _set_quarantine_role(self, interaction: discord.Interaction) -> None:
        values = interaction.data.get("values", [])
        value = int(values[0]) if values else None
        await self.commit(interaction, lambda settings: settings.__setitem__("automod_quarantine_role_id", value), "Quarantine role updated")

    async def _add_bypass_role(self, interaction: discord.Interaction) -> None:
        role_id = int(interaction.data["values"][0])

        def edit(settings: dict[str, Any]) -> None:
            values = list(dict.fromkeys(int(value) for value in settings.get("automod_bypass_roles", []) or [] if str(value).isdigit()))
            if role_id not in values:
                values.append(role_id)
            settings["automod_bypass_roles"] = values

        await self.commit(interaction, edit, "Bypass role added")

    async def _add_bypass_channel(self, interaction: discord.Interaction) -> None:
        channel_id = int(interaction.data["values"][0])

        def edit(settings: dict[str, Any]) -> None:
            values = list(dict.fromkeys(int(value) for value in settings.get("automod_bypass_channels", []) or [] if str(value).isdigit()))
            if channel_id not in values:
                values.append(channel_id)
            settings["automod_bypass_channels"] = values

        await self.commit(interaction, edit, "Bypass channel added")

    async def _remove_bypasses(self, interaction: discord.Interaction) -> None:
        selected = set(interaction.data.get("values", []))

        def edit(settings: dict[str, Any]) -> None:
            settings["automod_bypass_roles"] = [
                int(value) for value in settings.get("automod_bypass_roles", []) or []
                if str(value).isdigit() and f"role:{value}" not in selected
            ]
            settings["automod_bypass_channels"] = [
                int(value) for value in settings.get("automod_bypass_channels", []) or []
                if str(value).isdigit() and f"channel:{value}" not in selected
            ]

        await self.commit(interaction, edit, f"{len(selected)} bypass entries removed")

    async def _toggle_staff_bypass(self, interaction: discord.Interaction) -> None:
        value = not bool(self.settings.get("automod_bypass_staff", True))
        await self.commit(interaction, lambda settings: settings.__setitem__("automod_bypass_staff", value), f"Staff bypass {'enabled' if value else 'disabled'}")


class AutoMod(commands.Cog):
    """Configurable message moderation with deterministic local rules."""

    automod = app_commands.Group(name="automod", description="Configure and inspect AutoMod")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.engine = AutoModEngine()
        self._settings_cache: dict[int, tuple[float, dict[str, Any]]] = {}
        self._settings_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.cleanup_runtime_state.start()

    async def cog_unload(self) -> None:
        self.cleanup_runtime_state.cancel()
        await self.engine.close()

    @tasks.loop(minutes=15)
    async def cleanup_runtime_state(self) -> None:
        self.engine.prune()
        now = time.monotonic()
        for guild_id, (expires_at, _) in list(self._settings_cache.items()):
            if expires_at <= now:
                self._settings_cache.pop(guild_id, None)
        active_guild_ids = {guild.id for guild in self.bot.guilds}
        for guild_id in list(self._settings_locks):
            if guild_id not in active_guild_ids and guild_id not in self._settings_cache:
                self._settings_locks.pop(guild_id, None)

    @cleanup_runtime_state.before_loop
    async def before_cleanup_runtime_state(self) -> None:
        await self.bot.wait_until_ready()

    @staticmethod
    def _sync_master_module(settings: dict[str, Any]) -> None:
        modules = settings.setdefault("modules", {})
        if not isinstance(modules, dict):
            modules = {}
            settings["modules"] = modules
        module = modules.setdefault("automod", {})
        if not isinstance(module, dict):
            module = {}
            modules["automod"] = module
        module["enabled"] = bool(settings.get("automod_enabled", True))

    async def _get_settings(self, guild_id: int, *, fresh: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        cached = self._settings_cache.get(guild_id)
        if not fresh and cached and cached[0] > now:
            return copy.deepcopy(cached[1])
        async with self._settings_locks[guild_id]:
            cached = self._settings_cache.get(guild_id)
            now = time.monotonic()
            if not fresh and cached and cached[0] > now:
                return copy.deepcopy(cached[1])
            settings = await self.bot.db.get_settings(guild_id)
            self._settings_cache[guild_id] = (now + 30, copy.deepcopy(settings))
            return settings

    async def _edit_settings(
        self,
        guild_id: int,
        editor: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        async with self._settings_locks[guild_id]:
            settings = await self.bot.db.get_settings(guild_id)
            editor(settings)
            self._sync_master_module(settings)
            await self.bot.db.update_settings(guild_id, settings)
            self._settings_cache[guild_id] = (time.monotonic() + 30, copy.deepcopy(settings))
            return settings

    @staticmethod
    def _ensure_guild(interaction: discord.Interaction) -> Optional[int]:
        return interaction.guild_id

    @staticmethod
    def _status_embed(settings: Mapping[str, Any], guild: discord.Guild) -> discord.Embed:
        enabled = bool(settings.get("automod_enabled", True))
        embed = discord.Embed(
            title="AutoMod status",
            description=f"System: **{'Enabled' if enabled else 'Disabled'}**",
            color=Config.COLOR_SUCCESS if enabled else Config.COLOR_WARNING,
            timestamp=datetime.now(timezone.utc),
        )
        rules = []
        for rule, key in RULE_SETTING_KEYS.items():
            marker = "ON" if settings.get(key, False) else "OFF"
            rules.append(f"`{marker:<3}` {rule.replace('_', ' ').title()}")
        embed.add_field(name="Rules", value="\n".join(rules), inline=True)
        regular = str(settings.get("automod_punishment", "warn")).replace("mute", "timeout").title()
        security = str(settings.get("automod_security_punishment", "timeout")).replace("mute", "timeout").title()
        duration = _format_duration(int(settings.get("automod_mute_duration", 3600)))
        embed.add_field(
            name="Actions",
            value=f"Regular: **{regular}**\nSecurity: **{security}**\nTimeout: **{duration}**",
            inline=True,
        )
        log_channel = guild.get_channel(settings.get("automod_log_channel")) if settings.get("automod_log_channel") else None
        bypass_roles = settings.get("automod_bypass_roles", []) or []
        if settings.get("automod_bypass_role_id"):
            bypass_roles = list(bypass_roles) + [settings["automod_bypass_role_id"]]
        embed.add_field(
            name="Routing",
            value=(
                f"Logs: {log_channel.mention if log_channel else '`Not set`'}\n"
                f"Bypass roles: **{len(set(bypass_roles))}**\n"
                f"Bypass channels: **{len(set(settings.get('automod_bypass_channels', []) or []))}**"
            ),
            inline=False,
        )
        embed.set_footer(text="Use /automod help for the command map")
        return embed

    @staticmethod
    def _can_act_on(member: discord.Member, guild: discord.Guild) -> Optional[str]:
        bot_member = guild.me
        if member.id == guild.owner_id:
            return "The server owner cannot be moderated."
        if bot_member is None:
            return "The bot member could not be resolved."
        if member.top_role >= bot_member.top_role:
            return "Move the bot role above the target member's highest role."
        return None

    async def _create_case(
        self,
        guild: discord.Guild,
        member: discord.Member,
        action: Action,
        reason: str,
        duration: Optional[str] = None,
    ) -> Optional[int]:
        try:
            return await self.bot.db.create_case(
                guild.id,
                member.id,
                self.bot.user.id,
                f"AutoMod {action.value.title()}",
                reason,
                duration,
            )
        except Exception:
            logger.exception("Failed to create AutoMod case in guild %s", guild.id)
            return None

    async def _apply_warning_threshold(
        self,
        member: discord.Member,
        settings: Mapping[str, Any],
        warning_count: int,
        reason: str,
    ) -> Optional[str]:
        if not settings.get("warn_thresholds_enabled", True):
            return None
        guild = member.guild
        if warning_count >= int(settings.get("warn_threshold_ban", 7) or 10**9):
            await guild.ban(member, reason=f"[AutoMod] Warning threshold: {reason}")
            return "Ban threshold reached"
        if warning_count >= int(settings.get("warn_threshold_kick", 5) or 10**9):
            await member.kick(reason=f"[AutoMod] Warning threshold: {reason}")
            return "Kick threshold reached"
        if warning_count >= int(settings.get("warn_threshold_mute", 3) or 10**9):
            duration = min(28 * 86400, max(60, int(settings.get("warn_mute_duration", 3600))))
            await member.timeout(timedelta(seconds=duration), reason=f"[AutoMod] Warning threshold: {reason}")
            return f"Timeout threshold reached ({_format_duration(duration)})"
        return None

    async def _enforce(
        self,
        message: discord.Message,
        match: RuleMatch,
        settings: Mapping[str, Any],
    ) -> EnforcementOutcome:
        action = self.engine.resolve_action(match, settings)
        deleted = False
        deletion_error: Optional[str] = None
        if action is not Action.LOG and match.delete_message and settings.get("automod_delete_violations", True):
            try:
                await message.delete()
                deleted = True
            except discord.NotFound:
                deleted = True
            except discord.Forbidden:
                deletion_error = "Missing Manage Messages permission"
            except discord.HTTPException as exc:
                deletion_error = f"Discord rejected message deletion: {exc.code}"

        if action is Action.LOG:
            details = "Message deleted and logged" if deleted else "Logged only"
            success = deleted or not match.delete_message
            if deletion_error:
                details = deletion_error
            outcome = EnforcementOutcome(action, success, details, deleted, error=deletion_error)
            self.engine.mark_action(outcome.success)
            return outcome

        member = message.author
        hierarchy_error = self._can_act_on(member, message.guild)
        if hierarchy_error:
            outcome = EnforcementOutcome(action, False, hierarchy_error, deleted, error=hierarchy_error)
            self.engine.mark_action(False)
            return outcome

        duration_seconds = min(28 * 86400, max(60, int(settings.get("automod_mute_duration", 3600))))
        reason = _truncate(f"[AutoMod/{match.rule}] {match.reason}", 500)
        details = ""
        case_number: Optional[int] = None
        try:
            if action is Action.WARN:
                _, warning_count = await self.bot.db.add_warning(
                    message.guild.id,
                    member.id,
                    self.bot.user.id,
                    match.reason,
                )
                details = f"Warning issued (total: {warning_count})"
                threshold_result = await self._apply_warning_threshold(member, settings, warning_count, match.reason)
                if threshold_result:
                    details = f"{details}; {threshold_result}"
            elif action is Action.TIMEOUT:
                await member.timeout(timedelta(seconds=duration_seconds), reason=reason)
                details = f"Timed out for {_format_duration(duration_seconds)}"
            elif action is Action.KICK:
                await member.kick(reason=reason)
                details = "Kicked"
            elif action is Action.BAN:
                delete_seconds = min(7, max(0, int(settings.get("automod_ban_delete_days", 1)))) * 86400
                await message.guild.ban(member, reason=reason, delete_message_seconds=delete_seconds)
                details = "Banned"
            elif action is Action.QUARANTINE:
                role_id = settings.get("automod_quarantine_role_id")
                role = message.guild.get_role(int(role_id)) if role_id else None
                if role is None or role >= message.guild.me.top_role:
                    await member.timeout(timedelta(seconds=duration_seconds), reason=f"{reason} (quarantine fallback)")
                    details = f"Timed out for {_format_duration(duration_seconds)} (quarantine role unavailable)"
                else:
                    await member.add_roles(role, reason=reason)
                    details = f"Quarantined with {role.name}"
            duration = _format_duration(duration_seconds) if action is Action.TIMEOUT else None
            case_number = await self._create_case(message.guild, member, action, match.reason, duration)
            outcome = EnforcementOutcome(action, True, details, deleted, case_number)
        except discord.Forbidden:
            outcome = EnforcementOutcome(
                action,
                False,
                "Discord denied the action; check bot permissions and role order.",
                deleted,
                error="Forbidden",
            )
        except discord.HTTPException as exc:
            outcome = EnforcementOutcome(
                action,
                False,
                f"Discord rejected the action (HTTP {exc.status}, code {exc.code}).",
                deleted,
                error=str(exc),
            )
        except Exception as exc:
            logger.exception("AutoMod enforcement failed in guild %s", message.guild.id)
            outcome = EnforcementOutcome(action, False, "Internal enforcement error", deleted, error=str(exc))
        self.engine.mark_action(outcome.success)
        return outcome

    async def _send_log(
        self,
        message: discord.Message,
        match: RuleMatch,
        outcome: EnforcementOutcome,
        settings: Mapping[str, Any],
    ) -> None:
        channel_id = settings.get("automod_log_channel") or settings.get("log_channel_automod")
        channel = message.guild.get_channel(int(channel_id)) if channel_id else None
        if not isinstance(channel, discord.abc.Messageable):
            return
        colors = {
            "INFO": 0x3B82F6,
            "LOW": 0xF59E0B,
            "MEDIUM": 0xF97316,
            "HIGH": 0xEF4444,
            "CRITICAL": 0x991B1B,
        }
        embed = discord.Embed(
            title=f"AutoMod: {match.rule.replace('_', ' ').title()}",
            color=colors[match.severity.name],
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Member", value=f"{message.author.mention}\n`{message.author.id}`", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Severity", value=match.severity.name.title(), inline=True)
        embed.add_field(name="Reason", value=_truncate(match.reason, 1024), inline=False)
        action_text = outcome.details
        if outcome.case_number is not None:
            action_text += f"\nCase: `#{outcome.case_number}`"
        if not outcome.success:
            action_text = f"FAILED: {action_text}"
        embed.add_field(name="Action", value=_truncate(action_text, 1024), inline=False)
        if match.evidence:
            evidence = ", ".join(f"||{_truncate(item, 80)}||" for item in match.evidence)
            embed.add_field(name="Matched", value=_truncate(evidence, 1024), inline=False)
        content = (message.content or "").replace("```", "'''" )
        if content:
            embed.add_field(name="Message", value=f"```\n{_truncate(content, 900)}\n```", inline=False)
        try:
            await send_log_embed(channel, embed)
        except (discord.Forbidden, discord.HTTPException):
            logger.warning("Could not send AutoMod log in guild %s", message.guild.id)

    async def _notify_member(
        self,
        message: discord.Message,
        match: RuleMatch,
        outcome: EnforcementOutcome,
    ) -> None:
        if not outcome.success or outcome.action is Action.LOG:
            return
        embed = discord.Embed(
            title=f"Moderation action in {message.guild.name}",
            description="An automated rule was triggered by your message.",
            color=Config.COLOR_WARNING,
        )
        embed.add_field(name="Reason", value=_truncate(match.reason, 1024), inline=False)
        embed.add_field(name="Action", value=_truncate(outcome.details, 1024), inline=False)
        embed.set_footer(text="Contact the server's moderators if you believe this was a mistake.")
        try:
            await message.author.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            return

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot or message.webhook_id is not None:
            return
        try:
            settings = await self._get_settings(message.guild.id)
            if not settings.get("automod_enabled", True):
                return
            if self.engine.bypass_reason(message, settings, get_owner_ids()) is not None:
                return
            match = await self.engine.evaluate(message, settings)
            if match is None:
                return
            outcome = await self._enforce(message, match, settings)
            await self._send_log(message, match, outcome, settings)
            if settings.get("automod_notify_users", True):
                await self._notify_member(message, match, outcome)
            if settings.get("automod_public_feedback", False):
                text = f"AutoMod: {match.reason} — {outcome.details}"
                try:
                    await message.channel.send(
                        _truncate(text, 300),
                        delete_after=10,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                except (discord.Forbidden, discord.HTTPException):
                    pass
        except Exception:
            logger.exception("Unhandled AutoMod error in guild %s", message.guild.id)

    @automod.command(name="help", description="Show the AutoMod command map")
    @is_mod()
    async def automod_help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="AutoMod commands",
            description="All configuration responses are private to the moderator.",
            color=Config.COLOR_INFO,
        )
        embed.add_field(
            name="Start and inspect",
            value=(
                "`/automod setup` — apply a complete preset\n"
                "`/automod status` — inspect the live configuration\n"
                "`/automod enable` / `disable` — master switch\n"
                "`/automod test` — safely test sample text"
            ),
            inline=False,
        )
        embed.add_field(
            name="Tune behavior",
            value=(
                "`/automod rule` — enable one rule\n"
                "`/automod thresholds` — spam, duplicate, caps and mention limits\n"
                "`/automod actions` — regular/security actions and timeout duration\n"
                "`/automod link-mode` — dangerous-only or allowlist mode"
            ),
            inline=False,
        )
        embed.add_field(
            name="Lists and routing",
            value=(
                "`/automod words`, `/automod domains`, `/automod invites`\n"
                "`/automod bypass-role`, `/automod bypass-channel`\n"
                "`/automod logs`, `/automod recent`, `/automod stats`"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @automod.command(name="status", description="Show the active rules, actions and routing")
    @is_mod()
    async def automod_status(self, interaction: discord.Interaction) -> None:
        settings = await self._get_settings(interaction.guild_id)
        await interaction.response.send_message(
            embed=self._status_embed(settings, interaction.guild),
            ephemeral=True,
        )

    @automod.command(name="setup", description="Apply a complete, usable AutoMod preset")
    @app_commands.describe(preset="Protection level", log_channel="Where AutoMod actions should be logged")
    @is_admin()
    async def automod_setup(
        self,
        interaction: discord.Interaction,
        preset: Literal["relaxed", "standard", "strict"] = "standard",
        log_channel: Optional[discord.TextChannel] = None,
    ) -> None:
        def edit(settings: dict[str, Any]) -> None:
            settings.update(copy.deepcopy(PRESETS[preset]))
            if log_channel is not None:
                settings["automod_log_channel"] = log_channel.id

        settings = await self._edit_settings(interaction.guild_id, edit)
        embed = self._status_embed(settings, interaction.guild)
        embed.title = f"AutoMod setup: {preset.title()}"
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @automod.command(name="enable", description="Enable AutoMod without changing any rules")
    @is_admin()
    async def automod_enable(self, interaction: discord.Interaction) -> None:
        await self._edit_settings(interaction.guild_id, lambda settings: settings.__setitem__("automod_enabled", True))
        await interaction.response.send_message(embed=ModEmbed.success("AutoMod enabled", "Existing rule settings were preserved."), ephemeral=True)

    @automod.command(name="disable", description="Disable AutoMod without deleting its configuration")
    @is_admin()
    async def automod_disable(self, interaction: discord.Interaction) -> None:
        await self._edit_settings(interaction.guild_id, lambda settings: settings.__setitem__("automod_enabled", False))
        await interaction.response.send_message(embed=ModEmbed.success("AutoMod disabled", "Your configuration was preserved."), ephemeral=True)

    @automod.command(name="rule", description="Enable or disable one AutoMod rule")
    @app_commands.describe(rule="Rule to change", enabled="Whether the rule should run")
    @is_admin()
    async def automod_rule(self, interaction: discord.Interaction, rule: RuleName, enabled: bool) -> None:
        key = RULE_SETTING_KEYS[rule]
        await self._edit_settings(interaction.guild_id, lambda settings: settings.__setitem__(key, enabled))
        await interaction.response.send_message(
            embed=ModEmbed.success("Rule updated", f"**{rule.replace('_', ' ').title()}** is now **{'enabled' if enabled else 'disabled'}**."),
            ephemeral=True,
        )

    @automod.command(name="thresholds", description="Set spam, duplicate, caps, mention and account-age limits")
    @app_commands.describe(
        spam_messages="Messages allowed inside the spam window (2-50)",
        spam_seconds="Spam window in seconds (2-60)",
        duplicate_messages="Matching messages allowed (2-20)",
        duplicate_seconds="Duplicate window in seconds (5-300)",
        mentions="Unique user and role mentions allowed (1-50)",
        caps_percent="Uppercase percentage (50-100)",
        caps_characters="Minimum letters before caps checking (5-500)",
        new_account_days="Account age to log (0-365 days)",
    )
    @is_admin()
    async def automod_thresholds(
        self,
        interaction: discord.Interaction,
        spam_messages: Optional[app_commands.Range[int, 2, 50]] = None,
        spam_seconds: Optional[app_commands.Range[int, 2, 60]] = None,
        duplicate_messages: Optional[app_commands.Range[int, 2, 20]] = None,
        duplicate_seconds: Optional[app_commands.Range[int, 5, 300]] = None,
        mentions: Optional[app_commands.Range[int, 1, 50]] = None,
        caps_percent: Optional[app_commands.Range[int, 50, 100]] = None,
        caps_characters: Optional[app_commands.Range[int, 5, 500]] = None,
        new_account_days: Optional[app_commands.Range[int, 0, 365]] = None,
    ) -> None:
        changes = {
            "automod_spam_threshold": spam_messages,
            "automod_spam_window": spam_seconds,
            "automod_duplicate_threshold": duplicate_messages,
            "automod_duplicate_window": duplicate_seconds,
            "automod_max_mentions": mentions,
            "automod_caps_percentage": caps_percent,
            "automod_caps_min_length": caps_characters,
            "automod_newaccount_days": new_account_days,
        }
        supplied = {key: value for key, value in changes.items() if value is not None}
        if not supplied:
            settings = await self._get_settings(interaction.guild_id)
            text = (
                f"Spam: **{settings['automod_spam_threshold']}** / **{settings['automod_spam_window']}s**\n"
                f"Duplicates: **{settings['automod_duplicate_threshold']}** / **{settings['automod_duplicate_window']}s**\n"
                f"Mentions: **{settings['automod_max_mentions']}**\n"
                f"Caps: **{settings['automod_caps_percentage']}%** after **{settings['automod_caps_min_length']}** letters\n"
                f"New account: **{settings['automod_newaccount_days']} days**"
            )
            await interaction.response.send_message(embed=ModEmbed.info("Current thresholds", text), ephemeral=True)
            return
        await self._edit_settings(interaction.guild_id, lambda settings: settings.update(supplied))
        labels = [key.removeprefix("automod_").replace("_", " ").title() for key in supplied]
        await interaction.response.send_message(embed=ModEmbed.success("Thresholds updated", "\n".join(f"• {label}" for label in labels)), ephemeral=True)

    @automod.command(name="actions", description="Set actions for normal and security violations")
    @app_commands.describe(
        regular="Action for words, spam, mentions, invites and caps",
        security="Action for scams and dangerous links",
        timeout_duration="Timeout duration such as 30m, 2h or 1d",
        notify_users="DM users after a successful action",
        public_feedback="Post a short temporary notice in the channel",
    )
    @is_admin()
    async def automod_actions(
        self,
        interaction: discord.Interaction,
        regular: Optional[PolicyAction] = None,
        security: Optional[PolicyAction] = None,
        timeout_duration: Optional[str] = None,
        notify_users: Optional[bool] = None,
        public_feedback: Optional[bool] = None,
    ) -> None:
        duration = _parse_duration(timeout_duration) if timeout_duration is not None else None
        if timeout_duration is not None and duration is None:
            await interaction.response.send_message(
                embed=ModEmbed.error("Invalid duration", "Use values from 1 minute to 28 days, for example `30m`, `2h`, or `1d12h`."),
                ephemeral=True,
            )
            return
        changes: dict[str, Any] = {}
        if regular is not None:
            changes["automod_punishment"] = regular
        if security is not None:
            changes["automod_security_punishment"] = security
        if duration is not None:
            changes["automod_mute_duration"] = duration
        if notify_users is not None:
            changes["automod_notify_users"] = notify_users
        if public_feedback is not None:
            changes["automod_public_feedback"] = public_feedback
        if not changes:
            settings = await self._get_settings(interaction.guild_id)
            text = (
                f"Regular: **{settings.get('automod_punishment', 'warn')}**\n"
                f"Security: **{settings.get('automod_security_punishment', 'timeout')}**\n"
                f"Timeout: **{_format_duration(settings.get('automod_mute_duration', 3600))}**\n"
                f"DM users: **{settings.get('automod_notify_users', True)}**\n"
                f"Public feedback: **{settings.get('automod_public_feedback', False)}**"
            )
            await interaction.response.send_message(embed=ModEmbed.info("Current actions", text), ephemeral=True)
            return
        await self._edit_settings(interaction.guild_id, lambda settings: settings.update(changes))
        await interaction.response.send_message(embed=ModEmbed.success("Actions updated", "The new policy is active."), ephemeral=True)

    @automod.command(name="link-mode", description="Choose dangerous-link detection or a strict domain allowlist")
    @app_commands.describe(mode="Dangerous blocks known risky links; allowlist blocks every unlisted domain")
    @is_admin()
    async def automod_link_mode(
        self,
        interaction: discord.Interaction,
        mode: Literal["dangerous", "allowlist"],
    ) -> None:
        await self._edit_settings(interaction.guild_id, lambda settings: settings.__setitem__("automod_links_mode", mode))
        await interaction.response.send_message(
            embed=ModEmbed.success("Link mode updated", f"Link filtering now uses **{mode}** mode."),
            ephemeral=True,
        )

    async def _edit_string_list(
        self,
        interaction: discord.Interaction,
        *,
        key: str,
        operation: ListOperation,
        value: Optional[str],
        label: str,
        normalizer: Callable[[str], str],
        maximum: int,
        clear_confirmed: bool,
    ) -> None:
        if operation in {"add", "remove"} and not value:
            await interaction.response.send_message(embed=ModEmbed.error("Missing value", f"Provide the {label.lower()} to {operation}."), ephemeral=True)
            return
        if operation == "clear" and not clear_confirmed:
            await interaction.response.send_message(embed=ModEmbed.warning("Confirmation required", "Run the command again with `confirm:True`."), ephemeral=True)
            return
        normalized = normalizer(value or "")
        if value and not normalized:
            await interaction.response.send_message(embed=ModEmbed.error("Invalid value", f"That {label.lower()} is not valid."), ephemeral=True)
            return
        settings = await self._get_settings(interaction.guild_id, fresh=True)
        current = list(dict.fromkeys(str(item).casefold() for item in settings.get(key, []) if str(item).strip()))
        if operation == "list":
            shown = current[:40]
            body = "\n".join(f"• `{_truncate(item, 80)}`" for item in shown) or "`None configured`"
            if len(current) > len(shown):
                body += f"\n…and {len(current) - len(shown)} more."
            await interaction.response.send_message(embed=ModEmbed.info(f"{label} list", body), ephemeral=True)
            return
        if operation == "add":
            if normalized in current:
                await interaction.response.send_message(embed=ModEmbed.warning("No change", f"That {label.lower()} is already listed."), ephemeral=True)
                return
            if len(current) >= maximum:
                await interaction.response.send_message(embed=ModEmbed.error("List full", f"The limit is {maximum} entries."), ephemeral=True)
                return
            current.append(normalized)
        elif operation == "remove":
            if normalized not in current:
                await interaction.response.send_message(embed=ModEmbed.warning("No change", f"That {label.lower()} is not listed."), ephemeral=True)
                return
            current.remove(normalized)
        else:
            current.clear()
        await self._edit_settings(interaction.guild_id, lambda editable: editable.__setitem__(key, current))
        await interaction.response.send_message(embed=ModEmbed.success(f"{label} list updated", f"Entries: **{len(current)}**"), ephemeral=True)

    @automod.command(name="words", description="Add, remove, list or clear blocked words and phrases")
    @is_admin()
    async def automod_words(
        self,
        interaction: discord.Interaction,
        operation: ListOperation,
        phrase: Optional[app_commands.Range[str, 2, 80]] = None,
        confirm: bool = False,
    ) -> None:
        await self._edit_string_list(
            interaction,
            key="automod_badwords",
            operation=operation,
            value=phrase,
            label="Blocked phrase",
            normalizer=lambda value: re.sub(r"\s+", " ", value.strip().casefold()),
            maximum=500,
            clear_confirmed=confirm,
        )

    @automod.command(name="domains", description="Manage domains allowed by strict link mode")
    @is_admin()
    async def automod_domains(
        self,
        interaction: discord.Interaction,
        operation: ListOperation,
        domain: Optional[app_commands.Range[str, 3, 253]] = None,
        confirm: bool = False,
    ) -> None:
        await self._edit_string_list(
            interaction,
            key="automod_whitelisted_domains",
            operation=operation,
            value=domain,
            label="Allowed domain",
            normalizer=normalize_domain,
            maximum=500,
            clear_confirmed=confirm,
        )

    @automod.command(name="invites", description="Manage Discord invite codes that AutoMod allows")
    @is_admin()
    async def automod_invites(
        self,
        interaction: discord.Interaction,
        operation: ListOperation,
        invite: Optional[app_commands.Range[str, 2, 100]] = None,
        confirm: bool = False,
    ) -> None:
        def invite_code(value: str) -> str:
            return value.strip().rstrip("/").rsplit("/", 1)[-1].casefold()

        await self._edit_string_list(
            interaction,
            key="automod_allowed_invites",
            operation=operation,
            value=invite,
            label="Allowed invite",
            normalizer=invite_code,
            maximum=250,
            clear_confirmed=confirm,
        )

    async def _edit_bypass(
        self,
        interaction: discord.Interaction,
        operation: BypassOperation,
        target: Optional[discord.abc.Snowflake],
        *,
        key: str,
        label: str,
    ) -> None:
        settings = await self._get_settings(interaction.guild_id, fresh=True)
        current = []
        for value in settings.get(key, []) or []:
            try:
                current.append(int(value))
            except (TypeError, ValueError):
                continue
        current = list(dict.fromkeys(current))
        if operation == "list":
            mention = "<@&{}>" if key.endswith("roles") else "<#{}>"
            body = "\n".join(f"• {mention.format(item)}" for item in current) or "`None configured`"
            await interaction.response.send_message(embed=ModEmbed.info(f"Bypass {label}s", body), ephemeral=True)
            return
        if target is None:
            await interaction.response.send_message(embed=ModEmbed.error("Missing target", f"Choose a {label} to {operation}."), ephemeral=True)
            return
        if operation == "add" and target.id not in current:
            current.append(target.id)
        elif operation == "remove" and target.id in current:
            current.remove(target.id)
        else:
            await interaction.response.send_message(embed=ModEmbed.warning("No change", f"That {label} is {'already bypassed' if operation == 'add' else 'not bypassed'}."), ephemeral=True)
            return
        await self._edit_settings(interaction.guild_id, lambda editable: editable.__setitem__(key, current))
        await interaction.response.send_message(embed=ModEmbed.success("Bypass updated", f"{target.mention} was {operation}ed."), ephemeral=True)

    @automod.command(name="bypass-role", description="Add, remove or list roles ignored by AutoMod")
    @is_admin()
    async def automod_bypass_role(
        self,
        interaction: discord.Interaction,
        operation: BypassOperation,
        role: Optional[discord.Role] = None,
    ) -> None:
        await self._edit_bypass(interaction, operation, role, key="automod_bypass_roles", label="role")

    @automod.command(name="bypass-channel", description="Add, remove or list channels ignored by AutoMod")
    @is_admin()
    async def automod_bypass_channel(
        self,
        interaction: discord.Interaction,
        operation: BypassOperation,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        await self._edit_bypass(interaction, operation, channel, key="automod_bypass_channels", label="channel")

    @automod.command(name="logs", description="Set, disable or inspect the AutoMod log channel")
    @is_admin()
    async def automod_logs(
        self,
        interaction: discord.Interaction,
        operation: Literal["set", "disable", "status"],
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        if operation == "set" and channel is None:
            await interaction.response.send_message(embed=ModEmbed.error("Missing channel", "Choose a channel when using `set`."), ephemeral=True)
            return
        if operation == "status":
            settings = await self._get_settings(interaction.guild_id)
            existing = interaction.guild.get_channel(settings.get("automod_log_channel")) if settings.get("automod_log_channel") else None
            await interaction.response.send_message(embed=ModEmbed.info("AutoMod logs", existing.mention if existing else "`Disabled`"), ephemeral=True)
            return
        value = channel.id if operation == "set" else None
        await self._edit_settings(interaction.guild_id, lambda settings: settings.__setitem__("automod_log_channel", value))
        text = channel.mention if channel else "Logging disabled"
        await interaction.response.send_message(embed=ModEmbed.success("Log routing updated", text), ephemeral=True)

    @automod.command(name="test", description="Test sample text without deleting it or punishing anyone")
    @is_admin()
    async def automod_test(self, interaction: discord.Interaction, content: app_commands.Range[str, 1, 1500]) -> None:
        await interaction.response.defer(ephemeral=True)

        class TestMessage:
            def __init__(self) -> None:
                self.content = content
                self.author = interaction.user
                self.guild = interaction.guild
                self.channel = interaction.channel
                self.created_at = datetime.now(timezone.utc)
                self.mentions = list({match.group(1) for match in re.finditer(r"<@(\d+)>", content)})
                self.role_mentions = list({match.group(1) for match in re.finditer(r"<@&(\d+)>", content)})

        settings = await self._get_settings(interaction.guild_id)
        test_settings = dict(settings)
        test_settings["automod_newaccount_enabled"] = False
        match = await self.engine.evaluate(TestMessage(), test_settings, dry_run=True)
        if match is None:
            embed = ModEmbed.success("No violation", "The sample passed every enabled content rule.")
        else:
            action = self.engine.resolve_action(match, settings)
            embed = discord.Embed(title="Violation detected", color=Config.COLOR_WARNING)
            embed.add_field(name="Rule", value=match.rule.replace("_", " ").title(), inline=True)
            embed.add_field(name="Severity", value=match.severity.name.title(), inline=True)
            embed.add_field(name="Action", value=action.value.title(), inline=True)
            embed.add_field(name="Reason", value=match.reason, inline=False)
            if match.evidence:
                embed.add_field(name="Matched", value=", ".join(f"||{item}||" for item in match.evidence), inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @automod.command(name="stats", description="Show runtime AutoMod totals since the last bot restart")
    @is_mod()
    async def automod_stats(self, interaction: discord.Interaction) -> None:
        stats = self.engine.stats
        hits = self.engine.rule_hits
        hit_text = "\n".join(f"{name.replace('_', ' ').title()}: **{count:,}**" for name, count in hits.most_common()) or "`No violations yet`"
        embed = discord.Embed(title="AutoMod runtime stats", color=Config.COLOR_INFO)
        embed.add_field(
            name="Totals",
            value=(
                f"Messages checked: **{stats['messages_checked']:,}**\n"
                f"Violations: **{stats['violations_detected']:,}**\n"
                f"Actions succeeded: **{stats['actions_succeeded']:,}**\n"
                f"Actions failed: **{stats['actions_failed']:,}**"
            ),
            inline=True,
        )
        embed.add_field(name="Rule hits", value=_truncate(hit_text, 1024), inline=True)
        embed.set_footer(text="Runtime counters reset when the bot restarts")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @automod.command(name="recent", description="Show recent AutoMod violations from this bot session")
    @is_mod()
    async def automod_recent(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
    ) -> None:
        recent = self.engine.recent_for(interaction.guild_id, user.id if user else None)[:10]
        if not recent:
            await interaction.response.send_message(embed=ModEmbed.info("No recent violations", "No matching runtime records were found."), ephemeral=True)
            return
        lines = []
        for item in recent:
            timestamp = int(item.occurred_at)
            lines.append(
                f"<t:{timestamp}:R> <@{item.user_id}> in <#{item.channel_id}> — "
                f"**{item.rule.replace('_', ' ').title()}**: {_truncate(item.reason, 100)}"
            )
        embed = discord.Embed(title="Recent AutoMod violations", description="\n".join(lines), color=Config.COLOR_INFO)
        embed.set_footer(text="Runtime history is bounded and resets when the bot restarts")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @automod.command(name="reset", description="Restore all AutoMod settings to safe defaults")
    @is_admin()
    async def automod_reset(self, interaction: discord.Interaction, confirm: bool = False) -> None:
        if not confirm:
            await interaction.response.send_message(
                embed=ModEmbed.warning("Confirmation required", "Run `/automod reset confirm:True` to restore AutoMod defaults."),
                ephemeral=True,
            )
            return

        def reset(settings: dict[str, Any]) -> None:
            for key in list(settings):
                if key.startswith("automod_"):
                    settings.pop(key, None)
            settings.update(copy.deepcopy(AUTOMOD_SETTINGS))

        settings = await self._edit_settings(interaction.guild_id, reset)
        await interaction.response.send_message(embed=self._status_embed(settings, interaction.guild), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoMod(bot))
