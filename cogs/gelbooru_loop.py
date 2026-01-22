import discord
from discord.ext import commands, tasks
import aiohttp
import random
import logging

logger = logging.getLogger("modbot")

class GelbooruLoop(commands.Cog):
    """Background task to send images from Gelbooru every 30 seconds"""
    
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = 1463001859345354968
        self.tags = "animated+femboy"
        self.gelbooru_task.start()

    def cog_unload(self):
        self.gelbooru_task.cancel()

    @tasks.loop(seconds=30)
    async def gelbooru_task(self):
        """Fetch and send a random image/gif from Gelbooru"""
        await self.bot.wait_until_ready()
        
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except Exception as e:
                logger.error(f"Failed to fetch channel {self.channel_id}: {e}")
                return

        url = f"https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&tags={self.tags}&limit=50"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Gelbooru API returned status {response.status}")
                        return
                    
                    data = await response.json()
                    
            if not data or "post" not in data:
                logger.warning("No posts found for tags: " + self.tags)
                return

            posts = data["post"]
            post = random.choice(posts)
            file_url = post["file_url"]
            
            embed = discord.Embed(
                title="✨ New Femboy Drop",
                color=0xFF69B4, # Hot Pink
                url=f"https://gelbooru.com/index.php?page=post&s=view&id={post['id']}"
            )
            embed.set_image(url=file_url)
            embed.set_footer(text=f"Gelbooru ID: {post['id']} • Every 30s Loop")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in Gelbooru loop: {e}")

async def setup(bot):
    await bot.add_cog(GelbooruLoop(bot))