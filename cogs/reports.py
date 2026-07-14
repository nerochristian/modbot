"""Member reporting and staff review commands."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import Config
from utils.checks import is_mod
from utils.embeds import ModEmbed
from utils.logging import send_log_embed


class Reports(commands.Cog):
    """Let every member file a report while keeping review tools staff-only."""

    reports_group = app_commands.Group(name="reports", description="Review member reports")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _report_channel(guild: discord.Guild, settings: dict) -> Optional[discord.TextChannel]:
        channel_id = (
            settings.get("report_log_channel")
            or settings.get("mod_log_channel")
            or settings.get("audit_log_channel")
            or settings.get("log_channel_report")
            or settings.get("log_channel_mod")
        )
        try:
            channel = guild.get_channel(int(channel_id))
        except (TypeError, ValueError):
            return None
        return channel if isinstance(channel, discord.TextChannel) else None

    @app_commands.command(name="report", description="Privately report a member to the server staff")
    @app_commands.describe(
        member="Member you are reporting",
        reason="What happened",
        evidence="Optional message link or evidence URL",
    )
    async def report(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
        evidence: Optional[str] = None,
    ) -> None:
        if interaction.guild is None or interaction.guild_id is None:
            await interaction.response.send_message("Reports can only be filed in a server.", ephemeral=True)
            return
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                embed=ModEmbed.error("Report not filed", "You cannot report yourself."),
                ephemeral=True,
            )
            return
        if member.bot:
            await interaction.response.send_message(
                embed=ModEmbed.error("Report not filed", "Bots cannot be submitted as member reports."),
                ephemeral=True,
            )
            return

        clean_reason = " ".join(reason.split()).strip()
        if len(clean_reason) < 5:
            await interaction.response.send_message(
                embed=ModEmbed.error("Add more detail", "Give staff at least five characters explaining what happened."),
                ephemeral=True,
            )
            return
        clean_evidence = (evidence or "").strip()
        stored_reason = clean_reason[:1500]
        if clean_evidence:
            stored_reason = f"{stored_reason}\nEvidence: {clean_evidence[:500]}"

        report_id = await self.bot.db.create_report(
            interaction.guild_id,
            interaction.user.id,
            member.id,
            stored_reason,
        )
        settings = await self.bot.db.get_settings(interaction.guild_id)
        channel = self._report_channel(interaction.guild, settings)
        if channel is not None:
            embed = discord.Embed(
                title=f"Member report #{report_id}",
                description=clean_reason[:4000],
                color=Config.COLOR_WARNING,
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="Reported member", value=f"{member.mention}\n`{member.id}`", inline=True)
            embed.add_field(name="Submitted by", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=True)
            if clean_evidence:
                embed.add_field(name="Evidence", value=clean_evidence[:1024], inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Report #{report_id} · Review in the Docket dashboard or /reports resolve")
            await send_log_embed(channel, embed, bot=self.bot)

        await interaction.response.send_message(
            embed=ModEmbed.success(
                "Report submitted",
                f"Staff received report **#{report_id}** about {member.mention}. Your submission is private.",
            ),
            ephemeral=True,
        )

    @reports_group.command(name="list", description="List unresolved member reports")
    @app_commands.describe(member="Optionally show reports for one member")
    @is_mod()
    async def list_reports(
        self,
        interaction: discord.Interaction,
        member: Optional[discord.Member] = None,
    ) -> None:
        if interaction.guild is None or interaction.guild_id is None:
            return
        reports = await self.bot.db.get_reports(
            interaction.guild_id,
            member.id if member else None,
            resolved=None if member else False,
        )
        if not reports:
            await interaction.response.send_message(
                embed=ModEmbed.info("No reports", "There are no matching member reports."),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"Reports for {member}" if member else "Unresolved member reports",
            color=Config.COLOR_INFO,
        )
        for report in reports[:10]:
            reported = interaction.guild.get_member(report["reported_id"])
            target = reported.mention if reported else f"`{report['reported_id']}`"
            status = "Resolved" if report["resolved"] else "Needs review"
            embed.add_field(
                name=f"#{report['id']} · {status}",
                value=f"**Member:** {target}\n{str(report['reason'])[:700]}",
                inline=False,
            )
        if len(reports) > 10:
            embed.set_footer(text=f"Showing 10 of {len(reports)} · Open the dashboard for the full queue")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @reports_group.command(name="resolve", description="Resolve a member report")
    @app_commands.describe(report_id="Report number")
    @is_mod()
    async def resolve_report(self, interaction: discord.Interaction, report_id: int) -> None:
        if interaction.guild is None or interaction.guild_id is None:
            return
        resolved = await self.bot.db.resolve_report(interaction.guild_id, report_id, interaction.user.id)
        if not resolved:
            await interaction.response.send_message(
                embed=ModEmbed.error("Report not found", f"Report #{report_id} does not exist in this server."),
                ephemeral=True,
            )
            return
        settings = await self.bot.db.get_settings(interaction.guild_id)
        channel = self._report_channel(interaction.guild, settings)
        if channel is not None:
            embed = discord.Embed(
                title=f"Report #{report_id} resolved",
                description=f"Resolved by {interaction.user.mention}.",
                color=Config.COLOR_SUCCESS,
                timestamp=datetime.now(timezone.utc),
            )
            await send_log_embed(channel, embed, bot=self.bot)
        await interaction.response.send_message(
            embed=ModEmbed.success("Report resolved", f"Report #{report_id} is now resolved."),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Reports(bot))
