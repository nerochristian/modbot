"""
Economy Cog - Core economy commands and systems
Handles work, income, investments, and money management
Uses Discord Components V2 for interactive UI
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, Select, LayoutView, Modal, TextInput
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timedelta
import asyncio
import random
import logging
import os

from utils.format import format_currency, format_time, format_percentage
from utils.checks import is_registered
from utils.constants import *
from views.v2_embed import apply_v2_embed_layout

logger = logging.getLogger('LifeSimBot.Economy')

class WorkMinigame:
    """Base class for work minigames"""
    
    @staticmethod
    async def quick_math(interaction: discord.Interaction, base_reward: int) -> int:
        """Quick math challenge"""
        num1 = random.randint(1, 50)
        num2 = random.randint(1, 50)
        operation = random.choice(['+', '-', '*'])
        
        if operation == '+':
            answer = num1 + num2
            question = f"{num1} + {num2}"
        elif operation == '-':
            answer = num1 - num2
            question = f"{num1} - {num2}"
        else:
            answer = num1 * num2
            question = f"{num1} × {num2}"
        
        # Create modal for answer
        modal = WorkMathModal(question, answer, base_reward)
        await interaction.response.send_modal(modal)
        
        return -1  # Will be handled by modal
    
    @staticmethod
    async def reaction_test(interaction: discord.Interaction, base_reward: int) -> int:
        """Reaction time test"""
        view = ReactionTestView(base_reward)
        
        embed = discord.Embed(
            title="⚡ Reaction Test!",
            description="Click the button as fast as you can!",
            color=discord.Color.yellow()
        )
        
        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.send_message(view=view, ephemeral=True)
        return -1  # Will be handled by view
    
    @staticmethod
    async def typing_test(interaction: discord.Interaction, base_reward: int) -> int:
        """Typing speed test"""
        phrases = [
            "The quick brown fox jumps over the lazy dog",
            "Pack my box with five dozen liquor jugs",
            "How vexingly quick daft zebras jump",
            "Sphinx of black quartz judge my vow",
            "Two driven jocks help fax my big quiz"
        ]
        
        phrase = random.choice(phrases)
        modal = WorkTypingModal(phrase, base_reward)
        await interaction.response.send_modal(modal)
        
        return -1  # Will be handled by modal

class WorkMathModal(Modal, title="Work Minigame - Math Challenge"):
    """Modal for math minigame"""
    
    def __init__(self, question: str, correct_answer: int, base_reward: int):
        super().__init__(timeout=30)
        self.correct_answer = correct_answer
        self.base_reward = base_reward
        self.start_time = datetime.utcnow()
        
        self.answer = TextInput(
            label=f"What is {question}?",
            placeholder="Enter your answer...",
            required=True,
            min_length=1,
            max_length=10
        )
        self.add_item(self.answer)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle answer submission"""
        try:
            user_answer = int(self.answer.value.strip())
            time_taken = (datetime.utcnow() - self.start_time).total_seconds()
            
            if user_answer == self.correct_answer:
                # Correct! Calculate bonus based on speed
                speed_bonus = max(0, int((30 - time_taken) / 30 * self.base_reward * 0.5))
                total_reward = self.base_reward + speed_bonus
                
                # Update user balance
                await interaction.client.db.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (total_reward, interaction.user.id)
                )
                
                embed = discord.Embed(
                    title="✅ Correct!",
                    description=f"You earned {format_currency(total_reward)}!",
                    color=discord.Color.green()
                )
                
                if speed_bonus > 0:
                    embed.add_field(
                        name="⚡ Speed Bonus",
                        value=f"+{format_currency(speed_bonus)} (answered in {time_taken:.1f}s)",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                # Wrong answer - half reward
                penalty_reward = self.base_reward // 2
                
                await interaction.client.db.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (penalty_reward, interaction.user.id)
                )
                
                embed = discord.Embed(
                    title="❌ Wrong Answer",
                    description=f"The correct answer was {self.correct_answer}.\nYou still earned {format_currency(penalty_reward)}.",
                    color=discord.Color.red()
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid answer! Please enter a number.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in work math modal: {e}")
            await interaction.response.send_message(
                "❌ An error occurred. You didn't receive any money.",
                ephemeral=True
            )

class WorkTypingModal(Modal, title="Work Minigame - Typing Test"):
    """Modal for typing minigame"""
    
    def __init__(self, phrase: str, base_reward: int):
        super().__init__(timeout=30)
        self.phrase = phrase
        self.base_reward = base_reward
        self.start_time = datetime.utcnow()
        
        self.typed_text = TextInput(
            label="Type this phrase exactly:",
            placeholder=phrase,
            style=discord.TextStyle.paragraph,
            required=True,
            min_length=1,
            max_length=200
        )
        self.add_item(self.typed_text)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle typing submission"""
        try:
            user_text = self.typed_text.value.strip()
            time_taken = (datetime.utcnow() - self.start_time).total_seconds()
            
            # Calculate accuracy
            correct_chars = sum(1 for a, b in zip(user_text, self.phrase) if a == b)
            accuracy = correct_chars / len(self.phrase)
            
            # Calculate reward based on accuracy and speed
            accuracy_multiplier = accuracy
            speed_bonus = max(0, (30 - time_taken) / 30 * 0.5)
            
            total_reward = int(self.base_reward * (accuracy_multiplier + speed_bonus))
            
            # Update user balance
            await interaction.client.db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (total_reward, interaction.user.id)
            )
            
            embed = discord.Embed(
                title="📝 Typing Test Complete!",
                description=f"You earned {format_currency(total_reward)}!",
                color=discord.Color.green() if accuracy > 0.9 else discord.Color.orange()
            )
            
            embed.add_field(
                name="📊 Results",
                value=(
                    f"**Accuracy:** {format_percentage(accuracy)}\n"
                    f"**Time:** {time_taken:.1f}s\n"
                    f"**WPM:** {int(len(self.phrase.split()) / (time_taken / 60))}"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in work typing modal: {e}")
            await interaction.response.send_message(
                "❌ An error occurred. You didn't receive any money.",
                ephemeral=True
            )

class ReactionTestView(LayoutView):
    """View for reaction test minigame"""
    
    def __init__(self, base_reward: int):
        super().__init__(timeout=10)
        self.base_reward = base_reward
        self.start_time = datetime.utcnow()
        self.clicked = False
        
        # Add the reaction button
        button = Button(label="Click Me!", style=discord.ButtonStyle.danger, emoji="⚡")
        button.callback = self.button_clicked
        self.add_item(button)
    
    async def button_clicked(self, interaction: discord.Interaction):
        """Handle button click"""
        if self.clicked:
            await interaction.response.send_message(
                "❌ You already clicked!",
                ephemeral=True
            )
            return
        
        self.clicked = True
        reaction_time = (datetime.utcnow() - self.start_time).total_seconds()
        
        # Calculate reward based on reaction time
        if reaction_time < 0.5:
            multiplier = 2.0
            rating = "⚡ Lightning Fast!"
        elif reaction_time < 1.0:
            multiplier = 1.5
            rating = "🚀 Very Fast!"
        elif reaction_time < 2.0:
            multiplier = 1.2
            rating = "✨ Good!"
        else:
            multiplier = 1.0
            rating = "👍 Not bad!"
        
        total_reward = int(self.base_reward * multiplier)
        
        # Update user balance
        await interaction.client.db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (total_reward, interaction.user.id)
        )
        
        embed = discord.Embed(
            title=rating,
            description=f"You earned {format_currency(total_reward)}!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="⏱️ Reaction Time",
            value=f"{reaction_time:.3f} seconds",
            inline=True
        )
        
        embed.add_field(
            name="💰 Multiplier",
            value=f"{multiplier}x",
            inline=True
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

class InvestmentView(LayoutView):
    """View for managing investments"""
    
    def __init__(self, user: discord.User, bot):
        super().__init__(timeout=180)
        self.user = user
        self.bot = bot
        self.current_page = 0
    
    async def get_investments(self) -> List[Dict]:
        """Get user's investments"""
        investments = await self.bot.db.fetch_all(
            """
            SELECT * FROM user_investments 
            WHERE user_id = ? AND active = 1
            ORDER BY invested_at DESC
            """,
            (self.user.id,)
        )
        return investments or []
    
    async def create_embed(self) -> discord.Embed:
        """Create investments embed"""
        investments = await self.get_investments()
        
        embed = discord.Embed(
            title="📊 Your Investments",
            color=discord.Color.blue()
        )
        
        if investments:
            total_invested = sum(inv['amount'] for inv in investments)
            total_value = sum(self.calculate_current_value(inv) for inv in investments)
            profit = total_value - total_invested
            
            embed.description = (
                f"**Total Invested:** {format_currency(total_invested)}\n"
                f"**Current Value:** {format_currency(total_value)}\n"
                f"**Profit/Loss:** {format_currency(profit)} "
                f"({'📈' if profit >= 0 else '📉'} {format_percentage(profit / total_invested if total_invested > 0 else 0)})"
            )
            
            # Show individual investments
            for inv in investments[:5]:  # Show max 5
                current_value = self.calculate_current_value(inv)
                profit = current_value - inv['amount']
                time_invested = datetime.utcnow() - datetime.fromisoformat(inv['invested_at'])
                
                embed.add_field(
                    name=f"💼 {inv['investment_type'].title()}",
                    value=(
                        f"**Invested:** {format_currency(inv['amount'])}\n"
                        f"**Current:** {format_currency(current_value)}\n"
                        f"**Profit:** {format_currency(profit)}\n"
                        f"**Time:** {format_time(int(time_invested.total_seconds()))}"
                    ),
                    inline=True
                )
        else:
            embed.description = "You don't have any active investments.\nUse the button below to start investing!"
        
        embed.set_footer(text=f"Page {self.current_page + 1}")
        embed.timestamp = datetime.utcnow()
        
        return embed
    
    def calculate_current_value(self, investment: Dict) -> int:
        """Calculate current value of investment"""
        time_invested = datetime.utcnow() - datetime.fromisoformat(investment['invested_at'])
        hours_invested = time_invested.total_seconds() / 3600
        
        # Different return rates for different investment types
        rates = {
            'stocks': 0.02,  # 2% per hour
            'crypto': 0.05,  # 5% per hour (volatile)
            'bonds': 0.01,   # 1% per hour (stable)
            'real_estate': 0.015  # 1.5% per hour
        }
        
        rate = rates.get(investment['investment_type'], 0.01)
        
        # Add some randomness for stocks and crypto
        if investment['investment_type'] in ['stocks', 'crypto']:
            rate *= random.uniform(0.5, 1.5)
        
        return int(investment['amount'] * (1 + rate * hours_invested))
    
    @discord.ui.button(label="📈 New Investment", style=discord.ButtonStyle.green)
    async def new_investment(self, interaction: discord.Interaction, button: Button):
        """Create new investment"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This is not your investment portfolio!",
                ephemeral=True
            )
            return
        
        # Show investment options
        view = InvestmentOptionsView(self.user, self.bot)
        embed = discord.Embed(
            title="📊 Choose Investment Type",
            description="Select the type of investment you want to make:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📈 Stocks",
            value="**Risk:** Medium | **Return:** ~2%/hour\nSteady growth with moderate volatility",
            inline=False
        )
        
        embed.add_field(
            name="💎 Cryptocurrency",
            value="**Risk:** High | **Return:** ~5%/hour\nHigh returns but very volatile",
            inline=False
        )
        
        embed.add_field(
            name="🏛️ Bonds",
            value="**Risk:** Low | **Return:** ~1%/hour\nSafe and stable returns",
            inline=False
        )
        
        embed.add_field(
            name="🏠 Real Estate",
            value="**Risk:** Low-Medium | **Return:** ~1.5%/hour\nLong-term stable investment",
            inline=False
        )
        
        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.send_message(view=view, ephemeral=True)
    
    @discord.ui.button(label="💰 Cash Out", style=discord.ButtonStyle.primary)
    async def cash_out(self, interaction: discord.Interaction, button: Button):
        """Cash out an investment"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This is not your investment portfolio!",
                ephemeral=True
            )
            return
        
        investments = await self.get_investments()
        
        if not investments:
            await interaction.response.send_message(
                "❌ You don't have any investments to cash out!",
                ephemeral=True
            )
            return
        
        # Create select menu for cashing out
        view = CashOutView(self.user, self.bot, investments)
        await interaction.response.send_message(
            "Select an investment to cash out:",
            view=view,
            ephemeral=True
        )
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: Button):
        """Refresh investments"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This is not your investment portfolio!",
                ephemeral=True
            )
            return
        
        embed = await self.create_embed()
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)

class InvestmentOptionsView(LayoutView):
    """View for choosing investment type"""
    
    def __init__(self, user: discord.User, bot):
        super().__init__(timeout=60)
        self.user = user
        self.bot = bot
        
        # Add select menu
        options = [
            discord.SelectOption(label="Stocks", value="stocks", emoji="📈", description="Medium risk, ~2%/hour return"),
            discord.SelectOption(label="Cryptocurrency", value="crypto", emoji="💎", description="High risk, ~5%/hour return"),
            discord.SelectOption(label="Bonds", value="bonds", emoji="🏛️", description="Low risk, ~1%/hour return"),
            discord.SelectOption(label="Real Estate", value="real_estate", emoji="🏠", description="Low-medium risk, ~1.5%/hour return"),
        ]
        
        select = Select(placeholder="Choose investment type...", options=options)
        select.callback = self.select_callback
        self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        """Handle investment type selection"""
        investment_type = interaction.data['values'][0]
        
        # Show amount modal
        modal = InvestmentAmountModal(self.user, self.bot, investment_type)
        await interaction.response.send_modal(modal)

class InvestmentAmountModal(Modal, title="Investment Amount"):
    """Modal for entering investment amount"""
    
    amount = TextInput(
        label="How much do you want to invest?",
        placeholder="Enter amount...",
        required=True,
        min_length=1,
        max_length=15
    )
    
    def __init__(self, user: discord.User, bot, investment_type: str):
        super().__init__()
        self.user = user
        self.bot = bot
        self.investment_type = investment_type
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle investment creation"""
        try:
            amount = int(self.amount.value.replace(',', ''))
            
            if amount <= 0:
                await interaction.response.send_message(
                    "❌ Amount must be positive!",
                    ephemeral=True
                )
                return
            
            # Check user balance
            user_data = await self.bot.db.fetch_one(
                "SELECT username, balance FROM users WHERE user_id = ?",
                (self.user.id,)
            )
            
            if not user_data or user_data['balance'] < amount:
                await interaction.response.send_message(
                    f"❌ You don't have enough money! You need {format_currency(amount)}.",
                    ephemeral=True
                )
                return
            
            # Create investment
            await self.bot.db.execute(
                """
                INSERT INTO user_investments (
                    user_id, investment_type, amount, invested_at, active
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (self.user.id, self.investment_type, amount, datetime.utcnow().isoformat(), 1)
            )
            
            # Deduct from balance
            await self.bot.db.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (amount, self.user.id)
            )
            
            embed = discord.Embed(
                title="✅ Investment Created!",
                description=f"You invested {format_currency(amount)} in {self.investment_type}!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📊 Investment Details",
                value=(
                    f"**Type:** {self.investment_type.title()}\n"
                    f"**Amount:** {format_currency(amount)}\n"
                    f"**Started:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
                ),
                inline=False
            )
            
            embed.set_footer(text="Check your portfolio with /investments")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid amount! Please enter a number.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error creating investment: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while creating your investment.",
                ephemeral=True
            )

class CashOutView(LayoutView):
    """View for cashing out investments"""
    
    def __init__(self, user: discord.User, bot, investments: List[Dict]):
        super().__init__(timeout=60)
        self.user = user
        self.bot = bot
        self.investments = investments
        
        # Create select menu
        options = []
        for i, inv in enumerate(investments[:25]):  # Max 25 options
            time_invested = datetime.utcnow() - datetime.fromisoformat(inv['invested_at'])
            options.append(
                discord.SelectOption(
                    label=f"{inv['investment_type'].title()} - {format_currency(inv['amount'])}",
                    value=str(i),
                    description=f"Invested {format_time(int(time_invested.total_seconds()))} ago"
                )
            )
        
        select = Select(placeholder="Choose investment to cash out...", options=options)
        select.callback = self.select_callback
        self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        """Handle cash out selection"""
        try:
            idx = int(interaction.data['values'][0])
            investment = self.investments[idx]
            
            # Calculate current value
            time_invested = datetime.utcnow() - datetime.fromisoformat(investment['invested_at'])
            hours_invested = time_invested.total_seconds() / 3600
            
            rates = {
                'stocks': 0.02,
                'crypto': 0.05,
                'bonds': 0.01,
                'real_estate': 0.015
            }
            
            rate = rates.get(investment['investment_type'], 0.01)
            
            if investment['investment_type'] in ['stocks', 'crypto']:
                rate *= random.uniform(0.5, 1.5)
            
            current_value = int(investment['amount'] * (1 + rate * hours_invested))
            profit = current_value - investment['amount']
            
            # Update database
            await self.bot.db.execute(
                "UPDATE user_investments SET active = 0 WHERE investment_id = ?",
                (investment['investment_id'],)
            )
            
            await self.bot.db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (current_value, self.user.id)
            )
            
            # Create result embed
            embed = discord.Embed(
                title="💰 Investment Cashed Out!",
                color=discord.Color.green() if profit >= 0 else discord.Color.red()
            )
            
            embed.add_field(
                name="📊 Results",
                value=(
                    f"**Initial Investment:** {format_currency(investment['amount'])}\n"
                    f"**Time Invested:** {format_time(int(time_invested.total_seconds()))}\n"
                    f"**Final Value:** {format_currency(current_value)}\n"
                    f"**Profit/Loss:** {format_currency(profit)} "
                    f"({format_percentage(profit / investment['amount'])})"
                ),
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Error cashing out investment: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while cashing out.",
                ephemeral=True
            )

class Economy(commands.Cog):
    """Economy commands and systems"""
    
    def __init__(self, bot):
        self.bot = bot
        self.work_cooldowns = {}
        logger.info("Economy cog initialized")
    
    def get_work_cooldown(self, user_id: int) -> Optional[datetime]:
        """Get work cooldown for user"""
        return self.work_cooldowns.get(user_id)
    
    def set_work_cooldown(self, user_id: int):
        """Set work cooldown for user"""
        cooldown_seconds = int(os.getenv('WORK_COOLDOWN', 3600))
        self.work_cooldowns[user_id] = datetime.utcnow() + timedelta(seconds=cooldown_seconds)
    
    @app_commands.command(name="hustle", description="Do a quick hustle to earn money")
    @app_commands.describe(minigame="Choose a hustle minigame (optional)")
    @app_commands.choices(minigame=[
        app_commands.Choice(name="🧮 Math Challenge", value="math"),
        app_commands.Choice(name="⚡ Reaction Test", value="reaction"),
        app_commands.Choice(name="⌨️ Typing Test", value="typing"),
        app_commands.Choice(name="🎲 Random", value="random"),
    ])
    async def hustle(self, interaction: discord.Interaction, minigame: Optional[str] = None):
        """Do a quick hustle to earn money with optional minigames"""
        # Check cooldown first (fast path) to avoid interaction timeouts.
        cooldown = self.get_work_cooldown(interaction.user.id)
        if cooldown and datetime.utcnow() < cooldown:
            time_left = cooldown - datetime.utcnow()
            await interaction.response.send_message(
                f"⏰ You're tired! Rest for **{format_time(int(time_left.total_seconds()))}** before hustling again.",
                ephemeral=True
            )
            return

        # Check if user is registered
        user_data = await self.bot.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        if not user_data or not user_data.get("username"):
            await interaction.response.send_message(
                "❌ You need to register first! Use `/register`.",
                ephemeral=True
            )
            return
        
        # Calculate base reward
        base_reward = random.randint(100, 300)
        
        # Check if user has a job for bonus
        job = await self.bot.db.fetch_one(
            "SELECT * FROM user_jobs WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        if job:
            base_reward += job.get('salary', 0) // 10
        
        # Set cooldown
        self.set_work_cooldown(interaction.user.id)
        
        # Run minigame if specified
        if not minigame or minigame == "random":
            minigame = random.choice(['math', 'reaction', 'typing'])
        
        if minigame == "math":
            await WorkMinigame.quick_math(interaction, base_reward)
        elif minigame == "reaction":
            await WorkMinigame.reaction_test(interaction, base_reward)
        elif minigame == "typing":
            await WorkMinigame.typing_test(interaction, base_reward)
        else:
            # Simple work without minigame
            await self.bot.db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (base_reward, interaction.user.id)
            )
            
            embed = discord.Embed(
                title="💼 Work Complete!",
                description=f"You earned {format_currency(base_reward)}!",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="beg", description="Beg for money (last resort)")
    async def beg(self, interaction: discord.Interaction):
        """Beg for money"""
        user_data = await self.bot.db.fetch_one(
            "SELECT username, balance FROM users WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        if not user_data or not user_data.get("username"):
            await interaction.response.send_message(
                "❌ You need to register first! Use `/register`.",
                ephemeral=True
            )
            return
        
        # Random chance of success
        if random.random() < 0.6:  # 60% success rate
            amount = random.randint(10, 100)
            
            await self.bot.db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, interaction.user.id)
            )
            
            messages = [
                f"A kind stranger gave you {format_currency(amount)}!",
                f"You found {format_currency(amount)} on the ground!",
                f"Someone felt bad for you and gave {format_currency(amount)}.",
                f"You received {format_currency(amount)} from a generous donor!",
            ]
            
            embed = discord.Embed(
                title="🙏 Success!",
                description=random.choice(messages),
                color=discord.Color.green()
            )
        else:
            messages = [
                "Nobody gave you anything...",
                "People just walked past you.",
                "A cop told you to move along.",
                "Someone laughed at you.",
            ]
            
            embed = discord.Embed(
                title="😢 No Luck",
                description=random.choice(messages),
                color=discord.Color.red()
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="rob", description="Attempt to rob another user")
    @app_commands.describe(user="The user to rob")
    async def rob(self, interaction: discord.Interaction, user: discord.User):
        """Rob another user"""
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ You can't rob yourself!",
                ephemeral=True
            )
            return
        
        if user.bot:
            await interaction.response.send_message(
                "❌ You can't rob bots!",
                ephemeral=True
            )
            return
        
        # Check if robber is registered
        robber_data = await self.bot.db.fetch_one(
            "SELECT username, balance FROM users WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        if not robber_data or not robber_data.get("username"):
            await interaction.response.send_message(
                "❌ You need to register first! Use `/register`.",
                ephemeral=True
            )
            return
        
        # Check if target is registered
        target_data = await self.bot.db.fetch_one(
            "SELECT username, balance FROM users WHERE user_id = ?",
            (user.id,)
        )
        
        if not target_data or not target_data.get("username"):
            await interaction.response.send_message(
                f"❌ {user.mention} is not registered!",
                ephemeral=True
            )
            return
        
        # Check if target has enough money
        if target_data['balance'] < 100:
            await interaction.response.send_message(
                f"❌ {user.mention} doesn't have enough cash to rob!",
                ephemeral=True
            )
            return
        
        # Check cooldown
        cooldown_key = f"rob_{interaction.user.id}"
        if cooldown_key in self.bot.cooldowns:
            cooldown_end = self.bot.cooldowns[cooldown_key]
            if datetime.utcnow() < cooldown_end:
                time_left = cooldown_end - datetime.utcnow()
                await interaction.response.send_message(
                    f"⏰ You need to wait **{format_time(int(time_left.total_seconds()))}** before robbing again!",
                    ephemeral=True
                )
                return
        
        # Set cooldown
        cooldown_seconds = int(os.getenv('ROB_COOLDOWN', 7200))
        self.bot.cooldowns[cooldown_key] = datetime.utcnow() + timedelta(seconds=cooldown_seconds)
        
        # Calculate success chance (based on stats if available)
        base_success_rate = 0.5
        
        # Attempt robbery
        if random.random() < base_success_rate:
            # Success!
            stolen_amount = random.randint(50, min(target_data['balance'], 1000))
            
            await self.bot.db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (stolen_amount, interaction.user.id)
            )
            
            await self.bot.db.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (stolen_amount, user.id)
            )
            
            embed = discord.Embed(
                title="💰 Robbery Successful!",
                description=f"You stole {format_currency(stolen_amount)} from {user.mention}!",
                color=discord.Color.green()
            )
            
            # Try to notify victim
            try:
                victim_embed = discord.Embed(
                    title="🚨 You Were Robbed!",
                    description=f"{interaction.user.mention} stole {format_currency(stolen_amount)} from you!",
                    color=discord.Color.red()
                )
                await user.send(embed=victim_embed)
            except:
                pass
        else:
            # Failed! Lose money as fine
            fine = random.randint(100, 500)
            fine = min(fine, robber_data['balance'])
            
            if fine > 0:
                await self.bot.db.execute(
                    "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                    (fine, interaction.user.id)
                )
            
            embed = discord.Embed(
                title="🚔 Caught!",
                description=f"You got caught trying to rob {user.mention} and paid a fine of {format_currency(fine)}!",
                color=discord.Color.red()
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="investments", description="View and manage your investments")
    async def investments(self, interaction: discord.Interaction):
        """View investment portfolio"""
        user_data = await self.bot.db.fetch_one(
            "SELECT user_id, username FROM users WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        if not user_data or not user_data.get("username"):
            await interaction.response.send_message(
                "❌ You need to register first! Use `/register`.",
                ephemeral=True
            )
            return
        
        view = InvestmentView(interaction.user, self.bot)
        embed = await view.create_embed()
        
        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.send_message(view=view)
    
    @app_commands.command(name="give", description="Give money or items to another user")
    @app_commands.describe(
        user="The user to give to",
        amount="Amount of money to give",
        item="Item to give (optional)"
    )
    async def give(
        self, 
        interaction: discord.Interaction, 
        user: discord.User,
        amount: Optional[int] = None,
        item: Optional[str] = None
    ):
        """Give money or items to another user"""
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ You can't give things to yourself!",
                ephemeral=True
            )
            return
        
        if user.bot:
            await interaction.response.send_message(
                "❌ You can't give things to bots!",
                ephemeral=True
            )
            return
        
        if not amount and not item:
            await interaction.response.send_message(
                "❌ You must specify either an amount of money or an item!",
                ephemeral=True
            )
            return
        
        # Get giver data
        giver_data = await self.bot.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        if not giver_data or not giver_data.get("username"):
            await interaction.response.send_message(
                "❌ You need to register first! Use `/register`.",
                ephemeral=True
            )
            return
        
        # Get receiver data
        receiver_data = await self.bot.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (user.id,)
        )
        
        if not receiver_data or not receiver_data.get("username"):
            await interaction.response.send_message(
                f"❌ {user.mention} is not registered!",
                ephemeral=True
            )
            return
        
        # Handle money giving
        if amount:
            if amount <= 0:
                await interaction.response.send_message(
                    "❌ Amount must be positive!",
                    ephemeral=True
                )
                return
            
            if giver_data['balance'] < amount:
                await interaction.response.send_message(
                    f"❌ You don't have enough money! You only have {format_currency(giver_data['balance'])}.",
                    ephemeral=True
                )
                return
            
            # Transfer money (no tax for giving)
            await self.bot.db.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (amount, interaction.user.id)
            )
            
            await self.bot.db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, user.id)
            )
            
            embed = discord.Embed(
                title="💝 Gift Sent!",
                description=f"You gave {format_currency(amount)} to {user.mention}!",
                color=discord.Color.green()
            )
            
            # Notify receiver
            try:
                receiver_embed = discord.Embed(
                    title="🎁 You Received a Gift!",
                    description=f"{interaction.user.mention} gave you {format_currency(amount)}!",
                    color=discord.Color.green()
                )
                await user.send(embed=receiver_embed)
            except:
                pass
            
            await interaction.response.send_message(embed=embed)
        
        # Handle item giving
        elif item:
            # Check if giver has the item
            item_data = await self.bot.db.fetch_one(
                """
                SELECT ui.*, i.name
                FROM user_inventory ui
                JOIN items i ON ui.item_id = i.item_id
                WHERE ui.user_id = ? AND LOWER(i.name) = LOWER(?)
                """,
                (interaction.user.id, item)
            )
            
            if not item_data or item_data['quantity'] <= 0:
                await interaction.response.send_message(
                    f"❌ You don't have any {item}!",
                    ephemeral=True
                )
                return
            
            # Transfer item
            await self.bot.db.execute(
                """
                UPDATE user_inventory 
                SET quantity = quantity - 1 
                WHERE user_id = ? AND item_id = ?
                """,
                (interaction.user.id, item_data['item_id'])
            )
            
            # Add to receiver's inventory
            receiver_item = await self.bot.db.fetch_one(
                "SELECT * FROM user_inventory WHERE user_id = ? AND item_id = ?",
                (user.id, item_data['item_id'])
            )
            
            if receiver_item:
                await self.bot.db.execute(
                    """
                    UPDATE user_inventory 
                    SET quantity = quantity + 1 
                    WHERE user_id = ? AND item_id = ?
                    """,
                    (user.id, item_data['item_id'])
                )
            else:
                await self.bot.db.execute(
                    """
                    INSERT INTO user_inventory (user_id, item_id, quantity)
                    VALUES (?, ?, 1)
                    """,
                    (user.id, item_data['item_id'])
                )
            
            embed = discord.Embed(
                title="💝 Gift Sent!",
                description=f"You gave **{item_data['name']}** to {user.mention}!",
                color=discord.Color.green()
            )
            
            # Notify receiver
            try:
                receiver_embed = discord.Embed(
                    title="🎁 You Received an Item!",
                    description=f"{interaction.user.mention} gave you **{item_data['name']}**!",
                    color=discord.Color.green()
                )
                await user.send(embed=receiver_embed)
            except:
                pass
            
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="loan", description="Take out or repay a loan")
    @app_commands.describe(
        action="Action to perform",
        amount="Amount to borrow or repay"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="💰 Borrow", value="borrow"),
        app_commands.Choice(name="💵 Repay", value="repay"),
        app_commands.Choice(name="📊 Status", value="status"),
    ])
    async def loan(self, interaction: discord.Interaction, action: str, amount: Optional[int] = None):
        """Loan system"""
        user_data = await self.bot.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (interaction.user.id,)
        )
        
        if not user_data or not user_data.get("username"):
            await interaction.response.send_message(
                "❌ You need to register first! Use `/register`.",
                ephemeral=True
            )
            return
        
        # Get current loan
        loan_data = await self.bot.db.fetch_one(
            "SELECT * FROM user_loans WHERE user_id = ? AND active = 1",
            (interaction.user.id,)
        )
        
        if action == "borrow":
            if loan_data:
                await interaction.response.send_message(
                    f"❌ You already have an active loan of {format_currency(loan_data['amount'])}!\n"
                    f"Repay it before taking another loan.",
                    ephemeral=True
                )
                return
            
            if not amount or amount <= 0:
                await interaction.response.send_message(
                    "❌ You must specify a positive amount to borrow!",
                    ephemeral=True
                )
                return
            
            # Calculate interest (10%)
            interest_rate = 0.10
            total_debt = int(amount * (1 + interest_rate))
            
            # Create loan
            await self.bot.db.execute(
                """
                INSERT INTO user_loans (
                    user_id, amount, interest_rate, total_debt, 
                    borrowed_at, active
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    interaction.user.id,
                    amount,
                    interest_rate,
                    total_debt,
                    datetime.utcnow().isoformat(),
                    1
                )
            )
            
            # Add money to balance
            await self.bot.db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, interaction.user.id)
            )
            
            embed = discord.Embed(
                title="💰 Loan Approved!",
                description=f"You borrowed {format_currency(amount)}!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📊 Loan Details",
                value=(
                    f"**Borrowed:** {format_currency(amount)}\n"
                    f"**Interest Rate:** {format_percentage(interest_rate)}\n"
                    f"**Total Debt:** {format_currency(total_debt)}"
                ),
                inline=False
            )
            
            embed.set_footer(text="Don't forget to repay your loan!")
            
            await interaction.response.send_message(embed=embed)
        
        elif action == "repay":
            if not loan_data:
                await interaction.response.send_message(
                    "❌ You don't have any active loans!",
                    ephemeral=True
                )
                return
            
            if not amount:
                amount = loan_data['total_debt']
            
            if amount <= 0:
                await interaction.response.send_message(
                    "❌ Amount must be positive!",
                    ephemeral=True
                )
                return
            
            if user_data['balance'] < amount:
                await interaction.response.send_message(
                    f"❌ You don't have enough money! You need {format_currency(amount)}.",
                    ephemeral=True
                )
                return
            
            # Repay loan
            new_debt = loan_data['total_debt'] - amount
            
            await self.bot.db.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (amount, interaction.user.id)
            )
            
            if new_debt <= 0:
                # Loan fully repaid
                await self.bot.db.execute(
                    "UPDATE user_loans SET active = 0 WHERE loan_id = ?",
                    (loan_data['loan_id'],)
                )
                
                embed = discord.Embed(
                    title="✅ Loan Fully Repaid!",
                    description=f"You repaid {format_currency(amount)} and cleared your debt!",
                    color=discord.Color.green()
                )
            else:
                # Partial payment
                await self.bot.db.execute(
                    "UPDATE user_loans SET total_debt = ? WHERE loan_id = ?",
                    (new_debt, loan_data['loan_id'])
                )
                
                embed = discord.Embed(
                    title="💵 Partial Payment Made",
                    description=f"You repaid {format_currency(amount)}!",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="📊 Remaining Debt",
                    value=format_currency(new_debt),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
        
        elif action == "status":
            if not loan_data:
                await interaction.response.send_message(
                    "✅ You don't have any active loans!",
                    ephemeral=True
                )
                return
            
            borrowed_at = datetime.fromisoformat(loan_data['borrowed_at'])
            time_elapsed = datetime.utcnow() - borrowed_at
            
            embed = discord.Embed(
                title="📊 Loan Status",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="💰 Loan Details",
                value=(
                    f"**Borrowed:** {format_currency(loan_data['amount'])}\n"
                    f"**Interest Rate:** {format_percentage(loan_data['interest_rate'])}\n"
                    f"**Total Debt:** {format_currency(loan_data['total_debt'])}\n"
                    f"**Time Since Borrowed:** {format_time(int(time_elapsed.total_seconds()))}"
                ),
                inline=False
            )
            
            embed.set_footer(text="Use /loan repay <amount> to pay back your loan")
            
            await interaction.response.send_message(embed=embed)

async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Economy(bot))
