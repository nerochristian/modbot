"""
Prefix Help Command - Shows all , prefix commands organized by category
"""

import discord
from discord.ext import commands
from typing import Optional
from datetime import datetime, timezone

from config import Config


# Command categories for the help system
COMMAND_CATEGORIES = {
    "🛡️ Moderation": [
        ("`warn`", "Warn a user", ["w"]),
        ("`kick`", "Kick a user", ["k"]),
        ("`ban`", "Ban a user", ["b"]),
        ("`unban`", "Unban a user by ID", []),
        ("`mute`", "Timeout a user", ["timeout", "to"]),
        ("`unmute`", "Remove timeout", ["untimeout", "uto"]),
        ("`tempban`", "Temporarily ban", ["tb"]),
        ("`softban`", "Ban and unban to clear msgs", ["sb"]),
        ("`purge`", "Delete messages", ["clear", "prune"]),
        ("`purgeuser`", "Delete user's messages", ["pu"]),
        ("`slowmode`", "Set slowmode", ["slow"]),
        ("`lock`", "Lock channel", ["lockdown"]),
        ("`unlock`", "Unlock channel", []),
        ("`nick`", "Change nickname", ["setnick"]),
        ("`strip`", "Remove all roles", ["removeallroles"]),
        ("`vcmute`", "VC server mute", ["vm"]),
        ("`vcunmute`", "VC server unmute", ["vum"]),
        ("`deafen`", "Deafen in VC", ["deaf"]),
        ("`undeafen`", "Undeafen in VC", ["undeaf"]),
        ("`vckick`", "Disconnect from VC", ["vk", "disconnect"]),
        ("`vcmove`", "Move to VC", ["vmove"]),
        ("`hide`", "Hide channel", []),
        ("`unhide`", "Show channel", ["show"]),
        ("`nuke`", "Nuke channel", []),
        ("`massban`", "Ban multiple users", ["mb"]),
        ("`note`", "Add note to user", ["addnote"]),
        ("`notes`", "View user notes", []),
        ("`clearwarns`", "Clear warnings", ["cw"]),
        ("`role`", "Toggle role on user", ["giverole", "addrole"]),
    ],
    "ℹ️ Information": [
        ("`userinfo`", "User information", ["ui", "whois"]),
        ("`serverinfo`", "Server information", ["si", "guildinfo"]),
        ("`avatar`", "User's avatar", ["av", "pfp"]),
        ("`banner`", "User's banner", []),
        ("`roleinfo`", "Role information", ["ri"]),
        ("`channelinfo`", "Channel info", ["ci"]),
        ("`ping`", "Bot latency", []),
        ("`uptime`", "Bot uptime", []),
        ("`invite`", "Bot invite link", []),
        ("`botinfo`", "Bot information", ["bi", "about"]),
        ("`members`", "Member count", ["membercount", "mc"]),
        ("`roles`", "List roles", []),
        ("`emojis`", "List emojis", ["emotes"]),
        ("`icon`", "Server icon", []),
        ("`stats`", "Bot stats", []),
    ],
    "🎉 Fun": [
        ("`say`", "Bot says message", ["echo"]),
        ("`embed`", "Send embed", []),
        ("`poll`", "Create poll", []),
        ("`coinflip`", "Flip a coin", ["flip", "coin"]),
        ("`roll`", "Roll dice", ["dice"]),
        ("`8ball`", "Magic 8ball", ["eightball"]),
        ("`snipe`", "Snipe deleted msg", []),
        ("`editsnipe`", "Snipe edited msg", ["esnipe"]),
        ("`afk`", "Set AFK status", []),
        ("`choose`", "Choose between options", ["pick"]),
    ],
    "👮 Staff": [
        ("`modstats`", "Moderator stats", ["ms"]),
        ("`cases`", "User's cases", []),
        ("`case`", "View specific case", []),
        ("`history`", "User mod history", ["h"]),
        ("`lookup`", "Lookup user by ID", []),
        ("`stafflist`", "List staff members", ["staff"]),
        ("`infractions`", "Infraction count", ["inf"]),
        ("`search`", "Search users", []),
        ("`modlog`", "Recent mod actions", []),
        ("`warnings`", "User's warnings", ["warns"]),
    ],
    "👑 Owner": [
        ("`guilds`", "List bot guilds", ["servers"]),
        ("`leave`", "Leave a guild", []),
        ("`shutdown`", "Shutdown bot", ["die"]),
        ("`reload`", "Reload a cog", ["rl"]),
        ("`load`", "Load a cog", []),
        ("`unload`", "Unload a cog", []),
        ("`sync`", "Sync commands", []),
        ("`debug`", "Debug info", []),
        ("`status`", "Set bot status", []),
        ("`dm`", "DM a user", []),
    ],
}


class PrefixHelpView(discord.ui.View):
    """Paginated help view for prefix commands"""
    
    def __init__(self, author_id: int, prefix: str = ","):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.prefix = prefix
        self.current_category = "overview"
        self.categories = list(COMMAND_CATEGORIES.keys())
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Not your help menu!", ephemeral=True)
            return False
        return True

    def build_overview_embed(self) -> discord.Embed:
        total = sum(len(cmds) for cmds in COMMAND_CATEGORIES.values())
        embed = discord.Embed(
            title="📖 Command Help",
            description=f"**{total}** commands available with `{self.prefix}` prefix.\nSelect a category below to view commands.",
            color=Config.COLOR_EMBED,
            timestamp=datetime.now(timezone.utc)
        )
        for cat, cmds in COMMAND_CATEGORIES.items():
            embed.add_field(name=cat, value=f"`{len(cmds)}` commands", inline=True)
        embed.set_footer(text=f"Prefix: {self.prefix} | Use dropdown to browse")
        return embed

    def build_category_embed(self, category: str) -> discord.Embed:
        cmds = COMMAND_CATEGORIES.get(category, [])
        lines = []
        for cmd, desc, aliases in cmds:
            alias_str = f" ({', '.join(aliases)})" if aliases else ""
            lines.append(f"{cmd}{alias_str} - {desc}")
        
        embed = discord.Embed(
            title=f"{category}",
            description="\n".join(lines) or "No commands",
            color=Config.COLOR_EMBED,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"Prefix: {self.prefix} | {len(cmds)} commands")
        return embed

    @discord.ui.select(
        placeholder="📁 Select Category...",
        options=[
            discord.SelectOption(label="Overview", value="overview", emoji="🏠"),
            discord.SelectOption(label="Moderation", value="🛡️ Moderation", emoji="🛡️"),
            discord.SelectOption(label="Information", value="ℹ️ Information", emoji="ℹ️"),
            discord.SelectOption(label="Fun", value="🎉 Fun", emoji="🎉"),
            discord.SelectOption(label="Staff", value="👮 Staff", emoji="👮"),
            discord.SelectOption(label="Owner", value="👑 Owner", emoji="👑"),
        ]
    )
    async def select_category(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.current_category = select.values[0]
        if self.current_category == "overview":
            embed = self.build_overview_embed()
        else:
            embed = self.build_category_embed(self.current_category)
        await interaction.response.edit_message(embed=embed, view=self)


class PrefixHelp(commands.Cog):
    """Help command for prefix commands"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["h", "commands", "cmds"])
    async def help_cmd(self, ctx, command: str = None):
        """Show all prefix commands"""
        prefix = ","
        
        # If specific command requested
        if command:
            # Search for command
            for cat, cmds in COMMAND_CATEGORIES.items():
                for cmd_name, desc, aliases in cmds:
                    clean_name = cmd_name.strip("`")
                    if command.lower() == clean_name or command.lower() in aliases:
                        embed = discord.Embed(
                            title=f"Command: {prefix}{clean_name}",
                            description=desc,
                            color=Config.COLOR_EMBED
                        )
                        if aliases:
                            embed.add_field(name="Aliases", value=", ".join([f"`{a}`" for a in aliases]))
                        embed.add_field(name="Category", value=cat)
                        embed.add_field(name="Usage", value=f"`{prefix}{clean_name}`")
                        return await ctx.send(embed=embed)
            
            return await ctx.send(embed=discord.Embed(
                title="❌ Not Found",
                description=f"Command `{command}` not found.",
                color=0xFF0000
            ))
        
        # Show full help menu
        view = PrefixHelpView(ctx.author.id, prefix)
        embed = view.build_overview_embed()
        view.message = await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(PrefixHelp(bot))
