# cogs/cooking_cog.py

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from views.cooking_views import RecipeBrowserView, CookingMinigameView
from data.recipes import RECIPES, COOKING_INGREDIENTS
from utils.checks import safe_defer, safe_reply
from utils.format import money


class CookingCog(commands.Cog):
    """Cooking system commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="recipes", description="📖 Browse cooking recipes")
    @app_commands.describe(category="Filter by category")
    @app_commands.choices(category=[
        app_commands.Choice(name="📖 All Recipes", value="all"),
        app_commands.Choice(name="🍳 Basics", value="basics"),
        app_commands.Choice(name="🍽️ Meals", value="meals"),
        app_commands.Choice(name="🍰 Desserts", value="desserts"),
        app_commands.Choice(name="👨‍🍳 Advanced", value="advanced"),
    ])
    async def recipes(self, interaction: discord.Interaction, category: str = "all"):
        """Browse cooking recipes."""
        await safe_defer(interaction, ephemeral=True)

        view = RecipeBrowserView(self.bot, interaction.user, category)
        embed = view.create_embed()

        await safe_reply(interaction, embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="cook", description="🍳 Cook a recipe")
    @app_commands.describe(recipe="Recipe name to cook")
    async def cook(self, interaction: discord.Interaction, recipe: str):
        """Cook a recipe."""
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        # Find recipe
        recipe_id = recipe.lower().replace(" ", "_")
        recipe_data = None

        for rid, rdata in RECIPES.items():
            if rid == recipe_id or rdata["name"].lower() == recipe.lower():
                recipe_id = rid
                recipe_data = rdata
                break

        if not recipe_data:
            available = ", ".join([r["name"] for r in list(RECIPES.values())[:5]])
            return await safe_reply(
                interaction,
                content=f"❌ Recipe **{recipe}** not found!\n\n**Try:** {available}..."
            )

        # Check cooking skill
        cooking_skill = int(u.get("skill_cooking", 0))
        skill_required = recipe_data["skill_required"]

        if cooking_skill < skill_required:
            return await safe_reply(
                interaction,
                content=(
                    f"❌ You need **Cooking Level {skill_required}** to cook this!\n"
                    f"**Your Level:** {cooking_skill}\n\n"
                    f"Keep cooking simpler recipes to level up!"
                )
            )

        # Check ingredients
        inventory = u.get("inventory", {})
        missing_ingredients = []

        for ing_id, qty_needed in recipe_data["ingredients"].items():
            qty_have = inventory.get(ing_id, 0)
            if qty_have < qty_needed:
                ing_data = COOKING_INGREDIENTS.get(ing_id, {"name": ing_id, "emoji": "📦"})
                missing_ingredients.append(
                    f"{ing_data['emoji']} {ing_data['name']}: {qty_have}/{qty_needed}"
                )

        if missing_ingredients:
            embed = discord.Embed(
                title="❌ Missing Ingredients",
                description=f"You don't have all the ingredients to cook **{recipe_data['name']}**!",
                color=0xEF4444
            )
            embed.add_field(
                name="📦 Missing:",
                value="\n".join(missing_ingredients),
                inline=False
            )
            embed.add_field(
                name="🛒 Where to Get Them",
                value="Use `/shop` and search for ingredient names!",
                inline=False
            )
            return await safe_reply(interaction, embed=embed)

        # Remove ingredients from inventory
        for ing_id, qty_needed in recipe_data["ingredients"].items():
            inventory[ing_id] = inventory.get(ing_id, 0) - qty_needed
            if inventory[ing_id] <= 0:
                del inventory[ing_id]

        db.updatestat(userid, "inventory", inventory)

        # Start cooking minigame
        view = CookingMinigameView(self.bot, interaction.user, recipe_id, recipe_data)
        embed = view.create_step_embed()

        await safe_reply(interaction, embed=embed, view=view)

    @app_commands.command(name="selldish", description="💰 Sell a cooked dish")
    @app_commands.describe(dish="Cooked dish to sell")
    async def selldish(self, interaction: discord.Interaction, dish: str):
        """Sell a cooked dish."""
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        inventory = u.get("inventory", {})

        # Find cooked dish in inventory
        found_item = None
        for item_id in inventory.keys():
            if item_id.startswith("cooked_") and dish.lower() in item_id.lower():
                found_item = item_id
                break

        if not found_item:
            return await safe_reply(
                interaction,
                content=f"❌ You don't have any cooked **{dish}** to sell!\n\nUse `/cook` to make dishes."
            )

        # Parse item ID: cooked_{recipe_id}_{quality}
        parts = found_item.split("_")
        if len(parts) < 3:
            return await safe_reply(interaction, content="❌ Invalid item format!")

        quality = parts[-1]
        recipe_id = "_".join(parts[1:-1])

        recipe_data = RECIPES.get(recipe_id)
        if not recipe_data:
            return await safe_reply(interaction, content="❌ Recipe not found!")

        # Calculate sell price
        quality_multipliers = {
            "perfect": 1.5,
            "good": 1.0,
            "burnt": 0.5
        }
        multiplier = quality_multipliers.get(quality, 1.0)
        sell_price = int(recipe_data["sell_price"] * multiplier)

        # Remove from inventory
        inventory[found_item] -= 1
        if inventory[found_item] <= 0:
            del inventory[found_item]

        db.updatestat(userid, "inventory", inventory)
        db.addbalance(userid, sell_price)

        # Success message
        emoji = recipe_data["emoji"]
        quality_emojis = {"perfect": "✨", "good": "👍", "burnt": "🔥"}
        quality_emoji = quality_emojis.get(quality, "📦")

        embed = discord.Embed(
            title="✅ Dish Sold!",
            description=f"You sold your {quality_emoji} **{quality.title()} {emoji} {recipe_data['name']}** for {money(sell_price)}!",
            color=0x22C55E
        )

        new_balance = int(u.get("balance", 0)) + sell_price
        embed.add_field(
            name="💰 New Balance",
            value=money(new_balance),
            inline=True
        )

        embed.set_footer(text="Keep cooking to earn more money!")

        await safe_reply(interaction, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CookingCog(bot))
