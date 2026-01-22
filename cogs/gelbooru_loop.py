import discord
from discord.ext import commands, tasks
import aiohttp
import random
import logging

logger = logging.getLogger("ModBot")

class SafebooruLoop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = 1463001859345354968
        self.tags = "femboy"
        
        self.api_key = "4b5d1fd9db037eeb8b534b57f7d3d5e7f58f8ad8d3045fb75bd4f11f3db95345bef64f2551fd74a43b62b3f544996df06b01fec2cbb4b4cae335168f207855f2"
        self.user_id = "1900224"
        
        self.safebooru_task.start()

    def cog_unload(self):
        self.safebooru_task.cancel()

    @tasks.loop(seconds=30)
    async def safebooru_task(self):
        await self.bot.wait_until_ready()
        
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            return

        base_url = "https://safebooru.org/index.php"
        
        # We add 'pid' to pick a random page (0 to 20 usually covers ~1000 images)
        random_page = random.randint(0, 20) 
        
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": "1",
            "limit": "50",
            "pid": random_page, # This is the magic fix
            "tags": self.tags,
            "api_key": self.api_key,
            "user_id": self.user_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status != 200:
                        return
                    data = await response.json()
                    
            if not data:
                return

            post = random.choice(data)
            
            # Safebooru Image URL Construction
            image_name = post["image"]
            directory = post["directory"]
            file_url = f"https://safebooru.org/images/{directory}/{image_name}"
            
            embed = discord.Embed(
                title="✨ SFW Femboy Drop",
                url=f"https://safebooru.org/index.php?page=post&s=view&id={post['id']}",
                color=0x00aeef
            )
            embed.set_image(url=file_url)
            embed.set_footer(text=f"ID: {post['id']} • Page: {random_page}")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error: {e}")

async def setup(bot):
    await bot.add_cog(SafebooruLoop(bot))
