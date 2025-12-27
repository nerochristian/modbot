from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import aiohttp
import discord
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import Config


@dataclass(frozen=True)
class _BadgeItem:
    label: Optional[str] = None
    icon: Optional[Image.Image] = None


def _role_tag_text(member: discord.Member) -> Optional[str]:
    role = getattr(member, "top_role", None)
    if role is None:
        return None
    guild_id = getattr(getattr(member, "guild", None), "id", None)
    if guild_id is not None and getattr(role, "id", None) == guild_id:
        return None  # @everyone

    name = (getattr(role, "name", "") or "").strip()
    if not (2 <= len(name) <= 6):
        return None
    if not name.isascii():
        return None
    if not all(ch.isalnum() or ch in {"_", "-"} for ch in name):
        return None
    return name.upper()


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


_BADGE_MAP: list[tuple[str, str]] = [
    ("staff", "S"),
    ("partner", "P"),
    ("hypesquad", "H"),
    ("hypesquad_bravery", "B"),
    ("hypesquad_brilliance", "R"),
    ("hypesquad_balance", "L"),
    ("bug_hunter_level_1", "1"),
    ("bug_hunter", "1"),
    ("bug_hunter_level_2", "2"),
    ("early_supporter", "E"),
    ("early_verified_bot_developer", "D"),
    ("verified_bot_developer", "D"),
    ("discord_certified_moderator", "M"),
    ("active_developer", "A"),
]


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
    roles = sorted(getattr(member, "roles", []) or [], key=lambda r: getattr(r, "position", 0), reverse=True)
    guild_id = getattr(getattr(member, "guild", None), "id", None)
    urls: list[str] = []
    for role in roles:
        if guild_id is not None and getattr(role, "id", None) == guild_id:
            continue  # @everyone

        display_icon = getattr(role, "display_icon", None)
        if display_icon is None:
            continue

        url: str = ""
        try:
            url = display_icon.replace(size=64, static_format="png").url  # type: ignore[union-attr]
        except Exception:
            try:
                url = str(display_icon.url)  # type: ignore[union-attr]
            except Exception:
                url = ""

        if url:
            urls.append(url)
        if len(urls) >= limit:
            break
    return urls


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


@dataclass(frozen=True)
class WelcomeCardOptions:
    width: int = 1000
    height: int = 300
    radius: int = 26
    avatar_size: int = 196
    margin: int = 28
    accent_color: int = getattr(Config, "EMBED_ACCENT_COLOR", Config.COLOR_EMBED)
    server_name: str = "The Supreme People"
    welcome_label: str = "WELCOME!"
    role_badge_fallback: bool = True


async def build_welcome_card_png(
    bot: discord.Client,
    member: discord.Member,
    *,
    options: WelcomeCardOptions = WelcomeCardOptions(),
) -> bytes:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # fetch full user to access banner/decoration when available
        try:
            full_user = await bot.fetch_user(member.id)
        except Exception:
            full_user = member  # type: ignore[assignment]

        avatar_asset = member.display_avatar
        try:
            avatar_url = avatar_asset.replace(size=512, static_format="png").url
        except Exception:
            avatar_url = str(avatar_asset.url)

        banner_asset = getattr(full_user, "banner", None)
        banner_url: Optional[str] = None
        if banner_asset:
            try:
                banner_url = banner_asset.replace(size=1024).url
            except Exception:
                banner_url = str(banner_asset.url)

        decoration_asset = getattr(full_user, "avatar_decoration", None)
        decoration_url: Optional[str] = None
        if decoration_asset:
            try:
                decoration_url = decoration_asset.replace(size=256).url
            except Exception:
                decoration_url = str(getattr(decoration_asset, "url", "") or "")

        bg_img = await _fetch_asset_image(session, banner_url) if banner_url else None
        avatar_img = await _fetch_asset_image(session, avatar_url)
        decoration_img = await _fetch_asset_image(session, decoration_url) if decoration_url else None

        badge_items: list[_BadgeItem] = []
        for label in _badge_labels(full_user, member=member):  # type: ignore[arg-type]
            badge_items.append(_BadgeItem(label=label))

        if options.role_badge_fallback and not badge_items:
            for url in _role_badge_urls(member, limit=6):
                img = await _fetch_asset_image(session, url)
                if img is not None:
                    badge_items.append(_BadgeItem(icon=img))
                if len(badge_items) >= 6:
                    break
            tag = _role_tag_text(member)
            if tag:
                badge_items.append(_BadgeItem(label=tag))

    w, h = options.width, options.height
    accent_rgb = _int_to_rgb(options.accent_color)

    if bg_img is None:
        if avatar_img is not None:
            bg_img = avatar_img.copy()
        else:
            bg_img = Image.new("RGBA", (w, h), (18, 18, 18, 255))

    bg = _cover_resize(bg_img, (w, h)).convert("RGBA")
    bg = bg.filter(ImageFilter.GaussianBlur(radius=8))

    # dark overlay for legibility
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 140))
    bg = Image.alpha_composite(bg, overlay)

    # rounded card
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mask = _rounded_mask((w, h), options.radius)
    card.paste(bg, (0, 0), mask=mask)

    # soft accent border (blurred)
    border_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border_layer)
    border_draw.rounded_rectangle(
        (4, 4, w - 4, h - 4),
        radius=max(0, options.radius - 1),
        outline=(*accent_rgb, 220),
        width=16,
    )
    border_layer = border_layer.filter(ImageFilter.GaussianBlur(radius=5))
    card.alpha_composite(border_layer)

    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle(
        (6, 6, w - 6, h - 6),
        radius=max(0, options.radius - 2),
        outline=(255, 255, 255, 70),
        width=4,
    )

    # avatar
    avatar_size = options.avatar_size
    avatar_outer = avatar_size + 28
    avatar_x = options.margin
    avatar_y = (h - avatar_outer) // 2

    ring_inner = Image.new("RGBA", (avatar_outer, avatar_outer), (0, 0, 0, 0))
    ring_inner_draw = ImageDraw.Draw(ring_inner)
    ring_inner_draw.ellipse(
        (12, 12, avatar_outer - 12, avatar_outer - 12),
        outline=(255, 255, 255, 60),
        width=3,
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
            deco_size = avatar_outer + 8
            deco = _cover_resize(decoration_img, (deco_size, deco_size))
            deco_x = avatar_x + (avatar_outer - deco_size) // 2
            deco_y = avatar_y + (avatar_outer - deco_size) // 2
            card.alpha_composite(deco, (deco_x, deco_y))

    # text
    name_font = _load_font(58, bold=True)
    user_font = _load_font(34, bold=False)
    small_font = _load_font(24, bold=True)

    display_name = getattr(member, "display_name", member.name) or member.name
    username = _parse_username(full_user)  # type: ignore[arg-type]

    text_x = avatar_x + avatar_outer + 26
    max_text_w = w - text_x - options.margin - 10

    display_name = _text_fit(draw, display_name, name_font, max_text_w)
    username = _text_fit(draw, username, user_font, max_text_w)

    name_y = int(h * 0.36)
    user_y = name_y + 62

    # subtle shadow
    draw.text((text_x + 2, name_y + 2), display_name, font=name_font, fill=(0, 0, 0, 180))
    draw.text((text_x, name_y), display_name, font=name_font, fill=(255, 255, 255, 240))

    draw.text((text_x + 2, user_y + 2), username, font=user_font, fill=(0, 0, 0, 160))
    draw.text((text_x, user_y), username, font=user_font, fill=(220, 220, 220, 230))

    # welcome pill (bottom-right)
    pill_text = options.welcome_label
    bbox = draw.textbbox((0, 0), pill_text, font=small_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pill_padding_x = 18
    pill_padding_y = 12
    pill_w = text_w + pill_padding_x * 2
    pill_h = text_h + pill_padding_y * 2
    pill_x = w - options.margin - pill_w
    pill_y = h - options.margin - pill_h
    draw.rounded_rectangle(
        (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
        radius=18,
        fill=(0, 0, 0, 130),
        outline=(*accent_rgb, 200),
        width=2,
    )
    pill_text_x = pill_x + (pill_w - text_w) // 2 - bbox[0]
    pill_text_y = pill_y + (pill_h - text_h) // 2 - bbox[1]
    draw.text(
        (pill_text_x, pill_text_y),
        pill_text,
        font=small_font,
        fill=(255, 255, 255, 240),
    )

    # server name (above avatar)
    server_font = _load_font(22, bold=True)
    server_text = _text_fit(draw, options.server_name, server_font, w - 2 * options.margin)
    server_bbox = draw.textbbox((0, 0), server_text, font=server_font)
    server_tw = server_bbox[2] - server_bbox[0]
    server_th = server_bbox[3] - server_bbox[1]

    stx = avatar_x + max(0, (avatar_outer - server_tw) // 2) - server_bbox[0]
    min_x = options.margin - server_bbox[0]
    max_x = w - options.margin - server_bbox[2]
    stx = max(min_x, min(stx, max_x))

    sty = max(8, avatar_y - server_th - 4) - server_bbox[1]

    draw.text((stx + 2, sty + 2), server_text, font=server_font, fill=(0, 0, 0, 170))
    draw.text((stx, sty), server_text, font=server_font, fill=(255, 255, 255, 220))

    # badges (top-right)
    badge_size = 34
    gap = 10
    by = options.margin
    right = w - options.margin
    for item in badge_items:
        item_w = badge_size
        is_tag = bool(item.label) and len(item.label or "") > 1
        tag_font = None
        if is_tag:
            tag_font = _load_font(18, bold=True)
            bb = draw.textbbox((0, 0), item.label or "", font=tag_font)
            tw = bb[2] - bb[0]
            item_w = tw + 18

        bx = right - item_w
        draw.rounded_rectangle(
            (bx, by, bx + item_w, by + badge_size),
            radius=10,
            fill=(*accent_rgb, 210),
        )
        if item.icon is not None:
            icon = _cover_resize(item.icon.convert("RGBA"), (badge_size - 8, badge_size - 8))
            circ = _circle_mask(badge_size - 8)
            icon_layer = Image.new("RGBA", (badge_size - 8, badge_size - 8), (0, 0, 0, 0))
            icon_layer.paste(icon, (0, 0), mask=circ)
            card.alpha_composite(icon_layer, (bx + 4, by + 4))
        elif item.label and is_tag and tag_font is not None:
            bb = draw.textbbox((0, 0), item.label, font=tag_font)
            tw = bb[2] - bb[0]
            th = bb[3] - bb[1]
            tx = bx + (item_w - tw) // 2 - bb[0]
            ty = by + (badge_size - th) // 2 - bb[1]
            draw.text((tx, ty), item.label, font=tag_font, fill=(255, 255, 255, 245))
        elif item.label:
            badge_font = _load_font(22, bold=True)
            bb = draw.textbbox((0, 0), item.label, font=badge_font)
            tw = bb[2] - bb[0]
            th = bb[3] - bb[1]
            tx = bx + (badge_size - tw) // 2 - bb[0]
            ty = by + (badge_size - th) // 2 - bb[1]
            draw.text((tx, ty), item.label, font=badge_font, fill=(255, 255, 255, 245))
        right = bx - gap

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
