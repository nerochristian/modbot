"""
ModBot Web Dashboard — aiohttp API server
Runs inside the bot process, uses bot.db and bot.guilds for real data.
Serves the Vite dist/ as static files in production.
Render-compatible: reads PORT env var, adds /health endpoint, secure cookies.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import web

logger = logging.getLogger("ModBot.Dashboard")

# ─── Configuration ────────────────────────────────────────────────────────────

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("DASHBOARD_REDIRECT_URI", "http://localhost:10547/auth/callback")

# Render sets PORT; fall back to DASHBOARD_PORT, then 10547
DASHBOARD_PORT = int(os.getenv("PORT", os.getenv("DASHBOARD_PORT", "10547")))

SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))

# Detect Render environment (Render always sets RENDER=true)
IS_RENDER = os.getenv("RENDER", "").lower() in ("true", "1", "yes")

# Frontend URL — where the Vite SPA is served from (Render static site, or localhost)
FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    os.getenv("RENDER_EXTERNAL_URL", "http://localhost:3000"),
)

# Cross-origin mode: API and frontend on different domains
IS_CROSS_ORIGIN = bool(os.getenv("FRONTEND_URL"))

DISCORD_API = "https://discord.com/api/v10"
DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"

# In-memory session store  {session_id: {user data, access_token, expires_at}}
_sessions: Dict[str, Dict[str, Any]] = {}

# Bot reference (set by start_dashboard)
_bot = None


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
    redirect = REDIRECT_URI
    oauth_url = (
        f"{DISCORD_OAUTH_URL}?client_id={CLIENT_ID}"
        f"&redirect_uri={aiohttp.helpers.quote(redirect, safe='')}"
        f"&response_type=code&scope=identify+guilds"
    )
    raise web.HTTPFound(oauth_url)


async def auth_callback(request: web.Request):
    """Handle Discord OAuth2 callback — exchange code, fetch user, create session."""
    code = request.query.get("code")
    error = request.query.get("error")

    # After auth, redirect to the FRONTEND (Render static site or localhost)
    base_url = FRONTEND_URL.rstrip("/")

    if error:
        raise web.HTTPFound(f"{base_url}/?error={error}")

    if not code:
        raise web.HTTPFound(f"{base_url}/?error=no_code")

    # Exchange code for tokens
    async with aiohttp.ClientSession() as http:
        token_resp = await http.post(DISCORD_TOKEN_URL, data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})

        if token_resp.status != 200:
            logger.error(f"Token exchange failed: {await token_resp.text()}")
            raise web.HTTPFound(f"{base_url}/?error=token_exchange_failed")

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

    # Set cookie and redirect to dashboard on the frontend
    signed = _sign_session(session_id)
    response = web.HTTPFound(f"{base_url}/dashboard")
    # Cross-origin cookies need SameSite=None + Secure
    samesite = "None" if IS_CROSS_ORIGIN else "Lax"
    secure = IS_CROSS_ORIGIN or IS_RENDER
    response.set_cookie(
        "modbot_session", signed, max_age=expires_in,
        httponly=True, samesite=samesite, path="/",
        secure=secure,
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
    user_guilds = session.get("guilds", [])

    # Filter to guilds where the bot is actually present
    bot_guild_ids = {str(g.id) for g in _bot.guilds} if _bot else set()
    
    guilds = []
    for g in user_guilds:
        permissions = int(g.get("permissions", 0))
        has_manage = bool(permissions & 0x20 or permissions & 0x8 or g.get("owner"))
        bot_installed = str(g["id"]) in bot_guild_ids
        
        # Only show guilds user can manage OR where bot is installed
        if has_manage or bot_installed:
            icon = g.get("icon")
            icon_url = f"https://cdn.discordapp.com/icons/{g['id']}/{icon}.png" if icon else None
            guilds.append({
                "id": g["id"],
                "name": g["name"],
                "icon": icon_url,
                "memberCount": _get_guild_member_count(g["id"]),
                "botInstalled": bot_installed,
                "canManage": has_manage,
            })

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


def _get_guild_member_count(guild_id: str) -> int:
    if not _bot:
        return 0
    guild = _bot.get_guild(int(guild_id))
    return guild.member_count if guild else 0


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


async def api_guild_config(request: web.Request):
    """Get guild settings from database."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    if not _bot:
        raise web.HTTPServiceUnavailable(text=json.dumps({"code": 503, "message": "Bot not ready"}),
                                          content_type="application/json")

    settings = await _bot.db.get_settings(int(guild_id))
    
    # Build a full config response
    guild = _bot.get_guild(int(guild_id))
    config = {
        "guildId": guild_id,
        "version": 1,
        "prefix": settings.get("prefix", ","),
        "settings": settings,
        "commands": {},
        "modules": {},
        "logging": {},
        "permissions": {
            "dashboardRoleMappings": settings.get("dashboard_role_mappings", []),
        },
    }

    return web.json_response(config)


async def api_guild_config_update(request: web.Request):
    """Update guild settings in database."""
    session = _require_auth(request)
    guild_id = request.match_info["guild_id"]
    _require_guild_access(session, guild_id)

    if not _bot:
        raise web.HTTPServiceUnavailable(text=json.dumps({"code": 503, "message": "Bot not ready"}),
                                          content_type="application/json")

    body = await request.json()
    settings = body.get("settings", {})
    
    await _bot.db.update_settings(int(guild_id), settings)
    
    # Return updated config
    updated = await _bot.db.get_settings(int(guild_id))
    config = {
        "guildId": guild_id,
        "version": 2,
        "prefix": updated.get("prefix", ","),
        "settings": updated,
        "commands": {},
        "modules": {},
        "logging": {},
        "permissions": {
            "dashboardRoleMappings": updated.get("dashboard_role_mappings", []),
        },
    }

    return web.json_response(config)


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
            "action": r[5],
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
        "action": case["action"],
        "reason": case["reason"] or "No reason provided",
        "duration": case["duration"],
        "createdAt": case["created_at"],
        "active": bool(case.get("active", True)),
    })


def _resolve_user_name(user_id: int) -> str:
    """Try to get a username from the bot's user cache."""
    if not _bot:
        return f"User#{user_id}"
    user = _bot.get_user(int(user_id))
    if user:
        return user.display_name or user.name
    return f"User#{user_id}"


async def api_bot_capabilities(request: web.Request):
    """Return bot capabilities — loaded cogs, commands, version."""
    _require_auth(request)

    if not _bot:
        raise web.HTTPServiceUnavailable()

    # Build commands list from loaded bot commands
    commands_list = []
    for cmd in _bot.tree.get_commands():
        commands_list.append({
            "name": cmd.name,
            "description": getattr(cmd, "description", "") or "",
            "type": "slash",
            "category": _guess_command_category(cmd.name),
            "defaultEnabled": True,
        })
    
    # Also add prefix commands
    for cmd in _bot.commands:
        if cmd.hidden:
            continue
        cog_name = cmd.cog_name or "General"
        commands_list.append({
            "name": cmd.name,
            "description": cmd.help or cmd.brief or "",
            "type": "prefix",
            "category": cog_name,
            "defaultEnabled": True,
        })

    # Build modules from loaded cogs
    modules_list = []
    for name, cog in _bot.cogs.items():
        modules_list.append({
            "id": name.lower().replace(" ", "_"),
            "name": name,
            "description": cog.description or f"{name} module",
            "category": _guess_module_category(name),
            "iconHint": _guess_icon_hint(name),
            "premiumTier": "free",
            "supportsOverrides": False,
            "settingsSchema": [],
        })

    return web.json_response({
        "botVersion": getattr(_bot, "version", "3.3.0"),
        "modules": modules_list,
        "commands": commands_list,
        "eventTypes": [],
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


# ─── CORS Middleware ──────────────────────────────────────────────────────────

# Build allowed origins list
_ALLOWED_ORIGINS = set()

# Always allow the configured frontend URL
if FRONTEND_URL:
    _ALLOWED_ORIGINS.add(FRONTEND_URL.rstrip("/"))

if IS_RENDER:
    _render_url = os.getenv("RENDER_EXTERNAL_URL", "")
    if _render_url:
        _ALLOWED_ORIGINS.add(_render_url.rstrip("/"))
else:
    # Local development — allow common dev ports
    _ALLOWED_ORIGINS.update([
        "http://localhost:3000",
        "http://localhost:5173",
        f"http://localhost:{DASHBOARD_PORT}",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        f"http://127.0.0.1:{DASHBOARD_PORT}",
    ])


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
    if origin and (origin.rstrip("/") in _ALLOWED_ORIGINS or not IS_RENDER):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, If-Match"

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
    app.router.add_get("/auth/callback", auth_callback)
    app.router.add_post("/api/auth/logout", auth_logout)

    # API routes
    app.router.add_get("/api/me", api_me)
    app.router.add_get("/api/bot/capabilities", api_bot_capabilities)
    app.router.add_get("/api/guilds/{guild_id}/channels", api_guild_channels)
    app.router.add_get("/api/guilds/{guild_id}/roles", api_guild_roles)
    app.router.add_get("/api/guilds/{guild_id}/config", api_guild_config)
    app.router.add_put("/api/guilds/{guild_id}/config", api_guild_config_update)
    app.router.add_get("/api/guilds/{guild_id}/cases", api_guild_cases)
    app.router.add_get("/api/guilds/{guild_id}/cases/{case_id}", api_guild_case)
    app.router.add_get("/api/guilds/{guild_id}/warnings", api_guild_warnings)
    app.router.add_get("/api/guilds/{guild_id}/stats", api_guild_stats)

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
