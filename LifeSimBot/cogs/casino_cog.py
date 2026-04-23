from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from ..views.casino_views import CasinoMenuV2View
from ..utils.format import money
from ..utils.checks import safe_defer, safe_reply


logger = logging.getLogger("LifeSimBot.Casino")


class CasinoCog(commands.Cog):
    """Casino gambling commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="casino", description="🎰 View all casino games")
    async def casino(self, interaction: discord.Interaction):
        await safe_defer(interaction, ephemeral=True)

        embed = discord.Embed(
            title="🎰 Casino Games",
            description="Welcome to the casino! Here are all available games:",
            color=discord.Color.gold(),
        )

        embed.add_field(
            name="🎰 Slots",
            value=(
                "**How to play:** Spin the reels!\n"
                "**Payouts:**\n"
                "└ 3 matching = 2x-50x\n"
                "└ 7️⃣7️⃣7️⃣ = 50x jackpot!"
            ),
            inline=False,
        )

        embed.add_field(
            name="🃏 Blackjack",
            value=(
                "**How to play:** Get 21 or closer than dealer\n"
                "**Payouts:**\n"
                "└ Win = 2x\n"
                "└ Blackjack = 2.5x\n"
                "└ Push = bet back"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎲 Roulette",
            value=(
                "**How to play:** Bet on number, color, or range\n"
                "**Payouts:**\n"
                "└ Number = 35x\n"
                "└ Color = 2x\n"
                "└ Range = 2x-3x"
            ),
            inline=False,
        )

        embed.add_field(
            name="🪙 Coinflip",
            value=(
                "**How to play:** Choose heads or tails\n"
                "**Payouts:**\n"
                "└ Win = 2x\n"
                "└ 50/50 odds"
            ),
            inline=False,
        )

        embed.add_field(
            name="💣 Minesweeper",
            value=(
                "**How to play:** Reveal safe cells, avoid mines!\n"
                "**Difficulties:**\n"
                "└ Easy (5x5, 5 mines) = 1.5x max\n"
                "└ Medium (6x6, 8 mines) = 2x max\n"
                "└ Hard (7x7, 12 mines) = 3x max\n"
                "**Cash out anytime!**"
            ),
            inline=False,
        )

        embed.add_field(
            name="💡 How to Play",
            value=(
                "Use `/gamble <amount>` to start!\n"
                "**Examples:**\n"
                "• `/gamble 100` - Choose game from menu\n"
                "• `/gamble 500 slots` - Play slots directly\n"
                "• `/gamble 1000 minesweeper_easy` - Play minesweeper"
            ),
            inline=False,
        )

        embed.set_footer(text="💰 Min bet: $10 | Max bet: $100,000 | Good luck!")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="gamble", description="🎰 Gamble your money at the casino")
    @app_commands.describe(
        amount="Amount to bet",
        game="Game to play (optional - leave blank for menu)",
    )
    @app_commands.choices(game=[
        app_commands.Choice(name="🎰 Slots", value="slots"),
        app_commands.Choice(name="🃏 Blackjack", value="blackjack"),
        app_commands.Choice(name="🪙 Coinflip", value="coinflip"),
        app_commands.Choice(name="🎲 Dice", value="dice"),
        app_commands.Choice(name="📈 Crash", value="crash"),
        app_commands.Choice(name="💣 Minesweeper (Easy)", value="minesweeper_easy"),
        app_commands.Choice(name="💣 Minesweeper (Medium)", value="minesweeper_medium"),
        app_commands.Choice(name="💣 Minesweeper (Hard)", value="minesweeper_hard"),
    ])
    async def gamble(
        self,
        interaction: discord.Interaction,
        amount: int,
        game: app_commands.Choice[str] | None = None,
    ):
        await safe_defer(interaction)

        db = getattr(self.bot, "db", None)
        if db is None:
            return await safe_reply(interaction, content="❌ Database not ready yet. Try again in a moment.", ephemeral=True)

        userid = str(interaction.user.id)
        u = db.getuser(userid)

        balance = int(u.get("balance", 0))
        game_value = game.value if isinstance(game, app_commands.Choice) else None

        # Validation
        if amount < 10:
            return await safe_reply(interaction, content="❌ Minimum bet is $10!")

        if amount > balance:
            return await safe_reply(
                interaction,
                content=f"❌ You only have {money(balance)}!",
            )

        if amount > 100000:
            return await safe_reply(interaction, content="❌ Maximum bet is $100,000!")

        # Show the V2 casino menu. Bet is charged only when the user presses Play.
        view = CasinoMenuV2View(self.bot, interaction.user, amount, preselect=game_value)
        msg = await safe_reply(interaction, view=view)
        if msg is not None:
            try:
                view.message = msg
            except Exception:
                pass
        return


async def setup(bot: commands.Bot):
    await bot.add_cog(CasinoCog(bot))
