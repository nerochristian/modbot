import discord
from discord.ext import commands, tasks
import aiohttp
import random
import logging

logger = logging.getLogger("ModBot")

class Rule34Loop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = 1463001859345354968
        
        # Rule34 simplified Ecchi tags: 'femboy' + 'rating:q' (Questionable)
        self.tags = "femboy rating:q"
        
        self.api_key = "4b5d1fd9db037eeb8b534b57f7d3d5e7f58f8ad8d3045fb75bd4f11f3db95345bef64f2551fd74a43b62b3f544996df06b01fec2cbb4b4cae335168f207855f2"
        self.user_id = "1900224"
        
        self.rule34_task.start()

    def cog_unload(self):
        self.rule34_task.cancel()

    @tasks.loop(seconds=10)
    async def rule34_task(self):
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except:
                return

        # We use 'pid' (page ID) for randomness instead of 'sort:random' 
        # to ensure the API doesn't return an empty list.
        random_page = random.randint(0, 10)

        url = "https://api.rule34.xxx/index.php"
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": "1",
            "limit": "50",
            "pid": random_page,
            "tags": self.tags,
            "api_key": self.api_key,
            "user_id": self.user_id
        }
        
        headers = {"User-Agent": "ModBot/3.3.0 (Discord Bot)"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        return
                    data = await response.json()
                    
            if not data or not isinstance(data, list):
                # Fallback: If 'rating:q' fails, try 'rating:s' for Sensitive
                return

            post = random.choice(data)
            file_url = post.get("file_url")
            
            if not file_url:
                return

            embed = discord.Embed(
                title="🔥 Rule34 Ecchi Drop",
                url=f"https://rule34.xxx/index.php?page=post&s=view&id={post['id']}",
                color=0xffa500 
            )
            embed.set_image(url=file_url)
            embed.set_footer(text=f"ID: {post['id']} • 10s Loop")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Rule34 Loop Error: {e}")

    @rule34_task.before_loop
    async def before_rule34_task(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Rule34Loop(bot))
