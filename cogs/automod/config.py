"""Default AutoMod configuration.

Guild settings are stored as a flat dictionary so admins can change values from
slash commands and older database rows keep working. Values below are safe
defaults, not hard requirements.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal


# Preset profiles for quick setup
PresetName = Literal["strict", "moderate", "relaxed", "security", "minimal"]

AUTOMOD_PRESETS: dict[str, dict[str, Any]] = {
    "strict": {
        "description": "Maximum protection for high-traffic or sensitive servers",
        "automod_punishment": "timeout",
        "automod_security_punishment": "ban",
        "automod_spam_threshold": 3,
        "automod_spam_window": 5,
        "automod_duplicate_threshold": 2,
        "automod_duplicate_window": 30,
        "automod_fast_message_threshold": 3,
        "automod_fast_message_window": 3,
        "automod_max_mentions": 3,
        "automod_caps_percentage": 60,
        "automod_newaccount_days": 14,
        "automod_raid_join_threshold": 5,
        "automod_raid_join_window": 15,
        "automod_escalation": [
            {"offenses": 2, "action": "timeout", "duration": 3600},
            {"offenses": 3, "action": "kick", "duration": 0},
           {"offenses": 5, "action": "ban", "duration": 0},
        ],
    },
    "moderate": {
        "description": "Balanced protection suitable for most communities",
        "automod_punishment": "warn",
        "automod_security_punishment": "timeout",
        "automod_spam_threshold": 5,
        "automod_spam_window": 5,
        "automod_duplicate_threshold": 3,
        "automod_duplicate_window": 30,
        "automod_fast_message_threshold": 4,
        "automod_fast_message_window": 3,
        "automod_max_mentions": 5,
        "automod_caps_percentage": 70,
        "automod_newaccount_days": 7,
        "automod_raid_join_threshold": 8,
        "automod_raid_join_window": 20,
        "automod_escalation": [
            {"offenses": 2, "action": "timeout", "duration": 1800},
            {"offenses": 4, "action": "kick", "duration": 0},
            {"offenses": 6, "action": "ban", "duration": 0},
        ],
    },
    "relaxed": {
        "description": "Light moderation for chill communities",
        "automod_punishment": "log",
        "automod_security_punishment": "warn",
        "automod_spam_threshold": 8,
        "automod_spam_window": 10,
        "automod_duplicate_threshold": 5,
        "automod_duplicate_window": 60,
        "automod_fast_message_threshold": 6,
        "automod_fast_message_window": 5,
        "automod_max_mentions": 10,
        "automod_caps_percentage": 85,
        "automod_newaccount_days": 3,
        "automod_raid_join_threshold": 12,
        "automod_raid_join_window": 30,
        "automod_escalation": [
            {"offenses": 3, "action": "warn", "duration": 0},
            {"offenses": 5, "action": "timeout", "duration": 600},
            {"offenses": 8, "action": "kick", "duration": 0},
        ],
    },
    "security": {
        "description": "Focus on security threats: scams, phishing, raids, malicious links",
        "automod_punishment": "timeout",
        "automod_security_punishment": "ban",
        "automod_links_enabled": True,
        "automod_links_mode": "dangerous",
        "automod_scam_protection": True,
        "automod_invites_enabled": True,
       "automod_raid_enabled": True,
        "automod_raid_join_threshold": 5,
        "automod_raid_join_window": 10,
        "automod_raid_punishment": "ban",
        "automod_newaccount_enabled": True,
        "automod_newaccount_days": 7,
        "automod_newaccount_join_action": "timeout",
        "automod_escalation": [
            {"offenses": 1, "action": "timeout", "duration": 3600},
            {"offenses": 2, "action": "ban", "duration": 0},
        ],
    },
    "minimal": {
        "description": "Only critical protections, maximum freedom",
        "automod_punishment": "log",
        "automod_security_punishment": "warn",
        "automod_spam_enabled": False,
        "automod_duplicates_enabled": False,
        "automod_fast_messages_enabled": False,
        "automod_caps_enabled": False,
        "automod_mentions_enabled": True,
        "automod_max_mentions": 15,
        "automod_links_enabled": True,
        "automod_scam_protection": True,
        "automod_invites_enabled": True,
        "automod_badwords_enabled": True,
        "automod_raid_enabled": True,
        "automod_newaccount_enabled": False,
        "automod_escalation_enabled": False,
    },
}


MODULES: tuple[str, ...] = (
    "spam",
    "links",
    "invites",
    "mentions",
    "caps",
    "badwords",
    "duplicates",
    "fast_messages",
    "new_accounts",
    "raid",
)

PUNISHMENTS: tuple[str, ...] = ("none", "log", "warn", "mute", "timeout", "kick", "ban")

MODULE_SETTING_KEYS: dict[str, str] = {
    "spam": "automod_spam_enabled",
    "links": "automod_links_enabled",
    "invites": "automod_invites_enabled",
    "mentions": "automod_mentions_enabled",
    "caps": "automod_caps_enabled",
    "badwords": "automod_badwords_enabled",
    "duplicates": "automod_duplicates_enabled",
    "fast_messages": "automod_fast_messages_enabled",
    "new_accounts": "automod_newaccount_enabled",
    "raid": "automod_raid_enabled",
}

AUTOMOD_SETTINGS: dict[str, Any] = {
    "automod_enabled": True,
    "automod_log_channel": None,
    "log_channel_automod": None,
    "automod_delete_violations": True,
    "automod_notify_users": True,
    "automod_public_feedback": False,
    "automod_bypass_staff": True,
    "automod_violation_cooldown": 8,
    "automod_punishment": "warn",
    "automod_security_punishment": "timeout",
    "automod_mute_duration": 3600,
    "automod_ban_delete_days": 1,
    "automod_escalation_enabled": True,
    "automod_escalation_window": 86400,
    "automod_escalation": [
        {"offenses": 2, "action": "timeout", "duration": 1800},
        {"offenses": 4, "action": "kick", "duration": 0},
        {"offenses": 6, "action": "ban", "duration": 0},
    ],
    "automod_spam_enabled": True,
    "automod_spam_threshold": 5,
    "automod_spam_window": 5,
    "automod_links_enabled": True,
    "automod_scam_protection": True,
    "automod_links_mode": "dangerous",
    "automod_links_whitelist": ["discord.com", "discordapp.com", "youtube.com", "youtu.be", "github.com"],
    "automod_whitelisted_domains": [],
    "automod_invites_enabled": True,
    "automod_allowed_invites": [],
    "automod_mentions_enabled": True,
    "automod_max_mentions": 5,
    "automod_caps_enabled": True,
    "automod_caps_percentage": 70,
    "automod_caps_min_length": 12,
    "automod_badwords_enabled": True,
    "automod_badwords": [],
    "automod_duplicates_enabled": True,
    "automod_duplicate_threshold": 3,
    "automod_duplicate_window": 30,
    "automod_fast_messages_enabled": True,
    "automod_fast_message_threshold": 4,
    "automod_fast_message_window": 3,
    "automod_newaccount_enabled": True,
    "automod_newaccount_days": 7,
    "automod_newaccount_join_action": "log",
    "automod_raid_enabled": True,
    "automod_raid_join_threshold": 8,
    "automod_raid_join_window": 20,
    "automod_raid_punishment": "timeout",
    "automod_bypass_roles": [],
    "automod_bypass_users": [],
    "automod_bypass_channels": [],
    "ignored_roles": [],
    "ignored_channels": [],
    "warn_thresholds_enabled": True,
    "warn_threshold_mute": 3,
    "warn_threshold_kick": 5,
    "warn_threshold_ban": 7,
    "warn_mute_duration": 3600,
}

EXAMPLE_CONFIG: dict[str, Any] = {
    "automod_enabled": True,
    "automod_log_channel": 123456789012345678,
    "automod_punishment": "warn",
    "automod_spam_threshold": 5,
    "automod_spam_window": 5,
    "automod_max_mentions": 5,
    "automod_badwords": ["example banned phrase"],
    "automod_bypass_roles": [123456789012345678],
    "automod_bypass_channels": [123456789012345678],
}


def default_settings() -> dict[str, Any]:
    return deepcopy(AUTOMOD_SETTINGS)


def merged_settings(stored: dict[str, Any] | None) -> dict[str, Any]:
    settings = default_settings()
    settings.update(stored or {})
    return settings
