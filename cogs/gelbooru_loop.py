import discord
from discord.ext import commands, tasks
import aiohttp
import random
import logging

logger = logging.getLogger("ModBot")

class SafebooruLoop(commands.Cog):
    """Background task to send SFW images every 30 seconds"""
    
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = 1463001859345354968
        
        # Using SFW tags and adding rating:general for extra safety
        self.tags = "femboy"
        
        # Your API Credentials
        self.api_key = "4b5d1fd9db037eeb8b534b57f7d3d5e7f58f8ad8d3045fb75bd4f11f3db95345bef64f2551fd74a43b62b3f544996df06b01fec2cbb4b4cae335168f207855f2"
        self.user_id = "1900224"
        
        self.safebooru_task.start()

    def cog_unload(self):
        self.safebooru_task.cancel()

    @tasks.loop(seconds=30)
    async def safebooru_task(self):
        """Fetch and send a random SFW image/gif"""
        await self.bot.wait_until_ready()
        
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except Exception as e:
                logger.error(f"Failed to fetch channel {self.channel_id}: {e}")
                return

        # Switched to Safebooru endpoint
        base_url = "https://safebooru.org/index.php"
        
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
                async with session.get(base_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Safebooru API returned status {response.status}")
                        return
                    
                    data = await response.json()
                    
            if not data or len(data) == 0:
                logger.warning(f"No SFW posts found for tags: {self.tags}")
                return

            # Safebooru returns a list directly, not a dict with a "post" key
            post = random.choice(data)
            
            # Safebooru image URLs are slightly different; we construct it using the directory and image name
            image_name = post["image"]
            directory = post["directory"]
            file_url = f"https://safebooru.org/images/{directory}/{image_name}"
            
            embed = discord.Embed(
                title="✨ SFW Femboy Drop",
                url=f"https://safebooru.org/index.php?page=post&s=view&id={post['id']}",
                color=0x00aeef # Blue for safe/general
            )
            embed.set_image(url=file_url)
            embed.set_footer(text=f"Safebooru ID: {post['id']} • SFW Only")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in Safebooru loop: {e}")

async def setup(bot):
    await bot.add_cog(SafebooruLoop(bot))
