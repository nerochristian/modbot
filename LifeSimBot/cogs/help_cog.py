"""
Help Cog - Interactive help system with categories and search
Uses Discord Components V2 for modern interactive help menus
"""

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, Select, LayoutView, Modal, TextInput
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from utils.format import format_currency, format_time
from utils.constants import *
from utils.checks import safe_defer, safe_reply
from views.v2_embed import apply_v2_embed_layout

logger = logging.getLogger('LifeSimBot.Help')

class HelpCategory:
    """Help category data structure"""
    
    def __init__(self, name: str, emoji: str, description: str, commands: List[Dict]):
        self.name = name
        self.emoji = emoji
        self.description = description
        self.commands = commands

class HelpSystem:
    """Central help system with all categories and commands"""
    
    @staticmethod
    def get_categories() -> Dict[str, HelpCategory]:
        """Get all help categories"""
        return {
            'core': HelpCategory(
                name="Core",
                emoji="⚙️",
                description="Essential commands to get started",
                commands=[
                    {
                        'name': 'register',
                        'usage': '/register',
                        'description': 'Create your account to start playing',
                        'examples': ['/register']
                    },
                    {
                        'name': 'profile',
                        'usage': '/profile [user]',
                        'description': 'View your profile or another user\'s profile',
                        'examples': ['/profile', '/profile @User']
                    },
                    {
                        'name': 'daily',
                        'usage': '/daily',
                        'description': 'Claim your daily reward (24h cooldown)',
                        'examples': ['/daily']
                    },
                    {
                        'name': 'balance',
                        'usage': '/balance [user]',
                        'description': 'Check your balance or another user\'s balance',
                        'examples': ['/balance', '/balance @User']
                    },
                    {
                        'name': 'stats',
                        'usage': '/stats',
                        'description': 'View your detailed statistics',
                        'examples': ['/stats']
                    },
                    {
                        'name': 'leaderboard',
                        'usage': '/leaderboard [category]',
                        'description': 'View global leaderboards',
                        'examples': ['/leaderboard', '/leaderboard richest']
                    },
                    {
                        'name': 'hub',
                        'usage': '/hub',
                        'description': 'Open the main interactive menu',
                        'examples': ['/hub']
                    }
                ]
            ),
            'economy': HelpCategory(
                name="Economy",
                emoji="💰",
                description="Money management and earning commands",
                commands=[
                    {
                        'name': 'work',
                        'usage': '/work [minigame]',
                        'description': 'Work to earn money with optional minigames',
                        'examples': ['/work', '/work math', '/work typing']
                    },
                    {
                        'name': 'beg',
                        'usage': '/beg',
                        'description': 'Beg for money (low reward)',
                        'examples': ['/beg']
                    },
                    {
                        'name': 'deposit',
                        'usage': '/deposit <amount>',
                        'description': 'Deposit money into your bank',
                        'examples': ['/deposit 1000', '/deposit all']
                    },
                    {
                        'name': 'withdraw',
                        'usage': '/withdraw <amount>',
                        'description': 'Withdraw money from your bank',
                        'examples': ['/withdraw 1000', '/withdraw all']
                    },
                    {
                        'name': 'transfer',
                        'usage': '/transfer <user> <amount>',
                        'description': 'Transfer money to another user (5% tax)',
                        'examples': ['/transfer @User 1000']
                    },
                    {
                        'name': 'rob',
                        'usage': '/rob <user>',
                        'description': 'Attempt to rob another user (risky!)',
                        'examples': ['/rob @User']
                    },
                    {
                        'name': 'give',
                        'usage': '/give <user> <amount>',
                        'description': 'Give money or items to another user',
                        'examples': ['/give @User 500']
                    },
                    {
                        'name': 'investments',
                        'usage': '/investments',
                        'description': 'View and manage your investments',
                        'examples': ['/investments']
                    },
                    {
                        'name': 'loan',
                        'usage': '/loan <action> [amount]',
                        'description': 'Borrow or repay loans',
                        'examples': ['/loan borrow 5000', '/loan repay 1000', '/loan status']
                    }
                ]
            ),
            'casino': HelpCategory(
                name="Casino",
                emoji="🎰",
                description="Gambling and casino games",
                commands=[
                    {
                        'name': 'slots',
                        'usage': '/slots <bet>',
                        'description': 'Play the slot machine',
                        'examples': ['/slots 100']
                    },
                    {
                        'name': 'blackjack',
                        'usage': '/blackjack <bet>',
                        'description': 'Play blackjack against the dealer',
                        'examples': ['/blackjack 500']
                    },
                    {
                        'name': 'roulette',
                        'usage': '/roulette <bet> <choice>',
                        'description': 'Play roulette',
                        'examples': ['/roulette 100 red', '/roulette 500 17']
                    },
                    {
                        'name': 'coinflip',
                        'usage': '/coinflip <bet> <side>',
                        'description': 'Flip a coin and bet on the outcome',
                        'examples': ['/coinflip 100 heads']
                    },
                    {
                        'name': 'dice',
                        'usage': '/dice <bet> <number>',
                        'description': 'Roll dice and bet on the outcome',
                        'examples': ['/dice 100 6']
                    },
                    {
                        'name': 'poker',
                        'usage': '/poker <bet>',
                        'description': 'Play video poker',
                        'examples': ['/poker 250']
                    }
                ]
            ),
            'crypto': HelpCategory(
                name="Cryptocurrency",
                emoji="💎",
                description="Buy, sell, and trade cryptocurrencies",
                commands=[
                    {
                        'name': 'crypto',
                        'usage': '/crypto',
                        'description': 'View cryptocurrency market prices',
                        'examples': ['/crypto']
                    },
                    {
                        'name': 'crypto buy',
                        'usage': '/crypto buy <coin> <amount>',
                        'description': 'Buy cryptocurrency',
                        'examples': ['/crypto buy bitcoin 0.5']
                    },
                    {
                        'name': 'crypto sell',
                        'usage': '/crypto sell <coin> <amount>',
                        'description': 'Sell cryptocurrency',
                        'examples': ['/crypto sell ethereum 2']
                    },
                    {
                        'name': 'crypto portfolio',
                        'usage': '/crypto portfolio',
                        'description': 'View your cryptocurrency portfolio',
                        'examples': ['/crypto portfolio']
                    },
                    {
                        'name': 'crypto chart',
                        'usage': '/crypto chart <coin>',
                        'description': 'View price chart for a cryptocurrency',
                        'examples': ['/crypto chart bitcoin']
                    }
                ]
            ),
            'jobs': HelpCategory(
                name="Jobs & Careers",
                emoji="💼",
                description="Find work and build your career",
                commands=[
                    {
                        'name': 'jobs',
                        'usage': '/jobs',
                        'description': 'Browse available jobs',
                        'examples': ['/jobs']
                    },
                    {
                        'name': 'job apply',
                        'usage': '/job apply <job_name>',
                        'description': 'Apply for a job',
                        'examples': ['/job apply programmer']
                    },
                    {
                        'name': 'job resign',
                        'usage': '/job resign',
                        'description': 'Resign from your current job',
                        'examples': ['/job resign']
                    },
                    {
                        'name': 'job work',
                        'usage': '/job work',
                        'description': 'Work at your job to earn salary',
                        'examples': ['/job work']
                    },
                    {
                        'name': 'job info',
                        'usage': '/job info',
                        'description': 'View your current job information',
                        'examples': ['/job info']
                    }
                ]
            ),
            'businesses': HelpCategory(
                name="Businesses",
                emoji="🏢",
                description="Own and manage businesses",
                commands=[
                    {
                        'name': 'businesses',
                        'usage': '/businesses',
                        'description': 'View available businesses',
                        'examples': ['/businesses']
                    },
                    {
                        'name': 'business buy',
                        'usage': '/business buy <business>',
                        'description': 'Purchase a business',
                        'examples': ['/business buy restaurant']
                    },
                    {
                        'name': 'business manage',
                        'usage': '/business manage',
                        'description': 'Manage your businesses',
                        'examples': ['/business manage']
                    },
                    {
                        'name': 'business collect',
                        'usage': '/business collect',
                        'description': 'Collect income from your businesses',
                        'examples': ['/business collect']
                    },
                    {
                        'name': 'business upgrade',
                        'usage': '/business upgrade <business>',
                        'description': 'Upgrade a business to increase profits',
                        'examples': ['/business upgrade restaurant']
                    }
                ]
            ),
            'properties': HelpCategory(
                name="Properties",
                emoji="🏠",
                description="Buy and manage real estate",
                commands=[
                    {
                        'name': 'properties',
                        'usage': '/properties',
                        'description': 'Browse available properties',
                        'examples': ['/properties']
                    },
                    {
                        'name': 'property buy',
                        'usage': '/property buy <property>',
                        'description': 'Purchase a property',
                        'examples': ['/property buy apartment']
                    },
                    {
                        'name': 'property sell',
                        'usage': '/property sell <property>',
                        'description': 'Sell one of your properties',
                        'examples': ['/property sell apartment']
                    },
                    {
                        'name': 'property manage',
                        'usage': '/property manage',
                        'description': 'Manage your properties',
                        'examples': ['/property manage']
                    }
                ]
            ),
            'skills': HelpCategory(
                name="Skills",
                emoji="🎓",
                description="Level up your skills",
                commands=[
                    {
                        'name': 'skills',
                        'usage': '/skills',
                        'description': 'View your skills',
                        'examples': ['/skills']
                    },
                    {
                        'name': 'skill train',
                        'usage': '/skill train <skill>',
                        'description': 'Train a specific skill',
                        'examples': ['/skill train programming']
                    },
                    {
                        'name': 'skill info',
                        'usage': '/skill info <skill>',
                        'description': 'View information about a skill',
                        'examples': ['/skill info cooking']
                    }
                ]
            ),
            'pets': HelpCategory(
                name="Pets",
                emoji="🐾",
                description="Adopt and care for pets",
                commands=[
                    {
                        'name': 'pets',
                        'usage': '/pets',
                        'description': 'View available pets',
                        'examples': ['/pets']
                    },
                    {
                        'name': 'pet adopt',
                        'usage': '/pet adopt <pet>',
                        'description': 'Adopt a new pet',
                        'examples': ['/pet adopt dog']
                    },
                    {
                        'name': 'pet feed',
                        'usage': '/pet feed <pet>',
                        'description': 'Feed your pet',
                        'examples': ['/pet feed dog']
                    },
                    {
                        'name': 'pet play',
                        'usage': '/pet play <pet>',
                        'description': 'Play with your pet',
                        'examples': ['/pet play cat']
                    },
                    {
                        'name': 'pet info',
                        'usage': '/pet info <pet>',
                        'description': 'View pet information',
                        'examples': ['/pet info dog']
                    }
                ]
            ),
            'cooking': HelpCategory(
                name="Cooking",
                emoji="👨‍🍳",
                description="Cook food and create recipes",
                commands=[
                    {
                        'name': 'recipes',
                        'usage': '/recipes',
                        'description': 'View available recipes',
                        'examples': ['/recipes']
                    },
                    {
                        'name': 'cook',
                        'usage': '/cook <recipe>',
                        'description': 'Cook a recipe',
                        'examples': ['/cook pizza']
                    },
                    {
                        'name': 'eat',
                        'usage': '/eat <food>',
                        'description': 'Eat food to restore stats',
                        'examples': ['/eat pizza']
                    }
                ]
            ),
            'crime': HelpCategory(
                name="Crime",
                emoji="🔫",
                description="Live life on the edge",
                commands=[
                    {
                        'name': 'crime',
                        'usage': '/crime [type]',
                        'description': 'Commit a crime',
                        'examples': ['/crime', '/crime robbery']
                    },
                    {
                        'name': 'heist',
                        'usage': '/heist',
                        'description': 'Start a group heist',
                        'examples': ['/heist']
                    }
                ]
            ),
            'duels': HelpCategory(
                name="Duels",
                emoji="⚔️",
                description="Challenge other players",
                commands=[
                    {
                        'name': 'duel',
                        'usage': '/duel <user> <bet>',
                        'description': 'Challenge another user to a duel',
                        'examples': ['/duel @User 1000']
                    }
                ]
            ),
            'guilds': HelpCategory(
                name="Guilds",
                emoji="🏰",
                description="Create and join guilds",
                commands=[
                    {
                        'name': 'guild create',
                        'usage': '/guild create <name>',
                        'description': 'Create a new guild',
                        'examples': ['/guild create Warriors']
                    },
                    {
                        'name': 'guild join',
                        'usage': '/guild join <guild>',
                        'description': 'Join an existing guild',
                        'examples': ['/guild join Warriors']
                    },
                    {
                        'name': 'guild leave',
                        'usage': '/guild leave',
                        'description': 'Leave your current guild',
                        'examples': ['/guild leave']
                    },
                    {
                        'name': 'guild info',
                        'usage': '/guild info',
                        'description': 'View your guild information',
                        'examples': ['/guild info']
                    }
                ]
            ),
            'family': HelpCategory(
                name="Family",
                emoji="👨‍👩‍👧‍👦",
                description="Build relationships and families",
                commands=[
                    {
                        'name': 'marry',
                        'usage': '/marry <user>',
                        'description': 'Propose marriage to another user',
                        'examples': ['/marry @User']
                    },
                    {
                        'name': 'divorce',
                        'usage': '/divorce',
                        'description': 'Divorce your spouse',
                        'examples': ['/divorce']
                    },
                    {
                        'name': 'family',
                        'usage': '/family',
                        'description': 'View your family tree',
                        'examples': ['/family']
                    }
                ]
            ),
            'achievements': HelpCategory(
                name="Achievements",
                emoji="🏆",
                description="Track your progress",
                commands=[
                    {
                        'name': 'achievements',
                        'usage': '/achievements',
                        'description': 'View all achievements',
                        'examples': ['/achievements']
                    }
                ]
            ),
            'quests': HelpCategory(
                name="Quests",
                emoji="📜",
                description="Complete quests for rewards",
                commands=[
                    {
                        'name': 'quests',
                        'usage': '/quests',
                        'description': 'View available quests',
                        'examples': ['/quests']
                    },
                    {
                        'name': 'quest accept',
                        'usage': '/quest accept <quest>',
                        'description': 'Accept a quest',
                        'examples': ['/quest accept daily_grind']
                    },
                    {
                        'name': 'quest abandon',
                        'usage': '/quest abandon <quest>',
                        'description': 'Abandon a quest',
                        'examples': ['/quest abandon daily_grind']
                    }
                ]
            ),
            'inventory': HelpCategory(
                name="Inventory",
                emoji="🎒",
                description="Manage your items",
                commands=[
                    {
                        'name': 'inventory',
                        'usage': '/inventory',
                        'description': 'View your inventory',
                        'examples': ['/inventory']
                    },
                    {
                        'name': 'use',
                        'usage': '/use <item>',
                        'description': 'Use an item from your inventory',
                        'examples': ['/use health_potion']
                    },
                    {
                        'name': 'sell',
                        'usage': '/sell <item> [quantity]',
                        'description': 'Sell items from your inventory',
                        'examples': ['/sell apple 5']
                    }
                ]
            ),
            'shop': HelpCategory(
                name="Shop",
                emoji="🛒",
                description="Buy and sell items",
                commands=[
                    {
                        'name': 'shop',
                        'usage': '/shop [category]',
                        'description': 'Browse the shop',
                        'examples': ['/shop', '/shop food']
                    },
                    {
                        'name': 'buy',
                        'usage': '/buy <item> [quantity]',
                        'description': 'Buy items from the shop',
                        'examples': ['/buy apple 10']
                    }
                ]
            ),
            'social': HelpCategory(
                name="Social",
                emoji="👥",
                description="Interact with other players",
                commands=[
                    {
                        'name': 'social',
                        'usage': '/social',
                        'description': 'View your social connections',
                        'examples': ['/social']
                    },
                    {
                        'name': 'friend',
                        'usage': '/friend <user>',
                        'description': 'Send a friend request',
                        'examples': ['/friend @User']
                    },
                    {
                        'name': 'unfriend',
                        'usage': '/unfriend <user>',
                        'description': 'Remove a friend',
                        'examples': ['/unfriend @User']
                    }
                ]
            )
        }

class HelpCategorySelect(Select):
    """Select menu for choosing help category"""
    
    def __init__(self, view: 'HelpView'):
        self.help_view = view
        
        # Create options from categories
        categories = HelpSystem.get_categories()
        options = [
            discord.SelectOption(
                label=cat.name,
                value=key,
                emoji=cat.emoji,
                description=cat.description[:100]
            )
            for key, cat in categories.items()
        ]
        
        super().__init__(
            placeholder="Choose a category...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle category selection"""
        category_key = self.values[0]
        categories = HelpSystem.get_categories()
        category = categories[category_key]
        
        # Create category embed
        embed = self.help_view.create_category_embed(category)
        
        apply_v2_embed_layout(self.help_view, embed=embed)
        await interaction.response.edit_message(view=self.help_view)

class HelpCommandSelect(Select):
    """Select menu for viewing specific command details"""
    
    def __init__(self, view: 'HelpView', commands: List[Dict]):
        self.help_view = view
        self._commands: List[Dict] = []
        
        options: list[discord.SelectOption] = []
        for cmd in commands[:25]:
            options.append(
                discord.SelectOption(
                    label=cmd["name"],
                    value=cmd["name"],
                    description=cmd["description"][:100],
                )
            )
        self._commands = list(commands)

        if not options:
            options = [
                discord.SelectOption(
                    label="Select a category first",
                    value="__noop__",
                    description="Pick a category above to load commands.",
                )
            ]
        
        super().__init__(
            placeholder="Select a command for details...",
            min_values=1,
            max_values=1,
            options=options,
            row=1
        )
        self.disabled = options[0].value == "__noop__"

    def set_commands(self, commands: List[Dict]) -> None:
        options: list[discord.SelectOption] = []
        for cmd in commands[:25]:
            options.append(
                discord.SelectOption(
                    label=cmd["name"],
                    value=cmd["name"],
                    description=cmd["description"][:100],
                )
            )

        self._commands = list(commands)
        if not options:
            options = [
                discord.SelectOption(
                    label="No commands available",
                    value="__noop__",
                    description="This category has no commands.",
                )
            ]
        self.options = options
        self.disabled = options[0].value == "__noop__"
        self.placeholder = (
            "Select a command for details..."
            if not self.disabled
            else "Select a category to view commands..."
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle command selection"""
        command_name = self.values[0]
        if command_name == "__noop__":
            return await interaction.response.defer()
        
        # Find the command in all categories
        categories = HelpSystem.get_categories()
        found_command = None
        
        for category in categories.values():
            for cmd in category.commands:
                if cmd['name'] == command_name:
                    found_command = cmd
                    break
            if found_command:
                break
        
        if found_command:
            embed = self.help_view.create_command_embed(found_command)
            apply_v2_embed_layout(self.help_view, embed=embed)
            await interaction.response.edit_message(view=self.help_view)

class HelpSearchModal(Modal, title="Search Commands"):
    """Modal for searching commands"""
    
    search_query = TextInput(
        label="Search Query",
        placeholder="Enter command name or keyword...",
        required=True,
        min_length=1,
        max_length=50
    )
    
    def __init__(self, view: 'HelpView'):
        super().__init__()
        self.help_view = view
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle search submission"""
        query = self.search_query.value.lower().strip()
        
        # Search through all commands
        categories = HelpSystem.get_categories()
        results = []
        
        for category in categories.values():
            for cmd in category.commands:
                if (query in cmd['name'].lower() or 
                    query in cmd['description'].lower()):
                    results.append((category, cmd))
        
        if not results:
            await interaction.response.send_message(
                f"❌ No commands found matching '{query}'",
                ephemeral=True
            )
            return
        
        # Create results embed
        embed = discord.Embed(
            title=f"🔍 Search Results: {query}",
            description=f"Found {len(results)} command(s)",
            color=discord.Color.blue()
        )
        
        for category, cmd in results[:10]:  # Show max 10 results
            embed.add_field(
                name=f"{category.emoji} {cmd['name']}",
                value=f"{cmd['description']}\n`{cmd['usage']}`",
                inline=False
            )
        
        if len(results) > 10:
            embed.set_footer(text=f"Showing 10 of {len(results)} results")
        
        apply_v2_embed_layout(self.help_view, embed=embed)
        await interaction.response.edit_message(view=self.help_view)

class HelpView(LayoutView):
    """Main help view with category navigation"""
    
    def __init__(self, user: discord.User, timeout=300):
        super().__init__(timeout=timeout)
        self.user = user
        self.current_category = None
        
        # Add category select
        self.category_select = HelpCategorySelect(self)
        self.add_item(self.category_select)

        # Add command select (disabled until a category is picked)
        self.command_select = HelpCommandSelect(self, [])
        self.add_item(self.command_select)
    
    def create_home_embed(self) -> discord.Embed:
        """Create the home help embed"""
        embed = discord.Embed(
            title="📚 LifeSimBot Help",
            description=(
                "Welcome to LifeSimBot's interactive help system!\n\n"
                "**How to use:**\n"
                "• Use the dropdown menu below to browse categories\n"
                "• Click buttons for quick actions\n"
                "• Use the search feature to find specific commands\n\n"
                "**Quick Links:**\n"
                "• [Bot Invite](https://discord.com)\n"
                "• [Support Server](https://discord.com)\n"
                "• [Documentation](https://discord.com)"
            ),
            color=discord.Color.blue()
        )
        
        # Add quick category overview
        categories = HelpSystem.get_categories()
        categories_text = "\n".join([
            f"{cat.emoji} **{cat.name}** - {cat.description}"
            for cat in list(categories.values())[:8]
        ])
        
        embed.add_field(
            name="📋 Categories",
            value=categories_text,
            inline=False
        )
        
        embed.set_footer(text="Select a category from the dropdown to get started")
        embed.timestamp = datetime.utcnow()
        
        return embed
    
    def create_category_embed(self, category: HelpCategory) -> discord.Embed:
        """Create category-specific embed"""
        self.current_category = category
        
        embed = discord.Embed(
            title=f"{category.emoji} {category.name} Commands",
            description=category.description,
            color=discord.Color.green()
        )
        
        # Group commands if there are many
        for cmd in category.commands:
            embed.add_field(
                name=f"/{cmd['name']}",
                value=f"{cmd['description']}\n`{cmd['usage']}`",
                inline=False
            )
        
        embed.set_footer(text=f"Showing {len(category.commands)} command(s) | Use command select for details")
        embed.timestamp = datetime.utcnow()
        
        # Update view to show command select
        self.update_view_for_category(category)
        
        return embed
    
    def create_command_embed(self, command: Dict) -> discord.Embed:
        """Create detailed command embed"""
        embed = discord.Embed(
            title=f"📖 /{command['name']}",
            description=command['description'],
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💡 Usage",
            value=f"`{command['usage']}`",
            inline=False
        )
        
        if command.get('examples'):
            examples_text = "\n".join([f"`{ex}`" for ex in command['examples']])
            embed.add_field(
                name="📝 Examples",
                value=examples_text,
                inline=False
            )
        
        embed.set_footer(text="Use the dropdown to view other commands")
        embed.timestamp = datetime.utcnow()
        
        return embed
    
    def update_view_for_category(self, category: HelpCategory):
        """Update view when category is selected"""
        self.command_select.set_commands(category.commands)
    
    @discord.ui.button(label="🏠 Home", style=discord.ButtonStyle.primary, row=2)
    async def home_button(self, interaction: discord.Interaction, button: Button):
        """Return to home page"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This is not your help menu!",
                ephemeral=True
            )
            return
        
        self.command_select.set_commands([])
        
        self.current_category = None
        embed = self.create_home_embed()
        apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="🔍 Search", style=discord.ButtonStyle.secondary, row=2)
    async def search_button(self, interaction: discord.Interaction, button: Button):
        """Open search modal"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This is not your help menu!",
                ephemeral=True
            )
            return
        
        modal = HelpSearchModal(self)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger, row=2)
    async def close_button(self, interaction: discord.Interaction, button: Button):
        """Close the help menu"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This is not your help menu!",
                ephemeral=True
            )
            return
        
        self.stop()
        await interaction.response.edit_message(view=None)
    
    async def on_timeout(self):
        """Called when view times out"""
        # Try to remove buttons
        try:
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=None)
        except:
            pass

class Help(commands.Cog):
    """Help and documentation commands"""
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("Help cog initialized")
    
    @app_commands.command(name="help", description="View interactive help menu")
    @app_commands.describe(command="Get help for a specific command")
    async def help_command(self, interaction: discord.Interaction, command: Optional[str] = None):
        """Interactive help system"""
        await safe_defer(interaction)
        
        if command:
            # Search for specific command
            categories = HelpSystem.get_categories()
            found_command = None
            found_category = None
            
            for category in categories.values():
                for cmd in category.commands:
                    if cmd['name'].lower() == command.lower():
                        found_command = cmd
                        found_category = category
                        break
                if found_command:
                    break
            
            if not found_command:
                return await safe_reply(
                    interaction,
                    content=f"ƒ?O Command '{command}' not found. Use `/help` to browse all commands.",
                    ephemeral=True,
                )
                await interaction.response.send_message(
                    f"❌ Command '{command}' not found. Use `/help` to browse all commands.",
                    ephemeral=True
                )
                return
            
            # Create detailed command embed
            embed = discord.Embed(
                title=f"{found_category.emoji} /{found_command['name']}",
                description=found_command['description'],
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="📁 Category",
                value=found_category.name,
                inline=True
            )
            
            embed.add_field(
                name="💡 Usage",
                value=f"`{found_command['usage']}`",
                inline=False
            )
            
            if found_command.get('examples'):
                examples_text = "\n".join([f"`{ex}`" for ex in found_command['examples']])
                embed.add_field(
                    name="📝 Examples",
                    value=examples_text,
                    inline=False
                )
            
            embed.set_footer(text="Use /help to view all commands")
            embed.timestamp = datetime.utcnow()
            
            await interaction.followup.send(embed=embed)
        
        else:
            # Show interactive help menu
            view = HelpView(interaction.user)
            embed = view.create_home_embed()
            
            apply_v2_embed_layout(view, embed=embed)
            view.message = await interaction.followup.send(view=view)
    
    @app_commands.command(name="commands", description="List all available commands")
    @app_commands.describe(category="Filter by category")
    async def commands_list(self, interaction: discord.Interaction, category: Optional[str] = None):
        """List all commands"""
        categories = HelpSystem.get_categories()
        
        if category:
            # Show specific category
            if category.lower() not in categories:
                await interaction.response.send_message(
                    f"❌ Category '{category}' not found.",
                    ephemeral=True
                )
                return
            
            cat = categories[category.lower()]
            
            embed = discord.Embed(
                title=f"{cat.emoji} {cat.name} Commands",
                description=cat.description,
                color=discord.Color.blue()
            )
            
            commands_text = "\n".join([
                f"**/{cmd['name']}** - {cmd['description']}"
                for cmd in cat.commands
            ])
            
            embed.add_field(
                name="Commands",
                value=commands_text,
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        
        else:
            # Show all categories with command count
            embed = discord.Embed(
                title="📚 All Command Categories",
                description="Here are all available command categories:",
                color=discord.Color.blue()
            )
            
            total_commands = 0
            
            for key, cat in categories.items():
                command_count = len(cat.commands)
                total_commands += command_count
                
                embed.add_field(
                    name=f"{cat.emoji} {cat.name}",
                    value=f"{cat.description}\n**{command_count} commands**",
                    inline=True
                )
            
            embed.set_footer(text=f"Total: {total_commands} commands | Use /help for interactive menu")
            embed.timestamp = datetime.utcnow()
            
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="guide", description="Get started guide for new players")
    async def guide(self, interaction: discord.Interaction):
        """Show getting started guide"""
        
        embed = discord.Embed(
            title="📖 Getting Started Guide",
            description="Welcome to LifeSimBot! Here's everything you need to know to get started.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="1️⃣ Register Your Account",
            value=(
                "Use `/register` to create your account.\n"
                "You'll choose a username, bio, and favorite color!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="2️⃣ Claim Daily Rewards",
            value=(
                "Use `/daily` every 24 hours to get free money!\n"
                "Build up a streak for bonus rewards."
            ),
            inline=False
        )
        
        embed.add_field(
            name="3️⃣ Start Earning Money",
            value=(
                "• Use `/work` to earn money through minigames\n"
                "• Try `/beg` if you're desperate\n"
                "• Apply for `/jobs` for steady income"
            ),
            inline=False
        )
        
        embed.add_field(
            name="4️⃣ Manage Your Money",
            value=(
                "• Use `/deposit` to keep money safe in the bank\n"
                "• Use `/withdraw` when you need it\n"
                "• Try `/investments` to grow your wealth"
            ),
            inline=False
        )
        
        embed.add_field(
            name="5️⃣ Have Fun!",
            value=(
                "• Play casino games with `/slots`, `/blackjack`\n"
                "• Trade crypto with `/crypto`\n"
                "• Build businesses with `/business`\n"
                "• Complete quests with `/quests`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Pro Tips",
            value=(
                "• Use `/hub` for a quick access main menu\n"
                "• Check `/leaderboard` to see top players\n"
                "• Use `/profile` to view your progress\n"
                "• Join a `/guild` to play with others"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use /help for detailed command information")
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="faq", description="Frequently asked questions")
    async def faq(self, interaction: discord.Interaction):
        """Show FAQ"""
        
        embed = discord.Embed(
            title="❓ Frequently Asked Questions",
            description="Common questions about LifeSimBot",
            color=discord.Color.blue()
        )
        
        faqs = [
            {
                'q': 'How do I start playing?',
                'a': 'Use `/register` to create your account, then use `/guide` to learn the basics!'
            },
            {
                'q': 'How do I earn money?',
                'a': 'Use `/work`, `/daily`, apply for `/jobs`, or try your luck in the `/casino`!'
            },
            {
                'q': 'Is my money safe?',
                'a': 'Yes! Use `/deposit` to store money in your bank where it can\'t be stolen.'
            },
            {
                'q': 'Can I lose money?',
                'a': 'Yes - through gambling, being robbed, or failed crimes. Be careful!'
            },
            {
                'q': 'How do cooldowns work?',
                'a': 'Most commands have cooldowns to prevent spam. The time varies by command.'
            },
            {
                'q': 'Can I play with friends?',
                'a': 'Yes! Join `/guilds`, get `/married`, or `/duel` your friends!'
            },
            {
                'q': 'What are achievements?',
                'a': 'Complete specific tasks to unlock achievements! Check them with `/achievements`'
            },
            {
                'q': 'How do I level up?',
                'a': 'Earn XP by using commands and completing activities. Higher levels unlock features!'
            },
            {
                'q': 'Can I trade with others?',
                'a': 'Yes! Use `/transfer` for money or `/give` for items.'
            },
            {
                'q': 'Where can I get help?',
                'a': 'Use `/help` for commands or join our support server (coming soon)!'
            }
        ]
        
        for faq in faqs:
            embed.add_field(
                name=f"Q: {faq['q']}",
                value=f"A: {faq['a']}",
                inline=False
            )
        
        embed.set_footer(text="Still have questions? Ask in our support server!")
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="changelog", description="View recent bot updates")
    async def changelog(self, interaction: discord.Interaction):
        """Show changelog"""
        
        embed = discord.Embed(
            title="📝 Changelog",
            description="Recent updates and changes to LifeSimBot",
            color=discord.Color.purple()
        )
        
        # Version 2.0.0
        embed.add_field(
            name="🎉 Version 2.0.0 - Major Update",
            value=(
                "**New Features:**\n"
                "• Complete rewrite with Discord Components V2\n"
                "• Interactive menus with buttons and select menus\n"
                "• Enhanced UI/UX across all commands\n"
                "• New investment system\n"
                "• Improved minigames with modals\n"
                "• Better error handling\n\n"
                "**Improvements:**\n"
                "• Faster response times\n"
                "• Better database optimization\n"
                "• More intuitive command structure\n"
                "• Enhanced help system\n\n"
                "**Bug Fixes:**\n"
                "• Fixed various money duplication bugs\n"
                "• Fixed cooldown bypass exploits\n"
                "• Fixed inventory management issues"
            ),
            inline=False
        )
        
        embed.set_footer(text="Thank you for using LifeSimBot!")
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="about", description="About LifeSimBot")
    async def about(self, interaction: discord.Interaction):
        """Show bot information"""
        
        embed = discord.Embed(
            title="🤖 About LifeSimBot",
            description=(
                "LifeSimBot is a comprehensive life simulation Discord bot "
                "with economy, businesses, jobs, skills, and much more!\n\n"
                "Built with Discord.py and powered by SQLite."
            ),
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📊 Statistics",
            value=(
                f"**Servers:** {len(self.bot.guilds)}\n"
                f"**Users:** {sum(g.member_count for g in self.bot.guilds)}\n"
                f"**Commands:** {len(self.bot.tree.get_commands())}\n"
                f"**Uptime:** {format_time(int((datetime.utcnow() - self.bot.start_time).total_seconds()))}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="💻 Technology",
            value=(
                f"**Discord.py:** {discord.__version__}\n"
                "**Python:** 3.10+\n"
                "**Database:** SQLite\n"
                "**UI:** Components V2"
            ),
            inline=True
        )
        
        embed.add_field(
            name="✨ Features",
            value=(
                "• Economy & Banking\n"
                "• Casino Games\n"
                "• Cryptocurrency\n"
                "• Businesses & Properties\n"
                "• Jobs & Skills\n"
                "• Pets & Cooking\n"
                "• Crime & Duels\n"
                "• Guilds & Families\n"
                "• Achievements & Quests"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔗 Links",
            value=(
                "[Invite Bot](https://discord.com) • "
                "[Support Server](https://discord.com) • "
                "[Documentation](https://discord.com) • "
                "[GitHub](https://github.com)"
            ),
            inline=False
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url if self.bot.user else None)
        embed.set_footer(text="Made with ❤️ for the Discord community")
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="support", description="Get support and report issues")
    async def support(self, interaction: discord.Interaction):
        """Show support information"""
        
        embed = discord.Embed(
            title="🆘 Support",
            description="Need help? Here's how to get support:",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="📚 Documentation",
            value=(
                "Check out our comprehensive documentation:\n"
                "[Bot Documentation](https://discord.com)\n\n"
                "It includes guides, tutorials, and command references."
            ),
            inline=False
        )
        
        embed.add_field(
            name="💬 Support Server",
            value=(
                "Join our support server for help:\n"
                "[Join Support Server](https://discord.com)\n\n"
                "Our staff and community are here to help!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🐛 Report Bugs",
            value=(
                "Found a bug? Report it:\n"
                "• In our support server\n"
                "• On GitHub Issues\n"
                "• Via bot feedback system"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Feature Requests",
            value=(
                "Have an idea? We'd love to hear it!\n"
                "Submit feature requests in our support server."
            ),
            inline=False
        )
        
        embed.add_field(
            name="📧 Contact",
            value=(
                "**Email:** support@lifesimbot.com (coming soon)\n"
                "**Discord:** Support Server (coming soon)"
            ),
            inline=False
        )
        
        embed.set_footer(text="We typically respond within 24 hours")
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Help(bot))
