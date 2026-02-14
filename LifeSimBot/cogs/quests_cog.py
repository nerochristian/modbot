from __future__ import annotations

import json
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from data.quests import DAILY_QUESTS, WEEKLY_QUESTS, QUEST_DIFFICULTIES
from services.quests_service import (
    get_active_quests,
    get_completed_today,
    generate_daily_quests,
    generate_weekly_quests,
    should_reset_daily_quests,
    calculate_quest_progress_percent,
)
from utils.format import money, progress_bar
from utils.checks import safe_defer, safe_reply


class QuestsCog(commands.Cog):
    """Daily and weekly quest system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="quests", description="📜 View your active quests")
    async def quests(self, interaction: discord.Interaction):
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        # Check if should reset daily quests
        if should_reset_daily_quests(u):
            new_quests = generate_daily_quests(3)
            db.updatestat(userid, "active_daily_quests", json.dumps(new_quests))
            db.updatestat(userid, "completed_quests_today", json.dumps([]))
            db.updatestat(userid, "last_daily", datetime.now(timezone.utc).isoformat())
            u = db.getuser(userid)

        active_quests = get_active_quests(u)
        completed_today = get_completed_today(u)

        if not active_quests:
            new_quests = generate_daily_quests(3)
            db.updatestat(userid, "active_daily_quests", json.dumps(new_quests))
            active_quests = new_quests

        embed = discord.Embed(
            title=f"📜 {interaction.user.display_name}'s Quests",
            description=(
                f"**Completed Today:** {len(completed_today)}\n"
                f"**Total Completed:** {int(u.get('total_quests_completed', 0))}"
            ),
            color=discord.Color.blue(),
        )

        # Show active quests
        for quest in active_quests:
            quest_id = quest["id"]

            if quest_id in completed_today:
                status = "✅ Completed"
            else:
                progress = quest.get("progress", 0)
                required = quest["requirement"]["value"]
                percent = calculate_quest_progress_percent(quest)

                status = f"{progress_bar(progress, required, length=8)} {progress}/{required} ({percent}%)"

            difficulty = QUEST_DIFFICULTIES.get(
                quest.get("difficulty", "easy"),
                {"emoji": "⚪"},
            )

            reward_parts = []
            if quest["reward"].get("money"):
                reward_parts.append(f"💰 {money(quest['reward']['money'])}")
            if quest["reward"].get("xp"):
                reward_parts.append(f"⭐ {quest['reward']['xp']} XP")

            embed.add_field(
                name=f"{difficulty['emoji']} {quest['emoji']} {quest['name']}",
                value=(
                    f"{quest['description']}\n"
                    f"**Progress:** {status}\n"
                    f"**Reward:** {' + '.join(reward_parts)}"
                ),
                inline=False,
            )

        embed.set_footer(text="Complete quests to earn rewards! Resets daily at midnight UTC.")

        await safe_reply(interaction, embed=embed)

    @app_commands.command(name="claimquest", description="🎁 Claim completed quest rewards")
    @app_commands.describe(quest_number="Quest number to claim (1-3)")
    async def claimquest(self, interaction: discord.Interaction, quest_number: int):
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        active_quests = get_active_quests(u)
        completed_today = get_completed_today(u)

        if quest_number < 1 or quest_number > len(active_quests):
            return await safe_reply(
                interaction,
                content=f"❌ Invalid quest number! Use 1-{len(active_quests)}",
            )

        quest = active_quests[quest_number - 1]
        quest_id = quest["id"]

        if quest_id in completed_today:
            return await safe_reply(
                interaction,
                content="❌ You already claimed this quest today!",
            )

        progress = quest.get("progress", 0)
        required = quest["requirement"]["value"]

        if progress < required:
            return await safe_reply(
                interaction,
                content=f"❌ Quest not completed yet! Progress: {progress}/{required}",
            )

        # Give rewards
        reward_money = quest["reward"].get("money", 0)
        reward_xp = quest["reward"].get("xp", 0)

        if reward_money > 0:
            db.addbalance(userid, reward_money)
        if reward_xp > 0:
            db.addxp(userid, reward_xp)

        # Mark as completed
        completed_today.append(quest_id)
        db.updatestat(userid, "completed_quests_today", json.dumps(completed_today))

        # Increment total completed
        total = int(u.get("total_quests_completed", 0))
        db.updatestat(userid, "total_quests_completed", total + 1)

        difficulty = QUEST_DIFFICULTIES.get(
            quest.get("difficulty", "easy"),
            {"emoji": "⚪"},
        )

        embed = discord.Embed(
            title="🎉 Quest Completed!",
            description=f"{difficulty['emoji']} {quest['emoji']} **{quest['name']}**",
            color=discord.Color.gold(),
        )

        rewards = []
        if reward_money > 0:
            rewards.append(f"💰 {money(reward_money)}")
        if reward_xp > 0:
            rewards.append(f"⭐ {reward_xp} XP")

        embed.add_field(
            name="Rewards Claimed",
            value="\n".join(rewards),
            inline=False,
        )

        embed.set_footer(text=f"Total Quests Completed: {total + 1}")

        await safe_reply(interaction, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(QuestsCog(bot))
