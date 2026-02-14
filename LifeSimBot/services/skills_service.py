# services/skills_service.py
from __future__ import annotations

from typing import Tuple, Dict


# Skill names and their emojis
SKILLS = {
    "strength": {"emoji": "💪", "name": "Strength", "description": "Physical power - Helps with crime and combat"},
    "intelligence": {"emoji": "🧠", "name": "Intelligence", "description": "Mental ability - Increases work earnings"},
    "charisma": {"emoji": "✨", "name": "Charisma", "description": "Social skills - Better negotiations and discounts"},
    "luck": {"emoji": "🍀", "name": "Luck", "description": "Fortune - Better loot and gambling odds"},
    "cooking": {"emoji": "👨‍🍳", "name": "Cooking", "description": "Culinary skills - Cook better food"},
    "crime": {"emoji": "🔪", "name": "Crime", "description": "Illegal expertise - Better robbery success rates"},
    "business": {"emoji": "💼", "name": "Business", "description": "Entrepreneurship - More passive income"},
}


def calculate_skill_level(skill_xp: int) -> Tuple[int, int, int]:
    """
    Calculate skill level from XP.
    Returns (level, current_xp, xp_needed_for_next_level)
    
    Level 1: 0-99 XP
    Level 2: 100-249 XP
    Level 3: 250-449 XP
    etc.
    """
    if skill_xp < 0:
        skill_xp = 0
    
    # Cap at level 100
    if skill_xp >= 50000:
        return 100, 0, 0
    
    BASE_XP = 100
    MULTIPLIER = 1.15
    
    level = 1
    total_needed = 0
    
    while level < 100:
        xp_for_next = int(BASE_XP * (MULTIPLIER ** (level - 1)))
        if total_needed + xp_for_next > skill_xp:
            current_xp = skill_xp - total_needed
            return level, current_xp, xp_for_next
        total_needed += xp_for_next
        level += 1
    
    return 100, 0, 0


def get_skill_multiplier(skill_level: int) -> float:
    """Get gameplay multiplier based on skill level (1.0 - 2.0)."""
    return 1.0 + (skill_level * 0.01)  # +1% per level, max +100%


def calculate_training_xp(base_xp: int, skill_level: int) -> int:
    """Calculate XP gained from training (decreases as level increases)."""
    # Training becomes less effective at higher levels
    efficiency = max(0.3, 1.0 - (skill_level * 0.007))  # Min 30% efficiency
    return int(base_xp * efficiency)


def get_training_cost(skill_name: str) -> Tuple[int, int]:
    """Get energy cost and XP gain for training a skill."""
    training_data = {
        "strength": (15, 20),      # 15 energy, 20 base XP
        "intelligence": (10, 15),  # Easier to train
        "charisma": (10, 15),
        "luck": (20, 10),          # Harder to train, less XP
        "cooking": (15, 18),
        "crime": (20, 25),         # High risk, high reward
        "business": (15, 20),
    }
    
    return training_data.get(skill_name, (15, 15))


def get_all_skill_levels(user_data: Dict) -> Dict[str, Dict]:
    """Get all skills with their levels and progress."""
    result = {}
    
    for skill_id, skill_info in SKILLS.items():
        skill_xp = int(user_data.get(f"skill_{skill_id}", 0))
        level, curr_xp, needed_xp = calculate_skill_level(skill_xp)
        
        result[skill_id] = {
            "name": skill_info["name"],
            "emoji": skill_info["emoji"],
            "description": skill_info["description"],
            "xp": skill_xp,
            "level": level,
            "current_xp": curr_xp,
            "needed_xp": needed_xp,
            "multiplier": get_skill_multiplier(level)
        }
    
    return result


def apply_skill_bonuses(amount: int, skill_name: str, skill_level: int) -> int:
    """Apply skill bonus to an amount (work pay, crime loot, etc)."""
    multiplier = get_skill_multiplier(skill_level)
    return int(amount * multiplier)
