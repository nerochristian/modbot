"""
Advanced Court System - Complete with Logging
Features: Case filing, jury system, evidence, voting, Discord-style transcripts, logging
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
from utils.embeds import ModEmbed, Colors
from utils.checks import is_mod, is_admin
from utils.logging import send_log_embed
import asyncio
import io
import json
import aiosqlite


class CourtSession:
    """Represents an active court session"""
    def __init__(self, channel_id: int, guild_id: int, case_type: str, plaintiff_id: int, 
                 defendant_id: int, judge_id: int, reason: str):
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.case_type = case_type
        self.plaintiff_id = plaintiff_id
        self.defendant_id = defendant_id
        self.judge_id = judge_id
        self.reason = reason
        self.jury = []
        self.evidence = []
        self.witnesses = []
        self.votes = {}
        self.status = "open"
        self.verdict = None
        self.started_at = datetime.now(timezone.utc)


class CourtEvidence(discord.ui.Modal, title="Submit Evidence"):
    """Modal for submitting evidence"""
    
    evidence_title = discord.ui.TextInput(
        label="Evidence Title",
        placeholder="Brief title for this evidence",
        max_length=100,
        required=True
    )
    
    evidence_description = discord.ui.TextInput(
        label="Evidence Description",
        placeholder="Detailed description of the evidence",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )
    
    evidence_link = discord.ui.TextInput(
        label="Evidence Link (Optional)",
        placeholder="Image/video/document link",
        required=False
    )
    
    def __init__(self, cog, session):
        super().__init__()
        self.cog = cog
        self.session = session
    
    async def on_submit(self, interaction: discord.Interaction):
        evidence_data = {
            'title': self.evidence_title.value,
            'description': self.evidence_description.value,
            'link': self.evidence_link.value,
            'submitted_by': interaction.user.id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.session.evidence.append(evidence_data)
        
        embed = discord.Embed(
            title="📎 New Evidence Submitted",
            description=f"**Title:** {evidence_data['title']}\n**Submitted by:** {interaction.user.mention}",
            color=Colors.INFO,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Description", value=evidence_data['description'], inline=False)
        
        if evidence_data['link']:
            embed.add_field(name="Link", value=evidence_data['link'], inline=False)
        
        await interaction.response.send_message(embed=embed)


class VerdictVoteView(discord.ui.LayoutView):
    """Voting buttons for jury/judge verdict"""
    
    def __init__(self, cog, session):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session

        guilty = discord.ui.Button(
            label="Guilty",
            style=discord.ButtonStyle.red,
            emoji="⚖️",
        )
        not_guilty = discord.ui.Button(
            label="Not Guilty",
            style=discord.ButtonStyle.green,
            emoji="✅",
        )

        async def _g(interaction: discord.Interaction):
            return await self.guilty_button(interaction, guilty)

        async def _ng(interaction: discord.Interaction):
            return await self.not_guilty_button(interaction, not_guilty)

        guilty.callback = _g
        not_guilty.callback = _ng

        self.add_item(guilty)
        self.add_item(not_guilty)
    
    async def guilty_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.session.jury and interaction.user.id != self.session.judge_id:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Authorized", "Only jury members and the judge can vote."),
                ephemeral=True
            )
        
        self.session.votes[interaction.user.id] = "guilty"
        await interaction.response.send_message(
            embed=ModEmbed.success("Vote Recorded", "Your vote for **Guilty** has been recorded."),
            ephemeral=True
        )
        
        await self.cog.check_verdict_completion(self.session)
    
    async def not_guilty_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.session.jury and interaction.user.id != self.session.judge_id:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Authorized", "Only jury members and the judge can vote."),
                ephemeral=True
            )
        
        self.session.votes[interaction.user.id] = "not_guilty"
        await interaction.response.send_message(
            embed=ModEmbed.success("Vote Recorded", "Your vote for **Not Guilty** has been recorded."),
            ephemeral=True
        )
        
        await self.cog.check_verdict_completion(self.session)


class Court(commands.Cog):
    """Advanced court system with Discord-style transcripts and logging"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}
        # Legacy default (single-server). Prefer per-guild `court_category_id` in DB settings.
        self.court_category_id = 0

    async def _get_or_create_court_category(
        self, guild: discord.Guild
    ) -> Optional[discord.CategoryChannel]:
        """Resolve the court category for this guild (stored in DB settings)."""
        try:
            settings = await self.bot.db.get_settings(guild.id)
        except Exception:
            settings = {}

        category_id = settings.get("court_category_id") or None
        if category_id:
            ch = guild.get_channel(int(category_id))
            if isinstance(ch, discord.CategoryChannel):
                return ch

        # Try common names before creating.
        for name in ["⚖️ Court", "court", "Court", "court-cases", "Court Cases"]:
            found = discord.utils.get(guild.categories, name=name)
            if isinstance(found, discord.CategoryChannel):
                settings["court_category_id"] = found.id
                try:
                    await self.bot.db.update_settings(guild.id, settings)
                except Exception:
                    pass
                return found

        try:
            created = await guild.create_category("⚖️ Court", reason="ModBot: court system setup")
        except Exception:
            return None

        settings["court_category_id"] = created.id
        try:
            await self.bot.db.update_settings(guild.id, settings)
        except Exception:
            pass
        return created
    
    async def cog_load(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS court_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER,
                    guild_id INTEGER,
                    case_type TEXT,
                    plaintiff_id INTEGER,
                    defendant_id INTEGER,
                    judge_id INTEGER,
                    reason TEXT,
                    verdict TEXT,
                    status TEXT DEFAULT 'open',
                    jury_data TEXT DEFAULT '[]',
                    started_at TEXT,
                    closed_at TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS court_evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    channel_id INTEGER,
                    title TEXT,
                    description TEXT,
                    link TEXT,
                    submitted_by INTEGER,
                    timestamp TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS court_votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    voter_id INTEGER,
                    vote TEXT,
                    timestamp TEXT,
                    UNIQUE(session_id, voter_id)
                )
            """)
            
            await db.commit()
    
    @app_commands.command(name="court-setup-logs", description="⚙️ Configure court transcript logs channel")
    @app_commands.describe(channel="The channel to send court transcripts to")
    @is_admin()
    async def court_setup_logs(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        
        try:
            settings = await self.bot.db.get_settings(interaction.guild_id)
            settings['court_log_channel'] = channel.id
            await self.bot.db.update_settings(interaction.guild_id, settings)
            
            embed = discord.Embed(
                title="✅ Court Logs Configured",
                description=f"Court transcripts will now be sent to {channel.mention}\n\nAll closed cases will have their transcripts automatically saved here.",
                color=Colors.SUCCESS
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Send test message
            test_embed = discord.Embed(
                title="⚖️ Court Logs Channel Active",
                description="This channel will receive all court case transcripts when cases are closed.\n\n**What gets logged:**\n• Full Discord-style transcript\n• Case details (plaintiff, defendant, judge)\n• Verdict and voting results\n• Evidence submitted\n• Case summary",
                color=0x5865F2,
                timestamp=datetime.now(timezone.utc)
            )
            test_embed.set_footer(text="Court System v3.0")
            await channel.send(embed=test_embed)
            
        except Exception as e:
            await interaction.followup.send(
                embed=ModEmbed.error("Setup Failed", f"Error: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="court-file", description="⚖️ File a court case")
    @app_commands.describe(
        defendant="The person being sued/charged",
        case_type="Type of case",
        reason="Reason for the case"
    )
    @is_mod()
    async def court_file(
        self, 
        interaction: discord.Interaction, 
        defendant: discord.Member,
        case_type: Literal["Criminal", "Civil", "Appeal"],
        reason: str
    ):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check for existing case
            for session in self.active_sessions.values():
                if session.guild_id == interaction.guild_id and session.defendant_id == defendant.id:
                    return await interaction.followup.send(
                        embed=ModEmbed.error("Case Exists", f"{defendant.mention} already has an active case."),
                        ephemeral=True
                    )
            
            # Get category (per-guild, auto-created if needed)
            category = await self._get_or_create_court_category(interaction.guild)
            if not category:
                return await interaction.followup.send(
                    embed=ModEmbed.error("Setup Error", "Court category not found. Contact an admin."),
                    ephemeral=True
                )
            
            # Create channel
            case_name = f"case-{defendant.name.lower()}"[:100]
            court_channel = await interaction.guild.create_text_channel(
                name=case_name,
                category=category,
                topic=f"⚖️ {case_type} Case | {interaction.user.name} vs {defendant.name}",
                reason=f"Court case filed by {interaction.user}"
            )
            
            # Set permissions
            await court_channel.set_permissions(interaction.guild.default_role, view_channel=True, send_messages=False)
            await court_channel.set_permissions(defendant, send_messages=True)
            await court_channel.set_permissions(interaction.user, send_messages=True)
            
            # Create session
            session = CourtSession(
                channel_id=court_channel.id,
                guild_id=interaction.guild_id,
                case_type=case_type,
                plaintiff_id=interaction.user.id,
                defendant_id=defendant.id,
                judge_id=interaction.user.id,
                reason=reason
            )
            
            self.active_sessions[court_channel.id] = session
            
            # Save to DB
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute("""
                    INSERT INTO court_sessions 
                    (channel_id, guild_id, case_type, plaintiff_id, defendant_id, judge_id, reason, started_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')
                """, (
                    court_channel.id, interaction.guild_id, case_type, 
                    interaction.user.id, defendant.id, interaction.user.id, 
                    reason, datetime.now(timezone.utc).isoformat()
                ))
                await db.commit()
            
            # Send case info
            embed = discord.Embed(
                title=f"⚖️ {case_type} Case Filed",
                description=f"**Plaintiff:** {interaction.user.mention}\n**Defendant:** {defendant.mention}\n**Judge:** {interaction.user.mention}",
                color=Colors.INFO,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="📋 Case Reason", value=reason, inline=False)
            embed.add_field(name="🔧 Available Commands", value=(
                "`/court-evidence` - Submit evidence\n"
                "`/court-jury add @user` - Add jury members\n"
                "`/court-verdict` - Start deliberation\n"
                "`/court-view-evidence` - View all evidence\n"
                "`/court-close [summary]` - Close the case"
            ), inline=False)
            embed.set_footer(text="Present your case and evidence")
            
            await court_channel.send(f"{interaction.user.mention} vs {defendant.mention}", embed=embed)
            
            # DM defendant
            try:
                dm_embed = discord.Embed(
                    title="⚖️ Court Summons",
                    description=f"You have been summoned to court in **{interaction.guild.name}**",
                    color=Colors.WARNING
                )
                dm_embed.add_field(name="Case Type", value=case_type, inline=True)
                dm_embed.add_field(name="Filed By", value=str(interaction.user), inline=True)
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.add_field(name="Court Channel", value=court_channel.mention, inline=False)
                await defendant.send(embed=dm_embed)
            except:
                pass
            
            await interaction.followup.send(
                embed=ModEmbed.success("✅ Case Filed", f"Court case created: {court_channel.mention}"),
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                embed=ModEmbed.error("Error", f"Failed to create case: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="court-evidence", description="📎 Submit evidence to the court")
    @is_mod()
    async def court_evidence(self, interaction: discord.Interaction):
        session = self.active_sessions.get(interaction.channel_id)
        
        if not session:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not a Court", "This command only works in active court channels."),
                ephemeral=True
            )
        
        modal = CourtEvidence(self, session)
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="court-jury", description="👥 Manage jury members")
    @app_commands.describe(action="Add, remove, or list jury", member="The member")
    @is_mod()
    async def court_jury(
        self, 
        interaction: discord.Interaction,
        action: Literal["add", "remove", "list"],
        member: Optional[discord.Member] = None
    ):
        session = self.active_sessions.get(interaction.channel_id)
        
        if not session:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not a Court", "This command only works in active court channels."),
                ephemeral=True
            )
        
        if action == "add":
            if not member:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Missing Member", "Specify a member to add."),
                    ephemeral=True
                )
            
            if member.id in session.jury:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Already Added", f"{member.mention} is already a jury member."),
                    ephemeral=True
                )
            
            session.jury.append(member.id)
            
            channel = interaction.guild.get_channel(session.channel_id)
            await channel.set_permissions(member, send_messages=True, add_reactions=True)
            
            embed = discord.Embed(
                title="👥 Jury Member Added",
                description=f"{member.mention} has been added to the jury.\n\n**Total Jury:** {len(session.jury)} member(s)",
                color=Colors.SUCCESS
            )
            await interaction.response.send_message(embed=embed)
            
        elif action == "remove":
            if not member:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Missing Member", "Specify a member to remove."),
                    ephemeral=True
                )
            
            if member.id not in session.jury:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("Not Found", f"{member.mention} is not in the jury."),
                    ephemeral=True
                )
            
            session.jury.remove(member.id)
            
            embed = discord.Embed(
                title="👥 Jury Member Removed",
                description=f"{member.mention} has been removed from the jury.",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed)
            
        elif action == "list":
            if not session.jury:
                return await interaction.response.send_message(
                    embed=ModEmbed.info("No Jury", "No jury members have been added yet."),
                    ephemeral=True
                )
            
            jury_list = "\n".join([f"• <@{uid}>" for uid in session.jury])
            embed = discord.Embed(
                title=f"👥 Jury Members ({len(session.jury)})",
                description=jury_list,
                color=Colors.INFO
            )
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="court-verdict", description="⚖️ Start verdict deliberation")
    @is_mod()
    async def court_verdict(self, interaction: discord.Interaction):
        session = self.active_sessions.get(interaction.channel_id)
        
        if not session:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not a Court", "This command only works in active court channels."),
                ephemeral=True
            )
        
        if interaction.user.id != session.judge_id:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Judge", "Only the judge can start deliberation."),
                ephemeral=True
            )
        
        session.status = "deliberation"
        
        embed = discord.Embed(
            title="⚖️ Verdict Deliberation",
            description="**The jury and judge can now vote on the verdict.**\n\nClick the buttons below to cast your vote.",
            color=0xFEE75C,
            timestamp=datetime.now(timezone.utc)
        )
        
        voters_text = ""
        if session.jury:
            jury_mentions = ", ".join([f"<@{uid}>" for uid in session.jury])
            voters_text += f"**Jury:** {jury_mentions}\n"
        
        voters_text += f"**Judge:** <@{session.judge_id}>"
        embed.add_field(name="👥 Voters", value=voters_text, inline=False)
        embed.set_footer(text="Verdict will be announced when all votes are in")
        
        view = VerdictVoteView(self, session)
        await interaction.response.send_message(embed=embed, view=view)
    
    async def check_verdict_completion(self, session: CourtSession):
        """Check if all required votes are in"""
        total_voters = len(session.jury) + 1
        
        if len(session.votes) >= total_voters:
            guilty_votes = sum(1 for v in session.votes.values() if v == "guilty")
            not_guilty_votes = sum(1 for v in session.votes.values() if v == "not_guilty")
            
            if guilty_votes > not_guilty_votes:
                session.verdict = "guilty"
                verdict_text = "**GUILTY**"
                verdict_color = 0xED4245
            else:
                session.verdict = "not_guilty"
                verdict_text = "**NOT GUILTY**"
                verdict_color = 0x57F287
            
            channel = self.bot.get_channel(session.channel_id)
            
            embed = discord.Embed(
                title="⚖️ VERDICT REACHED",
                description=f"## {verdict_text}\n\nThe jury has reached a decision.",
                color=verdict_color,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="⚖️ Guilty Votes", value=f"``````", inline=True)
            embed.add_field(name="✅ Not Guilty Votes", value=f"``````", inline=True)
            embed.set_footer(text="Case can now be closed by the judge with /court-close")
            
            await channel.send(f"<@{session.plaintiff_id}> <@{session.defendant_id}>", embed=embed)
            
            session.status = "verdict_reached"
    
    @app_commands.command(name="court-view-evidence", description="📋 View all submitted evidence")
    async def court_view_evidence(self, interaction: discord.Interaction):
        session = self.active_sessions.get(interaction.channel_id)
        
        if not session:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not a Court", "This command only works in active court channels."),
                ephemeral=True
            )
        
        if not session.evidence:
            return await interaction.response.send_message(
                embed=ModEmbed.info("No Evidence", "No evidence has been submitted yet."),
                ephemeral=True
            )
        
        embed = discord.Embed(
            title=f"📎 Evidence Summary ({len(session.evidence)} items)",
            color=Colors.INFO,
            timestamp=datetime.now(timezone.utc)
        )
        
        for i, evidence in enumerate(session.evidence, 1):
            value = f"**Submitted by:** <@{evidence['submitted_by']}>\n{evidence['description'][:150]}"
            if evidence['link']:
                value += f"\n🔗 [View Evidence]({evidence['link']})"
            
            embed.add_field(
                name=f"{i}. {evidence['title']}", 
                value=value,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="court-close", description="🔒 Close the court case")
    @app_commands.describe(summary="Optional final case summary")
    @is_mod()
    async def court_close(self, interaction: discord.Interaction, summary: Optional[str] = None):
        session = self.active_sessions.get(interaction.channel_id)
        
        if not session:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not a Court", "This command only works in active court channels."),
                ephemeral=True
            )
        
        await interaction.response.defer()
        
        try:
            # Generate Discord-style transcript
            transcript = await self.generate_discord_transcript(interaction.channel, session, summary)
            
            # Save to DB
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute("""
                    UPDATE court_sessions 
                    SET status = 'closed', verdict = ?, closed_at = ?
                    WHERE channel_id = ?
                """, (session.verdict, datetime.now(timezone.utc).isoformat(), session.channel_id))
                await db.commit()
            
            # Create transcript file
            filename = f"court-case-{session.defendant_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
            
            # Get court logs channel
            settings = await self.bot.db.get_settings(interaction.guild_id)
            log_channel_id = settings.get('court_log_channel')
            
            transcript_sent = False
            
            if log_channel_id:
                log_channel = interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    # Get members
                    plaintiff = interaction.guild.get_member(session.plaintiff_id)
                    defendant = interaction.guild.get_member(session.defendant_id)
                    judge = interaction.guild.get_member(session.judge_id)
                    
                    # Create log embed
                    log_embed = discord.Embed(
                        title="⚖️ Court Case Transcript",
                        color=0xED4245 if session.verdict == "guilty" else 0x57F287 if session.verdict == "not_guilty" else 0x5865F2,
                        timestamp=datetime.now(timezone.utc)
                    )
                    log_embed.add_field(name="📋 Case Type", value=session.case_type, inline=True)
                    log_embed.add_field(name="⚖️ Verdict", value=session.verdict.replace('_', ' ').title() if session.verdict else 'No verdict', inline=True)
                    log_embed.add_field(name="⏱️ Duration", value=f"<t:{int(session.started_at.timestamp())}:R>", inline=True)
                    
                    log_embed.add_field(name="👤 Plaintiff", value=plaintiff.mention if plaintiff else 'Unknown', inline=True)
                    log_embed.add_field(name="👤 Defendant", value=defendant.mention if defendant else 'Unknown', inline=True)
                    log_embed.add_field(name="⚖️ Judge", value=judge.mention if judge else 'Unknown', inline=True)
                    
                    if session.jury:
                        jury_text = ", ".join([f"<@{uid}>" for uid in session.jury[:5]])
                        if len(session.jury) > 5:
                            jury_text += f" +{len(session.jury) - 5} more"
                        log_embed.add_field(name="👥 Jury", value=jury_text, inline=False)
                    
                    if summary:
                        log_embed.add_field(name="📝 Summary", value=summary[:1024], inline=False)
                    
                    log_embed.set_footer(text=f"Case closed by {interaction.user}")
                    
                    # Send to logs
                    file = discord.File(
                        io.BytesIO(transcript.encode('utf-8')),
                        filename=filename
                    )
                    
                    await send_log_embed(log_channel, log_embed, file=file)
                    transcript_sent = True
            
            # Send closure message to case channel
            embed = discord.Embed(
                title="📜 Case Closed",
                description=f"**Verdict:** {session.verdict.replace('_', ' ').title() if session.verdict else 'No verdict'}\n**Duration:** <t:{int(session.started_at.timestamp())}:R>",
                color=Colors.SUCCESS,
                timestamp=datetime.now(timezone.utc)
            )
            
            if summary:
                embed.add_field(name="📝 Summary", value=summary[:1024], inline=False)
            
            if transcript_sent and log_channel_id:
                embed.add_field(name="📂 Transcript", value=f"Saved to <#{log_channel_id}>", inline=False)
            else:
                embed.add_field(name="⚠️ Transcript", value="No log channel configured. Use `/court-setup-logs` to set one up.", inline=False)
            
            embed.set_footer(text="This channel will be deleted in 10 seconds")
            
            await interaction.channel.send(embed=embed)
            
            await interaction.followup.send(
                embed=ModEmbed.success("✅ Case Closed", "Transcript saved. Deleting channel..."),
                ephemeral=True
            )
            
            # Cleanup
            await asyncio.sleep(10)
            del self.active_sessions[session.channel_id]
            await interaction.channel.delete(reason=f"Case closed by {interaction.user}")
            
        except Exception as e:
            await interaction.followup.send(
                embed=ModEmbed.error("Error", f"Failed to close case: {str(e)}"),
                ephemeral=True
            )
    
    async def generate_discord_transcript(self, channel: discord.TextChannel, session: CourtSession, summary: Optional[str]) -> str:
        """Generate authentic Discord-style HTML transcript"""
        
        messages = []
        async for msg in channel.history(limit=None, oldest_first=True):
            messages.append(msg)
        
        guild = channel.guild
        plaintiff = guild.get_member(session.plaintiff_id)
        defendant = guild.get_member(session.defendant_id)
        judge = guild.get_member(session.judge_id)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Court Transcript - {guild.name}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;600;700&display=swap');
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Roboto', sans-serif; background: #36393f; color: #dcddde; font-size: 16px; }}
        .container {{ max-width: 100%; margin: 0 auto; background: #36393f; }}
        .header {{ background: #202225; padding: 16px 20px; border-bottom: 1px solid #202225; box-shadow: 0 1px 0 rgba(4,4,5,0.2); }}
        .channel-name {{ color: #fff; font-weight: 600; font-size: 16px; }}
        .channel-name::before {{ content: '#'; color: #8e9297; margin-right: 4px; }}
        .channel-topic {{ color: #b9bbbe; font-size: 14px; margin-top: 4px; margin-left: 20px; }}
        .case-banner {{ background: #5865f2; color: white; padding: 20px; text-align: center; }}
        .case-banner h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .case-details {{ background: #2f3136; padding: 20px; border-bottom: 1px solid #202225; }}
        .case-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; max-width: 1200px; margin: 0 auto; }}
        .case-item {{ background: #202225; padding: 12px 16px; border-radius: 4px; }}
        .case-label {{ color: #b9bbbe; font-size: 12px; text-transform: uppercase; font-weight: 600; margin-bottom: 4px; }}
        .case-value {{ color: #fff; font-size: 16px; font-weight: 500; }}
        .messages {{ padding: 16px 0; }}
        .message {{ padding: 4px 48px 4px 72px; margin: 0; position: relative; min-height: 44px; }}
        .message:hover {{ background: #32353b; }}
        .message.first-in-group {{ margin-top: 16px; padding-top: 8px; }}
        .avatar {{ position: absolute; left: 16px; width: 40px; height: 40px; border-radius: 50%; overflow: hidden; }}
        .avatar img {{ width: 100%; height: 100%; object-fit: cover; }}
        .message:not(.first-in-group) .avatar {{ display: none; }}
        .message:not(.first-in-group) .message-header {{ display: none; }}
        .message:not(.first-in-group):hover .timestamp-hover {{ display: block; }}
        .timestamp-hover {{ display: none; position: absolute; left: 0; width: 56px; text-align: center; font-size: 11px; color: #a3a6aa; }}
        .message-header {{ display: flex; align-items: center; margin-bottom: 2px; }}
        .username {{ color: #fff; font-size: 16px; font-weight: 500; margin-right: 6px; }}
        .bot-tag {{ background: #5865f2; color: #fff; font-size: 10px; font-weight: 600; padding: 2px 4px; border-radius: 3px; text-transform: uppercase; margin-right: 6px; }}
        .timestamp {{ color: #a3a6aa; font-size: 12px; font-weight: 500; }}
        .message-content {{ color: #dcddde; font-size: 16px; line-height: 1.375; word-wrap: break-word; }}
        .embed {{ display: flex; margin-top: 8px; max-width: 520px; }}
        .embed-color-pill {{ width: 4px; border-radius: 4px 0 0 4px; }}
        .embed-content {{ background: #2f3136; border: 1px solid #202225; border-left: none; border-radius: 0 4px 4px 0; padding: 8px 12px; flex: 1; }}
        .embed-title {{ color: #fff; font-size: 14px; font-weight: 600; margin-bottom: 4px; }}
        .embed-description {{ color: #dcddde; font-size: 14px; line-height: 1.375; }}
        .embed-field {{ margin-top: 8px; }}
        .embed-field-name {{ color: #fff; font-size: 14px; font-weight: 600; margin-bottom: 2px; }}
        .embed-field-value {{ color: #dcddde; font-size: 14px; }}
        .attachment {{ margin-top: 8px; max-width: 400px; }}
        .attachment img {{ max-width: 100%; border-radius: 4px; }}
        .verdict-banner {{ background: #2f3136; border: 2px solid #43b581; border-radius: 8px; padding: 20px; margin: 16px; text-align: center; }}
        .verdict-banner.guilty {{ border-color: #f04747; }}
        .verdict-result {{ font-size: 32px; font-weight: 700; color: #43b581; }}
        .verdict-result.guilty {{ color: #f04747; }}
        .verdict-stats {{ display: flex; justify-content: center; gap: 40px; margin-top: 16px; }}
        .verdict-stat-value {{ font-size: 24px; font-weight: 600; color: #fff; }}
        .verdict-stat-label {{ font-size: 12px; color: #b9bbbe; text-transform: uppercase; }}
        .summary-section {{ background: #2f3136; border-radius: 8px; padding: 16px; margin: 16px; }}
        .summary-title {{ color: #fff; font-size: 16px; font-weight: 600; margin-bottom: 8px; }}
        .summary-content {{ color: #dcddde; font-size: 14px; line-height: 1.5; }}
        a {{ color: #00aff4; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="channel-name">case-{defendant.name.lower() if defendant else 'unknown'}</div>
            <div class="channel-topic">⚖️ {session.case_type} Case | Court Transcript</div>
        </div>
        <div class="case-banner">
            <h1>⚖️ {session.case_type} Court Case</h1>
            <div style="opacity: 0.9;">{guild.name}</div>
        </div>
        <div class="case-details">
            <div class="case-grid">
                <div class="case-item"><div class="case-label">Plaintiff</div><div class="case-value">{plaintiff.display_name if plaintiff else 'Unknown'}</div></div>
                <div class="case-item"><div class="case-label">Defendant</div><div class="case-value">{defendant.display_name if defendant else 'Unknown'}</div></div>
                <div class="case-item"><div class="case-label">Judge</div><div class="case-value">{judge.display_name if judge else 'Unknown'}</div></div>
                <div class="case-item"><div class="case-label">Case Type</div><div class="case-value">{session.case_type}</div></div>
                <div class="case-item"><div class="case-label">Started</div><div class="case-value">{session.started_at.strftime('%b %d, %Y')}</div></div>
                <div class="case-item"><div class="case-label">Messages</div><div class="case-value">{len(messages)}</div></div>
            </div>
        </div>
        <div class="messages">
"""
        
        last_author = None
        last_timestamp = None
        
        for msg in messages:
            time_diff = (msg.created_at - last_timestamp).total_seconds() if last_timestamp else 999
            is_new_group = (msg.author.id != last_author) or (time_diff > 420)
            
            avatar_url = msg.author.display_avatar.url if msg.author.display_avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
            timestamp_str = msg.created_at.strftime('%I:%M %p')
            timestamp_hover = msg.created_at.strftime('%m/%d/%Y %I:%M %p')
            
            message_class = "message first-in-group" if is_new_group else "message"
            content = msg.content.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>') if msg.content else ''
            
            for member in msg.mentions:
                content = content.replace(f'&lt;@{member.id}&gt;', f'<span style="background: #5865f240; color: #dee0fc; padding: 0 2px; border-radius: 3px;">@{member.display_name}</span>')
            
            bot_tag = '<span class="bot-tag">BOT</span>' if msg.author.bot else ''
            no_content_html = '<em style="color: #72767d;">No content</em>'
            
            html += f'<div class="{message_class}"><span class="timestamp-hover">{timestamp_hover}</span><div class="avatar"><img src="{avatar_url}" alt="{msg.author.display_name}"></div><div class="message-header"><span class="username">{msg.author.display_name}</span>{bot_tag}<span class="timestamp">{timestamp_str}</span></div><div class="message-content">{content or no_content_html}</div>'
            
            for embed in msg.embeds:
                embed_color = f"#{embed.color.value:06x}" if embed.color else "#5865f2"
                html += f'<div class="embed"><div class="embed-color-pill" style="background: {embed_color};"></div><div class="embed-content">'
                if embed.title:
                    html += f'<div class="embed-title">{embed.title}</div>'
                if embed.description:
                    html += f'<div class="embed-description">{embed.description[:500]}</div>'
                for field in embed.fields[:5]:
                    html += f'<div class="embed-field"><div class="embed-field-name">{field.name}</div><div class="embed-field-value">{field.value[:200]}</div></div>'
                html += '</div></div>'
            
            for attachment in msg.attachments:
                if attachment.content_type and attachment.content_type.startswith('image'):
                    html += f'<div class="attachment"><img src="{attachment.url}" alt="{attachment.filename}"></div>'
                else:
                    html += f'<div class="attachment"><a href="{attachment.url}" target="_blank">📎 {attachment.filename}</a></div>'
            
            html += '</div>'
            last_author = msg.author.id
            last_timestamp = msg.created_at
        
        html += '</div>'
        
        if session.verdict:
            guilty_votes = sum(1 for v in session.votes.values() if v == "guilty")
            not_guilty_votes = sum(1 for v in session.votes.values() if v == "not_guilty")
            verdict_class = "verdict-banner guilty" if session.verdict == "guilty" else "verdict-banner"
            result_class = "verdict-result guilty" if session.verdict == "guilty" else "verdict-result"
            verdict_text = "GUILTY" if session.verdict == "guilty" else "NOT GUILTY"
            html += f'<div class="{verdict_class}"><h2 style="color: #fff; margin-bottom: 12px;">⚖️ FINAL VERDICT</h2><div class="{result_class}">{verdict_text}</div><div class="verdict-stats"><div><div class="verdict-stat-value">{guilty_votes}</div><div class="verdict-stat-label">Guilty</div></div><div><div class="verdict-stat-value">{not_guilty_votes}</div><div class="verdict-stat-label">Not Guilty</div></div></div></div>'
        
        if summary:
            html += f'<div class="summary-section"><div class="summary-title">📝 Case Summary</div><div class="summary-content">{summary}</div></div>'
        
        html += '</div></body></html>'
        return html


async def setup(bot):
    await bot.add_cog(Court(bot))
