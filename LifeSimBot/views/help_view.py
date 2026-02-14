# views/help_view.py (COMPLETE UPDATE with Crypto)

from __future__ import annotations

import discord
from typing import Optional


# ============= HELP VIEW =============

class HelpView(discord.ui.LayoutView):
    """Interactive help menu with category buttons."""

    def __init__(self, bot, user: discord.User):
        super().__init__(timeout=300)
        self.bot = bot
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This help menu isn't for you! Use `/help` to open your own.",
                ephemeral=True
            )
            return False
        return True

    def create_main_embed(self) -> discord.Embed:
        """Create the main help menu embed."""
        embed = discord.Embed(
            title="📚 Life Simulator - Help Menu",
            description=(
                "Welcome to Life Simulator! Choose a category below to learn more.\n\n"
                "**Quick Start:**\n"
                "• Use `/hub` for your main dashboard\n"
                "• Use `/start` to begin your journey\n"
                "• Use `/guide` for a step-by-step tutorial"
            ),
            color=0x5865F2
        )

        embed.add_field(
            name="📋 Categories",
            value=(
                "💰 **Economy** - Money, banking, trading\n"
                "💼 **Jobs** - Work, careers, income\n"
                "🛒 **Shop** - Buy items and manage inventory\n"
                "💎 **Crypto** - Cryptocurrency trading\n"
                "🎰 **Casino** - Gambling games\n"
                "🔪 **Crime** - Rob and commit crimes\n"
                "⚔️ **Skills** - Training and progression\n"
                "🐾 **Pets** - Adopt and care for pets\n"
                "❤️ **Social** - Family, relationships, guilds\n"
                "🏆 **Progress** - Achievements, quests, levels"
            ),
            inline=False
        )

        embed.add_field(
            name="🔗 Quick Links",
            value=(
                "**`/hub`** - Main dashboard\n"
                "**`/guide`** - Beginner's guide\n"
                "**`/commands`** - All commands list\n"
                "**`/tips`** - Random pro tips\n"
                "**`/faq`** - Common questions"
            ),
            inline=False
        )

        embed.set_footer(text="Click a category button below to explore!")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        return embed

    # ============= CATEGORY BUTTONS =============

    @discord.ui.button(label="Economy", style=discord.ButtonStyle.secondary, emoji="💰", row=0)
    async def economy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Economy category help."""
        embed = discord.Embed(
            title="💰 Economy System",
            description="Manage your money, earn income, and build wealth!",
            color=0x57F287
        )

        embed.add_field(
            name="💵 Basic Commands",
            value=(
                "**`/start`** - Get starter money\n"
                "**`/balance`** - Check your money\n"
                "**`/profile`** - View your stats\n"
                "**`/daily`** - Claim daily reward (24hr cooldown)\n"
                "**`/leaderboard`** - See top players"
            ),
            inline=False
        )

        embed.add_field(
            name="🏦 Banking",
            value=(
                "**`/deposit <amount>`** - Put money in bank (safe!)\n"
                "**`/withdraw <amount>`** - Take money out\n"
                "**`/pay <user> <amount>`** - Send money to someone\n\n"
                "**Tip:** Keep money in bank to protect from robberies!"
            ),
            inline=False
        )

        embed.add_field(
            name="💡 Money Tips",
            value=(
                "• Wallet can be robbed - bank is safe\n"
                "• Work regularly for steady income\n"
                "• Complete quests for bonus rewards\n"
                "• Invest in businesses for passive income\n"
                "• Trade crypto for high-risk profits"
            ),
            inline=False
        )

        embed.set_footer(text="Use /hub to see your balance and stats")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Jobs", style=discord.ButtonStyle.secondary, emoji="💼", row=0)
    async def jobs_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Jobs category help."""
        embed = discord.Embed(
            title="💼 Jobs & Work",
            description="Get a job and earn money by working!",
            color=0xEB459E
        )

        embed.add_field(
            name="🔍 Job Commands",
            value=(
                "**`/jobs`** - Browse available jobs\n"
                "**`/apply <job>`** - Apply for a job\n"
                "**`/work`** - Work your shift (play minigame!)\n"
                "**`/quit`** - Quit your current job\n"
                "**`/sleep`** - Restore energy (8hr cooldown)"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 Job Categories",
            value=(
                "🔰 **Entry Level** - Waiter, Cashier (Lv.1+)\n"
                "⭐ **Skilled** - Chef, Teacher (Lv.5+)\n"
                "💼 **Professional** - Programmer, Doctor (Lv.10+)\n"
                "👑 **Expert** - Lawyer, Engineer (Lv.15+)\n"
                "💎 **Elite** - CEO, Surgeon (Lv.20+)"
            ),
            inline=False
        )

        embed.add_field(
            name="🎮 Work Minigames",
            value=(
                "• **Memory** - Remember sequences\n"
                "• **Reaction** - Click buttons fast\n"
                "• **Timing** - Stop at the right time\n"
                "• **Math** - Solve quick calculations\n\n"
                "Better performance = higher pay!"
            ),
            inline=False
        )

        embed.add_field(
            name="💡 Job Tips",
            value=(
                "• Train relevant skills for better pay\n"
                "• Job level increases with work XP\n"
                "• Higher job level = more earnings\n"
                "• Perfect minigames for 150% pay\n"
                "• Work every hour to maximize income"
            ),
            inline=False
        )

        embed.set_footer(text="Use /jobs to find your perfect career!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Shop", style=discord.ButtonStyle.secondary, emoji="🛒", row=0)
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Shop category help."""
        embed = discord.Embed(
            title="🛒 Shop & Inventory",
            description="Buy items, manage your inventory, and use consumables!",
            color=0x3B82F6
        )

        embed.add_field(
            name="🛍️ Shopping Commands",
            value=(
                "**`/shop [category]`** - Browse the shop\n"
                "**`/buy <item> [qty]`** - Buy an item\n"
                "**`/sell <item> [qty]`** - Sell items (50% value)\n"
                "**`/inventory [category]`** - View your items"
            ),
            inline=False
        )

        embed.add_field(
            name="📦 Item Categories",
            value=(
                "🍔 **Food** - Restore hunger\n"
                "⚡ **Consumables** - Restore energy\n"
                "🔧 **Tools** - Work bonuses\n"
                "🚗 **Vehicles** - Speed bonuses\n"
                "💎 **Collectibles** - Valuable items"
            ),
            inline=False
        )

        embed.add_field(
            name="✨ Using Items",
            value=(
                "**`/use <item> [qty]`** - Use a consumable\n"
                "**`/eat <food>`** - Eat food to restore hunger\n"
                "**`/manage <item>`** - Sell all or drop items"
            ),
            inline=False
        )

        embed.add_field(
            name="💡 Shopping Tips",
            value=(
                "• Buy energy drinks for quick energy boosts\n"
                "• Food restores both hunger and health\n"
                "• Tools give permanent work bonuses\n"
                "• Sort inventory by value to find best items\n"
                "• Sell unwanted items for quick cash"
            ),
            inline=False
        )

        embed.set_footer(text="Use /shop to start shopping!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Crypto", style=discord.ButtonStyle.secondary, emoji="💎", row=0)
    async def crypto_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Crypto trading help."""
        embed = discord.Embed(
            title="💎 Cryptocurrency Trading",
            description="Trade crypto for profit! Buy low, sell high!",
            color=0xF7931A
        )

        embed.add_field(
            name="📊 Market Commands",
            value=(
                "**`/crypto market`** - Browse all cryptocurrencies\n"
                "**`/crypto portfolio`** - View your holdings\n"
                "**`/crypto price <symbol>`** - Check current price\n"
                "**`/crypto info`** - Learn about trading"
            ),
            inline=False
        )

        embed.add_field(
            name="💰 Trading Commands",
            value=(
                "**`/crypto buy <symbol> <amount>`** - Buy crypto\n"
                "**`/crypto sell <symbol> <amount>`** - Sell crypto\n\n"
                "**Examples:**\n"
                "`/crypto buy BTC 0.5` - Buy 0.5 Bitcoin\n"
                "`/crypto sell ETH 2` - Sell 2 Ethereum"
            ),
            inline=False
        )

        embed.add_field(
            name="📈 Available Cryptocurrencies",
            value=(
                "₿ **BTC** - Bitcoin (5% volatility)\n"
                "Ξ **ETH** - Ethereum (6% volatility)\n"
                "🐕 **DOGE** - Dogecoin (15% volatility)\n"
                "🔷 **ADA** - Cardano (8% volatility)\n"
                "◎ **SOL** - Solana (10% volatility)\n"
                "💧 **XRP** - Ripple (7% volatility)\n"
                "🔶 **BNB** - Binance Coin (6% volatility)\n"
                "🟣 **MATIC** - Polygon (9% volatility)\n"
                "🐶 **SHIB** - Shiba Inu (20% meme coin!)\n"
                "🐸 **PEPE** - Pepe (25% extreme meme!)"
            ),
            inline=False
        )

        embed.add_field(
            name="💡 Trading Tips",
            value=(
                "• Prices update every 5 minutes\n"
                "• Meme coins (DOGE, SHIB, PEPE) = high risk/reward\n"
                "• BTC and ETH are more stable\n"
                "• Check 24h change for trends (📈📉)\n"
                "• Portfolio shows profit/loss automatically\n"
                "• **WARNING:** You can lose money!"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 Understanding P/L",
            value=(
                "🟢 **Green** - You're making profit\n"
                "🔴 **Red** - You're losing money\n"
                "⚪ **White** - Break even\n\n"
                "Track average buy price vs current price!"
            ),
            inline=False
        )

        embed.set_footer(text="Use /crypto market to start trading!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Casino", style=discord.ButtonStyle.secondary, emoji="🎰", row=1)
    async def casino_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Casino category help."""
        embed = discord.Embed(
            title="🎰 Casino Games",
            description="Test your luck and win big!",
            color=0xFEE75C
        )

        embed.add_field(
            name="🎮 Games Available",
            value=(
                "🎰 **Slots** - Classic slot machine\n"
                "🃏 **Blackjack** - Beat the dealer to 21\n"
                "🪙 **Coinflip** - Heads or tails\n"
                "🎲 **Dice** - Roll the dice\n"
                "💣 **Minesweeper** - Avoid the mines\n"
                "📈 **Crash** - Cash out before crash"
            ),
            inline=False
        )

        embed.add_field(
            name="🎲 How to Play",
            value=(
                "**`/casino`** - View casino stats\n"
                "**`/gamble <amount>`** - Start gambling\n\n"
                "Choose your game from the interactive menu!"
            ),
            inline=False
        )

        embed.add_field(
            name="💡 Casino Tips",
            value=(
                "• Blackjack has best odds with strategy\n"
                "• Set a budget and stick to it\n"
                "• House always has an edge\n"
                "• Don't chase losses\n"
                "• Play for fun, not to make money"
            ),
            inline=False
        )

        embed.set_footer(text="Gamble responsibly!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Crime", style=discord.ButtonStyle.secondary, emoji="🔪", row=1)
    async def crime_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Crime category help."""
        embed = discord.Embed(
            title="🔪 Crime System",
            description="High risk, high reward! Rob others or commit crimes.",
            color=0xEF4444
        )

        embed.add_field(
            name="🔫 Crime Commands",
            value=(
                "**`/rob <user>`** - Rob someone's wallet\n"
                "**`/crime`** - Commit a crime\n\n"
                "**Warning:** You can fail and get caught!"
            ),
            inline=False
        )

        embed.add_field(
            name="🎮 Lockpick Minigame",
            value=(
                "When robbing, you'll play a lockpick game:\n"
                "• Find the correct pin positions\n"
                "• You get hints after each attempt\n"
                "• 3 attempts to crack the lock\n"
                "• Higher crime skill = easier game"
            ),
            inline=False
        )

        embed.add_field(
            name="⚠️ Consequences",
            value=(
                "**Failed robbery:**\n"
                "• You pay the victim 50% of steal amount\n"
                "• May go to jail (can't work/rob)\n\n"
                "**Successful robbery:**\n"
                "• Steal from their wallet (not bank!)\n"
                "• Gain crime XP and skill"
            ),
            inline=False
        )

        embed.add_field(
            name="💡 Crime Tips",
            value=(
                "• Train crime skill for better success\n"
                "• Can't rob guild members\n"
                "• Can't rob people with no money\n"
                "• Risk jail time on failure\n"
                "• Higher risk = higher reward"
            ),
            inline=False
        )

        embed.set_footer(text="Crime doesn't pay... or does it?")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Skills", style=discord.ButtonStyle.secondary, emoji="⚔️", row=1)
    async def skills_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Skills category help."""
        embed = discord.Embed(
            title="⚔️ Skills & Training",
            description="Train skills to improve your abilities!",
            color=0x9B59B6
        )

        embed.add_field(
            name="📊 Skill Commands",
            value=(
                "**`/skills`** - View all your skills\n"
                "**`/train <skill>`** - Train a skill\n"
                "**`/skillinfo <skill>`** - Learn about a skill"
            ),
            inline=False
        )

        embed.add_field(
            name="⚔️ Available Skills",
            value=(
                "💪 **Strength** - Physical power\n"
                "🧠 **Intelligence** - Mental ability\n"
                "🎨 **Creativity** - Artistic talent\n"
                "🤝 **Charisma** - Social skills\n"
                "⚡ **Speed** - Reaction time\n"
                "🏃 **Stamina** - Endurance\n"
                "🔪 **Crime** - Criminal expertise"
            ),
            inline=False
        )

        embed.add_field(
            name="📈 Skill Benefits",
            value=(
                "• **Jobs** - Better performance & pay\n"
                "• **Crime** - Higher success rates\n"
                "• **Casino** - Some games benefit from skills\n"
                "• **Training** - Costs energy, gives XP"
            ),
            inline=False
        )

        embed.add_field(
            name="💡 Training Tips",
            value=(
                "• Training costs energy\n"
                "• Focus on job-related skills first\n"
                "• Skills improve over time with use\n"
                "• Higher skills = better rewards\n"
                "• Balance multiple skills for versatility"
            ),
            inline=False
        )

        embed.set_footer(text="Train daily to become stronger!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Pets", style=discord.ButtonStyle.secondary, emoji="🐾", row=1)
    async def pets_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Pets category help."""
        embed = discord.Embed(
            title="🐾 Pet System",
            description="Adopt pets and care for them to get bonuses!",
            color=0xFF7F50
        )

        embed.add_field(
            name="🐕 Pet Commands",
            value=(
                "**`/adoptpet`** - Adopt a new pet\n"
                "**`/pets`** - View your pets\n"
                "**`/feedpet <pet>`** - Feed your pet\n"
                "**`/playpet <pet>`** - Play with pet\n"
                "**`/trainpet <pet>`** - Train your pet"
            ),
            inline=False
        )

        embed.add_field(
            name="🌟 Pet Rarities",
            value=(
                "⚪ **Common** - Basic bonuses\n"
                "🟢 **Uncommon** - Better bonuses\n"
                "🔵 **Rare** - Great bonuses\n"
                "🟣 **Epic** - Powerful bonuses\n"
                "🟠 **Legendary** - Best bonuses!"
            ),
            inline=False
        )

        embed.add_field(
            name="✨ Pet Benefits",
            value=(
                "• Passive money bonus\n"
                "• XP boost multiplier\n"
                "• Special abilities\n"
                "• Happiness affects bonus strength\n"
                "• Multiple pets stack bonuses!"
            ),
            inline=False
        )

        embed.add_field(
            name="💡 Pet Care Tips",
            value=(
                "• Feed pets regularly to maintain happiness\n"
                "• Play with pets to increase bonding\n"
                "• Train pets to level them up\n"
                "• Higher rarity = better bonuses\n"
                "• Happy pets give better bonuses"
            ),
            inline=False
        )

        embed.set_footer(text="Adopt a pet companion today!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Social", style=discord.ButtonStyle.secondary, emoji="❤️", row=2)
    async def social_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Social category help."""
        embed = discord.Embed(
            title="❤️ Social Features",
            description="Family, relationships, and guilds!",
            color=0xFF69B4
        )

        embed.add_field(
            name="💍 Family System",
            value=(
                "**`/marry <user>`** - Propose marriage\n"
                "**`/divorce`** - End marriage\n"
                "**`/family`** - View family info\n"
                "**`/familybank`** - Shared bank with spouse\n\n"
                "**Bonuses:** +10% XP & money!"
            ),
            inline=False
        )

        embed.add_field(
            name="❤️ Relationships",
            value=(
                "**`/relationships`** - View all relationships\n"
                "**`/interact <user>`** - Interact with someone\n"
                "**`/gift <user> <item>`** - Give gifts\n"
                "**`/askout <user>`** - Start dating\n"
                "**`/breakup <user>`** - End relationship"
            ),
            inline=False
        )

        embed.add_field(
            name="🏰 Guilds",
            value=(
                "**`/createguild <name>`** - Create a guild\n"
                "**`/guild`** - View guild info\n"
                "**`/guildinvite <user>`** - Invite members\n"
                "**`/leaveguild`** - Leave guild\n"
                "**`/guildbank`** - Guild shared bank\n\n"
                "**Bonuses:** XP/money boost, robbery protection!"
            ),
            inline=False
        )

        embed.add_field(
            name="💡 Social Tips",
            value=(
                "• Marriage gives powerful bonuses\n"
                "• Guild members can't rob each other\n"
                "• Higher guild level = better bonuses\n"
                "• Build relationships for benefits\n"
                "• Family bank is shared with spouse"
            ),
            inline=False
        )

        embed.set_footer(text="Build your social network!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Progress", style=discord.ButtonStyle.secondary, emoji="🏆", row=2)
    async def progress_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Progress category help."""
        embed = discord.Embed(
            title="🏆 Progression System",
            description="Achievements, quests, and leveling!",
            color=0xFFD700
        )

        embed.add_field(
            name="⭐ Leveling",
            value=(
                "**Earn XP by:**\n"
                "• Working your job\n"
                "• Training skills\n"
                "• Completing quests\n"
                "• Casino wins\n\n"
                "**Higher level = better jobs and features!**"
            ),
            inline=False
        )

        embed.add_field(
            name="📜 Daily Quests",
            value=(
                "**`/quests`** - View active quests\n"
                "**`/claimquest <number>`** - Claim rewards\n\n"
                "Complete 3 quests daily for bonus rewards!"
            ),
            inline=False
        )

        embed.add_field(
            name="🏆 Achievements",
            value=(
                "**`/achievements`** - View achievements\n"
                "**`/checkachievements`** - Check progress\n\n"
                "Unlock achievements for bonus rewards!"
            ),
            inline=False
        )

        embed.add_field(
            name="💡 Progress Tips",
            value=(
                "• Check quests daily for new tasks\n"
                "• Complete all 3 quests for streak bonus\n"
                "• Achievements give one-time rewards\n"
                "• XP bonuses stack (marriage, guild, pets)\n"
                "• Focus on consistent daily play"
            ),
            inline=False
        )

        embed.set_footer(text="Keep progressing to unlock everything!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Back to Hub", style=discord.ButtonStyle.primary, emoji="🏠", row=2)
    async def hub_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go back to hub."""
        await interaction.response.send_message(
            "✅ Opening your hub dashboard...\n\nUse `/hub` command to access your main dashboard!",
            ephemeral=True
        )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌", row=2)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close help menu."""
        embed = discord.Embed(
            title="📚 Help Menu Closed",
            description="Help closed. Use `/help` anytime to reopen!",
            color=0x5865F2
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
