# views/family_views.py

from __future__ import annotations

import discord
from datetime import datetime, timezone
from typing import Optional

from ..utils.format import money
from ..views.v2_embed import apply_v2_embed_layout, disable_all_interactive


# ============= CONSTANTS =============

FAMILY_COLORS = {
    "proposal": 0xFF69B4,    # Pink
    "married": 0xFFD700,     # Gold
    "divorce": 0xEF4444,     # Red
    "family": 0xFF7F50,      # Coral
}


# ============= MARRIAGE PROPOSAL =============

class MarriageProposal(discord.ui.LayoutView):
    """Marriage proposal view with enhanced UI."""

    def __init__(self, proposer: discord.User, target: discord.User, bot):
        super().__init__(timeout=120)
        self.proposer = proposer
        self.target = target
        self.bot = bot
        self.accepted = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(
                "❌ This proposal isn't for you!",
                ephemeral=True
            )
            return False
        return True

    def create_proposal_embed(self) -> discord.Embed:
        """Create the proposal embed."""
        embed = discord.Embed(
            title="💍 Marriage Proposal",
            description=(
                f"**{self.proposer.mention}** is proposing to **{self.target.mention}**!\n\n"
                f"*Will you marry {self.proposer.display_name}?*"
            ),
            color=FAMILY_COLORS["proposal"]
        )

        embed.add_field(
            name="💰 Marriage Benefits",
            value=(
                "• 💵 Shared family bank\n"
                "• ⭐ +10% XP bonus when working together\n"
                "• 💰 +10% money bonus on activities\n"
                "• 😊 +10 happiness bonus daily\n"
                "• 🏠 Access to family home (coming soon)\n"
                "• 👶 Ability to adopt children (coming soon)"
            ),
            inline=False
        )

        embed.add_field(
            name="📋 Marriage Rules",
            value=(
                "• Both partners must consent\n"
                "• Divorce costs $10,000\n"
                "• Shared assets during marriage\n"
                "• Cannot marry while already married"
            ),
            inline=False
        )

        embed.set_thumbnail(url=self.proposer.display_avatar.url)
        embed.set_footer(text="💝 This is a big decision! Choose wisely.")

        return embed

    @discord.ui.button(label="Accept 💍", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.accepted = True
        self.stop()

        # Perform marriage
        db = self.bot.db
        proposer_id = str(self.proposer.id)
        target_id = str(self.target.id)

        now = datetime.now(timezone.utc).isoformat()

        db.updatestat(proposer_id, "spouse", target_id)
        db.updatestat(proposer_id, "married_at", now)
        db.updatestat(target_id, "spouse", proposer_id)
        db.updatestat(target_id, "married_at", now)

        # Disable buttons
        disable_all_interactive(self)

        # Create celebration embed
        embed = discord.Embed(
            title="💍 Just Married!",
            description=f"🎉 **{self.proposer.display_name}** and **{self.target.display_name}** are now married!\n\nCongratulations on your union! 💝",
            color=FAMILY_COLORS["married"]
        )

        embed.add_field(
            name="💰 Family Benefits Activated",
            value=(
                "✅ Shared family bank created\n"
                "✅ +10% XP bonus active\n"
                "✅ +10% money bonus active\n"
                "✅ +10 happiness bonus daily"
            ),
            inline=False
        )

        embed.add_field(
            name="📝 Next Steps",
            value=(
                "• Use `/family` to view your family\n"
                "• Use `/familybank` to manage shared funds\n"
                "• Work together for bonus rewards!\n"
                "• Enjoy your married life! 💕"
            ),
            inline=False
        )

        embed.set_thumbnail(url="https://i.imgur.com/7VNLWCK.png")  # Wedding rings emoji image
        embed.set_footer(text=f"Married on {datetime.now(timezone.utc).strftime('%B %d, %Y')}")

        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.accepted = False
        self.stop()

        # Disable buttons
        disable_all_interactive(self)

        embed = discord.Embed(
            title="💔 Proposal Declined",
            description=f"**{self.target.display_name}** has declined the marriage proposal.\n\nBetter luck next time, {self.proposer.mention}...",
            color=FAMILY_COLORS["divorce"]
        )

        embed.set_footer(text="Sometimes things just don't work out. 😔")

        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        """Handle timeout."""
        disable_all_interactive(self)


# ============= DIVORCE CONFIRMATION =============

class DivorceConfirmation(discord.ui.LayoutView):
    """Confirm divorce with detailed information."""

    def __init__(self, user: discord.User, spouse_name: str, cost: int, bot):
        super().__init__(timeout=60)
        self.user = user
        self.spouse_name = spouse_name
        self.cost = cost
        self.confirmed = False
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Not your decision!",
                ephemeral=True
            )
            return False
        return True

    def create_divorce_embed(self) -> discord.Embed:
        """Create divorce confirmation embed."""
        embed = discord.Embed(
            title="⚠️ Divorce Confirmation",
            description=f"Are you sure you want to divorce **{self.spouse_name}**?\n\nThis action cannot be undone!",
            color=FAMILY_COLORS["divorce"]
        )

        embed.add_field(
            name="💸 Divorce Costs",
            value=f"**Fee:** {money(self.cost)}\n**Reason:** Legal fees and paperwork",
            inline=False
        )

        embed.add_field(
            name="❌ What You'll Lose",
            value=(
                "• 💵 Shared family bank access\n"
                "• ⭐ +10% XP bonus\n"
                "• 💰 +10% money bonus\n"
                "• 😊 +10 happiness bonus\n"
                "• 🏠 Family home access\n"
                "• 👶 Shared children custody"
            ),
            inline=False
        )

        embed.add_field(
            name="📋 After Divorce",
            value=(
                "• You'll be single again\n"
                "• Can remarry after 24 hours\n"
                "• Family assets will be split\n"
                "• All family bonuses removed"
            ),
            inline=False
        )

        embed.set_footer(text="💔 Think carefully before proceeding...")

        return embed

    @discord.ui.button(label="Confirm Divorce", style=discord.ButtonStyle.danger, emoji="💔")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop()

        # Disable buttons
        disable_all_interactive(self)

        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self.stop()

        # Disable buttons
        disable_all_interactive(self)

        embed = discord.Embed(
            title="✅ Divorce Cancelled",
            description=f"You decided to stay married to **{self.spouse_name}**.\n\nLove conquers all! 💕",
            color=FAMILY_COLORS["married"]
        )

        embed.set_footer(text="Sometimes second thoughts are the best thoughts. 💝")

        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)


# ============= FAMILY OVERVIEW =============

class FamilyView(discord.ui.LayoutView):
    """Family overview and management."""

    def __init__(self, bot, user: discord.User):
        super().__init__(timeout=180)
        self.bot = bot
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    async def create_embed(self) -> discord.Embed:
        """Create family overview embed."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)

        spouse_id = u.get("spouse")
        married_at = u.get("married_at")
        family_bank = int(u.get("family_bank", 0))

        embed = discord.Embed(
            title=f"👨‍👩‍👧‍👦 {self.user.display_name}'s Family",
            color=FAMILY_COLORS["family"]
        )

        if spouse_id:
            # Married
            spouse = await self.bot.fetch_user(int(spouse_id))
            
            # Calculate marriage duration
            if married_at:
                married_date = datetime.fromisoformat(married_at)
                duration = datetime.now(timezone.utc) - married_date
                days = duration.days
                hours = duration.seconds // 3600
                duration_str = f"{days} days, {hours} hours"
            else:
                duration_str = "Unknown"

            embed.add_field(
                name="💑 Marriage Status",
                value=f"**Spouse:** {spouse.mention}\n**Married For:** {duration_str}\n**Status:** Active 💚",
                inline=False
            )

            embed.add_field(
                name="💰 Family Bank",
                value=f"**Balance:** {money(family_bank)}\n**Shared:** Both partners can access",
                inline=True
            )

            embed.add_field(
                name="✨ Active Bonuses",
                value=(
                    "⭐ +10% XP\n"
                    "💰 +10% Money\n"
                    "😊 +10 Happiness"
                ),
                inline=True
            )

            embed.set_thumbnail(url=spouse.display_avatar.url)

        else:
            # Single
            embed.description = "You are currently single. 💔"
            
            embed.add_field(
                name="💍 Want to Get Married?",
                value="Use `/marry @user` to propose to someone!",
                inline=False
            )

            embed.add_field(
                name="💝 Marriage Benefits",
                value=(
                    "• Shared family bank\n"
                    "• +10% XP bonus\n"
                    "• +10% money bonus\n"
                    "• +10 happiness daily"
                ),
                inline=False
            )

        embed.set_footer(text="Use the buttons below to manage your family")

        return embed

    @discord.ui.button(label="Family Bank", style=discord.ButtonStyle.success, emoji="💰")
    async def family_bank_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)

        spouse_id = u.get("spouse")
        
        if not spouse_id:
            return await interaction.response.send_message(
                "❌ You need to be married to access the family bank!",
                ephemeral=True
            )

        family_bank = int(u.get("family_bank", 0))
        balance = int(u.get("balance", 0))

        embed = discord.Embed(
            title="💰 Family Bank",
            description=f"**Family Balance:** {money(family_bank)}\n**Your Wallet:** {money(balance)}",
            color=FAMILY_COLORS["married"]
        )

        embed.add_field(
            name="📝 Commands",
            value=(
                "• `/familydeposit <amount>` - Deposit to family bank\n"
                "• `/familywithdraw <amount>` - Withdraw from family bank"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Divorce", style=discord.ButtonStyle.danger, emoji="💔")
    async def divorce_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)

        spouse_id = u.get("spouse")
        
        if not spouse_id:
            return await interaction.response.send_message(
                "❌ You're not married!",
                ephemeral=True
            )

        spouse = await self.bot.fetch_user(int(spouse_id))
        
        # Show divorce confirmation
        divorce_cost = 10000
        view = DivorceConfirmation(self.user, spouse.display_name, divorce_cost, self.bot)
        embed = view.create_divorce_embed()

        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.create_embed()
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
