import discord
from discord.ext import commands, tasks
import aiohttp
import random
import logging

logger = logging.getLogger("ModBot")

class Rule34Loop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = 1463001859345354968 
        
        self.api_key = "4b5d1fd9db037eeb8b534b57f7d3d5e7f58f8ad8d3045fb75bd4f11f3db95345bef64f2551fd74a43b62b3f544996df06b01fec2cbb4b4cae335168f207855f2"
        self.user_id = "1900224"
        
        # UPDATED TAGS FOR ECCHI (Not Porn):
        # rating:questionable = The specific tag for "Ecchi" (suggestive/nudity but not explicit sex)
        # -rating:explicit = Double safety to block hardcore content
        # Removed 'score' to ensure you get results immediately.
        self.tags = "femboy rating:questionable -rating:explicit"
        
        self.session = None
        self.rule34_task.start()

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        self.rule34_task.cancel()
        if self.session:
            await self.session.close()

    @tasks.loop(seconds=10)
    async def rule34_task(self):
        channel = self.bot.get_channel(self.channel_id)
        
        if not channel:
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except Exception as e:
                print(f"Error finding channel: {e}")
                return

        # Ecchi (Questionable) has way more images than Safe, so we can check more pages.
        # Randomize Page 0-5 to keep it fresh but ensuring hits.
        random_pid = random.randint(0, 5)

        url = "https://api.rule34.xxx/index.php"
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": "1",
            "limit": "100", 
            "pid": random_pid,
            "tags": self.tags,
            "api_key": self.api_key,
            "user_id": self.user_id
        }
        
        headers = {"User-Agent": "ModBot/3.3.0 (Discord Bot)"}

        try:
            async with self.session.get(url, params=params, headers=headers, timeout=10) as response:
                if response.status != 200:
                    print(f"API Error: {response.status}")
                    return
                
                if response.content_type == 'application/json':
                    data = await response.json()
                else:
                    return

            if not data or not isinstance(data, list):
                print(f"No images found on Page {random_pid}. Retrying next loop.")
                return

            post = random.choice(data)
            file_url = post.get("file_url")
            
            if not file_url:
                return

            embed = discord.Embed(
                title="🔥 Ecchi Femboy Drop",
                url=f"https://rule34.xxx/index.php?page=post&s=view&id={post.get('id')}",
                color=0xffa500 # Orange for Questionable/Ecchi
            )
            embed.set_image(url=file_url)
            embed.set_footer(text=f"ID: {post.get('id')} • Rating: Questionable (Ecchi)")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Loop Error: {e}")

    @rule34_task.before_loop
    async def before_rule34_task(self):
        await self.bot.wait_until_ready()
        if not self.session:
            self.session = aiohttp.ClientSession()

async def setup(bot):
    await bot.add_cog(Rule34Loop(bot))
