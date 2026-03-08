"""
ModBot Web Dashboard — aiohttp API server
Runs inside the bot process, uses bot.db and bot.guilds for real data.
Serves the Vite dist/ as static files in production.
Render-compatible: reads PORT env var, adds /health endpoint, secure cookies.
"""

import hashlib
import hmac
import inspect
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, get_args, get_origin
from urllib.parse import urlencode

import aiohttp
import discord
from aiohttp import web
from discord import app_commands
from utils.server_setup import (
    apply_verification_gate,
    build_setup_summary,
    hydrate_setup_settings_from_guild,
    quickstart_server,
    sync_setup_aliases,
    sync_staff_role_groups,
)

try:
    from google import genai
    from google.genai import types as genai_types
    from google.genai.errors import APIError
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logger = logging.getLogger("ModBot.Dashboard")

# ─── Configuration ────────────────────────────────────────────────────────────

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")

# Render sets PORT; fall back to DASHBOARD_PORT, then 10547
DASHBOARD_PORT = int(os.getenv("PORT", os.getenv("DASHBOARD_PORT", "10547")))

SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))

# Detect Render environment (Render always sets RENDER=true)
IS_RENDER = os.getenv("RENDER", "").lower() in ("true", "1", "yes")

# Public URL where this API/auth server is exposed (optional override).
# Needed when the app is behind proxies that do not forward host headers.
BACKEND_PUBLIC_URL = os.getenv("DASHBOARD_PUBLIC_URL", "").rstrip("/")

# Public URL where the frontend is hosted (optional).
# If set to a different origin than BACKEND_PUBLIC_URL, auth cookies use SameSite=None.
FRONTEND_PUBLIC_URL = os.getenv("FRONTEND_PUBLIC_URL", os.getenv("RAILWAY_STATIC_URL", "")).rstrip("/")

DISCORD_API = "https://discord.com/api/v10"
DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"

# In-memory session store  {session_id: {user data, access_token, expires_at}}
_sessions: Dict[str, Dict[str, Any]] = {}

# Bot reference (set by start_dashboard)
_bot = None

# Lightweight in-memory sync status per guild
_sync_status: Dict[str, Dict[str, Any]] = {}

_MODULE_ID_ALIASES: Dict[str, str] = {
    "aimoderation": "aimod",
    "ai_moderation": "aimod",
    "ai_mod": "aimod",
    "automodv3": "automod",
    "auto_mod": "automod",
    "auto_moderation": "automod",
    "forummoderation": "forum_moderation",
}

_COG_TO_MODULE_ID: Dict[str, str] = {
    "AIModeration": "aimod",
    "AutoModV3": "automod",
    "AntiRaid": "antiraid",
    "Logging": "logging",
    "Moderation": "moderation",
    "Tickets": "tickets",
    "Verification": "verification",
    "Modmail": "modmail",
    "Whitelist": "whitelist",
    "ForumModeration": "forum_moderation",
}

_MODULE_ENABLED_KEYS: Dict[str, tuple[str, bool]] = {
    "aimod": ("aimod_enabled", True),
    "automod": ("automod_enabled", True),
    "antiraid": ("antiraid_enabled", False),
    "logging": ("logging_enabled", True),
    "tickets": ("tickets_enabled", False),
    "verification": ("verification_enabled", True),
    "modmail": ("modmail_enabled", True),
    "whitelist": ("whitelist_enabled", False),
}

_LOG_EVENT_TYPES: List[Dict[str, str]] = [
    {"id": "message_delete", "name": "Message Deleted", "category": "messages", "description": "A message was deleted", "severity": "info"},
    {"id": "message_edit", "name": "Message Edited", "category": "messages", "description": "A message was edited", "severity": "info"},
    {"id": "message_bulk_delete", "name": "Bulk Delete", "category": "messages", "description": "Messages were bulk deleted", "severity": "warning"},
    {"id": "member_join", "name": "Member Joined", "category": "members", "description": "A member joined the server", "severity": "info"},
    {"id": "member_leave", "name": "Member Left", "category": "members", "description": "A member left the server", "severity": "info"},
    {"id": "member_role_update", "name": "Role Updated", "category": "members", "description": "A member's roles changed", "severity": "info"},
    {"id": "member_nick_update", "name": "Nickname Changed", "category": "members", "description": "A member's nickname changed", "severity": "info"},
    {"id": "user_ban", "name": "User Banned", "category": "moderation", "description": "A user was banned", "severity": "critical"},
    {"id": "user_unban", "name": "User Unbanned", "category": "moderation", "description": "A user was unbanned", "severity": "warning"},
    {"id": "user_kick", "name": "User Kicked", "category": "moderation", "description": "A user was kicked", "severity": "warning"},
    {"id": "user_warn", "name": "User Warned", "category": "moderation", "description": "A user was warned", "severity": "warning"},
    {"id": "user_timeout", "name": "User Timed Out", "category": "moderation", "description": "A user was timed out", "severity": "warning"},
    {"id": "automod_trigger", "name": "Automod Triggered", "category": "automod", "description": "An automod rule triggered", "severity": "warning"},
    {"id": "automod_action", "name": "Automod Action", "category": "automod", "description": "An automod action was taken", "severity": "warning"},
    {"id": "channel_create", "name": "Channel Created", "category": "server", "description": "A channel was created", "severity": "info"},
    {"id": "channel_delete", "name": "Channel Deleted", "category": "server", "description": "A channel was deleted", "severity": "warning"},
    {"id": "role_create", "name": "Role Created", "category": "server", "description": "A role was created", "severity": "info"},
    {"id": "role_delete", "name": "Role Deleted", "category": "server", "description": "A role was deleted", "severity": "warning"},
    {"id": "server_update", "name": "Server Updated", "category": "server", "description": "Server settings changed", "severity": "info"},
    {"id": "voice_join", "name": "Voice Join", "category": "voice", "description": "A member joined voice", "severity": "info"},
    {"id": "voice_leave", "name": "Voice Leave", "category": "voice", "description": "A member left voice", "severity": "info"},
]

_LOG_CATEGORY_TO_SETTING_KEY: Dict[str, str] = {
    "moderation": "mod_log_channel",
    "automod": "automod_log_channel",
    "messages": "message_log_channel",
    "members": "audit_log_channel",
    "server": "audit_log_channel",
    "voice": "voice_log_channel",
}

_LOG_CATEGORY_TO_MODULE_SETTING_KEY: Dict[str, str] = {
    "moderation": "modChannel",
    "automod": "automodChannel",
    "messages": "messageChannel",
    "members": "auditChannel",
    "server": "auditChannel",
    "voice": "voiceChannel",
}

_LOG_SETTING_ALIASES: Dict[str, tuple[str, ...]] = {
    "mod_log_channel": ("mod_log_channel", "log_channel_mod"),
    "audit_log_channel": ("audit_log_channel", "log_channel_audit"),
    "message_log_channel": ("message_log_channel", "log_channel_message"),
    "voice_log_channel": ("voice_log_channel", "log_channel_voice"),
    "automod_log_channel": ("automod_log_channel", "log_channel_automod"),
    "report_log_channel": ("report_log_channel", "log_channel_report"),
    "ticket_log_channel": ("ticket_log_channel", "log_channel_ticket"),
}

_MODULE_CAPABILITY_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "automod": {
        "name": "Auto Moderation",
        "description": "Automatically filter spam, links, invites, and unsafe content.",
        "category": "Moderation",
        "iconHint": "Zap",
        "supportsOverrides": True,
        "settingsSchema": [
            {"key": "antiSpam", "label": "Anti-Spam", "type": "boolean", "defaultValue": True, "section": "Filters"},
            {"key": "spamThreshold", "label": "Spam Threshold", "type": "number", "defaultValue": 5, "constraints": {"min": 0, "max": 25}, "section": "Filters"},
            {"key": "antiLink", "label": "Anti-Link", "type": "boolean", "defaultValue": True, "section": "Filters"},
            {"key": "antiInvite", "label": "Anti-Invite", "type": "boolean", "defaultValue": True, "section": "Filters"},
            {"key": "mentionLimit", "label": "Mention Limit", "type": "number", "defaultValue": 5, "constraints": {"min": 0, "max": 50}, "section": "Content"},
            {"key": "capsThreshold", "label": "Max Caps %", "type": "number", "defaultValue": 70, "constraints": {"min": 0, "max": 100}, "section": "Content"},
            {"key": "action", "label": "Default Action", "type": "select", "defaultValue": "warn", "constraints": {"options": [{"label": "Warn", "value": "warn"}, {"label": "Delete", "value": "delete"}, {"label": "Timeout", "value": "timeout"}, {"label": "Kick", "value": "kick"}, {"label": "Ban", "value": "ban"}, {"label": "Quarantine", "value": "quarantine"}]}, "section": "Actions"},
            {"key": "notifyUsers", "label": "Notify Users", "type": "boolean", "defaultValue": True, "section": "Actions"},
            {"key": "muteDuration", "label": "Timeout Duration", "type": "duration", "defaultValue": 3600, "constraints": {"min": 1, "max": 2419200}, "section": "Actions", "advanced": True},
            {"key": "bannedWords", "label": "Banned Words", "type": "stringList", "defaultValue": [], "section": "Content", "advanced": True},
            {"key": "linkWhitelist", "label": "Allowed Domains", "type": "stringList", "defaultValue": [], "section": "Filters", "advanced": True},
            {"key": "aiEnabled", "label": "AI Checks", "type": "boolean", "defaultValue": False, "section": "AI", "advanced": True},
            {"key": "aiMinSeverity", "label": "AI Min Severity", "type": "number", "defaultValue": 4, "constraints": {"min": 0, "max": 10}, "section": "AI", "advanced": True},
            {"key": "scamProtection", "label": "Scam Protection", "type": "boolean", "defaultValue": True, "section": "AI", "advanced": True},
        ],
    },
    "antiraid": {
        "name": "Anti-Raid",
        "description": "Detect mass joins and apply automatic raid responses.",
        "category": "Protection",
        "iconHint": "ShieldAlert",
        "supportsOverrides": False,
        "settingsSchema": [
            {"key": "joinThreshold", "label": "Join Threshold", "type": "number", "defaultValue": 10, "constraints": {"min": 2, "max": 50}, "section": "Detection"},
            {"key": "timeWindow", "label": "Time Window (seconds)", "type": "number", "defaultValue": 10, "constraints": {"min": 1, "max": 120}, "section": "Detection"},
            {"key": "cooldownSeconds", "label": "Cooldown (seconds)", "type": "number", "defaultValue": 60, "constraints": {"min": 5, "max": 600}, "section": "Detection"},
            {"key": "action", "label": "Response Action", "type": "select", "defaultValue": "kick", "constraints": {"options": [{"label": "Kick", "value": "kick"}, {"label": "Ban", "value": "ban"}, {"label": "Lockdown", "value": "lockdown"}, {"label": "Quarantine", "value": "quarantine"}]}, "section": "Response"},
            {"key": "lockdownEnabled", "label": "Lockdown Mode", "type": "boolean", "defaultValue": False, "section": "Response"},
            {"key": "kickNewAccounts", "label": "Kick New Accounts", "type": "boolean", "defaultValue": False, "section": "Response"},
            {"key": "accountAgeHours", "label": "Min Account Age (hours)", "type": "number", "defaultValue": 24, "constraints": {"min": 1, "max": 720}, "section": "Response", "advanced": True},
            {"key": "quarantineRoleId", "label": "Quarantine Role", "type": "rolePicker", "defaultValue": "", "section": "Response", "advanced": True},
            {"key": "aiEnabled", "label": "AI Detection", "type": "boolean", "defaultValue": False, "section": "AI", "advanced": True},
            {"key": "aiMinConfidence", "label": "AI Min Confidence", "type": "number", "defaultValue": 70, "constraints": {"min": 0, "max": 100}, "section": "AI", "advanced": True},
            {"key": "aiOverrideAction", "label": "AI Overrides Action", "type": "boolean", "defaultValue": False, "section": "AI", "advanced": True},
            {"key": "raidMode", "label": "Manual Raid Mode", "type": "boolean", "defaultValue": False, "section": "AI", "advanced": True},
        ],
    },
    "aimod": {
        "name": "AI Moderation",
        "description": "Mention router with configurable tools, confirmations, and model behavior.",
        "category": "Moderation",
        "iconHint": "Shield",
        "supportsOverrides": True,
        "settingsSchema": [
            {"key": "model", "label": "Model", "type": "string", "defaultValue": "", "section": "Core"},
            {"key": "contextMessages", "label": "Context Messages", "type": "number", "defaultValue": 15, "constraints": {"min": 1, "max": 50}, "section": "Core"},
            {"key": "proactiveChance", "label": "Proactive Chance", "type": "number", "defaultValue": 0.02, "constraints": {"min": 0, "max": 1}, "section": "Core"},
            {"key": "confirmEnabled", "label": "Confirm High-Impact Actions", "type": "boolean", "defaultValue": True, "section": "Confirmations"},
            {"key": "confirmTimeoutSeconds", "label": "Confirmation Timeout", "type": "duration", "defaultValue": 25, "constraints": {"min": 5, "max": 120}, "section": "Confirmations"},
            {"key": "confirmActions", "label": "Confirmed Actions", "type": "stringList", "defaultValue": ["ban_member", "kick_member", "quarantine_member"], "section": "Confirmations"},
            {"key": "confirmationChannel", "label": "Confirmation Channel", "type": "channelPicker", "defaultValue": "", "section": "Confirmations", "advanced": True},
        ],
    },
    "logging": {
        "name": "Logging",
        "description": "Route moderation and server events to dedicated log channels.",
        "category": "Utility",
        "iconHint": "ScrollText",
        "supportsOverrides": False,
        "settingsSchema": [
            {"key": "modChannel", "label": "Moderation Log Channel", "type": "channelPicker", "defaultValue": "", "section": "Channels"},
            {"key": "auditChannel", "label": "Audit Log Channel", "type": "channelPicker", "defaultValue": "", "section": "Channels"},
            {"key": "messageChannel", "label": "Message Log Channel", "type": "channelPicker", "defaultValue": "", "section": "Channels"},
            {"key": "voiceChannel", "label": "Voice Log Channel", "type": "channelPicker", "defaultValue": "", "section": "Channels"},
            {"key": "automodChannel", "label": "AutoMod Log Channel", "type": "channelPicker", "defaultValue": "", "section": "Channels"},
            {"key": "reportChannel", "label": "Report Log Channel", "type": "channelPicker", "defaultValue": "", "section": "Channels"},
            {"key": "ticketChannel", "label": "Ticket Log Channel", "type": "channelPicker", "defaultValue": "", "section": "Channels"},
        ],
    },
    "tickets": {
        "name": "Tickets",
        "description": "Ticket panel, close flow, logs, and support role routing.",
        "category": "Support",
        "iconHint": "Ticket",
        "supportsOverrides": True,
        "settingsSchema": [
            {"key": "category", "label": "Ticket Category", "type": "channelPicker", "defaultValue": "", "section": "Routing"},
            {"key": "supportRole", "label": "Support Role", "type": "rolePicker", "defaultValue": "", "section": "Routing"},
            {"key": "modRole", "label": "Mod Role", "type": "rolePicker", "defaultValue": "", "section": "Routing", "advanced": True},
            {"key": "adminRole", "label": "Admin Role", "type": "rolePicker", "defaultValue": "", "section": "Routing", "advanced": True},
            {"key": "managerRole", "label": "Manager Role", "type": "rolePicker", "defaultValue": "", "section": "Routing", "advanced": True},
            {"key": "logChannel", "label": "Ticket Log Channel", "type": "channelPicker", "defaultValue": "", "section": "Routing"},
        ],
    },
    "verification": {
        "name": "Verification",
        "description": "Configure verification roles and optional voice verification flow.",
        "category": "Protection",
        "iconHint": "UserCheck",
        "supportsOverrides": False,
        "settingsSchema": [
            {"key": "verifyChannel", "label": "Verification Channel", "type": "channelPicker", "defaultValue": "", "section": "Core"},
            {"key": "verifyLogChannel", "label": "Verification Log Channel", "type": "channelPicker", "defaultValue": "", "section": "Core"},
            {"key": "verifiedRole", "label": "Verified Role", "type": "rolePicker", "defaultValue": "", "section": "Core"},
            {"key": "unverifiedRole", "label": "Unverified Role", "type": "rolePicker", "defaultValue": "", "section": "Core"},
            {"key": "voiceGateEnabled", "label": "Voice Verification", "type": "boolean", "defaultValue": False, "section": "Voice"},
            {"key": "waitingVoiceChannel", "label": "Waiting Voice Channel", "type": "channelPicker", "defaultValue": "", "section": "Voice", "advanced": True},
            {"key": "voiceSessionTtl", "label": "Voice Session TTL", "type": "duration", "defaultValue": 180, "constraints": {"min": 30, "max": 86400}, "section": "Voice", "advanced": True},
            {"key": "bypassRoles", "label": "Voice Bypass Roles", "type": "stringList", "defaultValue": [], "section": "Voice", "advanced": True},
        ],
    },
    "modmail": {
        "name": "Modmail",
        "description": "Ticket-style DM bridge between users and staff.",
        "category": "Support",
        "iconHint": "Ticket",
        "supportsOverrides": False,
        "settingsSchema": [
            {"key": "categoryId", "label": "Modmail Category", "type": "channelPicker", "defaultValue": "", "section": "Routing"},
            {"key": "logChannel", "label": "Modmail Log Channel", "type": "channelPicker", "defaultValue": "", "section": "Routing"},
        ],
    },
    "whitelist": {
        "name": "Whitelist",
        "description": "Allowlist-only server access with join protections.",
        "category": "Protection",
        "iconHint": "Shield",
        "supportsOverrides": False,
        "settingsSchema": [
            {"key": "immunity", "label": "Admin Immunity", "type": "boolean", "defaultValue": True, "section": "Behavior"},
            {"key": "dmOnKick", "label": "DM On Kick", "type": "boolean", "defaultValue": True, "section": "Behavior"},
        ],
    },
    "forum_moderation": {
        "name": "Forum Moderation",
        "description": "Moderate forum posts and route flagged content alerts.",
        "category": "Moderation",
        "iconHint": "ShieldAlert",
        "supportsOverrides": False,
        "settingsSchema": [
            {"key": "alertsChannel", "label": "Forum Alerts Channel", "type": "channelPicker", "defaultValue": "", "section": "Routing"},
        ],
    },
}


# ─── Session Helpers ──────────────────────────────────────────────────────────

def _make_session_id() -> str:
    return secrets.token_urlsafe(48)


def _sign_session(session_id: str) -> str:
    sig = hmac.new(SESSION_SECRET.encode(), session_id.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{session_id}.{sig}"


def _verify_session(cookie: str) -> Optional[str]:
    if "." not in cookie:
        return None
    session_id, sig = cookie.rsplit(".", 1)
    expected = hmac.new(SESSION_SECRET.encode(), session_id.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(sig, expected):
        return None
    return session_id


def _get_session(request: web.Request) -> Optional[Dict[str, Any]]:
    cookie = request.cookies.get("modbot_session")
    if not cookie:
        return None
    session_id = _verify_session(cookie)
    if not session_id:
        return None
    session = _sessions.get(session_id)
    if not session:
        return None
    if session.get("expires_at", 0) < time.time():
        _sessions.pop(session_id, None)
        return None
    return session


def _require_auth(request: web.Request) -> Dict[str, Any]:
    session = _get_session(request)
    if not session:
        raise web.HTTPUnauthorized(text=json.dumps({"code": 401, "message": "Not authenticated"}),
                                    content_type="application/json")
    return session


def _user_can_manage_guild(session: Dict[str, Any], guild_id: str) -> bool:
    """Check if the user has manage_guild permission or is owner."""
    for g in session.get("guilds", []):
        if str(g["id"]) == str(guild_id):
            permissions = int(g.get("permissions", 0))
            # MANAGE_GUILD = 0x20, ADMINISTRATOR = 0x8
            if permissions & 0x20 or permissions & 0x8 or g.get("owner"):
                return True
    return False


def _require_guild_access(session: Dict[str, Any], guild_id: str):
    if not _user_can_manage_guild(session, guild_id):
        raise web.HTTPForbidden(text=json.dumps({"code": 403, "message": "No access to this guild"}),
                                 content_type="application/json")


def _normalize_module_id(module_id: Any) -> str:
    raw = str(module_id or "").strip().lower().replace("-", "_").replace(" ", "_")
    return _MODULE_ID_ALIASES.get(raw, raw)


def _canonicalize_modules_blob(raw_modules: Any) -> Dict[str, Dict[str, Any]]:
    if not isinstance(raw_modules, dict):
        return {}
    canonical: Dict[str, Dict[str, Any]] = {}
    for key, value in raw_modules.items():
        module_id = _normalize_module_id(key)
        if not isinstance(value, dict):
            continue
        current = canonical.get(module_id, {})
        merged = dict(current)
        merged.update(value)
        current_settings = current.get("settings")
        value_settings = value.get("settings")
        if isinstance(current_settings, dict) and isinstance(value_settings, dict):
            merged["settings"] = {**current_settings, **value_settings}
        current_overrides = current.get("overrides")
        value_overrides = value.get("overrides")
        if isinstance(current_overrides, dict) and isinstance(value_overrides, dict):
            merged["overrides"] = {**current_overrides, **value_overrides}
        canonical[module_id] = merged
    return canonical


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on", "enabled"}:
            return True
        if lowered in {"0", "false", "no", "off", "disabled"}:
            return False
    return default


def _coerce_text_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    items: List[str] = []
    for item in value:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            items.append(text)
    return items


def _coerce_channel_like(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


_DASHBOARD_ROLE_CAPABILITIES: Dict[str, List[str]] = {
    "owner": [
        "view_dashboard", "view_commands", "manage_commands", "view_modules", "manage_modules",
        "view_logging", "manage_logging", "view_cases", "manage_cases", "view_automod",
        "manage_automod", "manage_permissions", "export_data", "danger_zone_actions",
        "run_sync_operations", "view_audit",
    ],
    "admin": [
        "view_dashboard", "view_commands", "manage_commands", "view_modules", "manage_modules",
        "view_logging", "manage_logging", "view_cases", "manage_cases", "view_automod",
        "manage_automod", "export_data", "run_sync_operations", "view_audit",
    ],
    "moderator": [
        "view_dashboard", "view_commands", "view_modules", "view_logging",
        "view_cases", "manage_cases", "view_automod", "view_audit",
    ],
    "viewer": ["view_dashboard", "view_commands", "view_modules", "view_logging", "view_cases"],
}


def _normalize_dashboard_role(value: Any) -> Optional[str]:
    role = str(value or "").strip().lower()
    if role in _DASHBOARD_ROLE_CAPABILITIES:
        return role
    return None


def _normalize_dashboard_capabilities(role: str, raw_caps: Any) -> List[str]:
    defaults = list(_DASHBOARD_ROLE_CAPABILITIES.get(role, []))
    if not isinstance(raw_caps, list):
        return defaults
    valid = [str(cap) for cap in raw_caps if isinstance(cap, str) and cap in _DASHBOARD_ROLE_CAPABILITIES["owner"]]
    return valid or defaults


def _normalize_dashboard_role_mappings(raw_mappings: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_mappings, list):
        return []
    normalized: List[Dict[str, Any]] = []
    seen_role_ids: set[str] = set()
    for entry in raw_mappings:
        if not isinstance(entry, dict):
            continue
        role_id = _coerce_channel_like(entry.get("roleId"))
        dashboard_role = _normalize_dashboard_role(entry.get("dashboardRole"))
        if not role_id or not dashboard_role or role_id in seen_role_ids:
            continue
        seen_role_ids.add(role_id)
        normalized.append({
            "roleId": role_id,
            "dashboardRole": dashboard_role,
            "capabilities": _normalize_dashboard_capabilities(dashboard_role, entry.get("capabilities")),
        })
    return normalized


def _normalize_dashboard_user_overrides(raw_overrides: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_overrides, list):
        return []
    normalized: List[Dict[str, Any]] = []
    seen_user_ids: set[str] = set()
    for entry in raw_overrides:
        if not isinstance(entry, dict):
            continue
        user_id = _coerce_channel_like(entry.get("userId"))
        dashboard_role = _normalize_dashboard_role(entry.get("dashboardRole"))
        if not user_id or not dashboard_role or user_id in seen_user_ids:
            continue
        seen_user_ids.add(user_id)
        normalized.append({
            "userId": user_id,
            "dashboardRole": dashboard_role,
            "capabilities": _normalize_dashboard_capabilities(dashboard_role, entry.get("capabilities")),
        })
    return normalized


def _derived_dashboard_role_mappings(settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    derived_pairs = (
        ("owner_role", "owner"),
        ("manager_role", "admin"),
        ("admin_role", "admin"),
        ("supervisor_role", "moderator"),
        ("senior_mod_role", "moderator"),
        ("mod_role", "moderator"),
        ("trial_mod_role", "moderator"),
        ("staff_role", "moderator"),
    )
    mappings: List[Dict[str, Any]] = []
    seen_role_ids: set[str] = set()
    for setting_key, dashboard_role in derived_pairs:
        role_id = _coerce_channel_like(settings.get(setting_key))
        if not role_id or role_id in seen_role_ids:
            continue
        seen_role_ids.add(role_id)
        mappings.append({
            "roleId": role_id,
            "dashboardRole": dashboard_role,
            "capabilities": list(_DASHBOARD_ROLE_CAPABILITIES[dashboard_role]),
        })
    return mappings


def _effective_dashboard_permissions(settings: Dict[str, Any]) -> Dict[str, Any]:
    explicit_mappings = _normalize_dashboard_role_mappings(settings.get("dashboardRoleMappings", []))
    overrides = _normalize_dashboard_user_overrides(settings.get("dashboardUserOverrides", []))
    configured = _coerce_bool(settings.get("dashboardPermissionsConfigured"), False)
    role_mappings = explicit_mappings if (configured or explicit_mappings) else _derived_dashboard_role_mappings(settings)
    return {
        "dashboardRoleMappings": role_mappings,
        "roleMappings": role_mappings,
        "userOverrides": overrides,
    }


def _get_log_setting(settings: Dict[str, Any], canonical_key: str) -> Optional[str]:
    for key in _LOG_SETTING_ALIASES.get(canonical_key, (canonical_key,)):
        value = _coerce_channel_like(settings.get(key))
        if value:
            return value
    return None


def _request_origin(request: web.Request) -> str:
    """Build request origin from proxy-aware headers."""
    proto = request.headers.get("X-Forwarded-Proto", request.scheme or "http")
    host = request.headers.get("X-Forwarded-Host", request.headers.get("Host", request.host))
    scheme = proto.split(",")[0].strip() or "http"
    authority = host.split(",")[0].strip() or request.host
    return f"{scheme}://{authority}".rstrip("/")


def _dashboard_base_url(request: web.Request) -> str:
    return BACKEND_PUBLIC_URL or _request_origin(request)


def _frontend_base_url(request: web.Request) -> str:
    return FRONTEND_PUBLIC_URL or _dashboard_base_url(request)


def _is_cross_origin_frontend(request: web.Request) -> bool:
    return _frontend_base_url(request).lower() != _dashboard_base_url(request).lower()


def _session_cookie_settings(request: web.Request) -> Dict[str, Any]:
    default_same_site = "None" if _is_cross_origin_frontend(request) else "Lax"
    configured_same_site = os.getenv("SESSION_COOKIE_SAMESITE", "").strip().capitalize()
    same_site = configured_same_site if configured_same_site in {"Lax", "Strict", "None"} else default_same_site

    secure_default = (
        same_site == "None"
        or _dashboard_base_url(request).startswith("https://")
        or IS_RENDER
        or bool(os.getenv("RAILWAY_ENVIRONMENT"))
    )
    secure = _coerce_bool(os.getenv("SESSION_COOKIE_SECURE"), secure_default)
    if same_site == "None":
        secure = True

    return {"samesite": same_site, "secure": secure}


# ─── Health Check ─────────────────────────────────────────────────────────────

async def health_check(request: web.Request):
    """Health check endpoint for Render."""
    bot_ready = _bot is not None and _bot.is_ready()
    return web.json_response({
        "status": "ok",
        "botReady": bot_ready,
    })


# ─── OAuth2 Routes ────────────────────────────────────────────────────────────

async def auth_login(request: web.Request):
    """Redirect to Discord OAuth2."""
    redirect = f"{_dashboard_base_url(request)}/auth/callback"

    # /auth/invite adds bot scopes so Discord returns through our callback and
    # then back into the dashboard instead of leaving users on a Discord page.
    include_bot_scopes = request.path.endswith("/auth/invite") or _coerce_bool(request.query.get("bot"), False)
    scopes = ["identify", "guilds"]
    if include_bot_scopes:
        scopes.extend(["bot", "applications.commands"])

    params: Dict[str, str] = {
        "client_id": CLIENT_ID,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": " ".join(scopes),
    }

    if include_bot_scopes:
        guild_id = str(request.query.get("guild_id", "")).strip()
        if guild_id.isdigit():
            params["guild_id"] = guild_id
            params["disable_guild_select"] = "true"

    oauth_url = f"{DISCORD_OAUTH_URL}?{urlencode(params)}"
    raise web.HTTPFound(oauth_url)


async def auth_callback(request: web.Request):
    """Handle Discord OAuth2 callback — exchange code, fetch user, create session."""
    code = request.query.get("code")
    error = request.query.get("error")

    frontend_base_url = _frontend_base_url(request)

    if error:
        raise web.HTTPFound(f"{frontend_base_url}/?error={error}")

    if not code:
        raise web.HTTPFound(f"{frontend_base_url}/?error=no_code")

    # Exchange code for tokens
    redirect = f"{_dashboard_base_url(request)}/auth/callback"
    
    async with aiohttp.ClientSession() as http:
        token_resp = await http.post(DISCORD_TOKEN_URL, data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})

        if token_resp.status != 200:
            err_text = await token_resp.text()
            logger.error(f"Token exchange failed: {err_text}")
            return web.Response(
                text=f"Discord OAuth2 Token Exchange Failed (Status {token_resp.status}):\n\n{err_text}\n\nClient ID: {CLIENT_ID}\nRedirect URI Used: {redirect}\nDid you forget to set DISCORD_CLIENT_SECRET in Railway?", 
                content_type="text/plain"
            )

        tokens = await token_resp.json()
        access_token = tokens["access_token"]
        expires_in = tokens.get("expires_in", 604800)

        # Fetch user info
        user_resp = await http.get(f"{DISCORD_API}/users/@me", headers={
            "Authorization": f"Bearer {access_token}"
        })
        user_data = await user_resp.json()

        # Fetch user guilds
        guilds_resp = await http.get(f"{DISCORD_API}/users/@me/guilds", headers={
            "Authorization": f"Bearer {access_token}"
        })
        guilds_data = await guilds_resp.json()

    # Create session
    session_id = _make_session_id()
    _sessions[session_id] = {
        "user": {
            "id": user_data["id"],
            "username": user_data["username"],
            "discriminator": user_data.get("discriminator", "0"),
            "avatar": user_data.get("avatar"),
            "global_name": user_data.get("global_name"),
        },
        "guilds": guilds_data,
        "access_token": access_token,
        "expires_at": time.time() + expires_in,
    }

    # Set cookie and redirect to dashboard
    signed = _sign_session(session_id)
    cookie_settings = _session_cookie_settings(request)
    response = web.HTTPFound(f"{frontend_base_url}/dashboard")
    response.set_cookie(
        "modbot_session",
        signed,
        max_age=expires_in,
        httponly=True,
        path="/",
        secure=cookie_settings["secure"],
        samesite=cookie_settings["samesite"],
    )
    raise response


async def auth_logout(request: web.Request):
    """Clear session."""
    cookie = request.cookies.get("modbot_session")
    if cookie:
        session_id = _verify_session(cookie)
        if session_id:
            _sessions.pop(session_id, None)

    response = web.json_response({"ok": True})
    response.del_cookie("modbot_session", path="/")
    return response


# ─── API Routes ───────────────────────────────────────────────────────────────

async def api_me(request: web.Request):
    """Return authenticated user info + their guilds where bot is installed."""
    session = _require_auth(request)
    user = session["user"]
    guilds = _build_accessible_guild_summaries(session)

    avatar = user.get("avatar")
    avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar}.png" if avatar else None

    return web.json_response({
        "id": user["id"],
        "username": user["username"],
        "discriminator": user.get("discriminator", "0"),
        "avatar": avatar_url,
        "globalName": user.get("global_name"),
        "guilds": guilds,
    })


def _build_accessible_guild_summaries(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    user_guilds = session.get("guilds", [])
    bot_guild_ids = {str(g.id) for g in _bot.guilds} if _bot else set()

    guilds: List[Dict[str, Any]] = []
    for g in user_guilds:
        owner = bool(g.get("owner"))
        permissions = int(g.get("permissions", 0))
        has_manage = bool(permissions & 0x20 or permissions & 0x8 or owner)
        bot_installed = str(g["id"]) in bot_guild_ids

        if has_manage or bot_installed:
            icon = g.get("icon")
            icon_url = f"https://cdn.discordapp.com/icons/{g['id']}/{icon}.png" if icon else None
            guilds.append({
                "id": str(g["id"]),
                "name": g["name"],
                "icon": icon_url,
                "owner": owner,
                "memberCount": _get_guild_member_count(str(g["id"])),
                "botInstalled": bot_installed,
                "canManage": has_manage,
            })
    return guilds


async def api_guilds(request: web.Request):
    """Return guilds available to the authenticated user."""
    session = _require_auth(request)
    return web.json_response(_build_accessible_guild_summaries(session))


async def api_guild_summary(request: web.Request):
    """Return a single guild summary for the authenticated user."""
    session = _require_auth(request)
    guild_id = str(request.match_info["guild_id"])
    for guild in _build_accessible_guild_summaries(session):
        if guild["id"] == guild_id:
            return web.json_response(guild)

    raise web.HTTPNotFound(
        text=json.dumps({"code": 404, "message": "Guild not found"}),
        content_type="application/json",
    )


def _get_guild_member_count(guild_id: str) -> int:
    if not _bot:
        return 0
    guild = _bot.get_guild(int(guild_id))
    if not guild:
        return 0

    member_count = getattr(guild, "member_count", None)
    if isinstance(member_count, int) and member_count >= 0:
        return member_count

    # Fallback for guilds where Discord did not provide member_count.
    try:
        return len(getattr(guild, "members", []) or [])
    except Exception:
        return 0


async def api_guild_channels(request: web.Request):
    """Return Discord channels for a guild from the bot's cache."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    guild = _bot.get_guild(int(guild_id)) if _bot else None
    if not guild:
        raise web.HTTPNotFound(text=json.dumps({"code": 404, "message": "Guild not found"}),
                                content_type="application/json")

    channels = []
    for ch in guild.channels:
        channels.append({
            "id": str(ch.id),
            "name": ch.name,
            "type": ch.type.value,
            "position": ch.position,
            "parentId": str(ch.category_id) if ch.category_id else None,
        })

    return web.json_response(sorted(channels, key=lambda c: c["position"]))


async def api_guild_roles(request: web.Request):
    """Return Discord roles for a guild from the bot's cache."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    guild = _bot.get_guild(int(guild_id)) if _bot else None
    if not guild:
        raise web.HTTPNotFound(text=json.dumps({"code": 404, "message": "Guild not found"}),
                                content_type="application/json")

    roles = []
    for role in guild.roles:
        if role.is_default():
            continue
        roles.append({
            "id": str(role.id),
            "name": role.name,
            "color": role.color.value,
            "position": role.position,
            "managed": role.managed,
            "permissions": str(role.permissions.value),
        })

    return web.json_response(sorted(roles, key=lambda r: -r["position"]))


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _normalize_case_action(action: Any) -> str:
    """Normalize raw case actions from DB into dashboard action IDs."""
    raw = str(action or "").strip().lower()
    if raw in {"warn", "warning"}:
        return "warn"
    if raw in {"mute", "muted", "timeout"}:
        return "timeout"
    if raw in {"kick", "kicked"}:
        return "kick"
    if raw in {"ban", "banned", "tempban", "softban"}:
        return "ban"
    if raw in {"unban", "unbanned"}:
        return "unban"
    if raw in {"quarantine", "quarantined"}:
        return "quarantine"
    return "note"


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _default_override_entry() -> Dict[str, Any]:
    return {
        "allowedChannels": [],
        "ignoredChannels": [],
        "allowedRoles": [],
        "ignoredRoles": [],
        "allowedUsers": [],
        "ignoredUsers": [],
    }


def _default_command_config(default_permission: str = "send_messages") -> Dict[str, Any]:
    return {
        "enabled": True,
        "requiredPermission": default_permission,
        "minimumStaffLevel": "everyone",
        "enforceRoleHierarchy": False,
        "requireReason": False,
        "requireConfirmation": False,
        "channelMode": "enabled_everywhere",
        "disableInThreads": False,
        "disableInForumPosts": False,
        "disableInDMs": False,
        "overrides": _default_override_entry(),
        "cooldown": {
            "global": 0,
            "perUser": 0,
            "perGuild": 0,
            "perChannel": 0,
        },
        "rateLimit": {
            "maxPerMinute": 0,
            "maxPerHour": 0,
            "concurrentLimit": 1,
            "maxPerMinuteChannel": 30,
            "maxPerMinuteGuild": 300,
        },
        "cooldownBypassRoles": [],
        "cooldownBypassUsers": [],
        "logging": {
            "logUsage": True,
            "routeOverride": None,
            "recordToAuditLog": True,
        },
        "visibility": {
            "hideFromHelp": False,
            "slashEnabled": True,
            "prefixEnabled": True,
            "hideFromAutocomplete": False,
            "defaultResponseVisibility": "auto",
        },
        "disableDuringMaintenanceMode": False,
        "disableDuringRaidMode": False,
        "syncWithDiscordSlashPermissions": False,
        "defaultMemberPermissions": "",
        "extras": {},
    }


def _all_runtime_command_names() -> set[str]:
    names: set[str] = set()
    if not _bot:
        return names

    for cmd in _bot.tree.get_commands():
        name = str(getattr(cmd, "name", "") or "").strip()
        if name:
            names.add(name)

    for cmd in _bot.commands:
        if getattr(cmd, "hidden", False):
            continue
        name = str(getattr(cmd, "name", "") or "").strip()
        if name:
            names.add(name)

    return names


def _normalize_single_command_config(command_name: str, value: Any) -> Dict[str, Any]:
    category = _guess_command_category(command_name)
    default_permission = "manage_guild" if category == "Admin" else ("moderate_members" if category == "Moderation" else "send_messages")
    defaults = _default_command_config(default_permission)
    if not isinstance(value, dict):
        return defaults

    merged = {**defaults, **value}

    overrides = value.get("overrides", {})
    merged["overrides"] = {**defaults["overrides"], **(overrides if isinstance(overrides, dict) else {})}

    cooldown = value.get("cooldown", {})
    merged["cooldown"] = {**defaults["cooldown"], **(cooldown if isinstance(cooldown, dict) else {})}

    rate_limit = value.get("rateLimit", {})
    merged["rateLimit"] = {**defaults["rateLimit"], **(rate_limit if isinstance(rate_limit, dict) else {})}

    logging_blob = value.get("logging", {})
    merged["logging"] = {**defaults["logging"], **(logging_blob if isinstance(logging_blob, dict) else {})}

    visibility = value.get("visibility", {})
    merged["visibility"] = {**defaults["visibility"], **(visibility if isinstance(visibility, dict) else {})}

    extras = value.get("extras", {})
    merged["extras"] = extras if isinstance(extras, dict) else {}

    return merged


def _normalize_command_configs_blob(raw_commands: Any) -> Dict[str, Any]:
    source = raw_commands if isinstance(raw_commands, dict) else {}
    normalized: Dict[str, Any] = {}

    for key, value in source.items():
        name = str(key or "").strip()
        if not name:
            continue
        normalized[name] = _normalize_single_command_config(name, value)

    for command_name in _all_runtime_command_names():
        if command_name not in normalized:
            normalized[command_name] = _normalize_single_command_config(command_name, {})

    return normalized


def _module_enabled_from_settings(module_id: str, settings: Dict[str, Any], base: Dict[str, Any]) -> bool:
    flat = _MODULE_ENABLED_KEYS.get(module_id)
    if flat:
        setting_key, default = flat
        return _coerce_bool(settings.get(setting_key), default)
    return _coerce_bool(base.get("enabled"), True)


def _safe_module_base(modules: Dict[str, Any], module_id: str) -> Dict[str, Any]:
    base = modules.get(module_id, {})
    return base if isinstance(base, dict) else {}


def _safe_module_settings(base: Dict[str, Any]) -> Dict[str, Any]:
    raw = base.get("settings", {})
    return dict(raw) if isinstance(raw, dict) else {}


def _safe_module_overrides(base: Dict[str, Any]) -> Dict[str, Any]:
    raw = base.get("overrides", _default_override_entry())
    return raw if isinstance(raw, dict) else _default_override_entry()


def _set_module(
    modules: Dict[str, Any],
    module_id: str,
    *,
    enabled: bool,
    settings_blob: Dict[str, Any],
    base: Dict[str, Any],
) -> None:
    modules[module_id] = {
        "enabled": enabled,
        "settings": settings_blob,
        "overrides": _safe_module_overrides(base),
        "loggingRouteOverride": base.get("loggingRouteOverride"),
    }


def _build_dashboard_logging(settings: Dict[str, Any]) -> Dict[str, Any]:
    stored = settings.get("logging", {})
    if not isinstance(stored, dict):
        stored = {}

    modules = _canonicalize_modules_blob(settings.get("modules", {}))
    logging_module = modules.get("logging", {})
    module_logging_settings = {}
    if isinstance(logging_module, dict):
        raw_settings = logging_module.get("settings", {})
        if isinstance(raw_settings, dict):
            module_logging_settings = raw_settings

    def resolve_channel_for_category(category: str) -> Optional[str]:
        setting_key = _LOG_CATEGORY_TO_SETTING_KEY.get(category)
        if setting_key:
            via_flat = _get_log_setting(settings, setting_key)
            if via_flat:
                return via_flat
        module_key = _LOG_CATEGORY_TO_MODULE_SETTING_KEY.get(category)
        if module_key:
            via_module = _coerce_channel_like(module_logging_settings.get(module_key))
            if via_module:
                return via_module
        return None

    any_configured_category_channel = any(
        resolve_channel_for_category(category)
        for category in _LOG_CATEGORY_TO_SETTING_KEY.keys()
    )

    logging_blob: Dict[str, Any] = {}
    known_event_ids = {event["id"] for event in _LOG_EVENT_TYPES}

    for event in _LOG_EVENT_TYPES:
        event_id = event["id"]
        category = event["category"]
        current = stored.get(event_id, {})
        if not isinstance(current, dict):
            current = {}

        channel_id = _coerce_channel_like(current.get("channelId"))
        if not channel_id:
            channel_id = resolve_channel_for_category(category)
        enabled_default = bool(channel_id) or _coerce_bool(settings.get("logging_enabled"), True)
        enabled = _coerce_bool(current.get("enabled"), enabled_default)
        fmt = "compact" if str(current.get("format", "detailed")).lower() == "compact" else "detailed"
        logging_blob[event_id] = {
            "eventTypeId": event_id,
            "enabled": enabled,
            "channelId": channel_id,
            "format": fmt,
        }

    for event_id, value in stored.items():
        if event_id in known_event_ids or not isinstance(value, dict):
            continue
        channel_id = _coerce_channel_like(value.get("channelId"))
        enabled_default = bool(channel_id) or _coerce_bool(settings.get("logging_enabled"), True)
        enabled = _coerce_bool(value.get("enabled"), enabled_default)
        fmt = "compact" if str(value.get("format", "detailed")).lower() == "compact" else "detailed"
        logging_blob[event_id] = {
            "eventTypeId": str(event_id),
            "enabled": enabled,
            "channelId": channel_id,
            "format": fmt,
        }

    # Backward-compatibility recovery: if channels exist but all events ended up disabled
    # from legacy defaults, surface them as enabled in dashboard UI.
    if logging_blob and any_configured_category_channel and not any(
        _coerce_bool(entry.get("enabled"), False) for entry in logging_blob.values() if isinstance(entry, dict)
    ):
        for entry in logging_blob.values():
            if isinstance(entry, dict):
                entry["enabled"] = True

    return logging_blob


def _apply_dashboard_logging_to_flat_settings(settings: Dict[str, Any], logging_blob: Dict[str, Any]) -> None:
    if not isinstance(logging_blob, dict):
        return

    channels_by_category: Dict[str, Optional[str]] = {}
    any_enabled = False

    for event in _LOG_EVENT_TYPES:
        event_id = event["id"]
        category = event["category"]
        current = logging_blob.get(event_id, {})
        if not isinstance(current, dict):
            continue
        enabled = _coerce_bool(current.get("enabled"), False)
        if not enabled:
            continue
        any_enabled = True
        if category in channels_by_category and channels_by_category.get(category):
            continue
        channel_id = _coerce_channel_like(current.get("channelId"))
        if channel_id:
            channels_by_category[category] = channel_id

    for category, setting_key in _LOG_CATEGORY_TO_SETTING_KEY.items():
        selected = channels_by_category.get(category)
        for alias in _LOG_SETTING_ALIASES.get(setting_key, (setting_key,)):
            settings[alias] = selected

    settings["logging_enabled"] = any_enabled


def _build_dashboard_modules(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Build dashboard modules map using canonical IDs and flat-key bridges."""
    sync_setup_aliases(settings)
    modules = _canonicalize_modules_blob(settings.get("modules", {}))

    # AutoMod
    automod_base = _safe_module_base(modules, "automod")
    automod_base_settings = _safe_module_settings(automod_base)
    automod_action = str(settings.get("automod_punishment", "warn")).lower()
    if automod_action == "mute":
        automod_action = "timeout"
    spam_threshold = max(0, _to_int(settings.get("automod_spam_threshold", 5), 5))
    automod_settings = {
        **automod_base_settings,
        "antiSpam": spam_threshold > 0,
        "antiLink": _coerce_bool(settings.get("automod_links_enabled"), True),
        "antiInvite": _coerce_bool(settings.get("automod_invites_enabled"), True),
        "spamThreshold": spam_threshold,
        "mentionLimit": max(0, _to_int(settings.get("automod_max_mentions", 5), 5)),
        "capsThreshold": max(0, min(100, _to_int(settings.get("automod_caps_percentage", 70), 70))),
        "action": automod_action,
        "notifyUsers": _coerce_bool(settings.get("automod_notify_users"), True),
        "muteDuration": max(1, _to_int(settings.get("automod_mute_duration", 3600), 3600)),
        "bannedWords": _coerce_text_list(settings.get("automod_badwords", [])),
        "linkWhitelist": _coerce_text_list(settings.get("automod_links_whitelist", [])),
        "aiEnabled": _coerce_bool(settings.get("automod_ai_enabled"), False),
        "aiMinSeverity": max(0, min(10, _to_int(settings.get("automod_ai_min_severity", 4), 4))),
        "scamProtection": _coerce_bool(settings.get("automod_scam_protection"), True),
    }
    _set_module(
        modules,
        "automod",
        enabled=_module_enabled_from_settings("automod", settings, automod_base),
        settings_blob=automod_settings,
        base=automod_base,
    )

    # AntiRaid
    antiraid_base = _safe_module_base(modules, "antiraid")
    antiraid_base_settings = _safe_module_settings(antiraid_base)
    antiraid_time_window = _to_int(settings.get("antiraid_join_seconds", settings.get("antiraid_join_interval", 10)), 10)
    antiraid_settings = {
        **antiraid_base_settings,
        "joinThreshold": max(2, _to_int(settings.get("antiraid_join_threshold", 10), 10)),
        "timeWindow": max(1, antiraid_time_window),
        "cooldownSeconds": max(5, _to_int(settings.get("antiraid_cooldown_seconds", 60), 60)),
        "action": str(settings.get("antiraid_action", "kick")).lower(),
        "lockdownEnabled": str(settings.get("antiraid_action", "kick")).lower() == "lockdown",
        "kickNewAccounts": _coerce_bool(settings.get("antiraid_kick_new_accounts"), False),
        "accountAgeHours": max(1, _to_int(settings.get("antiraid_account_age_hours", 24), 24)),
        "quarantineRoleId": _coerce_channel_like(settings.get("antiraid_quarantine_role")) or "",
        "aiEnabled": _coerce_bool(settings.get("antiraid_ai_enabled"), False),
        "aiMinConfidence": max(0, min(100, _to_int(settings.get("antiraid_ai_min_confidence", 70), 70))),
        "aiOverrideAction": _coerce_bool(settings.get("antiraid_override_ai_action"), False),
        "raidMode": _coerce_bool(settings.get("raid_mode"), False),
    }
    _set_module(
        modules,
        "antiraid",
        enabled=_module_enabled_from_settings("antiraid", settings, antiraid_base),
        settings_blob=antiraid_settings,
        base=antiraid_base,
    )

    # AI Moderation
    aimod_base = _safe_module_base(modules, "aimod")
    aimod_base_settings = _safe_module_settings(aimod_base)
    aimod_settings = {
        **aimod_base_settings,
        "model": str(settings.get("aimod_model", "") or ""),
        "contextMessages": max(1, _to_int(settings.get("aimod_context_messages", 15), 15)),
        "confirmEnabled": _coerce_bool(settings.get("aimod_confirm_enabled"), True),
        "confirmTimeoutSeconds": max(5, _to_int(settings.get("aimod_confirm_timeout_seconds", 25), 25)),
        "confirmActions": _coerce_text_list(settings.get("aimod_confirm_actions", [])),
        "proactiveChance": max(0.0, min(1.0, _to_float(settings.get("aimod_proactive_chance", 0.02), 0.02))),
        "confirmationChannel": _coerce_channel_like(settings.get("ai_confirmation_channel")) or "",
    }
    _set_module(
        modules,
        "aimod",
        enabled=_module_enabled_from_settings("aimod", settings, aimod_base),
        settings_blob=aimod_settings,
        base=aimod_base,
    )

    # Logging
    logging_base = _safe_module_base(modules, "logging")
    logging_base_settings = _safe_module_settings(logging_base)
    logging_settings = {
        **logging_base_settings,
        "modChannel": _get_log_setting(settings, "mod_log_channel") or "",
        "auditChannel": _get_log_setting(settings, "audit_log_channel") or "",
        "messageChannel": _get_log_setting(settings, "message_log_channel") or "",
        "voiceChannel": _get_log_setting(settings, "voice_log_channel") or "",
        "automodChannel": _get_log_setting(settings, "automod_log_channel") or "",
        "reportChannel": _get_log_setting(settings, "report_log_channel") or "",
        "ticketChannel": _get_log_setting(settings, "ticket_log_channel") or "",
    }
    logging_enabled = _module_enabled_from_settings("logging", settings, logging_base) or any(
        bool(logging_settings.get(key))
        for key in ("modChannel", "auditChannel", "messageChannel", "voiceChannel", "automodChannel", "reportChannel", "ticketChannel")
    )
    _set_module(
        modules,
        "logging",
        enabled=logging_enabled,
        settings_blob=logging_settings,
        base=logging_base,
    )

    # Tickets
    tickets_base = _safe_module_base(modules, "tickets")
    tickets_base_settings = _safe_module_settings(tickets_base)
    tickets_settings = {
        **tickets_base_settings,
        "category": _coerce_channel_like(settings.get("ticket_category")) or "",
        "supportRole": _coerce_channel_like(settings.get("ticket_support_role")) or "",
        "modRole": _coerce_channel_like(settings.get("ticket_mod_role")) or "",
        "adminRole": _coerce_channel_like(settings.get("ticket_admin_role")) or "",
        "managerRole": _coerce_channel_like(settings.get("ticket_manager_role")) or "",
        "logChannel": _coerce_channel_like(settings.get("ticket_log_channel")) or "",
    }
    _set_module(
        modules,
        "tickets",
        enabled=_module_enabled_from_settings("tickets", settings, tickets_base),
        settings_blob=tickets_settings,
        base=tickets_base,
    )

    # Verification
    verification_base = _safe_module_base(modules, "verification")
    verification_base_settings = _safe_module_settings(verification_base)
    verification_settings = {
        **verification_base_settings,
        "verifyChannel": _coerce_channel_like(settings.get("verify_channel")) or "",
        "verifyLogChannel": _coerce_channel_like(settings.get("verify_log_channel")) or "",
        "verifiedRole": _coerce_channel_like(settings.get("verified_role")) or "",
        "unverifiedRole": _coerce_channel_like(settings.get("unverified_role")) or "",
        "voiceGateEnabled": _coerce_bool(settings.get("voice_verification_enabled"), False),
        "waitingVoiceChannel": _coerce_channel_like(settings.get("waiting_verify_voice_channel")) or "",
        "voiceSessionTtl": max(30, _to_int(settings.get("vc_verify_session_ttl", 180), 180)),
        "bypassRoles": _coerce_text_list(settings.get("vc_verify_bypass_roles", [])),
    }
    _set_module(
        modules,
        "verification",
        enabled=_module_enabled_from_settings("verification", settings, verification_base),
        settings_blob=verification_settings,
        base=verification_base,
    )

    # Modmail
    modmail_base = _safe_module_base(modules, "modmail")
    modmail_base_settings = _safe_module_settings(modmail_base)
    modmail_settings = {
        **modmail_base_settings,
        "categoryId": _coerce_channel_like(settings.get("modmail_category_id")) or "",
        "logChannel": _coerce_channel_like(settings.get("modmail_log_channel")) or "",
    }
    _set_module(
        modules,
        "modmail",
        enabled=_module_enabled_from_settings("modmail", settings, modmail_base),
        settings_blob=modmail_settings,
        base=modmail_base,
    )

    # Whitelist
    whitelist_base = _safe_module_base(modules, "whitelist")
    whitelist_base_settings = _safe_module_settings(whitelist_base)
    whitelist_settings = {
        **whitelist_base_settings,
        "immunity": _coerce_bool(settings.get("whitelist_immunity"), True),
        "dmOnKick": _coerce_bool(settings.get("whitelist_dm_join"), True),
    }
    _set_module(
        modules,
        "whitelist",
        enabled=_module_enabled_from_settings("whitelist", settings, whitelist_base),
        settings_blob=whitelist_settings,
        base=whitelist_base,
    )

    # Forum moderation
    forum_base = _safe_module_base(modules, "forum_moderation")
    forum_base_settings = _safe_module_settings(forum_base)
    forum_settings = {
        **forum_base_settings,
        "alertsChannel": _coerce_channel_like(settings.get("forum_alerts_channel") or settings.get("forum_alert_channel")) or "",
    }
    _set_module(
        modules,
        "forum_moderation",
        enabled=_coerce_bool(settings.get("forum_moderation_enabled"), _coerce_bool(forum_base.get("enabled"), True)),
        settings_blob=forum_settings,
        base=forum_base,
    )

    return modules


def _apply_dashboard_modules_to_flat_settings(settings: Dict[str, Any], modules: Dict[str, Any]) -> None:
    """Propagate dashboard module fields into the flat keys used by cogs."""
    if not isinstance(modules, dict):
        return

    canonical_modules = _canonicalize_modules_blob(modules)

    for module_id, (enabled_key, default_enabled) in _MODULE_ENABLED_KEYS.items():
        cfg = canonical_modules.get(module_id)
        if isinstance(cfg, dict):
            settings[enabled_key] = _coerce_bool(cfg.get("enabled"), default_enabled)

    # AutoMod
    automod = canonical_modules.get("automod", {})
    if isinstance(automod, dict):
        ams = automod.get("settings", {})
        if not isinstance(ams, dict):
            ams = {}
        if "antiLink" in ams:
            settings["automod_links_enabled"] = _coerce_bool(ams.get("antiLink"), True)
        if "antiInvite" in ams:
            settings["automod_invites_enabled"] = _coerce_bool(ams.get("antiInvite"), True)
        if "mentionLimit" in ams:
            settings["automod_max_mentions"] = max(0, _to_int(ams.get("mentionLimit"), _to_int(settings.get("automod_max_mentions", 5), 5)))
        if "capsThreshold" in ams:
            settings["automod_caps_percentage"] = max(0, min(100, _to_int(ams.get("capsThreshold"), _to_int(settings.get("automod_caps_percentage", 70), 70))))
        if "spamThreshold" in ams:
            settings["automod_spam_threshold"] = max(0, _to_int(ams.get("spamThreshold"), _to_int(settings.get("automod_spam_threshold", 5), 5)))
        if "antiSpam" in ams:
            anti_spam_enabled = _coerce_bool(ams.get("antiSpam"), True)
            if anti_spam_enabled and _to_int(settings.get("automod_spam_threshold", 0), 0) <= 0:
                settings["automod_spam_threshold"] = max(1, _to_int(ams.get("spamThreshold"), 5))
            if not anti_spam_enabled:
                settings["automod_spam_threshold"] = 0
        if "action" in ams:
            action = str(ams.get("action", settings.get("automod_punishment", "warn"))).lower()
            if action == "timeout":
                action = "mute"
            if action not in {"none", "log", "warn", "delete", "mute", "kick", "ban", "tempban", "quarantine"}:
                action = "warn"
            settings["automod_punishment"] = action
        if "notifyUsers" in ams:
            settings["automod_notify_users"] = _coerce_bool(ams.get("notifyUsers"), True)
        if "muteDuration" in ams:
            settings["automod_mute_duration"] = max(1, _to_int(ams.get("muteDuration"), _to_int(settings.get("automod_mute_duration", 3600), 3600)))
        if "bannedWords" in ams:
            settings["automod_badwords"] = _coerce_text_list(ams.get("bannedWords"))
        if "linkWhitelist" in ams:
            settings["automod_links_whitelist"] = _coerce_text_list(ams.get("linkWhitelist"))
        if "aiEnabled" in ams:
            settings["automod_ai_enabled"] = _coerce_bool(ams.get("aiEnabled"), False)
        if "aiMinSeverity" in ams:
            settings["automod_ai_min_severity"] = max(0, min(10, _to_int(ams.get("aiMinSeverity"), _to_int(settings.get("automod_ai_min_severity", 4), 4))))
        if "scamProtection" in ams:
            settings["automod_scam_protection"] = _coerce_bool(ams.get("scamProtection"), True)

    # AntiRaid
    antiraid = canonical_modules.get("antiraid", {})
    if isinstance(antiraid, dict):
        ars = antiraid.get("settings", {})
        if not isinstance(ars, dict):
            ars = {}
        if "joinThreshold" in ars:
            settings["antiraid_join_threshold"] = max(2, _to_int(ars.get("joinThreshold"), _to_int(settings.get("antiraid_join_threshold", 10), 10)))
        if "timeWindow" in ars:
            seconds = max(1, _to_int(ars.get("timeWindow"), _to_int(settings.get("antiraid_join_seconds", 10), 10)))
            settings["antiraid_join_seconds"] = seconds
            settings["antiraid_join_interval"] = seconds
        if "cooldownSeconds" in ars:
            settings["antiraid_cooldown_seconds"] = max(5, _to_int(ars.get("cooldownSeconds"), _to_int(settings.get("antiraid_cooldown_seconds", 60), 60)))
        if "action" in ars:
            action = str(ars.get("action", settings.get("antiraid_action", "kick"))).lower()
            if action in {"kick", "ban", "lockdown", "quarantine"}:
                settings["antiraid_action"] = action
        if "lockdownEnabled" in ars:
            if _coerce_bool(ars.get("lockdownEnabled"), False):
                settings["antiraid_action"] = "lockdown"
            elif str(settings.get("antiraid_action", "kick")).lower() == "lockdown":
                settings["antiraid_action"] = "kick"
        if "kickNewAccounts" in ars:
            settings["antiraid_kick_new_accounts"] = _coerce_bool(ars.get("kickNewAccounts"), False)
        if "accountAgeHours" in ars:
            settings["antiraid_account_age_hours"] = max(1, _to_int(ars.get("accountAgeHours"), _to_int(settings.get("antiraid_account_age_hours", 24), 24)))
        if "quarantineRoleId" in ars:
            settings["antiraid_quarantine_role"] = _coerce_channel_like(ars.get("quarantineRoleId"))
        if "aiEnabled" in ars:
            settings["antiraid_ai_enabled"] = _coerce_bool(ars.get("aiEnabled"), False)
        if "aiMinConfidence" in ars:
            settings["antiraid_ai_min_confidence"] = max(0, min(100, _to_int(ars.get("aiMinConfidence"), _to_int(settings.get("antiraid_ai_min_confidence", 70), 70))))
        if "aiOverrideAction" in ars:
            settings["antiraid_override_ai_action"] = _coerce_bool(ars.get("aiOverrideAction"), False)
        if "raidMode" in ars:
            settings["raid_mode"] = _coerce_bool(ars.get("raidMode"), False)

    # AI Moderation
    aimod = canonical_modules.get("aimod", {})
    if isinstance(aimod, dict):
        ais = aimod.get("settings", {})
        if not isinstance(ais, dict):
            ais = {}
        if "model" in ais:
            settings["aimod_model"] = str(ais.get("model") or "")
        if "contextMessages" in ais:
            settings["aimod_context_messages"] = max(1, _to_int(ais.get("contextMessages"), _to_int(settings.get("aimod_context_messages", 15), 15)))
        if "confirmEnabled" in ais:
            settings["aimod_confirm_enabled"] = _coerce_bool(ais.get("confirmEnabled"), True)
        if "confirmTimeoutSeconds" in ais:
            settings["aimod_confirm_timeout_seconds"] = max(5, _to_int(ais.get("confirmTimeoutSeconds"), _to_int(settings.get("aimod_confirm_timeout_seconds", 25), 25)))
        if "confirmActions" in ais:
            settings["aimod_confirm_actions"] = _coerce_text_list(ais.get("confirmActions"))
        if "proactiveChance" in ais:
            settings["aimod_proactive_chance"] = max(0.0, min(1.0, _to_float(ais.get("proactiveChance"), _to_float(settings.get("aimod_proactive_chance", 0.02), 0.02))))
        if "confirmationChannel" in ais:
            settings["ai_confirmation_channel"] = _coerce_channel_like(ais.get("confirmationChannel"))

    # Logging channels in module settings
    logging_module = canonical_modules.get("logging", {})
    if isinstance(logging_module, dict):
        lgs = logging_module.get("settings", {})
        if not isinstance(lgs, dict):
            lgs = {}
        channel_key_map = {
            "modChannel": "mod_log_channel",
            "auditChannel": "audit_log_channel",
            "messageChannel": "message_log_channel",
            "voiceChannel": "voice_log_channel",
            "automodChannel": "automod_log_channel",
            "reportChannel": "report_log_channel",
            "ticketChannel": "ticket_log_channel",
        }
        for ui_key, setting_key in channel_key_map.items():
            if ui_key in lgs:
                value = _coerce_channel_like(lgs.get(ui_key))
                for alias in _LOG_SETTING_ALIASES.get(setting_key, (setting_key,)):
                    settings[alias] = value

    # Tickets
    tickets = canonical_modules.get("tickets", {})
    if isinstance(tickets, dict):
        tks = tickets.get("settings", {})
        if not isinstance(tks, dict):
            tks = {}
        ticket_key_map = {
            "category": "ticket_category",
            "supportRole": "ticket_support_role",
            "modRole": "ticket_mod_role",
            "adminRole": "ticket_admin_role",
            "managerRole": "ticket_manager_role",
            "logChannel": "ticket_log_channel",
        }
        for ui_key, setting_key in ticket_key_map.items():
            if ui_key in tks:
                settings[setting_key] = _coerce_channel_like(tks.get(ui_key))

    # Verification
    verification = canonical_modules.get("verification", {})
    if isinstance(verification, dict):
        vs = verification.get("settings", {})
        if not isinstance(vs, dict):
            vs = {}
        verification_key_map = {
            "verifyChannel": "verify_channel",
            "verifyLogChannel": "verify_log_channel",
            "verifiedRole": "verified_role",
            "unverifiedRole": "unverified_role",
            "waitingVoiceChannel": "waiting_verify_voice_channel",
        }
        for ui_key, setting_key in verification_key_map.items():
            if ui_key in vs:
                settings[setting_key] = _coerce_channel_like(vs.get(ui_key))
        if "voiceGateEnabled" in vs:
            settings["voice_verification_enabled"] = _coerce_bool(vs.get("voiceGateEnabled"), False)
        if "voiceSessionTtl" in vs:
            settings["vc_verify_session_ttl"] = max(30, _to_int(vs.get("voiceSessionTtl"), _to_int(settings.get("vc_verify_session_ttl", 180), 180)))
        if "bypassRoles" in vs:
            settings["vc_verify_bypass_roles"] = _coerce_text_list(vs.get("bypassRoles"))

    # Modmail
    modmail = canonical_modules.get("modmail", {})
    if isinstance(modmail, dict):
        ms = modmail.get("settings", {})
        if not isinstance(ms, dict):
            ms = {}
        if "categoryId" in ms:
            settings["modmail_category_id"] = _coerce_channel_like(ms.get("categoryId"))
        if "logChannel" in ms:
            settings["modmail_log_channel"] = _coerce_channel_like(ms.get("logChannel"))

    # Whitelist
    whitelist = canonical_modules.get("whitelist", {})
    if isinstance(whitelist, dict):
        ws = whitelist.get("settings", {})
        if not isinstance(ws, dict):
            ws = {}
        if "immunity" in ws:
            settings["whitelist_immunity"] = _coerce_bool(ws.get("immunity"), True)
        if "dmOnKick" in ws:
            settings["whitelist_dm_join"] = _coerce_bool(ws.get("dmOnKick"), True)

    # Forum moderation
    forum = canonical_modules.get("forum_moderation", {})
    if isinstance(forum, dict):
        settings["forum_moderation_enabled"] = _coerce_bool(forum.get("enabled"), True)
        fs = forum.get("settings", {})
        if isinstance(fs, dict) and "alertsChannel" in fs:
            alerts = _coerce_channel_like(fs.get("alertsChannel"))
            settings["forum_alerts_channel"] = alerts
            settings["forum_alert_channel"] = alerts


_SETUP_FIELD_TO_SETTING_KEY: Dict[str, str] = {
    "ownerRole": "owner_role",
    "managerRole": "manager_role",
    "adminRole": "admin_role",
    "supervisorRole": "supervisor_role",
    "seniorModRole": "senior_mod_role",
    "moderatorRole": "mod_role",
    "trialModRole": "trial_mod_role",
    "staffRole": "staff_role",
    "mutedRole": "muted_role",
    "quarantineRole": "automod_quarantine_role_id",
    "logsAccessRole": "logs_access_role",
    "bypassRole": "automod_bypass_role_id",
    "whitelistedRole": "whitelisted_role",
    "autoRole": "auto_role",
    "verifiedRole": "verified_role",
    "unverifiedRole": "unverified_role",
    "welcomeChannel": "welcome_channel",
    "staffChatChannel": "staff_chat_channel",
    "staffCommandsChannel": "staff_commands_channel",
    "staffAnnouncementsChannel": "staff_announcements_channel",
    "staffGuideChannel": "staff_guide_channel",
    "staffUpdatesChannel": "staff_updates_channel",
    "staffSanctionsChannel": "staff_sanctions_channel",
    "supervisorLogChannel": "supervisor_log_channel",
}


def _build_setup_config(settings: Dict[str, Any]) -> Dict[str, Any]:
    setup: Dict[str, Any] = {}
    for field_key, setting_key in _SETUP_FIELD_TO_SETTING_KEY.items():
        setup[field_key] = _coerce_channel_like(settings.get(setting_key)) or ""
    return setup


def _apply_setup_config_to_flat_settings(settings: Dict[str, Any], setup: Dict[str, Any]) -> None:
    if not isinstance(setup, dict):
        return

    for field_key, setting_key in _SETUP_FIELD_TO_SETTING_KEY.items():
        if field_key in setup:
            settings[setting_key] = _coerce_channel_like(setup.get(field_key))

    sync_setup_aliases(settings)
    sync_staff_role_groups(settings)


async def api_guild_config(request: web.Request):
    """Get guild settings from database."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    if not _bot:
        raise web.HTTPServiceUnavailable(text=json.dumps({"code": 503, "message": "Bot not ready"}),
                                          content_type="application/json")

    settings = await _bot.db.get_settings(int(guild_id))
    guild = _bot.get_guild(int(guild_id))
    if guild is not None:
        settings = hydrate_setup_settings_from_guild(guild, settings)
    else:
        sync_setup_aliases(settings)
    effective_permissions = _effective_dashboard_permissions(settings)
    
    # Build a full config response, extracting dashboard blobs and bridging key flat settings.
    modules = _build_dashboard_modules(settings)
    logging_blob = _build_dashboard_logging(settings)
    commands_blob = _normalize_command_configs_blob(settings.get("commands", {}))
    config = {
        "guildId": guild_id,
        "version": settings.get("_version", 1),
        "prefix": settings.get("prefix", ","),
        "updatedAt": settings.get("updatedAt", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        "defaultCooldown": settings.get("defaultCooldown", 0),
        "timezone": settings.get("timezone", "UTC"),
        "setup": _build_setup_config(settings),
        "settings": settings.get("general", {}),
        "commands": commands_blob,
        "modules": modules,
        "logging": logging_blob,
        "permissions": effective_permissions,
        "globalBypassRoles": settings.get("globalBypassRoles", []),
        "globalBypassUsers": settings.get("globalBypassUsers", []),
    }

    return web.json_response(config, headers={"ETag": str(config["version"])})


async def api_guild_config_update(request: web.Request):
    """Update guild settings in database."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    if not _bot:
        raise web.HTTPServiceUnavailable(text=json.dumps({"code": 503, "message": "Bot not ready"}),
                                          content_type="application/json")

    body = await request.json()
    previous = await _bot.db.get_settings(int(guild_id))
    permissions_payload = body.get("permissions", {}) if isinstance(body.get("permissions", {}), dict) else {}
    role_mappings = permissions_payload.get("dashboardRoleMappings")
    if role_mappings is None:
        role_mappings = permissions_payload.get("roleMappings", [])
    
    # Merge payload into existing settings so legacy keys used by cogs are preserved.
    updated_settings = dict(previous)
    updated_settings["_version"] = max(_to_int(previous.get("_version", 1), 1) + 1, _to_int(body.get("version", 1), 1) + 1)
    updated_settings["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if isinstance(body.get("prefix"), str):
        updated_settings["prefix"] = body.get("prefix", ",")
    if isinstance(body.get("settings"), dict):
        updated_settings["general"] = body.get("settings", {})
    if isinstance(body.get("setup"), dict):
        _apply_setup_config_to_flat_settings(updated_settings, body.get("setup", {}))
    if isinstance(body.get("commands"), dict):
        updated_settings["commands"] = _normalize_command_configs_blob(body.get("commands", {}))
    if isinstance(body.get("modules"), dict):
        canonical_modules = _canonicalize_modules_blob(body.get("modules", {}))
        updated_settings["modules"] = canonical_modules
        _apply_dashboard_modules_to_flat_settings(updated_settings, canonical_modules)
    if isinstance(body.get("logging"), dict):
        updated_settings["logging"] = body.get("logging", {})
        _apply_dashboard_logging_to_flat_settings(updated_settings, body.get("logging", {}))
    if isinstance(role_mappings, list):
        updated_settings["dashboardRoleMappings"] = _normalize_dashboard_role_mappings(role_mappings)
        updated_settings["dashboardPermissionsConfigured"] = True
    if isinstance(permissions_payload.get("userOverrides"), list):
        updated_settings["dashboardUserOverrides"] = _normalize_dashboard_user_overrides(permissions_payload.get("userOverrides"))
        updated_settings["dashboardPermissionsConfigured"] = True
    if isinstance(body.get("globalBypassRoles"), list):
        updated_settings["globalBypassRoles"] = body.get("globalBypassRoles", [])
    if isinstance(body.get("globalBypassUsers"), list):
        updated_settings["globalBypassUsers"] = body.get("globalBypassUsers", [])
    if "defaultCooldown" in body:
        updated_settings["defaultCooldown"] = _to_int(body.get("defaultCooldown"), _to_int(previous.get("defaultCooldown", 0), 0))
    if isinstance(body.get("timezone"), str):
        updated_settings["timezone"] = body.get("timezone", "UTC")

    sync_setup_aliases(updated_settings)
    sync_staff_role_groups(updated_settings)
    updated_settings["commands"] = _normalize_command_configs_blob(updated_settings.get("commands", {}))

    verification_sync_keys = (
        "verification_enabled",
        "unverified_role",
        "verified_role",
        "verify_channel",
        "welcome_channel",
    )
    should_sync_verification_gate = any(
        previous.get(key) != updated_settings.get(key)
        for key in verification_sync_keys
    )
    if should_sync_verification_gate:
        guild = _bot.get_guild(int(guild_id))
        if guild is not None:
            try:
                await apply_verification_gate(
                    guild,
                    updated_settings,
                    previous_unverified_role_id=_to_int(previous.get("unverified_role"), 0),
                )
            except Exception as exc:
                logger.warning("Failed to sync verification gate for guild %s: %s", guild_id, exc)
    
    await _bot.db.update_settings(int(guild_id), updated_settings)
    
    # Return updated config
    saved = await _bot.db.get_settings(int(guild_id))
    guild = _bot.get_guild(int(guild_id))
    if guild is not None:
        saved = hydrate_setup_settings_from_guild(guild, saved)
    else:
        sync_setup_aliases(saved)
    saved_modules = _build_dashboard_modules(saved)
    saved_logging = _build_dashboard_logging(saved)
    saved_commands = _normalize_command_configs_blob(saved.get("commands", {}))
    effective_permissions = _effective_dashboard_permissions(saved)
    config = {
        "guildId": guild_id,
        "version": saved.get("_version", 1),
        "prefix": saved.get("prefix", ","),
        "updatedAt": saved.get("updatedAt", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        "defaultCooldown": saved.get("defaultCooldown", 0),
        "timezone": saved.get("timezone", "UTC"),
        "setup": _build_setup_config(saved),
        "settings": saved.get("general", {}),
        "commands": saved_commands,
        "modules": saved_modules,
        "logging": saved_logging,
        "permissions": effective_permissions,
        "globalBypassRoles": saved.get("globalBypassRoles", []),
        "globalBypassUsers": saved.get("globalBypassUsers", []),
    }

    changes: Dict[str, Any] = {}
    old_prefix = previous.get("prefix", ",")
    new_prefix = saved.get("prefix", ",")
    if old_prefix != new_prefix:
        changes["prefix"] = {"from": old_prefix, "to": new_prefix}

    old_modules = _canonicalize_modules_blob(previous.get("modules", {}))
    new_modules = _canonicalize_modules_blob(saved.get("modules", {}))
    old_modules_enabled = sum(1 for item in old_modules.values() if isinstance(item, dict) and item.get("enabled"))
    new_modules_enabled = sum(1 for item in new_modules.values() if isinstance(item, dict) and item.get("enabled"))
    if old_modules_enabled != new_modules_enabled:
        changes["modulesEnabled"] = {"from": old_modules_enabled, "to": new_modules_enabled}

    if old_prefix != new_prefix and getattr(_bot, "prefix_cache", None):
        try:
            await _bot.prefix_cache.invalidate(int(guild_id))
        except Exception:
            logger.debug("Failed to invalidate prefix cache for guild %s", guild_id, exc_info=True)

    old_commands = previous.get("commands", {}) if isinstance(previous.get("commands", {}), dict) else {}
    new_commands = saved.get("commands", {}) if isinstance(saved.get("commands", {}), dict) else {}
    commands_changed = old_commands != new_commands
    old_commands_enabled = sum(1 for item in old_commands.values() if isinstance(item, dict) and item.get("enabled"))
    new_commands_enabled = sum(1 for item in new_commands.values() if isinstance(item, dict) and item.get("enabled"))
    if old_commands_enabled != new_commands_enabled:
        changes["commandsEnabled"] = {"from": old_commands_enabled, "to": new_commands_enabled}
    if commands_changed:
        status = _sync_status.get(guild_id) or {
            "status": "idle",
            "lastSyncedAt": None,
            "error": None,
            "progress": 0,
            "syncRequired": False,
        }
        status["syncRequired"] = True
        if status.get("status") == "complete":
            status["status"] = "idle"
            status["progress"] = 0
        _sync_status[guild_id] = status

    old_mappings = previous.get("dashboardRoleMappings", [])
    new_mappings = saved.get("dashboardRoleMappings", [])
    if isinstance(old_mappings, list) and isinstance(new_mappings, list) and len(old_mappings) != len(new_mappings):
        changes["roleMappings"] = {"from": len(old_mappings), "to": len(new_mappings)}

    await _append_dashboard_audit(
        guild_id,
        session,
        action="config_update",
        target="guild_config",
        changes=changes or {"version": {"from": previous.get("_version", 1), "to": saved.get("_version", 1)}},
    )

    return web.json_response(config, headers={"ETag": str(config["version"])})


async def api_guild_setup_summary(request: web.Request):
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    if not _bot:
        raise web.HTTPServiceUnavailable(
            text=json.dumps({"code": 503, "message": "Bot not ready"}),
            content_type="application/json",
        )

    guild = _bot.get_guild(int(guild_id))
    if not guild:
        raise web.HTTPNotFound(
            text=json.dumps({"code": 404, "message": "Guild not found"}),
            content_type="application/json",
        )

    settings = await _bot.db.get_settings(int(guild_id))
    settings = hydrate_setup_settings_from_guild(guild, settings)
    dashboard_url = f"{_frontend_base_url(request)}/dashboard/setup?guild={guild_id}"
    summary = build_setup_summary(guild, settings, dashboard_url=dashboard_url)
    return web.json_response(summary)


async def api_guild_setup_quickstart(request: web.Request):
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    if not _bot:
        raise web.HTTPServiceUnavailable(
            text=json.dumps({"code": 503, "message": "Bot not ready"}),
            content_type="application/json",
        )

    guild = _bot.get_guild(int(guild_id))
    if not guild:
        raise web.HTTPNotFound(
            text=json.dumps({"code": 404, "message": "Guild not found"}),
            content_type="application/json",
        )

    previous = await _bot.db.get_settings(int(guild_id))
    sync_setup_aliases(previous)
    result = await quickstart_server(guild, previous)
    updated_settings = dict(result.get("settings", previous))
    updated_settings["_version"] = max(
        _to_int(previous.get("_version", 1), 1) + 1,
        _to_int(updated_settings.get("_version", 1), 1),
    )
    updated_settings["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    await _bot.db.update_settings(int(guild_id), updated_settings)

    await _append_dashboard_audit(
        guild_id,
        session,
        action="setup_quickstart",
        target="guild_setup",
        changes={
            "createdRoles": {"from": None, "to": len(result.get("createdRoles", []))},
            "createdChannels": {"from": None, "to": len(result.get("createdChannels", []))},
            "errors": {"from": None, "to": len(result.get("errors", []))},
        },
    )

    dashboard_url = f"{_frontend_base_url(request)}/dashboard/setup?guild={guild_id}"
    summary = build_setup_summary(guild, updated_settings, dashboard_url=dashboard_url)
    return web.json_response(
        {
            "ok": True,
            "summary": summary,
            "createdRoles": result.get("createdRoles", []),
            "createdChannels": result.get("createdChannels", []),
            "reused": result.get("reused", []),
            "errors": result.get("errors", []),
        }
    )


async def api_guild_antiraid_panic(request: web.Request):
    """Enable/disable panic mode and immediately lock or unlock text channels."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    if not _bot:
        raise web.HTTPServiceUnavailable(
            text=json.dumps({"code": 503, "message": "Bot not ready"}),
            content_type="application/json",
        )

    guild = _bot.get_guild(int(guild_id))
    if not guild:
        raise web.HTTPNotFound(
            text=json.dumps({"code": 404, "message": "Guild not found"}),
            content_type="application/json",
        )

    payload: Dict[str, Any] = {}
    if request.can_read_body:
        try:
            parsed = await request.json()
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            payload = {}
    enabled = _coerce_bool(payload.get("enabled"), True)

    previous_settings = await _bot.db.get_settings(int(guild_id))
    previous_mode = _coerce_bool(previous_settings.get("raid_mode"), False)
    changed_count = 0
    actor = session.get("user", {}) if isinstance(session.get("user", {}), dict) else {}
    actor_name = str(
        actor.get("username")
        or actor.get("global_name")
        or actor.get("id")
        or "dashboard"
    )

    antiraid_cog = _bot.get_cog("AntiRaid")
    if antiraid_cog and hasattr(antiraid_cog, "set_manual_raid_mode"):
        try:
            changed_count = int(
                await antiraid_cog.set_manual_raid_mode(
                    guild,
                    enabled=enabled,
                    actor_text=actor_name,
                    reason_prefix="[DASHBOARD PANIC]",
                )
            )
        except Exception as exc:
            logger.error("Panic mode toggle failed via AntiRaid cog for guild %s: %s", guild_id, exc)
            raise web.HTTPInternalServerError(
                text=json.dumps({"code": 500, "message": "Failed to toggle panic mode"}),
                content_type="application/json",
            )
    else:
        updated_settings = dict(previous_settings)
        updated_settings["raid_mode"] = enabled
        if enabled:
            updated_settings["antiraid_enabled"] = True
        await _bot.db.update_settings(int(guild_id), updated_settings)

        send_messages_value = False if enabled else None
        reason_state = "enabled" if enabled else "disabled"
        reason = f"[DASHBOARD PANIC] {reason_state} by {actor_name}"

        for channel in guild.text_channels:
            try:
                await channel.set_permissions(
                    guild.default_role,
                    send_messages=send_messages_value,
                    reason=reason,
                )
                changed_count += 1
            except Exception:
                pass

        if antiraid_cog and hasattr(antiraid_cog, "raid_cooldown"):
            try:
                if enabled:
                    antiraid_cog.raid_cooldown.add(guild.id)
                else:
                    antiraid_cog.raid_cooldown.discard(guild.id)
            except Exception:
                pass

    await _append_dashboard_audit(
        guild_id,
        session,
        action="panic_mode_toggle",
        target="antiraid",
        changes={
            "raidMode": {"from": previous_mode, "to": enabled},
            "channelsAffected": {"from": None, "to": changed_count},
        },
    )

    return web.json_response({
        "ok": True,
        "enabled": enabled,
        "channelsAffected": changed_count,
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })


async def api_guild_cases(request: web.Request):
    """Get moderation cases for a guild."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    if not _bot:
        raise web.HTTPServiceUnavailable(text=json.dumps({"code": 503, "message": "Bot not ready"}),
                                          content_type="application/json")

    # Get all cases from database
    try:
        async with _bot.db.get_connection() as db:
            cursor = await db.execute(
                """SELECT * FROM cases WHERE guild_id = ? ORDER BY created_at DESC LIMIT 50""",
                (int(guild_id),),
            )
            rows = await cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch cases: {e}")
        rows = []

    cases = []
    for r in rows:
        # Try to resolve usernames from bot cache
        user_name = _resolve_user_name(r[3])
        mod_name = _resolve_user_name(r[4])
        
        cases.append({
            "id": r[2],  # case_number
            "guildId": str(r[1]),
            "targetUser": {
                "id": str(r[3]),
                "username": user_name,
            },
            "moderator": {
                "id": str(r[4]),
                "username": mod_name,
            },
            "action": _normalize_case_action(r[5]),
            "reason": r[6] or "No reason provided",
            "duration": r[7],
            "createdAt": r[8],
            "active": bool(r[9]) if r[9] is not None else True,
        })

    return web.json_response({
        "items": cases,
        "nextCursor": None,
        "hasMore": False,
    })


async def api_guild_case(request: web.Request):
    """Get a specific case."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    case_id = int(request.match_info["case_id"])
    _require_guild_access(session, guild_id)

    if not _bot:
        raise web.HTTPServiceUnavailable()

    case = await _bot.db.get_case(int(guild_id), case_id)
    if not case:
        raise web.HTTPNotFound(text=json.dumps({"code": 404, "message": "Case not found"}),
                                content_type="application/json")

    return web.json_response({
        "id": case["case_number"],
        "guildId": str(case["guild_id"]),
        "targetUser": {
            "id": str(case["user_id"]),
            "username": _resolve_user_name(case["user_id"]),
        },
        "moderator": {
            "id": str(case["moderator_id"]),
            "username": _resolve_user_name(case["moderator_id"]),
        },
        "action": _normalize_case_action(case["action"]),
        "reason": case["reason"] or "No reason provided",
        "duration": case["duration"],
        "createdAt": case["created_at"],
        "active": bool(case.get("active", True)),
    })


async def api_guild_audit(request: web.Request):
    """Get dashboard audit entries for a guild."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    if not _bot:
        raise web.HTTPServiceUnavailable(text=json.dumps({"code": 503, "message": "Bot not ready"}),
                                          content_type="application/json")

    await _ensure_dashboard_audit_table()

    try:
        async with _bot.db.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT id, guild_id, user_id, user_name, action, target, changes, created_at
                FROM dashboard_audit
                WHERE guild_id = ?
                ORDER BY id DESC
                LIMIT 200
                """,
                (int(guild_id),),
            )
            rows = await cursor.fetchall()

            case_cursor = await db.execute(
                """
                SELECT case_number, guild_id, user_id, moderator_id, action, reason, duration, created_at
                FROM cases
                WHERE guild_id = ?
                ORDER BY created_at DESC
                LIMIT 200
                """,
                (int(guild_id),),
            )
            case_rows = await case_cursor.fetchall()
    except Exception as exc:
        logger.error(f"Failed to fetch dashboard audit entries: {exc}")
        rows = []
        case_rows = []

    entries = []
    for row in rows:
        try:
            parsed_changes = json.loads(row[6]) if row[6] else {}
            if not isinstance(parsed_changes, dict):
                parsed_changes = {}
        except Exception:
            parsed_changes = {}
        entries.append({
            "id": str(row[0]),
            "guildId": str(row[1]),
            "userId": str(row[2] or ""),
            "userName": row[3] or "Unknown User",
            "action": row[4] or "config_update",
            "target": row[5] or "config",
            "changes": parsed_changes,
            "timestamp": row[7],
        })

    for row in case_rows:
        user_id = int(row[2]) if row[2] is not None else 0
        moderator_id = int(row[3]) if row[3] is not None else 0
        action = str(row[4] or "note").lower()
        reason = row[5] or "No reason provided"
        duration = row[6]
        case_target = f"case#{row[0]}"
        entries.append({
            "id": f"case_{row[0]}_{row[7]}",
            "guildId": str(row[1]),
            "userId": str(moderator_id),
            "userName": _resolve_user_name(moderator_id) if moderator_id else "Unknown Moderator",
            "action": f"case_{action}",
            "target": case_target,
            "changes": {
                "targetUser": {"from": None, "to": f"{_resolve_user_name(user_id)} ({user_id})"},
                "reason": {"from": None, "to": reason},
                **({"duration": {"from": None, "to": duration}} if duration else {}),
            },
            "timestamp": row[7],
        })

    entries.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)

    return web.json_response({
        "items": entries,
        "nextCursor": None,
        "hasMore": False,
    })


async def api_guild_commands_sync(request: web.Request):
    """Sync slash commands for a guild immediately."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    if not _bot:
        raise web.HTTPServiceUnavailable(text=json.dumps({"code": 503, "message": "Bot not ready"}),
                                          content_type="application/json")

    guild = _bot.get_guild(int(guild_id))
    if not guild:
        raise web.HTTPNotFound(text=json.dumps({"code": 404, "message": "Guild not found"}),
                                content_type="application/json")

    _sync_status[guild_id] = {
        "status": "syncing",
        "lastSyncedAt": None,
        "error": None,
        "progress": 20,
        "syncRequired": True,
    }

    try:
        synced = await _bot.tree.sync(guild=guild)
        synced_count = len(synced)
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _sync_status[guild_id] = {
            "status": "complete",
            "lastSyncedAt": now_iso,
            "error": None,
            "progress": 100,
            "syncRequired": False,
        }
        await _append_dashboard_audit(
            guild_id,
            session,
            action="sync_commands",
            target="slash_commands",
            changes={"syncedCount": {"from": None, "to": synced_count}},
        )
        return web.json_response({"ok": True, "synced": synced_count})
    except Exception as exc:
        msg = str(exc) or "Failed to sync slash commands"
        _sync_status[guild_id] = {
            "status": "error",
            "lastSyncedAt": None,
            "error": msg,
            "progress": 0,
            "syncRequired": True,
        }
        logger.error(f"Command sync failed for guild {guild_id}: {exc}")
        raise web.HTTPInternalServerError(
            text=json.dumps({"code": 500, "message": msg}),
            content_type="application/json",
        )


async def api_guild_commands_sync_status(request: web.Request):
    """Return the latest command sync status for a guild."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    status = _sync_status.get(guild_id) or {
        "status": "idle",
        "lastSyncedAt": None,
        "error": None,
        "progress": 0,
        "syncRequired": False,
    }
    return web.json_response(status)


def _resolve_user_name(user_id: int) -> str:
    """Try to get a username from the bot's user cache."""
    if not _bot:
        return f"User#{user_id}"
    user = _bot.get_user(int(user_id))
    if user:
        return user.display_name or user.name
    return f"User#{user_id}"


async def _ensure_dashboard_audit_table() -> None:
    """Create dashboard audit table if it does not exist."""
    if not _bot:
        return
    async with _bot.db.get_connection() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS dashboard_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id TEXT,
                user_name TEXT,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                changes TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()


async def _append_dashboard_audit(
    guild_id: str,
    session: Dict[str, Any],
    *,
    action: str,
    target: str,
    changes: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist a dashboard action for the /api/guilds/{guild_id}/audit endpoint."""
    if not _bot:
        return
    try:
        await _ensure_dashboard_audit_table()
        user = session.get("user", {})
        user_id = str(user.get("id", ""))
        user_name = user.get("username") or user.get("global_name") or "Unknown User"
        payload = json.dumps(changes or {}, ensure_ascii=False)
        async with _bot.db.get_connection() as db:
            await db.execute(
                """
                INSERT INTO dashboard_audit (guild_id, user_id, user_name, action, target, changes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (int(guild_id), user_id, user_name, action, target, payload),
            )
            await db.commit()
    except Exception as exc:
        logger.error(f"Failed to write dashboard audit entry: {exc}")


def _empty_command_config_hints() -> Dict[str, bool]:
    return {
        "supportsReason": False,
        "supportsConfirmation": False,
        "supportsRoleHierarchy": False,
    }


def _merge_command_config_hints(base: Dict[str, bool], incoming: Dict[str, bool]) -> Dict[str, bool]:
    merged = _empty_command_config_hints()
    for key in merged:
        merged[key] = bool(base.get(key, False) or incoming.get(key, False))
    return merged


def _merge_command_capability_type(current: str, incoming: str) -> str:
    if current == incoming:
        return current
    return "both"


def _annotation_is_target_like(annotation: Any) -> bool:
    if annotation in (discord.Member, discord.User, discord.Role):
        return True
    origin = get_origin(annotation)
    if origin is None:
        return False
    return any(_annotation_is_target_like(arg) for arg in get_args(annotation))


def _infer_prefix_command_hints(command_obj: Any) -> Dict[str, bool]:
    hints = _empty_command_config_hints()
    params = list(getattr(command_obj, "clean_params", {}).items())

    for param_name, parameter in params:
        lowered = str(param_name).strip().lower()
        if lowered == "reason":
            hints["supportsReason"] = True
        if lowered in {"confirm", "confirmation"}:
            hints["supportsConfirmation"] = True

        annotation = getattr(parameter, "annotation", inspect._empty)
        if annotation is not inspect._empty and _annotation_is_target_like(annotation):
            hints["supportsRoleHierarchy"] = True

    if not hints["supportsRoleHierarchy"]:
        fallback_target_names = {"target", "user", "member", "role", "victim"}
        if any(str(name).strip().lower() in fallback_target_names for name, _ in params):
            hints["supportsRoleHierarchy"] = True

    return hints


def _infer_slash_command_hints(command_obj: Any) -> Dict[str, bool]:
    hints = _empty_command_config_hints()

    if isinstance(command_obj, app_commands.Group):
        for child in getattr(command_obj, "commands", []) or []:
            hints = _merge_command_config_hints(hints, _infer_slash_command_hints(child))
        return hints

    parameters = getattr(command_obj, "parameters", []) or []
    for parameter in parameters:
        name = str(getattr(parameter, "name", "") or "").strip().lower()
        if name == "reason":
            hints["supportsReason"] = True
        if name in {"confirm", "confirmation"}:
            hints["supportsConfirmation"] = True

        option_type = getattr(parameter, "type", None)
        if option_type in {
            discord.AppCommandOptionType.user,
            discord.AppCommandOptionType.role,
            discord.AppCommandOptionType.mentionable,
        }:
            hints["supportsRoleHierarchy"] = True
            continue

        annotation = getattr(parameter, "annotation", None)
        if _annotation_is_target_like(annotation):
            hints["supportsRoleHierarchy"] = True

    return hints


async def api_bot_capabilities(request: web.Request):
    """Return bot capabilities with real module schemas and event types."""
    _require_auth(request)

    if not _bot:
        raise web.HTTPServiceUnavailable()

    commands_by_name: Dict[str, Dict[str, Any]] = {}

    def upsert_command_entry(
        *,
        name: str,
        description: str,
        command_type: str,
        group: str,
        default_required_permission: str,
        config_hints: Dict[str, bool],
    ) -> None:
        existing = commands_by_name.get(name)
        if existing is None:
            commands_by_name[name] = {
                "name": name,
                "description": description,
                "type": command_type,
                "group": group,
                "category": group,
                "defaultEnabled": True,
                "supportsOverrides": True,
                "defaultRequiredPermission": default_required_permission,
                "premiumTier": "free",
                "settingsSchema": [],
                "configHints": config_hints,
            }
            return

        existing["type"] = _merge_command_capability_type(str(existing.get("type", "both")), command_type)
        if not str(existing.get("description", "")).strip() and description:
            existing["description"] = description
        if str(existing.get("group", "General")).strip().lower() == "general" and group:
            existing["group"] = group
            existing["category"] = group
        existing_hints = existing.get("configHints", _empty_command_config_hints())
        if not isinstance(existing_hints, dict):
            existing_hints = _empty_command_config_hints()
        existing["configHints"] = _merge_command_config_hints(existing_hints, config_hints)

    for cmd in _bot.tree.get_commands():
        category = _guess_command_category(cmd.name)
        default_permission = "manage_guild" if category == "Admin" else ("moderate_members" if category == "Moderation" else "send_messages")
        upsert_command_entry(
            name=cmd.name,
            description=(getattr(cmd, "description", "") or "").strip(),
            command_type="slash",
            group=category,
            default_required_permission=default_permission,
            config_hints=_infer_slash_command_hints(cmd),
        )

    for cmd in _bot.commands:
        if cmd.hidden:
            continue
        category = _guess_command_category(cmd.name)
        default_permission = "manage_guild" if category == "Admin" else ("moderate_members" if category == "Moderation" else "send_messages")
        upsert_command_entry(
            name=cmd.name,
            description=((cmd.help or cmd.brief or "") or "").strip(),
            command_type="prefix",
            group=cmd.cog_name or "General",
            default_required_permission=default_permission,
            config_hints=_infer_prefix_command_hints(cmd),
        )

    commands_list: List[Dict[str, Any]] = sorted(commands_by_name.values(), key=lambda item: str(item.get("name", "")).lower())

    modules_list: List[Dict[str, Any]] = []
    seen_module_ids: set[str] = set()
    for name, cog in _bot.cogs.items():
        module_id = _COG_TO_MODULE_ID.get(name, _normalize_module_id(name))
        if not module_id or module_id in seen_module_ids:
            continue
        seen_module_ids.add(module_id)

        override = _MODULE_CAPABILITY_OVERRIDES.get(module_id, {})
        module_name = override.get("name", name)
        description = override.get("description", cog.description or f"{name} module")
        category = override.get("category", _guess_module_category(module_name))
        icon_hint = override.get("iconHint", _guess_icon_hint(module_name))
        settings_schema = override.get("settingsSchema", [])

        modules_list.append({
            "id": module_id,
            "name": module_name,
            "description": description,
            "category": category,
            "iconHint": icon_hint,
            "premiumTier": "free",
            "supportsOverrides": bool(override.get("supportsOverrides", False)),
            "settingsSchema": settings_schema if isinstance(settings_schema, list) else [],
        })

    return web.json_response({
        "botVersion": getattr(_bot, "version", "3.3.0"),
        "version": getattr(_bot, "version", "3.3.0"),
        "buildInfo": f"modbot v{getattr(_bot, 'version', '3.3.0')} - live",
        "modules": modules_list,
        "commands": commands_list,
        "eventTypes": _LOG_EVENT_TYPES,
        "permissionCapabilities": [
            "view_dashboard", "view_commands", "manage_commands", "view_modules", "manage_modules",
            "view_logging", "manage_logging", "view_cases", "manage_cases", "view_automod",
            "manage_automod", "manage_permissions", "export_data", "danger_zone_actions",
            "run_sync_operations", "view_audit",
        ],
    })


def _guess_command_category(name: str) -> str:
    mod_cmds = {"ban", "kick", "warn", "timeout", "mute", "unmute", "unban", "case", "cases", "purge", "slowmode", "lock", "unlock"}
    util_cmds = {"help", "ping", "info", "serverinfo", "userinfo", "avatar", "whois", "poll"}
    admin_cmds = {"setup", "settings", "config", "prefix", "blacklist", "whitelist"}
    if name in mod_cmds:
        return "Moderation"
    if name in util_cmds:
        return "Utility"
    if name in admin_cmds:
        return "Admin"
    return "General"


def _guess_module_category(name: str) -> str:
    name_lower = name.lower()
    if any(k in name_lower for k in ["mod", "ban", "warn", "case"]):
        return "Moderation"
    if any(k in name_lower for k in ["auto", "raid", "spam"]):
        return "Protection"
    if any(k in name_lower for k in ["log", "audit"]):
        return "Utility"
    if any(k in name_lower for k in ["ticket", "mail", "report"]):
        return "Support"
    return "General"


def _guess_icon_hint(name: str) -> str:
    name_lower = name.lower()
    if "mod" in name_lower:
        return "Shield"
    if "auto" in name_lower:
        return "Zap"
    if "log" in name_lower:
        return "ScrollText"
    if "raid" in name_lower:
        return "ShieldAlert"
    if "ticket" in name_lower:
        return "Ticket"
    if "verify" in name_lower:
        return "UserCheck"
    return "Package"


async def api_guild_warnings(request: web.Request):
    """Get warnings for a guild."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    if not _bot:
        raise web.HTTPServiceUnavailable()

    try:
        async with _bot.db.get_connection() as db:
            cursor = await db.execute(
                """SELECT * FROM warnings WHERE guild_id = ? ORDER BY created_at DESC LIMIT 50""",
                (int(guild_id),),
            )
            rows = await cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch warnings: {e}")
        rows = []

    warnings = []
    for r in rows:
        warnings.append({
            "id": r[0],
            "userId": str(r[2]),
            "userName": _resolve_user_name(r[2]),
            "moderatorId": str(r[3]),
            "moderatorName": _resolve_user_name(r[3]),
            "reason": r[4] or "No reason",
            "createdAt": r[5],
        })

    return web.json_response({"items": warnings})


async def api_guild_stats(request: web.Request):
    """Get basic stats for a guild."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    guild = _bot.get_guild(int(guild_id)) if _bot else None
    
    # Count cases and warnings from DB
    case_count = 0
    warning_count = 0
    try:
        async with _bot.db.get_connection() as db:
            cursor = await db.execute("SELECT COUNT(*) FROM cases WHERE guild_id = ?", (int(guild_id),))
            row = await cursor.fetchone()
            case_count = row[0] if row else 0
            
            cursor = await db.execute("SELECT COUNT(*) FROM warnings WHERE guild_id = ?", (int(guild_id),))
            row = await cursor.fetchone()
            warning_count = row[0] if row else 0
    except Exception:
        pass

    return web.json_response({
        "memberCount": guild.member_count if guild else 0,
        "channelCount": len(guild.channels) if guild else 0,
        "roleCount": len(guild.roles) if guild else 0,
        "caseCount": case_count,
        "warningCount": warning_count,
        "commandCount": len(list(_bot.tree.get_commands())) if _bot else 0,
        "cogCount": len(_bot.cogs) if _bot else 0,
        "botOnline": _bot is not None and _bot.is_ready(),
    })


async def api_guild_ai_chat(request: web.Request):
    """Handle chat completion requests from the dashboard AI assistant."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    if not _bot:
        raise web.HTTPServiceUnavailable(text=json.dumps({"code": 503, "message": "Bot not ready"}), content_type="application/json")

    if not GEMINI_AVAILABLE:
        raise web.HTTPServiceUnavailable(text=json.dumps({"code": 503, "message": "google-genai SDK not available"}), content_type="application/json")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise web.HTTPServiceUnavailable(text=json.dumps({"code": 503, "message": "Gemini API key not configured"}), content_type="application/json")

    try:
        body = await request.json()
    except Exception:
        raise web.HTTPBadRequest(text=json.dumps({"code": 400, "message": "Invalid JSON"}), content_type="application/json")

    messages = body.get("messages", [])
    if not isinstance(messages, list) or not messages:
        raise web.HTTPBadRequest(text=json.dumps({"code": 400, "message": "Missing 'messages' array"}), content_type="application/json")

    # Get dashboard context values safely
    settings = await _bot.db.get_settings(int(guild_id))
    modules = _build_dashboard_modules(settings)
    guild = _bot.get_guild(int(guild_id))
    
    context_data = {
        "guild": {
            "name": guild.name if guild else "Unknown",
            "memberCount": guild.member_count if guild else 0,
        },
        "botSettings": {
            "commands": _normalize_command_configs_blob(settings.get("commands", {})),
            "modules": modules,
             "loggingEnabled": _coerce_bool(settings.get("logging_enabled"), True),
             "prefix": settings.get("prefix", ",")
        }
    }

    system_prompt = f"""You are the ModBot AI Assistant, helping server administrators manage their Discord server via a web dashboard.
You can view and modify server settings, moderation logs, edit configs, and toggle modules.

CURRENT CONTEXT:
Guild Name: {context_data['guild']['name']}
Member Count: {context_data['guild']['memberCount']}
Current Config Prefix: '{context_data['botSettings']['prefix']}'

When the user asks you to modify a setting or toggle a module, explain what you will do or guide them to the correct setting. You do not have direct function-calling capability in this demo version to update the database, so your primary role is advice, reading current context, and confirming values.

Here is the current state of modules: {json.dumps(context_data['botSettings']['modules'])}
"""

    genai_client = genai.Client(api_key=api_key)
    
    formatted_messages = []
    for msg in messages:
        role = "user" if msg.get("role") == "user" else "model"
        formatted_messages.append({"role": role, "parts": [{"text": str(msg.get("content", ""))}]})
    
    try:
        completion = await aiohttp.to_thread(
            genai_client.models.generate_content,
            model="gemini-2.5-flash",
            contents=formatted_messages,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.4,
            )
        )
        
        reply = completion.text
        return web.json_response({
            "message": {"role": "assistant", "content": reply}
        })
    except APIError as e:
        logger.error(f"Gemini API error during dashboard chat: {e}")
        raise web.HTTPInternalServerError(text=json.dumps({"code": 500, "message": f"AI service error: {str(e)}"}), content_type="application/json")
    except Exception as e:
        logger.error(f"Error during dashboard chat: {e}")
        raise web.HTTPInternalServerError(text=json.dumps({"code": 500, "message": "Failed to process chat"}), content_type="application/json")

# ─── CORS Middleware ──────────────────────────────────────────────────────────

def _parse_origin_csv(value: str) -> List[str]:
    return [entry.strip().rstrip("/") for entry in (value or "").split(",") if entry.strip()]


# Build allowed origins list
_ALLOWED_ORIGINS = set(_parse_origin_csv(os.getenv("CORS_ALLOWED_ORIGINS", "")))
if FRONTEND_PUBLIC_URL:
    _ALLOWED_ORIGINS.add(FRONTEND_PUBLIC_URL.rstrip("/"))
if BACKEND_PUBLIC_URL:
    _ALLOWED_ORIGINS.add(BACKEND_PUBLIC_URL.rstrip("/"))

# Local development defaults
_ALLOWED_ORIGINS.update([
    "http://localhost:3000",
    "http://localhost:5173",
    f"http://localhost:{DASHBOARD_PORT}",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    f"http://127.0.0.1:{DASHBOARD_PORT}",
])

if IS_RENDER:
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if render_url:
        _ALLOWED_ORIGINS.add(render_url)

@web.middleware
async def cors_middleware(request: web.Request, handler):
    """Handle CORS with origin validation."""
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex

    origin = request.headers.get("Origin", "")
    allow_all = _coerce_bool(os.getenv("CORS_ALLOW_ALL"), False)
    if origin and (allow_all or origin.rstrip("/") in _ALLOWED_ORIGINS):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, If-Match"
        response.headers["Access-Control-Expose-Headers"] = "ETag"

    return response


# ─── Static File Serving & SPA Fallback ───────────────────────────────────────

def _setup_static(app: web.Application):
    """Serve Vite dist/ as static files with SPA fallback."""
    dist_dir = Path(__file__).parent.parent / "website" / "dist"
    
    if not dist_dir.exists():
        logger.warning(f"Static files directory not found: {dist_dir}")
        return

    # Serve static assets (JS, CSS, images)
    app.router.add_static("/assets/", dist_dir / "assets", name="static_assets")

    # SPA fallback — serve index.html for all non-API routes
    async def spa_handler(request: web.Request):
        # Also serve any root-level static files (favicon, robots.txt, etc.)
        file_path = dist_dir / request.match_info.get("path", "")
        if file_path.is_file() and file_path.resolve().is_relative_to(dist_dir.resolve()):
            return web.FileResponse(file_path)
        # SPA fallback
        index = dist_dir / "index.html"
        if index.exists():
            return web.FileResponse(index)
        raise web.HTTPNotFound()

    # Add SPA fallback for all non-API, non-auth paths
    app.router.add_get("/{path:.*}", spa_handler)


# ─── App Factory ──────────────────────────────────────────────────────────────

def create_app(bot=None) -> web.Application:
    global _bot
    _bot = bot

    app = web.Application(middlewares=[cors_middleware])

    # Health check (must be before auth routes so Render can reach it)
    app.router.add_get("/health", health_check)

    # Auth routes
    app.router.add_get("/auth/login", auth_login)
    app.router.add_get("/auth/invite", auth_login)
    app.router.add_get("/auth/callback", auth_callback)
    app.router.add_post("/api/auth/logout", auth_logout)

    # API routes
    app.router.add_get("/api/me", api_me)
    app.router.add_get("/api/bot/capabilities", api_bot_capabilities)
    app.router.add_get("/api/guilds", api_guilds)
    app.router.add_get("/api/guilds/{guild_id}/summary", api_guild_summary)
    app.router.add_get("/api/guilds/{guild_id}/channels", api_guild_channels)
    app.router.add_get("/api/guilds/{guild_id}/roles", api_guild_roles)
    app.router.add_get("/api/guilds/{guild_id}/config", api_guild_config)
    app.router.add_put("/api/guilds/{guild_id}/config", api_guild_config_update)
    app.router.add_get("/api/guilds/{guild_id}/setup", api_guild_setup_summary)
    app.router.add_post("/api/guilds/{guild_id}/setup/quickstart", api_guild_setup_quickstart)
    app.router.add_post("/api/guilds/{guild_id}/antiraid/panic", api_guild_antiraid_panic)
    app.router.add_post("/api/guilds/{guild_id}/commands/sync", api_guild_commands_sync)
    app.router.add_get("/api/guilds/{guild_id}/commands/sync/status", api_guild_commands_sync_status)
    app.router.add_get("/api/guilds/{guild_id}/cases", api_guild_cases)
    app.router.add_get("/api/guilds/{guild_id}/cases/{case_id}", api_guild_case)
    app.router.add_get("/api/guilds/{guild_id}/audit", api_guild_audit)
    app.router.add_get("/api/guilds/{guild_id}/warnings", api_guild_warnings)
    app.router.add_get("/api/guilds/{guild_id}/stats", api_guild_stats)
    app.router.add_post("/api/guilds/{guild_id}/ai/chat", api_guild_ai_chat)

    # Static files (production)
    _setup_static(app)

    return app


async def start_dashboard(bot) -> web.AppRunner:
    """Start the dashboard web server. Called from bot.py on_ready."""
    if not CLIENT_ID or not CLIENT_SECRET:
        logger.warning("Dashboard: DISCORD_CLIENT_ID or DISCORD_CLIENT_SECRET not set, skipping")
        return None

    app = create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", DASHBOARD_PORT)
    await site.start()
    
    logger.info(f"Dashboard running on http://0.0.0.0:{DASHBOARD_PORT}")
    if IS_RENDER:
        logger.info(f"Render external URL: {os.getenv('RENDER_EXTERNAL_URL', 'not set')}")
    return runner

