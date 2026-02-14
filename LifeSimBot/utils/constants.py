# utils/constants.py
import discord

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
    STARTING_BALANCE = 500
    STARTING_BANK = 0
    STARTING_BANK_LIMIT = 5000
    
    # Daily Rewards
    DAILY_BASE = 1000
    DAILY_STREAK_BONUS = 250
    MAX_STREAK = 10
    DAILY_COOLDOWN_SECONDS = 20 * Times.HOUR
    
    # Transfers
    TRANSFER_MIN = 10
    TAX_RATE = 0.03 # 3% tax on user-to-user payments

class CrimeConfig:
    # Success Rates (0.0 to 1.0)
    ROB_SUCCESS_BASE = 0.45
    SHOPLIFT_SUCCESS_BASE = 0.60
    HEIST_SUCCESS_BASE = 0.25
    
    # Penalties
    FINE_PERCENT_MIN = 0.10 # Lose 10% of wallet if caught
    FINE_PERCENT_MAX = 0.30 # Lose 30% of wallet if caught
    
    # Jail Times (Seconds)
    JAIL_MIN = 5 * Times.MINUTE
    JAIL_MAX = 2 * Times.HOUR

class JobConfig:
    MAX_SHIFT_HOURS = 8
    BASE_PAY_PER_HOUR = 50
    XP_PER_WORK = 10

class Cooldowns:
    """Cooldowns in Seconds (Use Times class)."""
    
    class Economy:
        DAILY = 20 * Times.HOUR # Slightly less than 24h to be forgiving
        WORK = 1 * Times.HOUR
        BEG = 5 * Times.MINUTE
        
    class Crime:
        ROB = 2 * Times.HOUR
        HEIST = 1 * Times.DAY
        SHOPLIFT = 30 * Times.MINUTE
        ESCAPE_ATTEMPT = 15 * Times.MINUTE
        
    class Interaction:
        GIFT = 1 * Times.DAY
        BATTLE = 15 * Times.MINUTE


# -----------------------------------------------------------------------------
# Legacy flat constants used by some cogs/views
# -----------------------------------------------------------------------------

# Economy
STARTING_BANK_LIMIT = EconomyConfig.STARTING_BANK_LIMIT
DAILY_COOLDOWN = EconomyConfig.DAILY_COOLDOWN_SECONDS
WORK_COOLDOWN = Cooldowns.Economy.WORK

# Crime
ROB_COOLDOWN = Cooldowns.Crime.ROB
CRIME_COOLDOWN = Cooldowns.Crime.SHOPLIFT
ROB_ENERGY_COST = 15
MIN_ROB_BALANCE = 100

# Lifecycle / stats caps
SLEEP_COOLDOWN = 8 * Times.HOUR
MAX_HEALTH = 100
MAX_ENERGY = 100
MAX_HUNGER = 100
MAX_HAPPINESS = 100

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
