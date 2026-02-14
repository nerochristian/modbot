# cogs/guilds_cog.py
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.guilds_service import (
    generate_guild_id,
    calculate_guild_level,
    get_guild_perks,
    calculate_guild_bonuses,
    get_guild_members,
    can_manage_guild
)
from views.guild_views import GuildInvite, LeaveGuildConfirmation
from utils.format import money, progress_bar
from utils.checks import safe_defer, safe_reply
from views.v2_embed import apply_v2_embed_layout


class GuildsCog(commands.Cog):
    """Guild system commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="createguild", description="🛡️ Create a guild")
    @app_commands.describe(name="Guild name")
    async def createguild(self, interaction: discord.Interaction, name: str):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        
        # Check if already in guild
        if u.get("guild_id"):
            return await safe_reply(interaction, content="❌ You're already in a guild! Leave it first.")
        
        # Check name length
        if len(name) > 32:
            return await safe_reply(interaction, content="❌ Guild name must be 32 characters or less!")
        
        if len(name) < 3:
            return await safe_reply(interaction, content="❌ Guild name must be at least 3 characters!")
        
        # Check cost
        creation_cost = 50000
        balance = int(u.get("balance", 0))
        
        if balance < creation_cost:
            return await safe_reply(
                interaction,
                content=f"❌ Creating a guild costs {money(creation_cost)}! You have {money(balance)}"
            )
        
        # Create guild
        guild_id = generate_guild_id()
        db.removebalance(userid, creation_cost)
        db.create_guild(guild_id, name, userid)
        
        embed = discord.Embed(
            title="🛡️ Guild Created!",
            description=f"**{name}** has been created!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Guild Info",
            value=(
                f"**ID:** `{guild_id}`\n"
                f"**Owner:** {interaction.user.mention}\n"
                f"**Cost:** {money(creation_cost)}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Next Steps",
            value=(
                "• Invite members with `/guildinvite`\n"
                "• Deposit to guild bank with `/guildbank`\n"
                "• Level up your guild by having members work and earn XP!"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Guild ID: {guild_id}")
        
        await safe_reply(interaction, embed=embed)
    
    @app_commands.command(name="guild", description="🛡️ View guild information")
    @app_commands.describe(guild_id="Guild ID to view (leave blank for your guild)")
    async def guild(self, interaction: discord.Interaction, guild_id: str = None):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        
        # Get guild ID
        if not guild_id:
            guild_id = u.get("guild_id")
            if not guild_id:
                return await safe_reply(interaction, content="❌ You're not in a guild!")
        
        # Get guild data
        guild_data = db.getguild(guild_id)
        if not guild_data:
            return await safe_reply(interaction, content="❌ Guild not found!")
        
        # Calculate level
        guild_xp = int(guild_data.get("xp", 0))
        level, curr_xp, needed_xp = calculate_guild_level(guild_xp)
        
        # Get perks
        perks = get_guild_perks(level)
        
        # Get members
        members = get_guild_members(self.bot, guild_data)
        member_count = len(members)
        
        # Get owner
        try:
            owner = await self.bot.fetch_user(int(guild_data["owner_id"]))
            owner_mention = owner.mention
        except:
            owner_mention = "Unknown"
        
        embed = discord.Embed(
            title=f"🛡️ {guild_data['name']}",
            description=guild_data.get("description", "No description set"),
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📊 Stats",
            value=(
                f"**Level:** {level}\n"
                f"**XP:** {progress_bar(curr_xp, needed_xp, 8)} {curr_xp}/{needed_xp}\n"
                f"**Members:** {member_count}\n"
                f"**Bank:** {money(int(guild_data.get('bank', 0)))}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="👑 Leadership",
            value=f"**Owner:** {owner_mention}",
            inline=False
        )
        
        if perks:
            embed.add_field(
                name="💎 Active Perks",
                value="\n".join(perks),
                inline=False
            )
        else:
            embed.add_field(
                name="💎 Active Perks",
                value="Reach level 5 to unlock perks!",
                inline=False
            )
        
        # Show top members
        if members:
            top_members = sorted(members, key=lambda m: m["level"], reverse=True)[:5]
            member_text = []
            for m in top_members:
                try:
                    user = await self.bot.fetch_user(int(m["userid"]))
                    role_emoji = {"owner": "👑", "admin": "⭐", "member": "🛡️"}.get(m["role"], "🛡️")
                    member_text.append(f"{role_emoji} **{user.display_name}** - Lv{m['level']}")
                except:
                    pass
            
            if member_text:
                embed.add_field(
                    name=f"👥 Top Members",
                    value="\n".join(member_text[:5]),
                    inline=False
                )
        
        embed.set_footer(text=f"Guild ID: {guild_id}")
        
        await safe_reply(interaction, embed=embed)
    
    @app_commands.command(name="guildinvite", description="📨 Invite someone to your guild")
    @app_commands.describe(user="User to invite")
    async def guildinvite(self, interaction: discord.Interaction, user: discord.User):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        target_id = str(user.id)
        
        u = db.getuser(userid)
        target_u = db.getuser(target_id)
        
        # Check if in guild
        guild_id = u.get("guild_id")
        if not guild_id:
            return await safe_reply(interaction, content="❌ You're not in a guild!")
        
        # Check if can invite
        if not can_manage_guild(u, "member"):
            return await safe_reply(interaction, content="❌ Only guild owner/admins can invite members!")
        
        # Check if target already in guild
        if target_u.get("guild_id"):
            return await safe_reply(interaction, content=f"❌ {user.mention} is already in a guild!")
        
        # Check if inviting self
        if userid == target_id:
            return await safe_reply(interaction, content="❌ You can't invite yourself!")
        
        # Check if bot
        if user.bot:
            return await safe_reply(interaction, content="❌ You can't invite bots!")
        
        # Get guild data
        guild_data = db.getguild(guild_id)
        
        # Send invite
        view = GuildInvite(interaction.user, user, guild_data, self.bot)
        
        embed = discord.Embed(
            title="📨 Guild Invite",
            description=(
                f"**{interaction.user.display_name}** invited you to join **{guild_data['name']}**!\n\n"
                f"**Guild Level:** {calculate_guild_level(int(guild_data.get('xp', 0)))[0]}\n"
                f"**Members:** {guild_data.get('member_count', 1)}"
            ),
            color=discord.Color.blue()
        )
        
        embed.set_footer(text="This invite expires in 2 minutes")
        
        apply_v2_embed_layout(view, embed=embed)
        await interaction.followup.send(content=user.mention, view=view)
    
    @app_commands.command(name="leaveguild", description="🚪 Leave your current guild")
    async def leaveguild(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        
        guild_id = u.get("guild_id")
        if not guild_id:
            return await safe_reply(interaction, content="❌ You're not in a guild!")
        
        # Check if owner
        guild_data = db.getguild(guild_id)
        if guild_data.get("owner_id") == userid:
            return await safe_reply(
                interaction,
                content="❌ Guild owners can't leave! Transfer ownership or disband the guild first."
            )
        
        # Confirm leave
        view = LeaveGuildConfirmation(interaction.user, guild_data["name"])
        
        embed = discord.Embed(
            title="🚪 Leave Guild?",
            description=f"Are you sure you want to leave **{guild_data['name']}**?",
            color=discord.Color.orange()
        )
        
        apply_v2_embed_layout(view, embed=embed)
        await safe_reply(interaction, view=view)
        
        # Wait for response
        await view.wait()
        
        if not view.confirmed:
            return
        
        # Leave guild
        db.updatestats(userid, guild_id=None, guild_role="member")
        
        # Update member count
        current_count = int(guild_data.get("member_count", 1))
        db.updateguild(guild_id, "member_count", max(1, current_count - 1))
        
        embed = discord.Embed(
            title="🚪 Left Guild",
            description=f"You left **{guild_data['name']}**",
            color=discord.Color.red()
        )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="guildbank", description="💰 Manage guild bank")
    @app_commands.describe(
        action="Deposit or withdraw",
        amount="Amount of money"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Deposit", value="deposit"),
        app_commands.Choice(name="Withdraw", value="withdraw"),
    ])
    async def guildbank(self, interaction: discord.Interaction, action: str, amount: int):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)
        
        guild_id = u.get("guild_id")
        if not guild_id:
            return await safe_reply(interaction, content="❌ You're not in a guild!")
        
        if amount <= 0:
            return await safe_reply(interaction, content="❌ Amount must be positive!")
        
        balance = int(u.get("balance", 0))
        guild_data = db.getguild(guild_id)
        guild_bank = int(guild_data.get("bank", 0))
        
        if action == "deposit":
            if balance < amount:
                return await safe_reply(
                    interaction,
                    content=f"❌ You don't have {money(amount)}! Balance: {money(balance)}"
                )
            
            db.removebalance(userid, amount)
            db.add_to_guild_bank(guild_id, amount)
            
            embed = discord.Embed(
                title="💰 Deposited to Guild Bank",
                description=f"**Amount:** {money(amount)}\n**New Guild Bank:** {money(guild_bank + amount)}",
                color=discord.Color.green()
            )
            
        else:  # withdraw
            # Only owner/admin can withdraw
            if not can_manage_guild(u, "member"):
                return await safe_reply(interaction, content="❌ Only guild owner/admins can withdraw!")
            
            if guild_bank < amount:
                return await safe_reply(
                    interaction,
                    content=f"❌ Guild bank only has {money(guild_bank)}!"
                )
            
            db.remove_from_guild_bank(guild_id, amount)
            db.addbalance(userid, amount)
            
            embed = discord.Embed(
                title="💰 Withdrawn from Guild Bank",
                description=f"**Amount:** {money(amount)}\n**New Guild Bank:** {money(guild_bank - amount)}",
                color=discord.Color.blue()
            )
        
        await safe_reply(interaction, embed=embed)
    
    @app_commands.command(name="guildkick", description="👢 Kick a member from the guild")
    @app_commands.describe(user="User to kick")
    async def guildkick(self, interaction: discord.Interaction, user: discord.User):
        await safe_defer(interaction)
        
        db = self.bot.db
        userid = str(interaction.user.id)
        target_id = str(user.id)
        
        u = db.getuser(userid)
        target_u = db.getuser(target_id)
        
        guild_id = u.get("guild_id")
        if not guild_id:
            return await safe_reply(interaction, content="❌ You're not in a guild!")
        
        # Check if can kick
        if not can_manage_guild(u, target_u.get("guild_role", "member")):
            return await safe_reply(interaction, content="❌ You don't have permission to kick this member!")
        
        # Check if target in same guild
        if target_u.get("guild_id") != guild_id:
            return await safe_reply(interaction, content="❌ That user isn't in your guild!")
        
        # Can't kick owner
        guild_data = db.getguild(guild_id)
        if target_id == guild_data.get("owner_id"):
            return await safe_reply(interaction, content="❌ You can't kick the guild owner!")
        
        # Can't kick self
        if userid == target_id:
            return await safe_reply(interaction, content="❌ Use `/leaveguild` to leave!")
        
        # Kick member
        db.updatestats(target_id, guild_id=None, guild_role="member")
        
        # Update member count
        current_count = int(guild_data.get("member_count", 1))
        db.updateguild(guild_id, "member_count", max(1, current_count - 1))
        
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"**{user.display_name}** was kicked from the guild",
            color=discord.Color.red()
        )
        
        await safe_reply(interaction, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(GuildsCog(bot))
