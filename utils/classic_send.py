from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

import discord


_MessageableSend = Callable[..., Awaitable[Any]]


def register_original_messageable_send(send: _MessageableSend) -> None:
    """Legacy stub — kept for backward compatibility with components_v2.py.

    No-op now that the v2 monkeypatch is disabled.
    """
    pass


def _strip_v2_only_kwargs(kwargs: dict[str, Any]) -> None:
    """Remove any leftover v2-specific kwargs that discord.py doesn't understand."""
    kwargs.pop("use_v2", None)
    if kwargs.get("view", discord.utils.MISSING) is None:
        kwargs.pop("view", None)


async def send_classic_message(target: discord.abc.Messageable, *args: Any, **kwargs: Any) -> Any:
    """
    Send a message using classic Discord embeds (no Components v2).

    Strips any v2-specific kwargs and sends through the standard discord.py path.
    """
    kwargs = dict(kwargs)
    _strip_v2_only_kwargs(kwargs)
    return await target.send(*args, **kwargs)
