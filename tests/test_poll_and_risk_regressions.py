import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from cogs.polls import PollView
from cogs.risk_scoring import RiskEngine


def test_poll_view_always_exposes_each_option_and_results_controls():
    poll = {
        "id": 42,
        "options": ["One", "Two", "Three", "Four", "Five", "Six"],
    }

    view = PollView(poll)
    custom_ids = {item.custom_id for item in view.children}

    assert {f"poll:42:option:{index}" for index in range(6)} <= custom_ids
    assert "poll:42:results" in custom_ids
    assert "poll:42:remove" in custom_ids
    assert next(item for item in view.children if item.custom_id == "poll:42:option:5").row == 1


def test_risk_engine_accepts_timezone_aware_discord_timestamps():
    class FakeDatabase:
        async def get_warnings(self, guild_id, member_id):
            return []

        async def get_risk_score(self, guild_id, member_id):
            return None

    bot = SimpleNamespace(db=FakeDatabase())
    now = datetime.now(timezone.utc)
    member = SimpleNamespace(
        id=123,
        guild=SimpleNamespace(id=456),
        created_at=now - timedelta(days=14),
        joined_at=now - timedelta(hours=2),
        avatar=object(),
    )

    result = asyncio.run(RiskEngine(bot).calculate(member))

    assert result.details["account_age_days"] >= 13
    assert result.details["join_hours"] >= 1.9
