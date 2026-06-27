"""Default settings for the AutoMod rule engine.

The database merges these defaults with each guild's stored settings.  Keep
the keys flat so older guild configurations remain compatible.
"""

AUTOMOD_SETTINGS = {
    # System
    "automod_enabled": True,
    "automod_log_channel": None,
    "automod_notify_users": True,
    "automod_public_feedback": False,
    "automod_delete_violations": True,
    "automod_violation_cooldown": 10,

    # Bypasses
    "automod_bypass_staff": True,
    "automod_bypass_role_id": None,
    "automod_bypass_roles": [],
    "automod_bypass_channels": [],
    "automod_temp_bypass": [],

    # Actions. Security rules intentionally have a separate policy.
    "automod_punishment": "warn",
    "automod_security_punishment": "timeout",
    "automod_mute_duration": 3600,
    "automod_tempban_duration": 86400,
    "automod_ban_delete_days": 1,
    "automod_quarantine_role_id": None,

    # Rule switches
    "automod_badwords_enabled": True,
    "automod_spam_enabled": True,
    "automod_mentions_enabled": True,
    "automod_caps_enabled": True,
    "automod_links_enabled": True,
    "automod_invites_enabled": True,
    "automod_scam_protection": True,
    "automod_newaccount_enabled": True,
    "automod_ai_enabled": False,

    # Content rules
    "automod_badwords": [
        "nigger", "nigga", "chink", "spic", "kike",
        "faggot", "fag", "tranny", "dyke",
        "retard", "autist", "kys", "kill yourself",
        "end your life",
    ],
    # ``dangerous`` blocks only known-dangerous links. ``allowlist`` blocks
    # every domain not listed below.
    "automod_links_mode": "dangerous",
    "automod_links_whitelist": [
        "youtube.com", "youtu.be", "twitter.com", "x.com", "github.com",
    ],
    "automod_whitelisted_domains": [
        "discord.com", "discordapp.com", "imgur.com",
    ],
    "automod_allowed_invites": [],

    # Behaviour rules
    "automod_spam_threshold": 5,
    "automod_spam_window": 5,
    "automod_duplicate_threshold": 3,
    "automod_duplicate_window": 30,
    "automod_caps_percentage": 70,
    "automod_caps_min_length": 10,
    "automod_max_mentions": 5,
    "automod_newaccount_days": 7,

    # Optional AI rule. Credentials and endpoint are read from environment.
    "automod_ai_min_severity": 7,

    # Warning thresholds are shared with manual moderation.
    "warn_thresholds_enabled": True,
    "warn_threshold_mute": 3,
    "warn_threshold_kick": 5,
    "warn_threshold_ban": 7,
    "warn_mute_duration": 3600,
}
