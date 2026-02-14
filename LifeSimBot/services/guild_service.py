# services/guilds_service.py
from __future__ import annotations

from typing import Dict, List, Any, Tuple
import json
import random
import string


def generate_guild_id() -> str:
    """Generate unique guild ID."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def calculate_guild_level(xp: int) -> Tuple[int, int, int]:
    """Calculate guild level from XP. Returns (level, current_xp, xp_needed)."""
    BASE_XP = 1000
    MULTIPLIER = 1.5
    
    level = 1
    total_needed = 0
    
    while level < 100:
        xp_for_next = int(BASE_XP * (MULTIPLIER ** (level - 1)))
        if total_needed + xp_for_next > xp:
            current_xp = xp - total_needed
            return level, current_xp, xp_for_next
        total_needed += xp_for_next
        level += 1
    
    return 100, 0, 0


def get_guild_perks(level: int) -> List[str]:
    """Get unlocked guild perks based on level."""
    perks = []
    
    if level >= 5:
        perks.append("💰 +5% work earnings for all members")
    if level >= 10:
        perks.append("⭐ +10% XP boost for all members")
    if level >= 15:
        perks.append("🎰 +5% casino winnings")
    if level >= 20:
        perks.append("🔪 +10% crime success rate")
    if level >= 25:
        perks.append("💼 +15% job earnings")
    if level >= 30:
        perks.append("🏆 Access to guild wars")
    if level >= 50:
        perks.append("👑 Legendary guild status")
    
    return perks


def calculate_guild_bonuses(guild_level: int) -> Dict[str, int]:
    """Calculate active bonuses from guild level."""
    bonuses = {
        "work_bonus": 0,
        "xp_bonus": 0,
        "casino_bonus": 0,
        "crime_bonus": 0,
    }
    
    if guild_level >= 5:
        bonuses["work_bonus"] = 5
    if guild_level >= 10:
        bonuses["xp_bonus"] = 10
    if guild_level >= 15:
        bonuses["casino_bonus"] = 5
    if guild_level >= 20:
        bonuses["crime_bonus"] = 10
    if guild_level >= 25:
        bonuses["work_bonus"] = 15
    
    return bonuses


def get_guild_members(bot, guild_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get all guild members with their data."""
    guild_id = guild_data.get("guild_id")
    
    all_users = bot.db.getallusers()
    members = []
    
    for uid in all_users:
        u = bot.db.getuser(uid)
        if u.get("guild_id") == guild_id:
            members.append({
                "userid": uid,
                "role": u.get("guild_role", "member"),
                "level": int(u.get("level", 1)),
                "xp": int(u.get("xp", 0))
            })
    
    return members


def can_manage_guild(user_data: Dict[str, Any], target_role: str = "member") -> bool:
    """Check if user can manage guild (owner or admin)."""
    user_role = user_data.get("guild_role", "member")
    
    if user_role == "owner":
        return True
    if user_role == "admin" and target_role == "member":
        return True
    
    return False
