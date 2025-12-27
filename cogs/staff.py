"""
Staff System - Staff guide, rules, and staff sanctions (SUPERVISOR SYSTEM)
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from typing import Optional
from utils.embeds import ModEmbed
from utils.checks import is_mod, is_admin, is_bot_owner_id
from utils.logging import send_log_embed
from config import Config


def is_supervisor():
    """Check if user has supervisor role or is admin/owner"""
    async def predicate(interaction: discord. Interaction):
        if is_bot_owner_id(interaction.user.id):
            return True
        if interaction.user.id == interaction.guild.owner_id:
            return True
        
        if interaction.user.guild_permissions.administrator:
            return True
        
        settings = await interaction.client.db.get_settings(interaction.guild_id)
        supervisor_role = settings.get('supervisor_role')
        
        if supervisor_role:
            user_role_ids = [r.id for r in interaction.user.roles]
            return supervisor_role in user_role_ids
        
        return False
    
    return app_commands.check(predicate)


class Staff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def create_status_bar(self, current: int, max_val: int, length: int = 10) -> str:
        """Create a visual progress bar"""
        filled = int((current / max_val) * length) if max_val > 0 else 0
        filled = min(filled, length)
        empty = length - filled
        
        if current == 0:
            return f"{'░' * length} {current}/{max_val}"
        elif current >= max_val:
            return f"{'█' * length} {current}/{max_val} ⚠️"
        else: 
            return f"{'█' * filled}{'░' * empty} {current}/{max_val}"

    def get_status_emoji(self, warns: int, strikes: int) -> str:
        """Get status emoji based on sanction level"""
        if strikes >= 3:
            return "🔴"
        elif strikes >= 2:
            return "🟠"
        elif strikes >= 1 or warns >= 2:
            return "🟡"
        else:
            return "🟢"

    def get_status_text(self, warns: int, strikes: int) -> str:
        """Get status description"""
        if strikes >= 3:
            return "🔴 **CRITICAL** - Staff ban required"
        elif strikes >= 2:
            return "🟠 **SEVERE** - One strike from removal"
        elif strikes >= 1 or warns >= 2:
            return "🟡 **WARNING** - Needs improvement"
        else:
            return "🟢 **GOOD STANDING**"

    async def is_staff_member(self, guild_id: int, member:  discord.Member) -> bool:
        """Check if a member is a staff member"""
        settings = await self.bot.db.get_settings(guild_id)
        staff_role_keys = ['admin_role', 'supervisor_role', 'senior_mod_role', 'mod_role', 'trial_mod_role', 'staff_role']
        
        staff_roles = [settings.get(key) for key in staff_role_keys if settings.get(key)]
        user_role_ids = [r.id for r in member.roles]
        
        return any(role_id in user_role_ids for role_id in staff_roles)

    async def get_sanction_counts(self, guild_id: int, staff_id: int) -> tuple: 
        """Get warn and strike counts for a staff member"""
        sanctions = await self.bot.db. get_staff_sanctions(guild_id, staff_id)
        warns = len([s for s in sanctions if s['sanction_type'] == 'warn'])
        strikes = len([s for s in sanctions if s['sanction_type'] == 'strike'])
        return warns, strikes

    # ============ RULES COMMANDS ============
    rules_group = app_commands.Group(name="rules", description="Server rules management")

    @rules_group.command(name="post", description="📜 Post the server rules")
    @app_commands.describe(channel="Channel to post rules in")
    @is_admin()
    async def rules_post(self, interaction:  discord.Interaction, channel: Optional[discord.TextChannel] = None):
        channel = channel or interaction.channel
        settings = await self.bot.db. get_settings(interaction.guild_id)
        rules = settings.get('server_rules', [])

        if not rules:
            return await interaction.response.send_message(
                embed=ModEmbed.error("No Rules", "No rules set.  Use `/rules add` first."),
                ephemeral=True
            )

        embed = discord.Embed(
            title="📜 Server Rules",
            description="Please read and follow all rules! ",
            color=Config.COLOR_EMBED,
            timestamp=datetime.now(timezone.utc)
        )

        rules_text = "\n\n".join([f"**{i}. ** {rule}" for i, rule in enumerate(rules, 1)])
        embed.add_field(name="​", value=rules_text, inline=False)

        embed.add_field(
            name="⚠️ Consequences",
            value="• Verbal Warning\n• Written Warning\n• Temporary Mute\n• Temporary Ban\n• Permanent Ban",
            inline=False
        )

        embed.set_footer(text=f"{interaction.guild.name}")
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        await channel.send(embed=embed)
        await interaction.response.send_message(
            embed=ModEmbed.success("Rules Posted", f"Rules posted in {channel.mention}"),
            ephemeral=True
        )

    @rules_group.command(name="add", description="➕ Add a new rule")
    @app_commands.describe(rule="The rule to add")
    @is_admin()
    async def rules_add(self, interaction: discord. Interaction, rule: str):
        settings = await self.bot.db. get_settings(interaction.guild_id)
        rules = settings. get('server_rules', [])
        rules.append(rule)
        settings['server_rules'] = rules
        await self.bot.db. update_settings(interaction.guild_id, settings)

        await interaction.response.send_message(
            embed=ModEmbed. success("Rule Added", f"**Rule #{len(rules)}:** {rule}")
        )

    @rules_group.command(name="remove", description="➖ Remove a rule")
    @app_commands.describe(rule_number="The rule number to remove")
    @is_admin()
    async def rules_remove(self, interaction: discord.Interaction, rule_number: int):
        settings = await self.bot.db. get_settings(interaction.guild_id)
        rules = settings. get('server_rules', [])

        if rule_number < 1 or rule_number > len(rules):
            return await interaction.response.send_message(
                embed=ModEmbed. error("Invalid Rule", f"Rule #{rule_number} doesn't exist."),
                ephemeral=True
            )

        removed = rules.pop(rule_number - 1)
        settings['server_rules'] = rules
        await self.bot.db.update_settings(interaction.guild_id, settings)

        await interaction.response.send_message(
            embed=ModEmbed.success("Rule Removed", f"Removed:  {removed}")
        )

    @rules_group.command(name="edit", description="✏️ Edit a rule")
    @app_commands.describe(rule_number="Rule number", new_rule="New rule text")
    @is_admin()
    async def rules_edit(self, interaction: discord.Interaction, rule_number: int, new_rule: str):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        rules = settings.get('server_rules', [])

        if rule_number < 1 or rule_number > len(rules):
            return await interaction. response.send_message(
                embed=ModEmbed.error("Invalid Rule", f"Rule #{rule_number} doesn't exist."),
                ephemeral=True
            )

        old_rule = rules[rule_number - 1]
        rules[rule_number - 1] = new_rule
        settings['server_rules'] = rules
        await self.bot.db.update_settings(interaction.guild_id, settings)

        await interaction.response.send_message(
            embed=ModEmbed.success("Rule Updated", f"**Before:** {old_rule}\n**After:** {new_rule}")
        )

    @rules_group.command(name="list", description="📋 List all rules")
    async def rules_list(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        rules = settings.get('server_rules', [])

        if not rules: 
            return await interaction.response.send_message(
                embed=ModEmbed.info("No Rules", "No rules have been set. "),
                ephemeral=True
            )

        embed = discord.Embed(title="📜 Server Rules", color=Config.COLOR_INFO)
        embed.description = "\n".join([f"**{i}.** {rule}" for i, rule in enumerate(rules, 1)])
        embed.set_footer(text=f"{len(rules)} rules total")

        await interaction.response. send_message(embed=embed)

    # ============ STAFF GUIDE COMMANDS ============
    staffguide_group = app_commands.Group(name="staffguide", description="Staff guide management")

    @staffguide_group.command(name="post", description="📚 Post the staff guide")
    @app_commands.describe(channel="Channel to post guide in")
    @is_admin()
    async def staffguide_post(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        channel = channel or interaction.channel
        settings = await self.bot.db.get_settings(interaction.guild_id)
        guide = settings.get('staff_guide', {})

        if not guide: 
            return await interaction.response.send_message(
                embed=ModEmbed.error("No Guide", "No staff guide configured. "),
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        # Welcome
        welcome_embed = discord.Embed(
            title="📚 Staff Guide",
            description=guide.get('welcome', 'Welcome to the staff team! '),
            color=Config.COLOR_EMBED,
            timestamp=datetime.now(timezone.utc)
        )
        if interaction.guild.icon:
            welcome_embed.set_thumbnail(url=interaction.guild.icon.url)
        welcome_embed.set_footer(text=f"{interaction.guild.name} Staff Team")
        await channel.send(embed=welcome_embed)

        # Sections
        for section in guide.get('sections', []):
            section_embed = discord. Embed(
                title=section['title'],
                description="\n".join([f"• {item}" for item in section. get('content', [])]),
                color=Config.COLOR_INFO
            )
            await channel.send(embed=section_embed)

        # Supervisor System
        supervisor_embed = discord. Embed(
            title="👁️ Supervisor & Sanction System",
            color=0x9B59B6
        )
        supervisor_embed. add_field(
            name="🔹 Supervisor Role",
            value="Supervisors can sanction **ANY** staff member,\nregardless of role hierarchy.",
            inline=False
        )
        supervisor_embed.add_field(
            name="⚠️ Warning & Strike System",
            value="**3 Warnings = 1 Strike**\n**3 Strikes = 7 Day Staff Ban**",
            inline=False
        )
        supervisor_embed.add_field(
            name="📊 Status Levels",
            value="🟢 Good Standing - 0-1 warns, 0 strikes\n🟡 Warning - 2+ warns or 1 strike\n🟠 Severe - 2 strikes\n🔴 Critical - 3 strikes",
            inline=False
        )
        await channel.send(embed=supervisor_embed)

        # Commands
        commands_embed = discord. Embed(title="🤖 Staff Commands", color=Config.COLOR_MOD)
        commands_embed. add_field(
            name="Moderation",
            value="`/warn` `/kick` `/ban` `/mute`\n`/tempban` `/purge` `/lock`",
            inline=True
        )
        commands_embed.add_field(
            name="Supervisor Only",
            value="`/staffsanction warn`\n`/staffsanction strike`\n`/staffsanction status`",
            inline=True
        )
        await channel.send(embed=commands_embed)

        await interaction.followup.send(
            embed=ModEmbed.success("Staff Guide Posted", f"Posted in {channel.mention}"),
            ephemeral=True
        )

    @staffguide_group.command(name="setwelcome", description="Set welcome message")
    @app_commands.describe(message="Welcome message")
    @is_admin()
    async def staffguide_setwelcome(self, interaction:  discord.Interaction, message: str):
        settings = await self. bot.db.get_settings(interaction.guild_id)
        guide = settings.get('staff_guide', {'sections': []})
        guide['welcome'] = message
        settings['staff_guide'] = guide
        await self.bot. db.update_settings(interaction. guild_id, settings)

        await interaction.response.send_message(
            embed=ModEmbed.success("Welcome Updated", "Staff guide welcome updated.")
        )

    @staffguide_group.command(name="addsection", description="Add a section")
    @app_commands.describe(title="Section title", content="Content (use | to separate)")
    @is_admin()
    async def staffguide_addsection(self, interaction: discord.Interaction, title: str, content: str):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        guide = settings.get('staff_guide', {'welcome': 'Welcome! ', 'sections': []})

        items = [item.strip() for item in content. split('|') if item.strip()]
        guide['sections'].append({'title': title, 'content':  items})

        settings['staff_guide'] = guide
        await self.bot. db.update_settings(interaction. guild_id, settings)

        await interaction.response.send_message(
            embed=ModEmbed.success("Section Added", f"Added **{title}** with {len(items)} items.")
        )

    # ============ STAFF SANCTION SYSTEM ============
    sanction_group = app_commands. Group(name="staffsanction", description="Staff sanctions (Supervisor only)")

    @sanction_group.command(name="warn", description="⚠️ Issue a warning to a staff member")
    @app_commands.describe(staff="Staff member to warn", reason="Reason for warning")
    @is_supervisor()
    async def sanction_warn(self, interaction:  discord.Interaction, staff: discord.Member, reason: str):
        # Verify target is staff
        if not await self.is_staff_member(interaction.guild_id, staff):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Staff", f"{staff.mention} is not a staff member."),
                ephemeral=True
            )

        if is_bot_owner_id(staff.id) and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You cannot sanction the bot owner."),
                ephemeral=True,
            )

        # Can't sanction yourself
        if staff. id == interaction.user.id:
            return await interaction.response. send_message(
                embed=ModEmbed.error("Error", "You cannot sanction yourself."),
                ephemeral=True
            )

        # Get current counts
        warns, strikes = await self.get_sanction_counts(interaction.guild_id, staff. id)

        # Check max warnings
        if warns >= 3:
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Max Warnings",
                    f"{staff.mention} has **3 warnings**.\n"
                    f"Use `/staffsanction strike` or `/staffsanction clearwarns` first."
                ),
                ephemeral=True
            )

        # Add warning
        await self.bot.db.add_staff_sanction(interaction.guild_id, staff.id, interaction.user.id, reason, 'warn')
        warns += 1

        # Create embed
        embed = discord.Embed(
            title="⚠️ Staff Sanction - Warning",
            color=Config.COLOR_WARNING,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Staff Member", value=f"{staff.mention}", inline=True)
        embed.add_field(name="Issued By", value=f"{interaction.user.mention}", inline=True)
        embed.add_field(name="Type", value="⚠️ Warning", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)

        # Status
        status_emoji = self.get_status_emoji(warns, strikes)
        status_bar = f"{status_emoji} **Staff Status**\n"
        status_bar += f"Warnings: {self.create_status_bar(warns, 3)}\n"
        status_bar += f"Strikes: {self.create_status_bar(strikes, 3)}"
        embed.add_field(name="📊 Standing", value=status_bar, inline=False)

        if warns >= 3:
            embed.add_field(
                name="⚠️ Threshold Reached",
                value="3 warnings reached!  Next sanction should be a strike.",
                inline=False
            )

        embed.set_thumbnail(url=staff.display_avatar.url)

        await interaction.response.send_message(embed=embed)

        # Log to channel
        settings = await self.bot.db. get_settings(interaction.guild_id)
        log_id = settings.get('staff_sanctions_channel')
        if log_id and log_id != interaction.channel_id:
            log_channel = interaction.guild.get_channel(log_id)
            if log_channel:
                await send_log_embed(log_channel, embed)

        # DM staff
        try:
            dm_embed = discord.Embed(
                title="⚠️ Staff Warning",
                description=f"You received a warning in **{interaction.guild.name}**",
                color=Config.COLOR_WARNING
            )
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            dm_embed.add_field(name="Warnings", value=f"{warns}/3", inline=True)
            dm_embed.add_field(name="Strikes", value=f"{strikes}/3", inline=True)
            await staff.send(embed=dm_embed)
        except:
            pass

    @sanction_group.command(name="strike", description="🔴 Issue a strike to a staff member")
    @app_commands.describe(staff="Staff member", reason="Reason", convert_warns="Convert 3 warnings to strike")
    @is_supervisor()
    async def sanction_strike(self, interaction: discord. Interaction, staff: discord.Member, reason: str, convert_warns:  bool = False):
        # Verify target is staff
        if not await self.is_staff_member(interaction.guild_id, staff):
            return await interaction.response. send_message(
                embed=ModEmbed.error("Not Staff", f"{staff.mention} is not a staff member."),
                ephemeral=True
            )

        if is_bot_owner_id(staff.id) and not is_bot_owner_id(interaction.user.id):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You cannot sanction the bot owner."),
                ephemeral=True,
            )

        # Can't sanction yourself
        if staff.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", "You cannot sanction yourself."),
                ephemeral=True
            )

        # Get current counts
        warns, strikes = await self.get_sanction_counts(interaction.guild_id, staff.id)

        # Convert warnings if requested
        if convert_warns and warns >= 3:
            await self.bot.db.clear_staff_warns(interaction.guild_id, staff.id)
            warns = 0
            reason = f"[Converted from 3 warnings] {reason}"

        # Add strike
        await self.bot.db.add_staff_sanction(interaction.guild_id, staff. id, interaction.user.id, reason, 'strike')
        strikes += 1

        staff_ban = strikes >= 3

        # Create embed
        embed = discord.Embed(
            title="🔴 Staff Sanction - Strike",
            color=0xFF0000 if not staff_ban else 0x8B0000,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Staff Member", value=f"{staff.mention}", inline=True)
        embed.add_field(name="Issued By", value=f"{interaction.user.mention}", inline=True)
        embed.add_field(name="Type", value="🔴 Strike", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)

        # Status
        status_emoji = self.get_status_emoji(warns, strikes)
        status_bar = f"{status_emoji} **Staff Status**\n"
        status_bar += f"Warnings: {self.create_status_bar(warns, 3)}\n"
        status_bar += f"Strikes: {self.create_status_bar(strikes, 3)}"
        embed.add_field(name="📊 Standing", value=status_bar, inline=False)

        if staff_ban:
            embed.add_field(
                name="🚨 3 STRIKES - STAFF BAN",
                value=f"{staff.mention} will be removed from staff for **7 days**.",
                inline=False
            )

        embed.set_thumbnail(url=staff.display_avatar. url)

        await interaction.response.send_message(embed=embed)

        # Log
        settings = await self.bot. db.get_settings(interaction. guild_id)
        log_id = settings.get('staff_sanctions_channel')
        if log_id and log_id != interaction.channel_id:
            log_channel = interaction.guild.get_channel(log_id)
            if log_channel:
                await send_log_embed(log_channel, embed)

        # Auto remove staff roles if 3 strikes
        if staff_ban and not is_bot_owner_id(staff.id): 
            staff_role_keys = ['admin_role', 'supervisor_role', 'senior_mod_role', 'mod_role', 'trial_mod_role', 'staff_role']
            for key in staff_role_keys: 
                role_id = settings.get(key)
                if role_id: 
                    role = interaction.guild. get_role(role_id)
                    if role and role in staff.roles:
                        try:
                            await staff.remove_roles(role, reason="3 strikes - 7 day staff ban")
                        except: 
                            pass

            ban_embed = discord.Embed(
                title="🚨 Staff Member Removed",
                description=f"{staff.mention} removed from staff for **7 days** (3 strikes).",
                color=0x8B0000
            )
            await interaction.followup.send(embed=ban_embed)

        # DM staff
        try: 
            dm_embed = discord. Embed(
                title="🔴 Staff Strike",
                description=f"You received a strike in **{interaction. guild.name}**",
                color=0xFF0000
            )
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            dm_embed.add_field(name="Warnings", value=f"{warns}/3", inline=True)
            dm_embed.add_field(name="Strikes", value=f"{strikes}/3", inline=True)
            if staff_ban:
                dm_embed.add_field(name="🚨 Notice", value="You have been removed from staff for 7 days.", inline=False)
            await staff.send(embed=dm_embed)
        except:
            pass

    @sanction_group. command(name="status", description="📊 View staff member's sanction status")
    @app_commands.describe(staff="Staff member to check")
    @is_supervisor()
    async def sanction_status(self, interaction: discord. Interaction, staff: discord.Member):
        warns, strikes = await self.get_sanction_counts(interaction.guild_id, staff.id)
        sanctions = await self.bot.db.get_staff_sanctions(interaction.guild_id, staff.id)

        embed = discord.Embed(
            title=f"📊 Staff Status - {staff.display_name}",
            color=Config.COLOR_INFO,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=staff.display_avatar.url)

        # Overall status
        embed.add_field(name="Status", value=self.get_status_text(warns, strikes), inline=False)

        # Bars
        bars = f"**Warnings:** {self.create_status_bar(warns, 3)}\n"
        bars += f"**Strikes:** {self.create_status_bar(strikes, 3)}"
        embed.add_field(name="📈 Progress", value=bars, inline=False)

        # Recent warnings
        warn_list = [s for s in sanctions if s['sanction_type'] == 'warn'][: 5]
        if warn_list:
            warn_text = "\n".join([f"• {w['reason'][: 50]}" for w in warn_list])
            embed.add_field(name=f"⚠️ Warnings ({warns})", value=warn_text, inline=False)

        # Recent strikes
        strike_list = [s for s in sanctions if s['sanction_type'] == 'strike'][:5]
        if strike_list:
            strike_text = "\n".join([f"• {s['reason'][:50]}" for s in strike_list])
            embed.add_field(name=f"🔴 Strikes ({strikes})", value=strike_text, inline=False)

        embed.add_field(name="ℹ️ Info", value="3 Warnings = 1 Strike\n3 Strikes = 7 Day Staff Ban", inline=False)

        await interaction.response.send_message(embed=embed)

    @sanction_group.command(name="history", description="📜 View full sanction history")
    @app_commands.describe(staff="Staff member")
    @is_supervisor()
    async def sanction_history(self, interaction: discord.Interaction, staff: discord.Member):
        sanctions = await self.bot. db.get_staff_sanctions(interaction.guild_id, staff. id)

        if not sanctions:
            return await interaction.response.send_message(
                embed=ModEmbed.info("Clean Record", f"{staff.mention} has no sanctions. "),
                ephemeral=True
            )

        warns = len([s for s in sanctions if s['sanction_type'] == 'warn'])
        strikes = len([s for s in sanctions if s['sanction_type'] == 'strike'])

        embed = discord. Embed(
            title=f"📜 Sanction History - {staff.display_name}",
            description=f"**Warnings:** {warns} | **Strikes:** {strikes}",
            color=Config.COLOR_INFO
        )
        embed.set_thumbnail(url=staff.display_avatar.url)

        for s in sanctions[: 15]: 
            issuer = interaction.guild.get_member(s['issuer_id'])
            issuer_name = issuer.display_name if issuer else "Unknown"
            type_emoji = "⚠️" if s['sanction_type'] == 'warn' else "🔴"

            embed.add_field(
                name=f"{type_emoji} {s['created_at'][:10]}",
                value=f"**Reason:** {s['reason'][:80]}\n**By:** {issuer_name}",
                inline=False
            )

        if len(sanctions) > 15:
            embed.set_footer(text=f"Showing 15 of {len(sanctions)}")

        await interaction.response. send_message(embed=embed)

    @sanction_group. command(name="clearwarns", description="🧹 Clear all warnings")
    @app_commands.describe(staff="Staff member", reason="Reason")
    @is_supervisor()
    async def sanction_clearwarns(self, interaction: discord.Interaction, staff: discord.Member, reason: str):
        count = await self.bot.db. clear_staff_warns(interaction. guild_id, staff.id)
        
        embed = ModEmbed. success("Warnings Cleared", f"Cleared **{count}** warnings from {staff.mention}\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)

        # Log
        settings = await self. bot.db.get_settings(interaction.guild_id)
        log_id = settings.get('staff_sanctions_channel')
        if log_id: 
            log_channel = interaction. guild.get_channel(log_id)
            if log_channel:
                log_embed = discord.Embed(
                    title="🧹 Warnings Cleared",
                    description=f"{staff.mention}'s warnings cleared by {interaction.user.mention}\n**Reason:** {reason}\n**Count:** {count}",
                    color=Config.COLOR_SUCCESS
                )
                await send_log_embed(log_channel, log_embed)

    @sanction_group.command(name="clearstrikes", description="🧹 Clear all strikes")
    @app_commands.describe(staff="Staff member", reason="Reason")
    @is_supervisor()
    async def sanction_clearstrikes(self, interaction: discord.Interaction, staff: discord. Member, reason: str):
        count = await self.bot.db.clear_staff_strikes(interaction.guild_id, staff.id)
        
        embed = ModEmbed.success("Strikes Cleared", f"Cleared **{count}** strikes from {staff. mention}\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)

        # Log
        settings = await self.bot.db. get_settings(interaction.guild_id)
        log_id = settings.get('staff_sanctions_channel')
        if log_id:
            log_channel = interaction.guild.get_channel(log_id)
            if log_channel:
                log_embed = discord.Embed(
                    title="🧹 Strikes Cleared",
                    description=f"{staff.mention}'s strikes cleared by {interaction.user.mention}\n**Reason:** {reason}\n**Count:** {count}",
                    color=Config. COLOR_SUCCESS
                )
                await send_log_embed(log_channel, log_embed)

    @sanction_group.command(name="clearall", description="🧹 Clear all sanctions")
    @app_commands.describe(staff="Staff member", reason="Reason")
    @is_supervisor()
    async def sanction_clearall(self, interaction: discord.Interaction, staff: discord.Member, reason: str):
        count = await self.bot.db.clear_staff_sanctions(interaction.guild_id, staff.id)
        
        embed = ModEmbed.success("Sanctions Cleared", f"Cleared **{count}** sanctions from {staff.mention}\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)

    @sanction_group.command(name="remove", description="🗑️ Remove specific sanction by ID")
    @app_commands.describe(sanction_id="Sanction ID", reason="Reason")
    @is_supervisor()
    async def sanction_remove(self, interaction:  discord.Interaction, sanction_id: int, reason: str):
        success = await self.bot.db. remove_staff_sanction(interaction.guild_id, sanction_id)

        if success:
            embed = ModEmbed.success("Removed", f"Sanction `{sanction_id}` removed.\n**Reason:** {reason}")
        else:
            embed = ModEmbed.error("Not Found", f"Sanction `{sanction_id}` not found.")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Staff(bot))
