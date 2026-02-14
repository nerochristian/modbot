# utils/format.py
import datetime
from .constants import Emojis

def format_number(value: int, short: bool = True) -> str:
    """Formats a number with commas or short suffixes (k, M, B)."""
    if value is None:
        return "0"

    try:
        num = float(value)
    except (TypeError, ValueError):
        return "0"

    if not short:
        return f"{int(num):,}"

    abs_num = abs(num)
    if abs_num >= 1_000_000_000:
        s = f"{num / 1_000_000_000:.1f}B"
    elif abs_num >= 1_000_000:
        s = f"{num / 1_000_000:.1f}M"
    elif abs_num >= 1_000:
        s = f"{num / 1_000:.1f}k"
    else:
        s = str(int(num))

    return s.replace(".0", "")

def format_currency(amount: int, short: bool = False) -> str:
    """
    Formats an integer into a currency string.
    short=True -> 1.5M, 10k
    short=False -> 1,500,000
    """
    if amount is None:
        return f"{Emojis.COIN} 0"
        
    if short:
        # Abbreviated formatting for Leaderboards/Compact Views
        if amount >= 1_000_000_000:
            val = f"{amount / 1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            val = f"{amount / 1_000_000:.1f}M"
        elif amount >= 1_000:
            val = f"{amount / 1_000:.1f}k"
        else:
            val = str(amount)
        # Remove .0 if it exists (e.g. 10.0k -> 10k)
        val = val.replace(".0", "")
        return f"{Emojis.COIN} {val}"
    
    # Standard comma formatting
    return f"{Emojis.COIN} {amount:,}"

def money(amount: int, short: bool = False) -> str:
    """Formats an amount as '$1,234' (or '$1.2k' when short=True)."""
    if amount is None:
        amount = 0
    if short:
        return f"${format_number(amount, short=True)}"
    return f"${int(amount):,}"

def format_duration(seconds: int) -> str:
    """
    Converts seconds to human readable text.
    Example: 3665 -> '1h 1m 5s'
    """
    if not seconds or seconds < 0:
        return "0s"
        
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    
    parts = []
    if d > 0: parts.append(f"{d}d")
    if h > 0: parts.append(f"{h}h")
    if m > 0: parts.append(f"{m}m")
    if s > 0: parts.append(f"{s}s")
    
    return " ".join(parts) if parts else "<1s"

def format_time(seconds: int) -> str:
    """Alias for `format_duration` used across the bot."""
    return format_duration(seconds)

def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Formats a fraction (0.0 to 1.0) as a percentage string.
    Example: 0.125 -> '12.5%'
    """
    if value is None:
        return "0%"

    try:
        pct = float(value) * 100
    except (TypeError, ValueError):
        return "0%"

    s = f"{pct:.{decimals}f}".rstrip("0").rstrip(".")
    return f"{s}%"

def progress_bar(current: int, total: int, length: int = 10, fill: str = "🟩", empty: str = "⬛") -> str:
    """Renders a simple text progress bar."""
    try:
        total_val = float(total)
        current_val = float(current)
    except (TypeError, ValueError):
        total_val = 0
        current_val = 0

    if total_val <= 0:
        filled = 0
    else:
        ratio = max(0.0, min(1.0, current_val / total_val))
        filled = int(round(ratio * length))

    filled = max(0, min(length, filled))
    return (fill * filled) + (empty * (length - filled))

def level_from_xp(total_xp: int, base: int = 100) -> tuple[int, int, int]:
    """
    Converts a cumulative XP value into (level, current_xp, needed_xp).
    Uses an increasing threshold: needed = level * base.
    """
    try:
        xp = int(total_xp)
    except (TypeError, ValueError):
        xp = 0

    level = 1
    while xp >= level * base and level < 10_000:
        xp -= level * base
        level += 1

    needed = level * base
    return level, xp, needed

def format_dt(dt: datetime.datetime, style: str = "f") -> str:
    """
    Returns a Discord Timestamp string.
    Styles:
    t: Short Time (16:20)
    T: Long Time (16:20:30)
    d: Short Date (20/04/2021)
    D: Long Date (20 April 2021)
    f: Short Date Time (20 April 2021 16:20)
    F: Long Date Time (Tuesday, 20 April 2021 16:20)
    R: Relative (2 months ago)
    """
    if not dt:
        return "Unknown"
    timestamp = int(dt.timestamp())
    return f"<t:{timestamp}:{style}>"
