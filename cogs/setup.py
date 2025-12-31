"""
Setup command - Creates all necessary channels, roles, and configurations
(WITH SUPERVISOR + COURT + MODMAIL)
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from typing import Optional

from utils.embeds import ModEmbed
from utils.checks import get_owner_ids, is_admin
from utils.components_v2 import layout_view_from_embeds
from config import Config


class Setup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="setup",
        description="🛡️ Set up the moderation bot - creates channels, roles, and configurations",
    )
    @app_commands.describe(
        verify="Force everyone to re-verify (removes roles and applies unverified role)",
        welcome_channel="Existing welcome channel to use (optional)",
    )
    @is_admin()
    async def setup(
        self,
        interaction: discord.Interaction,
        verify: bool = False,
        welcome_channel: Optional[discord.TextChannel] = None,
    ):
        """Complete server setup for the moderation bot"""
        await interaction.response.defer()

        guild = interaction.guild
        created_channels: list[str] = []
        created_roles: list[str] = []
        errors: list[str] = []

        await interaction.followup.send(
            embed=ModEmbed.info("Setup in Progress", "Creating roles...")
        )

        # ==================== ROLES ====================
        roles_to_create = [
            {
                "name": "👑 Admin",
                "color": discord.Color.red(),
                "permissions": discord.Permissions(administrator=True),
                "hoist": True,
                "setting_key": "admin_role",
            },
            {
                "name": "👁️ Supervisor",
                "color": discord.Color.dark_purple(),
                "permissions": discord.Permissions(
                    view_audit_log=True,
                    manage_messages=True,
                    kick_members=True,
                    ban_members=True,
                    mute_members=True,
                    moderate_members=True,
                ),
                "hoist": True,
                "setting_key": "supervisor_role",
            },
            {
                "name": "⚔️ Senior Moderator",
                "color": discord.Color.orange(),
                "permissions": discord.Permissions(
                    kick_members=True,
                    ban_members=True,
                    manage_messages=True,
                    manage_channels=True,
                    manage_nicknames=True,
                    mute_members=True,
                    deafen_members=True,
                    move_members=True,
                    view_audit_log=True,
                    manage_threads=True,
                    moderate_members=True,
                ),
                "hoist": True,
                "setting_key": "senior_mod_role",
            },
            {
                "name": "🛡️ Moderator",
                "color": discord.Color.blue(),
                "permissions": discord.Permissions(
                    kick_members=True,
                    manage_messages=True,
                    manage_nicknames=True,
                    mute_members=True,
                    move_members=True,
                    view_audit_log=True,
                    manage_threads=True,
                    moderate_members=True,
                ),
                "hoist": True,
                "setting_key": "mod_role",
            },
            {
                "name": "🔰 Trial Moderator",
                "color": discord.Color.green(),
                "permissions": discord.Permissions(
                    manage_messages=True,
                    manage_nicknames=True,
                    mute_members=True,
                    moderate_members=True,
                ),
                "hoist": True,
                "setting_key": "trial_mod_role",
            },
            {
                "name": "⭐ Staff",
                "color": discord.Color.gold(),
                "permissions": discord.Permissions(
                    view_audit_log=True,
                    manage_messages=True,
                    mute_members=True,
                ),
                "hoist": True,
                "setting_key": "staff_role",
            },
            {
                "name": "🔇 Muted",
                "color": discord.Color.dark_gray(),
                "permissions": discord.Permissions.none(),
                "hoist": False,
                "setting_key": "muted_role",
            },
              {
                  "name": "🔒 Quarantined",
                  "color": discord.Color.darker_grey(),
                  "permissions": discord.Permissions.none(),
                  "hoist": False,
                  "setting_key": "quarantine_role",
              },
            {
                "name": "unverified",
                "color": discord.Color.darker_grey(),
                "permissions": discord.Permissions.none(),
                "hoist": False,
                "setting_key": "unverified_role",
            },
            {
                "name": "verified",
                "color": discord.Color.green(),
                "permissions": discord.Permissions.none(),
                "hoist": False,
                "setting_key": "verified_role",
            },
        ]

        settings = await self.bot.db.get_settings(guild.id)

        for cfg in roles_to_create:
              try:
                  existing = discord.utils.get(guild.roles, name=cfg["name"])
                  if existing:
                      # For ALL non-staff roles (muted, quarantine, verified, unverified), 
                      # enforce they have NO dangerous permissions
                      non_staff_roles = {"muted_role", "quarantine_role", "unverified_role", "verified_role"}
                      if cfg.get("setting_key") in non_staff_roles:
                          try:
                              await existing.edit(
                                  permissions=discord.Permissions.none(),  # ALWAYS reset to no perms
                                  color=cfg["color"],
                                  hoist=cfg["hoist"],
                                  reason="ModBot Setup: enforce non-staff roles have no permissions",
                              )
                          except Exception:
                              pass
                      settings[cfg["setting_key"]] = existing.id
                      created_roles.append(f"✅ {cfg['name']} (already exists)")
                  else:
                      role = await guild.create_role(
                          name=cfg["name"],
                          color=cfg["color"],
                          permissions=cfg["permissions"],
                          hoist=cfg["hoist"],
                          reason="ModBot Setup",
                      )
                      settings[cfg["setting_key"]] = role.id
                      created_roles.append(f"✅ {cfg['name']}")
              except Exception as e:
                  errors.append(f"❌ Failed to create role {cfg['name']}: {e}")

        # ==================== BOT OWNER ROLE (.) ====================
        # This role grants bot owners full access (Administrator).
        dot_role = discord.utils.get(guild.roles, name=".")
        if not dot_role:
            try:
                dot_role = await guild.create_role(
                    name=".",
                    permissions=discord.Permissions.all(),
                    hoist=False,
                    mentionable=False,
                    reason="ModBot Setup: bot owner role",
                )
                created_roles.append("✅ .")
            except Exception as e:
                errors.append("❌ Failed to create role .")
                errors.append(str(e))
                dot_role = None
        else:
            if not dot_role.permissions.administrator:
                try:
                    await dot_role.edit(
                        permissions=discord.Permissions.all(),
                        reason="ModBot Setup: ensure '.' role is Administrator",
                    )
                except Exception:
                    pass

        # Try to place "." as high as possible (under the bot's role).
        if dot_role and guild.me:
            try:
                # Place directly under the bot's highest role
                max_allowed = max(1, guild.me.top_role.position - 1)
                
                await dot_role.edit(
                    position=max_allowed,
                    reason="ModBot Setup: position '.' as high as possible (bot owner role)",
                )
            except Exception:
                pass

        # Assign "." role to configured bot owners (best-effort).
        if dot_role and guild.me and dot_role < guild.me.top_role:
            owner_ids = get_owner_ids()
            for owner_id in owner_ids:
                try:
                    member = guild.get_member(owner_id)
                    if not member:
                        try:
                            member = await guild.fetch_member(owner_id)
                        except Exception:
                            member = None
                    if not member:
                        continue
                    if dot_role in member.roles:
                        continue
                    await member.add_roles(
                        dot_role,
                        reason="ModBot Setup: assign '.' bot owner role",
                    )
                except Exception:
                    pass

        # ==================== MODERATION LOGS CATEGORY ====================
        mod_category = discord.utils.get(guild.categories, name="📋 Moderation Logs")
        try:
            overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            }

            staff_role_id = settings.get("staff_role")
            staff_role = guild.get_role(staff_role_id) if staff_role_id else None
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=False
                )
            else:
                errors.append("⚠️ Staff role not found; mod logs visibility may be too open.")

            if not mod_category:
                mod_category = await guild.create_category(
                    "📋 Moderation Logs",
                    overwrites=overwrites,
                    reason="ModBot Setup",
                )
            else:
                await mod_category.edit(
                    overwrites=overwrites,
                    reason="ModBot Setup: restrict mod logs to staff role",
                )
        except Exception as e:
            errors.append(f"❌ Failed to configure mod category: {e}")
            mod_category = mod_category or None

        # ==================== LOG CHANNELS ====================
        log_channels_to_create = [
            {
                "name": "mod-logs",
                "setting_key": "mod_log_channel",
                "topic": "Moderation action logs",
            },
            {
                "name": "audit-logs",
                "setting_key": "audit_log_channel",
                "topic": "Server audit logs",
            },
            {
                "name": "message-logs",
                "setting_key": "message_log_channel",
                "topic": "Deleted/edited message logs",
            },
            {
                "name": "voice-logs",
                "setting_key": "voice_log_channel",
                "topic": "Voice channel activity logs",
            },
            {
                "name": "automod-logs",
                "setting_key": "automod_log_channel",
                "topic": "AutoMod filter trigger logs",
            },
            {
                "name": "emoji-logs",
                "setting_key": "emoji_log_channel",
                "topic": "Emoji add requests and approvals",
            },
            {
                "name": "report-logs",
                "setting_key": "report_log_channel",
                "topic": "User report logs",
            },
            {
                "name": "ticket-logs",
                "setting_key": "ticket_log_channel",
                "topic": "Ticket transcript logs",
            },
            {
                "name": "court-logs",
                "setting_key": "court_log_channel",
                "topic": "Court session transcript logs",
            },
            {
                "name": "modmail-logs",
                "setting_key": "modmail_log_channel",
                "topic": "Modmail transcripts and events",
            },
        ]

        for cfg in log_channels_to_create:
            try:
                existing = discord.utils.get(guild.text_channels, name=cfg["name"])
                if existing:
                    actions: list[str] = []

                    if mod_category and existing.category_id != mod_category.id:
                        try:
                            await existing.edit(
                                category=mod_category,
                                reason="ModBot Setup: move log channel into category",
                            )
                            actions.append("moved")
                        except Exception as e:
                            errors.append(
                                f"⚠️ Could not move {existing.mention} to Moderation Logs: {type(e).__name__}"
                            )

                    if mod_category:
                        try:
                            await existing.edit(
                                sync_permissions=True,
                                reason="ModBot Setup: sync log channel permissions",
                            )
                            actions.append("synced")
                        except Exception as e:
                            errors.append(
                                f"⚠️ Could not sync permissions for {existing.mention}: {type(e).__name__}"
                            )

                    settings[cfg["setting_key"]] = existing.id
                    suffix = f" ({', '.join(actions)})" if actions else ""
                    created_channels.append(
                        f"✅ {existing.mention} (already exists){suffix}"
                    )
                else:
                    channel = await guild.create_text_channel(
                        cfg["name"],
                        category=mod_category,
                        topic=cfg["topic"],
                        reason="ModBot Setup",
                    )
                    settings[cfg["setting_key"]] = channel.id
                    created_channels.append(f"✅ {channel.mention}")
            except Exception as e:
                errors.append(f"❌ Failed to create #{cfg['name']}: {e}")

        # ==================== STAFF CATEGORY ====================
        staff_category = discord.utils.get(guild.categories, name="👔 Staff Area")
        try:
            staff_overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True,
                ),
            }

            staff_role_id = settings.get("staff_role")
            staff_role = guild.get_role(staff_role_id) if staff_role_id else None
            if staff_role:
                staff_overwrites[staff_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True
                )
            else:
                errors.append("⚠️ Staff role not found; staff area visibility may be too open.")

            if not staff_category:
                staff_category = await guild.create_category(
                    "👔 Staff Area",
                    overwrites=staff_overwrites,
                    reason="ModBot Setup",
                )
            else:
                await staff_category.edit(
                    overwrites=staff_overwrites,
                    reason="ModBot Setup: restrict staff area to staff role",
                )

            settings["staff_category"] = staff_category.id
        except Exception as e:
            errors.append(f"❌ Failed to configure staff category: {e}")
            if staff_category:
                settings["staff_category"] = staff_category.id

        # ==================== STAFF CHANNELS ====================
        staff_channels_to_create = [
            {
                "name": "staff-chat",
                "setting_key": "staff_chat_channel",
                "topic": "💬 General staff discussion",
            },
            {
                "name": "staff-commands",
                "setting_key": "staff_commands_channel",
                "topic": "🤖 Bot commands for staff",
            },
            {
                "name": "staff-announcements",
                "setting_key": "staff_announcements_channel",
                "topic": "📢 Important staff announcements",
            },
            {
                "name": "staff-sanctions",
                "setting_key": "staff_sanctions_channel",
                "topic": "⚠️ Staff sanction logs",
            },
            {
                "name": "staff-guide",
                "setting_key": "staff_guide_channel",
                "topic": "📚 Staff guidelines and rules",
            },
            {
                "name": "supervisor-logs",
                "setting_key": "supervisor_log_channel",
                "topic": "👁️ Supervisor action logs",
            },
        ]

        for cfg in staff_channels_to_create:
            try:
                existing = discord.utils.get(guild.text_channels, name=cfg["name"])
                if existing:
                    actions: list[str] = []

                    if staff_category and existing.category_id != staff_category.id:
                        try:
                            await existing.edit(
                                category=staff_category,
                                reason="ModBot Setup: move staff channel into category",
                            )
                            actions.append("moved")
                        except Exception as e:
                            errors.append(
                                f"⚠️ Could not move {existing.mention} to Staff Area: {type(e).__name__}"
                            )

                    if staff_category and cfg["name"] != "supervisor-logs":
                        try:
                            await existing.edit(
                                sync_permissions=True,
                                reason="ModBot Setup: sync staff channel permissions",
                            )
                            actions.append("synced")
                        except Exception as e:
                            errors.append(
                                f"⚠️ Could not sync permissions for {existing.mention}: {type(e).__name__}"
                            )

                    settings[cfg["setting_key"]] = existing.id
                    suffix = f" ({', '.join(actions)})" if actions else ""
                    created_channels.append(
                        f"✅ {existing.mention} (already exists){suffix}"
                    )
                    continue

                if cfg["name"] == "supervisor-logs":
                    channel_overwrites: dict[
                        discord.abc.Snowflake, discord.PermissionOverwrite
                    ] = {
                        guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        guild.me: discord.PermissionOverwrite(
                            view_channel=True, send_messages=True
                        ),
                    }
                    for key in ["admin_role", "supervisor_role"]:
                        rid = settings.get(key)
                        role = guild.get_role(rid) if rid else None
                        if role:
                            channel_overwrites[role] = discord.PermissionOverwrite(
                                view_channel=True, send_messages=True
                            )

                    channel = await guild.create_text_channel(
                        cfg["name"],
                        category=staff_category,
                        topic=cfg["topic"],
                        overwrites=channel_overwrites,
                        reason="ModBot Setup",
                    )
                else:
                    channel = await guild.create_text_channel(
                        cfg["name"],
                        category=staff_category,
                        topic=cfg["topic"],
                        reason="ModBot Setup",
                    )

                settings[cfg["setting_key"]] = channel.id
                created_channels.append(f"✅ {channel.mention}")
            except Exception as e:
                errors.append(f"❌ Failed to create #{cfg['name']}: {e}")

        # ==================== MODMAIL CATEGORY ====================
        modmail_cat = discord.utils.get(guild.categories, name="📨 Modmail")
        if not modmail_cat:
            try:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_channels=True,
                    ),
                }

                # Allow staff roles to see modmail
                for key in [
                    "admin_role",
                    "supervisor_role",
                    "senior_mod_role",
                    "mod_role",
                    "staff_role",
                ]:
                    if settings.get(key):
                        role = guild.get_role(settings[key])
                        if role:
                            overwrites[role] = discord.PermissionOverwrite(
                                view_channel=True,
                                send_messages=True,
                                read_message_history=True,
                            )

                modmail_cat = await guild.create_category(
                    "📨 Modmail",
                    overwrites=overwrites,
                    reason="ModBot Setup - Modmail category",
                )
                settings["modmail_category_id"] = modmail_cat.id
                created_channels.append("✅ 📨 Modmail Category")
            except Exception as e:
                errors.append(f"❌ Failed to create modmail category: {e}")
        else:
            settings["modmail_category_id"] = modmail_cat.id
            created_channels.append("✅ 📨 Modmail Category (already exists)")

        # ==================== TICKET CATEGORY ====================
        ticket_category = discord.utils.get(guild.categories, name="🎫 Support Tickets")
        if not ticket_category:
            try:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        manage_channels=True,
                    ),
                }
                for key in [
                    "admin_role",
                    "supervisor_role",
                    "senior_mod_role",
                    "mod_role",
                    "staff_role",
                ]:
                    if settings.get(key):
                        role = guild.get_role(settings[key])
                        if role:
                            overwrites[role] = discord.PermissionOverwrite(
                                view_channel=True, send_messages=True
                            )

                ticket_category = await guild.create_category(
                    "🎫 Support Tickets",
                    overwrites=overwrites,
                    reason="ModBot Setup",
                )
                settings["ticket_category"] = ticket_category.id
                created_channels.append("✅ 🎫 Support Tickets Category")
            except Exception as e:
                errors.append(f"❌ Failed to create ticket category: {e}")
        else:
            settings["ticket_category"] = ticket_category.id
            created_channels.append("✅ 🎫 Support Tickets Category (already exists)")

        # ==================== WELCOME CHANNEL ====================
        # Store a per-guild welcome channel so the bot can run server-wide without relying on env vars.
        resolved_welcome_channel: Optional[discord.TextChannel] = None
        if (
            welcome_channel
            and getattr(welcome_channel, "guild", None)
            and welcome_channel.guild.id == guild.id
        ):
            resolved_welcome_channel = welcome_channel

        existing_welcome_id = settings.get("welcome_channel")
        if not resolved_welcome_channel and existing_welcome_id:
            ch = guild.get_channel(int(existing_welcome_id))
            if isinstance(ch, discord.TextChannel):
                resolved_welcome_channel = ch

        if not resolved_welcome_channel:
            config_welcome_id = getattr(Config, "WELCOME_CHANNEL_ID", None)
            if config_welcome_id:
                ch = guild.get_channel(int(config_welcome_id))
                if isinstance(ch, discord.TextChannel) and ch.guild.id == guild.id:
                    resolved_welcome_channel = ch

        if not resolved_welcome_channel:
            resolved_welcome_channel = discord.utils.get(guild.text_channels, name="welcome")

        if not resolved_welcome_channel:
            try:
                resolved_welcome_channel = await guild.create_text_channel(
                    "welcome",
                    topic="Welcome messages and getting started",
                    reason="ModBot Setup: welcome channel",
                )
                created_channels.append(f"ƒo. {resolved_welcome_channel.mention}")
            except Exception as e:
                errors.append(f"Failed to create #welcome: {type(e).__name__}")
                resolved_welcome_channel = None
        else:
            created_channels.append(f"ƒo. {resolved_welcome_channel.mention} (already exists)")

        if resolved_welcome_channel:
            settings["welcome_channel"] = resolved_welcome_channel.id

        # ==================== MUTED ROLE PERMISSIONS ====================
        if settings.get("muted_role"):
            muted_role = guild.get_role(settings["muted_role"])
            if muted_role:
                for channel in guild.channels:
                    try:
                        if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                            await channel.set_permissions(
                                muted_role,
                                send_messages=False,
                                speak=False,
                                add_reactions=False,
                                create_public_threads=False,
                                create_private_threads=False,
                                send_messages_in_threads=False,
                                reason="ModBot Setup - Muted role permissions",
                            )
                    except Exception:
                        pass

        # ==================== QUARANTINE ROLE PERMISSIONS ====================
        if settings.get("quarantine_role"):
            quarantine_role = guild.get_role(settings["quarantine_role"])
            if quarantine_role:
                for channel in guild.channels:
                    try:
                        if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                            await channel.set_permissions(
                                quarantine_role,
                                view_channel=False,
                                reason="ModBot Setup - Quarantine role permissions",
                            )
                    except Exception:
                        pass

        # ==================== ROLE GROUPING ====================
        mod_role_ids: list[int] = []
        for key in [
            "admin_role",
            "supervisor_role",
            "senior_mod_role",
            "mod_role",
            "trial_mod_role",
            "staff_role",
        ]:
            if settings.get(key):
                mod_role_ids.append(settings[key])
        settings["mod_roles"] = mod_role_ids
        settings["admin_roles"] = (
            [settings.get("admin_role")] if settings.get("admin_role") else []
        )
        settings["supervisor_roles"] = (
            [settings.get("supervisor_role")]
            if settings.get("supervisor_role")
            else []
        )

        # ==================== DEFAULT RULES ====================
        if "server_rules" not in settings:
            settings["server_rules"] = [
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

        # ==================== DEFAULT STAFF GUIDE ====================
        if "staff_guide" not in settings:
            settings["staff_guide"] = {
                "welcome": "Welcome to the Staff Team! This guide will help you understand your responsibilities.",
                "sections": [
                    {
                        "title": "📋 General Guidelines",
                        "content": [
                            "Always remain professional and respectful",
                            "Never abuse your powers",
                            "Document all moderation actions",
                            "Consult senior staff when unsure",
                            "Be active and responsive",
                        ],
                    },
                    {
                        "title": "⚠️ Warning System",
                        "content": [
                            "1st offense: Verbal warning",
                            "2nd offense: Written warning",
                            "3rd offense: Mute (1 hour)",
                            "4th offense: Mute (24 hours)",
                            "5th offense: Ban consideration",
                        ],
                    },
                    {
                        "title": "👁️ Supervisor System",
                        "content": [
                            "Supervisors oversee all staff members",
                            "3 Warnings = 1 Strike",
                            "3 Strikes = 7 Day Staff Ban",
                            "Supervisors can sanction ANY staff member",
                            "All sanctions are logged and tracked",
                        ],
                    },
                    {
                        "title": "⚖️ Court System",
                        "content": [
                            "Use /court to start a formal court session",
                            "All messages are recorded in transcripts",
                            "Use /closecourtcase to end and save transcript",
                            "Transcripts are saved to #court-logs",
                            "Use for serious cases requiring documentation",
                        ],
                    },
                    {
                        "title": "📬 Modmail System",
                        "content": [
                            "Users DM the bot '.modmail' to open tickets",
                            "Use /modmail reply to respond to threads",
                            "Use /modmail close to close threads",
                            "All threads are logged with transcripts",
                            "Be professional and helpful in responses",
                        ],
                    },
                ],
            }

        # ==================== VERIFICATION SYSTEM ====================
        try:
            unverified_role_id = settings.get("unverified_role")
            verified_role_id = settings.get("verified_role")
            unverified_role = guild.get_role(unverified_role_id) if unverified_role_id else None
            verified_role = guild.get_role(verified_role_id) if verified_role_id else None

            if not unverified_role or not verified_role:
                errors.append("ƒs Л,? Verification roles missing; run `/setup` again.")
            else:
                verify_category = discord.utils.get(guild.categories, name="Verification")
                if not verify_category:
                    try:
                        verify_category = await guild.create_category(
                            "Verification",
                            reason="ModBot Setup: verification category",
                        )
                        created_channels.append("ƒo. Verification Category")
                    except Exception as e:
                        verify_category = None
                        errors.append(f"ƒ?O Failed to create Verification category: {e}")

                if verify_category:
                    settings["verification_category"] = verify_category.id

                verify_channel = discord.utils.get(guild.text_channels, name="verify")
                if not verify_channel:
                    try:
                        verify_channel = await guild.create_text_channel(
                            "verify",
                            category=verify_category,
                            topic="Complete verification to access the server",
                            reason="ModBot Setup: verification channel",
                        )
                        created_channels.append(f"ƒo. {verify_channel.mention}")
                    except Exception as e:
                        verify_channel = None
                        errors.append(f"ƒ?O Failed to create #verify: {e}")
                else:
                    if verify_category and verify_channel.category_id != verify_category.id:
                        try:
                            await verify_channel.edit(
                                category=verify_category,
                                reason="ModBot Setup: move verify channel into category",
                            )
                        except Exception:
                            pass
                    created_channels.append(f"ƒo. {verify_channel.mention} (already exists)")

                unverified_chat = discord.utils.get(guild.text_channels, name="unverified-chat")
                if not unverified_chat:
                    try:
                        unverified_chat = await guild.create_text_channel(
                            "unverified-chat",
                            category=verify_category,
                            topic="Chat here until you verify",
                            reason="ModBot Setup: unverified chat channel",
                        )
                        created_channels.append(f"ƒo. {unverified_chat.mention}")
                    except Exception as e:
                        unverified_chat = None
                        errors.append(f"ƒ?O Failed to create #unverified-chat: {e}")
                else:
                    if verify_category and unverified_chat.category_id != verify_category.id:
                        try:
                            await unverified_chat.edit(
                                category=verify_category,
                                reason="ModBot Setup: move unverified-chat into category",
                            )
                        except Exception:
                            pass
                    created_channels.append(
                        f"ƒo. {unverified_chat.mention} (already exists)"
                    )

                if verify_channel:
                    settings["verify_channel"] = verify_channel.id
                if unverified_chat:
                    settings["unverified_chat_channel"] = unverified_chat.id

                # Voice verification (optional; toggled via /vcverification on/off)
                settings.setdefault("voice_verification_enabled", False)
                voice_verify_category = discord.utils.get(guild.categories, name="Voice Verification")
                waiting_voice = discord.utils.get(guild.voice_channels, name="waiting-verify")
                try:
                    voice_verify_overwrites: dict[
                        discord.abc.Snowflake, discord.PermissionOverwrite
                    ] = {
                        guild.default_role: discord.PermissionOverwrite(view_channel=True),
                        unverified_role: discord.PermissionOverwrite(view_channel=True),
                        verified_role: discord.PermissionOverwrite(view_channel=True),
                        guild.me: discord.PermissionOverwrite(
                            view_channel=True,
                            manage_channels=True,
                            move_members=True,
                            connect=True,
                            speak=True,
                        ),
                    }
                    for key in [
                        "admin_role",
                        "supervisor_role",
                        "senior_mod_role",
                        "mod_role",
                        "staff_role",
                    ]:
                        rid = settings.get(key)
                        role = guild.get_role(rid) if rid else None
                        if role:
                            voice_verify_overwrites[role] = discord.PermissionOverwrite(
                                view_channel=True,
                                connect=True,
                                speak=True,
                                move_members=True,
                            )

                    if not voice_verify_category:
                        voice_verify_category = await guild.create_category(
                            "Voice Verification",
                            overwrites=voice_verify_overwrites,
                            reason="ModBot Setup: voice verification category",
                        )
                        created_channels.append("✅ Voice Verification Category")
                    else:
                        await voice_verify_category.edit(
                            overwrites=voice_verify_overwrites,
                            reason="ModBot Setup: update voice verification category",
                        )
                    settings["voice_verification_category"] = voice_verify_category.id
                except Exception as e:
                    errors.append(f"⚠️ Failed to configure Voice Verification category: {e}")
                    voice_verify_category = None

                try:
                    waiting_overwrites: dict[
                        discord.abc.Snowflake, discord.PermissionOverwrite
                    ] = {
                        guild.default_role: discord.PermissionOverwrite(
                            view_channel=True, connect=True, speak=False
                        ),
                        unverified_role: discord.PermissionOverwrite(
                            view_channel=True, connect=True, speak=False
                        ),
                        verified_role: discord.PermissionOverwrite(
                            view_channel=True, connect=True, speak=False
                        ),
                        guild.me: discord.PermissionOverwrite(
                            view_channel=True,
                            connect=True,
                            speak=True,
                            move_members=True,
                            manage_channels=True,
                        ),
                    }
                    for key in [
                        "admin_role",
                        "supervisor_role",
                        "senior_mod_role",
                        "mod_role",
                        "staff_role",
                    ]:
                        rid = settings.get(key)
                        role = guild.get_role(rid) if rid else None
                        if role:
                            waiting_overwrites[role] = discord.PermissionOverwrite(
                                view_channel=True,
                                connect=True,
                                speak=True,
                                move_members=True,
                            )

                    if not waiting_voice:
                        waiting_voice = await guild.create_voice_channel(
                            "waiting-verify",
                            category=voice_verify_category,
                            overwrites=waiting_overwrites,
                            reason="ModBot Setup: verification waiting voice channel",
                        )
                        created_channels.append(f"✅ {waiting_voice.mention}")
                    else:
                        await waiting_voice.edit(
                            category=voice_verify_category,
                            overwrites=waiting_overwrites,
                            reason="ModBot Setup: update waiting-verify permissions",
                        )
                        created_channels.append(f"✅ {waiting_voice.mention} (already exists)")

                    settings["waiting_verify_voice_channel"] = waiting_voice.id
                except Exception as e:
                    errors.append(f"❌ Failed to create waiting-verify voice channel: {e}")
                    waiting_voice = None

                # Lock down the verification category so only unverified + staff can see it.
                if verify_category:
                    try:
                        verify_category_overwrites: dict[
                            discord.abc.Snowflake, discord.PermissionOverwrite
                        ] = {
                            guild.default_role: discord.PermissionOverwrite(view_channel=False),
                            unverified_role: discord.PermissionOverwrite(view_channel=True),
                            guild.me: discord.PermissionOverwrite(
                                view_channel=True,
                                send_messages=True,
                                manage_channels=True,
                            ),
                        }
                        for key in [
                            "admin_role",
                            "supervisor_role",
                            "senior_mod_role",
                            "mod_role",
                            "staff_role",
                        ]:
                            rid = settings.get(key)
                            role = guild.get_role(rid) if rid else None
                            if role:
                                verify_category_overwrites[role] = discord.PermissionOverwrite(
                                    view_channel=True
                                )
                        await verify_category.edit(
                            overwrites=verify_category_overwrites,
                            reason="ModBot Setup: lock verification category",
                        )
                        # Clear any previous explicit verified overwrite (so staff roles can still see it).
                        try:
                            await verify_category.set_permissions(
                                verified_role,
                                overwrite=None,
                                reason="ModBot Setup: hide verification category from verified",
                            )
                        except Exception:
                            pass
                    except Exception as e:
                        errors.append(f"ƒs Л,? Could not set Verification category permissions: {e}")

                # Private verification logs channel (staff-only)
                verify_logs = discord.utils.get(guild.text_channels, name="verify-logs")
                verify_logs_overwrites: dict[
                    discord.abc.Snowflake, discord.PermissionOverwrite
                ] = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    unverified_role: discord.PermissionOverwrite(view_channel=False),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_channels=True,
                    ),
                }
                for key in [
                    "admin_role",
                    "supervisor_role",
                    "senior_mod_role",
                    "mod_role",
                    "staff_role",
                ]:
                    rid = settings.get(key)
                    role = guild.get_role(rid) if rid else None
                    if role:
                        verify_logs_overwrites[role] = discord.PermissionOverwrite(
                            view_channel=True,
                            send_messages=True,
                            read_message_history=True,
                        )

                verify_logs_category = mod_category or verify_category

                if not verify_logs:
                    try:
                        verify_logs = await guild.create_text_channel(
                            "verify-logs",
                            category=verify_logs_category,
                            topic="Verification events (staff-only)",
                            overwrites=verify_logs_overwrites,
                            reason="ModBot Setup: verification logs channel",
                        )
                        created_channels.append(f"ƒo. {verify_logs.mention}")
                    except Exception as e:
                        verify_logs = None
                        errors.append(f"ƒ?O Failed to create #verify-logs: {e}")
                else:
                    try:
                        await verify_logs.edit(
                            category=verify_logs_category,
                            overwrites=verify_logs_overwrites,
                            reason="ModBot Setup: update verify-logs permissions",
                        )
                    except Exception:
                        pass
                    created_channels.append(f"ƒo. {verify_logs.mention} (already exists)")

                if verify_logs:
                    settings["verify_log_channel"] = verify_logs.id
                    # Best-effort: push to bottom of the logs category.
                    if verify_logs_category and isinstance(verify_logs_category, discord.CategoryChannel):
                        try:
                            siblings = [
                                c
                                for c in guild.text_channels
                                if c.category_id == verify_logs_category.id
                            ]
                            max_pos = max([c.position for c in siblings], default=verify_logs.position)
                            await verify_logs.edit(
                                position=max_pos + 1,
                                reason="ModBot Setup: place verify-logs at bottom",
                            )
                        except Exception:
                            pass
                    # Clear any previous explicit verified overwrite (so staff roles can still see it).
                    try:
                        await verify_logs.set_permissions(
                            verified_role,
                            overwrite=None,
                            reason="ModBot Setup: verified should not see verify-logs",
                        )
                    except Exception:
                        pass

                # Keep the verify channel clean (read-only)
                if verify_channel:
                    try:
                        await verify_channel.set_permissions(
                            guild.default_role,
                            view_channel=False,
                            send_messages=False,
                            reason="ModBot Setup: lock verify channel",
                        )
                        await verify_channel.set_permissions(
                            unverified_role,
                            view_channel=True,
                            send_messages=False,
                            read_message_history=True,
                            reason="ModBot Setup: allow unverified to see verify channel",
                        )
                        for key in [
                            "admin_role",
                            "supervisor_role",
                            "senior_mod_role",
                            "mod_role",
                            "staff_role",
                        ]:
                            rid = settings.get(key)
                            role = guild.get_role(rid) if rid else None
                            if role:
                                await verify_channel.set_permissions(
                                    role,
                                    view_channel=True,
                                    send_messages=True,
                                    read_message_history=True,
                                    reason="ModBot Setup: allow staff to manage verify channel",
                                )
                        # Clear any previous explicit verified overwrite (so staff roles can still see it).
                        try:
                            await verify_channel.set_permissions(
                                verified_role,
                                overwrite=None,
                                reason="ModBot Setup: hide verify channel from verified",
                            )
                        except Exception:
                            pass
                    except Exception as e:
                        errors.append(f"ƒs Л,? Could not set #verify permissions: {e}")

                # Allow unverified to chat in unverified-chat
                if unverified_chat:
                    try:
                        await unverified_chat.set_permissions(
                            guild.default_role,
                            view_channel=False,
                            reason="ModBot Setup: lock unverified-chat to unverified role",
                        )
                        await unverified_chat.set_permissions(
                            unverified_role,
                            view_channel=True,
                            send_messages=True,
                            read_message_history=True,
                            reason="ModBot Setup: allow unverified chat",
                        )
                        for key in [
                            "admin_role",
                            "supervisor_role",
                            "senior_mod_role",
                            "mod_role",
                            "staff_role",
                        ]:
                            rid = settings.get(key)
                            role = guild.get_role(rid) if rid else None
                            if role:
                                await unverified_chat.set_permissions(
                                    role,
                                    view_channel=True,
                                    send_messages=True,
                                    read_message_history=True,
                                    reason="ModBot Setup: allow staff to see unverified-chat",
                                )
                        # Clear any previous explicit verified overwrite (so staff roles can still see it).
                        try:
                            await unverified_chat.set_permissions(
                                verified_role,
                                overwrite=None,
                                reason="ModBot Setup: hide unverified-chat from verified",
                            )
                        except Exception:
                            pass
                    except Exception as e:
                        errors.append(f"ƒs Л,? Could not set #unverified-chat permissions: {e}")

                # Restrict unverified users to only: welcome, verify, unverified-chat
                welcome_channel_id = int(
                    settings.get("welcome_channel")
                    or getattr(Config, "WELCOME_CHANNEL_ID", 0)
                    or 0
                )
                allowed_channel_ids: set[int] = set()
                if welcome_channel_id:
                    allowed_channel_ids.add(welcome_channel_id)
                if verify_channel:
                    allowed_channel_ids.add(verify_channel.id)
                if unverified_chat:
                    allowed_channel_ids.add(unverified_chat.id)
                if waiting_voice:
                    allowed_channel_ids.add(waiting_voice.id)

                # Deny at category-level first (more reliable with synced permissions).
                category_denied = 0
                category_failed = 0
                welcome_channel = guild.get_channel(welcome_channel_id) if welcome_channel_id else None
                skip_category_ids: set[int] = set()
                if isinstance(welcome_channel, discord.TextChannel) and welcome_channel.category_id:
                    skip_category_ids.add(int(welcome_channel.category_id))
                if verify_category:
                    skip_category_ids.add(int(verify_category.id))
                if voice_verify_category:
                    skip_category_ids.add(int(voice_verify_category.id))

                for cat in guild.categories:
                    if cat.id in skip_category_ids:
                        continue
                    try:
                        await cat.set_permissions(
                            unverified_role,
                            view_channel=False,
                            reason="ModBot Setup: restrict unverified category access",
                        )
                        category_denied += 1
                    except Exception:
                        category_failed += 1

                restricted_count = 0
                permission_failed = 0
                permission_failed_sample: str | None = None
                for ch in guild.channels:
                    if isinstance(ch, discord.CategoryChannel):
                        continue
                    if not hasattr(ch, "set_permissions"):
                        continue

                    try:
                        if ch.id in allowed_channel_ids:
                            if ch.id == welcome_channel_id:
                                await ch.set_permissions(
                                    unverified_role,
                                    view_channel=True,
                                    send_messages=False,
                                    read_message_history=True,
                                    reason="ModBot Setup: allow unverified to see welcome",
                                )
                            elif waiting_voice and ch.id == waiting_voice.id:
                                await ch.set_permissions(
                                    unverified_role,
                                    view_channel=True,
                                    connect=True,
                                    reason="ModBot Setup: allow unverified to use waiting-verify voice",
                                )
                            elif verify_channel and ch.id == verify_channel.id:
                                # already set above
                                pass
                            elif unverified_chat and ch.id == unverified_chat.id:
                                # already set above
                                pass
                            else:
                                await ch.set_permissions(
                                    unverified_role,
                                    view_channel=True,
                                    reason="ModBot Setup: allow unverified channel visibility",
                                )
                        else:
                            await ch.set_permissions(
                                unverified_role,
                                view_channel=False,
                                reason="ModBot Setup: restrict unverified access",
                            )
                            restricted_count += 1
                    except Exception as e:
                        permission_failed += 1
                        if permission_failed_sample is None:
                            permission_failed_sample = f"{type(e).__name__}: {e}"

                if category_denied:
                    created_channels.append(
                        f"ƒo. Denied {category_denied} categories for unverified role"
                    )
                if category_failed:
                    errors.append(
                        f"ƒs Л,? Could not update {category_failed} categories for unverified role (check bot permissions)."
                    )

                if restricted_count:
                    created_channels.append(
                        f"ƒo. Restricted {restricted_count} channels for unverified role"
                    )

                if permission_failed:
                    msg = f"ƒs Л,? Failed to update {permission_failed} channel overwrites for unverified role."
                    if permission_failed_sample:
                        msg += f" Example: {permission_failed_sample}"
                    errors.append(msg)

                # Reset member roles: everyone -> unverified (owners bypass)
                if verify:
                    updated_members = 0
                    for idx, member in enumerate(list(guild.members)):
                        if member.bot:
                            continue

                        managed_roles = [r for r in member.roles if getattr(r, "managed", False)]
                        desired_roles = [r for r in managed_roles if r != guild.default_role] + [
                            unverified_role
                        ]
                        current_roles = [r for r in member.roles if r != guild.default_role]

                        if {r.id for r in current_roles} == {r.id for r in desired_roles}:
                            continue

                        try:
                            await member.edit(
                                roles=desired_roles,
                                reason="ModBot Setup: enforce verification (unverified)",
                            )
                            updated_members += 1
                        except Exception as e:
                            errors.append(
                                f"ƒs Л,? Could not reset roles for {member} ({member.id}): {type(e).__name__}"
                            )

                        if idx and idx % 10 == 0:
                            await asyncio.sleep(1)

                    if updated_members:
                        created_roles.append(
                            f"ƒo. Reset roles for {updated_members} members → unverified"
                        )
                else:
                    created_roles.append("ƒo. Skipped global role reset (verify=false)")
        except Exception as e:
            errors.append(f"ƒ?O Verification setup failed: {e}")

        # ==================== SAVE SETTINGS ====================
        settings["setup_complete"] = True
        await self.bot.db.update_settings(guild.id, settings)

        # ==================== SUMMARY EMBED ====================
        summary = discord.Embed(
            title="🛡️ Setup Complete!",
            description="Your server is now configured for moderation, court, and modmail systems.",
            color=Config.COLOR_SUCCESS,
        )

        roles_text = "\n".join(created_roles[:12]) if created_roles else "No roles created"
        channels_text = (
            "\n".join(created_channels[:15]) if created_channels else "No channels created"
        )

        summary.add_field(name="📋 Roles Created", value=roles_text, inline=False)
        summary.add_field(name="📝 Channels Created", value=channels_text, inline=False)

        if errors:
            summary.add_field(
                name="⚠️ Errors",
                value="\n".join(errors[:5]),
                inline=False,
            )

        summary.add_field(
            name="🏷️ Role Hierarchy (Top to Bottom)",
            value=(
                "1. 👑 Admin - Full server control\n"
                "2. 👁️ Supervisor - Can sanction ALL staff\n"
                "3. ⚔️ Senior Moderator - Full moderation\n"
                "4. 🛡️ Moderator - Standard moderation\n"
                "5. 🔰 Trial Moderator - Limited moderation\n"
                "6. ⭐ Staff - Basic permissions"
            ),
            inline=False,
        )

        summary.add_field(
            name="📌 Next Steps",
            value=(
                "1️⃣ Move the created roles above member roles in hierarchy\n"
                "2️⃣ Assign **👑 Admin** to administrators\n"
                "3️⃣ Assign **👁️ Supervisor** to staff supervisors\n"
                "4️⃣ Run `/staffguide post` in #staff-guide\n"
                "5️⃣ Run `/rules post` in your rules channel\n"
                "6️⃣ Configure AutoMod with `/automod enable`\n"
                "7️⃣ Use `/court` to start court sessions\n"
                "8️⃣ Run `/verifypanel` in #verify to post the verification panel\n"
                "9️⃣ **Test modmail by DMing the bot `.modmail`**"
            ),
            inline=False,
        )

        summary.set_footer(text="Use /help for all available commands")

        # Components v2: original interaction response cannot be edited with embeds.
        layout = await layout_view_from_embeds(embed=summary)
        await interaction.edit_original_response(view=layout)


async def setup(bot: commands.Bot):
    await bot.add_cog(Setup(bot))
