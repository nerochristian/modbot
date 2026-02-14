# views/cooking_views.py

from __future__ import annotations

import discord
import random
from typing import Optional

from utils.format import money
from data.recipes import RECIPES, RECIPE_CATEGORIES, COOKING_INGREDIENTS
from views.v2_embed import apply_v2_embed_layout


# ============= CONSTANTS =============

COOKING_COLORS = {
    "main": 0xFF6B35,
    "basics": 0x57F287,
    "meals": 0xEB459E,
    "desserts": 0xFEE75C,
    "advanced": 0x9B59B6,
    "perfect": 0x22C55E,
    "good": 0x3B82F6,
    "burnt": 0xEF4444,
}


# ============= RECIPE BROWSER =============

class RecipeBrowserView(discord.ui.LayoutView):
    """Browse recipes."""

    def __init__(self, bot, user: discord.User, category: str = "all"):
        super().__init__(timeout=300)
        self.bot = bot
        self.user = user
        self.category = category
        self.page = 0
        self.items_per_page = 6

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This isn't your recipe book!",
                ephemeral=True
            )
            return False
        return True

    def get_filtered_recipes(self):
        """Get recipes by category."""
        if self.category == "all":
            return list(RECIPES.items())
        return [(k, v) for k, v in RECIPES.items() if v["category"] == self.category]

    def create_embed(self) -> discord.Embed:
        """Create recipe list embed."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        
        cooking_skill = int(u.get("skill_cooking", 0))

        filtered = self.get_filtered_recipes()
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        page_recipes = filtered[start:end]

        color = COOKING_COLORS.get(self.category, COOKING_COLORS["main"])
        cat_name = self.category.title() if self.category != "all" else "All Recipes"

        embed = discord.Embed(
            title=f"📖 Recipe Book - {cat_name}",
            description=f"**Your Cooking Skill:** Level {cooking_skill}",
            color=color
        )

        if not page_recipes:
            embed.add_field(
                name="📦 No Recipes",
                value="No recipes in this category.",
                inline=False
            )
        else:
            for recipe_id, recipe in page_recipes:
                emoji = recipe["emoji"]
                name = recipe["name"]
                skill_req = recipe["skill_required"]
                
                can_cook = cooking_skill >= skill_req
                status = "✅" if can_cook else f"🔒 Lv.{skill_req}"

                ingredients = []
                for ing_id, qty in list(recipe["ingredients"].items())[:2]:
                    ing_data = COOKING_INGREDIENTS.get(ing_id, {"name": ing_id, "emoji": "📦"})
                    ingredients.append(f"{qty}x {ing_data['emoji']}")

                embed.add_field(
                    name=f"{status} {emoji} {name}",
                    value=f"Ingredients: {', '.join(ingredients)}...\nSell: {money(recipe['sell_price'])}",
                    inline=True
                )

        total_pages = (len(filtered) + self.items_per_page - 1) // self.items_per_page
        embed.set_footer(text=f"Page {self.page + 1}/{total_pages} • Use /cook <recipe>")

        return embed

    @discord.ui.button(label="All", emoji="📖", row=0)
    async def all_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "all"
        self.page = 0
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Basics", emoji="🍳", row=0)
    async def basics_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "basics"
        self.page = 0
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Meals", emoji="🍽️", row=0)
    async def meals_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "meals"
        self.page = 0
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Desserts", emoji="🍰", row=0)
    async def desserts_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "desserts"
        self.page = 0
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Advanced", emoji="👨‍🍳", row=1)
    async def advanced_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.category = "advanced"
        self.page = 0
        apply_v2_embed_layout(self, embed=self.create_embed())
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Close", emoji="❌", style=discord.ButtonStyle.danger, row=1)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="📖 Recipe book closed.", embed=None, view=None)
        self.stop()


# ============= COOKING MINIGAME =============

class CookingMinigameView(discord.ui.LayoutView):
    """Cooking minigame."""

    def __init__(self, bot, user: discord.User, recipe_id: str, recipe_data: dict):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.recipe_id = recipe_id
        self.recipe_data = recipe_data
        self.step = 0
        self.total_steps = 3
        self.success = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    def create_embed(self) -> discord.Embed:
        """Create cooking step embed."""
        emoji = self.recipe_data["emoji"]
        name = self.recipe_data["name"]

        steps = [
            {"name": "Prep", "emoji": "🔪"},
            {"name": "Cook", "emoji": "🔥"},
            {"name": "Plate", "emoji": "🍽️"},
        ]

        current = steps[self.step]

        embed = discord.Embed(
            title=f"🍳 Cooking {emoji} {name}",
            description=f"**Step {self.step + 1}/{self.total_steps}: {current['name']}**\n\nClick Perfect at the right time!",
            color=COOKING_COLORS["main"]
        )

        embed.add_field(
            name="📊 Progress",
            value=f"{'✅' * self.success}{'⬜' * (self.total_steps - self.success)}",
            inline=False
        )

        return embed

    @discord.ui.button(label="Perfect!", emoji="✨", style=discord.ButtonStyle.success)
    async def perfect_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Try to get perfect timing."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)
        cooking_skill = int(u.get("skill_cooking", 0))

        # Skill increases success chance
        threshold = 0.3 + (cooking_skill * 0.01)
        roll = random.random()

        if roll < threshold:
            self.success += 1

        self.step += 1

        if self.step >= self.total_steps:
            # Finished cooking
            await self.finish_cooking(interaction)
        else:
            embed = self.create_embed()
            apply_v2_embed_layout(self, embed=embed)
            await interaction.response.edit_message(view=self)

    async def finish_cooking(self, interaction: discord.Interaction):
        """Finish cooking and give result."""
        db = self.bot.db
        userid = str(self.user.id)
        u = db.getuser(userid)

        # Determine quality
        if self.success == 3:
            quality = "perfect"
        elif self.success >= 2:
            quality = "good"
        else:
            quality = "burnt"

        quality_data = {
            "perfect": {"emoji": "✨", "mult": 1.5, "color": COOKING_COLORS["perfect"]},
            "good": {"emoji": "👍", "mult": 1.0, "color": COOKING_COLORS["good"]},
            "burnt": {"emoji": "🔥", "mult": 0.5, "color": COOKING_COLORS["burnt"]},
        }

        qual = quality_data[quality]
        xp = int(self.recipe_data["xp_reward"] * qual["mult"])

        # Add to inventory
        inventory = u.get("inventory", {})
        cooked_id = f"cooked_{self.recipe_id}_{quality}"
        inventory[cooked_id] = inventory.get(cooked_id, 0) + 1
        db.updatestat(userid, "inventory", inventory)

        # Add XP
        db.add_skill_xp(userid, "cooking", xp)
        db.addxp(userid, xp // 2)

        emoji = self.recipe_data["emoji"]
        name = self.recipe_data["name"]

        embed = discord.Embed(
            title=f"{qual['emoji']} Cooking Complete!",
            description=f"You cooked a **{quality.title()} {emoji} {name}**!",
            color=qual["color"]
        )

        embed.add_field(
            name="⭐ XP Earned",
            value=f"+{xp} Cooking XP",
            inline=True
        )

        sell_price = int(self.recipe_data["sell_price"] * qual["mult"])
        embed.add_field(
            name="💰 Sell Price",
            value=money(sell_price),
            inline=True
        )

        embed.set_footer(text=f"Perfect steps: {self.success}/3 • Use /eat to consume!")

        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
