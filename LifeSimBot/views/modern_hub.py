# views/modern_hub.py
"""
Modern Hub - Central navigation with clean, simple UI
"""

import discord
from typing import Optional
from views.modern_ui import ModernView, Colors, Icons, create_progress_bar, format_stat_box
from utils.format import money, format_time
from views.v2_embed import apply_v2_embed_layout


class ModernHub(ModernView):
    """
    Redesigned hub with clean layout and intuitive navigation
    """
    
    def __init__(self, bot, user: discord.User):
        super().__init__(user, timeout=300)
        self.bot = bot
        self.current_page = "main"
        self.add_navigation_buttons()
    
    def add_navigation_buttons(self):
        """Add main navigation buttons"""
        self.clear_items()
        
        if self.current_page != "main":
            # Back to main button
            back_btn = discord.ui.Button(
                label="Main Menu",
                emoji=Icons.HOME,
                style=discord.ButtonStyle.secondary,
                row=0
            )
            back_btn.callback = self.show_main
            self.add_item(back_btn)
        
        if self.current_page == "main":
            # Main menu buttons
            profile_btn = discord.ui.Button(
                label="Profile",
                emoji="👤",
                style=discord.ButtonStyle.primary,
                row=0
            )
            profile_btn.callback = self.show_profile
            self.add_item(profile_btn)
            
            economy_btn = discord.ui.Button(
                label="Economy",
                emoji=Icons.MONEY,
                style=discord.ButtonStyle.success,
                row=0
            )
            economy_btn.callback = self.show_economy
            self.add_item(economy_btn)
            
            activities_btn = discord.ui.Button(
                label="Activities",
                emoji="🎮",
                style=discord.ButtonStyle.primary,
                row=0
            )
            activities_btn.callback = self.show_activities
            self.add_item(activities_btn)
            
            social_btn = discord.ui.Button(
                label="Social",
                emoji=Icons.SOCIAL,
                style=discord.ButtonStyle.primary,
                row=0
            )
            social_btn.callback = self.show_social
            self.add_item(social_btn)
            
            # Second row
            inventory_btn = discord.ui.Button(
                label="Inventory",
                emoji=Icons.INVENTORY,
                style=discord.ButtonStyle.secondary,
                row=1
            )
            inventory_btn.callback = self.show_inventory
            self.add_item(inventory_btn)
            
            settings_btn = discord.ui.Button(
                label="Settings",
                emoji=Icons.SETTINGS,
                style=discord.ButtonStyle.secondary,
                row=1
            )
            settings_btn.callback = self.show_settings
            self.add_item(settings_btn)
        
        # Always show refresh and close
        refresh_btn = discord.ui.Button(
            emoji=Icons.REFRESH,
            style=discord.ButtonStyle.secondary,
            row=2
        )
        refresh_btn.callback = self.refresh
        self.add_item(refresh_btn)
        
        close_btn = discord.ui.Button(
            emoji=Icons.CLOSE,
            style=discord.ButtonStyle.danger,
            row=2
        )
        close_btn.callback = self.close_hub
        self.add_item(close_btn)
    
    def get_user_data(self):
        """Get user data from database"""
        db = self.bot.db
        return db.getuser(str(self.user.id))
    
    async def show_main(self, interaction: discord.Interaction):
        """Show main hub page"""
        self.current_page = "main"
        self.add_navigation_buttons()
        
        u = self.get_user_data()
        balance = int(u.get("balance", 0))
        level = int(u.get("level", 1))
        xp = int(u.get("xp", 0))
        xp_needed = level * 100
        
        # Create clean main hub embed
        embed = discord.Embed(
            title=f"🏠 Welcome, {self.user.name}!",
            description="**Select a category to explore**",
            color=Colors.PRIMARY
        )
        
        # Quick stats
        stats_bar = create_progress_bar(xp, xp_needed, 15)
        
        embed.add_field(
            name="📊 Quick Stats",
            value=(
                f"💰 **Balance:** {money(balance)}\n"
                f"⭐ **Level:** {level}\n"
                f"📈 **XP:** {stats_bar} `{xp}/{xp_needed}`"
            ),
            inline=False
        )
        
        # Quick actions info
        embed.add_field(
            name="✨ Quick Actions",
            value=(
                "**Profile** - View your detailed stats\n"
                "**Economy** - Money, jobs, businesses\n"
                "**Activities** - Games, quests, events\n"
                "**Social** - Friends, guilds, family"
            ),
            inline=False
        )
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        embed.set_footer(text="💡 Tip: Use /help to see all commands")
        
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
    
    async def show_profile(self, interaction: discord.Interaction):
        """Show detailed profile"""
        self.current_page = "profile"
        self.add_navigation_buttons()
        
        u = self.get_user_data()
        
        # Get stats
        level = int(u.get("level", 1))
        xp = int(u.get("xp", 0))
        balance = int(u.get("balance", 0))
        bank = int(u.get("bank", 0))
        energy = int(u.get("energy", 100))
        health = int(u.get("health", 100))
        job = u.get("current_job", "Unemployed")
        
        embed = discord.Embed(
            title=f"👤 {self.user.name}'s Profile",
            color=Colors.INFO
        )
        
        # Level progress
        xp_needed = level * 100
        xp_bar = create_progress_bar(xp, xp_needed, 15)
        
        embed.add_field(
            name="📊 Level & XP",
            value=f"**Level {level}**\n{xp_bar}\n`{xp:,}/{xp_needed:,} XP`",
            inline=False
        )
        
        # Money
        total_wealth = balance + bank
        embed.add_field(
            name="💰 Wealth",
            value=f"**Total:** {money(total_wealth)}\n💵 Cash: {money(balance)}\n🏦 Bank: {money(bank)}",
            inline=True
        )
        
        # Job
        embed.add_field(
            name="💼 Career",
            value=f"**{job}**",
            inline=True
        )
        
        # Status
        energy_bar = create_progress_bar(energy, 100, 10)
        health_bar = create_progress_bar(health, 100, 10)
        
        embed.add_field(
            name="❤️ Status",
            value=f"⚡ Energy: {energy_bar} `{energy}%`\n❤️ Health: {health_bar} `{health}%`",
            inline=True
        )
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        embed.set_footer(text="Use the buttons below to navigate")
        
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
    
    async def show_economy(self, interaction: discord.Interaction):
        """Show economy overview"""
        self.current_page = "economy"
        self.add_navigation_buttons()
        
        u = self.get_user_data()
        balance = int(u.get("balance", 0))
        bank = int(u.get("bank", 0))
        job = u.get("current_job", "Unemployed")
        
        embed = discord.Embed(
            title="💰 Economy Hub",
            description="**Manage your finances and career**",
            color=Colors.ECONOMY
        )
        
        # Financial overview
        total = balance + bank
        embed.add_field(
            name="💵 Finances",
            value=(
                f"**Total Wealth:** {money(total)}\n"
                f"💰 Cash: {money(balance)}\n"
                f"🏦 Bank: {money(bank)}"
            ),
            inline=False
        )
        
        # Job info
        embed.add_field(
            name="💼 Career",
            value=f"**Current Job:** {job}\n\n`/jobs` - Browse careers\n`/work` - Start working",
            inline=True
        )
        
        # Quick actions
        embed.add_field(
            name="🛒 Quick Actions",
            value=(
                "`/shop` - Buy items\n"
                "`/daily` - Daily reward\n"
                "`/balance` - Check money"
            ),
            inline=True
        )
        
        embed.set_footer(text="💡 Tip: Keep money in the bank to earn interest!")
        
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
    
    async def show_activities(self, interaction: discord.Interaction):
        """Show activities menu"""
        self.current_page = "activities"
        self.add_navigation_buttons()
        
        embed = discord.Embed(
            title="🎮 Activities",
            description="**Fun ways to spend your time**",
            color=Colors.GAMING
        )
        
        # Casino
        embed.add_field(
            name="🎰 Casino",
            value=(
                "Test your luck!\n"
                "`/casino` - Play games\n"
                "`/slots` - Slot machine\n"
                "`/blackjack` - Card game"
            ),
            inline=True
        )
        
        # Crime
        embed.add_field(
            name="🔪 Crime",
            value=(
                "Live dangerously!\n"
                "`/crime` - Commit crimes\n"
                "`/rob` - Rob someone"
            ),
            inline=True
        )
        
        # Other activities
        embed.add_field(
            name="🎯 More Activities",
            value=(
                "`/cook` - Prepare food\n"
                "`/crypto` - Trade crypto\n"
                "`/quests` - Complete quests"
            ),
            inline=True
        )
        
        embed.set_footer(text="💡 Tip: Higher risk = higher reward!")
        
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
    
    async def show_social(self, interaction: discord.Interaction):
        """Show social menu"""
        self.current_page = "social"
        self.add_navigation_buttons()
        
        embed = discord.Embed(
            title="👥 Social Hub",
            description="**Connect with other players**",
            color=Colors.SOCIAL
        )
        
        # Relationships
        embed.add_field(
            name="💑 Relationships",
            value=(
                "`/marry` - Propose marriage\n"
                "`/divorce` - End marriage\n"
                "`/family` - View family"
            ),
            inline=True
        )
        
        # Guilds
        embed.add_field(
            name="🛡️ Guilds",
            value=(
                "`/guild` - View guild\n"
                "`/guild create` - Start guild\n"
                "`/guild join` - Join guild"
            ),
            inline=True
        )
        
        # Competition
        embed.add_field(
            name="🏆 Competition",
            value=(
                "`/leaderboard` - Top players\n"
                "`/duel` - Fight others\n"
                "`/achievements` - Your progress"
            ),
            inline=True
        )
        
        embed.set_footer(text="💡 Tip: Team up for better rewards!")
        
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
    
    async def show_inventory(self, interaction: discord.Interaction):
        """Show inventory info"""
        self.current_page = "inventory"
        self.add_navigation_buttons()
        
        embed = discord.Embed(
            title="🎒 Inventory",
            description="**Your items and belongings**",
            color=Colors.SECONDARY
        )
        
        embed.add_field(
            name="📦 Item Management",
            value=(
                "`/inventory` - View all items\n"
                "`/use [item]` - Use an item\n"
                "`/gift [user] [item]` - Give item"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🏠 Properties",
            value="`/properties` - View owned properties",
            inline=True
        )
        
        embed.add_field(
            name="🐾 Pets",
            value="`/pets` - Manage your pets",
            inline=True
        )
        
        embed.set_footer(text="💡 Tip: Use items for buffs and bonuses!")
        
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
    
    async def show_settings(self, interaction: discord.Interaction):
        """Show settings menu"""
        self.current_page = "settings"
        self.add_navigation_buttons()
        
        embed = discord.Embed(
            title="⚙️ Settings",
            description="**Customize your experience**",
            color=Colors.SECONDARY
        )
        
        embed.add_field(
            name="🔧 Available Commands",
            value=(
                "`/help` - Command list\n"
                "`/profile` - View profile\n"
                "`/stats` - Detailed statistics"
            ),
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ Information",
            value=(
                f"**Bot Version:** 2.0\n"
                f"**Commands:** 97\n"
                f"**Jobs Available:** 34"
            ),
            inline=False
        )
        
        embed.set_footer(text="More settings coming soon!")
        
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
    
    async def refresh(self, interaction: discord.Interaction):
        """Refresh current page"""
        page_methods = {
            "main": self.show_main,
            "profile": self.show_profile,
            "economy": self.show_economy,
            "activities": self.show_activities,
            "social": self.show_social,
            "inventory": self.show_inventory,
            "settings": self.show_settings
        }
        
        method = page_methods.get(self.current_page, self.show_main)
        await method(interaction)
    
    async def close_hub(self, interaction: discord.Interaction):
        """Close the hub"""
        embed = self.create_embed(
            title=f"{Icons.CHECK} Hub Closed",
            description="Thanks for using LifeSimBot! Use `/hub` to reopen anytime.",
            color=Colors.SUCCESS
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
