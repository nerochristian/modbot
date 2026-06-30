"""Conversational AutoMod setup and natural-language change flow."""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Optional

import discord

from cogs.automod_config import AUTOMOD_SETTINGS
from cogs.automod_engine import normalize_domain
from config import Config
from utils.embeds import ModEmbed
from utils.status_emojis import get_status_emoji_for_guild


log = logging.getLogger("AutoMod.Setup")

_ACTIVE_SETUPS: set[int] = set()
_ACTIVE_LOCK = asyncio.Lock()


def _deepseek_web_primary_timeout() -> float:
    raw = os.getenv("DEEPSEEK_WEB_PRIMARY_TIMEOUT", "25").strip()
    try:
        timeout = float(raw)
    except ValueError:
        timeout = 25.0
    return min(90.0, max(0.1, timeout))


@dataclass(frozen=True)
class SetupQuestion:
    key: str
    prompt: str
    options: tuple[str, ...] = ()
    helper: str = ""

    @property
    def is_closed(self) -> bool:
        return bool(self.options)


@dataclass(frozen=True)
class SetupProfile:
    name: str
    description: str
    focus: str = ""

_BOOL_KEYS = {
    "automod_enabled",
    "automod_notify_users",
    "automod_public_feedback",
    "automod_delete_violations",
    "automod_bypass_staff",
    "automod_badwords_enabled",
    "automod_spam_enabled",
    "automod_mentions_enabled",
    "automod_caps_enabled",
    "automod_links_enabled",
    "automod_invites_enabled",
    "automod_scam_protection",
    "automod_newaccount_enabled",
    "automod_ai_enabled",
    "warn_thresholds_enabled",
}
_INT_RANGES = {
    "automod_log_channel": (0, 2**63 - 1),
    "automod_violation_cooldown": (0, 300),
    "automod_mute_duration": (60, 28 * 86400),
    "automod_tempban_duration": (60, 28 * 86400),
    "automod_ban_delete_days": (0, 7),
    "automod_spam_threshold": (2, 50),
    "automod_spam_window": (2, 60),
    "automod_duplicate_threshold": (2, 20),
    "automod_duplicate_window": (5, 300),
    "automod_caps_percentage": (50, 100),
    "automod_caps_min_length": (5, 500),
    "automod_max_mentions": (1, 50),
    "automod_newaccount_days": (0, 365),
    "automod_ai_min_severity": (1, 10),
    "warn_threshold_mute": (1, 20),
    "warn_threshold_kick": (1, 20),
    "warn_threshold_ban": (1, 20),
    "warn_mute_duration": (60, 28 * 86400),
}
_OPTION_KEYS = {
    "automod_links_mode": {"dangerous", "allowlist"},
    "automod_punishment": {"log", "warn", "timeout", "kick", "ban", "quarantine"},
    "automod_security_punishment": {"log", "warn", "timeout", "kick", "ban", "quarantine"},
}
_STRING_LIST_KEYS = {
    "automod_badwords": (2, 80, 250, lambda value: str(value).strip().casefold()),
    "automod_links_whitelist": (3, 253, 500, normalize_domain),
    "automod_whitelisted_domains": (3, 253, 500, normalize_domain),
    "automod_allowed_invites": (2, 100, 250, lambda value: str(value).strip().split("/")[-1].casefold()),
}
_INT_LIST_KEYS = {
    "automod_bypass_roles",
    "automod_bypass_channels",
    "automod_temp_bypass",
}
_NULLABLE_INT_KEYS = {
    "automod_log_channel",
    "automod_bypass_role_id",
    "automod_quarantine_role_id",
}
_ALLOWED_KEYS = (
    set(AUTOMOD_SETTINGS)
    | _BOOL_KEYS
    | set(_INT_RANGES)
    | set(_OPTION_KEYS)
    | set(_STRING_LIST_KEYS)
    | _INT_LIST_KEYS
    | _NULLABLE_INT_KEYS
)


async def _status_icon(guild: Optional[discord.Guild], kind: str) -> str:
    return await get_status_emoji_for_guild(guild, kind=kind)


async def _setup_embed(
    guild: Optional[discord.Guild],
    *,
    kind: str,
    title: str,
    description: str,
    color: Optional[int] = None,
) -> discord.Embed:
    icon = await _status_icon(guild, kind)
    return discord.Embed(
        title=f"{icon} {title}",
        description=description,
        color=color if color is not None else Config.COLOR_INFO,
    )


async def _has_admin_access(interaction: discord.Interaction) -> bool:
    user = interaction.user
    if user.id in getattr(interaction.client, "owner_ids", set()):
        return True
    if interaction.guild is not None and user.id == interaction.guild.owner_id:
        return True
    permissions = getattr(user, "guild_permissions", None)
    if permissions is not None and getattr(permissions, "administrator", False):
        return True

    try:
        settings = await asyncio.wait_for(interaction.client.db.get_settings(interaction.guild_id), timeout=1.5)
    except Exception:
        log.exception("AutoMod permission lookup failed for guild %s", interaction.guild_id)
        return False

    role_ids = {role.id for role in getattr(user, "roles", [])}
    manager_role = settings.get("manager_role")
    admin_roles = settings.get("admin_roles", []) or []
    return bool(manager_role in role_ids or any(role_id in role_ids for role_id in admin_roles))


def _permission_denied_embed() -> discord.Embed:
    return ModEmbed.error(
        "Permission Denied",
        "You need Administrator, Manager, or a configured admin role to change AutoMod.",
    )


class SetupQuestionView(discord.ui.View):
    def __init__(self, owner_id: int, options: Iterable[str], icons: Mapping[str, str]) -> None:
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.value: Optional[str] = None
        option_list = list(options)
        for index, option in enumerate(option_list):
            button = discord.ui.Button(
                label=option,
                emoji=icons.get("success") if index == 0 else None,
                style=discord.ButtonStyle.primary if index == 0 else discord.ButtonStyle.secondary,
                row=index // 5,
                custom_id=f"automod_setup_answer:{index}",
            )
            button.callback = self._make_callback(option)
            self.add_item(button)

    def _make_callback(self, option: str) -> Callable[[discord.Interaction], Any]:
        async def callback(interaction: discord.Interaction) -> None:
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message("This setup belongs to another admin.", ephemeral=True)
                return
            self.value = option
            await interaction.response.defer()
            self.stop()

        return callback


class ProfilePaginatorView(discord.ui.View):
    def __init__(self, owner_id: int, profiles: list[SetupProfile], icons: Mapping[str, str]) -> None:
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.profiles = profiles
        self.icons = icons
        self.current = 0
        self.selected_profile: Optional[SetupProfile] = None
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        self.previous_button.disabled = self.current <= 0
        self.next_button.disabled = self.current >= len(self.profiles) - 1

    def build_embed(self, guild: Optional[discord.Guild]) -> discord.Embed:
        profile = self.profiles[self.current]
        icon = self.icons.get("info", "")
        embed = discord.Embed(
            title=f"{icon} Profile {self.current + 1}/{len(self.profiles)}: {profile.name}",
            description=profile.description,
            color=Config.COLOR_INFO,
        )
        if profile.focus:
            embed.add_field(name="Focus", value=profile.focus[:1024], inline=False)
        embed.set_footer(text="Use the arrows to compare profiles, then select one.")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("This setup belongs to another admin.", ephemeral=True)
        return False

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary, row=0)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current = max(0, self.current - 1)
        self._sync_buttons()
        await interaction.response.defer()
        if interaction.message:
            await interaction.message.edit(embed=self.build_embed(interaction.guild), view=self)

    @discord.ui.button(label="Select this profile", style=discord.ButtonStyle.primary, row=0)
    async def select_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.selected_profile = self.profiles[self.current]
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary, row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current = min(len(self.profiles) - 1, self.current + 1)
        self._sync_buttons()
        await interaction.response.defer()
        if interaction.message:
            await interaction.message.edit(embed=self.build_embed(interaction.guild), view=self)


def _format_duration(seconds: Any) -> str:
    value = _coerce_int(seconds) or 0
    if value <= 0:
        return "off"
    if value % 86400 == 0:
        amount = value // 86400
        unit = "day" if amount == 1 else "days"
        return f"{amount} {unit}"
    if value % 3600 == 0:
        amount = value // 3600
        unit = "hour" if amount == 1 else "hours"
        return f"{amount} {unit}"
    if value % 60 == 0:
        amount = value // 60
        unit = "minute" if amount == 1 else "minutes"
        return f"{amount} {unit}"
    return f"{value}s"


def _preview_values(values: Any, *, empty: str = "None", limit: int = 8) -> str:
    if not isinstance(values, list) or not values:
        return empty
    shown = [str(value) for value in values[:limit]]
    extra = len(values) - len(shown)
    preview = ", ".join(shown)
    if extra > 0:
        preview = f"{preview}, +{extra} more"
    return preview[:900]


def _review_description(settings: Mapping[str, Any], summary: str) -> str:
    badwords = settings.get("automod_badwords", [])
    link_mode = str(settings.get("automod_links_mode", "dangerous")).title()
    return (
        f"{summary[:500]}\n\n"
        "Review the generated setup before I save it. Use the buttons below to edit the panels that need changes.\n\n"
        f"**Blocked Words**\n"
        f"Status: **{'On' if settings.get('automod_badwords_enabled', False) else 'Off'}**\n"
        f"Words: `{_preview_values(badwords)}`\n\n"
        f"**Links**\n"
        f"Status: **{'On' if settings.get('automod_links_enabled', False) else 'Off'}**\n"
        f"Mode: **{link_mode}**\n"
        f"Allowed links: `{_preview_values(settings.get('automod_links_whitelist', []))}`\n"
        f"Safe domains: `{_preview_values(settings.get('automod_whitelisted_domains', []))}`\n\n"
        f"**Invites and Security**\n"
        f"Invites: **{'On' if settings.get('automod_invites_enabled', False) else 'Off'}**\n"
        f"Allowed invite codes: `{_preview_values(settings.get('automod_allowed_invites', []))}`\n"
        f"Scam protection: **{'On' if settings.get('automod_scam_protection', False) else 'Off'}**\n\n"
        f"**Limits and Actions**\n"
        f"Spam: **{settings.get('automod_spam_threshold', 5)} messages / {settings.get('automod_spam_window', 5)}s**\n"
        f"Mentions: **{settings.get('automod_max_mentions', 5)} max**\n"
        f"Regular action: **{str(settings.get('automod_punishment', 'warn')).title()}**\n"
        f"Security action: **{str(settings.get('automod_security_punishment', 'timeout')).title()}**"
    )


def _modal_update_from_fields(fields: Mapping[str, str]) -> dict[str, Any]:
    return validate_automod_update({"settings": dict(fields)}, require_changes=False)


class SetupReviewModal(discord.ui.Modal):
    def __init__(
        self,
        view: "SetupReviewView",
        title: str,
        fields: list[tuple[str, str, str, discord.TextStyle]],
    ) -> None:
        super().__init__(title=title, timeout=300)
        self.review_view = view
        self.field_keys: list[str] = []
        for key, label, value, style in fields:
            text_input = discord.ui.TextInput(
                label=label,
                default=str(value or "")[:4000],
                style=style,
                required=False,
                max_length=4000,
            )
            self.field_keys.append(key)
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        values = {
            key: str(item.value)
            for key, item in zip(self.field_keys, self.children)
            if isinstance(item, discord.ui.TextInput)
        }
        update = _modal_update_from_fields(values)
        self.review_view.settings.update(update)
        await interaction.response.defer(ephemeral=True)
        await self.review_view.refresh_message(interaction.guild)


class SetupReviewView(discord.ui.View):
    def __init__(self, owner_id: int, settings: Mapping[str, Any], icons: Mapping[str, str], summary: str) -> None:
        super().__init__(timeout=600)
        self.owner_id = owner_id
        self.settings = copy.deepcopy(dict(settings))
        self.icons = icons
        self.summary = summary
        self.confirmed = False
        self.cancelled = False
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("This setup belongs to another admin.", ephemeral=True)
        return False

    async def build_embed(self, guild: Optional[discord.Guild]) -> discord.Embed:
        return await _setup_embed(
            guild,
            kind="info",
            title="Review AutoMod Setup",
            description=_review_description(self.settings, self.summary),
        )

    async def refresh_message(self, guild: Optional[discord.Guild]) -> None:
        if self.message is not None:
            await self.message.edit(embed=await self.build_embed(guild), view=self)

    def _csv(self, key: str) -> str:
        value = self.settings.get(key, [])
        return "\n".join(str(item) for item in value) if isinstance(value, list) else ""

    @discord.ui.button(label="Blocked Words", style=discord.ButtonStyle.secondary, row=0)
    async def blocked_words_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(
            SetupReviewModal(
                self,
                "Blocked Words",
                [
                    ("automod_badwords_enabled", "Bad words on/off", "on" if self.settings.get("automod_badwords_enabled") else "off", discord.TextStyle.short),
                    ("automod_badwords", "Blocked words, one per line", self._csv("automod_badwords"), discord.TextStyle.paragraph),
                ],
            )
        )

    @discord.ui.button(label="Links", style=discord.ButtonStyle.secondary, row=0)
    async def links_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(
            SetupReviewModal(
                self,
                "Link Rules",
                [
                    ("automod_links_enabled", "Links on/off", "on" if self.settings.get("automod_links_enabled") else "off", discord.TextStyle.short),
                    ("automod_links_mode", "Mode: dangerous or allowlist", self.settings.get("automod_links_mode", "dangerous"), discord.TextStyle.short),
                    ("automod_links_whitelist", "Allowed links, one domain per line", self._csv("automod_links_whitelist"), discord.TextStyle.paragraph),
                    ("automod_whitelisted_domains", "Safe domains, one per line", self._csv("automod_whitelisted_domains"), discord.TextStyle.paragraph),
                ],
            )
        )

    @discord.ui.button(label="Invites", style=discord.ButtonStyle.secondary, row=0)
    async def invites_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(
            SetupReviewModal(
                self,
                "Invite Rules",
                [
                    ("automod_invites_enabled", "Invites on/off", "on" if self.settings.get("automod_invites_enabled") else "off", discord.TextStyle.short),
                    ("automod_allowed_invites", "Allowed invite codes, one per line", self._csv("automod_allowed_invites"), discord.TextStyle.paragraph),
                    ("automod_scam_protection", "Scam protection on/off", "on" if self.settings.get("automod_scam_protection") else "off", discord.TextStyle.short),
                ],
            )
        )

    @discord.ui.button(label="Limits", style=discord.ButtonStyle.secondary, row=1)
    async def limits_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(
            SetupReviewModal(
                self,
                "Limits",
                [
                    ("automod_spam_threshold", "Spam messages", str(self.settings.get("automod_spam_threshold", 5)), discord.TextStyle.short),
                    ("automod_spam_window", "Spam window seconds", str(self.settings.get("automod_spam_window", 5)), discord.TextStyle.short),
                    ("automod_max_mentions", "Max mentions", str(self.settings.get("automod_max_mentions", 5)), discord.TextStyle.short),
                    ("automod_newaccount_days", "New account days", str(self.settings.get("automod_newaccount_days", 7)), discord.TextStyle.short),
                ],
            )
        )

    @discord.ui.button(label="Actions", style=discord.ButtonStyle.secondary, row=1)
    async def actions_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(
            SetupReviewModal(
                self,
                "Actions",
                [
                    ("automod_punishment", "Regular action", self.settings.get("automod_punishment", "warn"), discord.TextStyle.short),
                    ("automod_security_punishment", "Security action", self.settings.get("automod_security_punishment", "timeout"), discord.TextStyle.short),
                    ("automod_mute_duration", "Timeout seconds", str(self.settings.get("automod_mute_duration", 3600)), discord.TextStyle.short),
                    ("automod_violation_cooldown", "Violation cooldown seconds", str(self.settings.get("automod_violation_cooldown", 10)), discord.TextStyle.short),
                ],
            )
        )

    @discord.ui.button(label="Save Setup", style=discord.ButtonStyle.success, row=2)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.confirmed = True
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.defer()
        if interaction.message:
            await interaction.message.edit(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=2)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.cancelled = True
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.defer()
        if interaction.message:
            await interaction.message.edit(view=self)
        self.stop()


class AutoModChangeModal(discord.ui.Modal, title="Change AutoMod"):
    def __init__(self, cog: Any) -> None:
        super().__init__(timeout=300)
        self.cog = cog
        self.request = discord.ui.TextInput(
            label="What would you like to change?",
            placeholder="Example: make spam stricter and timeout spammers for 10 minutes",
            style=discord.TextStyle.paragraph,
            min_length=3,
            max_length=1000,
        )
        self.add_item(self.request)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await _apply_automod_change(self.cog, interaction, str(self.request))


def _chunk_code(title: str, body: str) -> str:
    content = body if len(body) <= 1800 else f"{body[:1800]}... (truncated)"
    return f"**{title}**\n```text\n{content}\n```"


def _extract_json_object(raw: str) -> dict[str, Any]:
    content = (raw or "").strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if match is None:
            raise ValueError("DeepSeek did not return a JSON object.") from None
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("DeepSeek returned JSON, but it was not an object.")
    return parsed


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "yes", "y", "on", "enabled", "enable", "1"}:
            return True
        if normalized in {"false", "no", "n", "off", "disabled", "disable", "0"}:
            return False
    return None


def _coerce_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        match = re.fullmatch(r"\s*(?:<#|<@&)?(\d+)>?\s*", value)
        if match:
            return int(match.group(1))
    return None


def _coerce_string_list(
    value: Any,
    *,
    minimum_length: int,
    maximum_length: int,
    maximum_items: int,
    normalizer: Callable[[Any], str],
) -> Optional[list[str]]:
    if isinstance(value, str):
        raw_values = re.split(r"[\n,]+", value)
    elif isinstance(value, list):
        raw_values = value
    else:
        return None
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        item = normalizer(raw)
        if not item or item in {"none", "n/a", "na", "nothing"}:
            continue
        if not minimum_length <= len(item) <= maximum_length:
            continue
        if item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
        if len(cleaned) >= maximum_items:
            break
    return cleaned


def _coerce_int_list(value: Any) -> Optional[list[int]]:
    if not isinstance(value, list):
        return None
    result: list[int] = []
    seen: set[int] = set()
    for item in value:
        parsed = _coerce_int(item)
        if parsed is None or parsed < 0 or parsed in seen:
            continue
        seen.add(parsed)
        result.append(parsed)
        if len(result) >= 250:
            break
    return result


def validate_automod_update(candidate: Mapping[str, Any], *, require_changes: bool = True) -> dict[str, Any]:
    """Return a bounded AutoMod settings update from model output."""
    if not isinstance(candidate, Mapping):
        raise ValueError("AutoMod update must be a JSON object.")
    raw_settings = candidate.get("settings", candidate)
    if not isinstance(raw_settings, Mapping):
        raise ValueError("AutoMod update must contain a settings object.")

    update: dict[str, Any] = {}
    for key, value in raw_settings.items():
        if key not in _ALLOWED_KEYS:
            continue
        if key in _BOOL_KEYS:
            parsed_bool = _coerce_bool(value)
            if parsed_bool is not None:
                update[key] = parsed_bool
            continue
        if key in _NULLABLE_INT_KEYS and (
            value is None or (isinstance(value, str) and value.strip().casefold() in {"", "none", "null"})
        ):
            update[key] = None
            continue
        if key in _INT_RANGES:
            parsed_int = _coerce_int(value)
            if parsed_int is None:
                continue
            low, high = _INT_RANGES[key]
            if low <= parsed_int <= high:
                update[key] = parsed_int
            continue
        if key in _OPTION_KEYS:
            parsed_option = str(value or "").strip().casefold().replace("mute", "timeout")
            if parsed_option in _OPTION_KEYS[key]:
                update[key] = parsed_option
            continue
        if key in _STRING_LIST_KEYS:
            minimum, maximum, limit, normalizer = _STRING_LIST_KEYS[key]
            parsed_list = _coerce_string_list(
                value,
                minimum_length=minimum,
                maximum_length=maximum,
                maximum_items=limit,
                normalizer=normalizer,
            )
            if parsed_list is not None:
                update[key] = parsed_list
            continue
        if key in _INT_LIST_KEYS:
            parsed_ids = _coerce_int_list(value)
            if parsed_ids is not None:
                update[key] = parsed_ids

    if require_changes and not update:
        raise ValueError("DeepSeek did not return any valid AutoMod settings.")
    return update


async def call_deepseek_json(
    cog: Any,
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int = 1400,
    session_key: Optional[str] = None,
    session_name: Optional[str] = None,
) -> dict[str, Any]:
    ai_cog = cog.bot.get_cog("AIModeration")
    ai_client = getattr(ai_cog, "ai", None) if ai_cog else None
    web_client = getattr(ai_client, "_deepseek_web", None) if ai_client else None
    prompt = (
        "You are a strict JSON API. Follow the system instructions and return valid JSON only.\n\n"
        f"--- SYSTEM INSTRUCTIONS ---\n{system_prompt}\n\n"
        f"--- USER REQUEST ---\n{user_prompt}"
    )
    failures: list[str] = []

    if web_client and getattr(web_client, "enabled", False):
        try:
            response = await asyncio.wait_for(
                web_client.chat(
                    prompt,
                    search=False,
                    deepthink=False,
                    long_answer=False,
                    session_key=session_key,
                    session_name=session_name,
                ),
                timeout=_deepseek_web_primary_timeout(),
            )
            return _extract_json_object(response)
        except Exception as exc:
            failures.append(f"DeepSeek Web: {type(exc).__name__}: {str(exc)[:200]}")
            log.warning("AutoMod setup DeepSeek Web call failed; falling back to DigitalOcean.", exc_info=True)
    else:
        failures.append("DeepSeek Web: disabled")

    digitalocean_call = getattr(ai_client, "_call_digitalocean", None) if ai_client else None
    if callable(digitalocean_call):
        try:
            response = await digitalocean_call(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=max_tokens,
                json_mode=True,
            )
            if isinstance(response, str) and response.strip():
                return _extract_json_object(response)
            failures.append("DigitalOcean: empty response")
        except Exception as exc:
            failures.append(f"DigitalOcean: {type(exc).__name__}: {str(exc)[:200]}")
            log.warning("AutoMod setup DigitalOcean fallback failed.", exc_info=True)
    else:
        failures.append("DigitalOcean: unavailable")

    raise RuntimeError("AutoMod AI JSON generation failed. " + " | ".join(failures))


def _clean_text(value: Any, *, limit: int = 900) -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "")).strip()
    return cleaned[:limit]


def _profiles_prompt() -> str:
    return (
        "You design Discord AutoMod setup profiles. Return exactly one JSON object with key `profiles`. "
        "`profiles` must contain exactly 3 objects. Each object must have `name`, `description`, and `focus` strings. "
        "Base all 3 profiles on the admin's stated goal, but improve it into practical moderation setups. "
        "The 3 profiles must be clearly different choices, not copies: one lighter, one balanced, one stricter or more targeted. "
        "Do not return settings. Do not include markdown."
    )


def _profiles_user_prompt(guild: discord.Guild, initial_goal: str) -> str:
    return json.dumps(
        {
            "guild": {"id": guild.id, "name": guild.name, "member_count": guild.member_count},
            "admin_goal": initial_goal,
            "goal": "Create 3 improved AutoMod profile choices for this server.",
        },
        indent=2,
    )


def _questions_prompt() -> str:
    return (
        "You design concise Discord AutoMod setup questions for the selected profile. "
        "Return exactly one JSON object with key `questions`. "
        "`questions` must contain 8 to 10 objects. Each object must have `key`, `question`, `type`, and optional `options` and `helper`. "
        "`type` must be `choice` or `text`. At least 7 questions must be `choice`; at most 2 may be `text`. "
        "Choice questions must have 2 to 5 short options. Questions must be specific to the admin goal and selected profile, not generic boilerplate. "
        "Ask about the actual risks mentioned by the admin, punishments, links/invites, spam, raids/new accounts, and any custom allow/block lists that matter. "
        "Do not ask for raw setting keys. Do not include markdown."
    )


def _questions_user_prompt(guild: discord.Guild, initial_goal: str, profile: SetupProfile) -> str:
    return json.dumps(
        {
            "guild": {"id": guild.id, "name": guild.name, "member_count": guild.member_count},
            "admin_goal": initial_goal,
            "selected_profile": {
                "name": profile.name,
                "description": profile.description,
                "focus": profile.focus,
            },
            "goal": "Create profile-specific setup questions for this AutoMod setup.",
        },
        indent=2,
    )


def _parse_profiles(payload: Mapping[str, Any]) -> list[SetupProfile]:
    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, list):
        raise ValueError("DeepSeek did not return a profiles list.")
    profiles: list[SetupProfile] = []
    seen_names: set[str] = set()
    for raw in raw_profiles:
        if not isinstance(raw, Mapping):
            continue
        name = _clean_text(raw.get("name"), limit=60)
        description = _clean_text(raw.get("description"), limit=900)
        focus = _clean_text(raw.get("focus"), limit=500)
        if not name or not description or name.casefold() in seen_names:
            continue
        seen_names.add(name.casefold())
        profiles.append(SetupProfile(name=name, description=description, focus=focus))
        if len(profiles) == 3:
            break
    if len(profiles) != 3:
        raise ValueError("DeepSeek must return exactly 3 distinct setup profiles.")
    return profiles


def _parse_generated_questions(payload: Mapping[str, Any]) -> list[SetupQuestion]:
    raw_questions = payload.get("questions")
    if not isinstance(raw_questions, list):
        raise ValueError("DeepSeek did not return a questions list.")

    questions: list[SetupQuestion] = []
    text_count = 0
    seen_keys: set[str] = set()
    for index, raw in enumerate(raw_questions, start=1):
        if not isinstance(raw, Mapping):
            continue
        key = re.sub(r"[^a-z0-9_]+", "_", str(raw.get("key") or f"question_{index}").casefold()).strip("_")
        if not key or key in seen_keys:
            key = f"question_{index}"
        question = _clean_text(raw.get("question"), limit=240)
        helper = _clean_text(raw.get("helper"), limit=300)
        raw_type = str(raw.get("type") or "choice").strip().casefold()
        raw_options = raw.get("options")

        options: tuple[str, ...] = ()
        if raw_type == "choice" and isinstance(raw_options, list):
            cleaned_options: list[str] = []
            seen_options: set[str] = set()
            for option in raw_options:
                cleaned = _clean_text(option, limit=80)
                if cleaned and cleaned.casefold() not in seen_options:
                    seen_options.add(cleaned.casefold())
                    cleaned_options.append(cleaned)
                if len(cleaned_options) == 5:
                    break
            if len(cleaned_options) >= 2:
                options = tuple(cleaned_options)
        elif raw_type == "text":
            text_count += 1

        if not question:
            continue
        if raw_type == "text" and text_count <= 2:
            questions.append(SetupQuestion(key=key, prompt=question, helper=helper))
            seen_keys.add(key)
        elif options:
            questions.append(SetupQuestion(key=key, prompt=question, options=options, helper=helper))
            seen_keys.add(key)

        if len(questions) == 10:
            break

    closed_count = sum(1 for question in questions if question.is_closed)
    if not 8 <= len(questions) <= 10 or closed_count < 7:
        raise ValueError("DeepSeek must return 8-10 setup questions with at least 7 closed-ended questions.")
    return questions


async def _generate_profiles(
    cog: Any,
    guild: discord.Guild,
    initial_goal: str,
    *,
    session_key: str,
    session_name: str,
) -> list[SetupProfile]:
    payload = await call_deepseek_json(
        cog,
        _profiles_prompt(),
        _profiles_user_prompt(guild, initial_goal),
        max_tokens=1000,
        session_key=session_key,
        session_name=session_name,
    )
    return _parse_profiles(payload)


async def _generate_questions(
    cog: Any,
    guild: discord.Guild,
    initial_goal: str,
    profile: SetupProfile,
    *,
    session_key: str,
    session_name: str,
) -> list[SetupQuestion]:
    payload = await call_deepseek_json(
        cog,
        _questions_prompt(),
        _questions_user_prompt(guild, initial_goal, profile),
        max_tokens=1400,
        session_key=session_key,
        session_name=session_name,
    )
    return _parse_generated_questions(payload)


def _settings_prompt() -> str:
    return (
        "You configure a Discord bot AutoMod system. Return exactly one JSON object with a "
        "`settings` object and optional `summary` string. Do not include markdown.\n\n"
        "Only use these setting keys:\n"
        f"{', '.join(sorted(_ALLOWED_KEYS))}\n\n"
        "Accepted actions: log, warn, timeout, kick, ban, quarantine. "
        "Accepted link modes: dangerous, allowlist. Durations are seconds. "
        "Set every important automod_* key needed for a full setup. "
        "Do not invent slurs or profanity. If the admin wants common slur filtering, set automod_badwords_enabled true. "
        "Only set automod_badwords when the admin typed exact custom words. "
        "Keep values practical and avoid destructive punishments unless the answers clearly choose them."
    )


def _schema_summary() -> dict[str, Any]:
    return {
        "booleans": sorted(_BOOL_KEYS),
        "integers": _INT_RANGES,
        "choices": {key: sorted(values) for key, values in _OPTION_KEYS.items()},
        "string_lists": sorted(_STRING_LIST_KEYS),
        "nullable_ids": sorted(_NULLABLE_INT_KEYS),
    }


def _setup_user_prompt(
    guild: discord.Guild,
    initial_goal: str,
    selected_profile: SetupProfile,
    answers: list[dict[str, str]],
) -> str:
    return json.dumps(
        {
            "guild": {"id": guild.id, "name": guild.name, "member_count": guild.member_count},
            "schema": _schema_summary(),
            "admin_goal": initial_goal,
            "selected_profile": {
                "name": selected_profile.name,
                "description": selected_profile.description,
                "focus": selected_profile.focus,
            },
            "answers": answers,
            "goal": "Fill out a complete production-safe AutoMod setup from these answers.",
        },
        indent=2,
    )


def _change_user_prompt(current_settings: Mapping[str, Any], request: str) -> str:
    safe_current = {
        key: value
        for key, value in current_settings.items()
        if key in _ALLOWED_KEYS or str(key).startswith("warn_")
    }
    return json.dumps(
        {
            "current_settings": safe_current,
            "schema": _schema_summary(),
            "admin_request": request,
            "goal": "Return only the settings that must change to satisfy the admin request.",
        },
        indent=2,
    )


def _human_setting_lines(settings: Mapping[str, Any]) -> list[str]:
    return [
        f"Enabled: **{'Yes' if settings.get('automod_enabled', True) else 'No'}**",
        f"Bad words: **{'On' if settings.get('automod_badwords_enabled', False) else 'Off'}**",
        f"Spam: **{settings.get('automod_spam_threshold', 5)} messages / {settings.get('automod_spam_window', 5)}s**",
        f"Mentions: **{settings.get('automod_max_mentions', 5)} max**",
        f"Links: **{str(settings.get('automod_links_mode', 'dangerous')).title()}**",
        f"Regular action: **{str(settings.get('automod_punishment', 'warn')).title()}**",
        f"Security action: **{str(settings.get('automod_security_punishment', 'timeout')).title()}**",
    ]


async def _collect_open_answer(cog: Any, channel: discord.TextChannel, user: discord.abc.User) -> Optional[str]:
    def check(message: discord.Message) -> bool:
        return message.author.id == user.id and message.channel.id == channel.id

    try:
        message = await cog.bot.wait_for("message", check=check, timeout=300)
    except asyncio.TimeoutError:
        return None
    return message.content.strip()[:1500]


async def _resolve_icons(guild: discord.Guild) -> dict[str, str]:
    return {
        kind: await _status_icon(guild, kind)
        for kind in ("success", "error", "warning", "info", "loading", "lock")
    }


async def _ask_question(
    cog: Any,
    channel: discord.TextChannel,
    user: discord.abc.User,
    question: SetupQuestion,
    index: int,
    total: int,
    icons: Mapping[str, str],
) -> Optional[str]:
    description = question.prompt
    if question.helper:
        description = f"{description}\n\n{question.helper}"
    embed = await _setup_embed(
        channel.guild,
        kind="info",
        title=f"Question {index}/{total}",
        description=description,
    )
    if question.is_closed:
        view = SetupQuestionView(user.id, question.options, icons)
        prompt_message = await channel.send(embed=embed, view=view)
        await view.wait()
        if view.value is None:
            return None
        completed = await _setup_embed(
            channel.guild,
            kind="success",
            title=f"Question {index}/{total}",
            description=f"{question.prompt}\n\nAnswer: **{view.value}**",
            color=Config.COLOR_SUCCESS,
        )
        await prompt_message.edit(embed=completed, view=None)
        return view.value

    prompt_message = await channel.send(embed=embed)
    answer = await _collect_open_answer(cog, channel, user)
    if not answer:
        return None
    completed = await _setup_embed(
        channel.guild,
        kind="success",
        title=f"Question {index}/{total}",
        description=f"{question.prompt}\n\nAnswer: **{answer[:900]}**",
        color=Config.COLOR_SUCCESS,
    )
    await prompt_message.edit(embed=completed)
    return answer


async def start_setup_wizard(cog: Any, interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None or interaction.guild_id is None:
        await interaction.response.send_message("AutoMod setup can only run inside a server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    if not await _has_admin_access(interaction):
        await interaction.followup.send(embed=_permission_denied_embed(), ephemeral=True)
        return

    async with _ACTIVE_LOCK:
        if guild.id in _ACTIVE_SETUPS:
            await interaction.followup.send("An AutoMod setup is already running in this server.", ephemeral=True)
            return
        _ACTIVE_SETUPS.add(guild.id)

    channel: Optional[discord.TextChannel] = None
    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        if guild.me is not None:
            overwrites[guild.me] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
            )
        channel = await guild.create_text_channel(
            "automod-setup",
            overwrites=overwrites,
            reason=f"AutoMod setup started by {interaction.user}",
        )
    except discord.Forbidden:
        await interaction.followup.send("I need permission to create a private setup channel.", ephemeral=True)
        async with _ACTIVE_LOCK:
            _ACTIVE_SETUPS.discard(guild.id)
        return
    except discord.HTTPException as exc:
        log.exception("Failed to create AutoMod setup channel")
        await interaction.followup.send(f"Could not create the setup channel: `{exc}`", ephemeral=True)
        async with _ACTIVE_LOCK:
            _ACTIVE_SETUPS.discard(guild.id)
        return

    try:
        icons = await _resolve_icons(guild)
        setup_session_key = f"automod-setup:{guild.id}:{channel.id}"
        setup_session_name = f"{guild.name} AutoMod setup"
        await interaction.followup.send(f"{icons['success']} AutoMod setup started in {channel.mention}.", ephemeral=True)
        intro = await _setup_embed(
            guild,
            kind="info",
            title="AutoMod Setup",
            description=(
                "Welcome to your server's AutoMod setup.\n\n"
                "First, tell me what you want AutoMod to do. DeepSeek will turn that into 3 improved setup profiles. "
                "Pick the best profile, then the rest of the questions will be based on it."
            ),
        )
        await channel.send(embed=intro)

        goal_question = SetupQuestion(
            key="initial_goal",
            prompt="What do you want AutoMod for?",
            helper="Example: stop scam links and raids, keep normal gaming chat relaxed, and block slurs.",
        )
        initial_goal = await _ask_question(cog, channel, interaction.user, goal_question, 1, 1, icons)
        if initial_goal is None:
            timeout_embed = await _setup_embed(
                guild,
                kind="warning",
                title="Setup Timed Out",
                description="Run `/automod setup` again when you are ready.",
                color=Config.COLOR_WARNING,
            )
            await channel.send(embed=timeout_embed)
            return

        profile_message = await channel.send(
            embed=await _setup_embed(
                guild,
                kind="loading",
                title="Building Profile Choices",
                description="Generating 3 improved AutoMod profiles from what you said.",
            )
        )
        profiles = await _generate_profiles(
            cog,
            guild,
            initial_goal,
            session_key=setup_session_key,
            session_name=setup_session_name,
        )
        profile_view = ProfilePaginatorView(interaction.user.id, profiles, icons)
        await profile_message.edit(embed=profile_view.build_embed(guild), view=profile_view)
        await profile_view.wait()
        if profile_view.selected_profile is None:
            await profile_message.edit(view=None)
            timeout_embed = await _setup_embed(
                guild,
                kind="warning",
                title="Setup Timed Out",
                description="Run `/automod setup` again when you are ready.",
                color=Config.COLOR_WARNING,
            )
            await channel.send(embed=timeout_embed)
            return

        selected_profile = profile_view.selected_profile
        selected_embed = profile_view.build_embed(guild)
        selected_embed.color = Config.COLOR_SUCCESS
        selected_embed.set_footer(text="Selected. Generating setup questions from this profile.")
        await profile_message.edit(embed=selected_embed, view=None)
        question_message = await channel.send(
            embed=await _setup_embed(
                guild,
                kind="loading",
                title="Building Questions",
                description=f"Creating setup questions for **{selected_profile.name}**.",
            )
        )
        questions = await _generate_questions(
            cog,
            guild,
            initial_goal,
            selected_profile,
            session_key=setup_session_key,
            session_name=setup_session_name,
        )
        await question_message.edit(
            embed=await _setup_embed(
                guild,
                kind="success",
                title="Questions Ready",
                description=f"Generated **{len(questions)}** questions based on **{selected_profile.name}**.",
                color=Config.COLOR_SUCCESS,
            )
        )

        answers: list[dict[str, str]] = []
        for index, question in enumerate(questions, start=1):
            answer = await _ask_question(cog, channel, interaction.user, question, index, len(questions), icons)
            if answer is None:
                timeout_embed = await _setup_embed(
                    guild,
                    kind="warning",
                    title="Setup Timed Out",
                    description="Run `/automod setup` again when you are ready.",
                    color=Config.COLOR_WARNING,
                )
                await channel.send(embed=timeout_embed)
                return
            answers.append({"key": question.key, "question": question.prompt, "answer": answer})

        working = await channel.send(
            embed=await _setup_embed(
                guild,
                kind="loading",
                title="Building Setup",
                description="Sending your answers to DeepSeek. No default blocked-word list is included in this prompt.",
            )
        )
        response = await call_deepseek_json(
            cog,
            _settings_prompt(),
            _setup_user_prompt(guild, initial_goal, selected_profile, answers),
            max_tokens=1800,
            session_key=setup_session_key,
            session_name=setup_session_name,
        )
        model_update = validate_automod_update(response)
        settings_update = copy.deepcopy(AUTOMOD_SETTINGS)
        settings_update.update(model_update)
        settings_update["automod_enabled"] = True
        summary = str(response.get("summary") or "AutoMod has been configured from your answers.").strip()

        review_view = SetupReviewView(interaction.user.id, settings_update, icons, summary)
        review_view.message = working
        await working.edit(embed=await review_view.build_embed(guild), view=review_view)
        await review_view.wait()
        if review_view.cancelled:
            await working.edit(
                embed=await _setup_embed(
                    guild,
                    kind="warning",
                    title="Setup Cancelled",
                    description="No AutoMod settings were saved.",
                    color=Config.COLOR_WARNING,
                ),
                view=None,
            )
            return
        if not review_view.confirmed:
            await working.edit(
                embed=await _setup_embed(
                    guild,
                    kind="warning",
                    title="Setup Timed Out",
                    description="No AutoMod settings were saved. Run `/automod setup` again when you are ready.",
                    color=Config.COLOR_WARNING,
                ),
                view=None,
            )
            return
        settings_update = copy.deepcopy(review_view.settings)

        def apply_update(settings: dict[str, Any]) -> None:
            for key in list(settings):
                if key.startswith("automod_") or key.startswith("warn_"):
                    settings.pop(key, None)
            settings.update(settings_update)

        saved = await cog._edit_settings(guild.id, apply_update)
        complete = await _setup_embed(
            guild,
            kind="success",
            title="AutoMod Setup Complete",
            description=f"{summary[:700]}\n\n" + "\n".join(_human_setting_lines(saved)),
            color=Config.COLOR_SUCCESS,
        )
        complete.set_footer(text="This setup channel will be deleted in 10 seconds.")
        await working.edit(embed=complete, view=None)
        await interaction.followup.send(f"{icons['success']} AutoMod setup finished. The setup channel is being cleaned up.", ephemeral=True)
        await asyncio.sleep(10)
        try:
            await channel.delete(reason=f"AutoMod setup completed by {interaction.user}")
        except discord.NotFound:
            pass
        except discord.HTTPException:
            log.exception("Failed to delete AutoMod setup channel %s", channel.id)
    except Exception as exc:
        log.exception("AutoMod setup failed")
        if channel is not None:
            await channel.send(embed=ModEmbed.error("Setup failed", f"`{type(exc).__name__}: {str(exc)[:900]}`"))
    finally:
        async with _ACTIVE_LOCK:
            _ACTIVE_SETUPS.discard(guild.id)


async def _apply_automod_change(cog: Any, interaction: discord.Interaction, request: str) -> None:
    if interaction.guild_id is None:
        await interaction.response.send_message("AutoMod can only be changed inside a server.", ephemeral=True)
        return
    cleaned_request = (request or "").strip()
    if len(cleaned_request) < 3:
        await interaction.response.send_message("Tell me what AutoMod setting you want changed.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    if not await _has_admin_access(interaction):
        await interaction.followup.send(embed=_permission_denied_embed(), ephemeral=True)
        return

    try:
        current_settings = await cog._get_settings(interaction.guild_id, fresh=True)
        response = await call_deepseek_json(
            cog,
            _settings_prompt(),
            _change_user_prompt(current_settings, cleaned_request),
            max_tokens=1000,
        )
        changes = validate_automod_update(response)

        def apply_changes(settings: dict[str, Any]) -> None:
            settings.update(changes)

        saved = await cog._edit_settings(interaction.guild_id, apply_changes)
        change_lines = "\n".join(f"`{key}` -> `{value}`" for key, value in sorted(changes.items()))
        summary = str(response.get("summary") or "Requested AutoMod settings were updated.").strip()
        embed = discord.Embed(
            title="AutoMod changed",
            description=f"{summary[:600]}\n\n{change_lines[:1500]}\n\n" + "\n".join(_human_setting_lines(saved)),
            color=Config.COLOR_SUCCESS,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as exc:
        if "DeepSeek did not return any valid AutoMod settings" in str(exc):
            await interaction.followup.send(
                embed=ModEmbed.error(
                    "No changes made",
                    "The AI could not determine any settings to change. Ask for a specific setting, or provide exact custom words.",
                ),
                ephemeral=True,
            )
        else:
            log.exception("AutoMod change failed")
            await interaction.followup.send(
                embed=ModEmbed.error("AutoMod change failed", f"`{type(exc).__name__}: {str(exc)[:900]}`"),
                ephemeral=True,
            )


async def handle_automod_change(cog: Any, interaction: discord.Interaction, request: Optional[str] = None) -> None:
    if not (request or "").strip():
        if not await _has_admin_access(interaction):
            await interaction.response.send_message(embed=_permission_denied_embed(), ephemeral=True)
            return
        await interaction.response.send_modal(AutoModChangeModal(cog))
        return
    await _apply_automod_change(cog, interaction, request)
