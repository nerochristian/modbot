"""Interactive Discord polls with private results and public voting controls."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Set

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_mod
from utils.embeds import ModEmbed


class PollOptionButton(discord.ui.Button):
    def __init__(self, poll_id: int, option_index: int, option_text: str, *, disabled: bool = False):
        super().__init__(
            label=option_text[:80],
            style=discord.ButtonStyle.secondary,
            custom_id=f"poll:{poll_id}:option:{option_index}",
            row=option_index // 5,
            disabled=disabled,
        )
        self.poll_id = poll_id
        self.option_index = option_index

    async def callback(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("Polls")
        if isinstance(cog, Polls):
            await cog.handle_vote(interaction, self.poll_id, self.option_index)


class PollResultsButton(discord.ui.Button):
    def __init__(self, poll_id: int, *, disabled: bool = False):
        super().__init__(
            label="Show results",
            style=discord.ButtonStyle.primary,
            custom_id=f"poll:{poll_id}:results",
            row=2,
            disabled=disabled,
        )
        self.poll_id = poll_id

    async def callback(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("Polls")
        if isinstance(cog, Polls):
            await cog.show_results(interaction, self.poll_id)


class PollRemoveVoteButton(discord.ui.Button):
    def __init__(self, poll_id: int, *, disabled: bool = False):
        super().__init__(
            label="Remove vote",
            style=discord.ButtonStyle.secondary,
            custom_id=f"poll:{poll_id}:remove",
            row=2,
            disabled=disabled,
        )
        self.poll_id = poll_id

    async def callback(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("Polls")
        if isinstance(cog, Polls):
            await cog.remove_vote(interaction, self.poll_id)


class PollView(discord.ui.View):
    """A stable public view; user-specific state is delivered ephemerally."""

    def __init__(self, poll: dict, *, disabled: bool = False):
        super().__init__(timeout=None)
        poll_id = int(poll["id"])
        for index, option in enumerate(poll["options"]):
            self.add_item(PollOptionButton(poll_id, index, option, disabled=disabled))
        self.add_item(PollResultsButton(poll_id, disabled=disabled))
        self.add_item(PollRemoveVoteButton(poll_id, disabled=disabled))


class Polls(commands.Cog):
    """Create and operate polls with single- or multiple-choice voting."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_polls: Dict[int, dict] = {}
        self.poll_votes: Dict[int, Dict[int, Set[int]]] = {}
        self._poll_counter = 1

    poll_group = app_commands.Group(name="poll", description="Poll commands")

    @poll_group.command(name="create", description="Create a poll")
    @app_commands.describe(
        question="The poll question",
        option1="First option",
        option2="Second option",
        option3="Third option (optional)",
        option4="Fourth option (optional)",
        option5="Fifth option (optional)",
        option6="Sixth option (optional)",
        option7="Seventh option (optional)",
        option8="Eighth option (optional)",
        option9="Ninth option (optional)",
        option10="Tenth option (optional)",
        duration="How long the poll runs in hours (1-168)",
        channel="Channel to post the poll in",
        multiple_choice="Allow each member to select multiple options",
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
        option6: Optional[str] = None,
        option7: Optional[str] = None,
        option8: Optional[str] = None,
        option9: Optional[str] = None,
        option10: Optional[str] = None,
        duration: Optional[int] = 24,
        channel: Optional[discord.TextChannel] = None,
        multiple_choice: bool = False,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        target = channel or interaction.channel
        if not isinstance(target, discord.abc.Messageable):
            await interaction.response.send_message("Choose a text channel for this poll.", ephemeral=True)
            return

        options = [value.strip() for value in (option1, option2, option3, option4, option5, option6, option7, option8, option9, option10) if value and value.strip()]
        if len({value.casefold() for value in options}) != len(options):
            await interaction.response.send_message(
                embed=ModEmbed.error("Duplicate Options", "Every poll option must be different."),
                ephemeral=True,
            )
            return

        poll_id = self._poll_counter
        self._poll_counter += 1
        hours = max(1, min(168, int(duration or 24)))
        poll = {
            "id": poll_id,
            "guild_id": interaction.guild.id,
            "channel_id": target.id,
            "question": question.strip()[:300],
            "options": options,
            "creator_id": interaction.user.id,
            "created_at": datetime.now(timezone.utc),
            "ends_at": datetime.now(timezone.utc) + timedelta(hours=hours),
            "multiple_choice": multiple_choice,
            "ended": False,
        }

        await interaction.response.defer(ephemeral=True)
        try:
            message = await target.send(embed=self.build_embed(poll), view=PollView(poll))
        except discord.HTTPException as exc:
            await interaction.followup.send(
                embed=ModEmbed.error("Poll Failed", f"Docket could not post that poll: {exc}"),
                ephemeral=True,
            )
            return

        poll["message_id"] = message.id
        self.active_polls[poll_id] = poll
        self.poll_votes[poll_id] = {}
        asyncio.create_task(self.auto_end_poll(poll_id), name=f"poll-end-{poll_id}")
        await interaction.followup.send(
            embed=ModEmbed.success("Poll Created", f"Poll `{poll_id}` is live in {target.mention}.\n{message.jump_url}"),
            ephemeral=True,
        )

    def vote_counts(self, poll_id: int, option_count: int) -> list[int]:
        votes = self.poll_votes.get(poll_id, {})
        return [sum(index in selected for selected in votes.values()) for index in range(option_count)]

    def build_embed(
        self,
        poll: dict,
        *,
        show_results: bool = False,
        selected: Optional[Set[int]] = None,
    ) -> discord.Embed:
        options = poll["options"]
        votes = self.poll_votes.get(poll["id"], {})
        counts = self.vote_counts(poll["id"], len(options))
        voter_count = len(votes)
        lines = [
            f"**{poll['question']}**",
            f"*Select {'one or more answers' if poll.get('multiple_choice') else 'one answer'}*",
            "",
        ]
        for index, option in enumerate(options):
            marker = "✅ " if selected and index in selected else ""
            lines.append(f"{marker}**{option}**")
            if show_results:
                percentage = counts[index] / voter_count * 100 if voter_count else 0
                lines.append(f"`{counts[index]} vote{'s' if counts[index] != 1 else ''} · {percentage:.0f}%`")
            lines.append("")

        ends_at = poll.get("ends_at")
        if poll.get("ended"):
            time_text = "Ended"
        elif isinstance(ends_at, datetime):
            seconds = max(0, int((ends_at - datetime.now(timezone.utc)).total_seconds()))
            time_text = f"{seconds // 3600}h left" if seconds >= 3600 else f"{max(1, seconds // 60)}m left"
        else:
            time_text = "No time limit"
        lines.append(f"{voter_count} vote{'s' if voter_count != 1 else ''} · {time_text}")
        return discord.Embed(description="\n".join(lines), color=0x5865F2)

    async def handle_vote(self, interaction: discord.Interaction, poll_id: int, option_index: int) -> None:
        poll = self.active_polls.get(poll_id)
        if poll is None or poll.get("ended"):
            await interaction.response.send_message("This poll is no longer active.", ephemeral=True)
            return
        if option_index < 0 or option_index >= len(poll["options"]):
            await interaction.response.send_message("That option no longer exists.", ephemeral=True)
            return

        user_votes = self.poll_votes[poll_id]
        selected = set(user_votes.get(interaction.user.id, set()))
        if poll.get("multiple_choice"):
            selected.symmetric_difference_update({option_index})
        else:
            selected = {option_index}
        if selected:
            user_votes[interaction.user.id] = selected
        else:
            user_votes.pop(interaction.user.id, None)

        await interaction.response.defer(ephemeral=True)
        await self.refresh_public_message(interaction, poll)
        labels = ", ".join(poll["options"][index] for index in sorted(selected))
        await interaction.followup.send(
            f"Vote updated: **{labels}**" if labels else "Your vote was removed.",
            ephemeral=True,
        )

    async def remove_vote(self, interaction: discord.Interaction, poll_id: int) -> None:
        poll = self.active_polls.get(poll_id)
        if poll is None or poll.get("ended"):
            await interaction.response.send_message("This poll is no longer active.", ephemeral=True)
            return
        removed = self.poll_votes[poll_id].pop(interaction.user.id, None)
        await interaction.response.defer(ephemeral=True)
        if removed:
            await self.refresh_public_message(interaction, poll)
        await interaction.followup.send(
            "Your vote was removed." if removed else "You have not voted in this poll.",
            ephemeral=True,
        )

    async def show_results(self, interaction: discord.Interaction, poll_id: int) -> None:
        poll = self.active_polls.get(poll_id)
        if poll is None:
            await interaction.response.send_message("This poll is no longer available.", ephemeral=True)
            return
        selected = self.poll_votes.get(poll_id, {}).get(interaction.user.id, set())
        await interaction.response.send_message(
            embed=self.build_embed(poll, show_results=True, selected=selected),
            ephemeral=True,
        )

    async def refresh_public_message(self, interaction: discord.Interaction, poll: dict) -> None:
        if interaction.message is not None:
            await interaction.message.edit(embed=self.build_embed(poll), view=PollView(poll))

    async def auto_end_poll(self, poll_id: int) -> None:
        poll = self.active_polls.get(poll_id)
        if poll is None:
            return
        wait_seconds = max(0, (poll["ends_at"] - datetime.now(timezone.utc)).total_seconds())
        await asyncio.sleep(wait_seconds)
        await self.end_poll(poll_id)

    async def end_poll(self, poll_id: int) -> bool:
        poll = self.active_polls.get(poll_id)
        if poll is None or poll.get("ended"):
            return False
        poll["ended"] = True
        channel = self.bot.get_channel(poll["channel_id"])
        if not isinstance(channel, discord.abc.Messageable):
            return True
        try:
            message = await channel.fetch_message(poll["message_id"])
            counts = self.vote_counts(poll_id, len(poll["options"]))
            top = max(counts, default=0)
            winners = [poll["options"][index] for index, count in enumerate(counts) if count == top and top > 0]
            await message.edit(embed=self.build_embed(poll, show_results=True), view=PollView(poll, disabled=True))
            result = f"🏆 Winner: **{' / '.join(winners)}**" if winners else "Poll ended with no votes."
            await message.reply(result)
        except discord.HTTPException:
            pass
        return True

    @poll_group.command(name="end", description="End a poll early")
    @app_commands.describe(poll_id="The poll ID")
    @is_mod()
    async def poll_end(self, interaction: discord.Interaction, poll_id: int) -> None:
        if not await self.end_poll(poll_id):
            await interaction.response.send_message(
                embed=ModEmbed.error("Not Active", "That poll does not exist or has already ended."),
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=ModEmbed.success("Poll Ended", f"Poll `{poll_id}` is now closed."),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Polls(bot))
