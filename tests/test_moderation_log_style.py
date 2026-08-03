import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord

from cogs.moderation.extensions.helpers import HelperCommands
from cogs.moderation.extensions.management import ManagementCommands
from utils.embeds import (
    Colors,
    ModEmbed,
    moderation_list_embed,
    sapphire_log_embed,
    stamp_actor_footer,
)
from utils.status_emojis import _semantic_status_kind


class _Avatar:
    def __init__(self, url: str) -> None:
        self.url = url


class _User:
    def __init__(
        self,
        *,
        name: str,
        mention: str,
        avatar_url: str,
        created_at: datetime,
        bot: bool = False,
    ) -> None:
        self.name = name
        self.mention = mention
        self.display_avatar = _Avatar(avatar_url)
        self.created_at = created_at
        self.bot = bot

    def __str__(self) -> str:
        return self.name


class _Guild:
    name = "Luxury Guild"
    icon = _Avatar("https://cdn.example/guild.png")


def test_moderation_action_cards_match_sapphire_log_style() -> None:
    target = _User(
        name="target_user",
        mention="<@100>",
        avatar_url="https://cdn.example/target.png",
        created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    moderator = _User(
        name="staff_user",
        mention="<@200>",
        avatar_url="https://cdn.example/staff.png",
        created_at=datetime(2020, 1, 2, tzinfo=timezone.utc),
    )

    embed = asyncio.run(
        HelperCommands().create_mod_embed(
            title="Member quarantined",
            user=target,
            moderator=moderator,
            reason="Raid review",
            color=Colors.DARK_RED,
            case_num=42,
            extra_fields={"Duration": "Indefinite", "Roles removed": "8"},
        )
    )

    assert embed.title == "Member quarantined"
    assert embed.description == (
        "> **User:** target_user (<@100>)\n"
        "> **Account created:** <t:1704153600:R>\n"
        "> **Bot:** No\n"
        "> **Reason:** Raid review\n"
        "> **Case:** #42\n"
        "> **Duration:** Indefinite\n"
        "> **Roles removed:** 8"
    )
    assert list(embed.fields) == []
    assert embed.thumbnail.url == "https://cdn.example/target.png"
    assert embed.footer.text == "@staff_user"
    assert embed.footer.icon_url == "https://cdn.example/staff.png"
    assert embed.timestamp is not None


def test_summary_cards_use_the_same_quoted_layout() -> None:
    embed = sapphire_log_embed(
        title="Lockdown lifted",
        color=Colors.SUCCESS,
        detail_lines=["**Channels unlocked:** 12", "**Reason:** Review complete"],
        thumbnail_url="https://cdn.example/server.png",
        footer_text="@staff_user",
        footer_icon_url="https://cdn.example/staff.png",
    )

    assert embed.description == (
        "> **Channels unlocked:** 12\n> **Reason:** Review complete"
    )
    assert list(embed.fields) == []
    assert embed.thumbnail.url == "https://cdn.example/server.png"
    assert embed.footer.text == "@staff_user"


def test_quarantine_titles_resolve_to_the_intended_status_emojis() -> None:
    assert _semantic_status_kind("Member quarantined") == "lock"
    assert _semantic_status_kind("Quarantine lifted") == "success"
    assert _semantic_status_kind("Quarantine expired") == "warning"


def test_prefix_quarantine_preserves_reason_without_duration() -> None:
    assert ManagementCommands._normalize_prefix_quarantine_args(
        "gay.",
        "No reason provided",
    ) == (None, "gay.")
    assert ManagementCommands._normalize_prefix_quarantine_args(
        "repeated",
        "raid attempts",
    ) == (None, "repeated raid attempts")


def test_prefix_quarantine_keeps_valid_duration_separate() -> None:
    assert ManagementCommands._normalize_prefix_quarantine_args(
        "2h",
        "Repeated raid attempts",
    ) == ("2h", "Repeated raid attempts")


def test_member_quarantine_notice_is_not_an_audit_card() -> None:
    target = _User(
        name="target_user",
        mention="<@100>",
        avatar_url="https://cdn.example/target.png",
        created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    moderator = _User(
        name="staff_user",
        mention="<@200>",
        avatar_url="https://cdn.example/staff.png",
        created_at=datetime(2020, 1, 2, tzinfo=timezone.utc),
    )

    embed = ManagementCommands._build_quarantine_member_notice(
        guild=_Guild(),
        user=target,
        moderator=moderator,
        reason="Repeated raid attempts",
        duration="2 hours",
        case_number=77,
        expires_at=datetime(2026, 8, 1, 3, 30, tzinfo=timezone.utc),
    )

    assert "You are in quarantine" in embed.title
    assert "Why you are here" in embed.description
    assert "What happens next" in embed.description
    assert "Account created" not in embed.description
    assert "Bot:" not in embed.description
    assert [field.name for field in embed.fields] == ["Duration", "Case", "Review window"]
    assert embed.author.name == "Luxury Guild • Restricted access"
    assert embed.footer.text == "@staff_user"
    assert embed.footer.icon_url == "https://cdn.example/staff.png"
    assert embed.timestamp is not None


def test_moderation_responses_get_native_actor_timestamp_footer() -> None:
    moderator = _User(
        name="staff_user",
        mention="<@200>",
        avatar_url="https://cdn.example/staff.png",
        created_at=datetime(2020, 1, 2, tzinfo=timezone.utc),
    )
    source = SimpleNamespace(author=moderator, guild=None, reply=AsyncMock())

    asyncio.run(
        HelperCommands()._respond(
            source,
            embed=discord.Embed(title="Action complete"),
        )
    )

    kwargs = source.reply.await_args.kwargs
    assert kwargs["embed"].footer.text == "@staff_user"
    assert kwargs["embed"].footer.icon_url == "https://cdn.example/staff.png"
    assert kwargs["embed"].timestamp is not None
    assert kwargs["use_v2"] is False


def test_actor_footer_is_idempotent_and_preserves_existing_metadata() -> None:
    moderator = _User(
        name="staff_user",
        mention="<@200>",
        avatar_url="https://cdn.example/staff.png",
        created_at=datetime(2020, 1, 2, tzinfo=timezone.utc),
    )
    embed = discord.Embed(title="Action complete")
    embed.set_footer(text="Case #77")

    stamp_actor_footer(embed, moderator)
    stamp_actor_footer(embed, moderator)

    assert embed.footer.text == "@staff_user • Case #77"
    assert embed.footer.icon_url == "https://cdn.example/staff.png"
    assert embed.timestamp is not None


def test_native_moderator_footer_cannot_be_prefixed_by_bot_actor() -> None:
    moderator = _User(
        name="surreny",
        mention="<@200>",
        avatar_url="https://cdn.example/surreny.png",
        created_at=datetime(2020, 1, 2, tzinfo=timezone.utc),
    )
    bot_actor = _User(
        name="Docket",
        mention="<@999>",
        avatar_url="https://cdn.example/docket.png",
        created_at=datetime(2020, 1, 2, tzinfo=timezone.utc),
    )
    embed = discord.Embed(title="Punishment notice")

    stamp_actor_footer(embed, moderator)
    stamp_actor_footer(embed, bot_actor)

    assert embed.footer.text == "@surreny"
    assert embed.footer.icon_url == "https://cdn.example/surreny.png"


def test_moderation_lists_use_compact_description_instead_of_field_stacks() -> None:
    embed = moderation_list_embed(
        title="Moderation history · target_user",
        color=Colors.MOD,
        summary_rows=(("Cases", 12), ("Showing", "Newest 2")),
        entries=(
            "**Case #12 · Ban** · <t:1704153600:R>\n> Repeated spam\n-# by staff_user",
            "**Case #11 · Warn** · <t:1704067200:R>\n> Flooding chat\n-# by staff_user",
        ),
        thumbnail_url="https://cdn.example/target.png",
        footer_text="Showing 2 of 12 cases",
    )

    assert embed.title == "Moderation history · target_user"
    assert embed.description.startswith("> **Cases:** 12\n> **Showing:** Newest 2")
    assert "**Case #12 · Ban**" in embed.description
    assert list(embed.fields) == []
    assert embed.thumbnail.url == "https://cdn.example/target.png"
    assert embed.footer.text == "Showing 2 of 12 cases"
    assert embed.timestamp is not None


def test_fallback_punishment_notice_matches_private_moderation_style() -> None:
    expires_at = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    embed = ModEmbed.punishment_notice(
        guild=_Guild(),
        action="Tempban",
        reason="Repeated raid attempts",
        case_number=77,
        duration="2 days",
        expires_at=expires_at,
    )

    assert "Temporary ban applied" in embed.title
    assert embed.description == "> **Reason:** Repeated raid attempts"
    assert [field.name for field in embed.fields] == ["Server", "Case", "Duration", "Ends"]
    assert embed.fields[0].value == "Luxury Guild"
    assert embed.fields[1].value == "#77"
    assert embed.fields[3].value == f"<t:{int(expires_at.timestamp())}:R>"
    assert embed.footer.text == "Luxury Guild moderation"
    assert embed.footer.icon_url == "https://cdn.example/guild.png"
    assert embed.timestamp is not None
