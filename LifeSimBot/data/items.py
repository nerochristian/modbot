# data/items.py
from __future__ import annotations


# ==================== FOOD ====================
FOOD = {
    "apple": {
        "name": "🍎 Apple",
        "price": 5,
        "sell_price": 2,
        "hunger": 15,
        "energy": 5,
        "health": 5,
        "happiness": 3,
        "description": "A fresh, crispy apple",
        "category": "snack",
        "emoji": "🍎"
    },
    "banana": {
        "name": "🍌 Banana",
        "price": 4,
        "sell_price": 2,
        "hunger": 12,
        "energy": 8,
        "health": 3,
        "happiness": 2,
        "description": "Sweet and energy-boosting",
        "category": "snack",
        "emoji": "🍌"
    },
    "bread": {
        "name": "🍞 Bread",
        "price": 8,
        "sell_price": 3,
        "hunger": 20,
        "energy": 10,
        "health": 5,
        "happiness": 4,
        "description": "Freshly baked bread",
        "category": "meal",
        "emoji": "🍞"
    },
    "pizza": {
        "name": "🍕 Pizza",
        "price": 20,
        "sell_price": 10,
        "hunger": 45,
        "energy": 20,
        "health": 10,
        "happiness": 15,
        "description": "Hot, cheesy pizza slice",
        "category": "fast_food",
        "emoji": "🍕"
    },
    "burger": {
        "name": "🍔 Burger",
        "price": 15,
        "sell_price": 7,
        "hunger": 35,
        "energy": 15,
        "health": 10,
        "happiness": 12,
        "description": "Juicy cheeseburger",
        "category": "fast_food",
        "emoji": "🍔"
    },
    "salad": {
        "name": "🥗 Salad",
        "price": 12,
        "sell_price": 5,
        "hunger": 25,
        "energy": 8,
        "health": 20,
        "happiness": 6,
        "description": "Healthy green salad",
        "category": "healthy",
        "emoji": "🥗"
    },
    "ramen": {
        "name": "🍜 Ramen",
        "price": 12,
        "sell_price": 5,
        "hunger": 30,
        "energy": 15,
        "health": 10,
        "happiness": 10,
        "description": "Hot bowl of ramen",
        "category": "meal",
        "emoji": "🍜"
    },
    "taco": {
        "name": "🌮 Taco",
        "price": 10,
        "sell_price": 4,
        "hunger": 25,
        "energy": 12,
        "health": 8,
        "happiness": 9,
        "description": "Spicy street tacos",
        "category": "fast_food",
        "emoji": "🌮"
    },
    "spaghetti": {
        "name": "🍝 Spaghetti",
        "price": 18,
        "sell_price": 8,
        "hunger": 40,
        "energy": 18,
        "health": 12,
        "happiness": 11,
        "description": "Italian pasta with sauce",
        "category": "meal",
        "emoji": "🍝"
    },
    "steak": {
        "name": "🥩 Steak",
        "price": 50,
        "sell_price": 25,
        "hunger": 60,
        "energy": 30,
        "health": 25,
        "happiness": 20,
        "description": "Premium grilled steak",
        "category": "luxury",
        "emoji": "🥩"
    },
    "sushi": {
        "name": "🍣 Sushi",
        "price": 40,
        "sell_price": 20,
        "hunger": 50,
        "energy": 25,
        "health": 20,
        "happiness": 18,
        "description": "Fresh sushi platter",
        "category": "luxury",
        "emoji": "🍣"
    },
    "cake": {
        "name": "🍰 Cake",
        "price": 25,
        "sell_price": 12,
        "hunger": 35,
        "energy": 20,
        "health": 5,
        "happiness": 25,
        "description": "Sweet dessert cake",
        "category": "dessert",
        "emoji": "🍰"
    },
    "donut": {
        "name": "🍩 Donut",
        "price": 6,
        "sell_price": 2,
        "hunger": 15,
        "energy": 10,
        "health": 2,
        "happiness": 8,
        "description": "Glazed donut",
        "category": "dessert",
        "emoji": "🍩"
    },
    "coffee": {
        "name": "☕ Coffee",
        "price": 7,
        "sell_price": 3,
        "hunger": 5,
        "energy": 30,
        "health": 0,
        "happiness": 8,
        "description": "Hot cup of coffee",
        "category": "drink",
        "emoji": "☕"
    },
    "energy_drink": {
        "name": "🥤 Energy Drink",
        "price": 12,
        "sell_price": 5,
        "hunger": 5,
        "energy": 50,
        "health": -5,
        "happiness": 5,
        "description": "Boosts energy but not healthy",
        "category": "drink",
        "emoji": "🥤"
    },
    "smoothie": {
        "name": "🧃 Smoothie",
        "price": 10,
        "sell_price": 4,
        "hunger": 20,
        "energy": 15,
        "health": 25,
        "happiness": 10,
        "description": "Healthy fruit smoothie",
        "category": "healthy",
        "emoji": "🧃"
    }
}


# ==================== VEHICLES ====================
VEHICLES = {
    "bicycle": {
        "name": "🚲 Bicycle",
        "price": 500,
        "sell_price": 250,
        "description": "Eco-friendly transportation",
        "speed_bonus": 5,
        "status_level": 1,
        "maintenance_cost": 10,
        "emoji": "🚲"
    },
    "skateboard": {
        "name": "🛹 Skateboard",
        "price": 300,
        "sell_price": 150,
        "description": "Cool street transportation",
        "speed_bonus": 3,
        "status_level": 1,
        "maintenance_cost": 5,
        "emoji": "🛹"
    },
    "scooter": {
        "name": "🛴 Scooter",
        "price": 800,
        "sell_price": 400,
        "description": "Electric scooter for city travel",
        "speed_bonus": 8,
        "status_level": 2,
        "maintenance_cost": 15,
        "emoji": "🛴"
    },
    "motorcycle": {
        "name": "🏍️ Motorcycle",
        "price": 5000,
        "sell_price": 2500,
        "description": "Fast two-wheeler",
        "speed_bonus": 25,
        "status_level": 3,
        "maintenance_cost": 75,
        "emoji": "🏍️"
    },
    "sedan": {
        "name": "🚗 Sedan",
        "price": 15000,
        "sell_price": 7500,
        "description": "Reliable family car",
        "speed_bonus": 30,
        "status_level": 4,
        "maintenance_cost": 100,
        "emoji": "🚗"
    },
    "suv": {
        "name": "🚙 SUV",
        "price": 35000,
        "sell_price": 17500,
        "description": "Spacious and powerful",
        "speed_bonus": 40,
        "status_level": 5,
        "maintenance_cost": 150,
        "emoji": "🚙"
    },
    "sports_car": {
        "name": "🏎️ Sports Car",
        "price": 50000,
        "sell_price": 25000,
        "description": "Fast and flashy",
        "speed_bonus": 60,
        "status_level": 6,
        "maintenance_cost": 200,
        "emoji": "🏎️"
    },
    "truck": {
        "name": "🚚 Truck",
        "price": 25000,
        "sell_price": 12500,
        "description": "Heavy-duty hauler",
        "speed_bonus": 35,
        "status_level": 4,
        "maintenance_cost": 120,
        "emoji": "🚚"
    },
    "luxury_sedan": {
        "name": "🚙 Luxury Sedan",
        "price": 120000,
        "sell_price": 60000,
        "description": "Premium comfort and style",
        "speed_bonus": 50,
        "status_level": 7,
        "maintenance_cost": 250,
        "emoji": "🚙"
    },
    "supercar": {
        "name": "🏎️ Supercar",
        "price": 250000,
        "sell_price": 125000,
        "description": "Ultimate performance machine",
        "speed_bonus": 90,
        "status_level": 8,
        "maintenance_cost": 500,
        "emoji": "🏎️"
    },
    "helicopter": {
        "name": "🚁 Helicopter",
        "price": 200000,
        "sell_price": 100000,
        "description": "Fly above traffic",
        "speed_bonus": 80,
        "status_level": 9,
        "maintenance_cost": 1000,
        "emoji": "🚁"
    },
    "yacht": {
        "name": "🛥️ Yacht",
        "price": 500000,
        "sell_price": 250000,
        "description": "Luxury ocean vessel",
        "speed_bonus": 70,
        "status_level": 9,
        "maintenance_cost": 2000,
        "emoji": "🛥️"
    },
    "private_jet": {
        "name": "🛩️ Private Jet",
        "price": 1000000,
        "sell_price": 500000,
        "description": "Fly in luxury",
        "speed_bonus": 100,
        "status_level": 10,
        "maintenance_cost": 5000,
        "emoji": "🛩️"
    }
}


# ==================== PROPERTIES ====================
PROPERTIES = {
    "tent": {
        "name": "⛺ Tent",
        "price": 100,
        "sell_price": 50,
        "description": "Basic shelter",
        "comfort": 10,
        "status_level": 1,
        "capacity": 1,
        "maintenance_cost": 5,
        "emoji": "⛺"
    },
    "apartment": {
        "name": "🏢 Apartment",
        "price": 5000,
        "sell_price": 2500,
        "description": "Cozy city apartment",
        "comfort": 30,
        "status_level": 2,
        "capacity": 2,
        "maintenance_cost": 100,
        "emoji": "🏢"
    },
    "small_house": {
        "name": "🏠 Small House",
        "price": 50000,
        "sell_price": 25000,
        "description": "Starter home",
        "comfort": 50,
        "status_level": 3,
        "capacity": 3,
        "maintenance_cost": 200,
        "emoji": "🏠"
    },
    "family_home": {
        "name": "🏡 Family Home",
        "price": 150000,
        "sell_price": 75000,
        "description": "Spacious family house",
        "comfort": 70,
        "status_level": 4,
        "capacity": 5,
        "maintenance_cost": 300,
        "emoji": "🏡"
    },
    "villa": {
        "name": "🏘️ Villa",
        "price": 350000,
        "sell_price": 175000,
        "description": "Luxury villa with pool",
        "comfort": 85,
        "status_level": 6,
        "capacity": 6,
        "maintenance_cost": 500,
        "emoji": "🏘️"
    },
    "mansion": {
        "name": "🏰 Mansion",
        "price": 500000,
        "sell_price": 250000,
        "description": "Grand estate",
        "comfort": 100,
        "status_level": 8,
        "capacity": 10,
        "maintenance_cost": 1000,
        "emoji": "🏰"
    },
    "penthouse": {
        "name": "🌆 Penthouse",
        "price": 1000000,
        "sell_price": 500000,
        "description": "Top floor luxury",
        "comfort": 120,
        "status_level": 9,
        "capacity": 8,
        "maintenance_cost": 2000,
        "emoji": "🌆"
    },
    "island": {
        "name": "🏝️ Private Island",
        "price": 10000000,
        "sell_price": 5000000,
        "description": "Your own paradise",
        "comfort": 200,
        "status_level": 10,
        "capacity": 20,
        "maintenance_cost": 5000,
        "emoji": "🏝️"
    }
}


# ==================== PET TYPES ====================
PET_TYPES = {
    "dog": {
        "name": "🐕 Dog",
        "price": 500,
        "sell_price": 250,
        "description": "Loyal companion",
        "buffs": ["xp_boost_5"],  # 5% XP boost
        "hunger_decay": 10,
        "happiness_decay": 5,
        "max_level": 10,
        "emoji": "🐕"
    },
    "cat": {
        "name": "🐈 Cat",
        "price": 400,
        "sell_price": 200,
        "description": "Independent friend",
        "buffs": ["luck_boost_3"],  # 3% luck boost
        "hunger_decay": 8,
        "happiness_decay": 4,
        "max_level": 10,
        "emoji": "🐈"
    },
    "parrot": {
        "name": "🦜 Parrot",
        "price": 800,
        "sell_price": 400,
        "description": "Talkative bird",
        "buffs": ["charisma_boost_10"],  # +10 charisma
        "hunger_decay": 5,
        "happiness_decay": 6,
        "max_level": 10,
        "emoji": "🦜"
    },
    "rabbit": {
        "name": "🐰 Rabbit",
        "price": 300,
        "sell_price": 150,
        "description": "Cute and cuddly",
        "buffs": ["happiness_regen_2"],  # +2 happiness per hour
        "hunger_decay": 12,
        "happiness_decay": 3,
        "max_level": 10,
        "emoji": "🐰"
    },
    "hamster": {
        "name": "🐹 Hamster",
        "price": 150,
        "sell_price": 75,
        "description": "Tiny and adorable",
        "buffs": ["energy_regen_1"],
        "hunger_decay": 15,
        "happiness_decay": 2,
        "max_level": 5,
        "emoji": "🐹"
    },
    "fish": {
        "name": "🐠 Fish",
        "price": 100,
        "sell_price": 50,
        "description": "Calming aquarium pet",
        "buffs": ["stress_reduction_5"],
        "hunger_decay": 3,
        "happiness_decay": 1,
        "max_level": 3,
        "emoji": "🐠"
    },
    "dragon": {
        "name": "🐉 Dragon",
        "price": 50000,
        "sell_price": 25000,
        "description": "Legendary creature",
        "buffs": ["money_boost_15", "xp_boost_10"],  # 15% money, 10% XP
        "hunger_decay": 20,
        "happiness_decay": 10,
        "max_level": 20,
        "emoji": "🐉"
    },
    "phoenix": {
        "name": "🔥 Phoenix",
        "price": 100000,
        "sell_price": 50000,
        "description": "Mythical immortal bird",
        "buffs": ["health_regen_10", "resurrection"],
        "hunger_decay": 18,
        "happiness_decay": 12,
        "max_level": 25,
        "emoji": "🔥"
    }
}


# ==================== SHOP CATEGORIES ====================
SHOP_CATEGORIES = {
    "food": {
        "name": "🍔 Food & Drinks",
        "description": "Restore hunger, health, and energy",
        "items": FOOD,
        "emoji": "🍔"
    },
    "vehicles": {
        "name": "🚗 Vehicles",
        "description": "Show off your ride and gain status",
        "items": VEHICLES,
        "emoji": "🚗"
    },
    "properties": {
        "name": "🏠 Properties",
        "description": "Better comfort = better sleep restoration",
        "items": PROPERTIES,
        "emoji": "🏠"
    },
    "pets": {
        "name": "🐾 Pets",
        "description": "Companions that give you buffs",
        "items": PET_TYPES,
        "emoji": "🐾"
    }
}


# ==================== ITEM HELPERS ====================
def get_item_by_id(item_id: str, category: str = None):
    """Get item data by ID, optionally filtered by category."""
    if category:
        if category == "food":
            return FOOD.get(item_id)
        elif category == "vehicle":
            return VEHICLES.get(item_id)
        elif category == "property":
            return PROPERTIES.get(item_id)
        elif category == "pet":
            return PET_TYPES.get(item_id)
    else:
        # Search all categories
        return (
            FOOD.get(item_id) or
            VEHICLES.get(item_id) or
            PROPERTIES.get(item_id) or
            PET_TYPES.get(item_id)
        )


def get_all_items():
    """Get all items from all categories."""
    return {
        "food": FOOD,
        "vehicles": VEHICLES,
        "properties": PROPERTIES,
        "pets": PET_TYPES
    }
