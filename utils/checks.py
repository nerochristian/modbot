"""
Permission checks for commands
"""

import os
import re
import discord
from discord import app_commands
from discord.ext import commands
def get_owner_ids() -> set[int]:
    """Return bot owner IDs from `OWNER_IDS`/`OWNER_ID` env vars.

    Owner IDs come ONLY from configuration — there is deliberately no
    hardcoded fallback. A baked-in ID cannot be revoked without a code
    change and silently grants that account full, permission-check-bypassing
    power (including the ``execute_python`` gate), so it is treated as a
    backdoor and excluded.
    """
    raw = os.getenv("OWNER_IDS") or os.getenv("OWNER_ID") or ""
    owner_ids: set[int] = set()

    for part in re.split(r"[,\s]+", raw.strip()):
        part = part.strip()
        if not part:
            continue
        try:
            owner_ids.add(int(part))
        except ValueError:
            continue

    return owner_ids


def is_bot_owner_id(user_id: int) -> bool:
    return user_id in get_owner_ids()


def _command_actor(subject):
    return getattr(subject, "user", None) or getattr(subject, "author", None)


def _command_client(subject):
    return getattr(subject, "client", None) or getattr(subject, "bot", None)


def _command_guild_id(subject):
    guild_id = getattr(subject, "guild_id", None)
    if guild_id is not None:
        return guild_id
    return getattr(getattr(subject, "guild", None), "id", None)


def _configured_role_ids(settings: dict, *keys: str) -> set[int]:
    role_ids: set[int] = set()
    for key in keys:
        raw = settings.get(key)
        values = raw if isinstance(raw, (list, tuple, set, frozenset)) else [raw]
        for value in values:
            if isinstance(value, bool):
                continue
            try:
                role_id = int(value)
            except (TypeError, ValueError, OverflowError):
                continue
            if role_id > 0:
                role_ids.add(role_id)
    return role_ids


def _missing_permissions(subject, labels: list[str]):
    if isinstance(subject, commands.Context):
        raise commands.MissingPermissions(labels)
    raise app_commands.MissingPermissions(labels)


def _dual_check(predicate):
    """Apply the same async predicate to prefix and application commands."""
    def decorator(callback):
        callback = commands.check(predicate)(callback)
        return app_commands.check(predicate)(callback)
    return decorator


async def is_bot_owner(subject) -> bool:
    """Return True when the command actor is treated as the bot owner."""
    actor = _command_actor(subject)
    client = _command_client(subject)
    if actor is None or client is None:
        return False
    if is_bot_owner_id(actor.id):
        return True

    owner_ids = getattr(client, "owner_ids", None)
    if owner_ids and actor.id in owner_ids:
        return True

    is_owner = getattr(client, "is_owner", None)
    if is_owner is None:
        return False

    try:
        return bool(await is_owner(actor))
    except Exception:
        return False


async def moderator_predicate(subject) -> bool:
    actor = _command_actor(subject)
    client = _command_client(subject)
    guild_id = _command_guild_id(subject)
    if actor is None or client is None or guild_id is None:
        _missing_permissions(subject, ["Moderator"])
    if await is_bot_owner(subject):
        return True
    permissions = actor.guild_permissions
    if (
        permissions.administrator
        or permissions.kick_members
        or permissions.ban_members
        or permissions.manage_messages
        or permissions.moderate_members
    ):
        return True
    settings = await client.db.get_settings(guild_id)
    configured = _configured_role_ids(
        settings,
        "mod_roles",
        "mod_role",
        "moderator_role",
        "trial_mod_role",
        "senior_mod_role",
        "supervisor_role",
        "manager_role",
        "admin_role",
        "admin_roles",
    )
    if configured.intersection(role.id for role in actor.roles):
        return True
    _missing_permissions(subject, ["Moderator"])


def is_mod():
    """Require moderator authority for prefix and application commands."""
    return _dual_check(moderator_predicate)

def is_owner_only():
    """Check if user is a bot owner - for owner-only commands"""
    async def predicate(subject) -> bool:
        if await is_bot_owner(subject):
            return True
        _missing_permissions(subject, ["Bot Owner"])
    return _dual_check(predicate)

async def senior_mod_predicate(subject) -> bool:
    actor = _command_actor(subject)
    client = _command_client(subject)
    guild_id = _command_guild_id(subject)
    if actor is None or client is None or guild_id is None:
        _missing_permissions(subject, ["Senior Moderator"])
    if await is_bot_owner(subject):
        return True
    permissions = actor.guild_permissions
    if permissions.administrator or permissions.ban_members:
        return True
    settings = await client.db.get_settings(guild_id)
    configured = _configured_role_ids(
        settings,
        "mod_roles",
        "senior_mod_role",
        "senior_mod_roles",
        "supervisor_role",
        "manager_role",
        "admin_role",
        "admin_roles",
    )
    if configured.intersection(role.id for role in actor.roles):
        return True
    _missing_permissions(subject, ["Senior Moderator"])


def is_senior_mod():
    """Require senior-moderator authority for both command surfaces."""
    return _dual_check(senior_mod_predicate)

async def admin_predicate(subject) -> bool:
    actor = _command_actor(subject)
    client = _command_client(subject)
    guild_id = _command_guild_id(subject)
    if actor is None or client is None or guild_id is None:
        _missing_permissions(subject, ["Administrator", "Manager"])
    if await is_bot_owner(subject):
        return True
    if actor.guild_permissions.administrator:
        return True
    settings = await client.db.get_settings(guild_id)
    configured = _configured_role_ids(
        settings,
        "admin_role",
        "admin_roles",
        "manager_role",
        "manager_roles",
    )
    if configured.intersection(role.id for role in actor.roles):
        return True
    _missing_permissions(subject, ["Administrator", "Manager"])


def is_admin():
    """Require administrator authority for both command surfaces."""
    return _dual_check(admin_predicate)

def has_permissions_or_owner(**perms):
    """Prefix-command permission check that always allows configured bot owners."""
    base_check = commands.has_permissions(**perms)

    async def predicate(ctx: commands.Context) -> bool:
        if is_bot_owner_id(ctx.author.id):
            return True
        return await base_check.predicate(ctx)

    return commands.check(predicate)

def can_moderate(target:  discord.Member, moderator: discord.Member) -> bool:
    """Check if moderator can moderate the target"""
    # Bot owner can moderate anyone (subject to Discord's own limitations)
    if is_bot_owner_id(moderator.id):
        return True

    # Can't moderate yourself
    if target.id == moderator.id:
        return False

    # Server owner can moderate anyone (subject to Discord's own limitations)
    if moderator.id == moderator.guild.owner_id:
        return True

    # Can't moderate the bot owner(s)
    if is_bot_owner_id(target.id):
        return False
    
    # Can't moderate the owner
    if target.id == target.guild.owner_id:
        return False
    
    # Can't moderate someone with higher/equal role
    if target.top_role >= moderator.top_role:
        return False
    
    return True

def bot_can_moderate(target: discord.Member, guild: discord.Guild) -> bool:
    """Check if the bot can moderate the target"""
    bot_member = guild.me
    
    # Can't moderate the owner
    if target.id == guild.owner_id:
        return False
    
    # Can't moderate someone with higher/equal role than bot
    if target.top_role >= bot_member.top_role:
        return False
    
    return True
