
"""
Staff System - Staff guide, rules, and staff sanctions (SUPERVISOR SYSTEM)
Consolidated into single commands with action parameters
Includes promote/demote functionality with staff updates
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
from utils.embeds import ModEmbed
from utils.checks import is_mod, is_admin, is_bot_owner_id
from utils.logging import send_log_embed
from config import Config


def is_supervisor():
    """Check if user has supervisor role or is admin/owner"""
    async def predicate(interaction: discord.Interaction):
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


async def check_supervisor(interaction: discord.Interaction) -> bool:
    """Check supervisor permission for consolidated commands"""
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

    async def is_staff_member(self, guild_id: int, member: discord.Member) -> bool:
        """Check if a member is a staff member"""
        settings = await self.bot.db.get_settings(guild_id)
        staff_role_keys = ['admin_role', 'supervisor_role', 'senior_mod_role', 'mod_role', 'trial_mod_role', 'staff_role']
        
        staff_roles = [settings.get(key) for key in staff_role_keys if settings.get(key)]
        user_role_ids = [r.id for r in member.roles]
        
        return any(role_id in user_role_ids for role_id in staff_roles)

    async def get_sanction_counts(self, guild_id: int, staff_id: int) -> tuple: 
        """Get warn and strike counts for a staff member"""
        sanctions = await self.bot.db.get_staff_sanctions(guild_id, staff_id)
        warns = len([s for s in sanctions if s['sanction_type'] == 'warn'])
        strikes = len([s for s in sanctions if s['sanction_type'] == 'strike'])
        return warns, strikes

    # ==================== CONSOLIDATED /rules COMMAND ====================
    
    @app_commands.command(name="rules", description="📜 Server rules management")
    @app_commands.describe(
        action="The action to perform",
        rule="Rule text (for add/edit)",
        rule_number="Rule number (for remove/edit)",
        channel="Channel to post in (for post)",
    )
    @is_admin()
    async def rules(
        self,
        interaction: discord.Interaction,
        action: Literal["post", "add", "remove", "edit", "list"],
        rule: Optional[str] = None,
        rule_number: Optional[int] = None,
        channel: Optional[discord.TextChannel] = None,
    ):
        if action == "post":
            await self._rules_post(interaction, channel)
        elif action == "add":
            await self._rules_add(interaction, rule)
        elif action == "remove":
            await self._rules_remove(interaction, rule_number)
        elif action == "edit":
            await self._rules_edit(interaction, rule_number, rule)
        elif action == "list":
            await self._rules_list(interaction)

    async def _rules_post(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel]):
        channel = channel or interaction.channel
        settings = await self.bot.db.get_settings(interaction.guild_id)
        rules = settings.get('server_rules', [])

        if not rules:
            return await interaction.response.send_message(
                embed=ModEmbed.error("No Rules", "No rules set. Use `/rules action:add` first."),
                ephemeral=True
            )

        embed = discord.Embed(
            title="📜 Server Rules",
            description="Please read and follow all rules!",
            color=Config.COLOR_EMBED,
            timestamp=datetime.now(timezone.utc)
        )

        rules_text = "\n\n".join([f"**{i}.** {rule}" for i, rule in enumerate(rules, 1)])
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

    async def _rules_add(self, interaction: discord.Interaction, rule: Optional[str]):
        if not rule:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify the `rule` text to add."),
                ephemeral=True
            )

        settings = await self.bot.db.get_settings(interaction.guild_id)
        rules = settings.get('server_rules', [])
        rules.append(rule)
        settings['server_rules'] = rules
        await self.bot.db.update_settings(interaction.guild_id, settings)

        await interaction.response.send_message(
            embed=ModEmbed.success("Rule Added", f"**Rule #{len(rules)}:** {rule}")
        )

    async def _rules_remove(self, interaction: discord.Interaction, rule_number: Optional[int]):
        if not rule_number:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify the `rule_number` to remove."),
                ephemeral=True
            )

        settings = await self.bot.db.get_settings(interaction.guild_id)
        rules = settings.get('server_rules', [])

        if rule_number < 1 or rule_number > len(rules):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Invalid Rule", f"Rule #{rule_number} doesn't exist."),
                ephemeral=True
            )

        removed = rules.pop(rule_number - 1)
        settings['server_rules'] = rules
        await self.bot.db.update_settings(interaction.guild_id, settings)

        await interaction.response.send_message(
            embed=ModEmbed.success("Rule Removed", f"Removed: {removed}")
        )

    async def _rules_edit(self, interaction: discord.Interaction, rule_number: Optional[int], new_rule: Optional[str]):
        if not rule_number or not new_rule:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Arguments", "Please specify both `rule_number` and `rule` text."),
                ephemeral=True
            )

        settings = await self.bot.db.get_settings(interaction.guild_id)
        rules = settings.get('server_rules', [])

        if rule_number < 1 or rule_number > len(rules):
            return await interaction.response.send_message(
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

    async def _rules_list(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        rules = settings.get('server_rules', [])

        if not rules: 
            return await interaction.response.send_message(
                embed=ModEmbed.info("No Rules", "No rules have been set."),
                ephemeral=True
            )

        embed = discord.Embed(title="📜 Server Rules", color=Config.COLOR_INFO)
        embed.description = "\n".join([f"**{i}.** {rule}" for i, rule in enumerate(rules, 1)])
        embed.set_footer(text=f"{len(rules)} rules total")

        await interaction.response.send_message(embed=embed)

    # ==================== CONSOLIDATED /staffguide COMMAND ====================
    
    @app_commands.command(name="staffguide", description="📚 Staff guide management")
    @app_commands.describe(
        action="The action to perform",
        message="Welcome message (for setwelcome)",
        title="Section title (for addsection)",
        content="Content separated by | (for addsection)",
        channel="Channel to post in (for post)",
    )
    @is_admin()
    async def staffguide(
        self,
        interaction: discord.Interaction,
        action: Literal["post", "setwelcome", "addsection"],
        message: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None,
    ):
        if action == "post":
            await self._staffguide_post(interaction, channel)
        elif action == "setwelcome":
            await self._staffguide_setwelcome(interaction, message)
        elif action == "addsection":
            await self._staffguide_addsection(interaction, title, content)

    async def _staffguide_post(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel]):
        channel = channel or interaction.channel
        settings = await self.bot.db.get_settings(interaction.guild_id)
        guide = settings.get('staff_guide', {})

        if not guide: 
            return await interaction.response.send_message(
                embed=ModEmbed.error("No Guide", "No staff guide configured."),
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        # Welcome
        welcome_embed = discord.Embed(
            title="📚 Staff Guide",
            description=guide.get('welcome', 'Welcome to the staff team!'),
            color=Config.COLOR_EMBED,
            timestamp=datetime.now(timezone.utc)
        )
        if interaction.guild.icon:
            welcome_embed.set_thumbnail(url=interaction.guild.icon.url)
        welcome_embed.set_footer(text=f"{interaction.guild.name} Staff Team")
        await channel.send(embed=welcome_embed)

        # Sections
        for section in guide.get('sections', []):
            section_embed = discord.Embed(
                title=section['title'],
                description="\n".join([f"• {item}" for item in section.get('content', [])]),
                color=Config.COLOR_INFO
            )
            await channel.send(embed=section_embed)

        # Supervisor System
        supervisor_embed = discord.Embed(
            title="👁️ Supervisor & Sanction System",
            color=0x9B59B6
        )
        supervisor_embed.add_field(
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
        commands_embed = discord.Embed(title="🤖 Staff Commands", color=Config.COLOR_MOD)
        commands_embed.add_field(
            name="Moderation",
            value="`/warn` `/kick` `/ban` `/mute`\n`/tempban` `/purge` `/lock`",
            inline=True
        )
        commands_embed.add_field(
            name="Supervisor Only",
            value="`/sanction action:warn`\n`/sanction action:strike`\n`/sanction action:status`\n`/promote` `/demote`",
            inline=True
        )
        await channel.send(embed=commands_embed)

        await interaction.followup.send(
            embed=ModEmbed.success("Staff Guide Posted", f"Posted in {channel.mention}"),
            ephemeral=True
        )

    async def _staffguide_setwelcome(self, interaction: discord.Interaction, message: Optional[str]):
        if not message:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify the `message` for the welcome."),
                ephemeral=True
            )

        settings = await self.bot.db.get_settings(interaction.guild_id)
        guide = settings.get('staff_guide', {'sections': []})
        guide['welcome'] = message
        settings['staff_guide'] = guide
        await self.bot.db.update_settings(interaction.guild_id, settings)

        await interaction.response.send_message(
            embed=ModEmbed.success("Welcome Updated", "Staff guide welcome updated.")
        )

    async def _staffguide_addsection(self, interaction: discord.Interaction, title: Optional[str], content: Optional[str]):
        if not title or not content:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Arguments", "Please specify both `title` and `content`."),
                ephemeral=True
            )

        settings = await self.bot.db.get_settings(interaction.guild_id)
        guide = settings.get('staff_guide', {'welcome': 'Welcome!', 'sections': []})

        items = [item.strip() for item in content.split('|') if item.strip()]
        guide['sections'].append({'title': title, 'content': items})

        settings['staff_guide'] = guide
        await self.bot.db.update_settings(interaction.guild_id, settings)

        await interaction.response.send_message(
            embed=ModEmbed.success("Section Added", f"Added **{title}** with {len(items)} items.")
        )

    # ==================== CONSOLIDATED /sanction COMMAND ====================
    
    @app_commands.command(name="sanction", description="⚖️ Staff sanctions (Supervisor only)")
    @app_commands.describe(
        action="The action to perform",
        staff="Target staff member",
        reason="Reason for the action",
        convert_warns="Convert 3 warnings to strike (for strike)",
        sanction_id="Sanction ID (for remove)",
    )
    async def sanction(
        self,
        interaction: discord.Interaction,
        action: Literal["warn", "strike", "status", "history", "clearwarns", "clearstrikes", "clearall", "remove"],
        staff: Optional[discord.Member] = None,
        reason: Optional[str] = None,
        convert_warns: Optional[bool] = False,
        sanction_id: Optional[int] = None,
    ):
        # Check supervisor permission
        if not await check_supervisor(interaction):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need supervisor permissions for this command."),
                ephemeral=True
            )

        if action == "warn":
            await self._sanction_warn(interaction, staff, reason)
        elif action == "strike":
            await self._sanction_strike(interaction, staff, reason, convert_warns)
        elif action == "status":
            await self._sanction_status(interaction, staff)
        elif action == "history":
            await self._sanction_history(interaction, staff)
        elif action == "clearwarns":
            await self._sanction_clearwarns(interaction, staff, reason)
        elif action == "clearstrikes":
            await self._sanction_clearstrikes(interaction, staff, reason)
        elif action == "clearall":
            await self._sanction_clearall(interaction, staff, reason)
        elif action == "remove":
            await self._sanction_remove(interaction, sanction_id, reason)

    async def _sanction_warn(self, interaction: discord.Interaction, staff: Optional[discord.Member], reason: Optional[str]):
        if not staff or not reason:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Arguments", "Please specify both `staff` and `reason`."),
                ephemeral=True
            )

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

        if staff.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", "You cannot sanction yourself."),
                ephemeral=True
            )

        warns, strikes = await self.get_sanction_counts(interaction.guild_id, staff.id)

        if warns >= 3:
            return await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Max Warnings",
                    f"{staff.mention} has **3 warnings**.\n"
                    f"Use `/sanction action:strike` or `/sanction action:clearwarns` first."
                ),
                ephemeral=True
            )

        await self.bot.db.add_staff_sanction(interaction.guild_id, staff.id, interaction.user.id, reason, 'warn')
        warns += 1

        embed = discord.Embed(
            title="⚠️ Staff Sanction - Warning",
            color=Config.COLOR_WARNING,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Staff Member", value=f"{staff.mention}", inline=True)
        embed.add_field(name="Issued By", value=f"{interaction.user.mention}", inline=True)
        embed.add_field(name="Type", value="⚠️ Warning", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)

        status_emoji = self.get_status_emoji(warns, strikes)
        status_bar = f"{status_emoji} **Staff Status**\n"
        status_bar += f"Warnings: {self.create_status_bar(warns, 3)}\n"
        status_bar += f"Strikes: {self.create_status_bar(strikes, 3)}"
        embed.add_field(name="📊 Standing", value=status_bar, inline=False)

        if warns >= 3:
            embed.add_field(
                name="⚠️ Threshold Reached",
                value="3 warnings reached! Next sanction should be a strike.",
                inline=False
            )

        embed.set_thumbnail(url=staff.display_avatar.url)

        await interaction.response.send_message(embed=embed)

        settings = await self.bot.db.get_settings(interaction.guild_id)
        log_id = settings.get('staff_sanctions_channel')
        if log_id and log_id != interaction.channel_id:
            log_channel = interaction.guild.get_channel(log_id)
            if log_channel:
                await send_log_embed(log_channel, embed)

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

    async def _sanction_strike(self, interaction: discord.Interaction, staff: Optional[discord.Member], reason: Optional[str], convert_warns: Optional[bool]):
        if not staff or not reason:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Arguments", "Please specify both `staff` and `reason`."),
                ephemeral=True
            )

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

        if staff.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", "You cannot sanction yourself."),
                ephemeral=True
            )

        warns, strikes = await self.get_sanction_counts(interaction.guild_id, staff.id)

        if convert_warns and warns >= 3:
            await self.bot.db.clear_staff_warns(interaction.guild_id, staff.id)
            warns = 0
            reason = f"[Converted from 3 warnings] {reason}"

        await self.bot.db.add_staff_sanction(interaction.guild_id, staff.id, interaction.user.id, reason, 'strike')
        strikes += 1

        staff_ban = strikes >= 3

        embed = discord.Embed(
            title="🔴 Staff Sanction - Strike",
            color=0xFF0000 if not staff_ban else 0x8B0000,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Staff Member", value=f"{staff.mention}", inline=True)
        embed.add_field(name="Issued By", value=f"{interaction.user.mention}", inline=True)
        embed.add_field(name="Type", value="🔴 Strike", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)

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

        embed.set_thumbnail(url=staff.display_avatar.url)

        await interaction.response.send_message(embed=embed)

        settings = await self.bot.db.get_settings(interaction.guild_id)
        log_id = settings.get('staff_sanctions_channel')
        if log_id and log_id != interaction.channel_id:
            log_channel = interaction.guild.get_channel(log_id)
            if log_channel:
                await send_log_embed(log_channel, embed)

        if staff_ban and not is_bot_owner_id(staff.id): 
            staff_role_keys = ['admin_role', 'supervisor_role', 'senior_mod_role', 'mod_role', 'trial_mod_role', 'staff_role']
            for key in staff_role_keys: 
                role_id = settings.get(key)
                if role_id: 
                    role = interaction.guild.get_role(role_id)
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

        try: 
            dm_embed = discord.Embed(
                title="🔴 Staff Strike",
                description=f"You received a strike in **{interaction.guild.name}**",
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

    async def _sanction_status(self, interaction: discord.Interaction, staff: Optional[discord.Member]):
        if not staff:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `staff` member."),
                ephemeral=True
            )

        warns, strikes = await self.get_sanction_counts(interaction.guild_id, staff.id)
        sanctions = await self.bot.db.get_staff_sanctions(interaction.guild_id, staff.id)

        embed = discord.Embed(
            title=f"📊 Staff Status - {staff.display_name}",
            color=Config.COLOR_INFO,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=staff.display_avatar.url)

        embed.add_field(name="Status", value=self.get_status_text(warns, strikes), inline=False)

        bars = f"**Warnings:** {self.create_status_bar(warns, 3)}\n"
        bars += f"**Strikes:** {self.create_status_bar(strikes, 3)}"
        embed.add_field(name="📈 Progress", value=bars, inline=False)

        warn_list = [s for s in sanctions if s['sanction_type'] == 'warn'][:5]
        if warn_list:
            warn_text = "\n".join([f"• {w['reason'][:50]}" for w in warn_list])
            embed.add_field(name=f"⚠️ Warnings ({warns})", value=warn_text, inline=False)

        strike_list = [s for s in sanctions if s['sanction_type'] == 'strike'][:5]
        if strike_list:
            strike_text = "\n".join([f"• {s['reason'][:50]}" for s in strike_list])
            embed.add_field(name=f"🔴 Strikes ({strikes})", value=strike_text, inline=False)

        embed.add_field(name="ℹ️ Info", value="3 Warnings = 1 Strike\n3 Strikes = 7 Day Staff Ban", inline=False)

        await interaction.response.send_message(embed=embed)

    async def _sanction_history(self, interaction: discord.Interaction, staff: Optional[discord.Member]):
        if not staff:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Argument", "Please specify a `staff` member."),
                ephemeral=True
            )

        sanctions = await self.bot.db.get_staff_sanctions(interaction.guild_id, staff.id)

        if not sanctions:
            return await interaction.response.send_message(
                embed=ModEmbed.info("Clean Record", f"{staff.mention} has no sanctions."),
                ephemeral=True
            )

        warns = len([s for s in sanctions if s['sanction_type'] == 'warn'])
        strikes = len([s for s in sanctions if s['sanction_type'] == 'strike'])

        embed = discord.Embed(
            title=f"📜 Sanction History - {staff.display_name}",
            description=f"**Warnings:** {warns} | **Strikes:** {strikes}",
            color=Config.COLOR_INFO
        )
        embed.set_thumbnail(url=staff.display_avatar.url)

        for s in sanctions[:15]:
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

        await interaction.response.send_message(embed=embed)

    async def _sanction_clearwarns(self, interaction: discord.Interaction, staff: Optional[discord.Member], reason: Optional[str]):
        if not staff or not reason:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Arguments", "Please specify both `staff` and `reason`."),
                ephemeral=True
            )

        count = await self.bot.db.clear_staff_warns(interaction.guild_id, staff.id)
        
        embed = ModEmbed.success("Warnings Cleared", f"Cleared **{count}** warnings from {staff.mention}\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)

        settings = await self.bot.db.get_settings(interaction.guild_id)
        log_id = settings.get('staff_sanctions_channel')
        if log_id:
            log_channel = interaction.guild.get_channel(log_id)
            if log_channel:
                log_embed = discord.Embed(
                    title="🧹 Warnings Cleared",
                    description=f"{staff.mention}'s warnings cleared by {interaction.user.mention}\n**Reason:** {reason}\n**Count:** {count}",
                    color=Config.COLOR_SUCCESS
                )
                await send_log_embed(log_channel, log_embed)

    async def _sanction_clearstrikes(self, interaction: discord.Interaction, staff: Optional[discord.Member], reason: Optional[str]):
        if not staff or not reason:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Arguments", "Please specify both `staff` and `reason`."),
                ephemeral=True
            )

        count = await self.bot.db.clear_staff_strikes(interaction.guild_id, staff.id)
        
        embed = ModEmbed.success("Strikes Cleared", f"Cleared **{count}** strikes from {staff.mention}\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)

        settings = await self.bot.db.get_settings(interaction.guild_id)
        log_id = settings.get('staff_sanctions_channel')
        if log_id:
            log_channel = interaction.guild.get_channel(log_id)
            if log_channel:
                log_embed = discord.Embed(
                    title="🧹 Strikes Cleared",
                    description=f"{staff.mention}'s strikes cleared by {interaction.user.mention}\n**Reason:** {reason}\n**Count:** {count}",
                    color=Config.COLOR_SUCCESS
                )
                await send_log_embed(log_channel, log_embed)

    async def _sanction_clearall(self, interaction: discord.Interaction, staff: Optional[discord.Member], reason: Optional[str]):
        if not staff or not reason:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Arguments", "Please specify both `staff` and `reason`."),
                ephemeral=True
            )

        count = await self.bot.db.clear_staff_sanctions(interaction.guild_id, staff.id)
        
        embed = ModEmbed.success("Sanctions Cleared", f"Cleared **{count}** sanctions from {staff.mention}\n**Reason:** {reason}")
        await interaction.response.send_message(embed=embed)

    async def _sanction_remove(self, interaction: discord.Interaction, sanction_id: Optional[int], reason: Optional[str]):
        if not sanction_id or not reason:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Missing Arguments", "Please specify both `sanction_id` and `reason`."),
                ephemeral=True
            )

        success = await self.bot.db.remove_staff_sanction(interaction.guild_id, sanction_id)

        if success:
            embed = ModEmbed.success("Removed", f"Sanction `{sanction_id}` removed.\n**Reason:** {reason}")
        else:
            embed = ModEmbed.error("Not Found", f"Sanction `{sanction_id}` not found.")

        await interaction.response.send_message(embed=embed)

    # ==================== PROMOTE/DEMOTE COMMANDS ====================
    
    @app_commands.command(name="promote", description="👆 Promote a staff member to a higher role")
    @app_commands.describe(
        member="The staff member to promote",
        role="Optional: Specific role to promote to (must be higher than current)"
    )
    async def promote(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: Optional[discord.Role] = None
    ):
        """Promote a staff member up one rank or to a specific role"""
        # Check supervisor permission
        if not await check_supervisor(interaction):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need supervisor permissions for this command."),
                ephemeral=True
            )
        
        # Can't promote yourself
        if member.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", "You cannot promote yourself."),
                ephemeral=True
            )
        
        # Can't promote bots
        if member.bot:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", "You cannot promote bots."),
                ephemeral=True
            )
        
        settings = await self.bot.db.get_settings(interaction.guild_id)
        
        # Define staff hierarchy (lowest to highest)
        staff_hierarchy = [
            ('staff_role', '⭐ Staff'),
            ('trial_mod_role', '🔰 Trial Moderator'),
            ('mod_role', '🛡️ Moderator'),
            ('senior_mod_role', '⚔️ Senior Moderator'),
            ('supervisor_role', '👁️ Supervisor'),
            ('admin_role', '👑 Admin'),
        ]
        
        # Find current staff role
        current_role = None
        current_index = -1
        member_role_ids = [r.id for r in member.roles]
        
        for idx, (key, name) in enumerate(staff_hierarchy):
            role_id = settings.get(key)
            if role_id and role_id in member_role_ids:
                current_role = interaction.guild.get_role(role_id)
                current_index = idx
                break
        
        if current_role is None:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Staff", f"{member.mention} is not a staff member."),
                ephemeral=True
            )
        
        # Determine target role
        if role:
            # Custom role specified
            target_role = role
            target_role_name = role.name
            
            # Verify it's a staff role and higher than current
            target_index = -1
            for idx, (key, name) in enumerate(staff_hierarchy):
                role_id = settings.get(key)
                if role_id == role.id:
                    target_index = idx
                    target_role_name = name
                    break
            
            if target_index == -1:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Invalid Role", "The specified role is not a staff role."),
                    ephemeral=True
                )
            
            if target_index <= current_index:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Invalid Promotion", "The specified role must be higher than the member's current role."),
                    ephemeral=True
                )
        else:
            # Promote to next rank
            if current_index >= len(staff_hierarchy) - 1:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Max Rank", f"{member.mention} is already at the highest staff rank."),
                    ephemeral=True
                )
            
            next_key, target_role_name = staff_hierarchy[current_index + 1]
            next_role_id = settings.get(next_key)
            
            if not next_role_id:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Role Not Found", f"The next rank role ({target_role_name}) is not configured."),
                    ephemeral=True
                )
            
            target_role = interaction.guild.get_role(next_role_id)
            if not target_role:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Role Not Found", f"The role for {target_role_name} no longer exists."),
                    ephemeral=True
                )
        
        # Perform the promotion
        try:
            await member.remove_roles(current_role, reason=f"Promoted by {interaction.user}")
            await member.add_roles(target_role, reason=f"Promoted by {interaction.user}")
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Error", "I don't have permission to manage these roles."),
                ephemeral=True
            )
        except Exception as e:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", f"Failed to promote member: {e}"),
                ephemeral=True
            )
        
        # Send confirmation
        await interaction.response.send_message(
            embed=ModEmbed.success(
                "Staff Promoted",
                f"{member.mention} has been promoted from **{current_role.name}** to **{target_role.name}**"
            )
        )
        
        # Send public announcement
        staff_updates_channel_id = settings.get('staff_updates_channel')
        channel = None
        
        if staff_updates_channel_id:
            channel = interaction.guild.get_channel(staff_updates_channel_id)
            
        # Fallback: Search by name
        if not channel:
            channel = discord.utils.get(interaction.guild.text_channels, name="staff-updates")
            if channel:
                # Save it for next time
                settings['staff_updates_channel'] = channel.id
                await self.bot.db.update_settings(interaction.guild_id, settings)

        if channel:
            try:
                msg = await channel.send(
                    f"Congratulations {member.mention}, you have been promoted from **{current_role.name}** to **{target_role.name}**!"
                )
                await msg.add_reaction("🎉")
            except Exception as e:
                await interaction.followup.send(
                    embed=ModEmbed.error("Logging Failed", f"Promotion successful, but failed to log to {channel.mention}: {e}"),
                    ephemeral=True
                )
        else:
             await interaction.followup.send(
                embed=ModEmbed.warning("Logging Warning", "Promotion successful, but no `staff-updates` channel found."),
                ephemeral=True
            )
    
    @app_commands.command(name="demote", description="👇 Demote a staff member to a lower role")
    @app_commands.describe(
        member="The staff member to demote",
        role="Optional: Specific role to demote to (must be lower than current)"
    )
    async def demote(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: Optional[discord.Role] = None
    ):
        """Demote a staff member down one rank or to a specific role"""
        # Check supervisor permission
        if not await check_supervisor(interaction):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Denied", "You need supervisor permissions for this command."),
                ephemeral=True
            )
        
        # Can't demote yourself
        if member.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", "You cannot demote yourself."),
                ephemeral=True
            )
        
        # Can't demote bots
        if member.bot:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", "You cannot demote bots."),
                ephemeral=True
            )
        
        settings = await self.bot.db.get_settings(interaction.guild_id)
        
        # Define staff hierarchy (lowest to highest)
        staff_hierarchy = [
            ('staff_role', '⭐ Staff'),
            ('trial_mod_role', '🔰 Trial Moderator'),
            ('mod_role', '🛡️ Moderator'),
            ('senior_mod_role', '⚔️ Senior Moderator'),
            ('supervisor_role', '👁️ Supervisor'),
            ('admin_role', '👑 Admin'),
        ]
        
        # Find current staff role
        current_role = None
        current_index = -1
        member_role_ids = [r.id for r in member.roles]
        
        for idx, (key, name) in enumerate(staff_hierarchy):
            role_id = settings.get(key)
            if role_id and role_id in member_role_ids:
                current_role = interaction.guild.get_role(role_id)
                current_index = idx
                break
        
        if current_role is None:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Staff", f"{member.mention} is not a staff member."),
                ephemeral=True
            )
        
        # Determine target role
        if role:
            # Custom role specified
            target_role = role
            target_role_name = role.name
            
            # Verify it's a staff role and lower than current
            target_index = -1
            for idx, (key, name) in enumerate(staff_hierarchy):
                role_id = settings.get(key)
                if role_id == role.id:
                    target_index = idx
                    target_role_name = name
                    break
            
            if target_index == -1:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Invalid Role", "The specified role is not a staff role."),
                    ephemeral=True
                )
            
            if target_index >= current_index:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Invalid Demotion", "The specified role must be lower than the member's current role."),
                    ephemeral=True
                )
        else:
            # Demote to previous rank
            if current_index <= 0:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Min Rank", f"{member.mention} is already at the lowest staff rank."),
                    ephemeral=True
                )
            
            prev_key, target_role_name = staff_hierarchy[current_index - 1]
            prev_role_id = settings.get(prev_key)
            
            if not prev_role_id:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Role Not Found", f"The previous rank role ({target_role_name}) is not configured."),
                    ephemeral=True
                )
            
            target_role = interaction.guild.get_role(prev_role_id)
            if not target_role:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Role Not Found", f"The role for {target_role_name} no longer exists."),
                    ephemeral=True
                )
        
        # Perform the demotion
        try:
            await member.remove_roles(current_role, reason=f"Demoted by {interaction.user}")
            await member.add_roles(target_role, reason=f"Demoted by {interaction.user}")
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Permission Error", "I don't have permission to manage these roles."),
                ephemeral=True
            )
        except Exception as e:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Error", f"Failed to demote member: {e}"),
                ephemeral=True
            )
        
        # Send confirmation
        await interaction.response.send_message(
            embed=ModEmbed.success(
                "Staff Demoted",
                f"{member.mention} has been demoted from **{current_role.name}** to **{target_role.name}**"
            )
        )
        
        # Send public announcement
        staff_updates_channel_id = settings.get('staff_updates_channel')
        channel = None
        
        if staff_updates_channel_id:
            channel = interaction.guild.get_channel(staff_updates_channel_id)

        # Fallback: Search by name
        if not channel:
            channel = discord.utils.get(interaction.guild.text_channels, name="staff-updates")
            if channel:
                # Save it for next time
                settings['staff_updates_channel'] = channel.id
                await self.bot.db.update_settings(interaction.guild_id, settings)

        if channel:
            try:
                msg = await channel.send(
                    f"{member.mention}, you have been demoted from **{current_role.name}** to **{target_role.name}**."
                )
                await msg.add_reaction("🫡")
            except Exception as e:
                 await interaction.followup.send(
                    embed=ModEmbed.error("Logging Failed", f"Demotion successful, but failed to log to {channel.mention}: {e}"),
                    ephemeral=True
                )
        else:
            await interaction.followup.send(
                embed=ModEmbed.warning("Logging Warning", "Demotion successful, but no `staff-updates` channel found."),
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Staff(bot))
