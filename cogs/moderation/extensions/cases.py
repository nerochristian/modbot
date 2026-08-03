import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional

from utils.embeds import (
    Colors,
    ModEmbed,
    compact_kv_lines,
    compact_text,
    moderation_list_embed,
    sapphire_log_embed,
)
from utils.checks import is_mod

class CaseCommands:
    async def _case_logic(self, source, case_number: int):
        guild_id = source.guild.id
        case = await self.bot.db.get_case(guild_id, case_number)
        
        if not case:
            return await self._respond(source, embed=ModEmbed.error("Not Found", f"Case #{case_number} does not exist."))
        
        try:
            user = await self.bot.fetch_user(case['user_id'])
            moderator = await self.bot.fetch_user(case['moderator_id'])
        except discord.NotFound:
            user = f"Unknown User ({case['user_id']})"
            moderator = f"Unknown Moderator ({case['moderator_id']})"
        
        details = [
            ("User", user.mention if hasattr(user, "mention") else user),
            ("Moderator", moderator.mention if hasattr(moderator, "mention") else moderator),
            ("Reason", case.get("reason") or "No reason provided"),
        ]
        if case.get("duration"):
            details.append(("Duration", case["duration"]))
        created_at = self._parse_log_timestamp(case.get("created_at"))
        if created_at != self._unknown_timestamp():
            details.append(("Created", f"<t:{int(created_at.timestamp())}:R>"))

        embed = sapphire_log_embed(
            title=f"Case #{case['case_number']} · {case['action']}",
            color=Colors.MOD,
            detail_lines=compact_kv_lines(details).splitlines(),
            thumbnail_url=getattr(getattr(user, "display_avatar", None), "url", None),
        )
        
        await self._respond(source, embed=embed)

    async def _editcase_logic(self, source, case_number: int, reason: str):
        guild_id = source.guild.id
        case = await self.bot.db.get_case(guild_id, case_number)
        
        if not case:
             return await self._respond(source, embed=ModEmbed.error("Not Found", f"Case #{case_number} does not exist."))
        
        await self.bot.db.update_case(guild_id, case_number, reason)
        
        embed = ModEmbed.success(
            "Case Updated",
            f"Case #{case_number} reason has been updated to:\n`{reason}`"
        )
        
        await self._respond(source, embed=embed)

    async def _history_logic(self, source, user: discord.Member):
        guild = source.guild
        cases = await self.bot.db.get_user_cases(guild.id, user.id)
        
        if not cases:
             return await self._respond(source, embed=ModEmbed.info("No History", f"{user.mention} has no moderation history."))
        
        entries = []
        for case in cases[:10]:
            moderator = guild.get_member(case['moderator_id'])
            mod_display = moderator.display_name if moderator else f"ID: {case['moderator_id']}"
            created_at = self._parse_log_timestamp(case.get("created_at"))
            when = (
                f" · <t:{int(created_at.timestamp())}:R>"
                if created_at != self._unknown_timestamp()
                else ""
            )
            entries.append(
                f"**Case #{case['case_number']} · {case['action']}**{when}\n"
                f"> {compact_text(case.get('reason') or 'No reason provided', max_length=180)}\n"
                f"-# by {discord.utils.escape_markdown(mod_display)}"
            )

        shown = min(10, len(cases))
        embed = moderation_list_embed(
            title=f"Moderation history · {user.display_name}",
            color=Colors.MOD,
            summary_rows=(("Cases", len(cases)), ("Showing", f"Newest {shown}")),
            entries=entries,
            thumbnail_url=user.display_avatar.url,
            footer_text=f"Showing {shown} of {len(cases)} cases",
        )
        
        await self._respond(source, embed=embed)

    async def _modlogs_logic(self, source, user: discord.Member):
        if isinstance(source, discord.Interaction):
            await source.response.defer()
        else:
            await source.typing()
        
        guild = source.guild
        guild_id = guild.id
        
        # Fetch all data concurrently
        cases = await self.bot.db.get_user_cases(guild_id, user.id)
        warnings = await self.bot.db.get_warnings(guild_id, user.id)
        notes = await self.bot.db.get_notes(guild_id, user.id)
        
        all_logs = []
        
        # Process Cases
        for c in cases:
            all_logs.append({
                'type': 'case',
                'action': c['action'],
                'reason': c['reason'],
                'mod_id': c['moderator_id'],
                'timestamp': str(c['created_at']), # Ensure string for parsing
                'id': c['case_number']
            })
            
        # Process Warnings
        for w in warnings:
             all_logs.append({
                'type': 'warn',
                'action': 'Warning',
                'reason': w['reason'],
                'mod_id': w['moderator_id'],
                'timestamp': str(w['created_at']),
                'id': w['id']
            })
             
        # Process Notes
        for n in notes:
             all_logs.append({
                'type': 'note',
                'action': 'Note',
                'reason': n['note'],
                'mod_id': n['moderator_id'],
                'timestamp': str(n['created_at']),
                'id': n['id']
            })
        
        if not all_logs:
             return await self._respond(source, embed=ModEmbed.info("No Logs", f"{user.mention} has no moderation logs."))
            
        # Sort by timestamp (newest first)
        def parse_ts(x):
            return self._parse_log_timestamp(x.get('timestamp'))

        all_logs.sort(key=parse_ts, reverse=True)
        
        entries = []
        for log in all_logs[:15]:
            ts_obj = parse_ts(log)
            time_str = f"<t:{int(ts_obj.timestamp())}:R>" if ts_obj != self._unknown_timestamp() else "Unknown"
            mod_user = guild.get_member(log['mod_id'])
            mod_name = mod_user.name if mod_user else f"ID:{log['mod_id']}"
            label = log['action'].title()
            if log['type'] == 'case':
                label += f" · Case #{log['id']}"
            elif log.get('id') is not None:
                label += f" · #{log['id']}"
            entries.append(
                f"**{label}** · {time_str}\n"
                f"> {compact_text(log.get('reason') or 'No reason provided', max_length=150)}\n"
                f"-# by {discord.utils.escape_markdown(mod_name)}"
            )

        shown = min(15, len(all_logs))
        embed = moderation_list_embed(
            title=f"Moderation activity · {user.display_name}",
            color=Colors.MOD,
            summary_rows=(("Entries", len(all_logs)), ("Showing", f"Newest {shown}")),
            entries=entries,
            thumbnail_url=user.display_avatar.url,
            footer_text=f"Showing {shown} of {len(all_logs)} entries",
        )
        
        await self._respond(source, embed=embed)

    async def _note_logic(self, source, user: discord.Member, note: str):
        author_id = source.user.id if isinstance(source, discord.Interaction) else source.author.id
        await self.bot.db.add_note(source.guild.id, user.id, author_id, note)
        
        embed = ModEmbed.success(
            "Note Added",
            f"Added note to {user.mention}:\n`{note}`"
        )
        
        await self._respond(source, embed=embed)

    async def _notes_logic(self, source, user: discord.Member):
        guild = source.guild
        notes = await self.bot.db.get_notes(guild.id, user.id)
        
        if not notes:
             return await self._respond(source, embed=ModEmbed.info("No Notes", f"{user.mention} has no notes."))
        
        entries = []
        for n in notes[:10]:
            moderator = guild.get_member(n['moderator_id'])
            mod_display = moderator.display_name if moderator else f"ID: {n['moderator_id']}"
            created_at = self._parse_log_timestamp(n.get("created_at"))
            when = (
                f" · <t:{int(created_at.timestamp())}:R>"
                if created_at != self._unknown_timestamp()
                else ""
            )
            content = n.get("content") or n.get("note") or "No content"
            entries.append(
                f"**Note #{n['id']}**{when}\n"
                f"> {compact_text(content, max_length=220)}\n"
                f"-# by {discord.utils.escape_markdown(mod_display)}"
            )

        shown = min(10, len(notes))
        embed = moderation_list_embed(
            title=f"Staff notes · {user.display_name}",
            color=Colors.INFO,
            summary_rows=(("Notes", len(notes)), ("Showing", f"Newest {shown}")),
            entries=entries,
            thumbnail_url=user.display_avatar.url,
            footer_text=f"Showing {shown} of {len(notes)} notes",
        )
        
        await self._respond(source, embed=embed)

    async def _modstats_logic(self, source, moderator: Optional[discord.Member] = None):
        guild = source.guild
        if moderator:
            stats = await self.bot.db.get_moderator_stats(guild.id, moderator.id)
            title = f"Moderator statistics · {moderator.display_name}"
            thumbnail_url = moderator.display_avatar.url
        else:
            stats = await self.bot.db.get_guild_mod_stats(guild.id)
            title = "Server moderation statistics"
            thumbnail_url = getattr(getattr(guild, "icon", None), "url", None)
        
        # Action counts
        action_fields = {
            "Warnings": stats.get('warns', 0),
            "Kicks": stats.get('kicks', 0),
            "Bans": stats.get('bans', 0),
            "Temporary bans": stats.get('tempbans', 0),
            "Timeouts": stats.get('mutes', 0),
            "Quarantines": stats.get('quarantines', 0),
        }
        total_actions = sum(action_fields.values())
        rows = [("Total actions", total_actions), *action_fields.items()]
        embed = sapphire_log_embed(
            title=title,
            color=Colors.MOD,
            detail_lines=compact_kv_lines(rows).splitlines(),
            thumbnail_url=thumbnail_url,
        )
        
        await self._respond(source, embed=embed)

    @staticmethod
    def _parse_log_timestamp(value: object) -> datetime:
        try:
            parsed = datetime.fromisoformat(str(value).replace(' ', 'T'))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (TypeError, ValueError, OverflowError):
            return CaseCommands._unknown_timestamp()

    @staticmethod
    def _unknown_timestamp() -> datetime:
        return datetime.min.replace(tzinfo=timezone.utc)

    # Commands
    @commands.command(name="case", description="📋 View a specific moderation case")
    @is_mod()
    async def case(self, ctx: commands.Context, case_number: int):
        await self._case_logic(ctx, case_number)

    # Slash command - registered dynamically in __init__.py
    async def case_slash(self, interaction: discord.Interaction, case_number: int):
        await self._case_logic(interaction, case_number)

    @commands.command(name="editcase", description="✏️ Edit a case's reason")
    @is_mod()
    async def editcase(self, ctx: commands.Context, case_number: int, *, reason: str):
        await self._editcase_logic(ctx, case_number, reason)

    # Slash command - registered dynamically in __init__.py
    async def editcase_slash(self, interaction: discord.Interaction, case_number: int, reason: str):
        await self._editcase_logic(interaction, case_number, reason)

    @commands.command(name="history", description="📜 View a user's moderation history")
    @is_mod()
    async def history(self, ctx: commands.Context, user: discord.Member):
        await self._history_logic(ctx, user)

    # Slash command - registered dynamically in __init__.py
    async def history_slash(self, interaction: discord.Interaction, user: discord.Member):
        await self._history_logic(interaction, user)

    @commands.command(name="modlogs", description="📋 View comprehensive moderation logs")
    @is_mod()
    async def modlogs(self, ctx: commands.Context, user: discord.Member):
        await self._modlogs_logic(ctx, user)

    # Slash command - registered dynamically in __init__.py
    async def modlogs_slash(self, interaction: discord.Interaction, user: discord.Member):
        await self._modlogs_logic(interaction, user)

    @commands.command(name="note", description="📝 Add a note to a user")
    @is_mod()
    async def note(self, ctx: commands.Context, user: discord.Member, *, note: str):
        await self._note_logic(ctx, user, note)

    # Slash command - registered dynamically in __init__.py
    async def note_slash(self, interaction: discord.Interaction, user: discord.Member, note: str):
        await self._note_logic(interaction, user, note)

    @commands.command(name="notes", description="📋 View notes for a user")
    @is_mod()
    async def notes(self, ctx: commands.Context, user: discord.Member):
        await self._notes_logic(ctx, user)

    # Slash command - registered dynamically in __init__.py
    async def notes_slash(self, interaction: discord.Interaction, user: discord.Member):
        await self._notes_logic(interaction, user)

    @commands.command(name="modstats", description="📊 View moderation statistics")
    @is_mod()
    async def modstats(self, ctx: commands.Context, moderator: Optional[discord.Member] = None):
        await self._modstats_logic(ctx, moderator)

    # Slash command - registered dynamically in __init__.py
    async def modstats_slash(self, interaction: discord.Interaction, moderator: Optional[discord.Member] = None):
        await self._modstats_logic(interaction, moderator)
