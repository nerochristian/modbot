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
    width: int = 940
    height: int = 360
    radius: int = 26
    avatar_size: int = 220
    margin: int = 24
    accent_color: int = getattr(Config, "EMBED_ACCENT_COLOR", Config.COLOR_EMBED)
    server_name: str = "8kstore"
    welcome_label: str = "WELCOME!"
    role_badge_fallback: bool = True
    brand_banner_url: Optional[str] = (
        "https://media.discordapp.net/attachments/1461045644813668534/1461046165796552774/"
        "ChatGPT_Image_Jan_14_2026_11_38_25_AM.png?ex=696920c6&is=6967cf46&hm=c5411333a91339cf355a1f64d723e131b81e676aec7a1038ab07b0f038070c38&=&format=webp&quality=lossless&width=1249&height=499"
    )
    brand_logo_url: Optional[str] = (
        "https://media.discordapp.net/attachments/1461045644813668534/1461046354204954868/"
        "71ad111fcd062061bd30cde4b0230285.png?ex=696920f3&is=6967cf73&hm=23d85a81aad0f8541bef4818e9fd6bec179cd1caf99c47b0d61366664df48f99&=&format=webp&quality=lossless"
    )


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

        banner_url: Optional[str] = options.brand_banner_url
        if not banner_url:
            banner_asset = getattr(full_user, "banner", None)
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
        brand_logo_img = (
            await _fetch_asset_image(session, options.brand_logo_url) if options.brand_logo_url else None
        )

        badge_items: list[_BadgeItem] = []
        seen_badge_labels: set[str] = set()
        for label in _badge_labels(full_user, member=member):  # type: ignore[arg-type]
            normalized = label.strip().upper()
            if not normalized or normalized in seen_badge_labels:
                continue
            seen_badge_labels.add(normalized)
            badge_items.append(_BadgeItem(label=label))

        if options.role_badge_fallback:
            remaining_slots = max(0, 6 - len(badge_items))
            for url in _role_badge_urls(member, limit=remaining_slots):
                img = await _fetch_asset_image(session, url)
                if img is not None:
                    badge_items.append(_BadgeItem(icon=img))
                if len(badge_items) >= 6:
                    break
            tag = _role_tag_text(member)
            normalized_tag = (tag or "").strip().upper()
            if normalized_tag and normalized_tag not in seen_badge_labels and len(badge_items) < 6:
                seen_badge_labels.add(normalized_tag)
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
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 156))
    bg = Image.alpha_composite(bg, overlay)

    # rounded card
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mask = _rounded_mask((w, h), options.radius)
    card.paste(bg, (0, 0), mask=mask)

    # soft accent border (blurred)
    border_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border_layer)
    border_draw.rounded_rectangle(
        (5, 5, w - 5, h - 5),
        radius=max(0, options.radius - 1),
        outline=(*accent_rgb, 220),
        width=15,
    )
    border_layer = border_layer.filter(ImageFilter.GaussianBlur(radius=4))
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
    avatar_outer = avatar_size + 24
    avatar_x = options.margin
    avatar_y = (h - avatar_outer) // 2 + 6

    ring_inner = Image.new("RGBA", (avatar_outer, avatar_outer), (0, 0, 0, 0))
    ring_inner_draw = ImageDraw.Draw(ring_inner)
    ring_inner_draw.ellipse(
        (10, 10, avatar_outer - 10, avatar_outer - 10),
        outline=(255, 255, 255, 80),
        width=4,
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
    name_font = _load_font(74, bold=True)
    user_font = _load_font(38, bold=False)
    small_font = _load_font(22, bold=True)
    header_font = _load_font(20, bold=True)

    display_name = getattr(member, "display_name", member.name) or member.name
    username = _parse_username(full_user)  # type: ignore[arg-type]

    text_x = avatar_x + avatar_outer + 26
    max_text_w = w - text_x - options.margin - 12

    display_name = _text_fit(draw, display_name, name_font, max_text_w)
    username = _text_fit(draw, username, user_font, max_text_w)

    name_y = 128
    user_y = name_y + 78

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
    icon_gap = 10

    pill_logo = None
    logo_w = 0
    logo_h = 0
    if brand_logo_img is not None:
        pill_logo = brand_logo_img.copy()
        icon_size = text_h + 4
        pill_logo.thumbnail((icon_size, icon_size), Image.Resampling.LANCZOS)
        logo_w, logo_h = pill_logo.size

    pill_w = text_w + pill_padding_x * 2 + (logo_w + icon_gap if pill_logo else 0)
    content_h = max(text_h, logo_h) if pill_logo else text_h
    pill_h = content_h + pill_padding_y * 2
    pill_x = w - options.margin - pill_w
    pill_y = h - options.margin - pill_h
    draw.rounded_rectangle(
        (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
    radius=16,
        fill=(0, 0, 0, 130),
        outline=(*accent_rgb, 200),
        width=2,
    )
    pill_text_y = pill_y + (pill_h - text_h) // 2 - bbox[1]

    if pill_logo and logo_w > 0 and logo_h > 0:
        logo_x = pill_x + pill_padding_x
        logo_y = pill_y + (pill_h - logo_h) // 2
        card.alpha_composite(pill_logo, (logo_x, logo_y))
        pill_text_x = logo_x + logo_w + icon_gap - bbox[0]
    else:
        pill_text_x = pill_x + (pill_w - text_w) // 2 - bbox[0]

    draw.text(
        (pill_text_x, pill_text_y),
        pill_text,
        font=small_font,
        fill=(255, 255, 255, 240),
    )

    # header chip (top-left)
    header_text = _text_fit(draw, options.server_name, header_font, w - (options.margin * 2) - 220)
    header_bbox = draw.textbbox((0, 0), header_text, font=header_font)
    header_w = header_bbox[2] - header_bbox[0]
    header_h = header_bbox[3] - header_bbox[1]
    header_x = options.margin + 4
    header_y = 14
    draw.rounded_rectangle(
        (
            header_x - 10,
            header_y - 7,
            header_x + header_w + 10,
            header_y + header_h + 7,
        ),
        radius=14,
        fill=(0, 0, 0, 95),
        outline=(255, 255, 255, 40),
        width=2,
    )
    draw.text(
        (header_x - header_bbox[0], header_y - header_bbox[1]),
        header_text,
        font=header_font,
        fill=(255, 255, 255, 224),
    )

    # badges (top-right)
    badge_size = 30
    gap = 8
    by = 16
    right = w - options.margin + 2
    for item in badge_items:
        item_w = badge_size
        badge_font = _load_font(15, bold=True)
        if item.label:
            bb = draw.textbbox((0, 0), item.label, font=badge_font)
            tw = bb[2] - bb[0]
            item_w = max(badge_size, tw + 18)

        bx = right - item_w
        draw.rounded_rectangle(
            (bx, by, bx + item_w, by + badge_size),
            radius=10,
            fill=(12, 12, 12, 180),
            outline=(*accent_rgb, 210),
            width=2,
        )
        if item.icon is not None:
            icon = _cover_resize(item.icon.convert("RGBA"), (badge_size - 8, badge_size - 8))
            badge_mask = _rounded_mask((badge_size - 8, badge_size - 8), 7)
            icon_layer = Image.new("RGBA", (badge_size - 8, badge_size - 8), (0, 0, 0, 0))
            icon_layer.paste(icon, (0, 0), mask=badge_mask)
            card.alpha_composite(icon_layer, (bx + 4, by + 4))
        elif item.label:
            bb = draw.textbbox((0, 0), item.label, font=badge_font)
            tw = bb[2] - bb[0]
            th = bb[3] - bb[1]
            tx = bx + (item_w - tw) // 2 - bb[0]
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

