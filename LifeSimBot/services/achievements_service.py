# services/achievements_service.py
from __future__ import annotations

from typing import Dict, List, Any
import json

from data.achievements import ACHIEVEMENTS
from services.skills_service import calculate_skill_level


def check_achievement(achievement_id: str, user_data: Dict[str, Any]) -> bool:
    """Check if user meets achievement requirement."""
    achievement = ACHIEVEMENTS.get(achievement_id)
    if not achievement:
        return False
    
    req = achievement["requirement"]
    req_type = req["type"]
    req_value = req["value"]
    
    # Check different requirement types
    if req_type == "balance":
        return int(user_data.get("balance", 0)) >= req_value
    
    elif req_type == "net_worth":
        return int(user_data.get("net_worth", 0)) >= req_value
    
    elif req_type == "level":
        return int(user_data.get("level", 1)) >= req_value
    
    elif req_type == "work_count":
        return int(user_data.get("total_work_count", 0)) >= req_value
    
    elif req_type == "money_earned":
        return int(user_data.get("balance", 0)) >= req_value
    
    elif req_type == "crimes_committed":
        return int(user_data.get("crimes_committed", 0)) >= req_value
    
    elif req_type == "has_spouse":
        return user_data.get("spouse") is not None
    
    elif req_type == "kid_count":
        try:
            kids = json.loads(user_data.get("kids", "[]"))
            return len(kids) >= req_value
        except:
            return False
    
    elif req_type == "pet_count":
        try:
            pets = json.loads(user_data.get("pets", "[]"))
            return len(pets) >= req_value
        except:
            return False
    
    elif req_type == "casino_total_bet":
        return int(user_data.get("casino_total_bet", 0)) >= req_value
    
    elif req_type == "single_casino_win":
        # Would need to track this separately
        return False
    
    elif req_type == "has_property":
        return user_data.get("current_property") is not None
    
    elif req_type == "property_tier":
        # Would need property tier values
        return False
    
    elif req_type == "business_count":
        try:
            businesses = json.loads(user_data.get("businesses", "[]"))
            return len(businesses) >= req_value
        except:
            return False
    
    elif req_type == "friend_count":
        try:
            friends = json.loads(user_data.get("friends", "[]"))
            return len(friends) >= req_value
        except:
            return False
    
    elif req_type == "reputation":
        return int(user_data.get("reputation", 0)) >= req_value
    
    elif req_type == "fame":
        return int(user_data.get("fame", 0)) >= req_value
    
    return False


def get_unlocked_achievements(user_data: Dict[str, Any]) -> List[str]:
    """Get list of achievement IDs that user has unlocked."""
    try:
        return json.loads(user_data.get("achievements", "[]"))
    except:
        return []


def check_all_achievements(user_data: Dict[str, Any]) -> List[str]:
    """Check all achievements and return newly unlocked ones."""
    unlocked = get_unlocked_achievements(user_data)
    newly_unlocked = []
    
    for achievement_id in ACHIEVEMENTS.keys():
        if achievement_id not in unlocked:
            if check_achievement(achievement_id, user_data):
                newly_unlocked.append(achievement_id)
    
    return newly_unlocked


def calculate_achievement_progress(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate overall achievement progress."""
    total = len(ACHIEVEMENTS)
    unlocked = len(get_unlocked_achievements(user_data))
    
    return {
        "total": total,
        "unlocked": unlocked,
        "percentage": int((unlocked / total) * 100) if total > 0 else 0
    }


def group_achievements_by_category(achievements_dict: Dict) -> Dict[str, List]:
    """Group achievements by category (based on achievement IDs)."""
    categories = {
        "economy": [],
        "work": [],
        "level": [],
        "family": [],
        "pets": [],
        "gambling": [],
        "crime": [],
        "property": [],
        "business": [],
        "social": []
    }
    
    for ach_id, ach_data in achievements_dict.items():
        # Determine category from ID prefix
        if "level_" in ach_id or ach_id in ["novice", "expert", "master", "legend"]:
            categories["level"].append((ach_id, ach_data))
        elif "crime" in ach_id or ach_id == "criminal":
            categories["crime"].append((ach_id, ach_data))
        elif "work" in ach_id or "worker" in ach_id or ach_id == "first_day":
            categories["work"].append((ach_id, ach_data))
        elif "pet" in ach_id:
            categories["pets"].append((ach_id, ach_data))
        elif "casino" in ach_id or "gambl" in ach_id or "lucky" in ach_id or "roller" in ach_id:
            categories["gambling"].append((ach_id, ach_data))
        elif "married" in ach_id or "parent" in ach_id or "family" in ach_id or "kid" in ach_id:
            categories["family"].append((ach_id, ach_data))
        elif "property" in ach_id or "home" in ach_id or "luxury" in ach_id:
            categories["property"].append((ach_id, ach_data))
        elif "business" in ach_id or "entrepreneur" in ach_id or "tycoon" in ach_id:
            categories["business"].append((ach_id, ach_data))
        elif "friend" in ach_id or "popular" in ach_id or "famous" in ach_id or "reputation" in ach_id:
            categories["social"].append((ach_id, ach_data))
        elif "dollar" in ach_id or "millionaire" in ach_id or "billionaire" in ach_id:
            categories["economy"].append((ach_id, ach_data))
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}
