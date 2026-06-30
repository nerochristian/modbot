"""Conversational AutoMod setup and natural-language change flow."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Optional

import aiohttp
import discord

from cogs.automod_config import AUTOMOD_SETTINGS
from cogs.automod_engine import normalize_domain
from config import Config
from utils.embeds import ModEmbed


log = logging.getLogger("AutoMod.Setup")

_DO_API_KEY = os.getenv("DO_API_KEY", "").strip()
_DO_BASE_URL = os.getenv("DO_INFERENCE_BASE_URL", "https://inference.do-ai.run/v1").strip().rstrip("/")
_DO_MODEL = os.getenv("DO_AUTOMOD_MODEL", os.getenv("DO_PROFILE_MODEL", "deepseek-4-flash")).strip()

_ACTIVE_SETUPS: set[int] = set()
_ACTIVE_LOCK = asyncio.Lock()


@dataclass(frozen=True)
class SetupQuestion:
    key: str
    prompt: str
    options: tuple[str, ...] = ()

    @property
    def is_closed(self) -> bool:
        return bool(self.options)


QUESTIONS: tuple[SetupQuestion, ...] = (
    SetupQuestion(
        "strictness",
        "How strict should AutoMod be overall?",
        ("Standard", "Relaxed", "Strict"),
    ),
    SetupQuestion(
        "server_profile",
        "Describe your server and what you mainly want AutoMod to prevent.",
    ),
    SetupQuestion(
        "bad_words",
        "Should AutoMod block common slurs, harassment, and banned words?",
        ("Yes", "No", "Only severe words"),
    ),
    SetupQuestion(
        "spam_action",
        "What should happen when someone spams?",
        ("Warn", "Timeout", "Nothing"),
    ),
    SetupQuestion(
        "security_action",
        "What should happen for scams, phishing links, or dangerous invites?",
        ("Timeout", "Ban", "Warn"),
    ),
    SetupQuestion(
        "custom_words",
        "Any exact words or phrases you want banned? Type them separated by commas, or type none.",
    ),
    SetupQuestion(
        "links",
        "How should links and Discord invites work? Example: dangerous links only, block all except YouTube/GitHub, or allow normal links.",
    ),
    SetupQuestion(
        "raid_protection",
        "Should AutoMod be strict with brand-new accounts and mass mentions?",
        ("Yes", "No", "Only during raids"),
    ),
    SetupQuestion(
        "feedback",
        "Should users get a DM when AutoMod acts?",
        ("Yes", "No"),
    ),
)

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
    return bool(
        manager_role in role_ids
        or any(role_id in role_ids for role_id in admin_roles)
    )


def _permission_denied_embed() -> discord.Embed:
    return ModEmbed.error(
        "Permission Denied",
        "You need Administrator, Manager, or a configured admin role to change AutoMod.",
    )


class SetupQuestionView(discord.ui.View):
    def __init__(self, owner_id: int, options: Iterable[str]) -> None:
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.value: Optional[str] = None
        for index, option in enumerate(options):
            button = discord.ui.Button(
                label=option,
                style=discord.ButtonStyle.primary if index == 0 else discord.ButtonStyle.secondary,
                custom_id=f"automod_setup:{index}",
            )
            button.callback = self._make_callback(option)
            self.add_item(button)

    def _make_callback(self, option: str) -> Callable[[discord.Interaction], Any]:
        async def callback(interaction: discord.Interaction) -> None:
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message("This setup belongs to another admin.", ephemeral=True)
                return
            self.value = option
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
            if interaction.message and interaction.message.embeds:
                await interaction.response.edit_message(embed=interaction.message.embeds[0], view=self)
            else:
                await interaction.response.edit_message(view=self)
            self.stop()

        return callback


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
    if value is None:
        return None
    if isinstance(value, bool):
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


async def call_deepseek_json(system_prompt: str, user_prompt: str, *, max_tokens: int = 1400) -> dict[str, Any]:
    if not _DO_API_KEY:
        raise RuntimeError("DigitalOcean inference is missing DO_API_KEY.")
    payload = {
        "model": _DO_MODEL or "deepseek-4-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            f"{_DO_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {_DO_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        ) as response:
            data = await response.json(content_type=None)
            if response.status >= 400:
                detail = data.get("error", data) if isinstance(data, dict) else data
                raise RuntimeError(f"DigitalOcean HTTP {response.status}: {str(detail)[:500]}")
    choices = data.get("choices") if isinstance(data, dict) else None
    if not choices:
        raise RuntimeError("DigitalOcean response did not include choices.")
    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError("DigitalOcean response did not include text content.")
    return _extract_json_object(content)


def _settings_prompt() -> str:
    return (
        "You configure a Discord bot AutoMod system. Return exactly one JSON object with a "
        "`settings` object and optional `summary` string. Do not include markdown.\n\n"
        "Only use these setting keys:\n"
        f"{', '.join(sorted(_ALLOWED_KEYS))}\n\n"
        "Actions must be one of: log, warn, timeout, kick, ban, quarantine. "
        "Link mode must be dangerous or allowlist. Durations are seconds. "
        "If the user asks to block 'all bad words' or 'slurs', just set automod_badwords_enabled to true. Do not generate a list of bad words yourself. "
        "Keep values practical for a real Discord server. If the request is unclear, make the least destructive safe choice."
    )


def _setup_user_prompt(guild: discord.Guild, answers: list[dict[str, str]]) -> str:
    return json.dumps(
        {
            "guild": {"id": guild.id, "name": guild.name, "member_count": guild.member_count},
            "defaults": {key: AUTOMOD_SETTINGS[key] for key in sorted(AUTOMOD_SETTINGS)},
            "answers": answers,
            "goal": "Create a complete, production-safe AutoMod configuration from these setup answers.",
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


async def _delete_channel_later(channel: discord.TextChannel, delay: int = 30) -> None:
    await asyncio.sleep(delay)
    try:
        await channel.delete(reason="AutoMod setup completed")
    except discord.HTTPException:
        log.exception("Failed to delete AutoMod setup channel %s", channel.id)


async def _collect_open_answer(cog: Any, channel: discord.TextChannel, user: discord.abc.User) -> Optional[str]:
    def check(message: discord.Message) -> bool:
        return message.author.id == user.id and message.channel.id == channel.id

    try:
        message = await cog.bot.wait_for("message", check=check, timeout=300)
    except asyncio.TimeoutError:
        return None
    return message.content.strip()[:1500]


class SetupSummaryView(discord.ui.View):
    def __init__(self, settings: dict[str, Any]) -> None:
        super().__init__(timeout=None)
        self.settings = settings

    @discord.ui.button(label="Show Banned Words", style=discord.ButtonStyle.secondary, custom_id="setup_show_words")
    async def show_words(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        words = self.settings.get("automod_badwords", [])
        if not words:
            await interaction.response.send_message("No custom blocked words are configured.", ephemeral=True)
            return
        content = ", ".join(words)
        if len(content) > 1900:
            content = content[:1900] + "... (truncated)"
        await interaction.response.send_message(f"**Blocked Words:**\n```\n{content}\n```", ephemeral=True)

    @discord.ui.button(label="Show Allowed Links", style=discord.ButtonStyle.secondary, custom_id="setup_show_links")
    async def show_links(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        domains = self.settings.get("automod_whitelisted_domains", [])
        if not domains:
            await interaction.response.send_message("No allowed domains are configured.", ephemeral=True)
            return
        content = ", ".join(domains)
        if len(content) > 1900:
            content = content[:1900] + "... (truncated)"
        await interaction.response.send_message(f"**Allowed Domains:**\n```\n{content}\n```", ephemeral=True)


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
        await interaction.followup.send(f"AutoMod setup started in {channel.mention}.", ephemeral=True)
        await channel.send(
            embed=discord.Embed(
                title="AutoMod setup",
                description=(
                    "Hello! Welcome to your server's AutoMod setup.\n"
                    "Answer each question below. Button questions are closed-ended; text questions are open-ended."
                ),
                color=Config.COLOR_INFO,
            )
        )

        answers: list[dict[str, str]] = []
        for index, question in enumerate(QUESTIONS, start=1):
            embed = discord.Embed(
                title=f"Question {index}/{len(QUESTIONS)}",
                description=question.prompt,
                color=Config.COLOR_INFO,
            )
            if question.is_closed:
                view = SetupQuestionView(interaction.user.id, question.options)
                prompt_message = await channel.send(embed=embed, view=view)
                await view.wait()
                if view.value is None:
                    await channel.send(embed=ModEmbed.warning("Setup timed out", "Run `/automod setup` again when you are ready."))
                    return
                await prompt_message.edit(embed=embed, view=None)
                answer = view.value
                await channel.send(embed=ModEmbed.info("Selected", answer))
            else:
                await channel.send(embed=embed)
                answer = await _collect_open_answer(cog, channel, interaction.user)
                if answer is None:
                    await channel.send(embed=ModEmbed.warning("Setup timed out", "Run `/automod setup` again when you are ready."))
                    return
            answers.append({"key": question.key, "question": question.prompt, "answer": answer})

        working = await channel.send(embed=ModEmbed.info("Building setup", "Sending your answers to DeepSeek through DigitalOcean."))
        response = await call_deepseek_json(_settings_prompt(), _setup_user_prompt(guild, answers), max_tokens=1800)
        model_update = validate_automod_update(response)
        settings_update = dict(AUTOMOD_SETTINGS)
        settings_update.update(model_update)
        settings_update["automod_enabled"] = True

        def apply_update(settings: dict[str, Any]) -> None:
            for key in list(settings):
                if key.startswith("automod_") or key.startswith("warn_"):
                    settings.pop(key, None)
            settings.update(settings_update)

        saved = await cog._edit_settings(guild.id, apply_update)
        summary = str(response.get("summary") or "AutoMod has been configured from your answers.").strip()
        embed = discord.Embed(
            title="AutoMod setup complete",
            description=f"{summary[:700]}\n\n" + "\n".join(_human_setting_lines(saved)),
            color=Config.COLOR_SUCCESS,
        )
        view = SetupSummaryView(saved)
        await working.edit(embed=embed, view=view)
        await channel.send("This setup channel will close in 30 seconds.")
        asyncio.create_task(_delete_channel_later(channel))
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
                    "The AI couldn't determine any settings to change based on your request. "
                    "If you asked to add bad words, please provide the specific words you want to block, or ask to 'enable the bad word filter'."
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
