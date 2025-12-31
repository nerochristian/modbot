"""
Forum Moderation with AI-Powered Content Filtering
Automatically moderates forum posts using Groq AI to detect inappropriate content
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Literal
import os
from datetime import datetime, timezone
import asyncio

from groq import Groq
from utils.embeds import ModEmbed
from utils.checks import is_mod, is_admin, is_bot_owner_id


class ForumModeration(commands.Cog):
    """AI-powered forum moderation system"""
    
    def __init__(self, bot):
        self.bot = bot
        # Forum channel ID for anime recommendations
        self.anime_forum_id = 1455898752094175332
        
        # Initialize Groq client
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            self.groq_client = Groq(api_key=api_key)
        else:
            self.groq_client = None
            
        # Blacklisted post IDs (posts that failed moderation)
        self.blacklisted_posts: set[int] = set()
    
    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        """Auto-moderate new forum posts in the anime forum"""
        # Only moderate the anime forum
        if thread.parent_id != self.anime_forum_id:
            return
        
        # Don't moderate posts by staff
        if thread.owner and (thread.owner.guild_permissions.manage_messages or is_bot_owner_id(thread.owner_id)):
            return
        
        # Wait a moment for the initial message to be created
        await asyncio.sleep(2)
        
        try:
            # Get the starter message
            starter_message = await thread.fetch_message(thread.id)
            if not starter_message:
                return
            
            # Check content with AI
            is_safe, reason = await self._check_content_with_ai(
                title=thread.name,
                content=starter_message.content
            )
            
            if is_safe:
                # Approved!
                await thread.send(
                    f"✅ **Post Approved** - Thank you for your anime recommendation, {thread.owner.mention}! "
                    f"This content has been reviewed and approved for the community."
                )
            else:
                # Rejected - inappropriate content
                self.blacklisted_posts.add(thread.id)
                
                await thread.send(
                    f"🚫 **Post Flagged** - {thread.owner.mention}, this post has been flagged for review.\n"
                    f"**Reason:** {reason}\n\n"
                    f"A moderator will review this shortly. If this is a mistake, please contact staff."
                )
                
                # Notify moderators
                settings = await self.bot.db.get_settings(thread.guild.id)
                mod_log = settings.get("mod_log_channel")
                if mod_log:
                    channel = thread.guild.get_channel(mod_log)
                    if channel:
                        embed = discord.Embed(
                            title="🚨 Forum Post Flagged",
                            description=f"**Post:** {thread.mention}\n**Author:** {thread.owner.mention}\n**Reason:** {reason}",
                            color=0xFF0000,
                            timestamp=datetime.now(timezone.utc)
                        )
                        embed.add_field(name="Title", value=thread.name[:1024], inline=False)
                        if starter_message.content:
                            embed.add_field(name="Content Preview", value=starter_message.content[:1024], inline=False)
                        await channel.send(embed=embed)
        
        except Exception as e:
            print(f"[ForumMod] Error checking post {thread.id}: {e}")
    
    async def _check_content_with_ai(self, title: str, content: str) -> tuple[bool, str]:
        """
        Check if anime forum content is appropriate using Groq AI
        
        Returns:
            (is_safe, reason) - True if content is safe, and reason if not
        """
        if not self.groq_client:
            # No AI available - approve by default
            return True, "AI check unavailable"
        
        system_prompt = """You are a content moderator for an anime recommendations forum.
Your job is to determine if a post is appropriate anime content or if it contains hentai/NSFW content.

Respond with ONLY ONE WORD:
- "SAFE" if the post is about regular anime (any rating including ecchi, but not hentai)
- "UNSAFE" if the post contains hentai, pornographic content, or explicit NSFW anime

After your one-word response, add a brief reason (10 words max)."""

        user_prompt = f"""Title: {title}

Content: {content}

Is this appropriate anime content or hentai/NSFW?"""

        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                temperature=0.3,
                max_tokens=100,
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse response
            if result.upper().startswith("SAFE"):
                return True, "Content approved by AI"
            else:
                # Extract reason
                lines = result.split("\n")
                reason = lines[1] if len(lines) > 1 else "Inappropriate content detected"
                return False, reason
                
        except Exception as e:
            print(f"[ForumMod] AI check failed: {e}")
            # On error, approve but log
            return True, f"AI check failed: {str(e)[:50]}"
    
    @app_commands.command(name="forum", description="🔍 Manage forum posts")
    @app_commands.describe(
        action="Action to perform",
        thread="Forum thread to act on",
        reason="Reason for the action"
    )
    @is_mod()
    async def forum(
        self,
        interaction: discord.Interaction,
        action: Literal["check", "approve", "delete", "blacklist", "checkall", "list"],
        thread: Optional[discord.Thread] = None,
        reason: Optional[str] = "No reason provided"
    ):
        """Manage forum moderation"""
        
        if action == "check":
            await self._forum_check(interaction, thread)
        elif action == "approve":
            await self._forum_approve(interaction, thread)
        elif action == "delete":
            await self._forum_delete(interaction, thread, reason)
        elif action == "blacklist":
            await self._forum_blacklist(interaction, thread)
        elif action == "checkall":
            await self._forum_checkall(interaction)
        elif action == "list":
            await self._forum_list(interaction)
    
    async def _forum_check(self, interaction: discord.Interaction, thread: Optional[discord.Thread]):
        """Manually check a forum post with AI"""
        if not thread:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a thread to check."),
                ephemeral=True
            )
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            starter_message = await thread.fetch_message(thread.id)
            is_safe, reason = await self._check_content_with_ai(
                title=thread.name,
                content=starter_message.content
            )
            
            status = "✅ **SAFE**" if is_safe else "🚫 **FLAGGED**"
            embed = discord.Embed(
                title=f"Forum Check: {thread.name}",
                description=f"**Status:** {status}\n**Reason:** {reason}",
                color=0x00FF00 if is_safe else 0xFF0000
            )
            embed.add_field(name="Thread", value=thread.mention, inline=False)
            embed.add_field(name="Author", value=thread.owner.mention if thread.owner else "Unknown", inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                embed=ModEmbed.error("Error", f"Failed to check thread: {e}"),
                ephemeral=True
            )
    
    async def _forum_approve(self, interaction: discord.Interaction, thread: Optional[discord.Thread]):
        """Manually approve a forum post"""
        if not thread:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a thread to approve."),
                ephemeral=True
            )
        
        # Remove from blacklist
        self.blacklisted_posts.discard(thread.id)
        
        await thread.send(
            f"✅ **Manually Approved** - This post has been approved by {interaction.user.mention}."
        )
        
        await interaction.response.send_message(
            embed=ModEmbed.success("Post Approved", f"Approved {thread.mention}"),
            ephemeral=True
        )
    
    async def _forum_delete(self, interaction: discord.Interaction, thread: Optional[discord.Thread], reason: str):
        """Delete a forum post"""
        if not thread:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a thread to delete."),
                ephemeral=True
            )
        
        thread_name = thread.name
        thread_owner = thread.owner
        
        await thread.delete()
        
        embed = ModEmbed.success(
            "Thread Deleted",
            f"**Thread:** {thread_name}\n**Author:** {thread_owner.mention if thread_owner else 'Unknown'}\n**Reason:** {reason}"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _forum_blacklist(self, interaction: discord.Interaction, thread: Optional[discord.Thread]):
        """Add a thread to the blacklist"""
        if not thread:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a thread to blacklist."),
                ephemeral=True
            )
        
        self.blacklisted_posts.add(thread.id)
        
        await interaction.response.send_message(
            embed=ModEmbed.success("Thread Blacklisted", f"Blacklisted {thread.mention}"),
            ephemeral=True
        )
    
    async def _forum_checkall(self, interaction: discord.Interaction):
        """Check all recent posts in the anime forum"""
        await interaction.response.defer(ephemeral=True)
        
        forum = interaction.guild.get_channel(self.anime_forum_id)
        if not forum or not isinstance(forum, discord.ForumChannel):
            return await interaction.followup.send(
                embed=ModEmbed.error("Error", "Anime forum channel not found."),
                ephemeral=True
            )
        
        checked = 0
        flagged = 0
        safe = 0
        
        # Check active threads
        for thread in forum.threads:
            try:
                starter_message = await thread.fetch_message(thread.id)
                is_safe, reason = await self._check_content_with_ai(
                    title=thread.name,
                    content=starter_message.content
                )
                checked += 1
                
                if is_safe:
                    safe += 1
                else:
                    flagged += 1
                    self.blacklisted_posts.add(thread.id)
            except Exception:
                pass
        
        embed = discord.Embed(
            title="📊 Forum Check Complete",
            description=f"Checked {checked} threads",
            color=0x00FF00
        )
        embed.add_field(name="✅ Safe", value=str(safe), inline=True)
        embed.add_field(name="🚫 Flagged", value=str(flagged), inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _forum_list(self, interaction: discord.Interaction):
        """List all blacklisted threads"""
        if not self.blacklisted_posts:
            return await interaction.response.send_message(
                embed=ModEmbed.info("No Blacklisted Posts", "No forum posts are currently blacklisted."),
                ephemeral=True
            )
        
        forum = interaction.guild.get_channel(self.anime_forum_id)
        if not forum:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", "Anime forum channel not found."),
                ephemeral=True
            )
        
        lines = []
        for thread_id in list(self.blacklisted_posts)[:10]:
            try:
                thread = await interaction.guild.fetch_channel(thread_id)
                if thread:
                    lines.append(f"• {thread.mention} by {thread.owner.mention if thread.owner else 'Unknown'}")
            except Exception:
                lines.append(f"• ID: {thread_id} (deleted)")
        
        embed = discord.Embed(
            title="🚫 Blacklisted Forum Posts",
            description="\n".join(lines) if lines else "No active blacklisted posts",
            color=0xFF0000
        )
        embed.set_footer(text=f"Total: {len(self.blacklisted_posts)} posts")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ForumModeration(bot))
