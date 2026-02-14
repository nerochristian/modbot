"""
Core Cog - Essential bot commands and user management
Handles registration, profiles, daily rewards, and basic user operations
Uses Discord Components V2 for interactive UI
"""

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, Select, LayoutView, Modal, TextInput
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio
import logging
import os
from enum import Enum

from utils.format import format_currency, format_time, format_percentage
from utils.checks import is_registered
from utils.constants import *
from views.v2_embed import apply_v2_embed_layout

logger = logging.getLogger('LifeSimBot.Core')

class ProfileTab(Enum):
    """Enum for profile tabs"""
    OVERVIEW = "overview"
    STATS = "stats"
    ACHIEVEMENTS = "achievements"
    INVENTORY = "inventory"
    SOCIAL = "social"

class RegistrationModal(Modal, title="Register Your Account"):
    """Modal for user registration"""
    
    username = TextInput(
        label="Choose Your Username",
        placeholder="Enter a unique username (3-20 characters)",
        min_length=3,
        max_length=20,
        required=True
    )
    
    bio = TextInput(
        label="Bio (Optional)",
        placeholder="Tell us about yourself...",
        style=discord.TextStyle.paragraph,
        max_length=200,
        required=False
    )
    
    favorite_color = TextInput(
        label="Favorite Color (Hex Code)",
        placeholder="#FF5733",
        min_length=7,
        max_length=7,
        required=False,
        default="#3498db"
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle registration submission"""
        try:
            # Validate username
            username = self.username.value.strip()
            if not username.isalnum():
                await interaction.response.send_message(
                    "❌ Username must contain only letters and numbers!",
                    ephemeral=True
                )
                return
            
            # Check if username is taken
            existing = await self.cog.bot.db.fetch_one(
                "SELECT user_id FROM users WHERE username = ?",
                (username,)
            )
            if existing:
                await interaction.response.send_message(
                    f"❌ Username '{username}' is already taken!",
                    ephemeral=True
                )
                return
            
            # Validate color
            color = self.favorite_color.value.strip()
            if not color.startswith('#'):
                color = f"#{color}"
            try:
                int(color[1:], 16)
            except ValueError:
                color = "#3498db"
            
            # Create user account
            bio = self.bio.value.strip() or "No bio yet."
            starting_balance = int(os.getenv('STARTING_BALANCE', EconomyConfig.STARTING_BALANCE))
            
            await self.cog.bot.db.execute(
                """
                INSERT INTO users (
                    user_id, discord_id, username, bio, balance,
                    bank, net_worth, favorite_color, created_at, last_daily
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    discord_id = excluded.discord_id,
                    username = excluded.username,
                    bio = excluded.bio,
                    favorite_color = excluded.favorite_color
                """,
                (
                    interaction.user.id,
                    interaction.user.id,
                    username,
                    bio,
                    starting_balance,
                    0,
                    starting_balance,
                    color,
                    datetime.utcnow().isoformat(),
                    None
                )
            )
            
            # Initialize default stats
            await self.cog.bot.db.execute(
                """
                INSERT INTO user_stats (
                    user_id, level, xp, health, energy, happiness
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO NOTHING
                """,
                (interaction.user.id, 1, 0, 100, 100, 100)
            )
            
            # Create welcome embed
            embed = discord.Embed(
                title="🎉 Welcome to LifeSimBot!",
                description=(
                    f"**{username}**, your account has been created!\n\n"
                    f"**Starting Balance:** {format_currency(starting_balance)}\n"
                    f"**Bio:** {bio}\n\n"
                    "**Getting Started:**\n"
                    "• Use `/daily` to claim daily rewards\n"
                    "• Use `/work` to earn money\n"
                    "• Use `/profile` to view your profile\n"
                    "• Use `/hub` to access the main menu\n"
                    "• Use `/help` to see all commands"
                ),
                color=int(color[1:], 16)
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text=f"User ID: {interaction.user.id}")
            embed.timestamp = datetime.utcnow()
            
            await interaction.response.send_message(embed=embed)
            
            logger.info(f"New user registered: {username} ({interaction.user.id})")
            
        except Exception as e:
            logger.error(f"Error in registration: {e}")
            await interaction.response.send_message(
                "❌ An error occurred during registration. Please try again.",
                ephemeral=True
            )

class ProfileView(LayoutView):
    """Interactive profile view with tabs"""
    
    def __init__(self, user: discord.User, user_data: Dict, bot, timeout=180):
        super().__init__(timeout=timeout)
        self.user = user
        self.user_data = user_data
        self.bot = bot
        self.current_tab = ProfileTab.OVERVIEW
        self.message: Optional[discord.Message] = None
        
        # Add tab buttons
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current tab"""
        self.clear_items()
        
        # Tab buttons
        tabs = [
            ("📊 Overview", ProfileTab.OVERVIEW, discord.ButtonStyle.primary),
            ("📈 Stats", ProfileTab.STATS, discord.ButtonStyle.secondary),
            ("🏆 Achievements", ProfileTab.ACHIEVEMENTS, discord.ButtonStyle.secondary),
            ("🎒 Inventory", ProfileTab.INVENTORY, discord.ButtonStyle.secondary),
            ("👥 Social", ProfileTab.SOCIAL, discord.ButtonStyle.secondary),
        ]
        
        for label, tab, style in tabs:
            is_current = self.current_tab == tab
            button = Button(
                label=label,
                style=discord.ButtonStyle.success if is_current else style,
                disabled=is_current,
                custom_id=f"profile_tab_{tab.value}"
            )
            button.callback = self.create_tab_callback(tab)
            self.add_item(button)
        
        # Action buttons (second row)
        edit_btn = Button(label="✏️ Edit Profile", style=discord.ButtonStyle.secondary, row=1)
        edit_btn.callback = self.edit_profile
        self.add_item(edit_btn)
        
        refresh_btn = Button(label="🔄 Refresh", style=discord.ButtonStyle.secondary, row=1)
        refresh_btn.callback = self.refresh_profile
        self.add_item(refresh_btn)
        
        close_btn = Button(label="❌ Close", style=discord.ButtonStyle.danger, row=1)
        close_btn.callback = self.close_view
        self.add_item(close_btn)
    
    def create_tab_callback(self, tab: ProfileTab):
        """Create callback for tab button"""
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message(
                    "❌ This is not your profile!",
                    ephemeral=True
                )
                return
            
            self.current_tab = tab
            self.update_buttons()
            embed = await self.create_embed()
            apply_v2_embed_layout(self, embed=embed)
            await interaction.response.edit_message(view=self)
        
        return callback
    
    async def create_embed(self) -> discord.Embed:
        """Create embed based on current tab"""
        if self.current_tab == ProfileTab.OVERVIEW:
            return await self.create_overview_embed()
        elif self.current_tab == ProfileTab.STATS:
            return await self.create_stats_embed()
        elif self.current_tab == ProfileTab.ACHIEVEMENTS:
            return await self.create_achievements_embed()
        elif self.current_tab == ProfileTab.INVENTORY:
            return await self.create_inventory_embed()
        elif self.current_tab == ProfileTab.SOCIAL:
            return await self.create_social_embed()
    
    async def create_overview_embed(self) -> discord.Embed:
        """Create overview tab embed"""
        data = self.user_data
        color = int(data.get('favorite_color', '#3498db')[1:], 16)
        
        embed = discord.Embed(
            title=f"📋 {data['username']}'s Profile",
            description=data.get('bio', 'No bio set.'),
            color=color
        )
        
        # User info
        embed.add_field(
            name="💰 Economy",
            value=(
                f"**Cash:** {format_currency(data.get('balance', 0))}\n"
                f"**Bank:** {format_currency(data.get('bank', 0))}\n"
                f"**Net Worth:** {format_currency(data.get('balance', 0) + data.get('bank', 0))}"
            ),
            inline=True
        )
        
        # Stats
        stats = await self.bot.db.fetch_one(
            "SELECT * FROM user_stats WHERE user_id = ?",
            (self.user.id,)
        )
        if stats:
            embed.add_field(
                name="📊 Stats",
                value=(
                    f"**Level:** {stats.get('level', 1)}\n"
                    f"**XP:** {stats.get('xp', 0)}/{stats.get('level', 1) * 100}\n"
                    f"**Health:** {stats.get('health', 100)}/100"
                ),
                inline=True
            )
        
        # Job info
        job = await self.bot.db.fetch_one(
            "SELECT * FROM user_jobs WHERE user_id = ?",
            (self.user.id,)
        )
        if job:
            embed.add_field(
                name="💼 Employment",
                value=(
                    f"**Job:** {job.get('job_name', 'Unemployed')}\n"
                    f"**Position:** {job.get('position', 'N/A')}\n"
                    f"**Salary:** {format_currency(job.get('salary', 0))}/hr"
                ),
                inline=True
            )
        else:
            embed.add_field(
                name="💼 Employment",
                value="**Status:** Unemployed\nUse `/jobs` to find work!",
                inline=True
            )
        
        # Account info
        created_at = datetime.fromisoformat(data.get('created_at', datetime.utcnow().isoformat()))
        days_old = (datetime.utcnow() - created_at).days
        
        embed.add_field(
            name="📅 Account Info",
            value=(
                f"**Created:** {created_at.strftime('%Y-%m-%d')}\n"
                f"**Age:** {days_old} days\n"
                f"**User ID:** {self.user.id}"
            ),
            inline=False
        )
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        embed.set_footer(text="Use the buttons below to navigate")
        embed.timestamp = datetime.utcnow()
        
        return embed
    
    async def create_stats_embed(self) -> discord.Embed:
        """Create stats tab embed"""
        data = self.user_data
        color = int(data.get('favorite_color', '#3498db')[1:], 16)
        
        embed = discord.Embed(
            title=f"📈 {data['username']}'s Statistics",
            color=color
        )
        
        # Get stats
        stats = await self.bot.db.fetch_one(
            "SELECT * FROM user_stats WHERE user_id = ?",
            (self.user.id,)
        )
        
        if stats:
            # Basic stats
            embed.add_field(
                name="🎯 Basic Stats",
                value=(
                    f"**Level:** {stats.get('level', 1)}\n"
                    f"**XP:** {stats.get('xp', 0)}/{stats.get('level', 1) * 100}\n"
                    f"**Progress:** {format_percentage(stats.get('xp', 0) / (stats.get('level', 1) * 100))}"
                ),
                inline=True
            )
            
            # Vital stats
            embed.add_field(
                name="❤️ Vitals",
                value=(
                    f"**Health:** {stats.get('health', 100)}/100\n"
                    f"**Energy:** {stats.get('energy', 100)}/100\n"
                    f"**Happiness:** {stats.get('happiness', 100)}/100"
                ),
                inline=True
            )
        
        # Get skills
        skills = await self.bot.db.fetch_all(
            "SELECT * FROM user_skills WHERE user_id = ? ORDER BY level DESC LIMIT 5",
            (self.user.id,)
        )
        
        if skills:
            skills_text = "\n".join([
                f"**{skill['skill_name']}:** Level {skill['level']} ({skill['xp']}/{skill['level'] * 100} XP)"
                for skill in skills
            ])
            embed.add_field(
                name="🎓 Top Skills",
                value=skills_text or "No skills yet!",
                inline=False
            )
        
        # Activity stats
        activity = await self.bot.db.fetch_one(
            """
            SELECT 
                COUNT(DISTINCT command_name) as commands_used,
                SUM(times_used) as total_commands
            FROM user_command_stats WHERE user_id = ?
            """,
            (self.user.id,)
        )
        
        if activity:
            embed.add_field(
                name="📊 Activity",
                value=(
                    f"**Commands Used:** {activity.get('total_commands', 0)}\n"
                    f"**Unique Commands:** {activity.get('commands_used', 0)}"
                ),
                inline=True
            )
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        embed.set_footer(text="Keep playing to improve your stats!")
        embed.timestamp = datetime.utcnow()
        
        return embed
    
    async def create_achievements_embed(self) -> discord.Embed:
        """Create achievements tab embed"""
        data = self.user_data
        color = int(data.get('favorite_color', '#3498db')[1:], 16)
        
        embed = discord.Embed(
            title=f"🏆 {data['username']}'s Achievements",
            color=color
        )
        
        # Get achievements
        achievements = await self.bot.db.fetch_all(
            """
            SELECT ua.*, a.name, a.description, a.icon, a.rarity
            FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.achievement_id
            WHERE ua.user_id = ?
            ORDER BY ua.unlocked_at DESC
            LIMIT 10
            """,
            (self.user.id,)
        )
        
        # Count total achievements
        total_achievements = await self.bot.db.fetch_one(
            "SELECT COUNT(*) as count FROM achievements"
        )
        
        user_count = len(achievements)
        total_count = total_achievements['count'] if total_achievements else 0
        
        embed.description = (
            f"**Progress:** {user_count}/{total_count} "
            f"({format_percentage(user_count / total_count if total_count > 0 else 0)})\n\n"
        )
        
        if achievements:
            for achievement in achievements[:5]:  # Show only 5
                rarity_emoji = {
                    'common': '⚪',
                    'uncommon': '🟢',
                    'rare': '🔵',
                    'epic': '🟣',
                    'legendary': '🟡'
                }.get(achievement.get('rarity', 'common'), '⚪')
                
                unlocked_at = datetime.fromisoformat(achievement['unlocked_at'])
                embed.add_field(
                    name=f"{achievement['icon']} {achievement['name']} {rarity_emoji}",
                    value=(
                        f"{achievement['description']}\n"
                        f"*Unlocked {unlocked_at.strftime('%Y-%m-%d')}*"
                    ),
                    inline=False
                )
        else:
            embed.add_field(
                name="No Achievements Yet",
                value="Start playing to unlock achievements!",
                inline=False
            )
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        embed.set_footer(text="Use /achievements to see all available achievements")
        embed.timestamp = datetime.utcnow()
        
        return embed
    
    async def create_inventory_embed(self) -> discord.Embed:
        """Create inventory tab embed"""
        data = self.user_data
        color = int(data.get('favorite_color', '#3498db')[1:], 16)
        
        embed = discord.Embed(
            title=f"🎒 {data['username']}'s Inventory",
            color=color
        )
        
        # Get inventory items
        items = await self.bot.db.fetch_all(
            """
            SELECT ui.*, i.name, i.description, i.icon, i.rarity
            FROM user_inventory ui
            JOIN items i ON ui.item_id = i.item_id
            WHERE ui.user_id = ?
            ORDER BY i.rarity DESC, ui.quantity DESC
            LIMIT 15
            """,
            (self.user.id,)
        )
        
        if items:
            # Group by category
            categories = {}
            for item in items:
                category = item.get('category', 'Other')
                if category not in categories:
                    categories[category] = []
                categories[category].append(item)
            
            for category, category_items in categories.items():
                items_text = "\n".join([
                    f"{item['icon']} **{item['name']}** x{item['quantity']}"
                    for item in category_items[:5]
                ])
                embed.add_field(
                    name=f"📦 {category}",
                    value=items_text,
                    inline=True
                )
        else:
            embed.description = "Your inventory is empty! Buy items from `/shop` or earn them through gameplay."
        
        # Inventory stats
        total_items = await self.bot.db.fetch_one(
            "SELECT COUNT(*) as count, SUM(quantity) as total FROM user_inventory WHERE user_id = ?",
            (self.user.id,)
        )
        
        if total_items:
            embed.set_footer(
                text=f"Unique Items: {total_items.get('count', 0)} | Total Items: {total_items.get('total', 0)}"
            )
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        
        return embed
    
    async def create_social_embed(self) -> discord.Embed:
        """Create social tab embed"""
        data = self.user_data
        color = int(data.get('favorite_color', '#3498db')[1:], 16)
        
        embed = discord.Embed(
            title=f"👥 {data['username']}'s Social",
            color=color
        )
        
        # Get relationships
        relationships = await self.bot.db.fetch_all(
            """
            SELECT r.*, u.username, u.favorite_color
            FROM relationships r
            JOIN users u ON (
                CASE 
                    WHEN r.user_id = ? THEN r.target_id = u.user_id
                    ELSE r.user_id = u.user_id
                END
            )
            WHERE r.user_id = ? OR r.target_id = ?
            ORDER BY r.relationship_level DESC
            LIMIT 10
            """,
            (self.user.id, self.user.id, self.user.id)
        )
        
        if relationships:
            friends_text = ""
            family_text = ""
            
            for rel in relationships:
                rel_type = rel.get('relationship_type', 'friend')
                level = rel.get('relationship_level', 0)
                
                text = f"**{rel['username']}** - Level {level}\n"
                
                if rel_type in ['spouse', 'parent', 'child', 'sibling']:
                    family_text += text
                else:
                    friends_text += text
            
            if friends_text:
                embed.add_field(
                    name="👫 Friends",
                    value=friends_text[:1024],
                    inline=False
                )
            
            if family_text:
                embed.add_field(
                    name="👨‍👩‍👧‍👦 Family",
                    value=family_text[:1024],
                    inline=False
                )
        else:
            embed.description = "No relationships yet! Use social commands to make friends."
        
        # Guild info
        guild_member = await self.bot.db.fetch_one(
            """
            SELECT gm.*, g.name as guild_name, g.icon
            FROM guild_members gm
            JOIN guilds g ON gm.guild_id = g.guild_id
            WHERE gm.user_id = ?
            """,
            (self.user.id,)
        )
        
        if guild_member:
            embed.add_field(
                name="🏰 Guild",
                value=(
                    f"**{guild_member['guild_name']}**\n"
                    f"Rank: {guild_member.get('rank', 'Member')}\n"
                    f"Contribution: {guild_member.get('contribution', 0)}"
                ),
                inline=True
            )
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        embed.set_footer(text="Use /social to manage your relationships")
        embed.timestamp = datetime.utcnow()
        
        return embed
    
    async def edit_profile(self, interaction: discord.Interaction):
        """Edit profile button callback"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ You can only edit your own profile!",
                ephemeral=True
            )
            return
        
        # Create edit modal
        modal = EditProfileModal(self)
        await interaction.response.send_modal(modal)
    
    async def refresh_profile(self, interaction: discord.Interaction):
        """Refresh profile data"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This is not your profile!",
                ephemeral=True
            )
            return
        
        # Refresh user data
        self.user_data = await self.bot.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (self.user.id,)
        )
        
        embed = await self.create_embed()
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
    
    async def close_view(self, interaction: discord.Interaction):
        """Close the profile view"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Only the profile owner can close this!",
                ephemeral=True
            )
            return
        
        self.stop()
        await interaction.response.edit_message(view=None)
    
    async def on_timeout(self):
        """Called when view times out"""
        if self.message:
            try:
                await self.message.edit(view=None)
            except:
                pass

class EditProfileModal(Modal, title="Edit Your Profile"):
    """Modal for editing profile"""
    
    bio = TextInput(
        label="Bio",
        placeholder="Tell us about yourself...",
        style=discord.TextStyle.paragraph,
        max_length=200,
        required=False
    )
    
    favorite_color = TextInput(
        label="Favorite Color (Hex Code)",
        placeholder="#FF5733",
        min_length=7,
        max_length=7,
        required=False
    )
    
    def __init__(self, profile_view: ProfileView):
        super().__init__()
        self.profile_view = profile_view
        
        # Pre-fill with current values
        current_data = profile_view.user_data
        self.bio.default = current_data.get('bio', '')
        self.favorite_color.default = current_data.get('favorite_color', '#3498db')
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle profile edit submission"""
        try:
            bio = self.bio.value.strip() or "No bio set."
            color = self.favorite_color.value.strip()
            
            if not color.startswith('#'):
                color = f"#{color}"
            
            try:
                int(color[1:], 16)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid color code! Using default color.",
                    ephemeral=True
                )
                color = "#3498db"
            
            # Update profile
            await self.profile_view.bot.db.execute(
                "UPDATE users SET bio = ?, favorite_color = ? WHERE user_id = ?",
                (bio, color, interaction.user.id)
            )
            
            # Refresh profile view
            self.profile_view.user_data = await self.profile_view.bot.db.fetch_one(
                "SELECT * FROM users WHERE user_id = ?",
                (interaction.user.id,)
            )
            
            embed = await self.profile_view.create_embed()
            apply_v2_embed_layout(self.profile_view, embed=embed)
            await interaction.response.edit_message(view=self.profile_view)
            
        except Exception as e:
            logger.error(f"Error editing profile: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while updating your profile.",
                ephemeral=True
            )

class Core(commands.Cog):
    """Core commands for user management and basic operations"""
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("Core cog initialized")
    
    @app_commands.command(name="register", description="Register your account to start playing")
    async def register(self, interaction: discord.Interaction):
        """Register a new user account"""
        # Check if already registered
        user = await self.bot.db.fetch_one(
            "SELECT user_id, username FROM users WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        if user and user.get("username"):
            await interaction.response.send_message(
                "❌ You are already registered! Use `/profile` to view your account.",
                ephemeral=True
            )
            return
        
        # Show registration modal
        modal = RegistrationModal(self)
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="profile", description="View your or another user's profile")
    @app_commands.describe(user="The user whose profile to view (leave empty for your own)")
    async def profile(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """View user profile with interactive tabs"""
        target_user = user or interaction.user
        
        # Get user data
        user_data = await self.bot.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (target_user.id,)
        )
        
        if not user_data or not user_data.get("username"):
            if target_user.id == interaction.user.id:
                await interaction.response.send_message(
                    "❌ You are not registered! Use `/register` to create an account.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ {target_user.mention} is not registered!",
                    ephemeral=True
                )
            return
        
        # Create profile view
        view = ProfileView(target_user, user_data, self.bot)
        embed = await view.create_overview_embed()
        
        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.send_message(view=view)
        view.message = await interaction.original_response()
    
    @app_commands.command(name="daily", description="Claim your daily reward")
    async def daily(self, interaction: discord.Interaction):
        """Claim daily reward"""
        user_data = await self.bot.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        if not user_data or not user_data.get("username"):
            await interaction.response.send_message(
                "❌ You need to register first! Use `/register`.",
                ephemeral=True
            )
            return
        
        # Check if already claimed today
        last_daily = user_data.get('last_daily')
        if last_daily:
            last_daily_dt = datetime.fromisoformat(last_daily)
            time_since = datetime.utcnow() - last_daily_dt
            
            if time_since < timedelta(hours=24):
                time_left = timedelta(hours=24) - time_since
                await interaction.response.send_message(
                    f"⏰ You've already claimed your daily reward!\n"
                    f"Come back in **{format_time(int(time_left.total_seconds()))}**",
                    ephemeral=True
                )
                return
        
        # Calculate reward (with streak bonus)
        base_reward = int(os.getenv('DAILY_REWARD', 500))
        streak = user_data.get('daily_streak', 0) + 1
        streak_bonus = min(streak * 50, 1000)  # Max 1000 bonus
        total_reward = base_reward + streak_bonus
        
        # Update user
        new_balance = user_data['balance'] + total_reward
        await self.bot.db.execute(
            """
            UPDATE users 
            SET balance = ?, last_daily = ?, daily_streak = ?
            WHERE user_id = ?
            """,
            (new_balance, datetime.utcnow().isoformat(), streak, interaction.user.id)
        )
        
        # Create reward embed
        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=f"You've received your daily reward!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💰 Reward",
            value=f"{format_currency(total_reward)}",
            inline=True
        )
        
        embed.add_field(
            name="🔥 Streak",
            value=f"{streak} days",
            inline=True
        )
        
        if streak_bonus > 0:
            embed.add_field(
                name="✨ Streak Bonus",
                value=f"+{format_currency(streak_bonus)}",
                inline=True
            )
        
        embed.add_field(
            name="💵 New Balance",
            value=format_currency(new_balance),
            inline=False
        )
        
        embed.set_footer(text="Come back tomorrow to keep your streak!")
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)
        logger.info(f"User {interaction.user.id} claimed daily reward: {total_reward}")
    
    @app_commands.command(name="balance", description="Check your balance or another user's balance")
    @app_commands.describe(user="The user whose balance to check")
    async def balance(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """Check user balance"""
        target_user = user or interaction.user
        
        user_data = await self.bot.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (target_user.id,)
        )
        
        if not user_data or not user_data.get("username"):
            await interaction.response.send_message(
                f"❌ {target_user.mention} is not registered!",
                ephemeral=True
            )
            return
        
        cash = user_data.get('balance', 0)
        bank = user_data.get('bank', 0)
        net_worth = cash + bank
        
        embed = discord.Embed(
            title=f"💰 {user_data['username']}'s Balance",
            color=discord.Color.green()
        )
        
        embed.add_field(name="💵 Cash", value=format_currency(cash), inline=True)
        embed.add_field(name="🏦 Bank", value=format_currency(bank), inline=True)
        embed.add_field(name="💎 Net Worth", value=format_currency(net_worth), inline=True)
        
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="deposit", description="Deposit money into your bank")
    @app_commands.describe(amount="Amount to deposit (or 'all' for everything)")
    async def deposit(self, interaction: discord.Interaction, amount: str):
        """Deposit money to bank"""
        user_data = await self.bot.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        if not user_data or not user_data.get("username"):
            await interaction.response.send_message(
                "❌ You need to register first! Use `/register`.",
                ephemeral=True
            )
            return
        
        cash = user_data.get('balance', 0)
        bank = user_data.get('bank', 0)
        
        # Parse amount
        if amount.lower() == 'all':
            deposit_amount = cash
        else:
            try:
                deposit_amount = int(amount.replace(',', ''))
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid amount! Please enter a number or 'all'.",
                    ephemeral=True
                )
                return
        
        if deposit_amount <= 0:
            await interaction.response.send_message(
                "❌ You must deposit a positive amount!",
                ephemeral=True
            )
            return
        
        if deposit_amount > cash:
            await interaction.response.send_message(
                f"❌ You don't have enough cash! You only have {format_currency(cash)}.",
                ephemeral=True
            )
            return
        
        # Update balances
        new_cash = cash - deposit_amount
        new_bank = bank + deposit_amount
        
        await self.bot.db.execute(
            "UPDATE users SET balance = ?, bank = ? WHERE user_id = ?",
            (new_cash, new_bank, interaction.user.id)
        )
        
        embed = discord.Embed(
            title="🏦 Deposit Successful",
            description=f"Deposited {format_currency(deposit_amount)} into your bank!",
            color=discord.Color.green()
        )
        
        embed.add_field(name="💵 Cash", value=format_currency(new_cash), inline=True)
        embed.add_field(name="🏦 Bank", value=format_currency(new_bank), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="withdraw", description="Withdraw money from your bank")
    @app_commands.describe(amount="Amount to withdraw (or 'all' for everything)")
    async def withdraw(self, interaction: discord.Interaction, amount: str):
        """Withdraw money from bank"""
        user_data = await self.bot.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        if not user_data or not user_data.get("username"):
            await interaction.response.send_message(
                "❌ You need to register first! Use `/register`.",
                ephemeral=True
            )
            return
        
        cash = user_data.get('balance', 0)
        bank = user_data.get('bank', 0)
        
        # Parse amount
        if amount.lower() == 'all':
            withdraw_amount = bank
        else:
            try:
                withdraw_amount = int(amount.replace(',', ''))
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid amount! Please enter a number or 'all'.",
                    ephemeral=True
                )
                return
        
        if withdraw_amount <= 0:
            await interaction.response.send_message(
                "❌ You must withdraw a positive amount!",
                ephemeral=True
            )
            return
        
        if withdraw_amount > bank:
            await interaction.response.send_message(
                f"❌ You don't have enough in your bank! You only have {format_currency(bank)}.",
                ephemeral=True
            )
            return
        
        # Update balances
        new_cash = cash + withdraw_amount
        new_bank = bank - withdraw_amount
        
        await self.bot.db.execute(
            "UPDATE users SET balance = ?, bank = ? WHERE user_id = ?",
            (new_cash, new_bank, interaction.user.id)
        )
        
        embed = discord.Embed(
            title="🏦 Withdrawal Successful",
            description=f"Withdrew {format_currency(withdraw_amount)} from your bank!",
            color=discord.Color.green()
        )
        
        embed.add_field(name="💵 Cash", value=format_currency(new_cash), inline=True)
        embed.add_field(name="🏦 Bank", value=format_currency(new_bank), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="transfer", description="Transfer money to another user")
    @app_commands.describe(
        user="The user to transfer money to",
        amount="Amount to transfer"
    )
    async def transfer(self, interaction: discord.Interaction, user: discord.User, amount: int):
        """Transfer money between users"""
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ You cannot transfer money to yourself!",
                ephemeral=True
            )
            return
        
        if user.bot:
            await interaction.response.send_message(
                "❌ You cannot transfer money to bots!",
                ephemeral=True
            )
            return
        
        # Get sender data
        sender_data = await self.bot.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        if not sender_data:
            await interaction.response.send_message(
                "❌ You need to register first! Use `/register`.",
                ephemeral=True
            )
            return
        
        # Get recipient data
        recipient_data = await self.bot.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (user.id,)
        )
        
        if not recipient_data:
            await interaction.response.send_message(
                f"❌ {user.mention} is not registered!",
                ephemeral=True
            )
            return
        
        if amount <= 0:
            await interaction.response.send_message(
                "❌ You must transfer a positive amount!",
                ephemeral=True
            )
            return
        
        sender_cash = sender_data.get('balance', 0)
        
        if amount > sender_cash:
            await interaction.response.send_message(
                f"❌ You don't have enough cash! You only have {format_currency(sender_cash)}.",
                ephemeral=True
            )
            return
        
        # Calculate tax (5%)
        tax_rate = float(os.getenv('SHOP_TAX_RATE', 0.05))
        tax = int(amount * tax_rate)
        amount_after_tax = amount - tax
        
        # Update balances
        new_sender_balance = sender_cash - amount
        new_recipient_balance = recipient_data['balance'] + amount_after_tax
        
        await self.bot.db.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (new_sender_balance, interaction.user.id)
        )
        
        await self.bot.db.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (new_recipient_balance, user.id)
        )
        
        # Log transaction
        await self.bot.db.execute(
            """
            INSERT INTO transactions (
                from_user_id, to_user_id, amount, tax, 
                transaction_type, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.user.id,
                user.id,
                amount,
                tax,
                'transfer',
                datetime.utcnow().isoformat()
            )
        )
        
        embed = discord.Embed(
            title="💸 Transfer Successful",
            description=f"Transferred {format_currency(amount)} to {user.mention}!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📊 Details",
            value=(
                f"**Amount Sent:** {format_currency(amount)}\n"
                f"**Tax ({format_percentage(tax_rate)}):** {format_currency(tax)}\n"
                f"**They Received:** {format_currency(amount_after_tax)}\n"
                f"**Your New Balance:** {format_currency(new_sender_balance)}"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Try to notify recipient
        try:
            dm_embed = discord.Embed(
                title="💰 You Received Money!",
                description=f"{interaction.user.mention} sent you {format_currency(amount_after_tax)}!",
                color=discord.Color.green()
            )
            await user.send(embed=dm_embed)
        except:
            pass  # User has DMs disabled
    
    @app_commands.command(name="stats", description="View your detailed statistics")
    async def stats(self, interaction: discord.Interaction):
        """View detailed user statistics"""
        user_data = await self.bot.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        if not user_data or not user_data.get("username"):
            await interaction.response.send_message(
                "❌ You need to register first! Use `/register`.",
                ephemeral=True
            )
            return
        
        # Get stats
        stats = await self.bot.db.fetch_one(
            "SELECT * FROM user_stats WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        color = int(user_data.get('favorite_color', '#3498db')[1:], 16)
        
        embed = discord.Embed(
            title=f"📊 {user_data['username']}'s Statistics",
            color=color
        )
        
        if stats:
            # Level and XP
            level = stats.get('level', 1)
            xp = stats.get('xp', 0)
            xp_needed = level * 100
            
            embed.add_field(
                name="🎯 Progression",
                value=(
                    f"**Level:** {level}\n"
                    f"**XP:** {xp}/{xp_needed}\n"
                    f"**Progress:** {format_percentage(xp / xp_needed)}"
                ),
                inline=True
            )
            
            # Vitals
            embed.add_field(
                name="❤️ Vitals",
                value=(
                    f"**Health:** {stats.get('health', 100)}/100\n"
                    f"**Energy:** {stats.get('energy', 100)}/100\n"
                    f"**Happiness:** {stats.get('happiness', 100)}/100"
                ),
                inline=True
            )
            
            # Additional stats
            embed.add_field(
                name="📈 Other Stats",
                value=(
                    f"**Strength:** {stats.get('strength', 0)}\n"
                    f"**Intelligence:** {stats.get('intelligence', 0)}\n"
                    f"**Charisma:** {stats.get('charisma', 0)}\n"
                    f"**Luck:** {stats.get('luck', 0)}"
                ),
                inline=True
            )
        
        # Economy stats
        cash = user_data.get('balance', 0)
        bank = user_data.get('bank', 0)
        
        embed.add_field(
            name="💰 Economy",
            value=(
                f"**Cash:** {format_currency(cash)}\n"
                f"**Bank:** {format_currency(bank)}\n"
                f"**Net Worth:** {format_currency(cash + bank)}"
            ),
            inline=True
        )
        
        # Activity stats
        created_at = datetime.fromisoformat(user_data.get('created_at', datetime.utcnow().isoformat()))
        days_active = (datetime.utcnow() - created_at).days
        
        embed.add_field(
            name="📅 Activity",
            value=(
                f"**Member Since:** {created_at.strftime('%Y-%m-%d')}\n"
                f"**Days Active:** {days_active}\n"
                f"**Daily Streak:** {user_data.get('daily_streak', 0)}"
            ),
            inline=True
        )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leaderboard", description="View the global leaderboards")
    @app_commands.describe(category="Category to view leaderboard for")
    @app_commands.choices(category=[
        app_commands.Choice(name="💰 Richest", value="balance"),
        app_commands.Choice(name="🏦 Bank", value="bank"),
        app_commands.Choice(name="💎 Net Worth", value="networth"),
        app_commands.Choice(name="🎯 Level", value="level"),
        app_commands.Choice(name="🔥 Daily Streak", value="streak"),
    ])
    async def leaderboard(self, interaction: discord.Interaction, category: str = "networth"):
        """View global leaderboards"""
        await interaction.response.defer()
        
        # Build query based on category
        if category == "balance":
            query = "SELECT user_id, username, balance as value FROM users ORDER BY balance DESC LIMIT 10"
            title = "💰 Richest Players"
            value_format = lambda x: format_currency(x)
        elif category == "bank":
            query = "SELECT user_id, username, bank as value FROM users ORDER BY bank DESC LIMIT 10"
            title = "🏦 Biggest Banks"
            value_format = lambda x: format_currency(x)
        elif category == "networth":
            query = "SELECT user_id, username, (balance + bank) as value FROM users ORDER BY value DESC LIMIT 10"
            title = "💎 Highest Net Worth"
            value_format = lambda x: format_currency(x)
        elif category == "level":
            query = """
                SELECT u.user_id, u.username, s.level as value 
                FROM users u 
                JOIN user_stats s ON u.user_id = s.user_id 
                ORDER BY s.level DESC, s.xp DESC 
                LIMIT 10
            """
            title = "🎯 Highest Levels"
            value_format = lambda x: f"Level {int(x)}"
        elif category == "streak":
            query = "SELECT user_id, username, daily_streak as value FROM users ORDER BY daily_streak DESC LIMIT 10"
            title = "🔥 Longest Daily Streaks"
            value_format = lambda x: f"{int(x)} days"
        else:
            await interaction.followup.send("❌ Invalid category!", ephemeral=True)
            return
        
        # Get leaderboard data
        leaders = await self.bot.db.fetch_all(query)
        
        if not leaders:
            await interaction.followup.send("❌ No data available for this leaderboard!")
            return
        
        # Create embed
        embed = discord.Embed(
            title=title,
            color=discord.Color.gold()
        )
        
        # Add entries
        medals = ["🥇", "🥈", "🥉"]
        leaderboard_text = ""
        
        user_rank = None
        for i, leader in enumerate(leaders, 1):
            medal = medals[i-1] if i <= 3 else f"`#{i}`"
            
            # Try to get user
            try:
                user = await self.bot.fetch_user(leader['user_id'])
                display_name = user.name
            except:
                display_name = leader['username']
            
            leaderboard_text += f"{medal} **{display_name}** - {value_format(leader['value'])}\n"
            
            if leader['user_id'] == interaction.user.id:
                user_rank = i
        
        embed.description = leaderboard_text
        
        # Show user's rank if not in top 10
        if not user_rank:
            user_data = await self.bot.db.fetch_one(
                "SELECT * FROM users WHERE user_id = ?",
                (interaction.user.id,)
            )
            if user_data:
                # Calculate user's rank
                if category == "balance":
                    rank_query = "SELECT COUNT(*) + 1 as rank FROM users WHERE balance > ?"
                    user_value = user_data['balance']
                elif category == "bank":
                    rank_query = "SELECT COUNT(*) + 1 as rank FROM users WHERE bank > ?"
                    user_value = user_data['bank']
                elif category == "networth":
                    rank_query = "SELECT COUNT(*) + 1 as rank FROM users WHERE (balance + bank) > ?"
                    user_value = user_data['balance'] + user_data['bank']
                elif category == "level":
                    stats = await self.bot.db.fetch_one(
                        "SELECT level FROM user_stats WHERE user_id = ?",
                        (interaction.user.id,)
                    )
                    rank_query = "SELECT COUNT(*) + 1 as rank FROM user_stats WHERE level > ?"
                    user_value = stats['level'] if stats else 1
                elif category == "streak":
                    rank_query = "SELECT COUNT(*) + 1 as rank FROM users WHERE daily_streak > ?"
                    user_value = user_data['daily_streak']
                
                rank_result = await self.bot.db.fetch_one(rank_query, (user_value,))
                user_rank = rank_result['rank'] if rank_result else 0
                
                embed.set_footer(
                    text=f"Your Rank: #{user_rank} | {value_format(user_value)}"
                )
        else:
            embed.set_footer(text=f"You're ranked #{user_rank}! Great job!")
        
        embed.timestamp = datetime.utcnow()
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        """Check bot latency"""
        latency = round(self.bot.latency * 1000)
        
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Bot Latency: **{latency}ms**",
            color=discord.Color.green() if latency < 100 else discord.Color.orange()
        )
        
        # Add status indicator
        if latency < 100:
            status = "🟢 Excellent"
        elif latency < 200:
            status = "🟡 Good"
        elif latency < 500:
            status = "🟠 Fair"
        else:
            status = "🔴 Poor"
        
        embed.add_field(name="Status", value=status, inline=True)
        
        # Add uptime
        uptime = datetime.utcnow() - self.bot.start_time
        embed.add_field(name="Uptime", value=format_time(int(uptime.total_seconds())), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="botinfo", description="View information about the bot")
    async def botinfo(self, interaction: discord.Interaction):
        """Display bot information"""
        embed = discord.Embed(
            title="🤖 LifeSimBot Information",
            description="A comprehensive life simulation bot with economy, businesses, jobs, and more!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📊 Statistics",
            value=(
                f"**Servers:** {len(self.bot.guilds)}\n"
                f"**Users:** {sum(g.member_count for g in self.bot.guilds)}\n"
                f"**Commands:** {len(self.bot.tree.get_commands())}"
            ),
            inline=True
        )
        
        # Calculate uptime
        uptime = datetime.utcnow() - self.bot.start_time
        embed.add_field(
            name="⏰ Uptime",
            value=format_time(int(uptime.total_seconds())),
            inline=True
        )
        
        embed.add_field(
            name="🔗 Links",
            value="[Invite](https://discord.com) | [Support](https://discord.com) | [Website](https://discord.com)",
            inline=True
        )
        
        embed.add_field(
            name="🎮 Features",
            value=(
                "✅ Economy System\n"
                "✅ Casino Games\n"
                "✅ Cryptocurrency\n"
                "✅ Businesses\n"
                "✅ Properties\n"
                "✅ Jobs & Skills\n"
                "✅ Pets & Cooking\n"
                "✅ Crime & Duels\n"
                "✅ Guilds & Families\n"
                "✅ Achievements & Quests"
            ),
            inline=False
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url if self.bot.user else None)
        embed.set_footer(text=f"Version 2.0.0 | Discord.py {discord.__version__}")
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Core(bot))
