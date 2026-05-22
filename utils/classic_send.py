from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

import discord


_MessageableSend = Callable[..., Awaitable[Any]]
_original_messageable_send: Optional[_MessageableSend] = None


def register_original_messageable_send(send: _MessageableSend) -> None:
    """Register discord.py's unpatched Messageable.send implementation."""
    global _original_messageable_send
    if _original_messageable_send is None:
        _original_messageable_send = send


def _strip_v2_only_kwargs(kwargs: dict[str, Any]) -> None:
    kwargs.pop("use_v2", None)
    if kwargs.get("view", discord.utils.MISSING) is None:
        kwargs.pop("view", None)


async def send_classic_message(target: discord.abc.Messageable, *args: Any, **kwargs: Any) -> Any:
    """
    Send a message through the original discord.py send path.

    This is used for log embeds so they remain classic embeds even when the
    Components v2 compatibility monkeypatch is installed globally.
    """
    kwargs = dict(kwargs)
    _strip_v2_only_kwargs(kwargs)

    if _original_messageable_send is not None:
        return await _original_messageable_send(target, *args, **kwargs)

    try:
        return await target.send(*args, use_v2=False, **kwargs)
    except TypeError as exc:
        if "use_v2" not in str(exc):
            raise
        return await target.send(*args, **kwargs)
