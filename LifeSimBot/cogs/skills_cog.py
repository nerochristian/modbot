# cogs/skills_cog.py
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.skills_service import (
    SKILLS,
    calculate_skill_level,
    get_all_skill_levels,
    calculate_training_xp,
    get_training_cost
)
from utils.format import progress_bar
from utils.checks import safe_defer, safe_reply


class SkillsCog(commands.Cog):
    """Skill training and progression commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="skills", description="⚔️ View all your skill levels")
    async def skills(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        
        # Get all skills
        skills_data = get_all_skill_levels(u)
        
        embed = discord.Embed(
            title=f"⚔️ {interaction.user.display_name}'s Skills",
            description="Train skills to unlock bonuses and improve gameplay!",
            color=discord.Color.purple()
        )
        
        # Sort by level (highest first)
        sorted_skills = sorted(skills_data.items(), key=lambda x: x[1]["level"], reverse=True)
        
        for skill_id, skill_info in sorted_skills:
            level = skill_info["level"]
            curr_xp = skill_info["current_xp"]
            needed_xp = skill_info["needed_xp"]
            multiplier = skill_info["multiplier"]
            
            if level >= 100:
                progress_text = "⭐ **MAX LEVEL**"
            else:
                progress_text = f"{progress_bar(curr_xp, needed_xp, length=8)} {curr_xp}/{needed_xp}"
            
            skill_text = (
                f"**Level {level}** | Bonus: +{int((multiplier - 1) * 100)}%\n"
                f"{progress_text}\n"
                f"_{skill_info['description']}_"
            )
            
            embed.add_field(
                name=f"{skill_info['emoji']} {skill_info['name']}",
                value=skill_text,
                inline=False
            )
        
        embed.set_footer(text="Use /train <skill> to level up your skills!")
        
        await safe_reply(interaction, embed=embed)
    
    @app_commands.command(name="train", description="⚡ Train a skill to level it up")
    @app_commands.describe(skill="Skill to train")
    @app_commands.choices(skill=[
        app_commands.Choice(name="💪 Strength", value="strength"),
        app_commands.Choice(name="🧠 Intelligence", value="intelligence"),
        app_commands.Choice(name="✨ Charisma", value="charisma"),
        app_commands.Choice(name="🍀 Luck", value="luck"),
        app_commands.Choice(name="👨‍🍳 Cooking", value="cooking"),
        app_commands.Choice(name="🔪 Crime", value="crime"),
        app_commands.Choice(name="💼 Business", value="business"),
    ])
    async def train(self, interaction: discord.Interaction, skill: str):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        
        # Check if valid skill
        if skill not in SKILLS:
            return await safe_reply(interaction, content="❌ Invalid skill!")
        
        skill_info = SKILLS[skill]
        
        # Get current stats
        current_xp = int(u.get(f"skill_{skill}", 0))
        energy = int(u.get("energy", 100))
        
        level, curr_xp, needed_xp = calculate_skill_level(current_xp)
        
        # Check if maxed
        if level >= 100:
            return await safe_reply(
                interaction,
                content=f"⭐ Your {skill_info['name']} is already maxed at level 100!"
            )
        
        # Get training cost
        energy_cost, base_xp = get_training_cost(skill)
        
        # Check energy
        if energy < energy_cost:
            return await safe_reply(
                interaction,
                content=f"❌ Not enough energy! Need {energy_cost}, you have {energy}"
            )
        
        # Calculate XP gain (diminishing returns at higher levels)
        xp_gain = calculate_training_xp(base_xp, level)
        
        # Update stats
        db.updatestat(userid, "energy", energy - energy_cost)
        db.add_skill_xp(userid, skill, xp_gain)
        
        # Recalculate level
        new_xp = current_xp + xp_gain
        new_level, new_curr_xp, new_needed_xp = calculate_skill_level(new_xp)
        
        leveled_up = new_level > level
        
        # Create embed
        embed = discord.Embed(
            title=f"{skill_info['emoji']} Trained {skill_info['name']}!",
            description=(
                f"**XP Gained:** +{xp_gain}\n"
                f"**Energy Cost:** -{energy_cost}\n"
                f"**Level:** {new_level}\n"
                f"**Progress:** {progress_bar(new_curr_xp, new_needed_xp, length=10)}"
            ),
            color=discord.Color.gold() if leveled_up else discord.Color.blue()
        )
        
        if leveled_up:
            embed.add_field(
                name="🎉 Level Up!",
                value=f"**{skill_info['name']}** is now level {new_level}!\nYou gained +{leveled_up}% bonus!",
                inline=False
            )
        
        embed.set_footer(text=f"Training efficiency: {int((xp_gain / base_xp) * 100)}% (decreases with level)")
        
        await safe_reply(interaction, embed=embed)
    
    @app_commands.command(name="skillinfo", description="ℹ️ View detailed info about a skill")
    @app_commands.describe(skill="Skill to view")
    @app_commands.choices(skill=[
        app_commands.Choice(name="💪 Strength", value="strength"),
        app_commands.Choice(name="🧠 Intelligence", value="intelligence"),
        app_commands.Choice(name="✨ Charisma", value="charisma"),
        app_commands.Choice(name="🍀 Luck", value="luck"),
        app_commands.Choice(name="👨‍🍳 Cooking", value="cooking"),
        app_commands.Choice(name="🔪 Crime", value="crime"),
        app_commands.Choice(name="💼 Business", value="business"),
    ])
    async def skillinfo(self, interaction: discord.Interaction, skill: str):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        
        if skill not in SKILLS:
            return await safe_reply(interaction, content="❌ Invalid skill!")
        
        skill_info = SKILLS[skill]
        current_xp = int(u.get(f"skill_{skill}", 0))
        level, curr_xp, needed_xp = calculate_skill_level(current_xp)
        
        energy_cost, base_xp = get_training_cost(skill)
        training_efficiency = calculate_training_xp(base_xp, level)
        
        embed = discord.Embed(
            title=f"{skill_info['emoji']} {skill_info['name']}",
            description=skill_info['description'],
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="📊 Current Stats",
            value=(
                f"**Level:** {level}/100\n"
                f"**Total XP:** {current_xp:,}\n"
                f"**Progress:** {progress_bar(curr_xp, needed_xp, length=10)}\n"
                f"**Bonus:** +{int(level)}%"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚡ Training",
            value=(
                f"**Energy Cost:** {energy_cost}\n"
                f"**XP Gain:** ~{training_efficiency} (base: {base_xp})\n"
                f"**Efficiency:** {int((training_efficiency / base_xp) * 100)}%"
            ),
            inline=False
        )
        
        # Skill-specific benefits
        benefits = {
            "strength": "• Increases crime success rates\n• Better PvP combat damage\n• Higher robbery payouts",
            "intelligence": "• Higher work earnings\n• Better job performance\n• Faster XP gain",
            "charisma": "• Better shop discounts\n• Easier negotiations\n• Higher friend bonuses",
            "luck": "• Better gambling odds\n• More rare item drops\n• Critical hit chances",
            "cooking": "• Cook better food\n• Higher food stat bonuses\n• Open restaurant business",
            "crime": "• Better robbery success\n• Lower jail time\n• Unlock advanced crimes",
            "business": "• Higher passive income\n• Better investment returns\n• Unlock more businesses"
        }
        
        embed.add_field(
            name="💎 Benefits",
            value=benefits.get(skill, "Various gameplay bonuses"),
            inline=False
        )
        
        embed.set_footer(text=f"Use /train {skill} to level up!")
        
        await safe_reply(interaction, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(SkillsCog(bot))
