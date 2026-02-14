# utils/embeds.py

from __future__ import annotations

import discord
from typing import Optional

from utils.format import money, progress_bar


def create_success_embed(title: str, description: str, **kwargs) -> discord.Embed:
    """Create a success embed."""
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=0x22C55E,  # Green
        **kwargs
    )
    return embed


def create_error_embed(title: str, description: str, **kwargs) -> discord.Embed:
    """Create an error embed."""
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=0xF43F5E,  # Red
        **kwargs
    )
    return embed


def create_info_embed(title: str, description: str, **kwargs) -> discord.Embed:
    """Create an info embed."""
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=0x3B82F6,  # Blue
        **kwargs
    )
    return embed


def create_warning_embed(title: str, description: str, **kwargs) -> discord.Embed:
    """Create a warning embed."""
    embed = discord.Embed(
        title=f"⚠️ {title}",
        description=description,
        color=0xFBBF24,  # Yellow
        **kwargs
    )
    return embed


def create_loading_embed(title: str = "Loading...", description: str = "Please wait...") -> discord.Embed:
    """Create a loading embed."""
    embed = discord.Embed(
        title=f"⏳ {title}",
        description=description,
        color=0x6B7280,  # Gray
    )
    return embed
