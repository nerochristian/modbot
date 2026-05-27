import asyncio
import json
import logging
from datetime import datetime, timezone
import discord
from discord.ext import commands, tasks

logger = logging.getLogger("ModBot.AIScheduler")

class AIScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task_loop.start()

    def cog_unload(self):
        self._task_loop.cancel()

    @tasks.loop(seconds=30.0)
    async def _task_loop(self):
        await self.bot.wait_until_ready()
        try:
            db = self.bot.db._db # Using the underlying sqlite/postgres connection
            
            # Fetch pending tasks that are due
            # In sqlite/postgres, we can compare string timestamps easily or use datetime.now(timezone.utc)
            now = datetime.now(timezone.utc).isoformat()
            
            # Since bot.db abstracts things, we might need a custom query
            # We'll rely on the execute abstraction in database.py
            # wait, bot.db doesn't expose fetchall directly on the wrapper, we must use the raw conn
            if not getattr(self.bot.db, "_pool", None) and not getattr(self.bot.db, "_conn", None):
                return
                
            cursor_or_records = await self.bot.db.execute("SELECT id, guild_id, task_type, payload, execute_at FROM scheduled_tasks WHERE status = 'pending' AND execute_at <= ?", now)
            
            # execute() in database.py returns a list of asyncpg.Record or sqlite3.Row for SELECTs if implemented, 
            # actually we should use fetch()
            if hasattr(self.bot.db, "fetch"):
                records = await self.bot.db.fetch("SELECT id, guild_id, task_type, payload, execute_at FROM scheduled_tasks WHERE status = 'pending' AND execute_at <= ?", now)
            else:
                # Fallback to direct execute if fetch isn't defined
                records = await self.bot.db.execute("SELECT id, guild_id, task_type, payload, execute_at FROM scheduled_tasks WHERE status = 'pending' AND execute_at <= ?", now)
            
            if not records:
                return

            for row in records:
                task_id = row['id'] if isinstance(row, dict) else row[0]
                guild_id = row['guild_id'] if isinstance(row, dict) else row[1]
                task_type = row['task_type'] if isinstance(row, dict) else row[2]
                payload_str = row['payload'] if isinstance(row, dict) else row[3]
                
                try:
                    payload = json.loads(payload_str)
                    await self._execute_task(guild_id, task_type, payload)
                    await self.bot.db.execute("UPDATE scheduled_tasks SET status = 'completed' WHERE id = ?", task_id)
                except Exception as e:
                    logger.error(f"Failed to execute task {task_id}: {e}")
                    await self.bot.db.execute("UPDATE scheduled_tasks SET status = 'failed' WHERE id = ?", task_id)
        except Exception as e:
            logger.exception("AI Scheduler loop failed")

    async def _execute_task(self, guild_id: int, task_type: str, payload: dict):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        if task_type == "reminder":
            user_id = payload.get("user_id")
            message = payload.get("message")
            if user_id and message:
                member = guild.get_member(user_id) or await guild.fetch_member(user_id)
                if member:
                    await member.send(f"⏰ **Reminder:** {message}")
        
        elif task_type == "execute_python":
            # Very powerful: allows scheduled python execution!
            code = payload.get("code")
            if code:
                env = {
                    "bot": self.bot,
                    "guild": guild,
                    "discord": discord,
                    "asyncio": asyncio,
                }
                wrapped = f"async def _task():\\n"
                for line in code.splitlines():
                    wrapped += f"    {line}\\n"
                exec(wrapped, env)
                await env["_task"]()

        # Add more structured tasks here if needed

async def setup(bot):
    await bot.add_cog(AIScheduler(bot))
