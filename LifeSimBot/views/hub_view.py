# views/hub_views.py

from __future__ import annotations

import discord
from datetime import datetime, timezone

from utils.format import money, progress_bar, format_time
from utils.checks import check_cooldown
from utils.constants import *
import json
from views.v2_embed import apply_v2_embed_layout


def parse_json_field(data):
    """Parse JSON string fields."""
    if isinstance(data, dict):
        return data
    elif isinstance(data, str):
        try:
            return json.loads(data)
        except:
            return {}
    return {}


class HubView(discord.ui.LayoutView):
    """Advanced hub navigation with quick actions."""
    
    def __init__(self, bot, user: discord.User):
        super().__init__(timeout=600)
        self.bot = bot
        self.user = user
        self.page = "main"
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This isn't your hub!", ephemeral=True)
            return False
        return True
    
    def get_user_data(self):
        """Get user data."""
        userid = str(self.user.id)
        return self.bot.db.getuser(userid)
    
    def create_embed(self) -> discord.Embed:
        """Create embed based on current page."""
        u = self.get_user_data()
        
        pages = {
            "stats": self._stats_page,
            "economy": self._economy_page,
            "activities": self._activities_page,
            "cooldowns": self._cooldowns_page,
            "inventory": self._inventory_page
        }
        
        return pages.get(self.page, self._main_page)(u)
    
    def _main_page(self, u) -> discord.Embed:
        """Main overview with enhanced info."""
        level = int(u.get("level", 1))
        xp = int(u.get("xp", 0))
        xp_needed = level * 100
        balance = int(u.get("balance", 0))
        bank = int(u.get("bank", 0))
        bank_limit = int(u.get("bank_limit", STARTING_BANK_LIMIT))
        
        health = int(u.get("health", 100))
        energy = int(u.get("energy", 100))
        hunger = int(u.get("hunger", 100))
        
        # Status emoji
        health_emoji = "💚" if health > 70 else "💛" if health > 30 else "❤️"
        energy_emoji = "⚡" if energy > 50 else "🔋" if energy > 20 else "🪫"
        hunger_emoji = "🍗" if hunger > 60 else "🍔" if hunger > 30 else "🍕"
        
        # Job info
        job = u.get("job", "Unemployed")
        job_emoji = "💼" if job != "Unemployed" else "🚫"
        
        embed = discord.Embed(
            title=f"🏠 {self.user.display_name}'s Dashboard",
            description=f"**Level {level}** • {job_emoji} {job}",
            color=0x5865F2
        )
        
        # Progress section
        embed.add_field(
            name="⭐ Level Progress",
            value=f"{progress_bar(xp, xp_needed)}\n**{xp:,}** / **{xp_needed:,}** XP",
            inline=False
        )
        
        # Money section
        net_worth = balance + bank
        bank_pct = (bank / bank_limit * 100) if bank_limit > 0 else 0
        
        embed.add_field(
            name="💰 Finances",
            value=(
                f"💵 Cash: **{money(balance)}**\n"
                f"🏦 Bank: **{money(bank)}** ({bank_pct:.1f}% full)\n"
                f"💎 Net Worth: **{money(net_worth)}**"
            ),
            inline=True
        )
        
        # Status section
        embed.add_field(
            name="📊 Status",
            value=(
                f"{health_emoji} Health: **{health}%**\n"
                f"{energy_emoji} Energy: **{energy}%**\n"
                f"{hunger_emoji} Hunger: **{hunger}%**"
            ),
            inline=True
        )
        
        # Quick stats
        crimes = int(u.get("crimes_done", 0))
        jobs = int(u.get("jobs_done", 0))
        total_earned = int(u.get("total_earned", 0))
        
        embed.add_field(
            name="📈 Quick Stats",
            value=(
                f"💼 Jobs Completed: **{jobs:,}**\n"
                f"🔪 Crimes Done: **{crimes:,}**\n"
                f"💰 Total Earned: **{money(total_earned)}**"
            ),
            inline=False
        )
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        embed.set_footer(text="Navigate with buttons • Auto-updates")
        embed.timestamp = datetime.now(timezone.utc)
        
        return embed
    
    def _stats_page(self, u) -> discord.Embed:
        """Advanced stats with rankings."""
        level = int(u.get("level", 1))
        xp = int(u.get("xp", 0))
        
        # Skills
        strength = int(u.get("strength", 1))
        intelligence = int(u.get("intelligence", 1))
        charisma = int(u.get("charisma", 1))
        luck = int(u.get("luck", 1))
        
        # Calculate total skill level
        total_skills = strength + intelligence + charisma + luck
        
        # Lifetime stats
        total_earned = int(u.get("total_earned", 0))
        total_spent = int(u.get("total_spent", 0))
        crimes_done = int(u.get("crimes_done", 0))
        jobs_done = int(u.get("jobs_done", 0))
        
        # Additional stats
        items_bought = int(u.get("items_bought", 0))
        times_robbed = int(u.get("times_robbed", 0))
        successful_robs = int(u.get("successful_robs", 0))
        
        embed = discord.Embed(
            title=f"📊 {self.user.display_name}'s Stats",
            description=f"**Level {level}** • {xp:,} XP • {total_skills} Total Skill Points",
            color=0x3B82F6
        )
        
        # Skills with bars
        embed.add_field(
            name="💪 Skills",
            value=(
                f"💪 Strength: **{strength}** {progress_bar(strength, 100, length=10)}\n"
                f"🧠 Intelligence: **{intelligence}** {progress_bar(intelligence, 100, length=10)}\n"
                f"💬 Charisma: **{charisma}** {progress_bar(charisma, 100, length=10)}\n"
                f"🍀 Luck: **{luck}** {progress_bar(luck, 100, length=10)}"
            ),
            inline=False
        )
        
        # Economy stats
        embed.add_field(
            name="💰 Economic Stats",
            value=(
                f"💵 Total Earned: **{money(total_earned)}**\n"
                f"💸 Total Spent: **{money(total_spent)}**\n"
                f"📊 Net Profit: **{money(total_earned - total_spent)}**\n"
                f"🛒 Items Bought: **{items_bought:,}**"
            ),
            inline=True
        )
        
        # Activity stats
        embed.add_field(
            name="🎮 Activity Stats",
            value=(
                f"💼 Jobs Completed: **{jobs_done:,}**\n"
                f"🔪 Crimes Done: **{crimes_done:,}**\n"
                f"🎯 Successful Robs: **{successful_robs:,}**\n"
                f"😵 Times Robbed: **{times_robbed:,}**"
            ),
            inline=True
        )
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        embed.set_footer(text="Keep grinding to improve your stats!")
        
        return embed
    
    def _economy_page(self, u) -> discord.Embed:
        """Detailed economy overview."""
        balance = int(u.get("balance", 0))
        bank = int(u.get("bank", 0))
        bank_limit = int(u.get("bank_limit", STARTING_BANK_LIMIT))
        family_bank = int(u.get("family_bank", 0))
        
        # Crypto portfolio value
        crypto_portfolio = parse_json_field(u.get("crypto_portfolio", {}))
        crypto_value = 0
        # Would need price_simulator here to calculate, simplified for now
        
        # Total assets
        total_liquid = balance + bank + family_bank
        total_assets = total_liquid + crypto_value
        
        # Bank info
        bank_space = bank_limit - bank
        bank_pct = (bank / bank_limit * 100) if bank_limit > 0 else 0
        
        embed = discord.Embed(
            title="💰 Economy Overview",
            description=f"💎 Total Assets: **{money(total_assets)}**",
            color=0x22C55E
        )
        
        # Liquid assets
        embed.add_field(
            name="💵 Liquid Assets",
            value=(
                f"💵 Cash: **{money(balance)}**\n"
                f"🏦 Bank: **{money(bank)}**\n"
                f"👨‍👩‍👧 Family: **{money(family_bank)}**\n"
                f"━━━━━━━━━━\n"
                f"💧 Total Liquid: **{money(total_liquid)}**"
            ),
            inline=True
        )
        
        # Bank details
        embed.add_field(
            name="🏦 Bank Details",
            value=(
                f"📊 Stored: **{money(bank)}**\n"
                f"📈 Limit: **{money(bank_limit)}**\n"
                f"📉 Space: **{money(bank_space)}**\n"
                f"━━━━━━━━━━\n"
                f"🔋 Usage: **{bank_pct:.1f}%**"
            ),
            inline=True
        )
        
        # Bank space visual
        embed.add_field(
            name="📊 Bank Storage",
            value=progress_bar(bank, bank_limit),
            inline=False
        )
        
        # Investments (if any)
        if crypto_portfolio:
            embed.add_field(
                name="💎 Investments",
                value=f"📈 Crypto Holdings: **{len(crypto_portfolio)}** coins\nUse `/crypto portfolio` to view",
                inline=False
            )
        
        # Quick commands
        embed.add_field(
            name="💼 Quick Commands",
            value=(
                "**Earn:** `/work` `/crime` `/daily`\n"
                "**Manage:** `/deposit` `/withdraw` `/bankupgrade`\n"
                "**Spend:** `/shop` `/gamble` `/pay`"
            ),
            inline=False
        )
        
        embed.set_footer(text="Keep your money safe in the bank!")
        
        return embed
    
    def _activities_page(self, u) -> discord.Embed:
        """All available activities organized."""
        embed = discord.Embed(
            title="🎮 Available Activities",
            description="Everything you can do in Life Simulator!",
            color=0xF59E0B
        )
        
        embed.add_field(
            name="💼 Work & Income",
            value=(
                "• `/work` - Work your job\n"
                "• `/crime` - Commit crimes\n"
                "• `/rob @user` - Rob players\n"
                "• `/daily` - Daily reward\n"
                "• `/gamble <amt>` - Casino"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🛒 Shopping & Items",
            value=(
                "• `/shop` - Browse shop\n"
                "• `/buy <item>` - Buy items\n"
                "• `/inventory` - View items\n"
                "• `/use <item>` - Use items\n"
                "• `/eat <food>` - Eat food"
            ),
            inline=True
        )
        
        embed.add_field(
            name="💎 Crypto Trading",
            value=(
                "• `/crypto market` - View market\n"
                "• `/crypto buy` - Buy crypto\n"
                "• `/crypto sell` - Sell crypto\n"
                "• `/crypto portfolio` - Holdings"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🍳 Cooking & Farming",
            value=(
                "• `/cook` - Cook recipes\n"
                "• `/farm` - Farm ingredients\n"
                "• `/fish` - Go fishing\n"
                "• `/recipes` - View recipes"
            ),
            inline=True
        )
        
        embed.add_field(
            name="💰 Banking",
            value=(
                "• `/balance` - Check balance\n"
                "• `/deposit` - Store money\n"
                "• `/withdraw` - Take money\n"
                "• `/bankupgrade` - Upgrade bank\n"
                "• `/pay @user` - Send money"
            ),
            inline=True
        )
        
        embed.add_field(
            name="👤 Profile & Social",
            value=(
                "• `/profile` - View profile\n"
                "• `/leaderboard` - Top players\n"
                "• `/hub` - This dashboard"
            ),
            inline=True
        )
        
        embed.set_footer(text="Try them all and level up!")
        
        return embed
    
    def _cooldowns_page(self, u) -> discord.Embed:
        """Show all command cooldowns."""
        embed = discord.Embed(
            title="⏰ Cooldowns",
            description="Track when commands are available",
            color=0xA855F7
        )
        
        cooldowns = {
            "Work": ("last_work", WORK_COOLDOWN),
            "Crime": ("last_crime", CRIME_COOLDOWN),
            "Daily": ("last_daily", DAILY_COOLDOWN),
            "Rob": ("last_rob", ROB_COOLDOWN),
            "Farm": ("last_farm", getattr(self.bot, 'FARM_COOLDOWN', 3600)),
            "Fish": ("last_fish", getattr(self.bot, 'FISH_COOLDOWN', 1800)),
        }
        
        ready_commands = []
        waiting_commands = []
        
        for name, (last_key, cooldown_sec) in cooldowns.items():
            last_time = u.get(last_key)
            can_use, remaining = check_cooldown(last_time, cooldown_sec)
            
            if can_use:
                ready_commands.append(f"✅ **{name}** - Ready!")
            else:
                from utils.format import format_time
                waiting_commands.append(f"⏰ **{name}** - {format_time(remaining)}")
        
        if ready_commands:
            embed.add_field(
                name="✅ Ready to Use",
                value="\n".join(ready_commands),
                inline=False
            )
        
        if waiting_commands:
            embed.add_field(
                name="⏰ On Cooldown",
                value="\n".join(waiting_commands),
                inline=False
            )
        
        if not ready_commands and not waiting_commands:
            embed.description = "No cooldowns tracked yet. Start using commands!"
        
        embed.set_footer(text="Cooldowns refresh automatically")
        
        return embed
    
    def _inventory_page(self, u) -> discord.Embed:
        """Quick inventory overview."""
        inventory = parse_json_field(u.get("inventory", {}))
        
        embed = discord.Embed(
            title="🎒 Inventory Quick View",
            description=f"You have **{len(inventory)}** different items",
            color=0x8B5CF6
        )
        
        if not inventory:
            embed.description = "Your inventory is empty!\n\nVisit `/shop` to buy items."
            return embed
        
        # Count by category
        from views.shop_views import SHOP_ITEMS
        
        categories = {}
        for item_id, qty in inventory.items():
            if qty <= 0:
                continue
            
            item_data = SHOP_ITEMS.get(item_id)
            if item_data:
                cat = item_data.get("category", "other")
                if cat not in categories:
                    categories[cat] = 0
                categories[cat] += qty
        
        # Show top items
        sorted_inv = sorted(inventory.items(), key=lambda x: x[1], reverse=True)[:10]
        
        items_list = []
        for item_id, qty in sorted_inv:
            if qty <= 0:
                continue
            
            item_data = SHOP_ITEMS.get(item_id)
            if item_data:
                emoji = item_data.get("emoji", "📦")
                name = item_data["name"]
                items_list.append(f"{emoji} **{name}** x{qty}")
        
        if items_list:
            embed.add_field(
                name="📦 Top Items",
                value="\n".join(items_list[:10]),
                inline=False
            )
        
        # Category breakdown
        if categories:
            cat_text = "\n".join([f"• {cat.title()}: {count}" for cat, count in categories.items()])
            embed.add_field(
                name="📊 By Category",
                value=cat_text,
                inline=False
            )
        
        embed.set_footer(text="Use /inventory for full view")
        
        return embed
    
    # Row 0: Main navigation
    @discord.ui.button(label="Main", style=discord.ButtonStyle.primary, emoji="🏠", row=0)
    async def main_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = "main"
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Stats", style=discord.ButtonStyle.primary, emoji="📊", row=0)
    async def stats_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = "stats"
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Economy", style=discord.ButtonStyle.success, emoji="💰", row=0)
    async def economy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = "economy"
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Activities", style=discord.ButtonStyle.success, emoji="🎮", row=0)
    async def activities_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = "activities"
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)
    
    # Row 1: Extra pages
    @discord.ui.button(label="Cooldowns", style=discord.ButtonStyle.secondary, emoji="⏰", row=1)
    async def cooldowns_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = "cooldowns"
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Inventory", style=discord.ButtonStyle.secondary, emoji="🎒", row=1)
    async def inventory_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = "inventory"
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌", row=1)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👋 Dashboard Closed",
            description="Use `/hub` anytime to reopen your dashboard!",
            color=0x5865F2
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
