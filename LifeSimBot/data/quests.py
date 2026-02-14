# data/quests.py
from __future__ import annotations

from typing import Dict, Any


# Daily quest pool (randomly assigned)
DAILY_QUESTS = {
    "work_5": {
        "id": "work_5",
        "name": "Hard Day's Work",
        "description": "Work 5 times",
        "emoji": "💼",
        "requirement": {"type": "work_count", "value": 5},
        "reward": {"money": 5000, "xp": 100},
        "difficulty": "easy"
    },
    "earn_10k": {
        "id": "earn_10k",
        "name": "Big Earner",
        "description": "Earn $10,000",
        "emoji": "💰",
        "requirement": {"type": "money_earned", "value": 10000},
        "reward": {"money": 2000, "xp": 80},
        "difficulty": "easy"
    },
    "train_skills": {
        "id": "train_skills",
        "name": "Self Improvement",
        "description": "Train any skill 3 times",
        "emoji": "⚔️",
        "requirement": {"type": "train_count", "value": 3},
        "reward": {"money": 3000, "xp": 120},
        "difficulty": "easy"
    },
    "feed_pet": {
        "id": "feed_pet",
        "name": "Pet Care",
        "description": "Feed your pet 3 times",
        "emoji": "🐾",
        "requirement": {"type": "feed_pet_count", "value": 3},
        "reward": {"money": 2000, "xp": 60},
        "difficulty": "easy"
    },
    "gamble_5": {
        "id": "gamble_5",
        "name": "High Roller",
        "description": "Play 5 casino games",
        "emoji": "🎰",
        "requirement": {"type": "gamble_count", "value": 5},
        "reward": {"money": 4000, "xp": 100},
        "difficulty": "medium"
    },
    "rob_3": {
        "id": "rob_3",
        "name": "Street Hustler",
        "description": "Rob 3 people",
        "emoji": "🔪",
        "requirement": {"type": "rob_count", "value": 3},
        "reward": {"money": 5000, "xp": 150},
        "difficulty": "medium"
    },
    "spend_50k": {
        "id": "spend_50k",
        "name": "Big Spender",
        "description": "Spend $50,000 in the shop",
        "emoji": "🛒",
        "requirement": {"type": "money_spent", "value": 50000},
        "reward": {"money": 10000, "xp": 200},
        "difficulty": "hard"
    },
    "earn_100k": {
        "id": "earn_100k",
        "name": "Money Maker",
        "description": "Earn $100,000",
        "emoji": "💵",
        "requirement": {"type": "money_earned", "value": 100000},
        "reward": {"money": 15000, "xp": 300},
        "difficulty": "hard"
    },
}


# Weekly quest pool (harder, better rewards)
WEEKLY_QUESTS = {
    "work_50": {
        "id": "work_50",
        "name": "Dedicated Worker",
        "description": "Work 50 times this week",
        "emoji": "🏭",
        "requirement": {"type": "work_count", "value": 50},
        "reward": {"money": 50000, "xp": 1000},
        "difficulty": "medium"
    },
    "earn_1m": {
        "id": "earn_1m",
        "name": "Millionaire Grind",
        "description": "Earn $1,000,000 this week",
        "emoji": "💎",
        "requirement": {"type": "money_earned", "value": 1000000},
        "reward": {"money": 100000, "xp": 2000},
        "difficulty": "hard"
    },
    "level_up_5": {
        "id": "level_up_5",
        "name": "Rapid Growth",
        "description": "Level up 5 times",
        "emoji": "⭐",
        "requirement": {"type": "level_ups", "value": 5},
        "reward": {"money": 75000, "xp": 1500},
        "difficulty": "hard"
    },
    "train_20": {
        "id": "train_20",
        "name": "Training Montage",
        "description": "Train skills 20 times",
        "emoji": "💪",
        "requirement": {"type": "train_count", "value": 20},
        "reward": {"money": 40000, "xp": 800},
        "difficulty": "medium"
    },
    "crime_20": {
        "id": "crime_20",
        "name": "Crime Spree",
        "description": "Commit 20 crimes",
        "emoji": "🚔",
        "requirement": {"type": "crime_count", "value": 20},
        "reward": {"money": 60000, "xp": 1200},
        "difficulty": "hard"
    },
    "gamble_100k": {
        "id": "gamble_100k",
        "name": "Casino VIP",
        "description": "Bet $100,000 total in casino",
        "emoji": "🎲",
        "requirement": {"type": "money_gambled", "value": 100000},
        "reward": {"money": 50000, "xp": 1000},
        "difficulty": "medium"
    },
}


QUEST_DIFFICULTIES = {
    "easy": {"color": 0x00FF00, "emoji": "🟢"},
    "medium": {"color": 0xFFAA00, "emoji": "🟡"},
    "hard": {"color": 0xFF0000, "emoji": "🔴"}
}
