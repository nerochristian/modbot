"""
Verification system:
- /verifypanel posts a verification panel
- Users solve a simple per-user captcha to receive the Verified role
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal

import discord
from discord import app_commands
from discord.ext import commands

from config import Config
from utils.checks import is_admin
from utils.embeds import ModEmbed
from utils.components_v2 import branded_panel_container


CAPTCHA_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CAPTCHA_LENGTH = 5
CAPTCHA_TTL_SECONDS = 5 * 60
CaptchaPurpose = Literal["server", "voice"]


@dataclass(frozen=True)
class CaptchaEntry:
    code: str
    expires_at: datetime

    def expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


def _generate_captcha() -> str:
    return "".join(secrets.choice(CAPTCHA_ALPHABET) for _ in range(CAPTCHA_LENGTH))


def _brand_assets(guild: Optional[discord.Guild]) -> tuple[Optional[str], Optional[str]]:
    logo_url = (getattr(Config, "SERVER_LOGO_URL", "") or "").strip() or None
    banner_url = (getattr(Config, "SERVER_BANNER_URL", "") or "").strip() or None

    if not logo_url and guild and getattr(guild, "icon", None):
        try:
            logo_url = str(guild.icon.url)
        except Exception:
            logo_url = None

    if not banner_url and guild and getattr(guild, "banner", None):
        try:
            banner_url = str(guild.banner.url)
        except Exception:
            banner_url = None

    return logo_url, banner_url


class CaptchaModal(discord.ui.Modal, title="Verification Captcha"):
    captcha = discord.ui.TextInput(
        label="Enter the captcha",
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

        logo_url, banner_url = _brand_assets(guild)
        container = branded_panel_container(
            title="Server Verification",
            description=(
                "To access the server you must verify.\n\n"
                "**How it works**\n"
                "1) Press **Start Verification**\n"
                "2) Solve the simple captcha\n"
                "3) Receive the **verified** role\n\n"
                "Need help? Press **Tutorial**."
            ),
            banner_url=banner_url,
            logo_url=logo_url,
            accent_color=getattr(Config, "COLOR_BRAND", 0x5865F2),
            banner_separated=True,
        )

        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

        start_button = discord.ui.Button(
            label="Start Verification",
            style=discord.ButtonStyle.success,
            custom_id="verification:start",
        )

        async def _start(interaction: discord.Interaction) -> None:
            await self._cog._start_captcha(interaction, regenerate=True, purpose="server")

        start_button.callback = _start

        tutorial_button = discord.ui.Button(
            label="Tutorial",
            style=discord.ButtonStyle.secondary,
            custom_id="verification:tutorial",
        )

        async def _tutorial(interaction: discord.Interaction) -> None:
            await self._cog._send_tutorial(interaction)

        tutorial_button.callback = _tutorial

        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay("**Start Verification**\nBegin the captcha verification."),
                accessory=start_button,
            )
        )
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay("**Tutorial**\nWatch a short guide (ephemeral)."),
                accessory=tutorial_button,
            )
        )

        self.add_item(container)


class Verification(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._pending: dict[tuple[int, int, CaptchaPurpose], CaptchaEntry] = {}
        self._voice_targets: dict[tuple[int, int], int] = {}
        self._voice_allow_once: dict[tuple[int, int], int] = {}
        # Tracks whether the user has passed the voice captcha in their current voice session.
        # Cleared when they disconnect from voice.
        self._voice_session_verified: set[tuple[int, int]] = set()
        # Persistent components (so old panels keep working after restarts).
        self.bot.add_view(VerificationPanelLayout(self))

    async def _get_roles(
        self, guild: discord.Guild
    ) -> tuple[Optional[discord.Role], Optional[discord.Role]]:
        settings = await self.bot.db.get_settings(guild.id)
        unverified_id = settings.get("unverified_role")
        verified_id = settings.get("verified_role")
        unverified = guild.get_role(unverified_id) if unverified_id else None
        verified = guild.get_role(verified_id) if verified_id else None
        return unverified, verified

    async def _get_verify_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        try:
            settings = await self.bot.db.get_settings(guild.id)
            cid = settings.get("verify_log_channel")
            if not cid:
                return None
            ch = guild.get_channel(int(cid))
            return ch if isinstance(ch, discord.TextChannel) else None
        except Exception:
            return None

    async def _log_verify_event(
        self,
        guild: discord.Guild,
        *,
        member: discord.Member,
        outcome: str,
        detail: str,
    ) -> None:
        ch = await self._get_verify_log_channel(guild)
        if not ch:
            return
        try:
            embed = discord.Embed(
                title="Verification Log",
                description=f"**Outcome:** {outcome}\n**User:** {member.mention} (`{member.id}`)\n**Detail:** {detail}",
                color=Config.COLOR_INFO,
            )
            await ch.send(embed=embed)
        except Exception:
            return

    async def _send_tutorial(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Verification Tutorial",
            description=(
                "Watch the tutorial video and then come back to verify.\n\n"
                f"**Video (placeholder):** {getattr(Config, 'VERIFY_TUTORIAL_VIDEO_URL', 'https://example.com/')}\n\n"
                "If the video link is not set yet, try again later or contact staff."
            ),
            color=Config.COLOR_INFO,
        )
        await interaction.response.send_message(embed=embed, ephemeral=interaction.guild is not None)

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
            # Allow this specific target move without re-triggering gating.
            self._voice_allow_once[key] = int(target_id)
            self._voice_session_verified.add(key)
            await member.move_to(target, reason="Voice verification complete")
            self._voice_targets.pop(key, None)
        except Exception:
            return

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

    async def _send_voice_verify_dm(self, *, guild: discord.Guild, member: discord.Member) -> None:
        layout = discord.ui.LayoutView(timeout=15 * 60)

        logo_url, banner_url = _brand_assets(guild)
        container = branded_panel_container(
            title="Voice Verification Required",
            description=(
                f"You tried to join a voice channel in **{guild.name}**.\n\n"
                "Complete verification to be moved into the voice channel you selected."
            ),
            banner_url=banner_url,
            logo_url=logo_url,
            accent_color=getattr(Config, "COLOR_BRAND", 0x5865F2),
            banner_separated=True,
        )

        start_button = discord.ui.Button(
            label="Start Verification",
            style=discord.ButtonStyle.success,
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
                discord.ui.TextDisplay("**Start Verification**\nSolve the captcha to join voice."),
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

    async def _start_captcha(
        self,
        interaction: discord.Interaction,
        *,
        regenerate: bool,
        guild_id: Optional[int] = None,
        purpose: CaptchaPurpose = "server",
    ) -> None:
        target_guild_id = int(guild_id or (interaction.guild.id if interaction.guild else 0))
        if not target_guild_id:
            await interaction.response.send_message(
                embed=ModEmbed.error("Guild Only", "Verification can only be used for a server."),
                ephemeral=interaction.guild is not None,
            )
            return

        guild, member = await self._resolve_guild_member(interaction, guild_id=target_guild_id)
        if not guild or not member:
            await interaction.response.send_message(
                embed=ModEmbed.error("Not Found", "Could not resolve your server membership."),
                ephemeral=interaction.guild is not None,
            )
            return

        ephemeral = interaction.guild is not None

        unverified_role, verified_role = await self._get_roles(guild)
        if not unverified_role or not verified_role:
            await interaction.response.send_message(
                embed=ModEmbed.error(
                    "Not Configured",
                    "Verification roles are not set. Run `/setup` first.",
                ),
                ephemeral=ephemeral,
            )
            return

        if purpose == "server":
            if verified_role in member.roles and unverified_role not in member.roles:
                await interaction.response.send_message(
                    embed=ModEmbed.success("Already Verified", "You already have access."),
                    ephemeral=ephemeral,
                )
                return

            if unverified_role not in member.roles:
                await interaction.response.send_message(
                    embed=ModEmbed.error(
                        "No Unverified Role",
                        "You don't have the `unverified` role. Ask a staff member to run `/setup` again.",
                    ),
                    ephemeral=ephemeral,
                )
                return

        key = (guild.id, member.id, purpose)
        existing = self._pending.get(key)
        if regenerate or not existing or existing.expired():
            code = _generate_captcha()
            self._pending[key] = CaptchaEntry(
                code=code,
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=CAPTCHA_TTL_SECONDS),
            )
        else:
            code = existing.code

        embed = discord.Embed(
            title="Verification Captcha",
            description=(
                "Type the code shown below.\n\n"
                f"**Captcha:** `{code}`\n\n"
                "Press **Submit Captcha** to enter it."
            ),
            color=Config.COLOR_INFO,
        )
        logo_url, _ = _brand_assets(guild)
        if logo_url:
            embed.set_thumbnail(url=logo_url)

        await interaction.response.send_message(
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
            await interaction.response.send_message(
                embed=ModEmbed.error("Expired", "Your captcha expired. Click **New Captcha** and try again."),
                ephemeral=ephemeral,
            )
            return

        if attempt.strip().upper() != entry.code.strip().upper():
            await interaction.response.send_message(
                embed=ModEmbed.error("Incorrect", "Wrong captcha. Click **New Captcha** to generate another."),
                ephemeral=ephemeral,
            )
            return

        if purpose == "server":
            try:
                await member.add_roles(verified_role, reason="Verification captcha passed")
                if unverified_role in member.roles:
                    await member.remove_roles(unverified_role, reason="Verification complete")
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
            self._voice_session_verified.add((guild.id, member.id))
            await self._maybe_move_to_voice_target(guild, member)
        await interaction.response.send_message(
            embed=ModEmbed.success(
                "Verified",
                "Verification complete. Welcome!"
                if purpose == "server"
                else "Voice verification complete. Moving you now...",
            ),
            ephemeral=ephemeral,
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

        settings = await self.bot.db.get_settings(interaction.guild.id)
        verify_channel_id = settings.get("verify_channel")
        channel = (
            interaction.guild.get_channel(int(verify_channel_id)) if verify_channel_id else None
        )
        if not isinstance(channel, discord.abc.Messageable):
            channel = interaction.channel

        try:
            # Send a Components v2 panel so buttons appear inside the card.
            await channel.send(view=VerificationPanelLayout(self, guild=interaction.guild))
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

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        try:
            if member.bot:
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
        session_keys = [k for k in self._voice_session_verified if k[0] == guild.id]
        for k in session_keys:
            self._voice_session_verified.discard(k)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        async def _cleanup_loop() -> None:
            await self.bot.wait_until_ready()
            while not self.bot.is_closed():
                try:
                    now = datetime.now(timezone.utc)
                    expired = [k for k, v in self._pending.items() if v.expires_at <= now]
                    for k in expired:
                        self._pending.pop(k, None)
                    await asyncio.sleep(60)
                except Exception:
                    await asyncio.sleep(60)

        if not getattr(self, "_cleanup_task_started", False):
            setattr(self, "_cleanup_task_started", True)
            self.bot.loop.create_task(_cleanup_loop())

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
            if after.channel is None:
                # cleanup when leaving voice
                self._voice_targets.pop(key, None)
                self._voice_allow_once.pop(key, None)
                self._voice_session_verified.discard(key)
                return

            waiting = await self._get_waiting_voice_channel(member.guild)
            if not waiting:
                return

            # Only act on actual channel changes (join or move).
            if before.channel and before.channel.id == after.channel.id:
                return

            # Skip once when we just moved them into the target after passing captcha.
            allowed_target = self._voice_allow_once.get(key)
            if allowed_target and int(allowed_target) == int(after.channel.id):
                self._voice_allow_once.pop(key, None)
                return

            # If they enter the waiting room manually, allow it and DM them the prompt.
            if after.channel.id == waiting.id:
                if before.channel is None:
                    await self._send_voice_verify_dm(guild=member.guild, member=member)
                return

            # If they already passed voice captcha in this voice session and are just switching VCs,
            # don't require re-verification.
            if key in self._voice_session_verified:
                return

            # Move to waiting and DM verification.
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
