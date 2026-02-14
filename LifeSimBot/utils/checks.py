# utils/checks.py
import discord
from discord import app_commands
from .constants import Emojis
from db.database import db # This assumes db is initialized in your bot lifecycle
from datetime import datetime, timezone

def is_developer():
    """
    Check if the user is a developer listed in .env.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        # We lazy load os to avoid circular dependencies if possible, 
        # but usually safe here.
        import os
        dev_ids = os.getenv("DEV_IDS", "").split(",")
        if str(interaction.user.id) not in dev_ids:
            raise app_commands.MissingPermissions(["Developer Access"])
        return True
    return app_commands.check(predicate)

def is_registered():
    """
    Checks if the user has an account in the database.
    If not, it prompts them to start.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        # We query the DB to see if they exist
        # Note: This requires the DB to be accessible here.
        # To keep it fast, we can sometimes check a cache, 
        # but for this scale, a quick DB Select is fine.
        
        user = await db.fetch_one("SELECT user_id, username FROM users WHERE user_id = ?", interaction.user.id)

        if not user or not user.get("username"):
            # We reject the command and tell them to register
            # We raise a custom error or just return False (which raises CheckFailure)
            # Custom error allows for a specific error message in the handler
            raise app_commands.AppCommandError("User Not Registered")
            
        return True
    return app_commands.check(predicate)

def has_permissions(*permission_names: str):
    """
    Checks if the invoking user has the given Discord guild permissions.
    Intended for slash commands (app_commands).
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild or not interaction.user:
            raise app_commands.MissingPermissions(list(permission_names))

        perms = getattr(interaction.user, "guild_permissions", None)
        if perms is None:
            raise app_commands.MissingPermissions(list(permission_names))

        missing = [name for name in permission_names if not getattr(perms, name, False)]
        if missing:
            raise app_commands.MissingPermissions(missing)
        return True

    return app_commands.check(predicate)

def has_item(item_id: str, quantity: int = 1):
    """
    Checks if a user has a specific item in their inventory.
    Useful for 'crafting' or 'using' commands.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        row = await db.fetch_one(
            "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", 
            interaction.user.id, item_id
        )
        
        if not row or row['quantity'] < quantity:
            raise app_commands.AppCommandError(f"Missing Item: {item_id}")
            
        return True
    return app_commands.check(predicate)


async def safe_defer(interaction: discord.Interaction, *, ephemeral: bool = False, thinking: bool = True):
    """
    Safely defers an interaction response if it hasn't been responded to yet.
    Useful when commands may do DB work before replying.
    """
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral, thinking=thinking)
    except (discord.InteractionResponded, discord.NotFound):
        return


async def safe_reply(
    interaction: discord.Interaction,
    *,
    content: str | None = None,
    embed: discord.Embed | None = None,
    embeds: list[discord.Embed] | None = None,
    view: discord.ui.View | None = None,
    ephemeral: bool = False,
    **kwargs,
):
    """
    Sends a response or followup depending on whether the interaction was already responded to.
    """
    try:
        embed_kw = kwargs.pop("embed", None)
        embeds_kw = kwargs.pop("embeds", None)

        merged_embeds: list[discord.Embed] = []
        if embed is not None:
            merged_embeds.append(embed)
        if embeds:
            merged_embeds.extend(embeds)
        if embed_kw is not None:
            merged_embeds.append(embed_kw)
        if embeds_kw is not None:
            if isinstance(embeds_kw, (list, tuple)):
                merged_embeds.extend(list(embeds_kw))
            else:
                merged_embeds.append(embeds_kw)

        layout_view_type = getattr(getattr(discord, "ui", None), "LayoutView", None)
        if view is not None and layout_view_type is not None and isinstance(view, layout_view_type):
            try:
                from views.v2_embed import apply_v2_embed_layout, embed_to_v2_items, iter_all_items

                layout_types = (
                    discord.ui.Container,
                    discord.ui.TextDisplay,
                    discord.ui.Section,
                    discord.ui.MediaGallery,
                    discord.ui.Separator,
                )
                already_has_layout = any(isinstance(item, layout_types) for item in iter_all_items(view))

                if not already_has_layout and (content or merged_embeds):
                    body_items: list[discord.ui.Item] = []
                    if content:
                        body_items.extend(embed_to_v2_items(discord.Embed(description=content)))
                        content = None

                    for emb in merged_embeds:
                        body_items.extend(embed_to_v2_items(emb))
                        try:
                            from views.v2_embed import _safe_separator

                            body_items.append(_safe_separator())
                        except Exception:
                            body_items.append(discord.ui.Separator())

                    if body_items and isinstance(body_items[-1], discord.ui.Separator):
                        body_items.pop()

                    apply_v2_embed_layout(view, body_items=body_items)

                merged_embeds = []
            except Exception:
                merged_embeds = []

        payload: dict[str, object] = dict(content=content, ephemeral=ephemeral, **kwargs)
        if view is not None:
            payload["view"] = view

        if len(merged_embeds) == 1:
            payload["embed"] = merged_embeds[0]
        elif len(merged_embeds) > 1:
            payload["embeds"] = merged_embeds

        if interaction.response.is_done():
            return await interaction.followup.send(**payload)

        return await interaction.response.send_message(**payload)
    except discord.NotFound:
        return None


def _parse_time(value) -> datetime | None:
    """Best-effort parse of timestamps stored as ISO strings or epoch seconds."""
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OSError, ValueError):
            return None

    if isinstance(value, str):
        # Epoch-as-string
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except ValueError:
            pass

        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            return None

    return None


def check_cooldown(last_time, cooldown_seconds: int) -> tuple[bool, int]:
    """
    Returns (can_use, remaining_seconds).
    `last_time` may be an ISO timestamp string or epoch seconds.
    """
    last_dt = _parse_time(last_time)
    if last_dt is None:
        return True, 0

    now = datetime.now(timezone.utc)
    elapsed = (now - last_dt).total_seconds()
    remaining = int(max(0, cooldown_seconds - elapsed))
    return remaining <= 0, remaining


def check_in_jail(user_data: dict) -> str | None:
    """If the user is in jail, returns a user-facing message; otherwise None."""
    until = _parse_time(user_data.get("jail_until") or user_data.get("jail_release_time"))
    if until is None:
        return None

    now = datetime.now(timezone.utc)
    if until <= now:
        return None

    remaining = int((until - now).total_seconds())
    from utils.format import format_time
    return f"⛓️ You're in jail for **{format_time(remaining)}**."


def check_in_hospital(user_data: dict) -> str | None:
    """If the user is in hospital, returns a user-facing message; otherwise None."""
    until = _parse_time(user_data.get("hospital_until"))
    if until is None:
        return None

    now = datetime.now(timezone.utc)
    if until <= now:
        return None

    remaining = int((until - now).total_seconds())
    from utils.format import format_time
    return f"🏥 You're in the hospital for **{format_time(remaining)}**."


def check_user_stats(user_data: dict, *, energy_needed: int = 0) -> list[str]:
    """Returns a list of issues preventing an action (empty means OK)."""
    issues: list[str] = []

    if energy_needed:
        energy = int(user_data.get("energy", 100))
        if energy < energy_needed:
            issues.append(f"⚡ Not enough energy (**{energy}**/{energy_needed})")

    return issues
