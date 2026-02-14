# cogs/hub_cog.py
"""
Modern Hub Cog - Simple, Clean Navigation
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import safe_defer
from views.modern_hub import ModernHub
from views.v2_embed import apply_v2_embed_layout


class HubCog(commands.Cog):
    """Modern hub dashboard with clean UI and intuitive navigation."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="hub", description="🏠 Open your dashboard")
    async def hub(self, interaction: discord.Interaction):
        """Open modern hub with all features."""
        await safe_defer(interaction)
        
        # Create modern hub view
        view = ModernHub(self.bot, interaction.user)
        
        # Get user data for initial page
        u = self.bot.db.getuser(str(interaction.user.id))
        
        from utils.format import money
        from views.modern_ui import Colors, create_progress_bar
        
        balance = int(u.get("balance", 0))
        level = int(u.get("level", 1))
        xp = int(u.get("xp", 0))
        xp_needed = level * 100
        
        # Create clean main hub embed
        embed = discord.Embed(
            title=f"🏠 Welcome, {interaction.user.name}!",
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
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="💡 Tip: Use /help to see all commands")
        
        apply_v2_embed_layout(view, embed=embed)
        view.message = await interaction.followup.send(view=view)
    
    @app_commands.command(name="dashboard", description="🏠 Alias for /hub")
    async def dashboard(self, interaction: discord.Interaction):
        """Alias for hub command."""
        await self.hub.callback(self, interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(HubCog(bot))
