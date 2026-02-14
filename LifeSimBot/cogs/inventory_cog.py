# cogs/inventory_cog.py

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List, Dict
import json

from views.inventory_views import InventoryView, ItemUseView, ItemDetailView
from views.shop_views import SHOP_ITEMS, safe_get_inventory
from data.recipes import RECIPES
from utils.checks import safe_defer, safe_reply
from utils.format import money
from views.v2_embed import apply_v2_embed_layout


def parse_inventory(inventory_data):
    """Parse inventory from DB (handles both dict and JSON string)."""
    if isinstance(inventory_data, dict):
        return inventory_data
    elif isinstance(inventory_data, str):
        try:
            return json.loads(inventory_data)
        except:
            return {}
    return {}


# ============= ITEM SELECTOR FOR USE/EAT/DROP =============

class ItemSelectorView(discord.ui.LayoutView):
    """Generic item selector with dropdown."""
    
    def __init__(self, bot, user: discord.User, items: List[Dict], action: str):
        super().__init__(timeout=120)
        self.bot = bot
        self.user = user
        self.items = items
        self.action = action
        
        # Add select menu if items exist
        if items:
            self.add_item(ItemSelectMenu(items, action))
    
    def create_components(self):
        """Build v2 component layout for item selection."""
        action_info = {
            "use": {"emoji": "✨", "title": "Use Item", "tip": "💡 Consumables restore stats like energy and health"},
            "eat": {"emoji": "🍔", "title": "Eat Food", "tip": "💡 Cooked dishes are better than raw ingredients!"},
            "drop": {"emoji": "🗑️", "title": "Drop Items", "tip": "⚠️ Dropped items are permanently deleted!"}
        }
        
        info = action_info.get(self.action, {"emoji": "📦", "title": "Select Item", "tip": ""})
        
        components = []
        
        # Header
        header = f"# {info['emoji']} {info['title']}\n\n"
        header += f"Select an item to {self.action} from the dropdown below.\n\n"
        header += f"**Available items:** {len(self.items)}"
        
        components.append(discord.ui.TextDisplay(content=header))
        try:
            from views.v2_embed import _safe_separator

            components.append(_safe_separator())
        except Exception:
            components.append(discord.ui.Separator())
        
        # Tip
        if info['tip']:
            components.append(discord.ui.TextDisplay(content=info['tip']))
        
        return components
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This isn't your inventory!",
                ephemeral=True
            )
            return False
        return True


class ItemSelectMenu(discord.ui.Select):
    """Dropdown for selecting items."""
    
    def __init__(self, items: List[Dict], action: str):
        self.action = action
        self.items_data = {item["id"]: item for item in items}
        
        options = []
        for item in items[:25]:  # Discord limit
            description = f"{item['quantity']}x owned"
            if item.get("effects"):
                effects_str = ", ".join([f"+{v} {k}" for k, v in item["effects"].items()])
                description += f" | {effects_str}"
            
            options.append(
                discord.SelectOption(
                    label=item["name"],
                    value=item["id"],
                    description=description[:100],
                    emoji=item.get("emoji", "📦")
                )
            )
        
        super().__init__(
            placeholder=f"Select an item to {action}...",
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        selected_id = self.values[0]
        item_data = self.items_data[selected_id]
        
        if self.action in ["eat", "use"]:
            # Show ItemUseView
            view = ItemUseView(
                interaction.client,
                interaction.user,
                selected_id,
                1
            )
            apply_v2_embed_layout(view, body_items=view.create_components())
            await interaction.response.edit_message(view=view)
        elif self.action == "drop":
            # Show drop confirmation
            view = DropConfirmView(
                interaction.client,
                interaction.user,
                selected_id,
                item_data
            )
            apply_v2_embed_layout(view, body_items=view.create_components())
            await interaction.response.edit_message(view=view)


class DropConfirmView(discord.ui.LayoutView):
    """Confirmation view for dropping items."""
    
    def __init__(self, bot, user: discord.User, item_id: str, item_data: Dict):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.item_id = item_id
        self.item_data = item_data
    
    def create_components(self):
        """Build drop confirmation layout."""
        emoji = self.item_data.get("emoji", "📦")
        name = self.item_data.get("name", self.item_id)
        qty = self.item_data.get("quantity", 0)
        
        components = [
            discord.ui.TextDisplay(
                content=f"# 🗑️ Drop Items?\n\n"
                        f"**Item:** {emoji} {name}\n"
                        f"**You have:** {qty}x\n\n"
                        f"⚠️ **Warning:** Dropped items are permanently deleted!"
            )
        ]
        
        return components
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id
    
    @discord.ui.button(label="Drop 1", style=discord.ButtonStyle.secondary, emoji="1️⃣")
    async def drop_one(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._drop_items(interaction, 1)
    
    @discord.ui.button(label="Drop All", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def drop_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._drop_items(interaction, self.item_data.get("quantity", 0))
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.success, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Cancelled",
            description="No items were dropped.",
            color=discord.Color.red(),
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    async def _drop_items(self, interaction: discord.Interaction, quantity: int):
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        inventory = parse_inventory(u.get("inventory", {}))
        
        owned = inventory.get(self.item_id, 0)
        qty_dropped = min(quantity, owned)
        
        inventory[self.item_id] = owned - qty_dropped
        if inventory[self.item_id] <= 0:
            del inventory[self.item_id]
        db.updatestat(userid, "inventory", json.dumps(inventory))
        
        emoji = self.item_data.get("emoji", "📦")
        name = self.item_data.get("name", self.item_id)
        
        embed = discord.Embed(
            title="🗑️ Items Dropped!",
            description=(
                f"**Dropped:** {qty_dropped}x {emoji} {name}\n"
                f"**Remaining:** {inventory.get(self.item_id, 0)}x\n\n"
                "Items permanently deleted!"
            ),
            color=discord.Color.orange(),
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


# ============= MAIN COG =============

class InventoryCog(commands.Cog):
    """Inventory management and item usage with Components V2."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="inventory", description="🎒 View your inventory")
    @app_commands.describe(category="Filter by category")
    @app_commands.choices(category=[
        app_commands.Choice(name="🎒 All Items", value="all"),
        app_commands.Choice(name="🍔 Food", value="food"),
        app_commands.Choice(name="⚡ Consumables", value="consumables"),
        app_commands.Choice(name="🔧 Tools", value="tools"),
        app_commands.Choice(name="🚗 Vehicles", value="vehicles"),
        app_commands.Choice(name="💎 Collectibles", value="collectibles"),
        app_commands.Choice(name="🥕 Ingredients", value="ingredients"),
        app_commands.Choice(name="🍳 Cooked Dishes", value="cooked"),
    ])
    async def inventory(self, interaction: discord.Interaction, category: str = "all"):
        """View your inventory with filtering and pagination."""
        await safe_defer(interaction, ephemeral=True)
        
        view = InventoryView(self.bot, interaction.user, category)
        apply_v2_embed_layout(view, body_items=view.create_components())
        
        await interaction.followup.send(view=view, ephemeral=True)
    
    @app_commands.command(name="use", description="✨ Use a consumable item from your inventory")
    async def use(self, interaction: discord.Interaction):
        """Use consumable items - shows interactive selection menu."""
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        inventory = parse_inventory(u.get("inventory", {}))
        
        # Get all usable items
        usable_items = []
        
        for item_id, quantity in inventory.items():
            if quantity <= 0:
                continue
                
            # Check shop items
            item_data = SHOP_ITEMS.get(item_id)
            if item_data and item_data.get("consumable", False):
                effects = {}
                if "energy_restore" in item_data:
                    effects["Energy"] = item_data["energy_restore"]
                if "health_restore" in item_data:
                    effects["Health"] = item_data["health_restore"]
                if "hunger_restore" in item_data:
                    effects["Hunger"] = item_data["hunger_restore"]
                
                usable_items.append({
                    "id": item_id,
                    "name": item_data["name"],
                    "emoji": item_data.get("emoji", "📦"),
                    "quantity": quantity,
                    "effects": effects
                })
        
        if not usable_items:
            embed = discord.Embed(
                title="❌ No Usable Items",
                description=(
                    "You don't have any consumable items!\n\n"
                    "**Get items from:**\n"
                    "• `/shop consumables` - Buy consumables\n"
                    "• `/work` - Earn items from jobs\n"
                    "• `/crime` - Steal items (risky!)"
                ),
                color=discord.Color.red(),
            )
            return await interaction.followup.send(embed=embed)
        
        # Show selection menu
        view = ItemSelectorView(self.bot, interaction.user, usable_items, "use")
        apply_v2_embed_layout(view, body_items=view.create_components())
        
        await interaction.followup.send(view=view)
    
    @app_commands.command(name="eat", description="🍔 Eat food to restore hunger and stats")
    async def eat(self, interaction: discord.Interaction):
        """Eat food items - shows interactive selection menu."""
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        inventory = parse_inventory(u.get("inventory", {}))
        
        # Get all edible items
        edible_items = []
        
        for item_id, quantity in inventory.items():
            if quantity <= 0:
                continue
            
            # Check cooked dishes
            if item_id.startswith("cooked_"):
                parts = item_id.split("_")
                quality = parts[-1]
                recipe_id = "_".join(parts[1:-1])
                recipe_data = RECIPES.get(recipe_id)
                
                if recipe_data:
                    quality_multipliers = {"perfect": 1.5, "good": 1.0, "burnt": 0.5}
                    multiplier = quality_multipliers.get(quality, 1.0)
                    
                    effects = {}
                    for effect, value in recipe_data["effects"].items():
                        effects[effect.title()] = int(value * multiplier)
                    
                    quality_emojis = {"perfect": "✨", "good": "👍", "burnt": "🔥"}
                    
                    edible_items.append({
                        "id": item_id,
                        "name": f"{quality_emojis.get(quality, '')} {quality.title()} {recipe_data['name']}",
                        "emoji": recipe_data["emoji"],
                        "quantity": quantity,
                        "effects": effects
                    })
            
            # Check shop food items
            else:
                item_data = SHOP_ITEMS.get(item_id)
                if item_data and item_data.get("category") in ["food", "consumables"]:
                    effects = {}
                    if "energy_restore" in item_data:
                        effects["Energy"] = item_data["energy_restore"]
                    if "health_restore" in item_data:
                        effects["Health"] = item_data["health_restore"]
                    if "hunger_restore" in item_data:
                        effects["Hunger"] = item_data["hunger_restore"]
                    
                    edible_items.append({
                        "id": item_id,
                        "name": item_data["name"],
                        "emoji": item_data.get("emoji", "🍔"),
                        "quantity": quantity,
                        "effects": effects
                    })
        
        if not edible_items:
            embed = discord.Embed(
                title="❌ No Food",
                description=(
                    "You don't have any food to eat!\n\n"
                    "**Get food from:**\n"
                    "• `/shop food` - Buy food items\n"
                    "• `/cook` - Cook recipes\n"
                    "• `/work` - Some jobs give food"
                ),
                color=discord.Color.red(),
            )
            return await interaction.followup.send(embed=embed)
        
        # Show selection menu
        view = ItemSelectorView(self.bot, interaction.user, edible_items, "eat")
        apply_v2_embed_layout(view, body_items=view.create_components())
        
        await interaction.followup.send(view=view)
    
    @app_commands.command(name="iteminfo", description="📋 View detailed information about an item")
    @app_commands.describe(item="Item name to view")
    async def iteminfo(self, interaction: discord.Interaction, item: str):
        """View detailed item information."""
        await safe_defer(interaction, ephemeral=True)
        
        # Find item
        item_id = item.lower().replace(" ", "_")
        item_data = None
        
        for iid, idata in SHOP_ITEMS.items():
            if iid == item_id or idata["name"].lower() == item.lower():
                item_id = iid
                item_data = idata
                break
        
        if not item_data:
            embed = discord.Embed(
                title="❌ Item Not Found",
                description=f"Item **{item}** not found in shop database!",
                color=discord.Color.red(),
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)
        
        view = ItemDetailView(self.bot, interaction.user, item_id)
        apply_v2_embed_layout(view, body_items=view.create_components())
        
        await interaction.followup.send(view=view, ephemeral=True)
    
    @app_commands.command(name="drop", description="🗑️ Drop items from your inventory")
    async def drop(self, interaction: discord.Interaction):
        """Drop (delete) items from inventory - shows selection menu."""
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        inventory = parse_inventory(u.get("inventory", {}))
        
        if not inventory or all(qty <= 0 for qty in inventory.values()):
            embed = discord.Embed(
                title="❌ Empty Inventory",
                description="You don't have any items to drop!",
                color=discord.Color.red(),
            )
            return await interaction.followup.send(embed=embed)
        
        # Get all items
        droppable_items = []
        
        for item_id, quantity in inventory.items():
            if quantity <= 0:
                continue
            
            # Check shop items
            item_data = SHOP_ITEMS.get(item_id)
            if item_data:
                droppable_items.append({
                    "id": item_id,
                    "name": item_data["name"],
                    "emoji": item_data.get("emoji", "📦"),
                    "quantity": quantity,
                    "effects": {}
                })
            # Check cooked items
            elif item_id.startswith("cooked_"):
                parts = item_id.split("_")
                quality = parts[-1]
                recipe_id = "_".join(parts[1:-1])
                recipe = RECIPES.get(recipe_id)
                if recipe:
                    quality_emojis = {"perfect": "✨", "good": "👍", "burnt": "🔥"}
                    droppable_items.append({
                        "id": item_id,
                        "name": f"{quality_emojis.get(quality, '')} {quality.title()} {recipe['name']}",
                        "emoji": recipe["emoji"],
                        "quantity": quantity,
                        "effects": {}
                    })
        
        if not droppable_items:
            embed = discord.Embed(
                title="❌ No Items",
                description="You don't have any items to drop!",
                color=discord.Color.red(),
            )
            return await interaction.followup.send(embed=embed)
        
        # Show selection menu
        view = ItemSelectorView(self.bot, interaction.user, droppable_items, "drop")
        apply_v2_embed_layout(view, body_items=view.create_components())
        
        await interaction.followup.send(view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(InventoryCog(bot))
