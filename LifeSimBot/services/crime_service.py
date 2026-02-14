# services/crime_service.py
import random
import time
from datetime import datetime, timedelta
from services.base_service import BaseService
from services.economy_service import economy_service
from utils.constants import CrimeConfig, Cooldowns, Times

class CrimeService(BaseService):
    def __init__(self):
        super().__init__("crime")

    # -------------------------------------------------------------------------
    # STATE MANAGEMENT (Jail & Heat)
    # -------------------------------------------------------------------------

    async def get_criminal_profile(self, user_id: int):
        """Fetches criminal stats. Creates record if missing."""
        # Ensure base user exists first
        await economy_service.ensure_account(user_id)
        
        record = await self.db.fetch_one("SELECT * FROM criminal_records WHERE user_id = ?", user_id)
        if not record:
            await self.db.execute("INSERT INTO criminal_records (user_id) VALUES (?)", user_id)
            record = await self.db.fetch_one("SELECT * FROM criminal_records WHERE user_id = ?", user_id)
        return dict(record)

    async def check_jail_status(self, user_id: int):
        """
        Returns True if user is currently in jail.
        Auto-releases them if time is up.
        """
        record = await self.get_criminal_profile(user_id)
        release_time = record['jail_release_time']

        if not release_time:
            return False

        # Convert string timestamp to datetime
        if isinstance(release_time, str):
            release_dt = datetime.strptime(release_time, "%Y-%m-%d %H:%M:%S")
        else:
            release_dt = release_time

        if datetime.now() < release_dt:
            # Still in jail
            remaining = (release_dt - datetime.now()).total_seconds()
            return {"jailed": True, "remaining": remaining}
        
        # Time served: Release them
        await self.release_prisoner(user_id)
        return {"jailed": False}

    async def jail_user(self, user_id: int, duration_seconds: int):
        """Sends a user to jail."""
        release_time = datetime.now() + timedelta(seconds=duration_seconds)
        
        await self.db.execute(
            """UPDATE criminal_records 
               SET jail_release_time = ?, times_jailed = times_jailed + 1, heat_level = 0 
               WHERE user_id = ?""",
            release_time, user_id
        )
        self.logger.info(f"Jailed User {user_id} for {duration_seconds}s")

    async def release_prisoner(self, user_id: int):
        """Releases a user."""
        await self.db.execute(
            "UPDATE criminal_records SET jail_release_time = NULL WHERE user_id = ?", 
            user_id
        )

    # -------------------------------------------------------------------------
    # CRIME MECHANICS
    # -------------------------------------------------------------------------

    async def commit_crime(self, user_id: int, crime_type: str):
        """
        The Master Crime Function.
        Handles Robbery, Shoplifting, Heists, etc.
        """
        # 1. Check Jail Status
        status = await self.check_jail_status(user_id)
        if status['jailed']:
            return {"success": False, "jailed": True, "remaining": status['remaining']}

        # 2. Fetch User Stats
        user = await economy_service.get_user_profile(user_id)
        record = await self.get_criminal_profile(user_id)
        
        # 3. Determine Difficulty & Payouts based on type
        if crime_type == "shoplift":
            base_chance = CrimeConfig.SHOPLIFT_SUCCESS_BASE
            payout_min, payout_max = 50, 200
            jail_time = CrimeConfig.JAIL_MIN
            fine_pct = CrimeConfig.FINE_PERCENT_MIN
            
        elif crime_type == "rob":
            base_chance = CrimeConfig.ROB_SUCCESS_BASE
            payout_min, payout_max = 500, 1500
            jail_time = CrimeConfig.JAIL_MIN * 2
            fine_pct = CrimeConfig.FINE_PERCENT_MAX
            
        elif crime_type == "heist":
            base_chance = CrimeConfig.HEIST_SUCCESS_BASE
            payout_min, payout_max = 10000, 50000
            jail_time = CrimeConfig.JAIL_MAX
            fine_pct = 0.50 # Lose 50% if caught in heist!
            
        else:
            return {"success": False, "error": "Unknown crime type"}

        # 4. Modifiers (Items, Heat, etc.)
        # TODO: Check inventory for 'Lockpick' (+10% chance) or 'Disguise' (-Heat)
        # heat_penalty = record['heat_level'] * 0.05
        # chance = base_chance - heat_penalty
        chance = base_chance # Simplified for now

        # 5. Roll the Dice
        roll = random.random() # 0.0 to 1.0
        
        if roll < chance:
            # SUCCESS
            payout = random.randint(payout_min, payout_max)
            
            # Add Money
            await economy_service.modify_balance(user_id, payout, "crime_reward", f"Successful {crime_type}")
            
            # Increase Heat
            await self.db.execute(
                "UPDATE criminal_records SET crimes_committed = crimes_committed + 1, heat_level = heat_level + 1 WHERE user_id = ?",
                user_id
            )
            
            return {
                "success": True,
                "payout": payout,
                "message": f"You successfully committed {crime_type} and got {payout} coins!"
            }
            
        else:
            # FAILURE - GET CAUGHT
            wallet = user['balance']
            fine = int(wallet * fine_pct)
            
            # Deduct Fine
            if fine > 0:
                await economy_service.modify_balance(user_id, -fine, "crime_fine", f"Caught for {crime_type}")
            
            # Send to Jail
            await self.jail_user(user_id, jail_time)
            
            return {
                "success": False,
                "fine": fine,
                "jail_time": jail_time,
                "message": f"You were caught! You paid a fine of {fine} and were sent to jail."
            }

crime_service = CrimeService()