"""Welcome system generates a Koya-styled welcome card."""

from __future__ import annotations

import asyncio
import io
import logging
from pathlib import Path
from typing import Optional
import os

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter

LOGGER = logging.getLogger("enzo-bot.welcome")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

def _welcome_bg_path() -> Path:
    for filename in (
        "welcome_img.gif",
        "welcome_img.png",
        "welcome_img.jpg",
        "welcome_img.jpeg",
    ):
        path = BASE_DIR / "assets" / filename
        if path.exists():
            return path
    return BASE_DIR / "assets" / "welcome_img.png"


WELCOME_BG_PATH = _welcome_bg_path()

# ── Style constants ───────────────────────────────────────────────────────────
CARD_WIDTH = 800
CARD_HEIGHT = 400
AVATAR_SIZE = 180

def _generate_welcome_card(
    username: str,
    avatar_bytes: bytes,
    member_count: int,
    bg_path: Path,
    server_name: str,
) -> io.BytesIO:
    """Generate the Koya-style welcome card image."""
    W, H = CARD_WIDTH, CARD_HEIGHT
    
    # Load or create background
    if bg_path.exists():
        bg = Image.open(bg_path).convert("RGBA")
    else:
        bg = Image.new("RGBA", (W, H), (18, 18, 18, 255))
        
    # Resize and crop to fill
    bg_w, bg_h = bg.size
    ratio = max(W / bg_w, H / bg_h)
    new_w, new_h = int(bg_w * ratio), int(bg_h * ratio)
    bg = bg.resize((new_w, new_h), Image.LANCZOS)
    x = (new_w - W) // 2
    y = (new_h - H) // 2
    card = bg.crop((x, y, x + W, y + H)).convert("RGBA")
    
    # Very subtle overlay if background is too bright
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 40))
    card = Image.alpha_composite(card, overlay)

    draw = ImageDraw.Draw(card)

    # ── Avatar ─────────────────────────────────────────────────────────────
    AV = AVATAR_SIZE
    av_x = (W - AV) // 2
    av_y = (H - AV) // 2 - 40
    RING = 6

    # Draw solid white border
    draw.ellipse(
        (av_x - RING, av_y - RING, av_x + AV + RING, av_y + AV + RING),
        fill=(255, 255, 255, 255)
    )

    # Avatar image
    try:
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        avatar = avatar.resize((AV, AV), Image.LANCZOS)
        
        mask = Image.new("L", (AV, AV), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, AV - 1, AV - 1), fill=255)
        
        circular = Image.new("RGBA", (AV, AV), (0, 0, 0, 0))
        circular.paste(avatar, (0, 0), mask)
        
        card.alpha_composite(circular, (av_x, av_y))
    except Exception:
        pass

    # ── Fonts ──────────────────────────────────────────────────────────────
    font_welcome = None
    font_user = None
    for font_name in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "FreeSansBold.ttf"):
        try:
            font_welcome = ImageFont.truetype(font_name, 76)
            font_user = ImageFont.truetype(font_name, 34)
            break
        except Exception:
            continue
            
    if font_welcome is None:
        font_welcome = ImageFont.load_default()
        font_user = ImageFont.load_default()
        
    display_name = username.upper()

    # ── Text WELCOME ───────────────────────────────────────────────────────
    try:
        w_bb = draw.textbbox((0, 0), "WELCOME", font=font_welcome)
    except Exception:
        w_bb = (0, 0, 300, 50)
        
    w_w, w_h = w_bb[2] - w_bb[0], w_bb[3] - w_bb[1]
    
    wx = (W - w_w) // 2
    wy = av_y + AV - (w_h // 2) + 10
    
    # Subtle drop shadow
    draw.text((wx + 3, wy + 3), "WELCOME", font=font_welcome, fill=(0, 0, 0, 200))
    # Main text
    draw.text((wx, wy), "WELCOME", font=font_welcome, fill=(255, 255, 255, 255))
    
    # ── Text Username ──────────────────────────────────────────────────────
    try:
        u_bb = draw.textbbox((0, 0), display_name, font=font_user)
    except Exception:
        u_bb = (0, 0, 150, 30)
        
    u_w, u_h = u_bb[2] - u_bb[0], u_bb[3] - u_bb[1]
    
    ux = (W - u_w) // 2
    uy = wy + w_h + 10
    
    draw.text((ux + 2, uy + 2), display_name, font=font_user, fill=(0, 0, 0, 200))
    draw.text((ux, uy), display_name, font=font_user, fill=(255, 255, 255, 255))

    out = io.BytesIO()
    card.save(out, format="PNG")
    out.seek(0)
    return out

class WelcomeSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel_id = int(os.environ.get("WELCOME_CHANNEL_ID", "0"))
        if not channel_id:
            return
            
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            avatar_bytes = await member.display_avatar.with_format("png").with_size(256).read()
        except Exception:
            avatar_bytes = b""

        try:
            image_stream = await asyncio.to_thread(
                _generate_welcome_card,
                member.name,
                avatar_bytes,
                member.guild.member_count or 0,
                WELCOME_BG_PATH,
                member.guild.name,
            )
            file = discord.File(image_stream, filename="welcome.png")
            await channel.send(f"Greetings {member.mention}, welcome to {member.guild.name}.", file=file)
        except Exception as e:
            LOGGER.error(f"Failed to generate welcome card: {e}")
            await channel.send(f"Greetings {member.mention}, welcome to {member.guild.name}.")

    @app_commands.command(name="setwelcome", description="Configure the welcome system (attach an image to set a custom background)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setwelcome(self, interaction: discord.Interaction, background: Optional[discord.Attachment] = None):
        if not background:
            if WELCOME_BG_PATH.exists():
                WELCOME_BG_PATH.unlink()
            await interaction.response.send_message("Welcome background reset to default.", ephemeral=True)
            return

        if not background.content_type or not background.content_type.startswith("image/"):
            return await interaction.response.send_message("Please attach a valid image file.", ephemeral=True)

        await background.save(WELCOME_BG_PATH)
        await interaction.response.send_message("Welcome background updated successfully!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeSystem(bot))
