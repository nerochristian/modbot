# cogs/shop_cog.py

from __future__ import annotations

import difflib
import re
from typing import Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import safe_defer, safe_reply
from utils.format import money
from views.shop_views import ItemDetailView, SHOP_ITEMS, ShopBrowserView
from views.v2_embed import apply_v2_embed_layout


class ShopCog(commands.Cog):
    """Shop commands: shop, buy, sell."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _normalize_item_query(value: str) -> str:
        value = (value or "").strip().lower()
        value = re.sub(r"^[^a-z0-9]+", "", value)
        value = re.sub(r"[^a-z0-9]+$", "", value)
        value = value.replace("_", " ").replace("-", " ")
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @classmethod
    def _resolve_shop_item(cls, query: str) -> Tuple[Optional[str], Optional[dict], list[str]]:
        if not query:
            return None, None, []

        raw = query.strip()
        if raw in SHOP_ITEMS:
            return raw, SHOP_ITEMS[raw], []

        normalized_query = cls._normalize_item_query(raw)
        if not normalized_query:
            return None, None, []

        exact: list[tuple[str, dict]] = []
        partial: list[tuple[str, dict]] = []

        all_names: list[str] = []
        all_normalized_names: list[str] = []
        name_by_normalized: dict[str, str] = {}

        for item_id, item_data in SHOP_ITEMS.items():
            name = str(item_data.get("name", item_id))
            name_norm = cls._normalize_item_query(name)
            id_norm = cls._normalize_item_query(item_id)

            all_names.append(name)
            all_normalized_names.append(name_norm)
            name_by_normalized[name_norm] = name

            if raw.lower() == name.lower() or normalized_query in (name_norm, id_norm):
                exact.append((item_id, item_data))
            elif normalized_query in name_norm or normalized_query in id_norm:
                partial.append((item_id, item_data))

        if len(exact) == 1:
            item_id, item_data = exact[0]
            return item_id, item_data, []

        if len(partial) == 1:
            item_id, item_data = partial[0]
            return item_id, item_data, []

        suggestions: list[str] = []
        if len(exact) > 1:
            suggestions = [item_data.get("name", item_id) for item_id, item_data in exact[:5]]
        elif len(partial) > 1:
            suggestions = [item_data.get("name", item_id) for item_id, item_data in partial[:5]]
        else:
            close_norm = difflib.get_close_matches(normalized_query, all_normalized_names, n=5, cutoff=0.55)
            suggestions = [name_by_normalized.get(n, "") for n in close_norm if name_by_normalized.get(n)]
            if not suggestions:
                suggestions = difflib.get_close_matches(raw, all_names, n=5, cutoff=0.55)

        return None, None, suggestions

    @app_commands.command(name="shop", description="🛍️ Browse the shop")
    @app_commands.describe(category="Filter by category")
    @app_commands.choices(
        category=[
            app_commands.Choice(name="🛍️ All Items", value="all"),
            app_commands.Choice(name="🍔 Food", value="food"),
            app_commands.Choice(name="🛠️ Tools", value="tools"),
            app_commands.Choice(name="🧪 Consumables", value="consumables"),
            app_commands.Choice(name="🚗 Vehicles", value="vehicles"),
            app_commands.Choice(name="🏆 Collectibles", value="collectibles"),
        ]
    )
    async def shop(self, interaction: discord.Interaction, category: str = "all"):
        """Open the shop browser."""
        await safe_defer(interaction, ephemeral=True)

        view = ShopBrowserView(self.bot, interaction.user, category)
        embed = view.create_embed()

        apply_v2_embed_layout(view, embed=embed)
        await safe_reply(interaction, view=view, ephemeral=True)

    @app_commands.command(name="buy", description="🛒 Buy an item from the shop")
    @app_commands.describe(item="Item name to buy", quantity="How many to buy (default: 1)")
    async def buy(self, interaction: discord.Interaction, item: str, quantity: int = 1):
        """Buy an item."""
        await safe_defer(interaction)

        item_id, item_data, suggestions = self._resolve_shop_item(item)
        if not item_data or not item_id:
            suggestion_text = ""
            if suggestions:
                suggestion_text = "\n\nDid you mean:\n- " + "\n- ".join(suggestions)
            return await safe_reply(
                interaction,
                content=f"❌ Item **{item}** not found. Use `/shop` (or autocomplete) to pick an item.{suggestion_text}",
            )

        if quantity < 1:
            return await safe_reply(interaction, content="❌ Quantity must be at least 1.")
        if quantity > 100:
            return await safe_reply(interaction, content="❌ Maximum purchase quantity is 100.")

        view = ItemDetailView(self.bot, interaction.user, item_id, quantity)
        embed = view.create_embed()

        apply_v2_embed_layout(view, embed=embed)
        await safe_reply(interaction, view=view)

    @buy.autocomplete("item")
    async def buy_item_autocomplete(self, interaction: discord.Interaction, current: str):
        current_norm = self._normalize_item_query(current)
        results: list[app_commands.Choice[str]] = []

        for item_id, item_data in SHOP_ITEMS.items():
            name = str(item_data.get("name", item_id))
            if not current_norm:
                results.append(app_commands.Choice(name=name, value=item_id))
                continue

            name_norm = self._normalize_item_query(name)
            id_norm = self._normalize_item_query(item_id)
            if current_norm in name_norm or current_norm in id_norm:
                results.append(app_commands.Choice(name=name, value=item_id))

        if len(results) < 25 and current_norm:
            all_names = [str(idata.get("name", iid)) for iid, idata in SHOP_ITEMS.items()]
            for close in difflib.get_close_matches(current, all_names, n=25, cutoff=0.55):
                for iid, idata in SHOP_ITEMS.items():
                    if str(idata.get("name", iid)) == close:
                        choice = app_commands.Choice(name=close, value=iid)
                        if choice not in results:
                            results.append(choice)
                        break

        return results[:25]

    @app_commands.command(name="sell", description="💸 Sell items from your inventory")
    @app_commands.describe(item="Item name to sell", quantity="How many to sell (default: 1)")
    async def sell(self, interaction: discord.Interaction, item: str, quantity: int = 1):
        """Sell an item."""
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        item_id, item_data, suggestions = self._resolve_shop_item(item)
        if not item_data or not item_id:
            suggestion_text = ""
            if suggestions:
                suggestion_text = "\n\nDid you mean:\n- " + "\n- ".join(suggestions)
            return await safe_reply(interaction, content=f"❌ Item **{item}** not found.{suggestion_text}")

        inventory = u.get("inventory", {})
        owned = int(inventory.get(item_id, 0) or 0)

        if quantity < 1:
            return await safe_reply(interaction, content="❌ Quantity must be at least 1.")

        if owned < quantity:
            return await safe_reply(
                interaction,
                content=f"❌ You only have **{owned}x {item_data['name']}**.",
            )

        sell_price = int(item_data["price"] * 0.5)
        total_earn = sell_price * quantity

        inventory[item_id] = owned - quantity
        if inventory[item_id] <= 0:
            del inventory[item_id]

        db.updatestat(userid, "inventory", inventory)
        db.addbalance(userid, total_earn)

        emoji = item_data.get("emoji", "")
        new_balance = int(u.get("balance", 0)) + total_earn

        embed = discord.Embed(
            title="✅ Items Sold!",
            description=f"You sold **{quantity}x {emoji} {item_data['name']}** for {money(total_earn)}!",
            color=0x22C55E,
        )
        embed.add_field(name="💰 Earnings", value=f"{money(total_earn)}\n({money(sell_price)} each)", inline=True)
        embed.add_field(name="🏦 New Balance", value=money(new_balance), inline=True)
        embed.add_field(name="📦 Remaining", value=f"{int(inventory.get(item_id, 0) or 0)} left", inline=True)
        embed.set_footer(text="Sell price is 50% of buy price")

        await safe_reply(interaction, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ShopCog(bot))

