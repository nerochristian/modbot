# cogs/businesses_cog.py
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

from data.businesses import BUSINESS_TYPES, calculate_business_revenue, calculate_upgrade_cost
from utils.format import money, progress_bar
from utils.checks import safe_defer, safe_reply


class BusinessesCog(commands.Cog):
    """Business ownership and passive income."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="businesses", description="🏢 View your businesses")
    async def businesses(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        
        businesses = db.get_user_businesses(userid)
        
        if not businesses:
            embed = discord.Embed(
                title="🏢 Your Businesses",
                description="You don't own any businesses yet.\n\nUse `/buybusiness` to purchase one.",
                color=discord.Color.blue()
            )
            return await safe_reply(interaction, embed=embed)
        
        embed = discord.Embed(
            title=f"🏢 {interaction.user.display_name}'s Businesses",
            color=discord.Color.blue()
        )
        
        total_revenue = 0
        
        for biz in businesses:
            biz_type = BUSINESS_TYPES.get(biz["business_type"], {})
            emoji = biz_type.get("emoji", "🏢")
            
            level = int(biz.get("level", 1))
            revenue = calculate_business_revenue(biz)
            total_revenue += revenue
            
            last_collected = biz.get("last_collected")
            if last_collected:
                try:
                    last_time = datetime.fromisoformat(last_collected)
                    hours_passed = (datetime.now(timezone.utc) - last_time).total_seconds() / 3600
                    hours_passed = min(24, max(0, hours_passed))
                    uncollected = int(revenue * hours_passed)
                except:
                    uncollected = 0
            else:
                uncollected = 0
            
            upgrade_cost = calculate_upgrade_cost(biz)
            upgrade_text = f"Upgrade: {money(upgrade_cost)}" if upgrade_cost > 0 else "Max level reached"
            
            embed.add_field(
                name=f"{emoji} {biz['name']} (Lv{level})",
                value=(
                    f"**Type:** {biz_type.get('name', biz['business_type'])}\n"
                    f"**Revenue:** {money(revenue)}/hour\n"
                    f"**Uncollected:** {money(uncollected)}\n"
                    f"**{upgrade_text}**"
                ),
                inline=False
            )
        
        embed.set_footer(text=f"Total passive income: {money(total_revenue)}/hour")
        
        await safe_reply(interaction, embed=embed)
    
    @app_commands.command(name="buybusiness", description="🛒 Buy a new business")
    @app_commands.choices(business=[
        app_commands.Choice(name="🍋 Lemonade Stand", value="lemonade_stand"),
        app_commands.Choice(name="🚚 Food Truck", value="food_truck"),
        app_commands.Choice(name="🏪 Convenience Store", value="convenience_store"),
        app_commands.Choice(name="🎵 Nightclub", value="nightclub"),
        app_commands.Choice(name="💻 Tech Startup", value="tech_startup"),
    ])
    async def buybusiness(self, interaction: discord.Interaction, business: str):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        
        biz_type = BUSINESS_TYPES.get(business)
        if not biz_type:
            return await safe_reply(interaction, content="❌ Invalid business type!")
        
        # Limit number of businesses
        current = db.get_user_businesses(userid)
        if len(current) >= 5:
            return await safe_reply(interaction, content="❌ You already own 5 businesses! (Max limit)")
        
        cost = biz_type["base_cost"]
        balance = int(u.get("balance", 0))
        
        if balance < cost:
            return await safe_reply(
                interaction,
                content=f"❌ You need {money(cost)}, but you only have {money(balance)}"
            )
        
        # Remove money, create business
        db.removebalance(userid, cost)
        biz_id = db.create_business(userid, business, biz_type["name"], biz_type["base_revenue"])
        
        embed = discord.Embed(
            title="🏢 New Business Purchased!",
            description=f"You bought **{biz_type['name']}** for {money(cost)}",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Details",
            value=(
                f"**ID:** `{biz_id}`\n"
                f"**Revenue:** {money(biz_type['base_revenue'])}/hour\n"
                f"**Risk:** {biz_type['risk'].title()}"
            ),
            inline=False
        )
        
        embed.set_footer(text="Your business will now generate hourly passive income.")
        
        await safe_reply(interaction, embed=embed)
    
    @app_commands.command(name="upgradebusiness", description="⬆️ Upgrade one of your businesses")
    @app_commands.describe(business_id="ID of the business to upgrade")
    async def upgradebusiness(self, interaction: discord.Interaction, business_id: str):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        
        businesses = db.get_user_businesses(userid)
        biz = next((b for b in businesses if b["business_id"] == business_id), None)
        
        if not biz:
            return await safe_reply(interaction, content="❌ You don't own a business with that ID!")
        
        biz_type = BUSINESS_TYPES.get(biz["business_type"])
        if not biz_type:
            return await safe_reply(interaction, content="❌ This business type is no longer valid.")
        
        level = int(biz.get("level", 1))
        max_level = biz_type["max_level"]
        
        if level >= max_level:
            return await safe_reply(interaction, content="❌ This business is already at max level!")
        
        cost = calculate_upgrade_cost(biz)
        
        u = db.getuser(userid)
        balance = int(u.get("balance", 0))
        
        if balance < cost:
            return await safe_reply(
                interaction,
                content=f"❌ You need {money(cost)} to upgrade, but you only have {money(balance)}"
            )
        
        # Pay and upgrade
        db.removebalance(userid, cost)
        db.updatebusiness(business_id, "level", level + 1)
        
        # Update revenue_per_hour in DB so background task uses correct value
        new_revenue = calculate_business_revenue({**biz, "level": level + 1})
        db.updatebusiness(business_id, "revenue_per_hour", new_revenue)
        
        embed = discord.Embed(
            title="⬆️ Business Upgraded!",
            description=f"**{biz_type['name']}** is now level **{level + 1}**!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="New Stats",
            value=(
                f"**Revenue:** {money(new_revenue)}/hour\n"
                f"**Upgrade Cost Paid:** {money(cost)}"
            ),
            inline=False
        )
        
        await safe_reply(interaction, embed=embed)
    
    @app_commands.command(name="collectbusiness", description="💰 Collect unclaimed business income")
    async def collectbusiness(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        
        businesses = db.get_user_businesses(userid)
        
        if not businesses:
            return await safe_reply(interaction, content="❌ You don't own any businesses!")
        
        total_collected = 0
        
        now = datetime.now(timezone.utc)
        
        for biz in businesses:
            revenue = calculate_business_revenue(biz)
            
            last_collected = biz.get("last_collected")
            if last_collected:
                try:
                    last_time = datetime.fromisoformat(last_collected)
                except:
                    last_time = now
            else:
                last_time = now
            
            hours_passed = (now - last_time).total_seconds() / 3600
            hours_passed = min(24, max(0, hours_passed))
            
            income = int(revenue * hours_passed)
            
            if income > 0:
                db.addbalance(userid, income)
                db.updatebusiness(biz["business_id"], "last_collected", now.isoformat())
                total_collected += income
        
        if total_collected == 0:
            return await safe_reply(
                interaction,
                content="⏰ No income to collect yet. Try again later!"
            )
        
        embed = discord.Embed(
            title="💰 Business Income Collected",
            description=f"You collected **{money(total_collected)}** from your businesses.",
            color=discord.Color.green()
        )
        
        await safe_reply(interaction, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(BusinessesCog(bot))
