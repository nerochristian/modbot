from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

from ..utils.format import format_number, money


class AdminCog(commands.Cog):
    """Admin-only commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- PERM CHECK ----------

    @staticmethod
    def is_bot_owner(interaction: discord.Interaction) -> bool:
        """Check if user is bot owner."""
        OWNER_IDS = [1269772767516033025]  # your ID
        return interaction.user.id in OWNER_IDS

    # ---------- PANEL ----------

    @app_commands.command(name="admin", description="🔧 Admin panel")
    @app_commands.check(is_bot_owner)
    async def admin(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        db = self.bot.db

        total_users = len(db.getallusers())
        uptime = datetime.now(timezone.utc) - self.bot.start_time
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)

        embed = discord.Embed(
            title="🔧 Admin Panel",
            color=discord.Color.purple(),
        )

        embed.add_field(
            name="📊 Bot Stats",
            value=(
                f"Uptime: **{hours}h {minutes}m**\n"
                f"Guilds: **{len(self.bot.guilds)}**\n"
                f"Users: **{total_users}**\n"
                f"Commands: **{len(self.bot.tree.get_commands())}**"
            ),
            inline=False,
        )

        embed.add_field(
            name="💾 Database",
            value="✅ Connected",
            inline=True,
        )

        task_candidates = [
            getattr(self.bot, "update_stats", None),
            getattr(self.bot, "check_cooldowns", None),
            getattr(self.bot, "auto_save", None),
            getattr(self.bot, "passive_decay", None),
            getattr(self.bot, "pet_decay", None),
            getattr(self.bot, "business_income", None),
        ]
        running_tasks = [t for t in task_candidates if getattr(t, "is_running", lambda: False)()]
        embed.add_field(
            name="🔄 Tasks Running",
            value=f"✅ {len(running_tasks)}",
            inline=True,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ---------- MONEY / XP ----------

    @app_commands.command(name="givemoney", description="💰 Give money to a user (admin only)")
    @app_commands.describe(user="User to give money to", amount="Amount to give")
    @app_commands.check(is_bot_owner)
    async def givemoney(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        await interaction.response.defer(ephemeral=True)

        if amount <= 0:
            return await interaction.followup.send("❌ Amount must be positive!", ephemeral=True)

        db = self.bot.db
        db.addbalance(str(user.id), amount, use_buffs=False)

        embed = discord.Embed(
            title="✅ Money Given",
            description=f"Gave **{money(amount)}** to {user.mention}",
            color=discord.Color.green(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="removemoney", description="💰 Remove money from a user (admin only)")
    @app_commands.describe(user="User to remove money from", amount="Amount to remove")
    @app_commands.check(is_bot_owner)
    async def removemoney(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        await interaction.response.defer(ephemeral=True)

        if amount <= 0:
            return await interaction.followup.send("❌ Amount must be positive!", ephemeral=True)

        db = self.bot.db
        db.removebalance(str(user.id), amount)

        embed = discord.Embed(
            title="✅ Money Removed",
            description=f"Removed **{money(amount)}** from {user.mention}",
            color=discord.Color.red(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="givexp", description="⭐ Give XP to a user (admin only)")
    @app_commands.describe(user="User to give XP to", amount="Amount of XP")
    @app_commands.check(is_bot_owner)
    async def givexp(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        await interaction.response.defer(ephemeral=True)

        if amount <= 0:
            return await interaction.followup.send("❌ Amount must be positive!", ephemeral=True)

        db = self.bot.db
        db.addxp(str(user.id), amount, use_buffs=False)

        embed = discord.Embed(
            title="✅ XP Given",
            description=f"Gave **{format_number(amount)}** XP to {user.mention}",
            color=discord.Color.green(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="setlevel", description="📈 Set a user's level (admin only)")
    @app_commands.describe(user="User to edit", level="New level value")
    @app_commands.check(is_bot_owner)
    async def setlevel(self, interaction: discord.Interaction, user: discord.Member, level: int):
        await interaction.response.defer(ephemeral=True)

        if level <= 0:
            return await interaction.followup.send("❌ Level must be positive!", ephemeral=True)

        db = self.bot.db
        db.updatestat(str(user.id), "level", level)

        embed = discord.Embed(
            title="✅ Level Set",
            description=f"Set {user.mention}'s level to **{level}**",
            color=discord.Color.green(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ---------- GENERIC STAT TOOLS ----------

    @app_commands.command(name="setstat", description="🧬 Set any user stat field (admin only)")
    @app_commands.describe(user="User to edit", field="DB field name", value="New value")
    @app_commands.check(is_bot_owner)
    async def setstat(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        field: str,
        value: str,
    ):
        await interaction.response.defer(ephemeral=True)

        db = self.bot.db
        userid = str(user.id)

        # try to coerce to int if numeric
        try:
            if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
                new_val: object = int(value)
            else:
                new_val = value
        except Exception:
            new_val = value

        try:
            db.updatestat(userid, field, new_val)
        except Exception as e:
            return await interaction.followup.send(
                f"❌ Failed to set stat: `{e}`",
                ephemeral=True,
            )

        embed = discord.Embed(
            title="✅ Stat Updated",
            description=f"Set `{field}` for {user.mention} to `{new_val}`",
            color=discord.Color.green(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="getstat", description="🔎 View a raw user stat field (admin only)")
    @app_commands.describe(user="User to inspect", field="DB field name")
    @app_commands.check(is_bot_owner)
    async def getstat(self, interaction: discord.Interaction, user: discord.Member, field: str):
        await interaction.response.defer(ephemeral=True)

        db = self.bot.db
        data = db.getuser(str(user.id))
        value = data.get(field, "<missing>")

        embed = discord.Embed(
            title="🔎 Stat Value",
            description=f"`{field}` for {user.mention}: `{value}`",
            color=discord.Color.blurple(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ---------- INVENTORY / ITEMS ----------

    @app_commands.command(name="giveitem", description="🎁 Give an item to a user (admin only)")
    @app_commands.describe(user="User to give item to", item_id="Internal item id", amount="Amount")
    @app_commands.check(is_bot_owner)
    async def giveitem(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        item_id: str,
        amount: int = 1,
    ):
        await interaction.response.defer(ephemeral=True)

        if amount <= 0:
            return await interaction.followup.send("❌ Amount must be positive!", ephemeral=True)

        db = self.bot.db
        db.additem(str(user.id), item_id, amount)

        embed = discord.Embed(
            title="✅ Item Given",
            description=f"Gave **{amount}x** `{item_id}` to {user.mention}",
            color=discord.Color.green(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="removeitem", description="🗑️ Remove an item from a user (admin only)")
    @app_commands.describe(user="User to remove item from", item_id="Internal item id", amount="Amount")
    @app_commands.check(is_bot_owner)
    async def removeitem(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        item_id: str,
        amount: int = 1,
    ):
        await interaction.response.defer(ephemeral=True)

        if amount <= 0:
            return await interaction.followup.send("❌ Amount must be positive!", ephemeral=True)

        db = self.bot.db
        db.removeitem(str(user.id), item_id, amount)

        embed = discord.Embed(
            title="✅ Item Removed",
            description=f"Removed **{amount}x** `{item_id}` from {user.mention}",
            color=discord.Color.red(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ---------- USER RESET ----------

    @app_commands.command(name="resetuser", description="🔄 Reset a user's data (admin only)")
    @app_commands.describe(user="User to reset", confirm="Type 'yes' to confirm")
    @app_commands.check(is_bot_owner)
    async def resetuser(self, interaction: discord.Interaction, user: discord.Member, confirm: str):
        await interaction.response.defer(ephemeral=True)

        if confirm.lower() != "yes":
            return await interaction.followup.send(
                "❌ Confirmation failed! Type 'yes' to confirm.",
                ephemeral=True,
            )

        db = self.bot.db
        userid = str(user.id)

        db.conn.execute("DELETE FROM users WHERE userid = ?", (userid,))
        db.conn.commit()
        db.ensure_user(userid)

        embed = discord.Embed(
            title="✅ User Reset",
            description=f"Reset all data for {user.mention}",
            color=discord.Color.green(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ---------- QUESTS / BUFFS DEBUG ----------

    @app_commands.command(name="forcequests", description="📜 Force refresh daily quests for a user (admin only)")
    @app_commands.describe(user="User to refresh")
    @app_commands.check(is_bot_owner)
    async def forcequests(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        try:
            from ..services.quests_service import QuestsService
        except Exception as e:
            return await interaction.followup.send(
                f"❌ QuestsService import failed: `{e}`",
                ephemeral=True,
            )

        svc = QuestsService(self.bot.db)
        svc.force_refresh_for_user(str(user.id))

        embed = discord.Embed(
            title="✅ Quests Refreshed",
            description=f"Forced daily quest refresh for {user.mention}",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="testbuffs", description="📊 Show effective buff multipliers for a user (admin only)")
    @app_commands.describe(user="User to inspect")
    @app_commands.check(is_bot_owner)
    async def testbuffs(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        try:
            from ..services.buffs_service import BuffsService
        except Exception as e:
            return await interaction.followup.send(
                f"❌ BuffsService import failed: `{e}`",
                ephemeral=True,
            )

        svc = BuffsService(self.bot.db)
        buffs = svc.get_user_buffs(str(user.id))

        embed = discord.Embed(
            title=f"📊 Buffs for {user.display_name}",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Money Multiplier",
            value=f"`x{buffs.money_mult:.2f}`",
            inline=True,
        )
        embed.add_field(
            name="XP Multiplier",
            value=f"`x{buffs.xp_mult:.2f}`",
            inline=True,
        )
        embed.add_field(
            name="Notes",
            value="Includes family, relationships, housing, pets, and other sources.",
            inline=False,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ---------- ANNOUNCE ----------

    @app_commands.command(name="announce", description="📢 Send an announcement to this server (admin only)")
    @app_commands.describe(message="Announcement message")
    @app_commands.check(is_bot_owner)
    async def announce(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="📢 Life Sim Announcement",
            description=message,
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Announcement from the bot owner")

        channel = interaction.channel
        if channel is None or not isinstance(channel, discord.TextChannel):
            return await interaction.followup.send(
                "❌ Could not determine a text channel to send in.",
                ephemeral=True,
            )

        await channel.send(embed=embed)

        result_embed = discord.Embed(
            title="✅ Announcement Sent",
            description=f"Sent announcement in {channel.mention}",
            color=discord.Color.green(),
        )

        await interaction.followup.send(embed=result_embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
