from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

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


def test_verification_queue_role_addition_is_not_logged_individually() -> None:
    unverified = SimpleNamespace(id=300)
    settings = {
        "verification_enabled": True,
        "unverified_role": "300",
    }

    assert Logging._is_verification_queue_role_update(settings, [unverified], []) is True
    assert Logging._is_verification_queue_role_update(settings, [unverified], [SimpleNamespace(id=301)]) is False
    assert Logging._is_verification_queue_role_update({**settings, "verification_enabled": False}, [unverified], []) is False


def test_primary_ban_path_suppresses_gateway_event_before_banning() -> None:
    source = (ROOT / "cogs" / "moderation" / "extensions" / "management.py").read_text(
        encoding="utf-8-sig"
    )
    function = source[source.index("    async def _ban_logic("):source.index("    async def _unban_logic(")]

    suppression = 'self._suppress_duplicate_member_action_log(guild.id, user.id, "ban")'
    assert function.index(suppression) < function.index("await user.ban(")


def test_primary_ban_path_preopens_dm_before_removing_member() -> None:
    source = (ROOT / "cogs" / "moderation" / "extensions" / "management.py").read_text(
        encoding="utf-8-sig"
    )
    function = source[source.index("    async def _ban_logic("):source.index("    async def _unban_logic(")]

    assert function.index("await self.prepare_dm_channel(user)") < function.index("await user.ban(")
    assert "delivery_channel=dm_channel" in function
    assert function.index("await user.ban(") < function.index("await self.send_punishment_notice(")
    assert function.index("await user.ban(") < function.index("await self.bot.db.create_case(")


def test_other_primary_departure_or_timeout_paths_notify_only_after_enforcement() -> None:
    source = (ROOT / "cogs" / "moderation" / "extensions" / "management.py").read_text(
        encoding="utf-8-sig"
    )
    boundaries = [
        ("_kick_logic", "_ban_logic", "await user.kick("),
        ("_softban_logic", "_tempban_logic", "await user.ban("),
        ("_tempban_logic", "_mute_logic", "await user.ban("),
        ("_mute_logic", "_unmute_logic", "await user.timeout("),
    ]
    for current, following, enforcement in boundaries:
        function = source[source.index(f"    async def {current}("):source.index(f"    async def {following}(")]
        assert function.index("await self.prepare_dm_channel(user)") < function.index(enforcement)
        assert function.index(enforcement) < function.index("await self.send_punishment_notice(")


def test_automod_notifies_only_after_timeout_kick_or_ban_succeeds() -> None:
    source = (ROOT / "cogs" / "automod" / "punishments.py").read_text(encoding="utf-8-sig")
    apply = source[source.index("    async def apply("):source.index("    async def _notify_appeal(")]

    for marker, enforcement in (
        ("if action is Action.TIMEOUT:", "await member.timeout("),
        ("if action is Action.KICK:", "await member.kick("),
        ("if action is Action.BAN:", "await guild.ban("),
    ):
        branch = apply[apply.index(marker):]
        assert branch.index(enforcement) < branch.index("await self._notify_appeal(")


def test_gateway_ban_listener_consumes_suppression_before_logging() -> None:
    source = (ROOT / "cogs" / "logging_cog.py").read_text(encoding="utf-8-sig")
    function = source[source.index("    async def on_member_ban("):source.index("    async def on_member_unban(")]

    assert function.index("_consume_member_action_log_suppression") < function.index("get_log_channel")
