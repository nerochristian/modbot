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
        
        # 'rating:sensitive' and 'rating:questionable' cover the "Ecchi" spectrum.
        # '-rating:explicit' ensures no full porn is sent.
        self.tags = "femboy rating:sensitive rating:questionable -rating:explicit sort:random"
        
        self.api_key = "4b5d1fd9db037eeb8b534b57f7d3d5e7f58f8ad8d3045fb75bd4f11f3db95345bef64f2551fd74a43b62b3f544996df06b01fec2cbb4b4cae335168f207855f2"
        self.user_id = "1900224"
        
        self.gelbooru_task.start()

    def cog_unload(self):
        self.gelbooru_task.cancel()

    @tasks.loop(seconds=10)
    async def gelbooru_task(self):
        await self.bot.wait_until_ready()
        
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            return

        url = "https://gelbooru.com/index.php"
        
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": "1",
            "limit": "1",
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
                    
            if not data or "post" not in data:
                # If nothing is found, we broaden the search slightly
                logger.warning("No ecchi posts found with current tags.")
                return

            post = data["post"][0]
            file_url = post["file_url"]
            
            embed = discord.Embed(
                title="🔥 Ecchi Femboy Drop",
                url=f"https://gelbooru.com/index.php?page=post&s=view&id={post['id']}",
                color=0xe91e63 # Hot pink color
            )
            embed.set_image(url=file_url)
            embed.set_footer(text=f"Gelbooru ID: {post['id']} • Rating: {post['rating']}")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Loop error: {e}")

async def setup(bot):
    await bot.add_cog(GelbooruLoop(bot))
