from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Optional

import aiohttp
import discord
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _asset_url(asset: object, *, size: int = 64, static_format: str = "png") -> Optional[str]:
    if asset is None:
        return None
    try:
        return asset.replace(size=size, static_format=static_format).url  # type: ignore[union-attr]
    except Exception:
        try:
            return str(asset.url)  # type: ignore[union-attr]
        except Exception:
            return None


def _parse_username(user: discord.abc.User) -> str:
    discriminator = getattr(user, "discriminator", "0")
    if discriminator and discriminator != "0":
        return f"{user.name}#{discriminator}"
    return user.name


def _int_to_rgb(color: int) -> tuple[int, int, int]:
    return ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)


def _cover_resize(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = img.size
    if src_w <= 0 or src_h <= 0:
        return Image.new("RGBA", size, (0, 0, 0, 255))
    scale = max(target_w / src_w, target_h / src_h)
    resized = img.resize(
        (max(1, int(src_w * scale)), max(1, int(src_h * scale))),
        Image.Resampling.LANCZOS,
    )
    left = (resized.size[0] - target_w) // 2
    top = (resized.size[1] - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def _circle_mask(size: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    return mask


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
        ("arialbd.ttf" if bold else "arial.ttf"),
        ("segoeuib.ttf" if bold else "segoeui.ttf"),
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _text_fit(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    if not text:
        return text

    def width(s: str) -> int:
        bbox = draw.textbbox((0, 0), s, font=font)
        return bbox[2] - bbox[0]

    if width(text) <= max_width:
        return text

    ellipsis = "..."
    lo, hi = 0, len(text)
    best = ellipsis
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = text[:mid].rstrip() + ellipsis
        if width(candidate) <= max_width:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return best


# ---------------------------------------------------------------------------
# Badge helpers
# ---------------------------------------------------------------------------

_BADGE_MAP: list[tuple[str, str]] = [
    ("staff", "STAFF"),
    ("partner", "PART"),
    ("hypesquad", "HYPE"),
    ("hypesquad_bravery", "BRV"),
    ("hypesquad_brilliance", "BRL"),
    ("hypesquad_balance", "BAL"),
    ("bug_hunter_level_1", "BH1"),
    ("bug_hunter", "BH1"),
    ("bug_hunter_level_2", "BH2"),
    ("early_supporter", "EARLY"),
    ("early_verified_bot_developer", "DEV"),
    ("verified_bot_developer", "DEV"),
    ("discord_certified_moderator", "MOD"),
    ("active_developer", "ACTIVE"),
    ("nitro", "NITRO"),
    ("premium", "NITRO"),
]


def _has_nitro(user: discord.User | discord.Member) -> bool:
    """Return True if the user appears to have Nitro (via public flags or premium type)."""
    flags = getattr(user, "public_flags", None) or getattr(user, "flags", None)
    if flags:
        for attr in ("premium", "nitro"):
            try:
                if getattr(flags, attr, False):
                    return True
            except Exception:
                pass
    # premium_type: 1 = Nitro Classic, 2 = Nitro, 3 = Nitro Basic
    premium_type = getattr(user, "premium_type", None)
    if premium_type and getattr(premium_type, "value", premium_type) not in (0, None):
        return True
    return False


def _badge_labels(
    user: discord.User | discord.Member,
    *,
    member: Optional[discord.Member] = None,
) -> list[str]:
    labels: list[str] = []
    flags = getattr(user, "public_flags", None) or getattr(user, "flags", None)
    if flags:
        for attr, label in _BADGE_MAP:
            try:
                if getattr(flags, attr, False):
                    labels.append(label)
            except Exception:
                continue

    seen: set[str] = set()
    unique: list[str] = []
    for label in labels:
        if label in seen:
            continue
        seen.add(label)
        unique.append(label)
    return unique[:6]


def _role_badge_urls(member: discord.Member, *, limit: int = 6) -> list[str]:
    roles = sorted(
        getattr(member, "roles", []) or [],
        key=lambda r: getattr(r, "position", 0),
        reverse=True,
    )
    guild_id = getattr(getattr(member, "guild", None), "id", None)
    urls: list[str] = []
    for role in roles:
        if guild_id is not None and getattr(role, "id", None) == guild_id:
            continue
        display_icon = getattr(role, "display_icon", None)
        if display_icon is None:
            continue
        url = _asset_url(display_icon, size=64, static_format="png") or ""
        if url:
            urls.append(url)
        if len(urls) >= limit:
            break
    return urls


def _primary_guild_badge_url(user: discord.User | discord.Member) -> Optional[str]:
    try:
        primary_guild = getattr(user, "primary_guild", None)
    except Exception:
        primary_guild = None
    if primary_guild is None:
        return None
    try:
        badge = primary_guild.badge
    except Exception:
        badge = None
    return _asset_url(badge, size=64, static_format="png")


def _top_role_color(member: discord.Member) -> Optional[tuple[int, int, int]]:
    """Return the RGB of the member's highest coloured role, or None."""
    roles = sorted(
        getattr(member, "roles", []) or [],
        key=lambda r: getattr(r, "position", 0),
        reverse=True,
    )
    guild_id = getattr(getattr(member, "guild", None), "id", None)
    for role in roles:
        if guild_id is not None and getattr(role, "id", None) == guild_id:
            continue
        color_val = getattr(getattr(role, "color", None), "value", 0)
        if color_val:
            return _int_to_rgb(color_val)
    return None


async def _fetch_asset_image(session: aiohttp.ClientSession, url: str) -> Optional[Image.Image]:
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        return img
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------

# Per-guild welcome labels: map guild_id (int) → welcome text shown in the pill.
# Add entries here as needed; falls back to DEFAULT_WELCOME_LABEL.
GUILD_WELCOME_LABELS: dict[int, str] = {
    # 123456789012345678: "Welcome to MyCoolServer!",
}

DEFAULT_WELCOME_LABEL: str = "WELCOME!"


@dataclass(frozen=True)
class WelcomeCardOptions:
    width: int = 940
    height: int = 360
    radius: int = 26
    avatar_size: int = 220
    margin: int = 24
    # Accent colour used for the card border & badge outlines.
    # Overridden at runtime by the member's top-role colour when available.
    accent_color: int = getattr(Config, "EMBED_ACCENT_COLOR", Config.COLOR_EMBED)
    # When True, the member's top-role colour replaces accent_color.
    use_role_color: bool = True
    # Fallback server name shown in the header chip (top-left).
    server_name: str = ""
    # Pill text override.  Leave empty to use GUILD_WELCOME_LABELS / DEFAULT.
    welcome_label: str = ""
    role_badge_fallback: bool = True


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

async def build_welcome_card_png(
    bot: discord.Client,
    member: discord.Member,
    *,
    options: WelcomeCardOptions = WelcomeCardOptions(),
) -> bytes:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Fetch full user so we can access banner / decoration
        try:
            full_user = await bot.fetch_user(member.id)
        except Exception:
            full_user = member  # type: ignore[assignment]

        # --- Avatar ---
        avatar_asset = member.display_avatar
        try:
            avatar_url = avatar_asset.replace(size=512, static_format="png").url
        except Exception:
            avatar_url = str(avatar_asset.url)

        # --- Background: user banner if Nitro, else pfp ---
        banner_url: Optional[str] = None
        user_has_nitro = _has_nitro(full_user)  # type: ignore[arg-type]
        if user_has_nitro:
            banner_asset = getattr(full_user, "banner", None)
            if banner_asset:
                try:
                    banner_url = banner_asset.replace(size=1024).url
                except Exception:
                    banner_url = str(getattr(banner_asset, "url", "") or "")

        # --- Avatar decoration ---
        decoration_asset = getattr(full_user, "avatar_decoration", None)
        decoration_url: Optional[str] = None
        if decoration_asset:
            try:
                decoration_url = decoration_asset.replace(size=256).url
            except Exception:
                decoration_url = str(getattr(decoration_asset, "url", "") or "")

        # Fetch images concurrently (well, sequentially – aiohttp is already async)
        avatar_img = await _fetch_asset_image(session, avatar_url)
        bg_img = await _fetch_asset_image(session, banner_url) if banner_url else None
        # If no banner, use avatar as background
        if bg_img is None and avatar_img is not None:
            bg_img = avatar_img.copy()
        decoration_img = await _fetch_asset_image(session, decoration_url) if decoration_url else None

        # --- Badges ---
        @dataclass
        class _BadgeItem:
            label: Optional[str] = None
            icon: Optional[Image.Image] = None

        badge_items: list[_BadgeItem] = []
        seen_badge_labels: set[str] = set()

        # Primary guild badge (clan icon)
        primary_badge_url = _primary_guild_badge_url(full_user)  # type: ignore[arg-type]
        if primary_badge_url:
            primary_badge_img = await _fetch_asset_image(session, primary_badge_url)
            if primary_badge_img is not None:
                badge_items.append(_BadgeItem(icon=primary_badge_img))

        # Public flag badges (text labels)
        for label in _badge_labels(full_user, member=member):  # type: ignore[arg-type]
            normalized = label.strip().upper()
            if not normalized or normalized in seen_badge_labels:
                continue
            seen_badge_labels.add(normalized)
            badge_items.append(_BadgeItem(label=label))

        # Role icon badges (fallback)
        if options.role_badge_fallback:
            remaining_slots = max(0, 6 - len(badge_items))
            for url in _role_badge_urls(member, limit=remaining_slots):
                img = await _fetch_asset_image(session, url)
                if img is not None:
                    badge_items.append(_BadgeItem(icon=img))
                if len(badge_items) >= 6:
                    break

    # ---------------------------------------------------------------------------
    # Resolve accent colour
    # ---------------------------------------------------------------------------
    accent_rgb: tuple[int, int, int]
    if options.use_role_color:
        role_color = _top_role_color(member)
        accent_rgb = role_color if role_color else _int_to_rgb(options.accent_color)
    else:
        accent_rgb = _int_to_rgb(options.accent_color)

    # ---------------------------------------------------------------------------
    # Resolve per-guild text
    # ---------------------------------------------------------------------------
    guild = getattr(member, "guild", None)
    guild_id = getattr(guild, "id", None)
    guild_name: str = getattr(guild, "name", None) or options.server_name or ""

    if options.welcome_label:
        pill_text = options.welcome_label
    elif guild_id and guild_id in GUILD_WELCOME_LABELS:
        pill_text = GUILD_WELCOME_LABELS[guild_id]
    else:
        pill_text = DEFAULT_WELCOME_LABEL

    # ---------------------------------------------------------------------------
    # Canvas setup
    # ---------------------------------------------------------------------------
    w, h = options.width, options.height

    if bg_img is None:
        bg_img = Image.new("RGBA", (w, h), (18, 18, 18, 255))

    bg = _cover_resize(bg_img, (w, h)).convert("RGBA")
    bg = bg.filter(ImageFilter.GaussianBlur(radius=10))

    # Dark overlay for legibility
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 170))
    bg = Image.alpha_composite(bg, overlay)

    # Rounded card mask
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mask = _rounded_mask((w, h), options.radius)
    card.paste(bg, (0, 0), mask=mask)

    # Glowing accent border (blurred outer glow)
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.rounded_rectangle(
        (4, 4, w - 4, h - 4),
        radius=options.radius,
        outline=(*accent_rgb, 200),
        width=14,
    )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=5))
    card.alpha_composite(glow_layer)

    # Sharp inner border
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle(
        (5, 5, w - 5, h - 5),
        radius=max(0, options.radius - 1),
        outline=(*accent_rgb, 160),
        width=3,
    )

    # ---------------------------------------------------------------------------
    # Avatar
    # ---------------------------------------------------------------------------
    avatar_size = options.avatar_size
    avatar_outer = avatar_size + 28
    avatar_x = options.margin
    avatar_y = (h - avatar_outer) // 2 + 4

    # Subtle white backing circle (sits behind avatar, visible if decoration has gaps)
    ring_inner = Image.new("RGBA", (avatar_outer, avatar_outer), (0, 0, 0, 0))
    ring_inner_draw = ImageDraw.Draw(ring_inner)
    ring_inner_draw.ellipse(
        (0, 0, avatar_outer, avatar_outer),
        fill=(255, 255, 255, 30),
    )
    card.alpha_composite(ring_inner, (avatar_x, avatar_y))

    if avatar_img is not None:
        avatar = avatar_img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        circ = _circle_mask(avatar_size)
        avatar_layer = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
        avatar_layer.paste(avatar, (0, 0), mask=circ)
        inner_x = avatar_x + (avatar_outer - avatar_size) // 2
        inner_y = avatar_y + (avatar_outer - avatar_size) // 2
        card.alpha_composite(avatar_layer, (inner_x, inner_y))

        if decoration_img is not None:
            deco_size = avatar_outer + 12
            deco = _cover_resize(decoration_img, (deco_size, deco_size))
            deco_x = avatar_x + (avatar_outer - deco_size) // 2
            deco_y = avatar_y + (avatar_outer - deco_size) // 2
            card.alpha_composite(deco, (deco_x, deco_y))

    # ---------------------------------------------------------------------------
    # Text
    # ---------------------------------------------------------------------------
    name_font = _load_font(72, bold=True)
    user_font = _load_font(36, bold=False)
    small_font = _load_font(22, bold=True)
    header_font = _load_font(20, bold=True)

    display_name = getattr(member, "display_name", member.name) or member.name
    username = _parse_username(full_user)  # type: ignore[arg-type]

    text_x = avatar_x + avatar_outer + 28
    max_text_w = w - text_x - options.margin - 14

    draw2 = ImageDraw.Draw(card)

    display_name = _text_fit(draw2, display_name, name_font, max_text_w)
    username = _text_fit(draw2, username, user_font, max_text_w)

    name_y = 118
    user_y = name_y + 82

    # Drop shadow + main text for display name
    draw2.text((text_x + 2, name_y + 3), display_name, font=name_font, fill=(0, 0, 0, 200))
    draw2.text((text_x, name_y), display_name, font=name_font, fill=(255, 255, 255, 245))

    # Username (slightly muted)
    draw2.text((text_x + 1, user_y + 2), username, font=user_font, fill=(0, 0, 0, 160))
    draw2.text((text_x, user_y), username, font=user_font, fill=(210, 210, 210, 220))

    # ---------------------------------------------------------------------------
    # WELCOME pill (bottom-right)
    # ---------------------------------------------------------------------------
    bbox = draw2.textbbox((0, 0), pill_text, font=small_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pill_px = 20
    pill_py = 11

    pill_w = text_w + pill_px * 2
    pill_h = text_h + pill_py * 2
    pill_x = w - options.margin - pill_w
    pill_y = h - options.margin - pill_h

    draw2.rounded_rectangle(
        (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
        radius=14,
        fill=(10, 10, 10, 140),
        outline=(*accent_rgb, 200),
        width=2,
    )
    pill_text_x = pill_x + pill_px - bbox[0]
    pill_text_y = pill_y + pill_py - bbox[1]
    draw2.text((pill_text_x, pill_text_y), pill_text, font=small_font, fill=(255, 255, 255, 240))

    # ---------------------------------------------------------------------------
    # Server name header chip (top-left) — only if server_name is set
    # ---------------------------------------------------------------------------
    if guild_name:
        header_text = _text_fit(draw2, guild_name, header_font, w // 2)
        header_bbox = draw2.textbbox((0, 0), header_text, font=header_font)
        header_w = header_bbox[2] - header_bbox[0]
        header_h = header_bbox[3] - header_bbox[1]
        hx = options.margin + 4
        hy = 14
        draw2.rounded_rectangle(
            (hx - 10, hy - 7, hx + header_w + 10, hy + header_h + 7),
            radius=12,
            fill=(0, 0, 0, 100),
            outline=(255, 255, 255, 40),
            width=2,
        )
        draw2.text(
            (hx - header_bbox[0], hy - header_bbox[1]),
            header_text,
            font=header_font,
            fill=(255, 255, 255, 220),
        )

    # ---------------------------------------------------------------------------
    # Badges (top-right, flowing left)
    # ---------------------------------------------------------------------------
    badge_size = 32
    gap = 8
    by = 14
    right = w - options.margin + 2
    badge_font = _load_font(14, bold=True)

    for item in badge_items:
        item_w = badge_size
        if item.label:
            bb = draw2.textbbox((0, 0), item.label, font=badge_font)
            tw = bb[2] - bb[0]
            item_w = max(badge_size, tw + 16)

        bx = right - item_w

        # Badge background with accent outline
        draw2.rounded_rectangle(
            (bx, by, bx + item_w, by + badge_size),
            radius=10,
            fill=(8, 8, 8, 190),
            outline=(*accent_rgb, 220),
            width=2,
        )

        if item.icon is not None:
            icon_pad = 6
            icon_sz = badge_size - icon_pad * 2
            icon = _cover_resize(item.icon.convert("RGBA"), (icon_sz, icon_sz))
            icon_mask = _circle_mask(icon_sz)
            icon_layer = Image.new("RGBA", (icon_sz, icon_sz), (0, 0, 0, 0))
            icon_layer.paste(icon, (0, 0), mask=icon_mask)
            card.alpha_composite(icon_layer, (bx + icon_pad, by + icon_pad))
        elif item.label:
            bb = draw2.textbbox((0, 0), item.label, font=badge_font)
            tw = bb[2] - bb[0]
            th = bb[3] - bb[1]
            tx = bx + (item_w - tw) // 2 - bb[0]
            ty = by + (badge_size - th) // 2 - bb[1]
            draw2.text((tx, ty), item.label, font=badge_font, fill=(255, 255, 255, 245))

        right = bx - gap

    # ---------------------------------------------------------------------------
    # Export
    # ---------------------------------------------------------------------------
    out = io.BytesIO()
    card.save(out, format="PNG", optimize=True)
    return out.getvalue()


async def build_welcome_card_file(
    bot: discord.Client,
    member: discord.Member,
    *,
    filename: str = "welcome.png",
    options: WelcomeCardOptions = WelcomeCardOptions(),
) -> discord.File:
    png = await build_welcome_card_png(bot, member, options=options)
    return discord.File(io.BytesIO(png), filename=filename)