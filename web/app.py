"""
ModBot Web Dashboard
aiohttp-based web server with Discord OAuth2 authentication.
Runs alongside the bot in the same process, sharing the database.
"""

import os
import json
import logging
import secrets
import time
from collections import deque
from pathlib import Path
from urllib.parse import urlencode
from typing import Optional, Dict, Any

import aiohttp
from aiohttp import web

logger = logging.getLogger("ModBot.Dashboard")

# ── Paths ──
WEB_DIR = Path(__file__).parent
TEMPLATE_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

# ── OAuth2 Config ──
DISCORD_API = "https://discord.com/api/v10"
OAUTH2_SCOPES = "identify guilds"


def _get_config() -> dict:
    return {
        "client_id": os.getenv("DISCORD_CLIENT_ID", ""),
        "client_secret": os.getenv("DISCORD_CLIENT_SECRET", ""),
        "redirect_uri": os.getenv("DASHBOARD_REDIRECT_URI", "http://localhost:8080/callback"),
        "secret_key": os.getenv("DASHBOARD_SECRET_KEY", secrets.token_hex(32)),
        "port": int(os.getenv("DASHBOARD_PORT", "8080")),
    }


# ── Session Store ──
_sessions: Dict[str, Dict[str, Any]] = {}

# ── Recent Actions (per guild, in-memory ring buffer) ──
_recent_actions: Dict[int, deque] = {}

def _log_action(guild_id: int, username: str, action: str):
    if guild_id not in _recent_actions:
        _recent_actions[guild_id] = deque(maxlen=50)
    _recent_actions[guild_id].appendleft({
        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "user": username,
        "action": action,
    })


def _create_session(user_data: dict, guilds: list) -> str:
    token = secrets.token_urlsafe(48)
    _sessions[token] = {
        "user": user_data,
        "guilds": guilds,
        "created": time.time(),
    }
    return token


def _get_session(request: web.Request) -> Optional[dict]:
    token = request.cookies.get("session")
    if not token:
        return None
    session = _sessions.get(token)
    if session and time.time() - session["created"] < 86400:
        return session
    if token in _sessions:
        del _sessions[token]
    return None


def _render_template(name: str, **kwargs) -> web.Response:
    path = TEMPLATE_DIR / name
    if not path.exists():
        return web.Response(text=f"Template {name} not found", status=404)
    html = path.read_text(encoding="utf-8")
    for key, value in kwargs.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))
    return web.Response(text=html, content_type="text/html")


def _check_guild_access(session: dict, guild_id: int) -> bool:
    return any(
        int(g["id"]) == guild_id and (int(g.get("permissions", 0)) & 0x28)
        for g in session["guilds"]
    )


# ═══════════════════════════════════════════════════════════════
# PAGE ROUTES
# ═══════════════════════════════════════════════════════════════

async def index(request: web.Request) -> web.Response:
    session = _get_session(request)
    if session:
        raise web.HTTPFound("/dashboard")
    return _render_template("index.html")


async def login(request: web.Request) -> web.Response:
    config = _get_config()
    params = urlencode({
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": OAUTH2_SCOPES,
    })
    raise web.HTTPFound(f"https://discord.com/oauth2/authorize?{params}")


async def callback(request: web.Request) -> web.Response:
    code = request.query.get("code")
    if not code:
        raise web.HTTPFound("/?error=no_code")

    config = _get_config()

    async with aiohttp.ClientSession() as cs:
        token_resp = await cs.post(
            f"{DISCORD_API}/oauth2/token",
            data={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": config["redirect_uri"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status != 200:
            raise web.HTTPFound("/?error=token_failed")

        token_data = await token_resp.json()
        access_token = token_data["access_token"]

        headers = {"Authorization": f"Bearer {access_token}"}
        user_resp = await cs.get(f"{DISCORD_API}/users/@me", headers=headers)
        user_data = await user_resp.json()

        guilds_resp = await cs.get(f"{DISCORD_API}/users/@me/guilds", headers=headers)
        guilds = await guilds_resp.json()

    session_token = _create_session(user_data, guilds)

    response = web.HTTPFound("/dashboard")
    response.set_cookie("session", session_token, max_age=86400, httponly=True, samesite="Lax")
    raise response


async def logout(request: web.Request) -> web.Response:
    token = request.cookies.get("session")
    if token and token in _sessions:
        del _sessions[token]
    response = web.HTTPFound("/")
    response.del_cookie("session")
    raise response


async def dashboard(request: web.Request) -> web.Response:
    session = _get_session(request)
    if not session:
        raise web.HTTPFound("/login")

    bot = request.app["bot"]
    user = session["user"]

    manageable_guilds = []
    for g in session["guilds"]:
        perms = int(g.get("permissions", 0))
        has_manage = (perms & 0x20) == 0x20
        has_admin = (perms & 0x8) == 0x8
        bot_guild = bot.get_guild(int(g["id"]))

        if (has_manage or has_admin) and bot_guild:
            manageable_guilds.append({
                "id": g["id"],
                "name": g["name"],
                "icon": g.get("icon", ""),
                "members": bot_guild.member_count or 0,
            })

    guilds_html = ""
    for g in manageable_guilds:
        icon_url = f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png?size=128" if g["icon"] else "https://cdn.discordapp.com/embed/avatars/0.png"
        guilds_html += f'''
        <a href="/guild/{g['id']}" class="guild-card">
            <img src="{icon_url}" alt="{g['name']}" class="guild-icon">
            <div class="guild-info">
                <h3>{g['name']}</h3>
                <span class="guild-members">{g['members']:,} members</span>
            </div>
            <svg class="arrow-icon" viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z"/></svg>
        </a>
        '''

    avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png?size=64" if user.get("avatar") else "https://cdn.discordapp.com/embed/avatars/0.png"

    return _render_template(
        "dashboard.html",
        username=user["username"],
        avatar_url=avatar_url,
        guild_count=len(manageable_guilds),
        guilds_html=guilds_html,
    )


async def guild_settings(request: web.Request) -> web.Response:
    session = _get_session(request)
    if not session:
        raise web.HTTPFound("/login")

    guild_id = int(request.match_info["guild_id"])
    bot = request.app["bot"]
    guild = bot.get_guild(guild_id)

    if not guild:
        return web.Response(text="Guild not found", status=404)

    if not _check_guild_access(session, guild_id):
        return web.Response(text="Access denied", status=403)

    icon_url = str(guild.icon.url) if guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png"
    bot_member = guild.get_member(bot.user.id)
    bot_nick = bot_member.display_name if bot_member else bot.user.name

    return _render_template(
        "guild.html",
        guild_name=guild.name,
        guild_icon=icon_url,
        guild_id=guild_id,
        member_count=guild.member_count or 0,
        bot_nickname=bot_nick,
    )


# ═══════════════════════════════════════════════════════════════
# REST API
# ═══════════════════════════════════════════════════════════════

ALLOWED_KEYS = {
    # AutoMod
    "automod_enabled", "automod_links_enabled", "automod_invites_enabled",
    "automod_scam_protection", "automod_ai_enabled", "automod_notify_users",
    "automod_spam_threshold", "automod_duplicate_threshold",
    "automod_caps_percentage", "automod_caps_min_length",
    "automod_max_mentions", "automod_newaccount_days",
    "automod_punishment", "automod_mute_duration", "automod_tempban_duration",
    "automod_ban_delete_days",
    "automod_log_channel", "automod_bypass_role_id", "automod_quarantine_role_id",
    "automod_bypass_channels", "automod_temp_bypass",
    "automod_badwords", "automod_whitelisted_domains",
    "automod_links_whitelist", "automod_allowed_invites",
    "automod_ai_min_severity",
    # Logging
    "log_channel_mod", "log_channel_audit", "log_channel_message",
    "log_channel_voice", "log_channel_automod", "log_channel_report",
    "log_channel_ticket",
    # General / Roles
    "prefix", "mute_role", "manager_role", "mod_log_channel",
    "forum_alert_channel",
    "owner_role", "admin_role", "moderator_role", "helper_role",
    "whitelisted_role",
    # Voice
    "voice_afk_detection", "voice_afk_timeout", "afk_response_timeout",
    "voice_ignored_channels",
    # Verification
    "verification_enabled", "verification_channel", "verification_role",
    # Tickets
    "ticket_category", "ticket_support_role", "ticket_log_channel",
    # Antiraid
    "antiraid_enabled", "antiraid_join_threshold", "antiraid_join_interval",
    "antiraid_action",
}


async def api_get_settings(request: web.Request) -> web.Response:
    session = _get_session(request)
    if not session:
        return web.json_response({"error": "unauthorized"}, status=401)

    guild_id = int(request.match_info["guild_id"])
    bot = request.app["bot"]

    if not _check_guild_access(session, guild_id):
        return web.json_response({"error": "forbidden"}, status=403)

    guild = bot.get_guild(guild_id)
    if not guild:
        return web.json_response({"error": "guild_not_found"}, status=404)

    settings = await bot.db.get_settings(guild_id)

    roles = [{"id": str(r.id), "name": r.name, "color": str(r.color)} for r in guild.roles if not r.is_default()]
    channels = [{"id": str(c.id), "name": c.name} for c in guild.text_channels]
    voice_channels = [{"id": str(c.id), "name": c.name} for c in guild.voice_channels]

    bot_member = guild.get_member(bot.user.id)
    bot_nick = bot_member.display_name if bot_member else bot.user.name

    return web.json_response({
        "settings": settings,
        "roles": roles,
        "channels": channels,
        "voice_channels": voice_channels,
        "bot_nickname": bot_nick,
        "member_count": guild.member_count or 0,
    })


async def api_update_settings(request: web.Request) -> web.Response:
    session = _get_session(request)
    if not session:
        return web.json_response({"error": "unauthorized"}, status=401)

    guild_id = int(request.match_info["guild_id"])
    bot = request.app["bot"]

    if not _check_guild_access(session, guild_id):
        return web.json_response({"error": "forbidden"}, status=403)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "invalid_json"}, status=400)

    updates = body.get("settings", {})
    if not isinstance(updates, dict):
        return web.json_response({"error": "settings must be an object"}, status=400)

    current = await bot.db.get_settings(guild_id)

    changed = []
    for key, value in updates.items():
        if key in ALLOWED_KEYS:
            current[key] = value
            changed.append(key)

    await bot.db.update_settings(guild_id, current)

    username = session["user"].get("username", "Unknown")
    for key in changed:
        _log_action(guild_id, username, f"settings.update: {key}")

    return web.json_response({"ok": True, "settings": current})


async def api_get_cases(request: web.Request) -> web.Response:
    session = _get_session(request)
    if not session:
        return web.json_response({"error": "unauthorized"}, status=401)

    guild_id = int(request.match_info["guild_id"])
    bot = request.app["bot"]

    if not _check_guild_access(session, guild_id):
        return web.json_response({"error": "forbidden"}, status=403)

    limit = min(int(request.query.get("limit", "25")), 100)

    try:
        async with bot.db.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM cases WHERE guild_id = ? ORDER BY created_at DESC LIMIT ?",
                (guild_id, limit),
            )
            rows = await cursor.fetchall()
            cases = [
                {
                    "case_number": r[2],
                    "user_id": str(r[3]),
                    "moderator_id": str(r[4]),
                    "action": r[5],
                    "reason": r[6],
                    "duration": r[7],
                    "created_at": r[8],
                    "active": bool(r[9]),
                }
                for r in rows
            ]
    except Exception:
        cases = []

    return web.json_response({"cases": cases})


async def api_get_stats(request: web.Request) -> web.Response:
    session = _get_session(request)
    if not session:
        return web.json_response({"error": "unauthorized"}, status=401)

    guild_id = int(request.match_info["guild_id"])
    bot = request.app["bot"]

    if not _check_guild_access(session, guild_id):
        return web.json_response({"error": "forbidden"}, status=403)

    stats = {}
    try:
        async with bot.db.get_connection() as db:
            for table, key in [("cases", "total_cases"), ("warnings", "total_warnings"), ("reports", "total_reports"), ("tickets", "total_tickets")]:
                cursor = await db.execute(f"SELECT COUNT(*) FROM {table} WHERE guild_id = ?", (guild_id,))
                row = await cursor.fetchone()
                stats[key] = row[0] if row else 0

            cursor = await db.execute(
                "SELECT action, COUNT(*) FROM cases WHERE guild_id = ? GROUP BY action",
                (guild_id,),
            )
            stats["actions_breakdown"] = {r[0]: r[1] for r in await cursor.fetchall()}
    except Exception:
        stats = {"total_cases": 0, "total_warnings": 0, "total_reports": 0, "total_tickets": 0, "actions_breakdown": {}}

    return web.json_response({"stats": stats})


async def api_get_recent_actions(request: web.Request) -> web.Response:
    session = _get_session(request)
    if not session:
        return web.json_response({"error": "unauthorized"}, status=401)

    guild_id = int(request.match_info["guild_id"])
    if not _check_guild_access(session, guild_id):
        return web.json_response({"error": "forbidden"}, status=403)

    actions = list(_recent_actions.get(guild_id, []))
    return web.json_response({"actions": actions})


# ═══════════════════════════════════════════════════════════════
# APP FACTORY
# ═══════════════════════════════════════════════════════════════

def create_app(bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot

    # Pages
    app.router.add_get("/", index)
    app.router.add_get("/login", login)
    app.router.add_get("/callback", callback)
    app.router.add_get("/logout", logout)
    app.router.add_get("/dashboard", dashboard)
    app.router.add_get("/guild/{guild_id}", guild_settings)

    # API
    app.router.add_get("/api/guild/{guild_id}/settings", api_get_settings)
    app.router.add_post("/api/guild/{guild_id}/settings", api_update_settings)
    app.router.add_get("/api/guild/{guild_id}/cases", api_get_cases)
    app.router.add_get("/api/guild/{guild_id}/stats", api_get_stats)
    app.router.add_get("/api/guild/{guild_id}/actions", api_get_recent_actions)

    # Static files
    if STATIC_DIR.exists():
        app.router.add_static("/static", STATIC_DIR, name="static")

    return app


async def start_dashboard(bot, port: int = None):
    config = _get_config()
    port = port or config["port"]

    if not config["client_id"] or not config["client_secret"]:
        logger.warning("Dashboard disabled: DISCORD_CLIENT_ID and/or DISCORD_CLIENT_SECRET not set")
        return None

    app = create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Dashboard running at http://localhost:{port}")
    return runner
