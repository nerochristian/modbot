"""
Ticket System - Support ticket management
"""

import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
from datetime import datetime
from typing import Optional, Literal, Any
import re
import unicodedata
from utils.embeds import ModEmbed
from utils.components_v2 import branded_panel_container
from utils.checks import is_mod, is_bot_owner_id
from utils.logging import send_log_embed
from config import Config
import io
from utils.transcript import generate_html_transcript

def _brand_assets(guild: Optional[discord.Guild], override_banner_url: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    logo_url = None
    banner_url = None

    # Prioritize override banner
    if override_banner_url:
        banner_url = override_banner_url
    elif guild and getattr(guild, "banner", None):
        try:
            banner_url = str(guild.banner.url)
        except Exception:
            pass
    
    # Fallback to config banner
    if not banner_url:
        banner_url = (getattr(Config, "SERVER_BANNER_URL", "") or "").strip() or None

    # Prioritize server icon for logo
    if guild and getattr(guild, "icon", None):
        try:
            logo_url = str(guild.icon.url)
        except Exception:
            pass

    # Fallback to config logo
    if not logo_url:
        logo_url = (getattr(Config, "SERVER_LOGO_URL", "") or "").strip() or None

    return logo_url, banner_url


class TicketPanelView(discord.ui.LayoutView):
    def __init__(self, cog: "Tickets", *, guild: Optional[discord.Guild] = None, banner_url: Optional[str] = None):
        super().__init__(timeout=None)
        self.cog = cog

        logo_url, banner_url = _brand_assets(guild, override_banner_url=banner_url)
        title = f"{guild.name} Tickets" if guild else "Tickets"
        description = (
            "If you need help, click on the option corresponding to the type of ticket you want to open.\n"
            "**Response time may vary due to many factors, so please be patient.**"
        )

        select = discord.ui.Select(
            placeholder="Select a ticket category...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label="Support",
                    value="general",
                    description="Help with an issue",
                    emoji="🛠️",
                ),
                discord.SelectOption(
                    label="Report",
                    value="report",
                    description="Report a user or problem",
                    emoji="🚨",
                ),
                discord.SelectOption(
                    label="Appeal",
                    value="appeal",
                    description="Appeal a punishment",
                    emoji="📝",
                ),
                discord.SelectOption(
                    label="Other",
                    value="other",
                    description="Anything else",
                    emoji="💬",
                ),
            ],
            custom_id="ticket_panel_select",
        )

        async def _select_cb(interaction: discord.Interaction):
            await self._on_select(interaction, select)

        select.callback = _select_cb

        container = branded_panel_container(
            title=title,
            description=description,
            banner_url=banner_url,
            logo_url=logo_url,
            accent_color=Config.COLOR_BRAND,
        )
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(discord.ui.ActionRow(select))
        self.add_item(container)

    async def _on_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if not interaction.guild or not interaction.guild_id:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Unavailable", "Tickets can only be created in a server."),
                ephemeral=True,
            )

        category = (select.values[0] if select.values else "general").strip().lower()
        await interaction.response.send_modal(TicketDetailsModal(self.cog, category=category))


def _slugify_display_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "user"

    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = name.lower()
    name = re.sub(r"[0-9]+", "", name)
    name = re.sub(r"[^a-z\\s-]", "", name)
    name = re.sub(r"\\s+", "-", name).strip("-")
    name = re.sub(r"-{2,}", "-", name)
    return name or "user"


def _unique_channel_name(base: str, existing_names: set[str]) -> str:
    base = (base or "").strip().lower()
    if base and base not in existing_names:
        return base

    alphabet = "abcdefghijklmnopqrstuvwxyz"
    suffix = 0
    while True:
        suffix += 1
        x = suffix
        letters = []
        while x > 0:
            x -= 1
            letters.append(alphabet[x % 26])
            x //= 26
        candidate = f"{base}-" + "".join(reversed(letters))
        if candidate not in existing_names:
            return candidate


def _ticket_category_label(category: str) -> str:
    category = (category or "general").strip().lower()
    return {
        "general": "Support",
        "report": "Report",
        "appeal": "Appeal",
        "other": "Other",
    }.get(category, "Support")


class TicketDetailsModal(discord.ui.Modal):
    def __init__(self, cog: "Tickets", *, category: str):
        self.cog = cog
        self.category = (category or "general").strip().lower()

        title = f"{_ticket_category_label(self.category)} Ticket"
        super().__init__(title=title, timeout=300)

        if self.category == "report":
            self.reported = discord.ui.TextInput(
                label="Who are you reporting? (name/ID)",
                placeholder="User#0000 or 1234567890",
                required=True,
                max_length=100,
            )
            self.reason = discord.ui.TextInput(
                label="Reason",
                placeholder="Explain what happened...",
                required=True,
                style=discord.TextStyle.paragraph,
                max_length=1000,
            )
            self.evidence = discord.ui.TextInput(
                label="Evidence (links) (optional)",
                placeholder="Links to screenshots/videos/messages",
                required=False,
                style=discord.TextStyle.paragraph,
                max_length=1000,
            )
            self.add_item(self.reported)
            self.add_item(self.reason)
            self.add_item(self.evidence)
        elif self.category == "appeal":
            self.punishment = discord.ui.TextInput(
                label="What are you appealing? (ban/mute/etc.)",
                placeholder="e.g. mute",
                required=True,
                max_length=60,
            )
            self.why = discord.ui.TextInput(
                label="Why should it be lifted?",
                placeholder="Explain why you should be unpunished...",
                required=True,
                style=discord.TextStyle.paragraph,
                max_length=1000,
            )
            self.add_item(self.punishment)
            self.add_item(self.why)
        else:
            self.details = discord.ui.TextInput(
                label="How can we help you?",
                placeholder="Describe your issue...",
                required=True,
                style=discord.TextStyle.paragraph,
                max_length=1000,
            )
            self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not interaction.guild_id:
            await interaction.response.send_message(
                embed=ModEmbed.error("Unavailable", "Tickets can only be created in a server."),
                ephemeral=True,
            )
            return

        details = ""
        if self.category == "report":
            evidence = (getattr(self, "evidence").value or "").strip()
            details = (
                f"**Reported:** {getattr(self, 'reported').value.strip()}\n"
                f"**Reason:** {getattr(self, 'reason').value.strip()}"
            )
            if evidence:
                details += f"\n**Evidence:** {evidence}"
        elif self.category == "appeal":
            details = (
                f"**Punishment:** {getattr(self, 'punishment').value.strip()}\n"
                f"**Appeal:** {getattr(self, 'why').value.strip()}"
            )
        else:
            details = getattr(self, "details").value.strip()

        await interaction.response.defer(ephemeral=True)
        await self.cog._create_ticket_from_panel(interaction, category=self.category, details=details)


class TicketThreadPanel(discord.ui.LayoutView):
    def __init__(
        self,
        cog: "Tickets",
        *,
        opener: discord.Member,
        category: str,
        details: str,
        claimed_by: Optional[int] = None,
    ):
        super().__init__(timeout=None)
        self.cog = cog
        self.opener_id = opener.id
        self.category = (category or "general").strip().lower()
        self.details = (details or "").strip()
        self.claimed_by = claimed_by

        opener_avatar = None
        try:
            opener_avatar = str(opener.display_avatar.url)
        except Exception:
            opener_avatar = None

        category_label = _ticket_category_label(self.category)

        assigned = (
            f"<@{claimed_by}> ({claimed_by})" if claimed_by else "*Unassigned*"
        )

        self.assigned_text = discord.ui.TextDisplay(f"**Assigned staff**\n{assigned}")

        # Main ticket card
        container_children: list[discord.ui.Item[Any]] = []
        header_text = (
            f"**{category_label} Ticket**\n"
            "Please wait until one of our support team members can help you.\n"
            "**Response time may vary due to many factors, so please be patient.**"
        )
        if opener_avatar:
            container_children.append(
                discord.ui.Section(
                    discord.ui.TextDisplay(header_text),
                    accessory=discord.ui.Thumbnail(opener_avatar),
                )
            )
        else:
            container_children.append(discord.ui.TextDisplay(header_text))
        container_children.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container_children.append(self.assigned_text)
        container_children.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container_children.append(
            discord.ui.TextDisplay(
                f"❓ **How can we help you?**\n```{(self.details or 'No details provided.').strip()}```"
            )
        )

        close_button = discord.ui.Button(
            label="Close Ticket",
            style=discord.ButtonStyle.danger,
            custom_id="ticket_close_v2",
        )
        claim_button = discord.ui.Button(
            label="Assign me",
            style=discord.ButtonStyle.success,
            custom_id="ticket_claim_v2",
        )
        self.close_button = close_button
        self.claim_button = claim_button

        async def _close_cb(interaction: discord.Interaction):
            await self.cog._handle_ticket_close_button(interaction, panel=self)

        async def _claim_cb(interaction: discord.Interaction):
            await self.cog._handle_ticket_claim_button(interaction, panel=self)

        close_button.callback = _close_cb
        claim_button.callback = _claim_cb

        container_children.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        container_children.append(discord.ui.ActionRow(close_button, claim_button))

        self.container = discord.ui.Container(*container_children, accent_color=Config.COLOR_BRAND)
        self.add_item(self.container)

    def set_claimed_by(self, user_id: int) -> None:
        self.claimed_by = user_id
        self.assigned_text.content = f"**Assigned staff**\n<@{user_id}> ({user_id})"


class TicketCloseButton(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Close Ticket", style=discord.ButtonStyle. danger, emoji="🔒", custom_id="ticket_close")
    async def close_ticket(self, interaction: discord. Interaction, button: ui.Button):
        await interaction.response. send_message("Closing ticket in 5 seconds...", ephemeral=True)
        await interaction.channel.send(embed=ModEmbed.warning("Ticket Closing", "This ticket will be closed in 5 seconds... "))
        
        import asyncio
        await asyncio.sleep(5)
        
        # Generate transcript
        messages = [m async for m in interaction.channel.history(limit=500, oldest_first=True)]
        transcript_file = generate_html_transcript(interaction.guild, interaction.channel, messages)
        transcript_file.seek(0)
        
        # Get ticket info
        ticket = await interaction.client.db.get_ticket(interaction.channel.id)
        if ticket:
            await interaction.client.db.close_ticket(interaction.channel.id)
            
            # Send transcript to log channel
            settings = await interaction.client.db. get_settings(interaction.guild_id)
            if settings.get('ticket_log_channel'):
                log_channel = interaction.guild.get_channel(settings['ticket_log_channel'])
                if log_channel:
                    embed = discord.Embed(
                        title=f"🎫 Ticket #{ticket['ticket_number']} Closed",
                        color=Config.COLOR_INFO,
                        timestamp=datetime. utcnow()
                    )
                    creator = interaction.guild.get_member(ticket['user_id'])
                    embed. add_field(name="Created By", value=creator.mention if creator else f"ID:  {ticket['user_id']}", inline=True)
                    embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
                    embed.add_field(name="Category", value=ticket['category'], inline=True)
                    
                    file = discord.File(transcript_file, filename=f"ticket-{ticket['ticket_number']}.html")
                    await send_log_embed(log_channel, embed, file=file)
        
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")

class TicketCreateButton(ui.View):
    def __init__(self, cog: Optional["Tickets"] = None):
        super().__init__(timeout=None)
        self.cog = cog
    
    @ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="ticket_create")
    async def create_ticket(self, interaction: discord.Interaction, button: ui. Button):
        if not self.cog:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Unavailable", "Ticket system is still starting up. Try again in a moment."),
                ephemeral=True,
            )
        await interaction.response.send_modal(TicketDetailsModal(self.cog, category="general"))

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Register persistent views
        self.bot.add_view(TicketCreateButton(self))
        self.bot.add_view(TicketCloseButton())
        self.bot.add_view(TicketPanelView(self))
    
    # ==================== CONSOLIDATED /ticket COMMAND ====================
    
    @app_commands.command(name="ticket", description="🎫 Ticket management commands")
    @app_commands.describe(
        action="The action to perform",
        category="Ticket category (for create)",
        reason="Reason (for close)",
        user="Target user (for add/remove)",
        name="New name (for rename)",
    )
    async def ticket(
        self,
        interaction: discord.Interaction,
        action: Literal["create", "close", "add", "remove", "rename", "transcript"],
        category: Optional[Literal['general', 'report', 'appeal', 'other']] = None,
        reason: Optional[str] = None,
        user: Optional[discord.Member] = None,
        name: Optional[str] = None,
    ):
        if action == "create":
            await interaction.response.send_modal(
                TicketDetailsModal(self, category=str(category or "general"))
            )
        elif action == "close":
            await self._ticket_close(interaction, reason)
        elif action == "add":
            await self._ticket_add(interaction, user)
        elif action == "remove":
            await self._ticket_remove(interaction, user)
        elif action == "rename":
            await self._ticket_rename(interaction, name)
        elif action == "transcript":
            await self._ticket_transcript(interaction)

    async def _ticket_close(self, interaction: discord.Interaction, reason: Optional[str]):
        ticket = await self.bot.db.get_ticket(interaction.channel.id)
        
        if not ticket:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not a Ticket", "This channel is not a ticket."),
                ephemeral=True
            )
        
        reason = reason or "No reason provided"
        await interaction.response.send_message(
            embed=ModEmbed.warning("Closing Ticket", f"This ticket will be closed in 5 seconds...\n**Reason:** {reason}")
        )
        
        await asyncio.sleep(5)
        
        # Generate transcript
        messages = [m async for m in interaction.channel.history(limit=500, oldest_first=True)]
        transcript_file = generate_html_transcript(interaction.guild, interaction.channel, messages)
        transcript_file.seek(0)
        await self.bot.db.close_ticket(interaction.channel.id)
        
        # Send transcript to log channel
        settings = await self.bot.db.get_settings(interaction.guild_id)
        if settings.get('ticket_log_channel'):
            log_channel = interaction.guild.get_channel(settings['ticket_log_channel'])
            if log_channel:
                embed = discord.Embed(
                    title=f"🎫 Ticket #{ticket['ticket_number']} Closed",
                    color=Config.COLOR_INFO,
                    timestamp=datetime.utcnow()
                )
                creator = interaction.guild.get_member(ticket['user_id'])
                embed.add_field(name="Created By", value=creator.mention if creator else f"ID: {ticket['user_id']}", inline=True)
                embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
                embed.add_field(name="Reason", value=reason, inline=False)
                
                file = discord.File(transcript_file, filename=f"ticket-{ticket['ticket_number']}.html")
                await send_log_embed(log_channel, embed, file=file)
        
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}: {reason}")

    async def _ticket_add(self, interaction: discord.Interaction, user: Optional[discord.Member]):
        # Check mod permission
        if not interaction.user.guild_permissions.manage_messages and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need mod permissions for this action."),
                ephemeral=True
            )

        if not user:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `user` to add."),
                ephemeral=True
            )

        ticket = await self.bot.db.get_ticket(interaction.channel.id)
        
        if not ticket:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not a Ticket", "This channel is not a ticket."),
                ephemeral=True
            )
        
        await interaction.channel.set_permissions(
            user,
            view_channel=True,
            send_messages=True,
            attach_files=True
        )
        
        embed = ModEmbed.success("User Added", f"{user.mention} has been added to this ticket.")
        await interaction.response.send_message(embed=embed)

    async def _ticket_remove(self, interaction: discord.Interaction, user: Optional[discord.Member]):
        # Check mod permission
        if not interaction.user.guild_permissions.manage_messages and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need mod permissions for this action."),
                ephemeral=True
            )

        if not user:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `user` to remove."),
                ephemeral=True
            )

        ticket = await self.bot.db.get_ticket(interaction.channel.id)
        
        if not ticket:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not a Ticket", "This channel is not a ticket."),
                ephemeral=True
            )
        
        if user.id == ticket['user_id']:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Cannot Remove", "You cannot remove the ticket creator."),
                ephemeral=True
            )
        
        await interaction.channel.set_permissions(user, overwrite=None)
        
        embed = ModEmbed.success("User Removed", f"{user.mention} has been removed from this ticket.")
        await interaction.response.send_message(embed=embed)

    async def _ticket_rename(self, interaction: discord.Interaction, name: Optional[str]):
        # Check mod permission
        if not interaction.user.guild_permissions.manage_messages and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need mod permissions for this action."),
                ephemeral=True
            )

        if not name:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `name` for the ticket."),
                ephemeral=True
            )

        ticket = await self.bot.db.get_ticket(interaction.channel.id)
        
        if not ticket:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not a Ticket", "This channel is not a ticket."),
                ephemeral=True
            )
        
        await interaction.channel.edit(name=name)
        embed = ModEmbed.success("Ticket Renamed", f"Ticket renamed to **{name}**")
        await interaction.response.send_message(embed=embed)

    async def _ticket_transcript(self, interaction: discord.Interaction):
        # Check mod permission
        if not interaction.user.guild_permissions.manage_messages and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need mod permissions for this action."),
                ephemeral=True
            )

        await interaction.response.defer()
        
        messages = [m async for m in interaction.channel.history(limit=500, oldest_first=True)]
        transcript_file = generate_html_transcript(interaction.guild, interaction.channel, messages)
        transcript_file.seek(0)
        
        file = discord.File(transcript_file, filename=f"transcript-{interaction.channel.name}.html")
        
        embed = ModEmbed.success("Transcript Generated", "Here is the transcript of this ticket.")
        await interaction.followup.send(embed=embed, file=file)

    async def _create_ticket_from_panel(self, interaction: discord.Interaction, *, category: str, details: str) -> None:
        settings = await self.bot.db.get_settings(interaction.guild_id)
        category_id = settings.get("ticket_category")

        if not category_id:
            await interaction.followup.send(
                embed=ModEmbed.error("Not Configured", "Ticket system is not set up. Run `/setup` first."),
                ephemeral=True,
            )
            return

        ticket_category = interaction.guild.get_channel(category_id)
        if not ticket_category:
            await interaction.followup.send(
                embed=ModEmbed.error("Category Missing", "Ticket category was deleted. Run `/setup` again."),
                ephemeral=True,
            )
            return

        topic_marker = f"({interaction.user.id})"
        for channel in ticket_category.channels:
            if getattr(channel, "topic", None) and topic_marker in (channel.topic or ""):
                await interaction.followup.send(
                    embed=ModEmbed.error("Ticket Exists", f"You already have an open ticket: {channel.mention}"),
                    ephemeral=True,
                )
                return

        category = (category or "general").strip().lower()
        category_label = _ticket_category_label(category)

        display_slug = _slugify_display_name(getattr(interaction.user, "display_name", str(interaction.user)))
        base_name = f"{category_label.lower()}-{display_slug}"
        existing_names = {c.name for c in ticket_category.channels}
        channel_name = _unique_channel_name(base_name, existing_names)

        ticket_number = await self.bot.db.get_next_ticket_number(interaction.guild_id)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }

        staff_role_id = settings.get("staff_role")
        if staff_role_id:
            role = interaction.guild.get_role(staff_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        for key in ["admin_role", "supervisor_role", "senior_mod_role", "mod_role", "trial_mod_role"]:
            if settings.get(key):
                role = interaction.guild.get_role(settings[key])
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await interaction.guild.create_text_channel(
            channel_name,
            category=ticket_category,
            overwrites=overwrites,
            topic=f"Ticket for {interaction.user} ({interaction.user.id}) | Category: {category}",
        )

        await self.bot.db.create_ticket(
            interaction.guild_id,
            channel.id,
            interaction.user.id,
            ticket_number,
            category,
            details=details,
        )

        panel_view = TicketThreadPanel(
            self,
            opener=interaction.user,
            category=category,
            details=details,
            claimed_by=None,
        )
        panel_message = await channel.send(view=panel_view)
        try:
            await panel_message.pin(reason="Ticket panel")
        except Exception:
            pass

        await interaction.followup.send(
            embed=discord.Embed(
                title="Ticket Created",
                description=f"Your ticket has been created: {channel.mention}",
                color=Config.COLOR_BRAND,
            ),
            ephemeral=True,
        )

    async def _is_ticket_staff(self, member: discord.Member, settings: dict) -> bool:
        if is_bot_owner_id(member.id):
            return True
        if member.guild_permissions.administrator:
            return True
        staff_role_id = settings.get("staff_role")
        if staff_role_id:
            staff_role = member.guild.get_role(staff_role_id)
            if staff_role and staff_role in member.roles:
                return True
        return False

    async def _handle_ticket_claim_button(self, interaction: discord.Interaction, *, panel: TicketThreadPanel) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("This can only be used in a server.", ephemeral=True)

        settings = await self.bot.db.get_settings(interaction.guild_id)
        if not await self._is_ticket_staff(interaction.user, settings):
            return await interaction.response.send_message("Only staff can claim tickets.", ephemeral=True)

        ticket = await self.bot.db.get_ticket(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)

        claimed_by = ticket.get("claimed_by")
        if claimed_by:
            return await interaction.response.send_message(f"This ticket is already claimed by <@{claimed_by}>.", ephemeral=True)

        await self.bot.db.claim_ticket(interaction.channel.id, interaction.user.id)

        panel.set_claimed_by(interaction.user.id)
        panel.claim_button.disabled = True
        try:
            await interaction.message.edit(view=panel)
        except Exception:
            pass

        await interaction.response.send_message("Ticket claimed.", ephemeral=True)

    async def _handle_ticket_close_button(self, interaction: discord.Interaction, *, panel: TicketThreadPanel) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("This can only be used in a server.", ephemeral=True)

        settings = await self.bot.db.get_settings(interaction.guild_id)
        is_staff = await self._is_ticket_staff(interaction.user, settings)
        if not is_staff and interaction.user.id != panel.opener_id:
            return await interaction.response.send_message("Only staff or the ticket creator can close this ticket.", ephemeral=True)

        await interaction.response.send_message("Closing ticket in 5 seconds...", ephemeral=True)
        await interaction.channel.send(
            embed=discord.Embed(
                title="Ticket Closing",
                description="This ticket will be closed in 5 seconds...",
                color=Config.COLOR_BRAND,
            )
        )

        await asyncio.sleep(Config.TICKET_CLOSE_DELAY)

        # Generate transcript
        messages = [m async for m in interaction.channel.history(limit=500, oldest_first=True)]
        transcript_file = generate_html_transcript(interaction.guild, interaction.channel, messages)
        transcript_file.seek(0)

        ticket = await self.bot.db.get_ticket(interaction.channel.id)
        if ticket:
            await self.bot.db.close_ticket(interaction.channel.id)

            settings = await self.bot.db.get_settings(interaction.guild_id)
            log_channel_id = settings.get("ticket_log_channel")
            if log_channel_id:
                log_channel = interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title=f"🎫 Ticket Closed",
                        color=Config.COLOR_BRAND,
                        timestamp=datetime.utcnow(),
                    )
                    creator = interaction.guild.get_member(ticket["user_id"])
                    embed.add_field(
                        name="Created By",
                        value=creator.mention if creator else f"ID: {ticket['user_id']}",
                        inline=True,
                    )
                    embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
                    embed.add_field(name="Category", value=ticket.get("category", "unknown"), inline=True)

                    file = discord.File(
                        transcript_file,
                        filename=f"ticket-{ticket['ticket_number']}.html",
                    )
                    await send_log_embed(log_channel, embed, file=file)

        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except Exception:
            pass
    
    
    @app_commands.command(name="ticketpanel", description="Create a ticket panel embed")
    @is_mod()
    async def ticketpanel(self, interaction:  discord.Interaction):
        embed = discord.Embed(
            title="🎫 Support Tickets",
            description="Need help?  Click the button below to create a support ticket!\n\n"
                        "**Guidelines:**\n"
                        "• Be patient and respectful\n"
                        "• Provide as much detail as possible\n"
                        "• Don't create multiple tickets for the same issue\n"
                        "• Don't ping staff unnecessarily",
            color=Config.COLOR_EMBED
        )
        embed.set_footer(text="Click the button below to open a ticket")
        
        settings = await self.bot.db.get_settings(interaction.guild_id)
        banner_url = settings.get("server_banner_url")

        await interaction.channel.send(view=TicketPanelView(self, guild=interaction.guild, banner_url=banner_url))
        await interaction.response.send_message(
            embed=ModEmbed. success("Panel Created", "Ticket panel has been created! "),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Tickets(bot))
