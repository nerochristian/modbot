# cogs/jobs_cog.py

from __future__ import annotations

import random
import logging
from datetime import datetime, timezone
from typing import List, Dict

import discord
from discord import app_commands
from discord.ext import commands

from utils.format import format_number, money, progress_bar, level_from_xp, format_time
from utils.checks import (
    safe_defer,
    safe_reply,
    check_in_hospital,
    check_in_jail,
    check_cooldown,
    check_user_stats,
)
from utils.constants import WORK_COOLDOWN, SKILL_EMOJIS
from services.jobs_service import (
    calculate_work_earnings,
    calculate_work_xp,
    calculate_job_xp,
    get_job_level_from_xp,
)
from data.jobs import JOBS, JOB_CATEGORIES
from views.job_minigames import get_job_minigame
from views.v2_embed import apply_v2_embed_layout

logger = logging.getLogger('LifeSimBot.Jobs')

# ============= CONSTANTS =============

JOB_COLORS = {
    "entry": 0x57F287,
    "skilled": 0x3B82F6,
    "professional": 0x9B59B6,
    "expert": 0xEB459E,
    "elite": 0xFFD700,
    "work": 0x5865F2,
    "success": 0x22C55E,
    "quit": 0xEF4444,
}

SKILL_XP_WORK = 10

# ============= JOB APPLICATION VIEWS =============

class JobApplicationView(discord.ui.LayoutView):
    """Interactive job application with dropdown selector."""

    def __init__(self, bot, user: discord.User, available_jobs: List[Dict]):
        super().__init__(timeout=120)
        self.bot = bot
        self.user = user
        self.available_jobs = available_jobs
        
        # Add dropdown
        if available_jobs:
            self.add_item(JobSelectMenu(bot, available_jobs))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This isn't your job application!",
                ephemeral=True
            )
            return False
        return True


class JobCategoryView(discord.ui.LayoutView):
    """Category-first job browser to avoid the 25-option select limit."""

    def __init__(self, bot, user: discord.User, available_jobs: List[Dict], *, user_level: int, current_job: str):
        super().__init__(timeout=180)
        self.bot = bot
        self.user = user
        self.available_jobs = available_jobs
        self.user_level = user_level
        self.current_job = current_job

        self.jobs_by_category: Dict[str, List[Dict]] = {}
        for job in available_jobs:
            cat = str(job.get("category") or "entry")
            self.jobs_by_category.setdefault(cat, []).append(job)

        self.add_item(JobCategoryMenu(self))

    def create_embed(self) -> discord.Embed:
        unlocked = sum(1 for j in self.available_jobs if j.get("can_apply"))
        locked = len(self.available_jobs) - unlocked

        embed = discord.Embed(
            title="💼 Job Application",
            description=(
                f"**Your Level:** {self.user_level}\n"
                f"**Current Job:** {self.current_job}\n\n"
                "Select a category to browse jobs."
            ),
            color=JOB_COLORS["work"],
        )

        embed.add_field(
            name="📊 Available Jobs",
            value=f"✅ **{unlocked}** unlocked\n🔒 **{locked}** locked",
            inline=True,
        )

        embed.add_field(
            name="Tip",
            value="Level up to unlock better jobs with higher pay!",
            inline=True,
        )

        embed.set_footer(text="Select a category from the dropdown below")
        embed.set_thumbnail(url=self.user.display_avatar.url)
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This isn't your job application!", ephemeral=True)
            return False
        return True


class JobCategoryMenu(discord.ui.Select):
    """Dropdown for choosing a job category."""

    def __init__(self, view: JobCategoryView):
        self.parent_view = view

        options: List[discord.SelectOption] = []
        for cat_id, cat_data in JOB_CATEGORIES.items():
            count = len(view.jobs_by_category.get(cat_id, []))
            options.append(
                discord.SelectOption(
                    label=cat_data["name"],
                    value=cat_id,
                    description=f"{count} job(s) • {cat_data.get('description', '')}"[:100],
                    emoji=cat_data.get("emoji"),
                )
            )

        super().__init__(
            placeholder="Choose a job category...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        jobs = list(self.parent_view.jobs_by_category.get(category, []))

        cat = JOB_CATEGORIES.get(category, {"name": category.title(), "color": JOB_COLORS["work"], "emoji": "💼"})

        embed = discord.Embed(
            title=f"{cat.get('emoji', '💼')} {cat.get('name', category.title())} Jobs",
            description=(
                f"**Your Level:** {self.parent_view.user_level}\n"
                f"**Current Job:** {self.parent_view.current_job}\n\n"
                "Select a job from the dropdown to view details and apply!"
            ),
            color=cat.get("color", JOB_COLORS["work"]),
        )
        embed.set_footer(text="Select a job from the dropdown below")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        view = JobListView(
            self.parent_view.bot,
            interaction.user,
            jobs,
            user_level=self.parent_view.user_level,
            current_job=self.parent_view.current_job,
            all_jobs=self.parent_view.available_jobs,
        )
        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.edit_message(view=view)


class JobListView(discord.ui.LayoutView):
    """Job picker for a single category (<=25 options), with a Back button."""

    def __init__(
        self,
        bot,
        user: discord.User,
        jobs: List[Dict],
        *,
        user_level: int,
        current_job: str,
        all_jobs: List[Dict],
    ):
        super().__init__(timeout=180)
        self.bot = bot
        self.user = user
        self.jobs = jobs
        self.user_level = user_level
        self.current_job = current_job
        self.all_jobs = all_jobs

        if jobs:
            self.add_item(JobSelectMenu(bot, jobs))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This isn't your job application!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = JobCategoryView(
            self.bot,
            interaction.user,
            self.all_jobs,
            user_level=self.user_level,
            current_job=self.current_job,
        )
        embed = view.create_embed()
        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.edit_message(view=view)


class JobSelectMenu(discord.ui.Select):
    """Dropdown menu for selecting jobs."""

    def __init__(self, bot, jobs: List[Dict]):
        self.bot = bot
        self.jobs_data = {job["id"]: job for job in jobs}
        
        # Create options (max 25)
        options = []
        for job in jobs[:25]:  # Discord limit
            pay_min, pay_max = job["pay_range"]
            
            # Build description
            description = f"💰 ${pay_min}-${pay_max} | ⚡ {job['energy_cost']} energy"
            if not job["can_apply"]:
                description = f"🔒 Requires Lv.{job['level_required']}"
            
            options.append(
                discord.SelectOption(
                    label=job["name"],
                    value=job["id"],
                    description=description[:100],
                    emoji=job.get("emoji", "💼")
                )
            )
        
        super().__init__(
            placeholder="Select a job to apply for...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_id = self.values[0]
        job_data = self.jobs_data[selected_id]
        
        # Show job details with apply confirmation
        view = JobConfirmView(self.bot, interaction.user, selected_id, job_data)
        embed = view.create_embed()
        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.edit_message(view=view)


class JobConfirmView(discord.ui.LayoutView):
    """Confirmation view for applying to a job."""

    def __init__(self, bot, user: discord.User, job_id: str, job_data: Dict):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.job_id = job_id
        self.job_data = job_data

    def create_embed(self) -> discord.Embed:
        full_job_data = JOBS.get(self.job_id)
        pay_min, pay_max = self.job_data["pay_range"]
        
        can_apply = self.job_data["can_apply"]
        
        if can_apply:
            embed = discord.Embed(
                title=f"📝 Apply for {self.job_data['name']}?",
                description=full_job_data["description"],
                color=JOB_COLORS.get(full_job_data["category"], JOB_COLORS["work"])
            )
        else:
            embed = discord.Embed(
                title=f"🔒 {self.job_data['name']} - Locked",
                description=f"{full_job_data['description']}\n\n**You need to reach level {self.job_data['level_required']} first!**",
                color=discord.Color.red()
            )

        embed.add_field(
            name="💰 Salary",
            value=f"{money(pay_min)} - {money(pay_max)}\nper shift",
            inline=True
        )

        embed.add_field(
            name="⚡ Energy Cost",
            value=f"{self.job_data['energy_cost']}\nper shift",
            inline=True
        )

        embed.add_field(
            name="📊 Requirements",
            value=f"**Level:** {self.job_data['level_required']}\n**Category:** {full_job_data['category'].title()}",
            inline=True
        )

        skill = full_job_data.get("skill", "intelligence")
        embed.add_field(
            name=f"{SKILL_EMOJIS.get(skill, '⚔️')} Primary Skill",
            value=f"**{skill.title()}**\nTrain this to earn more!",
            inline=True
        )

        embed.add_field(
            name="🎮 Minigame",
            value=f"**{full_job_data.get('minigame', 'sequence').title()}**",
            inline=True
        )

        embed.add_field(
            name="⭐ XP Reward",
            value=f"{full_job_data['xp_reward']} XP",
            inline=True
        )

        if can_apply:
            embed.set_footer(text="Click 'Apply Now' to get hired!")
        else:
            embed.set_footer(text="Level up to unlock this job!")

        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    @staticmethod
    def _result_layout(embed: discord.Embed) -> discord.ui.LayoutView:
        view = discord.ui.LayoutView(timeout=None)
        apply_v2_embed_layout(view, embed=embed)
        return view

    @discord.ui.button(label="Apply Now", style=discord.ButtonStyle.success, emoji="✅")
    async def apply_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.job_data["can_apply"]:
            return await interaction.response.send_message(
                f"❌ You need level {self.job_data['level_required']} to apply for this job!",
                ephemeral=True
            )

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        current_job = u.get("current_job", "Unemployed")
        full_job_data = JOBS.get(self.job_id)

        # Check if already has this job
        if current_job == full_job_data["name"]:
            return await interaction.response.send_message(
                f"❌ You already work as a **{full_job_data['name']}**!",
                ephemeral=True
            )

        # Apply for job
        db.updatejob(userid, full_job_data["name"])
        db.updatestat(userid, "job_level", 1)
        db.updatestat(userid, "job_xp", 0)

        pay_min, pay_max = full_job_data["pay"]

        embed = discord.Embed(
            title="✅ Application Accepted!",
            description=f"Congratulations! You've been hired as a **{full_job_data['name']}**!",
            color=JOB_COLORS["success"]
        )

        embed.add_field(
            name="💰 Salary",
            value=f"{money(pay_min)} - {money(pay_max)} per shift",
            inline=True
        )

        embed.add_field(
            name="⚡ Energy Cost",
            value=f"{full_job_data['energy_cost']} per shift",
            inline=True
        )

        embed.add_field(
            name="📊 Job Level",
            value="Level 1 (starter)",
            inline=True
        )

        embed.add_field(
            name="📝 Your New Role",
            value=full_job_data["description"],
            inline=False
        )

        skill = full_job_data.get("skill", "intelligence")
        embed.add_field(
            name=f"{SKILL_EMOJIS.get(skill, '⚔️')} Primary Skill",
            value=f"**{skill.title()}**\nTrain this skill to perform better!",
            inline=True
        )

        embed.add_field(
            name="🎮 Work Type",
            value=f"**{full_job_data.get('minigame', 'sequence').title()}** minigame",
            inline=True
        )

        if current_job != "Unemployed":
            embed.set_footer(text=f"You quit your job as {current_job} • Use /work to start your new job!")
        else:
            embed.set_footer(text="Use /work to start your first shift!")

        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.response.edit_message(view=self._result_layout(embed))
        self.stop()

    @discord.ui.button(label="View Other Jobs", style=discord.ButtonStyle.secondary, emoji="🔍")
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Go back to job list
        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        user_level = int(u.get("level", 1))
        available_jobs = []

        for job_id, job_data in JOBS.items():
            pay_min, pay_max = job_data["pay"]
            can_apply = user_level >= job_data["level_required"]

            available_jobs.append({
                "id": job_id,
                "name": job_data["name"],
                "category": job_data.get("category", "entry"),
                "pay_range": (pay_min, pay_max),
                "energy_cost": job_data["energy_cost"],
                "level_required": job_data["level_required"],
                "can_apply": can_apply,
                "emoji": "✅" if can_apply else "🔒"
            })

        # Sort by level requirement
        available_jobs.sort(key=lambda x: x["level_required"])

        embed = discord.Embed(
            title="💼 Job Opportunities",
            description=f"**Your Level:** {user_level}\n\nSelect a job to view details and apply:",
            color=JOB_COLORS["work"]
        )
        embed.set_footer(text="💡 Higher level = access to better jobs")

        view = JobApplicationView(self.bot, interaction.user, available_jobs)
        apply_v2_embed_layout(view, embed=embed)
        await interaction.response.edit_message(view=view)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Application Cancelled",
            description="You didn't apply for any job.",
            color=discord.Color.greyple()
        )
        await interaction.response.edit_message(view=self._result_layout(embed))
        self.stop()


# ============= MAIN COG =============

class JobsCog(commands.Cog):
    """Job commands: jobs, apply, work, quit."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="jobs", description="💼 View available jobs")
    @app_commands.describe(category="Filter by job category")
    @app_commands.choices(category=[
        app_commands.Choice(name="📋 All Jobs", value="all"),
        app_commands.Choice(name="🔰 Entry Level", value="entry"),
        app_commands.Choice(name="⭐ Skilled", value="skilled"),
        app_commands.Choice(name="💼 Professional", value="professional"),
        app_commands.Choice(name="👑 Expert", value="expert"),
        app_commands.Choice(name="💎 Elite", value="elite"),
    ])
    async def jobs(self, interaction: discord.Interaction, category: str = "all"):
        """Browse available jobs."""
        await safe_defer(interaction, ephemeral=True)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        user_level = int(u.get("level", 1))
        current_job = u.get("current_job", "Unemployed")
        job_level = int(u.get("job_level", 1))

        # Filter jobs
        filtered_jobs = {}
        for job_id, job_data in JOBS.items():
            if category != "all" and job_data["category"] != category:
                continue
            filtered_jobs[job_id] = job_data

        if not filtered_jobs:
            return await safe_reply(
                interaction,
                content="❌ No jobs found in that category!",
                ephemeral=True
            )

        color = JOB_COLORS.get(category, JOB_COLORS["work"])

        embed = discord.Embed(
            title="💼 Job Opportunities",
            description=(
                f"**Your Level:** {user_level}\n"
                f"**Current Job:** {current_job} (Lv.{job_level})\n"
                f"**Filter:** {category.title() if category != 'all' else 'All Categories'}"
            ),
            color=color
        )

        # Group by category
        for cat_id, cat_data in JOB_CATEGORIES.items():
            if category != "all" and category != cat_id:
                continue

            jobs_in_cat = [j for j in filtered_jobs.values() if j["category"] == cat_id]
            if not jobs_in_cat:
                continue

            job_lines = []
            for job in sorted(jobs_in_cat, key=lambda x: x["level_required"]):
                job_name = job["name"]
                pay_min, pay_max = job["pay"]
                level_req = job["level_required"]
                energy = job["energy_cost"]
                skill = job.get("skill", "intelligence")

                can_apply = user_level >= level_req
                status_emoji = "✅" if can_apply else "🔒"
                status_text = "" if can_apply else f" • Requires Lv.{level_req}"

                job_lines.append(
                    f"{status_emoji} **{job_name}**{status_text}\n"
                    f"└ 💰 {money(pay_min)}-{money(pay_max)} • ⚡ {energy} energy • {SKILL_EMOJIS.get(skill, '⚔️')} {skill.title()}"
                )

            if job_lines:
                embed.add_field(
                    name=f"{cat_data['emoji']} {cat_data['name']}",
                    value="\n".join(job_lines),
                    inline=False
                )

        embed.add_field(
            name="💡 How to Apply",
            value=(
                "• Use `/apply` to see interactive job selector\n"
                "• Higher level = access to better jobs\n"
                "• Train skills to perform better at work"
            ),
            inline=False
        )

        embed.set_footer(text="💼 Use /apply to browse and get hired • /work to start working")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await safe_reply(interaction, embed=embed, ephemeral=True)

    @app_commands.command(name="apply", description="📝 Apply for a job (interactive)")
    async def apply(self, interaction: discord.Interaction):
        """Apply for a job - shows interactive selector."""
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        user_level = int(u.get("level", 1))
        current_job = u.get("current_job", "Unemployed")

        # Get all available jobs
        available_jobs = []

        for job_id, job_data in JOBS.items():
            pay_min, pay_max = job_data["pay"]
            can_apply = user_level >= job_data["level_required"]

            available_jobs.append({
                "id": job_id,
                "name": job_data["name"],
                "pay_range": (pay_min, pay_max),
                "energy_cost": job_data["energy_cost"],
                "level_required": job_data["level_required"],
                "can_apply": can_apply,
                "emoji": "✅" if can_apply else "🔒"
            })

        # Sort: unlocked first, then by level requirement
        available_jobs.sort(key=lambda x: (not x["can_apply"], x["level_required"]))

        embed = discord.Embed(
            title="💼 Job Application",
            description=(
                f"**Your Level:** {user_level}\n"
                f"**Current Job:** {current_job}\n\n"
                f"Select a job from the dropdown to view details and apply!"
            ),
            color=JOB_COLORS["work"]
        )

        # Show stats
        unlocked = sum(1 for j in available_jobs if j["can_apply"])
        locked = len(available_jobs) - unlocked

        embed.add_field(
            name="📊 Available Jobs",
            value=f"✅ **{unlocked}** unlocked\n🔒 **{locked}** locked",
            inline=True
        )

        embed.add_field(
            name="💡 Tip",
            value="Level up to unlock better jobs with higher pay!",
            inline=True
        )

        embed.set_footer(text="Select a job from the dropdown below")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        view = JobCategoryView(
            self.bot,
            interaction.user,
            available_jobs,
            user_level=user_level,
            current_job=current_job,
        )
        await safe_reply(interaction, embed=view.create_embed(), view=view)

    @app_commands.command(name="work", description="⚙️ Work your job (play a minigame!)")
    async def work(self, interaction: discord.Interaction):
        """Work your current job."""
        await safe_defer(interaction, ephemeral=False)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        # Check hospital
        hospital_msg = check_in_hospital(u)
        if hospital_msg:
            return await safe_reply(interaction, content=hospital_msg)

        # Check jail
        jail_msg = check_in_jail(u)
        if jail_msg:
            return await safe_reply(interaction, content=jail_msg)

        # Check cooldown
        last_work = u.get("last_work")
        can_work, remaining = check_cooldown(last_work, WORK_COOLDOWN)

        if not can_work:
            embed = discord.Embed(
                title="⏰ Still Tired",
                description=(
                    f"{interaction.user.mention} needs rest!\n\n"
                    f"**Time Remaining:** {format_time(remaining)}\n"
                    "Use `/sleep` to restore energy faster!"
                ),
                color=discord.Color.orange()
            )
            embed.set_footer(text=f"Work cooldown: {WORK_COOLDOWN // 3600} hour(s)")
            return await safe_reply(interaction, embed=embed)

        # Check if has job
        current_job = u.get("current_job", "Unemployed")
        if current_job == "Unemployed":
            embed = discord.Embed(
                title="❌ No Job",
                description=(
                    f"{interaction.user.mention} doesn't have a job!\n\n"
                    "Use `/apply` to browse available positions."
                ),
                color=JOB_COLORS["quit"]
            )
            return await safe_reply(interaction, embed=embed)

        # Find job data
        job_id = None
        job_data = None
        for jid, jdata in JOBS.items():
            if jdata["name"] == current_job:
                job_id = jid
                job_data = jdata
                break

        if not job_data:
            return await safe_reply(
                interaction,
                content="❌ Job data error! Please reapply with `/apply`."
            )

        # Check user stats
        issues = check_user_stats(u, energy_needed=job_data["energy_cost"])
        if issues:
            embed = discord.Embed(
                title="❌ Can't Work",
                description=f"{interaction.user.mention}\n\n" + "\n".join(issues),
                color=JOB_COLORS["quit"]
            )
            embed.add_field(
                name="💡 How to Fix",
                value=(
                    "• Use `/sleep` to restore energy\n"
                    "• Use `/eat` to restore hunger\n"
                    "• Wait for health to regenerate"
                ),
                inline=False
            )
            return await safe_reply(interaction, embed=embed)

        # Get stats
        user_level = int(u.get("level", 1))
        job_level = int(u.get("job_level", 1))
        skill_name = job_data.get("skill", "intelligence")
        skill_value = int(u.get(f"skill_{skill_name}", 0))

        # Start minigame
        minigame = get_job_minigame(job_id, job_data, job_level)

        if not minigame:
            return await safe_reply(
                interaction,
                content="❌ Minigame error! Please try again."
            )

        try:
            await minigame.start_game(interaction)
            await minigame.wait()
        except Exception as e:
            logger.exception("Minigame error in /work")
            return await safe_reply(
                interaction,
                content="Minigame error. Please try `/work` again.",
            )
            print(f"[MINIGAME ERROR] {e}")
            import traceback
            traceback.print_exc()
            return await interaction.followup.send(
                f"❌ Minigame error: {e}\nPlease try again!"
            )

        # Calculate results
        performance_multiplier, performance_msg, performance_color = minigame.calculate_performance()

        pay_min, pay_max = job_data["pay"]
        skill_bonus = skill_value / 200

        base_earnings = calculate_work_earnings(
            pay_min,
            pay_max,
            user_level,
            job_level,
            skill_bonus,
        )

        final_earnings = int(base_earnings * performance_multiplier)

        xp_gained = calculate_work_xp(
            job_data["xp_reward"],
            performance_multiplier,
            job_level,
        )
        job_xp_gained = calculate_job_xp(20, performance_multiplier)
        skill_xp = SKILL_XP_WORK

        # Update database
        db.addbalance(userid, final_earnings)
        db.addxp(userid, xp_gained)
        db.add_skill_xp(userid, skill_name, skill_xp)

        current_job_xp = int(u.get("job_xp", 0))
        new_job_xp = current_job_xp + job_xp_gained
        db.updatestat(userid, "job_xp", new_job_xp)

        old_job_level, _, _ = get_job_level_from_xp(current_job_xp)
        new_job_level, curr_xp, needed_xp = get_job_level_from_xp(new_job_xp)

        leveled_up = new_job_level > old_job_level
        if leveled_up:
            db.updatestat(userid, "job_level", new_job_level)

        db.updatestat(
            userid,
            "energy",
            int(u.get("energy", 100)) - job_data["energy_cost"],
        )
        db.updatelastwork(userid, datetime.now(timezone.utc).isoformat())
        db.increment_work_count(userid)

        # Create result embed
        result_embed = discord.Embed(
            title=f"⚙️ Work Shift Complete!",
            description=f"{interaction.user.mention} finished working as a **{current_job}**",
            color=performance_color
        )

        result_embed.add_field(
            name="🎯 Performance",
            value=f"**{performance_msg}**\n{performance_multiplier:.0%} multiplier",
            inline=False
        )

        result_embed.add_field(
            name="💰 Earnings",
            value=f"**{money(final_earnings)}**",
            inline=True
        )

        result_embed.add_field(
            name="⭐ XP Gained",
            value=f"**+{xp_gained}**",
            inline=True
        )

        result_embed.add_field(
            name=f"{SKILL_EMOJIS.get(skill_name, '⚔️')} Skill XP",
            value=f"**+{skill_xp}** {skill_name.title()}",
            inline=True
        )

        if leveled_up:
            result_embed.add_field(
                name="🎉 Job Level Up!",
                value=f"**Level {old_job_level}** → **Level {new_job_level}**\n💰 Earnings increased!",
                inline=False
            )
        else:
            progress = progress_bar(curr_xp, needed_xp, length=10)
            result_embed.add_field(
                name="📊 Job Progress",
                value=f"**Level {new_job_level}**\n{progress} {curr_xp}/{needed_xp} XP",
                inline=False
            )

        result_embed.add_field(
            name="📈 Minigame Stats",
            value=f"**Score:** {minigame.score}/{minigame.max_score}",
            inline=True
        )

        result_embed.add_field(
            name="⏰ Cooldown",
            value=f"{WORK_COOLDOWN // 3600} hour(s)",
            inline=True
        )

        new_energy = int(u.get("energy", 100)) - job_data["energy_cost"]
        result_embed.add_field(
            name="⚡ Energy",
            value=f"{new_energy}% remaining",
            inline=True
        )

        result_embed.set_thumbnail(url=interaction.user.display_avatar.url)
        result_embed.set_footer(text=f"Job: {current_job} Lv.{new_job_level} • Keep working to level up!")

        await interaction.followup.send(embed=result_embed)

    @app_commands.command(name="shift", description="Alias for /work")
    async def shift(self, interaction: discord.Interaction):
        """Alias for /work."""
        return await self.work.callback(self, interaction)

    @app_commands.command(name="quit", description="🚪 Quit your current job")
    async def quit(self, interaction: discord.Interaction):
        """Quit your current job."""
        await safe_defer(interaction)

        db = self.bot.db
        userid = str(interaction.user.id)
        u = db.getuser(userid)

        current_job = u.get("current_job", "Unemployed")
        job_level = int(u.get("job_level", 1))
        job_xp = int(u.get("job_xp", 0))

        if current_job == "Unemployed":
            return await safe_reply(
                interaction,
                content="❌ You don't have a job to quit!"
            )

        # Quit job
        db.updatejob(userid, "Unemployed")
        db.updatestat(userid, "job_level", 1)
        db.updatestat(userid, "job_xp", 0)

        embed = discord.Embed(
            title="🚪 Job Resignation",
            description=f"You quit your job as a **{current_job}**.",
            color=JOB_COLORS["quit"]
        )

        embed.add_field(
            name="📊 Final Stats",
            value=(
                f"**Level:** {job_level}\n"
                f"**Total XP:** {job_xp:,}"
            ),
            inline=True
        )

        embed.add_field(
            name="💡 What's Next?",
            value=(
                "Use `/apply` to find a new job\n"
                "Your character level and skills are saved!"
            ),
            inline=True
        )

        embed.set_footer(text="You can reapply for this job anytime!")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await safe_reply(interaction, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(JobsCog(bot))
