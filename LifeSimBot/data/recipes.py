# data/recipes.py

from __future__ import annotations

from typing import Dict, List


# ============= RECIPE DATA =============

RECIPES = {
    # ============= BASICS (Level 1+) =============
    "sandwich": {
        "name": "Sandwich",
        "emoji": "🥪",
        "category": "basics",
        "description": "A simple but delicious sandwich",
        "ingredients": {
            "bread": 2,
            "lettuce": 1,
            "tomato": 1,
        },
        "cooking_time": 10,
        "skill_required": 0,
        "xp_reward": 10,
        "effects": {
            "hunger": 40,
            "health": 10,
        },
        "sell_price": 150,
    },
    "salad": {
        "name": "Garden Salad",
        "emoji": "🥗",
        "category": "basics",
        "description": "Fresh and healthy salad",
        "ingredients": {
            "lettuce": 2,
            "tomato": 2,
            "cucumber": 1,
        },
        "cooking_time": 8,
        "skill_required": 0,
        "xp_reward": 10,
        "effects": {
            "hunger": 35,
            "health": 20,
        },
        "sell_price": 120,
    },
    "scrambled_eggs": {
        "name": "Scrambled Eggs",
        "emoji": "🍳",
        "category": "basics",
        "description": "Classic breakfast eggs",
        "ingredients": {
            "eggs": 3,
            "butter": 1,
        },
        "cooking_time": 12,
        "skill_required": 0,
        "xp_reward": 15,
        "effects": {
            "hunger": 45,
            "health": 15,
            "energy": 10,
        },
        "sell_price": 180,
    },
    
    # ============= MEALS (Level 5+) =============
    "pasta": {
        "name": "Spaghetti Pasta",
        "emoji": "🍝",
        "category": "meals",
        "description": "Classic Italian pasta with sauce",
        "ingredients": {
            "pasta_noodles": 1,
            "tomato_sauce": 1,
            "cheese": 1,
        },
        "cooking_time": 15,
        "skill_required": 5,
        "xp_reward": 25,
        "effects": {
            "hunger": 60,
            "health": 20,
            "energy": 15,
        },
        "sell_price": 300,
    },
    "pizza": {
        "name": "Homemade Pizza",
        "emoji": "🍕",
        "category": "meals",
        "description": "Fresh pizza with toppings",
        "ingredients": {
            "dough": 1,
            "tomato_sauce": 1,
            "cheese": 2,
            "pepperoni": 1,
        },
        "cooking_time": 20,
        "skill_required": 8,
        "xp_reward": 35,
        "effects": {
            "hunger": 70,
            "health": 25,
            "energy": 20,
        },
        "sell_price": 450,
    },
    "steak": {
        "name": "Grilled Steak",
        "emoji": "🥩",
        "category": "meals",
        "description": "Perfectly grilled steak",
        "ingredients": {
            "raw_steak": 1,
            "butter": 1,
            "seasoning": 1,
        },
        "cooking_time": 18,
        "skill_required": 10,
        "xp_reward": 40,
        "effects": {
            "hunger": 75,
            "health": 30,
            "energy": 25,
        },
        "sell_price": 600,
    },
    "burger": {
        "name": "Gourmet Burger",
        "emoji": "🍔",
        "category": "meals",
        "description": "Juicy burger with all the fixings",
        "ingredients": {
            "ground_beef": 1,
            "buns": 1,
            "lettuce": 1,
            "tomato": 1,
            "cheese": 1,
        },
        "cooking_time": 16,
        "skill_required": 7,
        "xp_reward": 30,
        "effects": {
            "hunger": 65,
            "health": 25,
            "energy": 20,
        },
        "sell_price": 400,
    },
    
    # ============= DESSERTS (Level 10+) =============
    "cake": {
        "name": "Chocolate Cake",
        "emoji": "🍰",
        "category": "desserts",
        "description": "Rich and moist chocolate cake",
        "ingredients": {
            "flour": 2,
            "sugar": 2,
            "eggs": 3,
            "chocolate": 2,
            "butter": 1,
        },
        "cooking_time": 25,
        "skill_required": 12,
        "xp_reward": 50,
        "effects": {
            "hunger": 50,
            "health": 15,
            "energy": 30,
        },
        "sell_price": 700,
    },
    "cookies": {
        "name": "Chocolate Chip Cookies",
        "emoji": "🍪",
        "category": "desserts",
        "description": "Warm, gooey cookies",
        "ingredients": {
            "flour": 1,
            "sugar": 1,
            "eggs": 1,
            "chocolate_chips": 1,
            "butter": 1,
        },
        "cooking_time": 15,
        "skill_required": 10,
        "xp_reward": 35,
        "effects": {
            "hunger": 40,
            "health": 10,
            "energy": 25,
        },
        "sell_price": 350,
    },
    "ice_cream": {
        "name": "Homemade Ice Cream",
        "emoji": "🍦",
        "category": "desserts",
        "description": "Creamy vanilla ice cream",
        "ingredients": {
            "milk": 2,
            "sugar": 1,
            "vanilla": 1,
        },
        "cooking_time": 20,
        "skill_required": 15,
        "xp_reward": 45,
        "effects": {
            "hunger": 35,
            "health": 20,
            "energy": 35,
        },
        "sell_price": 500,
    },
    
    # ============= ADVANCED (Level 20+) =============
    "sushi": {
        "name": "Sushi Platter",
        "emoji": "🍣",
        "category": "advanced",
        "description": "Artisan sushi rolls",
        "ingredients": {
            "rice": 2,
            "fish": 2,
            "seaweed": 1,
            "wasabi": 1,
        },
        "cooking_time": 30,
        "skill_required": 20,
        "xp_reward": 75,
        "effects": {
            "hunger": 80,
            "health": 40,
            "energy": 30,
        },
        "sell_price": 1000,
    },
    "ramen": {
        "name": "Gourmet Ramen",
        "emoji": "🍜",
        "category": "advanced",
        "description": "Rich, flavorful ramen bowl",
        "ingredients": {
            "noodles": 1,
            "broth": 1,
            "eggs": 2,
            "pork": 1,
            "vegetables": 1,
        },
        "cooking_time": 28,
        "skill_required": 18,
        "xp_reward": 70,
        "effects": {
            "hunger": 85,
            "health": 35,
            "energy": 40,
        },
        "sell_price": 900,
    },
    "lobster": {
        "name": "Lobster Thermidor",
        "emoji": "🦞",
        "category": "advanced",
        "description": "Fancy lobster dish",
        "ingredients": {
            "lobster": 1,
            "butter": 2,
            "cream": 1,
            "cheese": 1,
            "wine": 1,
        },
        "cooking_time": 35,
        "skill_required": 25,
        "xp_reward": 100,
        "effects": {
            "hunger": 90,
            "health": 50,
            "energy": 50,
        },
        "sell_price": 1500,
    },
}


# ============= RECIPE CATEGORIES =============

RECIPE_CATEGORIES = {
    "basics": {
        "name": "Basics",
        "emoji": "🍳",
        "description": "Simple recipes for beginners",
        "level_required": 0,
    },
    "meals": {
        "name": "Meals",
        "emoji": "🍽️",
        "description": "Hearty main courses",
        "level_required": 5,
    },
    "desserts": {
        "name": "Desserts",
        "emoji": "🍰",
        "description": "Sweet treats and pastries",
        "level_required": 10,
    },
    "advanced": {
        "name": "Advanced",
        "emoji": "👨‍🍳",
        "description": "Gourmet dishes for masters",
        "level_required": 20,
    },
}


# ============= COOKING INGREDIENTS (for shop) =============

COOKING_INGREDIENTS = {
    # Basic ingredients
    "bread": {"name": "Bread", "price": 20, "emoji": "🍞"},
    "lettuce": {"name": "Lettuce", "price": 10, "emoji": "🥬"},
    "tomato": {"name": "Tomato", "price": 15, "emoji": "🍅"},
    "cucumber": {"name": "Cucumber", "price": 12, "emoji": "🥒"},
    "eggs": {"name": "Eggs", "price": 25, "emoji": "🥚"},
    "butter": {"name": "Butter", "price": 30, "emoji": "🧈"},
    "cheese": {"name": "Cheese", "price": 40, "emoji": "🧀"},
    
    # Cooking ingredients
    "flour": {"name": "Flour", "price": 20, "emoji": "🌾"},
    "sugar": {"name": "Sugar", "price": 15, "emoji": "🍬"},
    "milk": {"name": "Milk", "price": 25, "emoji": "🥛"},
    "chocolate": {"name": "Chocolate", "price": 50, "emoji": "🍫"},
    "chocolate_chips": {"name": "Chocolate Chips", "price": 45, "emoji": "🍫"},
    "vanilla": {"name": "Vanilla", "price": 60, "emoji": "🌿"},
    
    # Meal ingredients
    "pasta_noodles": {"name": "Pasta Noodles", "price": 30, "emoji": "🍝"},
    "tomato_sauce": {"name": "Tomato Sauce", "price": 35, "emoji": "🥫"},
    "dough": {"name": "Pizza Dough", "price": 40, "emoji": "🍞"},
    "pepperoni": {"name": "Pepperoni", "price": 60, "emoji": "🍖"},
    "raw_steak": {"name": "Raw Steak", "price": 150, "emoji": "🥩"},
    "seasoning": {"name": "Seasoning", "price": 20, "emoji": "🧂"},
    "ground_beef": {"name": "Ground Beef", "price": 80, "emoji": "🥩"},
    "buns": {"name": "Burger Buns", "price": 25, "emoji": "🍞"},
    
    # Advanced ingredients
    "rice": {"name": "Rice", "price": 30, "emoji": "🍚"},
    "fish": {"name": "Fresh Fish", "price": 100, "emoji": "🐟"},
    "seaweed": {"name": "Seaweed", "price": 40, "emoji": "🌿"},
    "wasabi": {"name": "Wasabi", "price": 50, "emoji": "🟢"},
    "noodles": {"name": "Ramen Noodles", "price": 35, "emoji": "🍜"},
    "broth": {"name": "Broth", "price": 45, "emoji": "🥣"},
    "pork": {"name": "Pork", "price": 90, "emoji": "🥓"},
    "vegetables": {"name": "Vegetables", "price": 30, "emoji": "🥕"},
    "lobster": {"name": "Live Lobster", "price": 300, "emoji": "🦞"},
    "cream": {"name": "Heavy Cream", "price": 40, "emoji": "🥛"},
    "wine": {"name": "Cooking Wine", "price": 80, "emoji": "🍷"},
}
