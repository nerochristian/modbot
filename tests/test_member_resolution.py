import inspect
import asyncio
from types import SimpleNamespace
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


def test_subcommand_member_resolution_extracts_target_after_full_command_path() -> None:
    ctx = SimpleNamespace(
        message=SimpleNamespace(content=",role   add   ashley role maker"),
        prefix=",",
        command=SimpleNamespace(qualified_name="role add"),
    )

    assert ModBot._extract_first_argument_and_tail(None, ctx) == (
        "ashley",
        "role maker",
    )


def test_member_resolution_rebuilds_commands_with_greedy_arguments() -> None:
    captured: dict[str, object] = {}

    async def role_add(ctx, member: discord.Member, *role_parts: str) -> None:
        return None

    command = commands.Command(role_add, name="add")

    async def invoke(invoked_command, *args, **kwargs):
        captured["command"] = invoked_command
        captured["args"] = args
        captured["kwargs"] = kwargs

    target = object()
    ctx = SimpleNamespace(command=command, invoke=invoke)
    resolver = SimpleNamespace(_split_tokens=ModBot._split_tokens)

    ok, error = asyncio.run(
        ModBot._invoke_with_resolved_target(
            resolver,
            ctx,
            target=target,
            args_tail="role maker",
        )
    )

    assert ok is True
    assert error == ""
    assert captured == {
        "command": command,
        "args": (target, "role", "maker"),
        "kwargs": {},
    }
