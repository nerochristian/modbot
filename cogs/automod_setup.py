"""Modal-based AutoMod setup and natural-language change flow."""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import re
from typing import Any, Callable, Mapping, Optional

import discord

from cogs.automod_config import AUTOMOD_SETTINGS
from cogs.automod_engine import LinksRule, ScamRule, normalize_domain
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


def _detail_lines(values: Any, *, empty: str = "None", limit: int = 40) -> str:
    if not isinstance(values, list) or not values:
        return empty
    shown = [f"- `{str(value)[:120]}`" for value in values[:limit]]
    extra = len(values) - len(shown)
    if extra > 0:
        shown.append(f"- ...and {extra} more")
    return "\n".join(shown)


def _blocked_link_summary(settings: Mapping[str, Any]) -> str:
    if not settings.get("automod_links_enabled", False):
        return "Link filtering is off."
    mode = str(settings.get("automod_links_mode", "dangerous")).casefold()
    suspicious = ", ".join(f"`{domain}`" for domain in LinksRule._suspicious_domains)
    if mode == "allowlist":
        allowed = list(settings.get("automod_links_whitelist", [])) + list(settings.get("automod_whitelisted_domains", []))
        return (
            "Blocks **every link domain that is not allowed**.\n"
            f"Allowed domains: {_preview_values(allowed)}"
        )
    return (
        "Blocks suspicious shortened links and known dangerous links.\n"
        f"Suspicious shorteners: {suspicious}\n"
        f"Known dangerous tracking/phishing domains: {_preview_values(list(ScamRule._dangerous_domains))}"
    )


def _blocked_invite_summary(settings: Mapping[str, Any]) -> str:
    if not settings.get("automod_invites_enabled", False):
        return "Invite filtering is off."
    allowed = settings.get("automod_allowed_invites", [])
    if not isinstance(allowed, list) or not allowed:
        return "Blocks **all Discord invite links**."
    return (
        "Blocks every Discord invite link except these invite codes:\n"
        f"{_detail_lines(allowed)}"
    )


def _review_description(settings: Mapping[str, Any], summary: str) -> str:
    badwords = settings.get("automod_badwords", [])
    link_mode = str(settings.get("automod_links_mode", "dangerous")).title()
    return (
        f"{summary[:500]}\n\n"
        "Review what this setup will block before I save it. Use the buttons below to see the full blocked lists and rules.\n\n"
        f"**Blocked Words**\n"
        f"Status: **{'On' if settings.get('automod_badwords_enabled', False) else 'Off'}**\n"
        f"Blocked words/phrases: `{_preview_values(badwords)}`\n\n"
        f"**Links**\n"
        f"Status: **{'On' if settings.get('automod_links_enabled', False) else 'Off'}**\n"
        f"Mode: **{link_mode}**\n"
        f"Blocked links: {_blocked_link_summary(settings)}\n\n"
        f"**Invites and Security**\n"
        f"Invites: **{'On' if settings.get('automod_invites_enabled', False) else 'Off'}**\n"
        f"Blocked invites: {_blocked_invite_summary(settings)}\n"
        f"Scam protection: **{'On' if settings.get('automod_scam_protection', False) else 'Off'}**\n\n"
        f"**Limits and Actions**\n"
        f"Spam: **{settings.get('automod_spam_threshold', 5)} messages / {settings.get('automod_spam_window', 5)}s**\n"
        f"Mentions: **{settings.get('automod_max_mentions', 5)} max**\n"
        f"Regular action: **{str(settings.get('automod_punishment', 'warn')).title()}**\n"
        f"Security action: **{str(settings.get('automod_security_punishment', 'timeout')).title()}**"
    )


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

    async def _send_detail(self, interaction: discord.Interaction, title: str, description: str) -> None:
        embed = await _setup_embed(
            interaction.guild,
            kind="info",
            title=title,
            description=description[:3900],
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Blocked Words", style=discord.ButtonStyle.secondary, row=0)
    async def blocked_words_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        words = self.settings.get("automod_badwords", [])
        await self._send_detail(
            interaction,
            "Blocked Words",
            (
                f"Status: **{'On' if self.settings.get('automod_badwords_enabled') else 'Off'}**\n\n"
                "Messages are blocked when they contain these configured words or phrases, including common spacing/evasion variants:\n"
                f"{_detail_lines(words)}"
            ),
        )

    @discord.ui.button(label="Links", style=discord.ButtonStyle.secondary, row=0)
    async def links_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        allowed = list(self.settings.get("automod_links_whitelist", [])) + list(self.settings.get("automod_whitelisted_domains", []))
        await self._send_detail(
            interaction,
            "Blocked Links",
            (
                f"Status: **{'On' if self.settings.get('automod_links_enabled') else 'Off'}**\n"
                f"Mode: **{str(self.settings.get('automod_links_mode', 'dangerous')).title()}**\n\n"
                f"{_blocked_link_summary(self.settings)}\n\n"
                f"Allowed domains that will not be blocked:\n{_detail_lines(allowed)}"
            ),
        )

    @discord.ui.button(label="Invites", style=discord.ButtonStyle.secondary, row=0)
    async def invites_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._send_detail(
            interaction,
            "Blocked Invites and Scams",
            (
                f"Invite filter: **{'On' if self.settings.get('automod_invites_enabled') else 'Off'}**\n"
                f"{_blocked_invite_summary(self.settings)}\n\n"
                f"Scam protection: **{'On' if self.settings.get('automod_scam_protection') else 'Off'}**\n"
                "Scam protection blocks known tracking/phishing links and messages like free Nitro, claim rewards, Steam/Discord gifts, account verification scams, and crypto giveaway/airdrop scams when they include links."
            ),
        )

    @discord.ui.button(label="Limits", style=discord.ButtonStyle.secondary, row=1)
    async def limits_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._send_detail(
            interaction,
            "Blocked Limits",
            (
                f"Spam: blocks **{self.settings.get('automod_spam_threshold', 5)} messages in {self.settings.get('automod_spam_window', 5)} seconds**.\n"
                f"Duplicates: blocks **{self.settings.get('automod_duplicate_threshold', 3)} repeated messages in {self.settings.get('automod_duplicate_window', 30)} seconds**.\n"
                f"Mentions: blocks messages with **{self.settings.get('automod_max_mentions', 5)} or more unique mentions**.\n"
                f"Caps: blocks messages at **{self.settings.get('automod_caps_percentage', 70)}% caps** after **{self.settings.get('automod_caps_min_length', 10)} letters**.\n"
                f"New accounts: applies new-account restrictions for **{self.settings.get('automod_newaccount_days', 7)} days**."
            ),
        )

    @discord.ui.button(label="Actions", style=discord.ButtonStyle.secondary, row=1)
    async def actions_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._send_detail(
            interaction,
            "Actions",
            (
                f"Normal violations: **{str(self.settings.get('automod_punishment', 'warn')).title()}**.\n"
                f"Security violations: **{str(self.settings.get('automod_security_punishment', 'timeout')).title()}**.\n"
                f"Timeout length: **{_format_duration(self.settings.get('automod_mute_duration', 3600))}**.\n"
                f"Tempban length: **{_format_duration(self.settings.get('automod_tempban_duration', 86400))}**.\n"
                f"Violation cooldown: **{self.settings.get('automod_violation_cooldown', 10)} seconds**."
            ),
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


class AutoModSetupModal(discord.ui.Modal, title="AutoMod Setup"):
    """A single up-front form covering the whole AutoMod setup in one submit."""

    def __init__(self, cog: Any) -> None:
        super().__init__(timeout=900)
        self.cog = cog
        self.goal = discord.ui.TextInput(
            label="What should AutoMod do? (style/goals)",
            placeholder="e.g. Keep gaming chat relaxed, but stop scam links and raids hard.",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True,
        )
        self.words_and_links = discord.ui.TextInput(
            label="Bad words / links & invites policy",
            placeholder="e.g. block slurs + 'simp'; only allow youtube.com, twitch.tv; no invites except ours",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False,
        )
        self.limits = discord.ui.TextInput(
            label="Spam/raid limits & punishments",
            placeholder="e.g. timeout for spam, ban new accounts that raid, kick for caps spam",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False,
        )
        self.warnings = discord.ui.TextInput(
            label="Warning thresholds",
            placeholder="e.g. 3 warnings = mute, 5 = kick, 8 = ban",
            style=discord.TextStyle.short,
            max_length=200,
            required=False,
        )
        self.notes = discord.ui.TextInput(
            label="Anything else?",
            placeholder="e.g. log channel #mod-log, ignore staff role, exclude #memes",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False,
        )
        for field in (self.goal, self.words_and_links, self.limits, self.warnings, self.notes):
            self.add_item(field)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await _build_and_review_setup(
            self.cog,
            interaction,
            {
                "goal": str(self.goal),
                "words_and_links": str(self.words_and_links),
                "limits_and_punishments": str(self.limits),
                "warning_thresholds": str(self.warnings),
                "notes": str(self.notes),
            },
        )


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
    
    # Try parsing the whole thing first
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Find the first valid JSON object by extracting from the first '{'
    start_idx = content.find('{')
    if start_idx == -1:
        raise ValueError("DeepSeek did not return a JSON object.")

    # Iterate through possible end indices for the JSON object
    for end_idx in range(len(content), start_idx, -1):
        if content[end_idx - 1] != '}':
            continue
        try:
            parsed = json.loads(content[start_idx:end_idx])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    raise ValueError("DeepSeek returned malformed JSON.")


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
                    search=True,
                    deepthink=True,
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


def _settings_prompt() -> str:
    return (
        "You configure a Discord bot AutoMod system. Return exactly one JSON object with a "
        "`settings` object and optional `summary` string. Do not include markdown.\n\n"
        "Only use these setting keys:\n"
        f"{', '.join(sorted(_ALLOWED_KEYS))}\n\n"
        "Accepted actions: log, warn, timeout, kick, ban, quarantine. "
        "Accepted link modes: dangerous, allowlist. Durations are seconds. "
        "Set every important automod_* key needed for a full setup. "
        "If the admin asks for common slurs or says 'all', do NOT output severe real-world slurs (which trigger safety filters); rely on `automod_badwords_enabled` for those. However, you MUST creatively infer and add mild/moderate custom words or specific slang to `automod_badwords` if they ask for it. "
        "If the admin is vague about links (e.g. 'all safe ones'), you MUST intelligently infer and populate `automod_whitelisted_domains` with 5-10 popular safe websites (like youtube.com, twitch.tv, twitter.com). "
        "Do NOT literally add words like 'idk' or 'all' to the lists. Keep values practical and avoid destructive punishments unless clearly requested."
    )


def _schema_summary() -> dict[str, Any]:
    return {
        "booleans": sorted(_BOOL_KEYS),
        "integers": _INT_RANGES,
        "choices": {key: sorted(values) for key, values in _OPTION_KEYS.items()},
        "string_lists": sorted(_STRING_LIST_KEYS),
        "nullable_ids": sorted(_NULLABLE_INT_KEYS),
    }


def _setup_user_prompt(guild: discord.Guild, answers: Mapping[str, str]) -> str:
    return json.dumps(
        {
            "guild": {"id": guild.id, "name": guild.name, "member_count": guild.member_count},
            "schema": _schema_summary(),
            "admin_answers": {
                "goal_and_style": answers.get("goal", ""),
                "bad_words_and_links_policy": answers.get("words_and_links", ""),
                "spam_raid_limits_and_punishments": answers.get("limits_and_punishments", ""),
                "warning_thresholds": answers.get("warning_thresholds", ""),
                "other_notes": answers.get("notes", ""),
            },
            "goal": (
                "Fill out a complete production-safe AutoMod setup from these answers. "
                "Infer sensible, practical defaults for anything the admin did not mention."
            ),
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


async def _resolve_icons(guild: discord.Guild) -> dict[str, str]:
    return {
        kind: await _status_icon(guild, kind)
        for kind in ("success", "error", "warning", "info", "loading", "lock")
    }


async def start_setup_wizard(cog: Any, interaction: discord.Interaction) -> None:
    """Entry point for `/automod setup`: opens the single setup form."""
    if interaction.guild is None or interaction.guild_id is None:
        await interaction.response.send_message("AutoMod setup can only run inside a server.", ephemeral=True)
        return

    # Keep this check fast: it short-circuits on owner/administrator before
    # touching the database, so it stays well within Discord's 3s response window.
    if not await _has_admin_access(interaction):
        await interaction.response.send_message(embed=_permission_denied_embed(), ephemeral=True)
        return

    await interaction.response.send_modal(AutoModSetupModal(cog))


async def _build_and_review_setup(cog: Any, interaction: discord.Interaction, answers: dict[str, str]) -> None:
    guild = interaction.guild
    if guild is None or interaction.guild_id is None:
        await interaction.response.send_message("AutoMod setup can only run inside a server.", ephemeral=True)
        return

    async with _ACTIVE_LOCK:
        if guild.id in _ACTIVE_SETUPS:
            await interaction.response.send_message(
                "An AutoMod setup is already running in this server.", ephemeral=True
            )
            return
        _ACTIVE_SETUPS.add(guild.id)

    await interaction.response.defer(ephemeral=True, thinking=True)
    icons = await _resolve_icons(guild)
    working: Optional[discord.Message] = None
    try:
        working = await interaction.followup.send(
            embed=await _setup_embed(
                guild,
                kind="loading",
                title="Building Setup",
                description="Sending your answers to DeepSeek.",
            ),
            wait=True,
        )

        response = await call_deepseek_json(
            cog,
            _settings_prompt(),
            _setup_user_prompt(guild, answers),
            max_tokens=1800,
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

        final_settings = copy.deepcopy(review_view.settings)

        def apply_update(settings: dict[str, Any]) -> None:
            for key in list(settings):
                if key.startswith("automod_") or key.startswith("warn_"):
                    settings.pop(key, None)
            settings.update(final_settings)

        saved = await cog._edit_settings(guild.id, apply_update)
        complete = await _setup_embed(
            guild,
            kind="success",
            title="AutoMod Setup Complete",
            description=f"{summary[:700]}\n\n" + "\n".join(_human_setting_lines(saved)),
            color=Config.COLOR_SUCCESS,
        )
        await working.edit(embed=complete, view=None)
    except Exception as exc:
        log.exception("AutoMod setup failed")
        error_embed = ModEmbed.error("Setup failed", f"`{type(exc).__name__}: {str(exc)[:900]}`")
        if working is not None:
            await working.edit(embed=error_embed, view=None)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)
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
