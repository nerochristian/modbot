"""
AutoMod V3 Configuration
"""

AUTOMOD_SETTINGS = {
    # General Settings
    "automod_enabled": True,
    "automod_log_channel": None,
    "automod_notify_users": True,
    
    # Bypass Settings
    "automod_bypass_role_id": None,
    "automod_temp_bypass": [],
    "automod_bypass_channels": [],
    
    # Punishment Settings
    "automod_punishment": "warn",
    "automod_mute_duration": 3600,
    "automod_tempban_duration": 86400,
    "automod_ban_delete_days": 1,
    
    # Quarantine Settings
    "automod_quarantine_role_id": None,
    
    # Filter Configurations
    "automod_badwords": [
        "nigger", "nigga", "chink", "spic", "kike",
        "faggot", "fag", "tranny", "dyke",
        "retard", "autist",
        "kys", "kill yourself", "end your life"
    ],
    
    "automod_links_enabled": True,
    "automod_links_whitelist": [
        "youtube.com", "youtu.be", "twitter.com", "x.com", "github.com"
    ],
    "automod_whitelisted_domains": [
        "discord.com", "discordapp.com", "imgur.com"
    ],
    
    "automod_invites_enabled": True,
    "automod_allowed_invites": [],
    
    "automod_spam_threshold": 5,
    "automod_duplicate_threshold": 3,
    
    "automod_caps_percentage": 70,
    "automod_caps_min_length": 10,
    
    "automod_max_mentions": 5,
    
    "automod_newaccount_days": 7,
    
    "automod_ai_enabled": False,
    "automod_ai_min_severity": 4,
    
    "automod_scam_protection": True,

    # Warning Threshold Settings (unified for automod + manual warns)
    "warn_thresholds_enabled": True,
    "warn_threshold_mute": 3,
    "warn_threshold_kick": 5,
    "warn_threshold_ban": 7,
    "warn_mute_duration": 3600,
}
