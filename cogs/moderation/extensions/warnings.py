import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional

from utils.embeds import Colors, ModEmbed, compact_text, moderation_list_embed
from utils.checks import is_mod, is_bot_owner_id
from utils.warning_escalation import apply_warning_escalation, build_escalation_dm_embed
from utils.async_tasks import fire_and_forget

class WarningCommands:
    async def _warn_logic(self, source, user: discord.Member, reason: str):
        author = source.user if isinstance(source, discord.Interaction) else source.author
        can_mod, error = await self.can_moderate(
            source.guild.id,
            author,
            user,
            allow_protected_target=True,
        )
        if not can_mod:
            return await self._respond(source, embed=ModEmbed.error("Cannot Warn", error), ephemeral=True)

        settings = await self.bot.db.get_settings(source.guild.id)
        case_num = await self.bot.db.create_case(
            source.guild.id, user.id, author.id, "Warn", reason
        )

        # Record the warning BEFORE any DM so the moderator's confirmation
        # embed (and its "Total Warnings" count) reflects the authoritative
        # state. add_warning returns the new total, so we avoid the redundant
        # get_warnings re-read the old flow did.
        warning_id, warn_count = await self.bot.db.add_warning(
            source.guild.id, user.id, author.id, reason
        )

        # Confirm to the moderator immediately — the warning is recorded and
        # the case # is real. Everything below this point is side-effect.
        embed = await self.create_mod_embed(
            title="Member warned",
            user=user,
            moderator=author,
            reason=reason,
            color=Colors.WARNING,
            case_num=case_num,
            extra_fields={"Total Warnings": str(warn_count)},
        )
        await self._respond(source, embed=embed)
        await self.log_action(source.guild, embed)

        # Background the punishment DM + appeal-token transaction. A closed-DM
        # or appeal-token DB hiccup must never block or fail the warning, which
        # is already recorded above.
        if settings.get("moderation_dm_users", True):
            dm_embed = ModEmbed.punishment_notice(
                guild=source.guild,
                action="Warn",
                reason=reason,
                case_number=case_num,
                guidance=f"You now have **{warn_count}** active warning(s).",
            )
            fire_and_forget(
                self.send_punishment_notice(
                    guild=source.guild,
                    user=user,
                    action="Warn",
                    reason=reason,
                    case_number=case_num,
                    settings=settings,
                    fallback_embed=dm_embed,
                    moderator=author,
                ),
                name=f"warn-dm-{source.guild.id}-{user.id}",
            )

        # Apply only the highest escalation whose threshold this warning
        # crossed. The punishment (timeout/kick/ban) stays synchronous so the
        # moderator sees the auto-action outcome inline; only its DM is
        # backgrounded via skip_dm so it never delays the confirmation above.
        auto_action = None

        async def create_escalation_case(action: str, action_reason: str, duration_seconds: Optional[int]):
            duration = f"{duration_seconds // 60}m" if duration_seconds else None
            await self.bot.db.create_case(
                source.guild.id,
                user.id,
                self.bot.user.id,
                action,
                action_reason,
                duration,
            )

        try:
            escalation = await apply_warning_escalation(
                source.guild,
                user,
                settings,
                warn_count,
                previous_count=max(0, warn_count - 1),
                reason_prefix="Automatic warning escalation",
                ban_delete_days=1,
                create_case=create_escalation_case,
                skip_dm=True,
            )
            if escalation is not None:
                action_labels = {
                    "timeout": "Auto-timed out",
                    "kick": "Auto-kicked",
                    "ban": "Auto-banned",
                }
                duration = ""
                if escalation.rule.duration_seconds:
                    duration = f" for {escalation.rule.duration_seconds // 60}m"
                auto_action = (
                    f"**{action_labels[escalation.rule.action]}** {user.mention}{duration} "
                    f"— reached {warn_count} warnings"
                )
                # Background the escalation DM. The punishment already landed
                # synchronously; a closed-DM or slow send must not block the
                # moderator's already-delivered confirmation.
                if settings.get("moderation_dm_users", True):
                    escalation_dm_body = build_escalation_dm_embed(source.guild, escalation)
                    if escalation_dm_body:
                        async def _send_escalation_dm(
                            member: discord.Member, body: str
                        ) -> None:
                            try:
                                await member.send(body)
                            except (discord.Forbidden, discord.HTTPException):
                                pass

                        fire_and_forget(
                            _send_escalation_dm(user, escalation_dm_body),
                            name=f"warn-escalation-dm-{source.guild.id}-{user.id}",
                        )
        except discord.Forbidden:
            auto_action = f"Auto-punishment failed for {user.mention}: missing permissions"
        except discord.HTTPException as exc:
            auto_action = f"Auto-punishment failed for {user.mention}: {exc}"

        if auto_action:
            if "failed" in auto_action.casefold():
                auto_embed = ModEmbed.error("Automatic escalation failed", auto_action)
            else:
                auto_embed = ModEmbed.warning("Automatic escalation", auto_action)
            await self._respond(source, embed=auto_embed)

    async def _warnings_logic(self, source, user: discord.Member):
        warnings = await self.bot.db.get_warnings(source.guild.id, user.id)
        
        if not warnings:
            return await self._respond(source, embed=ModEmbed.info("No Warnings", f"{user.mention} has no warnings."), ephemeral=True)
        
        entries = []
        for warn in warnings[:10]:  # Limit to 10 most recent
            moderator = source.guild.get_member(warn['moderator_id'])
            mod_display = moderator.display_name if moderator else f"ID: {warn['moderator_id']}"
            timestamp = self._warning_timestamp(warn.get('created_at'))
            entries.append(
                f"**Warning #{warn['id']}** · {timestamp}\n"
                f"> {compact_text(warn.get('reason') or 'No reason provided', max_length=200)}\n"
                f"-# by {discord.utils.escape_markdown(mod_display)}"
            )

        shown = min(10, len(warnings))
        embed = moderation_list_embed(
            title=f"Warnings · {user.display_name}",
            color=Colors.WARNING,
            summary_rows=(("Active warnings", len(warnings)), ("Showing", f"Newest {shown}")),
            entries=entries,
            thumbnail_url=user.display_avatar.url,
            footer_text=f"Showing {shown} of {len(warnings)} warnings",
        )
        
        await self._respond(source, embed=embed)

    async def _delwarn_logic(self, source, warning_id: int):
        success = await self.bot.db.delete_warning(source.guild.id, warning_id)
        
        if success:
            embed = ModEmbed.success("Warning Deleted", f"Warning `#{warning_id}` has been removed.")
        else:
            embed = ModEmbed.error("Not Found", f"Warning `#{warning_id}` does not exist.")
        
        await self._respond(source, embed=embed, ephemeral=True)

    @staticmethod
    def _warning_timestamp(value: object) -> str:
        try:
            parsed = datetime.fromisoformat(str(value).replace(" ", "T"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return f"<t:{int(parsed.timestamp())}:R>"
        except (TypeError, ValueError, OverflowError):
            return "Unknown time"

    async def _clearwarnings_logic(self, source, user: discord.Member, reason: str):
        count = await self.bot.db.clear_warnings(source.guild.id, user.id)
        
        author = source.user if isinstance(source, discord.Interaction) else source.author
        embed = await self.create_mod_embed(
            title="Member warnings cleared",
            user=user,
            moderator=author,
            reason=reason,
            color=Colors.SUCCESS,
            extra_fields={"Warnings cleared": str(count)},
        )
        
        await self._respond(source, embed=embed)
        await self.log_action(source.guild, embed)

    # Commands
    @commands.command(name="warn", description="⚠️ Warn a user")
    @is_mod()
    async def mod_warn(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        await self._warn_logic(ctx, user, reason)

    # Slash command - registered dynamically in __init__.py
    async def warn_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        await self._warn_logic(interaction, user, reason)

    @commands.command(name="warnings", description="⚠️ View warnings for a user")
    @is_mod()
    async def mod_warnings(self, ctx: commands.Context, user: discord.Member):
        await self._warnings_logic(ctx, user)

    # Slash command - registered dynamically in __init__.py
    async def warnings_slash(self, interaction: discord.Interaction, user: discord.Member):
        await self._warnings_logic(interaction, user)

    @commands.command(name="delwarn", description="🗑️ Delete a warning")
    @is_mod()
    async def mod_delwarn(self, ctx: commands.Context, warning_id: int):
        await self._delwarn_logic(ctx, warning_id)

    # Slash command - registered dynamically in __init__.py
    async def delwarn_slash(self, interaction: discord.Interaction, warning_id: int):
        await self._delwarn_logic(interaction, warning_id)

    @commands.command(name="clearwarnings", description="🧹 Clear all warnings for a user")
    @is_mod()
    async def mod_clearwarnings(self, ctx: commands.Context, user: discord.Member, *, reason: str = "Cleared by moderator"):
        await self._clearwarnings_logic(ctx, user, reason)

    # Slash command - registered dynamically in __init__.py
    async def clearwarnings_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Cleared by moderator"):
        await self._clearwarnings_logic(interaction, user, reason)
