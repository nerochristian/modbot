# views/shop_views.py

from __future__ import annotations

import discord
import json
from typing import Optional, List, Dict

from utils.format import money
from data.recipes import COOKING_INGREDIENTS
from views.v2_embed import apply_v2_embed_layout


# ============= HELPER FUNCTION =============

def safe_get_inventory(user_data: dict) -> dict:
    """Safely get inventory from user data (handles JSON strings)."""
    inventory = user_data.get("inventory", {})
    
    if isinstance(inventory, str):
        try:
            inventory = json.loads(inventory)
        except:
            inventory = {}
    
    return inventory if isinstance(inventory, dict) else {}


# ============= CONSTANTS =============

SHOP_COLORS = {
    "main": 0x5865F2,
    "food": 0x57F287,
    "tools": 0x3B82F6,
    "consumables": 0xFEE75C,
    "collectibles": 0x9B59B6,
    "vehicles": 0xEB459E,
    "ingredients": 0xFF6B35,
    "success": 0x22C55E,
    "error": 0xEF4444,
}

CATEGORY_EMOJIS = {
    "food": "🍔",
    "tools": "🔧",
    "consumables": "⚡",
    "collectibles": "💎",
    "vehicles": "🚗",
    "housing": "🏠",
    "pets": "🐾",
    "ingredients": "🥕",
    "other": "📦",
}


# ============= SHOP ITEMS DATA =============

SHOP_ITEMS = {
    # Food Items
    "burger": {
        "name": "Burger",
        "description": "A delicious burger that restores hunger",
        "category": "food",
        "price": 50,
        "emoji": "🍔",
        "effects": {"hunger": 30, "health": 5},
        "consumable": True,
    },
    "pizza": {
        "name": "Pizza",
        "description": "Hot pizza slice, very filling",
        "category": "food",
        "price": 100,
        "emoji": "🍕",
        "effects": {"hunger": 50, "health": 10},
        "consumable": True,
    },
    "energy_drink": {
        "name": "Energy Drink",
        "description": "Restores energy quickly",
        "category": "consumables",
        "price": 200,
        "emoji": "⚡",
        "effects": {"energy": 30},
        "consumable": True,
    },
    "coffee": {
        "name": "Coffee",
        "description": "Wake up with a coffee boost",
        "category": "consumables",
        "price": 75,
        "emoji": "☕",
        "effects": {"energy": 15},
        "consumable": True,
    },
    
    # Tools
    "laptop": {
        "name": "Laptop",
        "description": "Required for programming jobs",
        "category": "tools",
        "price": 5000,
        "emoji": "💻",
        "effects": {"work_bonus": 0.05},
        "consumable": False,
    },
    "toolbox": {
        "name": "Toolbox",
        "description": "Useful for mechanic and electrician jobs",
        "category": "tools",
        "price": 2500,
        "emoji": "🧰",
        "effects": {"work_bonus": 0.03},
        "consumable": False,
    },
    
    # Vehicles
    "bicycle": {
        "name": "Bicycle",
        "description": "Get around faster",
        "category": "vehicles",
        "price": 500,
        "emoji": "🚲",
        "effects": {"speed_bonus": 0.05},
        "consumable": False,
    },
    "car": {
        "name": "Car",
        "description": "A nice car for transportation",
        "category": "vehicles",
        "price": 50000,
        "emoji": "🚗",
        "effects": {"speed_bonus": 0.15},
        "consumable": False,
    },
    
    # Collectibles
    "trophy": {
        "name": "Trophy",
        "description": "A shiny trophy for your collection",
        "category": "collectibles",
        "price": 10000,
        "emoji": "🏆",
        "effects": {},
        "consumable": False,
    },
    "gem": {
        "name": "Gem",
        "description": "A valuable gemstone",
        "category": "collectibles",
        "price": 25000,
        "emoji": "💎",
        "effects": {},
        "consumable": False,
    },
}

# Add cooking ingredients
for ing_id, ing_data in COOKING_INGREDIENTS.items():
    SHOP_ITEMS[ing_id] = {
        "name": ing_data["name"],
        "description": "Cooking ingredient for recipes",
        "category": "ingredients",
        "price": ing_data["price"],
        "emoji": ing_data["emoji"],
        "effects": {},
        "consumable": False,
    }


# ============= SHOP BROWSER VIEW =============

class ShopBrowserView(discord.ui.LayoutView):
    """Main shop browser with category navigation."""

    def __init__(self, bot, user: discord.User, category: str = "all"):
        super().__init__(timeout=300)
        self.bot = bot
        self.user = user
        self.category = category
        self.page = 0
        self.items_per_page = 8

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This isn't your shop! Use `/shop` to open your own.",
                ephemeral=True
            )
            return False
        return True

    def get_filtered_items(self) -> List[tuple]:
        """Get items filtered by category."""
        if self.category == "all":
            return list(SHOP_ITEMS.items())
        return [(k, v) for k, v in SHOP_ITEMS.items() if v["category"] == self.category]

    def create_embed(self) -> discord.Embed:
        """Create shop browser embed."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        balance = int(u.get("balance", 0))

        # Get items for current category
        filtered_items = self.get_filtered_items()
        
        # Pagination
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        page_items = filtered_items[start:end]

        # Determine color
        color = SHOP_COLORS.get(self.category, SHOP_COLORS["main"])

        # Category name
        cat_name = self.category.title() if self.category != "all" else "All Items"
        cat_emoji = CATEGORY_EMOJIS.get(self.category, "🛒")

        embed = discord.Embed(
            title=f"{cat_emoji} Shop - {cat_name}",
            description=f"**Your Balance:** {money(balance)}",
            color=color
        )

        # SAFE inventory retrieval
        inventory = safe_get_inventory(u)
        
        # Add items
        if not page_items:
            embed.add_field(
                name="📦 No Items",
                value="No items found in this category.",
                inline=False
            )
        else:
            for item_id, item_data in page_items:
                emoji = item_data.get("emoji", "📦")
                name = item_data["name"]
                price = item_data["price"]
                description = item_data["description"]
                
                # Check if user can afford
                can_afford = balance >= price
                price_display = f"💰 {money(price)}" if can_afford else f"🔒 {money(price)}"

                # Check if already owned
                owned = inventory.get(item_id, 0)
                owned_text = f" • **Owned:** {owned}" if owned > 0 else ""

                embed.add_field(
                    name=f"{emoji} {name}",
                    value=f"{description}\n{price_display}{owned_text}",
                    inline=True
                )

        # Page info
        total_items = len(filtered_items)
        total_pages = (total_items + self.items_per_page - 1) // self.items_per_page
        if total_pages > 0:
            embed.set_footer(text=f"Page {self.page + 1}/{total_pages} • /buy <item> to purchase")
        else:
            embed.set_footer(text="Use category buttons to browse • /buy <item> to purchase")

        return embed

    # Category buttons
    @discord.ui.button(label="All", style=discord.ButtonStyle.secondary, emoji="🛒", row=0)
    async def all_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "all"
        self.page = 0
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Food", style=discord.ButtonStyle.secondary, emoji="🍔", row=0)
    async def food_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "food"
        self.page = 0
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Tools", style=discord.ButtonStyle.secondary, emoji="🔧", row=0)
    async def tools_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "tools"
        self.page = 0
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Consumables", style=discord.ButtonStyle.secondary, emoji="⚡", row=0)
    async def consumables_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "consumables"
        self.page = 0
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Ingredients", style=discord.ButtonStyle.secondary, emoji="🥕", row=1)
    async def ingredients_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "ingredients"
        self.page = 0
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Vehicles", style=discord.ButtonStyle.secondary, emoji="🚗", row=1)
    async def vehicles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "vehicles"
        self.page = 0
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Collectibles", style=discord.ButtonStyle.secondary, emoji="💎", row=1)
    async def collectibles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "collectibles"
        self.page = 0
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    # Navigation buttons
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, emoji="⬅️", row=2)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, emoji="➡️", row=2)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        filtered_items = self.get_filtered_items()
        total_pages = (len(filtered_items) + self.items_per_page - 1) // self.items_per_page
        
        if self.page < total_pages - 1:
            self.page += 1
        
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄", row=2)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌", row=2)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🛒 Shop Closed",
            description="Thanks for browsing! Use `/shop` to reopen.",
            color=SHOP_COLORS["main"]
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


# ============= ITEM DETAIL VIEW =============

class ItemDetailView(discord.ui.LayoutView):
    """Detailed view of a single item with purchase option."""

    def __init__(self, bot, user: discord.User, item_id: str, quantity: int = 1):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.item_id = item_id
        self.quantity = quantity
        self.item_data = SHOP_ITEMS.get(item_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    def create_embed(self) -> discord.Embed:
        """Create item detail embed."""
        if not self.item_data:
            return discord.Embed(
                title="❌ Item Not Found",
                description="This item doesn't exist in the shop.",
                color=SHOP_COLORS["error"]
            )

        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        balance = int(u.get("balance", 0))

        emoji = self.item_data.get("emoji", "📦")
        name = self.item_data["name"]
        description = self.item_data["description"]
        price = self.item_data["price"]
        total_price = price * self.quantity
        category = self.item_data["category"]
        effects = self.item_data.get("effects", {})
        consumable = self.item_data.get("consumable", False)

        # Get owned count
        inventory = safe_get_inventory(u)
        owned = inventory.get(self.item_id, 0)

        can_afford = balance >= total_price

        embed = discord.Embed(
            title=f"{emoji} {name}",
            description=description,
            color=SHOP_COLORS.get(category, SHOP_COLORS["main"])
        )

        embed.add_field(
            name="💰 Price",
            value=f"{money(price)} each\n**Total:** {money(total_price)}",
            inline=True
        )

        embed.add_field(
            name="📦 Category",
            value=category.title(),
            inline=True
        )

        embed.add_field(
            name="📊 Type",
            value="Consumable" if consumable else "Permanent",
            inline=True
        )

        if effects:
            effects_text = []
            for effect, value in effects.items():
                if effect in ["hunger", "health", "energy"]:
                    effects_text.append(f"• +{value} {effect.title()}")
                elif "_bonus" in effect:
                    effects_text.append(f"• +{value * 100}% {effect.replace('_bonus', '').title()} Bonus")
                else:
                    effects_text.append(f"• {effect.title()}: {value}")
            
            embed.add_field(
                name="✨ Effects",
                value="\n".join(effects_text) if effects_text else "None",
                inline=False
            )

        embed.add_field(
            name="🎒 Your Inventory",
            value=f"**Owned:** {owned}",
            inline=True
        )

        embed.add_field(
            name="💵 Your Balance",
            value=money(balance),
            inline=True
        )

        embed.add_field(
            name="📝 Quantity",
            value=f"**{self.quantity}**",
            inline=True
        )

        if can_afford:
            embed.set_footer(text="✅ You can afford this! Click Buy to purchase.")
        else:
            needed = total_price - balance
            embed.set_footer(text=f"❌ You need {money(needed)} more to buy this.")

        return embed

    @discord.ui.button(label="Buy", style=discord.ButtonStyle.success, emoji="💰")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Purchase the item."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        balance = int(u.get("balance", 0))

        total_price = self.item_data["price"] * self.quantity

        if balance < total_price:
            return await interaction.response.send_message(
                f"❌ You can't afford this! You need {money(total_price - balance)} more.",
                ephemeral=True
            )

        # Deduct money
        db.removebalance(userid, total_price)

        # Add to inventory
        inventory = safe_get_inventory(u)
        inventory[self.item_id] = inventory.get(self.item_id, 0) + self.quantity
        db.updatestat(userid, "inventory", json.dumps(inventory))

        # Success message
        emoji = self.item_data.get("emoji", "📦")
        name = self.item_data["name"]

        embed = discord.Embed(
            title="✅ Purchase Successful!",
            description=f"You bought **{self.quantity}x {emoji} {name}** for {money(total_price)}!",
            color=SHOP_COLORS["success"]
        )

        embed.add_field(
            name="💰 New Balance",
            value=money(balance - total_price),
            inline=True
        )

        embed.add_field(
            name="🎒 Total Owned",
            value=f"{inventory[self.item_id]}",
            inline=True
        )

        if self.item_data.get("consumable"):
            embed.set_footer(text="Use /eat or /use to consume this item!")
        elif self.item_data.get("category") == "ingredients":
            embed.set_footer(text="Use /cook to use these ingredients in recipes!")
        else:
            embed.set_footer(text="This item is now in your inventory!")

        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel purchase."""
        embed = discord.Embed(
            title="❌ Purchase Cancelled",
            description="You didn't buy anything.",
            color=SHOP_COLORS["error"]
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
