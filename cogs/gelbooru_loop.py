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
        self.tags = "femboy -rating:general -rating:explicit sort:random"
        self.last_post_id = None # Prevent back-to-back duplicates
        
        self.api_key = "4b5d1fd9db037eeb8b534b57f7d3d5e7f58f8ad8d3045fb75bd4f11f3db95345bef64f2551fd74a43b62b3f544996df06b01fec2cbb4b4cae335168f207855f2"
        self.user_id = "1900224"
        
        self.rule34_task.start()

    def cog_unload(self):
        self.rule34_task.cancel()

    @tasks.loop(seconds=10)
    async def rule34_task(self):
        if not self.bot.is_ready():
            return

        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            # Fallback if channel isn't in cache
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except:
                logger.error(f"Could not find channel {self.channel_id}")
                return

        url = "https://api.rule34.xxx/index.php"
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": "1",
            "limit": "10",
            "tags": self.tags,
            "api_key": self.api_key,
            "user_id": self.user_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status != 200:
                        logger.warning(f"R34 API returned status {response.status}")
                        return
                    data = await response.json()
                    
            if not data or not isinstance(data, list):
                return

            # Filter out the last post we sent
            valid_posts = [p for p in data if p.get('id') != self.last_post_id]
            if not valid_posts:
                return
                
            post = random.choice(valid_posts)
            self.last_post_id = post.get('id')
            
            file_url = post.get("file_url")
            if not file_url:
                return

            embed = discord.Embed(
                title="🔥 Rule34 Ecchi Drop",
                url=f"https://rule34.xxx/index.php?page=post&s=view&id={post['id']}",
                color=0xffa500 
            )
            embed.set_image(url=file_url)
            embed.set_footer(text=f"ID: {post['id']} | 10s Loop")
            
            await channel.send(embed=embed)
            logger.info(f"Successfully sent image {post['id']} to {self.channel_id}")
            
        except Exception as e:
            logger.error(f"Rule34 Loop Error: {e}")

async def setup(bot):
    await bot.add_cog(Rule34Loop(bot))
