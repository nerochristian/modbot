# data/properties_advanced.py
from __future__ import annotations

from typing import Dict, Any


PROPERTY_TYPES: Dict[str, Dict[str, Any]] = {
    "studio_apartment": {
        "id": "studio_apartment",
        "name": "Studio Apartment",
        "emoji": "🏚️",
        "description": "A tiny studio. Better than the streets, boosts happiness a bit.",
        "base_cost": 25_000,
        "base_rent": 1_000,          # per hour
        "rent_multiplier": 1.12,     # per level
        "max_level": 10,
        "comfort": 5,                # affects happiness regen
        "energy_bonus": 5,           # affects sleep recovery
    },
    "small_house": {
        "id": "small_house",
        "name": "Small House",
        "emoji": "🏠",
        "description": "Cozy starter house with decent comfort.",
        "base_cost": 100_000,
        "base_rent": 4_000,
        "rent_multiplier": 1.14,
        "max_level": 15,
        "comfort": 10,
        "energy_bonus": 10,
    },
    "suburban_home": {
        "id": "suburban_home",
        "name": "Suburban Home",
        "emoji": "🏡",
        "description": "Family home in a quiet neighborhood.",
        "base_cost": 350_000,
        "base_rent": 12_000,
        "rent_multiplier": 1.16,
        "max_level": 20,
        "comfort": 16,
        "energy_bonus": 15,
    },
    "city_penthouse": {
        "id": "city_penthouse",
        "name": "City Penthouse",
        "emoji": "🏙️",
        "description": "Luxury penthouse with a skyline view.",
        "base_cost": 1_000_000,
        "base_rent": 40_000,
        "rent_multiplier": 1.18,
        "max_level": 25,
        "comfort": 24,
        "energy_bonus": 20,
    },
    "beach_villa": {
        "id": "beach_villa",
        "name": "Beach Villa",
        "emoji": "🏖️",
        "description": "High-end villa by the ocean, very relaxing.",
        "base_cost": 2_500_000,
        "base_rent": 90_000,
        "rent_multiplier": 1.2,
        "max_level": 30,
        "comfort": 30,
        "energy_bonus": 25,
    },
}


def calculate_property_rent(prop: dict) -> int:
    """Calculate current rent_per_hour for a property."""
    prop_type = PROPERTY_TYPES.get(prop["property_type"])
    if not prop_type:
        return int(prop.get("rent_per_hour", 0))

    level = int(prop.get("level", 1))
    base = prop_type["base_rent"]
    mult = prop_type["rent_multiplier"]

    rent = int(base * (mult ** (level - 1)))
    return rent


def calculate_property_upgrade_cost(prop: dict) -> int:
    """Calculate cost to upgrade property to next level."""
    prop_type = PROPERTY_TYPES.get(prop["property_type"])
    if not prop_type:
        return 0

    level = int(prop.get("level", 1))
    max_level = prop_type["max_level"]

    if level >= max_level:
        return 0

    base_cost = prop_type["base_cost"]
    cost = int(base_cost * (1.22 ** level))
    return cost
