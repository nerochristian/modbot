"""
Server setup command.

This setup flow is intentionally status-first. It shows what is configured,
offers an optional quickstart scaffold, and points admins to the web dashboard
for the rest of the server-wide tuning.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_admin
from utils.embeds import ModEmbed
from utils.server_setup import build_setup_summary, dashboard_setup_url, quickstart_server

logger = logging.getLogger(__name__)


class Setup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _section_lines(section: dict) -> str:
        lines = []
        for item in section.get("items", [])[:8]:
            icon = "OK" if item.get("configured") else "MISSING"
            label = str(item.get("label", "Item"))
            value = str(item.get("value") or "Not configured")
            lines.append(f"{icon} {label}: {value}")
        return "\n".join(lines) or "No items"

    def _build_status_embed(self, guild: discord.Guild, summary: dict) -> discord.Embed:
        percent = int(summary.get("percent", 0) or 0)
        complete = int(summary.get("complete", 0) or 0)
        total = int(summary.get("total", 0) or 0)

        if percent >= 90:
            color = discord.Color.green()
        elif percent >= 50:
            color = discord.Color.gold()
        else:
            color = discord.Color.orange()

        embed = discord.Embed(
            title="Server Setup",
            description=(
                f"Setup coverage for **{guild.name}**\n\n"
                f"**Progress:** `{percent}%` ({complete}/{total})\n"
                f"Run `/setup` to scaffold missing defaults, or use `/setup create_missing:false` for status only."
            ),
            color=color,
        )

        for section in summary.get("sections", [])[:4]:
            section_complete = int(section.get("complete", 0) or 0)
            section_total = int(section.get("total", 0) or 0)
            embed.add_field(
                name=f"{section.get('label', 'Section')} ({section_complete}/{section_total})",
                value=self._section_lines(section),
                inline=False,
            )

        if summary.get("setupComplete"):
            embed.set_footer(text="Setup has been marked complete for this server.")
        else:
            embed.set_footer(text="Setup is not complete yet.")

        return embed

    @staticmethod
    def _dashboard_view(guild_id: int) -> Optional[discord.ui.View]:
        url = dashboard_setup_url(guild_id)
        if not url:
            return None
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open Dashboard Setup", url=url))
        return view

    @app_commands.command(
        name="setup",
        description="Create missing baseline setup resources and show setup status",
    )
    @app_commands.describe(
        create_missing="Create missing baseline roles, categories, and channels. Disable this to only view status.",
    )
    @is_admin()
    async def setup_command(
        self,
        interaction: discord.Interaction,
        create_missing: bool = True,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                embed=ModEmbed.error("Server Only", "This command can only be used in a server."),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            settings = await self.bot.db.get_settings(guild.id)
            if create_missing:
                result = await quickstart_server(guild, settings)
                settings = result["settings"]
                settings["_version"] = int(settings.get("_version", 1) or 1) + 1
                settings["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                await self.bot.db.update_settings(guild.id, settings)

                summary = build_setup_summary(guild, settings, dashboard_url=dashboard_setup_url(guild.id))
                embed = self._build_status_embed(guild, summary)
                embed.description = (
                    f"Missing baseline resources were created where possible for **{guild.name}**.\n\n"
                    f"**Progress:** `{summary['percent']}%` ({summary['complete']}/{summary['total']})\n"
                    "Review the remaining items in the dashboard or rerun `/setup create_missing:false` for status only."
                )
                embed.add_field(
                    name="Created",
                    value=(
                        f"Roles: `{len(result.get('createdRoles', []))}`\n"
                        f"Channels/Categories: `{len(result.get('createdChannels', []))}`\n"
                        f"Reused Existing: `{len(result.get('reused', []))}`\n"
                        f"Verification Access Updates: `{int(result.get('permissionUpdates', 0) or 0)}`"
                    ),
                    inline=False,
                )
                if result.get("errors"):
                    embed.add_field(
                        name="Errors",
                        value="\n".join(str(item)[:150] for item in result["errors"][:5]),
                        inline=False,
                    )
                await interaction.followup.send(embed=embed, view=self._dashboard_view(guild.id), ephemeral=True)
                return

            summary = build_setup_summary(guild, settings, dashboard_url=dashboard_setup_url(guild.id))
            embed = self._build_status_embed(guild, summary)
            await interaction.followup.send(embed=embed, view=self._dashboard_view(guild.id), ephemeral=True)
        except Exception as exc:
            logger.exception("Setup command failed for guild %s", guild.id)
            await interaction.followup.send(
                embed=ModEmbed.error("Setup Failed", f"An error occurred while running setup: {exc}"),
                ephemeral=True,
            )

    @app_commands.command(
        name="staffupdates",
        description="Configure the public staff updates channel for promotions and demotions",
    )
    @app_commands.describe(channel="Channel used for public staff update posts")
    @is_admin()
    async def staffupdates(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["staff_updates_channel"] = channel.id
        settings["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        settings["_version"] = int(settings.get("_version", 1) or 1) + 1
        await self.bot.db.update_settings(interaction.guild_id, settings)

        embed = ModEmbed.success(
            "Staff Updates Configured",
            f"Promotion and demotion updates will be posted in {channel.mention}.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Setup(bot))
