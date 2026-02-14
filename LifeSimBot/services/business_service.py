# services/business_service.py
from __future__ import annotations
import random
from datetime import datetime, timedelta
from typing import Dict, List

# Business types and their properties
BUSINESS_TYPES = {
    "lemonade_stand": {
        "name": "Lemonade Stand",
        "cost": 500,
        "base_revenue": 10,  # per hour
        "max_level": 5,
        "emoji": "🍋",
        "description": "Classic starter business"
    },
    "food_truck": {
        "name": "Food Truck",
        "cost": 5000,
        "base_revenue": 100,
        "max_level": 10,
        "emoji": "🚚",
        "description": "Mobile food business"
    },
    "coffee_shop": {
        "name": "Coffee Shop",
        "cost": 25000,
        "base_revenue": 300,
        "max_level": 15,
        "emoji": "☕",
        "description": "Cozy cafe"
    },
    "restaurant": {
        "name": "Restaurant",
        "cost": 100000,
        "base_revenue": 1000,
        "max_level": 20,
        "emoji": "🍽️",
        "description": "Fine dining establishment"
    },
    "nightclub": {
        "name": "Nightclub",
        "cost": 500000,
        "base_revenue": 5000,
        "max_level": 25,
        "emoji": "🎵",
        "description": "Entertainment venue"
    },
    "tech_startup": {
        "name": "Tech Startup",
        "cost": 1000000,
        "base_revenue": 10000,
        "max_level": 30,
        "emoji": "💻",
        "description": "Silicon Valley dream"
    },
    "casino": {
        "name": "Casino",
        "cost": 5000000,
        "base_revenue": 50000,
        "max_level": 50,
        "emoji": "🎰",
        "description": "Luxury gambling hall"
    }
}


def calculate_revenue(business_type: str, level: int, owner_skill: int = 0) -> int:
    """
    Calculate hourly revenue for a business.
    
    Args:
        business_type: Type of business
        level: Business level
        owner_skill: Owner's business skill (0-100)
    
    Returns:
        Revenue per hour
    """
    biz = BUSINESS_TYPES.get(business_type)
    if not biz:
        return 0
    
    base = biz["base_revenue"]
    
    # Level multiplier (10% per level)
    level_mult = 1.0 + (level * 0.10)
    
    # Skill bonus (0.5% per skill point, max 50%)
    skill_bonus = 1.0 + ((owner_skill / 100) * 0.50)
    
    return int(base * level_mult * skill_bonus)


def calculate_upgrade_cost(business_type: str, current_level: int) -> int:
    """Calculate cost to upgrade business to next level."""
    biz = BUSINESS_TYPES.get(business_type)
    if not biz:
        return 0
    
    base_cost = biz["cost"]
    
    # Each level costs 50% more than the last
    upgrade_cost = int(base_cost * (1.5 ** current_level))
    
    return upgrade_cost


def can_upgrade(business_level: int, business_type: str) -> bool:
    """Check if business can be upgraded."""
    biz = BUSINESS_TYPES.get(business_type)
    if not biz:
        return False
    
    return business_level < biz["max_level"]


def calculate_uncollected_revenue(last_collected: str, revenue_per_hour: int, max_hours: int = 24) -> int:
    """
    Calculate revenue accumulated since last collection.
    
    Args:
        last_collected: ISO timestamp of last collection
        revenue_per_hour: Hourly revenue rate
        max_hours: Maximum hours to accumulate (prevents abuse)
    
    Returns:
        Total accumulated revenue
    """
    try:
        last_time = datetime.fromisoformat(last_collected)
        now = datetime.utcnow()
        
        hours_passed = (now - last_time).total_seconds() / 3600
        hours_passed = min(hours_passed, max_hours)  # Cap at max_hours
        
        return int(revenue_per_hour * hours_passed)
    except:
        return 0


def get_business_upgrades() -> Dict[str, dict]:
    """Get available business upgrades."""
    return {
        "marketing": {
            "name": "Marketing Campaign",
            "cost": 5000,
            "effect": "+10% revenue",
            "emoji": "📢"
        },
        "automation": {
            "name": "Automation System",
            "cost": 10000,
            "effect": "+15% revenue",
            "emoji": "🤖"
        },
        "expansion": {
            "name": "Business Expansion",
            "cost": 25000,
            "effect": "+20% revenue",
            "emoji": "🏗️"
        },
        "premium": {
            "name": "Premium Service",
            "cost": 50000,
            "effect": "+25% revenue",
            "emoji": "⭐"
        }
    }


def apply_upgrade_bonus(base_revenue: int, upgrades: List[str]) -> int:
    """Apply upgrade bonuses to revenue."""
    multiplier = 1.0
    upgrade_data = get_business_upgrades()
    
    for upgrade_id in upgrades:
        if upgrade_id == "marketing":
            multiplier += 0.10
        elif upgrade_id == "automation":
            multiplier += 0.15
        elif upgrade_id == "expansion":
            multiplier += 0.20
        elif upgrade_id == "premium":
            multiplier += 0.25
    
    return int(base_revenue * multiplier)
