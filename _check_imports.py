import sys
import importlib
import traceback

sys.path.insert(0, ".")

cogs = [
    "cogs.moderation",
    "cogs.setup",
    "cogs.verification",
    "cogs.help",
    "cogs.roles",
    "cogs.logging_cog",
    "cogs.pin",
    "cogs.reports",
    "cogs.blacklist",
    "cogs.prefix_commands",
    "cogs.aimoderation",
    "cogs.ai_scheduler",
    "cogs.automod",
    "cogs.antiraid",
    "cogs.voice",
    "cogs.settings",
    "cogs.polls",
    "cogs.tickets",
    "cogs.utility",
    "cogs.admin",
    "cogs.court",
    "cogs.whitelist",
    "cogs.server_backup",
    "cogs.risk_scoring",
    "cogs.alt_detection",
    "cogs.staff_reports",
    "cogs.behavior_profiling",
]

for cog in cogs:
    try:
        mod = importlib.import_module(cog)
        print(f"  [OK] {cog}")
    except Exception as e:
        print(f"  [ERR] {cog}: {e}")
        traceback.print_exc()