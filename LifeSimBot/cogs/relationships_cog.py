from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.relationships_service import RelationshipsService
from utils.checks import safe_defer, safe_reply
from utils.format import progress_bar


class RelationshipsCog(commands.Cog):
    """Friendships, dating, and relationship stats."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.service = RelationshipsService(bot.db)

    # -------- View relationships --------

    @app_commands.command(name="relationships", description="❤️ View your relationships")
    async def relationships(self, interaction: discord.Interaction):
        await safe_defer(interaction, ephemeral=True)

        user_id = str(interaction.user.id)
        rels = self.service.list_relationships(user_id)

        if not rels:
            return await safe_reply(
                interaction,
                content="You don't have any tracked relationships yet. Use `/interact` or `/gift` to start.",
                ephemeral=True,
            )

        embed = discord.Embed(
            title=f"❤️ {interaction.user.display_name}'s Relationships",
            color=discord.Color.red(),
        )

        # show top 6
        for rel in rels[:6]:
            member = None
            if interaction.guild:
                try:
                    member = interaction.guild.get_member(int(rel.target_id))
                except Exception:
                    member = None

            name = member.display_name if member else f"User {rel.target_id}"
            bar = progress_bar(rel.affection, 200, length=10)

            embed.add_field(
                name=f"{name} — {rel.status.title()}",
                value=f"{bar} `{rel.affection}` affection",
                inline=False,
            )

        await safe_reply(interaction, embed=embed, ephemeral=True)

    # -------- Interact --------

    @app_commands.command(name="interact", description="💬 Interact with someone to build affection")
    @app_commands.describe(
        user="The person you want to interact with",
        interaction_type="Type of interaction",
    )
    @app_commands.choices(
        interaction_type=[
            app_commands.Choice(name="Talk", value="talk"),
            app_commands.Choice(name="Hang Out", value="hangout"),
            app_commands.Choice(name="Flirt", value="flirt"),
        ]
    )
    async def interact(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        interaction_type: app_commands.Choice[str],
    ):
        await safe_defer(interaction)

        if user.id == interaction.user.id:
            return await safe_reply(
                interaction,
                content="You can't interact with yourself for affection.",
                ephemeral=True,
            )

        user_id = str(interaction.user.id)
        target_id = str(user.id)

        rel = self.service.get_relationship(user_id, target_id)
        can, remaining = rel.can_interact()
        if not can:
            minutes = max(1, remaining // 60)
            return await safe_reply(
                interaction,
                content=f"That relationship needs a breather. Try again in about {minutes} minutes.",
                ephemeral=True,
            )

        rel_after, _ = self.service.apply_interaction(
            user_id=user_id,
            target_id=target_id,
            interaction_type=interaction_type.value,  # type: ignore
        )

        bar = progress_bar(rel_after.affection, 200, length=10)

        embed = discord.Embed(
            title="💬 Interaction",
            description=f"You {interaction_type.name.lower()} with **{user.display_name}**.",
            color=discord.Color.red(),
        )
        embed.add_field(
            name="Affection",
            value=f"{bar} `{rel_after.affection}`",
            inline=False,
        )
        embed.add_field(
            name="Status",
            value=rel_after.status.title(),
            inline=True,
        )

        await safe_reply(interaction, embed=embed)

    # -------- Gift --------

    @app_commands.command(name="gift", description="🎁 Give a gift to boost affection")
    @app_commands.describe(
        user="The person you want to gift",
        amount="How much money the gift is worth",
    )
    async def gift(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: int,
    ):
        await safe_defer(interaction)

        if amount <= 0:
            return await safe_reply(
                interaction,
                content="Gift amount must be positive.",
                ephemeral=True,
            )

        if user.id == interaction.user.id:
            return await safe_reply(
                interaction,
                content="Gifting yourself does not count.",
                ephemeral=True,
            )

        db = self.bot.db
        user_id = str(interaction.user.id)
        target_id = str(user.id)

        u = db.getuser(user_id)
        balance = int(u.get("balance", 0))
        if balance < amount:
            return await safe_reply(
                interaction,
                content=f"You don't have enough money for that gift. You have {balance}, need {amount}.",
                ephemeral=True,
            )

        db.removebalance(user_id, amount)

        rel_after = self.service.apply_gift(
            user_id=user_id,
            target_id=target_id,
            value=amount,
        )

        bar = progress_bar(rel_after.affection, 200, length=10)

        embed = discord.Embed(
            title="🎁 Gift Sent",
            description=f"You sent a gift worth `{amount}` to **{user.display_name}**.",
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="Affection",
            value=f"{bar} `{rel_after.affection}`",
            inline=False,
        )
        embed.add_field(
            name="Status",
            value=rel_after.status.title(),
            inline=True,
        )

        await safe_reply(interaction, embed=embed)

    # -------- Ask out --------

    @app_commands.command(name="askout", description="💖 Ask someone out")
    @app_commands.describe(user="Who you want to ask out")
    async def askout(self, interaction: discord.Interaction, user: discord.Member):
        await safe_defer(interaction)

        if user.id == interaction.user.id:
            return await safe_reply(
                interaction,
                content="You cannot date yourself.",
                ephemeral=True,
            )

        user_id = str(interaction.user.id)
        target_id = str(user.id)

        success, rel, message = self.service.askout(user_id, target_id)

        color = discord.Color.green() if success else discord.Color.red()
        embed = discord.Embed(
            title="💖 Ask Out",
            description=message,
            color=color,
        )
        bar = progress_bar(rel.affection, 200, length=10)
        embed.add_field(
            name="Affection",
            value=f"{bar} `{rel.affection}`",
            inline=False,
        )
        embed.add_field(
            name="Status",
            value=rel.status.title(),
            inline=True,
        )

        await safe_reply(interaction, embed=embed)

    # -------- Breakup --------

    @app_commands.command(name="breakup", description="💔 End a relationship")
    @app_commands.describe(user="Who you want to break up with")
    async def breakup(self, interaction: discord.Interaction, user: discord.Member):
        await safe_defer(interaction)

        if user.id == interaction.user.id:
            return await safe_reply(
                interaction,
                content="You can't break up with yourself.",
                ephemeral=True,
            )

        user_id = str(interaction.user.id)
        target_id = str(user.id)

        rel = self.service.breakup(user_id, target_id)
        bar = progress_bar(rel.affection, 200, length=10)

        embed = discord.Embed(
            title="💔 Breakup",
            description=f"You ended your relationship with **{user.display_name}**.",
            color=discord.Color.dark_red(),
        )
        embed.add_field(
            name="Affection",
            value=f"{bar} `{rel.affection}`",
            inline=False,
        )
        embed.add_field(
            name="Status",
            value=rel.status.title(),
            inline=True,
        )

        await safe_reply(interaction, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(RelationshipsCog(bot))
