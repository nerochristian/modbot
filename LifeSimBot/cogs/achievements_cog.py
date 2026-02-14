# cogs/achievements_cog.py
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
import json
from typing import Optional, Dict, List

from data.achievements import ACHIEVEMENTS, ACHIEVEMENT_TIERS
from services.achievements_service import (
    get_unlocked_achievements,
    check_all_achievements,
    calculate_achievement_progress,
    group_achievements_by_category
)
from utils.format import money
from utils.checks import safe_defer, safe_reply
from views.v2_embed import apply_v2_embed_layout


# ============= ACHIEVEMENT VIEWS =============

class AchievementView(discord.ui.LayoutView):
    """Main achievement browsing view with pagination and filtering."""
    
    def __init__(self, bot, user: discord.User, category: str = "all"):
        super().__init__(timeout=180)
        self.bot = bot
        self.user = user
        self.category = category
        self.page = 0
        
        # Add category selector
        self.add_item(CategorySelect(self.get_categories()))
    
    def get_categories(self) -> List[str]:
        """Get all achievement categories."""
        categories = set()
        for ach_data in ACHIEVEMENTS.values():
            categories.add(ach_data.get("category", "other"))
        return sorted(list(categories))
    
    def create_embed(self) -> discord.Embed:
        """Create achievement list embed."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        
        unlocked = get_unlocked_achievements(u)
        progress = calculate_achievement_progress(u)
        
        # Filter achievements
        filtered_achievements = []
        for ach_id, ach_data in ACHIEVEMENTS.items():
            if self.category == "all" or ach_data.get("category") == self.category:
                filtered_achievements.append((ach_id, ach_data))
        
        # Paginate
        per_page = 5
        total_pages = max(1, (len(filtered_achievements) + per_page - 1) // per_page)
        self.page = max(0, min(self.page, total_pages - 1))
        
        start = self.page * per_page
        end = start + per_page
        page_achievements = filtered_achievements[start:end]
        
        # Create embed
        embed = discord.Embed(
            title=f"🏆 {self.user.display_name}'s Achievements",
            description=(
                f"**Progress:** {progress['unlocked']}/{progress['total']} "
                f"({progress['percentage']}%)\n"
                f"**Category:** {self.category.title()}"
            ),
            color=discord.Color.gold()
        )
        
        # Add achievements
        for ach_id, ach_data in page_achievements:
            is_unlocked = ach_id in unlocked
            tier = ACHIEVEMENT_TIERS.get(ach_data["tier"], {"emoji": "🏆"})
            status = tier["emoji"] if is_unlocked else "🔒"
            
            reward_parts = []
            if ach_data["reward"].get("money"):
                reward_parts.append(f"💰 {money(ach_data['reward']['money'])}")
            if ach_data["reward"].get("xp"):
                reward_parts.append(f"⭐ {ach_data['reward']['xp']} XP")
            
            reward_text = " • ".join(reward_parts) if reward_parts else "No reward"
            
            embed.add_field(
                name=f"{status} {ach_data['emoji']} {ach_data['name']}",
                value=f"{ach_data['description']}\n**Reward:** {reward_text}",
                inline=False
            )
        
        if not page_achievements:
            embed.description += "\n\n*No achievements in this category*"
        
        embed.set_footer(text=f"Page {self.page + 1}/{total_pages} • Use /checkachievements to claim rewards")
        
        return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This isn't your achievement list!",
                ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, emoji="◀️", row=1)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        embed = self.create_embed()
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, emoji="▶️", row=1)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        embed = self.create_embed()
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Check New", style=discord.ButtonStyle.success, emoji="🔍", row=1)
    async def check_new(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Quick check for new achievements."""
        await interaction.response.defer()
        
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        
        newly_unlocked = check_all_achievements(u)
        
        if not newly_unlocked:
            await interaction.followup.send(
                "🔍 No new achievements unlocked. Keep playing!",
                ephemeral=True
            )
            return
        
        # Show claim view
        view = ClaimAchievementsView(self.bot, self.user, newly_unlocked)
        embed = view.create_embed()
        apply_v2_embed_layout(view, embed=embed)
        await interaction.followup.send(view=view, ephemeral=True)


class CategorySelect(discord.ui.Select):
    """Dropdown for filtering achievements by category."""
    
    def __init__(self, categories: List[str]):
        category_emojis = {
            "all": "🏆",
            "economy": "💰",
            "work": "💼",
            "level": "⭐",
            "family": "👨‍👩‍👧",
            "pets": "🐾",
            "gambling": "🎰",
            "crime": "🔪",
            "property": "🏠",
            "business": "🏢",
            "social": "👥",
            "other": "📦"
        }
        
        options = [
            discord.SelectOption(
                label="All Achievements",
                value="all",
                emoji="🏆",
                description="Show all achievements"
            )
        ]
        
        for cat in categories:
            options.append(
                discord.SelectOption(
                    label=cat.title(),
                    value=cat,
                    emoji=category_emojis.get(cat, "📦"),
                    description=f"Filter by {cat} achievements"
                )
            )
        
        super().__init__(
            placeholder="Select a category...",
            options=options[:25],  # Discord limit
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        view: AchievementView = self.view
        view.category = self.values[0]
        view.page = 0  # Reset to first page
        embed = view.create_embed()
        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.edit_message(view=view)


class ClaimAchievementsView(discord.ui.LayoutView):
    """View for claiming newly unlocked achievements."""
    
    def __init__(self, bot, user: discord.User, achievement_ids: List[str]):
        super().__init__(timeout=120)
        self.bot = bot
        self.user = user
        self.achievement_ids = achievement_ids
        self.claimed = False
    
    def create_embed(self) -> discord.Embed:
        """Create claim embed."""
        total_money = 0
        total_xp = 0
        
        for ach_id in self.achievement_ids:
            ach = ACHIEVEMENTS.get(ach_id)
            if ach:
                total_money += ach["reward"].get("money", 0)
                total_xp += ach["reward"].get("xp", 0)
        
        embed = discord.Embed(
            title="🎉 New Achievements Unlocked!",
            description=(
                f"**Achievements:** {len(self.achievement_ids)}\n"
                f"**Total Rewards:**\n"
                f"💰 {money(total_money)}\n"
                f"⭐ {total_xp} XP"
            ),
            color=discord.Color.gold()
        )
        
        for ach_id in self.achievement_ids[:10]:
            ach = ACHIEVEMENTS.get(ach_id)
            if not ach:
                continue
                
            tier = ACHIEVEMENT_TIERS.get(ach["tier"], {"emoji": "🏆"})
            
            reward_parts = []
            if ach["reward"].get("money"):
                reward_parts.append(f"💰 {money(ach['reward']['money'])}")
            if ach["reward"].get("xp"):
                reward_parts.append(f"⭐ {ach['reward']['xp']} XP")
            
            embed.add_field(
                name=f"{tier['emoji']} {ach['emoji']} {ach['name']}",
                value=f"{ach['description']}\n{' • '.join(reward_parts)}",
                inline=False
            )
        
        if len(self.achievement_ids) > 10:
            embed.set_footer(text=f"+{len(self.achievement_ids) - 10} more achievements!")
        else:
            embed.set_footer(text="Click the button below to claim your rewards!")
        
        return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ These aren't your achievements!",
                ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(label="Claim Rewards", style=discord.ButtonStyle.success, emoji="🎁")
    async def claim_rewards(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.claimed:
            return await interaction.response.send_message(
                "❌ You already claimed these rewards!",
                ephemeral=True
            )
        
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        
        # Update achievements
        unlocked = get_unlocked_achievements(u)
        unlocked.extend(self.achievement_ids)
        db.updatestat(userid, "achievements", json.dumps(unlocked))
        
        # Calculate and give rewards
        total_money = 0
        total_xp = 0
        
        for ach_id in self.achievement_ids:
            ach = ACHIEVEMENTS.get(ach_id)
            if ach:
                total_money += ach["reward"].get("money", 0)
                total_xp += ach["reward"].get("xp", 0)
        
        if total_money > 0:
            db.addbalance(userid, total_money)
        if total_xp > 0:
            db.addxp(userid, total_xp)
        
        self.claimed = True
        
        # Update embed
        embed = discord.Embed(
            title="✅ Rewards Claimed!",
            description=(
                f"**You received:**\n"
                f"💰 {money(total_money)}\n"
                f"⭐ {total_xp} XP\n\n"
                f"*{len(self.achievement_ids)} achievements added to your profile*"
            ),
            color=discord.Color.green()
        )
        
        # Disable button
        button.disabled = True
        button.label = "Claimed!"
        button.style = discord.ButtonStyle.secondary
        
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
        self.stop()
    
    @discord.ui.button(label="View All", style=discord.ButtonStyle.secondary, emoji="🏆")
    async def view_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View all achievements."""
        view = AchievementView(self.bot, self.user)
        embed = view.create_embed()
        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.send_message(view=view, ephemeral=True)


# ============= MAIN COG =============

class AchievementsCog(commands.Cog):
    """Achievement tracking and rewards."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="achievements", description="🏆 View your achievements")
    @app_commands.describe(category="Filter by category")
    async def achievements(self, interaction: discord.Interaction, category: Optional[str] = "all"):
        """View achievements with interactive filtering and pagination."""
        await safe_defer(interaction)
        
        view = AchievementView(self.bot, interaction.user, category)
        embed = view.create_embed()
        
        apply_v2_embed_layout(view, embed=embed)
        await safe_reply(interaction, view=view)
    
    @app_commands.command(name="checkachievements", description="🔍 Check for newly unlocked achievements")
    async def checkachievements(self, interaction: discord.Interaction):
        """Check and claim newly unlocked achievements."""
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        
        # Check for new achievements
        newly_unlocked = check_all_achievements(u)
        
        if not newly_unlocked:
            embed = discord.Embed(
                title="🔍 No New Achievements",
                description=(
                    "Keep playing to unlock more achievements!\n\n"
                    "**Tip:** Use `/achievements` to see all available achievements."
                ),
                color=discord.Color.blue()
            )
            return await safe_reply(interaction, embed=embed)
        
        # Show claim view
        view = ClaimAchievementsView(self.bot, interaction.user, newly_unlocked)
        embed = view.create_embed()
        
        apply_v2_embed_layout(view, embed=embed)
        await safe_reply(interaction, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(AchievementsCog(bot))
