# data/businesses.py
from __future__ import annotations

from typing import Dict, Any


BUSINESS_TYPES: Dict[str, Dict[str, Any]] = {
    "lemonade_stand": {
        "id": "lemonade_stand",
        "name": "Lemonade Stand",
        "emoji": "🍋",
        "description": "A small stand on the corner. Simple, low risk starter business.",
        "base_cost": 5_000,
        "base_revenue": 500,        # per hour
        "revenue_multiplier": 1.15, # per level
        "max_level": 10,
        "risk": "low"
    },
    "food_truck": {
        "id": "food_truck",
        "name": "Food Truck",
        "emoji": "🚚",
        "description": "Serve tasty food around the city.",
        "base_cost": 25_000,
        "base_revenue": 2_000,
        "revenue_multiplier": 1.18,
        "max_level": 15,
        "risk": "medium"
    },
    "convenience_store": {
        "id": "convenience_store",
        "name": "Convenience Store",
        "emoji": "🏪",
        "description": "A small local store open 24/7.",
        "base_cost": 100_000,
        "base_revenue": 7_500,
        "revenue_multiplier": 1.20,
        "max_level": 20,
        "risk": "medium"
    },
    "nightclub": {
        "id": "nightclub",
        "name": "Nightclub",
        "emoji": "🎵",
        "description": "High risk, high reward nightlife spot.",
        "base_cost": 500_000,
        "base_revenue": 35_000,
        "revenue_multiplier": 1.22,
        "max_level": 25,
        "risk": "high"
    },
    "tech_startup": {
        "id": "tech_startup",
        "name": "Tech Startup",
        "emoji": "💻",
        "description": "Scalable software business with huge potential.",
        "base_cost": 1_500_000,
        "base_revenue": 80_000,
        "revenue_multiplier": 1.25,
        "max_level": 30,
        "risk": "high"
    },
}


def calculate_business_revenue(business: dict) -> int:
    """Calculate current revenue_per_hour for a business."""
    biz_type = BUSINESS_TYPES.get(business["business_type"])
    if not biz_type:
        return int(business.get("revenue_per_hour", 0))
    
    level = int(business.get("level", 1))
    base = biz_type["base_revenue"]
    mult = biz_type["revenue_multiplier"]
    
    revenue = int(base * (mult ** (level - 1)))
    return revenue


def calculate_upgrade_cost(business: dict) -> int:
    """Calculate cost to upgrade business to next level."""
    biz_type = BUSINESS_TYPES.get(business["business_type"])
    if not biz_type:
        return 0
    
    level = int(business.get("level", 1))
    max_level = biz_type["max_level"]
    
    if level >= max_level:
        return 0
    
    base_cost = biz_type["base_cost"]
    # Upgrade cost grows faster than purchase cost
    cost = int(base_cost * (1.25 ** level))
    return cost
