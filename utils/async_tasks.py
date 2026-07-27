"""Fire-and-forget helpers for non-critical background side-effects.

Moderation commands (warn, quarantine, etc.) need to confirm to the moderator
the moment the *authoritative* outcome lands — the warning is recorded, the
quarantine role is applied, the case # is generated. The slower side-effects
that follow (punishment DM, appeal-token DB transaction, jail-channel notice)
must never block that confirmation, but they also must not fail silently.

``fire_and_forget`` schedules a coroutine on the running loop and attaches a
done-callback that logs any exception, mirroring the ad-hoc pattern already
used in ``cogs/aimoderation/ai_client.py`` and ``cogs/logging_cog.py`` but
centralizing the error reporting so a backgrounded step fails visibly in logs.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Optional

logger = logging.getLogger("ModBot.AsyncTasks")


def _make_done_callback(name: str):
    def _callback(task: "asyncio.Task[object]") -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Background task %r failed", name)

    return _callback


def fire_and_forget(
    coro: Awaitable[object],
    *,
    name: str,
    log: Optional[logging.Logger] = None,
) -> "asyncio.Task[object]":
    """Schedule ``coro`` as a background task that logs its own failures.

    The returned task holds a strong reference for as long as it runs, so the
    caller does not need to keep a reference (unlike a bare
    ``asyncio.create_task`` which can be garbage-collected mid-flight). Any
    exception raised by ``coro`` is reported through the done-callback to
    ``log`` (defaults to this module's logger) and never propagates to the
    caller.
    """

    log = log or logger
    task = asyncio.ensure_future(coro)
    try:
        task.set_name(name)
    except Exception:
        # Older Python versions or odd task types — naming is cosmetic only.
        pass
    task.add_done_callback(_make_done_callback(name))
    return task


__all__ = ["fire_and_forget"]
