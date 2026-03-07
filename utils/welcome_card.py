from __future__ import annotations

import io
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

import aiohttp
import discord
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import Config


@dataclass(frozen=True)
class _BadgeItem:
    label: Optional[str] = None
    icon: Optional[Image.Image] = None
    fill: tuple[int, int, int] = (88, 101, 242)
    outline: tuple[int, int, int] = (205, 214, 255)
    text_fill: tuple[int, int, int] = (255, 255, 255)


_LOCAL_FONT_DIR = Path(__file__).resolve().parent / "fonts"


def _font_candidates(*, bold: bool) -> list[str]:
    local_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return [
        str(_LOCAL_FONT_DIR / local_name),
        local_name,
        "arialbd.ttf" if bold else "arial.ttf",
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]


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


def _parse_username_parts(username: str, discriminator: object) -> str:
    discriminator = str(discriminator or "0")
    if discriminator and discriminator != "0":
        return f"{username}#{discriminator}"
    return username


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
    for name in _font_candidates(bold=bold):
        try:
            if os.path.isabs(name) and not os.path.exists(name):
                continue
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
    ("staff", "staff"),
    ("partner", "partner"),
    ("hypesquad", "hypesquad"),
    ("hypesquad_bravery", "hypesquad_bravery"),
    ("hypesquad_brilliance", "hypesquad_brilliance"),
    ("hypesquad_balance", "hypesquad_balance"),
    ("bug_hunter_level_1", "bug_hunter_level_1"),
    ("bug_hunter", "bug_hunter_level_1"),
    ("bug_hunter_level_2", "bug_hunter_level_2"),
    ("early_supporter", "early_supporter"),
    ("team_user", "team_user"),
    ("system", "system"),
    ("verified_bot", "verified_bot"),
    ("early_verified_bot_developer", "verified_bot_developer"),
    ("verified_bot_developer", "verified_bot_developer"),
    ("discord_certified_moderator", "discord_certified_moderator"),
    ("bot_http_interactions", "bot_http_interactions"),
    ("active_developer", "active_developer"),
]


_BADGE_STYLES: dict[str, tuple[str, tuple[int, int, int], tuple[int, int, int]]] = {
    "nitro": ("NITRO", (88, 101, 242), (205, 214, 255)),
    "boost": ("BOOST", (237, 96, 171), (255, 214, 234)),
    "staff": ("STAFF", (88, 101, 242), (205, 214, 255)),
    "partner": ("PARTNER", (35, 165, 90), (205, 242, 217)),
    "hypesquad": ("HQ", (244, 184, 64), (255, 232, 179)),
    "hypesquad_bravery": ("BRAVE", (226, 74, 99), (255, 210, 217)),
    "hypesquad_brilliance": ("BRILL", (249, 168, 37), (255, 227, 179)),
    "hypesquad_balance": ("BAL", (69, 181, 154), (194, 243, 231)),
    "bug_hunter_level_1": ("BUG I", (74, 164, 109), (203, 242, 212)),
    "bug_hunter_level_2": ("BUG II", (41, 121, 255), (201, 223, 255)),
    "early_supporter": ("EARLY", (233, 131, 92), (255, 222, 208)),
    "team_user": ("TEAM", (104, 109, 224), (215, 218, 255)),
    "system": ("SYSTEM", (88, 101, 242), (205, 214, 255)),
    "verified_bot": ("BOT", (88, 176, 86), (212, 245, 209)),
    "verified_bot_developer": ("DEV", (88, 101, 242), (205, 214, 255)),
    "discord_certified_moderator": ("MOD", (49, 152, 216), (203, 237, 255)),
    "bot_http_interactions": ("APP", (88, 176, 86), (212, 245, 209)),
    "active_developer": ("ACTIVE", (46, 204, 113), (208, 247, 221)),
    "guild_tag": ("GUILD", (64, 78, 237), (214, 219, 255)),
    "role_tag": ("ROLE", (94, 99, 115), (211, 215, 223)),
}


def _badge_style(key: str) -> tuple[str, tuple[int, int, int], tuple[int, int, int]]:
    return _BADGE_STYLES.get(key, ("BADGE", (88, 101, 242), (205, 214, 255)))


def _make_badge_item(
    key: str,
    *,
    label: Optional[str] = None,
    icon: Optional[Image.Image] = None,
) -> _BadgeItem:
    default_label, fill, outline = _badge_style(key)
    return _BadgeItem(
        label=label if label is not None else default_label,
        icon=icon,
        fill=fill,
        outline=outline,
    )


def _asset_is_animated(asset: object) -> bool:
    try:
        animated = getattr(asset, "is_animated", None)
        if callable(animated):
            return bool(animated())
        if animated is not None:
            return bool(animated)
    except Exception:
        pass
    return False


def _public_user_flags_from_payload(
    profile_payload: Optional[Mapping[str, Any]],
) -> Optional[discord.PublicUserFlags]:
    if not profile_payload:
        return None

    raw_value = profile_payload.get("public_flags")
    if raw_value is None:
        raw_value = profile_payload.get("flags")

    try:
        if raw_value is None:
            return None
        return discord.PublicUserFlags._from_value(int(raw_value))
    except Exception:
        return None


def _user_payload_banner_url(
    user_id: int,
    profile_payload: Optional[Mapping[str, Any]],
) -> Optional[str]:
    if not profile_payload:
        return None
    banner_hash = str(profile_payload.get("banner") or "").strip()
    if not banner_hash:
        return None
    ext = "gif" if banner_hash.startswith("a_") else "png"
    return f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{ext}?size=1024"


def _user_payload_avatar_decoration_url(
    profile_payload: Optional[Mapping[str, Any]],
) -> Optional[str]:
    if not profile_payload:
        return None
    decoration_data = profile_payload.get("avatar_decoration_data")
    if not isinstance(decoration_data, Mapping):
        return None
    asset = str(decoration_data.get("asset") or "").strip()
    if not asset:
        return None
    return f"https://cdn.discordapp.com/avatar-decoration-presets/{asset}.png?size=256"


def _user_payload_primary_guild_data(
    profile_payload: Optional[Mapping[str, Any]],
) -> Optional[Mapping[str, Any]]:
    if not profile_payload:
        return None
    primary_guild = profile_payload.get("primary_guild")
    if not isinstance(primary_guild, Mapping):
        return None
    if primary_guild.get("identity_enabled") is False:
        return None
    return primary_guild


def _user_payload_primary_guild_tag(
    profile_payload: Optional[Mapping[str, Any]],
) -> Optional[str]:
    primary_guild = _user_payload_primary_guild_data(profile_payload)
    if not primary_guild:
        return None
    tag = str(primary_guild.get("tag") or "").strip()
    return tag or None


def _user_payload_primary_guild_badge_url(
    profile_payload: Optional[Mapping[str, Any]],
) -> Optional[str]:
    primary_guild = _user_payload_primary_guild_data(profile_payload)
    if not primary_guild:
        return None

    badge_hash = str(primary_guild.get("badge") or "").strip()
    if not badge_hash:
        return None

    try:
        guild_id = int(primary_guild.get("identity_guild_id") or 0)
    except Exception:
        guild_id = 0

    if guild_id <= 0:
        return None

    return f"https://cdn.discordapp.com/guild-tag-badges/{guild_id}/{badge_hash}.png?size=64"


async def _fetch_user_profile_payload(
    bot: discord.Client,
    user_id: int,
) -> Optional[Mapping[str, Any]]:
    http = getattr(bot, "http", None)
    if http is None:
        return None

    try:
        payload = await http.get_user(user_id)
    except Exception:
        return None

    if isinstance(payload, Mapping):
        return payload
    return None


def _infer_profile_badges(
    user: discord.User | discord.Member,
    *,
    member: Optional[discord.Member] = None,
    profile_payload: Optional[Mapping[str, Any]] = None,
) -> list[str]:
    inferred: list[str] = []

    premium_type = 0
    if profile_payload is not None:
        try:
            premium_type = int(profile_payload.get("premium_type") or 0)
        except Exception:
            premium_type = 0

    if premium_type > 0:
        inferred.append("nitro")

    avatar_asset = getattr(user, "display_avatar", None) or getattr(user, "avatar", None)
    banner_asset = getattr(user, "banner", None)
    decoration_asset = getattr(user, "avatar_decoration", None)

    if (
        not inferred
        and (
            decoration_asset is not None
            or banner_asset is not None
            or _asset_is_animated(avatar_asset)
            or _user_payload_avatar_decoration_url(profile_payload) is not None
            or _user_payload_banner_url(getattr(user, "id", 0), profile_payload) is not None
        )
    ):
        inferred.append("nitro")

    if member is not None and getattr(member, "premium_since", None) is not None:
        inferred.append("boost")

    seen: set[str] = set()
    unique: list[str] = []
    for key in inferred:
        if key in seen:
            continue
        seen.add(key)
        unique.append(key)
    return unique


def _badge_keys(
    user: discord.User | discord.Member,
    *,
    member: Optional[discord.Member] = None,
    profile_payload: Optional[Mapping[str, Any]] = None,
) -> list[str]:
    keys: list[str] = []

    keys.extend(_infer_profile_badges(user, member=member, profile_payload=profile_payload))

    flags = _public_user_flags_from_payload(profile_payload)
    if flags is None:
        flags = getattr(user, "public_flags", None) or getattr(user, "flags", None)
    if flags:
        for attr, key in _BADGE_MAP:
            try:
                if getattr(flags, attr, False):
                    keys.append(key)
            except Exception:
                continue

    seen: set[str] = set()
    unique: list[str] = []
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        unique.append(key)
    return unique[:8]


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
        profile_payload = await _fetch_user_profile_payload(bot, member.id)

        avatar_asset = member.display_avatar
        try:
            avatar_url = avatar_asset.replace(size=512, static_format="png").url
        except Exception:
            avatar_url = str(avatar_asset.url)

        banner_url: Optional[str] = options.brand_banner_url
        if not banner_url:
            banner_url = _user_payload_banner_url(member.id, profile_payload)

        decoration_url = _user_payload_avatar_decoration_url(profile_payload)
        if decoration_url is None:
            decoration_asset = getattr(member, "avatar_decoration", None)
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
        for key in _badge_keys(member, member=member, profile_payload=profile_payload):
            badge_items.append(_make_badge_item(key))

        primary_guild_badge_url = _user_payload_primary_guild_badge_url(profile_payload)
        if primary_guild_badge_url:
            primary_guild_badge = await _fetch_asset_image(session, primary_guild_badge_url)
            if primary_guild_badge is not None:
                badge_items.append(_make_badge_item("guild_tag", icon=primary_guild_badge))

        primary_guild_tag = _user_payload_primary_guild_tag(profile_payload)
        if primary_guild_tag:
            badge_items.append(_make_badge_item("guild_tag", label=primary_guild_tag))

        if options.role_badge_fallback and not badge_items:
            for url in _role_badge_urls(member, limit=6):
                img = await _fetch_asset_image(session, url)
                if img is not None:
                    badge_items.append(_make_badge_item("role_tag", icon=img))
                if len(badge_items) >= 6:
                    break
            tag = _role_tag_text(member)
            if tag:
                badge_items.append(_make_badge_item("role_tag", label=tag))

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
    username = _parse_username_parts(
        str((profile_payload or {}).get("username") or member.name),
        (profile_payload or {}).get("discriminator") or getattr(member, "discriminator", "0"),
    )

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
    icon_gap = 10

    pill_logo = None
    logo_w = 0
    logo_h = 0
    if brand_logo_img is not None:
        pill_logo = brand_logo_img.copy()
        icon_size = text_h + 6
        pill_logo.thumbnail((icon_size, icon_size), Image.Resampling.LANCZOS)
        logo_w, logo_h = pill_logo.size

    pill_w = text_w + pill_padding_x * 2 + (logo_w + icon_gap if pill_logo else 0)
    content_h = max(text_h, logo_h) if pill_logo else text_h
    pill_h = content_h + pill_padding_y * 2
    pill_x = w - options.margin - pill_w
    pill_y = h - options.margin - pill_h
    draw.rounded_rectangle(
        (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
        radius=18,
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
    row_y = options.margin
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

        if right - item_w < text_x + 30:
            next_row_y = row_y + badge_size + 8
            if next_row_y + badge_size > name_y - 8:
                break
            row_y = next_row_y
            right = w - options.margin

        bx = right - item_w
        draw.rounded_rectangle(
            (bx, row_y, bx + item_w, row_y + badge_size),
            radius=10,
            fill=(*item.fill, 225),
            outline=(*item.outline, 235),
            width=2,
        )
        if item.icon is not None:
            icon = _cover_resize(item.icon.convert("RGBA"), (badge_size - 8, badge_size - 8))
            circ = _circle_mask(badge_size - 8)
            icon_layer = Image.new("RGBA", (badge_size - 8, badge_size - 8), (0, 0, 0, 0))
            icon_layer.paste(icon, (0, 0), mask=circ)
            card.alpha_composite(icon_layer, (bx + 4, row_y + 4))
        elif item.label and is_tag and tag_font is not None:
            bb = draw.textbbox((0, 0), item.label, font=tag_font)
            tw = bb[2] - bb[0]
            th = bb[3] - bb[1]
            tx = bx + (item_w - tw) // 2 - bb[0]
            ty = row_y + (badge_size - th) // 2 - bb[1]
            draw.text((tx, ty), item.label, font=tag_font, fill=(*item.text_fill, 245))
        elif item.label:
            badge_font = _load_font(22, bold=True)
            bb = draw.textbbox((0, 0), item.label, font=badge_font)
            tw = bb[2] - bb[0]
            th = bb[3] - bb[1]
            tx = bx + (badge_size - tw) // 2 - bb[0]
            ty = row_y + (badge_size - th) // 2 - bb[1]
            draw.text((tx, ty), item.label, font=badge_font, fill=(*item.text_fill, 245))
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

