"""
Advanced Modmail System with Full Database Integration

- Complete database persistence
- Survives bot restarts
- Full message history with transcripts
- Advanced features (priority, claiming, transfers)
- Clean architecture with proper error handling
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
import asyncio
import io
import logging

from config import Config
from utils.embeds import ModEmbed, Colors
from utils.components_v2 import branded_panel_container
from utils.logging import send_log_embed

logger = logging.getLogger("ModBot.Modmail")

# ==================== CONSTANTS ====================
CATEGORY_EMOJIS = {
    "appeal": "⚖️",
    "support": "🎫",
    "report": "🚨",
    "feedback": "💬",
    "partnership": "🤝",
    "other": "📩"
}

PRIORITY_COLORS = {
    "low": 0x95A5A6,
    "normal": 0x3498DB,
    "high": 0xE67E22,
    "urgent": 0xE74C3C
}

PRIORITY_EMOJIS = {
    "low": "🟢",
    "normal": "🔵",
    "high": "🟠",
    "urgent": "🔴"
}

CHECK_EMOJI = "✅"
INACTIVE_WARNING_HOURS = 24
AUTO_CLOSE_HOURS = 48


# ==================== MODALS ====================
class AppealForm(discord.ui.Modal, title="Ban/Mute Appeal Form"):
    """Appeal form for banned/muted users"""
    
    username = discord.ui.TextInput(
        label="Your Discord Username",
        placeholder="e.g., Username#1234",
        required=True,
        max_length=100
    )
    
    reason_for_punishment = discord.ui.TextInput(
        label="What were you punished for?",
        placeholder="Explain the reason for your ban/mute",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )
    
    why_appeal = discord.ui.TextInput(
        label="Why should we unban/unmute you?",
        placeholder="Explain why you believe you should be unbanned/unmuted",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    what_learned = discord.ui.TextInput(
        label="What have you learned?",
        placeholder="What did you learn from this experience?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )
    
    additional_info = discord.ui.TextInput(
        label="Additional Information (Optional)",
        placeholder="Any other information you'd like to provide",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )
    
    def __init__(self, cog, user: discord.User):
        super().__init__()
        self.cog = cog
        self.user = user
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        data = {
            "category": "appeal",
            "username": str(self.username),
            "reason_for_punishment": str(self.reason_for_punishment),
            "why_appeal": str(self.why_appeal),
            "what_learned": str(self.what_learned),
            "additional_info": str(self.additional_info) if self.additional_info.value else "None provided"
        }
        
        success = await self.cog.create_modmail_thread(self.user, "appeal", data, priority="high")
        
        if success:
            embed = discord.Embed(
                title="✅ Appeal Submitted Successfully",
                description=(
                    "Your appeal has been submitted to our staff team.\n\n"
                    "**What happens next:**\n"
                    "• Staff will review your appeal\n"
                    "• You'll receive a response here via DM\n"
                    "• Average response time: 24-48 hours\n\n"
                    "Please be patient and do not spam or create multiple appeals."
                ),
                color=Colors.SUCCESS,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text="ModBot Modmail System")
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                embed=ModEmbed.error("Failed to Submit", "An error occurred while submitting your appeal. Please try again later."),
                ephemeral=True
            )


class SupportForm(discord.ui.Modal, title="Support Request Form"):
    """Support ticket form"""
    
    subject = discord.ui.TextInput(
        label="Subject",
        placeholder="Brief description of your issue",
        required=True,
        max_length=100
    )
    
    category = discord.ui.TextInput(
        label="Issue Category",
        placeholder="e.g., Account Issue, Bug Report, Feature Request",
        required=True,
        max_length=100
    )
    
    description = discord.ui.TextInput(
        label="Detailed Description",
        placeholder="Explain your issue in detail",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500
    )
    
    steps_to_reproduce = discord.ui.TextInput(
        label="Steps to Reproduce (if applicable)",
        placeholder="1. Go to...\n2. Click on...\n3. See error...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )
    
    urgency = discord.ui.TextInput(
        label="Urgency Level",
        placeholder="Low, Normal, High, or Urgent",
        required=True,
        max_length=20
    )
    
    def __init__(self, cog, user: discord.User):
        super().__init__()
        self.cog = cog
        self.user = user
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        urgency_input = str(self.urgency).lower()
        if "urgent" in urgency_input or "critical" in urgency_input:
            priority = "urgent"
        elif "high" in urgency_input:
            priority = "high"
        elif "low" in urgency_input:
            priority = "low"
        else:
            priority = "normal"
        
        data = {
            "category": "support",
            "subject": str(self.subject),
            "issue_category": str(self.category),
            "description": str(self.description),
            "steps_to_reproduce": str(self.steps_to_reproduce) if self.steps_to_reproduce.value else "N/A",
            "priority": priority
        }
        
        success = await self.cog.create_modmail_thread(self.user, "support", data, priority=priority)
        
        if success:
            embed = discord.Embed(
                title="✅ Support Request Submitted",
                description=(
                    f"Your support request has been submitted with **{priority.upper()}** priority.\n\n"
                    "**What happens next:**\n"
                    "• Our support team will review your request\n"
                    "• You'll receive updates here via DM\n"
                    f"• Priority: {PRIORITY_EMOJIS[priority]} {priority.capitalize()}\n\n"
                    "You can continue to send messages here and they will be forwarded to staff."
                ),
                color=PRIORITY_COLORS[priority],
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"Priority: {priority.upper()}")
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                embed=ModEmbed.error("Failed to Submit", "An error occurred. Please try again later."),
                ephemeral=True
            )


class ReportForm(discord.ui.Modal, title="User Report Form"):
    """Report form for rule violations"""
    
    reported_user = discord.ui.TextInput(
        label="User Being Reported",
        placeholder="Username#1234 or User ID",
        required=True,
        max_length=100
    )
    
    violation_type = discord.ui.TextInput(
        label="Type of Violation",
        placeholder="e.g., Harassment, Spam, Scam, etc.",
        required=True,
        max_length=100
    )
    
    description = discord.ui.TextInput(
        label="Detailed Description",
        placeholder="Describe what happened in detail",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500
    )
    
    evidence = discord.ui.TextInput(
        label="Evidence Links (Optional)",
        placeholder="Paste message links, image URLs, etc.",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )
    
    witnesses = discord.ui.TextInput(
        label="Witnesses (Optional)",
        placeholder="List any users who witnessed this",
        required=False,
        max_length=200
    )
    
    def __init__(self, cog, user: discord.User):
        super().__init__()
        self.cog = cog
        self.user = user
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        data = {
            "category": "report",
            "reported_user": str(self.reported_user),
            "violation_type": str(self.violation_type),
            "description": str(self.description),
            "evidence": str(self.evidence) if self.evidence.value else "No evidence provided",
            "witnesses": str(self.witnesses) if self.witnesses.value else "None listed"
        }
        
        success = await self.cog.create_modmail_thread(self.user, "report", data, priority="high")
        
        if success:
            embed = discord.Embed(
                title="✅ Report Submitted",
                description=(
                    "Your report has been submitted to our moderation team.\n\n"
                    "**What happens next:**\n"
                    "• Moderators will investigate the report\n"
                    "• Appropriate action will be taken if needed\n"
                    "• You may be contacted for more information\n\n"
                    "Thank you for helping keep our community safe."
                ),
                color=Colors.ERROR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text="⚠️ High Priority Report")
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                embed=ModEmbed.error("Failed to Submit", "An error occurred. Please try again later."),
                ephemeral=True
            )


class FeedbackForm(discord.ui.Modal, title="Feedback & Suggestions"):
    """Feedback and suggestions form"""
    
    feedback_type = discord.ui.TextInput(
        label="Feedback Type",
        placeholder="e.g., Suggestion, Complaint, Compliment, General",
        required=True,
        max_length=50
    )
    
    subject = discord.ui.TextInput(
        label="Subject",
        placeholder="Brief summary of your feedback",
        required=True,
        max_length=100
    )
    
    details = discord.ui.TextInput(
        label="Detailed Feedback",
        placeholder="Provide your feedback in detail",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500
    )
    
    suggestions = discord.ui.TextInput(
        label="Suggestions for Improvement (Optional)",
        placeholder="How can we improve?",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )
    
    rating = discord.ui.TextInput(
        label="Overall Rating (1-10)",
        placeholder="Rate your experience from 1 to 10",
        required=False,
        max_length=2
    )
    
    def __init__(self, cog, user: discord.User):
        super().__init__()
        self.cog = cog
        self.user = user
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        rating_value = "Not provided"
        if self.rating.value:
            try:
                rating_num = int(self.rating.value)
                if 1 <= rating_num <= 10:
                    rating_value = f"{rating_num}/10"
            except ValueError:
                pass
        
        data = {
            "category": "feedback",
            "feedback_type": str(self.feedback_type),
            "subject": str(self.subject),
            "details": str(self.details),
            "suggestions": str(self.suggestions) if self.suggestions.value else "None provided",
            "rating": rating_value
        }
        
        success = await self.cog.create_modmail_thread(self.user, "feedback", data, priority="low")
        
        if success:
            embed = discord.Embed(
                title="✅ Feedback Submitted",
                description=(
                    "Thank you for your feedback!\n\n"
                    "**What happens next:**\n"
                    "• Your feedback will be reviewed by our team\n"
                    "• We appreciate your input and suggestions\n"
                    "• You may receive a response if needed\n\n"
                    "Your feedback helps us improve!"
                ),
                color=Colors.INFO,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text="Thank you for your contribution!")
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                embed=ModEmbed.error("Failed to Submit", "An error occurred. Please try again later."),
                ephemeral=True
            )


class PartnershipForm(discord.ui.Modal, title="Partnership Request"):
    """Partnership proposal form"""
    
    server_name = discord.ui.TextInput(
        label="Server/Community Name",
        placeholder="Name of your server or community",
        required=True,
        max_length=100
    )
    
    member_count = discord.ui.TextInput(
        label="Member Count",
        placeholder="Approximate number of members",
        required=True,
        max_length=50
    )
    
    description = discord.ui.TextInput(
        label="Server Description",
        placeholder="Brief description of your server/community",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )
    
    partnership_benefits = discord.ui.TextInput(
        label="Partnership Benefits",
        placeholder="What can you offer? What are you looking for?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=800
    )
    
    invite_link = discord.ui.TextInput(
        label="Invite Link (Optional)",
        placeholder="Permanent invite link to your server",
        required=False,
        max_length=100
    )
    
    def __init__(self, cog, user: discord.User):
        super().__init__()
        self.cog = cog
        self.user = user
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        data = {
            "category": "partnership",
            "server_name": str(self.server_name),
            "member_count": str(self.member_count),
            "description": str(self.description),
            "partnership_benefits": str(self.partnership_benefits),
            "invite_link": str(self.invite_link) if self.invite_link.value else "Not provided"
        }
        
        success = await self.cog.create_modmail_thread(self.user, "partnership", data, priority="normal")
        
        if success:
            embed = discord.Embed(
                title="✅ Partnership Request Submitted",
                description=(
                    "Your partnership request has been submitted!\n\n"
                    "**What happens next:**\n"
                    "• Our partnership team will review your request\n"
                    "• We'll evaluate if it's a good fit\n"
                    "• You'll receive a response within 3-5 business days\n\n"
                    "Thank you for your interest in partnering with us!"
                ),
                color=Colors.INFO,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text="Partnership Team")
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                embed=ModEmbed.error("Failed to Submit", "An error occurred. Please try again later."),
                ephemeral=True
            )


# ==================== VIEWS ====================
class ModmailCategorySelect(discord.ui.LayoutView):
    """Category selection menu for modmail"""
    
    def __init__(self, cog, user: discord.User, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.user = user

        appeal_button = discord.ui.Button(
            label="Ban/Mute Appeal",
            style=discord.ButtonStyle.danger,
            emoji="⚖️",
            row=0,
        )
        support_button = discord.ui.Button(
            label="Support Request",
            style=discord.ButtonStyle.primary,
            emoji="🎫",
            row=0,
        )
        report_button = discord.ui.Button(
            label="Report User",
            style=discord.ButtonStyle.danger,
            emoji="🚨",
            row=0,
        )
        feedback_button = discord.ui.Button(
            label="Feedback/Suggestions",
            style=discord.ButtonStyle.success,
            emoji="💬",
            row=1,
        )
        partnership_button = discord.ui.Button(
            label="Partnership Request",
            style=discord.ButtonStyle.success,
            emoji="🤝",
            row=1,
        )
        other_button = discord.ui.Button(
            label="General Inquiry",
            style=discord.ButtonStyle.secondary,
            emoji="📩",
            row=1,
        )
        cancel_button = discord.ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.secondary,
            emoji="❌",
            row=2,
        )

        async def _appeal(interaction: discord.Interaction):
            return await self.appeal_button(interaction, appeal_button)

        async def _support(interaction: discord.Interaction):
            return await self.support_button(interaction, support_button)

        async def _report(interaction: discord.Interaction):
            return await self.report_button(interaction, report_button)

        async def _feedback(interaction: discord.Interaction):
            return await self.feedback_button(interaction, feedback_button)

        async def _partnership(interaction: discord.Interaction):
            return await self.partnership_button(interaction, partnership_button)

        async def _other(interaction: discord.Interaction):
            return await self.other_button(interaction, other_button)

        async def _cancel(interaction: discord.Interaction):
            return await self.cancel_button(interaction, cancel_button)

        appeal_button.callback = _appeal
        support_button.callback = _support
        report_button.callback = _report
        feedback_button.callback = _feedback
        partnership_button.callback = _partnership
        other_button.callback = _other
        cancel_button.callback = _cancel

        self.add_item(appeal_button)
        self.add_item(support_button)
        self.add_item(report_button)
        self.add_item(feedback_button)
        self.add_item(partnership_button)
        self.add_item(other_button)
        self.add_item(cancel_button)
    
    async def appeal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
        
        await interaction.response.send_modal(AppealForm(self.cog, self.user))
        self.stop()
    
    async def support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
        
        await interaction.response.send_modal(SupportForm(self.cog, self.user))
        self.stop()
    
    async def report_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
        
        await interaction.response.send_modal(ReportForm(self.cog, self.user))
        self.stop()
    
    async def feedback_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
        
        await interaction.response.send_modal(FeedbackForm(self.cog, self.user))
        self.stop()
    
    async def partnership_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
        
        await interaction.response.send_modal(PartnershipForm(self.cog, self.user))
        self.stop()
    
    async def other_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        data = {"category": "other"}
        success = await self.cog.create_modmail_thread(self.user, "other", data, priority="normal")
        
        if success:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="✅ Modmail Thread Created",
                    description="Your modmail thread has been created! You can now send messages here and they will be forwarded to our staff team.",
                    color=Colors.INFO
                )
            )
        
        self.stop()
    
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
        
        await interaction.response.send_message(
            embed=ModEmbed.info("Cancelled", "Modmail request cancelled."),
            ephemeral=True
        )
        self.stop()


class BrandedModmailPanel(discord.ui.LayoutView):
    def __init__(self, cog, user: discord.User, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.user = user

        logo_url = (Config.SERVER_LOGO_URL or "").strip() or None
        banner_url = (Config.SERVER_BANNER_URL or "").strip() or None

        select = discord.ui.Select(
            placeholder="Select a modmail category...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Ban/Mute Appeal", value="appeal", description="Appeal a punishment", emoji="📝"),
                discord.SelectOption(label="Support Request", value="support", description="Get help with an issue", emoji="🛠️"),
                discord.SelectOption(label="Report User", value="report", description="Report rule violations", emoji="🚨"),
                discord.SelectOption(label="Feedback/Suggestions", value="feedback", description="Share ideas or feedback", emoji="💡"),
                discord.SelectOption(label="Partnership Request", value="partnership", description="Business/partner inquiries", emoji="🤝"),
                discord.SelectOption(label="General Inquiry", value="other", description="Other questions", emoji="💬"),
                discord.SelectOption(label="Cancel", value="cancel", description="Close this menu", emoji="❌"),
            ],
            custom_id="modmail_panel_select",
        )

        async def _select_cb(interaction: discord.Interaction):
            await self._on_select(interaction, select)

        select.callback = _select_cb

        container = branded_panel_container(
            title="Modmail",
            description="Select a category below to contact staff.",
            banner_url=banner_url,
            logo_url=logo_url,
            accent_color=Config.COLOR_BRAND,
        )
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay("Response time may vary. Please avoid spamming multiple threads."))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(discord.ui.ActionRow(select))
        self.add_item(container)

    async def _on_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user.id:
            ephemeral = bool(interaction.guild_id)
            await interaction.response.send_message("This menu is not for you!", ephemeral=ephemeral)
            return

        choice = (select.values[0] if select.values else "").strip().lower()

        async def _disable() -> None:
            try:
                select.disabled = True
                if interaction.message:
                    await interaction.message.edit(view=self)
            except Exception:
                pass

        if choice == "cancel":
            ephemeral = bool(interaction.guild_id)
            await interaction.response.send_message(
                embed=ModEmbed.info("Cancelled", "Modmail request cancelled."),
                ephemeral=ephemeral,
            )
            await _disable()
            self.stop()
            return

        if choice == "other":
            await interaction.response.defer()
            data = {"category": "other"}
            success = await self.cog.create_modmail_thread(self.user, "other", data, priority="normal")
            if success:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="📩 Modmail Thread Created",
                        description=(
                            "Your modmail thread has been created!\n"
                            "You can now send messages here and they will be forwarded to our staff team."
                        ),
                        color=Colors.INFO,
                    )
                )
            await _disable()
            self.stop()
            return

        modal = None
        if choice == "appeal":
            modal = AppealForm(self.cog, self.user)
        elif choice == "support":
            modal = SupportForm(self.cog, self.user)
        elif choice == "report":
            modal = ReportForm(self.cog, self.user)
        elif choice == "feedback":
            modal = FeedbackForm(self.cog, self.user)
        elif choice == "partnership":
            modal = PartnershipForm(self.cog, self.user)

        if modal is None:
            await interaction.response.send_message(
                embed=ModEmbed.error("Unknown Option", "That option is not available."),
                ephemeral=bool(interaction.guild_id),
            )
            return

        await interaction.response.send_modal(modal)
        await _disable()
        self.stop()


class ThreadControlPanel(discord.ui.LayoutView):
    """Control panel for modmail threads (staff only)"""
    
    def __init__(self, cog, channel_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id

        claim_button = discord.ui.Button(
            label="Claim",
            style=discord.ButtonStyle.primary,
            emoji="👤",
            custom_id="modmail_claim",
        )
        close_button = discord.ui.Button(
            label="Close",
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            custom_id="modmail_close",
        )
        priority_button = discord.ui.Button(
            label="Priority",
            style=discord.ButtonStyle.secondary,
            emoji="🔺",
            custom_id="modmail_priority",
        )
        transfer_button = discord.ui.Button(
            label="Transfer",
            style=discord.ButtonStyle.secondary,
            emoji="↪️",
            custom_id="modmail_transfer",
        )

        async def _claim(interaction: discord.Interaction):
            return await self.claim_button(interaction, claim_button)

        async def _close(interaction: discord.Interaction):
            return await self.close_button(interaction, close_button)

        async def _priority(interaction: discord.Interaction):
            return await self.priority_button(interaction, priority_button)

        async def _transfer(interaction: discord.Interaction):
            return await self.transfer_button(interaction, transfer_button)

        claim_button.callback = _claim
        close_button.callback = _close
        priority_button.callback = _priority
        transfer_button.callback = _transfer

        self.add_item(claim_button)
        self.add_item(close_button)
        self.add_item(priority_button)
        self.add_item(transfer_button)
    
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread_data = self.cog.active_threads.get(self.channel_id)
        
        if not thread_data:
            await interaction.response.send_message("Thread data not found!", ephemeral=True)
            return
        
        if thread_data.get("claimed_by"):
            claimer = interaction.guild.get_member(thread_data["claimed_by"])
            await interaction.response.send_message(
                f"This thread is already claimed by {claimer.mention if claimer else 'someone'}!",
                ephemeral=True
            )
            return
        
        # Claim the thread
        thread_data["claimed_by"] = interaction.user.id
        await self.cog.update_thread_claim(self.channel_id, interaction.user.id)
        
        embed = discord.Embed(
            title="✅ Thread Claimed",
            description=f"{interaction.user.mention} has claimed this thread!",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
        await interaction.response.send_message(embed=embed)
    
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CloseThreadModal(self.cog, self.channel_id))
    
    async def priority_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ChangePriorityModal(self.cog, self.channel_id))
    
    async def transfer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread_data = self.cog.active_threads.get(self.channel_id)
        
        if not thread_data:
            await interaction.response.send_message("Thread data not found!", ephemeral=True)
            return
        
        view = TransferThreadView(self.cog, self.channel_id)
        await interaction.response.send_message(
            "Select the category to transfer this thread to:",
            view=view,
            ephemeral=True
        )


class CloseThreadModal(discord.ui.Modal, title="Close Thread"):
    """Modal for closing a thread with reason"""
    
    reason = discord.ui.TextInput(
        label="Reason for closing",
        placeholder="Why are you closing this thread?",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
        default="No reason provided"
    )
    
    def __init__(self, cog, channel_id: int):
        super().__init__()
        self.cog = cog
        self.channel_id = channel_id
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        reason = str(self.reason) or "No reason provided"
        
        success = await self.cog.close_thread(interaction.channel, interaction.user, reason)
        
        if success:
            await interaction.followup.send(
                embed=ModEmbed.success("Thread Closed", f"Modmail thread closed by {interaction.user.mention}.\n**Reason:** {reason}")
            )


class ChangePriorityModal(discord.ui.Modal, title="Change Priority"):
    """Modal for changing thread priority"""
    
    priority = discord.ui.TextInput(
        label="New Priority",
        placeholder="low, normal, high, or urgent",
        required=True,
        max_length=10
    )
    
    def __init__(self, cog, channel_id: int):
        super().__init__()
        self.cog = cog
        self.channel_id = channel_id
    
    async def on_submit(self, interaction: discord.Interaction):
        priority_input = str(self.priority).lower()
        
        if priority_input not in ["low", "normal", "high", "urgent"]:
            await interaction.response.send_message(
                embed=ModEmbed.error("Invalid Priority", "Priority must be: low, normal, high, or urgent"),
                ephemeral=True
            )
            return
        
        thread_data = self.cog.active_threads.get(self.channel_id)
        if thread_data:
            thread_data["priority"] = priority_input
            await self.cog.update_thread_priority(self.channel_id, priority_input)
            
            embed = discord.Embed(
                title=f"{PRIORITY_EMOJIS[priority_input]} Priority Updated",
                description=f"Thread priority changed to **{priority_input.upper()}**",
                color=PRIORITY_COLORS[priority_input],
                timestamp=datetime.now(timezone.utc)
            )
            await interaction.response.send_message(embed=embed)


class TransferThreadView(discord.ui.LayoutView):
    """View for transferring thread to different category"""
    
    def __init__(self, cog, channel_id: int):
        super().__init__(timeout=60)
        self.cog = cog
        self.channel_id = channel_id

        select = discord.ui.Select(
            placeholder="Select new category...",
            options=[
                discord.SelectOption(label="Appeal", value="appeal", emoji="⚖️"),
                discord.SelectOption(label="Support", value="support", emoji="🎫"),
                discord.SelectOption(label="Report", value="report", emoji="🚨"),
                discord.SelectOption(label="Feedback", value="feedback", emoji="💬"),
                discord.SelectOption(label="Partnership", value="partnership", emoji="🤝"),
                discord.SelectOption(label="Other", value="other", emoji="📩"),
            ],
        )

        async def _select(interaction: discord.Interaction):
            return await self.select_category(interaction, select)

        select.callback = _select
        self.add_item(select)
    
    async def select_category(self, interaction: discord.Interaction, select: discord.ui.Select):
        new_category = select.values[0]
        thread_data = self.cog.active_threads.get(self.channel_id)
        
        if thread_data:
            old_category = thread_data["category"]
            thread_data["category"] = new_category
            await self.cog.update_thread_category(self.channel_id, new_category)
            
            embed = discord.Embed(
                title="✅ Thread Transferred",
                description=f"Thread transferred from **{old_category}** to **{new_category}**",
                color=Colors.SUCCESS
            )
            await interaction.response.send_message(embed=embed)
            
            # Update channel name
            try:
                emoji = CATEGORY_EMOJIS.get(new_category, "📩")
                user_id = thread_data["user_id"]
                await interaction.channel.edit(name=f"{emoji}┃{new_category}-{user_id}")
            except Exception as e:
                logger.error(f"Failed to update channel name: {e}")
        
        self.stop()


class RatingView(discord.ui.LayoutView):
    """Rating system for closed threads"""
    
    def __init__(self, cog, user_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.user_id = user_id

        ratings: list[tuple[int, discord.ui.Button]] = [
            (1, discord.ui.Button(label="⭐", style=discord.ButtonStyle.secondary, custom_id="rate_1")),
            (2, discord.ui.Button(label="⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rate_2")),
            (3, discord.ui.Button(label="⭐⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rate_3")),
            (4, discord.ui.Button(label="⭐⭐⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rate_4")),
            (5, discord.ui.Button(label="⭐⭐⭐⭐⭐", style=discord.ButtonStyle.primary, custom_id="rate_5")),
        ]

        for rating, button in ratings:
            async def _cb(interaction: discord.Interaction, r=rating):
                return await self.handle_rating(interaction, r)

            button.callback = _cb
            self.add_item(button)
    
    async def rate_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 1)
    
    async def rate_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 2)
    
    async def rate_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 3)
    
    async def rate_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 4)
    
    async def rate_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 5)
    
    async def handle_rating(self, interaction: discord.Interaction, rating: int):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This rating is not for you!", ephemeral=True)
            return
        
        await self.cog.store_rating(self.user_id, rating)
        
        embed = discord.Embed(
            title="✅ Thank You for Your Feedback!",
            description=f"You rated your experience: {'⭐' * rating}\n\nYour feedback helps us improve our support!",
            color=Colors.SUCCESS
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.message.edit(view=None)
        self.stop()


# ==================== MAIN COG ====================
class Modmail(commands.Cog):
    """Advanced Modmail System with Full Database Integration"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_threads: Dict[int, Dict] = {}  # channel_id -> thread_data
        self.user_threads: Dict[int, int] = {}  # user_id -> channel_id
        self._threads_loaded = False
        
        # Statistics (loaded from DB)
        self.stats = {
            "total_threads": 0,
            "threads_closed": 0,
            "total_messages": 0,
            "ratings_total": 0,
            "ratings_sum": 0
        }
    
    async def cog_load(self):
        """Initialize modmail system"""
        logger.info("📬 Loading modmail system...")
        
        # Start background task (has its own before_loop that waits)
        self.check_inactive_threads.start()
        
        logger.info("✅ Modmail cog loaded - threads will restore when bot is ready")
    
    async def cog_unload(self):
        """Cleanup on cog unload"""
        self.check_inactive_threads.cancel()
        logger.info("✅ Modmail system unloaded")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Load threads from database when bot is fully ready"""
        if self._threads_loaded:
            return  # only run once
        
        self._threads_loaded = True
        logger.info("📬 Restoring modmail threads from database...")
        
        guild = await self.get_modmail_guild()
        if not guild:
            logger.warning("⚠️ Modmail guild not configured - system will activate when bot receives DMs")
            return

        # Ensure schema exists before loading threads (avoids first-boot races).
        try:
            await self.bot.db.init_guild(guild.id)
        except Exception as e:
            logger.warning(f"⚠️ Modmail DB init failed (will retry on demand): {e}")
        
        # Load active threads from database
        try:
            async with self.bot.db.get_connection() as db:
                cursor = await db.execute(
                    """
                    SELECT channel_id, user_id, category, priority, opened_at,
                           claimed_by, message_count, id
                    FROM modmail_threads
                    WHERE guild_id = ? AND status = 'open'
                    """,
                    (guild.id,)
                )
                rows = await cursor.fetchall()
                
                for row in rows:
                    channel_id, user_id, category, priority, opened_at, claimed_by, msg_count, thread_id = row
                    
                    # Check if channel still exists
                    channel = guild.get_channel(channel_id)
                    if not channel:
                        # Channel was deleted, close thread in DB
                        await self.bot.db.close_modmail_thread(guild.id, user_id)
                        logger.warning(f"⚠️ Channel {channel_id} not found, closed thread in DB")
                        continue
                    
                    # Restore thread data to memory
                    self.active_threads[channel_id] = {
                        "user_id": user_id,
                        "category": category,
                        "priority": priority,
                        "opened_at": opened_at,
                        "claimed_by": claimed_by,
                        "message_count": msg_count,
                        "thread_id": thread_id,
                        "last_message_at": opened_at,
                        "reminder_sent": False
                    }
                    self.user_threads[user_id] = channel_id
                    self.stats["total_threads"] += 1
                    logger.info(f"✅ Restored thread: {channel.name} (User: {user_id})")
            
            logger.info(f"✅ Loaded {len(self.active_threads)} active modmail threads from database")
        except Exception as e:
            logger.error(f"❌ Failed to load threads from database: {e}", exc_info=True)
    
    # ==================== HELPER METHODS ====================
    async def get_modmail_guild(self) -> Optional[discord.Guild]:
        """Get the modmail guild from config or use first guild"""
        if hasattr(Config, 'MODMAIL_GUILD_ID') and Config.MODMAIL_GUILD_ID:
            guild = self.bot.get_guild(Config.MODMAIL_GUILD_ID)
            if guild:
                return guild
        
        # Fallback: use the first guild
        return self.bot.guilds[0] if self.bot.guilds else None
    
    async def get_modmail_category(self, guild: discord.Guild) -> Optional[discord.CategoryChannel]:
        """Get or create modmail category"""
        category_id = getattr(Config, 'MODMAIL_CATEGORY_ID', None)
        if category_id:
            category = guild.get_channel(category_id)
            if category:
                return category
        
        # Create category if not found
        try:
            category = await guild.create_category("📬 Modmail")
            logger.info(f"Created modmail category: {category.id}")
            return category
        except Exception as e:
            logger.error(f"Failed to create modmail category: {e}")
            return None
    
    async def get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Get modmail log channel"""
        log_channel_id = getattr(Config, 'MODMAIL_LOG_CHANNEL', None)
        if log_channel_id:
            return guild.get_channel(log_channel_id)
        return None
    
    async def get_staff_role(self, guild: discord.Guild) -> Optional[discord.Role]:
        """Get staff role for modmail"""
        staff_role_id = getattr(Config, 'MODMAIL_STAFF_ROLE', None)
        if staff_role_id:
            return guild.get_role(staff_role_id)
        return None
    
    # ==================== DATABASE UPDATE METHODS ====================
    async def update_thread_claim(self, channel_id: int, staff_id: int) -> None:
        """Update thread claimed_by in database"""
        try:
            async with self.bot.db.get_connection() as db:
                await db.execute(
                    "UPDATE modmail_threads SET claimed_by = ? WHERE channel_id = ?",
                    (staff_id, channel_id)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update thread claim: {e}")
    
    async def update_thread_priority(self, channel_id: int, priority: str) -> None:
        """Update thread priority in database"""
        try:
            async with self.bot.db.get_connection() as db:
                await db.execute(
                    "UPDATE modmail_threads SET priority = ? WHERE channel_id = ?",
                    (priority, channel_id)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update thread priority: {e}")
    
    async def update_thread_category(self, channel_id: int, category: str) -> None:
        """Update thread category in database"""
        try:
            async with self.bot.db.get_connection() as db:
                await db.execute(
                    "UPDATE modmail_threads SET category = ? WHERE channel_id = ?",
                    (category, channel_id)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update thread category: {e}")
    
    # ==================== CORE MODMAIL METHODS ====================
    async def create_modmail_thread(
        self,
        user: discord.User,
        category: str,
        data: Dict,
        priority: str = "normal"
    ) -> bool:
        """Create a new modmail thread"""
        guild = await self.get_modmail_guild()
        if not guild:
            logger.error("Modmail guild not found")
            return False
        
        # Check if user is blocked
        try:
            if await self.bot.db.is_modmail_blocked(guild.id, user.id):
                try:
                    await user.send(
                        embed=ModEmbed.error(
                            "Access Denied",
                            "You are blocked from using the modmail system."
                        )
                    )
                except discord.Forbidden:
                    pass
                return False
        except Exception as e:
            logger.error(f"Error checking if user is blocked: {e}")
            # Continue anyway if DB check fails
        
        # Check if user already has an active thread
        if user.id in self.user_threads:
            try:
                await user.send(
                    embed=ModEmbed.info(
                        "Active Thread Exists",
                        "You already have an active modmail thread. Your messages here will be forwarded to staff."
                    )
                )
            except discord.Forbidden:
                pass
            return False
        
        try:
            modmail_category = await self.get_modmail_category(guild)
            if not modmail_category:
                logger.error("Could not get or create modmail category")
                return False
            
            staff_role = await self.get_staff_role(guild)
            
            # Create channel with proper permissions
            emoji = CATEGORY_EMOJIS.get(category, "📩")
            channel_name = f"{emoji}┃{category}-{user.id}"
            
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    read_message_history=True,
                    manage_messages=True
                )
            }
            
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    read_message_history=True
                )
            
            channel = await guild.create_text_channel(
                name=channel_name,
                category=modmail_category,
                overwrites=overwrites,
                topic=f"Modmail: {user} ({user.id}) | {category} | Priority: {priority}"
            )
            
            # Store in database using the proper method
            thread_id = await self.bot.db.upsert_modmail_thread(
                guild.id,
                user.id,
                channel.id,
                category,
                priority
            )
            
            # Store in memory
            now = datetime.now(timezone.utc).isoformat()
            self.active_threads[channel.id] = {
                "user_id": user.id,
                "category": category,
                "priority": priority,
                "opened_at": now,
                "last_message_at": now,
                "claimed_by": None,
                "message_count": 0,
                "thread_id": thread_id,
                "reminder_sent": False
            }
            self.user_threads[user.id] = channel.id
            self.stats["total_threads"] += 1
            
            # Send thread info to staff channel
            info_embed = discord.Embed(
                title=f"{emoji} New Modmail: {category.capitalize()}",
                description=f"**User:** {user.mention} (`{user.id}`)\n**Priority:** {PRIORITY_EMOJIS[priority]} {priority.capitalize()}",
                color=PRIORITY_COLORS[priority],
                timestamp=datetime.now(timezone.utc)
            )
            info_embed.set_thumbnail(url=user.display_avatar.url)
            info_embed.set_footer(text=f"Thread ID: {thread_id} | User ID: {user.id}")
            
            # Add form data if provided
            if data and len(data) > 1:  # More than just category
                form_data = ""
                for key, value in data.items():
                    if key != "category" and value:
                        field_name = key.replace('_', ' ').title()
                        # Truncate long values
                        display_value = str(value)[:500]
                        if len(str(value)) > 500:
                            display_value += "..."
                        form_data += f"**{field_name}:** {display_value}\n\n"
                
                if form_data:
                    # Split into multiple fields if too long
                    if len(form_data) <= 1024:
                        info_embed.add_field(name="📋 Form Data", value=form_data, inline=False)
                    else:
                        # Split into chunks
                        chunks = [form_data[i:i+1020] for i in range(0, len(form_data), 1020)]
                        for i, chunk in enumerate(chunks[:3]):  # Max 3 fields
                            info_embed.add_field(name=f"📋 Form Data (Part {i+1})", value=chunk, inline=False)
            
            # Send control panel
            view = ThreadControlPanel(self, channel.id)
            await channel.send(embed=info_embed, view=view)
            
            # Log to log channel
            log_channel = await self.get_log_channel(guild)
            if log_channel:
                try:
                    log_embed = discord.Embed(
                        title="📬 New Modmail Thread",
                        description=(
                            f"**User:** {user.mention} (`{user.id}`)\n"
                            f"**Category:** {category.capitalize()}\n"
                            f"**Channel:** {channel.mention}\n"
                            f"**Priority:** {PRIORITY_EMOJIS[priority]} {priority.capitalize()}"
                        ),
                        color=PRIORITY_COLORS[priority],
                        timestamp=datetime.now(timezone.utc)
                    )
                    await send_log_embed(log_channel, log_embed)
                except Exception as e:
                    logger.error(f"Failed to send to log channel: {e}")
            
            # Send confirmation to user
            try:
                confirm_embed = discord.Embed(
                    title="✅ Modmail Thread Created",
                    description=(
                        f"Your **{category.capitalize()}** request has been received!\n\n"
                        "**What you can do now:**\n"
                        "• Send messages here - they'll be forwarded to staff\n"
                        "• Attach files or images if needed\n"
                        "• Wait for a response from our team\n\n"
                        f"**Priority:** {PRIORITY_EMOJIS[priority]} {priority.capitalize()}\n\n"
                        "Please be patient. Staff will respond as soon as possible."
                    ),
                    color=PRIORITY_COLORS[priority],
                    timestamp=datetime.now(timezone.utc)
                )
                confirm_embed.set_footer(text=f"Thread ID: {thread_id}")
                await user.send(embed=confirm_embed)
            except discord.Forbidden:
                logger.warning(f"Cannot send DM to user {user.id}")
            
            logger.info(f"✅ Created modmail thread for {user} ({user.id}) - Channel: {channel.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create modmail thread: {e}", exc_info=True)
            return False
    
    async def forward_user_message(self, user: discord.User, message: discord.Message) -> None:
        """Forward user message to staff channel"""
        if user.id not in self.user_threads:
            return
        
        channel_id = self.user_threads[user.id]
        guild = await self.get_modmail_guild()
        if not guild:
            return
        
        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            logger.warning(f"Channel {channel_id} not found for user {user.id}")
            return
        
        thread_data = self.active_threads.get(channel_id)
        if not thread_data:
            return
        
        # Update thread data
        now = datetime.now(timezone.utc).isoformat()
        thread_data["last_message_at"] = now
        thread_data["message_count"] += 1
        thread_data["reminder_sent"] = False
        
        # Store message in database
        try:
            content_to_store = message.content or "[Attachment]"
            if message.attachments:
                content_to_store += f" [+{len(message.attachments)} attachment(s)]"
            
            await self.bot.db.add_modmail_message(
                thread_data["thread_id"],
                user.id,
                content_to_store,
                is_staff=False
            )
        except Exception as e:
            logger.error(f"Failed to store message in DB: {e}")
        
        # Build message content
        content = message.content or "*[No text content]*"
        
        # Handle attachments
        files = []
        attachment_urls = []
        if message.attachments:
            for att in message.attachments:
                attachment_urls.append(f"[{att.filename}]({att.url})")
                
                # Only download files under 8MB
                if att.size <= 8388608:
                    try:
                        file_data = await att.to_file()
                        files.append(file_data)
                    except Exception as e:
                        logger.error(f"Failed to download attachment: {e}")
        
        if attachment_urls:
            content += f"\n\n**Attachments:**\n" + "\n".join(attachment_urls)
        
        # Create embed
        embed = discord.Embed(
            description=content[:4000],  # Discord limit
            color=0x5865F2,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id} | Messages: {thread_data['message_count']}")
        
        try:
            await channel.send(embed=embed, files=files)
            self.stats["total_messages"] += 1
        except Exception as e:
            logger.error(f"Failed to forward message to channel: {e}")
        
        # React to user's message with checkmark
        try:
            await message.add_reaction(CHECK_EMOJI)
        except Exception as e:
            logger.debug(f"Failed to add reaction: {e}")
    
    async def forward_staff_reply(
        self,
        staff: discord.Member,
        user: discord.User,
        content: str,
        channel: discord.TextChannel,
        attachments: List[discord.Attachment] = None
    ) -> bool:
        """Forward staff reply to user"""
        thread_data = self.active_threads.get(channel.id)
        if not thread_data:
            return False
        
        # Update thread data
        thread_data["last_message_at"] = datetime.now(timezone.utc).isoformat()
        thread_data["reminder_sent"] = False
        
        # Store in database
        try:
            content_to_store = content
            if attachments:
                content_to_store += f" [+{len(attachments)} attachment(s)]"
            
            await self.bot.db.add_modmail_message(
                thread_data["thread_id"],
                staff.id,
                content_to_store,
                is_staff=True
            )
        except Exception as e:
            logger.error(f"Failed to store staff message: {e}")
        
        try:
            # Build message embed
            embed = discord.Embed(
                description=content[:4000],
                color=0x5865F2,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=f"Staff: {staff.display_name}", icon_url=staff.display_avatar.url)
            
            # Handle attachments
            files = []
            if attachments:
                for att in attachments:
                    if att.size <= 8388608:  # 8MB limit
                        try:
                            files.append(await att.to_file())
                        except Exception as e:
                            logger.error(f"Failed to download attachment: {e}")
            
            await user.send(embed=embed, files=files)
            self.stats["total_messages"] += 1
            return True
            
        except discord.Forbidden:
            error_embed = ModEmbed.error(
                "Cannot Send Message",
                f"Unable to DM {user.mention}. They may have DMs disabled or blocked the bot."
            )
            await channel.send(embed=error_embed)
            return False
        except Exception as e:
            logger.error(f"Failed to send staff reply: {e}")
            return False
    
    async def close_thread(
        self,
        channel: discord.TextChannel,
        closer: discord.Member,
        reason: str = "No reason provided",
        send_rating: bool = True
    ) -> bool:
        """Close a modmail thread"""
        thread_data = self.active_threads.get(channel.id)
        if not thread_data:
            logger.warning(f"Attempted to close non-existent thread: {channel.id}")
            return False
        
        user_id = thread_data["user_id"]
        user = self.bot.get_user(user_id)
        guild = channel.guild
        
        try:
            # Generate transcript
            transcript = await self.generate_transcript(thread_data, guild, closer, reason)
            
            # Log to log channel
            log_channel = await self.get_log_channel(guild)
            if log_channel and transcript:
                try:
                    duration = self.calculate_duration(thread_data['opened_at'])
                    log_embed = discord.Embed(
                        title="🔒 Modmail Thread Closed",
                        description=(
                            f"**User:** <@{user_id}> (`{user_id}`)\n"
                            f"**Category:** {thread_data['category'].capitalize()}\n"
                            f"**Priority:** {PRIORITY_EMOJIS[thread_data['priority']]} {thread_data['priority'].capitalize()}\n"
                            f"**Closed by:** {closer.mention}\n"
                            f"**Reason:** {reason}\n"
                            f"**Messages:** {thread_data['message_count']}\n"
                            f"**Duration:** {duration}"
                        ),
                        color=Colors.ERROR,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await send_log_embed(log_channel, log_embed, file=transcript)
                except Exception as e:
                    logger.error(f"Failed to send to log channel: {e}")
            
            # Notify user
            if user:
                try:
                    close_embed = discord.Embed(
                        title="🔒 Modmail Thread Closed",
                        description=(
                            f"Your modmail thread has been closed.\n\n"
                            f"**Reason:** {reason}\n"
                            f"**Closed by:** {closer.display_name}\n\n"
                            "If you need further assistance, you can create a new modmail thread by sending `.modmail` here."
                        ),
                        color=Colors.ERROR,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await user.send(embed=close_embed)
                    
                    # Send rating request
                    if send_rating:
                        rating_embed = discord.Embed(
                            title="⭐ Rate Your Experience",
                            description="We'd love to hear your feedback! Please rate your experience with our support team.",
                            color=Colors.INFO
                        )
                        rating_view = RatingView(self, user_id)
                        await user.send(embed=rating_embed, view=rating_view)
                        
                except discord.Forbidden:
                    logger.warning(f"Cannot send closure message to user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to notify user of closure: {e}")
            
            # Close in database
            await self.bot.db.close_modmail_thread(guild.id, user_id)
            
            # Cleanup memory
            self.active_threads.pop(channel.id, None)
            self.user_threads.pop(user_id, None)
            self.stats["threads_closed"] += 1
            
            # Delete channel after short delay
            await asyncio.sleep(5)
            try:
                await channel.delete(reason=f"Modmail closed by {closer}")
                logger.info(f"✅ Closed modmail thread for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to delete channel: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing thread: {e}", exc_info=True)
            return False
    
    async def generate_transcript(
        self,
        thread_data: Dict,
        guild: discord.Guild,
        closer: discord.Member,
        reason: str
    ) -> Optional[discord.File]:
        """Generate transcript file from database"""
        try:
            user_id = thread_data["user_id"]
            user = self.bot.get_user(user_id)
            
            lines = [
                "=" * 80,
                "MODMAIL TRANSCRIPT",
                "=" * 80,
                f"User: {user} ({user_id})" if user else f"User ID: {user_id}",
                f"Category: {thread_data['category'].capitalize()}",
                f"Priority: {thread_data['priority'].capitalize()}",
                f"Opened: {thread_data['opened_at']}",
                f"Closed: {datetime.now(timezone.utc).isoformat()}",
                f"Closed by: {closer} ({closer.id})",
                f"Reason: {reason}",
                f"Total Messages: {thread_data['message_count']}",
                f"Duration: {self.calculate_duration(thread_data['opened_at'])}",
                "=" * 80,
                ""
            ]
            
            # Get messages from database
            messages = await self.bot.db.get_modmail_messages(thread_data["thread_id"])
            if messages:
                lines.append("MESSAGE HISTORY")
                lines.append("-" * 80)
                lines.append("")
                
                for msg in messages:
                    timestamp = msg["timestamp"]
                    author_id = msg["author_id"]
                    content = msg["content"] or "*No content*"
                    is_staff = msg["is_staff"]
                    
                    # Get author info
                    author = guild.get_member(author_id) or self.bot.get_user(author_id)
                    author_name = str(author) if author else f"Unknown User ({author_id})"
                    prefix = "[STAFF]" if is_staff else "[USER]"
                    
                    lines.append(f"[{timestamp}] {prefix} {author_name}:")
                    lines.append(f"  {content}")
                    lines.append("")
            else:
                lines.append("No messages in this thread.")
                lines.append("")
            
            lines.append("=" * 80)
            lines.append("END OF TRANSCRIPT")
            lines.append("=" * 80)
            
            # Create file
            transcript_text = "\n".join(lines)
            transcript_bytes = io.BytesIO(transcript_text.encode("utf-8"))
            filename = f"modmail-{user_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
            
            return discord.File(transcript_bytes, filename=filename)
            
        except Exception as e:
            logger.error(f"Failed to generate transcript: {e}", exc_info=True)
            return None
    
    def calculate_duration(self, opened_at: str) -> str:
        """Calculate thread duration as human-readable string"""
        try:
            opened = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
            if opened.tzinfo is None:
                opened = opened.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            delta = now - opened
            
            days = delta.days
            hours = int(delta.seconds // 3600)
            minutes = int((delta.seconds % 3600) // 60)
            
            parts = []
            if days > 0:
                parts.append(f"{days}d")
            if hours > 0:
                parts.append(f"{hours}h")
            if minutes > 0 or not parts:
                parts.append(f"{minutes}m")
            
            return " ".join(parts)
        except Exception as e:
            logger.error(f"Error calculating duration: {e}")
            return "Unknown"
    
    async def store_rating(self, user_id: int, rating: int) -> None:
        """Store user rating in statistics"""
        self.stats["ratings_total"] += 1
        self.stats["ratings_sum"] += rating
        avg = self.stats['ratings_sum'] / self.stats['ratings_total']
        logger.info(f"User {user_id} rated their experience: {rating}/5 (Avg: {avg:.2f})")
    
    # ==================== EVENT LISTENERS ====================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle DM messages and staff replies"""
        # Ignore bots
        if message.author.bot:
            return
        
        # Handle DMs (user messages)
        if not message.guild:
            user = message.author
            
            # Check for .modmail command
            if message.content.lower().strip() == ".modmail":
                # Check if user already has active thread
                if user.id in self.user_threads:
                    try:
                        await user.send(
                            embed=ModEmbed.info(
                                "Active Thread Exists",
                                "You already have an active modmail thread. Your messages here will be forwarded to staff."
                            )
                        )
                    except discord.Forbidden:
                        pass
                    return
                
                # Send category selection menu
                view = BrandedModmailPanel(self, user)
                embed = discord.Embed(
                    title="📬 Modmail System",
                    description=(
                        "Welcome to the modmail system! Please select a category below:\n\n"
                        "⚖️ **Ban/Mute Appeal** - Appeal a punishment\n"
                        "🎫 **Support Request** - Get help with an issue\n"
                        "🚨 **Report User** - Report rule violations\n"
                        "💬 **Feedback/Suggestions** - Share your thoughts\n"
                        "🤝 **Partnership Request** - Partnership proposals\n"
                        "📩 **General Inquiry** - Other questions"
                    ),
                    color=Colors.INFO
                )
                
                try:
                    await user.send(view=view)
                except discord.Forbidden:
                    logger.warning(f"Cannot send DM to user {user.id}")
                
                return
            
            # Forward user message to staff if they have active thread
            if user.id in self.user_threads:
                await self.forward_user_message(user, message)
            
            return
        
        # Handle staff replies in modmail channels
        else:
            # Check if this is a modmail thread
            if message.channel.id not in self.active_threads:
                return
            
            # Ignore bot messages
            if message.author.bot:
                return
            
            # Staff internal chat - ignore messages starting with comma
            if message.content.startswith(","):
                return
            
            # Ignore commands and special prefixes
            if message.content.startswith((".", "!", "/", "-", "?", ">")):
                return
            
            thread_data = self.active_threads.get(message.channel.id)
            if not thread_data:
                return
            
            user_id = thread_data["user_id"]
            user = self.bot.get_user(user_id)
            
            if not user:
                await message.channel.send(
                    embed=ModEmbed.error("User Not Found", "Could not find the user to send the message to.")
                )
                return
            
            # Forward to user
            success = await self.forward_staff_reply(
                message.author,
                user,
                message.content,
                message.channel,
                message.attachments
            )
            
            if success:
                try:
                    await message.add_reaction(CHECK_EMOJI)
                except Exception:
                    pass
    
    # ==================== SLASH COMMANDS ====================
    modmail_group = app_commands.Group(name="modmail", description="Modmail system management")
    
    @modmail_group.command(name="close", description="Close a modmail thread")
    @app_commands.describe(reason="Reason for closing the thread")
    async def modmail_close(self, interaction: discord.Interaction, reason: Optional[str] = "No reason provided"):
        """Close a modmail thread"""
        if interaction.channel.id not in self.active_threads:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not a Modmail Channel", "This command can only be used in modmail threads."),
                ephemeral=True
            )
        
        await interaction.response.defer()
        success = await self.close_thread(interaction.channel, interaction.user, reason)
        
        if success:
            await interaction.followup.send(
                embed=ModEmbed.success(
                    "Thread Closed",
                    f"Modmail thread closed by {interaction.user.mention}.\n**Reason:** {reason}"
                )
            )
        else:
            await interaction.followup.send(
                embed=ModEmbed.error("Error", "Failed to close thread."),
                ephemeral=True
            )
    
    @modmail_group.command(name="reply", description="Reply to a modmail thread")
    @app_commands.describe(message="Message to send to the user")
    async def modmail_reply(self, interaction: discord.Interaction, message: str):
        """Reply to user in modmail thread"""
        if interaction.channel.id not in self.active_threads:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not a Modmail Channel", "This command can only be used in modmail threads."),
                ephemeral=True
            )
        
        thread_data = self.active_threads.get(interaction.channel.id)
        if not thread_data:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Thread Not Found", "Thread data not found."),
                ephemeral=True
            )
        
        user_id = thread_data["user_id"]
        user = self.bot.get_user(user_id)
        
        if not user:
            return await interaction.response.send_message(
                embed=ModEmbed.error("User Not Found", "Could not find the user."),
                ephemeral=True
            )
        
        await interaction.response.defer(ephemeral=True)
        
        success = await self.forward_staff_reply(
            interaction.user,
            user,
            message,
            interaction.channel,
            None
        )
        
        if success:
            await interaction.followup.send(
                embed=ModEmbed.success("Sent", "Message delivered to user!"),
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                embed=ModEmbed.error("Failed", "Could not send message to user."),
                ephemeral=True
            )
    
    @modmail_group.command(name="note", description="Add a staff note to the thread")
    @app_commands.describe(note="Staff note to add")
    async def modmail_note(self, interaction: discord.Interaction, note: str):
        """Add internal staff note"""
        if interaction.channel.id not in self.active_threads:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not a Modmail Channel", "This command can only be used in modmail threads."),
                ephemeral=True
            )
        
        thread_data = self.active_threads.get(interaction.channel.id)
        if not thread_data:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Thread Not Found", "Thread data not found."),
                ephemeral=True
            )
        
        # Store note in database with special marker
        try:
            await self.bot.db.add_modmail_message(
                thread_data["thread_id"],
                interaction.user.id,
                f"[STAFF NOTE] {note}",
                is_staff=True
            )
        except Exception as e:
            logger.error(f"Failed to add staff note: {e}")
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", "Failed to add note to database."),
                ephemeral=True
            )
        
        embed = discord.Embed(
            title="📝 Staff Note Added",
            description=f"**By:** {interaction.user.mention}\n**Note:** {note}",
            color=Colors.INFO,
            timestamp=datetime.now(timezone.utc)
        )
        await interaction.response.send_message(embed=embed)
    
    @modmail_group.command(name="block", description="Block a user from using modmail")
    @app_commands.describe(user="User to block", reason="Reason for block")
    async def modmail_block(self, interaction: discord.Interaction, user: discord.User, reason: str = "No reason provided"):
        """Block user from modmail"""
        guild = await self.get_modmail_guild()
        if not guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", "Modmail guild not found."),
                ephemeral=True
            )
        
        try:
            if await self.bot.db.is_modmail_blocked(guild.id, user.id):
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Already Blocked", f"{user.mention} is already blocked."),
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error checking block status: {e}")
        
        try:
            await self.bot.db.add_modmail_block(guild.id, user.id, reason, interaction.user.id)
        except Exception as e:
            logger.error(f"Failed to block user: {e}")
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", "Failed to block user."),
                ephemeral=True
            )
        
        # Notify user
        try:
            embed = discord.Embed(
                title="🚫 Modmail Access Revoked",
                description=(
                    "You have been blocked from using the modmail system.\n\n"
                    f"**Reason:** {reason}\n\n"
                    "If you believe this is a mistake, please contact a server administrator through other means."
                ),
                color=Colors.ERROR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"Blocked by {interaction.user}")
            await user.send(embed=embed)
        except discord.Forbidden:
            pass
        
        await interaction.response.send_message(
            embed=ModEmbed.success(
                "User Blocked",
                f"{user.mention} has been blocked from using modmail.\n**Reason:** {reason}"
            )
        )
    
    @modmail_group.command(name="unblock", description="Remove block from a user")
    @app_commands.describe(user="User to unblock")
    async def modmail_unblock(self, interaction: discord.Interaction, user: discord.User):
        """Unblock user from modmail"""
        guild = await self.get_modmail_guild()
        if not guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", "Modmail guild not found."),
                ephemeral=True
            )
        
        try:
            if not await self.bot.db.is_modmail_blocked(guild.id, user.id):
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Not Blocked", f"{user.mention} is not blocked."),
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error checking block status: {e}")
        
        try:
            await self.bot.db.remove_modmail_block(guild.id, user.id)
        except Exception as e:
            logger.error(f"Failed to unblock user: {e}")
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", "Failed to unblock user."),
                ephemeral=True
            )
        
        # Notify user
        try:
            embed = discord.Embed(
                title="✅ Modmail Access Restored",
                description=(
                    "Your modmail access has been restored!\n\n"
                    "You can now use the modmail system again by sending `.modmail` in DMs."
                ),
                color=Colors.SUCCESS,
                timestamp=datetime.now(timezone.utc)
            )
            await user.send(embed=embed)
        except discord.Forbidden:
            pass
        
        await interaction.response.send_message(
            embed=ModEmbed.success("User Unblocked", f"{user.mention} can now use modmail again.")
        )
    
    @modmail_group.command(name="stats", description="View modmail statistics")
    async def modmail_stats(self, interaction: discord.Interaction):
        """Show modmail stats"""
        guild = await self.get_modmail_guild()
        blocked_count = 0
        
        if guild:
            try:
                blocks = await self.bot.db.get_modmail_blocks(guild.id)
                blocked_count = len(blocks)
            except Exception as e:
                logger.error(f"Error getting blocks: {e}")
        
        embed = discord.Embed(
            title="📊 Modmail Statistics",
            color=Colors.INFO,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Active Threads", value=f"``````", inline=True)
        embed.add_field(name="Total Opened", value=f"``````", inline=True)
        embed.add_field(name="Total Closed", value=f"``````", inline=True)
        embed.add_field(name="Total Messages", value=f"``````", inline=True)
        embed.add_field(name="Blocked Users", value=f"``````", inline=True)
        
        avg_rating = "N/A"
        if self.stats["ratings_total"] > 0:
            avg = self.stats['ratings_sum'] / self.stats['ratings_total']
            avg_rating = f"{avg:.2f}/5 ⭐ ({self.stats['ratings_total']} ratings)"
        
        embed.add_field(name="Average Rating", value=f"``````", inline=True)
        
        # Category breakdown
        if self.active_threads:
            categories = {}
            for thread in self.active_threads.values():
                cat = thread.get('category', 'other')
                categories[cat] = categories.get(cat, 0) + 1
            
            category_text = "\n".join([f"{CATEGORY_EMOJIS.get(cat, '📩')} {cat.capitalize()}: {count}"
                                      for cat, count in sorted(categories.items())])
            embed.add_field(name="Active by Category", value=category_text or "None", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @modmail_group.command(name="info", description="Get information about current thread")
    async def modmail_info(self, interaction: discord.Interaction):
        """Get thread information"""
        if interaction.channel.id not in self.active_threads:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not a Modmail Channel", "This command can only be used in modmail threads."),
                ephemeral=True
            )
        
        thread_data = self.active_threads.get(interaction.channel.id)
        if not thread_data:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Thread Not Found", "Thread data not found."),
                ephemeral=True
            )
        
        user_id = thread_data["user_id"]
        user = self.bot.get_user(user_id)
        
        embed = discord.Embed(
            title="📋 Thread Information",
            color=PRIORITY_COLORS[thread_data.get('priority', 'normal')],
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="User", value=f"{user.mention if user else f'<@{user_id}>'} (`{user_id}`)", inline=True)
        embed.add_field(name="Category", value=f"{CATEGORY_EMOJIS.get(thread_data['category'], '📩')} {thread_data['category'].capitalize()}", inline=True)
        embed.add_field(name="Priority", value=f"{PRIORITY_EMOJIS[thread_data['priority']]} {thread_data['priority'].capitalize()}", inline=True)
        embed.add_field(name="Messages", value=f"``````", inline=True)
        embed.add_field(name="Duration", value=f"``````", inline=True)
        
        claimed_by = thread_data.get('claimed_by')
        if claimed_by:
            claimer = interaction.guild.get_member(claimed_by)
            embed.add_field(name="Claimed By", value=f"{claimer.mention if claimer else f'<@{claimed_by}>'}", inline=True)
        else:
            embed.add_field(name="Claimed By", value="``````", inline=True)
        
        embed.add_field(name="Opened", value=f"<t:{int(datetime.fromisoformat(thread_data['opened_at'].replace('Z', '+00:00')).timestamp())}:R>", inline=True)
        embed.add_field(name="Last Message", value=f"<t:{int(datetime.fromisoformat(thread_data['last_message_at'].replace('Z', '+00:00')).timestamp())}:R>", inline=True)
        embed.add_field(name="Thread ID", value=f"``````", inline=True)
        
        if user:
            embed.set_thumbnail(url=user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # ==================== BACKGROUND TASKS ====================
    @tasks.loop(minutes=30)
    async def check_inactive_threads(self):
        """Check for inactive threads and send reminders/auto-close"""
        try:
            current_time = datetime.now(timezone.utc)
            
            for channel_id, thread_data in list(self.active_threads.items()):
                try:
                    last_message_str = thread_data["last_message_at"]
                    last_message = datetime.fromisoformat(last_message_str.replace('Z', '+00:00'))
                    if last_message.tzinfo is None:
                        last_message = last_message.replace(tzinfo=timezone.utc)
                    
                    inactive_duration = current_time - last_message
                    
                    guild = await self.get_modmail_guild()
                    if not guild:
                        continue
                    
                    channel = guild.get_channel(channel_id)
                    user_id = thread_data["user_id"]
                    user = self.bot.get_user(user_id)
                    
                    if not channel:
                        # Channel deleted, clean up
                        logger.warning(f"Channel {channel_id} not found, cleaning up")
                        self.active_threads.pop(channel_id, None)
                        self.user_threads.pop(user_id, None)
                        continue
                    
                    if not user:
                        continue
                    
                    # Send reminder after INACTIVE_WARNING_HOURS hours
                    if inactive_duration >= timedelta(hours=INACTIVE_WARNING_HOURS) and not thread_data.get("reminder_sent"):
                        try:
                            # Send reminder to user
                            embed = discord.Embed(
                                title="⚠️ Modmail Thread Inactive",
                                description=(
                                    f"Your modmail thread has been inactive for {INACTIVE_WARNING_HOURS} hours.\n\n"
                                    "If you still need assistance, please send a message. "
                                    f"Otherwise, this thread will be automatically closed in {AUTO_CLOSE_HOURS - INACTIVE_WARNING_HOURS} hours."
                                ),
                                color=Colors.WARNING
                            )
                            await user.send(embed=embed)
                            
                            # Send reminder to channel
                            channel_embed = discord.Embed(
                                title="⚠️ Inactivity Warning",
                                description=f"This thread has been inactive for {INACTIVE_WARNING_HOURS} hours. It will auto-close in {AUTO_CLOSE_HOURS - INACTIVE_WARNING_HOURS} hours if no response.",
                                color=Colors.WARNING
                            )
                            await channel.send(embed=channel_embed)
                            
                            thread_data["reminder_sent"] = True
                            logger.info(f"Sent inactivity reminder for thread {channel_id}")
                        except Exception as e:
                            logger.error(f"Failed to send inactivity reminder: {e}")
                    
                    # Auto-close after AUTO_CLOSE_HOURS hours
                    if inactive_duration >= timedelta(hours=AUTO_CLOSE_HOURS):
                        bot_member = guild.me
                        logger.info(f"Auto-closing inactive thread {channel_id} (inactive for {inactive_duration.total_seconds()/3600:.1f} hours)")
                        
                        await self.close_thread(
                            channel,
                            bot_member,
                            f"Auto-closed due to inactivity ({AUTO_CLOSE_HOURS} hours)",
                            send_rating=False
                        )
                
                except Exception as e:
                    logger.error(f"Error processing thread {channel_id} in inactive check: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error in check_inactive_threads task: {e}", exc_info=True)
    
    @check_inactive_threads.before_loop
    async def before_check_inactive(self):
        """Wait for bot to be ready before starting task"""
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Modmail(bot))
