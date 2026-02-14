# data/jobs.py
"""
Enhanced Jobs System with 34 diverse careers across 5 categories
Each job has unique minigames, skills, and progression paths

Categories:
- Entry Level (7 jobs): Levels 1-2
- Skilled (7 jobs): Levels 3-5  
- Professional (8 jobs): Levels 6-9
- Expert (7 jobs): Levels 9-14
- Elite (5 jobs): Levels 15-25
"""
from __future__ import annotations

JOBS: dict[str, dict] = {
    # ==================== ENTRY LEVEL (Levels 1-2) ====================
    "cashier": {
        "name": "Cashier",
        "pay": (25, 50),
        "energy_cost": 15,
        "description": "Scan items quickly and accurately at the checkout",
        "level_required": 1,
        "category": "entry",
        "xp_reward": 10,
        "skill": "intelligence",
        "minigame": "sequence"
    },
    "waiter": {
        "name": "Waiter",
        "pay": (30, 55),
        "energy_cost": 16,
        "description": "Remember and deliver customer orders efficiently",
        "level_required": 1,
        "category": "entry",
        "xp_reward": 10,
        "skill": "charisma",
        "minigame": "memory"
    },
    "janitor": {
        "name": "Janitor",
        "pay": (20, 40),
        "energy_cost": 14,
        "description": "Clean and maintain buildings in proper order",
        "level_required": 1,
        "category": "entry",
        "xp_reward": 8,
        "skill": "strength",
        "minigame": "sequence"
    },
    "dogwalker": {
        "name": "Dog Walker",
        "pay": (22, 45),
        "energy_cost": 18,
        "description": "Keep multiple dogs happy and under control",
        "level_required": 1,
        "category": "entry",
        "xp_reward": 10,
        "skill": "charisma",
        "minigame": "reaction"
    },
    "paperboy": {
        "name": "Paper Delivery",
        "pay": (18, 35),
        "energy_cost": 12,
        "description": "Deliver newspapers to the right houses on time",
        "level_required": 1,
        "category": "entry",
        "xp_reward": 8,
        "skill": "luck",
        "minigame": "timing"
    },
    "fastfood": {
        "name": "Fast Food Worker",
        "pay": (24, 48),
        "energy_cost": 15,
        "description": "Prepare orders quickly during the lunch rush",
        "level_required": 1,
        "category": "entry",
        "xp_reward": 9,
        "skill": "cooking",
        "minigame": "sequence"
    },
    "receptionist": {
        "name": "Receptionist",
        "pay": (28, 52),
        "energy_cost": 14,
        "description": "Greet visitors and manage appointments professionally",
        "level_required": 2,
        "category": "entry",
        "xp_reward": 11,
        "skill": "charisma",
        "minigame": "memory"
    },
    
    # ==================== SKILLED (Levels 3-5) ====================
    "delivery": {
        "name": "Delivery Driver",
        "pay": (40, 75),
        "energy_cost": 20,
        "description": "Navigate optimal delivery routes efficiently",
        "level_required": 3,
        "category": "skilled",
        "xp_reward": 15,
        "skill": "intelligence",
        "minigame": "quiz"
    },
    "barista": {
        "name": "Barista",
        "pay": (35, 65),
        "energy_cost": 18,
        "description": "Craft coffee drinks with correct ingredients",
        "level_required": 3,
        "category": "skilled",
        "xp_reward": 15,
        "skill": "cooking",
        "minigame": "quiz"
    },
    "lifeguard": {
        "name": "Lifeguard",
        "pay": (45, 80),
        "energy_cost": 22,
        "description": "Spot and rescue swimmers in danger quickly",
        "level_required": 4,
        "category": "skilled",
        "xp_reward": 18,
        "skill": "strength",
        "minigame": "reaction"
    },
    "photographer": {
        "name": "Photographer",
        "pay": (50, 90),
        "energy_cost": 20,
        "description": "Capture the perfect shot with precise timing",
        "level_required": 4,
        "category": "skilled",
        "xp_reward": 18,
        "skill": "intelligence",
        "minigame": "timing"
    },
    "electrician": {
        "name": "Electrician",
        "pay": (55, 100),
        "energy_cost": 24,
        "description": "Connect electrical wiring in correct sequence",
        "level_required": 5,
        "category": "skilled",
        "xp_reward": 20,
        "skill": "intelligence",
        "minigame": "sequence"
    },
    "mechanic": {
        "name": "Mechanic",
        "pay": (60, 110),
        "energy_cost": 25,
        "description": "Diagnose and fix vehicle problems accurately",
        "level_required": 5,
        "category": "skilled",
        "xp_reward": 20,
        "skill": "intelligence",
        "minigame": "quiz"
    },
    "paramedic": {
        "name": "Paramedic",
        "pay": (58, 105),
        "energy_cost": 26,
        "description": "Respond to emergencies with speed and precision",
        "level_required": 5,
        "category": "skilled",
        "xp_reward": 22,
        "skill": "intelligence",
        "minigame": "reaction"
    },
    
    # ==================== PROFESSIONAL (Levels 6-9) ====================
    "chef": {
        "name": "Chef",
        "pay": (80, 150),
        "energy_cost": 28,
        "description": "Cook gourmet dishes with perfect timing",
        "level_required": 6,
        "category": "professional",
        "xp_reward": 25,
        "skill": "cooking",
        "minigame": "timing"
    },
    "teacher": {
        "name": "Teacher",
        "pay": (75, 140),
        "energy_cost": 26,
        "description": "Educate students and answer questions correctly",
        "level_required": 6,
        "category": "professional",
        "xp_reward": 25,
        "skill": "intelligence",
        "minigame": "quiz"
    },
    "nurse": {
        "name": "Nurse",
        "pay": (85, 155),
        "energy_cost": 30,
        "description": "Administer correct treatments to patients",
        "level_required": 7,
        "category": "professional",
        "xp_reward": 28,
        "skill": "intelligence",
        "minigame": "quiz"
    },
    "programmer": {
        "name": "Programmer",
        "pay": (100, 180),
        "energy_cost": 30,
        "description": "Debug code and develop software solutions",
        "level_required": 7,
        "category": "professional",
        "xp_reward": 30,
        "skill": "intelligence",
        "minigame": "quiz"
    },
    "accountant": {
        "name": "Accountant",
        "pay": (90, 165),
        "energy_cost": 28,
        "description": "Balance the books and manage finances",
        "level_required": 8,
        "category": "professional",
        "xp_reward": 28,
        "skill": "intelligence",
        "minigame": "quiz"
    },
    "architect": {
        "name": "Architect",
        "pay": (110, 200),
        "energy_cost": 32,
        "description": "Design buildings with precise specifications",
        "level_required": 9,
        "category": "professional",
        "xp_reward": 32,
        "skill": "intelligence",
        "minigame": "quiz"
    },
    "musician": {
        "name": "Musician",
        "pay": (70, 130),
        "energy_cost": 24,
        "description": "Keep the rhythm and entertain the crowd",
        "level_required": 6,
        "category": "professional",
        "xp_reward": 22,
        "skill": "charisma",
        "minigame": "timing"
    },
    "realtor": {
        "name": "Real Estate Agent",
        "pay": (95, 175),
        "energy_cost": 28,
        "description": "Close property deals with persuasion and timing",
        "level_required": 8,
        "category": "professional",
        "xp_reward": 30,
        "skill": "charisma",
        "minigame": "quiz"
    },
    
    # ==================== EXPERT (Levels 10-14) ====================
    "lawyer": {
        "name": "Lawyer",
        "pay": (150, 280),
        "energy_cost": 35,
        "description": "Win cases with strong legal arguments",
        "level_required": 10,
        "category": "expert",
        "xp_reward": 40,
        "skill": "charisma",
        "minigame": "quiz"
    },
    "doctor": {
        "name": "Doctor",
        "pay": (180, 320),
        "energy_cost": 38,
        "description": "Diagnose patients accurately and save lives",
        "level_required": 11,
        "category": "expert",
        "xp_reward": 45,
        "skill": "intelligence",
        "minigame": "quiz"
    },
    "pilot": {
        "name": "Pilot",
        "pay": (200, 350),
        "energy_cost": 40,
        "description": "Land planes safely under pressure",
        "level_required": 12,
        "category": "expert",
        "xp_reward": 50,
        "skill": "intelligence",
        "minigame": "reaction"
    },
    "scientist": {
        "name": "Scientist",
        "pay": (190, 340),
        "energy_cost": 38,
        "description": "Complete complex experiments correctly",
        "level_required": 13,
        "category": "expert",
        "xp_reward": 50,
        "skill": "intelligence",
        "minigame": "quiz"
    },
    "surgeon": {
        "name": "Surgeon",
        "pay": (250, 400),
        "energy_cost": 42,
        "description": "Perform precise life-saving operations",
        "level_required": 14,
        "category": "expert",
        "xp_reward": 55,
        "skill": "intelligence",
        "minigame": "timing"
    },
    "detective": {
        "name": "Detective",
        "pay": (140, 240),
        "energy_cost": 32,
        "description": "Spot clues and solve complex cases",
        "level_required": 10,
        "category": "expert",
        "xp_reward": 40,
        "skill": "intelligence",
        "minigame": "quiz"
    },
    "firefighter": {
        "name": "Firefighter",
        "pay": (120, 220),
        "energy_cost": 34,
        "description": "Respond fast and save lives from danger",
        "level_required": 9,
        "category": "expert",
        "xp_reward": 35,
        "skill": "strength",
        "minigame": "reaction"
    },
    
    # ==================== ELITE (Levels 15-25) ====================
    "trader": {
        "name": "Stock Trader",
        "pay": (200, 450),
        "energy_cost": 40,
        "description": "Predict market movements for maximum profit",
        "level_required": 15,
        "category": "elite",
        "xp_reward": 60,
        "skill": "business",
        "minigame": "quiz"
    },
    "hacker": {
        "name": "Ethical Hacker",
        "pay": (280, 500),
        "energy_cost": 45,
        "description": "Crack security systems ethically",
        "level_required": 16,
        "category": "elite",
        "xp_reward": 65,
        "skill": "intelligence",
        "minigame": "quiz"
    },
    "astronaut": {
        "name": "Astronaut",
        "pay": (350, 600),
        "energy_cost": 50,
        "description": "Complete dangerous space missions successfully",
        "level_required": 18,
        "category": "elite",
        "xp_reward": 70,
        "skill": "intelligence",
        "minigame": "reaction"
    },
    "ceo": {
        "name": "CEO",
        "pay": (400, 800),
        "energy_cost": 50,
        "description": "Make critical business decisions under pressure",
        "level_required": 20,
        "category": "elite",
        "xp_reward": 80,
        "skill": "business",
        "minigame": "quiz"
    },
    "president": {
        "name": "President",
        "pay": (500, 1000),
        "energy_cost": 55,
        "description": "Lead the nation with wisdom and charisma",
        "level_required": 25,
        "category": "elite",
        "xp_reward": 100,
        "skill": "charisma",
        "minigame": "quiz"
    },
}

# Total jobs count
TOTAL_JOBS = len(JOBS)

# Job categories info
JOB_CATEGORIES = {
    "entry": {
        "name": "Entry Level",
        "emoji": "🔰",
        "description": "Perfect for beginners just starting out",
        "color": 0x95A5A6
    },
    "skilled": {
        "name": "Skilled",
        "emoji": "⚙️",
        "description": "Requires experience and training",
        "color": 0x3498DB
    },
    "professional": {
        "name": "Professional",
        "emoji": "💼",
        "description": "For experienced professionals",
        "color": 0x9B59B6
    },
    "expert": {
        "name": "Expert",
        "emoji": "🎓",
        "description": "High-level positions requiring expertise",
        "color": 0xE67E22
    },
    "elite": {
        "name": "Elite",
        "emoji": "👑",
        "description": "The best of the best - pinnacle careers",
        "color": 0xF1C40F
    }
}

# Skill bonuses for jobs
SKILL_MULTIPLIERS = {
    "intelligence": 1.0,
    "charisma": 1.0,
    "strength": 0.8,
    "cooking": 0.9,
    "business": 1.2,
    "luck": 0.7,
}
