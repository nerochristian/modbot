import inspect
from typing import Union

import discord
from discord.ext import commands

from bot import ModBot


def test_union_member_lookup_failure_reaches_nickname_resolver() -> None:
    parameter = commands.Parameter(
        name="target",
        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
        annotation=Union[discord.Role, discord.Member],
    )
    error = commands.BadUnionArgument(
        parameter,
        (discord.Role, discord.Member),
        [
            commands.RoleNotFound("ashley"),
            commands.MemberNotFound("ashley"),
        ],
    )

    resolved = ModBot._member_lookup_error(error)

    assert isinstance(resolved, commands.MemberNotFound)
    assert resolved.argument == "ashley"
    assert ModBot._is_member_like_annotation(parameter.annotation)


def test_unrelated_bad_union_does_not_trigger_member_resolution() -> None:
    parameter = commands.Parameter(
        name="amount",
        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )
    error = commands.BadUnionArgument(
        parameter,
        (int, float),
        [commands.BadArgument("not an integer"), commands.BadArgument("not a float")],
    )

    assert ModBot._member_lookup_error(error) is None
