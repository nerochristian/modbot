# services/jobs_service.py
import math
import random
from services.base_service import BaseService
from services.economy_service import economy_service
from utils.constants import JobConfig


def calculate_work_earnings(
    pay_min: int,
    pay_max: int,
    user_level: int,
    job_level: int,
    skill_bonus: float = 0.0,
) -> int:
    """Calculate base earnings for a work shift before minigame multipliers."""
    base = random.randint(int(pay_min), int(pay_max))
    user_mult = 1.0 + max(0, user_level - 1) * 0.02
    job_mult = 1.0 + max(0, job_level - 1) * 0.05
    skill_mult = 1.0 + max(0.0, float(skill_bonus))
    return int(base * user_mult * job_mult * skill_mult)


def calculate_work_xp(base_xp: int, performance_multiplier: float, job_level: int) -> int:
    """Calculate XP gain from working."""
    level_mult = 1.0 + max(0, job_level - 1) * 0.01
    return max(1, int(base_xp * float(performance_multiplier) * level_mult))


def calculate_job_xp(base_xp: int, performance_multiplier: float) -> int:
    """Calculate job-specific XP gain (separate from character XP)."""
    return max(1, int(base_xp * float(performance_multiplier)))


def get_job_level_from_xp(total_xp: int, base: int = 100) -> tuple[int, int, int]:
    """
    Convert cumulative job XP into (level, current_xp, needed_xp).
    Uses an increasing threshold: needed = level * base.
    """
    try:
        xp = int(total_xp)
    except (TypeError, ValueError):
        xp = 0

    level = 1
    while xp >= level * base and level < 10_000:
        xp -= level * base
        level += 1

    needed = level * base
    return level, xp, needed

class JobsService(BaseService):
    def __init__(self):
        super().__init__("jobs")

    async def get_job_profile(self, user_id: int):
        """Fetches career stats."""
        # Ensure record exists
        await self._ensure_record(
            table="user_jobs",
            key_col="user_id",
            key_val=user_id,
            defaults={
                "job_id": "unemployed",
                "current_position": "None",
                "shifts_worked": 0,
                "promotions": 0,
                "salary_bonus_percent": 0
            }
        )
        return await self.db.fetch_one("SELECT * FROM user_jobs WHERE user_id = ?", user_id)

    async def quit_job(self, user_id: int):
        """Resets job status to unemployed but keeps general work stats."""
        await self.db.execute(
            "UPDATE user_jobs SET job_id = 'unemployed', current_position = 'None' WHERE user_id = ?",
            user_id
        )
        return True

    async def join_job(self, user_id: int, job_id: str):
        """
        Signs a user up for a new job.
        Requires data/jobs.py to verify requirements (handled in Cog usually).
        """
        current = await self.get_job_profile(user_id)
        if current['job_id'] != 'unemployed':
            return {"success": False, "error": "You already have a job. Quit first."}

        # Initialize new job state
        await self.db.execute(
            "UPDATE user_jobs SET job_id = ?, current_position = 'Intern', shifts_worked = 0 WHERE user_id = ?",
            job_id, user_id
        )
        return {"success": True, "job_id": job_id}

    async def work_shift(self, user_id: int):
        """
        Calculates payout for working.
        Includes Logic for: Base Pay + Promotion Bonus + Streak Bonus.
        """
        job_data = await self.get_job_profile(user_id)
        job_id = job_data['job_id']

        if job_id == 'unemployed':
            # Welfare check?
            return {"success": False, "error": "You are unemployed. Get a job!"}

        # 1. Calculate Base Pay
        # In a real scenario, we fetch base pay from data/jobs.py using job_id
        # For this service layer, we assume a standard calculation or lookup
        base_pay = JobConfig.BASE_PAY_PER_HOUR * 8 # Standard 8 hour shift
        
        # 2. Apply Bonuses
        bonus_pct = job_data['salary_bonus_percent']
        # Promotion multiplier (simple log scale or linear)
        promo_mult = 1 + (job_data['promotions'] * 0.1) 
        
        total_pay = int(base_pay * promo_mult * (1 + bonus_pct / 100))

        # 3. Update Economy
        await economy_service.modify_balance(user_id, total_pay, "salary", f"Worked shift as {job_id}")

        # 4. Update Job Progress
        new_shifts = job_data['shifts_worked'] + 1
        
        # Check for Promotion (Every 10 shifts for example)
        promoted = False
        if new_shifts % 10 == 0:
            promoted = True
            await self.promote_user(user_id)

        await self.db.execute(
            "UPDATE user_jobs SET shifts_worked = ?, last_worked = CURRENT_TIMESTAMP WHERE user_id = ?",
            new_shifts, user_id
        )
        
        return {
            "success": True,
            "pay": total_pay,
            "shifts": new_shifts,
            "promoted": promoted
        }

    async def promote_user(self, user_id: int):
        """Internal method to handle promotion logic."""
        await self.db.execute(
            "UPDATE user_jobs SET promotions = promotions + 1, salary_bonus_percent = salary_bonus_percent + 5 WHERE user_id = ?",
            user_id
        )
        # Notify user via return in work_shift

jobs_service = JobsService()
