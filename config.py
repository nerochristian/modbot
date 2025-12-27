"""
Bot Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

def _parse_hex_color(value: str | None, default: int) -> int:
    if not value:
        return default
    s = value.strip()
    if s.startswith("#"):
        s = s[1:]
    if s.lower().startswith("0x"):
        s = s[2:]
    try:
        return int(s, 16)
    except Exception:
        return default


class Config:
    # Bot Token
    TOKEN = os.getenv('DISCORD_TOKEN')
    PREFIX = os.getenv('PREFIX', '!')
    
    # Global embed side color (set `EMBED_ACCENT_COLOR` to a hex like `#A020F0`)
    EMBED_ACCENT_COLOR = _parse_hex_color(os.getenv("EMBED_ACCENT_COLOR"), 0x5865F2)

    # Embed Colors (forced to the global accent color)
    COLOR_SUCCESS = EMBED_ACCENT_COLOR
    COLOR_ERROR = EMBED_ACCENT_COLOR
    COLOR_WARNING = EMBED_ACCENT_COLOR
    COLOR_INFO = EMBED_ACCENT_COLOR
    COLOR_MOD = EMBED_ACCENT_COLOR
    COLOR_BRAND = EMBED_ACCENT_COLOR
    COLOR_EMBED = EMBED_ACCENT_COLOR
    COLOR_PINK = EMBED_ACCENT_COLOR
    COLOR_GOLD = EMBED_ACCENT_COLOR
    COLOR_DARK_RED = EMBED_ACCENT_COLOR

    # Log embed sizing (best-effort padding; higher = taller)
    LOG_EMBED_TARGET_LINES = int(os.getenv("LOG_EMBED_TARGET_LINES", "24"))

    # Welcome system
    WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "1454276301623005336"))
    WELCOME_SERVER_NAME = os.getenv("WELCOME_SERVER_NAME", "The Supreme People")
    WELCOME_SYSTEM_NAME = os.getenv("WELCOME_SYSTEM_NAME", "Supreme Council")
    # Welcome card accent (border/pill); set to a hex like `#D9D1B2`
    WELCOME_CARD_ACCENT_COLOR = _parse_hex_color(os.getenv("WELCOME_CARD_ACCENT_COLOR"), 0xD9D1B2)

    # Branding (Components v2 panels)
    SERVER_LOGO_URL = os.getenv(
        "SERVER_LOGO_URL",
        "https://cdn.discordapp.com/icons/1388268039195201677/21d33244f4779190ff1395121d9fb69a.png?size=1024",
    )
    SERVER_BANNER_URL = os.getenv(
        "SERVER_BANNER_URL",
        "https://cdn.discordapp.com/attachments/1430639019582034013/1454273701716693053/unbranded.jpg?ex=69507d6d&is=694f2bed&hm=13f8884818beaa821b2bd9dea27ef2bb205c5045d71d2b71a3453e6c458e2f46&",
    )

    # Verification
    VERIFY_TUTORIAL_VIDEO_URL = os.getenv(
        "VERIFY_TUTORIAL_VIDEO_URL",
        "https://example.com/verification-tutorial.mp4",
    )
    
    # Emojis
    EMOJI_SUCCESS = "✅"
    EMOJI_ERROR = "❌"
    EMOJI_WARNING = "⚠️"
    EMOJI_INFO = "ℹ️"
    EMOJI_LOADING = "⏳"
    EMOJI_LOCK = "🔒"
    EMOJI_UNLOCK = "🔓"
    EMOJI_BAN = "🔨"
    EMOJI_KICK = "👢"
    EMOJI_MUTE = "🔇"
    EMOJI_WARN = "⚠️"
    
    # Limits
    MAX_WARNINGS = 5
    MAX_MESSAGE_LENGTH = 2000
    PURGE_LIMIT = 1000
    
    # Timeouts (seconds)
    BUTTON_TIMEOUT = 180
    MENU_TIMEOUT = 60
    TICKET_CLOSE_DELAY = 5
    
    # Staff Sanction System
    WARNS_PER_STRIKE = 3
    STRIKES_FOR_BAN = 3
    STAFF_BAN_DAYS = 7
    
    # AutoMod Defaults
    DEFAULT_SPAM_THRESHOLD = 5
    DEFAULT_SPAM_TIMEOUT = 60
    DEFAULT_MUTE_DURATION = 3600
    DEFAULT_CAPS_PERCENTAGE = 70
    DEFAULT_MAX_MENTIONS = 5
