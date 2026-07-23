"""Admin-level handlers — execute_raw_api, execute_python."""
from __future__ import annotations

import asyncio
import collections
import csv
import datetime as datetime_module
import io
import itertools
import json
import logging
import math
import random
import re
import statistics
import time as time_module
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict

import discord

from ..context import ToolContext, ToolResult, _now
from ..python_runtime import (
    PythonSafetyError,
    execution_digest,
    normalize_python_code,
    safe_builtins,
    validate_python_code,
)
from ..registry import ToolRegistry
from ..types import ToolType
from utils.checks import is_bot_owner_id

logger = logging.getLogger("ModBot.AIModeration.Handlers.Admin")


def _make_activity_fetcher(guild: discord.Guild) -> Callable:
    import datetime as _dt

    async def fetch_recent_activity(days: int = 7) -> Dict[int, Any]:
        now_dt = _dt.datetime.now(timezone.utc)
        cutoff = now_dt - _dt.timedelta(days=max(1, min(days, 30)))
        activity: Dict[int, Any] = {}

        async def _scan(ch: discord.TextChannel) -> None:
            try:
                async for msg in ch.history(limit=50, after=cutoff):
                    prev = activity.get(msg.author.id)
                    if prev is None or msg.created_at > prev:
                        activity[msg.author.id] = msg.created_at
            except (discord.Forbidden, discord.HTTPException):
                pass

        channels = guild.text_channels
        for i in range(0, len(channels), 10):
            batch = channels[i:i + 10]
            await asyncio.gather(*[_scan(ch) for ch in batch])

        return activity

    return fetch_recent_activity


async def _log_execution(ctx: ToolContext, preview: str, log_embed: discord.Embed) -> None:
    await ctx.cog.log_action(
        message=ctx.message, action="execute_python",
        actor=ctx.actor, target=None,
        reason=ctx.decision.reason or "AI Python execution",
        decision=ctx.decision, extra={"Result": preview[:900]}, view=None,
    )
    logging_cog = ctx.cog.bot.get_cog("Logging")
    if not logging_cog:
        return
    try:
        log_channel = await logging_cog.get_log_channel(ctx.guild, "automod")
        if log_channel:
            await logging_cog.safe_send_log(log_channel, log_embed)
    except Exception:
        logger.debug("Failed to send Python execution details to automod log", exc_info=True)


# ---- raw_api safety helpers -------------------------------------------------


def _contains_forbidden_raw_api_key(value: object) -> bool:
    if isinstance(value, dict):
        for key, inner in value.items():
            if str(key).lower() in {"token", "authorization", "client_secret", "bot_token"}:
                return True
            if _contains_forbidden_raw_api_key(inner):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_raw_api_key(inner) for inner in value)
    return False


def _raw_api_safety_error(ctx: ToolContext, method: str, endpoint: str, payload: object) -> str | None:
    if not is_bot_owner_id(ctx.actor.id):
        return "Raw Discord API access is restricted to the bot owner."
    if not endpoint.startswith("/"):
        return "Raw API endpoint must start with `/`."
    if "{" in endpoint or "}" in endpoint:
        return "Raw API endpoint contains unresolved placeholders."
    if "://" in endpoint or endpoint.startswith("//"):
        return "Raw API endpoint must be a Discord path, not a full URL."
    if method not in {"GET", "POST", "PATCH", "PUT", "DELETE"}:
        return "Unsupported HTTP method."
    normalized = endpoint.lower().split("?", 1)[0].rstrip("/")
    if ".." in normalized or "%2e" in normalized or "%2f" in normalized:
        return "Raw API endpoint contains unsafe path encoding."
    guild_id = str(ctx.guild.id)
    bot_id = str(ctx.cog.bot.user.id) if ctx.cog.bot.user else ""
    if re.fullmatch(rf"/guilds/{guild_id}", normalized) and method == "DELETE":
        return "Deleting the server is blocked."
    if normalized.startswith("/users/@me") or (bot_id and normalized.startswith(f"/users/{bot_id}")):
        return "Manipulating the bot account is blocked."
    if any(part in normalized for part in ("/oauth2", "/auth", "/tokens", "/applications/@me")):
        return "OAuth, auth, token, and application-account endpoints are blocked."
    guild_prefix = f"/guilds/{guild_id}"
    if normalized.startswith("/guilds/"):
        if normalized != guild_prefix and not normalized.startswith(f"{guild_prefix}/"):
            return "Raw API guild routes are restricted to this server."
    elif channel_match := re.match(r"^/channels/(\d+)(?:/|$)", normalized):
        channel_id = int(channel_match.group(1))
        get_channel_or_thread = getattr(ctx.guild, "get_channel_or_thread", None)
        channel = get_channel_or_thread(channel_id) if callable(get_channel_or_thread) else ctx.guild.get_channel(channel_id)
        if channel is None:
            return "Raw API channel routes are restricted to this server."
    elif normalized.startswith("/webhooks/"):
        return "Raw webhook routes are blocked because ownership cannot be verified safely."
    else:
        return "Raw API is restricted to this server's guild and channel endpoints."
    if _contains_forbidden_raw_api_key(payload):
        return "Payload cannot contain token or authorization fields."
    return None


def _normalize_scheduled_event_payload(endpoint: str, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized_endpoint = endpoint.lower().split("?", 1)[0].rstrip("/")
    if method != "POST" or not re.fullmatch(r"/guilds/\d{15,22}/scheduled-events", normalized_endpoint):
        return payload

    fixed = dict(payload)
    name_text = str(fixed.get("name") or "").lower()
    metadata = fixed.get("entity_metadata")
    metadata = dict(metadata) if isinstance(metadata, dict) else {}
    location_text = str(metadata.get("location") or "").lower()
    looks_external = any(
        word in f"{name_text} {location_text}"
        for word in ("smp", "minecraft", "manhunt", "server", "external", "irl")
    )
    if looks_external or fixed.get("entity_type") in (None, 3, "3", "external"):
        fixed["entity_type"] = 3
        fixed.pop("channel_id", None)
        if not metadata.get("location"):
            metadata["location"] = "Supreme SMP" if "smp" in name_text else "External"
        fixed["entity_metadata"] = metadata
        if not fixed.get("scheduled_end_time") and fixed.get("scheduled_start_time"):
            try:
                start = datetime.fromisoformat(str(fixed["scheduled_start_time"]).replace("Z", "+00:00"))
                fixed["scheduled_end_time"] = (start + timedelta(hours=1)).isoformat()
            except Exception:
                pass
    elif str(fixed.get("entity_type")).lower() == "voice":
        fixed["entity_type"] = 2
    fixed.setdefault("privacy_level", 2)
    return fixed


# ---- registered handlers ----------------------------------------------------


@ToolRegistry.register(
    ToolType.EXECUTE_RAW_API,
    display_name="Execute Raw API",
    color=discord.Color.blurple(),
    emoji="API",
    required_permission="bot_owner",
    category="admin",
)
async def handle_execute_raw_api(ctx: ToolContext) -> ToolResult:
    method = str(ctx.arg("method", "")).strip().upper()
    endpoint = str(ctx.arg("endpoint", "")).strip()
    raw_payload = ctx.arg("payload", {})
    payload: Dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}

    safety_error = _raw_api_safety_error(ctx, method, endpoint, payload)
    if safety_error:
        return ToolResult.fail(safety_error)
    payload = _normalize_scheduled_event_payload(endpoint, method, payload)

    route = discord.http.Route(method, endpoint)
    kwargs: Dict[str, Any] = {"reason": f"AI raw API ({ctx.actor})"}
    if method in {"POST", "PATCH", "PUT"}:
        kwargs["json"] = payload

    result = await ctx.cog.bot.http.request(route, **kwargs)

    preview = "No response body."
    if result is not None:
        try:
            preview = json.dumps(result, ensure_ascii=True)
        except TypeError:
            preview = str(result)
        if len(preview) > 900:
            preview = preview[:897] + "..."

    embed = discord.Embed(title="Raw Discord API Executed", color=discord.Color.blurple(), timestamp=_now())
    embed.add_field(name="Method", value=method, inline=True)
    embed.add_field(name="Endpoint", value=f"`{endpoint[:250]}`", inline=False)
    embed.add_field(name="Response", value=f"```json\n{preview}\n```", inline=False)
    return ToolResult.ok("Raw Discord API request executed.", embed=embed)


@ToolRegistry.register(
    ToolType.EXECUTE_PYTHON,
    display_name="Execute Python",
    color=discord.Color.red(),
    emoji="Python",
    required_permission="bot_owner",
    category="admin",
)
async def handle_execute_python(ctx: ToolContext) -> ToolResult:
    _TIMEOUT = 60
    _MAX_PREVIEW = 900
    _MAX_CODE_DISPLAY = 1000

    is_owner = is_bot_owner_id(ctx.actor.id) or await ctx.cog.bot.is_owner(ctx.actor)
    if not is_owner:
        return ToolResult.fail("Execute Python is restricted to the bot owner.")

    code = normalize_python_code(str(ctx.arg("code", "")))
    try:
        compiled = validate_python_code(code)
    except PythonSafetyError as exc:
        return ToolResult.fail(f"Generated action failed its safety check: {exc}")

    digest = execution_digest(code)
    expected_digest = str(ctx.arg("code_sha256", "")).strip().lower()
    if expected_digest and expected_digest != digest:
        return ToolResult.fail("Generated action changed after confirmation, so it was not executed.")

    real_channel = ctx.message.channel if ctx.message else None

    async def send_bounded(
        destination: Any,
        content: Any,
        *,
        filename: str = "ai-action-report.txt",
    ) -> Any:
        """Send generated reports without exceeding Discord's content limit."""
        sender = getattr(destination, "send", None)
        if not callable(sender):
            raise TypeError("send_bounded destination must provide an async send method.")
        text = str(content)
        if len(text) <= 3_800:
            return await sender(text)

        safe_filename = re.sub(r"[^A-Za-z0-9._-]+", "-", str(filename)).strip(".-")
        safe_filename = (safe_filename or "ai-action-report.txt")[:100]
        payload = text.encode("utf-8")
        max_bytes = 7_500_000
        if len(payload) > max_bytes:
            suffix = b"\n\n[Report truncated to fit Discord's upload limit.]"
            payload = payload[: max_bytes - len(suffix)] + suffix
        report = discord.File(io.BytesIO(payload), filename=safe_filename)
        return await sender("The full action report is attached.", file=report)

    env: Dict[str, Any] = {
        "__builtins__": safe_builtins(),
        "bot": ctx.cog.bot,
        "guild": ctx.guild,
        "author": ctx.actor,
        "message": ctx.message,
        "channel": real_channel,
        "discord": discord,
        "asyncio": asyncio,
        "collections": collections,
        "csv": csv,
        "datetime": datetime_module,
        "io": io,
        "itertools": itertools,
        "json": json,
        "math": math,
        "random": random,
        "re": re,
        "statistics": statistics,
        "time": time_module,
        "uuid": uuid,
        "fetch_recent_activity": _make_activity_fetcher(ctx.guild),
        "send_bounded": send_bounded,
    }

    try:
        exec(compiled, env)
        raw_result = await asyncio.wait_for(env["__ai_exec_func"](), timeout=_TIMEOUT)
    except asyncio.TimeoutError:
        log_embed = discord.Embed(title="Python Execution Timed Out", color=discord.Color.orange(), timestamp=_now())
        log_embed.add_field(name="Execution ID", value=f"`{digest[:12]}`", inline=True)
        log_embed.add_field(name="Code", value=f"```py\n{code[:_MAX_CODE_DISPLAY]}\n```", inline=False)
        await _log_execution(ctx, f"Timed out after {_TIMEOUT}s", log_embed)
        return ToolResult.fail(f"Execution timed out after {_TIMEOUT}s. Try a smaller scope or break into steps.")
    except Exception as exc:
        logger.exception("Owner-authorized AI Python execution failed (id=%s)", digest[:12])
        error_preview = f"{type(exc).__name__}: {exc}"
        log_embed = discord.Embed(title="Python Execution Failed", color=discord.Color.red(), timestamp=_now())
        log_embed.add_field(name="Execution ID", value=f"`{digest[:12]}`", inline=True)
        log_embed.add_field(name="Error", value=f"```\n{error_preview[:_MAX_PREVIEW]}\n```", inline=False)
        log_embed.add_field(name="Code", value=f"```py\n{code[:_MAX_CODE_DISPLAY]}\n```", inline=False)
        await _log_execution(ctx, error_preview, log_embed)
        return ToolResult.fail(
            f"The generated action failed during execution ({type(exc).__name__}). "
            f"Execution ID: `{digest[:12]}`. Details are in automod logs."
        )

    preview = str(raw_result) if raw_result is not None else "Execution completed successfully (no return value)."
    if len(preview) > _MAX_PREVIEW:
        preview = preview[:_MAX_PREVIEW - 3] + "..."

    log_embed = discord.Embed(title="Python Code Executed", color=discord.Color.green(), timestamp=_now())
    log_embed.add_field(name="Execution ID", value=f"`{digest[:12]}`", inline=True)
    if summary := str(ctx.arg("summary", "")).strip():
        log_embed.add_field(name="Plan", value=summary[:500], inline=False)
    log_embed.add_field(name="Code", value=f"```py\n{code[:_MAX_CODE_DISPLAY]}\n```", inline=False)
    log_embed.add_field(name="Result", value=f"```\n{preview}\n```", inline=False)
    log_embed.add_field(name="Actor", value=f"{ctx.actor.mention} (`{ctx.actor.id}`)", inline=True)

    await _log_execution(ctx, preview, log_embed)
    return ToolResult.ok(f"Done: {preview}\nExecution ID: `{digest[:12]}`.")
