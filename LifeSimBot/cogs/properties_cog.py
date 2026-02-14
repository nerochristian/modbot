# cogs/properties_cog.py
from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from data.properties_advanced import (
    PROPERTY_TYPES,
    calculate_property_rent,
    calculate_property_upgrade_cost,
)
from utils.format import money, progress_bar
from utils.checks import safe_defer, safe_reply


class PropertiesCog(commands.Cog):
    """Real estate, housing, and rental income."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----- View properties -----

    @app_commands.command(name="properties", description="🏠 View your properties")
    async def properties(self, interaction: discord.Interaction):
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)

        props = db.get_user_properties(userid)  # you implement this like businesses

        if not props:
            embed = discord.Embed(
                title="🏠 Your Properties",
                description="You don't own any properties yet.\n\nUse `/buyproperty` to purchase one.",
                color=discord.Color.blue(),
            )
            return await safe_reply(interaction, embed=embed)

        embed = discord.Embed(
            title=f"🏠 {interaction.user.display_name}'s Properties",
            color=discord.Color.blue(),
        )

        total_rent = 0
        total_comfort = 0
        total_energy = 0

        now = datetime.now(timezone.utc)

        for prop in props:
            ptype = PROPERTY_TYPES.get(prop["property_type"], {})
            emoji = ptype.get("emoji", "🏠")

            level = int(prop.get("level", 1))
            rent = calculate_property_rent(prop)
            total_rent += rent
            total_comfort += int(ptype.get("comfort", 0))
            total_energy += int(ptype.get("energy_bonus", 0))

            last_collected = prop.get("last_collected")
            if last_collected:
                try:
                    last_time = datetime.fromisoformat(last_collected)
                    hours_passed = (now - last_time).total_seconds() / 3600
                    hours_passed = min(24, max(0, hours_passed))
                    uncollected = int(rent * hours_passed)
                except Exception:
                    uncollected = 0
            else:
                uncollected = 0

            upgrade_cost = calculate_property_upgrade_cost(prop)
            upgrade_text = f"Upgrade: {money(upgrade_cost)}" if upgrade_cost > 0 else "Max level reached"

            embed.add_field(
                name=f"{emoji} {prop['name']} (Lv{level})",
                value=(
                    f"**Type:** {ptype.get('name', prop['property_type'])}\n"
                    f"**Rent:** {money(rent)}/hour\n"
                    f"**Uncollected:** {money(uncollected)}\n"
                    f"**Comfort:** +{ptype.get('comfort', 0)}\n"
                    f"**Energy Bonus:** +{ptype.get('energy_bonus', 0)}\n"
                    f"**{upgrade_text}**"
                ),
                inline=False,
            )

        embed.set_footer(
            text=f"Total rent: {money(total_rent)}/hour | Total comfort: +{total_comfort} | Energy bonus: +{total_energy}"
        )

        await safe_reply(interaction, embed=embed)

    # ----- Buy property -----

    @app_commands.command(name="buyproperty", description="🛒 Buy a new property")
    @app_commands.choices(property=[
        app_commands.Choice(name="🏚️ Studio Apartment", value="studio_apartment"),
        app_commands.Choice(name="🏠 Small House", value="small_house"),
        app_commands.Choice(name="🏡 Suburban Home", value="suburban_home"),
        app_commands.Choice(name="🏙️ City Penthouse", value="city_penthouse"),
        app_commands.Choice(name="🏖️ Beach Villa", value="beach_villa"),
    ])
    async def buyproperty(self, interaction: discord.Interaction, property: str):
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        ptype = PROPERTY_TYPES.get(property)
        if not ptype:
            return await safe_reply(interaction, content="❌ Invalid property type!")

        # limit: 1 primary home + N rentals?
        owned = db.get_user_properties(userid)
        if len(owned) >= 5:
            return await safe_reply(
                interaction,
                content="❌ You already own 5 properties! (Max limit)",
            )

        cost = ptype["base_cost"]
        balance = int(u.get("balance", 0))

        if balance < cost:
            return await safe_reply(
                interaction,
                content=f"❌ You need {money(cost)}, but you only have {money(balance)}",
            )

        db.removebalance(userid, cost)

        # create_property(owner_id, property_type, name, base_rent)
        prop_id = db.create_property(
            userid,
            property,
            ptype["name"],
            ptype["base_rent"],
        )

        embed = discord.Embed(
            title="🏠 New Property Purchased!",
            description=f"You bought **{ptype['name']}** for {money(cost)}",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Details",
            value=(
                f"**ID:** `{prop_id}`\n"
                f"**Rent:** {money(ptype['base_rent'])}/hour\n"
                f"**Comfort:** +{ptype['comfort']}\n"
                f"**Energy Bonus:** +{ptype['energy_bonus']}"
            ),
            inline=False,
        )
        embed.set_footer(text="Your property will now generate hourly rental income.")

        await safe_reply(interaction, embed=embed)

    # ----- Upgrade property -----

    @app_commands.command(name="upgradeproperty", description="⬆️ Upgrade one of your properties")
    @app_commands.describe(property_id="ID of the property to upgrade")
    async def upgradeproperty(self, interaction: discord.Interaction, property_id: str):
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)

        props = db.get_user_properties(userid)
        prop = next((p for p in props if p["property_id"] == property_id), None)

        if not prop:
            return await safe_reply(interaction, content="❌ You don't own a property with that ID!")

        ptype = PROPERTY_TYPES.get(prop["property_type"])
        if not ptype:
            return await safe_reply(
                interaction,
                content="❌ This property type is no longer valid.",
            )

        level = int(prop.get("level", 1))
        max_level = ptype["max_level"]

        if level >= max_level:
            return await safe_reply(
                interaction,
                content="❌ This property is already at max level!",
            )

        cost = calculate_property_upgrade_cost(prop)

        u = db.getuser(userid)
        balance = int(u.get("balance", 0))

        if balance < cost:
            return await safe_reply(
                interaction,
                content=f"❌ You need {money(cost)} to upgrade, but you only have {money(balance)}",
            )

        db.removebalance(userid, cost)
        db.updateproperty(property_id, "level", level + 1)

        new_rent = calculate_property_rent({**prop, "level": level + 1})
        db.updateproperty(property_id, "rent_per_hour", new_rent)

        embed = discord.Embed(
            title="⬆️ Property Upgraded!",
            description=f"**{ptype['name']}** is now level **{level + 1}**!",
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="New Stats",
            value=(
                f"**Rent:** {money(new_rent)}/hour\n"
                f"**Upgrade Cost Paid:** {money(cost)}"
            ),
            inline=False,
        )

        await safe_reply(interaction, embed=embed)

    # ----- Collect rent -----

    @app_commands.command(name="collectrent", description="💰 Collect unclaimed rental income")
    async def collectrent(self, interaction: discord.Interaction):
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)

        props = db.get_user_properties(userid)
        if not props:
            return await safe_reply(
                interaction,
                content="❌ You don't own any properties!",
            )

        total_collected = 0
        now = datetime.now(timezone.utc)

        for prop in props:
            rent = calculate_property_rent(prop)

            last_collected = prop.get("last_collected")
            if last_collected:
                try:
                    last_time = datetime.fromisoformat(last_collected)
                except Exception:
                    last_time = now
            else:
                last_time = now

            hours_passed = (now - last_time).total_seconds() / 3600
            hours_passed = min(24, max(0, hours_passed))  # cap at 24h offline

            income = int(rent * hours_passed)

            if income > 0:
                db.addbalance(userid, income)
                db.updateproperty(prop["property_id"], "last_collected", now.isoformat())
                total_collected += income

        if total_collected == 0:
            return await safe_reply(
                interaction,
                content="⏰ No rent to collect yet. Try again later!",
            )

        embed = discord.Embed(
            title="💰 Rental Income Collected",
            description=f"You collected **{money(total_collected)}** from your properties.",
            color=discord.Color.green(),
        )

        await safe_reply(interaction, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(PropertiesCog(bot))
