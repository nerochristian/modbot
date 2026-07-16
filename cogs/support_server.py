"""Docket's first-party support server provisioning and presentation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from cogs.tickets import TicketDetailsModal
from config import Config


SUPPORT_BANNER = Path(__file__).resolve().parents[1] / "assets" / "started.png"

SUPPORT_TICKET_OPTIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "general",
        "label": "Help Desk",
        "description": "Get help configuring or using Docket",
        "emoji": "🛟",
        "heading": "Help Desk",
        "summary": "Tell us what you are trying to do and where you got stuck.",
        "placeholder": "Open a help ticket…",
        "questions": [
            {
                "id": "topic",
                "label": "What do you need help with?",
                "placeholder": "AutoMod, dashboard, tickets, commands…",
                "style": "short",
                "required": True,
            },
            {
                "id": "details",
                "label": "What happened?",
                "placeholder": "Describe what you tried and what you expected…",
                "style": "paragraph",
                "required": True,
            },
        ],
    },
    {
        "id": "bug",
        "label": "Bug Report",
        "description": "Report something broken or inconsistent",
        "emoji": "🐛",
        "heading": "Bug Reports",
        "summary": "Give us enough detail to reproduce the problem and fix the right path.",
        "placeholder": "Report a bug…",
        "questions": [
            {
                "id": "area",
                "label": "Where is the bug?",
                "placeholder": "Dashboard, AutoMod, command name…",
                "style": "short",
                "required": True,
            },
            {
                "id": "summary",
                "label": "What is broken?",
                "placeholder": "A short description of the problem",
                "style": "short",
                "required": True,
            },
            {
                "id": "steps",
                "label": "How can we reproduce it?",
                "placeholder": "List the exact steps that trigger the bug…",
                "style": "paragraph",
                "required": True,
            },
            {
                "id": "result",
                "label": "Expected vs. actual result",
                "placeholder": "What should happen, and what happens instead?",
                "style": "paragraph",
                "required": True,
            },
            {
                "id": "evidence",
                "label": "Evidence (optional)",
                "placeholder": "Screenshot, message, or video links",
                "style": "paragraph",
                "required": False,
            },
        ],
    },
    {
        "id": "feature",
        "label": "Feature Request",
        "description": "Suggest an improvement for Docket",
        "emoji": "💡",
        "heading": "Feature Requests",
        "summary": "Explain the problem first, then the change that would make Docket better.",
        "placeholder": "Suggest a feature…",
        "questions": [
            {
                "id": "title",
                "label": "Feature name",
                "placeholder": "A short name for your idea",
                "style": "short",
                "required": True,
            },
            {
                "id": "problem",
                "label": "What problem does it solve?",
                "placeholder": "Describe the workflow or limitation…",
                "style": "paragraph",
                "required": True,
            },
            {
                "id": "solution",
                "label": "How should it work?",
                "placeholder": "Describe the behavior you would like…",
                "style": "paragraph",
                "required": True,
            },
            {
                "id": "context",
                "label": "Extra context (optional)",
                "placeholder": "Examples, screenshots, or related tools",
                "style": "paragraph",
                "required": False,
            },
        ],
    },
)


def _public_base_url() -> str:
    return (
        os.getenv("DASHBOARD_PUBLIC_URL")
        or os.getenv("FRONTEND_PUBLIC_URL")
        or "https://docketbot.xyz"
    ).strip().rstrip("/")


def _ticket_option_for_storage(option: dict[str, Any]) -> dict[str, Any]:
    return {
        key: option[key]
        for key in ("id", "label", "description", "emoji", "questions")
    }


def build_welcome_view(guild_name: str, *, include_banner: bool = True) -> discord.ui.LayoutView:
    base_url = _public_base_url()
    children: list[discord.ui.Item] = []
    if include_banner:
        children.append(
            discord.ui.MediaGallery(discord.MediaGalleryItem("attachment://started.png"))
        )
    children.extend(
        [
            discord.ui.TextDisplay(
                f"### Welcome to {guild_name}\n"
                "## Docket support starts here\n"
                "-# Find answers, report bugs, suggest features, and follow service updates."
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.Section(
                discord.ui.TextDisplay(
                    "## 🧭 Start here\n"
                    "-# Read the rules, check bot status, then choose the support channel that matches your request."
                ),
                accessory=discord.ui.Button(label="View commands", url=f"{base_url}/commands"),
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.Section(
                discord.ui.TextDisplay(
                    "## ⚙️ Manage Docket\n"
                    "-# Open the dashboard to configure your server, modules, staff, and protection rules."
                ),
                accessory=discord.ui.Button(label="Dashboard", url=f"{base_url}/servers"),
            ),
        ]
    )
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(discord.ui.Container(*children, accent_color=Config.COLOR_BRAND))
    return view


def build_rules_view() -> discord.ui.LayoutView:
    rules = discord.ui.TextDisplay(
        "## 📜 Docket Support Rules\n"
        "-# These rules keep support useful, safe, and easy to search.\n\n"
        "### 1. Respect people\n"
        "-# No harassment, hate speech, threats, or hostile behavior toward members or staff.\n\n"
        "### 2. Use the correct support channel\n"
        "-# Help requests, bugs, and feature ideas have separate ticket forms. Do not open duplicates.\n\n"
        "### 3. Include useful evidence\n"
        "-# Share exact commands, screenshots, error messages, and reproduction steps. Remove tokens and private data first.\n\n"
        "### 4. No spam or advertising\n"
        "-# Do not mass mention, flood channels, solicit members, or advertise unrelated servers and services.\n\n"
        "### 5. Protect accounts and credentials\n"
        "-# Staff will never ask for your bot token, password, recovery code, or payment information.\n\n"
        "### 6. Follow Discord's policies\n"
        "-# Discord's Terms of Service and Community Guidelines apply everywhere in this server."
    )
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(discord.ui.Container(rules, accent_color=Config.COLOR_BRAND))
    return view


def build_announcements_view() -> discord.ui.LayoutView:
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(
        discord.ui.Container(
            discord.ui.TextDisplay(
                "## 📣 Docket Announcements\n"
                "-# Releases, maintenance windows, important fixes, and changes that affect your server appear here."
            ),
            accent_color=Config.COLOR_BRAND,
        )
    )
    return view


def build_status_view(bot: commands.Bot) -> discord.ui.LayoutView:
    now = discord.utils.utcnow()
    start_time = getattr(bot, "start_time", now)
    uptime_seconds = max(0, int((now - start_time).total_seconds()))
    days, remainder = divmod(uptime_seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes = remainder // 60
    uptime = f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m"
    latency = max(0, round(float(getattr(bot, "latency", 0.0)) * 1000))
    version = str(getattr(bot, "version", "unknown"))
    avatar_url = str(bot.user.display_avatar.url) if getattr(bot, "user", None) else None

    status_text = discord.ui.TextDisplay(
        "## 🟢 All systems operational\n"
        "-# Docket is connected and accepting commands and ticket interactions."
    )
    details = discord.ui.TextDisplay(
        f"### Live connection\n"
        f"-# Gateway latency: **{latency} ms**\n"
        f"-# Uptime: **{uptime}**\n"
        f"-# Version: **{version}**"
    )
    children: list[discord.ui.Item] = [status_text, discord.ui.Separator()]
    if avatar_url:
        children.append(discord.ui.Section(details, accessory=discord.ui.Thumbnail(avatar_url)))
    else:
        children.append(details)
    children.extend(
        [
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(f"-# Last checked {discord.utils.format_dt(now, style='R')}"),
        ]
    )
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(discord.ui.Container(*children, accent_color=0x57F287))
    return view


class SupportRequestPanelView(discord.ui.LayoutView):
    """A dedicated V2 ticket panel backed by Docket's existing ticket engine."""

    def __init__(self, tickets_cog: commands.Cog, option: dict[str, Any]):
        super().__init__(timeout=None)
        self.tickets_cog = tickets_cog
        self.option = option

        select = discord.ui.Select(
            custom_id=f"docket:support-ticket:{option['id']}",
            placeholder=str(option["placeholder"]),
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=str(option["label"]),
                    value=str(option["id"]),
                    description=str(option["description"]),
                    emoji=str(option["emoji"]),
                )
            ],
        )

        async def select_callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(
                TicketDetailsModal(self.tickets_cog, option=self.option)
            )

        select.callback = select_callback
        container = discord.ui.Container(
            discord.ui.TextDisplay(
                f"## {option['emoji']} {option['heading']}\n"
                f"-# {option['summary']}"
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(
                "### What happens next\n"
                "-# Complete the form below. Docket creates a private channel where support staff can claim and resolve your request."
            ),
            discord.ui.ActionRow(select),
            discord.ui.TextDisplay(
                "-# Closing a ticket generates a transcript for support records. Please open one ticket per issue."
            ),
            accent_color=Config.COLOR_BRAND,
        )
        self.add_item(container)


class SupportServer(commands.GroupCog, group_name="supportserver", group_description="Manage Docket's support server"):
    """Owner-only support server provisioning and live status updates."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        tickets_cog = self.bot.get_cog("Tickets")
        if tickets_cog is not None:
            for option in SUPPORT_TICKET_OPTIONS:
                self.bot.add_view(SupportRequestPanelView(tickets_cog, option))
        if not self.status_refresh.is_running():
            self.status_refresh.start()

    def cog_unload(self) -> None:
        self.status_refresh.cancel()

    @staticmethod
    async def _ensure_role(
        guild: discord.Guild,
        *,
        name: str,
        color: discord.Color,
        permissions: discord.Permissions,
    ) -> discord.Role:
        role = discord.utils.find(lambda item: item.name.casefold() == name.casefold(), guild.roles)
        if role is None:
            return await guild.create_role(
                name=name,
                color=color,
                permissions=permissions,
                hoist=True,
                mentionable=False,
                reason="Docket support server setup",
            )
        if not role.managed and (role.color != color or role.permissions != permissions or not role.hoist):
            await role.edit(
                color=color,
                permissions=permissions,
                hoist=True,
                mentionable=False,
                reason="Repair Docket support role",
            )
        return role

    @staticmethod
    async def _ensure_category(
        guild: discord.Guild,
        *,
        name: str,
        overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite],
    ) -> discord.CategoryChannel:
        category = discord.utils.find(
            lambda item: item.name.casefold() == name.casefold(),
            guild.categories,
        )
        if category is None:
            return await guild.create_category(
                name,
                overwrites=overwrites,
                reason="Docket support server setup",
            )
        await category.edit(overwrites=overwrites, reason="Repair Docket support category")
        return category

    @staticmethod
    async def _ensure_text_channel(
        guild: discord.Guild,
        *,
        category: discord.CategoryChannel,
        name: str,
        topic: str,
        overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite],
    ) -> discord.TextChannel:
        channel = discord.utils.find(
            lambda item: isinstance(item, discord.TextChannel) and item.name.casefold() == name.casefold(),
            guild.channels,
        )
        if channel is None:
            return await guild.create_text_channel(
                name,
                category=category,
                topic=topic,
                overwrites=overwrites,
                reason="Docket support server setup",
            )
        await channel.edit(
            category=category,
            topic=topic,
            overwrites=overwrites,
            reason="Repair Docket support channel",
        )
        return channel

    @staticmethod
    async def _ensure_voice_channel(
        guild: discord.Guild,
        *,
        category: discord.CategoryChannel,
        name: str,
        overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite],
    ) -> discord.VoiceChannel:
        channel = discord.utils.find(
            lambda item: isinstance(item, discord.VoiceChannel) and item.name.casefold() == name.casefold(),
            guild.channels,
        )
        if channel is None:
            return await guild.create_voice_channel(
                name,
                category=category,
                overwrites=overwrites,
                reason="Docket support server setup",
            )
        await channel.edit(
            category=category,
            overwrites=overwrites,
            reason="Repair Docket support voice channel",
        )
        return channel

    async def _upsert_panel(
        self,
        channel: discord.TextChannel,
        *,
        message_id: Any,
        view: discord.ui.LayoutView,
        attachment: Optional[Path] = None,
    ) -> int:
        message: Optional[discord.Message] = None
        try:
            if message_id:
                message = await channel.fetch_message(int(message_id))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException, TypeError, ValueError):
            message = None

        if message is not None and self.bot.user is not None and message.author.id == self.bot.user.id:
            await message.edit(view=view)
            return message.id

        kwargs: dict[str, Any] = {
            "view": view,
            "allowed_mentions": discord.AllowedMentions.none(),
        }
        if attachment is not None and attachment.is_file():
            kwargs["file"] = discord.File(attachment, filename="started.png")
        message = await channel.send(**kwargs)
        return message.id

    async def _provision(self, guild: discord.Guild) -> dict[str, Any]:
        bot_member = guild.me
        if bot_member is None:
            raise RuntimeError("Docket's guild member could not be resolved.")

        moderator = await self._ensure_role(
            guild,
            name="Moderator",
            color=discord.Color.from_rgb(88, 101, 242),
            permissions=discord.Permissions(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                moderate_members=True,
                kick_members=True,
                ban_members=True,
            ),
        )
        support_team = await self._ensure_role(
            guild,
            name="Support Team",
            color=discord.Color.from_rgb(87, 242, 135),
            permissions=discord.Permissions(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                attach_files=True,
                embed_links=True,
            ),
        )
        docket_team = await self._ensure_role(
            guild,
            name="Docket Team",
            color=discord.Color.from_rgb(235, 69, 158),
            permissions=discord.Permissions(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                manage_channels=True,
                manage_roles=True,
                manage_guild=True,
                moderate_members=True,
                kick_members=True,
                ban_members=True,
                view_audit_log=True,
            ),
        )

        bot_access = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True,
            attach_files=True,
            embed_links=True,
        )
        public_read_only = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                add_reactions=False,
                read_message_history=True,
            ),
            bot_member: bot_access,
        }
        public_conversation = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                add_reactions=True,
                read_message_history=True,
            ),
            bot_member: bot_access,
            moderator: discord.PermissionOverwrite(manage_messages=True),
            support_team: discord.PermissionOverwrite(manage_messages=True),
            docket_team: discord.PermissionOverwrite(manage_messages=True),
        }
        public_voice = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                use_voice_activation=True,
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                move_members=True,
                mute_members=True,
            ),
            moderator: discord.PermissionOverwrite(move_members=True, mute_members=True),
            support_team: discord.PermissionOverwrite(move_members=True, mute_members=True),
            docket_team: discord.PermissionOverwrite(move_members=True, mute_members=True),
        }
        staff_only = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            bot_member: bot_access,
            moderator: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            support_team: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            docket_team: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
        }

        start_here = await self._ensure_category(
            guild, name="START HERE", overwrites=public_read_only
        )
        support = await self._ensure_category(
            guild, name="SUPPORT", overwrites=public_read_only
        )
        community = await self._ensure_category(
            guild, name="COMMUNITY", overwrites=public_conversation
        )
        staff = await self._ensure_category(guild, name="STAFF", overwrites=staff_only)
        open_tickets = await self._ensure_category(
            guild, name="OPEN TICKETS", overwrites=staff_only
        )

        channel_specs = (
            ("welcome", start_here, "welcome", "Start here for Docket support.", public_read_only),
            ("rules", start_here, "rules", "Rules for the Docket support community.", public_read_only),
            ("announcements", start_here, "announcements", "Official Docket news and releases.", public_read_only),
            ("status", start_here, "status", "Live Docket bot status.", public_read_only),
            ("help_desk", support, "help-desk", "Open a private general support ticket.", public_read_only),
            ("bug_reports", support, "bug-reports", "Open a private Docket bug report.", public_read_only),
            ("feature_requests", support, "feature-requests", "Open a private feature request.", public_read_only),
            ("bot_commands", support, "bot-commands", "Use Docket commands here.", public_conversation),
            ("general", community, "general", "Talk with the Docket community.", public_conversation),
            ("showcase", community, "showcase", "Share Docket setups and workflows.", public_conversation),
            ("staff_chat", staff, "staff-chat", "Private support staff coordination.", staff_only),
            ("support_logs", staff, "support-logs", "Ticket transcripts and support audit records.", staff_only),
        )
        channels: dict[str, discord.TextChannel] = {}
        for key, category, name, topic, overwrites in channel_specs:
            channels[key] = await self._ensure_text_channel(
                guild,
                category=category,
                name=name,
                topic=topic,
                overwrites=overwrites,
            )
        waiting_room = await self._ensure_voice_channel(
            guild,
            category=support,
            name="Support Waiting Room",
            overwrites=public_voice,
        )

        settings = await self.bot.db.get_settings(guild.id)
        await self.bot.db.update_settings(
            guild.id,
            {
                "support_server_enabled": True,
                "tickets_enabled": True,
                "ticket_category": open_tickets.id,
                "ticket_log_channel": channels["support_logs"].id,
                "ticket_support_role": support_team.id,
                "ticket_options": [
                    _ticket_option_for_storage(option) for option in SUPPORT_TICKET_OPTIONS
                ],
                "support_server_channels": {
                    **{key: channel.id for key, channel in channels.items()},
                    "support_waiting_room": waiting_room.id,
                },
            },
        )

        tickets_cog = self.bot.get_cog("Tickets")
        if tickets_cog is None:
            raise RuntimeError("The ticket cog is not loaded.")

        message_ids = dict(settings.get("support_server_messages") or {})
        message_ids["welcome"] = await self._upsert_panel(
            channels["welcome"],
            message_id=message_ids.get("welcome"),
            view=build_welcome_view(guild.name, include_banner=SUPPORT_BANNER.is_file()),
            attachment=SUPPORT_BANNER,
        )
        message_ids["rules"] = await self._upsert_panel(
            channels["rules"],
            message_id=message_ids.get("rules"),
            view=build_rules_view(),
        )
        message_ids["announcements"] = await self._upsert_panel(
            channels["announcements"],
            message_id=message_ids.get("announcements"),
            view=build_announcements_view(),
        )
        message_ids["status"] = await self._upsert_panel(
            channels["status"],
            message_id=message_ids.get("status"),
            view=build_status_view(self.bot),
        )

        panel_targets = (
            ("help_desk", SUPPORT_TICKET_OPTIONS[0]),
            ("bug_reports", SUPPORT_TICKET_OPTIONS[1]),
            ("feature_requests", SUPPORT_TICKET_OPTIONS[2]),
        )
        for key, option in panel_targets:
            message_ids[key] = await self._upsert_panel(
                channels[key],
                message_id=message_ids.get(key),
                view=SupportRequestPanelView(tickets_cog, option),
            )

        await self.bot.db.update_settings(
            guild.id,
            {"support_server_messages": message_ids},
        )
        return {
            "roles": (docket_team, support_team, moderator),
            "channels": channels,
            "voice_channel": waiting_room,
            "ticket_category": open_tickets,
        }

    @app_commands.command(name="setup", description="Create or repair Docket's support server")
    @app_commands.default_permissions(administrator=True)
    async def setup_support_server(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Run this command inside the Docket support server.", ephemeral=True
            )
            return
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message(
                "Only a Docket bot owner can provision the support server.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            result = await self._provision(interaction.guild)
        except discord.Forbidden:
            await interaction.followup.send(
                "Docket needs **Manage Server**, **Manage Channels**, **Manage Roles**, and **Manage Messages** to finish setup.",
                ephemeral=True,
            )
            return
        except Exception as exc:
            await interaction.followup.send(
                f"Support server setup failed: `{type(exc).__name__}: {exc}`",
                ephemeral=True,
            )
            raise

        await interaction.followup.send(
            f"Support server ready: **{len(result['channels']) + 1} channels**, "
            f"**{len(result['roles'])} staff roles**, and **3 ticket workflows** configured.",
            ephemeral=True,
        )

    @tasks.loop(minutes=2)
    async def status_refresh(self) -> None:
        for guild in tuple(self.bot.guilds):
            try:
                settings = await self.bot.db.get_settings(guild.id)
                if not settings.get("support_server_enabled"):
                    continue
                channels = settings.get("support_server_channels") or {}
                messages = settings.get("support_server_messages") or {}
                channel_id = int(channels.get("status") or 0)
                message_id = int(messages.get("status") or 0)
                channel = guild.get_channel(channel_id)
                if not isinstance(channel, discord.TextChannel) or message_id <= 0:
                    continue
                message = await channel.fetch_message(message_id)
                await message.edit(view=build_status_view(self.bot))
            except (discord.NotFound, discord.Forbidden):
                continue
            except Exception:
                continue

    @status_refresh.before_loop
    async def before_status_refresh(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SupportServer(bot))
