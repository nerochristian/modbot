# data/achievements.py
from __future__ import annotations

ACHIEVEMENTS = {
    # ==================== ECONOMY ====================
    "first_dollar": {
        "id": "first_dollar",
        "name": "First Dollar",
        "description": "Earn your first dollar",
        "emoji": "💵",
        "requirement": {"type": "money_earned", "value": 1},
        "reward": {"xp": 10},
        "tier": "bronze"
    },
    "millionaire": {
        "id": "millionaire",
        "name": "Millionaire",
        "description": "Reach $1,000,000 in balance",
        "emoji": "💰",
        "requirement": {"type": "balance", "value": 1000000},
        "reward": {"xp": 1000, "money": 50000},
        "tier": "gold"
    },
    "billionaire": {
        "id": "billionaire",
        "name": "Billionaire",
        "description": "Reach $1,000,000,000 in net worth",
        "emoji": "🤑",
        "requirement": {"type": "net_worth", "value": 1000000000},
        "reward": {"xp": 10000, "money": 1000000},
        "tier": "legendary"
    },
    
    # ==================== WORK ====================
    "first_day": {
        "id": "first_day",
        "name": "First Day",
        "description": "Complete your first work shift",
        "emoji": "💼",
        "requirement": {"type": "work_count", "value": 1},
        "reward": {"xp": 20},
        "tier": "bronze"
    },
    "hard_worker": {
        "id": "hard_worker",
        "name": "Hard Worker",
        "description": "Work 100 times",
        "emoji": "⚒️",
        "requirement": {"type": "work_count", "value": 100},
        "reward": {"xp": 500, "money": 5000},
        "tier": "silver"
    },
    "workaholic": {
        "id": "workaholic",
        "name": "Workaholic",
        "description": "Work 1000 times",
        "emoji": "🏭",
        "requirement": {"type": "work_count", "value": 1000},
        "reward": {"xp": 5000, "money": 50000},
        "tier": "gold"
    },
    
    # ==================== LEVEL ====================
    "level_10": {
        "id": "level_10",
        "name": "Novice",
        "description": "Reach level 10",
        "emoji": "⭐",
        "requirement": {"type": "level", "value": 10},
        "reward": {"money": 10000},
        "tier": "bronze"
    },
    "level_25": {
        "id": "level_25",
        "name": "Expert",
        "description": "Reach level 25",
        "emoji": "🌟",
        "requirement": {"type": "level", "value": 25},
        "reward": {"money": 50000},
        "tier": "silver"
    },
    "level_50": {
        "id": "level_50",
        "name": "Master",
        "description": "Reach level 50",
        "emoji": "✨",
        "requirement": {"type": "level", "value": 50},
        "reward": {"money": 250000},
        "tier": "gold"
    },
    "level_100": {
        "id": "level_100",
        "name": "Legend",
        "description": "Reach level 100",
        "emoji": "🏆",
        "requirement": {"type": "level", "value": 100},
        "reward": {"money": 1000000},
        "tier": "legendary"
    },
    
    # ==================== FAMILY ====================
    "married": {
        "id": "married",
        "name": "Married",
        "description": "Get married to someone",
        "emoji": "💍",
        "requirement": {"type": "has_spouse", "value": True},
        "reward": {"xp": 100, "money": 5000},
        "tier": "silver"
    },
    "parent": {
        "id": "parent",
        "name": "Parent",
        "description": "Adopt your first child",
        "emoji": "👶",
        "requirement": {"type": "kid_count", "value": 1},
        "reward": {"xp": 150, "money": 10000},
        "tier": "silver"
    },
    "big_family": {
        "id": "big_family",
        "name": "Big Family",
        "description": "Have 5 or more kids",
        "emoji": "👨‍👩‍👧‍👦",
        "requirement": {"type": "kid_count", "value": 5},
        "reward": {"xp": 500, "money": 50000},
        "tier": "gold"
    },
    
    # ==================== PETS ====================
    "pet_owner": {
        "id": "pet_owner",
        "name": "Pet Owner",
        "description": "Adopt your first pet",
        "emoji": "🐾",
        "requirement": {"type": "pet_count", "value": 1},
        "reward": {"xp": 50},
        "tier": "bronze"
    },
    "pet_collector": {
        "id": "pet_collector",
        "name": "Pet Collector",
        "description": "Own 5 different pets",
        "emoji": "🦜",
        "requirement": {"type": "pet_count", "value": 5},
        "reward": {"xp": 500, "money": 25000},
        "tier": "gold"
    },
    
    # ==================== GAMBLING ====================
    "lucky_win": {
        "id": "lucky_win",
        "name": "Lucky Win",
        "description": "Win $10,000 in a single casino game",
        "emoji": "🎰",
        "requirement": {"type": "single_casino_win", "value": 10000},
        "reward": {"xp": 200},
        "tier": "silver"
    },
    "high_roller": {
        "id": "high_roller",
        "name": "High Roller",
        "description": "Wager $1,000,000 total in casino",
        "emoji": "🎲",
        "requirement": {"type": "casino_total_bet", "value": 1000000},
        "reward": {"xp": 1000, "money": 100000},
        "tier": "gold"
    },
    
    # ==================== CRIME ====================
    "first_crime": {
        "id": "first_crime",
        "name": "Criminal",
        "description": "Commit your first crime",
        "emoji": "🔪",
        "requirement": {"type": "crimes_committed", "value": 1},
        "reward": {"xp": 50},
        "tier": "bronze"
    },
    "crime_lord": {
        "id": "crime_lord",
        "name": "Crime Lord",
        "description": "Commit 100 crimes",
        "emoji": "👑",
        "requirement": {"type": "crimes_committed", "value": 100},
        "reward": {"xp": 2000, "money": 100000},
        "tier": "gold"
    },
    
    # ==================== PROPERTY ====================
    "homeowner": {
        "id": "homeowner",
        "name": "Homeowner",
        "description": "Buy your first property",
        "emoji": "🏠",
        "requirement": {"type": "has_property", "value": True},
        "reward": {"xp": 100, "money": 5000},
        "tier": "silver"
    },
    "luxury_life": {
        "id": "luxury_life",
        "name": "Luxury Life",
        "description": "Own a mansion or better",
        "emoji": "🏰",
        "requirement": {"type": "property_tier", "value": 8},
        "reward": {"xp": 1000, "money": 100000},
        "tier": "gold"
    },
    
    # ==================== BUSINESS ====================
    "entrepreneur": {
        "id": "entrepreneur",
        "name": "Entrepreneur",
        "description": "Start your first business",
        "emoji": "💼",
        "requirement": {"type": "business_count", "value": 1},
        "reward": {"xp": 200, "money": 10000},
        "tier": "silver"
    },
    "business_tycoon": {
        "id": "business_tycoon",
        "name": "Business Tycoon",
        "description": "Own 10 businesses",
        "emoji": "🏢",
        "requirement": {"type": "business_count", "value": 10},
        "reward": {"xp": 5000, "money": 500000},
        "tier": "legendary"
    },
    
    # ==================== SOCIAL ====================
    "friendly": {
        "id": "friendly",
        "name": "Friendly",
        "description": "Add 5 friends",
        "emoji": "👥",
        "requirement": {"type": "friend_count", "value": 5},
        "reward": {"xp": 100},
        "tier": "bronze"
    },
    "popular": {
        "id": "popular",
        "name": "Popular",
        "description": "Have 1000+ reputation",
        "emoji": "⭐",
        "requirement": {"type": "reputation", "value": 1000},
        "reward": {"xp": 500, "money": 50000},
        "tier": "gold"
    },
    "famous": {
        "id": "famous",
        "name": "Famous",
        "description": "Have 10000+ fame",
        "emoji": "🌟",
        "requirement": {"type": "fame", "value": 10000},
        "reward": {"xp": 2000, "money": 200000},
        "tier": "legendary"
    }
}

# Achievement tiers
ACHIEVEMENT_TIERS = {
    "bronze": {"color": 0xCD7F32, "emoji": "🥉"},
    "silver": {"color": 0xC0C0C0, "emoji": "🥈"},
    "gold": {"color": 0xFFD700, "emoji": "🥇"},
    "legendary": {"color": 0xFF6B6B, "emoji": "👑"}
}
