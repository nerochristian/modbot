# services/economy_service.py
import math
import random
from datetime import datetime, timedelta
from services.base_service import BaseService
from utils.constants import EconomyConfig, Colors, Emojis
from utils.format import format_currency

class EconomyService(BaseService):
    def __init__(self):
        super().__init__("economy")

    # -------------------------------------------------------------------------
    # USER ACCOUNT MANAGEMENT
    # -------------------------------------------------------------------------

    async def ensure_account(self, user_id: int):
        """Ensures the user has a bank account. Creates one if not."""
        return await self._ensure_record(
            table="users",
            key_col="user_id",
            key_val=user_id,
            defaults={
                "balance": EconomyConfig.STARTING_BALANCE,
                "bank": EconomyConfig.STARTING_BANK,
                "bank_limit": EconomyConfig.STARTING_BANK_LIMIT,
                "net_worth": EconomyConfig.STARTING_BALANCE,
                "created_at": datetime.now()
            }
        )

    async def get_user_profile(self, user_id: int):
        """
        Fetches the complete financial profile of a user.
        Calculates dynamic Net Worth on the fly.
        """
        await self.ensure_account(user_id)
        
        # 1. Get Basic Data
        user = await self.db.fetch_one("SELECT * FROM users WHERE user_id = ?", user_id)
        if not user:
            return None # Should not happen due to ensure_account

        # 2. Calculate Asset Value (Inventory + Stocks + Businesses)
        # We wrap these in try-except to prevent crashes if tables are empty/locked
        try:
            # Inventory Value
            inv_val_query = """
                SELECT SUM(i.quantity * it.price) as total 
                FROM inventory i
                -- Join with a hypothetical items definition table or verify later
                -- For now we assume a raw calculation or integration with ItemService
                LEFT JOIN (SELECT 'placeholder' as item_id, 0 as price) it ON i.item_id = it.item_id
            """
            # Note: Since item prices are usually in code (data/items.py), we might need
            # to fetch inventory and sum it up in Python.
            # For efficiency in this file, we will rely on stored 'net_worth' column
            # but trigger a recalculation occasionally.
            pass 
        except Exception as e:
            self.logger.warning(f"Failed to calc asset value: {e}")

        return dict(user)

    # -------------------------------------------------------------------------
    # TRANSACTION HANDLING
    # -------------------------------------------------------------------------

    async def modify_balance(self, user_id: int, amount: int, transaction_type: str, description: str):
        """
        The SAFEST way to add or remove money.
        - Checks funds.
        - Updates DB.
        - Logs transaction.
        - Returns Success/Failure object.
        """
        await self.ensure_account(user_id)
        
        if amount == 0:
            return {"success": False, "error": "Amount cannot be zero."}

        # Fetch current state
        user = await self.db.fetch_one("SELECT balance FROM users WHERE user_id = ?", user_id)
        current_bal = user['balance']

        # Validation for deduction
        if amount < 0 and current_bal + amount < 0:
            return {"success": False, "error": "Insufficient funds."}

        # Execute Transaction
        new_bal = current_bal + amount
        await self.db.execute("UPDATE users SET balance = ? WHERE user_id = ?", new_bal, user_id)
        
        # Update Net Worth (Simplified)
        await self.update_net_worth(user_id)

        # Audit Log
        await self.log_transaction(user_id, amount, transaction_type, description)

        return {
            "success": True, 
            "new_balance": new_bal, 
            "amount": amount,
            "formatted": format_currency(new_bal)
        }

    async def log_transaction(self, user_id: int, amount: int, type: str, desc: str):
        """Records every single coin movement for audit/support."""
        await self.db.execute(
            """INSERT INTO transactions (user_id, amount, type, description, timestamp) 
               VALUES (?, ?, ?, ?, ?)""",
            user_id, amount, type, desc, datetime.now()
        )

    # -------------------------------------------------------------------------
    # BANKING SYSTEM
    # -------------------------------------------------------------------------

    async def deposit(self, user_id: int, amount_str: str):
        """
        Moves money from Wallet -> Bank.
        Handles 'all', 'half', 'max' keywords.
        """
        await self.ensure_account(user_id)
        user = await self.get_user_profile(user_id)
        
        wallet = user['balance']
        bank = user['bank']
        limit = user['bank_limit']

        # Parse Amount
        if str(amount_str).lower() in ['all', 'max']:
            amount = wallet
        elif str(amount_str).lower() == 'half':
            amount = wallet // 2
        else:
            try:
                amount = int(amount_str)
            except ValueError:
                return {"success": False, "error": "Invalid amount."}

        # Logic Checks
        if amount <= 0:
            return {"success": False, "error": "Amount must be positive."}
        if amount > wallet:
            return {"success": False, "error": "You don't have that much cash."}
        
        # Capacity Check
        space_available = limit - bank
        if space_available <= 0:
            return {"success": False, "error": "Your bank account is full! Upgrade it."}
        
        # Cap amount to available space
        final_deposit = min(amount, space_available)
        
        # Execute
        await self.db.execute(
            "UPDATE users SET balance = balance - ?, bank = bank + ? WHERE user_id = ?",
            final_deposit, final_deposit, user_id
        )
        
        return {
            "success": True, 
            "amount": final_deposit, 
            "capped": final_deposit < amount,
            "new_bank": bank + final_deposit
        }

    async def withdraw(self, user_id: int, amount_str: str):
        """Moves money from Bank -> Wallet."""
        await self.ensure_account(user_id)
        user = await self.get_user_profile(user_id)
        
        bank = user['bank']

        if str(amount_str).lower() in ['all', 'max']:
            amount = bank
        else:
            try:
                amount = int(amount_str)
            except ValueError:
                return {"success": False, "error": "Invalid amount."}

        if amount <= 0:
            return {"success": False, "error": "Amount must be positive."}
        if amount > bank:
            return {"success": False, "error": "You don't have that much in the bank."}

        await self.db.execute(
            "UPDATE users SET balance = balance + ?, bank = bank - ? WHERE user_id = ?",
            amount, amount, user_id
        )
        
        return {"success": True, "amount": amount}

    # -------------------------------------------------------------------------
    # TRANSFER SYSTEM
    # -------------------------------------------------------------------------

    async def transfer(self, sender_id: int, receiver_id: int, amount: int):
        """
        Secure P2P transfer.
        Applies Taxes defined in constants.
        Prevents negative transfers or self-transfers.
        """
        if sender_id == receiver_id:
            return {"success": False, "error": "You cannot pay yourself."}
        
        if amount < EconomyConfig.TRANSFER_MIN:
            return {"success": False, "error": f"Minimum transfer is {EconomyConfig.TRANSFER_MIN}."}

        # Check Sender Funds
        sender = await self.get_user_profile(sender_id)
        if sender['balance'] < amount:
            return {"success": False, "error": "Insufficient funds."}
        
        # Calculate Tax
        tax = int(amount * EconomyConfig.TAX_RATE)
        final_amount = amount - tax
        
        # ATOMIC TRANSACTION SIMULATION
        # In a real SQL server we'd use BEGIN TRANSACTION, here we chain logical checks
        
        # 1. Deduct from Sender
        await self.modify_balance(sender_id, -amount, "transfer_out", f"Transfer to {receiver_id}")
        
        # 2. Add to Receiver
        await self.modify_balance(receiver_id, final_amount, "transfer_in", f"Transfer from {sender_id}")
        
        # 3. (Optional) Pay Tax to Bot/Government
        # await self.modify_balance(bot_id, tax, "tax_collection", ...)

        return {
            "success": True,
            "amount_sent": amount,
            "tax_paid": tax,
            "amount_received": final_amount
        }

    # -------------------------------------------------------------------------
    # UTILITIES & REWARDS
    # -------------------------------------------------------------------------

    async def claim_daily(self, user_id: int):
        """
        Handles Daily Reward logic.
        Calculates streak bonuses and resets streak if missed.
        """
        await self.ensure_account(user_id)
        user = await self.db.fetch_one("SELECT last_daily, daily_streak FROM users WHERE user_id = ?", user_id)
        
        now = datetime.now()
        last_daily = user['last_daily']
        streak = user['daily_streak']

        # Time Logic
        if last_daily:
            last_date = datetime.strptime(str(last_daily), "%Y-%m-%d %H:%M:%S.%f") if "." in str(last_daily) else datetime.strptime(str(last_daily), "%Y-%m-%d %H:%M:%S")
            diff = now - last_date
            
            # Cooldown check
            if diff.total_seconds() < EconomyConfig.DAILY_COOLDOWN_SECONDS: # e.g. 20 hours
                remaining = EconomyConfig.DAILY_COOLDOWN_SECONDS - diff.total_seconds()
                return {"success": False, "remaining_seconds": remaining}
            
            # Streak Logic (48 hours grace period usually)
            if diff.total_seconds() > 48 * 3600:
                streak = 0
            else:
                streak += 1
        else:
            streak = 1
            
        # Cap streak
        streak = min(streak, EconomyConfig.MAX_STREAK)
        
        # Calculate Prize
        prize = EconomyConfig.DAILY_BASE + (streak * EconomyConfig.DAILY_STREAK_BONUS)
        
        # Update DB
        await self.db.execute(
            "UPDATE users SET balance = balance + ?, last_daily = ?, daily_streak = ? WHERE user_id = ?",
            prize, now, streak, user_id
        )
        
        return {
            "success": True,
            "amount": prize,
            "streak": streak,
            "bonus": streak * EconomyConfig.DAILY_STREAK_BONUS
        }

    async def update_net_worth(self, user_id: int):
        """
        Recalculates Net Worth: Wallet + Bank.
        (Future: + Stocks + Business + Inventory Value)
        """
        # This is a simplified query. In the full version, this query becomes huge.
        query = """
        UPDATE users 
        SET net_worth = balance + bank 
        WHERE user_id = ?
        """
        await self.db.execute(query, user_id)

# Initialize singleton
economy_service = EconomyService()