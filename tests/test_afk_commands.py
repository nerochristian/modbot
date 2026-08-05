from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_afk_nickname_guards_use_guild_owner_id() -> None:
    prefix_source = (ROOT / "cogs" / "prefix_commands.py").read_text(encoding="utf-8")
    utility_source = (ROOT / "cogs" / "utility.py").read_text(encoding="utf-8")

    assert ".guild_owner" not in prefix_source
    assert ".guild_owner" not in utility_source
    assert "member.id != ctx.guild.owner_id" in prefix_source
    assert "member.id != interaction.guild.owner_id" in utility_source
