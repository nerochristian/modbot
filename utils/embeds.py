"""
Custom Embed Templates
"""

import discord
from datetime import datetime, timezone
from typing import Optional

from config import Config

_ZWS = "\u200b"
_LOG_PAD_MARKER = _ZWS * 5
_LOG_PAD_FIELD_NAME = _LOG_PAD_MARKER


def _count_lines(text: Optional[str]) -> int:
    if not text:
        return 0
    lines = str(text).splitlines()
    return max(1, len(lines))


def _strip_existing_log_padding(description: Optional[str]) -> Optional[str]:
    if not description:
        return description
    idx = description.rfind(_LOG_PAD_MARKER)
    if idx == -1:
        return description
    # Remove the marker line and any trailing padding after it.
    trimmed = description[:idx].rstrip("\n")
    return trimmed if trimmed else None


def _estimate_embed_lines(embed: discord.Embed) -> int:
    # Approximation of visible vertical space. Good enough for consistent padding.
    total = 0
    total += _count_lines(getattr(embed, "description", None))

    for field in getattr(embed, "fields", []) or []:
        total += 1  # field name line
        total += _count_lines(getattr(field, "value", None))

    try:
        # These are not "lines", but help prevent over-padding embeds that already
        # have a large image area (e.g. emoji approval requests).
        if getattr(getattr(embed, "image", None), "url", None):
            total += 12
        if getattr(getattr(embed, "thumbnail", None), "url", None):
            total += 2
    except Exception:
        pass

    return total


def force_log_embed_size(embed: discord.Embed, *, target_lines: Optional[int] = None) -> discord.Embed:
    """
    Best-effort embed size normalization for log channels.

    Discord doesn't support a fixed embed height; this pads the description with
    invisible lines until the embed reaches a consistent minimum height.
    """
    if target_lines is None:
        target_lines = int(getattr(Config, "LOG_EMBED_TARGET_LINES", 24))

    embed.description = _strip_existing_log_padding(getattr(embed, "description", None))

    # Strip any existing pad field so padding is deterministic and stays at the bottom.
    # Never write to embed._fields directly; that can corrupt discord.Embed internals.
    try:
        existing_fields = list(getattr(embed, "fields", []) or [])
        kept_fields = [
            f for f in existing_fields
            if getattr(f, "name", None) != _LOG_PAD_FIELD_NAME
        ]
        if len(kept_fields) != len(existing_fields):
            embed.clear_fields()
            for field in kept_fields:
                try:
                    embed.add_field(
                        name=str(getattr(field, "name", "")),
                        value=str(getattr(field, "value", "")),
                        inline=bool(getattr(field, "inline", False)),
                    )
                except Exception:
                    continue
    except Exception:
        pass

    current = _estimate_embed_lines(embed)
    needed = target_lines - current
    if needed <= 0:
        return embed

    # Add a bottom pad field so it doesn't push real fields down.
    # (Description padding creates an ugly blank block near the top.)
    if len(getattr(embed, "fields", []) or []) >= 25:
        return embed

    pad_total_lines = max(1, needed)
    pad_value_lines = max(1, pad_total_lines - 1)
    padding_value = "\n".join([_ZWS] * pad_value_lines)
    embed.add_field(name=_LOG_PAD_FIELD_NAME, value=padding_value, inline=False)

    return embed


class Colors:
    """Color constants for embeds"""
    ACCENT = getattr(Config, "EMBED_ACCENT_COLOR", Config.COLOR_EMBED)
    SUCCESS = ACCENT
    ERROR = ACCENT
    WARNING = ACCENT
    INFO = ACCENT
    MOD = ACCENT
    EMBED = ACCENT
    PINK = ACCENT
    GOLD = ACCENT
    DARK_RED = ACCENT


class ModEmbed:
    """Pre-built embed templates for moderation actions"""

    @staticmethod
    def success(title: str, description: Optional[str] = None) -> discord.Embed:
        """Green success embed"""
        embed = discord. Embed(
            title=f"✅ {title}",
            description=description,
            color=Colors.SUCCESS,
        )
        return embed

    @staticmethod
    def error(title: str, description: Optional[str] = None) -> discord.Embed:
        """Red error embed"""
        embed = discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=Colors. ERROR,
        )
        return embed

    @staticmethod
    def warning(title: str, description: Optional[str] = None) -> discord.Embed:
        """Orange warning embed"""
        embed = discord. Embed(
            title=f"⚠️ {title}",
            description=description,
            color=Colors.WARNING,
        )
        return embed

    @staticmethod
    def info(title:  str, description: Optional[str] = None) -> discord.Embed:
        """Blue info embed"""
        embed = discord.Embed(
            title=f"ℹ️ {title}",
            description=description,
            color=Colors.INFO,
        )
        return embed

    @staticmethod
    def mod_action(title: str, description: Optional[str] = None) -> discord.Embed:
        """Purple moderation action embed"""
        embed = discord. Embed(
            title=f"🔨 {title}",
            description=description,
            color=Colors.MOD,
        )
        return embed

    @staticmethod
    def case(case_number: int, action: str, user, moderator, reason: str) -> discord.Embed:
        """Case embed for mod logs"""
        embed = discord. Embed(
            title=f"Case #{case_number} | {action}",
            color=Colors.MOD,
        )
        embed.add_field(
            name="User",
            value=f"{user.mention} ({user.id})",
            inline=True
        )
        embed.add_field(
            name="Moderator",
            value=f"{moderator.mention}",
            inline=True
        )
        embed.add_field(
            name="Reason",
            value=reason or "No reason provided",
            inline=False
        )
        if hasattr(user, 'display_avatar'):
            embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    @staticmethod
    def log(title: str, description: Optional[str] = None, color: int = None) -> discord.Embed:
        """Generic log embed"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or Colors. EMBED,
        )
        return embed

    @staticmethod
    def staff_warning(staff:  discord.Member, reason: str, warn_count: int, strike_count: int) -> discord.Embed:
        """Staff warning embed"""
        embed = discord. Embed(
            title="⚠️ Staff Warning Applied",
            color=Colors.GOLD,
        )
        embed.add_field(
            name="Staff Member:",
            value=f"{staff. mention}\n{staff.name} ({staff.display_name})",
            inline=True
        )
        embed.add_field(
            name="Staff ID:",
            value=f"`{staff.id}`",
            inline=True
        )
        
        # Progress bar
        bar = ModEmbed._create_progress_bar(warn_count, 3)
        embed.add_field(
            name="Warning Count:",
            value=f"{bar}  **{warn_count}/3**",
            inline=False
        )
        embed.add_field(
            name="Reason:",
            value=f">>> {reason}",
            inline=False
        )
        embed.set_thumbnail(url=staff.display_avatar.url)
        
        if warn_count >= 3:
            embed.add_field(
                name="",
                value="⚠️ **Warning threshold reached!  Next sanction will be a strike.**",
                inline=False
            )
        
        return embed

    @staticmethod
    def staff_strike(staff: discord.Member, reason: str, warn_count: int, strike_count: int) -> discord.Embed:
        """Staff strike embed"""
        is_ban = strike_count >= 3
        embed = discord.Embed(
            title="⛔ Staff Strike Applied",
            color=Colors.DARK_RED if is_ban else Colors.PINK,
        )
        embed.add_field(
            name="Staff Member:",
            value=f"{staff. mention}\n{staff.name} ({staff.display_name})",
            inline=True
        )
        embed.add_field(
            name="Staff ID:",
            value=f"`{staff.id}`",
            inline=True
        )
        
        # Progress bar
        bar = ModEmbed._create_progress_bar(strike_count, 3)
        embed.add_field(
            name="Strike Count:",
            value=f"{bar}  **{strike_count}/3**",
            inline=False
        )
        embed.add_field(
            name="Reason:",
            value=f">>> {reason}",
            inline=False
        )
        embed.set_thumbnail(url=staff.display_avatar.url)
        
        if is_ban:
            embed. add_field(
                name="",
                value="🚨 **3 STRIKES REACHED - Staff member will be removed for 7 days.**",
                inline=False
            )
        
        return embed

    @staticmethod
    def staff_status(staff: discord.Member, warn_count: int, strike_count: int, recent_sanctions: list = None) -> discord.Embed:
        """Staff status embed"""
        embed = discord.Embed(
            title="📊 Staff Status",
            color=Colors. MOD,
        )
        
        embed.add_field(
            name="Staff Member:",
            value=f"{staff.mention}\n{staff.name} ({staff.display_name})",
            inline=True
        )
        embed.add_field(
            name="Staff ID:",
            value=f"`{staff.id}`",
            inline=True
        )
        embed.add_field(name="", value="", inline=False)
        
        # Status text
        status = ModEmbed._get_status_text(warn_count, strike_count)
        embed.add_field(name="Status:", value=status, inline=False)
        
        # Warning bar
        warn_bar = ModEmbed._create_progress_bar(warn_count, 3)
        embed.add_field(
            name="Warning Count:",
            value=f"{warn_bar}  **{warn_count}/3**",
            inline=True
        )
        
        # Strike bar
        strike_bar = ModEmbed._create_progress_bar(strike_count, 3)
        embed.add_field(
            name="Strike Count:",
            value=f"{strike_bar}  **{strike_count}/3**",
            inline=True
        )
        
        embed.set_thumbnail(url=staff.display_avatar.url)
        
        # Recent sanctions
        if recent_sanctions:
            recent = []
            for s in recent_sanctions[: 5]: 
                icon = "⚠️" if s. get('sanction_type') == 'warn' else "⛔"
                reason = s.get('reason', 'No reason')[: 40]
                recent.append(f"{icon} {reason}{'.. .' if len(s.get('reason', '')) > 40 else ''}")
            
            embed.add_field(
                name="Recent Sanctions:",
                value="\n".join(recent) if recent else "None",
                inline=False
            )
        
        embed.set_footer(text="3 Warnings = 1 Strike • 3 Strikes = 7 Day Staff Ban")
        
        return embed

    @staticmethod
    def _create_progress_bar(current: int, max_val: int) -> str:
        """Create a colored progress bar"""
        if current == 0:
            return "⬛⬛⬛"
        elif current == 1:
            return "🟪⬛⬛"
        elif current == 2:
            return "🟪🟪⬛"
        else:
            return "🟪🟪🟪"

    @staticmethod
    def _get_status_text(warns: int, strikes: int) -> str:
        """Get status description based on sanctions"""
        if strikes >= 3:
            return "🔴 **CRITICAL** - Staff ban required"
        elif strikes >= 2:
            return "🟠 **SEVERE** - One strike from removal"
        elif strikes >= 1 or warns >= 2:
            return "🟡 **WARNING** - Needs improvement"
        else:
            return "🟢 **GOOD STANDING**"

    @staticmethod
    def _get_status_emoji(warns: int, strikes: int) -> str:
        """Get status emoji"""
        if strikes >= 3:
            return "🔴"
        elif strikes >= 2:
            return "🟠"
        elif strikes >= 1 or warns >= 2:
            return "🟡"
        else:
            return "🟢"
