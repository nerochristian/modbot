# services/family_service.py
from __future__ import annotations

from typing import Dict, List, Any, Optional
import json
from datetime import datetime, timezone


def get_kids(user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return user's kids list as Python objects."""
    try:
        return json.loads(user_data.get("kids", "[]"))
    except Exception:
        return []


def add_kid(user_data: Dict[str, Any], kid_name: str, age: int = 0) -> List[Dict[str, Any]]:
    """Append a new kid to the family list and return updated list."""
    kids = get_kids(user_data)

    new_kid = {
        "name": kid_name,
        "age": age,
        "adopted_at": datetime.now(timezone.utc).isoformat(),
        "happiness": 100,
        "education": 0,
    }

    kids.append(new_kid)
    return kids


def calculate_family_bonus(
    user_data: Dict[str, Any],
    spouse_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, int]:
    """
    Calculate bonuses from having a family.

    Basic idea (tunable):
    - Being married gives flat XP/money/happiness buffs.
    - Each kid adds small extra bonuses.
    """
    bonuses = {
        "xp_bonus": 0,
        "money_bonus": 0,
        "happiness_bonus": 0,
    }

    # Marriage bonus
    if user_data.get("spouse"):
        bonuses["xp_bonus"] += 5
        bonuses["money_bonus"] += 10
        bonuses["happiness_bonus"] += 10

    # Kids bonus (each kid gives a small bonus)
    kids = get_kids(user_data)
    kid_count = len(kids)

    bonuses["happiness_bonus"] += kid_count * 2
    bonuses["xp_bonus"] += kid_count

    return bonuses


def generate_kid_names() -> List[str]:
    """Pool of random kid names for adoption."""
    return [
        "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason",
        "Isabella", "William", "Mia", "James", "Charlotte", "Benjamin", "Amelia",
        "Lucas", "Harper", "Henry", "Evelyn", "Alexander", "Abigail", "Michael",
        "Emily", "Daniel", "Elizabeth", "Matthew", "Sofia", "Jackson", "Avery",
        "Sebastian", "Ella", "David", "Scarlett", "Joseph", "Grace", "Samuel",
    ]


def calculate_divorce_cost(user_data: Dict[str, Any]) -> int:
    """Divorce cost = 50% of family bank + flat lawyer fee."""
    family_bank = int(user_data.get("family_bank", 0))
    lawyer_fee = 50_000
    return (family_bank // 2) + lawyer_fee
