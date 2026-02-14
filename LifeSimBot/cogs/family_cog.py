# cogs/family_cog.py
from __future__ import annotations

import json
import random
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from services.family_service import (
    get_kids,
    add_kid,
    calculate_family_bonus,
    generate_kid_names,
    calculate_divorce_cost,
)
from services.relationships_service import RelationshipsService
from views.family_views import MarriageProposal, DivorceConfirmation
from utils.format import money
from utils.checks import safe_defer, safe_reply


class FamilyCog(commands.Cog):
    """Marriage and family management commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.relationships = RelationshipsService(bot.db)

    # -------- Marriage --------

    @app_commands.command(name="marry", description="💍 Propose marriage to another user")
    @app_commands.describe(user="User to propose to")
    async def marry(self, interaction: discord.Interaction, user: discord.User):
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        target_id = str(user.id)

        # Self / bot checks
        if userid == target_id:
            return await safe_reply(interaction, content="❌ You can't marry yourself!")

        if user.bot:
            return await safe_reply(interaction, content="❌ You can't marry a bot!")

        u = db.getuser(userid)
        target_u = db.getuser(target_id)

        # Already married checks
        if u.get("spouse"):
            return await safe_reply(
                interaction,
                content="❌ You're already married! Use `/divorce` first.",
            )

        if target_u.get("spouse"):
            return await safe_reply(
                interaction,
                content=f"❌ {user.display_name} is already married!",
            )

        # Prepare interactive proposal view
        view = MarriageProposal(interaction.user, user, self.bot)

        embed = discord.Embed(
            title="💍 Marriage Proposal",
            description=(
                f"**{interaction.user.display_name}** proposed to **{user.display_name}**!\n\n"
                f"Will you accept?"
            ),
            color=discord.Color.pink(),
        )
        embed.set_footer(text="This proposal expires in 2 minutes")

        await safe_reply(
            interaction,
            content=user.mention,
            embed=embed,
            view=view,
        )

        # Wait for accept/deny from the view
        await view.wait()

        if not getattr(view, "accepted", False):
            return

        # Actually perform the marriage here (if your view doesn't already)
        now_iso = datetime.now(timezone.utc).isoformat()

        db.updatestat(userid, "spouse", target_id)
        db.updatestat(userid, "married_at", now_iso)

        db.updatestat(target_id, "spouse", userid)
        db.updatestat(target_id, "married_at", now_iso)

        # Optionally reset / initialize family bank for both
        # (depends on how your db helpers treat it)
        for uid in (userid, target_id):
            udata = db.getuser(uid)
            if "family_bank" not in udata:
                db.updatestat(uid, "family_bank", 0)

        # Sync with relationships: both sides become high‑affection partners
        # Give them a big gift-equivalent to shoot affection up
        self.relationships.apply_gift(userid, target_id, value=100_000)
        self.relationships.apply_gift(target_id, userid, value=100_000)
        self.relationships.askout(userid, target_id)
        self.relationships.askout(target_id, userid)

        confirm_embed = discord.Embed(
            title="💍 Married!",
            description=f"**{interaction.user.display_name}** is now married to **{user.display_name}**!",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=confirm_embed)

    # -------- Divorce --------

    @app_commands.command(name="divorce", description="💔 Divorce your spouse")
    async def divorce(self, interaction: discord.Interaction):
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        spouse_id = u.get("spouse")

        if not spouse_id:
            return await safe_reply(interaction, content="❌ You're not married!")

        # Get spouse display name (best-effort)
        try:
            spouse_user = await self.bot.fetch_user(int(spouse_id))
            spouse_name = spouse_user.display_name
        except Exception:
            spouse_name = "Unknown User"

        # Calculate divorce cost
        cost = calculate_divorce_cost(u)
        balance = int(u.get("balance", 0))

        if balance < cost:
            return await safe_reply(
                interaction,
                content=f"❌ You can't afford the divorce! Cost: {money(cost)}, you have: {money(balance)}",
            )

        # Confirm divorce with view
        view = DivorceConfirmation(interaction.user, spouse_name, cost)

        embed = discord.Embed(
            title="💔 Divorce Confirmation",
            description=(
                f"Are you sure you want to divorce **{spouse_name}**?\n\n"
                f"**Cost:** {money(cost)}\n"
                f"**Includes:** Lawyer fees + 50% of family bank"
            ),
            color=discord.Color.red(),
        )

        await safe_reply(interaction, embed=embed, view=view)

        await view.wait()
        if not getattr(view, "confirmed", False):
            return

        # Perform divorce
        db.removebalance(userid, cost)

        # Clear marriage / family bank for both
        db.updatestat(userid, "spouse", None)
        db.updatestat(userid, "married_at", None)
        db.updatestat(userid, "family_bank", 0)

        db.updatestat(spouse_id, "spouse", None)
        db.updatestat(spouse_id, "married_at", None)
        db.updatestat(spouse_id, "family_bank", 0)

        # Sync with relationships: both become ex with reduced affection
        self.relationships.breakup(userid, spouse_id)
        self.relationships.breakup(spouse_id, userid)

        embed = discord.Embed(
            title="💔 Divorced",
            description=f"You are no longer married to **{spouse_name}**.\n\nCost: {money(cost)}",
            color=discord.Color.red(),
        )

        await interaction.followup.send(embed=embed)

    # -------- Family view --------

    @app_commands.command(name="family", description="👨‍👩‍👧 View your family")
    async def family(self, interaction: discord.Interaction):
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        spouse_id = u.get("spouse")
        kids = get_kids(u)
        family_bank = int(u.get("family_bank", 0))

        embed = discord.Embed(
            title=f"👨‍👩‍👧 {interaction.user.display_name}'s Family",
            color=discord.Color.blue(),
        )

        # Spouse
        if spouse_id:
            try:
                spouse_user = await self.bot.fetch_user(int(spouse_id))
                married_at = u.get("married_at")

                if married_at:
                    try:
                        married_time = datetime.fromisoformat(married_at)
                        days_married = (datetime.now(timezone.utc) - married_time).days
                        time_text = f"{days_married} days"
                    except Exception:
                        time_text = "Unknown"
                else:
                    time_text = "Unknown"

                embed.add_field(
                    name="💍 Spouse",
                    value=f"{spouse_user.mention}\n└ Married: {time_text}",
                    inline=False,
                )
            except Exception:
                embed.add_field(
                    name="💍 Spouse",
                    value="Unknown User",
                    inline=False,
                )
        else:
            embed.add_field(
                name="💍 Spouse",
                value="Single",
                inline=False,
            )

        # Kids
        if kids:
            kids_text = []
            for kid in kids:
                kids_text.append(
                    f"• **{kid['name']}** (Age {kid['age']})\n"
                    f"  └ 😊 Happiness: {kid.get('happiness', 100)}"
                )

            embed.add_field(
                name=f"👶 Kids ({len(kids)})",
                value="\n".join(kids_text),
                inline=False,
            )
        else:
            embed.add_field(
                name="👶 Kids",
                value="No kids",
                inline=False,
            )

        # Family bank
        embed.add_field(
            name="💰 Family Bank",
            value=money(family_bank),
            inline=False,
        )

        # Family bonuses
        bonuses = calculate_family_bonus(u)
        bonus_text = []
        for bonus_type, value in bonuses.items():
            if value > 0:
                bonus_text.append(f"• {bonus_type.replace('_', ' ').title()}: +{value}%")

        if bonus_text:
            embed.add_field(
                name="💎 Family Bonuses",
                value="\n".join(bonus_text),
                inline=False,
            )

        await safe_reply(interaction, embed=embed)

    # -------- Adoption --------

    @app_commands.command(name="adopt", description="👶 Adopt a child")
    @app_commands.describe(name="Name for your child (optional)")
    async def adopt(self, interaction: discord.Interaction, name: str | None = None):
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        # Must be married
        if not u.get("spouse"):
            return await safe_reply(
                interaction,
                content="❌ You must be married to adopt a child!",
            )

        adoption_cost = 25_000
        balance = int(u.get("balance", 0))

        if balance < adoption_cost:
            return await safe_reply(
                interaction,
                content=f"❌ Adoption costs {money(adoption_cost)}! You have {money(balance)}",
            )

        kids = get_kids(u)
        if len(kids) >= 10:
            return await safe_reply(
                interaction,
                content="❌ You already have 10 kids! (Max limit)",
            )

        # Generate or use provided name
        if not name:
            available_names = generate_kid_names()
            name = random.choice(available_names)

        if len(name) > 20:
            return await safe_reply(
                interaction,
                content="❌ Name must be 20 characters or less!",
            )

        # Adopt kid
        db.removebalance(userid, adoption_cost)
        new_kids = add_kid(u, name, age=0)
        db.updatestat(userid, "kids", json.dumps(new_kids))

        embed = discord.Embed(
            title="👶 Child Adopted!",
            description=f"Welcome **{name}** to the family!",
            color=discord.Color.green(),
        )

        embed.add_field(
            name="Details",
            value=(
                f"**Name:** {name}\n"
                f"**Age:** 0 (newborn)\n"
                f"**Cost:** {money(adoption_cost)}"
            ),
            inline=False,
        )

        embed.set_footer(text=f"You now have {len(new_kids)} kid(s)")

        await safe_reply(interaction, embed=embed)

    # -------- Family bank --------

    @app_commands.command(name="familybank", description="💰 Manage family bank")
    @app_commands.describe(
        action="Deposit or withdraw",
        amount="Amount of money",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Deposit", value="deposit"),
            app_commands.Choice(name="Withdraw", value="withdraw"),
        ]
    )
    async def familybank(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        amount: int,
    ):
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        if not u.get("spouse"):
            return await safe_reply(
                interaction,
                content="❌ You must be married to use the family bank!",
            )

        if amount <= 0:
            return await safe_reply(
                interaction,
                content="❌ Amount must be positive!",
            )

        balance = int(u.get("balance", 0))
        family_bank = int(u.get("family_bank", 0))

        if action.value == "deposit":
            if balance < amount:
                return await safe_reply(
                    interaction,
                    content=f"❌ You don't have {money(amount)}! Balance: {money(balance)}",
                )

            db.removebalance(userid, amount)
            db.add_to_family_bank(userid, amount)

            embed = discord.Embed(
                title="💰 Deposited to Family Bank",
                description=(
                    f"**Amount:** {money(amount)}\n"
                    f"**New Family Bank:** {money(family_bank + amount)}"
                ),
                color=discord.Color.green(),
            )

        else:  # withdraw
            if family_bank < amount:
                return await safe_reply(
                    interaction,
                    content=f"❌ Family bank only has {money(family_bank)}!",
                )

            db.remove_from_family_bank(userid, amount)
            db.addbalance(userid, amount)

            embed = discord.Embed(
                title="💰 Withdrawn from Family Bank",
                description=(
                    f"**Amount:** {money(amount)}\n"
                    f"**New Family Bank:** {money(family_bank - amount)}"
                ),
                color=discord.Color.blue(),
            )

        await safe_reply(interaction, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(FamilyCog(bot))
