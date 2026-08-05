"""
Ultra-Improved Verification System:
- Image-based captcha (Pillow) with text fallback
- Session TTL (grace period for reconnects)
- Bypass roles (staff/boosters skip verification)
- Rate limiting (cooldown between captcha generation)
- Rich logging (attempts, success, failure, timeout)
- Admin controls (settings, bypass management, timeout config)
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import io
import json
import logging
import os
import random
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal, List

import discord
from discord import app_commands
from discord.ext import commands

from config import Config
from utils.checks import is_admin
from utils.embeds import ModEmbed
from utils.components_v2 import branded_panel_container
from utils.guild_branding import get_guild_brand_assets, resolve_guild_component_emoji
from utils.status_emojis import get_app_emoji, sync_status_emojis_to_application
from utils.server_setup import apply_verification_gate, module_enabled, sync_setup_aliases

# Try to import Pillow for image captchas
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


CAPTCHA_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CAPTCHA_LENGTH = 5
CAPTCHA_TTL_SECONDS = 5 * 60
CAPTCHA_COOLDOWN_SECONDS = 15
DEFAULT_SESSION_TTL_SECONDS = 30 * 60  # 30 minutes
CaptchaPurpose = Literal["server", "voice"]
logger = logging.getLogger("ModBot.Verification")


@dataclass(frozen=True)
class CaptchaEntry:
    code: str
    expires_at: datetime
    image_bytes: Optional[bytes] = None

    def expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


@dataclass
class SessionEntry:
    verified_at: datetime
    expires_at: datetime

    def expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


def _generate_captcha_code() -> str:
    return "".join(secrets.choice(CAPTCHA_ALPHABET) for _ in range(CAPTCHA_LENGTH))


def _generate_captcha_image(code: str) -> Optional[bytes]:
    """Generate a distorted captcha image using Pillow."""
    if not PILLOW_AVAILABLE:
        return None

    try:
        # Image dimensions
        width, height = 200, 80
        
        # Create image with gradient background
        img = Image.new("RGB", (width, height), (45, 45, 55))
        draw = ImageDraw.Draw(img)
        
        # Add noise dots
        for _ in range(150):
            x = random.randint(0, width)
            y = random.randint(0, height)
            r = random.randint(60, 120)
            g = random.randint(60, 120)
            b = random.randint(80, 140)
            draw.ellipse([x, y, x + 2, y + 2], fill=(r, g, b))
        
        # Add noise lines
        for _ in range(5):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            draw.line([(x1, y1), (x2, y2)], fill=(80, 80, 100), width=1)
        
        # Try to use a font, fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except Exception:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            except Exception:
                font = ImageFont.load_default()
        
        # Draw each character with slight rotation/offset
        x_offset = 15
        colors = [
            (88, 101, 242),   # Blurple
            (87, 242, 135),   # Green
            (254, 231, 92),   # Yellow
            (235, 69, 158),   # Pink
            (237, 66, 69),    # Red
        ]
        
        for i, char in enumerate(code):
            color = colors[i % len(colors)]
            y_offset = random.randint(-5, 5)
            draw.text((x_offset, 15 + y_offset), char, font=font, fill=color)
            x_offset += 35
        
        # Apply slight blur for anti-OCR
        img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()
    except Exception:
        return None


class CaptchaModal(discord.ui.Modal, title="Verification Captcha"):
    captcha = discord.ui.TextInput(
        label="Enter the captcha code",
        placeholder="Example: A1B2C",
        min_length=CAPTCHA_LENGTH,
        max_length=CAPTCHA_LENGTH,
        required=True,
    )

    def __init__(
        self,
        cog: "Verification",
        *,
        guild_id: int,
        user_id: int,
        purpose: CaptchaPurpose,
    ):
        super().__init__(timeout=60)
        self._cog = cog
        self._guild_id = guild_id
        self._user_id = user_id
        self._purpose = purpose

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._cog._handle_captcha_submit(
            interaction,
            guild_id=self._guild_id,
            user_id=self._user_id,
            purpose=self._purpose,
            attempt=str(self.captcha.value or "").strip(),
        )


class CaptchaView(discord.ui.View):
    def __init__(
        self,
        cog: "Verification",
        *,
        guild_id: int,
        user_id: int,
        purpose: CaptchaPurpose,
    ):
        super().__init__(timeout=180)
        self._cog = cog
        self._guild_id = guild_id
        self._user_id = user_id
        self._purpose = purpose

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self._user_id:
            return True
        try:
            ephemeral = interaction.guild is not None
            await interaction.response.send_message(
                embed=ModEmbed.error("Not For You", "Start your own verification from the panel."),
                ephemeral=ephemeral,
            )
        except Exception:
            pass
        return False

    @discord.ui.button(
        label="Submit Captcha",
        style=discord.ButtonStyle.primary,
        custom_id="verification:captcha_submit",
    )
    async def submit(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(
            CaptchaModal(
                self._cog,
                guild_id=self._guild_id,
                user_id=self._user_id,
                purpose=self._purpose,
            )
        )

    @discord.ui.button(
        label="New Captcha",
        style=discord.ButtonStyle.secondary,
        custom_id="verification:captcha_new",
    )
    async def new(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._cog._start_captcha(
            interaction,
            regenerate=True,
            guild_id=self._guild_id,
            purpose=self._purpose,
        )


class VerificationPanelLayout(discord.ui.LayoutView):
    def __init__(self, cog: "Verification", *, guild: Optional[discord.Guild] = None):
        super().__init__(timeout=None)
        self._cog = cog

        guild_name = guild.name if guild else "this server"
        logo_url, _ = get_guild_brand_assets(guild) if guild else (None, None)
        container = branded_panel_container(
            title=f"Unlock {guild_name}",
            description=(
                "Complete one private security check to enter. "
                "Docket grants your access automatically."
            ),
            logo_url=logo_url,
            accent_color=0x2B7FFF,
        )

        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

        start_button = discord.ui.Button(
            label="Verify now",
            style=discord.ButtonStyle.primary,
            custom_id="verification:start",
        )

        async def _start(interaction: discord.Interaction) -> None:
            await self._cog._start_captcha(interaction, regenerate=True, purpose="server")

        start_button.callback = _start

        tutorial_button = discord.ui.Button(
            label="How it works",
            style=discord.ButtonStyle.secondary,
            custom_id="verification:tutorial",
        )

        async def _tutorial(interaction: discord.Interaction) -> None:
            await self._cog._send_tutorial(interaction)

        tutorial_button.callback = _tutorial

        container.add_item(discord.ui.ActionRow(start_button, tutorial_button))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(
            discord.ui.TextDisplay(
                "-# Private  •  No password  •  Usually under a minute"
            )
        )

        self.add_item(container)


class WebsiteVerificationLayout(discord.ui.LayoutView):
    """Ephemeral Components v2 card handed to a member after they press Verify me
    when the server uses website (Cloudflare Turnstile) verification."""

    def __init__(self, *, guild: Optional[discord.Guild], url: str):
        super().__init__(timeout=10 * 60)

        guild_name = guild.name if guild else "this server"
        logo_url, _ = get_guild_brand_assets(guild) if guild else (None, None)
        container = branded_panel_container(
            title="Your checkpoint is ready",
            description=(
                f"Open the secure page below to unlock **{guild_name}**. "
                "Docket never asks for your password or another Discord login."
            ),
            logo_url=logo_url,
            accent_color=0x2B7FFF,
        )

        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(
            discord.ui.ActionRow(
                discord.ui.Button(
                    label="Open secure checkpoint",
                    style=discord.ButtonStyle.link,
                    url=url,
                )
            )
        )
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(
            discord.ui.TextDisplay(
                "-# Expires in 10 minutes  •  Single-use  •  Protected human check"
            )
        )

        self.add_item(container)


class Verification(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Pending captchas: (guild_id, user_id, purpose) -> CaptchaEntry
        self._pending: dict[tuple[int, int, CaptchaPurpose], CaptchaEntry] = {}
        # Cooldowns: (guild_id, user_id) -> last_captcha_time
        self._cooldowns: dict[tuple[int, int], datetime] = {}
        # Voice targets: (guild_id, user_id) -> target_channel_id
        self._voice_targets: dict[tuple[int, int], int] = {}
        # Allow once (skip re-gating after move): (guild_id, user_id) -> channel_id
        self._voice_allow_once: dict[tuple[int, int], int] = {}
        # Voice sessions with TTL: (guild_id, user_id) -> SessionEntry
        self._voice_sessions: dict[tuple[int, int], SessionEntry] = {}
        # Persistent components (so old panels keep working after restarts)
        self.bot.add_view(VerificationPanelLayout(self))
        self._panels_refreshed = False

    async def _refresh_configured_panels(self) -> None:
        if self._panels_refreshed:
            return
        self._panels_refreshed = True

        for guild in self.bot.guilds:
            try:
                settings = await self._get_settings(guild.id)
                if not module_enabled(settings, "verification", False):
                    continue
                unverified_role, verified_role = await self._ensure_verification_roles(
                    guild,
                    settings,
                )
                gate_result = await apply_verification_gate(guild, settings)
                republish_panel = bool(gate_result.get("updated"))
                if gate_result.get("errors"):
                    logger.warning(
                        "Verification access repair reported errors for guild %s: %s",
                        guild.id,
                        "; ".join(str(error) for error in gate_result["errors"]),
                    )
                if unverified_role is not None and verified_role is not None:
                    reconciled = await self._reconcile_verified_members(
                        guild,
                        unverified_role,
                        verified_role,
                    )
                    if reconciled:
                        logger.info(
                            "Removed the waiting role from %s verified member(s) in guild %s",
                            reconciled,
                            guild.id,
                        )
                    assigned = await self._queue_existing_members(
                        guild,
                        settings,
                        unverified_role,
                        verified_role,
                    )
                    if assigned:
                        logger.info(
                            "Queued %s existing member(s) for verification in guild %s",
                            assigned,
                            guild.id,
                        )
                channel_id = int(settings.get("verify_channel", 0) or 0)
                message_id = int(settings.get("verification_panel_message_id", 0) or 0)
                channel = guild.get_channel(channel_id)
                if not isinstance(channel, discord.TextChannel):
                    continue

                panel_view = VerificationPanelLayout(self, guild=guild)
                panel_message: Optional[discord.Message] = None
                if message_id and not republish_panel:
                    try:
                        panel_message = await channel.fetch_message(message_id)
                    except discord.NotFound:
                        panel_message = None

                if message_id and republish_panel:
                    try:
                        stale_panel = await channel.fetch_message(message_id)
                        await stale_panel.delete()
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        pass

                if panel_message is None:
                    panel_message = await channel.send(view=panel_view)
                    await self.bot.db.update_settings(
                        guild.id,
                        {"verification_panel_message_id": str(panel_message.id)},
                    )
                else:
                    await panel_message.edit(content=None, embeds=[], view=panel_view)
            except (TypeError, ValueError, discord.Forbidden, discord.HTTPException) as exc:
                logger.warning("Could not refresh verification panel for guild %s: %s", guild.id, exc)

    # ─────────────────────────────────────────────────────────────────────────
    # Settings Helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _get_roles(
        self, guild: discord.Guild
    ) -> tuple[Optional[discord.Role], Optional[discord.Role]]:
        settings = await self.bot.db.get_settings(guild.id)
        sync_setup_aliases(settings)
        try:
            unverified_id = int(settings.get("unverified_role", 0) or 0)
            verified_id = int(settings.get("verified_role", 0) or 0)
        except (TypeError, ValueError):
            return None, None
        unverified = guild.get_role(unverified_id) if unverified_id else None
        verified = guild.get_role(verified_id) if verified_id else None
        return unverified, verified

    async def _ensure_verification_roles(
        self,
        guild: discord.Guild,
        settings: dict,
    ) -> tuple[discord.Role, discord.Role]:
        """Resolve or recreate verification roles when a configured role was deleted."""
        sync_setup_aliases(settings)
        try:
            unverified_id = int(settings.get("unverified_role", 0) or 0)
            verified_id = int(settings.get("verified_role", 0) or 0)
        except (TypeError, ValueError):
            unverified_id = 0
            verified_id = 0

        unverified = guild.get_role(unverified_id) if unverified_id else None
        verified = guild.get_role(verified_id) if verified_id else None
        settings_changed = False

        if verified is None:
            verified = next(
                (role for role in guild.roles if not role.managed and role.name.casefold() == "verified"),
                None,
            )
            if verified is None:
                verified = await guild.create_role(
                    name="Verified",
                    colour=discord.Colour(0x57F287),
                    permissions=discord.Permissions.none(),
                    reason="Repair missing verification role",
                )
            settings["verified_role"] = verified.id
            settings["verification_role"] = verified.id
            settings_changed = True

        if unverified is None:
            unverified = next(
                (role for role in guild.roles if not role.managed and role.name.casefold() == "unverified"),
                None,
            )
            if unverified is None:
                unverified = await guild.create_role(
                    name="Unverified",
                    colour=discord.Colour(0x747F8D),
                    permissions=discord.Permissions.none(),
                    reason="Repair missing verification waiting role",
                )
            settings["unverified_role"] = unverified.id
            settings_changed = True

        if settings_changed:
            await self.bot.db.update_settings(guild.id, settings)
            logger.info(
                "Repaired verification role configuration for guild %s (verified=%s, unverified=%s)",
                guild.id,
                verified.id,
                unverified.id,
            )

        return unverified, verified

    @staticmethod
    async def _ensure_waiting_role(
        member: discord.Member,
        unverified_role: discord.Role,
    ) -> bool:
        """Repair setup gaps for members who joined before verification was enabled."""
        if unverified_role in member.roles:
            return True
        try:
            await member.add_roles(
                unverified_role,
                reason="Verification started - assign waiting role",
            )
        except (discord.Forbidden, discord.HTTPException):
            return False
        return True

    @staticmethod
    def _member_needs_waiting_role(
        member: discord.Member,
        *,
        owner_id: int,
        unverified_role: discord.Role,
        verified_role: discord.Role,
        staff_role_ids: set[int],
    ) -> bool:
        if member.bot or member.id == owner_id:
            return False
        if unverified_role in member.roles or verified_role in member.roles:
            return False
        if any(role.id in staff_role_ids for role in member.roles):
            return False
        permissions = member.guild_permissions
        return not (
            permissions.administrator
            or permissions.manage_guild
            or permissions.manage_channels
            or permissions.moderate_members
        )

    async def _queue_existing_members(
        self,
        guild: discord.Guild,
        settings: dict,
        unverified_role: discord.Role,
        verified_role: discord.Role,
    ) -> int:
        staff_role_ids: set[int] = set()
        for key in (
            "owner_role",
            "manager_role",
            "admin_role",
            "supervisor_role",
            "senior_mod_role",
            "mod_role",
            "trial_mod_role",
            "staff_role",
        ):
            try:
                role_id = int(settings.get(key, 0) or 0)
            except (TypeError, ValueError):
                role_id = 0
            if role_id:
                staff_role_ids.add(role_id)

        assigned = 0
        for member in guild.members:
            if not self._member_needs_waiting_role(
                member,
                owner_id=guild.owner_id,
                unverified_role=unverified_role,
                verified_role=verified_role,
                staff_role_ids=staff_role_ids,
            ):
                continue
            if await self._ensure_waiting_role(member, unverified_role):
                assigned += 1
        return assigned

    @staticmethod
    async def _reconcile_verified_members(
        guild: discord.Guild,
        unverified_role: discord.Role,
        verified_role: discord.Role,
    ) -> int:
        """Restore the invariant that a verified member never keeps the waiting role."""
        candidates = [
            member
            for member in guild.members
            if verified_role in member.roles and unverified_role in member.roles
        ]
        if not candidates:
            return 0

        removed = 0
        semaphore = asyncio.Semaphore(4)

        async def remove_waiting_role(member: discord.Member) -> None:
            nonlocal removed
            async with semaphore:
                try:
                    await member.remove_roles(
                        unverified_role,
                        reason="Verification role reconciliation",
                    )
                    removed += 1
                except (discord.Forbidden, discord.HTTPException) as exc:
                    logger.warning(
                        "Could not reconcile verification roles for member %s in guild %s: %s",
                        member.id,
                        guild.id,
                        exc,
                    )

        await asyncio.gather(*(remove_waiting_role(member) for member in candidates))
        return removed

    @staticmethod
    async def _apply_verified_roles(
        member: discord.Member,
        unverified_role: discord.Role,
        verified_role: discord.Role,
        *,
        reason: str,
    ) -> discord.Member:
        """Atomically grant access and remove the waiting role, then verify the result."""
        roles_by_id = {
            role.id: role
            for role in member.roles
            if role.id not in {member.guild.id, unverified_role.id}
        }
        roles_by_id[verified_role.id] = verified_role
        updated = await member.edit(roles=list(roles_by_id.values()), reason=reason)
        updated_member = updated or await member.guild.fetch_member(member.id)
        updated_role_ids = {role.id for role in updated_member.roles}
        if verified_role.id not in updated_role_ids or unverified_role.id in updated_role_ids:
            raise RuntimeError("Discord did not persist the final verification role state")
        return updated_member

    async def _get_settings(self, guild_id: int) -> dict:
        settings = await self.bot.db.get_settings(guild_id)
        sync_setup_aliases(settings)
        return settings

    async def _save_verification_settings(
        self,
        guild: discord.Guild,
        settings: dict,
        *,
        previous_unverified_role_id: Optional[int] = None,
    ) -> dict:
        sync_setup_aliases(settings)
        await self.bot.db.update_settings(guild.id, settings)
        return await apply_verification_gate(
            guild,
            settings,
            previous_unverified_role_id=previous_unverified_role_id,
        )

    async def _is_server_verification_enabled(self, guild_id: int) -> bool:
        try:
            settings = await self._get_settings(guild_id)
            return module_enabled(settings, "verification", False)
        except Exception:
            return False

    async def _website_verification_url(self, guild_id: int, user_id: int) -> Optional[str]:
        settings = await self._get_settings(guild_id)
        if settings.get("verification_method") != "website":
            return None
        base_url = (os.getenv("DASHBOARD_PUBLIC_URL") or "").strip().rstrip("/")
        secret = (
            os.getenv("VERIFICATION_LINK_SECRET")
            or os.getenv("SESSION_SECRET")
            or ""
        ).strip()
        if not base_url or not secret:
            return None
        payload = {
            "e": int(time.time()) + 10 * 60,
            "g": str(guild_id),
            "n": secrets.token_hex(16),
            "u": str(user_id),
        }
        encoded = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).decode("ascii").rstrip("=")
        signature = base64.urlsafe_b64encode(
            hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest()
        ).decode("ascii").rstrip("=")
        return f"{base_url}/verify/{encoded}.{signature}"

    async def _get_verify_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        try:
            settings = await self._get_settings(guild.id)
            cid = settings.get("verify_log_channel")
            if not cid:
                return None
            ch = guild.get_channel(int(cid))
            return ch if isinstance(ch, discord.TextChannel) else None
        except Exception:
            return None

    async def _get_bypass_roles(self, guild_id: int) -> List[int]:
        """Get list of role IDs that bypass voice verification."""
        try:
            settings = await self.bot.db.get_settings(guild_id)
            bypass = settings.get("vc_verify_bypass_roles", [])
            return bypass if isinstance(bypass, list) else []
        except Exception:
            return []

    async def _get_session_ttl(self, guild_id: int) -> int:
        """Get session TTL in seconds."""
        try:
            settings = await self.bot.db.get_settings(guild_id)
            return int(settings.get("vc_verify_session_ttl", DEFAULT_SESSION_TTL_SECONDS))
        except Exception:
            return DEFAULT_SESSION_TTL_SECONDS

    async def _is_voice_verification_enabled(self, guild_id: int) -> bool:
        try:
            settings = await self.bot.db.get_settings(guild_id)
            return bool(settings.get("voice_verification_enabled", False))
        except Exception:
            return False

    async def _get_waiting_voice_channel(self, guild: discord.Guild) -> Optional[discord.VoiceChannel]:
        try:
            settings = await self.bot.db.get_settings(guild.id)
            cid = settings.get("waiting_verify_voice_channel")
            if not cid:
                return None
            ch = guild.get_channel(int(cid))
            return ch if isinstance(ch, discord.VoiceChannel) else None
        except Exception:
            return None

    def _has_bypass_role(self, member: discord.Member, bypass_role_ids: List[int]) -> bool:
        """Check if member has any bypass role."""
        member_role_ids = {r.id for r in member.roles}
        return bool(member_role_ids & set(bypass_role_ids))

    def _is_on_cooldown(self, guild_id: int, user_id: int) -> tuple[bool, int]:
        """Check if user is on cooldown. Returns (is_cooldown, seconds_remaining)."""
        key = (guild_id, user_id)
        last_time = self._cooldowns.get(key)
        if not last_time:
            return False, 0
        elapsed = (datetime.now(timezone.utc) - last_time).total_seconds()
        remaining = CAPTCHA_COOLDOWN_SECONDS - elapsed
        if remaining <= 0:
            return False, 0
        return True, int(remaining)

    def _set_cooldown(self, guild_id: int, user_id: int) -> None:
        self._cooldowns[(guild_id, user_id)] = datetime.now(timezone.utc)

    def _has_valid_session(self, guild_id: int, user_id: int) -> bool:
        """Check if user has a valid (non-expired) voice verification session."""
        key = (guild_id, user_id)
        session = self._voice_sessions.get(key)
        if not session:
            return False
        if session.expired():
            self._voice_sessions.pop(key, None)
            return False
        return True

    async def _create_session(self, guild_id: int, user_id: int) -> None:
        """Create a new voice verification session with TTL."""
        ttl = await self._get_session_ttl(guild_id)
        now = datetime.now(timezone.utc)
        self._voice_sessions[(guild_id, user_id)] = SessionEntry(
            verified_at=now,
            expires_at=now + timedelta(seconds=ttl),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Logging
    # ─────────────────────────────────────────────────────────────────────────

    async def _log_verify_event(
        self,
        guild: discord.Guild,
        *,
        member: discord.Member,
        outcome: str,
        detail: str,
        channel_name: Optional[str] = None,
    ) -> None:
        ch = await self._get_verify_log_channel(guild)
        if not ch:
            return
        try:
            color = {
                "verified": 0x57F287,
                "failed": 0xED4245,
                "timeout": 0xFEE75C,
                "bypass": 0x5865F2,
                "moved": 0x3498DB,
            }.get(outcome, Config.COLOR_INFO)
            
            embed = discord.Embed(
                title=f"📋 Verification: {outcome.title()}",
                color=color,
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=True)
            embed.add_field(name="Outcome", value=outcome.title(), inline=True)
            if channel_name:
                embed.add_field(name="Channel", value=channel_name, inline=True)
            embed.add_field(name="Detail", value=detail, inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            await ch.send(embed=embed)
        except Exception:
            return

    # ─────────────────────────────────────────────────────────────────────────
    # Voice Movement
    # ─────────────────────────────────────────────────────────────────────────

    async def _maybe_move_to_voice_target(self, guild: discord.Guild, member: discord.Member) -> None:
        key = (guild.id, member.id)
        target_id = self._voice_targets.get(key)
        if not target_id:
            return
        target = guild.get_channel(int(target_id))
        if not isinstance(target, (discord.VoiceChannel, discord.StageChannel)):
            self._voice_targets.pop(key, None)
            return
        try:
            # Allow this specific target move without re-triggering gating
            self._voice_allow_once[key] = int(target_id)
            await self._create_session(guild.id, member.id)
            await member.move_to(target, reason="Voice verification complete")
            self._voice_targets.pop(key, None)
            await self._log_verify_event(
                guild,
                member=member,
                outcome="moved",
                detail="Moved to target channel after verification",
                channel_name=target.name,
            )
        except Exception:
            return

    # ─────────────────────────────────────────────────────────────────────────
    # DM Verification Panel
    # ─────────────────────────────────────────────────────────────────────────

    async def _send_voice_verify_dm(self, *, guild: discord.Guild, member: discord.Member) -> None:
        layout = discord.ui.LayoutView(timeout=15 * 60)

        logo_url, banner_url = get_guild_brand_assets(guild)
        container = branded_panel_container(
            title="🔊 Voice Verification Required",
            description=(
                f"You tried to join a voice channel in **{guild.name}**.\n\n"
                "Complete verification to be moved into the voice channel you selected.\n\n"
                "**Solve the captcha image to continue.**"
            ),
            banner_url=banner_url,
            logo_url=logo_url,
            accent_color=getattr(Config, "COLOR_BRAND", 0x5865F2),
            banner_separated=True,
        )

        start_button = discord.ui.Button(
            label="Start Verification",
            style=discord.ButtonStyle.success,
            emoji=resolve_guild_component_emoji(
                guild,
                "verify",
                "verified",
                "success",
                "check",
                fallback="✅",
            ),
        )

        async def _start(interaction: discord.Interaction) -> None:
            if interaction.user.id != member.id:
                await interaction.response.send_message(
                    embed=ModEmbed.error("Not For You", "This verification is for someone else."),
                    ephemeral=interaction.guild is not None,
                )
                return
            await self._start_captcha(
                interaction,
                regenerate=True,
                guild_id=guild.id,
                purpose="voice",
            )

        start_button.callback = _start

        tutorial_button = discord.ui.Button(
            label="Tutorial",
            style=discord.ButtonStyle.secondary,
            emoji=resolve_guild_component_emoji(
                guild,
                "tutorial",
                "info",
                "help",
                fallback="ℹ️",
            ),
        )

        async def _tutorial(interaction: discord.Interaction) -> None:
            if interaction.user.id != member.id:
                await interaction.response.send_message(
                    embed=ModEmbed.error("Not For You", "This verification is for someone else."),
                    ephemeral=interaction.guild is not None,
                )
                return
            await self._send_tutorial(interaction)

        tutorial_button.callback = _tutorial

        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay("**Start Verification**\nSolve the captcha image to join voice."),
                accessory=start_button,
            )
        )
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay("**Tutorial**\nWatch the verification guide."),
                accessory=tutorial_button,
            )
        )

        layout.add_item(container)

        try:
            await member.send(view=layout)
        except Exception:
            return

    async def _send_tutorial(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="How verification works",
            description=(
                "1. Press **Verify now**.\n"
                "2. Complete the private human check Docket opens for you.\n"
                "3. Return to Discord—your access updates automatically.\n\n"
                "Docket never asks for your password or another Discord login."
            ),
            color=Config.COLOR_INFO,
        )
        await interaction.response.send_message(embed=embed, ephemeral=interaction.guild is not None)

    # ─────────────────────────────────────────────────────────────────────────
    # Captcha Flow
    # ─────────────────────────────────────────────────────────────────────────

    async def _resolve_guild_member(
        self, interaction: discord.Interaction, *, guild_id: int
    ) -> tuple[Optional[discord.Guild], Optional[discord.Member]]:
        guild = interaction.guild if interaction.guild and interaction.guild.id == guild_id else None
        if guild is None:
            guild = self.bot.get_guild(guild_id)
        if guild is None:
            return None, None

        if interaction.guild and isinstance(interaction.user, discord.Member):
            return guild, interaction.user

        try:
            member = guild.get_member(interaction.user.id)
            if member is None:
                member = await guild.fetch_member(interaction.user.id)
            return guild, member
        except Exception:
            return guild, None

    @staticmethod
    async def _send_start_response(
        interaction: discord.Interaction,
        *,
        ephemeral: bool,
        **payload,
    ) -> None:
        """Finish a verification start interaction, including a deferred one."""
        if not interaction.response.is_done():
            await interaction.response.send_message(ephemeral=ephemeral, **payload)
            return

        edit_payload = dict(payload)
        file = edit_payload.pop("file", None)
        files = edit_payload.pop("files", None)
        if file is not None:
            edit_payload["attachments"] = [file]
        elif files is not None:
            edit_payload["attachments"] = list(files)
        await interaction.edit_original_response(**edit_payload)

    async def _start_captcha(
        self,
        interaction: discord.Interaction,
        *,
        regenerate: bool,
        guild_id: Optional[int] = None,
        purpose: CaptchaPurpose = "server",
    ) -> None:
        target_guild_id = int(guild_id or (interaction.guild.id if interaction.guild else 0))
        ephemeral = interaction.guild is not None
        if not target_guild_id:
            await self._send_start_response(
                interaction,
                embed=ModEmbed.error("Guild Only", "Verification can only be used for a server."),
                ephemeral=ephemeral,
            )
            return

        # Discord requires an interaction acknowledgement within three seconds.
        # Reserve the private response before database, member and role work.
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)

        guild, member = await self._resolve_guild_member(interaction, guild_id=target_guild_id)
        if not guild or not member:
            await self._send_start_response(
                interaction,
                embed=ModEmbed.error("Not Found", "Could not resolve your server membership."),
                ephemeral=ephemeral,
            )
            return

        # Check cooldown
        on_cooldown, remaining = self._is_on_cooldown(guild.id, member.id)
        if on_cooldown and regenerate:
            await self._send_start_response(
                interaction,
                embed=ModEmbed.error("Cooldown", f"Please wait **{remaining}** seconds before generating a new captcha."),
                ephemeral=ephemeral,
            )
            return

        # Set cooldown
        self._set_cooldown(guild.id, member.id)

        if purpose == "server" and not await self._is_server_verification_enabled(guild.id):
            await self._send_start_response(
                interaction,
                embed=ModEmbed.error("Disabled", "Server verification is currently turned off."),
                ephemeral=ephemeral,
            )
            return

        unverified_role, verified_role = await self._get_roles(guild)
        if not unverified_role or not verified_role:
            await self._send_start_response(
                interaction,
                embed=ModEmbed.error(
                    "Not Configured",
                    "Verification roles are not set. Run `/setup` to create the baseline verification roles first.",
                ),
                ephemeral=ephemeral,
            )
            return

        if purpose == "server":
            if verified_role in member.roles and unverified_role not in member.roles:
                await self._send_start_response(
                    interaction,
                    embed=ModEmbed.success("Already Verified", "You already have access."),
                    ephemeral=ephemeral,
                )
                return

            if unverified_role not in member.roles:
                waiting_role_ready = await self._ensure_waiting_role(member, unverified_role)
                if not waiting_role_ready:
                    await self._send_start_response(
                        interaction,
                        embed=ModEmbed.error(
                            "Verification Role Unavailable",
                            "Docket could not assign your waiting role. A server admin must move "
                            "Docket's role above **Unverified**, then you can press **Verify me** again.",
                        ),
                        ephemeral=ephemeral,
                    )
                    return

            settings = await self._get_settings(guild.id)
            if settings.get("verification_method") == "website":
                website_url = await self._website_verification_url(guild.id, member.id)
                if not website_url:
                    await self._send_start_response(
                        interaction,
                        embed=ModEmbed.error(
                            "Website Verification Unavailable",
                            "The secure website checkpoint is not configured correctly. "
                            "Ask a server admin to check Docket's dashboard URL and verification secret.",
                        ),
                        ephemeral=ephemeral,
                    )
                    return
                view = WebsiteVerificationLayout(guild=guild, url=website_url)
                await self._send_start_response(
                    interaction,
                    view=view,
                    ephemeral=ephemeral,
                )
                return

        key = (guild.id, member.id, purpose)
        existing = self._pending.get(key)
        if regenerate or not existing or existing.expired():
            code = _generate_captcha_code()
            image_bytes = _generate_captcha_image(code)
            self._pending[key] = CaptchaEntry(
                code=code,
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=CAPTCHA_TTL_SECONDS),
                image_bytes=image_bytes,
            )
        else:
            code = existing.code
            image_bytes = existing.image_bytes

        logo_url, _ = get_guild_brand_assets(guild)

        # Build message with image or text fallback
        if image_bytes:
            embed = discord.Embed(
                title="🔐 Verification Captcha",
                description=(
                    "**Type the code shown in the image below.**\n\n"
                    "Press **Submit Captcha** to enter your answer."
                ),
                color=Config.COLOR_INFO,
            )
            embed.set_image(url="attachment://captcha.png")
            if logo_url:
                embed.set_thumbnail(url=logo_url)
            
            file = discord.File(io.BytesIO(image_bytes), filename="captcha.png")
            await self._send_start_response(
                interaction,
                embed=embed,
                file=file,
                view=CaptchaView(self, guild_id=guild.id, user_id=member.id, purpose=purpose),
                ephemeral=ephemeral,
            )
        else:
            # Text fallback
            embed = discord.Embed(
                title="🔐 Verification Captcha",
                description=(
                    "Type the code shown below.\n\n"
                    f"**Captcha:** `{code}`\n\n"
                    "Press **Submit Captcha** to enter it."
                ),
                color=Config.COLOR_INFO,
            )
            if logo_url:
                embed.set_thumbnail(url=logo_url)

            await self._send_start_response(
                interaction,
                embed=embed,
                view=CaptchaView(self, guild_id=guild.id, user_id=member.id, purpose=purpose),
                ephemeral=ephemeral,
            )

    async def _handle_captcha_submit(
        self,
        interaction: discord.Interaction,
        *,
        guild_id: int,
        user_id: int,
        purpose: CaptchaPurpose,
        attempt: str,
    ) -> None:
        if interaction.user.id != user_id:
            await interaction.response.send_message(
                embed=ModEmbed.error("Not For You", "Start your own verification from the panel."),
                ephemeral=interaction.guild is not None,
            )
            return

        guild, member = await self._resolve_guild_member(interaction, guild_id=guild_id)
        if not guild or not member:
            await interaction.response.send_message(
                embed=ModEmbed.error("Not Found", "Could not resolve your server membership."),
                ephemeral=True,
            )
            return

        ephemeral = interaction.guild is not None

        unverified_role, verified_role = await self._get_roles(guild)
        if not unverified_role or not verified_role:
            await interaction.response.send_message(
                embed=ModEmbed.error("Not Configured", "Run `/setup` first."),
                ephemeral=ephemeral,
            )
            return

        key = (guild_id, user_id, purpose)
        entry = self._pending.get(key)
        if not entry or entry.expired():
            await self._log_verify_event(
                guild,
                member=member,
                outcome="timeout",
                detail="Captcha expired before submission",
            )
            await interaction.response.send_message(
                embed=ModEmbed.error("Expired", "Your captcha expired. Click **New Captcha** and try again."),
                ephemeral=ephemeral,
            )
            return

        if attempt.strip().upper() != entry.code.strip().upper():
            await self._log_verify_event(
                guild,
                member=member,
                outcome="failed",
                detail=f"Incorrect captcha attempt: `{attempt}`",
            )
            await interaction.response.send_message(
                embed=ModEmbed.error("Incorrect", "Wrong captcha. Click **New Captcha** to generate another."),
                ephemeral=ephemeral,
            )
            return

        if purpose == "server":
            try:
                member = await self._apply_verified_roles(
                    member,
                    unverified_role,
                    verified_role,
                    reason="Verification captcha passed",
                )
            except Exception as e:
                await interaction.response.send_message(
                    embed=ModEmbed.error("Failed", f"Could not update your roles: {e}"),
                    ephemeral=ephemeral,
                )
                return
            finally:
                self._pending.pop(key, None)
        else:
            self._pending.pop(key, None)

        await self._log_verify_event(
            guild,
            member=member,
            outcome="verified",
            detail="Captcha passed" if purpose == "server" else "Voice captcha passed",
        )
        
        if purpose == "voice":
            await self._create_session(guild.id, member.id)
            await self._maybe_move_to_voice_target(guild, member)
        
        await interaction.response.send_message(
            embed=ModEmbed.success(
                "✅ Verified",
                "Verification complete. Welcome!"
                if purpose == "server"
                else "Voice verification complete. Moving you now...",
            ),
            ephemeral=ephemeral,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Commands
    # ─────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="verification",
        description="Turn server verification on or off and configure the verification roles",
    )
    @app_commands.describe(
        state="Enable or disable server verification",
        verified_role="Role granted after a member passes verification",
        unverified_role="Role assigned while a member is waiting to verify",
    )
    @is_admin()
    async def verification(
        self,
        interaction: discord.Interaction,
        state: Literal["on", "off"],
        verified_role: Optional[discord.Role] = None,
        unverified_role: Optional[discord.Role] = None,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                embed=ModEmbed.error("Guild Only", "Use this command in a server."),
                ephemeral=True,
            )
            return

        settings = await self._get_settings(interaction.guild.id)
        previous_unverified_role_id = int(settings.get("unverified_role", 0) or 0)
        if verified_role is not None:
            settings["verified_role"] = verified_role.id
        if unverified_role is not None:
            settings["unverified_role"] = unverified_role.id

        if state == "on" and (not settings.get("verified_role") or not settings.get("unverified_role")):
            await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Missing Roles",
                    "Set both the verified and unverified roles before turning verification on.",
                ),
                ephemeral=True,
            )
            return

        if state == "on":
            bot_member = interaction.guild.me
            resolved_verified = interaction.guild.get_role(int(settings.get("verified_role", 0) or 0))
            resolved_unverified = interaction.guild.get_role(int(settings.get("unverified_role", 0) or 0))
            if (
                bot_member is None
                or not bot_member.guild_permissions.manage_roles
                or (resolved_verified is not None and resolved_verified >= bot_member.top_role)
                or (resolved_unverified is not None and resolved_unverified >= bot_member.top_role)
            ):
                await interaction.response.send_message(
                    embed=ModEmbed.error(
                        "Role Hierarchy",
                        "I need `Manage Roles`, and both verification roles must stay below my top role.",
                    ),
                    ephemeral=True,
                )
                return

        settings["verification_enabled"] = state == "on"
        if state == "on":
            settings["autoroles_enabled"] = False
        gate_result = await self._save_verification_settings(
            interaction.guild,
            settings,
            previous_unverified_role_id=previous_unverified_role_id,
        )

        resolved_verified = interaction.guild.get_role(int(settings.get("verified_role", 0) or 0))
        resolved_unverified = interaction.guild.get_role(int(settings.get("unverified_role", 0) or 0))
        updated_channels = int(gate_result.get("updated", 0) or 0)
        errors = gate_result.get("errors", [])

        description = (
            f"Verification is now **{state.upper()}**.\n"
            f"Verified role: {resolved_verified.mention if resolved_verified else '`Not set`'}\n"
            f"Unverified role: {resolved_unverified.mention if resolved_unverified else '`Not set`'}\n"
            f"Channel access sync: `{updated_channels}` channel(s) updated"
        )
        if state == "on":
            description += "\nAuto Role was disabled because only one join access system can run at a time."
        if errors:
            description += f"\nPermission sync issues: `{len(errors)}`"

        await interaction.response.send_message(
            embed=ModEmbed.success("Verification Updated", description),
            ephemeral=True,
        )

    @app_commands.command(
        name="verifypanel",
        description="Post the verification panel to the verify channel",
    )
    @is_admin()
    async def verifypanel(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                embed=ModEmbed.error("Guild Only", "Use this command in a server."),
                ephemeral=True,
            )
            return

        settings = await self._get_settings(interaction.guild.id)
        verify_channel_id = settings.get("verify_channel")
        channel = (
            interaction.guild.get_channel(int(verify_channel_id)) if verify_channel_id else None
        )
        if not isinstance(channel, discord.abc.Messageable):
            channel = interaction.channel

        try:
            await apply_verification_gate(interaction.guild, settings)
            await channel.send(view=VerificationPanelLayout(self, guild=interaction.guild))
        except discord.Forbidden:
            # Self-healing: try to fix permissions if we are admin but locked out
            try:
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(
                        interaction.guild.me,
                        view_channel=True,
                        send_messages=True,
                        manage_channels=True,
                        manage_messages=True,
                        reason="ModBot Auto-Fix: verify channel permissions",
                    )
                    await channel.send(view=VerificationPanelLayout(self, guild=interaction.guild))
                else:
                    raise
            except Exception as e:
                await interaction.response.send_message(
                    embed=ModEmbed.error(
                        "Permission Denied",
                        f"I cannot post in {channel.mention}. Please ensure I have 'Manage Channel' and 'Send Messages' permissions there.\nError: {e}"
                    ),
                    ephemeral=True,
                )
                return
        except Exception as e:
            await interaction.response.send_message(
                embed=ModEmbed.error("Failed", f"Could not post panel: {e}"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=ModEmbed.success("Posted", f"Verification panel posted in {getattr(channel, 'mention', 'the channel')}."),
            ephemeral=True,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Admin Controls (called from voice.py)
    # ─────────────────────────────────────────────────────────────────────────

    async def show_settings(self, interaction: discord.Interaction) -> None:
        """Show current voice verification settings."""
        if not interaction.guild:
            return
        
        settings = await self.bot.db.get_settings(interaction.guild.id)
        enabled = settings.get("voice_verification_enabled", False)
        bypass_ids = settings.get("vc_verify_bypass_roles", [])
        session_ttl = settings.get("vc_verify_session_ttl", DEFAULT_SESSION_TTL_SECONDS)
        waiting_id = settings.get("waiting_verify_voice_channel")
        
        waiting_channel = interaction.guild.get_channel(int(waiting_id)) if waiting_id else None
        
        # Get bypass role names
        bypass_roles = []
        for rid in bypass_ids:
            role = interaction.guild.get_role(rid)
            if role:
                bypass_roles.append(role.mention)
        
        embed = discord.Embed(
            title="🔊 Voice Verification Settings",
            color=Config.COLOR_INFO,
        )
        embed.add_field(name="Status", value="✅ Enabled" if enabled else "❌ Disabled", inline=True)
        embed.add_field(name="Session TTL", value=f"{session_ttl // 60} minutes", inline=True)
        embed.add_field(name="Waiting Channel", value=waiting_channel.mention if waiting_channel else "Not Set", inline=True)
        embed.add_field(
            name="Bypass Roles",
            value=", ".join(bypass_roles) if bypass_roles else "None",
            inline=False,
        )
        embed.add_field(
            name="Image Captcha",
            value="✅ Available (Pillow)" if PILLOW_AVAILABLE else "❌ Fallback to Text",
            inline=True,
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def add_bypass_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        """Add a role to the bypass list."""
        if not interaction.guild:
            return
        
        settings = await self.bot.db.get_settings(interaction.guild.id)
        bypass_ids = settings.get("vc_verify_bypass_roles", [])
        if not isinstance(bypass_ids, list):
            bypass_ids = []
        
        if role.id in bypass_ids:
            await interaction.response.send_message(
                embed=ModEmbed.error("Already Exists", f"{role.mention} is already a bypass role."),
                ephemeral=True,
            )
            return
        
        bypass_ids.append(role.id)
        settings["vc_verify_bypass_roles"] = bypass_ids
        await self.bot.db.update_settings(interaction.guild.id, settings)
        
        await interaction.response.send_message(
            embed=ModEmbed.success("Bypass Role Added", f"{role.mention} can now skip voice verification."),
            ephemeral=True,
        )

    async def remove_bypass_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        """Remove a role from the bypass list."""
        if not interaction.guild:
            return
        
        settings = await self.bot.db.get_settings(interaction.guild.id)
        bypass_ids = settings.get("vc_verify_bypass_roles", [])
        if not isinstance(bypass_ids, list):
            bypass_ids = []
        
        if role.id not in bypass_ids:
            await interaction.response.send_message(
                embed=ModEmbed.error("Not Found", f"{role.mention} is not a bypass role."),
                ephemeral=True,
            )
            return
        
        bypass_ids.remove(role.id)
        settings["vc_verify_bypass_roles"] = bypass_ids
        await self.bot.db.update_settings(interaction.guild.id, settings)
        
        await interaction.response.send_message(
            embed=ModEmbed.success("Bypass Role Removed", f"{role.mention} must now complete voice verification."),
            ephemeral=True,
        )

    async def set_session_timeout(self, interaction: discord.Interaction, minutes: int) -> None:
        """Set the session TTL in minutes."""
        if not interaction.guild:
            return
        
        if minutes < 1 or minutes > 1440:
            await interaction.response.send_message(
                embed=ModEmbed.error("Invalid Value", "Session timeout must be between 1 and 1440 minutes (24 hours)."),
                ephemeral=True,
            )
            return
        
        settings = await self.bot.db.get_settings(interaction.guild.id)
        settings["vc_verify_session_ttl"] = minutes * 60
        await self.bot.db.update_settings(interaction.guild.id, settings)
        
        await interaction.response.send_message(
            embed=ModEmbed.success("Session Timeout Updated", f"Voice verification sessions now last **{minutes} minutes**."),
            ephemeral=True,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Event Listeners
    # ─────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        try:
            if member.bot:
                return

            if not await self._is_server_verification_enabled(member.guild.id):
                return

            unverified_role, _ = await self._get_roles(member.guild)
            if not unverified_role:
                return

            await member.add_roles(unverified_role, reason="New member - verification required")
        except Exception:
            return

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        keys = [k for k in self._pending.keys() if k[0] == guild.id]
        for k in keys:
            self._pending.pop(k, None)
        voice_keys = [k for k in self._voice_targets.keys() if k[0] == guild.id]
        for k in voice_keys:
            self._voice_targets.pop(k, None)
        allow_keys = [k for k in self._voice_allow_once.keys() if k[0] == guild.id]
        for k in allow_keys:
            self._voice_allow_once.pop(k, None)
        session_keys = [k for k in self._voice_sessions.keys() if k[0] == guild.id]
        for k in session_keys:
            self._voice_sessions.pop(k, None)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        async def _cleanup_loop() -> None:
            await self.bot.wait_until_ready()
            while not self.bot.is_closed():
                try:
                    now = datetime.now(timezone.utc)
                    # Clean expired captchas
                    expired = [k for k, v in self._pending.items() if v.expires_at <= now]
                    for k in expired:
                        self._pending.pop(k, None)
                    # Clean expired sessions
                    expired_sessions = [k for k, v in self._voice_sessions.items() if v.expired()]
                    for k in expired_sessions:
                        self._voice_sessions.pop(k, None)
                    # Clean old cooldowns (older than 5 min)
                    old_cooldowns = [k for k, v in self._cooldowns.items() if (now - v).total_seconds() > 300]
                    for k in old_cooldowns:
                        self._cooldowns.pop(k, None)
                    await asyncio.sleep(60)
                except Exception:
                    await asyncio.sleep(60)

        if not getattr(self, "_cleanup_task_started", False):
            setattr(self, "_cleanup_task_started", True)
            self.bot.loop.create_task(_cleanup_loop())
        try:
            await sync_status_emojis_to_application(self.bot)
        except Exception as exc:
            logger.warning("Could not prepare Docket emojis for verification panels: %s", exc)
        await self._refresh_configured_panels()

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        try:
            if member.bot or not member.guild:
                return

            key = (member.guild.id, member.id)

            # User left voice entirely - clear allow_once but keep session
            if after.channel is None:
                self._voice_targets.pop(key, None)
                self._voice_allow_once.pop(key, None)
                return

            if not await self._is_voice_verification_enabled(member.guild.id):
                return

            waiting = await self._get_waiting_voice_channel(member.guild)
            if not waiting:
                return

            # Only act on actual channel changes (join or move)
            if before.channel and before.channel.id == after.channel.id:
                return

            # Skip once when we just moved them into the target after passing captcha
            allowed_target = self._voice_allow_once.get(key)
            if allowed_target and int(allowed_target) == int(after.channel.id):
                self._voice_allow_once.pop(key, None)
                return

            # If they enter the waiting room manually, allow it and DM them the prompt
            if after.channel.id == waiting.id:
                if before.channel is None:
                    await self._send_voice_verify_dm(guild=member.guild, member=member)
                return

            # Check bypass roles
            bypass_role_ids = await self._get_bypass_roles(member.guild.id)
            if self._has_bypass_role(member, bypass_role_ids):
                await self._log_verify_event(
                    member.guild,
                    member=member,
                    outcome="bypass",
                    detail="User has bypass role",
                    channel_name=after.channel.name,
                )
                return

            # Check if user has a valid session (verified recently)
            if self._has_valid_session(member.guild.id, member.id):
                return

            # User needs verification - store target and move to waiting
            target = after.channel
            self._voice_targets[key] = target.id
            try:
                await member.move_to(waiting, reason="Voice verification required")
            except Exception:
                return
            await self._send_voice_verify_dm(guild=member.guild, member=member)
        except Exception:
            return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Verification(bot))
