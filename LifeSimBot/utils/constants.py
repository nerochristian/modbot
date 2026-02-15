# utils/constants.py
import discord

try:
    # Package import path: LifeSimBot.utils.constants
    from ..config import LifeSimConfig
except Exception:
    # Script import path: utils.constants (cwd=LifeSimBot)
    from config import LifeSimConfig

class Times:
    """Time constants in seconds."""
    SECOND = 1
    MINUTE = 60
    HOUR = 3600
    DAY = 86400
    WEEK = 604800
    MONTH = 2592000 # 30 Days

class Emojis:
    """
    Centralized Emoji Repository.
    Replace the IDs with your own custom emojis for a 'Premium' feel.
    """
    # UI Elements
    LOADING = "⏳"
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOCK = "🔒"
    UNLOCK = "🔓"
    
    # Economy
    COIN = "🪙" # Replace with <:coin:123...>
    BANK = "🏦"
    CARD = "💳"
    MONEY_BAG = "💰"
    GRAPH_UP = "📈"
    GRAPH_DOWN = "📉"
    
    # Life Sim
    HEALTH = "❤️"
    ENERGY = "⚡"
    HUNGER = "🍗"
    HAPPY = "😄"
    SMART = "🧠"
    
    # Jobs & Tools
    WORK = "💼"
    PICKAXE = "⛏️"
    FISHING_ROD = "🎣"
    COMPUTER = "💻"
    POLICE = "🚓"
    GUN = "🔫"
    HANDCUFFS = "🔗"

class Colors:
    """Hex colors for V2 Components and Embeds."""
    # Standard Discord Colors
    BLURPLE = 0x5865F2
    GREEN = 0x57F287
    RED = 0xED4245
    YELLOW = 0xFEE75C
    WHITE = 0xFFFFFF
    BLACK = 0x000000
    
    # Themed Colors
    DARK_BG = 0x2b2d31  # Matches Discord Dark Mode
    GOLD = 0xF1C40F
    SILVER = 0x95A5A6
    BRONZE = 0xCD7F32
    CRIME = 0x992D22    # Dark Red
    POLICE = 0x3498DB   # Blue
    LIFE = 0xE91E63     # Pink

class Paths:
    """File paths for the system."""
    DB_NAME = "life_sim.db"
    LOG_DIR = "logs"
    COGS_DIR = "./cogs"
    ASSETS_DIR = "./assets" # For local images if needed

# -----------------------------------------------------------------------------
# GAME BALANCE CONFIGURATION
# -----------------------------------------------------------------------------

class EconomyConfig:
    STARTING_BALANCE = LifeSimConfig.ECONOMY.STARTING_BALANCE
    STARTING_BANK = LifeSimConfig.ECONOMY.STARTING_BANK
    STARTING_BANK_LIMIT = LifeSimConfig.ECONOMY.STARTING_BANK_LIMIT
    
    # Daily Rewards
    DAILY_BASE = LifeSimConfig.ECONOMY.DAILY_BASE
    DAILY_STREAK_BONUS = LifeSimConfig.ECONOMY.DAILY_STREAK_BONUS
    MAX_STREAK = LifeSimConfig.ECONOMY.MAX_STREAK
    DAILY_COOLDOWN_SECONDS = LifeSimConfig.COOLDOWNS.DAILY
    
    # Transfers
    TRANSFER_MIN = LifeSimConfig.ECONOMY.TRANSFER_MIN
    TAX_RATE = LifeSimConfig.ECONOMY.TAX_RATE # 3% tax on user-to-user payments

class CrimeConfig:
    # Success Rates (0.0 to 1.0)
    ROB_SUCCESS_BASE = LifeSimConfig.CRIME.ROB_SUCCESS_BASE
    SHOPLIFT_SUCCESS_BASE = LifeSimConfig.CRIME.SHOPLIFT_SUCCESS_BASE
    HEIST_SUCCESS_BASE = LifeSimConfig.CRIME.HEIST_SUCCESS_BASE
    
    # Penalties
    FINE_PERCENT_MIN = LifeSimConfig.CRIME.FINE_PERCENT_MIN # Lose 10% of wallet if caught
    FINE_PERCENT_MAX = LifeSimConfig.CRIME.FINE_PERCENT_MAX # Lose 30% of wallet if caught
    
    # Jail Times (Seconds)
    JAIL_MIN = LifeSimConfig.CRIME.JAIL_MIN
    JAIL_MAX = LifeSimConfig.CRIME.JAIL_MAX

class JobConfig:
    MAX_SHIFT_HOURS = LifeSimConfig.JOBS.MAX_SHIFT_HOURS
    BASE_PAY_PER_HOUR = LifeSimConfig.JOBS.BASE_PAY_PER_HOUR
    XP_PER_WORK = LifeSimConfig.JOBS.XP_PER_WORK

class Cooldowns:
    """Cooldowns in Seconds (Use Times class)."""
    
    class Economy:
        DAILY = LifeSimConfig.COOLDOWNS.DAILY
        WORK = LifeSimConfig.COOLDOWNS.WORK
        BEG = LifeSimConfig.COOLDOWNS.BEG
        FARM = LifeSimConfig.COOLDOWNS.FARM
        FISH = LifeSimConfig.COOLDOWNS.FISH
        
    class Crime:
        ROB = LifeSimConfig.COOLDOWNS.ROB
        HEIST = LifeSimConfig.COOLDOWNS.HEIST
        SHOPLIFT = LifeSimConfig.COOLDOWNS.CRIME
        ESCAPE_ATTEMPT = LifeSimConfig.COOLDOWNS.ESCAPE_ATTEMPT
        
    class Interaction:
        GIFT = LifeSimConfig.COOLDOWNS.GIFT
        BATTLE = LifeSimConfig.COOLDOWNS.BATTLE


# -----------------------------------------------------------------------------
# Legacy flat constants used by some cogs/views
# -----------------------------------------------------------------------------

# Economy
STARTING_BANK_LIMIT = EconomyConfig.STARTING_BANK_LIMIT
DAILY_COOLDOWN = EconomyConfig.DAILY_COOLDOWN_SECONDS
WORK_COOLDOWN = Cooldowns.Economy.WORK
BEG_COOLDOWN = Cooldowns.Economy.BEG
FARM_COOLDOWN = Cooldowns.Economy.FARM
FISH_COOLDOWN = Cooldowns.Economy.FISH

# Crime
ROB_COOLDOWN = Cooldowns.Crime.ROB
CRIME_COOLDOWN = Cooldowns.Crime.SHOPLIFT
HEIST_COOLDOWN = Cooldowns.Crime.HEIST
ROB_ENERGY_COST = LifeSimConfig.CRIME.ROB_ENERGY_COST
MIN_ROB_BALANCE = LifeSimConfig.CRIME.MIN_ROB_BALANCE

# Lifecycle / stats caps
SLEEP_COOLDOWN = LifeSimConfig.COOLDOWNS.SLEEP
MAX_HEALTH = LifeSimConfig.CAPS.MAX_HEALTH
MAX_ENERGY = LifeSimConfig.CAPS.MAX_ENERGY
MAX_HUNGER = LifeSimConfig.CAPS.MAX_HUNGER
MAX_HAPPINESS = LifeSimConfig.CAPS.MAX_HAPPINESS

# Skills
SKILL_EMOJIS = {
    "strength": "💪",
    "intelligence": "🧠",
    "charisma": "😎",
    "luck": "🍀",
    "cooking": "🍳",
    "crime": "🗡️",
    "business": "🏢",
}
