# cogs/leaderboard_cog.py
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.format import format_number, money


class LeaderboardCog(commands.Cog):
    """Leaderboard commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="🏆 View the leaderboard")
    @app_commands.describe(leaderboard_type="Type of leaderboard to view")
    @app_commands.choices(leaderboard_type=[
        app_commands.Choice(name="💰 Richest (Balance)", value="balance"),
        app_commands.Choice(name="🏦 Bank Balance", value="bank"),
        app_commands.Choice(name="💎 Net Worth", value="net_worth"),
        app_commands.Choice(name="⭐ Highest Level", value="level"),
        app_commands.Choice(name="💼 Most Work Sessions", value="work"),
        app_commands.Choice(name="🔪 Most Crimes", value="crime"),
        app_commands.Choice(name="🎰 Biggest Gambler", value="casino"),
        app_commands.Choice(name="🌟 Most Famous", value="fame"),
        app_commands.Choice(name="⭐ Best Reputation", value="reputation"),
    ])
    async def leaderboard(self, interaction: discord.Interaction, leaderboard_type: str = "balance"):
        await interaction.response.defer()
        
        db = self.bot.db
        
        # Map types to fields and emojis
        type_map = {
            "balance": ("balance", "💰 Richest Players", money),
            "bank": ("bank", "🏦 Biggest Banks", money),
            "net_worth": ("net_worth", "💎 Highest Net Worth", money),
            "level": ("level", "⭐ Highest Levels", str),
            "work": ("total_work_count", "💼 Hardest Workers", lambda x: f"{format_number(x)} shifts"),
            "crime": ("crimes_committed", "🔪 Most Crimes", lambda x: f"{format_number(x)} crimes"),
            "casino": ("casino_total_bet", "🎰 Biggest Gamblers", lambda x: f"{money(x)} wagered"),
            "fame": ("fame", "🌟 Most Famous", str),
            "reputation": ("reputation", "⭐ Best Reputation", str),
        }
        
        if leaderboard_type not in type_map:
            leaderboard_type = "balance"
        
        field, title, formatter = type_map[leaderboard_type]
        
        # Get leaderboard data
        try:
            leaderboard_data = db.getleaderboard(field=field, limit=10)
        except:
            return await interaction.followup.send("❌ Error loading leaderboard!", ephemeral=True)
        
        if not leaderboard_data:
            return await interaction.followup.send("❌ No data available yet!", ephemeral=True)
        
        # Create embed
        embed = discord.Embed(
            title=f"🏆 {title}",
            description="Top 10 players",
            color=discord.Color.gold()
        )
        
        # Add leaderboard entries
        leaderboard_text = []
        for idx, (userid, value) in enumerate(leaderboard_data, 1):
            try:
                user = await self.bot.fetch_user(int(userid))
                username = user.display_name
            except:
                username = f"User {userid}"
            
            # Medal emojis for top 3
            if idx == 1:
                medal = "🥇"
            elif idx == 2:
                medal = "🥈"
            elif idx == 3:
                medal = "🥉"
            else:
                medal = f"`{idx}.`"
            
            formatted_value = formatter(value)
            leaderboard_text.append(f"{medal} **{username}** - {formatted_value}")
        
        embed.description = "\n".join(leaderboard_text)
        
        # Check user's rank
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        user_value = int(u.get(field, 0))
        
        if user_value > 0:
            # Find user's rank
            all_data = db.getleaderboard(field=field, limit=1000)
            user_rank = None
            for idx, (uid, _) in enumerate(all_data, 1):
                if uid == userid:
                    user_rank = idx
                    break
            
            if user_rank:
                embed.set_footer(text=f"Your rank: #{user_rank} with {formatter(user_value)}")
        
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
    