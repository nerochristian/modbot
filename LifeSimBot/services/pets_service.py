# services/pets_service.py
from __future__ import annotations

from typing import Tuple, Dict, Any
from data.items import PET_TYPES


def calculate_pet_level_from_xp(xp: int) -> Tuple[int, int, int]:
    """Calculate pet level from XP. Returns (level, current_xp, xp_needed_for_next)."""
    BASE_XP = 50
    MULTIPLIER = 1.3
    
    level = 1
    total_needed = 0
    
    while True:
        xp_for_next = int(BASE_XP * (MULTIPLIER ** (level - 1)))
        if total_needed + xp_for_next > xp:
            current_xp = xp - total_needed
            return level, current_xp, xp_for_next
        total_needed += xp_for_next
        level += 1


def get_pet_buffs(pet_type: str, pet_level: int) -> Dict[str, Any]:
    """Get active buffs for a pet based on type and level."""
    pet_data = PET_TYPES.get(pet_type)
    if not pet_data:
        return {}
    
    buffs = {}
    for buff in pet_data.get("buffs", []):
        if "xp_boost" in buff:
            value = int(buff.split("_")[-1])
            buffs["xp_boost"] = value + (pet_level // 2)  # +1% per 2 levels
        elif "money_boost" in buff:
            value = int(buff.split("_")[-1])
            buffs["money_boost"] = value + (pet_level // 2)
        elif "luck_boost" in buff:
            value = int(buff.split("_")[-1])
            buffs["luck_boost"] = value + pet_level
        elif "charisma_boost" in buff:
            value = int(buff.split("_")[-1])
            buffs["charisma_boost"] = value + pet_level
        elif "happiness_regen" in buff:
            value = int(buff.split("_")[-1])
            buffs["happiness_regen"] = value
        elif "energy_regen" in buff:
            value = int(buff.split("_")[-1])
            buffs["energy_regen"] = value
        elif "health_regen" in buff:
            value = int(buff.split("_")[-1])
            buffs["health_regen"] = value
    
    return buffs


def calculate_total_buffs(user_pets: list) -> Dict[str, int]:
    """Calculate total buffs from all alive pets."""
    total_buffs = {
        "xp_boost": 0,
        "money_boost": 0,
        "luck_boost": 0,
        "charisma_boost": 0,
        "happiness_regen": 0,
        "energy_regen": 0,
        "health_regen": 0,
    }
    
    for pet in user_pets:
        if not pet.get("is_alive"):
            continue
        
        pet_type = pet.get("pet_type")
        pet_level = int(pet.get("level", 1))
        
        buffs = get_pet_buffs(pet_type, pet_level)
        
        for buff_type, value in buffs.items():
            total_buffs[buff_type] += value
    
    return total_buffs
