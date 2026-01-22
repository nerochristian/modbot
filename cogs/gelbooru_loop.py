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
        
        # Rule34 tags for 'Ecchi': 
        # Using -rating:general and -rating:explicit is the most reliable way 
        # to find the "Questionable/Sensitive" middle ground.
        self.tags = "femboy -rating:general -rating:explicit sort:random"
        
        self.api_key = "4b5d1fd9db037eeb8b534b57f7d3d5e7f58f8ad8d3045fb75bd4f11f3db95345bef64f2551fd74a43b62b3f544996df06b01fec2cbb4b4cae335168f207855f2"
        self.user_id = "1900224"
        
        self.rule34_task.start()

    def cog_unload(self):
        self.rule34_task.cancel()

    @tasks.loop(seconds=10) # Set to 10 seconds
    async def rule34_task(self):
        await self.bot.wait_until_ready()
        
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            return

        url = "https://api.rule34.xxx/index.php"
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": "1",
            "limit": "20", # Fetch more to ensure we get a valid image
            "tags": self.tags,
            "api_key": self.api_key,
            "user_id": self.user_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    # Rule34 sometimes returns text/html on error, safety check:
                    if response.status != 200:
                        return
                    data = await response.json()
                    
            # Check if data is a list (valid) or a dict/string (error/empty)
            if not isinstance(data, list) or len(data) == 0:
                return

            # Pick a random post from the returned list
            post = random.choice(data)
            
            # Ensure the post has the expected image data
            if "file_url" not in post:
                return

            file_url = post["file_url"]
            
            embed = discord.Embed(
                title="🔥 Rule34 Ecchi Drop",
                url=f"https://rule34.xxx/index.php?page=post&s=view&id={post['id']}",
                color=0xffa500 
            )
            embed.set_image(url=file_url)
            embed.set_footer(text=f"R34 ID: {post['id']} | Rating: {post['rating']} | 10s Loop")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            # This logs the specific error to your console for debugging
            logger.error(f"Rule34 Loop Error: {e}")

async def setup(bot):
    await bot.add_cog(Rule34Loop(bot))
