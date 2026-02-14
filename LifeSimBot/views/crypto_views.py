# views/crypto_views.py

from __future__ import annotations

import discord
from typing import Optional
from datetime import datetime, timezone
import json

from utils.format import money
from data.crypto import CRYPTOCURRENCIES, price_simulator
from views.v2_embed import apply_v2_embed_layout


# ============= HELPER FUNCTIONS =============

def parse_crypto_portfolio(portfolio_data):
    """Parse crypto portfolio from DB (handles both dict and JSON string)."""
    if isinstance(portfolio_data, dict):
        return portfolio_data
    elif isinstance(portfolio_data, str):
        try:
            return json.loads(portfolio_data)
        except:
            return {}
    return {}


# ============= CONSTANTS =============

CRYPTO_COLORS = {
    "market": 0x5865F2,      # Blurple
    "portfolio": 0x57F287,   # Green
    "buy": 0x22C55E,         # Green
    "sell": 0xEF4444,        # Red
    "info": 0x3B82F6,        # Blue
}


# ============= CRYPTO MARKET VIEW =============

class CryptoMarketView(discord.ui.LayoutView):
    """Browse crypto market and prices."""

    def __init__(self, bot, user: discord.User):
        super().__init__(timeout=300)
        self.bot = bot
        self.user = user
        self.page = 0
        self.cryptos_per_page = 5

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This isn't your market! Use `/crypto market` to open your own.",
                ephemeral=True
            )
            return False
        return True

    def create_embed(self) -> discord.Embed:
        """Create market overview embed."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        balance = int(u.get("balance", 0))

        # Get cryptos for current page
        crypto_list = list(CRYPTOCURRENCIES.items())
        start = self.page * self.cryptos_per_page
        end = start + self.cryptos_per_page
        page_cryptos = crypto_list[start:end]

        embed = discord.Embed(
            title="💎 Crypto Market",
            description=f"**Your Balance:** {money(balance)}\n**Live Prices** • Updated every 5 minutes",
            color=CRYPTO_COLORS["market"]
        )

        for crypto_id, crypto_data in page_cryptos:
            emoji = crypto_data["emoji"]
            name = crypto_data["name"]
            symbol = crypto_data["symbol"]
            
            current_price = price_simulator.get_price(crypto_id)
            change_24h = price_simulator.get_24h_change(crypto_id)
            trend = price_simulator.get_trend(crypto_id)
            
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
            
            embed.add_field(
                name=f"{emoji} {name} ({symbol})",
                value=(
                    f"**Price:** {price_str}\n"
                    f"**24h:** {change_color} {change_24h:+.2f}%\n"
                    f"**Trend:** {trend_emoji}"
                ),
                inline=True
            )

        # Page info
        total_pages = (len(crypto_list) + self.cryptos_per_page - 1) // self.cryptos_per_page
        embed.set_footer(text=f"Page {self.page + 1}/{total_pages} • Use /crypto buy <coin> <amount> to invest")

        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, emoji="⬅️", row=0)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, emoji="➡️", row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        crypto_list = list(CRYPTOCURRENCIES.items())
        total_pages = (len(crypto_list) + self.cryptos_per_page - 1) // self.cryptos_per_page
        
        if self.page < total_pages - 1:
            self.page += 1
        
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Refresh Prices", style=discord.ButtonStyle.success, emoji="🔄", row=0)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        price_simulator.update_prices()
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="My Portfolio", style=discord.ButtonStyle.primary, emoji="📊", row=1)
    async def portfolio_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CryptoPortfolioView(self.bot, self.user)
        embed = view.create_embed()
        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.edit_message(view=view)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌", row=1)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💎 Market Closed",
            description="Crypto market closed. Use `/crypto market` to reopen!",
            color=CRYPTO_COLORS["market"]
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


# ============= CRYPTO PORTFOLIO VIEW =============

class CryptoPortfolioView(discord.ui.LayoutView):
    """View user's crypto portfolio."""

    def __init__(self, bot, user: discord.User):
        super().__init__(timeout=300)
        self.bot = bot
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    def create_embed(self) -> discord.Embed:
        """Create portfolio embed."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        
        # FIX: Parse crypto portfolio
        crypto_portfolio = parse_crypto_portfolio(u.get("crypto_portfolio", {}))
        balance = int(u.get("balance", 0))

        embed = discord.Embed(
            title=f"📊 {self.user.display_name}'s Crypto Portfolio",
            description=f"**Cash Balance:** {money(balance)}",
            color=CRYPTO_COLORS["portfolio"]
        )

        if not crypto_portfolio:
            embed.add_field(
                name="📦 Empty Portfolio",
                value="You don't own any crypto yet!\n\nUse `/crypto buy` to start investing.",
                inline=False
            )
            embed.set_footer(text="Start your crypto journey today!")
            return embed

        total_value = 0
        total_invested = 0

        for crypto_id, holdings in crypto_portfolio.items():
            crypto_data = CRYPTOCURRENCIES.get(crypto_id)
            if not crypto_data:
                continue

            amount = holdings.get("amount", 0)
            avg_buy_price = holdings.get("avg_price", 0)
            
            if amount <= 0:
                continue

            current_price = price_simulator.get_price(crypto_id)
            current_value = amount * current_price
            invested_value = amount * avg_buy_price
            profit_loss = current_value - invested_value
            profit_loss_pct = (profit_loss / invested_value * 100) if invested_value > 0 else 0

            total_value += current_value
            total_invested += invested_value

            emoji = crypto_data["emoji"]
            name = crypto_data["name"]
            symbol = crypto_data["symbol"]

            # Format price
            if current_price < 0.01:
                price_str = f"${current_price:.8f}"
            elif current_price < 1:
                price_str = f"${current_price:.4f}"
            else:
                price_str = money(current_price)

            # Profit/loss color
            if profit_loss > 0:
                pl_emoji = "🟢"
            elif profit_loss < 0:
                pl_emoji = "🔴"
            else:
                pl_emoji = "⚪"

            embed.add_field(
                name=f"{emoji} {name} ({symbol})",
                value=(
                    f"**Amount:** {amount:,.8f}\n"
                    f"**Value:** {money(current_value)}\n"
                    f"**P/L:** {pl_emoji} {money(profit_loss)} ({profit_loss_pct:+.2f}%)"
                ),
                inline=True
            )

        # Total portfolio stats
        total_pl = total_value - total_invested
        total_pl_pct = (total_pl / total_invested * 100) if total_invested > 0 else 0

        if total_pl > 0:
            pl_color = "🟢"
        elif total_pl < 0:
            pl_color = "🔴"
        else:
            pl_color = "⚪"

        embed.add_field(
            name="💰 Portfolio Summary",
            value=(
                f"**Total Value:** {money(total_value)}\n"
                f"**Total Invested:** {money(total_invested)}\n"
                f"**Total P/L:** {pl_color} {money(total_pl)} ({total_pl_pct:+.2f}%)"
            ),
            inline=False
        )

        embed.set_footer(text="Use /crypto sell to cash out")
        embed.set_thumbnail(url=self.user.display_avatar.url)

        return embed

    @discord.ui.button(label="Back to Market", style=discord.ButtonStyle.primary, emoji="💎", row=0)
    async def market_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CryptoMarketView(self.bot, self.user)
        embed = view.create_embed()
        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.edit_message(view=view)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.success, emoji="🔄", row=0)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌", row=0)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📊 Portfolio Closed",
            description="Portfolio closed. Use `/crypto portfolio` to reopen!",
            color=CRYPTO_COLORS["portfolio"]
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


# ============= CRYPTO TRADE CONFIRMATION =============

class CryptoTradeView(discord.ui.LayoutView):
    """Confirm buy/sell crypto transaction."""

    def __init__(self, bot, user: discord.User, crypto_id: str, amount: float, trade_type: str):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.crypto_id = crypto_id
        self.amount = amount
        self.trade_type = trade_type  # "buy" or "sell"
        self.crypto_data = CRYPTOCURRENCIES.get(crypto_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    def create_embed(self) -> discord.Embed:
        """Create trade confirmation embed."""
        if not self.crypto_data:
            return discord.Embed(
                title="❌ Invalid Crypto",
                description="This cryptocurrency doesn't exist.",
                color=CRYPTO_COLORS["sell"]
            )

        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        balance = int(u.get("balance", 0))

        emoji = self.crypto_data["emoji"]
        name = self.crypto_data["name"]
        symbol = self.crypto_data["symbol"]
        
        current_price = price_simulator.get_price(self.crypto_id)
        total_cost = current_price * self.amount

        if self.trade_type == "buy":
            color = CRYPTO_COLORS["buy"]
            title = f"💰 Buy {emoji} {name}?"
            
            can_afford = balance >= total_cost
            
            embed = discord.Embed(
                title=title,
                description=f"Confirm your purchase of **{self.amount:,.8f} {symbol}**",
                color=color
            )

            embed.add_field(
                name="💵 Price",
                value=f"${current_price:,.8f} per {symbol}",
                inline=True
            )

            embed.add_field(
                name="📦 Amount",
                value=f"{self.amount:,.8f} {symbol}",
                inline=True
            )

            embed.add_field(
                name="💰 Total Cost",
                value=money(total_cost),
                inline=True
            )

            embed.add_field(
                name="💵 Your Balance",
                value=money(balance),
                inline=True
            )

            if can_afford:
                embed.add_field(
                    name="💵 After Purchase",
                    value=money(balance - total_cost),
                    inline=True
                )
                embed.set_footer(text="✅ Click Buy to confirm transaction")
            else:
                needed = total_cost - balance
                embed.add_field(
                    name="❌ Can't Afford",
                    value=f"Need {money(needed)} more",
                    inline=True
                )
                embed.set_footer(text="❌ Insufficient funds")

        else:  # sell
            color = CRYPTO_COLORS["sell"]
            title = f"💸 Sell {emoji} {name}?"

            # FIX: Parse crypto portfolio
            crypto_portfolio = parse_crypto_portfolio(u.get("crypto_portfolio", {}))
            holdings = crypto_portfolio.get(self.crypto_id, {})
            owned = holdings.get("amount", 0)
            avg_price = holdings.get("avg_price", 0)

            can_sell = owned >= self.amount

            embed = discord.Embed(
                title=title,
                description=f"Confirm sale of **{self.amount:,.8f} {symbol}**",
                color=color
            )

            embed.add_field(
                name="💵 Sell Price",
                value=f"${current_price:,.8f} per {symbol}",
                inline=True
            )

            embed.add_field(
                name="📦 Amount",
                value=f"{self.amount:,.8f} {symbol}",
                inline=True
            )

            embed.add_field(
                name="💰 Total Earnings",
                value=money(total_cost),
                inline=True
            )

            if can_sell:
                profit_loss = (current_price - avg_price) * self.amount
                profit_loss_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
                
                pl_emoji = "🟢" if profit_loss > 0 else "🔴" if profit_loss < 0 else "⚪"

                embed.add_field(
                    name="📊 Profit/Loss",
                    value=f"{pl_emoji} {money(profit_loss)} ({profit_loss_pct:+.2f}%)",
                    inline=True
                )

                embed.add_field(
                    name="💵 New Balance",
                    value=money(balance + total_cost),
                    inline=True
                )

                embed.set_footer(text="✅ Click Sell to confirm transaction")
            else:
                embed.add_field(
                    name="❌ Can't Sell",
                    value=f"You only have {owned:,.8f} {symbol}",
                    inline=True
                )
                embed.set_footer(text="❌ Insufficient holdings")

        return embed

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Execute the trade."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)

        current_price = price_simulator.get_price(self.crypto_id)
        total_amount = current_price * self.amount

        if self.trade_type == "buy":
            balance = int(u.get("balance", 0))
            
            if balance < total_amount:
                return await interaction.response.send_message(
                    f"❌ You can't afford this! You need {money(total_amount - balance)} more.",
                    ephemeral=True
                )

            # Deduct money
            db.addbalance(userid, -int(total_amount))

            # FIX: Parse crypto portfolio
            crypto_portfolio = parse_crypto_portfolio(u.get("crypto_portfolio", {}))
            if self.crypto_id not in crypto_portfolio:
                crypto_portfolio[self.crypto_id] = {"amount": 0, "avg_price": 0}

            old_amount = crypto_portfolio[self.crypto_id].get("amount", 0)
            old_avg = crypto_portfolio[self.crypto_id].get("avg_price", 0)

            # Calculate new average price
            total_old_value = old_amount * old_avg
            total_new_value = total_old_value + total_amount
            new_total_amount = old_amount + self.amount
            new_avg_price = total_new_value / new_total_amount if new_total_amount > 0 else current_price

            crypto_portfolio[self.crypto_id] = {
                "amount": new_total_amount,
                "avg_price": new_avg_price
            }

            db.updatestat(userid, "crypto_portfolio", crypto_portfolio)

            # Success message
            emoji = self.crypto_data["emoji"]
            name = self.crypto_data["name"]
            symbol = self.crypto_data["symbol"]

            embed = discord.Embed(
                title="✅ Purchase Successful!",
                description=f"You bought **{self.amount:,.8f} {emoji} {symbol}** for {money(total_amount)}!",
                color=CRYPTO_COLORS["buy"]
            )

            embed.add_field(
                name="📊 Your Holdings",
                value=f"**Total {symbol}:** {new_total_amount:,.8f}\n**Avg Price:** ${new_avg_price:,.8f}",
                inline=False
            )

            embed.set_footer(text="Use /crypto portfolio to view your investments")

        else:  # sell
            # FIX: Parse crypto portfolio
            crypto_portfolio = parse_crypto_portfolio(u.get("crypto_portfolio", {}))
            holdings = crypto_portfolio.get(self.crypto_id, {})
            owned = holdings.get("amount", 0)

            if owned < self.amount:
                return await interaction.response.send_message(
                    f"❌ You don't have enough! You only have {owned:,.8f} {self.crypto_data['symbol']}.",
                    ephemeral=True
                )

            # Add money
            db.addbalance(userid, int(total_amount))

            # Remove crypto from portfolio
            new_amount = owned - self.amount
            if new_amount <= 0:
                del crypto_portfolio[self.crypto_id]
            else:
                crypto_portfolio[self.crypto_id]["amount"] = new_amount

            db.updatestat(userid, "crypto_portfolio", crypto_portfolio)

            # Success message
            emoji = self.crypto_data["emoji"]
            symbol = self.crypto_data["symbol"]

            embed = discord.Embed(
                title="✅ Sale Successful!",
                description=f"You sold **{self.amount:,.8f} {emoji} {symbol}** for {money(total_amount)}!",
                color=CRYPTO_COLORS["sell"]
            )

            if new_amount > 0:
                embed.add_field(
                    name="📊 Remaining Holdings",
                    value=f"**{symbol}:** {new_amount:,.8f}",
                    inline=False
                )

            embed.set_footer(text="Funds added to your wallet")

        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the trade."""
        embed = discord.Embed(
            title="❌ Trade Cancelled",
            description="Transaction cancelled. No changes made.",
            color=CRYPTO_COLORS["sell"]
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
