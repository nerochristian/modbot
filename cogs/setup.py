"""
Setup command - Creates all necessary channels, roles, and configurations
(WITH SUPERVISOR + COURT + MODMAIL)
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from typing import Optional, List, Dict

from utils.embeds import ModEmbed
from utils.checks import get_owner_ids, is_admin
from utils.components_v2 import layout_view_from_embeds
from utils.status_emojis import apply_status_emoji_overrides
from config import Config

# ---------------------------------------------------------------------------
# Role / channel definitions
# ---------------------------------------------------------------------------

STAFF_ROLE_KEYS = [
    "owner_role", "manager_role", "admin_role", "supervisor_role",
    "senior_mod_role", "mod_role", "trial_mod_role", "staff_role",
]

LEADERSHIP_KEYS = ["owner_role", "manager_role", "admin_role", "supervisor_role"]

ROLES_TO_CREATE = [
    {"name": "Owner",            "color": discord.Color.from_rgb(74, 0, 0),    "permissions": discord.Permissions(administrator=True), "hoist": True, "setting_key": "owner_role"},
    {"name": "Manager",          "color": discord.Color.from_rgb(114, 0, 0),   "permissions": discord.Permissions(administrator=True), "hoist": True, "setting_key": "manager_role"},
    {"name": "Admin",            "color": discord.Color.from_rgb(153, 0, 0),   "permissions": discord.Permissions(administrator=True), "hoist": True, "setting_key": "admin_role"},
    {"name": "Supervisor",       "color": discord.Color.from_rgb(204, 0, 0),   "permissions": discord.Permissions(kick_members=True, ban_members=True, manage_messages=True, manage_channels=True, manage_nicknames=True, mute_members=True, deafen_members=True, move_members=True, view_audit_log=True, manage_threads=True, moderate_members=True), "hoist": True, "setting_key": "supervisor_role"},
    {"name": "Senior Moderator", "color": discord.Color.from_rgb(255, 0, 0),   "permissions": discord.Permissions(kick_members=True, ban_members=True, manage_messages=True, manage_channels=True, manage_nicknames=True, mute_members=True, deafen_members=True, move_members=True, view_audit_log=True, manage_threads=True, moderate_members=True), "hoist": True, "setting_key": "senior_mod_role"},
    {"name": "Moderator",        "color": discord.Color.from_rgb(255, 77, 77), "permissions": discord.Permissions(kick_members=True, manage_messages=True, manage_nicknames=True, mute_members=True, move_members=True, view_audit_log=True, manage_threads=True, moderate_members=True), "hoist": True, "setting_key": "mod_role"},
    {"name": "Trial Moderator",  "color": discord.Color.from_rgb(255, 128, 128), "permissions": discord.Permissions(manage_messages=True, manage_nicknames=True, mute_members=True, moderate_members=True), "hoist": True, "setting_key": "trial_mod_role"},
    {"name": "Staff",            "color": discord.Color.from_rgb(255, 179, 179), "permissions": discord.Permissions(view_audit_log=True, manage_messages=True, mute_members=True), "hoist": True, "setting_key": "staff_role"},
    {"name": "Muted",            "color": discord.Color.dark_gray(),            "permissions": discord.Permissions.none(), "hoist": False, "setting_key": "muted_role"},
    {"name": "Quarantined",      "color": discord.Color.darker_grey(),          "permissions": discord.Permissions.none(), "hoist": False, "setting_key": "automod_quarantine_role_id"},
    {"name": "unverified",       "color": discord.Color.darker_grey(),          "permissions": discord.Permissions.none(), "hoist": False, "setting_key": "unverified_role"},
    {"name": "verified",         "color": discord.Color.green(),                "permissions": discord.Permissions.none(), "hoist": False, "setting_key": "verified_role"},
    {"name": "log-access",       "color": discord.Color.teal(),                 "permissions": discord.Permissions.none(), "hoist": False, "setting_key": "log_access_role"},
    {"name": "Whitelisted",      "color": discord.Color.gold(),                 "permissions": discord.Permissions.none(), "hoist": False, "setting_key": "whitelisted_role"},
    {"name": "Bypass",           "color": discord.Color.dark_teal(),            "permissions": discord.Permissions.none(), "hoist": False, "setting_key": "automod_bypass_role_id"},
]

LOG_CHANNELS = [
    {"name": "mod-logs",        "setting_key": "mod_log_channel",        "topic": "Moderation action logs"},
    {"name": "audit-logs",      "setting_key": "audit_log_channel",      "topic": "Server audit logs"},
    {"name": "message-logs",    "setting_key": "message_log_channel",    "topic": "Deleted/edited message logs"},
    {"name": "voice-logs",      "setting_key": "voice_log_channel",      "topic": "Voice channel activity logs"},
    {"name": "automod-logs",    "setting_key": "automod_log_channel",    "topic": "AutoMod filter trigger logs"},
    {"name": "emoji-logs",      "setting_key": "emoji_log_channel",      "topic": "Emoji add requests and approvals"},
    {"name": "report-logs",     "setting_key": "report_log_channel",     "topic": "User report logs"},
    {"name": "ticket-logs",     "setting_key": "ticket_log_channel",     "topic": "Ticket transcript logs"},
    {"name": "court-logs",      "setting_key": "court_log_channel",      "topic": "Court session transcript logs"},
    {"name": "modmail-logs",    "setting_key": "modmail_log_channel",    "topic": "Modmail transcripts and events"},
    {"name": "forum-alerts",    "setting_key": "forum_alerts_channel",   "topic": "Flagged forum recommendations with moderation actions"},
    {"name": "ai-confirmation", "setting_key": "ai_confirmation_channel","topic": "AI moderation confirmation requests"},
]

LOG_CHANNEL_KEY_ALIASES: Dict[str, tuple[str, ...]] = {
    "mod_log_channel": ("mod_log_channel", "log_channel_mod"),
    "audit_log_channel": ("audit_log_channel", "log_channel_audit"),
    "message_log_channel": ("message_log_channel", "log_channel_message"),
    "voice_log_channel": ("voice_log_channel", "log_channel_voice"),
    "automod_log_channel": ("automod_log_channel", "log_channel_automod"),
    "report_log_channel": ("report_log_channel", "log_channel_report"),
    "ticket_log_channel": ("ticket_log_channel", "log_channel_ticket"),
}

DASHBOARD_ROLE_CAPABILITIES: Dict[str, List[str]] = {
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
}

STAFF_CHANNELS = [
    {"name": "staff-chat",          "setting_key": "staff_chat_channel",          "topic": "General staff discussion"},
    {"name": "staff-commands",      "setting_key": "staff_commands_channel",      "topic": "Bot commands for staff"},
    {"name": "staff-announcements", "setting_key": "staff_announcements_channel", "topic": "Important staff announcements"},
    {"name": "staff-updates",       "setting_key": "staff_updates_channel",       "topic": "Staff promotions and demotions"},
    {"name": "staff-sanctions",     "setting_key": "staff_sanctions_channel",     "topic": "Staff sanction logs"},
    {"name": "staff-guide",         "setting_key": "staff_guide_channel",         "topic": "Staff guidelines and rules"},
    {"name": "supervisor-logs",     "setting_key": "supervisor_log_channel",      "topic": "Supervisor action logs"},
]

NON_STAFF_SETTING_KEYS = {"muted_role", "automod_quarantine_role_id", "unverified_role", "verified_role"}

DEFAULT_RULES = [
    "Be respectful to all members",
    "No spam or self-promotion",
    "No NSFW content",
    "No harassment or bullying",
    "Follow Discord's Terms of Service",
    "Listen to staff members",
    "Use channels for their intended purpose",
    "No excessive caps or emojis",
    "English only in main channels",
    "Have fun!",
]

DEFAULT_STAFF_GUIDE = {
    "welcome": "Welcome to the Staff Team! This guide will help you understand your responsibilities.",
    "sections": [
        {"title": "📋 General Guidelines",  "content": ["Always remain professional and respectful", "Never abuse your powers", "Document all moderation actions", "Consult senior staff when unsure", "Be active and responsive"]},
        {"title": "⚠️ Warning System",      "content": ["1st offense: Verbal warning", "2nd offense: Written warning", "3rd offense: Mute (1 hour)", "4th offense: Mute (24 hours)", "5th offense: Ban consideration"]},
        {"title": "👁️ Supervisor System",   "content": ["Supervisors oversee all staff members", "3 Warnings = 1 Strike", "3 Strikes = 7 Day Staff Ban", "Supervisors can sanction ANY staff member", "All sanctions are logged and tracked"]},
        {"title": "⚖️ Court System",        "content": ["Use /court to start a formal court session", "All messages are recorded in transcripts", "Use /closecourtcase to end and save transcript", "Transcripts are saved to #court-logs", "Use for serious cases requiring documentation"]},
        {"title": "📬 Modmail System",       "content": ["Users DM the bot '.modmail' to open tickets", "Use /modmail reply to respond to threads", "Use /modmail close to close threads", "All threads are logged with transcripts", "Be professional and helpful in responses"]},
    ],
}


class Setup(commands.Cog):
    set_group = app_commands.Group(name="set", description="Set up role and channel mappings")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_roles(guild: discord.Guild, settings: dict, keys: List[str]) -> List[discord.Role]:
        """Resolve a list of setting keys to actual Role objects, deduped."""
        roles, seen = [], set()
        for key in keys:
            rid = settings.get(key)
            if not rid:
                continue
            try:
                role = guild.get_role(int(rid))
            except (TypeError, ValueError):
                role = None
            if role and role.id not in seen:
                roles.append(role)
                seen.add(role.id)
        return roles

    @staticmethod
    def _staff_overwrites(guild: discord.Guild, staff_roles: List[discord.Role], *, send: bool = True) -> Dict:
        """Build permission overwrites that hide a channel from @everyone but allow staff."""
        ow = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        for r in staff_roles:
            ow[r] = discord.PermissionOverwrite(view_channel=True, send_messages=send, read_message_history=True)
        return ow

    async def _update_progress(self, interaction: discord.Interaction, section: str):
        """Best-effort progress update."""
        try:
            embed = ModEmbed.info("Setup in Progress", f"**{section}**...")
            try:
                embed = await apply_status_emoji_overrides(embed, interaction.guild)
            except Exception:
                pass
            await interaction.edit_original_response(embed=embed)
        except Exception:
            pass

    @staticmethod
    def _dashboard_mapping(role_id: int, dashboard_role: str) -> Dict[str, object]:
        return {
            "roleId": str(role_id),
            "dashboardRole": dashboard_role,
            "capabilities": DASHBOARD_ROLE_CAPABILITIES.get(dashboard_role, []),
        }

    @staticmethod
    def _to_int(value: object) -> Optional[int]:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _sync_dashboard_role_mappings(self, settings: dict, owner_role_id: int, admin_role_id: int, moderator_role_id: int) -> None:
        preserved: List[Dict[str, object]] = []
        for entry in settings.get("dashboardRoleMappings", []):
            if not isinstance(entry, dict):
                continue
            role_name = str(entry.get("dashboardRole", "")).lower()
            if role_name in {"owner", "admin", "moderator"}:
                continue
            preserved.append(entry)

        preserved.extend(
            [
                self._dashboard_mapping(owner_role_id, "owner"),
                self._dashboard_mapping(admin_role_id, "admin"),
                self._dashboard_mapping(moderator_role_id, "moderator"),
            ]
        )
        settings["dashboardRoleMappings"] = preserved

    def _sync_staff_role_lists(self, settings: dict) -> None:
        mod_role_ids = []
        for key in ["admin_role", "supervisor_role", "senior_mod_role", "mod_role", "trial_mod_role", "staff_role"]:
            role_id = self._to_int(settings.get(key))
            if role_id and role_id not in mod_role_ids:
                mod_role_ids.append(role_id)
        settings["mod_roles"] = mod_role_ids
        settings["admin_roles"] = [settings["admin_role"]] if self._to_int(settings.get("admin_role")) else []
        settings["supervisor_roles"] = [settings["supervisor_role"]] if self._to_int(settings.get("supervisor_role")) else []

    # ------------------------------------------------------------------
    # Role creation
    # ------------------------------------------------------------------

    async def _create_roles(self, guild: discord.Guild, settings: dict, created: List[str], errors: List[str]):
        for cfg in ROLES_TO_CREATE:
            try:
                final_name = cfg["name"]
                final_icon = None

                # Try loading a custom icon
                icon_bytes = None
                icon_path = f"icons/{cfg.get('setting_key', 'unknown')}.png"
                if os.path.exists(icon_path):
                    try:
                        with open(icon_path, "rb") as f:
                            icon_bytes = f.read()
                    except Exception:
                        pass

                if icon_bytes:
                    if "ROLE_ICONS" in guild.features:
                        final_icon = icon_bytes
                    else:
                        emoji_name = f"role_icon_{cfg.get('setting_key', 'unknown')}"[:32]
                        emoji = discord.utils.get(guild.emojis, name=emoji_name)
                        if not emoji:
                            try:
                                emoji = await guild.create_custom_emoji(name=emoji_name, image=icon_bytes, reason="ModBot Setup: Role Icon Fallback")
                            except Exception:
                                pass
                        if emoji:
                            final_name = f"{emoji} {cfg['name']}"

                # Find existing role
                existing = None
                stored_id = settings.get(cfg["setting_key"])
                if stored_id:
                    existing = guild.get_role(int(stored_id))
                if not existing:
                    existing = discord.utils.get(guild.roles, name=cfg["name"])
                if not existing and final_name != cfg["name"]:
                    existing = discord.utils.get(guild.roles, name=final_name)

                if existing:
                    # Update existing role
                    if cfg["setting_key"] == "owner_role":
                        try:
                            await existing.edit(name=final_name, permissions=discord.Permissions.all(), color=cfg["color"], hoist=cfg["hoist"], display_icon=final_icon, reason="ModBot Setup: enforce Owner role")
                        except Exception:
                            try:
                                await existing.edit(name=final_name, permissions=discord.Permissions.all(), color=cfg["color"], hoist=cfg["hoist"], reason="ModBot Setup: enforce Owner role")
                            except Exception:
                                pass
                    elif cfg["setting_key"] in NON_STAFF_SETTING_KEYS:
                        try:
                            await existing.edit(name=final_name, permissions=discord.Permissions.none(), color=cfg["color"], hoist=cfg["hoist"], reason="ModBot Setup: enforce non-staff permissions")
                        except Exception:
                            pass
                    else:
                        try:
                            await existing.edit(name=final_name, display_icon=final_icon, reason="ModBot Setup: update role icon")
                        except Exception:
                            pass

                    settings[cfg["setting_key"]] = existing.id
                    created.append(f"✅ {existing.mention} (exists)")
                else:
                    perms = discord.Permissions.all() if cfg["setting_key"] == "owner_role" else cfg["permissions"]
                    try:
                        role = await guild.create_role(name=final_name, color=cfg["color"], permissions=perms, hoist=cfg["hoist"], display_icon=final_icon, reason="ModBot Setup")
                    except Exception:
                        role = await guild.create_role(name=final_name, color=cfg["color"], permissions=perms, hoist=cfg["hoist"], reason="ModBot Setup")
                    settings[cfg["setting_key"]] = role.id
                    created.append(f"✅ {role.mention}")
            except Exception as e:
                errors.append(f"❌ Failed to create role {cfg['name']}: {e}")

        # Sync aliases
        if settings.get("muted_role") and not settings.get("mute_role"):
            settings["mute_role"] = settings["muted_role"]
        elif settings.get("mute_role") and not settings.get("muted_role"):
            settings["muted_role"] = settings["mute_role"]
        if settings.get("automod_quarantine_role_id") and not settings.get("antiraid_quarantine_role"):
            settings["antiraid_quarantine_role"] = settings["automod_quarantine_role_id"]

    async def _ensure_required_setup_roles(
        self,
        guild: discord.Guild,
        settings: dict,
        created: List[str],
        errors: List[str],
    ):
        """Ensure core moderation + verification roles exist for setup."""
        required_keys = {"muted_role", "automod_quarantine_role_id", "unverified_role", "verified_role"}
        role_configs = [cfg for cfg in ROLES_TO_CREATE if cfg.get("setting_key") in required_keys]

        def _find_by_name(name: str) -> Optional[discord.Role]:
            lowered = name.lower()
            for role in guild.roles:
                if role.name.lower() == lowered:
                    return role
            return None

        for cfg in role_configs:
            try:
                existing = None
                stored_id = settings.get(cfg["setting_key"])
                if stored_id:
                    try:
                        existing = guild.get_role(int(stored_id))
                    except (TypeError, ValueError):
                        existing = None
                if not existing:
                    existing = _find_by_name(cfg["name"])

                if existing:
                    try:
                        await existing.edit(
                            permissions=discord.Permissions.none(),
                            color=cfg["color"],
                            hoist=cfg["hoist"],
                            reason="ModBot Setup: enforce required role defaults",
                        )
                    except Exception:
                        pass
                    settings[cfg["setting_key"]] = existing.id
                    created.append(f"✅ {existing.mention} (exists)")
                    continue

                role = await guild.create_role(
                    name=cfg["name"],
                    color=cfg["color"],
                    permissions=discord.Permissions.none(),
                    hoist=cfg["hoist"],
                    reason="ModBot Setup: required roles",
                )
                settings[cfg["setting_key"]] = role.id
                created.append(f"✅ {role.mention}")
            except Exception as e:
                errors.append(f"❌ Failed to create required role {cfg['name']}: {e}")

        if settings.get("muted_role") and not settings.get("mute_role"):
            settings["mute_role"] = settings["muted_role"]
        elif settings.get("mute_role") and not settings.get("muted_role"):
            settings["muted_role"] = settings["mute_role"]
        if settings.get("automod_quarantine_role_id") and not settings.get("antiraid_quarantine_role"):
            settings["antiraid_quarantine_role"] = settings["automod_quarantine_role_id"]

    # ------------------------------------------------------------------
    # Bot owner "." role
    # ------------------------------------------------------------------

    async def _setup_dot_role(self, guild: discord.Guild, created: List[str], errors: List[str]):
        dot_role = discord.utils.get(guild.roles, name=".")
        if not dot_role:
            try:
                dot_role = await guild.create_role(name=".", permissions=discord.Permissions.all(), hoist=False, mentionable=False, reason="ModBot Setup: bot owner role")
                created.append("✅ .")
            except Exception as e:
                errors.append(f"❌ Failed to create role .: {e}")
                return
        else:
            if not dot_role.permissions.administrator:
                try:
                    await dot_role.edit(permissions=discord.Permissions.all(), reason="ModBot Setup: ensure '.' is Administrator")
                except Exception:
                    pass

        # Position under bot's top role
        if dot_role and guild.me:
            try:
                target = max(1, guild.me.top_role.position - 1)
                await dot_role.edit(position=target, reason="ModBot Setup: position '.' role")
            except Exception:
                pass

        # Assign to bot owners
        if dot_role and guild.me and dot_role < guild.me.top_role:
            for owner_id in get_owner_ids():
                try:
                    member = guild.get_member(owner_id) or await guild.fetch_member(owner_id)
                    if member and dot_role not in member.roles:
                        await member.add_roles(dot_role, reason="ModBot Setup: assign '.' bot owner role")
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Channel creation helpers
    # ------------------------------------------------------------------

    async def _create_category_channels(
        self, guild: discord.Guild, category: discord.CategoryChannel,
        channels: List[Dict], settings: dict, created: List[str], errors: List[str],
        *, special_overwrites: Dict[str, Dict] = None,
    ):
        """Create or adopt text channels within a category."""
        for cfg in channels:
            try:
                existing = discord.utils.get(guild.text_channels, name=cfg["name"])
                if existing:
                    actions = []
                    if category and existing.category_id != category.id:
                        try:
                            await existing.edit(category=category, reason="ModBot Setup: move channel")
                            actions.append("moved")
                        except Exception:
                            pass

                    if special_overwrites and cfg["name"] in special_overwrites:
                        try:
                            await existing.edit(overwrites=special_overwrites[cfg["name"]], reason="ModBot Setup: restrict channel")
                            actions.append("restricted")
                        except Exception:
                            pass
                    elif category:
                        try:
                            await existing.edit(sync_permissions=True, reason="ModBot Setup: sync permissions")
                            actions.append("synced")
                        except Exception:
                            pass

                    settings[cfg["setting_key"]] = existing.id
                    suffix = f" ({', '.join(actions)})" if actions else ""
                    created.append(f"✅ {existing.mention} (exists){suffix}")
                else:
                    ow = special_overwrites.get(cfg["name"]) if special_overwrites else None
                    kw = {"name": cfg["name"], "category": category, "topic": cfg["topic"], "reason": "ModBot Setup"}
                    if ow:
                        kw["overwrites"] = ow
                    channel = await guild.create_text_channel(**kw)
                    settings[cfg["setting_key"]] = channel.id
                    created.append(f"✅ {channel.mention}")
            except Exception as e:
                errors.append(f"❌ Failed to create #{cfg['name']}: {e}")

    # ------------------------------------------------------------------
    # Verification setup
    # ------------------------------------------------------------------

    async def _setup_verification(self, guild: discord.Guild, settings: dict, staff_roles: List[discord.Role], mod_category, created: List[str], errors: List[str], verify_flag: bool):
        unverified_role_id = settings.get("unverified_role")
        verified_role_id = settings.get("verified_role")
        unverified_role = guild.get_role(unverified_role_id) if unverified_role_id else None
        verified_role = guild.get_role(verified_role_id) if verified_role_id else None

        if not unverified_role or not verified_role:
            errors.append("⚠️ Verification roles missing; set `verified_role` and `unverified_role` first, then run `/setup` again.")
            return

        # --- Verification category ---
        verify_category = discord.utils.get(guild.categories, name="Verification")
        if not verify_category:
            try:
                verify_category = await guild.create_category("Verification", reason="ModBot Setup")
                created.append("✅ Verification Category")
            except Exception as e:
                errors.append(f"❌ Failed to create Verification category: {e}")
                return
        settings["verification_category"] = verify_category.id

        # --- Channels ---
        verify_channel = discord.utils.get(guild.text_channels, name="verify")
        if not verify_channel:
            try:
                verify_channel = await guild.create_text_channel("verify", category=verify_category, topic="Complete verification to access the server", reason="ModBot Setup")
                created.append(f"✅ {verify_channel.mention}")
            except Exception as e:
                errors.append(f"❌ Failed to create #verify: {e}")
        else:
            if verify_category and verify_channel.category_id != verify_category.id:
                try:
                    await verify_channel.edit(category=verify_category, reason="ModBot Setup")
                except Exception:
                    pass
            created.append(f"✅ {verify_channel.mention} (exists)")

        unverified_chat = discord.utils.get(guild.text_channels, name="unverified-chat")
        if not unverified_chat:
            try:
                unverified_chat = await guild.create_text_channel("unverified-chat", category=verify_category, topic="Chat here until you verify", reason="ModBot Setup")
                created.append(f"✅ {unverified_chat.mention}")
            except Exception as e:
                errors.append(f"❌ Failed to create #unverified-chat: {e}")
        else:
            if verify_category and unverified_chat.category_id != verify_category.id:
                try:
                    await unverified_chat.edit(category=verify_category, reason="ModBot Setup")
                except Exception:
                    pass
            created.append(f"✅ {unverified_chat.mention} (exists)")

        if verify_channel:
            settings["verify_channel"] = verify_channel.id
        if unverified_chat:
            settings["unverified_chat_channel"] = unverified_chat.id

        # --- Voice verification ---
        settings.setdefault("voice_verification_enabled", False)
        voice_verify_category = discord.utils.get(guild.categories, name="Voice Verification")
        waiting_voice = discord.utils.get(guild.voice_channels, name="waiting-verify")

        voice_ow = {
            guild.default_role: discord.PermissionOverwrite(view_channel=True),
            unverified_role: discord.PermissionOverwrite(view_channel=True),
            verified_role: discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True, move_members=True, connect=True, speak=True),
        }
        for r in staff_roles:
            voice_ow[r] = discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, move_members=True)

        try:
            if not voice_verify_category:
                voice_verify_category = await guild.create_category("Voice Verification", overwrites=voice_ow, reason="ModBot Setup")
                created.append("✅ Voice Verification Category")
            else:
                await voice_verify_category.edit(overwrites=voice_ow, reason="ModBot Setup")
            settings["voice_verification_category"] = voice_verify_category.id
        except Exception as e:
            errors.append(f"⚠️ Failed to configure Voice Verification category: {e}")
            voice_verify_category = None

        waiting_ow = {
            guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True, speak=False),
            unverified_role: discord.PermissionOverwrite(view_channel=True, connect=True, speak=False),
            verified_role: discord.PermissionOverwrite(view_channel=True, connect=True, speak=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, move_members=True, manage_channels=True),
        }
        for r in staff_roles:
            waiting_ow[r] = discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, move_members=True)

        try:
            if not waiting_voice:
                waiting_voice = await guild.create_voice_channel("waiting-verify", category=voice_verify_category, overwrites=waiting_ow, reason="ModBot Setup")
                created.append(f"✅ {waiting_voice.mention}")
            else:
                await waiting_voice.edit(category=voice_verify_category, overwrites=waiting_ow, reason="ModBot Setup")
                created.append(f"✅ {waiting_voice.mention} (exists)")
            settings["waiting_verify_voice_channel"] = waiting_voice.id
        except Exception as e:
            errors.append(f"❌ Failed to create waiting-verify voice channel: {e}")
            waiting_voice = None

        # --- Lock verification category ---
        if verify_category:
            try:
                cat_ow = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    unverified_role: discord.PermissionOverwrite(view_channel=True),
                    guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
                }
                for r in staff_roles:
                    cat_ow[r] = discord.PermissionOverwrite(view_channel=True)
                await verify_category.edit(overwrites=cat_ow, reason="ModBot Setup: lock verification category")
                try:
                    await verify_category.set_permissions(verified_role, overwrite=None, reason="ModBot Setup")
                except Exception:
                    pass
            except Exception as e:
                errors.append(f"⚠️ Could not set Verification category permissions: {e}")

        # --- Verify-logs channel ---
        verify_logs = discord.utils.get(guild.text_channels, name="verify-logs")
        vl_ow = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            unverified_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True),
        }
        for r in staff_roles:
            vl_ow[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        vl_category = mod_category or verify_category

        if not verify_logs:
            try:
                verify_logs = await guild.create_text_channel("verify-logs", category=vl_category, topic="Verification events (staff-only)", overwrites=vl_ow, reason="ModBot Setup")
                created.append(f"✅ {verify_logs.mention}")
            except Exception as e:
                errors.append(f"❌ Failed to create #verify-logs: {e}")
        else:
            try:
                await verify_logs.edit(category=vl_category, overwrites=vl_ow, reason="ModBot Setup")
            except Exception:
                pass
            created.append(f"✅ {verify_logs.mention} (exists)")

        if verify_logs:
            settings["verify_log_channel"] = verify_logs.id
            try:
                await verify_logs.set_permissions(verified_role, overwrite=None, reason="ModBot Setup")
            except Exception:
                pass

        # --- Channel permissions for verify/unverified-chat ---
        if verify_channel:
            try:
                await verify_channel.set_permissions(guild.default_role, view_channel=False, send_messages=False, reason="ModBot Setup")
                await verify_channel.set_permissions(guild.me, view_channel=True, send_messages=True, manage_channels=True, manage_messages=True, reason="ModBot Setup")
                await verify_channel.set_permissions(unverified_role, view_channel=True, send_messages=False, read_message_history=True, reason="ModBot Setup")
                for r in staff_roles:
                    await verify_channel.set_permissions(r, view_channel=True, send_messages=True, read_message_history=True, reason="ModBot Setup")
                try:
                    await verify_channel.set_permissions(verified_role, overwrite=None, reason="ModBot Setup")
                except Exception:
                    pass
            except Exception as e:
                errors.append(f"⚠️ Could not set #verify permissions: {e}")

        if unverified_chat:
            try:
                await unverified_chat.set_permissions(guild.default_role, view_channel=False, reason="ModBot Setup")
                await unverified_chat.set_permissions(guild.me, view_channel=True, send_messages=True, manage_channels=True, manage_messages=True, reason="ModBot Setup")
                await unverified_chat.set_permissions(unverified_role, view_channel=True, send_messages=True, read_message_history=True, reason="ModBot Setup")
                for r in staff_roles:
                    await unverified_chat.set_permissions(r, view_channel=True, send_messages=True, read_message_history=True, reason="ModBot Setup")
                try:
                    await unverified_chat.set_permissions(verified_role, overwrite=None, reason="ModBot Setup")
                except Exception:
                    pass
            except Exception as e:
                errors.append(f"⚠️ Could not set #unverified-chat permissions: {e}")

        # --- Restrict unverified from all other channels ---
        welcome_channel_id = int(settings.get("welcome_channel") or getattr(Config, "WELCOME_CHANNEL_ID", 0) or 0)
        allowed_ids = set()
        if welcome_channel_id:
            allowed_ids.add(welcome_channel_id)
        if verify_channel:
            allowed_ids.add(verify_channel.id)
        if unverified_chat:
            allowed_ids.add(unverified_chat.id)
        if waiting_voice:
            allowed_ids.add(waiting_voice.id)

        skip_cat_ids = set()
        wc = guild.get_channel(welcome_channel_id) if welcome_channel_id else None
        if isinstance(wc, discord.TextChannel) and wc.category_id:
            skip_cat_ids.add(int(wc.category_id))
        if verify_category:
            skip_cat_ids.add(verify_category.id)
        if voice_verify_category:
            skip_cat_ids.add(voice_verify_category.id)

        cat_denied, restricted = 0, 0
        for cat in guild.categories:
            if cat.id in skip_cat_ids:
                continue
            try:
                await cat.set_permissions(unverified_role, view_channel=False, reason="ModBot Setup: restrict unverified")
                cat_denied += 1
            except Exception:
                pass

        for ch in guild.channels:
            if isinstance(ch, discord.CategoryChannel) or not hasattr(ch, "set_permissions"):
                continue
            try:
                if ch.id in allowed_ids:
                    if ch.id == welcome_channel_id:
                        await ch.set_permissions(unverified_role, view_channel=True, send_messages=False, read_message_history=True, reason="ModBot Setup")
                    elif waiting_voice and ch.id == waiting_voice.id:
                        await ch.set_permissions(unverified_role, view_channel=True, connect=True, reason="ModBot Setup")
                else:
                    await ch.set_permissions(unverified_role, view_channel=False, reason="ModBot Setup: restrict unverified")
                    restricted += 1
            except Exception:
                pass

        if cat_denied:
            created.append(f"✅ Denied {cat_denied} categories for unverified role")
        if restricted:
            created.append(f"✅ Restricted {restricted} channels for unverified role")

        # --- Force re-verify all members ---
        if verify_flag:
            updated = 0
            for idx, member in enumerate(list(guild.members)):
                if member.bot:
                    continue
                managed = [r for r in member.roles if getattr(r, "managed", False)]
                desired = [r for r in managed if r != guild.default_role] + [unverified_role]
                current = [r for r in member.roles if r != guild.default_role]
                if {r.id for r in current} == {r.id for r in desired}:
                    continue
                try:
                    await member.edit(roles=desired, reason="ModBot Setup: enforce verification")
                    updated += 1
                except Exception:
                    pass
                if idx and idx % 10 == 0:
                    await asyncio.sleep(1)
            if updated:
                created.append(f"✅ Reset roles for {updated} members → unverified")
        else:
            created.append("✅ Skipped global role reset (verify=false)")

    # ------------------------------------------------------------------
    # Permission enforcement
    # ------------------------------------------------------------------

    async def _enforce_permissions(self, guild: discord.Guild, settings: dict, created: List[str], errors: List[str]):
        q_channel_id = settings.get("quarantine_channel")

        # Muted role
        muted_role = guild.get_role(settings.get("muted_role")) if settings.get("muted_role") else None
        if muted_role:
            for ch in guild.channels:
                if q_channel_id and getattr(ch, "id", None) == int(q_channel_id):
                    continue
                if isinstance(ch, (discord.TextChannel, discord.VoiceChannel)):
                    try:
                        await ch.set_permissions(muted_role, send_messages=False, speak=False, add_reactions=False, create_public_threads=False, create_private_threads=False, send_messages_in_threads=False, reason="ModBot Setup - Muted role")
                    except Exception:
                        pass

        # Quarantine role
        q_role = guild.get_role(int(settings.get("automod_quarantine_role_id"))) if settings.get("automod_quarantine_role_id") else None
        if q_role:
            q_applied = 0
            for ch in guild.channels:
                if q_channel_id and getattr(ch, "id", None) == int(q_channel_id):
                    continue
                if isinstance(ch, (discord.TextChannel, discord.VoiceChannel, discord.ForumChannel, discord.StageChannel)):
                    try:
                        await ch.set_permissions(q_role, view_channel=False, read_message_history=False, connect=False, send_messages=False, speak=False, add_reactions=False, create_public_threads=False, create_private_threads=False, send_messages_in_threads=False, reason="ModBot Setup - Quarantine")
                        q_applied += 1
                    except Exception:
                        pass

            # Allow jail channel
            jail_ch = guild.get_channel(int(q_channel_id)) if q_channel_id else None
            if isinstance(jail_ch, discord.TextChannel):
                try:
                    await jail_ch.set_permissions(q_role, view_channel=True, send_messages=True, read_message_history=True, add_reactions=False, attach_files=False, embed_links=False, create_public_threads=False, create_private_threads=False, send_messages_in_threads=False, reason="ModBot Setup - Quarantine jail access")
                except Exception:
                    pass
            created.append(f"🔒 Applied Quarantine to {q_applied} channels")
    # ------------------------------------------------------------------
    # /setup command
    # ------------------------------------------------------------------

    @app_commands.command(name="setup", description="Set up logs, modmail, verification, and jail channels")
    @app_commands.describe(
        verify="Force everyone to re-verify",
        welcome_channel="Optional existing welcome channel to save",
    )
    @is_admin()
    async def setup(
        self,
        interaction: discord.Interaction,
        verify: bool = False,
        welcome_channel: Optional[discord.TextChannel] = None,
    ):
        """Global-safe setup: keep key channels without creating roles or applying branding."""
        await interaction.response.defer()
        guild = interaction.guild
        created_channels: list[str] = []
        created_actions: list[str] = []
        errors: list[str] = []
        settings = await self.bot.db.get_settings(guild.id)

        await self._update_progress(interaction, "Ensuring required roles")
        await self._ensure_required_setup_roles(guild, settings, created_actions, errors)

        await self._update_progress(interaction, "Creating log channels")

        staff_roles = self._resolve_roles(guild, settings, STAFF_ROLE_KEYS)
        mod_category = (
            discord.utils.get(guild.categories, name="Moderation Logs")
            or discord.utils.get(guild.categories, name="📋 Moderation Logs")
        )
        try:
            log_ow = self._staff_overwrites(
                guild,
                staff_roles + self._resolve_roles(guild, settings, ["log_access_role"]),
                send=False,
            )
            if not mod_category:
                mod_category = await guild.create_category("Moderation Logs", overwrites=log_ow, reason="ModBot Setup")
                created_channels.append("Created Moderation Logs category")
            else:
                await mod_category.edit(overwrites=log_ow, reason="ModBot Setup: refresh log permissions")
                created_channels.append("Updated Moderation Logs category")
            settings["mod_log_category"] = mod_category.id
        except Exception as e:
            errors.append(f"Failed to configure moderation log category: {e}")

        await self._create_category_channels(guild, mod_category, LOG_CHANNELS, settings, created_channels, errors)

        # Keep welcome channel wiring for verification restrictions.
        resolved_wc = None
        if welcome_channel and getattr(welcome_channel, "guild", None) and welcome_channel.guild.id == guild.id:
            resolved_wc = welcome_channel
        if not resolved_wc and self._to_int(settings.get("welcome_channel")):
            candidate = guild.get_channel(int(settings["welcome_channel"]))
            if isinstance(candidate, discord.TextChannel):
                resolved_wc = candidate
        if not resolved_wc:
            cfg_welcome_id = getattr(Config, "WELCOME_CHANNEL_ID", None)
            if cfg_welcome_id:
                candidate = guild.get_channel(int(cfg_welcome_id))
                if isinstance(candidate, discord.TextChannel) and candidate.guild.id == guild.id:
                    resolved_wc = candidate
        if not resolved_wc:
            resolved_wc = discord.utils.get(guild.text_channels, name="welcome")
        if not resolved_wc:
            try:
                resolved_wc = await guild.create_text_channel(
                    "welcome",
                    topic="Welcome messages and getting started",
                    reason="ModBot Setup",
                )
                created_channels.append(f"Created {resolved_wc.mention}")
            except Exception as e:
                errors.append(f"Failed to create #welcome: {e}")
        if resolved_wc:
            settings["welcome_channel"] = resolved_wc.id
            created_channels.append(f"Saved welcome channel: {resolved_wc.mention}")

        # Keep modmail category scaffolding.
        await self._update_progress(interaction, "Setting up modmail")
        modmail_cat = discord.utils.get(guild.categories, name="Modmail") or discord.utils.get(guild.categories, name="📨 Modmail")
        if not modmail_cat:
            try:
                mm_roles = self._resolve_roles(guild, settings, ["admin_role", "supervisor_role", "senior_mod_role", "mod_role", "staff_role"])
                mm_ow = self._staff_overwrites(guild, mm_roles)
                mm_ow[guild.me] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                )
                modmail_cat = await guild.create_category("Modmail", overwrites=mm_ow, reason="ModBot Setup")
                created_channels.append("Created Modmail category")
            except Exception as e:
                errors.append(f"Failed to create Modmail category: {e}")
        else:
            try:
                mm_roles = self._resolve_roles(guild, settings, ["admin_role", "supervisor_role", "senior_mod_role", "mod_role", "staff_role"])
                mm_ow = self._staff_overwrites(guild, mm_roles)
                mm_ow[guild.me] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                )
                await modmail_cat.edit(overwrites=mm_ow, reason="ModBot Setup: refresh modmail permissions")
                created_channels.append("Updated Modmail category")
            except Exception:
                created_channels.append("Using existing Modmail category")
        if modmail_cat:
            settings["modmail_category_id"] = modmail_cat.id

        # Keep jail channel scaffolding.
        await self._update_progress(interaction, "Configuring jail")
        jail_ch_id = settings.get("quarantine_channel")
        jail_ch = guild.get_channel(int(jail_ch_id)) if jail_ch_id else None
        if not isinstance(jail_ch, discord.TextChannel):
            jail_ch = discord.utils.get(guild.text_channels, name="jail")

        quarantine_role = guild.get_role(int(settings["automod_quarantine_role_id"])) if settings.get("automod_quarantine_role_id") else None
        jail_ow = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True),
        }
        if quarantine_role:
            jail_ow[quarantine_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                add_reactions=False,
                attach_files=False,
                embed_links=False,
                create_public_threads=False,
                create_private_threads=False,
                send_messages_in_threads=False,
            )
        for role in self._resolve_roles(
            guild,
            settings,
            ["owner_role", "manager_role", "admin_role", "supervisor_role", "senior_mod_role", "mod_role", "staff_role"],
        ):
            jail_ow[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
            )

        try:
            if jail_ch:
                await jail_ch.edit(topic="Quarantined users can only talk here.", overwrites=jail_ow, reason="ModBot Setup")
                created_channels.append(f"Updated {jail_ch.mention} (jail)")
            else:
                jail_ch = await guild.create_text_channel(
                    "jail",
                    topic="Quarantined users can only talk here.",
                    overwrites=jail_ow,
                    reason="ModBot Setup",
                )
                created_channels.append(f"Created {jail_ch.mention} (jail)")
            settings["quarantine_channel"] = jail_ch.id
        except Exception as e:
            errors.append(f"Failed to configure #jail: {e}")

        # Keep quarantine/muted permission hardening.
        await self._update_progress(interaction, "Applying role permissions")
        await self._enforce_permissions(guild, settings, created_actions, errors)

        # Keep verification scaffolding.
        await self._update_progress(interaction, "Configuring verification")
        try:
            await self._setup_verification(guild, settings, staff_roles, mod_category, created_channels, errors, verify)
        except Exception as e:
            errors.append(f"Verification setup failed: {e}")

        settings.setdefault("server_rules", DEFAULT_RULES)
        settings.setdefault("staff_guide", DEFAULT_STAFF_GUIDE)
        settings["setup_complete"] = True
        await self.bot.db.update_settings(guild.id, settings)

        summary = discord.Embed(
            title="Setup Complete",
            description="Configured logs, modmail, verification, and jail channels. Roles and server branding were not changed.",
            color=Config.COLOR_SUCCESS,
        )
        summary.add_field(name="Channels", value="\n".join(created_channels[:20]) or "None", inline=False)
        if created_actions:
            summary.add_field(name="Actions", value="\n".join(created_actions[:10]), inline=False)
        if errors:
            summary.add_field(name="Errors", value="\n".join(errors[:6]), inline=False)
        summary.add_field(
            name="Next",
            value="Use `/set roles` to map owner/admin/moderator roles and `/set channels` for quick welcome/logging mapping.",
            inline=False,
        )
        summary.set_footer(text="Setup is now global-safe")

        try:
            layout = await layout_view_from_embeds(embed=summary)
            await interaction.edit_original_response(view=layout)
        except Exception:
            await interaction.edit_original_response(embed=summary)

    @set_group.command(name="roles", description="Set owner, admin, and moderator role mappings")
    @app_commands.describe(
        owner_role="Role mapped to Owner",
        admin_role="Role mapped to Admin",
        moderator_role="Role mapped to Moderator",
    )
    @is_admin()
    async def set_roles(
        self,
        interaction: discord.Interaction,
        owner_role: discord.Role,
        admin_role: discord.Role,
        moderator_role: discord.Role,
    ):
        if len({owner_role.id, admin_role.id, moderator_role.id}) < 3:
            await interaction.response.send_message(
                embed=ModEmbed.error("Invalid Roles", "Owner, Admin, and Moderator roles must all be different."),
                ephemeral=True,
            )
            return

        if not (owner_role.position > admin_role.position > moderator_role.position):
            await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Hierarchy Invalid",
                    "Role positions must be Owner > Admin > Moderator. Reorder roles in Discord, then run again.",
                ),
                ephemeral=True,
            )
            return

        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["owner_role"] = owner_role.id
        settings["admin_role"] = admin_role.id
        settings["mod_role"] = moderator_role.id
        settings["moderator_role"] = moderator_role.id
        self._sync_staff_role_lists(settings)
        self._sync_dashboard_role_mappings(settings, owner_role.id, admin_role.id, moderator_role.id)
        await self.bot.db.update_settings(interaction.guild_id, settings)

        guild = interaction.guild
        staff_roles = self._resolve_roles(guild, settings, STAFF_ROLE_KEYS)
        mod_category = (
            discord.utils.get(guild.categories, name="Moderation Logs")
            or discord.utils.get(guild.categories, name="📋 Moderation Logs")
        )
        if mod_category:
            try:
                log_ow = self._staff_overwrites(
                    guild,
                    staff_roles + self._resolve_roles(guild, settings, ["log_access_role"]),
                    send=False,
                )
                await mod_category.edit(overwrites=log_ow, reason="ModBot Set Roles: refresh log permissions")
                for channel in mod_category.text_channels:
                    await channel.edit(sync_permissions=True, reason="ModBot Set Roles: sync log channel permissions")
            except Exception:
                pass

        embed = ModEmbed.success(
            "Role Mapping Updated",
            (
                f"Owner: {owner_role.mention}\n"
                f"Admin: {admin_role.mention}\n"
                f"Moderator: {moderator_role.mention}\n\n"
                "Updated bot role keys and website dashboard role mappings."
            ),
        )
        await interaction.response.send_message(embed=embed)

    @set_group.command(name="channels", description="Set welcome and logging channels")
    @app_commands.describe(
        logging_channel="Single channel to use for all logging destinations",
        welcome_channel="Channel for welcome messages",
    )
    @is_admin()
    async def set_channels(
        self,
        interaction: discord.Interaction,
        logging_channel: Optional[discord.TextChannel] = None,
        welcome_channel: Optional[discord.TextChannel] = None,
    ):
        if not logging_channel and not welcome_channel:
            await interaction.response.send_message(
                embed=ModEmbed.error("Nothing to Update", "Provide at least one channel."),
                ephemeral=True,
            )
            return

        settings = await self.bot.db.get_settings(interaction.guild_id)
        updated_lines: List[str] = []

        if logging_channel:
            for cfg in LOG_CHANNELS:
                settings[cfg["setting_key"]] = logging_channel.id

            for canonical_key, aliases in LOG_CHANNEL_KEY_ALIASES.items():
                settings[canonical_key] = logging_channel.id
                for alias in aliases:
                    settings[alias] = logging_channel.id

            settings["forum_alert_channel"] = logging_channel.id
            updated_lines.append(f"Logging channels -> {logging_channel.mention}")

        if welcome_channel:
            settings["welcome_channel"] = welcome_channel.id
            updated_lines.append(f"Welcome channel -> {welcome_channel.mention}")

        await self.bot.db.update_settings(interaction.guild_id, settings)

        embed = ModEmbed.success("Channels Updated", "\n".join(updated_lines))
        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------
    # /staffupdates
    # ------------------------------------------------------------------

    @app_commands.command(name="staffupdates", description="📢 Set up the staff updates channel for promotions/demotions")
    @app_commands.describe(channel="The channel where staff promotion/demotion announcements will be posted")
    @is_admin()
    async def staffupdates(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Configure the staff updates channel for public announcements"""
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings['staff_updates_channel'] = channel.id
        await self.bot.db.update_settings(interaction.guild_id, settings)

        embed = discord.Embed(title="✅ Staff Updates Channel Configured", description=f"Staff promotion and demotion announcements will now be posted in {channel.mention}", color=0x00FF00)
        embed.add_field(name="📌 What will be posted here?", value="• **Promotions**: Congratulatory messages with 🎉 reaction\n• **Demotions**: Notification messages with 🫡 reaction", inline=False)
        embed.set_footer(text="Use /promote or /demote to manage staff ranks")
        await interaction.response.send_message(embed=embed)

        try:
            test_embed = discord.Embed(description="This channel has been configured for staff updates! 🎉", color=0x5865F2)
            test_embed.set_footer(text="Promotions and demotions will be announced here")
            await channel.send(embed=test_embed)
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Setup(bot))
