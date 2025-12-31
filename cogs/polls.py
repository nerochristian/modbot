"""
Poll System - Create interactive polls with reactions or buttons
Similar structure to giveaway system
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Literal, List
from datetime import datetime, timezone, timedelta
import asyncio

from utils.embeds import ModEmbed
from utils.checks import is_mod
from config import Config


class PollView(discord.ui.View):
    """Interactive view for poll with buttons"""
    
    def __init__(self, poll_data: dict, ended: bool = False):
        super().__init__(timeout=None)
        self.poll_data = poll_data
        self.ended = ended
        
        # Add buttons for each option
        options = poll_data.get("options", [])
        for i, option in enumerate(options[:5]):  # Max 5 options for buttons
            button = discord.ui.Button(
                label=option[:80],  # Discord button label limit
                custom_id=f"poll_{poll_data['id']}_{i}",
                style=discord.ButtonStyle.primary,
                disabled=ended
            )
            button.callback = self._create_callback(i)
            self.add_item(button)
    
    def _create_callback(self, option_index: int):
        async def callback(interaction: discord.Interaction):
            # Get the poll cog to handle the vote
            poll_cog = interaction.client.get_cog("Polls")
            if poll_cog:
                await poll_cog._handle_vote(interaction, self.poll_data['id'], option_index)
            else:
                await interaction.response.send_message(
                    "Poll system is currently unavailable.",
                    ephemeral=True
                )
        return callback


class Polls(commands.Cog):
    """Poll management system"""
    
    def __init__(self, bot):
        self.bot = bot
        # In-memory storage for polls (could be moved to database)
        self.active_polls: dict[int, dict] = {}
        self.poll_votes: dict[int, dict[int, int]] = {}  # poll_id -> {user_id -> option_index}
        self._poll_counter = 1
    
    poll_group = app_commands.Group(name="poll", description="📊 Poll commands")
    
    @poll_group.command(name="create", description="📊 Create a poll")
    @app_commands.describe(
        question="The poll question",
        option1="First option",
        option2="Second option",
        option3="Third option (optional)",
        option4="Fourth option (optional)",
        option5="Fifth option (optional)",
        duration="How long the poll runs (e.g. 1h, 1d, 30m). Leave empty for no expiry.",
        channel="Which channel to post the poll in",
        multiple_choice="Allow users to vote for multiple options",
        anonymous="Hide who voted for what (shows only counts)",
        image="URL to an image to show with the poll"
    )
    @is_mod()
    async def poll_create(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: Optional[str] = None,
        option4: Optional[str] = None,
        option5: Optional[str] = None,
        duration: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None,
        multiple_choice: bool = False,
        anonymous: bool = False,
        image: Optional[str] = None
    ):
        """Create a new poll"""
        
        # Collect options
        options = [option1, option2]
        for opt in [option3, option4, option5]:
            if opt:
                options.append(opt)
        
        if len(options) < 2:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Enough Options", "Polls need at least 2 options."),
                ephemeral=True
            )
        
        # Parse duration if provided
        ends_at = None
        if duration:
            from utils.time_parser import parse_time
            parsed = parse_time(duration)
            if parsed:
                delta, human_duration = parsed
                ends_at = datetime.now(timezone.utc) + delta
            else:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Invalid Duration", "Please use a format like `1d`, `12h`, `30m`"),
                    ephemeral=True
                )
        
        # Default to current channel
        if channel is None:
            channel = interaction.channel
        
        # Create poll data
        poll_id = self._poll_counter
        self._poll_counter += 1
        
        poll_data = {
            "id": poll_id,
            "guild_id": interaction.guild_id,
            "channel_id": channel.id,
            "question": question,
            "options": options,
            "creator_id": interaction.user.id,
            "created_at": datetime.now(timezone.utc),
            "ends_at": ends_at,
            "multiple_choice": multiple_choice,
            "anonymous": anonymous,
            "image_url": image,
            "ended": False
        }
        
        # Create embed
        embed = self._create_poll_embed(poll_data, vote_counts={})
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Send poll message
            view = PollView(poll_data, ended=False)
            msg = await channel.send(embed=embed, view=view)
            
            # Store poll data
            poll_data["message_id"] = msg.id
            self.active_polls[poll_id] = poll_data
            self.poll_votes[poll_id] = {}
            
            # Start auto-end task if duration specified
            if ends_at:
                asyncio.create_task(self._auto_end_poll(poll_id, ends_at))
            
            await interaction.followup.send(
                embed=ModEmbed.success(
                    "Poll Created",
                    f"Poll ID: `{poll_id}`\nPosted in {channel.mention}\n{msg.jump_url}"
                ),
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.followup.send(
                embed=ModEmbed.error("Forbidden", f"I don't have permission to post in {channel.mention}."),
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                embed=ModEmbed.error("Failed", f"Failed to create poll: {e}"),
                ephemeral=True
            )
    
    def _create_poll_embed(self, poll_data: dict, vote_counts: dict[int, int]) -> discord.Embed:
        """Create the poll embed"""
        question = poll_data["question"]
        options = poll_data["options"]
        ends_at = poll_data.get("ends_at")
        ended = poll_data.get("ended", False)
        
        # Build description
        description = ""
        total_votes = sum(vote_counts.values())
        
        # Emojis for options
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        
        for i, option in enumerate(options):
            votes = vote_counts.get(i, 0)
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            
            # Create progress bar
            bar_length = 10
            filled = int(percentage / 10)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            description += f"{emojis[i]} **{option}**\n"
            description += f"{bar} {percentage:.1f}% ({votes} vote{'s' if votes != 1 else ''})\n\n"
        
        # Create embed
        embed = discord.Embed(
            title=f"📊 {question}",
            description=description or "No votes yet",
            color=Config.COLOR_INFO if not ended else 0x808080,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add footer
        footer_text = f"Poll ID: {poll_data['id']} | Total Votes: {total_votes}"
        if ends_at and not ended:
            footer_text += f" | Ends: "
            embed.timestamp = ends_at
        elif ended:
            footer_text += " | Poll Ended"
        
        embed.set_footer(text=footer_text)
        
        # Add image if provided
        if poll_data.get("image_url"):
            embed.set_image(url=poll_data["image_url"])
        
        # Add info field
        info = []
        if poll_data.get("multiple_choice"):
            info.append("🔢 Multiple choice allowed")
        if poll_data.get("anonymous"):
            info.append("🕵️ Anonymous voting")
        
        if info:
            embed.add_field(name="ℹ️ Info", value="\n".join(info), inline=False)
        
        return embed
    
    async def _handle_vote(self, interaction: discord.Interaction, poll_id: int, option_index: int):
        """Handle a vote on a poll"""
        poll_data = self.active_polls.get(poll_id)
        
        if not poll_data:
            return await interaction.response.send_message(
                "This poll is no longer active.",
                ephemeral=True
            )
        
        if poll_data.get("ended"):
            return await interaction.response.send_message(
                "This poll has ended.",
                ephemeral=True
            )
        
        user_id = interaction.user.id
        votes = self.poll_votes.get(poll_id, {})
        
        # Check if user already voted
        if user_id in votes:
            if poll_data.get("multiple_choice"):
                # Toggle vote in multiple choice
                current = votes[user_id]
                if isinstance(current, list):
                    if option_index in current:
                        current.remove(option_index)
                    else:
                        current.append(option_index)
                else:
                    votes[user_id] = [current, option_index] if current != option_index else [option_index]
            else:
                # Change vote in single choice
                if votes[user_id] == option_index:
                    # Remove vote if clicking same option
                    del votes[user_id]
                    await interaction.response.send_message(
                        "Vote removed!",
                        ephemeral=True
                    )
                else:
                    votes[user_id] = option_index
                    await interaction.response.send_message(
                        f"Vote changed to **{poll_data['options'][option_index]}**!",
                        ephemeral=True
                    )
        else:
            # New vote
            if poll_data.get("multiple_choice"):
                votes[user_id] = [option_index]
            else:
                votes[user_id] = option_index
            
            await interaction.response.send_message(
                f"Voted for **{poll_data['options'][option_index]}**!",
                ephemeral=True
            )
        
        self.poll_votes[poll_id] = votes
        
        # Update poll message
        await self._update_poll_message(poll_id)
    
    async def _update_poll_message(self, poll_id: int):
        """Update the poll message with current vote counts"""
        poll_data = self.active_polls.get(poll_id)
        if not poll_data:
            return
        
        votes = self.poll_votes.get(poll_id, {})
        
        # Count votes for each option
        vote_counts = {i: 0 for i in range(len(poll_data["options"]))}
        
        for user_vote in votes.values():
            if isinstance(user_vote, list):
                # Multiple choice
                for opt_idx in user_vote:
                    vote_counts[opt_idx] = vote_counts.get(opt_idx, 0) + 1
            else:
                # Single choice
                vote_counts[user_vote] = vote_counts.get(user_vote, 0) + 1
        
        # Update embed
        embed = self._create_poll_embed(poll_data, vote_counts)
        view = PollView(poll_data, ended=poll_data.get("ended", False))
        
        try:
            channel = self.bot.get_channel(poll_data["channel_id"])
            if channel:
                msg = await channel.fetch_message(poll_data["message_id"])
                await msg.edit(embed=embed, view=view)
        except Exception as e:
            print(f"[Polls] Failed to update poll {poll_id}: {e}")
    
    async def _auto_end_poll(self, poll_id: int, ends_at: datetime):
        """Automatically end a poll after duration"""
        now = datetime.now(timezone.utc)
        wait_seconds = (ends_at - now).total_seconds()
        
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)
        
        await self._end_poll(poll_id)
    
    async def _end_poll(self, poll_id: int):
        """End a poll and show results"""
        poll_data = self.active_polls.get(poll_id)
        if not poll_data or poll_data.get("ended"):
            return
        
        poll_data["ended"] = True
        
        # Update message one last time
        await self._update_poll_message(poll_id)
        
        # Send results message
        votes = self.poll_votes.get(poll_id, {})
        vote_counts = {i: 0 for i in range(len(poll_data["options"]))}
        
        for user_vote in votes.values():
            if isinstance(user_vote, list):
                for opt_idx in user_vote:
                    vote_counts[opt_idx] = vote_counts.get(opt_idx, 0) + 1
            else:
                vote_counts[user_vote] = vote_counts.get(user_vote, 0) + 1
        
        # Find winner(s)
        max_votes = max(vote_counts.values()) if vote_counts.values() else 0
        winners = [poll_data["options"][i] for i, count in vote_counts.items() if count == max_votes]
        
        try:
            channel = self.bot.get_channel(poll_data["channel_id"])
            if channel:
                msg = await channel.fetch_message(poll_data["message_id"])
                
                result_text = f"🏆 **Win ner{'s' if len(winners) > 1 else ''}:** {', '.join(f'**{w}**' for w in winners)}"
                if max_votes > 0:
                    result_text += f" ({max_votes} vote{'s' if max_votes != 1 else ''})"
                
                await msg.reply(f"📊 **Poll Ended!**\n{result_text}")
        except Exception as e:
            print(f"[Polls] Failed to post poll results for {poll_id}: {e}")
    
    @poll_group.command(name="end", description="🛑 End a poll early")
    @app_commands.describe(poll_id="The poll ID to end")
    @is_mod()
    async def poll_end(self, interaction: discord.Interaction, poll_id: int):
        """Manually end a poll"""
        poll_data = self.active_polls.get(poll_id)
        
        if not poll_data:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Found", "I couldn't find that poll."),
                ephemeral=True
            )
        
        if poll_data.get("ended"):
            return await interaction.response.send_message(
                embed=ModEmbed.info("Already Ended", f"Poll ID: `{poll_id}`"),
                ephemeral=True
            )
        
        await self._end_poll(poll_id)
        
        await interaction.response.send_message(
            embed=ModEmbed.success("Poll Ended", f"Poll ID: `{poll_id}` has been ended."),
            ephemeral=True
        )
    
    @poll_group.command(name="results", description="📊 View poll results")
    @app_commands.describe(poll_id="The poll ID")
    async def poll_results(self, interaction: discord.Interaction, poll_id: int):
        """View detailed poll results"""
        poll_data = self.active_polls.get(poll_id)
        
        if not poll_data:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Found", "I couldn't find that poll."),
                ephemeral=True
            )
        
        votes = self.poll_votes.get(poll_id, {})
        vote_counts = {i: 0 for i in range(len(poll_data["options"]))}
        voter_lists = {i: [] for i in range(len(poll_data["options"]))}
        
        # Count votes and collect voters
        for user_id, user_vote in votes.items():
            if isinstance(user_vote, list):
                for opt_idx in user_vote:
                    vote_counts[opt_idx] = vote_counts.get(opt_idx, 0) + 1
                    voter_lists[opt_idx].append(user_id)
            else:
                vote_counts[user_vote] = vote_counts.get(user_vote, 0) + 1
                voter_lists[user_vote].append(user_id)
        
        # Create results embed
        embed = discord.Embed(
            title=f"📊 Poll Results: {poll_data['question']}",
            description=f"Poll ID: `{poll_id}`",
            color=Config.COLOR_INFO,
            timestamp=datetime.now(timezone.utc)
        )
        
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        total_votes = sum(vote_counts.values())
        
        for i, option in enumerate(poll_data["options"]):
            votes_count = vote_counts.get(i, 0)
            percentage = (votes_count / total_votes * 100) if total_votes > 0 else 0
            
            value = f"**{votes_count}** vote{'s' if votes_count != 1 else ''} ({percentage:.1f}%)"
            
            # Show voters if not anonymous
            if not poll_data.get("anonymous") and voter_lists[i]:
                voters = voter_lists[i][:10]  # Limit to first 10
                voter_mentions = [f"<@{uid}>" for uid in voters]
                value += f"\n{', '.join(voter_mentions)}"
                if len(voter_lists[i]) > 10:
                    value += f" +{len(voter_lists[i]) - 10} more"
            
            embed.add_field(
                name=f"{emojis[i]} {option}",
                value=value,
                inline=False
            )
        
        embed.set_footer(text=f"Total Votes: {total_votes} | Status: {'Ended' if poll_data.get('ended') else 'Active'}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Polls(bot))
