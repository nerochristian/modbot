"""
Custom Embed Templates
"""

import discord
from datetime import datetime, timezone
from typing import Iterable, Optional

from config import Config
from utils.status_emojis import status_embed_pad_line, get_app_emoji

_ZWS = "\u200b"
_LOG_PAD_MARKER = _ZWS * 5
_LOG_PAD_FIELD_NAME = _LOG_PAD_MARKER


def stamp_actor_footer(
    embed: discord.Embed,
    actor: object,
    *,
    timestamp: Optional[datetime] = None,
) -> discord.Embed:
    """Add Discord's native actor avatar/name/time footer to a response embed."""
    if actor is None:
        return embed

    actor_name = str(getattr(actor, "name", None) or actor).strip()
    if not actor_name:
        return embed

    actor_label = f"@{actor_name}"
    existing_text = str(
        getattr(getattr(embed, "footer", None), "text", None) or ""
    ).strip()
    if existing_text == actor_label or existing_text.startswith(f"{actor_label} •"):
        footer_text = existing_text
    elif existing_text:
        footer_text = f"{actor_label} • {existing_text}"
    else:
        footer_text = actor_label

    actor_icon = getattr(getattr(actor, "display_avatar", None), "url", None)
    footer_kwargs = {"text": footer_text}
    if actor_icon:
        footer_kwargs["icon_url"] = str(actor_icon)
    embed.set_footer(**footer_kwargs)

    if embed.timestamp is None:
        embed.timestamp = timestamp or datetime.now(timezone.utc)
    return embed


def _count_lines(text: Optional[str]) -> int:
    if not text:
        return 0
    lines = str(text).splitlines()
    return max(1, len(lines))


def compact_text(value: object, *, max_length: int = 900) -> str:
    """Normalize short embed text without creating visual dead space."""
    text = str(value or "").strip()
    if not text:
        return "`None`"

    lines = [" ".join(line.split()) for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    if len(text) > max_length:
        text = text[: max(0, max_length - 3)].rstrip() + "..."
    return text or "`None`"


def compact_kv_lines(
    rows: Iterable[tuple[str, object]],
    *,
    max_value_length: int = 220,
) -> str:
    """Render short facts as dense one-line label/value rows."""
    lines: list[str] = []
    for label, value in rows:
        clean_label = str(label or "").strip().rstrip(":")
        if not clean_label:
            continue
        lines.append(f"**{clean_label}:** {compact_text(value, max_length=max_value_length)}")
    return "\n".join(lines)


def quoted_lines(lines: Iterable[object]) -> str:
    """Render compact log details as a single Discord blockquote."""
    return "\n".join(f"> {line}" for line in lines if str(line or "").strip())


def sapphire_log_embed(
    *,
    title: str,
    color: int,
    detail_lines: Iterable[object],
    message_text: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    footer_text: Optional[str] = None,
    footer_icon_url: Optional[str] = None,
) -> discord.Embed:
    """Build the shared compact card used by Docket's modern log surfaces."""
    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )

    rendered_details = quoted_lines(detail_lines)
    if rendered_details:
        embed.description = rendered_details

    if message_text is not None:
        value = (message_text or "").strip() or "*No content*"
        if len(value) > 1024:
            value = value[:1021].rstrip() + "..."
        embed.add_field(name="Message", value=value, inline=False)

    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    if footer_text:
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)

    return embed


def moderation_list_embed(
    *,
    title: str,
    color: int,
    entries: Iterable[object],
    summary_rows: Iterable[tuple[str, object]] = (),
    thumbnail_url: Optional[str] = None,
    footer_text: Optional[str] = None,
) -> discord.Embed:
    """Build a compact moderation history/list card without stacked fields."""
    sections: list[str] = []
    summary = compact_kv_lines(summary_rows, max_value_length=120)
    if summary:
        sections.append(quoted_lines(summary.splitlines()))

    clean_entries = [str(entry).strip() for entry in entries if str(entry).strip()]
    if clean_entries:
        sections.append("\n\n".join(clean_entries))

    description = "\n\n".join(sections) or "*Nothing to show.*"
    if len(description) > 4096:
        description = description[:4093].rstrip() + "..."

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if footer_text:
        embed.set_footer(text=footer_text)
    return embed


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
        target_lines = int(getattr(Config, "LOG_EMBED_TARGET_LINES", 0))
    if target_lines <= 0:
        return embed

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
    SUCCESS = 0x22C55E
    ERROR = 0xEF4444
    WARNING = 0xF59E0B
    INFO = 0x2563EB
    MOD = ACCENT
    EMBED = ACCENT
    PINK = 0xEC4899
    GOLD = 0xF59E0B
    DARK_RED = 0x991B1B


class ModEmbed:
    """Pre-built embed templates for moderation actions"""

    @staticmethod
    def _emoji(config_attr: str, fallback: str) -> str:
        # Map config attrs to emoji kinds for app emoji lookup
        _CONFIG_TO_KIND = {
            "EMOJI_SUCCESS": "success",
            "EMOJI_ERROR": "error",
            "EMOJI_WARNING": "warning",
            "EMOJI_INFO": "info",
            "EMOJI_LOCK": "lock",
            "EMOJI_UNLOCK": "unlock",
            "EMOJI_LOADING": "loading",
            "EMOJI_BAN": "ban",
            "EMOJI_KICK": "kick",
            "EMOJI_MUTE": "mute",
            "EMOJI_WARN": "warn",
        }
        kind = _CONFIG_TO_KIND.get(config_attr)
        if kind:
            app_emoji = get_app_emoji(kind)
            if app_emoji:
                return app_emoji
        value = str(getattr(Config, config_attr, "") or "").strip()
        return value or fallback

    @staticmethod
    def _clean_title(title: str) -> str:
        cleaned = (title or "").strip()
        # Keep mentions/user tags intact (e.g. "<@123> muted").
        if cleaned.startswith("<@") or cleaned.startswith("@"):
            return cleaned
        while cleaned and not cleaned[0].isalnum():
            cleaned = cleaned[1:].lstrip()
        return cleaned or "Update"

    @staticmethod
    def _quote_description_lines(description: Optional[str]) -> str:
        body = (description or "").strip()
        if not body:
            return ""
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        return "\n".join(f"> {line}" for line in lines)

    @staticmethod
    def _status_embed(
        *,
        icon: str,
        title: str,
        description: Optional[str],
        color: int,
    ) -> discord.Embed:
        header = f"{icon} **{ModEmbed._clean_title(title)}**"
        quoted_body = ModEmbed._quote_description_lines(description)
        message = header if not quoted_body else f"{header}\n{quoted_body}"

        # Keep short status embeds from collapsing into tiny cards.
        min_chars = max(0, int(getattr(Config, "STATUS_EMBED_MIN_WIDTH_CHARS", 32)))
        if min_chars > 0:
            longest = 0
            for line in message.splitlines():
                stripped = line.replace("**", "").replace("`", "")
                longest = max(longest, len(stripped))
            if longest < min_chars:
                pad = status_embed_pad_line(min_chars - longest)
                if pad:
                    lines = message.splitlines()
                    if lines:
                        lines[0] = f"{lines[0]}{pad}"
                        message = "\n".join(lines)
                    else:
                        message = pad

        return discord.Embed(description=message, color=color)

    @staticmethod
    def success(title: str, description: Optional[str] = None) -> discord.Embed:
        """Green success embed"""
        return ModEmbed._status_embed(
            icon=ModEmbed._emoji("EMOJI_SUCCESS", "\u2705"),
            title=title,
            description=description,
            color=Colors.SUCCESS,
        )

    @staticmethod
    def error(title: str, description: Optional[str] = None) -> discord.Embed:
        """Red error embed"""
        return ModEmbed._status_embed(
            icon=ModEmbed._emoji("EMOJI_ERROR", "\u274c"),
            title=title,
            description=description,
            color=Colors.ERROR,
        )

    @staticmethod
    def warning(title: str, description: Optional[str] = None) -> discord.Embed:
        """Orange warning embed"""
        return ModEmbed._status_embed(
            icon=ModEmbed._emoji("EMOJI_WARNING", "\u26a0\ufe0f"),
            title=title,
            description=description,
            color=Colors.WARNING,
        )

    @staticmethod
    def info(title: str, description: Optional[str] = None) -> discord.Embed:
        """Blue info embed"""
        return ModEmbed._status_embed(
            icon=ModEmbed._emoji("EMOJI_INFO", "\u2139\ufe0f"),
            title=title,
            description=description,
            color=Colors.INFO,
        )

    @staticmethod
    def mod_action(title: str, description: Optional[str] = None) -> discord.Embed:
        """Purple moderation action embed"""
        return ModEmbed._status_embed(
            icon=ModEmbed._emoji("EMOJI_BAN", "\U0001f528"),
            title=title,
            description=description,
            color=Colors.MOD,
        )

    @staticmethod
    def moderation_response(action: str, content: str) -> discord.Embed:
        """Render a configured moderation confirmation as a branded status embed."""
        normalized = str(action or "").strip().casefold()
        presentation = {
            "ban": ("EMOJI_BAN", "\U0001f528", Colors.DARK_RED),
            "softban": ("EMOJI_BAN", "\U0001f528", Colors.DARK_RED),
            "kick": ("EMOJI_KICK", "\U0001f462", Colors.ERROR),
            "mute": ("EMOJI_MUTE", "\U0001f507", Colors.ERROR),
            "unban": ("EMOJI_UNLOCK", "\U0001f513", Colors.SUCCESS),
            "unmute": ("EMOJI_UNLOCK", "\U0001f513", Colors.SUCCESS),
            "quarantine": ("EMOJI_LOCK", "\U0001f512", Colors.WARNING),
        }
        config_attr, fallback, color = presentation.get(
            normalized,
            ("EMOJI_SUCCESS", "\u2705", Colors.SUCCESS),
        )
        icon = ModEmbed._emoji(config_attr, fallback)
        body = str(content or "Action completed.").strip()
        return discord.Embed(description=f"{icon} {body}", color=color)

    @staticmethod
    def punishment_notice(
        *,
        guild: discord.Guild,
        action: str,
        reason: str,
        case_number: int,
        duration: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        guidance: Optional[str] = None,
    ) -> discord.Embed:
        """Build the classic fallback for private punishment notifications."""
        normalized = str(action or "Moderation action").strip().casefold()
        presentation = {
            "warn": ("EMOJI_WARN", "⚠️", "Warning issued", Colors.WARNING),
            "kick": ("EMOJI_KICK", "👢", "Removed from server", Colors.ERROR),
            "ban": ("EMOJI_BAN", "🔨", "Banned from server", Colors.DARK_RED),
            "softban": ("EMOJI_BAN", "🔨", "Softban applied", Colors.ERROR),
            "tempban": ("EMOJI_BAN", "🔨", "Temporary ban applied", Colors.DARK_RED),
            "mute": ("EMOJI_MUTE", "🔇", "Timeout applied", Colors.ERROR),
            "quarantine": ("EMOJI_LOCK", "🔒", "Quarantine applied", Colors.WARNING),
        }
        config_attr, fallback, title, color = presentation.get(
            normalized,
            ("EMOJI_WARNING", "⚠️", "Moderation action", Colors.WARNING),
        )
        icon = ModEmbed._emoji(config_attr, fallback)
        clean_reason = compact_text(reason or "No reason provided", max_length=900)
        description = f"> **Reason:** {clean_reason}"
        if guidance:
            description += f"\n\n{str(guidance).strip()}"

        embed = discord.Embed(
            title=f"{icon} {title}",
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Server", value=guild.name, inline=True)
        embed.add_field(name="Case", value=f"#{case_number}", inline=True)
        if duration:
            embed.add_field(name="Duration", value=duration, inline=True)
        if expires_at is not None:
            embed.add_field(
                name="Ends",
                value=f"<t:{int(expires_at.timestamp())}:R>",
                inline=True,
            )

        guild_icon = getattr(getattr(guild, "icon", None), "url", None)
        footer_kwargs = {"text": f"{guild.name} moderation"}
        if guild_icon:
            footer_kwargs["icon_url"] = str(guild_icon)
        embed.set_footer(**footer_kwargs)
        return embed

    @staticmethod
    def case(case_number: int, action: str, user, moderator, reason: str) -> discord.Embed:
        """Case embed for mod logs"""
        embed = discord.Embed(
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
            color=color or Colors.EMBED,
        )
        return embed

    @staticmethod
    def staff_warning(staff:  discord.Member, reason: str, warn_count: int, strike_count: int) -> discord.Embed:
        """Staff warning embed"""
        embed = discord.Embed(
            title="⚠️ Staff Warning Applied",
            color=Colors.GOLD,
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
            value=f"{staff.mention}\n{staff.name} ({staff.display_name})",
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
            embed.add_field(
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
            color=Colors.MOD,
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
                icon = "⚠️" if s.get('sanction_type') == 'warn' else "⛔"
                reason = s.get('reason', 'No reason')[: 40]
                recent.append(f"{icon} {reason}{'...' if len(s.get('reason', '')) > 40 else ''}")
            
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
