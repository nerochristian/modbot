# cogs/crypto_cog.py

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands, tasks

from views.crypto_views import CryptoMarketView, CryptoPortfolioView, CryptoTradeView
from data.crypto import CRYPTOCURRENCIES, price_simulator
from utils.checks import safe_defer, safe_reply
from utils.format import money


class CryptoCog(commands.Cog):
    """Cryptocurrency trading system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.price_updater.start()

    def cog_unload(self):
        self.price_updater.cancel()

    @tasks.loop(minutes=5)
    async def price_updater(self):
        """Update crypto prices every 5 minutes."""
        price_simulator.update_prices()
        print("[CRYPTO] Prices updated")

    @price_updater.before_loop
    async def before_price_updater(self):
        await self.bot.wait_until_ready()

    # ============= CRYPTO GROUP =============

    crypto_group = app_commands.Group(
        name="crypto",
        description="💎 Cryptocurrency trading commands"
    )

    @crypto_group.command(name="market", description="💎 View crypto market prices")
    async def market(self, interaction: discord.Interaction):
        """View the crypto market."""
        await safe_defer(interaction, ephemeral=True)

        view = CryptoMarketView(self.bot, interaction.user)
        embed = view.create_embed()

        await safe_reply(interaction, embed=embed, view=view, ephemeral=True)

    @crypto_group.command(name="portfolio", description="📊 View your crypto portfolio")
    async def portfolio(self, interaction: discord.Interaction):
        """View your crypto holdings."""
        await safe_defer(interaction, ephemeral=True)

        view = CryptoPortfolioView(self.bot, interaction.user)
        embed = view.create_embed()

        await safe_reply(interaction, embed=embed, view=view, ephemeral=True)

    @crypto_group.command(name="buy", description="💰 Buy cryptocurrency")
    @app_commands.describe(
        crypto="Cryptocurrency symbol (BTC, ETH, DOGE, etc.)",
        amount="Amount to buy (in USD or crypto amount)"
    )
    async def buy(self, interaction: discord.Interaction, crypto: str, amount: float):
        """Buy cryptocurrency."""
        await safe_defer(interaction)

        # Find crypto
        crypto_id = crypto.lower()
        crypto_data = CRYPTOCURRENCIES.get(crypto_id)

        if not crypto_data:
            # Try to find by symbol
            for cid, cdata in CRYPTOCURRENCIES.items():
                if cdata["symbol"].lower() == crypto.lower():
                    crypto_id = cid
                    crypto_data = cdata
                    break

        if not crypto_data:
            available = ", ".join([c["symbol"] for c in CRYPTOCURRENCIES.values()])
            return await safe_reply(
                interaction,
                content=f"❌ Cryptocurrency **{crypto}** not found!\n\n**Available:** {available}"
            )

        if amount <= 0:
            return await safe_reply(
                interaction,
                content="❌ Amount must be greater than 0!"
            )

        # Show confirmation
        view = CryptoTradeView(self.bot, interaction.user, crypto_id, amount, "buy")
        embed = view.create_embed()

        await safe_reply(interaction, embed=embed, view=view)

    @crypto_group.command(name="sell", description="💸 Sell cryptocurrency")
    @app_commands.describe(
        crypto="Cryptocurrency symbol (BTC, ETH, DOGE, etc.)",
        amount="Amount to sell"
    )
    async def sell(self, interaction: discord.Interaction, crypto: str, amount: float):
        """Sell cryptocurrency."""
        await safe_defer(interaction)

        # Find crypto
        crypto_id = crypto.lower()
        crypto_data = CRYPTOCURRENCIES.get(crypto_id)

        if not crypto_data:
            # Try to find by symbol
            for cid, cdata in CRYPTOCURRENCIES.items():
                if cdata["symbol"].lower() == crypto.lower():
                    crypto_id = cid
                    crypto_data = cdata
                    break

        if not crypto_data:
            available = ", ".join([c["symbol"] for c in CRYPTOCURRENCIES.values()])
            return await safe_reply(
                interaction,
                content=f"❌ Cryptocurrency **{crypto}** not found!\n\n**Available:** {available}"
            )

        if amount <= 0:
            return await safe_reply(
                interaction,
                content="❌ Amount must be greater than 0!"
            )

        # Show confirmation
        view = CryptoTradeView(self.bot, interaction.user, crypto_id, amount, "sell")
        embed = view.create_embed()

        await safe_reply(interaction, embed=embed, view=view)

    @crypto_group.command(name="price", description="💵 Check current price of a crypto")
    @app_commands.describe(crypto="Cryptocurrency symbol")
    async def price(self, interaction: discord.Interaction, crypto: str):
        """Check crypto price."""
        await safe_defer(interaction, ephemeral=True)

        # Find crypto
        crypto_id = crypto.lower()
        crypto_data = CRYPTOCURRENCIES.get(crypto_id)

        if not crypto_data:
            # Try to find by symbol
            for cid, cdata in CRYPTOCURRENCIES.items():
                if cdata["symbol"].lower() == crypto.lower():
                    crypto_id = cid
                    crypto_data = cdata
                    break

        if not crypto_data:
            available = ", ".join([c["symbol"] for c in CRYPTOCURRENCIES.values()])
            return await safe_reply(
                interaction,
                content=f"❌ Cryptocurrency **{crypto}** not found!\n\n**Available:** {available}",
                ephemeral=True
            )

        emoji = crypto_data["emoji"]
        name = crypto_data["name"]
        symbol = crypto_data["symbol"]
        description = crypto_data["description"]
        
        current_price = price_simulator.get_price(crypto_id)
        change_24h = price_simulator.get_24h_change(crypto_id)
        trend = price_simulator.get_trend(crypto_id)
        chart = price_simulator.get_price_chart(crypto_id)

        # Trend emoji
        if trend == "up":
            trend_emoji = "📈"
            change_color = "🟢"
        elif trend == "down":
            trend_emoji = "📉"
            change_color = "🔴"
        else:
            trend_emoji = "📊"
            change_color = "⚪"

        # Format price
        if current_price < 0.01:
            price_str = f"${current_price:.8f}"
        elif current_price < 1:
            price_str = f"${current_price:.4f}"
        else:
            price_str = money(current_price)

        embed = discord.Embed(
            title=f"{emoji} {name} ({symbol})",
            description=description,
            color=crypto_data["color"]
        )

        embed.add_field(
            name="💵 Current Price",
            value=price_str,
            inline=True
        )

        embed.add_field(
            name="📊 24h Change",
            value=f"{change_color} {change_24h:+.2f}%",
            inline=True
        )

        embed.add_field(
            name="📈 Trend",
            value=f"{trend_emoji} {trend.title()}",
            inline=True
        )

        embed.add_field(
            name="📊 Price Chart (24h)",
            value=chart,
            inline=False
        )

        embed.set_footer(text=f"Use /crypto buy {symbol} <amount> to invest")

        await safe_reply(interaction, embed=embed, ephemeral=True)

    @crypto_group.command(name="info", description="ℹ️ Learn about cryptocurrency trading")
    async def info(self, interaction: discord.Interaction):
        """Get info about crypto trading."""
        await safe_defer(interaction, ephemeral=True)

        embed = discord.Embed(
            title="💎 Cryptocurrency Trading Guide",
            description="Learn how to trade crypto in Life Simulator!",
            color=0x5865F2
        )

        embed.add_field(
            name="📚 What is Crypto?",
            value=(
                "Cryptocurrency is a digital currency that you can buy and sell for profit. "
                "Prices fluctuate constantly based on market volatility!"
            ),
            inline=False
        )

        embed.add_field(
            name="💰 How to Buy",
            value=(
                "**`/crypto buy <symbol> <amount>`**\n"
                "Example: `/crypto buy BTC 0.5`\n\n"
                "This buys 0.5 Bitcoin at current market price using your wallet balance."
            ),
            inline=False
        )

        embed.add_field(
            name="💸 How to Sell",
            value=(
                "**`/crypto sell <symbol> <amount>`**\n"
                "Example: `/crypto sell ETH 2`\n\n"
                "This sells 2 Ethereum at current market price and adds funds to your wallet."
            ),
            inline=False
        )

        embed.add_field(
            name="📊 Track Your Portfolio",
            value=(
                "**`/crypto portfolio`** - View all your holdings\n"
                "**`/crypto market`** - Browse available cryptos\n"
                "**`/crypto price <symbol>`** - Check current price"
            ),
            inline=False
        )

        embed.add_field(
            name="📈 Available Cryptocurrencies",
            value="\n".join([
                f"{c['emoji']} **{c['symbol']}** - {c['name']}"
                for c in CRYPTOCURRENCIES.values()
            ]),
            inline=False
        )

        embed.add_field(
            name="💡 Pro Tips",
            value=(
                "• Prices update every 5 minutes\n"
                "• Different cryptos have different volatility\n"
                "• DOGE, SHIB, PEPE are meme coins (very volatile!)\n"
                "• BTC, ETH are more stable\n"
                "• Buy low, sell high!\n"
                "• Don't invest more than you can afford to lose"
            ),
            inline=False
        )

        embed.add_field(
            name="⚠️ Risk Warning",
            value=(
                "Crypto prices are simulated and highly volatile. "
                "You can lose money! Trade responsibly."
            ),
            inline=False
        )

        embed.set_footer(text="Use /crypto market to start trading!")

        await safe_reply(interaction, embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CryptoCog(bot))
