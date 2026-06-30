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
        if not hasattr(self.bot, 'db') or not hasattr(self.bot.db, 'get_recent_user_messages'):
            await interaction.response.send_message("Message tracking database is not available.", ephemeral=True)
            return

        # Defer because AI calls can be slow
        await interaction.response.defer(ephemeral=False)

        # Get the AI moderation cog to use its AI client
        aimod_cog = self.bot.get_cog("AIModeration")
        if not aimod_cog or not hasattr(aimod_cog, 'ai') or not aimod_cog.ai.is_available:
            await interaction.followup.send("AI client is currently offline or unavailable.")
            return

        recent_msgs = await self.bot.db.get_recent_user_messages(interaction.guild.id, target.id, limit=300)
        
        if not recent_msgs:
            # Fallback: pull from channel history
            fallback_msgs = []
            channels = [c for c in interaction.guild.text_channels if c.permissions_for(interaction.guild.me).read_message_history]
            # Try to gather messages from the first 10 text channels
            for channel in channels[:10]:
                try:
                    async for msg in channel.history(limit=1000):
                        if msg.author.id == target.id and msg.content.strip():
                            fallback_msgs.append({
                                'timestamp': msg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                                'content': msg.content.strip()
                            })
                except Exception:
                    continue
                if len(fallback_msgs) >= 300:
                    break
            recent_msgs = fallback_msgs[:300]

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
        
        # The AI inference proxy uses Discord under the hood and limits inputs to 4000 characters.
        if len(prompt) > 2500:
            prompt = prompt[:2500] + "\n...[TRUNCATED]"

        try:
            logger.info("Requesting behavioral profile for %s (prompt length: %d)", target.id, len(prompt))
            profile_content = await aimod_cog.ai._call_digitalocean(
                [
                    {
                        "role": "system",
                        "content": "You are an expert behavioral analyst profiling Discord user behavior. Be objective, accurate, and concise."
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=600,
                model="deepseek-4-flash",
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
