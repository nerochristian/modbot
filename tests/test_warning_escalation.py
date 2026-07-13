import asyncio
from datetime import timedelta

from utils.warning_escalation import (
    MAX_TIMEOUT_SECONDS,
    apply_warning_escalation,
    crossed_warning_rule,
    normalize_warning_rules,
)


def test_dashboard_rules_are_authoritative_and_normalized():
    settings = {
        "moderation_autopunish_rules": [
            {"warnings": 7, "action": "ban", "durationMinutes": 0},
            {"warnings": 3, "action": "mute", "durationMinutes": 30},
            {"warnings": 5, "action": "kick", "durationMinutes": 0},
        ],
        "warn_threshold_mute": 1,
    }

    rules = normalize_warning_rules(settings)

    assert [(rule.warning_count, rule.action, rule.duration_seconds) for rule in rules] == [
        (3, "timeout", 1800),
        (5, "kick", None),
        (7, "ban", None),
    ]


def test_empty_dashboard_rules_disable_legacy_fallback():
    settings = {
        "moderation_autopunish_rules": [],
        "warn_thresholds_enabled": True,
        "warn_threshold_mute": 3,
        "warn_threshold_kick": 5,
        "warn_threshold_ban": 7,
    }

    assert normalize_warning_rules(settings) == ()


def test_global_threshold_toggle_disables_dashboard_rules():
    settings = {
        "warn_thresholds_enabled": False,
        "moderation_autopunish_rules": [
            {"warnings": 3, "action": "timeout", "durationMinutes": 30},
        ],
    }

    assert normalize_warning_rules(settings) == ()


def test_invalid_duplicate_and_decreasing_rules_are_discarded():
    settings = {
        "moderation_autopunish_rules": [
            {"warnings": 0, "action": "timeout", "durationMinutes": 30},
            {"warnings": 3, "action": "timeout", "durationMinutes": 0},
            {"warnings": 3, "action": "timeout", "durationMinutes": 30},
            {"warnings": 4, "action": "ban", "durationMinutes": 0},
            {"warnings": 5, "action": "kick", "durationMinutes": 0},
            {"warnings": 8, "action": "timeout", "durationMinutes": MAX_TIMEOUT_SECONDS // 60 + 1},
        ]
    }

    rules = normalize_warning_rules(settings)

    assert [(rule.warning_count, rule.action) for rule in rules] == [(3, "timeout"), (4, "ban")]


def test_legacy_flat_settings_are_synthesized():
    rules = normalize_warning_rules(
        {
            "warn_thresholds_enabled": True,
            "warn_threshold_mute": 2,
            "warn_mute_duration": 600,
            "warn_threshold_kick": 4,
            "warn_threshold_ban": 6,
        }
    )

    assert [(rule.warning_count, rule.action, rule.duration_seconds) for rule in rules] == [
        (2, "timeout", 600),
        (4, "kick", None),
        (6, "ban", None),
    ]


def test_only_highest_newly_crossed_rule_is_selected():
    settings = {
        "moderation_autopunish_rules": [
            {"warnings": 3, "action": "timeout", "durationMinutes": 30},
            {"warnings": 5, "action": "kick", "durationMinutes": 0},
            {"warnings": 7, "action": "ban", "durationMinutes": 0},
        ]
    }

    assert crossed_warning_rule(settings, 8, previous_count=2).action == "ban"
    assert crossed_warning_rule(settings, 8, previous_count=7) is None
    assert crossed_warning_rule(settings, 5).action == "kick"


class FakeMember:
    def __init__(self):
        self.timeouts = []
        self.direct_messages = []
        self.roles = []

    async def timeout(self, duration, *, reason):
        self.timeouts.append((duration, reason))

    async def send(self, content):
        self.direct_messages.append(content)


class FakeGuild:
    def __init__(self):
        self.name = "Test Guild"
        self.kicks = []
        self.bans = []

    async def kick(self, member, *, reason):
        self.kicks.append((member, reason))

    async def ban(self, member, *, reason, delete_message_days):
        self.bans.append((member, reason, delete_message_days))


def test_apply_timeout_executes_and_creates_case():
    guild = FakeGuild()
    member = FakeMember()
    cases = []

    async def create_case(action, reason, duration_seconds):
        cases.append((action, reason, duration_seconds))

    result = asyncio.run(
        apply_warning_escalation(
            guild,
            member,
            {"moderation_autopunish_rules": [{"warnings": 3, "action": "timeout", "durationMinutes": 30}]},
            3,
            previous_count=2,
            create_case=create_case,
        )
    )

    assert result.rule.action == "timeout"
    assert member.timeouts[0][0] == timedelta(minutes=30)
    assert "timed out in Test Guild" in member.direct_messages[0]
    assert cases == [("Mute", "Automatic warning escalation: 3 warnings reached", 1800)]


def test_apply_ban_preserves_messages_when_configured():
    guild = FakeGuild()
    member = FakeMember()

    asyncio.run(
        apply_warning_escalation(
            guild,
            member,
            {
                "moderation_preserve_ban_messages": True,
                "moderation_autopunish_rules": [{"warnings": 7, "action": "ban", "durationMinutes": 0}],
            },
            7,
            previous_count=6,
            ban_delete_days=7,
        )
    )

    assert guild.bans[0][2] == 0


def test_apply_ban_preserves_messages_by_default():
    guild = FakeGuild()
    member = FakeMember()

    asyncio.run(
        apply_warning_escalation(
            guild,
            member,
            {"moderation_autopunish_rules": [{"warnings": 7, "action": "ban", "durationMinutes": 0}]},
            7,
            previous_count=6,
            ban_delete_days=7,
        )
    )

    assert guild.bans[0][2] == 0


def test_protected_roles_skip_crossed_punishment():
    guild = FakeGuild()
    member = FakeMember()
    member.roles = [type("Role", (), {"id": 123})()]

    result = asyncio.run(
        apply_warning_escalation(
            guild,
            member,
            {
                "protected_roles": ["123"],
                "moderation_autopunish_rules": [
                    {"warnings": 3, "action": "timeout", "durationMinutes": 30},
                ],
            },
            3,
            previous_count=2,
        )
    )

    assert result is None
    assert member.timeouts == []
