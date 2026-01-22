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
        
        # Rule34 uses the same rating system. 
        # We use 'rating:questionable' for ecchi and 'sort:random' for variety.
        self.tags = "femboy rating:questionable sort:random"
        
        # Rule34 API is public and usually doesn't require these, 
        # but we'll keep them in the params for consistency.
        self.api_key = "4b5d1fd9db037eeb8b534b57f7d3d5e7f58f8ad8d3045fb75bd4f11f3db95345bef64f2551fd74a43b62b3f544996df06b01fec2cbb4b4cae335168f207855f2"
        self.user_id = "1900224"
        
        self.rule34_task.start()

    def cog_unload(self):
        self.rule34_task.cancel()

    @tasks.loop(seconds=10)
    async def rule34_task(self):
        await self.bot.wait_until_ready()
        
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            return

        # Changed endpoint to Rule34
        url = "https://api.rule34.xxx/index.php"
        
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
                    
            if not data:
                logger.warning(f"Rule34: No posts found for {self.tags}")
                return

            # Rule34 returns a list of dictionaries directly
            post = data[0]
            file_url = post["file_url"]
            
            embed = discord.Embed(
                title="🔥 Rule34 Ecchi Drop",
                url=f"https://rule34.xxx/index.php?page=post&s=view&id={post['id']}",
                color=0xffa500 # Orange theme for Rule34
            )
            embed.set_image(url=file_url)
            embed.set_footer(text=f"R34 ID: {post['id']} | Rating: {post['rating']}")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Rule34 Loop Error: {e}")

async def setup(bot):
    await bot.add_cog(Rule34Loop(bot))
