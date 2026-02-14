from __future__ import annotations

import json
import random
from typing import Dict, List, Any
from datetime import datetime, timezone

from data.quests import DAILY_QUESTS, WEEKLY_QUESTS


def get_active_quests(user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get user's active daily quests."""
    try:
        return json.loads(user_data.get("active_daily_quests", "[]"))
    except Exception:
        return []


def get_completed_today(user_data: Dict[str, Any]) -> List[str]:
    """Get quest IDs completed today."""
    try:
        return json.loads(user_data.get("completed_quests_today", "[]"))
    except Exception:
        return []


def generate_daily_quests(count: int = 3) -> List[Dict[str, Any]]:
    """Generate random daily quests."""
    quest_pool = list(DAILY_QUESTS.values())
    selected = random.sample(quest_pool, min(count, len(quest_pool)))

    # Add progress tracking
    for quest in selected:
        quest["progress"] = 0

    return selected


def generate_weekly_quests(count: int = 2) -> List[Dict[str, Any]]:
    """Generate random weekly quests."""
    quest_pool = list(WEEKLY_QUESTS.values())
    selected = random.sample(quest_pool, min(count, len(quest_pool)))

    # Add progress tracking
    for quest in selected:
        quest["progress"] = 0

    return selected


def update_quest_progress(
    quest: Dict[str, Any],
    progress_type: str,
    amount: int = 1,
) -> bool:
    """
    Update quest progress. Returns True if quest completed.

    progress_type examples: work_count, money_earned, train_count, etc.
    """
    if quest["requirement"]["type"] == progress_type:
        quest["progress"] = quest.get("progress", 0) + amount

        if quest["progress"] >= quest["requirement"]["value"]:
            return True

    return False


def update_all_quests_progress(
    quests: List[Dict[str, Any]],
    progress_type: str,
    amount: int = 1,
) -> List[str]:
    """
    Update all quests' progress. Returns list of completed quest IDs.
    """
    completed = []

    for quest in quests:
        if update_quest_progress(quest, progress_type, amount):
            if quest["id"] not in completed:
                completed.append(quest["id"])

    return completed


def calculate_quest_progress_percent(quest: Dict[str, Any]) -> int:
    """Calculate quest completion percentage."""
    current = quest.get("progress", 0)
    required = quest["requirement"]["value"]

    return min(100, int((current / required) * 100)) if required > 0 else 0


def should_reset_daily_quests(user_data: Dict[str, Any]) -> bool:
    """Check if daily quests should reset (new day)."""
    last_daily = user_data.get("last_daily")

    if not last_daily:
        return True

    try:
        last_time = datetime.fromisoformat(last_daily)
        now = datetime.now(timezone.utc)

        # Reset if it's a new day
        return last_time.date() < now.date()
    except Exception:
        return True
