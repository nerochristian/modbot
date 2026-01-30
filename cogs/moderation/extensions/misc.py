import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import re
import asyncio
import aiohttp
from typing import Optional
from urllib.parse import urlparse

from utils.embeds import ModEmbed, Colors
from utils.checks import is_mod, is_admin, is_owner_only
from utils.welcome_card import WelcomeCardOptions, build_welcome_card_file
from config import Config
from .ui import EmojiApprovalView, AddEmojiTutorialView, _fetch_addemoji_tutorial_gif_file, ADD_EMOJI_TUTORIAL_GIF_FILENAME, ADD_EMOJI_TUTORIAL_GIF_URL, EMOJI_COMMAND_CHANNEL_ID

class MiscCommands:
    # ==================== EMOJI/STICKER MANAGEMENT ====================

    @staticmethod
    def _sanitize_emoji_name(raw: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", (raw or "").strip())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        return cleaned[:32]

    @staticmethod
    def _normalize_asset_url(raw: str) -> str:
        cleaned = (raw or "").strip()
        if cleaned.startswith("<") and cleaned.endswith(">"):
            cleaned = cleaned[1:-1].strip()
        if cleaned.startswith("`") and cleaned.endswith("`"):
            cleaned = cleaned[1:-1].strip()
        return cleaned

    @staticmethod
    def _validate_asset_url(url: str) -> Optional[str]:
        """Return an error string if invalid; otherwise None."""
        if not url:
            return "URL is required."
        if any(ch.isspace() for ch in url):
            return "URL must not contain spaces."
        if len(url) > 2048:
            return "URL is too long."

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return "URL must start with http:// or https:// and be a valid link."

        if len(url) > 1024:
            return "URL is too long for the log embed. Use a shorter direct image link."

        return None

    async def _create_emoji_from_url(
        self,
        *,
        guild: discord.Guild,
        name: str,
        url: str,
        reason: str,
    ) -> discord.Emoji:
        url = self._normalize_asset_url(url)
        if not (url.startswith('http://') or url.startswith('https://')):
            raise ValueError('invalid_url')

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError('fetch_failed')
                emoji_bytes = await response.read()

        if len(emoji_bytes) > 256 * 1024:
            raise ValueError('file_too_large')

        return await guild.create_custom_emoji(
            name=name,
            image=emoji_bytes,
            reason=reason,
        )

    async def _get_emoji_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        try:
            settings = await self.bot.db.get_settings(guild.id)
        except Exception:
            settings = {}
        channel_id = settings.get('emoji_log_channel') or settings.get('automod_log_channel')
        if channel_id:
            ch = guild.get_channel(int(channel_id))
            if isinstance(ch, discord.TextChannel):
                return ch
        return None

    @commands.group(name="emoji", invoke_without_command=True)
    async def emoji_group(self, ctx: commands.Context):
        """
        Emoji tools (add, steal, tutorial)
        Usage: 
          ,emoji add <name> <url>
          ,emoji steal <emojis>
          ,emoji tutorial
        """
        await self.emoji_tutorial(ctx)

    @emoji_group.command(name="tutorial")
    async def emoji_tutorial(self, ctx: commands.Context):
        """Show emoji submission tutorial"""
        steps = (
            "This server uses **admin approval** for new emojis.\n\n"
            "**Step 1: Get a direct image URL**\n"
            "• Use a direct link to a `.png`, `.jpg`, or `.gif`.\n"
            "• If you're using a Discord attachment, copy the attachment URL.\n\n"
            "**Step 2: Pick a name**\n"
            "• Only letters, numbers, and underscores.\n"
            "• Example: `cool_cat`, `pepe_laugh`.\n\n"
            "**Step 3: Submit the request**\n"
            "• Run: `,emoji add <name> <url>`\n\n"
            "**Step 4: Wait for approval**\n"
            "• An admin will approve/reject in `#emoji-logs`.\n\n"
        )
        embed = discord.Embed(
            title="Emoji Tutorial",
            description=steps,
            color=Colors.EMBED,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Tip: The bot will reject files over ~256KB.")
        
        try:
             gif = await _fetch_addemoji_tutorial_gif_file()
        except:
             gif = None

        if gif:
             embed.set_image(url=f"attachment://{ADD_EMOJI_TUTORIAL_GIF_FILENAME}")
             await ctx.reply(embed=embed, file=gif)
        else:
             embed.set_image(url=ADD_EMOJI_TUTORIAL_GIF_URL)
             await ctx.reply(embed=embed)

    @emoji_group.command(name="add")
    async def emoji_add(self, ctx: commands.Context, name: str, url: str):
        """Request to add a new emoji"""
        settings = await self.bot.db.get_settings(ctx.guild.id)
        restricted = settings.get("emoji_command_channel") or settings.get("emoji_command_channel_id") or EMOJI_COMMAND_CHANNEL_ID
        if restricted and ctx.channel.id != int(restricted):
             return await ctx.reply(embed=ModEmbed.error("Wrong Channel", f"Use emoji commands in <#{int(restricted)}>."));
        
        url = self._normalize_asset_url(url)
        url_error = self._validate_asset_url(url)
        if url_error:
            return await ctx.reply(embed=ModEmbed.error("Invalid URL", f"{url_error}\n\nExample: `https://.../image.png`"))
            
        emoji_name = self._sanitize_emoji_name(name)
        if len(emoji_name) < 2:
            return await ctx.reply(embed=ModEmbed.error('Invalid Name', 'Names must be 2+ chars.'))
            
        if any(e.name == emoji_name for e in ctx.guild.emojis):
            return await ctx.reply(embed=ModEmbed.error('Exists', f'`:{emoji_name}:` exists.'))
            
        log_channel = await self._get_emoji_log_channel(ctx.guild)
        if not log_channel:
             return await ctx.reply(embed=ModEmbed.error("Not Configured", "Ask admin to setup `#emoji-logs`."))
             
        view = EmojiApprovalView(self, requester_id=ctx.author.id, emoji_name=emoji_name, emoji_url=url)
        try:
            msg = await log_channel.send(view=view)
            view.message = msg
            await ctx.reply(embed=ModEmbed.success('Submitted', f'Sent to {log_channel.mention}.'))
        except Exception as e:
            await ctx.reply(embed=ModEmbed.error("Failed", f"Error: {e}"))

    @emoji_group.command(name="steal")
    async def emoji_steal(self, ctx: commands.Context, *, emojis: str):
        """Steal emojis"""
        matches = list(re.finditer(r"<(a?):([A-Za-z0-9_]+):(\d+)>", emojis))
        if not matches:
             return await ctx.reply(embed=ModEmbed.error("No Emojis", "Paste custom emojis."))
             
        log_channel = await self._get_emoji_log_channel(ctx.guild)
        if not log_channel:
             return await ctx.reply(embed=ModEmbed.error("Not Configured", "Ask admin to setup `#emoji-logs`."))

        submitted = []
        skipped = []
        failed = []
        existing_names = {e.name for e in ctx.guild.emojis}
        seen_names = set()
        
        for m in matches[:25]:
            try:
                animated = bool(m.group(1))
                ename = m.group(2)
                eid = m.group(3)
                dname = self._sanitize_emoji_name(ename)
                eurl = f"https://cdn.discordapp.com/emojis/{eid}.{'gif' if animated else 'png'}"
                
                if dname in existing_names or dname in seen_names:
                    skipped.append(ename)
                    continue
                seen_names.add(dname)
                
                view = EmojiApprovalView(self, requester_id=ctx.author.id, emoji_name=dname, emoji_url=eurl)
                msg = await log_channel.send(view=view)
                view.message = msg
                submitted.append(f"`:{dname}:`")
            except Exception as e:
                failed.append(f"{ename} ({type(e).__name__})")
                
        msg = ""
        if submitted: msg += f"Submitted {len(submitted)} to {log_channel.mention}."
        if skipped: msg += f"\nSkipped: {', '.join(skipped[:10])}"
        if failed: msg += f"\nFailed: {', '.join(failed[:10])}"
        
        await ctx.reply(embed=ModEmbed.success("Steal Report", msg or "Nothing processed."))

    # ==================== WELCOME SYSTEM ====================

    async def _send_welcome_message(
        self,
        *,
        member: discord.Member,
        channel: discord.abc.Messageable,
    ) -> None:
        settings = await self.bot.db.get_settings(member.guild.id)
        server_name = (settings.get("welcome_server_name") or getattr(Config, "WELCOME_SERVER_NAME", "") or "").strip()
        if not server_name:
            server_name = member.guild.name

        system_name = (settings.get("welcome_system_name") or getattr(Config, "WELCOME_SYSTEM_NAME", "Welcome System") or "").strip()
        if not system_name:
            system_name = "Welcome System"
        accent = getattr(Config, "EMBED_ACCENT_COLOR", getattr(Config, "COLOR_EMBED", 0x5865F2))
        card_accent = getattr(Config, "WELCOME_CARD_ACCENT_COLOR", accent)

        joined_at = member.joined_at or datetime.now(timezone.utc)
        try:
            ts = int(joined_at.timestamp())
        except Exception:
            ts = int(datetime.now(timezone.utc).timestamp())

        options = WelcomeCardOptions(
            accent_color=card_accent,
            server_name=f"{system_name} - Moderation",
        )

        card_file = await build_welcome_card_file(
            self.bot,
            member,
            filename=f"welcome_{member.id}.png",
            options=options,
        )

        view = discord.ui.LayoutView(timeout=60)
        view.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"# {system_name} - {server_name}"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(f"# \N{INVERTED EXCLAMATION MARK}Welcome to {server_name}!"),
                discord.ui.TextDisplay(
                    f"| User: {member.mention}\n"
                    f"| Joined On: <t:{ts}:D> at <t:{ts}:t>"
                ),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.MediaGallery(
                    discord.MediaGalleryItem(f"attachment://{card_file.filename}")
                ),
                accent_color=accent,
            )
        )

        await channel.send(view=view, file=card_file)

    # Slash command - registered dynamically in __init__.py
    async def testwelcome(
        self,
        interaction: discord.Interaction,
        member: Optional[discord.Member] = None,
        channel: Optional[discord.TextChannel] = None,
    ):
        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Available", "This command can only be used in a server."),
                ephemeral=True,
            )

        target = member or interaction.user
        if not isinstance(target, discord.Member):
            target = interaction.guild.get_member(interaction.user.id)  # type: ignore[assignment]
        if not isinstance(target, discord.Member):
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Found", "Could not resolve the target member."),
                ephemeral=True,
            )

        dest = channel or interaction.channel
        if dest is None:
            return await interaction.response.send_message(
                embed=ModEmbed.error("No Channel", "Could not determine where to send the preview."),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self._send_welcome_message(member=target, channel=dest)
        except Exception as e:
            return await interaction.followup.send(
                embed=ModEmbed.error("Failed", f"Could not send preview: `{type(e).__name__}`"),
                ephemeral=True,
            )

        return await interaction.followup.send(
            embed=ModEmbed.success("Sent", f"Welcome preview sent in {getattr(dest, 'mention', 'the channel')}."),
            ephemeral=True,
        )

    # Slash command - registered dynamically in __init__.py
    async def welcomeall(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        include_bots: bool = False,
        confirm: bool = False,
        limit: Optional[int] = None,
    ):
        if not interaction.guild:
            return await interaction.response.send_message(
                embed=ModEmbed.error("Not Available", "This command can only be used in a server."),
                ephemeral=True,
            )

        dest = channel
        if dest is None:
            settings = await self.bot.db.get_settings(interaction.guild.id)
            channel_id = settings.get("welcome_channel")
            if channel_id:
                resolved = interaction.guild.get_channel(int(channel_id))
                if isinstance(resolved, discord.TextChannel):
                    dest = resolved

        if dest is None:
            if isinstance(interaction.channel, discord.TextChannel):
                dest = interaction.channel
            else:
                return await interaction.response.send_message(
                    embed=ModEmbed.error("No Channel", "Could not determine where to send the welcome messages."),
                    ephemeral=True,
                )

        members: list[discord.Member] = list(getattr(interaction.guild, "members", []) or [])
        try:
            if not members or (
                interaction.guild.member_count
                and len(members) < int(interaction.guild.member_count * 0.75)
            ):
                members = [m async for m in interaction.guild.fetch_members(limit=None)]
        except Exception:
            pass

        if not include_bots:
            members = [m for m in members if not getattr(m, "bot", False)]

        if limit is not None:
            members = members[: int(limit)]

        if not members:
            return await interaction.response.send_message(
                embed=ModEmbed.info("Nothing To Do", "No members found to welcome."),
                ephemeral=True,
            )

        if not confirm:
            return await interaction.response.send_message(
                embed=ModEmbed.warning(
                    "Confirmation Required",
                    f"This will send **{len(members)}** welcome message(s) in {dest.mention}.\n"
                    "Re-run with `confirm: True` to proceed.",
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True, thinking=True)

        sent = 0
        failed = 0
        for m in members:
            try:
                await self._send_welcome_message(member=m, channel=dest)
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.35)

        return await interaction.followup.send(
            embed=ModEmbed.success(
                "Done",
                f"Sent **{sent}** welcome message(s) in {dest.mention}."
                + (f" Failed: **{failed}**." if failed else ""),
            ),
            ephemeral=True,
        )

    # Slash command - registered dynamically in __init__.py
    async def ownerinfo(self, interaction: discord.Interaction):
        """Display information about the bot owner(s)"""
        if not await self.bot.is_owner(interaction.user):
            return await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            
        embed = discord.Embed(title="Bot Owner Information", color=Colors.INFO)
        embed.description = f"Owner: {interaction.user.mention}"
        await interaction.response.send_message(embed=embed, ephemeral=True)
