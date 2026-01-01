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


class ForumActionButtons(discord.ui.View):
    """Action buttons for moderators to act on flagged forum posts"""
    
    def __init__(self, bot, thread_id: int, author_id: int, guild_id: int):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.thread_id = thread_id
        self.author_id = author_id
        self.guild_id = guild_id
    
    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.success, custom_id="forum_approve")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Approve the flagged post"""
        # Check if user has manage_messages permission
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need Manage Messages permission."),
                ephemeral=True
            )
        
        try:
            thread = interaction.guild.get_thread(self.thread_id)
            if not thread:
                thread = await interaction.guild.fetch_channel(self.thread_id)
            
            if thread:
                # Send approval message to the thread
                approval_embed = discord.Embed(
                    title="✅ Post Approved",
                    description=f"This post has been reviewed and approved by a moderator.\n\n"
                                f"**Approved by:** {interaction.user.mention}\n"
                                f"Thank you for your contribution!",
                    color=0x00FF00,
                    timestamp=datetime.now(timezone.utc)
                )
                await thread.send(embed=approval_embed)
                
                # Remove from forum moderation cog blacklist if exists
                forum_cog = self.bot.get_cog("ForumModeration")
                if forum_cog:
                    forum_cog.blacklisted_posts.discard(self.thread_id)
                
                # Update the original message to show it was handled
                embed = interaction.message.embeds[0] if interaction.message.embeds else None
                if embed:
                    embed.color = 0x00FF00
                    embed.title = "✅ Forum Post Approved"
                    embed.set_footer(text=f"Approved by {interaction.user} at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
                
                # Disable buttons
                for item in self.children:
                    item.disabled = True
                
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.response.send_message(
                    embed=ModEmbed.error("Error", "Thread not found - it may have been deleted."),
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                embed=ModEmbed.error("Error", f"Failed to approve: {str(e)[:100]}"),
                ephemeral=True
            )
    
    @discord.ui.button(label="🗑️ Delete", style=discord.ButtonStyle.danger, custom_id="forum_delete")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Delete the flagged post"""
        if not interaction.user.guild_permissions.manage_threads:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need Manage Threads permission."),
                ephemeral=True
            )
        
        try:
            thread = interaction.guild.get_thread(self.thread_id)
            if not thread:
                thread = await interaction.guild.fetch_channel(self.thread_id)
            
            if thread:
                thread_name = thread.name
                author = thread.owner
                
                # Try to DM the author
                if author:
                    try:
                        dm_embed = discord.Embed(
                            title="🗑️ Forum Post Removed",
                            description=f"Your post **{thread_name}** in **{interaction.guild.name}** was removed by a moderator.",
                            color=0xFF0000,
                            timestamp=datetime.now(timezone.utc)
                        )
                        dm_embed.add_field(name="Removed by", value=str(interaction.user), inline=True)
                        dm_embed.add_field(name="Reason", value="Content flagged by moderation system", inline=True)
                        await author.send(embed=dm_embed)
                    except:
                        pass
                
                # Delete the thread
                await thread.delete()
                
                # Remove from blacklist
                forum_cog = self.bot.get_cog("ForumModeration")
                if forum_cog:
                    forum_cog.blacklisted_posts.discard(self.thread_id)
                
                # Update the original message
                embed = interaction.message.embeds[0] if interaction.message.embeds else None
                if embed:
                    embed.color = 0xFF0000
                    embed.title = "🗑️ Forum Post Deleted"
                    embed.set_footer(text=f"Deleted by {interaction.user} at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
                
                # Disable buttons
                for item in self.children:
                    item.disabled = True
                
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.response.send_message(
                    embed=ModEmbed.error("Error", "Thread not found - it may already be deleted."),
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                embed=ModEmbed.error("Error", f"Failed to delete: {str(e)[:100]}"),
                ephemeral=True
            )
    
    @discord.ui.button(label="👁️ View Post", style=discord.ButtonStyle.secondary, custom_id="forum_view")
    async def view_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View the flagged post"""
        try:
            thread = interaction.guild.get_thread(self.thread_id)
            if not thread:
                thread = await interaction.guild.fetch_channel(self.thread_id)
            
            if thread:
                await interaction.response.send_message(
                    f"📍 **Go to post:** {thread.mention}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=ModEmbed.error("Error", "Thread not found - it may have been deleted."),
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                embed=ModEmbed.error("Error", f"Failed to find thread: {str(e)[:100]}"),
                ephemeral=True
            )



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
        print(f"[ForumMod] Thread created: {thread.name} (ID: {thread.id}, Parent: {thread.parent_id})")
        
        # Only moderate the anime forum
        if thread.parent_id != self.anime_forum_id:
            print(f"[ForumMod] Skipping - not in anime forum (expected {self.anime_forum_id})")
            return
        
        # Check if author is staff (still check but don't auto-flag)
        is_staff = False
        if thread.owner and (thread.owner.guild_permissions.manage_messages or is_bot_owner_id(thread.owner_id)):
            is_staff = True
            print(f"[ForumMod] Author is staff: {thread.owner} - will check but not auto-flag")
        
        print(f"[ForumMod] Processing thread: {thread.name}")
        
        # Wait a moment for the initial message to be created
        await asyncio.sleep(2)
        
        try:
            # Get the starter message
            starter_message = await thread.fetch_message(thread.id)
            if not starter_message:
                print(f"[ForumMod] Could not fetch starter message for {thread.id}")
                return
            
            print(f"[ForumMod] Checking content - Title: {thread.name[:50]}, Content: {starter_message.content[:100] if starter_message.content else '(empty)'}...")
            
            # Check content with API
            is_safe, reason = await self._check_content_with_ai(
                title=thread.name,
                content=starter_message.content
            )
            
            print(f"[ForumMod] Check Result - Safe: {is_safe}, Reason: {reason}")
            
            if is_safe:
                # Approved!
                await thread.send(
                    f"✅ **Post Approved** - Thank you for your anime recommendation, {thread.owner.mention if thread.owner else 'author'}! "
                    f"This content has been reviewed and approved for the community."
                )
                print(f"[ForumMod] Post approved: {thread.name}")
            else:
                # Rejected - inappropriate content
                self.blacklisted_posts.add(thread.id)
                
                await thread.send(
                    f"🚫 **Post Flagged** - {thread.owner.mention if thread.owner else 'Author'}, this post has been flagged for review.\n"
                    f"**Reason:** {reason}\n\n"
                    f"A moderator will review this shortly. If this is a mistake, please contact staff."
                )
                
                print(f"[ForumMod] Post FLAGGED: {thread.name} - {reason}")
                
                # Notify moderators in the forum alerts channel with action buttons
                settings = await self.bot.db.get_settings(thread.guild.id)
                print(f"[ForumMod] Settings: forum_alerts={settings.get('forum_alerts_channel')}, mod_log={settings.get('mod_log_channel')}")
                
                # Try forum alerts channel first, fall back to mod log
                alerts_channel_id = settings.get("forum_alerts_channel") or settings.get("mod_log_channel")
                print(f"[ForumMod] Using alerts channel ID: {alerts_channel_id}")
                
                if alerts_channel_id:
                    channel = thread.guild.get_channel(alerts_channel_id)
                    print(f"[ForumMod] Found channel: {channel}")
                    if channel:
                        embed = discord.Embed(
                            title="🚨 Forum Post Flagged - Action Required",
                            description=f"**Post:** {thread.mention}\n**Author:** {thread.owner.mention if thread.owner else 'Unknown'}\n**Reason:** {reason}",
                            color=0xFF6600,
                            timestamp=datetime.now(timezone.utc)
                        )
                        embed.add_field(name="📝 Title", value=thread.name[:1024], inline=False)
                        if starter_message.content:
                            embed.add_field(name="📄 Content Preview", value=starter_message.content[:500] + ("..." if len(starter_message.content) > 500 else ""), inline=False)
                        embed.set_footer(text="Use the buttons below to take action")
                        
                        # Create action buttons
                        view = ForumActionButtons(
                            self.bot,
                            thread_id=thread.id,
                            author_id=thread.owner_id if thread.owner else 0,
                            guild_id=thread.guild.id
                        )
                        
                        await channel.send(embed=embed, view=view)
                        print(f"[ForumMod] Alert sent to {channel.name}")
                    else:
                        print(f"[ForumMod] Could not find channel with ID {alerts_channel_id}")
                else:
                    print(f"[ForumMod] No alerts channel configured!")
        
        except Exception as e:
            print(f"[ForumMod] Error checking post {thread.id}: {e}")
            import traceback
            traceback.print_exc()

    
    async def _check_content_with_ai(self, title: str, content: str) -> tuple[bool, str]:
        """
        Check if anime forum content is appropriate by looking up the anime on MyAnimeList
        Uses Jikan API to check ratings
        
        Returns:
            (is_safe, reason) - True if content is safe, and reason if not
        """
        import aiohttp
        import re
        import urllib.parse
        
        combined_text = f"{title} {content}".lower()
        
        # Quick keyword blocklist for obvious cases
        quick_block = ["hentai", "h-anime", "hanime", "nhentai", "hentaihaven", 
                       "fakku", "doujinshi", "18+", "xxx", "porn", "ecchi"]
        for keyword in quick_block:
            if keyword in combined_text:
                return False, f"Blocked: Contains '{keyword}'"
        
        # Extract anime title - usually the thread title is the anime name
        anime_title = title.strip()
        
        # Clean up common patterns like "Anime Name - My Review" or "Anime Name (2024)"
        anime_title = re.sub(r'\s*[-–—]\s*.*$', '', anime_title)  # Remove " - anything after"
        anime_title = re.sub(r'\s*\([^)]*\)\s*$', '', anime_title)  # Remove (year) etc
        anime_title = re.sub(r'\s*\[[^\]]*\]\s*$', '', anime_title)  # Remove [tags]
        anime_title = anime_title.strip()
        
        if not anime_title or len(anime_title) < 2:
            print(f"[ForumMod] Could not extract anime title from: {title}")
            return False, "Could not determine anime title - flagged for manual review"
        
        print(f"[ForumMod] Looking up anime: '{anime_title}'")
        
        # For long titles, try using just the first few words for search
        search_terms = [anime_title]
        words = anime_title.split()
        if len(words) > 3:
            search_terms.append(" ".join(words[:3]))  # First 3 words
        if len(words) > 2:
            search_terms.append(" ".join(words[:2]))  # First 2 words
        # Also try the first word if it's reasonably long
        if len(words[0]) >= 4:
            search_terms.append(words[0])
        
        try:
            async with aiohttp.ClientSession() as session:
                for search_term in search_terms:
                    encoded_term = urllib.parse.quote(search_term)
                    search_url = f"https://api.jikan.moe/v4/anime?q={encoded_term}&limit=5&sfw=false"
                    
                    print(f"[ForumMod] Searching: '{search_term}'")
                    
                    async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 429:  # Rate limited
                            await asyncio.sleep(1)
                            continue
                        if response.status != 200:
                            print(f"[ForumMod] Jikan API error: {response.status}")
                            continue
                        
                        data = await response.json()
                        
                        if not data.get("data"):
                            continue
                        
                        # Check the top results
                        for result in data["data"]:
                            result_title = result.get("title", "").lower()
                            result_title_en = (result.get("title_english") or "").lower()
                            all_titles = [result_title, result_title_en]
                            # Add synonyms
                            for syn in result.get("title_synonyms", []):
                                all_titles.append(syn.lower())
                            
                            search_lower = anime_title.lower()
                            
                            # Check for matches
                            match_found = False
                            for t in all_titles:
                                if not t:
                                    continue
                                # Check various matching conditions
                                if search_lower == t or t == search_lower:
                                    match_found = True
                                elif search_lower.startswith(t[:min(10, len(t))]):
                                    match_found = True
                                elif t.startswith(search_lower[:min(10, len(search_lower))]):
                                    match_found = True
                                elif search_term.lower() in t or t in search_term.lower():
                                    match_found = True
                            
                            if match_found:
                                # Check rating
                                rating = result.get("rating", "") or ""
                                genres = [g.get("name", "").lower() for g in result.get("genres", [])]
                                
                                print(f"[ForumMod] Found match: {result.get('title')} - Rating: {rating}, Genres: {genres}")
                                
                                # Rx - Hentai is the explicit adult rating on MAL
                                if "rx" in rating.lower() or "hentai" in rating.lower():
                                    return False, f"BLOCKED: {result.get('title')} is rated Rx (Hentai)"
                                
                                # Check if hentai or ecchi is in genres
                                if "hentai" in genres:
                                    return False, f"BLOCKED: {result.get('title')} - Genre: Hentai"
                                
                                if "ecchi" in genres:
                                    return False, f"BLOCKED: {result.get('title')} - Genre: Ecchi (sexually suggestive)"
                                
                                # R+ - Mild Nudity should also be flagged
                                if "r+" in rating.lower() or "mild nudity" in rating.lower():
                                    return False, f"BLOCKED: {result.get('title')} - Rated R+ (Mild Nudity)"
                                
                                # Found a match that's appropriate
                                return True, f"Verified: {result.get('title')} - {rating or 'No rating'}"
                    
                    # Small delay between searches to avoid rate limiting
                    await asyncio.sleep(0.5)
                
                # No match found with any search term
                print(f"[ForumMod] No match found for: {anime_title}")
                return False, "Anime not found in database - flagged for manual review"
                    
        except asyncio.TimeoutError:
            print(f"[ForumMod] API timeout for: {anime_title}")
            return False, "API timeout - flagged for manual review"
        except Exception as e:
            print(f"[ForumMod] API error: {e}")
            return False, f"API error - flagged for manual review"
    
    async def _log_to_mod_log(self, guild: discord.Guild, thread: discord.Thread, reason: str, content: str = None):
        """Log a forum moderation action to the mod log channel with action buttons"""
        try:
            settings = await self.bot.db.get_settings(guild.id)
            # Try forum alerts channel first, fall back to mod log
            alerts_channel_id = settings.get("forum_alerts_channel") or settings.get("mod_log_channel")
            
            if alerts_channel_id:
                channel = guild.get_channel(alerts_channel_id)
                if channel:
                    embed = discord.Embed(
                        title="🚨 Forum Post Flagged - Action Required",
                        description=f"**Post:** {thread.mention}\n**Author:** {thread.owner.mention if thread.owner else 'Unknown'}\n**Reason:** {reason}",
                        color=0xFF6600,
                        timestamp=datetime.now(timezone.utc)
                    )
                    embed.add_field(name="📝 Title", value=thread.name[:1024], inline=False)
                    if content:
                        embed.add_field(name="📄 Content Preview", value=content[:500] + ("..." if len(content) > 500 else ""), inline=False)
                    embed.set_footer(text="Use the buttons below to take action")
                    
                    # Create action buttons
                    view = ForumActionButtons(
                        self.bot,
                        thread_id=thread.id,
                        author_id=thread.owner_id if thread.owner else 0,
                        guild_id=guild.id
                    )
                    
                    await channel.send(embed=embed, view=view)
        except Exception as e:
            print(f"[ForumMod] Error logging to mod log: {e}")
    
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
        # Defer once at the start for all actions
        await interaction.response.defer(ephemeral=True)
        
        try:
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
        except Exception as e:
            print(f"[ForumMod] Error in /forum {action}: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                embed=ModEmbed.error("Error", f"An error occurred: {str(e)[:200]}"),
                ephemeral=True
            )
    
    async def _forum_check(self, interaction: discord.Interaction, thread: Optional[discord.Thread]):
        """Manually check a forum post with API"""
        if not thread:
            return await interaction.followup.send(
                embed=ModEmbed.error("Missing Argument", "Please specify a thread to check."),
                ephemeral=True
            )
        
        try:
            starter_message = await thread.fetch_message(thread.id)
            is_safe, reason = await self._check_content_with_ai(
                title=thread.name,
                content=starter_message.content
            )
            
            status = "✅ **SAFE**" if is_safe else "🚫 **FLAGGED**"
            
            # Send result message to the thread
            if is_safe:
                await thread.send(
                    f"✅ **Post Approved** - Thank you for your anime recommendation, {thread.owner.mention if thread.owner else 'author'}! "
                    f"This content has been reviewed and approved for the community."
                )
            else:
                self.blacklisted_posts.add(thread.id)
                await thread.send(
                    f"🚫 **Post Flagged** - {thread.owner.mention if thread.owner else 'Author'}, this post has been flagged for review.\n"
                    f"**Reason:** {reason}\n\n"
                    f"A moderator will review this shortly. If this is a mistake, please contact staff."
                )
                # Log to mod log
                await self._log_to_mod_log(interaction.guild, thread, reason, starter_message.content)
            
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
            return await interaction.followup.send(
                embed=ModEmbed.error("Missing Argument", "Please specify a thread to approve."),
                ephemeral=True
            )
        
        # Remove from blacklist
        self.blacklisted_posts.discard(thread.id)
        
        await thread.send(
            f"✅ **Manually Approved** - This post has been approved by {interaction.user.mention}."
        )
        
        await interaction.followup.send(
            embed=ModEmbed.success("Post Approved", f"Approved {thread.mention}"),
            ephemeral=True
        )
    
    async def _forum_delete(self, interaction: discord.Interaction, thread: Optional[discord.Thread], reason: str):
        """Delete a forum post"""
        if not thread:
            return await interaction.followup.send(
                embed=ModEmbed.error("Missing Argument", "Please specify a thread to delete."),
                ephemeral=True
            )
        
        thread_name = thread.name
        thread_owner = thread.owner
        
        # Send deletion notice to thread before deleting
        try:
            await thread.send(
                f"🗑️ **Post Deleted** - This post has been removed by {interaction.user.mention}.\n"
                f"**Reason:** {reason}\n\n"
                f"This thread will be deleted shortly."
            )
            await asyncio.sleep(2)  # Brief delay so the message can be seen
        except Exception:
            pass
        
        # Try to notify the author via DM
        if thread_owner:
            try:
                dm_embed = discord.Embed(
                    title="📋 Forum Post Deleted",
                    description=f"Your forum post **{thread_name}** in **{interaction.guild.name}** has been deleted.",
                    color=0xFF6600,
                    timestamp=datetime.now(timezone.utc)
                )
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.add_field(name="Deleted by", value=str(interaction.user), inline=True)
                await thread_owner.send(embed=dm_embed)
            except Exception:
                pass  # Can't DM user
        
        # Remove from blacklist if present
        self.blacklisted_posts.discard(thread.id)
        
        await thread.delete()
        
        # Log to mod log
        settings = await self.bot.db.get_settings(interaction.guild.id)
        mod_log = settings.get("mod_log_channel")
        if mod_log:
            channel = interaction.guild.get_channel(mod_log)
            if channel:
                log_embed = discord.Embed(
                    title="🗑️ Forum Post Deleted",
                    description=f"**Thread:** {thread_name}\n**Author:** {thread_owner.mention if thread_owner else 'Unknown'}\n**Deleted by:** {interaction.user.mention}\n**Reason:** {reason}",
                    color=0xFF6600,
                    timestamp=datetime.now(timezone.utc)
                )
                await channel.send(embed=log_embed)
        
        embed = ModEmbed.success(
            "Thread Deleted",
            f"**Thread:** {thread_name}\n**Author:** {thread_owner.mention if thread_owner else 'Unknown'}\n**Reason:** {reason}"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _forum_blacklist(self, interaction: discord.Interaction, thread: Optional[discord.Thread]):
        """Add a thread to the blacklist"""
        if not thread:
            return await interaction.followup.send(
                embed=ModEmbed.error("Missing Argument", "Please specify a thread to blacklist."),
                ephemeral=True
            )
        
        self.blacklisted_posts.add(thread.id)
        
        # Send flagged message to the thread
        await thread.send(
            f"🚫 **Post Blacklisted** - {thread.owner.mention if thread.owner else 'Author'}, this post has been manually flagged by {interaction.user.mention}.\n\n"
            f"A moderator has determined this content requires review. If this is a mistake, please contact staff."
        )
        
        # Log to mod log
        try:
            starter_message = await thread.fetch_message(thread.id)
            content = starter_message.content
        except Exception:
            content = "(Could not fetch content)"
        
        await self._log_to_mod_log(interaction.guild, thread, f"Manually blacklisted by {interaction.user}", content)
        
        await interaction.followup.send(
            embed=ModEmbed.success("Thread Blacklisted", f"Blacklisted {thread.mention} and sent flagged notification."),
            ephemeral=True
        )
    
    async def _forum_checkall(self, interaction: discord.Interaction):
        """Check all recent posts in the anime forum"""
        # Already deferred by main command
        
        forum = interaction.guild.get_channel(self.anime_forum_id)
        if not forum or not isinstance(forum, discord.ForumChannel):
            return await interaction.followup.send(
                embed=ModEmbed.error("Error", f"Anime forum channel not found (ID: {self.anime_forum_id})."),
                ephemeral=True
            )
        
        checked = 0
        flagged = 0
        safe = 0
        errors = 0
        
        # Get all threads - both active and archived
        all_threads = list(forum.threads)  # Active threads
        
        # Also fetch archived threads
        try:
            async for archived_thread in forum.archived_threads(limit=50):
                if archived_thread not in all_threads:
                    all_threads.append(archived_thread)
        except Exception as e:
            print(f"[ForumMod] Could not fetch archived threads: {e}")
        
        if not all_threads:
            return await interaction.followup.send(
                embed=ModEmbed.warning("No Threads", "No threads found in the anime forum."),
                ephemeral=True
            )
        
        # Send initial status
        status_msg = await interaction.followup.send(
            embed=discord.Embed(
                title="🔍 Checking Forum Posts...",
                description=f"Found **{len(all_threads)}** threads to check.\nThis may take a while due to API rate limits.",
                color=0x00AAFF
            ),
            ephemeral=True
        )
        
        # Check each thread
        for thread in all_threads:
            try:
                starter_message = await thread.fetch_message(thread.id)
                is_safe, reason = await self._check_content_with_ai(
                    title=thread.name,
                    content=starter_message.content
                )
                checked += 1
                
                if is_safe:
                    safe += 1
                    # Send approval message
                    await thread.send(
                        f"✅ **Post Approved** - Thank you for your anime recommendation, {thread.owner.mention if thread.owner else 'author'}! "
                        f"This content has been reviewed and approved for the community.\n"
                        f"*Verified: {reason}*"
                    )
                else:
                    flagged += 1
                    self.blacklisted_posts.add(thread.id)
                    # Send flagged message
                    await thread.send(
                        f"🚫 **Post Flagged** - {thread.owner.mention if thread.owner else 'Author'}, this post has been flagged for review.\n"
                        f"**Reason:** {reason}\n\n"
                        f"A moderator will review this shortly. If this is a mistake, please contact staff."
                    )
                
                # Rate limit - Jikan API allows 3 requests/second, so wait 2 seconds between checks
                await asyncio.sleep(2)
                
            except Exception as e:
                errors += 1
                print(f"[ForumMod] Error checking thread {thread.id}: {e}")
        
        embed = discord.Embed(
            title="📊 Forum Check Complete",
            description=f"Checked **{checked}** threads",
            color=0x00FF00 if flagged == 0 else 0xFFAA00
        )
        embed.add_field(name="✅ Safe", value=str(safe), inline=True)
        embed.add_field(name="🚫 Flagged", value=str(flagged), inline=True)
        if errors > 0:
            embed.add_field(name="❌ Errors", value=str(errors), inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    
    async def _forum_list(self, interaction: discord.Interaction):
        """List all blacklisted threads"""
        if not self.blacklisted_posts:
            return await interaction.followup.send(
                embed=ModEmbed.info("No Blacklisted Posts", "No forum posts are currently blacklisted."),
                ephemeral=True
            )
        
        forum = interaction.guild.get_channel(self.anime_forum_id)
        if not forum:
            return await interaction.followup.send(
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
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ForumModeration(bot))
