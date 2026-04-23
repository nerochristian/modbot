# views/guild_views.py

from __future__ import annotations

import discord
from datetime import datetime, timezone
from typing import Optional, List

from ..utils.format import money
from ..views.v2_embed import apply_v2_embed_layout, disable_all_interactive


# ============= CONSTANTS =============

GUILD_COLORS = {
    "invite": 0x5865F2,      # Discord Blurple
    "success": 0x22C55E,     # Green
    "danger": 0xEF4444,      # Red
    "info": 0x3B82F6,        # Blue
    "warning": 0xFBBF24,     # Yellow
    "guild": 0x00CED1,       # Cyan
}

GUILD_RANK_EMOJIS = {
    "leader": "👑",
    "officer": "⭐",
    "member": "🛡️",
    "recruit": "🔰",
}


# ============= GUILD INVITE =============

class GuildInvite(discord.ui.LayoutView):
    """Guild invite view with detailed information."""

    def __init__(
        self,
        inviter: discord.User,
        target: discord.User,
        guild_data: dict,
        bot
    ):
        super().__init__(timeout=120)
        self.inviter = inviter
        self.target = target
        self.guild_data = guild_data
        self.bot = bot
        self.accepted = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(
                "❌ This invite isn't for you!",
                ephemeral=True
            )
            return False
        return True

    def create_invite_embed(self) -> discord.Embed:
        """Create guild invite embed."""
        guild_name = self.guild_data.get("name", "Unknown Guild")
        guild_level = self.guild_data.get("level", 1)
        member_count = self.guild_data.get("member_count", 0)
        max_members = self.guild_data.get("max_members", 20)
        guild_bank = int(self.guild_data.get("bank", 0))
        description = self.guild_data.get("description", "No description")

        embed = discord.Embed(
            title="🛡️ Guild Invitation",
            description=f"**{self.inviter.mention}** invited you to join **{guild_name}**!",
            color=GUILD_COLORS["invite"]
        )

        # Guild info
        embed.add_field(
            name="📊 Guild Information",
            value=(
                f"**Name:** {guild_name}\n"
                f"**Level:** {guild_level}\n"
                f"**Members:** {member_count}/{max_members}\n"
                f"**Description:** {description}"
            ),
            inline=False
        )

        # Guild bank
        embed.add_field(
            name="💰 Guild Bank",
            value=f"**Balance:** {money(guild_bank)}\n**Shared:** All members contribute",
            inline=True
        )

        # Benefits
        embed.add_field(
            name="✨ Member Benefits",
            value=(
                f"• ⭐ +{5 + guild_level}% XP bonus\n"
                f"• 💰 +{5 + guild_level}% money bonus\n"
                "• 🛡️ Guild protection\n"
                "• 🎁 Guild events & rewards\n"
                "• 💬 Guild chat access"
            ),
            inline=True
        )

        # Responsibilities
        embed.add_field(
            name="📋 Member Responsibilities",
            value=(
                "• Contribute to guild bank\n"
                "• Help guild level up\n"
                "• Participate in events\n"
                "• Follow guild rules\n"
                "• Support other members"
            ),
            inline=False
        )

        embed.set_footer(text=f"Invited by {self.inviter.display_name} • Decision required")
        
        return embed

    @discord.ui.button(label="Accept Invite", style=discord.ButtonStyle.success, emoji="🛡️")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.accepted = True
        self.stop()

        # Join guild
        db = self.bot.db
        target_id = str(self.target.id)
        guild_id = self.guild_data["guild_id"]

        # Check if already in a guild
        target_u = db.getuser(target_id)
        if target_u.get("guild_id"):
            self.accepted = False
            
            # Disable buttons
            disable_all_interactive(self)
            
            embed = discord.Embed(
                title="❌ Already in Guild",
                description=f"You're already in a guild!\n\nUse `/leaveguild` to leave your current guild first.",
                color=GUILD_COLORS["danger"]
            )
            apply_v2_embed_layout(self, embed=embed)
            return await interaction.response.edit_message(view=self)

        # Join with "recruit" role initially
        db.updatestat(target_id, "guild_id", guild_id)
        db.updatestat(target_id, "guild_role", "recruit")
        db.updatestat(target_id, "guild_joined_at", datetime.now(timezone.utc).isoformat())

        # Update member count
        current_count = int(self.guild_data.get("member_count", 0))
        db.updateguild(guild_id, "member_count", current_count + 1)

        # Disable buttons
        disable_all_interactive(self)

        # Success embed
        guild_name = self.guild_data.get("name", "the guild")
        guild_level = self.guild_data.get("level", 1)

        embed = discord.Embed(
            title="🎉 Welcome to the Guild!",
            description=f"**{self.target.display_name}** joined **{guild_name}**!",
            color=GUILD_COLORS["success"]
        )

        embed.add_field(
            name="🔰 Your Role",
            value="**Recruit** - Prove yourself to rank up!",
            inline=True
        )

        embed.add_field(
            name="✨ Active Bonuses",
            value=(
                f"⭐ +{5 + guild_level}% XP\n"
                f"💰 +{5 + guild_level}% Money\n"
                "🛡️ Guild Protection"
            ),
            inline=True
        )

        embed.add_field(
            name="📝 Next Steps",
            value=(
                "• Use `/guild` to view guild info\n"
                "• Use `/guildbank` to contribute\n"
                "• Work hard to rank up!\n"
                "• Help the guild grow!"
            ),
            inline=False
        )

        embed.set_footer(text=f"Joined {guild_name} • Welcome aboard!")

        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.accepted = False
        self.stop()

        # Disable buttons
        disable_all_interactive(self)

        embed = discord.Embed(
            title="❌ Invitation Declined",
            description=f"**{self.target.display_name}** declined the invitation to **{self.guild_data.get('name', 'the guild')}**.",
            color=GUILD_COLORS["danger"]
        )

        embed.set_footer(text="You can always join another guild later!")

        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        """Handle timeout."""
        disable_all_interactive(self)


# ============= LEAVE GUILD CONFIRMATION =============

class LeaveGuildConfirmation(discord.ui.LayoutView):
    """Confirm leaving guild with warnings."""

    def __init__(self, user: discord.User, guild_name: str, guild_data: dict):
        super().__init__(timeout=60)
        self.user = user
        self.guild_name = guild_name
        self.guild_data = guild_data
        self.confirmed = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Not your decision!",
                ephemeral=True
            )
            return False
        return True

    def create_leave_embed(self) -> discord.Embed:
        """Create leave confirmation embed."""
        guild_level = self.guild_data.get("level", 1)

        embed = discord.Embed(
            title="⚠️ Leave Guild?",
            description=f"Are you sure you want to leave **{self.guild_name}**?\n\nThis action cannot be undone!",
            color=GUILD_COLORS["warning"]
        )

        embed.add_field(
            name="❌ What You'll Lose",
            value=(
                f"• ⭐ +{5 + guild_level}% XP bonus\n"
                f"• 💰 +{5 + guild_level}% money bonus\n"
                "• 🛡️ Guild protection\n"
                "• 💰 Access to guild bank\n"
                "• 🎁 Guild events & rewards\n"
                "• 👥 Guild member benefits"
            ),
            inline=False
        )

        embed.add_field(
            name="📋 After Leaving",
            value=(
                "• You'll become guildless\n"
                "• Can join another guild immediately\n"
                "• All guild bonuses removed\n"
                "• Cannot rejoin for 24 hours"
            ),
            inline=False
        )

        embed.set_footer(text="Think carefully before proceeding...")

        return embed

    @discord.ui.button(label="Confirm Leave", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop()

        # Disable buttons
        disable_all_interactive(self)

        await interaction.response.defer()

    @discord.ui.button(label="Stay in Guild", style=discord.ButtonStyle.success, emoji="🛡️")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self.stop()

        # Disable buttons
        disable_all_interactive(self)

        embed = discord.Embed(
            title="✅ Stayed in Guild",
            description=f"You decided to stay in **{self.guild_name}**.\n\nGood choice! Your guild needs you! 🛡️",
            color=GUILD_COLORS["success"]
        )

        embed.set_footer(text="Loyalty is rewarded! 💪")

        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)


# ============= GUILD OVERVIEW =============

class GuildView(discord.ui.LayoutView):
    """Guild overview and management."""

    def __init__(self, bot, user: discord.User):
        super().__init__(timeout=180)
        self.bot = bot
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    async def create_embed(self) -> discord.Embed:
        """Create guild overview embed."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)

        guild_id = u.get("guild_id")

        if not guild_id:
            # Not in a guild
            embed = discord.Embed(
                title="🛡️ Guild System",
                description="You're not in a guild! Join or create one to unlock benefits.",
                color=GUILD_COLORS["info"]
            )

            embed.add_field(
                name="💡 What are Guilds?",
                value=(
                    "Guilds are groups of players working together!\n"
                    "Join forces for bonuses and rewards."
                ),
                inline=False
            )

            embed.add_field(
                name="✨ Guild Benefits",
                value=(
                    "• ⭐ Increased XP gains\n"
                    "• 💰 Money bonuses\n"
                    "• 🛡️ Protection from robberies\n"
                    "• 🎁 Exclusive guild events\n"
                    "• 💬 Guild chat & community"
                ),
                inline=False
            )

            embed.add_field(
                name="📝 Getting Started",
                value=(
                    "• `/createguild <name>` - Create your own ($10,000)\n"
                    "• `/guilds` - Browse available guilds\n"
                    "• Wait for an invitation from a guild leader"
                ),
                inline=False
            )

            return embed

        # In a guild - fetch guild data
        guild_data = db.getguild(guild_id)
        
        if not guild_data:
            embed = discord.Embed(
                title="❌ Error",
                description="Your guild data couldn't be found. Contact an admin!",
                color=GUILD_COLORS["danger"]
            )
            return embed

        guild_name = guild_data.get("name", "Unknown Guild")
        guild_level = guild_data.get("level", 1)
        guild_xp = guild_data.get("xp", 0)
        guild_bank = int(guild_data.get("bank", 0))
        member_count = guild_data.get("member_count", 0)
        max_members = guild_data.get("max_members", 20)
        created_at = guild_data.get("created_at")
        description = guild_data.get("description", "No description")

        user_role = u.get("guild_role", "member")
        role_emoji = GUILD_RANK_EMOJIS.get(user_role, "🛡️")

        embed = discord.Embed(
            title=f"🛡️ {guild_name}",
            description=description,
            color=GUILD_COLORS["guild"]
        )

        # Guild stats
        embed.add_field(
            name="📊 Guild Stats",
            value=(
                f"**Level:** {guild_level}\n"
                f"**XP:** {guild_xp:,}/{guild_level * 1000:,}\n"
                f"**Members:** {member_count}/{max_members}"
            ),
            inline=True
        )

        # Guild bank
        embed.add_field(
            name="💰 Guild Bank",
            value=f"**Balance:** {money(guild_bank)}",
            inline=True
        )

        # Your role
        embed.add_field(
            name="👤 Your Role",
            value=f"{role_emoji} **{user_role.title()}**",
            inline=True
        )

        # Active bonuses
        embed.add_field(
            name="✨ Active Bonuses",
            value=(
                f"⭐ +{5 + guild_level}% XP\n"
                f"💰 +{5 + guild_level}% Money\n"
                "🛡️ Guild Protection"
            ),
            inline=True
        )

        # Guild age
        if created_at:
            created_date = datetime.fromisoformat(created_at)
            age = datetime.now(timezone.utc) - created_date
            days = age.days
            embed.add_field(
                name="📅 Guild Age",
                value=f"{days} days old",
                inline=True
            )

        embed.set_footer(text="Use buttons below to manage your guild")

        return embed

    @discord.ui.button(label="Members", style=discord.ButtonStyle.primary, emoji="👥")
    async def members_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)

        guild_id = u.get("guild_id")
        
        if not guild_id:
            return await interaction.response.send_message(
                "❌ You're not in a guild!",
                ephemeral=True
            )

        # Get all guild members
        members = db.get_guild_members(guild_id)  # You'll need to implement this
        
        embed = discord.Embed(
            title="👥 Guild Members",
            description=f"Showing all members of the guild",
            color=GUILD_COLORS["info"]
        )

        # Group by role
        leaders = [m for m in members if m.get("guild_role") == "leader"]
        officers = [m for m in members if m.get("guild_role") == "officer"]
        regular = [m for m in members if m.get("guild_role") == "member"]
        recruits = [m for m in members if m.get("guild_role") == "recruit"]

        if leaders:
            leader_list = "\n".join([f"👑 <@{m['user_id']}>" for m in leaders[:5]])
            embed.add_field(name="Leaders", value=leader_list, inline=False)

        if officers:
            officer_list = "\n".join([f"⭐ <@{m['user_id']}>" for m in officers[:5]])
            embed.add_field(name="Officers", value=officer_list, inline=False)

        if regular:
            member_list = "\n".join([f"🛡️ <@{m['user_id']}>" for m in regular[:10]])
            embed.add_field(name="Members", value=member_list, inline=False)

        if recruits:
            recruit_list = "\n".join([f"🔰 <@{m['user_id']}>" for m in recruits[:10]])
            embed.add_field(name="Recruits", value=recruit_list, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Guild Bank", style=discord.ButtonStyle.success, emoji="💰")
    async def bank_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)

        guild_id = u.get("guild_id")
        
        if not guild_id:
            return await interaction.response.send_message(
                "❌ You're not in a guild!",
                ephemeral=True
            )

        guild_data = db.getguild(guild_id)
        guild_bank = int(guild_data.get("bank", 0))
        balance = int(u.get("balance", 0))

        embed = discord.Embed(
            title="💰 Guild Bank",
            description=f"**Guild Balance:** {money(guild_bank)}\n**Your Wallet:** {money(balance)}",
            color=GUILD_COLORS["success"]
        )

        embed.add_field(
            name="📝 Commands",
            value=(
                "• `/guilddeposit <amount>` - Contribute to guild\n"
                "• `/guildwithdraw <amount>` - Withdraw (leader only)"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Leave Guild", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)

        guild_id = u.get("guild_id")
        
        if not guild_id:
            return await interaction.response.send_message(
                "❌ You're not in a guild!",
                ephemeral=True
            )

        guild_data = db.getguild(guild_id)
        guild_name = guild_data.get("name", "the guild")

        # Check if leader
        user_role = u.get("guild_role", "member")
        if user_role == "leader":
            return await interaction.response.send_message(
                "❌ You can't leave as the guild leader! Transfer leadership or disband the guild first.",
                ephemeral=True
            )

        # Show confirmation
        view = LeaveGuildConfirmation(self.user, guild_name, guild_data)
        embed = view.create_leave_embed()

        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.create_embed()
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
