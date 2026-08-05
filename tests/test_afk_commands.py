import asyncio
from pathlib import Path
from types import SimpleNamespace

from cogs.prefix_commands import PrefixCommands


ROOT = Path(__file__).resolve().parents[1]


def test_afk_nickname_guards_use_guild_owner_id() -> None:
    prefix_source = (ROOT / "cogs" / "prefix_commands.py").read_text(encoding="utf-8")
    utility_source = (ROOT / "cogs" / "utility.py").read_text(encoding="utf-8")

    assert ".guild_owner" not in prefix_source
    assert ".guild_owner" not in utility_source
    assert "member.id != ctx.guild.owner_id" in prefix_source
    assert "member.id != interaction.guild.owner_id" in utility_source


class _Message:
    def __init__(self) -> None:
        self.deleted = False

    async def delete(self) -> None:
        self.deleted = True


class _Context:
    def __init__(self) -> None:
        self.author = SimpleNamespace(id=42, mention="<@42>", display_name="Owner")
        self.member = SimpleNamespace(id=42, display_name="Owner")
        self.guild = SimpleNamespace(
            id=7,
            owner_id=42,
            me=SimpleNamespace(guild_permissions=SimpleNamespace(manage_nicknames=True), top_role=10),
            get_member=lambda _member_id: self.member,
        )
        self.message = _Message()
        self.sent = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)


def test_prefix_afk_owner_path_sets_status_without_invalid_member_property() -> None:
    bot = SimpleNamespace(get_cog=lambda _name: None)
    cog = PrefixCommands(bot)
    ctx = _Context()

    asyncio.run(PrefixCommands.afk_cmd.callback(cog, ctx, reason="Lunch"))

    assert cog.afk_users[42]["reason"] == "Lunch"
    assert cog.afk_users[42]["guild_id"] == 7
    assert ctx.message.deleted is True
    assert len(ctx.sent) == 1
    assert "nickname could not be changed" in ctx.sent[0]["embed"].description
