# cogs/lifecycle_cog.py

from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.format import format_number, progress_bar, format_time
from utils.checks import safe_defer, safe_reply, check_cooldown
from utils.constants import (
    SLEEP_COOLDOWN,
    MAX_HEALTH,
    MAX_ENERGY,
    MAX_HAPPINESS,
    MAX_HUNGER,
)


class LifecycleCog(commands.Cog):
    """Life management commands: sleep."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sleep", description="😴 Sleep to restore health, energy, and hunger")
    async def sleep(self, interaction: discord.Interaction):
        """Sleep to restore stats."""
        await safe_defer(interaction, ephemeral=True)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        # Check cooldown
        last_sleep = u.get("last_sleep")
        can_sleep, remaining = check_cooldown(last_sleep, SLEEP_COOLDOWN)

        if not can_sleep:
            embed = discord.Embed(
                title="⏰ Not Tired Yet",
                description=(
                    f"You already slept recently!\n\n"
                    f"You can sleep again in **{format_time(remaining)}**"
                ),
                color=discord.Color.orange(),
            )
            return await safe_reply(interaction, embed=embed, ephemeral=True)

        # Get current stats
        health = int(u.get("health", MAX_HEALTH))
        energy = int(u.get("energy", MAX_ENERGY))
        hunger = int(u.get("hunger", MAX_HUNGER))
        happiness = int(u.get("happiness", MAX_HAPPINESS))

        # Calculate restoration amounts
        health_restore = min(MAX_HEALTH - health, 10)  # Small health boost
        energy_restore = energy_restore = MAX_ENERGY - energy  # Full energy restore
        hunger_restore = MAX_HUNGER - hunger  # Full hunger restore

        # New values after sleep
        new_health = min(MAX_HEALTH, health + health_restore)
        new_energy = MAX_ENERGY  # Always restore to full
        new_hunger = MAX_HUNGER  # Always restore to full

        # Update database
        db.updatestats(
            userid,
            health=new_health,
            energy=new_energy,
            hunger=new_hunger,
        )
        
        # Update last sleep time (timezone-aware)
        db.updatelastsleep(userid, datetime.now(timezone.utc).isoformat())

        # Create success embed
        embed = discord.Embed(
            title="😴 Good Sleep!",
            description="You had a restful sleep and feel refreshed!",
            color=discord.Color.green(),
        )

        # Health field
        embed.add_field(
            name="❤️ Health",
            value=f"+{health_restore}\n{progress_bar(new_health, MAX_HEALTH)}",
            inline=True,
        )

        # Energy field
        embed.add_field(
            name="⚡ Energy",
            value=f"+{energy_restore}\n{progress_bar(new_energy, MAX_ENERGY)}",
            inline=True,
        )

        # Hunger field
        embed.add_field(
            name="🍔 Hunger",
            value=f"+{hunger_restore}\n{progress_bar(new_hunger, MAX_HUNGER)}",
            inline=True,
        )

        # Footer with cooldown info
        hours = SLEEP_COOLDOWN // 3600
        embed.set_footer(
            text=f"Sleep restores health, energy, and hunger • Cooldown: {hours} hours"
        )

        await safe_reply(interaction, embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(LifecycleCog(bot))
