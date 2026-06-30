"""
Behavioral Profiling - AI Analysis of user behavior
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging

logger = logging.getLogger("ModBot.Behavior")

class BehaviorProfiling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="Generate an AI behavioral profile for a user based on their recent messages")
    @app_commands.default_permissions(moderate_members=True)
    async def profile_user(self, interaction: discord.Interaction, target: discord.Member):
        if not hasattr(self.bot, 'database') or not hasattr(self.bot.database, 'get_recent_user_messages'):
            await interaction.response.send_message("Message tracking database is not available.", ephemeral=True)
            return

        # Defer because AI calls can be slow
        await interaction.response.defer(ephemeral=False)

        # Get the AI moderation cog to use its AI client
        aimod_cog = self.bot.get_cog("AIModeration")
        if not aimod_cog or not hasattr(aimod_cog, 'ai') or not aimod_cog.ai.is_available:
            await interaction.followup.send("AI client is currently offline or unavailable.")
            return

        recent_msgs = await self.bot.database.get_recent_user_messages(interaction.guild.id, target.id, limit=300)
        
        if not recent_msgs:
            await interaction.followup.send(f"I don't have enough message history for {target.mention} to build a profile.")
            return

        # Format messages for AI
        message_context = "\n".join(
            f"[{m['timestamp']}] {m['content']}" for m in recent_msgs
        )

        prompt = (
            f"Analyze the following recent messages from Discord user '{target.display_name}' and provide a comprehensive Behavioral & Personality Profile.\n"
            "Include their general tone, primary interests or topics they discuss, their level of toxicity/friendliness, and any notable behavioral patterns.\n"
            "Keep it professional but insightful. Format the response nicely using Discord markdown.\n\n"
            f"Messages:\n{message_context}"
        )

        try:
            profile_content = await aimod_cog.ai._call(
                [
                    {
                        "role": "system",
                        "content": "You are an expert behavioral analyst profiling Discord user behavior. Be objective, accurate, and concise."
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=600,
                model=None,
                session_key=f"profile-{target.id}",
                session_name=f"Profile: {target.display_name}",
            )

            embed = discord.Embed(
                title=f"🧠 Behavioral Profile: {target.display_name}",
                description=profile_content or "Failed to generate profile.",
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            embed.set_footer(text=f"Based on their last {len(recent_msgs)} tracked messages.")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("Error generating profile: %s", e)
            await interaction.followup.send(f"An error occurred while generating the profile: {str(e)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(BehaviorProfiling(bot))
