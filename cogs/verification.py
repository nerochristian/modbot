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
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import Config
from utils.checks import get_owner_ids, is_admin, is_bot_owner_id
from utils.embeds import ModEmbed
from utils.components_v2 import branded_panel_container


CAPTCHA_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CAPTCHA_LENGTH = 5
CAPTCHA_TTL_SECONDS = 5 * 60


@dataclass(frozen=True)
class CaptchaEntry:
    code: str
    expires_at: datetime

    def expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


def _generate_captcha() -> str:
    return "".join(secrets.choice(CAPTCHA_ALPHABET) for _ in range(CAPTCHA_LENGTH))


class CaptchaModal(discord.ui.Modal, title="Verification Captcha"):
    captcha = discord.ui.TextInput(
        label="Enter the captcha",
        placeholder="Example: A1B2C",
        min_length=CAPTCHA_LENGTH,
        max_length=CAPTCHA_LENGTH,
        required=True,
    )

    def __init__(self, cog: "Verification", *, guild_id: int, user_id: int):
        super().__init__(timeout=60)
        self._cog = cog
        self._guild_id = guild_id
        self._user_id = user_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._cog._handle_captcha_submit(
            interaction,
            guild_id=self._guild_id,
            user_id=self._user_id,
            attempt=str(self.captcha.value or "").strip(),
        )


class CaptchaView(discord.ui.View):
    def __init__(self, cog: "Verification", *, guild_id: int, user_id: int):
        super().__init__(timeout=180)
        self._cog = cog
        self._guild_id = guild_id
        self._user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self._user_id:
            return True
        try:
            await interaction.response.send_message(
                embed=ModEmbed.error("Not For You", "Start your own verification from the panel."),
                ephemeral=True,
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
            CaptchaModal(self._cog, guild_id=self._guild_id, user_id=self._user_id)
        )

    @discord.ui.button(
        label="New Captcha",
        style=discord.ButtonStyle.secondary,
        custom_id="verification:captcha_new",
    )
    async def new(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._cog._start_captcha(interaction, regenerate=True, guild_id=self._guild_id)


class VerificationPanelLayout(discord.ui.LayoutView):
    def __init__(self, cog: "Verification"):
        super().__init__(timeout=None)
        self._cog = cog

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
            banner_url=getattr(Config, "SERVER_BANNER_URL", None),
            logo_url=getattr(Config, "SERVER_LOGO_URL", None),
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
            await self._cog._start_captcha(interaction, regenerate=True)

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
        self._pending: dict[tuple[int, int], CaptchaEntry] = {}
        self._voice_targets: dict[tuple[int, int], int] = {}
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
        await interaction.response.send_message(embed=embed, ephemeral=True)

    def _bypass_ids(self, guild: discord.Guild) -> set[int]:
        out = set(get_owner_ids())
        if guild.owner_id:
            out.add(int(guild.owner_id))
        return out

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

    async def _send_voice_verify_dm(self, *, guild: discord.Guild, member: discord.Member, target_id: int) -> None:
        layout = discord.ui.LayoutView(timeout=15 * 60)

        container = branded_panel_container(
            title="Voice Verification Required",
            description=(
                f"You tried to join a voice channel in **{guild.name}**.\n\n"
                "Complete verification to be moved into the voice channel you selected."
            ),
            banner_url=getattr(Config, "SERVER_BANNER_URL", None),
            logo_url=getattr(Config, "SERVER_LOGO_URL", None),
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
                    ephemeral=True,
                )
                return
            await self._start_captcha(interaction, regenerate=True, guild_id=guild.id)

        start_button.callback = _start

        tutorial_button = discord.ui.Button(
            label="Tutorial",
            style=discord.ButtonStyle.secondary,
        )

        async def _tutorial(interaction: discord.Interaction) -> None:
            if interaction.user.id != member.id:
                await interaction.response.send_message(
                    embed=ModEmbed.error("Not For You", "This verification is for someone else."),
                    ephemeral=True,
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
    ) -> None:
        target_guild_id = int(guild_id or (interaction.guild.id if interaction.guild else 0))
        if not target_guild_id:
            await interaction.response.send_message(
                embed=ModEmbed.error("Guild Only", "Verification can only be used for a server."),
                ephemeral=True,
            )
            return

        guild, member = await self._resolve_guild_member(interaction, guild_id=target_guild_id)
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
                embed=ModEmbed.error(
                    "Not Configured",
                    "Verification roles are not set. Run `/setup` first.",
                ),
                ephemeral=ephemeral,
            )
            return

        if is_bot_owner_id(member.id) or member.id in self._bypass_ids(guild):
            try:
                if unverified_role in member.roles:
                    await member.remove_roles(unverified_role, reason="Verification bypass")
                if verified_role not in member.roles:
                    await member.add_roles(verified_role, reason="Verification bypass")
                await interaction.response.send_message(
                    embed=ModEmbed.success("Bypassed", "You are bypassed and have been verified."),
                    ephemeral=ephemeral,
                )
                await self._log_verify_event(
                    guild,
                    member=member,
                    outcome="bypassed",
                    detail="Owner/server-owner bypass",
                )
            except Exception as e:
                await interaction.response.send_message(
                    embed=ModEmbed.error("Failed", f"Could not apply roles: {e}"),
                    ephemeral=ephemeral,
                )
            return

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

        key = (guild.id, member.id)
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
        if getattr(Config, "SERVER_LOGO_URL", None):
            embed.set_thumbnail(url=Config.SERVER_LOGO_URL)

        await interaction.response.send_message(
            embed=embed,
            view=CaptchaView(self, guild_id=guild.id, user_id=member.id),
            ephemeral=ephemeral,
        )

    async def _handle_captcha_submit(
        self,
        interaction: discord.Interaction,
        *,
        guild_id: int,
        user_id: int,
        attempt: str,
    ) -> None:
        if interaction.user.id != user_id:
            await interaction.response.send_message(
                embed=ModEmbed.error("Not For You", "Start your own verification from the panel."),
                ephemeral=True,
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

        key = (guild_id, user_id)
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

        await self._log_verify_event(
            guild,
            member=member,
            outcome="verified",
            detail="Captcha passed",
        )
        await self._maybe_move_to_voice_target(guild, member)
        await interaction.response.send_message(
            embed=ModEmbed.success("Verified", "Verification complete. Welcome!"),
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
            await channel.send(view=VerificationPanelLayout(self))
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
            if is_bot_owner_id(member.id) or member.id in self._bypass_ids(member.guild):
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
            if after.channel is None:
                # cleanup when leaving voice
                self._voice_targets.pop((member.guild.id, member.id), None)
                return

            waiting = await self._get_waiting_voice_channel(member.guild)
            if not waiting:
                return

            if after.channel.id == waiting.id:
                return

            unverified_role, verified_role = await self._get_roles(member.guild)
            if not unverified_role or not verified_role:
                return

            if is_bot_owner_id(member.id) or member.id in self._bypass_ids(member.guild):
                return

            # Only gate unverified users.
            if verified_role in member.roles and unverified_role not in member.roles:
                return

            if unverified_role not in member.roles:
                return

            # Move to waiting and DM verification.
            target = after.channel
            self._voice_targets[(member.guild.id, member.id)] = target.id
            try:
                await member.move_to(waiting, reason="Voice verification required")
            except Exception:
                return
            await self._send_voice_verify_dm(guild=member.guild, member=member, target_id=target.id)
        except Exception:
            return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Verification(bot))
