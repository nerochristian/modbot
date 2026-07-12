import asyncio, os, sys, traceback
sys.path.insert(0, os.getcwd())
import discord
from discord.ext import commands

COGS = [
    "cogs.moderation","cogs.setup","cogs.verification","cogs.help","cogs.roles",
    "cogs.logging_cog","cogs.pin","cogs.reports","cogs.blacklist","cogs.prefix_commands","cogs.aimoderation",
    "cogs.ai_scheduler","cogs.automod","cogs.antiraid","cogs.voice","cogs.settings",
    "cogs.polls","cogs.tickets","cogs.utility","cogs.admin","cogs.court","cogs.whitelist",
    "cogs.server_backup","cogs.risk_scoring","cogs.alt_detection","cogs.staff_reports",
    "cogs.behavior_profiling",
]

from database import Database

class FakeBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=",", intents=discord.Intents.all(),
                         help_command=None, case_insensitive=True)

async def main():
    bot = FakeBot()
    bot.db = Database()
    for attr in ("prefix_cache","caches","_cache_backend"):
        if not hasattr(bot, attr):
            setattr(bot, attr, None)
    ok, fail = [], []
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            ok.append(cog)
        except Exception as e:
            fail.append((cog, repr(e)))
            print("---- TRACEBACK for", cog, "----")
            traceback.print_exc()
    print("\n==== SUMMARY ====")
    print("Loaded:", len(ok))
    print("Failed:", len(fail))
    for c,e in fail:
        print("  FAIL", c, e)
    try:
        print("Prefix commands:", len(list(bot.walk_commands())))
        print("Slash (tree):", len(bot.tree.get_commands()))
    except Exception as e:
        print("count err", e)

    # Detect duplicate/aliased prefix command names
    from collections import Counter
    names = Counter()
    for c in bot.walk_commands():
        names[c.qualified_name] += 1
        for a in getattr(c, "aliases", []):
            names[a] += 1
    dupes = {n:k for n,k in names.items() if k > 1}
    print("Prefix name collisions:", dupes or "none")

    # List top-level slash command names
    slash_names = sorted(c.name for c in bot.tree.get_commands())
    print("Top-level slash:", slash_names)

asyncio.run(main())
