from __future__ import annotations

import random
import asyncio
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.format import money
from utils.checks import (
    safe_defer,
    safe_reply,
    check_in_hospital,
    check_in_jail,
    check_cooldown,
    check_user_stats,
)
from utils.constants import (
    ROB_COOLDOWN,
    ROB_ENERGY_COST,
    MIN_ROB_BALANCE,
    CRIME_COOLDOWN,
)
from views.crime_views import LockpickGame
from views.v2_embed import apply_v2_embed_layout


class CrimeCog(commands.Cog):
    """Crime commands: rob, steal, etc."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="mug", description="💰 Attempt to mug another user")
    @app_commands.describe(user="The user to mug")
    async def rob(self, interaction: discord.Interaction, user: discord.User):
        await safe_defer(interaction, ephemeral=False)

        db = self.bot.db
        attacker_id = str(interaction.user.id)
        victim_id = str(user.id)

        # Check 1: Can't rob yourself
        if attacker_id == victim_id:
            return await safe_reply(interaction, content="❌ You can't rob yourself! 🤦")

        # Check 2: Can't rob bots
        if user.bot:
            return await safe_reply(interaction, content="❌ You can't rob bots!")

        # Get users
        attacker = db.getuser(attacker_id)
        victim = db.getuser(victim_id)

        # Check 3: Hospital/Jail
        hospital_msg = check_in_hospital(attacker)
        if hospital_msg:
            return await safe_reply(interaction, content=hospital_msg)

        jail_msg = check_in_jail(attacker)
        if jail_msg:
            return await safe_reply(interaction, content=jail_msg)

        # Check 4: Energy
        issues = check_user_stats(attacker, energy_needed=ROB_ENERGY_COST)
        if issues:
            embed = discord.Embed(
                title="❌ Can't Rob",
                description="\n".join(issues),
                color=discord.Color.red(),
            )
            return await safe_reply(interaction, embed=embed)

        # Check 5: Cooldown
        last_rob = attacker.get("last_rob")
        can_rob, remaining = check_cooldown(last_rob, ROB_COOLDOWN)

        if not can_rob:
            from utils.format import format_time

            embed = discord.Embed(
                title="⏰ Robbery Cooldown",
                description=f"{interaction.user.mention}, wait **{format_time(remaining)}** before robbing again!",
                color=discord.Color.orange(),
            )
            return await safe_reply(interaction, embed=embed)

        # Check 6: Victim must have enough money
        victim_balance = int(victim.get("balance", 0))
        if victim_balance < MIN_ROB_BALANCE:
            return await safe_reply(
                interaction,
                content=f"❌ {user.mention} is too broke to rob! (Needs at least {money(MIN_ROB_BALANCE)})",
            )

        # Calculate steal amount (10-25% of victim balance)
        steal_percent = random.uniform(0.10, 0.25)
        potential_steal = int(victim_balance * steal_percent)

        # Get difficulty based on victim level
        victim_level = int(victim.get("level", 1))
        difficulty = min(3 + (victim_level // 10), 6)  # 3-6 digits

        # Create lockpick minigame
        game = LockpickGame(interaction.user, user, potential_steal, difficulty)
        game.start_time = asyncio.get_event_loop().time()

        # Send game
        apply_v2_embed_layout(game, embed=game.create_game_embed())
        await interaction.followup.send(view=game)

        # Drain energy immediately
        db.updatestat(
            attacker_id,
            "energy",
            int(attacker.get("energy", 100)) - ROB_ENERGY_COST,
        )

        # Wait for game to complete
        await game.wait()

        # Update cooldown
        db.updatestat(attacker_id, "last_rob", datetime.now(timezone.utc).isoformat())

        # Process results
        if game.success:
            # Successful robbery
            db.addbalance(attacker_id, potential_steal)
            db.removebalance(victim_id, potential_steal)

            # Add to stats
            db.increment_stat(attacker_id, "robberies_success")
            db.increment_stat(victim_id, "times_robbed")

        elif game.failed:
            # Failed robbery - pay fine
            fine = potential_steal // 2

            # Make sure attacker has enough
            attacker_balance = int(attacker.get("balance", 0))
            actual_fine = min(fine, attacker_balance)

            if actual_fine > 0:
                db.removebalance(attacker_id, actual_fine)

            # Add to stats
            db.increment_stat(attacker_id, "robberies_failed")

    @app_commands.command(name="crime", description="🎰 Commit a random crime for money")
    async def crime(self, interaction: discord.Interaction):
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        # Check hospital/jail
        hospital_msg = check_in_hospital(u)
        if hospital_msg:
            return await safe_reply(interaction, content=hospital_msg)

        jail_msg = check_in_jail(u)
        if jail_msg:
            return await safe_reply(interaction, content=jail_msg)

        # Check cooldown using CRIME_COOLDOWN from constants
        last_crime = u.get("last_crime")
        can_crime, remaining = check_cooldown(last_crime, CRIME_COOLDOWN)

        if not can_crime:
            from utils.format import format_time

            embed = discord.Embed(
                title="⏰ Crime Cooldown",
                description=f"Wait **{format_time(remaining)}** before committing another crime!",
                color=discord.Color.orange(),
            )
            return await safe_reply(interaction, embed=embed)

        # Crime scenarios
        crimes = [
            {
                "name": "shoplifting",
                "success_msg": "stole some snacks from a convenience store",
                "reward": (50, 200),
            },
            {
                "name": "pickpocket",
                "success_msg": "pickpocketed a tourist",
                "reward": (100, 400),
            },
            {
                "name": "graffiti",
                "success_msg": "got paid to do street art",
                "reward": (150, 350),
            },
            {
                "name": "scalping",
                "success_msg": "scalped concert tickets",
                "reward": (200, 600),
            },
            {
                "name": "hacking",
                "success_msg": "hacked someone's crypto wallet",
                "reward": (500, 1500),
            },
            {
                "name": "heist",
                "success_msg": "pulled off a small bank heist",
                "reward": (1000, 3000),
            },
        ]

        # Success rate based on user level
        user_level = int(u.get("level", 1))
        success_rate = min(0.60 + (user_level * 0.01), 0.85)  # 60-85%

        crime = random.choice(crimes)
        success = random.random() < success_rate

        # Update cooldown
        db.updatestat(userid, "last_crime", datetime.now(timezone.utc).isoformat())

        if success:
            # Success
            reward = random.randint(*crime["reward"])
            db.addbalance(userid, reward)

            embed = discord.Embed(
                title="✅ Crime Successful!",
                description=f"{interaction.user.mention} {crime['success_msg']}!\n\n💰 **+{money(reward)}**",
                color=discord.Color.green(),
            )
            db.increment_stat(userid, "crimes_success")
        else:
            # Caught - lose money or go to jail
            if random.random() < 0.5:
                # Fine
                fine = random.randint(100, 500)
                balance = int(u.get("balance", 0))
                actual_fine = min(fine, balance)

                if actual_fine > 0:
                    db.removebalance(userid, actual_fine)

                embed = discord.Embed(
                    title="❌ Caught!",
                    description=f"{interaction.user.mention} got caught {crime['name']}!\n\n💸 **Fine: {money(actual_fine)}**",
                    color=discord.Color.red(),
                )
            else:
                # Jail
                jail_time = random.randint(300, 900)  # 5-15 minutes
                jail_until = datetime.now(timezone.utc).timestamp() + jail_time
                db.updatestat(userid, "jail_until", jail_until)

                from utils.format import format_time

                embed = discord.Embed(
                    title="🚔 Arrested!",
                    description=f"{interaction.user.mention} got arrested for {crime['name']}!\n\n⏰ **Jail Time: {format_time(jail_time)}**",
                    color=discord.Color.dark_red(),
                )

            db.increment_stat(userid, "crimes_failed")

        await safe_reply(interaction, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CrimeCog(bot))
