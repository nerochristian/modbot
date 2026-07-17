from datetime import datetime, timedelta, timezone
from pathlib import Path

from cogs.logging_cog import Logging


ROOT = Path(__file__).resolve().parent.parent


def _logging_cog() -> Logging:
    cog = object.__new__(Logging)
    cog._suppressed_member_action_logs = {}
    return cog


def test_member_action_suppression_is_scoped_and_consumed_once() -> None:
    cog = _logging_cog()

    cog.suppress_member_action_log(100, 200, "ban")

    assert cog._consume_member_action_log_suppression(100, 200, "ban") is True
    assert cog._consume_member_action_log_suppression(100, 200, "ban") is False
    assert cog._consume_member_action_log_suppression(100, 201, "ban") is False
    assert cog._consume_member_action_log_suppression(100, 200, "unban") is False


def test_expired_member_action_suppression_does_not_hide_manual_action() -> None:
    cog = _logging_cog()
    cog._suppressed_member_action_logs[(100, 200, "ban")] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )

    assert cog._consume_member_action_log_suppression(100, 200, "ban") is False
    assert cog._suppressed_member_action_logs == {}


def test_primary_ban_path_suppresses_gateway_event_before_banning() -> None:
    source = (ROOT / "cogs" / "moderation" / "extensions" / "management.py").read_text(
        encoding="utf-8-sig"
    )
    function = source[source.index("    async def _ban_logic("):source.index("    async def _unban_logic(")]

    suppression = 'self._suppress_duplicate_member_action_log(guild.id, user.id, "ban")'
    assert function.index(suppression) < function.index("await user.ban(")


def test_gateway_ban_listener_consumes_suppression_before_logging() -> None:
    source = (ROOT / "cogs" / "logging_cog.py").read_text(encoding="utf-8-sig")
    function = source[source.index("    async def on_member_ban("):source.index("    async def on_member_unban(")]

    assert function.index("_consume_member_action_log_suppression") < function.index("get_log_channel")
