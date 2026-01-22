import discord
from discord.ext import commands, tasks
import aiohttp
import random
import logging

# Set up logging
logger = logging.getLogger("ModBot")

class Rule34Loop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = 1463001859345354968
        
        # Hardcoded credentials as requested
        self.api_key = "4b5d1fd9db037eeb8b534b57f7d3d5e7f58f8ad8d3045fb75bd4f11f3db95345bef64f2551fd74a43b62b3f544996df06b01fec2cbb4b4cae335168f207855f2"
        self.user_id = "1900224"
        
        # Search tags
        self.tags = "femboy rating:q"
        
        self.session = None
        self.rule34_task.start()

    async def cog_load(self):
        """Initializes the aiohttp session when the Cog is loaded."""
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        """Cancels the task and closes the session gracefully."""
        self.rule34_task.cancel()
        if self.session:
            await self.session.close()

    @tasks.loop(seconds=10)
    async def rule34_task(self):
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            # Optional: Add fetch_channel logic if strictly needed, 
            # but get_channel is safer for loops to avoid API spam.
            return

        # Randomize PID (Page ID) 
        # Kept range smaller (0-10) to ensure you actually hit pages with content
        random_pid = random.randint(0, 10)

        url = "https://api.rule34.xxx/index.php"
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": "1",
            "limit": "100", # Fetching 100 posts gives better variety
            "pid": random_pid,
            "tags": self.tags,
            "api_key": self.api_key,
            "user_id": self.user_id
        }
        
        headers = {
            "User-Agent": "ModBot/3.3.0 (Discord Bot)"
        }

        try:
            # Use the persistent session created in cog_load
            async with self.session.get(url, params=params, headers=headers, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Rule34 API returned status: {response.status}")
                    return
                
                # Check for valid JSON content type to avoid crashing on HTML errors
                if response.content_type == 'application/json':
                    data = await response.json()
                else:
                    return

            if not data or not isinstance(data, list):
                return

            post = random.choice(data)
            file_url = post.get("file_url")
            
            if not file_url:
                return

            embed = discord.Embed(
                title="🔥 Rule34 Ecchi Drop",
                url=f"https://rule34.xxx/index.php?page=post&s=view&id={post.get('id')}",
                color=0xffa500 
            )
            embed.set_image(url=file_url)
            
            # Map the rating letter to a word for the footer
            rating_map = {"q": "Questionable", "e": "Explicit", "s": "Safe"}
            rating_text = rating_map.get(post.get('rating'), post.get('rating'))
            
            embed.set_footer(text=f"ID: {post.get('id')} • 10s Loop • Rating: {rating_text}")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Rule34 Loop Error: {e}")

    @rule34_task.before_loop
    async def before_rule34_task(self):
        await self.bot.wait_until_ready()
        # Fallback ensure session exists
        if not self.session:
            self.session = aiohttp.ClientSession()

async def setup(bot):
    await bot.add_cog(Rule34Loop(bot))
