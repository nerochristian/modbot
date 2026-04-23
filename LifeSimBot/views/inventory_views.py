# views/inventory_views.py

from __future__ import annotations

import discord
import json
from typing import Optional, List, Dict, Tuple

from ..utils.format import money, progress_bar
from ..views.shop_views import SHOP_ITEMS, safe_get_inventory
from ..data.recipes import RECIPES
from ..views.v2_embed import apply_v2_embed_layout


# ============= CONSTANTS =============

INVENTORY_COLORS = {
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
    "all": "🎒",
    "food": "🍔",
    "consumables": "⚡",
    "tools": "🔧",
    "vehicles": "🚗",
    "collectibles": "💎",
    "ingredients": "🥕",
    "cooked": "🍳",
}


# ============= INVENTORY BROWSER VIEW =============

class InventoryView(discord.ui.LayoutView):
    """Main inventory browser with filtering and pagination using V2 components."""

    def __init__(self, bot, user: discord.User, category: str = "all", sort: str = "name"):
        super().__init__(timeout=300)
        self.bot = bot
        self.user = user
        self.category = category
        self.sort = sort
        self.page = 0
        self.items_per_page = 9

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This isn't your inventory! Use `/inventory` to view your own.",
                ephemeral=True
            )
            return False
        return True

    def get_filtered_items(self) -> List[Tuple[str, int, dict]]:
        """Get and filter inventory items."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        
        inventory = safe_get_inventory(u)

        filtered = []

        for item_id, quantity in inventory.items():
            if quantity <= 0:
                continue

            # Check if it's a cooked dish
            if item_id.startswith("cooked_"):
                if self.category not in ["all", "cooked", "food"]:
                    continue

                parts = item_id.split("_")
                quality = parts[-1]
                recipe_id = "_".join(parts[1:-1])
                recipe_data = RECIPES.get(recipe_id)

                if recipe_data:
                    quality_mult = {"perfect": 1.5, "good": 1.0, "burnt": 0.5}.get(quality, 1.0)
                    price = int(recipe_data["sell_price"] * quality_mult)
                    
                    display_name = f"{quality.title()} {recipe_data['name']}"
                    emoji = recipe_data["emoji"]
                    
                    filtered.append((
                        item_id,
                        quantity,
                        {
                            "name": display_name,
                            "emoji": emoji,
                            "price": price,
                            "category": "cooked",
                            "description": f"{quality.title()} quality cooked dish"
                        }
                    ))
                continue

            # Regular shop items
            item_data = SHOP_ITEMS.get(item_id)
            if not item_data:
                continue

            if self.category != "all" and item_data["category"] != self.category:
                continue

            filtered.append((item_id, quantity, item_data))

        # Sort items
        if self.sort == "name":
            filtered.sort(key=lambda x: x[2]["name"].lower())
        elif self.sort == "value":
            filtered.sort(key=lambda x: x[2]["price"] * x[1], reverse=True)
        elif self.sort == "quantity":
            filtered.sort(key=lambda x: x[1], reverse=True)

        return filtered

    def create_components(self) -> List[discord.ui.Component]:
        """Create V2 component layout for inventory."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        balance = int(u.get("balance", 0))
        bank = int(u.get("bank", 0))

        # Get filtered items
        filtered_items = self.get_filtered_items()

        # Pagination
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        page_items = filtered_items[start:end]

        # Calculate total value
        total_value = sum(item[2]["price"] * item[1] for item in filtered_items)

        # Category info
        cat_emoji = CATEGORY_EMOJIS.get(self.category, "🎒")
        cat_name = self.category.title() if self.category != "all" else "All Items"

        components = []

        # Header
        header_text = f"# {cat_emoji} {self.user.display_name}'s Inventory\n\n"
        header_text += f"**Category:** {cat_name}\n"
        header_text += f"**Total Items:** {len(filtered_items)} unique items\n"
        header_text += f"**Inventory Value:** {money(total_value)}\n"
        header_text += f"**Wallet:** {money(balance)} • **Bank:** {money(bank)}"

        components.append(discord.ui.TextDisplay(content=header_text))
        try:
            from ..views.v2_embed import _safe_separator

            components.append(_safe_separator())
        except Exception:
            components.append(discord.ui.Separator())

        if not page_items:
            components.append(
                discord.ui.TextDisplay(
                    content="## 📦 Empty Inventory\n\n"
                            "No items found in this category!\n\n"
                            "**Get items by:**\n"
                            "• `/shop` - Buy items\n"
                            "• `/cook` - Cook dishes\n"
                            "• `/work` - Earn money to buy items"
                )
            )
        else:
            # Display items in a formatted list
            items_text = ""
            for item_id, quantity, item_data in page_items:
                emoji = item_data.get("emoji", "📦")
                name = item_data["name"]
                price = item_data["price"]
                total_val = price * quantity

                items_text += f"{emoji} **{name}**\n"
                items_text += f"└ Qty: {quantity:,} • Value: {money(total_val)}"

                # Add effects if consumable
                if item_data.get("consumable") or item_data.get("category") == "cooked":
                    effects = item_data.get("effects", {})
                    if effects:
                        effect_list = []
                        for effect, val in list(effects.items())[:2]:
                            if effect == "hunger":
                                effect_list.append(f"🍔+{val}")
                            elif effect == "energy":
                                effect_list.append(f"⚡+{val}")
                            elif effect == "health":
                                effect_list.append(f"❤️+{val}")
                        if effect_list:
                            items_text += f" • {' '.join(effect_list)}"
                
                items_text += "\n\n"

            components.append(discord.ui.TextDisplay(content=items_text.strip()))

        # Footer with pagination
        total_pages = (len(filtered_items) + self.items_per_page - 1) // self.items_per_page
        if total_pages > 0:
            footer_text = f"*Page {self.page + 1}/{total_pages} • Use buttons to navigate*"
        else:
            footer_text = "*Use /buy to purchase items • /cook to make dishes*"

        try:
            from ..views.v2_embed import _safe_separator

            components.append(_safe_separator())
        except Exception:
            components.append(discord.ui.Separator())
        components.append(discord.ui.TextDisplay(content=footer_text))

        return components

    # Category buttons
    @discord.ui.button(label="All", style=discord.ButtonStyle.secondary, emoji="🎒", row=0)
    async def all_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "all"
        self.page = 0
        apply_v2_embed_layout(self, body_items=self.create_components(), accent_color=INVENTORY_COLORS.get(self.category, INVENTORY_COLORS["main"]))
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Food", style=discord.ButtonStyle.secondary, emoji="🍔", row=0)
    async def food_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "food"
        self.page = 0
        apply_v2_embed_layout(self, body_items=self.create_components(), accent_color=INVENTORY_COLORS.get(self.category, INVENTORY_COLORS["main"]))
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Tools", style=discord.ButtonStyle.secondary, emoji="🔧", row=0)
    async def tools_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "tools"
        self.page = 0
        apply_v2_embed_layout(self, body_items=self.create_components(), accent_color=INVENTORY_COLORS.get(self.category, INVENTORY_COLORS["main"]))
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Ingredients", style=discord.ButtonStyle.secondary, emoji="🥕", row=0)
    async def ingredients_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "ingredients"
        self.page = 0
        apply_v2_embed_layout(self, body_items=self.create_components(), accent_color=INVENTORY_COLORS.get(self.category, INVENTORY_COLORS["main"]))
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Cooked", style=discord.ButtonStyle.secondary, emoji="🍳", row=1)
    async def cooked_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "cooked"
        self.page = 0
        apply_v2_embed_layout(self, body_items=self.create_components(), accent_color=INVENTORY_COLORS.get(self.category, INVENTORY_COLORS["main"]))
        await interaction.response.edit_message(view=self)

    # Navigation buttons
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, emoji="⬅️", row=1)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        apply_v2_embed_layout(self, body_items=self.create_components(), accent_color=INVENTORY_COLORS.get(self.category, INVENTORY_COLORS["main"]))
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, emoji="➡️", row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        filtered_items = self.get_filtered_items()
        total_pages = (len(filtered_items) + self.items_per_page - 1) // self.items_per_page
        
        if self.page < total_pages - 1:
            self.page += 1
        
        apply_v2_embed_layout(self, body_items=self.create_components(), accent_color=INVENTORY_COLORS.get(self.category, INVENTORY_COLORS["main"]))
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        apply_v2_embed_layout(self, body_items=self.create_components(), accent_color=INVENTORY_COLORS.get(self.category, INVENTORY_COLORS["main"]))
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌", row=2)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🎒 Inventory Closed",
                description="Inventory closed. Use `/inventory` to reopen!",
                color=INVENTORY_COLORS["main"],
            ),
            view=None,
        )
        self.stop()


# ============= ITEM USE VIEW =============

class ItemUseView(discord.ui.LayoutView):
    """Interactive item usage confirmation with V2 components."""

    def __init__(self, bot, user: discord.User, item_id: str, quantity: int = 1):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.item_id = item_id
        self.quantity = quantity
        self.item_data = SHOP_ITEMS.get(item_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    def create_components(self) -> List[discord.ui.Item]:
        """Create V2 component layout for item usage."""
        if not self.item_data:
            return [
                discord.ui.TextDisplay(
                    content="# ❌ Item Not Found\n\nThis item doesn't exist."
                )
            ]

        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        
        inventory = safe_get_inventory(u)
        owned = inventory.get(self.item_id, 0)

        if owned < self.quantity:
            return [
                discord.ui.TextDisplay(
                    content=f"# ❌ Not Enough Items\n\n"
                            f"You only have **{owned}x {self.item_data['name']}**!"
                )
            ]

        emoji = self.item_data.get("emoji", "📦")
        name = self.item_data["name"]
        effects = self.item_data.get("effects", {})

        components = []

        # Header
        header = f"# {emoji} Use {name}?\n\n"
        header += f"Are you sure you want to use **{self.quantity}x {name}**?"
        components.append(discord.ui.TextDisplay(content=header))
        
        try:
            from ..views.v2_embed import _safe_separator

            components.append(_safe_separator())
        except Exception:
            components.append(discord.ui.Separator())

        # Current stats
        health = int(u.get("health", 100))
        energy = int(u.get("energy", 100))
        hunger = int(u.get("hunger", 100))

        stats_text = "## 📊 Current Stats\n\n"
        stats_text += f"❤️ Health: {health}/100\n"
        stats_text += f"⚡ Energy: {energy}/100\n"
        stats_text += f"🍔 Hunger: {hunger}/100"
        
        components.append(discord.ui.TextDisplay(content=stats_text))

        # Effects preview
        if effects:
            effects_text = "## ✨ Effects Preview\n\n"
            for effect, value in effects.items():
                total = value * self.quantity
                if effect == "energy":
                    new_val = min(100, energy + total)
                    effects_text += f"⚡ Energy: {energy} → {new_val} (+{new_val - energy})\n"
                elif effect == "health":
                    new_val = min(100, health + total)
                    effects_text += f"❤️ Health: {health} → {new_val} (+{new_val - health})\n"
                elif effect == "hunger":
                    new_val = min(100, hunger + total)
                    effects_text += f"🍔 Hunger: {hunger} → {new_val} (+{new_val - hunger})\n"

            components.append(discord.ui.TextDisplay(content=effects_text.strip()))

        try:
            from ..views.v2_embed import _safe_separator

            components.append(_safe_separator())
        except Exception:
            components.append(discord.ui.Separator())

        # Inventory info
        inventory_text = f"**🎒 You Have:** {owned}x {name}\n"
        inventory_text += f"**📦 After Use:** {owned - self.quantity}x remaining"
        components.append(discord.ui.TextDisplay(content=inventory_text))

        footer_text = "*Click Use to consume or Cancel to abort*"
        components.append(discord.ui.TextDisplay(content=footer_text))

        return components

    @discord.ui.button(label="Use", style=discord.ButtonStyle.success, emoji="✅")
    async def use_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Use the item."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        
        inventory = safe_get_inventory(u)
        owned = inventory.get(self.item_id, 0)

        if owned < self.quantity:
            return await interaction.response.send_message(
                f"❌ You don't have enough! You only have {owned}x.",
                ephemeral=True
            )

        # Apply effects
        effects = self.item_data.get("effects", {})
        effects_applied = []

        for effect, value in effects.items():
            total = value * self.quantity

            if effect == "energy":
                current = int(u.get("energy", 100))
                new_val = min(100, current + total)
                db.updatestat(userid, "energy", new_val)
                if new_val > current:
                    effects_applied.append(f"⚡ Energy: {current} → {new_val} (+{new_val - current})")

            elif effect == "health":
                current = int(u.get("health", 100))
                new_val = min(100, current + total)
                db.updatestat(userid, "health", new_val)
                if new_val > current:
                    effects_applied.append(f"❤️ Health: {current} → {new_val} (+{new_val - current})")

            elif effect == "hunger":
                current = int(u.get("hunger", 100))
                new_val = min(100, current + total)
                db.updatestat(userid, "hunger", new_val)
                if new_val > current:
                    effects_applied.append(f"🍔 Hunger: {current} → {new_val} (+{new_val - current})")

        # Remove items from inventory
        inventory[self.item_id] = owned - self.quantity
        if inventory[self.item_id] <= 0:
            del inventory[self.item_id]
        db.updatestat(userid, "inventory", json.dumps(inventory))

        # Success message
        emoji = self.item_data.get("emoji", "📦")
        name = self.item_data["name"]

        success_text = f"# ✅ Used {emoji} {name}!\n\n"
        success_text += f"You consumed **{self.quantity}x {name}**!\n\n"

        if effects_applied:
            success_text += "## ✨ Effects Applied\n\n"
            success_text += "\n".join(effects_applied)
        else:
            success_text += "## ℹ️ No Effects\n\nYour stats are already full!"

        remaining = inventory.get(self.item_id, 0)
        success_text += f"\n\n**🎒 Remaining:** {remaining}x {name}"

        embed = discord.Embed(
            title=f"✅ Used {emoji} {name}!",
            description=success_text.replace(f"# ✅ Used {emoji} {name}!\n\n", ""),
            color=INVENTORY_COLORS["success"],
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel usage."""
        embed = discord.Embed(
            title="❌ Cancelled",
            description="Item not used.",
            color=INVENTORY_COLORS["error"],
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


# ============= ITEM DETAIL VIEW =============

class ItemDetailView(discord.ui.LayoutView):
    """Detailed item information view with V2 components."""

    def __init__(self, bot, user: discord.User, item_id: str):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.item_id = item_id
        self.item_data = SHOP_ITEMS.get(item_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    def create_components(self) -> List[discord.ui.Item]:
        """Create V2 component layout for item details."""
        if not self.item_data:
            return [
                discord.ui.TextDisplay(content="# ❌ Item Not Found")
            ]

        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        
        inventory = safe_get_inventory(u)

        emoji = self.item_data.get("emoji", "📦")
        name = self.item_data["name"]
        description = self.item_data["description"]
        price = self.item_data["price"]
        category = self.item_data["category"]
        consumable = self.item_data.get("consumable", False)
        effects = self.item_data.get("effects", {})
        owned = inventory.get(self.item_id, 0)

        components = []

        # Header
        header = f"# {emoji} {name}\n\n{description}"
        components.append(discord.ui.TextDisplay(content=header))
        
        try:
            from ..views.v2_embed import _safe_separator

            components.append(_safe_separator())
        except Exception:
            components.append(discord.ui.Separator())

        # Item info
        info_text = f"**💰 Price**\n"
        info_text += f"Buy: {money(price)} • Sell: {money(price // 2)}\n\n"
        info_text += f"**📦 Category:** {category.title()}\n"
        info_text += f"**📊 Type:** {'Consumable' if consumable else 'Permanent'}"
        
        components.append(discord.ui.TextDisplay(content=info_text))

        # Effects
        if effects:
            effects_text = "## ✨ Effects\n\n"
            for effect, value in effects.items():
                if effect in ["hunger", "health", "energy"]:
                    effects_text += f"• +{value} {effect.title()}\n"
                elif "_bonus" in effect:
                    effects_text += f"• +{value * 100:.0f}% {effect.replace('_bonus', '').title()}\n"
            
            components.append(discord.ui.TextDisplay(content=effects_text.strip()))

        try:
            from ..views.v2_embed import _safe_separator

            components.append(_safe_separator())
        except Exception:
            components.append(discord.ui.Separator())

        # Ownership
        ownership_text = f"**🎒 You Own:** {owned}x\n"
        ownership_text += f"**💵 Total Value:** {money(price * owned)}"
        components.append(discord.ui.TextDisplay(content=ownership_text))

        footer = f"*Item ID: {self.item_id}*"
        components.append(discord.ui.TextDisplay(content=footer))

        return components

    @discord.ui.button(label="Close", style=discord.ButtonStyle.secondary, emoji="❌")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=discord.Embed(title="ℹ️ Closed", color=INVENTORY_COLORS["main"]),
            view=None,
        )
        self.stop()


# Placeholder classes for future implementation
class ItemManageView(discord.ui.LayoutView):
    pass


class ItemGiftView(discord.ui.LayoutView):
    pass
