import discord
from discord.ext import commands, tasks
import aiohttp
import random
import logging

logger = logging.getLogger("ModBot")

class GelbooruLoop(commands.Cog):
    """Background task to send images from Gelbooru every 30 seconds"""
    
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = 1463001859345354968
        self.tags = "femboy"
        
        # Authentication credentials
        self.api_key = "4b5d1fd9db037eeb8b534b57f7d3d5e7f58f8ad8d3045fb75bd4f11f3db95345bef64f2551fd74a43b62b3f544996df06b01fec2cbb4b4cae335168f207855f2"
        self.user_id = "1900224"
        
        self.gelbooru_task.start()

    def cog_unload(self):
        self.gelbooru_task.cancel()

    @tasks.loop(seconds=30)
    async def gelbooru_task(self):
        """Fetch and send a random image/gif from Gelbooru with Authentication"""
        await self.bot.wait_until_ready()
        
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except Exception as e:
                logger.error(f"Failed to fetch channel {self.channel_id}: {e}")
                return

        # Base URL
        base_url = "https://gelbooru.com/index.php"
        
        # Parameters dictionary (Handling API Key and User ID here)
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": "1",
            "limit": "50",
            "tags": self.tags,
            "api_key": self.api_key,
            "user_id": self.user_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Pass params dictionary here - aiohttp handles the formatting
                async with session.get(base_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Gelbooru API returned status {response.status}")
                        return
                    
                    data = await response.json()
                    
            if not data or "post" not in data:
                logger.warning(f"No posts found for tags: {self.tags}")
                return

            posts = data["post"]
            post = random.choice(posts)
            file_url = post["file_url"]
            
            embed = discord.Embed(
                title="✨ New Femboy Drop",
                url=f"https://gelbooru.com/index.php?page=post&s=view&id={post['id']}",
                color=0xff69b4 # Added a pinkish color for style
            )
            embed.set_image(url=file_url)
            embed.set_footer(text=f"Gelbooru ID: {post['id']} • Authenticated Request")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in Gelbooru loop: {e}")

async def setup(bot):
    await bot.add_cog(GelbooruLoop(bot))
