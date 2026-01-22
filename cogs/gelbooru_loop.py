import discord
from discord.ext import commands, tasks
import aiohttp
import random
import logging

logger = logging.getLogger("ModBot")

class GelbooruLoop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = 1463001859345354968
        
        # Tags: 'sort:random' prevents repeats. 'rating:general' keeps it safe.
        self.tags = "femboy rating:general sort:random"
        
        self.api_key = "4b5d1fd9db037eeb8b534b57f7d3d5e7f58f8ad8d3045fb75bd4f11f3db95345bef64f2551fd74a43b62b3f544996df06b01fec2cbb4b4cae335168f207855f2"
        self.user_id = "1900224"
        
        self.gelbooru_task.start()

    def cog_unload(self):
        self.gelbooru_task.cancel()

    @tasks.loop(seconds=30)
    async def gelbooru_task(self):
        await self.bot.wait_until_ready()
        
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            return

        # Back to Gelbooru for better results
        url = "https://gelbooru.com/index.php"
        
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": "1",
            "limit": "1", # We only need 1 because sort:random does the work
            "tags": self.tags,
            "api_key": self.api_key,
            "user_id": self.user_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return
                    data = await response.json()
                    
            # Gelbooru format is a dictionary with a "post" list
            if not data or "post" not in data:
                logger.warning("No images found. Try removing 'animated' if this persists.")
                return

            post = data["post"][0]
            file_url = post["file_url"]
            
            embed = discord.Embed(
                title="✨ SFW Femboy Drop",
                url=f"https://gelbooru.com/index.php?page=post&s=view&id={post['id']}",
                color=0xff69b4 
            )
            embed.set_image(url=file_url)
            embed.set_footer(text=f"Gelbooru ID: {post['id']} • Randomly Selected")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Loop error: {e}")

async def setup(bot):
    await bot.add_cog(GelbooruLoop(bot))
